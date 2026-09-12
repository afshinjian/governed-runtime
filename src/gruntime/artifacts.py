"""Content-addressed artifact store.

Design basis: evidence-model §3.2 step 1 (payload written before the event),
§3.3 payload binding, domain-model §1.2 (`ArtifactRef`).

The store is keyed by digest, so writing the same bytes twice yields one
object. Reads re-hash what they read: a payload that no longer matches its key
is an `IntegrityViolation`, never a silently different artifact.
"""

from __future__ import annotations

from pathlib import Path

from .models import ArtifactRef, Encoding, Hash, RetentionClass


class ArtifactStore:
    """A content-addressed store rooted at `root`."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def put(
        self,
        data: bytes,
        *,
        media_type: str,
        encoding: Encoding = Encoding.IDENTITY,
        retention_class: RetentionClass = RetentionClass.STANDARD,
    ) -> ArtifactRef:
        """Store `data` and return its ref. Idempotent on content."""
        raise NotImplementedError

    def get(self, digest: Hash) -> bytes:
        """Return the stored bytes for `digest`.

        Raises `KeyError` when the digest is unknown, and `IntegrityViolation`
        when the stored bytes no longer hash to it.
        """
        raise NotImplementedError

    def has(self, digest: Hash) -> bool:
        """True iff an object is stored under `digest`."""
        raise NotImplementedError

    def path_for(self, digest: Hash) -> Path:
        """On-disk location of the object stored under `digest`."""
        raise NotImplementedError
