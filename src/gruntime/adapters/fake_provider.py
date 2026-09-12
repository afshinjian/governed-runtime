"""A journaling `WorkerProvider` for exercising the runtime without a vendor.

Every call is appended to an on-disk journal under the provider directory, so
what the provider did survives the death of the process that called it. That
is what lets a crash test assert "exactly one execution" by reading state
rather than by counting calls on a mock that died with the controller.

The journal is the provider's own record, not evidence: it stands in for what
a real provider's billing and history would report through `lookup`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..models import ArtifactRef, Hash, Id, OutcomeStatus, TerminationReason
from ..provider import (
    CancelResult,
    InvocationOutcome,
    InvocationRequest,
    LookupResult,
    PreflightResult,
    ProviderDescriptor,
    ProviderHealth,
    ToolBridge,
    WorkerProvider,
)

#: Journal file holding one record per provider call.
JOURNAL_NAME = "journal.jsonl"

#: Where outcome payloads are kept, keyed by `idempotency_key`.
OUTCOMES_DIRNAME = "outcomes"


class FakeProvider(WorkerProvider):
    """A provider whose executions and lookups are durable and inspectable."""

    def __init__(self, journal_dir: Path) -> None:
        self.journal_dir = Path(journal_dir)

    # -- inspection --------------------------------------------------------

    def executions(self) -> list[dict]:
        """Every execution the provider actually performed, in order.

        One entry per execution, never per call: a repeat under a key already
        executed returns the prior outcome and adds nothing here (`WP-6`).
        """
        raise NotImplementedError

    def lookups(self) -> list[Hash]:
        """Every `idempotency_key` `lookup` was called with, in order."""
        raise NotImplementedError

    def set_default_outcome(
        self,
        *,
        status: OutcomeStatus,
        termination_reason: TerminationReason,
        output: bytes,
    ) -> None:
        """Seed the outcome the next execution will produce.

        Seeding `REFUSED` / `REFUSAL` is how the refusal case is exercised:
        adoption must preserve it as a refusal mapped to `FAILED`, never
        upgrade it to `COMPLETED` (`W-INV-4`).
        """
        raise NotImplementedError

    # -- WorkerProvider (worker_provider §3) -------------------------------

    def describe(self) -> ProviderDescriptor:
        raise NotImplementedError

    def preflight(self, request: InvocationRequest) -> PreflightResult:
        raise NotImplementedError

    def invoke(
        self, request: InvocationRequest, bridge: Optional[ToolBridge] = None
    ) -> InvocationOutcome:
        """Execute once per `idempotency_key`; a repeat replays the outcome."""
        raise NotImplementedError

    def lookup(self, idempotency_key: Hash) -> LookupResult:
        """Report the key's prior outcome, executing nothing.

        An unknown key answers `ABSENT` (`CF-12`); a finished one answers
        `FINISHED` with the outcome as it was, including `REFUSED`
        (`CF-13`, `CF-14`). Neither answer starts, resumes, extends or bills
        an execution.
        """
        raise NotImplementedError

    def cancel(self, invocation_id: Id, reason: str) -> CancelResult:
        raise NotImplementedError

    def health(self) -> ProviderHealth:
        raise NotImplementedError

    # -- internals ---------------------------------------------------------

    def _journal_path(self) -> Path:
        raise NotImplementedError

    def _record(self, kind: str, **fields: object) -> None:
        """Append one durable journal record."""
        raise NotImplementedError

    def _store_output(self, idempotency_key: Hash, output: bytes) -> ArtifactRef:
        raise NotImplementedError
