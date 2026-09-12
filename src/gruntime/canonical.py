"""Canonical form and content addressing.

Design basis: evidence-model §3.1 (chain construction) steps 2-3.

`canonical_json` is RFC 8785 (JCS): object keys sorted, no insignificant
whitespace, shortest-round-trip number form. `digest_bytes` produces the `Hash`
scalar used everywhere in the domain model.

Key ordering note. JCS states its sort over UTF-16 code units, which orders a
non-BMP key *before* U+E000..U+FFFF because a surrogate pair begins at U+D800.
The runtime orders by scalar value instead — identical to the order of the UTF-8
octets that are actually hashed, and identical for every key outside
U+D800..U+FFFF. `test_canonical_json_orders_by_utf16_code_unit` asserts this
scalar-value order (U+FFF0 before U+1F600); its comment names the UTF-16 rule,
which would give the opposite result for that one pair.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

#: Every `Hash` in the domain model carries this algorithm prefix.
DIGEST_PREFIX = "sha256:"

#: Length of the lowercase hex body that follows :data:`DIGEST_PREFIX`.
DIGEST_HEX_LEN = 64

_DIGEST_RE = re.compile(r"^" + re.escape(DIGEST_PREFIX) + r"[0-9a-f]{%d}$" % DIGEST_HEX_LEN)


def _sort_key(key: str) -> bytes:
    """Ordering key for an object member name.

    The UTF-8 octets are the bytes that get hashed, so ordering by them keeps
    the canonical form and its digest preimage in the same order.
    """
    return key.encode("utf-8")


def _canonicalize(value: Any) -> Any:
    """Recursively rebuild `value` with every mapping in canonical key order."""
    if isinstance(value, dict):
        return {
            key: _canonicalize(value[key])
            for key in sorted(value, key=_sort_key)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def canonical_json(value: Any) -> bytes:
    """Serialize `value` to canonical JSON (evidence-model §3.1 step 2)."""
    return json.dumps(
        _canonicalize(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def digest_bytes(data: bytes) -> str:
    """Return `"sha256:" + lowerhex(sha256(data))` (evidence-model §3.1 step 3)."""
    return DIGEST_PREFIX + hashlib.sha256(data).hexdigest()


def digest_json(value: Any) -> str:
    """Digest of the canonical form of `value`."""
    return digest_bytes(canonical_json(value))


def is_digest(value: str) -> bool:
    """True iff `value` is a well-formed `Hash` scalar."""
    return isinstance(value, str) and _DIGEST_RE.match(value) is not None
