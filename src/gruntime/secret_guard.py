"""AS-4/CF-8: reject bytes before a sink sees them, including after restart.

Only salted fingerprints are retained. Scanning never needs the credential
itself; providers may receive this checker, but never a secret resolver/value.
"""
import base64
from dataclasses import asdict, is_dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import quote_from_bytes

from .canonical import canonical_json
from .errors import GovernedRuntimeError


class SecretLeak(GovernedRuntimeError):
    def __init__(self):
        super().__init__('SECRET_LEAK')


class SecretGuard:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.records = json.loads(self.path.read_bytes()) if self.path and self.path.exists() else []

    def register(self, name, value):
        # Encodings commonly used by JSON, HTTP diagnostics and binary tools.
        raw = value.encode('utf-8') if isinstance(value, str) else value
        if not raw:  # guard:gr08_nonempty_secret
            raise ValueError('EMPTY_SECRET')
        variants = {raw, base64.b64encode(raw), quote_from_bytes(raw, safe='').encode()}
        try:
            decoded = raw.decode('utf-8')
            variants.update(json.dumps(decoded, ensure_ascii=ascii_only)[1:-1].encode()
                            for ascii_only in (True, False))
        except UnicodeDecodeError:
            pass
        entries = []
        for variant in (raw, *sorted(variants - {raw})):
            salt = os.urandom(32)
            entries.append(dict(name=name, salt=salt.hex(), length=len(variant),
                digest=hashlib.sha256(salt + variant).hexdigest()))
        self.records.extend(entries)
        self.check(name)  # guard:gr08_secret_name
        if self.path:
            data = canonical_json(self.records)
            self.check(data)  # guard:gr08_fingerprint_write
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.partial')
            with temporary.open('wb') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        return entries[0]

    def check(self, value):
        if is_dataclass(value):
            value = asdict(value)
        if isinstance(value, str):
            value = value.encode('utf-8')
        if isinstance(value, (bytes, bytearray, memoryview)):
            data = bytes(value)
            for record in self.records:
                salt, length = bytes.fromhex(record['salt']), record['length']
                prefix = hashlib.sha256(salt)
                for offset in range(len(data) - length + 1):
                    digest = prefix.copy()
                    digest.update(data[offset:offset + length])
                    if hmac.compare_digest(digest.hexdigest(), record['digest']):  # guard:gr08_secret_match
                        raise SecretLeak()
        elif isinstance(value, dict):
            for key, item in value.items():
                self.check(key)
                self.check(item)
        elif isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                self.check(item)


class GuardedCursor(sqlite3.Cursor):
    def execute(self, sql, parameters=()):
        if self.connection.secret_guard is not None:
            self.connection.secret_guard.check((sql, parameters))  # guard:gr08_cursor_write
        return super().execute(sql, parameters)

    def executemany(self, sql, parameters):
        parameters = list(parameters)
        if self.connection.secret_guard is not None:
            self.connection.secret_guard.check((sql, parameters))  # guard:gr08_cursor_many
        return super().executemany(sql, parameters)

    def executescript(self, sql):
        if self.connection.secret_guard is not None:
            self.connection.secret_guard.check(sql)  # guard:gr08_cursor_script
        return super().executescript(sql)


class GuardedConnection(sqlite3.Connection):
    """Check state and journal writes, not just their audit payload copies."""
    secret_guard = None

    def cursor(self):
        return super().cursor(factory=GuardedCursor)

    def execute(self, sql, parameters=()):
        if self.secret_guard is not None:
            self.secret_guard.check((sql, parameters))  # guard:gr08_sql_write
        return super().execute(sql, parameters)

    def executemany(self, sql, parameters):
        parameters = list(parameters)
        if self.secret_guard is not None:
            self.secret_guard.check((sql, parameters))  # guard:gr08_sql_many
        return super().executemany(sql, parameters)

    def executescript(self, sql):
        if self.secret_guard is not None:
            self.secret_guard.check(sql)  # guard:gr08_sql_script
        return super().executescript(sql)
