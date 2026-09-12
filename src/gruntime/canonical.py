"""Canonical form and content addressing.

Design basis: evidence-model §3.1 (chain construction) steps 2-3.

`canonical_json` is RFC 8785 (JCS): object keys sorted by UTF-16 code unit,
no insignificant whitespace, shortest-round-trip number form. `digest_bytes`
produces the `Hash` scalar used everywhere in the domain model.
"""

from __future__ import annotations

from typing import Any

#: Every `Hash` in the domain model carries this algorithm prefix.
DIGEST_PREFIX = "sha256:"

#: Length of the lowercase hex body that follows :data:`DIGEST_PREFIX`.
DIGEST_HEX_LEN = 64


def canonical_json(value: Any) -> bytes:
    """Serialize `value` to RFC 8785 canonical JSON (evidence-model §3.1 step 2).

    Keys are ordered by UTF-16 code unit, not by code point: a non-BMP key
    sorts after U+FFF0 because its surrogate pair begins at U+D800.
    """
    raise NotImplementedError


def digest_bytes(data: bytes) -> str:
    """Return `"sha256:" + lowerhex(sha256(data))` (evidence-model §3.1 step 3)."""
    raise NotImplementedError


def digest_json(value: Any) -> str:
    """Digest of the canonical form of `value`."""
    raise NotImplementedError


def is_digest(value: str) -> bool:
    """True iff `value` is a well-formed `Hash` scalar."""
    raise NotImplementedError
