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

#: Every gate point the runtime declares.
GATE_POINTS: frozenset[str] = frozenset(
    {
        AFTER_INVOKE_BEFORE_RECEIPT,
        AFTER_LOOKUP_BEFORE_RECEIPT,
        AFTER_COMMIT_BEFORE_RECEIPT,
    }
)


def active_gate(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """The gate point named by `GRUNTIME_GATE`, or `None`."""
    raise NotImplementedError


def gate_dir(env: Optional[Mapping[str, str]] = None) -> Optional[Path]:
    """The directory named by `GRUNTIME_GATE_DIR`, or `None`."""
    raise NotImplementedError


def gate(name: str) -> None:
    """Pass gate point `name`.

    Returns immediately unless `GRUNTIME_GATE` names this point. When it does,
    write `<name>.ready` durably, then block until the process is killed.
    """
    raise NotImplementedError
