"""GR-08: actual TLS requests, hostile destinations, OS isolation and sinks."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import ssl
import subprocess
import threading
import time

import pytest

from gruntime.adapters.claude_code import ClaudeCodeProvider
from gruntime.adapters.relay_process import WorkerRelayTransport
from gruntime.adapters.worker_process import ProcessResult, ProcessTransport
from gruntime.canonical import canonical_json, digest_bytes, digest_json
from gruntime.controller import Controller
from gruntime.decision import decision_content_hash
from gruntime.errors import CapabilityDenied
from gruntime.inference_relay import CAPABILITY, TOOL, InferenceRelay, destination
from gruntime.models import (ActorKind, ActorRef, AuthMethod, Budget, DecisionKind, DecisionScope,
    DecisionState, DecisionSubjectKind, EpistemicClass, GovernanceMode, InvocationStatus, TerminationReason)
from gruntime.provider import ToolCall
from genesis_support import OWNER
from gruntime.secret_guard import SecretGuard, SecretLeak
from gruntime.store import StateStore, now_ts
from gruntime.worker_bridge import InvocationBridge, WorkerLease
from gruntime.worker_protocol import strict_json
from gr06_support import document
from test_gr07_workers import Transport, envelope, wire


SECRET = 'sk-gr08-canary-7c73586e9868447ab9c54c79'
NAME = 'inference-key'
OWNER = ActorRef(ActorKind.HUMAN, 'relay-owner', AuthMethod.SESSION, principal_key_id='owner-key')


@pytest.fixture(scope='module')
def certificate(tmp_path_factory):
    root = tmp_path_factory.mktemp('tls')
    cert, key = root/'cert.pem', root/'key.pem'
    subprocess.run(['/usr/bin/openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
        '-keyout', str(key), '-out', str(cert), '-days', '1', '-subj', '/CN=localhost',
        '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1'], check=True, capture_output=True)
    return cert, key


@contextmanager
def tls_server(certificate):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            requests.append(dict(path=self.path, headers=dict(self.headers), body=body))
            status, headers, data = server.reply(self.path, body)
            self.send_response(status)
            for name, value in headers.items(): self.send_header(name, value)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            try:
                if getattr(server, 'trickle', False):
                    for byte in data:
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                        time.sleep(.02)
                else:
                    self.wfile.write(data)
            except (BrokenPipeError, ssl.SSLError): pass
        do_GET = do_POST
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.reply = lambda path, body: (200, {'Content-Type':'application/json'}, b'{"answer":"ok"}')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(*map(str, certificate))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.origin = f'https://127.0.0.1:{server.server_port}'
    server.requests = requests
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def upstream(certificate):
    with tls_server(certificate) as server:
        yield server


def decision(c, project, *, kind=DecisionKind.GRANT_CAPABILITY,
             subject_kind=DecisionSubjectKind.PROJECT, subject=None,
             scope=DecisionScope.PROJECT, chosen='yes', grants=()):
    return c.record_decision(project, decision_kind=kind, subject_kind=subject_kind,
        subject_id=subject or project, scope=scope, chosen=chosen, question='Allow this action?',
        justification='Test decision', options_offered=(chosen,), decided_by=OWNER,
        evidence_shown=(c.store.store_artifact(b'relay evidence', media_type='text/plain'),),
        grants=frozenset(grants))


@pytest.fixture
def ctx(h):
    h.init_repo()
    (h.repo_dir/'src').mkdir()
    with h.controller(with_repo=True) as c:
        project = c.create_project(name='Relay', slug='relay', workspace_root=str(h.repo_dir),
                                   approved_by=OWNER)
        c.start(project)
        run = Controller.open_run(c, project)
        c.take_snapshot(project)
        yield c, project, run


def activate(ctx, *, mode='SUPERVISED', grant_kind='human', requested=True, wall_clock_ms=None):
    c, project_id, run = ctx
    project = c.store.get_project(project_id)
    project.governance_mode = GovernanceMode(mode)
    caps = ['fs.read', 'fs.write', 'commit.propose'] + ([CAPABILITY] if requested else [])
    project.capability_ceiling = frozenset([*caps, 'secret.read'])
    project.budget = Budget(7200000, 1000, 1000, 1000, 1000, 1000)
    evaluations = []
    if grant_kind == 'policy':
        policy = dict(authored_by=dict(actor_kind='HUMAN', actor_id='owner', auth_method='SESSION', principal_key_id='key'), policy_grantable=[CAPABILITY])
        project.policy_digest = c.store.store_artifact(canonical_json(policy), media_type='application/json').digest
    c.store.put_project(project)
    if grant_kind == 'policy': evaluations.append(c.evaluate_grant_policy(project_id))
    doc = document(project_id, c.store.get_run(run).stage_id, capability_request=caps)
    if wall_clock_ms is not None: doc['budget_ceiling']['wall_clock_ms'] = wall_clock_ms
    contract = c.author_contract(doc)
    grants = []
    if grant_kind == 'human': grants.append(decision(c, project_id, grants=[CAPABILITY]).decision_id)
    approval = decision(c, project_id, kind=DecisionKind.APPROVE, subject_kind=DecisionSubjectKind.CONTRACT,
                        subject=contract.contract_id) if mode == 'SUPERVISED' else None
    activation = c.activate_contract(contract.contract_id, run, decision_ids=grants,
        policy_evaluation_ids=evaluations, approval_id=approval.decision_id if approval else None)
    return contract, activation, grants


def configure(ctx, upstream, certificate, **changes):
    c, project, run = ctx
    grant = decision(c, project, grants=['secret.read'])
    approval = decision(c, project, kind=DecisionKind.APPROVE,
        subject_kind=DecisionSubjectKind.CAPABILITY, subject='secret.read',
        scope=DecisionScope.SINGLE_ACTION, chosen=NAME)
    options = dict(origin=upstream.origin, secret_name=NAME, resolve_secret=lambda name: SECRET,
        grant_decision_id=grant.decision_id, approval_id=approval.decision_id,
        ca_file=str(certificate[0]), protocol_headers=ClaudeCodeProvider.relay_headers)
    options.update(changes)
    c.configure_inference_relay(run, **options)
    return grant, approval, options


def bridge_for(ctx):
    c, _, run = ctx
    transport = Transport(ClaudeCodeProvider)
    provider = ClaudeCodeProvider(c.governance_dir/'workers', transport=transport, read_artifact=c.store.artifact_bytes)
    c.register_provider(provider)
    inv = c.create_invocation(run, prompt=b'Use the relay', provider_id=provider.provider_id)
    request = c._request_for(inv)
    lease = WorkerLease('lease', inv.invocation_id, run, inv.controller_epoch, request.deadline_at, request.session_id)
    return InvocationBridge(c, inv, request, lease), inv, provider, transport


def call(bridge, upstream, *, call_id=None, **changes):
    args = dict(url=upstream.origin+'/v1/messages', method='POST', headers={'Content-Type':'application/json'}, body='{}')
    args.update(changes)
    c = bridge._controller
    ref = c.store.store_artifact(canonical_json(args), media_type='application/json')
    return bridge.call(ToolCall(call_id or str(len(bridge.calls)), TOOL, ref, now_ts()))


def assert_no_secret(root):
    for path in Path(root).rglob('*'):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes(), f'leaked to {path}'


def test_https_relay_injects_only_at_upstream(ctx, upstream, certificate):
    activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, inv, provider, _ = bridge_for(ctx)
    result = call(bridge, upstream, headers={'Authorization':'worker-forgery', 'Host':'attacker.invalid',
        'X-Api-Key':'worker-forgery', 'anthropic-version':'2023-06-01', 'Cookie':'bad'})
    assert result.outcome == 'OK'
    sent = upstream.requests[0]
    assert sent['headers']['Authorization'] == 'Bearer '+SECRET
    assert sent['headers']['Host'] == upstream.origin.removeprefix('https://')
    assert 'Cookie' not in sent['headers'] and 'X-Api-Key' not in sent['headers']
    assert sent['headers']['anthropic-version'] == '2023-06-01'
    assert strict_json(ctx[0].store.artifact_bytes(result.result_ref.digest))['body'] == '{"answer":"ok"}'
    assert SECRET not in provider._input(bridge._request).decode()
    assert 'secret.read' not in inv.granted_capabilities
    assert_no_secret(ctx[0].governance_dir)
    ctx[0].store.verify_chain(ctx[1])


@pytest.mark.parametrize('mode,grant_kind,requested,allowed', [
    ('SUPERVISED','none',True,False), ('SUPERVISED','policy',True,False),
    ('SUPERVISED','human',False,False), ('SUPERVISED','human',True,True),
    ('AUTONOMOUS','policy',True,True)])
def test_network_needs_admissible_invocation_grant(ctx, upstream, certificate, mode, grant_kind, requested, allowed):
    activate(ctx, mode=mode, grant_kind=grant_kind, requested=requested)
    configure(ctx, upstream, certificate)
    bridge, *_ = bridge_for(ctx)
    assert (call(bridge, upstream).outcome == 'OK') is allowed
    assert len(upstream.requests) == int(allowed)


@pytest.mark.parametrize('change', ['void','expired','stale','consumed','actor','scope','grant','mode','revoked','ceiling','budget','closed','epoch','suspension'])
def test_every_request_rechecks_live_authority(ctx, upstream, certificate, change):
    c, project, run = ctx
    _, _, grants = activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, *_ = bridge_for(ctx)
    assert call(bridge, upstream).outcome == 'OK'
    d = c.store.get_decision(grants[0])
    if change in ('void','stale','consumed'): d.decision_state = DecisionState(change.upper())
    if change == 'expired': d.expires_at = now_ts()-timedelta(seconds=1)
    if change == 'actor': d.decided_by = replace(OWNER, auth_method=AuthMethod.NONE)
    if change == 'scope': d.subject_id = 'other-project'
    if change == 'grant': d.grants = frozenset()
    d.decision_hash = decision_content_hash(d)
    c.store.put_decision(d)
    if change in ('expired', 'actor', 'scope', 'grant'):
        from gruntime.store import actor_to_json
        c.store.connection.execute('UPDATE decisions SET expires_at=?,decided_by=?,subject_id=?,grants=?,decision_hash=? WHERE decision_id=?',
            (d.expires_at.isoformat() if d.expires_at else None, actor_to_json(d.decided_by), d.subject_id,
             canonical_json(sorted(d.grants)).decode(), d.decision_hash, d.decision_id))
    p = c.store.get_project(project)
    if change == 'mode': p.governance_mode = GovernanceMode.AUTONOMOUS
    if change == 'ceiling': p.capability_ceiling = frozenset()
    if change == 'budget': p.budget = Budget()
    if change == 'epoch': p.controller_epoch += 1
    c.store.put_project(p)
    if change == 'closed': bridge.close()
    if change == 'revoked': c.revoke_contract(c.store.activation_for_run(run).contract_id)
    if change == 'suspension':
        from gruntime.models import SuspensionState
        r = c.store.get_run(run)
        r.suspension = SuspensionState.SUSPENDED_BY_HUMAN
        c.store.put_run(r)
    assert call(bridge, upstream).outcome == 'DENIED'
    assert len(upstream.requests) == 1


@pytest.mark.parametrize('target', ['other-port','other-host','http','userinfo','suffix','scheme-relative','absolute-path','backslash','fragment','control'])
def test_other_destinations_make_zero_requests(ctx, upstream, certificate, target):
    activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, *_ = bridge_for(ctx)
    with tls_server(certificate) as forbidden:
        url = {'other-port':forbidden.origin, 'other-host':upstream.origin.replace('127.0.0.1','localhost'),
            'http':upstream.origin.replace('https:','http:'), 'userinfo':upstream.origin.replace('https://','https://user@'),
            'suffix':upstream.origin.replace('127.0.0.1','127.0.0.1.attacker.invalid'),
            'scheme-relative':'//127.0.0.1', 'absolute-path':upstream.origin+'//attacker.invalid/path',
            'backslash':upstream.origin+'\\@attacker.invalid', 'fragment':upstream.origin+'/#elsewhere',
            'control':upstream.origin+'/\nattack'}[target]
        assert call(bridge, upstream, url=url).outcome == 'DENIED'
        assert not upstream.requests and not forbidden.requests


@pytest.mark.parametrize('status', [301,302,303,307,308])
@pytest.mark.parametrize('target', ['same','other','http','relative'])
def test_redirects_are_refused_without_following(ctx, upstream, certificate, status, target):
    activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, *_ = bridge_for(ctx)
    with tls_server(certificate) as forbidden:
        location = {'same':upstream.origin+'/other', 'other':forbidden.origin+'/steal',
                    'http':forbidden.origin.replace('https:', 'http:'), 'relative':'/other'}[target]
        upstream.reply = lambda path, body: (status, {'Location':location}, b'')
        assert call(bridge, upstream).outcome == 'DENIED'
        assert len(upstream.requests) == 1 and not forbidden.requests


@pytest.mark.parametrize('where', ['stdout','stderr','claim','mutation','exception','progress','response','response-header'])
def test_secret_never_reaches_any_artifact_or_journal(ctx, upstream, certificate, where, monkeypatch):
    c, project, run = ctx
    activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, inv, provider, transport = bridge_for(ctx)
    def output(request, data):
        if where == 'stdout': return ProcessResult(wire(ClaudeCodeProvider, envelope(request, output=SECRET)))
        if where == 'stderr': return ProcessResult(wire(ClaudeCodeProvider, envelope(request)), stderr=SECRET.encode())
        if where == 'claim': return envelope(request, claims=[dict(subject='x', assertion=SECRET, confidence=1)])
        if where == 'mutation': return envelope(request, proposed_mutations=[dict(op='CREATE', path='x', content=SECRET, rename_to=None, before_digest=None, mode=None)])
        if where == 'exception': raise ValueError(SECRET)
        return envelope(request)
    transport.callback = output
    if where in ('progress','response','response-header'):
        original = provider.invoke
        def invoke(request, actual_bridge):
            if where == 'progress': actual_bridge.progress(SECRET)
            else:
                upstream.reply = lambda path, body: (200, {'Content-Type':SECRET if where == 'response-header' else 'text/plain'}, SECRET.encode() if where == 'response' else b'ok')
                result = call(actual_bridge, upstream)
                assert result.outcome == 'DENIED'
            return original(request, actual_bridge)
        monkeypatch.setattr(provider, 'invoke', invoke)
    receipt = c.invoke(inv.invocation_id)
    assert receipt.termination_reason is TerminationReason.PROVIDER_ERROR
    assert c.store.get_invocation(inv.invocation_id).status is InvocationStatus.FAILED
    assert b'SECRET_LEAK' in c.store.artifact_bytes(receipt.output_digest)
    assert_no_secret(c.governance_dir)


@pytest.mark.parametrize('url', [
    ' http://host', 'https://host/\npart', 'https://host\\escape', 'http://host',
    'https://user@host', 'https://host/#fragment', 'https://h%6fst', 'https://host:0'])
def test_destination_parser_guards(url):
    with pytest.raises(CapabilityDenied):
        destination(url)


@pytest.mark.parametrize('change', [
    {'origin':'https://example.invalid/path'}, {'origin':'https://example.invalid/?query'},
    {'credential_header':'Host'}, {'credential_prefix':'x\r\nInjected: value'},
    {'secret':'key\r\ninjection'}, {'protocol_headers':('Host',)},
])
def test_relay_configuration_guards(change):
    args = dict(run_id='run', origin='https://example.invalid', secret=SECRET, secret_guard=SecretGuard())
    args.update(change)
    with pytest.raises(CapabilityDenied):
        InferenceRelay(**args)


@pytest.mark.parametrize('change,limit', [
    ({'url':'https://elsewhere.invalid/'}, None), ({'method':'CONNECT'}, None),
    ({'headers':{'accept':123}}, None), ({'body':'abc'}, 2),
    ({'body':SECRET}, None), ({'headers':{'accept':'a\r\nHost: elsewhere'}}, None),
    ({'url':'https://example.invalid//elsewhere'}, None),
])
def test_request_guards_precede_transport(change, limit, monkeypatch):
    import gruntime.inference_relay as module
    guard = SecretGuard()
    guard.register(NAME, SECRET)
    relay = InferenceRelay(run_id='run', origin='https://example.invalid', secret=SECRET, secret_guard=guard,
        max_request_bytes=limit or 4096)
    attempts = []
    monkeypatch.setattr(module.http.client, 'HTTPSConnection', lambda *a,**kw: attempts.append('connection'))
    args = dict(url=relay.origin+'/', method='POST', headers={}, body='{}')
    args.update(change)
    with pytest.raises((CapabilityDenied, SecretLeak)):
        relay.execute(args, authorize=lambda: attempts.append('authorized'), timeout=1)
    assert attempts == []


def test_relay_authorization_and_deadline_guards(monkeypatch):
    import gruntime.inference_relay as module
    relay = InferenceRelay(run_id='run', origin='https://example.invalid', secret=SECRET, secret_guard=SecretGuard())
    attempts = []
    monkeypatch.setattr(module.http.client, 'HTTPSConnection', lambda *a,**kw: attempts.append('connection'))
    args = dict(url=relay.origin+'/', method='POST', headers={}, body='')
    def deny(): raise CapabilityDenied('revoked')
    with pytest.raises(CapabilityDenied, match='revoked'):
        relay.execute(args, authorize=deny, timeout=1)
    with pytest.raises(CapabilityDenied, match='RELAY_DEADLINE'):
        relay.execute(args, authorize=lambda: None, timeout=0)
    assert not attempts


@pytest.mark.parametrize('case', ['tls','oversize','response-secret'])
def test_relay_response_guards(ctx, upstream, certificate, case):
    activate(ctx)
    configure(ctx, upstream, certificate, ca_file=None if case == 'tls' else str(certificate[0]))
    relay = ctx[0]._inference_relay
    if case != 'tls':
        upstream.reply = lambda path, body: (200, {}, SECRET.encode() if case == 'response-secret' else b'x'*20)
    if case == 'oversize': relay.max_response_bytes = 10
    args = dict(url=relay.origin+'/', method='POST', headers={}, body='')
    with pytest.raises((ssl.SSLError, CapabilityDenied, SecretLeak)):
        relay.execute(args, authorize=lambda: None, timeout=1)
    assert len(upstream.requests) == (0 if case == 'tls' else 1)


@pytest.mark.parametrize('case', ['grant','approval','integrity','currency','nonce','single-origin'])
def test_secret_resolution_authority_guards(ctx, upstream, certificate, case, monkeypatch):
    c, project, run = ctx
    _, activation, _ = activate(ctx)
    grant = decision(c, project, grants=['secret.read'])
    approval = decision(c, project, kind=DecisionKind.APPROVE, subject_kind=DecisionSubjectKind.CAPABILITY,
        subject='secret.read', scope=DecisionScope.SINGLE_ACTION, chosen=NAME)
    if case == 'single-origin':
        configure(ctx, upstream, certificate)
    if case == 'grant': grant.grants = frozenset()
    if case == 'approval': approval.chosen = 'different-secret'
    if case == 'currency': approval.subject_snapshot_id = 'old-snapshot'
    if case == 'nonce':
        c.store.connection.execute('INSERT INTO grant_nonces VALUES (?,?,?)', (grant.nonce, grant.decision_id, activation.activation_id))
    for d in (grant, approval): d.decision_hash = decision_content_hash(d)
    if case == 'integrity': grant.decision_hash = digest_bytes(b'forged')
    original = c.store.get_decision
    monkeypatch.setattr(c.store, 'get_decision', lambda key: grant if key == grant.decision_id else approval if key == approval.decision_id else original(key))
    resolved = []
    with pytest.raises(CapabilityDenied):
        c.configure_inference_relay(run, origin=upstream.origin, secret_name=NAME,
            resolve_secret=lambda name: resolved.append(name) or SECRET,
            grant_decision_id=grant.decision_id, approval_id=approval.decision_id, ca_file=str(certificate[0]))
    assert resolved == []


def test_secret_approval_consumed_and_resolver_exception_is_safe(ctx, upstream, certificate):
    activate(ctx)
    def fail(name): raise RuntimeError(SECRET)
    with pytest.raises(CapabilityDenied, match='^SECRET_RESOLUTION_FAILED$') as error:
        configure(ctx, upstream, certificate, resolve_secret=fail)
    assert SECRET not in str(error.value)
    assert_no_secret(ctx[0].governance_dir)


def test_secret_name_and_fingerprint_write_guards(tmp_path):
    guard = SecretGuard()
    with pytest.raises(SecretLeak): guard.register(SECRET, SECRET)
    guard = SecretGuard(tmp_path/'checks.json')
    guard.register('clean', SECRET)
    before = guard.path.read_bytes()
    guard.records[0]['name'] = SECRET
    with pytest.raises(SecretLeak): guard.register('other', 'another-value-long-enough')
    assert guard.path.read_bytes() == before


def test_log_and_fake_output_checked_before_write(ctx):
    c = ctx[0]
    c.secret_guard.register(NAME, SECRET)
    with pytest.raises(SecretLeak): c.provider._record('progress', note=SECRET)
    with pytest.raises(SecretLeak): c.provider._store_output('key', SECRET.encode())
    assert_no_secret(c.governance_dir)


@pytest.mark.parametrize('case', ['missing','other-run','grant','revoked','target'])
def test_bridge_network_guards(ctx, upstream, certificate, case):
    c, project, run = ctx
    _, _, grants = activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, *_ = bridge_for(ctx)
    if case == 'missing': c._inference_relay = None
    if case == 'other-run': c._inference_relay.run_id = 'other-run'
    if case in ('missing','other-run'):
        assert call(bridge, upstream).outcome == 'DENIED'
    if case == 'grant':
        bridge._request = replace(bridge._request, granted_capabilities=frozenset())
        with pytest.raises(CapabilityDenied): bridge._network_authority()
    if case == 'revoked':
        d = c.store.get_decision(grants[0])
        d.decision_state = DecisionState.VOID
        c.store.put_decision(d)
        with pytest.raises(CapabilityDenied): bridge._network_authority()
    if case == 'target':
        before = len(list(c.store.artifacts.root.rglob('*')))
        with pytest.raises(CapabilityDenied):
            bridge.request_network('POST', 'https://elsewhere.invalid/', {}, b'')
        assert len(list(c.store.artifacts.root.rglob('*'))) == before
    assert not upstream.requests


@pytest.mark.parametrize('case', ['metadata','diagnostic'])
def test_tool_secret_diagnostics_are_discarded(ctx, upstream, certificate, case, monkeypatch):
    c = ctx[0]
    activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, *_ = bridge_for(ctx)
    if case == 'diagnostic':
        def fail(*args, **kwargs): raise CapabilityDenied(SECRET)
        monkeypatch.setattr(c._inference_relay, 'execute', fail)
    result = call(bridge, upstream, call_id=SECRET if case == 'metadata' else None)
    assert result.outcome == 'DENIED'
    assert bridge.secret_failure
    assert 'SECRET_LEAK' in bridge.violations[-1]['detail']
    assert_no_secret(c.governance_dir)


def test_controller_worker_output_is_checked_before_processing(ctx, upstream, certificate, monkeypatch):
    import gruntime.worker_controller as module
    c = ctx[0]
    activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, inv, provider, _ = bridge_for(ctx)
    # Stand in for an untrusted provider returning previously stored remote
    # bytes. The controller must check before parsing/applying any proposals.
    parsed = []
    original = module.result_document
    def parse(*args):
        parsed.append(True)
        return original(*args)
    monkeypatch.setattr(module, 'result_document', parse)
    monkeypatch.setattr(provider, 'fetch', lambda ref: canonical_json(envelope(bridge._request, output=SECRET)))
    receipt = c.invoke(inv.invocation_id)
    assert b'SECRET_LEAK' in c.store.artifact_bytes(receipt.output_digest)
    assert receipt.termination_reason is TerminationReason.PROVIDER_ERROR
    assert not parsed
    assert_no_secret(c.governance_dir)


def test_controller_diagnostic_is_checked_before_receipt(ctx, upstream, certificate, monkeypatch):
    c = ctx[0]
    activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, inv, provider, _ = bridge_for(ctx)
    receipt_inputs = []
    mint = c._mint_worker_receipt
    def capture(*args, **kwargs):
        receipt_inputs.append(kwargs['output'])
        return mint(*args, **kwargs)
    monkeypatch.setattr(c, '_mint_worker_receipt', capture)
    def fail(*args): raise ValueError(SECRET)
    monkeypatch.setattr(provider, 'invoke', fail)
    receipt = c.invoke(inv.invocation_id)
    assert b'SECRET_LEAK' in c.store.artifact_bytes(receipt.output_digest)
    assert receipt_inputs and all(SECRET.encode() not in data for data in receipt_inputs)
    assert_no_secret(c.governance_dir)


def test_receipt_boundary_discards_tainted_output_and_fields(ctx, upstream, certificate):
    from gruntime.models import Attribution, Usage, Claim
    c = ctx[0]
    activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, inv, *_ = bridge_for(ctx)
    receipt = c._mint_worker_receipt(inv, ctx[1], output=b'clean',
        claims=(Claim(claim_id='claim', subject='s', assertion=SECRET, confidence=1),),
        termination_reason=TerminationReason.COMPLETED, attribution=Attribution.RECONCILED,
        status=InvocationStatus.COMPLETED, usage=Usage())
    assert receipt.termination_reason is TerminationReason.PROVIDER_ERROR
    assert not receipt.claims
    assert b'SECRET_LEAK' in c.store.artifact_bytes(receipt.output_digest)
    assert_no_secret(c.governance_dir)


def test_provider_input_is_checked_before_launch(ctx, upstream, certificate, monkeypatch):
    c = ctx[0]
    activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, inv, provider, transport = bridge_for(ctx)
    monkeypatch.setattr(provider, '_input', lambda r: canonical_json(dict(secret=SECRET)))
    outcome = provider.invoke(bridge._request, bridge)
    assert outcome.termination_reason is TerminationReason.PROVIDER_ERROR
    assert transport.calls == []
    assert b'SECRET_LEAK' in provider.fetch(outcome.output_ref)
    assert_no_secret(c.governance_dir)

    c.store.verify_chain(ctx[1])


def test_fingerprints_survive_restart_and_include_no_values(ctx, upstream, certificate):
    import hashlib
    c, _, _ = ctx
    activate(ctx)
    configure(ctx, upstream, certificate)
    manifest = c.store.db_path.with_suffix('.secrets.json').read_bytes()
    assert NAME.encode() in manifest and SECRET.encode() not in manifest
    assert hashlib.sha256(SECRET.encode()).hexdigest().encode() not in manifest
    other = StateStore.open(c.store.db_path)
    try:
        with pytest.raises(SecretLeak, match='SECRET_LEAK'):
            other.store_artifact(b'prefix '+SECRET.encode()+b' suffix', media_type='text/plain')
    finally: other.close()


@pytest.mark.parametrize('encoding', ['plain','json','base64','url'])
def test_salted_checker_discards_encoded_secrets(tmp_path, encoding):
    from urllib.parse import quote
    guard = SecretGuard(tmp_path/'checks.json')
    value = 'key-with-"quotes"/and+unicode-\u00fc'
    guard.register('key', value)
    data = {'plain':value, 'json':json.dumps(value), 'base64':base64.b64encode(value.encode()).decode(), 'url':quote(value,safe='')}[encoding]
    with pytest.raises(SecretLeak): guard.check('prefix '+data+' suffix')


@pytest.mark.parametrize('sink', ['artifact','media','event-payload','event-subject','event-type','event-actor','state','sql-many','sql-script','progress'])
def test_checks_run_before_sink_write(ctx, upstream, certificate, sink):
    c, project, _ = ctx
    activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, *_ = bridge_for(ctx)
    before = [p for p in c.store.artifacts.root.rglob('*') if p.is_file()]
    seq = c.store.get_project(project).event_seq
    if sink == 'progress':
        bridge.progress(SECRET)
        assert bridge.secret_failure
    else:
        with pytest.raises(SecretLeak):
            if sink == 'artifact': c.store.store_artifact(SECRET.encode(), media_type='text/plain')
            elif sink == 'media': c.store.store_artifact(b'clean', media_type=SECRET)
            elif sink.startswith('event-'):
                field = sink.removeprefix('event-')
                args = dict(event_type='test.append', epistemic_class=EpistemicClass.CLAIM,
                    actor=OWNER, subject={}, payload=b'clean')
                if field == 'payload': args['payload'] = SECRET.encode()
                if field == 'subject': args['subject'] = {'id':SECRET}
                if field == 'type': args['event_type'] = SECRET
                if field == 'actor': args['actor'] = replace(OWNER, actor_id=SECRET)
                c.store.append_event(project, **args)
            elif sink == 'state':
                p = c.store.get_project(project)
                p.name = SECRET
                c.store.put_project(p)
            elif sink == 'sql-many': c.store.connection.executemany('UPDATE projects SET name=? WHERE project_id=?', [(SECRET,project)])
            elif sink == 'sql-script': c.store.connection.executescript("UPDATE projects SET name='"+SECRET+"';")
        assert len([p for p in c.store.artifacts.root.rglob('*') if p.is_file()]) == len(before)
        assert c.store.get_project(project).event_seq == seq
    assert_no_secret(c.governance_dir)


def test_real_worker_uses_bridge_and_validation_remains_isolated(ctx, upstream, certificate, monkeypatch):
    c, project, run = ctx
    activate(ctx)
    configure(ctx, upstream, certificate)
    bridge, inv, provider, _ = bridge_for(ctx)
    monkeypatch.setenv('ANTHROPIC_API_KEY', SECRET)
    monkeypatch.setenv('HTTPS_PROXY', 'http://127.0.0.1:1')
    script = '''import os,socket,urllib.request,json,sys
data=json.load(sys.stdin)
endpoint=os.environ['ANTHROPIC_BASE_URL']
response=urllib.request.urlopen(urllib.request.Request(endpoint+'/v1/messages',data=b'{}')).read().decode()
try:
 socket.create_connection(('127.0.0.1',PORT),timeout=.2)
 direct='allowed'
except OSError: direct='denied'
r=data['request']
doc=dict(version=1,invocation_id=r['invocation_id'],status='COMPLETED',termination_reason='COMPLETED',session=dict(id=r['session_id'],fresh=True,continued_from=None),output=json.dumps(dict(response=response,direct=direct,endpoint=endpoint,key=os.environ.get('ANTHROPIC_API_KEY'),proxy=os.environ.get('HTTPS_PROXY'),home=os.environ.get('HOME'))),claims=[],review=None,proposed_mutations=[],requested_validations=[],tool_calls=[])
print(json.dumps(dict(type='result',subtype='success',is_error=False,structured_output=doc)))
'''.replace('PORT', str(upstream.server_port))
    provider.transport = WorkerRelayTransport('/usr/bin/python3', prefix=('-c',script))
    receipt = c.invoke(inv.invocation_id)
    assert receipt.termination_reason is TerminationReason.COMPLETED, c.store.artifact_bytes(receipt.output_digest)
    output = json.loads(strict_json(c.store.artifact_bytes(receipt.output_digest))['output'])
    assert output['direct'] == 'denied'
    assert output['endpoint'].startswith('http://127.0.0.1:')
    assert output['key'] == 'governed-local-bridge'
    assert output['proxy'] is None and output['home'] == '/home/worker'
    assert len(upstream.requests) == 1
    assert upstream.requests[0]['headers']['Authorization'] == 'Bearer '+SECRET
    probe = "import socket,os,json; s=socket.socket(); s.settimeout(.2); print(json.dumps(dict(connect=s.connect_ex(('127.0.0.1',PORT)),bridge=os.path.exists('/bridge.sock'),key=os.environ.get('ANTHROPIC_API_KEY'))))".replace('PORT',str(upstream.server_port))
    result = ProcessTransport('/usr/bin/python3', prefix=('-c',probe)).run((), b'', timeout=2, max_output_bytes=4096)
    isolated = strict_json(result.stdout)
    assert isolated['connect'] != 0 and isolated['bridge'] is False and isolated['key'] is None
    from gruntime.validation import ValidationExecutor
    from gruntime.validation_catalog import ValidationCatalog, ValidationOperation
    catalog = ValidationCatalog(c.governance_dir/'isolated-catalog.db')
    op = ValidationOperation(operation_id='relay.isolation', version='1.0.0', argv=('/usr/bin/python3','-c',probe),
        parameters={}, cwd='src', env_allowlist=(), network='NONE', timeout_ms=2000,
        write_policy='READ_ONLY', side_effect_class='READ_ONLY', safe_to_rerun=True)
    catalog.register(op)
    snapshot = c.store.newest_complete_snapshot(project)
    validation = ValidationExecutor(catalog, c.artifacts).execute(op.reference, {}, snapshot=snapshot,
        snapshot_document=c.store.snapshot_document(snapshot), workspace_root=Path(c.store.get_project(project).workspace_root),
        run_id=run, op_id='test', prev_event_hash=c.store.get_project(project).event_head)
    assert validation.outcome == 'PASS'
    isolated = strict_json(c.artifacts.get(validation.stdout_ref.digest))
    assert isolated['connect'] != 0 and isolated['bridge'] is False and isolated['key'] is None
    assert len(upstream.requests) == 1
    assert_no_secret(c.governance_dir)
