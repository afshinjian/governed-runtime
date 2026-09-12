"""Domain entities and the enumerations used as state axes.

Design basis: domain-model.md §1 (shared value types), §7 (evidence-producing
entities), §8 (action entities), §9 (governance entities), §10 (enumerations).

Records are data only. Every state transition is owned by the controller; a
record never transitions itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Mapping, Optional, Sequence

from .errors import IntegrityViolation

# --- scalar aliases (domain-model §0.1) ----------------------------------

Id = str
Hash = str
CapabilityId = str
SemVer = str
Glob = str
PathStr = str
Ts = datetime
Ms = int
Unit = float
Ratio = float


# --- enumerations ---------------------------------------------------------


class ActorKind(str, Enum):
    HUMAN = "HUMAN"
    WORKER = "WORKER"
    RUNTIME = "RUNTIME"
    ADAPTER = "ADAPTER"
    EXTERNAL = "EXTERNAL"


class AuthMethod(str, Enum):
    NONE = "NONE"
    SESSION = "SESSION"
    SIGNATURE = "SIGNATURE"
    MTLS = "MTLS"
    DELEGATED = "DELEGATED"


class Encoding(str, Enum):
    IDENTITY = "IDENTITY"
    GZIP = "GZIP"
    ZSTD = "ZSTD"


class RetentionClass(str, Enum):
    PERMANENT = "PERMANENT"
    STANDARD = "STANDARD"
    EPHEMERAL = "EPHEMERAL"


class EpistemicClass(str, Enum):
    """evidence-model §2. Fixed at append; never upgraded afterwards."""

    CLAIM = "CLAIM"
    EVIDENCE = "EVIDENCE"
    DECISION = "DECISION"
    AUTHORITY = "AUTHORITY"


class ProjectLifecycle(str, Enum):
    """domain-model §10.1 — axis 1."""

    DRAFT = "DRAFT"
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    SETTLING = "SETTLING"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"
    ABANDONED = "ABANDONED"


class SuspensionState(str, Enum):
    """domain-model §10.3 — axis 3, orthogonal to lifecycle."""

    NONE = "NONE"
    SUSPENDED_BY_HUMAN = "SUSPENDED_BY_HUMAN"
    SUSPENDED_BY_POLICY = "SUSPENDED_BY_POLICY"
    SUSPENDED_BY_ESCALATION = "SUSPENDED_BY_ESCALATION"
    SUSPENDED_BY_BUDGET = "SUSPENDED_BY_BUDGET"
    SUSPENDED_BY_INTEGRITY = "SUSPENDED_BY_INTEGRITY"
    SUSPENDED_BY_DRIFT = "SUSPENDED_BY_DRIFT"
    QUIESCING = "QUIESCING"


class GovernanceMode(str, Enum):
    SUPERVISED = "SUPERVISED"
    AUTONOMOUS = "AUTONOMOUS"


class RunLifecycle(str, Enum):
    """transition-matrix §5. `CLOSED_*` are terminal."""

    ALLOCATED = "ALLOCATED"
    DISPATCHED = "DISPATCHED"
    WORKING = "WORKING"
    VALIDATING = "VALIDATING"
    REVIEWING = "REVIEWING"
    AWAITING_DECISION = "AWAITING_DECISION"
    CLOSED_SATISFIED = "CLOSED_SATISFIED"
    CLOSED_REJECTED = "CLOSED_REJECTED"
    CLOSED_ABORTED = "CLOSED_ABORTED"
    CLOSED_EXPIRED = "CLOSED_EXPIRED"


class WorkerRole(str, Enum):
    PLANNER = "PLANNER"
    IMPLEMENTER = "IMPLEMENTER"
    REVIEWER = "REVIEWER"
    INTEGRATOR = "INTEGRATOR"
    ANALYST = "ANALYST"


class InvocationStatus(str, Enum):
    """domain-model §8.1. Terminal from `COMPLETED` onwards."""

    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    REJECTED_BY_POLICY = "REJECTED_BY_POLICY"


class CommitIntentStatus(str, Enum):
    """domain-model §8.3, transitioned in transition-matrix §7.4."""

    PROPOSED = "PROPOSED"
    BLOCKED = "BLOCKED"
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class ReconciliationState(str, Enum):
    """Derived solely by `reconciliation.derive_reconciliation_state`.

    No other module may name a member of this enum; the derivation lives in
    exactly one place (transition-matrix §5.1).
    """

    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    ADOPTED = "ADOPTED"
    ORPHANED = "ORPHANED"
    UNRESOLVABLE = "UNRESOLVABLE"


class OutcomeStatus(str, Enum):
    """`InvocationOutcome.status` (worker_provider §2)."""

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    REFUSED = "REFUSED"


class TerminationReason(str, Enum):
    """domain-model §8.2 plus the provider's `REFUSAL` (worker_provider §2)."""

    COMPLETED = "COMPLETED"
    DEADLINE = "DEADLINE"
    BUDGET = "BUDGET"
    POLICY_STOP = "POLICY_STOP"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    HUMAN_STOP = "HUMAN_STOP"
    INTEGRITY = "INTEGRITY"
    REFUSAL = "REFUSAL"


