"""Content-addressed artifact store.

Design basis: evidence-model §3.2 step 1 (payload written before the event),
§3.3 payload binding, domain-model §1.2 (`ArtifactRef`).

The store is keyed by digest, so writing the same bytes twice yields one
object. Reads re-hash what they read: a payload that no longer matches its key
is an `IntegrityViolation`, never a silently different artifact.

A write is durable before it is announced: the object file and the directory
entry naming it are both fsynced before `put` returns, so a payload referenced
by an event that survived a crash is on disk too.
"""

from __future__ import annotations

import os
from pathlib import Path

from .canonical import digest_bytes, is_digest
from .errors import IntegrityViolation
from .models import ArtifactRef, Encoding, Hash, RetentionClass


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


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
        digest = digest_bytes(data)
        target = self.path_for(digest)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + f".{os.getpid()}.partial")
            with open(temporary, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            _fsync_dir(target.parent)
        return ArtifactRef(
            digest=digest,
            media_type=media_type,
            byte_len=len(data),
            encoding=encoding,
            retention_class=retention_class,
        )

    def get(self, digest: Hash) -> bytes:
        """Return the stored bytes for `digest`.

        Raises `KeyError` when the digest is unknown, and `IntegrityViolation`
        when the stored bytes no longer hash to it (`AS-5`).
        """
        target = self.path_for(digest)
        if not target.exists():
            raise KeyError(digest)
        data = target.read_bytes()
        actual = digest_bytes(data)
        if actual != digest:
            raise IntegrityViolation(
                f"artifact {digest} rehashes to {actual}"
            )
        return data

    def has(self, digest: Hash) -> bool:
        """True iff an object is stored under `digest`."""
        return self.path_for(digest).exists()

    def path_for(self, digest: Hash) -> Path:
        """On-disk location of the object stored under `digest`."""
        if not is_digest(digest):
            raise IntegrityViolation(f"not a content address: {digest!r}")
        body = digest.split(":", 1)[1]
        return self.root / body[:2] / body[2:]
