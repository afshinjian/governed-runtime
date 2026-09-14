"""A journaling `WorkerProvider` for exercising the runtime without a vendor.

Every call is appended to an on-disk journal under the provider directory, so
what the provider did survives the death of the process that called it. That
is what lets a crash test assert "exactly one execution" by reading state
rather than by counting calls on a mock that died with the controller.

The journal is the provider's own record, not evidence: it stands in for what
a real provider's billing and history would report through `lookup`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..canonical import digest_bytes
from ..models import ArtifactRef, Hash, Id, OutcomeStatus, TerminationReason, Usage
from ..provider import (
    BindingDescriptor,
    CancelResult,
    InvocationOutcome,
    InvocationRequest,
    LookupAbsent,
    LookupFinished,
    LookupResult,
    PreflightResult,
    ProviderDescriptor,
    ProviderHealth,
    ToolBridge,
    WorkerProvider,
)
from ..models import WorkerRole
from ..secret_guard import SecretGuard

#: Journal file holding one record per provider call.
JOURNAL_NAME = "journal.jsonl"

#: Where outcome payloads are kept, keyed by `idempotency_key`.
OUTCOMES_DIRNAME = "outcomes"

#: Where `set_default_outcome` parks the next execution's result. On disk
#: because the process that seeds it is never the process that executes.
DEFAULT_OUTCOME_NAME = "default_outcome.json"

PROVIDER_ID = "fake"
PROVIDER_VERSION = "0.1.0"


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_durably(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.partial")
    with open(temporary, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_dir(path.parent)


class FakeProvider(WorkerProvider):
    """A provider whose executions and lookups are durable and inspectable."""

    def __init__(self, journal_dir: Path) -> None:
        self.journal_dir = Path(journal_dir)
        self.secret_guard = SecretGuard()

    def _write_durably(self, path, data):
        self.secret_guard.check(data)  # guard:gr08_fake_write
        _write_durably(path, data)

    # -- inspection --------------------------------------------------------

    def _records(self, kind: str) -> list[dict]:
        path = self._journal_path()
        if not path.exists():
            return []
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("kind") == kind:
                records.append(record)
        return records

    def executions(self) -> list[dict]:
        """Every execution the provider actually performed, in order.

        One entry per execution, never per call: a repeat under a key already
        executed returns the prior outcome and adds nothing here (`WP-6`).
        """
        return self._records("execute")

    def lookups(self) -> list[Hash]:
        """Every `idempotency_key` `lookup` was called with, in order."""
        return [record["idempotency_key"] for record in self._records("lookup")]

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
        self._write_durably(
            self.journal_dir / DEFAULT_OUTCOME_NAME,
            json.dumps(
                {
                    "status": status.value,
                    "termination_reason": termination_reason.value,
                    "output": output.decode("utf-8", errors="surrogateescape"),
                }
            ).encode("utf-8"),
        )

    def _default_outcome(self) -> dict:
        path = self.journal_dir / DEFAULT_OUTCOME_NAME
        if not path.exists():
            return {
                "status": OutcomeStatus.COMPLETED.value,
                "termination_reason": TerminationReason.COMPLETED.value,
                "output": "",
            }
        return json.loads(path.read_text(encoding="utf-8"))

    # -- WorkerProvider (worker_provider §3) -------------------------------

    def describe(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=PROVIDER_ID,
            provider_version=PROVIDER_VERSION,
            supported_roles=frozenset(WorkerRole),
            bindings=(
                BindingDescriptor(
                    binding_id="default",
                    label="default",
                    max_output_bytes=1 << 20,
                    relative_cost=1.0,
                    deterministic=True,
                ),
            ),
            max_context_bytes=1 << 20,
            supports_cancel=True,
            supports_streaming=False,
            cost_model="flat",
        )

    def preflight(self, request: InvocationRequest) -> PreflightResult:
        self._record("preflight", idempotency_key=request.idempotency_key)
        return PreflightResult(accepted=True)

    def invoke(
        self, request: InvocationRequest, bridge: Optional[ToolBridge] = None
    ) -> InvocationOutcome:
        """Execute once per `idempotency_key`; a repeat replays the outcome."""
        key = request.idempotency_key
        stored = self._outcome_path(key)
        if stored.exists():
            # `WP-6`: the same key is the same execution. Replayed, not rerun,
            # and not journalled as a second execution.
            return self._outcome_from_disk(request.invocation_id, key)

        seed = self._default_outcome()
        output = seed["output"].encode("utf-8", errors="surrogateescape")
        output_ref = self._store_output(key, output)
        self._write_durably(
            stored,
            json.dumps(
                {
                    "status": seed["status"],
                    "termination_reason": seed["termination_reason"],
                    "output_digest": output_ref.digest,
                    "output_byte_len": output_ref.byte_len,
                }
            ).encode("utf-8"),
        )
        # Journalled only after the outcome is durable: a crash here must not
        # leave a billed execution the provider cannot report through lookup.
        self._record(
            "execute",
            idempotency_key=key,
            invocation_id=request.invocation_id,
            output_digest=output_ref.digest,
        )
        return self._outcome_from_disk(request.invocation_id, key)

    def _outcome_from_disk(self, invocation_id: Id, key: Hash) -> InvocationOutcome:
        record = json.loads(self._outcome_path(key).read_text(encoding="utf-8"))
        return InvocationOutcome(
            invocation_id=invocation_id,
            status=OutcomeStatus(record["status"]),
            output_ref=ArtifactRef(
                digest=record["output_digest"],
                media_type="application/octet-stream",
                byte_len=record["output_byte_len"],
            ),
            termination_reason=TerminationReason(record["termination_reason"]),
            usage=Usage(),
        )

    def lookup(self, idempotency_key: Hash) -> LookupResult:
        """Report the key's prior outcome, executing nothing.

        An unknown key answers `ABSENT` (`CF-12`); a finished one answers
        `FINISHED` with the outcome as it was, including `REFUSED`
        (`CF-13`, `CF-14`). Neither answer starts, resumes, extends or bills
        an execution.
        """
        self._record("lookup", idempotency_key=idempotency_key)
        if not self._outcome_path(idempotency_key).exists():
            return LookupAbsent()
        return LookupFinished(
            outcome=self._outcome_from_disk("", idempotency_key)
        )

    def fetch(self, ref: ArtifactRef) -> bytes:
        data = (self.journal_dir / OUTCOMES_DIRNAME / ref.digest.replace(":", "-")).read_bytes()
        if digest_bytes(data) != ref.digest:  # pragma: no cover
            raise ValueError(f"provider artifact {ref.digest} does not rehash")
        return data

    def cancel(self, invocation_id: Id, reason: str) -> CancelResult:
        self._record("cancel", invocation_id=invocation_id, reason=reason)
        return CancelResult(acknowledged=True)

    def health(self) -> ProviderHealth:
        return ProviderHealth(status="OK", checked_at=datetime.now(timezone.utc))

    # -- internals ---------------------------------------------------------

    def _journal_path(self) -> Path:
        return self.journal_dir / JOURNAL_NAME

    def _outcome_path(self, idempotency_key: Hash) -> Path:
        return (
            self.journal_dir
            / OUTCOMES_DIRNAME
            / f"{idempotency_key.replace(':', '-')}.json"
        )

    def _record(self, kind: str, **fields: object) -> None:
        """Append one durable journal record."""
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {"kind": kind, "at": datetime.now(timezone.utc).isoformat(), **fields},
            sort_keys=True,
        )
        self.secret_guard.check(line)  # guard:gr08_log_line
        with open(self._journal_path(), "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _store_output(self, idempotency_key: Hash, output: bytes) -> ArtifactRef:
        digest = digest_bytes(output)
        self._write_durably(
            self.journal_dir / OUTCOMES_DIRNAME / digest.replace(":", "-"), output
        )
        return ArtifactRef(
            digest=digest,
            media_type="application/octet-stream",
            byte_len=len(output),
        )
