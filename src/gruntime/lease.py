"""The repository lease: one controller may mutate one repository at a time.

Design basis: domain-model `P-INV-4` and `G-9`, `CM-INV-2`/`CM-INV-3`,
transition-matrix §5 (`RUN-INV-3`).

Recovery rests on being able to say what happened to an operation. Two
controllers mutating one repository at once break that: each scans for its own
`operation_token`, finds it, and neither can tell whether the revision it did
not recognise was left by a crashed predecessor or is being written *right now*
by a live peer. `CM-INV-3`'s "one revision, or provably none" is a statement
about the repository, and it is only true while one controller writes to it.

The lease has two parts, and the split is the whole design:

| part | file | lifetime | what it provides |
|---|---|---|---|
| mutex | `<name>.lock` | the critical section | `flock`, so read-modify-write of the record is atomic between processes |
| lease | `<name>.lease` | until `expires_at` | the durable record of who holds the repository |

`flock` is released by the kernel when the holder dies, which makes it useless
as the lease itself — a `kill -9` would hand the repository to the next
controller instantly, while the dead controller's half-applied mutation is
still on disk. So the lease is a *record with an expiry*, and the flock only
guards the moments the record is read and written. A dead controller's lease
therefore stays held until it expires: reclamation is a decision about elapsed
time, never about whether a pid still exists.

The lease lives in the governance directory, never inside the repository: a
lease file written into the user's checkout would itself be the mutation this
module exists to prevent.
"""

from __future__ import annotations

import fcntl
import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .canonical import canonical_json, digest_bytes
from .errors import LeaseUnavailable

#: How long a lease is honoured without renewal. A crashed holder blocks the
#: repository for exactly this long, so it trades recovery latency against the
#: risk of two controllers overlapping.
DEFAULT_TTL_MS = 300_000

#: Capability the lease is taken and released under. Holding the repository is
#: part of starting to act on it, not a grant of its own.
LEASE_CAPABILITY = "controller.start"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class LeaseRecord:
    """Who holds the repository, and until when."""

    lease_id: str
    holder_id: str
    repository_root: str
    acquired_at: datetime
    expires_at: datetime
    pid: int
    controller_epoch: Optional[int] = None
    reclaimed_from: Optional[str] = None

    def expired(self, at: Optional[datetime] = None) -> bool:
        """True iff the lease may be reclaimed. Liveness is never consulted."""
        return (at or _now()) >= self.expires_at

    def to_json(self) -> bytes:
        return canonical_json(
            {
                "lease_id": self.lease_id,
                "holder_id": self.holder_id,
                "repository_root": self.repository_root,
                "acquired_at": self.acquired_at.isoformat(),
                "expires_at": self.expires_at.isoformat(),
                "pid": self.pid,
                "controller_epoch": self.controller_epoch,
                "reclaimed_from": self.reclaimed_from,
            }
        )

    @classmethod
    def from_json(cls, data: bytes) -> "LeaseRecord":
        raw = json.loads(data)
        return cls(
            lease_id=raw["lease_id"],
            holder_id=raw["holder_id"],
            repository_root=raw["repository_root"],
            acquired_at=datetime.fromisoformat(raw["acquired_at"]),
            expires_at=datetime.fromisoformat(raw["expires_at"]),
            pid=int(raw["pid"]),
            controller_epoch=raw.get("controller_epoch"),
            reclaimed_from=raw.get("reclaimed_from"),
        )


def lease_name_for(repository_root: Path) -> str:
    """A stable file name for one repository, from its resolved root.

    Two controllers pointed at the same repository derive the same name, which
    is what makes the exclusion mutual rather than per-process.
    """
    resolved = str(Path(repository_root).resolve())
    return digest_bytes(resolved.encode("utf-8")).split(":", 1)[1][:32]


