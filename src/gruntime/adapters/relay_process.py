"""Worker-only bridge transport. ProcessTransport stays entirely unchanged.

The controller services the Unix socket on its own thread (and SQLite
connection). No host TCP listener, host network sharing, ambient environment,
repository mount, or secret-bearing file is passed into the sandbox.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import os
import selectors
import signal
import socket
import subprocess
import tempfile
import time

from ..canonical import canonical_json
from ..contracts import require
from ..errors import CapabilityDenied
from ..secret_guard import SecretLeak
from ..worker_protocol import RESULT_SCHEMA
from .worker_process import ProcessResult, ProcessTransport


class UnixServer(HTTPServer):
    address_family = socket.AF_UNIX

    def server_bind(self):
        # HTTPServer's TCP hostname lookup has no meaning for AF_UNIX.
        socket.socket.bind(self.socket, self.server_address)
        self.server_name, self.server_port = 'local-bridge', 0

    def handle_error(self, request, client_address):
        pass  # Never let socketserver print an untrusted exception traceback.


class RelayHandler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(min(2, max(.001, self.server.deadline - time.monotonic())))
        super().setup()

    def log_message(self, *args):
        pass

    def send_error(self, code, *args):
        self.send_response(code)
        self.end_headers()

    def forward(self):
        bridge = self.server.bridge
        try:
            lengths = self.headers.get_all('Content-Length', [])
            require(len(lengths) <= 1 and 'Transfer-Encoding' not in self.headers,
                    'RELAY_FRAMING', CapabilityDenied)  # guard:gr08_http_framing
            length = int(lengths[0]) if lengths else 0
            require(0 <= length <= 4 << 20, 'RELAY_REQUEST_LIMIT', CapabilityDenied)  # guard:gr08_http_limit
            require(time.monotonic() < self.server.deadline,
                    'RELAY_DEADLINE', CapabilityDenied)  # guard:gr08_http_deadline
            result = bridge.request_network(self.command, self.path, dict(self.headers), self.rfile.read(length))
            data = result['body'].encode('utf-8')
            bridge._controller.secret_guard.check((result['headers'], data))  # guard:gr08_http_delivery
        except Exception as exc:
            # Neither upstream/server exception text nor request bytes are echoed.
            if isinstance(exc, SecretLeak):
                bridge.secret_failure = True
            code = 'SECRET_LEAK' if isinstance(exc, SecretLeak) or bridge.secret_failure else 'RELAY_DENIED'
            data = canonical_json({'error': code})
            result = dict(status=403, headers={'Content-Type': 'application/json'})
        self.send_response(result['status'])
        for key, value in result['headers'].items():
            self.send_header(key, value)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_CONNECT = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = forward


class WorkerRelayTransport(ProcessTransport):
    def run_worker(self, argv, payload, *, bridge, endpoint_environment, timeout,
                   max_output_bytes, cancelled=lambda: False):
        from ..worker_bridge import InvocationBridge
        require(isinstance(bridge, InvocationBridge), 'WORKER_BRIDGE_REQUIRED', CapabilityDenied)  # guard:gr08_worker_only
        guard = bridge._controller.secret_guard
        endpoint_variable, environment = endpoint_environment
        guard.check((payload, argv, endpoint_variable, environment))  # guard:gr08_process_input
        with tempfile.TemporaryDirectory(prefix='gr-relay-') as temporary:
            root = Path(temporary)
            schema = root / 'result.schema.json'
            schema_data = canonical_json(RESULT_SCHEMA)
            guard.check(schema_data)  # guard:gr08_schema_write
            schema.write_bytes(schema_data)
            socket_path = str(root / 'bridge.sock')
            with UnixServer(socket_path, RelayHandler) as server:
                os.chmod(socket_path, 0o600)
                server.bridge, server.deadline = bridge, time.monotonic() + timeout
                command = [self.sandbox, '--unshare-all', '--die-with-parent', '--new-session', '--cap-drop', 'ALL']  # guard:gr08_worker_isolation
                for path in ('/usr', '/bin', '/lib', '/lib64'):
                    if Path(path).exists():
                        command += ['--ro-bind', path, path]
                command += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--tmpfs', '/home',
                    '--dir', '/home/worker', '--chdir', '/home/worker', '--clearenv',
                    '--setenv', 'HOME', '/home/worker', '--setenv', 'PATH', '/usr/local/bin:/usr/bin:/bin']  # guard:gr08_worker_environment
                command += ['--ro-bind', str(schema), '/result.schema.json',
                    '--ro-bind', socket_path, '/bridge.sock',
                    '--ro-bind', str(Path(__file__).with_name('relay_client.py')), '/relay-client.py',
                    '--', '/usr/bin/python3', '/relay-client.py', endpoint_variable, canonical_json(environment).decode(),
                    self.executable, *self.prefix, *argv]
                with tempfile.TemporaryFile() as input_file:
                    input_file.write(payload)
                    input_file.seek(0)
                    with subprocess.Popen(command, stdin=input_file, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env={}, start_new_session=True) as process:
                        streams = {process.stdout: bytearray(), process.stderr: bytearray()}
                        timed_out = truncated = False
                        try:
                            with selectors.DefaultSelector() as selector:
                                for stream in streams:
                                    selector.register(stream, selectors.EVENT_READ)
                                selector.register(server, selectors.EVENT_READ)
                                while any(key.fileobj in streams for key in selector.get_map().values()):
                                    if time.monotonic() >= server.deadline or cancelled():  # guard:gr08_process_deadline
                                        timed_out = not cancelled()
                                        break
                                    for key, _ in selector.select(.02):
                                        if key.fileobj is server:
                                            server.handle_request()
                                            continue
                                        data = os.read(key.fileobj.fileno(), 65536)
                                        if not data:
                                            selector.unregister(key.fileobj)
                                            continue
                                        room = max_output_bytes - sum(map(len, streams.values()))
                                        # Scan BEFORE truncation discards a secret suffix.
                                        guard.check(bytes(streams[key.fileobj]) + data)  # guard:gr08_process_output
                                        streams[key.fileobj].extend(data[:max(0, room)])
                                        if len(data) > room:  # guard:gr08_process_output_limit
                                            truncated = True
                                            break
                                    if truncated:
                                        break
                        finally:
                            if process.poll() is None:  # guard:gr08_process_kill
                                os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
                return ProcessResult(bytes(streams[process.stdout]), bytes(streams[process.stderr]),
                                     process.returncode, timed_out, truncated)
