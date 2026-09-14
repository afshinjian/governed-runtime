"""Runs INSIDE the worker network namespace. No upstream address or credential.

The only host object mounted here is the invocation's Unix socket. This local
HTTP shim lets unmodified CLI clients use that socket as their API endpoint.
"""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import socket
import subprocess
import sys
import threading


class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect('/bridge.sock')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Raw HTTP diagnostics and access logs are deliberately disabled.

    def send_error(self, code, *args):
        self.send_response(code)
        self.end_headers()

    def forward(self):
        upstream = UnixConnection('local-bridge', timeout=30)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 <= length <= 4 << 20 or 'Transfer-Encoding' in self.headers:  # guard:gr08_shim_framing
                self.send_error(400)
                return
            body = self.rfile.read(length)
            upstream.request(self.command, self.path, body, dict(self.headers))
            response = upstream.getresponse()
            data = response.read(4 << 20)
            self.send_response(response.status)
            self.send_header('Content-Type', response.getheader('Content-Type', 'application/json'))
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_error(502)
        finally:
            upstream.close()

    do_GET = do_POST = do_CONNECT = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = forward


def main():
    endpoint_variable, environment_json, *command = sys.argv[1:]
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    environment = dict(os.environ)
    environment.update(json.loads(environment_json))
    environment[endpoint_variable] = f'http://127.0.0.1:{server.server_port}'
    result = subprocess.run(command, env=environment)
    server.shutdown()
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