class RepositoryLease:
    """An exclusive, expiring hold on one repository.

    Not reentrant: a second `acquire` on a held lease is refused exactly as a
    peer's would be, because "this process already holds it" is a claim about
    program structure and the lease is a fact about the repository.
    """

    def __init__(
        self,
        directory: Path,
        repository_root: Path,
        *,
        holder_id: str,
        ttl_ms: int = DEFAULT_TTL_MS,
        controller_epoch: Optional[int] = None,
    ) -> None:
        self.directory = Path(directory)
        self.repository_root = Path(repository_root)
        self.holder_id = holder_id
        self.ttl_ms = int(ttl_ms)
        self.controller_epoch = controller_epoch
        name = lease_name_for(self.repository_root)
        self.path = self.directory / f"{name}.lease"
        self.lock_path = self.directory / f"{name}.lock"
        self.held: Optional[LeaseRecord] = None

    # -- the guarded critical section --------------------------------------

    @contextmanager
    def _locked(self):
        """Hold the inter-process mutex around one read-modify-write.

        Short-lived on purpose: the mutex answers "who is editing the record",
        never "who holds the repository". The kernel drops it when the process
        dies, which is exactly why the lease itself is a record with an expiry.
        """
        self.directory.mkdir(parents=True, exist_ok=True)
        handle = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield
        finally:
            os.close(handle)

    def _read(self) -> Optional[LeaseRecord]:
        try:
            data = self.path.read_bytes()
        except FileNotFoundError:
            return None
        try:
            return LeaseRecord.from_json(data)
        except (ValueError, KeyError):
            # An unreadable lease is not a held lease. It is replaced, and the
            # replacement records that something was there.
            return None

    def _write(self, record: LeaseRecord) -> None:
        temporary = self.path.with_name(f"{self.path.name}.{os.getpid()}.partial")
        with open(temporary, "wb") as handle:
            handle.write(record.to_json())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)
        descriptor = os.open(str(self.directory), os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    # -- operations ---------------------------------------------------------

    def current(self) -> Optional[LeaseRecord]:
        """The lease on disk, whoever holds it and whether or not it expired."""
        with self._locked():
            return self._read()

    def acquire(self) -> LeaseRecord:
        """Take the lease, or raise `LeaseUnavailable`.

        An existing lease is honoured until `expires_at`, whether or not its
        holder is still alive. Reclaiming an expired one records the holder it
        was taken from, so an operator can see that a hold was broken rather
        than released.
        """
        with self._locked():
            existing = self._read()
            now = _now()
            if existing is not None and not existing.expired(now):
                raise LeaseUnavailable(
                    f"repository {self.repository_root} is leased to "
                    f"{existing.holder_id!r} (pid {existing.pid}) until "
                    f"{existing.expires_at.isoformat()}; a lease is honoured "
                    "until it expires, whether or not its holder is alive"
                )
            record = LeaseRecord(
                lease_id=f"lease-{uuid.uuid4().hex}",
                holder_id=self.holder_id,
                repository_root=str(self.repository_root.resolve()),
                acquired_at=now,
                expires_at=now + timedelta(milliseconds=self.ttl_ms),
                pid=os.getpid(),
                controller_epoch=self.controller_epoch,
                reclaimed_from=None if existing is None else existing.holder_id,
            )
            self._write(record)
            self.held = record
            return record

    def _holds(self, existing: Optional[LeaseRecord]) -> bool:
        """True iff the lease on disk is the one this object took.

        Identity is the `lease_id`, not the holder name or the pid: a
        reclaimed lease has a new id, so a controller whose hold was broken
        can tell the difference between "still mine" and "someone else's, with
        my name on the previous one".
        """
        if self.held is None or existing is None:
            return False
        return existing.lease_id == self.held.lease_id

    def renew(self) -> LeaseRecord:
        """Extend the lease this object holds. Refused if it was taken away."""
        with self._locked():
            existing = self._read()
            if not self._holds(existing):
                raise LeaseUnavailable(
                    f"this controller no longer holds {self.repository_root}"
                )
            now = _now()
            record = LeaseRecord(
                lease_id=existing.lease_id,
                holder_id=existing.holder_id,
                repository_root=existing.repository_root,
                acquired_at=existing.acquired_at,
                expires_at=now + timedelta(milliseconds=self.ttl_ms),
                pid=existing.pid,
                controller_epoch=existing.controller_epoch,
                reclaimed_from=existing.reclaimed_from,
            )
            self._write(record)
            self.held = record
            return record

    def release(self) -> None:
        """Give the lease back, if this object still holds it.

        Releasing a lease that was already reclaimed is a no-op: the reclaimer
        holds it, and deleting its record would hand the repository to a third
        controller.
        """
        with self._locked():
            existing = self._read()
            if existing is not None and not self._holds(existing):
                # Somebody reclaimed it. Deleting their record here would hand
                # the repository to a third controller.
                self.held = None
                return
            self.path.unlink(missing_ok=True)
            self.held = None

    def __enter__(self) -> LeaseRecord:
        return self.acquire()

    def __exit__(self, *exc_info) -> None:
        self.release()
