"""Independent guards at the HTTP and sandbox persistence boundaries."""
from email.message import Message
from io import BytesIO
from types import SimpleNamespace
import time

import pytest

from gruntime.adapters.relay_process import RelayHandler, WorkerRelayTransport
from gruntime.errors import CapabilityDenied
from gruntime.secret_guard import SecretGuard, SecretLeak
from test_gr08_inference_relay import ctx, activate, bridge_for, SECRET, NAME


@pytest.mark.parametrize('case', ['duplicate-length', 'transfer', 'limit', 'deadline', 'delivery'])
def test_http_boundary_guards(case):
    guard = SecretGuard()
    guard.register(NAME, SECRET)
    forwarded, statuses, written_headers = [], [], []
    def network(*args):
        forwarded.append(args)
        return dict(status=200, headers={'Content-Type':'text/plain'}, body=SECRET if case == 'delivery' else 'clean')
    bridge = SimpleNamespace(request_network=network, secret_failure=False,
                             _controller=SimpleNamespace(secret_guard=guard))
    handler = object.__new__(RelayHandler)
    handler.server = SimpleNamespace(bridge=bridge, deadline=time.monotonic() + (-1 if case == 'deadline' else 10))
    handler.command, handler.path = 'POST', '/'
    handler.headers = Message()
    handler.headers['Content-Length'] = '4194305' if case == 'limit' else '0'
    if case == 'duplicate-length': handler.headers['Content-Length'] = '0'
    if case == 'transfer': handler.headers['Transfer-Encoding'] = 'chunked'
    handler.rfile, handler.wfile = BytesIO(), BytesIO()
    handler.send_response = statuses.append
    handler.send_header = lambda *args: written_headers.append(args)
    handler.end_headers = lambda: None
    handler.forward()
    assert statuses == [403]
    assert len(forwarded) == (1 if case == 'delivery' else 0)
    assert SECRET.encode() not in handler.wfile.getvalue()


def test_worker_only_transport_guard():
    transport = WorkerRelayTransport('/usr/bin/python3', prefix=('-c','pass'))
    with pytest.raises(CapabilityDenied, match='WORKER_BRIDGE_REQUIRED'):
        transport.run_worker((), b'', bridge=None, endpoint_environment=('LOCAL_ENDPOINT', {}),
            timeout=1, max_output_bytes=4096)


@pytest.mark.parametrize('case', ['input','schema','output','deadline','limit','kill'])
def test_worker_transport_guards(ctx, case, monkeypatch):
    import gruntime.adapters.relay_process as module
    c = ctx[0]
    activate(ctx)
    c.secret_guard.register(NAME, SECRET)
    bridge, inv, provider, _ = bridge_for(ctx)
    code = 'pass'
    argv = ()
    timeout, maximum = 2, 4096
    if case == 'input': argv = (SECRET,)
    if case == 'schema': monkeypatch.setattr(module, 'RESULT_SCHEMA', {'description':SECRET})
    if case == 'output': code = "print(" + repr(SECRET[:12]) + "+" + repr(SECRET[12:]) + ")"
    if case == 'deadline':
        code, timeout = 'import time; time.sleep(.4)', .05
    if case == 'limit': code, maximum = 'print("x"*10000)', 32
    if case == 'kill':
        code = 'import time; time.sleep(2)'
        def fail(): raise OSError('monitor failed')
        monkeypatch.setattr(module.selectors, 'DefaultSelector', fail)
    transport = WorkerRelayTransport('/usr/bin/python3', prefix=('-c',code))
    def run():
        return transport.run_worker(argv, b'', bridge=bridge,
            endpoint_environment=provider.relay_environment(), timeout=timeout, max_output_bytes=maximum)
    if case in ('input','schema','output'):
        with pytest.raises(SecretLeak): run()
    elif case == 'kill':
        tick = time.monotonic()
        with pytest.raises(OSError): run()
        assert time.monotonic() - tick < 1
    else:
        result = run()
        assert result.timed_out if case == 'deadline' else result.truncated


