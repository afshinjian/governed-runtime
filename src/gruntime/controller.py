"""The controller: the only thing that transitions state.

Design basis: worker_provider.md §6 (invocation sequence) and §6.1 (recovery),
transition-matrix §5 (`RUN-INV-3`), §7.4, evidence-model §3.2 and §3.2.1,
domain-model `P-INV-4`.

Workers propose; adapters observe; the controller decides. Every method here
that changes anything appends its `AuditEvent` before the new state is
observable (`AE-INV-2`).

Two orderings are not negotiable and are why a kill between any two steps is
recoverable:

* `controller_epoch` increments and commits before any other work (`P-INV-4`).
* An external effect's durable identity is appended before the effect is
  performed — `idempotency_key` with `request_ref` for an invocation,
  `operation_token` in the revision's trailers for a commit — so the outside
  world holds the same identifier the log does (evidence-model §3.2.1).

Command line, used by operators and by the crash tests::

    python -m gruntime.controller
        --db PATH --artifacts DIR --journal DIR [--repo DIR]
        --project PROJECT_ID
        {start | invoke --run RUN_ID | commit --run RUN_ID --path P --content C
         | recover}

`start` prints one JSON object carrying `controller_epoch`. The process is
always launched as `sys.executable -m gruntime.controller`; the runtime never
shells out to a bare interpreter name.
"""

from __future__ import annotations

from typing import Optional, Sequence

from .artifacts import ArtifactStore
from .models import (
    CommitIntent,
    CommitPreconditions,
    CommitReceipt,
    Id,
    Independence,
    ReviewAttestation,
    ReviewerKind,
    Verdict,
    WorkerInvocation,
    WorkerReceipt,
)
from .models import Review as ReviewRecord
from .provider import GovernedProvider, WorkerProvider
from .recovery import RecoveryOutcome
from .store import StateStore


class Controller:
    """Owns every state transition for one store."""

    def __init__(
        self,
        *,
        store: StateStore,
        artifacts: ArtifactStore,
        provider: WorkerProvider,
        repo: Optional[object] = None,
    ) -> None:
        self.store = store
        self.artifacts = artifacts
        self.provider = provider
        self.repo = repo

    # -- project and run ---------------------------------------------------

    def create_project(self, *, name: str, slug: str, workspace_root: str) -> Id:
        """Create a project and anchor its chain with the genesis event."""
        raise NotImplementedError

    def start(self, project_id: Id) -> int:
        """Increment `controller_epoch` and return the new value.

        `P-INV-4`: the increment is committed before this controller does any
        other work, so an operation carrying a lower epoch is provably the
        work of a controller that is gone.
        """
        raise NotImplementedError

    def open_run(self, project_id: Id) -> Id:
        """Allocate a `StageRun` under the current epoch."""
        raise NotImplementedError

    def take_snapshot(self, project_id: Id) -> Id:
        """Take a `RealitySnapshot` — the only source of truth about the
        workspace (`RS-INV-1`)."""
        raise NotImplementedError

    # -- invocations (worker_provider §6) ----------------------------------

    def create_invocation(self, run_id: Id, *, prompt: bytes) -> WorkerInvocation:
        """Mint the key and persist the request, before any provider call.

        Refuses with `BarrierViolation` while any record of the run is
        unreconciled: a run that outlived a controller initiates no new
        external effect until its records are settled (`RUN-INV-3`).
        """
        raise NotImplementedError

    def mark_dispatched(self, invocation_id: Id) -> None:
        """`PENDING → DISPATCHED` (transition-matrix §7.1)."""
        raise NotImplementedError

    def invoke(self, invocation_id: Id) -> WorkerReceipt:
        """Call the provider and mint the receipt with `attribution = DIRECT`.

        The gate point between those two steps is where the crash tests kill
        the process.
        """
        raise NotImplementedError

    # -- commits (transition-matrix §7.4) ----------------------------------

    def propose_commit(
        self,
        run_id: Id,
        *,
        path: str,
        content: str,
        message: str,
        preconditions: Optional[CommitPreconditions] = None,
    ) -> CommitIntent:
        """`∅ → PROPOSED`, minting `operation_token` into the trailers."""
        raise NotImplementedError

    def block_commit(self, intent_id: Id) -> None:
        """`PROPOSED → BLOCKED` when a precondition is unmet."""
        raise NotImplementedError

    def authorize_commit(self, intent_id: Id) -> None:
        """`PROPOSED → AUTHORIZED`.

        Re-evaluates the preconditions rather than trusting the stored value:
        a review-backed precondition is refused here even if something wrote
        one directly into the record (`G-1`).
        """
        raise NotImplementedError

    def deny_commit(self, intent_id: Id, reason: str) -> None:
        """`PROPOSED → DENIED`."""
        raise NotImplementedError

    def mark_applying(self, intent_id: Id) -> None:
        """`AUTHORIZED → APPLYING`.

        The token and epoch are durable before the first repository mutation,
        so a revision that lands afterwards is always matchable back to this
        intent (`CM-INV-2`).
        """
        raise NotImplementedError

    def apply_commit(self, intent_id: Id) -> CommitReceipt:
        """Apply the intent and mint the receipt with `attribution = DIRECT`.

        Refuses with `BarrierViolation` while the run is unreconciled.
        """
        raise NotImplementedError

    # -- reviews and attestations ------------------------------------------

    def record_review(
        self,
        run_id: Id,
        *,
        review_spec_id: str,
        verdict: Verdict,
        reviewer_kind: ReviewerKind,
        independence: Independence,
        input_snapshot_id: Id,
    ) -> ReviewRecord:
        """Record a reviewer's judgement. It gates nothing by itself."""
        raise NotImplementedError

    def attest_reviews(
        self,
        run_id: Id,
        review_spec_id: str,
        reviews: Sequence[ReviewRecord],
        *,
        quorum: int,
    ) -> ReviewAttestation:
        """Mint the kernel's measurement of those judgements (`review.attest`).

        A spec whose quorum or independence cannot be met produces no
        attestation at all (`RA-INV-2`).
        """
        raise NotImplementedError

    # -- recovery (worker_provider §6.1) -----------------------------------

    def recover(self, project_id: Id) -> RecoveryOutcome:
        """Reconcile every old-epoch record, under `recovery.reconcile` only.

        Holds no capability that can execute: the provider is reached through
        a gate that exposes `lookup` and nothing else (`WP-16`).
        """
        raise NotImplementedError

    def recovery_provider(self) -> GovernedProvider:
        """The provider as recovery sees it: `lookup`, and nothing else."""
        raise NotImplementedError


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for `python -m gruntime.controller`.

    Parses the command line documented in the module docstring, opens the
    store, runs the named command, and prints its JSON result on stdout.
    """
    raise NotImplementedError


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
