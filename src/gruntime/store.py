"""Durable state: SQLite schema, the hash-chained event log, and readers.

Design basis: evidence-model §3.1-§3.4, domain-model §9.C, `P-INV-4`.

Storage configuration is part of the design, not a tuning choice: WAL journal,
`synchronous = FULL`, and STRICT tables. Every commit is therefore fsynced
before it is reported, which is what makes "durable before the external effect"
mean anything.

`audit_events` is append-only. The guard is a per-connection SQLite authorizer
rather than a schema trigger: a trigger would also bind connections opened by an
auditor or a forensic tool, and the point of the rule is that *this* runtime
never rewrites its own log, not that the bytes are physically immutable to
everyone. `raw_execute` of an UPDATE or DELETE against the table raises
`sqlite3.DatabaseError`; tampering from outside is detected by `verify_chain`,
which is the check that actually protects the record.

The store reads and appends. It never decides a transition; the controller
does that.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from .artifacts import ArtifactStore
from .canonical import canonical_json, digest_bytes
from .errors import IntegrityViolation, SchemaTooOld
from .models import (
    ActorRef,
    ActorKind,
    ArtifactRef,
    AuditEvent,
    AuthMethod,
    Budget,
    BudgetUsage,
    CommitIntent,
    CommitIntentStatus,
    CommitPreconditions,
    CommitReceipt,
    Completeness,
    DecisionKind,
    DecisionScope,
    DecisionState,
    DecisionSubjectKind,
    DriftSummary,
    Encoding,
    EpistemicClass,
    Escalation,
    EscalationSeverity,
    EscalationStatus,
    EscalationTrigger,
    GovernanceMode,
    Hash,
    HumanDecision,
    Id,
    Independence,
    InvocationStatus,
    MutationOp,
    MutationProposal,
    Project,
    ProjectLifecycle,
    RealitySnapshot,
    ReconciliationState,
    Ref,
    RetentionClass,
    Review,
    ReviewAttestation,
    ReviewerKind,
    RunLifecycle,
    SnapshotTrigger,
    StageRun,
    SuspensionState,
    TerminationReason,
    Usage,
    Attribution,
    Verdict,
    Verification,
    VcsKind,
    WorkerInvocation,
    WorkerReceipt,
    WorkerRole,
)
from .reconciliation import clears_barrier

#: Applied at open, before any read or write (evidence-model §3.2).
PRAGMAS: tuple[tuple[str, str], ...] = (
    ("journal_mode", "WAL"),
    ("synchronous", "FULL"),
    ("foreign_keys", "ON"),
)

#: `PRAGMA synchronous` value for FULL, as SQLite reports it.
SYNCHRONOUS_FULL = 2

#: Domain-model version stamped on every project row (domain-model §2), and
#: the anchor of every chain's genesis hash (evidence-model §3.1 step 5). It
#: tracks `design-01-frozen`, which GR-03 did not change: `suspension_ref` and
#: `drift_summary` were always in the model, this build merely began persisting
#: them. It must not move for a storage-only reason, or a physical change would
#: silently re-anchor every new project's chain.
SCHEMA_VERSION = "0.1.0"

#: Physical layout version, kept in `PRAGMA user_version` — the place SQLite
#: provides for exactly this, and separate from `SCHEMA_VERSION` because the
#: two answer different questions: which domain model this database speaks,
#: and which columns it actually has. GR-03 is version 2.
STORAGE_VERSION = 2

#: Columns this build reads that a pre-`STORAGE_VERSION` database lacks.
#: Checked structurally as well as by version, because `user_version` defaults
#: to 0 on any database that never set it: the number names the refusal, the
#: columns are what make it true, and a structural check cannot drift out of
#: step with the schema above.
REQUIRED_COLUMNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("projects", ("suspension_ref",)),
    ("snapshots", ("scope", "drift_vs", "drift_summary")),
)

#: Name of the append-only table the authorizer protects.
EVENT_TABLE = "audit_events"

SCHEMA: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS projects (
        project_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT NOT NULL,
        schema_version TEXT NOT NULL,
        lifecycle TEXT NOT NULL,
        suspension TEXT NOT NULL,
        governance_mode TEXT NOT NULL,
        workspace_root TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT NOT NULL,
        event_head TEXT NOT NULL,
        event_seq INTEGER NOT NULL,
        controller_epoch INTEGER NOT NULL,
        policy_digest TEXT,
        snapshot_current TEXT,
        suspension_ref TEXT
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_events (
        project_id TEXT NOT NULL,
        seq INTEGER NOT NULL,
        event_id TEXT NOT NULL,
        prev_event_hash TEXT NOT NULL,
        event_hash TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        epistemic_class TEXT NOT NULL,
        event_type TEXT NOT NULL,
        actor TEXT NOT NULL,
        subject TEXT NOT NULL,
        payload_digest TEXT NOT NULL,
        payload_media_type TEXT NOT NULL,
        payload_byte_len INTEGER NOT NULL,
        capability_used TEXT,
        authority_ref TEXT,
        causal_parent TEXT,
        clock_skew_ms INTEGER NOT NULL,
        signature TEXT,
        PRIMARY KEY (project_id, seq)
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        stage_id TEXT NOT NULL,
        lifecycle TEXT NOT NULL,
        suspension TEXT NOT NULL,
        controller_epoch INTEGER NOT NULL,
        started_at TEXT NOT NULL,
        input_snapshot_id TEXT,
        output_snapshot_id TEXT,
        deadline_at TEXT,
        attempt INTEGER NOT NULL,
        ordinal INTEGER NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS invocations (
        invocation_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        stage_id TEXT NOT NULL,
        provider_id TEXT NOT NULL,
        provider_version TEXT NOT NULL,
        worker_role TEXT NOT NULL,
        prompt_bundle_digest TEXT NOT NULL,
        request_digest TEXT NOT NULL,
        context_digest TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        controller_epoch INTEGER NOT NULL,
        status TEXT NOT NULL,
        reconciliation_state TEXT NOT NULL,
        sandbox_profile_id TEXT NOT NULL,
        dispatched_at TEXT,
        deadline_at TEXT,
        receipt_id TEXT,
        ordinal INTEGER NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS worker_receipts (
        receipt_id TEXT PRIMARY KEY,
        invocation_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        ended_at TEXT NOT NULL,
        duration_ms INTEGER NOT NULL,
        usage TEXT NOT NULL,
        output_digest TEXT NOT NULL,
        output_media_type TEXT NOT NULL,
        output_byte_len INTEGER NOT NULL,
        termination_reason TEXT NOT NULL,
        attribution TEXT NOT NULL,
        attested_by TEXT NOT NULL,
        receipt_hash TEXT NOT NULL,
        prev_event_hash TEXT NOT NULL,
        ordinal INTEGER NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS commit_intents (
        intent_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        stage_id TEXT NOT NULL,
        vcs_kind TEXT NOT NULL,
        base_revision_id TEXT NOT NULL,
        target_ref TEXT NOT NULL,
        expected_tree_digest TEXT NOT NULL,
        message TEXT NOT NULL,
        operation_token TEXT NOT NULL,
        controller_epoch INTEGER NOT NULL,
        status TEXT NOT NULL,
        reconciliation_state TEXT NOT NULL,
        preconditions TEXT NOT NULL,
        preconditions_met INTEGER NOT NULL,
        mutations TEXT NOT NULL,
        trailers TEXT NOT NULL,
        authorized_by TEXT,
        authorized_at TEXT,
        denial_reason TEXT,
        receipt_id TEXT,
        ordinal INTEGER NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS commit_receipts (
        receipt_id TEXT PRIMARY KEY,
        intent_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        revision_id TEXT NOT NULL,
        actual_tree_digest TEXT NOT NULL,
        verification TEXT NOT NULL,
        diff_digest TEXT NOT NULL,
        diff_media_type TEXT NOT NULL,
        diff_byte_len INTEGER NOT NULL,
        applied_at TEXT NOT NULL,
        applied_by TEXT NOT NULL,
        attribution TEXT NOT NULL,
        operation_token TEXT NOT NULL,
        post_snapshot_id TEXT NOT NULL,
        receipt_hash TEXT NOT NULL,
        prev_event_hash TEXT NOT NULL,
        parent_revision_ids TEXT NOT NULL,
        rollback_handle TEXT,
        ordinal INTEGER NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS reviews (
        review_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        stage_id TEXT NOT NULL,
        review_spec_id TEXT NOT NULL,
        reviewer TEXT NOT NULL,
        reviewer_kind TEXT NOT NULL,
        independence TEXT NOT NULL,
        inputs_digest TEXT NOT NULL,
        input_snapshot_id TEXT NOT NULL,
        verdict TEXT NOT NULL,
        review_hash TEXT NOT NULL,
        completed_at TEXT,
        ordinal INTEGER NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS attestations (
        attestation_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        stage_id TEXT NOT NULL,
        review_spec_id TEXT NOT NULL,
        review_ids TEXT NOT NULL,
        verdict TEXT NOT NULL,
        quorum_met INTEGER NOT NULL,
        independence_satisfied INTEGER NOT NULL,
        input_snapshot_id TEXT NOT NULL,
        contract_hash TEXT NOT NULL,
        attested_by TEXT NOT NULL,
        attested_at TEXT NOT NULL,
        attestation_hash TEXT NOT NULL,
        prev_event_hash TEXT NOT NULL,
        ordinal INTEGER NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS snapshots (
        snapshot_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        taken_at TEXT NOT NULL,
        taken_by TEXT NOT NULL,
        trigger TEXT NOT NULL,
        completeness TEXT NOT NULL,
        tree_digest TEXT NOT NULL,
        file_index_digest TEXT NOT NULL,
        file_count INTEGER NOT NULL,
        byte_count INTEGER NOT NULL,
        snapshot_hash TEXT NOT NULL,
        vcs_state TEXT,
        scope TEXT NOT NULL,
        drift_vs TEXT,
        drift_summary TEXT,
        ordinal INTEGER NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS decisions (
        decision_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        subject_kind TEXT NOT NULL,
        subject_id TEXT NOT NULL,
        decision_kind TEXT NOT NULL,
        question TEXT NOT NULL,
        options_offered TEXT NOT NULL,
        chosen TEXT NOT NULL,
        justification TEXT NOT NULL,
        scope TEXT NOT NULL,
        decided_by TEXT NOT NULL,
        auth_method TEXT NOT NULL,
        decided_at TEXT NOT NULL,
        nonce TEXT NOT NULL,
        snapshot_bound INTEGER NOT NULL,
        subject_snapshot_id TEXT,
        decision_state TEXT NOT NULL,
        evidence_shown TEXT NOT NULL,
        expires_at TEXT,
        decision_hash TEXT,
        prev_event_hash TEXT,
        ordinal INTEGER NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS escalations (
        escalation_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        trigger TEXT NOT NULL,
        severity TEXT NOT NULL,
        summary TEXT NOT NULL,
        raised_by TEXT NOT NULL,
        raised_at TEXT NOT NULL,
        suspension_applied TEXT NOT NULL,
        suspension_target TEXT NOT NULL,
        status TEXT NOT NULL,
        stage_id TEXT,
        run_id TEXT,
        escalation_hash TEXT,
        ordinal INTEGER NOT NULL
    ) STRICT
    """,
)