class Attribution(str, Enum):
    """`DIRECT` under `worker.invoke`/`commit.apply`; `RECONCILED` under
    `recovery.reconcile` (domain-model §8.2, §8.4)."""

    DIRECT = "DIRECT"
    RECONCILED = "RECONCILED"


class Verification(str, Enum):
    """`CommitReceipt.verification` vs `expected_tree_digest` (§8.4)."""

    MATCHED = "MATCHED"
    DIVERGED = "DIVERGED"


class Verdict(str, Enum):
    """domain-model §7.3 / §7.3.1."""

    PASS = "PASS"
    PASS_WITH_FINDINGS = "PASS_WITH_FINDINGS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    ABSTAIN = "ABSTAIN"


class ReviewerKind(str, Enum):
    AUTOMATED = "AUTOMATED"
    PEER_WORKER = "PEER_WORKER"
    HUMAN = "HUMAN"


class Independence(str, Enum):
    """Computed from provenance (`WP-12`), never asserted by a reviewer."""

    INDEPENDENT = "INDEPENDENT"
    SHARED_CONTEXT = "SHARED_CONTEXT"
    SELF_REVIEW = "SELF_REVIEW"


class MutationOp(str, Enum):
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    RENAME = "RENAME"
    CHMOD = "CHMOD"


class VcsKind(str, Enum):
    DVCS = "DVCS"
    CVCS = "CVCS"
    NONE = "NONE"


class SnapshotTrigger(str, Enum):
    SCHEDULED = "SCHEDULED"
    PRE_RUN = "PRE_RUN"
    POST_RUN = "POST_RUN"
    PRE_COMMIT = "PRE_COMMIT"
    POST_COMMIT = "POST_COMMIT"
    DRIFT_CHECK = "DRIFT_CHECK"
    ON_DEMAND = "ON_DEMAND"


