"""Kernel-only HTTPS execution behind InvocationBridge (WP-4/WP-7/CF-4).

One immutable origin, verified TLS, no proxy discovery, no redirects. Responses
are bounded and checked in full before either persistence or worker delivery.
"""
import http.client
import re
import socket
import ssl
import threading
from urllib.parse import urlsplit

from .contracts import require
from .errors import CapabilityDenied


CAPABILITY = 'net.egress.allowlist'
TOOL = 'net.request'


def destination(url):
    require(type(url) is str and url and not re.search(r'[\s\\\x00-\x1f\x7f]', url),
            'RELAY_DESTINATION_DENIED', CapabilityDenied)  # guard:gr08_url_syntax
    parsed = urlsplit(url)
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username
            and not parsed.password and '@' not in parsed.netloc and '%' not in parsed.netloc
            and not parsed.fragment, 'RELAY_DESTINATION_DENIED', CapabilityDenied)  # guard:gr08_https
    port = parsed.port if parsed.port is not None else 443
    require(0 < port <= 65535, 'RELAY_DESTINATION_DENIED', CapabilityDenied)  # guard:gr08_port
    return parsed, (parsed.hostname.lower(), port)


class InferenceRelay:
    def __init__(self, *, run_id, origin, secret, secret_guard,
                 credential_header='Authorization', credential_prefix='Bearer ',
                 ca_file=None, protocol_headers=(), max_request_bytes=4 << 20, max_response_bytes=4 << 20):
        parsed, self._destination = destination(origin)
        require(parsed.path in ('', '/') and not parsed.query,
                'RELAY_ORIGIN_REQUIRED', CapabilityDenied)  # guard:gr08_origin_config
        require(credential_header.lower() in ('authorization', 'x-api-key')
                and '\r' not in credential_prefix and '\n' not in credential_prefix,
                'RELAY_CREDENTIAL_HEADER', CapabilityDenied)  # guard:gr08_credential_header
        require(type(secret) is str and secret and all(32 <= ord(c) < 127 for c in secret),
                'RELAY_INVALID_SECRET', CapabilityDenied)  # guard:gr08_credential_value
        self.run_id, self.origin = run_id, origin.rstrip('/')
        self._secret = secret
        self._header, self._prefix = credential_header, credential_prefix
        self._protocol_headers = frozenset(h.lower() for h in protocol_headers)
        require(not self._protocol_headers & {'host', 'authorization', 'x-api-key', 'cookie',
                'proxy-authorization', 'connection', 'transfer-encoding', 'content-length', 'upgrade', 'expect'},
                'RELAY_PROTOCOL_HEADERS', CapabilityDenied)  # guard:gr08_protocol_headers
        self.secret_guard = secret_guard
        self._tls = ssl.create_default_context(cafile=ca_file)  # guard:gr08_tls_verification
        self.max_request_bytes, self.max_response_bytes = max_request_bytes, max_response_bytes

    def execute(self, args, *, authorize, timeout):
        parsed, target = destination(args['url'])
        require(target == self._destination, 'RELAY_DESTINATION_DENIED', CapabilityDenied)  # guard:gr08_origin_request
        require(args['method'] in ('GET', 'POST'), 'RELAY_METHOD_DENIED', CapabilityDenied)  # guard:gr08_method
        require(type(args['body']) is str and type(args['headers']) is dict
                and all(type(k) is str and type(v) is str for k, v in args['headers'].items()),
                'RELAY_ARGUMENTS', CapabilityDenied)  # guard:gr08_request_types
        body = args['body'].encode('utf-8')
        require(len(body) <= self.max_request_bytes, 'RELAY_REQUEST_LIMIT', CapabilityDenied)  # guard:gr08_request_limit
        self.secret_guard.check(args)  # guard:gr08_request_secret
        # Host, auth, proxy, cookie, hop-by-hop and framing headers are never
        # worker-controlled. Vendor protocol headers carry no authority.
        headers = {k.lower(): v for k, v in args['headers'].items()
                   if k.lower() in {'content-type', 'accept'} | self._protocol_headers}  # guard:gr08_outbound_headers
        require(all('\r' not in v and '\n' not in v for v in headers.values()),
                'RELAY_HEADER_DENIED', CapabilityDenied)  # guard:gr08_header_injection
        headers.update({self._header: self._prefix + self._secret, 'Accept-Encoding': 'identity'})
        path = parsed.path or '/'
        require(not path.startswith('//'), 'RELAY_DESTINATION_DENIED', CapabilityDenied)  # guard:gr08_request_target
        if parsed.query:
            path += '?' + parsed.query
        # No cached authorization: immediately before every outbound request.
        authorize()  # guard:gr08_request_authority
        require(timeout > 0, 'RELAY_DEADLINE', CapabilityDenied)  # guard:gr08_relay_deadline
        connection = http.client.HTTPSConnection(*self._destination, context=self._tls, timeout=min(timeout, 30))
        expired = threading.Event()
        transport_socket = None
        def interrupt():
            expired.set()
            sock = transport_socket or connection.sock
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        watchdog = threading.Timer(min(timeout, 30), interrupt)
        watchdog.daemon = True
        try:
            watchdog.start()  # guard:gr08_relay_watchdog
            connection.connect()
            transport_socket = connection.sock
            # DNS/TLS may take time. Replay authority after connecting too;
            # only the controller thread may inspect its live StateStore.
            authorize()  # guard:gr08_before_send
            require(not expired.is_set(), 'RELAY_DEADLINE', CapabilityDenied)  # guard:gr08_send_deadline
            connection.request(args['method'], path, body=body, headers=headers)
            response = connection.getresponse()
            require(not 300 <= response.status < 400, 'RELAY_REDIRECT_DENIED', CapabilityDenied)  # guard:gr08_redirect
            data = response.read(self.max_response_bytes + 1)
            require(len(data) <= self.max_response_bytes, 'RELAY_RESPONSE_LIMIT', CapabilityDenied)  # guard:gr08_response_limit
            result = dict(status=response.status, headers={'Content-Type': response.getheader('Content-Type', 'application/json')},
                          body=data.decode('utf-8'))
            self.secret_guard.check((data, response.getheaders(), result))  # guard:gr08_response_secret
            require(not expired.is_set(), 'RELAY_DEADLINE', CapabilityDenied)  # guard:gr08_response_deadline
            return result
        finally:
            watchdog.cancel()
            connection.close()