@pytest.mark.parametrize('case', ['authorization','send-deadline','response-deadline'])
def test_deadline_and_authority_after_connect(case, monkeypatch):
    import gruntime.inference_relay as module
    from gruntime.inference_relay import InferenceRelay
    sent, authorized = [], []
    class Connection:
        sock = None
        def __init__(self, *args, **kwargs): pass
        def connect(self):
            if case == 'send-deadline': time.sleep(.04)
        def request(self, *args, **kwargs): sent.append(True)
        def close(self): pass
        def getresponse(self): return self
        status = 200
        def read(self, limit):
            if case == 'response-deadline': time.sleep(.04)
            return b'clean'
        def getheader(self, key, default): return default
        def getheaders(self): return []
    monkeypatch.setattr(module.http.client, 'HTTPSConnection', Connection)
    def authorize():
        authorized.append(True)
        if case == 'authorization' and len(authorized) == 2: raise CapabilityDenied('revoked')
    relay = InferenceRelay(run_id='run', origin='https://example.invalid', secret=SECRET, secret_guard=SecretGuard())
    with pytest.raises(CapabilityDenied):
        relay.execute(dict(url=relay.origin+'/', method='POST', headers={}, body=''), authorize=authorize,
                      timeout=.01 if case != 'authorization' else 1)
    assert len(sent) == (1 if case == 'response-deadline' else 0)


from test_gr08_inference_relay import certificate, upstream, configure


def test_watchdog_interrupts_trickling_response(ctx, upstream, certificate):
    import http.client
    activate(ctx)
    configure(ctx, upstream, certificate)
    upstream.trickle = True
    relay = ctx[0]._inference_relay
    tick = time.monotonic()
    with pytest.raises((OSError, CapabilityDenied, http.client.HTTPException)):
        relay.execute(dict(url=relay.origin+'/', method='POST', headers={}, body=''),
                      authorize=lambda: None, timeout=.1)
    assert time.monotonic() - tick < .35


def test_worker_lease_limits_requests_to_wall_budget(ctx, upstream, certificate, monkeypatch):
    from gruntime.models import TerminationReason
    from test_gr08_inference_relay import call
    c = ctx[0]
    activate(ctx, wall_clock_ms=30)
    configure(ctx, upstream, certificate)
    bridge, inv, provider, _ = bridge_for(ctx)
    original = provider.invoke
    def invoke(request, actual_bridge):
        time.sleep(.04)
        assert call(actual_bridge, upstream).outcome == 'DENIED'
        return original(request, actual_bridge)
    monkeypatch.setattr(provider, 'invoke', invoke)
    receipt = c.invoke(inv.invocation_id)
    assert receipt.termination_reason is not TerminationReason.COMPLETED
    assert not upstream.requests


def test_empty_secret_refused_before_fingerprint_write(tmp_path):
    guard = SecretGuard(tmp_path/'fingerprints.json')
    with pytest.raises(ValueError, match='EMPTY_SECRET'):
        guard.register(NAME, '')
    assert not guard.path.exists()


@pytest.mark.parametrize('method', ['execute','executemany','executescript'])
def test_cursor_sinks_reject_before_sqlite_write(ctx, method):
    c, project, _ = ctx
    c.secret_guard.register(NAME, SECRET)
    cursor = c.store.connection.cursor()
    with pytest.raises(SecretLeak):
        if method == 'execute':
            cursor.execute('UPDATE projects SET name=? WHERE project_id=?', (SECRET,project))
        elif method == 'executemany':
            cursor.executemany('UPDATE projects SET name=? WHERE project_id=?', [(SECRET,project)])
        else:
            cursor.executescript("UPDATE projects SET name='"+SECRET+"';")
    assert c.store.get_project(project).name != SECRET


@pytest.mark.parametrize('case', ['length','transfer'])
def test_shim_framing_guard(case, monkeypatch):
    import gruntime.adapters.relay_client as module
    forwarded, statuses = [], []
    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, *args, **kwargs): forwarded.append(args)
        def getresponse(self): return self
        def read(self, limit): return b'clean'
        def getheader(self, key, default): return default
        def close(self): pass
        status = 200
    monkeypatch.setattr(module, 'UnixConnection', Connection)
    handler = object.__new__(module.Handler)
    handler.command, handler.path = 'POST', '/'
    handler.headers = Message()
    handler.headers['Content-Length'] = '-1' if case == 'length' else '0'
    if case == 'transfer': handler.headers['Transfer-Encoding'] = 'chunked'
    handler.rfile, handler.wfile = BytesIO(), BytesIO()
    handler.send_response = statuses.append
    handler.send_header = lambda *args: None
    handler.end_headers = lambda: None
    handler.forward()
    assert not forwarded and statuses == [400]