class Completeness(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    TRUNCATED = "TRUNCATED"
    FAILED = "FAILED"


class EscalationTrigger(str, Enum):
    """domain-model §9.B.1."""

    CONTRACT_AMBIGUITY = "CONTRACT_AMBIGUITY"
    CAPABILITY_DENIED = "CAPABILITY_DENIED"
    SCOPE_BREACH_ATTEMPT = "SCOPE_BREACH_ATTEMPT"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    REPEATED_FAILURE = "REPEATED_FAILURE"
    VALIDATION_UNAVAILABLE = "VALIDATION_UNAVAILABLE"
    NONDETERMINISM = "NONDETERMINISM"
    BLOCKER_FINDING = "BLOCKER_FINDING"
    DECLARED_OBSERVED_CONFLICT = "DECLARED_OBSERVED_CONFLICT"
    REALITY_DRIFT = "REALITY_DRIFT"
    ROADMAP_DIVERGED = "ROADMAP_DIVERGED"
    POLICY_CONFLICT = "POLICY_CONFLICT"
    INTEGRITY_VIOLATION = "INTEGRITY_VIOLATION"
    RECOVERY_AMBIGUITY = "RECOVERY_AMBIGUITY"


class EscalationSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EscalationStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"
    WITHDRAWN = "WITHDRAWN"


#: Statuses past which no further transition is defined (transition-matrix
#: §5.1 reads this through :func:`is_terminal_status`).
TERMINAL_INVOCATION_STATUSES: frozenset[InvocationStatus] = frozenset(
    {
        InvocationStatus.COMPLETED,
        InvocationStatus.FAILED,
        InvocationStatus.TIMED_OUT,
        InvocationStatus.CANCELLED,
        InvocationStatus.REJECTED_BY_POLICY,
    }
)

TERMINAL_INTENT_STATUSES: frozenset[CommitIntentStatus] = frozenset(
    {
        CommitIntentStatus.DENIED,
        CommitIntentStatus.APPLIED,
        CommitIntentStatus.FAILED,
        CommitIntentStatus.ROLLED_BACK,
    }
)


def is_terminal_status(status: InvocationStatus | CommitIntentStatus) -> bool:
    """True iff `status` is terminal for its entity.

    The reconciliation derivation (transition-matrix §5.1) reads status only
    through this predicate, so both entities share one notion of terminal.

    Both enumerations are `str` enums and some members share a value, so the
    entity is selected by type rather than by membership alone.
    """
    if isinstance(status, InvocationStatus):
        return status in TERMINAL_INVOCATION_STATUSES
    if isinstance(status, CommitIntentStatus):
        return status in TERMINAL_INTENT_STATUSES
    raise IntegrityViolation(f"not a governed status: {status!r}")


# --- shared value types (domain-model §1) ---------------------------------


@dataclass(frozen=True)
class Ref:
    """A typed reference: `Ref<Entity>` in the domain model.

    `kind` is the referent's entity name. A reference is not interchangeable
    with a bare id string, and a reference to one entity type never satisfies
    a field declared over another (`G-1`).
    """

    kind: str
    id: Id


@dataclass(frozen=True)
class ActorRef:
    """domain-model §1.1."""

    actor_kind: ActorKind
    actor_id: str
    auth_method: AuthMethod
    principal_key_id: Optional[str] = None
    on_behalf_of: Optional["ActorRef"] = None


@dataclass(frozen=True)
class ArtifactRef:
    """domain-model §1.2. `digest` is the artifact-store key."""

    digest: Hash
    media_type: str
    byte_len: int
    encoding: Encoding = Encoding.IDENTITY
    retention_class: RetentionClass = RetentionClass.STANDARD
    redacted: bool = False


@dataclass(frozen=True)
class Budget:
    """domain-model §1.3."""

    wall_clock_ms: Ms = 0
    worker_invocations: int = 0
    cost_units: Unit = 0.0
    validation_executions: int = 0
    commits: int = 0
    escalations: int = 0


@dataclass(frozen=True)
class BudgetUsage:
    """domain-model §1.3. Derived from receipts, never self-reported."""

    wall_clock_ms: Ms = 0
    worker_invocations: int = 0
    cost_units: Unit = 0.0
    validation_executions: int = 0
    commits: int = 0
    escalations: int = 0


@dataclass(frozen=True)
class Usage:
    """worker_provider §2. The authoritative copy is the kernel's (`WP-5`)."""

    input_units: Unit = 0.0
    output_units: Unit = 0.0
    tool_calls: int = 0
    cost_units: Unit = 0.0
    wall_clock_ms: Ms = 0


@dataclass(frozen=True)
class MutationProposal:
    """domain-model §1.5. A proposal; only an applied `CommitIntent` writes."""

    op: MutationOp
    path: PathStr
    rename_to: Optional[PathStr] = None
    before_digest: Optional[Hash] = None
    after_ref: Optional[ArtifactRef] = None
    mode: Optional[int] = None
    in_scope: bool = False


@dataclass(frozen=True)
class Claim:
    """domain-model §1.6. Non-authoritative; never gates a transition."""

    claim_id: Id
    subject: str
    assertion: str
    confidence: Ratio
    subject_ref: Optional[str] = None
    offered_evidence: Sequence[ArtifactRef] = ()
    corroboration: str = "UNCHECKED"


#: The only `Ref.kind` a review precondition may carry (`G-1`). The judgement
#: record's own kind never appears here: it is recorded and attested, never
#: consumed.
ATTESTATION_KIND = "ReviewAttestation"


@dataclass(frozen=True)
class CommitPreconditions:
    """`CommitIntent.preconditions` (domain-model §8.3).

    `reviews` holds `Ref<ReviewAttestation>` only. A `Ref` to any other entity,
    and a bare id string, are rejected at construction: a precondition is
    discharged by the kernel's measurement of a review, never by the reviewer's
    own verdict (`G-1`, evidence-model §4).
    """

    validations: tuple[Hash, ...] = ()
    reviews: tuple[Ref, ...] = ()
    decisions: tuple[Ref, ...] = ()

    def __post_init__(self) -> None:
        """Reject anything in `reviews` that is not a `ReviewAttestation` ref."""
        for entry in self.reviews:
            if not isinstance(entry, Ref):
                raise IntegrityViolation(
                    "a review precondition must be a typed reference, not "
                    f"{type(entry).__name__}: {entry!r}"
                )
            if entry.kind != ATTESTATION_KIND:
                raise IntegrityViolation(
                    "a review precondition is discharged by a kernel-minted "
                    f"{ATTESTATION_KIND}; got a reference to {entry.kind!r}"
                )


# --- action entities (domain-model §8) ------------------------------------


@dataclass
class WorkerInvocation:
    """domain-model §8.1.

    `idempotency_key` and `request_ref` are durable before the first provider
    call (`WP-15`); recovery reads them and never re-sends them (`WP-16`).
    """

    invocation_id: Id
    run_id: Id
    stage_id: Id
    provider_id: str
    provider_version: SemVer
    worker_role: WorkerRole
    prompt_bundle_ref: ArtifactRef
    request_ref: ArtifactRef
    request_digest: Hash
    context_digest: Hash
    idempotency_key: Hash
    controller_epoch: int
    status: InvocationStatus
    reconciliation_state: ReconciliationState
    execution_binding: Optional[str] = None
    context_refs: Sequence[ArtifactRef] = ()
    granted_capabilities: frozenset[CapabilityId] = frozenset()
    sandbox_profile_id: str = ""
    budget_allocated: Budget = field(default_factory=Budget)
    dispatched_at: Optional[Ts] = None
    deadline_at: Optional[Ts] = None
    receipt_id: Optional[Id] = None


@dataclass
class WorkerReceipt:
    """domain-model §8.2. EVIDENCE that a worker *said* something.

    `attribution = RECONCILED` carries the outcome `lookup` reported, including
    a `REFUSED` one mapped to `FAILED` — never a better outcome (`W-INV-4`).
    """

    receipt_id: Id
    invocation_id: Id
    ended_at: Ts
    duration_ms: Ms
    usage: Usage
    output_ref: ArtifactRef
    output_digest: Hash
    termination_reason: TerminationReason
    attribution: Attribution
    attested_by: ActorRef
    receipt_hash: Hash
    prev_event_hash: Hash
    claims: Sequence[Claim] = ()
    proposed_mutations: Sequence[MutationProposal] = ()
    requested_validations: Sequence[Id] = ()
    capability_violations_attempted: Sequence[Mapping[str, object]] = ()
    scope_breaches_attempted: Sequence[Mapping[str, object]] = ()


@dataclass
class CommitIntent:
    """domain-model §8.3.

    `operation_token` is minted at `PROPOSED` and written into `trailers`, so a
    revision that landed while the controller was down is findable (`CM-INV-2`).
    """

    intent_id: Id
    run_id: Id
    stage_id: Id
    vcs_kind: VcsKind
    base_revision_id: str
    target_ref: str
    expected_tree_digest: Hash
    message: str
    operation_token: str
    controller_epoch: int
    status: CommitIntentStatus
    reconciliation_state: ReconciliationState
    preconditions: Optional[CommitPreconditions] = None
    preconditions_met: bool = False
    mutations: Sequence[MutationProposal] = ()
    trailers: Mapping[str, str] = field(default_factory=dict)
    authorized_by: Optional[ActorRef] = None
    authorized_at: Optional[Ts] = None
    denial_reason: Optional[str] = None
    receipt_id: Optional[Id] = None


@dataclass
class CommitReceipt:
    """domain-model §8.4. `verification = DIVERGED` escalates (`CM-INV-1`)."""

    receipt_id: Id
    intent_id: Id
    revision_id: str
    actual_tree_digest: Hash
    verification: Verification
    diff_ref: ArtifactRef
    applied_at: Ts
    applied_by: ActorRef
    attribution: Attribution
    operation_token: str
    post_snapshot_id: Id
    receipt_hash: Hash
    prev_event_hash: Hash
    parent_revision_ids: Sequence[str] = ()
    files_changed: Sequence[Mapping[str, object]] = ()
    rollback_handle: Optional[str] = None


# --- evidence-producing entities (domain-model §7) -------------------------


@dataclass
class Review:
    """domain-model §7.3. A judgement — CLAIM class, never a precondition.

    It is recorded and it may be attested; it is never consumed as evidence.
    The consuming path reads `ReviewAttestation` (`G-1`).
    """

    review_id: Id
    run_id: Id
    stage_id: Id
    review_spec_id: str
    reviewer: ActorRef
    reviewer_kind: ReviewerKind
    independence: Independence
    inputs_digest: Hash
    input_snapshot_id: Id
    verdict: Verdict
    review_hash: Hash
    criteria_addressed: frozenset[str] = frozenset()
    findings: Sequence[Id] = ()
    evidence_refs: Sequence[ArtifactRef] = ()
    started_at: Optional[Ts] = None
    completed_at: Optional[Ts] = None


@dataclass
class ReviewAttestation:
    """domain-model §7.3.1 — EVIDENCE, minted under `review.attest` only.

    `verdict` is the aggregate over `review_ids`; `RVW(v)` matches this value,
    not a member review's verdict.
    """

    attestation_id: Id
    run_id: Id
    stage_id: Id
    review_spec_id: str
    review_ids: frozenset[Id]
    verdict: Verdict
    quorum_met: bool
    independence_satisfied: bool
    input_snapshot_id: Id
    contract_hash: Hash
    attested_by: ActorRef
    attested_at: Ts
    attestation_hash: Hash
    prev_event_hash: Hash
    criteria_addressed: frozenset[str] = frozenset()
    blocking_findings: frozenset[Id] = frozenset()


# --- governance entities (domain-model §9) --------------------------------


@dataclass
class AuditEvent:
    """domain-model §9.C. Append-only; the chain is per project."""

    event_id: Id
    project_id: Id
    seq: int
    prev_event_hash: Hash
    event_hash: Hash
    recorded_at: Ts
    epistemic_class: EpistemicClass
    event_type: str
    actor: ActorRef
    subject: Mapping[str, str]
    payload_ref: ArtifactRef
    payload_digest: Hash
    capability_used: Optional[CapabilityId] = None
    authority_ref: Optional[Id] = None
    causal_parent: Optional[Id] = None
    clock_skew_ms: int = 0
    signature: Optional[Hash] = None


@dataclass
class Escalation:
    """domain-model §9.B."""

    escalation_id: Id
    project_id: Id
    trigger: EscalationTrigger
    severity: EscalationSeverity
    summary: str
    raised_by: ActorRef
    raised_at: Ts
    suspension_applied: SuspensionState
    suspension_target: str
    status: EscalationStatus
    stage_id: Optional[Id] = None
    run_id: Optional[Id] = None
    evidence_refs: Sequence[ArtifactRef] = ()
    required_decision_kinds: frozenset[str] = frozenset()
    auto_resolvable: bool = False
    assigned_to: Optional[ActorRef] = None
    resolution_decision_id: Optional[Id] = None
    resolved_at: Optional[Ts] = None
    escalation_hash: Optional[Hash] = None


@dataclass
class RealitySnapshot:
    """domain-model §9.D. The only source of truth about the workspace."""

    snapshot_id: Id
    project_id: Id
    taken_at: Ts
    taken_by: ActorRef
    trigger: SnapshotTrigger
    completeness: Completeness
    tree_digest: Hash
    file_index_ref: ArtifactRef
    file_count: int
    byte_count: int
    snapshot_hash: Hash
    scope: Sequence[Glob] = ()
    vcs_state: Optional[Mapping[str, object]] = None
    toolchain_digest: Optional[Hash] = None
    env_digest: Optional[Hash] = None
    drift_vs: Optional[Id] = None


@dataclass
class Project:
    """domain-model §2.

    `controller_epoch` increments once per controller start, before any
    dispatch or apply (`P-INV-4`).
    """

    project_id: Id
    name: str
    slug: str
    schema_version: SemVer
    lifecycle: ProjectLifecycle
    suspension: SuspensionState
    governance_mode: GovernanceMode
    workspace_root: PathStr
    created_at: Ts
    updated_at: Ts
    created_by: ActorRef
    event_head: Hash
    event_seq: int
    controller_epoch: int
    policy_digest: Optional[Hash] = None
    capability_ceiling: frozenset[CapabilityId] = frozenset()
    budget: Budget = field(default_factory=Budget)
    budget_used: BudgetUsage = field(default_factory=BudgetUsage)
    suspension_ref: Optional[Id] = None
    roadmap_id: Optional[Id] = None
    snapshot_current: Optional[Id] = None


@dataclass
class StageRun:
    """domain-model §5. Carries the epoch it was allocated under."""

    run_id: Id
    project_id: Id
    stage_id: Id
    lifecycle: RunLifecycle
    suspension: SuspensionState
    controller_epoch: int
    started_at: Ts
    input_snapshot_id: Optional[Id] = None
    output_snapshot_id: Optional[Id] = None
    deadline_at: Optional[Ts] = None
    attempt: int = 1