def now_ts() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Optional[datetime]) -> Optional[str]:
    return None if value is None else value.isoformat()


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    return None if value is None else datetime.fromisoformat(value)


def actor_to_json(actor: ActorRef) -> str:
    return canonical_json(actor_to_dict(actor)).decode("utf-8")


def actor_to_dict(actor: ActorRef) -> dict:
    return {
        "actor_kind": actor.actor_kind.value,
        "actor_id": actor.actor_id,
        "auth_method": actor.auth_method.value,
        "principal_key_id": actor.principal_key_id,
    }


def actor_from_json(raw: str) -> ActorRef:
    data = json.loads(raw)
    return ActorRef(
        actor_kind=ActorKind(data["actor_kind"]),
        actor_id=data["actor_id"],
        auth_method=AuthMethod(data["auth_method"]),
        principal_key_id=data.get("principal_key_id"),
    )


def _drift_to_dict(summary: DriftSummary) -> dict:
    return {
        "added": summary.added,
        "removed": summary.removed,
        "modified": summary.modified,
        "unattributed": summary.unattributed,
    }


def mutation_to_dict(mutation: MutationProposal) -> dict:
    return {
        "op": mutation.op.value,
        "path": mutation.path,
        "rename_to": mutation.rename_to,
        "before_digest": mutation.before_digest,
        "after_digest": None if mutation.after_ref is None else mutation.after_ref.digest,
        "after_byte_len": None if mutation.after_ref is None else mutation.after_ref.byte_len,
        "mode": mutation.mode,
        "in_scope": mutation.in_scope,
    }


def mutation_from_dict(data: dict) -> MutationProposal:
    after_ref = None
    if data.get("after_digest") is not None:
        after_ref = ArtifactRef(
            digest=data["after_digest"],
            media_type="application/octet-stream",
            byte_len=data.get("after_byte_len") or 0,
        )
    return MutationProposal(
        op=MutationOp(data["op"]),
        path=data["path"],
        rename_to=data.get("rename_to"),
        before_digest=data.get("before_digest"),
        after_ref=after_ref,
        mode=data.get("mode"),
        in_scope=bool(data.get("in_scope")),
    )


