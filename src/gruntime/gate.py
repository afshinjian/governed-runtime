"""Named blocking points, for terminating a real controller at a real seam.

A gate is not a fault injection and not a monkeypatch: at a named point the
process publishes `<GRUNTIME_GATE_DIR>/<name>.ready` and then blocks forever.
Whoever is watching sends a signal from outside, so the process dies exactly
between two durable steps — an external effect and its receipt — with no
cleanup, no handler, and no in-process cooperation.

Gates are inert unless `GRUNTIME_GATE` names the point being passed, so the
same code path runs unchanged in production.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Mapping, Optional

#: Names the single gate point at which this process should block.
GATE_ENV = "GRUNTIME_GATE"

#: Directory the readiness file is published into.
GATE_DIR_ENV = "GRUNTIME_GATE_DIR"

#: After the provider execution finished, before the direct `WorkerReceipt`
#: is durable (`CF-11`).
AFTER_INVOKE_BEFORE_RECEIPT = "after_invoke_before_receipt"

#: After a `FINISHED` lookup, before the reconciled `WorkerReceipt` is durable
#: (`WP-16`, transition-matrix §7.2).
AFTER_LOOKUP_BEFORE_RECEIPT = "after_lookup_before_receipt"

#: After the repository mutation landed, before the `CommitReceipt` is durable
#: (`CM-INV-2`, transition-matrix §7.4).
AFTER_COMMIT_BEFORE_RECEIPT = "after_commit_before_receipt"

#: Inside the repository lease, before the mutation. A process killed here
#: leaves the lease record behind with time still on it, which is what a
#: second controller must honour (`lease.py`, `CM-INV-3`).
INSIDE_REPOSITORY_LEASE = "inside_repository_lease"

#: Every gate point the runtime declares.
GATE_POINTS: frozenset[str] = frozenset(
    {
        AFTER_INVOKE_BEFORE_RECEIPT,
        AFTER_LOOKUP_BEFORE_RECEIPT,
        AFTER_COMMIT_BEFORE_RECEIPT,
        INSIDE_REPOSITORY_LEASE,
    }
)


def active_gate(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """The gate point named by `GRUNTIME_GATE`, or `None`."""
    source = os.environ if env is None else env
    name = source.get(GATE_ENV)
    if not name:
        return None
    if name not in GATE_POINTS:
        raise ValueError(f"{GATE_ENV}={name!r} names no declared gate point")
    return name


def gate_dir(env: Optional[Mapping[str, str]] = None) -> Optional[Path]:
    """The directory named by `GRUNTIME_GATE_DIR`, or `None`."""
    source = os.environ if env is None else env
    value = source.get(GATE_DIR_ENV)
    return None if not value else Path(value)


def gate(name: str) -> None:
    """Pass gate point `name`.

    Returns immediately unless `GRUNTIME_GATE` names this point. When it does,
    write `<name>.ready` durably, then block until the process is killed.

    The readiness file is fsynced, and so is the directory entry naming it,
    before the block begins: the watcher must not be able to see the file
    before the process has genuinely reached this point.
    """
    if active_gate() != name:
        return
    directory = gate_dir()
    if directory is None:
        raise ValueError(f"{GATE_ENV}={name!r} set without {GATE_DIR_ENV}")
    directory.mkdir(parents=True, exist_ok=True)

    ready = directory / f"{name}.ready"
    temporary = ready.with_suffix(f".ready.{os.getpid()}.partial")
    with open(temporary, "wb") as handle:
        handle.write(f"{name} {os.getpid()}\n".encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, ready)
    fd = os.open(str(directory), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

    # Nothing after this point runs. The process is terminated from outside,
    # with no handler and no cleanup, which is the whole point: the next step
    # must be recoverable from durable state alone.
    while True:  # pragma: no cover
        time.sleep(3600)
