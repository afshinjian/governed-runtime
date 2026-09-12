"""Durable state: SQLite schema, the hash-chained event log, and readers.

Design basis: evidence-model §3.1-§3.4, domain-model §9.C, `P-INV-4`.

Storage configuration is part of the design, not a tuning choice: WAL journal,
`synchronous = FULL`, and STRICT tables. The `audit_events` table is
append-only, enforced by triggers rather than by convention — `raw_execute` of
an UPDATE or DELETE against it raises.

The store reads and appends. It never decides a transition; the controller
does that.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

from .models import (
    ActorRef,
    ArtifactRef,
    AuditEvent,
    CommitIntent,
    CommitReceipt,
    EpistemicClass,
    Escalation,
    Hash,
    Id,
    Project,
    RealitySnapshot,
    Ref,
    Review,
    ReviewAttestation,
    StageRun,
    WorkerInvocation,
    WorkerReceipt,
)

#: Applied at open, before any read or write (evidence-model §3.2).
PRAGMAS: tuple[tuple[str, str], ...] = (
    ("journal_mode", "WAL"),
    ("synchronous", "FULL"),
    ("foreign_keys", "ON"),
)

#: `PRAGMA synchronous` value for FULL, as SQLite reports it.
SYNCHRONOUS_FULL = 2

#: Domain-model version stamped on every project row.
SCHEMA_VERSION = "0.1.0"


class StateStore:
    """The project's durable state and its per-project event chain."""

    def __init__(self, connection: Any, db_path: Path) -> None:
        self.connection = connection
        self.db_path = Path(db_path)

    # -- lifecycle ---------------------------------------------------------

    @classmethod
    def open(cls, db_path: Path) -> "StateStore":
        """Open (creating if absent) the store at `db_path`.

        Applies :data:`PRAGMAS` and creates the STRICT schema, including the
        append-only triggers on `audit_events`.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Close the connection."""
        raise NotImplementedError

    def pragma(self, name: str) -> Any:
        """Return the current value of `PRAGMA <name>`."""
        raise NotImplementedError

    def raw_execute(self, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        """Execute `sql` directly, without passing through the append protocol.

        Exists so integrity rules can be exercised against the real database.
        The append-only triggers make an UPDATE or DELETE of `audit_events`
        raise `sqlite3.DatabaseError` here exactly as they would anywhere else.
        """
        raise NotImplementedError

    # -- event log (evidence-model §3.1-§3.3) ------------------------------

    def genesis_hash(self, project_id: Id) -> Hash:
        """`sha256(project_id ‖ 0x00 ‖ schema_version)` — §3.1 step 5."""
        raise NotImplementedError

    def append_event(
        self,
        project_id: Id,
        *,
        event_type: str,
        epistemic_class: EpistemicClass,
        actor: ActorRef,
        subject: dict[str, str],
        payload: bytes,
        capability_used: Optional[str] = None,
        authority_ref: Optional[Id] = None,
        causal_parent: Optional[Id] = None,
    ) -> AuditEvent:
        """Append one event and advance the head atomically (§3.2).

        The payload is written to the artifact store first; `seq` is reserved
        under the per-project lock; the event and the new `event_head` are
        persisted in one transaction. Only then is the change observable.
        """
        raise NotImplementedError

    def list_events(self, project_id: Id) -> list[AuditEvent]:
        """Every event of the project, ordered by `seq`."""
        raise NotImplementedError

    def verify_chain(self, project_id: Id) -> None:
        """Run the §3.3 checks over the project's chain.

        Continuity, gaplessness and payload binding; any failure raises
        `IntegrityViolation`.
        """
        raise NotImplementedError

    def audit_reconciliation_closure(self, project_id: Id) -> None:
        """Evidence-model §3.2.1: no non-terminal operation of an older epoch
        precedes a later dispatch or apply on the same run (`RUN-INV-3`)."""
        raise NotImplementedError

    def artifact_bytes(self, digest: Hash) -> bytes:
        """Payload bytes behind `digest`, re-hashed on the way out."""
        raise NotImplementedError

    # -- projects and runs -------------------------------------------------

    def get_project(self, project_id: Id) -> Project:
        raise NotImplementedError

    def put_project(self, project: Project) -> None:
        raise NotImplementedError

    def bump_controller_epoch(self, project_id: Id) -> int:
        """Increment and commit `controller_epoch`, returning the new value.

        `P-INV-4`: this is durable before the controller does any other work.
        """
        raise NotImplementedError

    def get_run(self, run_id: Id) -> StageRun:
        raise NotImplementedError

    def list_runs(self, project_id: Id) -> list[StageRun]:
        raise NotImplementedError

    # -- invocations and receipts ------------------------------------------

    def get_invocation(self, invocation_id: Id) -> WorkerInvocation:
        raise NotImplementedError

    def list_invocations(self, run_id: Id) -> list[WorkerInvocation]:
        raise NotImplementedError

    def list_unreconciled_invocations(self, project_id: Id) -> list[WorkerInvocation]:
        """Invocations with `controller_epoch < project.controller_epoch`."""
        raise NotImplementedError

    def list_worker_receipts(self, invocation_id: Id) -> list[WorkerReceipt]:
        raise NotImplementedError

    # -- commit intents and receipts ---------------------------------------

    def get_commit_intent(self, intent_id: Id) -> CommitIntent:
        raise NotImplementedError

    def list_commit_intents(self, run_id: Id) -> list[CommitIntent]:
        raise NotImplementedError

    def list_unreconciled_intents(self, project_id: Id) -> list[CommitIntent]:
        """Intents with `controller_epoch < project.controller_epoch`."""
        raise NotImplementedError

    def list_commit_receipts(self, intent_id: Id) -> list[CommitReceipt]:
        raise NotImplementedError

    # -- reviews, attestations, evidence resolution ------------------------

    def get_review(self, review_id: Id) -> Review:
        raise NotImplementedError

    def get_attestation(self, attestation_id: Id) -> ReviewAttestation:
        raise NotImplementedError

    def resolve_review_evidence(self, ref: Ref) -> ReviewAttestation:
        """Resolve a review precondition to the attestation that discharges it.

        A ref of any other kind, and a ref whose id names a review record
        rather than an attestation, raise `IntegrityViolation` (`G-1`): the
        evaluator never reads a reviewer's own verdict.
        """
        raise NotImplementedError

    # -- snapshots and escalations -----------------------------------------

    def get_snapshot(self, snapshot_id: Id) -> RealitySnapshot:
        raise NotImplementedError

    def list_escalations(self, project_id: Id) -> list[Escalation]:
        raise NotImplementedError

    # -- test-facing forcing hooks -----------------------------------------
    #
    # These write fields the normal path derives, so recovery and the
    # consuming paths can be exercised against states a correct controller
    # would not produce. They bypass no integrity check downstream.

    def force_expected_tree_digest(self, intent_id: Id, digest: Hash) -> None:
        """Overwrite an intent's `expected_tree_digest`."""
        raise NotImplementedError

    def force_precondition_reviews(
        self, intent_id: Id, review_ids: Sequence[Id]
    ) -> None:
        """Write raw ids into an intent's review preconditions."""
        raise NotImplementedError

    def store_artifact(self, data: bytes, *, media_type: str) -> ArtifactRef:
        """Put bytes in the artifact store this store reads payloads from."""
        raise NotImplementedError