class StateStore:
    """The project's durable state and its per-project event chain."""

    def __init__(self, connection: Any, db_path: Path) -> None:
        self.connection = connection
        self.db_path = Path(db_path)
        self.artifacts = ArtifactStore(self.db_path.parent / "artifacts")

    # -- lifecycle ---------------------------------------------------------

    @classmethod
    def open(cls, db_path: Path) -> "StateStore":
        """Open (creating if absent) the store at `db_path`.

        Applies :data:`PRAGMAS`, creates the STRICT schema, installs the
        append-only guard on `audit_events`, and refuses a database this build
        cannot read.

        `CREATE TABLE IF NOT EXISTS` is a no-op on a table that already exists,
        so an older database opens with its old columns and no complaint. The
        staleness check is what turns that silence into a refusal.
        """
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(db_path), isolation_level=None)
        connection.row_factory = sqlite3.Row
        for name, value in PRAGMAS:
            connection.execute(f"PRAGMA {name}={value}")
        for statement in SCHEMA:
            connection.execute(statement)
        store = cls(connection, db_path)
        store._install_append_only_guard()
        try:
            store._refuse_stale_schema()
        except BaseException:
            connection.close()
            raise
        return store

    def _refuse_stale_schema(self) -> None:
        """Refuse a database written before :data:`STORAGE_VERSION`.

        There is no `ALTER TABLE` path while the storage layout is
        pre-release. A loud refusal naming the version and the missing column
        is the whole contract: the alternative is opening cleanly and failing
        on the first `get_project` with an error that mentions neither.

        A database that is missing nothing is stamped current on the way out,
        so the version travels with the file rather than being re-derived from
        its columns on every open.
        """
        missing: list[str] = []
        for table, columns in REQUIRED_COLUMNS:
            present = {
                row[1]
                for row in self.connection.execute(f"PRAGMA table_info({table})")
            }
            if not present:
                continue
            missing += [
                f"{table}.{column}" for column in columns if column not in present
            ]
        if missing:
            raise SchemaTooOld(
                f"database storage version {self.storage_version()} "
                f"(domain model {self._persisted_schema_version()}) predates "
                + ", ".join(missing)
                + f"; no migration path to storage version {STORAGE_VERSION}"
            )
        self.connection.execute(f"PRAGMA user_version={STORAGE_VERSION}")

    def storage_version(self) -> int:
        """This database's physical layout version. `0` if never stamped."""
        return int(self.pragma("user_version") or 0)

    def _persisted_schema_version(self) -> str:
        """The domain-model version this database's projects were written under.

        Reported alongside the storage version so the refusal says which model
        the data speaks, not only which columns are absent.
        """
        try:
            row = self.connection.execute(
                "SELECT schema_version FROM projects ORDER BY rowid LIMIT 1"
            ).fetchone()
        except sqlite3.DatabaseError:  # pragma: no cover - table shape unknown
            return "unknown"
        return "unknown" if row is None else row["schema_version"]

    def _install_append_only_guard(self) -> None:
        """Deny UPDATE and DELETE of `audit_events` on this connection."""

        def authorize(action, arg1, arg2, db_name, trigger):
            if action in (sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
                if arg1 == EVENT_TABLE:
                    return sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_DROP_TABLE and arg1 == EVENT_TABLE:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        self.connection.set_authorizer(authorize)

    def close(self) -> None:
        """Close the connection."""
        self.connection.close()

    def pragma(self, name: str) -> Any:
        """Return the current value of `PRAGMA <name>`."""
        row = self.connection.execute(f"PRAGMA {name}").fetchone()
        return None if row is None else row[0]

    def raw_execute(self, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        """Execute `sql` directly, without passing through the append protocol.

        Exists so integrity rules can be exercised against the real database.
        The append-only guard makes an UPDATE or DELETE of `audit_events` raise
        `sqlite3.DatabaseError` here exactly as it would anywhere else in the
        runtime.
        """
        cursor = self.connection.execute(sql, tuple(params))
        return [tuple(row) for row in cursor.fetchall()]

    # -- event log (evidence-model §3.1-§3.3) ------------------------------

    def genesis_hash(self, project_id: Id) -> Hash:
        """`sha256(project_id ‖ 0x00 ‖ schema_version)` — §3.1 step 5."""
        return digest_bytes(
            project_id.encode("utf-8") + b"\x00" + SCHEMA_VERSION.encode("utf-8")
        )

    @staticmethod
    def _event_body(
        *,
        event_id: Id,
        project_id: Id,
        seq: int,
        prev_event_hash: Hash,
        recorded_at: str,
        epistemic_class: str,
        event_type: str,
        actor: dict,
        subject: dict,
        payload_digest: Hash,
        payload_media_type: str,
        payload_byte_len: int,
        capability_used: Optional[str],
        authority_ref: Optional[str],
        causal_parent: Optional[str],
        clock_skew_ms: int,
    ) -> dict:
        """The §3.1 step-1 preimage: the event minus `event_hash`/`signature`."""
        return {
            "event_id": event_id,
            "project_id": project_id,
            "seq": seq,
            "prev_event_hash": prev_event_hash,
            "recorded_at": recorded_at,
            "epistemic_class": epistemic_class,
            "event_type": event_type,
            "actor": actor,
            "subject": subject,
            "payload_digest": payload_digest,
            "payload_media_type": payload_media_type,
            "payload_byte_len": payload_byte_len,
            "capability_used": capability_used,
            "authority_ref": authority_ref,
            "causal_parent": causal_parent,
            "clock_skew_ms": clock_skew_ms,
        }

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
        payload_ref = self.artifacts.put(payload, media_type="application/json")
        connection = self.connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            row = connection.execute(
                "SELECT event_head, event_seq FROM projects WHERE project_id=?",
                (project_id,),
            ).fetchone()
            if row is None:
                seq = 0
                prev_event_hash = self.genesis_hash(project_id)
            else:
                seq = int(row["event_seq"]) + 1
                prev_event_hash = row["event_head"]

            recorded_at = now_ts()
            event_id = f"ev-{uuid.uuid4().hex}"
            body = self._event_body(
                event_id=event_id,
                project_id=project_id,
                seq=seq,
                prev_event_hash=prev_event_hash,
                recorded_at=recorded_at.isoformat(),
                epistemic_class=epistemic_class.value,
                event_type=event_type,
                actor=actor_to_dict(actor),
                subject=dict(subject),
                payload_digest=payload_ref.digest,
                payload_media_type=payload_ref.media_type,
                payload_byte_len=payload_ref.byte_len,
                capability_used=capability_used,
                authority_ref=authority_ref,
                causal_parent=causal_parent,
                clock_skew_ms=0,
            )
            event_hash = digest_bytes(canonical_json(body))
            connection.execute(
                "INSERT INTO audit_events (project_id, seq, event_id, prev_event_hash,"
                " event_hash, recorded_at, epistemic_class, event_type, actor, subject,"
                " payload_digest, payload_media_type, payload_byte_len, capability_used,"
                " authority_ref, causal_parent, clock_skew_ms, signature)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    project_id,
                    seq,
                    event_id,
                    prev_event_hash,
                    event_hash,
                    body["recorded_at"],
                    body["epistemic_class"],
                    event_type,
                    canonical_json(body["actor"]).decode("utf-8"),
                    canonical_json(body["subject"]).decode("utf-8"),
                    payload_ref.digest,
                    payload_ref.media_type,
                    payload_ref.byte_len,
                    capability_used,
                    authority_ref,
                    causal_parent,
                    0,
                    None,
                ),
            )
            if row is not None:
                connection.execute(
                    "UPDATE projects SET event_head=?, event_seq=?, updated_at=?"
                    " WHERE project_id=?",
                    (event_hash, seq, recorded_at.isoformat(), project_id),
                )
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise

        return AuditEvent(
            event_id=event_id,
            project_id=project_id,
            seq=seq,
            prev_event_hash=prev_event_hash,
            event_hash=event_hash,
            recorded_at=recorded_at,
            epistemic_class=epistemic_class,
            event_type=event_type,
            actor=actor,
            subject=dict(subject),
            payload_ref=payload_ref,
            payload_digest=payload_ref.digest,
            capability_used=capability_used,
            authority_ref=authority_ref,
            causal_parent=causal_parent,
        )

    def _event_from_row(self, row: sqlite3.Row) -> AuditEvent:
        return AuditEvent(
            event_id=row["event_id"],
            project_id=row["project_id"],
            seq=int(row["seq"]),
            prev_event_hash=row["prev_event_hash"],
            event_hash=row["event_hash"],
            recorded_at=_parse_ts(row["recorded_at"]),
            epistemic_class=EpistemicClass(row["epistemic_class"]),
            event_type=row["event_type"],
            actor=actor_from_json(row["actor"]),
            subject=json.loads(row["subject"]),
            payload_ref=ArtifactRef(
                digest=row["payload_digest"],
                media_type=row["payload_media_type"],
                byte_len=int(row["payload_byte_len"]),
                encoding=Encoding.IDENTITY,
                retention_class=RetentionClass.PERMANENT,
            ),
            payload_digest=row["payload_digest"],
            capability_used=row["capability_used"],
            authority_ref=row["authority_ref"],
            causal_parent=row["causal_parent"],
            clock_skew_ms=int(row["clock_skew_ms"]),
            signature=row["signature"],
        )

    def list_events(self, project_id: Id) -> list[AuditEvent]:
        """Every event of the project, ordered by `seq`."""
        rows = self.connection.execute(
            "SELECT * FROM audit_events WHERE project_id=? ORDER BY seq", (project_id,)
        ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def verify_chain(self, project_id: Id) -> None:
        """Run the §3.3 checks over the project's chain.

        Continuity, gaplessness and payload binding; any failure raises
        `IntegrityViolation`.
        """
        rows = self.connection.execute(
            "SELECT * FROM audit_events WHERE project_id=? ORDER BY seq", (project_id,)
        ).fetchall()
        if not rows:
            raise IntegrityViolation(f"project {project_id} has no chain")

        expected_prev = self.genesis_hash(project_id)
        for index, row in enumerate(rows):
            seq = int(row["seq"])
            if seq != index:
                raise IntegrityViolation(
                    f"chain gap at position {index}: found seq {seq}"
                )
            if row["prev_event_hash"] != expected_prev:
                raise IntegrityViolation(
                    f"broken link at seq {seq}: prev_event_hash does not match"
                )
            body = self._event_body(
                event_id=row["event_id"],
                project_id=row["project_id"],
                seq=seq,
                prev_event_hash=row["prev_event_hash"],
                recorded_at=row["recorded_at"],
                epistemic_class=row["epistemic_class"],
                event_type=row["event_type"],
                actor=json.loads(row["actor"]),
                subject=json.loads(row["subject"]),
                payload_digest=row["payload_digest"],
                payload_media_type=row["payload_media_type"],
                payload_byte_len=int(row["payload_byte_len"]),
                capability_used=row["capability_used"],
                authority_ref=row["authority_ref"],
                causal_parent=row["causal_parent"],
                clock_skew_ms=int(row["clock_skew_ms"]),
            )
            recomputed = digest_bytes(canonical_json(body))
            if recomputed != row["event_hash"]:
                raise IntegrityViolation(
                    f"event {seq} does not match its recorded event_hash"
                )
            stored = self.artifacts.get(row["payload_digest"])
            if digest_bytes(stored) != row["payload_digest"]:
                raise IntegrityViolation(f"payload binding failed at seq {seq}")
            expected_prev = row["event_hash"]

        head = self.connection.execute(
            "SELECT event_head, event_seq FROM projects WHERE project_id=?",
            (project_id,),
        ).fetchone()
        if head is not None:
            if head["event_head"] != rows[-1]["event_hash"]:
                raise IntegrityViolation("event_head does not name the highest seq")
            if int(head["event_seq"]) != int(rows[-1]["seq"]):
                raise IntegrityViolation("event_seq does not name the highest seq")

    def audit_reconciliation_closure(self, project_id: Id) -> None:
        """Evidence-model §3.2.1: no non-terminal operation of an older epoch
        precedes a later dispatch or apply on the same run (`RUN-INV-3`)."""
        project_epoch = self.get_project(project_id).controller_epoch
        offenders: list[str] = []
        for invocation in self._all_invocations(project_id):
            if invocation.controller_epoch < project_epoch and not clears_barrier(
                invocation.reconciliation_state
            ):
                offenders.append(invocation.invocation_id)
        for intent in self._all_intents(project_id):
            if intent.controller_epoch < project_epoch and not clears_barrier(
                intent.reconciliation_state
            ):
                offenders.append(intent.intent_id)
        if offenders:
            raise IntegrityViolation(
                "unreconciled old-epoch operations remain: " + ", ".join(offenders)
            )

    def artifact_bytes(self, digest: Hash) -> bytes:
        """Payload bytes behind `digest`, re-hashed on the way out."""
        return self.artifacts.get(digest)

    def store_artifact(self, data: bytes, *, media_type: str) -> ArtifactRef:
        """Put bytes in the artifact store this store reads payloads from."""
        return self.artifacts.put(data, media_type=media_type)

    # -- projects and runs -------------------------------------------------

    def get_project(self, project_id: Id) -> Project:
        row = self.connection.execute(
            "SELECT * FROM projects WHERE project_id=?", (project_id,)
        ).fetchone()
        if row is None:
            raise KeyError(project_id)
        return Project(
            project_id=row["project_id"],
            name=row["name"],
            slug=row["slug"],
            schema_version=row["schema_version"],
            lifecycle=ProjectLifecycle(row["lifecycle"]),
            suspension=SuspensionState(row["suspension"]),
            governance_mode=GovernanceMode(row["governance_mode"]),
            workspace_root=row["workspace_root"],
            created_at=_parse_ts(row["created_at"]),
            updated_at=_parse_ts(row["updated_at"]),
            created_by=actor_from_json(row["created_by"]),
            event_head=row["event_head"],
            event_seq=int(row["event_seq"]),
            controller_epoch=int(row["controller_epoch"]),
            policy_digest=row["policy_digest"],
            budget=Budget(),
            budget_used=BudgetUsage(),
            snapshot_current=row["snapshot_current"],
            suspension_ref=row["suspension_ref"],
        )

    def put_project(self, project: Project) -> None:
        self.connection.execute(
            "INSERT INTO projects (project_id, name, slug, schema_version, lifecycle,"
            " suspension, governance_mode, workspace_root, created_at, updated_at,"
            " created_by, event_head, event_seq, controller_epoch, policy_digest,"
            " snapshot_current, suspension_ref)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(project_id) DO UPDATE SET"
            " name=excluded.name, slug=excluded.slug, lifecycle=excluded.lifecycle,"
            " suspension=excluded.suspension,"
            " governance_mode=excluded.governance_mode,"
            " workspace_root=excluded.workspace_root,"
            " updated_at=excluded.updated_at, event_head=excluded.event_head,"
            " event_seq=excluded.event_seq,"
            " controller_epoch=excluded.controller_epoch,"
            " policy_digest=excluded.policy_digest,"
            " snapshot_current=excluded.snapshot_current,"
            " suspension_ref=excluded.suspension_ref",
            (
                project.project_id,
                project.name,
                project.slug,
                project.schema_version,
                project.lifecycle.value,
                project.suspension.value,
                project.governance_mode.value,
                project.workspace_root,
                _iso(project.created_at),
                _iso(project.updated_at),
                actor_to_json(project.created_by),
                project.event_head,
                project.event_seq,
                project.controller_epoch,
                project.policy_digest,
                project.snapshot_current,
                project.suspension_ref,
            ),
        )

    def set_project_suspension(
        self,
        project_id: Id,
        suspension: SuspensionState,
        *,
        suspension_ref: Optional[Id] = None,
    ) -> None:
        """Write axis 3 alone (`O-3`, `G-8`).

        A targeted UPDATE, not a whole-row write: `event_head` and `event_seq`
        belong to the append protocol, and a read-modify-write around an
        `append_event` would roll the chain head back onto a sequence number
        that is already spent.
        """
        self.connection.execute(
            "UPDATE projects SET suspension=?, suspension_ref=?, updated_at=?"
            " WHERE project_id=?",
            (suspension.value, suspension_ref, _iso(now_ts()), project_id),
        )

    def set_project_snapshot_current(self, project_id: Id, snapshot_id: Id) -> None:
        """Point `snapshot_current` at the newest snapshot. Targeted, as above."""
        self.connection.execute(
            "UPDATE projects SET snapshot_current=?, updated_at=? WHERE project_id=?",
            (snapshot_id, _iso(now_ts()), project_id),
        )

    def bump_controller_epoch(self, project_id: Id) -> int:
        """Increment and commit `controller_epoch`, returning the new value.

        `P-INV-4`: this is durable before the controller does any other work.
        Committed under `synchronous = FULL`, so it is fsynced before it is
        reported, not merely written.
        """
        connection = self.connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            row = connection.execute(
                "SELECT controller_epoch FROM projects WHERE project_id=?",
                (project_id,),
            ).fetchone()
            if row is None:
                raise KeyError(project_id)
            epoch = int(row["controller_epoch"]) + 1
            connection.execute(
                "UPDATE projects SET controller_epoch=?, updated_at=? WHERE project_id=?",
                (epoch, now_ts().isoformat(), project_id),
            )
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        return epoch

    def put_run(self, run: StageRun) -> None:
        self.connection.execute(
            "INSERT INTO runs (run_id, project_id, stage_id, lifecycle, suspension,"
            " controller_epoch, started_at, input_snapshot_id, output_snapshot_id,"
            " deadline_at, attempt, ordinal)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,"
            " COALESCE((SELECT ordinal FROM runs WHERE run_id=?),"
            " (SELECT COUNT(*) FROM runs)))"
            " ON CONFLICT(run_id) DO UPDATE SET lifecycle=excluded.lifecycle,"
            " suspension=excluded.suspension,"
            " input_snapshot_id=excluded.input_snapshot_id,"
            " output_snapshot_id=excluded.output_snapshot_id,"
            " deadline_at=excluded.deadline_at, attempt=excluded.attempt",
            (
                run.run_id,
                run.project_id,
                run.stage_id,
                run.lifecycle.value,
                run.suspension.value,
                run.controller_epoch,
                _iso(run.started_at),
                run.input_snapshot_id,
                run.output_snapshot_id,
                _iso(run.deadline_at),
                run.attempt,
                run.run_id,
            ),
        )

    def _run_from_row(self, row: sqlite3.Row) -> StageRun:
        return StageRun(
            run_id=row["run_id"],
            project_id=row["project_id"],
            stage_id=row["stage_id"],
            lifecycle=RunLifecycle(row["lifecycle"]),
            suspension=SuspensionState(row["suspension"]),
            controller_epoch=int(row["controller_epoch"]),
            started_at=_parse_ts(row["started_at"]),
            input_snapshot_id=row["input_snapshot_id"],
            output_snapshot_id=row["output_snapshot_id"],
            deadline_at=_parse_ts(row["deadline_at"]),
            attempt=int(row["attempt"]),
        )

    def get_run(self, run_id: Id) -> StageRun:
        row = self.connection.execute(
            "SELECT * FROM runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return self._run_from_row(row)

    def list_runs(self, project_id: Id) -> list[StageRun]:
        rows = self.connection.execute(
            "SELECT * FROM runs WHERE project_id=? ORDER BY ordinal", (project_id,)
        ).fetchall()
        return [self._run_from_row(row) for row in rows]

    # -- invocations and receipts ------------------------------------------

    def put_invocation(self, invocation: WorkerInvocation, project_id: Id) -> None:
        self.connection.execute(
            "INSERT INTO invocations (invocation_id, run_id, project_id, stage_id,"
            " provider_id, provider_version, worker_role, prompt_bundle_digest,"
            " request_digest, context_digest, idempotency_key, controller_epoch,"
            " status, reconciliation_state, sandbox_profile_id, dispatched_at,"
            " deadline_at, receipt_id, ordinal)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,"
            " COALESCE((SELECT ordinal FROM invocations WHERE invocation_id=?),"
            " (SELECT COUNT(*) FROM invocations)))"
            " ON CONFLICT(invocation_id) DO UPDATE SET status=excluded.status,"
            " reconciliation_state=excluded.reconciliation_state,"
            " dispatched_at=excluded.dispatched_at, receipt_id=excluded.receipt_id",
            (
                invocation.invocation_id,
                invocation.run_id,
                project_id,
                invocation.stage_id,
                invocation.provider_id,
                invocation.provider_version,
                invocation.worker_role.value,
                invocation.prompt_bundle_ref.digest,
                invocation.request_digest,
                invocation.context_digest,
                invocation.idempotency_key,
                invocation.controller_epoch,
                invocation.status.value,
                invocation.reconciliation_state.value,
                invocation.sandbox_profile_id,
                _iso(invocation.dispatched_at),
                _iso(invocation.deadline_at),
                invocation.receipt_id,
                invocation.invocation_id,
            ),
        )

    def _invocation_from_row(self, row: sqlite3.Row) -> WorkerInvocation:
        prompt_ref = ArtifactRef(
            digest=row["prompt_bundle_digest"],
            media_type="application/octet-stream",
            byte_len=0,
        )
        request_ref = ArtifactRef(
            digest=row["request_digest"],
            media_type="application/json",
            byte_len=0,
        )
        return WorkerInvocation(
            invocation_id=row["invocation_id"],
            run_id=row["run_id"],
            stage_id=row["stage_id"],
            provider_id=row["provider_id"],
            provider_version=row["provider_version"],
            worker_role=WorkerRole(row["worker_role"]),
            prompt_bundle_ref=prompt_ref,
            request_ref=request_ref,
            request_digest=row["request_digest"],
            context_digest=row["context_digest"],
            idempotency_key=row["idempotency_key"],
            controller_epoch=int(row["controller_epoch"]),
            status=InvocationStatus(row["status"]),
            reconciliation_state=ReconciliationState(row["reconciliation_state"]),
            sandbox_profile_id=row["sandbox_profile_id"],
            dispatched_at=_parse_ts(row["dispatched_at"]),
            deadline_at=_parse_ts(row["deadline_at"]),
            receipt_id=row["receipt_id"],
        )

    def get_invocation(self, invocation_id: Id) -> WorkerInvocation:
        row = self.connection.execute(
            "SELECT * FROM invocations WHERE invocation_id=?", (invocation_id,)
        ).fetchone()
        if row is None:
            raise KeyError(invocation_id)
        return self._invocation_from_row(row)

    def invocation_project(self, invocation_id: Id) -> Id:
        row = self.connection.execute(
            "SELECT project_id FROM invocations WHERE invocation_id=?", (invocation_id,)
        ).fetchone()
        if row is None:
            raise KeyError(invocation_id)
        return row["project_id"]

    def list_invocations(self, run_id: Id) -> list[WorkerInvocation]:
        rows = self.connection.execute(
            "SELECT * FROM invocations WHERE run_id=? ORDER BY ordinal", (run_id,)
        ).fetchall()
        return [self._invocation_from_row(row) for row in rows]

    def _all_invocations(self, project_id: Id) -> list[WorkerInvocation]:
        rows = self.connection.execute(
            "SELECT * FROM invocations WHERE project_id=? ORDER BY ordinal",
            (project_id,),
        ).fetchall()
        return [self._invocation_from_row(row) for row in rows]

    def list_unreconciled_invocations(self, project_id: Id) -> list[WorkerInvocation]:
        """Invocations with `controller_epoch < project.controller_epoch`."""
        epoch = self.get_project(project_id).controller_epoch
        return [
            invocation
            for invocation in self._all_invocations(project_id)
            if invocation.controller_epoch < epoch
        ]

    def put_worker_receipt(self, receipt: WorkerReceipt, project_id: Id) -> None:
        self.connection.execute(
            "INSERT INTO worker_receipts (receipt_id, invocation_id, project_id,"
            " ended_at, duration_ms, usage, output_digest, output_media_type,"
            " output_byte_len, termination_reason, attribution, attested_by,"
            " receipt_hash, prev_event_hash, ordinal)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,"
            " (SELECT COUNT(*) FROM worker_receipts))",
            (
                receipt.receipt_id,
                receipt.invocation_id,
                project_id,
                _iso(receipt.ended_at),
                receipt.duration_ms,
                canonical_json(
                    {
                        "input_units": receipt.usage.input_units,
                        "output_units": receipt.usage.output_units,
                        "tool_calls": receipt.usage.tool_calls,
                        "cost_units": receipt.usage.cost_units,
                        "wall_clock_ms": receipt.usage.wall_clock_ms,
                    }
                ).decode("utf-8"),
                receipt.output_digest,
                receipt.output_ref.media_type,
                receipt.output_ref.byte_len,
                receipt.termination_reason.value,
                receipt.attribution.value,
                actor_to_json(receipt.attested_by),
                receipt.receipt_hash,
                receipt.prev_event_hash,
            ),
        )

    def _worker_receipt_from_row(self, row: sqlite3.Row) -> WorkerReceipt:
        usage = json.loads(row["usage"])
        return WorkerReceipt(
            receipt_id=row["receipt_id"],
            invocation_id=row["invocation_id"],
            ended_at=_parse_ts(row["ended_at"]),
            duration_ms=int(row["duration_ms"]),
            usage=Usage(**usage),
            output_ref=ArtifactRef(
                digest=row["output_digest"],
                media_type=row["output_media_type"],
                byte_len=int(row["output_byte_len"]),
            ),
            output_digest=row["output_digest"],
            termination_reason=TerminationReason(row["termination_reason"]),
            attribution=Attribution(row["attribution"]),
            attested_by=actor_from_json(row["attested_by"]),
            receipt_hash=row["receipt_hash"],
            prev_event_hash=row["prev_event_hash"],
        )

    def list_worker_receipts(self, invocation_id: Id) -> list[WorkerReceipt]:
        rows = self.connection.execute(
            "SELECT * FROM worker_receipts WHERE invocation_id=? ORDER BY ordinal",
            (invocation_id,),
        ).fetchall()
        return [self._worker_receipt_from_row(row) for row in rows]

    # -- commit intents and receipts ---------------------------------------

    def put_commit_intent(self, intent: CommitIntent, project_id: Id) -> None:
        preconditions = intent.preconditions or CommitPreconditions()
        payload = {
            "validations": list(preconditions.validations),
            "reviews": [
                {"kind": entry.kind, "id": entry.id} for entry in preconditions.reviews
            ],
            "decisions": [
                {"kind": entry.kind, "id": entry.id} for entry in preconditions.decisions
            ],
        }
        self.connection.execute(
            "INSERT INTO commit_intents (intent_id, run_id, project_id, stage_id,"
            " vcs_kind, base_revision_id, target_ref, expected_tree_digest, message,"
            " operation_token, controller_epoch, status, reconciliation_state,"
            " preconditions, preconditions_met, mutations, trailers, authorized_by,"
            " authorized_at, denial_reason, receipt_id, ordinal)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,"
            " COALESCE((SELECT ordinal FROM commit_intents WHERE intent_id=?),"
            " (SELECT COUNT(*) FROM commit_intents)))"
            " ON CONFLICT(intent_id) DO UPDATE SET status=excluded.status,"
            " reconciliation_state=excluded.reconciliation_state,"
            " preconditions=excluded.preconditions,"
            " preconditions_met=excluded.preconditions_met,"
            " expected_tree_digest=excluded.expected_tree_digest,"
            " authorized_by=excluded.authorized_by,"
            " authorized_at=excluded.authorized_at,"
            " denial_reason=excluded.denial_reason, receipt_id=excluded.receipt_id",
            (
                intent.intent_id,
                intent.run_id,
                project_id,
                intent.stage_id,
                intent.vcs_kind.value,
                intent.base_revision_id,
                intent.target_ref,
                intent.expected_tree_digest,
                intent.message,
                intent.operation_token,
                intent.controller_epoch,
                intent.status.value,
                intent.reconciliation_state.value,
                canonical_json(payload).decode("utf-8"),
                1 if intent.preconditions_met else 0,
                canonical_json(
                    [mutation_to_dict(m) for m in intent.mutations]
                ).decode("utf-8"),
                canonical_json(dict(intent.trailers)).decode("utf-8"),
                None if intent.authorized_by is None else actor_to_json(intent.authorized_by),
                _iso(intent.authorized_at),
                intent.denial_reason,
                intent.receipt_id,
                intent.intent_id,
            ),
        )

    def _intent_from_row(self, row: sqlite3.Row) -> CommitIntent:
        raw = json.loads(row["preconditions"])
        preconditions = CommitPreconditions.__new__(CommitPreconditions)
        # Stored preconditions are re-read without re-running validation: the
        # consuming path re-checks them (`G-1`), so a record written past the
        # constructor is still refused where it matters rather than here.
        object.__setattr__(preconditions, "validations", tuple(raw.get("validations", ())))
        object.__setattr__(
            preconditions,
            "reviews",
            tuple(Ref(entry["kind"], entry["id"]) for entry in raw.get("reviews", ())),
        )
        object.__setattr__(
            preconditions,
            "decisions",
            tuple(Ref(entry["kind"], entry["id"]) for entry in raw.get("decisions", ())),
        )
        return CommitIntent(
            intent_id=row["intent_id"],
            run_id=row["run_id"],
            stage_id=row["stage_id"],
            vcs_kind=VcsKind(row["vcs_kind"]),
            base_revision_id=row["base_revision_id"],
            target_ref=row["target_ref"],
            expected_tree_digest=row["expected_tree_digest"],
            message=row["message"],
            operation_token=row["operation_token"],
            controller_epoch=int(row["controller_epoch"]),
            status=CommitIntentStatus(row["status"]),
            reconciliation_state=ReconciliationState(row["reconciliation_state"]),
            preconditions=preconditions,
            preconditions_met=bool(row["preconditions_met"]),
            mutations=tuple(
                mutation_from_dict(entry) for entry in json.loads(row["mutations"])
            ),
            trailers=json.loads(row["trailers"]),
            authorized_by=(
                None if row["authorized_by"] is None
                else actor_from_json(row["authorized_by"])
            ),
            authorized_at=_parse_ts(row["authorized_at"]),
            denial_reason=row["denial_reason"],
            receipt_id=row["receipt_id"],
        )

    def get_commit_intent(self, intent_id: Id) -> CommitIntent:
        row = self.connection.execute(
            "SELECT * FROM commit_intents WHERE intent_id=?", (intent_id,)
        ).fetchone()
        if row is None:
            raise KeyError(intent_id)
        return self._intent_from_row(row)

    def intent_project(self, intent_id: Id) -> Id:
        row = self.connection.execute(
            "SELECT project_id FROM commit_intents WHERE intent_id=?", (intent_id,)
        ).fetchone()
        if row is None:
            raise KeyError(intent_id)
        return row["project_id"]

    def list_commit_intents(self, run_id: Id) -> list[CommitIntent]:
        rows = self.connection.execute(
            "SELECT * FROM commit_intents WHERE run_id=? ORDER BY ordinal", (run_id,)
        ).fetchall()
        return [self._intent_from_row(row) for row in rows]

    def _all_intents(self, project_id: Id) -> list[CommitIntent]:
        rows = self.connection.execute(
            "SELECT * FROM commit_intents WHERE project_id=? ORDER BY ordinal",
            (project_id,),
        ).fetchall()
        return [self._intent_from_row(row) for row in rows]

    def list_unreconciled_intents(self, project_id: Id) -> list[CommitIntent]:
        """Intents with `controller_epoch < project.controller_epoch`."""
        epoch = self.get_project(project_id).controller_epoch
        return [
            intent
            for intent in self._all_intents(project_id)
            if intent.controller_epoch < epoch
        ]

    def put_commit_receipt(self, receipt: CommitReceipt, project_id: Id) -> None:
        self.connection.execute(
            "INSERT INTO commit_receipts (receipt_id, intent_id, project_id,"
            " revision_id, actual_tree_digest, verification, diff_digest,"
            " diff_media_type, diff_byte_len, applied_at, applied_by, attribution,"
            " operation_token, post_snapshot_id, receipt_hash, prev_event_hash,"
            " parent_revision_ids, rollback_handle, ordinal)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,"
            " (SELECT COUNT(*) FROM commit_receipts))",
            (
                receipt.receipt_id,
                receipt.intent_id,
                project_id,
                receipt.revision_id,
                receipt.actual_tree_digest,
                receipt.verification.value,
                receipt.diff_ref.digest,
                receipt.diff_ref.media_type,
                receipt.diff_ref.byte_len,
                _iso(receipt.applied_at),
                actor_to_json(receipt.applied_by),
                receipt.attribution.value,
                receipt.operation_token,
                receipt.post_snapshot_id,
                receipt.receipt_hash,
                receipt.prev_event_hash,
                canonical_json(list(receipt.parent_revision_ids)).decode("utf-8"),
                receipt.rollback_handle,
            ),
        )

    def _commit_receipt_from_row(self, row: sqlite3.Row) -> CommitReceipt:
        return CommitReceipt(
            receipt_id=row["receipt_id"],
            intent_id=row["intent_id"],
            revision_id=row["revision_id"],
            actual_tree_digest=row["actual_tree_digest"],
            verification=Verification(row["verification"]),
            diff_ref=ArtifactRef(
                digest=row["diff_digest"],
                media_type=row["diff_media_type"],
                byte_len=int(row["diff_byte_len"]),
            ),
            applied_at=_parse_ts(row["applied_at"]),
            applied_by=actor_from_json(row["applied_by"]),
            attribution=Attribution(row["attribution"]),
            operation_token=row["operation_token"],
            post_snapshot_id=row["post_snapshot_id"],
            receipt_hash=row["receipt_hash"],
            prev_event_hash=row["prev_event_hash"],
            parent_revision_ids=tuple(json.loads(row["parent_revision_ids"])),
            rollback_handle=row["rollback_handle"],
        )

    def list_commit_receipts(self, intent_id: Id) -> list[CommitReceipt]:
        rows = self.connection.execute(
            "SELECT * FROM commit_receipts WHERE intent_id=? ORDER BY ordinal",
            (intent_id,),
        ).fetchall()
        return [self._commit_receipt_from_row(row) for row in rows]

    # -- reviews, attestations, evidence resolution ------------------------

    def put_review(self, review: Review, project_id: Id) -> None:
        self.connection.execute(
            "INSERT INTO reviews (review_id, run_id, project_id, stage_id,"
            " review_spec_id, reviewer, reviewer_kind, independence, inputs_digest,"
            " input_snapshot_id, verdict, review_hash, completed_at, ordinal)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,(SELECT COUNT(*) FROM reviews))",
            (
                review.review_id,
                review.run_id,
                project_id,
                review.stage_id,
                review.review_spec_id,
                actor_to_json(review.reviewer),
                review.reviewer_kind.value,
                review.independence.value,
                review.inputs_digest,
                review.input_snapshot_id,
                review.verdict.value,
                review.review_hash,
                _iso(review.completed_at),
            ),
        )

    def _review_from_row(self, row: sqlite3.Row) -> Review:
        return Review(
            review_id=row["review_id"],
            run_id=row["run_id"],
            stage_id=row["stage_id"],
            review_spec_id=row["review_spec_id"],
            reviewer=actor_from_json(row["reviewer"]),
            reviewer_kind=ReviewerKind(row["reviewer_kind"]),
            independence=Independence(row["independence"]),
            inputs_digest=row["inputs_digest"],
            input_snapshot_id=row["input_snapshot_id"],
            verdict=Verdict(row["verdict"]),
            review_hash=row["review_hash"],
            completed_at=_parse_ts(row["completed_at"]),
        )

    def get_review(self, review_id: Id) -> Review:
        row = self.connection.execute(
            "SELECT * FROM reviews WHERE review_id=?", (review_id,)
        ).fetchone()
        if row is None:
            raise KeyError(review_id)
        return self._review_from_row(row)

    def put_attestation(self, attestation: ReviewAttestation, project_id: Id) -> None:
        self.connection.execute(
            "INSERT INTO attestations (attestation_id, run_id, project_id, stage_id,"
            " review_spec_id, review_ids, verdict, quorum_met, independence_satisfied,"
            " input_snapshot_id, contract_hash, attested_by, attested_at,"
            " attestation_hash, prev_event_hash, ordinal)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,(SELECT COUNT(*) FROM attestations))",
            (
                attestation.attestation_id,
                attestation.run_id,
                project_id,
                attestation.stage_id,
                attestation.review_spec_id,
                canonical_json(sorted(attestation.review_ids)).decode("utf-8"),
                attestation.verdict.value,
                1 if attestation.quorum_met else 0,
                1 if attestation.independence_satisfied else 0,
                attestation.input_snapshot_id,
                attestation.contract_hash,
                actor_to_json(attestation.attested_by),
                _iso(attestation.attested_at),
                attestation.attestation_hash,
                attestation.prev_event_hash,
            ),
        )

    def _attestation_from_row(self, row: sqlite3.Row) -> ReviewAttestation:
        return ReviewAttestation(
            attestation_id=row["attestation_id"],
            run_id=row["run_id"],
            stage_id=row["stage_id"],
            review_spec_id=row["review_spec_id"],
            review_ids=frozenset(json.loads(row["review_ids"])),
            verdict=Verdict(row["verdict"]),
            quorum_met=bool(row["quorum_met"]),
            independence_satisfied=bool(row["independence_satisfied"]),
            input_snapshot_id=row["input_snapshot_id"],
            contract_hash=row["contract_hash"],
            attested_by=actor_from_json(row["attested_by"]),
            attested_at=_parse_ts(row["attested_at"]),
            attestation_hash=row["attestation_hash"],
            prev_event_hash=row["prev_event_hash"],
        )

    def get_attestation(self, attestation_id: Id) -> ReviewAttestation:
        row = self.connection.execute(
            "SELECT * FROM attestations WHERE attestation_id=?", (attestation_id,)
        ).fetchone()
        if row is None:
            raise KeyError(attestation_id)
        return self._attestation_from_row(row)

    def resolve_review_evidence(self, ref: Ref) -> ReviewAttestation:
        """Resolve a review precondition to the attestation that discharges it.

        A ref of any other kind, and a ref whose id names a judgement record
        rather than an attestation, raise `IntegrityViolation` (`G-1`): the
        evaluator never reads a reviewer's own verdict.
        """
        from .models import ATTESTATION_KIND

        if not isinstance(ref, Ref):
            raise IntegrityViolation(
                f"a review precondition must be a typed reference, got {ref!r}"
            )
        if ref.kind != ATTESTATION_KIND:
            raise IntegrityViolation(
                f"{ref.kind!r} is not evidence; only a kernel-minted "
                f"{ATTESTATION_KIND} discharges a review precondition"
            )
        row = self.connection.execute(
            "SELECT * FROM attestations WHERE attestation_id=?", (ref.id,)
        ).fetchone()
        if row is None:
            raise IntegrityViolation(
                f"no {ATTESTATION_KIND} is recorded under {ref.id!r}; a judgement "
                "record never satisfies a reference declared over attestations"
            )
        return self._attestation_from_row(row)

    # -- snapshots and escalations -----------------------------------------

    def put_snapshot(self, snapshot: RealitySnapshot) -> None:
        self.connection.execute(
            "INSERT INTO snapshots (snapshot_id, project_id, taken_at, taken_by,"
            " trigger, completeness, tree_digest, file_index_digest, file_count,"
            " byte_count, snapshot_hash, vcs_state, scope, drift_vs, drift_summary,"
            " ordinal)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,(SELECT COUNT(*) FROM snapshots))",
            (
                snapshot.snapshot_id,
                snapshot.project_id,
                _iso(snapshot.taken_at),
                actor_to_json(snapshot.taken_by),
                snapshot.trigger.value,
                snapshot.completeness.value,
                snapshot.tree_digest,
                snapshot.file_index_ref.digest,
                snapshot.file_count,
                snapshot.byte_count,
                snapshot.snapshot_hash,
                None
                if snapshot.vcs_state is None
                else canonical_json(dict(snapshot.vcs_state)).decode("utf-8"),
                canonical_json(list(snapshot.scope)).decode("utf-8"),
                snapshot.drift_vs,
                None
                if snapshot.drift_summary is None
                else canonical_json(_drift_to_dict(snapshot.drift_summary)).decode("utf-8"),
            ),
        )

    def _snapshot_from_row(self, row: sqlite3.Row) -> RealitySnapshot:
        return RealitySnapshot(
            snapshot_id=row["snapshot_id"],
            project_id=row["project_id"],
            taken_at=_parse_ts(row["taken_at"]),
            taken_by=actor_from_json(row["taken_by"]),
            trigger=SnapshotTrigger(row["trigger"]),
            completeness=Completeness(row["completeness"]),
            tree_digest=row["tree_digest"],
            file_index_ref=ArtifactRef(
                digest=row["file_index_digest"],
                media_type="application/json",
                byte_len=0,
            ),
            file_count=int(row["file_count"]),
            byte_count=int(row["byte_count"]),
            snapshot_hash=row["snapshot_hash"],
            vcs_state=None if row["vcs_state"] is None else json.loads(row["vcs_state"]),
            scope=tuple(json.loads(row["scope"])),
            drift_vs=row["drift_vs"],
            drift_summary=(
                None
                if row["drift_summary"] is None
                else DriftSummary(**json.loads(row["drift_summary"]))
            ),
        )

    def get_snapshot(self, snapshot_id: Id) -> RealitySnapshot:
        row = self.connection.execute(
            "SELECT * FROM snapshots WHERE snapshot_id=?", (snapshot_id,)
        ).fetchone()
        if row is None:
            raise KeyError(snapshot_id)
        return self._snapshot_from_row(row)

    def list_snapshots(self, project_id: Id) -> list[RealitySnapshot]:
        """Every snapshot of a project, oldest first."""
        rows = self.connection.execute(
            "SELECT * FROM snapshots WHERE project_id=? ORDER BY ordinal",
            (project_id,),
        ).fetchall()
        return [self._snapshot_from_row(row) for row in rows]

    def latest_snapshot(self, project_id: Id) -> Optional[RealitySnapshot]:
        """The most recent observation, whatever it managed to see.

        Distinct from :meth:`newest_complete_snapshot` and from
        `Project.snapshot_current`, which are both the newest *`COMPLETE`*
        snapshot: this one answers "what happened the last time the runtime
        looked?", which is the question a gate on new effects has to ask. A
        failed observation would otherwise be invisible to every caller.
        """
        row = self.connection.execute(
            "SELECT * FROM snapshots WHERE project_id=? ORDER BY ordinal DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return None if row is None else self._snapshot_from_row(row)

    def newest_complete_snapshot(self, project_id: Id) -> Optional[RealitySnapshot]:
        """The newest `COMPLETE` snapshot, or `None`.

        Only `COMPLETE` counts: a partial or failed observation supersedes
        nothing, because absence of observation is not observation of absence
        (`RS-INV-1`).
        """
        row = self.connection.execute(
            "SELECT * FROM snapshots WHERE project_id=? AND completeness=?"
            " ORDER BY ordinal DESC LIMIT 1",
            (project_id, Completeness.COMPLETE.value),
        ).fetchone()
        return None if row is None else self._snapshot_from_row(row)

    def snapshot_document(self, snapshot: RealitySnapshot) -> dict:
        """The stored `file_index_ref` payload for a snapshot.

        Re-hashed on the way out by the artifact store, so a file index that no
        longer matches its digest is an `IntegrityViolation` rather than a
        quietly different reality.
        """
        return json.loads(self.artifact_bytes(snapshot.file_index_ref.digest))

    # -- human decisions (domain-model §9.A) --------------------------------

    def put_decision(self, decision: HumanDecision) -> None:
        self.connection.execute(
            "INSERT INTO decisions (decision_id, project_id, subject_kind,"
            " subject_id, decision_kind, question, options_offered, chosen,"
            " justification, scope, decided_by, auth_method, decided_at, nonce,"
            " snapshot_bound, subject_snapshot_id, decision_state, evidence_shown,"
            " expires_at, decision_hash, prev_event_hash, ordinal)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,"
            "(SELECT COUNT(*) FROM decisions))"
            " ON CONFLICT(decision_id) DO UPDATE SET"
            " decision_state=excluded.decision_state",
            (
                decision.decision_id,
                decision.project_id,
                decision.subject_kind.value,
                decision.subject_id,
                decision.decision_kind.value,
                decision.question,
                canonical_json(list(decision.options_offered)).decode("utf-8"),
                decision.chosen,
                decision.justification,
                decision.scope.value,
                actor_to_json(decision.decided_by),
                decision.auth_method.value,
                _iso(decision.decided_at),
                decision.nonce,
                int(decision.snapshot_bound),
                decision.subject_snapshot_id,
                decision.decision_state.value,
                canonical_json(
                    [ref.digest for ref in decision.evidence_shown]
                ).decode("utf-8"),
                _iso(decision.expires_at),
                decision.decision_hash,
                decision.prev_event_hash,
            ),
        )

    def _decision_from_row(self, row: sqlite3.Row) -> HumanDecision:
        return HumanDecision(
            decision_id=row["decision_id"],
            project_id=row["project_id"],
            subject_kind=DecisionSubjectKind(row["subject_kind"]),
            subject_id=row["subject_id"],
            decision_kind=DecisionKind(row["decision_kind"]),
            question=row["question"],
            chosen=row["chosen"],
            justification=row["justification"],
            scope=DecisionScope(row["scope"]),
            decided_by=actor_from_json(row["decided_by"]),
            auth_method=AuthMethod(row["auth_method"]),
            decided_at=_parse_ts(row["decided_at"]),
            nonce=row["nonce"],
            snapshot_bound=bool(row["snapshot_bound"]),
            decision_state=DecisionState(row["decision_state"]),
            options_offered=tuple(json.loads(row["options_offered"])),
            evidence_shown=tuple(
                ArtifactRef(digest=digest, media_type="application/json", byte_len=0)
                for digest in json.loads(row["evidence_shown"])
            ),
            subject_snapshot_id=row["subject_snapshot_id"],
            expires_at=_parse_ts(row["expires_at"]),
            decision_hash=row["decision_hash"],
            prev_event_hash=row["prev_event_hash"],
        )

    def get_decision(self, decision_id: Id) -> HumanDecision:
        row = self.connection.execute(
            "SELECT * FROM decisions WHERE decision_id=?", (decision_id,)
        ).fetchone()
        if row is None:
            raise KeyError(decision_id)
        return self._decision_from_row(row)

    def list_decisions(self, project_id: Id) -> list[HumanDecision]:
        rows = self.connection.execute(
            "SELECT * FROM decisions WHERE project_id=? ORDER BY ordinal",
            (project_id,),
        ).fetchall()
        return [self._decision_from_row(row) for row in rows]

    def put_escalation(self, escalation: Escalation) -> None:
        self.connection.execute(
            "INSERT INTO escalations (escalation_id, project_id, trigger, severity,"
            " summary, raised_by, raised_at, suspension_applied, suspension_target,"
            " status, stage_id, run_id, escalation_hash, ordinal)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,(SELECT COUNT(*) FROM escalations))",
            (
                escalation.escalation_id,
                escalation.project_id,
                escalation.trigger.value,
                escalation.severity.value,
                escalation.summary,
                actor_to_json(escalation.raised_by),
                _iso(escalation.raised_at),
                escalation.suspension_applied.value,
                escalation.suspension_target,
                escalation.status.value,
                escalation.stage_id,
                escalation.run_id,
                escalation.escalation_hash,
            ),
        )

    def list_escalations(self, project_id: Id) -> list[Escalation]:
        rows = self.connection.execute(
            "SELECT * FROM escalations WHERE project_id=? ORDER BY ordinal",
            (project_id,),
        ).fetchall()
        return [
            Escalation(
                escalation_id=row["escalation_id"],
                project_id=row["project_id"],
                trigger=EscalationTrigger(row["trigger"]),
                severity=EscalationSeverity(row["severity"]),
                summary=row["summary"],
                raised_by=actor_from_json(row["raised_by"]),
                raised_at=_parse_ts(row["raised_at"]),
                suspension_applied=SuspensionState(row["suspension_applied"]),
                suspension_target=row["suspension_target"],
                status=EscalationStatus(row["status"]),
                stage_id=row["stage_id"],
                run_id=row["run_id"],
                escalation_hash=row["escalation_hash"],
            )
            for row in rows
        ]

    # -- test-facing forcing hooks -----------------------------------------
    #
    # These write fields the normal path derives, so recovery and the
    # consuming paths can be exercised against states a correct controller
    # would not produce. They bypass no integrity check downstream.

    def force_expected_tree_digest(self, intent_id: Id, digest: Hash) -> None:
        """Overwrite an intent's `expected_tree_digest`."""
        self.connection.execute(
            "UPDATE commit_intents SET expected_tree_digest=? WHERE intent_id=?",
            (digest, intent_id),
        )

    def force_mutation_path(self, intent_id: Id, path: str) -> None:
        """Rewrite the path of an intent's single mutation.

        Lets the apply-time protected-path guard be exercised against a record
        the proposing guard would never have created — which is the only way to
        find out whether the second guard is real or decorative.
        """
        row = self.connection.execute(
            "SELECT mutations FROM commit_intents WHERE intent_id=?", (intent_id,)
        ).fetchone()
        if row is None:
            raise KeyError(intent_id)
        raw = json.loads(row["mutations"])
        for entry in raw:
            entry["path"] = path
        self.connection.execute(
            "UPDATE commit_intents SET mutations=? WHERE intent_id=?",
            (canonical_json(raw).decode("utf-8"), intent_id),
        )

    def force_precondition_reviews(
        self, intent_id: Id, review_ids: Sequence[Id]
    ) -> None:
        """Write raw ids into an intent's review preconditions.

        The ids are stored with a kind naming the judgement record, which is
        exactly what the consuming path must refuse (`G-1`).
        """
        row = self.connection.execute(
            "SELECT preconditions FROM commit_intents WHERE intent_id=?", (intent_id,)
        ).fetchone()
        if row is None:
            raise KeyError(intent_id)
        raw = json.loads(row["preconditions"])
        raw["reviews"] = [
            {"kind": "Review", "id": review_id} for review_id in review_ids
        ]
        self.connection.execute(
            "UPDATE commit_intents SET preconditions=? WHERE intent_id=?",
            (canonical_json(raw).decode("utf-8"), intent_id),
        )
