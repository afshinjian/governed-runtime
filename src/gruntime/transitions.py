"""The transition graph: every legal edge, and every permanently illegal one.

Design basis: transition-matrix.md §0 (orthogonality and the axis-3 gate),
§1 (column semantics and the policy vocabulary), §2–§7.6 (the legal rows),
§8 (composition), §9 (the ILLEGAL SECTION).

This module is **data**. It holds no behaviour beyond lookup: the evaluator and
the policy resolution live in `policy.py`, and the controller is the only thing
that acts on a resolution. Workers propose; nothing here decides.

Two properties the tables are built to make checkable:

* **One graph, two profiles.** `supervised` and `autonomous` are two columns of
  one row. There is no per-mode edge set, and no code path that adds or removes
  an edge because of `governance_mode`. A mode changes the *verdict* on an edge,
  never whether the edge exists.
* **Illegality is structural.** A §9 row is not a stricter precondition; it is a
  row that no capability, decision, or mode can satisfy. Its
  `required_capability` is `NONE_GRANTABLE` and both policy columns are `DENY`.

One matrix row is one rule here, including the rows written over several
`from_state`s or several `to_state`s. `row` carries the matrix coordinate, so a
resolution can be traced back to the line of design it came from.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Optional, Union

from .models import (
    ActorKind,
    CapabilityId,
    CommitIntentStatus,
    ContractStatus,
    DecisionKind,
    DecisionState,
    EscalationStatus,
    FindingStatus,
    GovernanceMode,
    InvocationStatus,
    ProjectLifecycle,
    RunLifecycle,
    StageLifecycle,
    SuspensionState,
    ValidationStatus,
)

#: `∅` in the matrix: the state before the entity exists.
ORIGIN: Optional[str] = None

#: `any` in a §9 row: matches every state on that axis, including `∅`.
ANY_STATE = "*"

#: §9's `required_capability` for a row no capability, decision, or mode can
#: authorize. It is never held, so a rule carrying it is never satisfiable.
NONE_GRANTABLE: CapabilityId = "NONE_GRANTABLE"


class Axis(str, Enum):
    """One state machine each. The three lifecycle axes plus the subordinates.

    `PROJECT`, `STAGE` and `SUSPENSION` are the orthogonal axes 1, 2 and 3
    (§0). The rest qualify a single entity and are never a lifecycle axis
    (domain-model §10.4). `OPERATION` is not a state machine at all: it carries
    the §9.3 authority and evidence prohibitions, which are operations rather
    than edges.
    """

    PROJECT = "PROJECT"
    STAGE = "STAGE"
    SUSPENSION = "SUSPENSION"
    RUN = "RUN"
    CONTRACT = "CONTRACT"
    VALIDATION = "VALIDATION"
    INVOCATION = "INVOCATION"
    FINDING = "FINDING"
    COMMIT_INTENT = "COMMIT_INTENT"
    DECISION = "DECISION"
    ESCALATION = "ESCALATION"
    OPERATION = "OPERATION"


class PolicyVerdict(str, Enum):
    """§1.1. `CONFIRM` is `DECIDE(APPROVE)` under its own name."""

    AUTO = "AUTO"
    NOTIFY = "NOTIFY"
    CONFIRM = "CONFIRM"
    DECIDE = "DECIDE"
    DENY = "DENY"


class Precondition(str, Enum):
    """The predicates the matrix's `preconditions` column is written over.

    Each member is one observable predicate over entity fields. The controller
    observes them; a proposal never asserts them (`G-6`: a claim is not a
    precondition). A row requires the conjunction of its members; where the
    matrix states a disjunction the disjunction is one member, named for it.
    """

    # §2 — project lifecycle
    CREATOR_IS_HUMAN = "project.creator_is_human"
    CREATOR_IS_NOT_HUMAN = "project.creator_is_not_human"
    WORKSPACE_ROOT_EXISTS = "project.workspace_root_exists"
    ROADMAP_PRESENT = "roadmap.present"
    ROADMAP_IN_SYNC = "roadmap.in_sync"
    DEPENDENCY_EDGES_ACYCLIC = "roadmap.dependency_edges_acyclic"
    ROADMAP_UNREADABLE_OR_DIVERGED = "roadmap.unreadable_or_diverged"
    READY_STAGE_EXISTS = "project.ready_stage_exists"
    CAPABILITY_CEILING_NON_EMPTY = "project.capability_ceiling_non_empty"
    BUDGET_NON_ZERO = "project.budget_non_zero"
    ALL_STAGES_TERMINAL = "project.all_stages_terminal"
    NO_NON_TERMINAL_RUN = "project.no_non_terminal_run"
    STAGE_DEMOTED_OR_ROADMAP_REVISED = "project.stage_demoted_or_roadmap_revised"
    ALL_STAGES_SATISFIED_OR_RISK_ACCEPTED = "project.all_stages_satisfied_or_risk_accepted"
    NO_OPEN_ESCALATION = "project.no_open_escalation"
    NO_BLOCKING_FINDING = "project.no_blocking_finding"
    ROADMAP_REVISED_OR_STAGE_STALE = "project.roadmap_revised_or_stage_stale"
    AUDIT_CHAIN_VERIFIES = "audit.chain_verifies"
    EPHEMERAL_ARTIFACTS_COLLECTED = "artifacts.ephemeral_collected"

    # §3 — stage lifecycle
    STAGE_IN_ROADMAP_ORDER = "stage.in_roadmap_order"
    PROJECT_ADMITS_MATERIALIZATION = "stage.project_admits_materialization"
    DEPENDENCIES_SATISFIED = "stage.dependencies_satisfied"
    DEPENDENCY_LEFT_SATISFIED = "stage.dependency_left_satisfied"
    CONTRACT_ACTIVE_FOR_STAGE = "stage.contract_active"
    RUN_DISPATCHED = "stage.run_dispatched"
    ATTEMPTS_REMAIN = "stage.attempts_remain"
    BUDGET_REMAINS = "stage.budget_remains"
    CONTRACT_REVOKED_OR_EXPIRED = "stage.contract_revoked_or_expired"
    NO_RUN_STARTED = "stage.no_run_started"
    WORKER_RECEIPT_PRESENT = "run.worker_receipt_present"
    MECHANICAL_OPERATIONS_EXIST = "stage.mechanical_operations_exist"
    RUN_CLOSED_ABORTED = "stage.run_closed_aborted"
    CONTRACT_STILL_ACTIVE = "stage.contract_still_active"
    BLOCKING_ESCALATION_BOUND = "stage.blocking_escalation_bound"
    MECHANICAL_CRITERIA_MET = "stage.mechanical_criteria_met"
    MECHANICAL_CRITERION_UNMET = "stage.mechanical_criterion_unmet"
    VALIDATION_EXHAUSTED_OR_UNAVAILABLE = "stage.validation_exhausted_or_unavailable"
    OBSERVED_SATISFACTION_SATISFIED = "stage.observed_satisfaction_satisfied"
    OBSERVED_SATISFACTION_NOT_SATISFIED = "stage.observed_satisfaction_not_satisfied"
    DECLARED_STATUS_AS_BASIS = "stage.declared_status_as_basis"
    REVIEW_SPECS_MET = "stage.review_specs_met"
    MUTATIONS_LANDED_VIA_COMMIT = "stage.mutations_landed_via_commit"
    BLOCKING_FINDING_PRESENT = "stage.blocking_finding_present"
    RECEIPT_INVALIDATED = "stage.receipt_invalidated"
    WAIVABLE_BLOCKER_OR_INCONCLUSIVE_REVIEW = "stage.waivable_blocker_or_inconclusive_review"
    BLOCKING_FINDINGS_RESOLVED = "stage.blocking_findings_resolved"
    SHORTFALLS_WAIVED = "stage.shortfalls_waived"
    REWORK_DIRECTED = "stage.rework_directed"
    REJECTION_RECORDED = "stage.rejection_recorded"
    ABANDONMENT_RECORDED = "stage.abandonment_recorded"
    SATISFACTION_STALE_OR_CONTRADICTED = "stage.satisfaction_stale_or_contradicted"
    NEW_CONTRACT_DRAFTED = "stage.new_contract_drafted"
    OVERRIDE_PERMITS_RETRY = "stage.override_permits_retry"

    # §4 — suspension
    SUSPENSION_REQUESTED = "suspension.requested"
    OPERATIONS_IN_FLIGHT = "suspension.operations_in_flight"
    NO_OPERATIONS_IN_FLIGHT = "suspension.no_operations_in_flight"
    POLICY_RULE_MATCHED = "suspension.policy_rule_matched"
    NON_AUTO_ESCALATION_TARGETS_HOLDER = "suspension.non_auto_escalation_targets_holder"
    BUDGET_CEILING_REACHED = "suspension.budget_ceiling_reached"
    UNATTRIBUTED_DRIFT = "suspension.unattributed_drift"
    INTEGRITY_VIOLATION_DETECTED = "suspension.integrity_violation_detected"
    SUSPENSION_REQUEST_WITHDRAWN = "suspension.request_withdrawn"
    RESUME_DECISION_RECORDED = "suspension.resume_decision_recorded"
    POLICY_RULE_NO_LONGER_MATCHES = "suspension.policy_rule_no_longer_matches"
    ESCALATIONS_SETTLED = "suspension.escalations_settled"
    ALL_RESOLUTIONS_AUTO_RESOLVABLE = "suspension.all_resolutions_auto_resolvable"
    BUDGET_EXTENDED = "suspension.budget_extended"
    DRIFT_CLEARED_OR_ACCEPTED = "suspension.drift_cleared_or_accepted"
    CHAIN_REVERIFIED = "suspension.chain_reverified"
    HUMAN_SUSPENDS_OVER_EXISTING = "suspension.human_suspends_over_existing"

    # §5 — run lifecycle
    ACTIVATION_VALID = "run.activation_valid"
    RUN_SUSPENSION_NONE = "run.suspension_none"
    PROVIDER_ACCEPTED_INVOCATION = "run.provider_accepted_invocation"
    GRANTS_WITHIN_EFFECTIVE = "run.grants_within_effective"
    ACTIVATION_REVOKED_BEFORE_DISPATCH = "run.activation_revoked_before_dispatch"
    PROVIDER_REPORTED_START = "run.provider_reported_start"
    PROVIDER_REJECTED = "run.provider_rejected"
    VALIDATION_AUTHORIZED = "run.validation_authorized"
    DEADLINE_PASSED = "run.deadline_passed"
    BUDGET_OR_STOP_OR_SCOPE_BREACH = "run.budget_or_stop_or_scope_breach"
    MANDATORY_REVIEW_SPECS_EXIST = "run.mandatory_review_specs_exist"
    MANDATORY_VALIDATION_FAILED = "run.mandatory_validation_failed"
    STAGE_SATISFIED = "run.stage_satisfied"
    COMMIT_INTENTS_SETTLED = "run.commit_intents_settled"
    OPERATION_UNRESOLVABLE = "run.operation_unresolvable"

    # §6 — contract status
    SCHEMA_VALID = "contract.schema_valid"
    CONTRACT_HASH_RECOMPUTES = "contract.hash_recomputes"
    NO_OTHER_ACTIVE_CONTRACT = "contract.no_other_active"
    REQUEST_WITHIN_CEILING = "contract.request_within_ceiling"
    BUDGET_WITHIN_PROJECT_REMAINING = "contract.budget_within_project_remaining"
    AUTHOR_WITHDREW = "contract.author_withdrew"
    SUCCESSOR_ACTIVE = "contract.successor_active"
    REVOCATION_TRIGGERED = "contract.revocation_triggered"
    REVOCATION_BY_BREACH_OR_INTEGRITY = "contract.revocation_by_breach_or_integrity"
    ACTIVATION_EXPIRED = "contract.activation_expired"

    # §7.1 — validation operation
    SPEC_IN_PINNED_CONTRACT = "validation.spec_in_pinned_contract"
    COMMAND_MATCHES_SPEC = "validation.command_matches_spec"
    CWD_IN_SCOPE = "validation.cwd_in_scope"
    NETWORK_PERMITTED = "validation.network_permitted"
    COMMAND_ALTERED_OR_UNAUTHORIZED = "validation.command_altered_or_unauthorized"
    SANDBOX_ALLOCATED = "validation.sandbox_allocated"
    PROCESS_EXITED_IN_TIME = "validation.process_exited_in_time"
    TIMEOUT_ELAPSED = "validation.timeout_elapsed"
    SANDBOX_OR_TOOLCHAIN_ERROR = "validation.sandbox_or_toolchain_error"
    HOLDER_QUIESCING_OR_RUN_CLOSED = "validation.holder_quiescing_or_run_closed"

    # §7.2 — worker invocation
    RUN_ALLOCATED_OR_WORKING = "invocation.run_allocated_or_working"
    BUDGET_HEADROOM = "invocation.budget_headroom"
    BARRIER_CLEAR = "invocation.barrier_clear"
    FIRST_INVOCATION_OF_RUN = "invocation.first_of_run"
    CAPABILITIES_EXCEEDED_OR_PROVIDER_UNREGISTERED = "invocation.capabilities_exceeded_or_provider_unregistered"
    PROMPT_BUNDLE_STORED = "invocation.prompt_bundle_stored"
    PROVIDER_RETURNED_OUTPUT = "invocation.provider_returned_output"
    PROVIDER_ERROR = "invocation.provider_error"
    SUSPENSION_OR_BUDGET_OR_HUMAN_STOP = "invocation.suspension_or_budget_or_human_stop"
    OLD_EPOCH = "invocation.old_epoch"
    LOOKUP_FINISHED = "invocation.lookup_finished"
    LOOKUP_ABSENT = "invocation.lookup_absent"

    # §7.3 — finding
    RAISED_WITHIN_ATTESTED_REVIEW = "finding.raised_within_attested_review"
    REMEDIATION_ACCEPTED = "finding.remediation_accepted"
    DEFECT_GONE = "finding.defect_gone"
    CRITERION_WAIVABLE = "finding.criterion_waivable"
    CONTESTED_WITH_COUNTER_EVIDENCE = "finding.contested_with_counter_evidence"
    COUNTER_EVIDENCE_ACCEPTED = "finding.counter_evidence_accepted"
    INDEPENDENT_REVIEW_CLEARED = "finding.independent_review_cleared"
    COUNTER_EVIDENCE_REJECTED = "finding.counter_evidence_rejected"
    WAIVER_EXPIRED_OR_REVOKED = "finding.waiver_expired_or_revoked"

    # §7.4 — commit intent
    MUTATIONS_IN_SCOPE = "commit.mutations_in_scope"
    BASE_MATCHES_SNAPSHOT = "commit.base_matches_snapshot"
    TOKEN_MINTED_AND_CARRIED = "commit.token_minted_and_carried"
    INTENT_PRECONDITION_UNMET = "commit.intent_precondition_unmet"
    INTENT_PRECONDITIONS_NOW_MET = "commit.intent_preconditions_now_met"
    INTENT_PRECONDITIONS_MET = "commit.intent_preconditions_met"
    WORKSPACE_UNCHANGED = "commit.workspace_unchanged"
    SCOPE_BREACH_OR_PROHIBITION = "commit.scope_breach_or_prohibition"
    WRITE_LOCK_HELD = "commit.write_lock_held"
    TOKEN_DURABLE_BEFORE_MUTATION = "commit.token_durable_before_mutation"
    APPLICATION_SUCCEEDED = "commit.application_succeeded"
    TREE_DIGEST_MATCHES = "commit.tree_digest_matches"
    APPLICATION_FAILED_OR_DIVERGED = "commit.application_failed_or_diverged"
    ROLLBACK_POLICY_INVOKED = "commit.rollback_policy_invoked"
    PARTIAL_APPLICATION_REVERTED = "commit.partial_application_reverted"
    SCAN_FOUND_MATCHING_REVISION = "commit.scan_found_matching_revision"
    SCAN_FOUND_NO_REVISION = "commit.scan_found_no_revision"
    SCAN_FOUND_DIVERGENT_REVISION = "commit.scan_found_divergent_revision"
    NEVER_REACHED_APPLYING = "commit.never_reached_applying"

    # §7.5 — human decision
    RECORDED_PER_HD_INV = "decision.recorded_per_hd_inv"
    SNAPSHOT_BINDING_CURRENT = "decision.snapshot_binding_current"
    DISCHARGED_ITS_TRANSITION = "decision.discharged_its_transition"
    NEWER_SNAPSHOT_SUPERSEDES = "decision.newer_snapshot_supersedes"
    EXPIRED_OR_SCOPE_LEFT = "decision.expired_or_scope_left"
    HD_INV_1_VIOLATED = "decision.hd_inv_1_violated"

    # §7.6 — escalation
    TRIGGER_FIRED = "escalation.trigger_fired"
    ASSIGNEE_ACCEPTED = "escalation.assignee_accepted"
    DECISION_OR_CONDITION_CLEARED = "escalation.decision_or_condition_cleared"
    AUTO_RESOLVABLE = "escalation.auto_resolvable"
    NO_RESOLUTION_IN_WINDOW = "escalation.no_resolution_in_window"
    RAISER_RETRACTED = "escalation.raiser_retracted"


class Evidence(str, Enum):
    """§1.2's shorthand, plus the record classes the rows name in full.

    `RVW_PASS` covers both `RVW(PASS)` and `RVW(PASS_WITH_FINDINGS)`: §2 and §3
    accept either wherever they accept one. `DEC` is the `DEC(K)` of the row's
    own verdict — the kind lives on the policy, not on a second token.
    """

    SNAP = "SNAP"
    VR_PASS = "VR(pass)"
    VR_ANY = "VR(any)"
    RVW_PASS = "RVW(pass)"
    RVW_FAIL = "RVW(fail)"
    RVW_ANY = "RVW(any)"
    WR = "WR"
    CR = "CR"
    DEC = "DEC"
    ACT = "ACT"
    ESC_OPEN = "ESC(OPEN)"
    CONTRACT_HASH = "contract_hash verified"
    ACTIVATION_RECORD = "ContractActivationRecord"
    SUCCESSOR_ACTIVATION = "successor ContractActivationRecord"
    POLICY_RECORD = "policy evaluation record"
    USAGE_RECORD = "usage record"
    TERMINAL_RECEIPT = "terminal receipt per drained operation"
    REVOCATION_RECORD = "revocation record"
    TRIGGERING_RECORD = "triggering record"
    CHAIN_VERIFICATION = "chain verification record"
    COUNTER_EVIDENCE = "counter ArtifactRef set"
    AUDIT_EVENT = "the transition's own AuditEvent"
    REQUEST_REF = "request_ref persisted with its idempotency_key"
    PROMPT_BUNDLE_REF = "prompt_bundle_ref persisted"
    VALIDATION_RECEIPT = "ValidationReceipt"


#: One entry of a row's `required_evidence`: a token, or a set of tokens of
#: which any one satisfies the entry (the matrix's "X, or Y").
EvidenceRequirement = Union[Evidence, frozenset]


def any_of(*evidence: Evidence) -> frozenset:
    """An evidence entry the matrix writes as a disjunction."""
    return frozenset(evidence)


class Operation(str, Enum):
    """The §9.3 authority and evidence operations.

    These are not edges. Each is an act that no capability, decision, or mode
    authorizes, for the actor kinds the row names.
    """

    MINT_VALIDATION_RECEIPT = "mint ValidationReceipt"
    MINT_COMMIT_RECEIPT = "mint CommitReceipt"
    CREATE_REALITY_SNAPSHOT = "create RealitySnapshot"
    CREATE_HUMAN_DECISION = "create HumanDecision"
    CREATE_HUMAN_DECISION_UNAUTHENTICATED = "create HumanDecision with auth_method in {NONE, DELEGATED}"
    CREATE_HUMAN_DECISION_WITHOUT_EVIDENCE = "create HumanDecision with empty evidence_shown"
    REPLAY_CONSUMED_DECISION_NONCE = "replay a consumed HumanDecision nonce"
    MUTATE_ACTIVE_CONTRACT = "mutate a field of an ACTIVE StageContract"
    WIDEN_EFFECTIVE_CAPABILITIES = "widen StageRun.effective_capabilities in place"
    GRANT_OUTSIDE_CEILING = "grant a capability outside project.capability_ceiling"
    DELEGATE_UNHELD_CAPABILITY = "delegate a capability a worker does not hold"
    REWRITE_AUDIT_EVENT = "rewrite or delete an AuditEvent"
    WRITE_OBSERVED_SATISFACTION = "write observed_satisfaction directly"
    GATE_ON_DECLARED_STATUS = "write declared_status and have it gate a transition"
    EXECUTE_DIVERGENT_COMMAND_SPEC = "execute a CommandSpec whose argv differs from the contract's ValidationSpec"
    WRITE_OUTSIDE_SCOPE = "write outside scope_include minus scope_exclude"
    SELF_REVIEW_FOR_INDEPENDENT_SPEC = "satisfy an INDEPENDENT ReviewSpec with independence = SELF_REVIEW"
    WAIVE_NON_WAIVABLE_CRITERION = "waive a criterion with waivable = false"
    RESOLVE_ESCALATION_WITHOUT_DECISION = "resolve an Escalation with auto_resolvable = false without a HumanDecision"
    SET_AUTONOMOUS_WITHOUT_DECISION = "set governance_mode = AUTONOMOUS without a HumanDecision"
    APPLY_INTENT_WITH_STALE_BASE = "apply a CommitIntent whose base_revision_id no longer matches reality"
    SATISFY_FROM_INCOMPLETE_SNAPSHOT = "mark a stage SATISFIED from a snapshot with completeness != COMPLETE"
    GRANT_WITHOUT_ADMISSIBLE_GRANTOR = "grant a capability no admissible principal produced a grant record for"
    ACTIVATE_WITHOUT_GRANT_BASIS = "write a ContractActivationRecord whose capability_grant_basis does not cover every granted capability"
    DISPATCH_UNDER_BARRIER = "dispatch a WorkerInvocation, or advance a CommitIntent past AUTHORIZED under commit.apply, for a run holding an unreconciled operation"
    REPLACE_UNRECONCILED_INVOCATION = "replace an unreconciled WorkerInvocation with a new idempotency_key, rebuilt context, or a new attempt"
    RESUBMIT_REQUEST_REF = "resubmit a persisted request_ref to invoke as a means of reconciling an invocation"
    DISPATCH_WITHOUT_LOOKUP = "dispatch a governed mutation to a provider that does not implement lookup"
    MUTATE_BEFORE_TOKEN_DURABLE = "mutate the repository before the intent's operation_token is durable"
    REAPPLY_UNRECONCILED_INTENT = "re-apply a CommitIntent in APPLYING without reconciling it first"
    CITE_INVALID_DECISION = "cite a HumanDecision with decision_state != VALID as DEC(K) or CONFIRM"
    MINT_REVIEW_ATTESTATION = "mint a ReviewAttestation"
    CITE_REVIEW_AS_EVIDENCE = "cite a Review directly as required_evidence"


#: A §9.3 row whose `actor` column reads `any`.
ANY_ACTOR: frozenset[ActorKind] = frozenset(ActorKind)


@dataclass(frozen=True)
class Policy:
    """A §1.1 verdict, possibly conditional on an observed predicate.

    Several rows carry a conditional verdict — "`AUTO` when triggered by breach
    or integrity, else `CONFIRM`". `when` names the predicate that selects
    `verdict`; `otherwise` is the verdict when it does not hold. `settle`
    collapses the conditional against observed facts.
    """

    verdict: PolicyVerdict
    decision_kind: Optional[DecisionKind] = None
    when: Optional[Precondition] = None
    otherwise: Optional["Policy"] = None

    def settle(self, facts: Iterable[Precondition]) -> "Policy":
        """The unconditional verdict these facts select."""
        if self.when is None:
            return self
        if self.when in set(facts):
            return Policy(self.verdict, self.decision_kind)
        assert self.otherwise is not None, "a conditional policy needs a fallback"
        return self.otherwise.settle(facts)

    @property
    def required_decision(self) -> Optional[DecisionKind]:
        """The `K` a `HumanDecision` must carry to discharge this verdict.

        `CONFIRM` is `DECIDE(APPROVE)` (§1.1). A `DECIDE` with no
        `decision_kind` is §7.6's `DECIDE(K)` over an escalation's own
        `required_decision_kinds`, which are not known until the escalation is.
        """
        if self.verdict is PolicyVerdict.CONFIRM:
            return DecisionKind.APPROVE
        if self.verdict is PolicyVerdict.DECIDE:
            return self.decision_kind
        return None


AUTO = Policy(PolicyVerdict.AUTO)
NOTIFY = Policy(PolicyVerdict.NOTIFY)
CONFIRM = Policy(PolicyVerdict.CONFIRM)
DENY = Policy(PolicyVerdict.DENY)

#: §7.6: `DECIDE(K)` for `K ∈ escalation.required_decision_kinds`.
DECIDE_PER_ESCALATION = Policy(PolicyVerdict.DECIDE)


def DECIDE(kind: DecisionKind) -> Policy:
    """`DECIDE(K)`: a `HumanDecision{kind: K}` recorded before the transition."""
    return Policy(PolicyVerdict.DECIDE, decision_kind=kind)


def WHEN(predicate: Precondition, then: Policy, otherwise: Policy) -> Policy:
    """A row whose verdict in one mode depends on an observed predicate."""
    return Policy(then.verdict, then.decision_kind, when=predicate, otherwise=otherwise)


def normalize_state(value) -> Optional[str]:
    """Normalize a state to its plain string.

    The axis enumerations are `str` enums and several share a value —
    `ABANDONED` is both a `ProjectLifecycle` and a `StageLifecycle`. The axis in
    the key is what tells them apart, so the state itself is carried as a bare
    string and never as a member of one particular enumeration.
    """
    if value is None:
        return None
    return value.value if isinstance(value, Enum) else str(value)


def _states(value) -> tuple:
    if isinstance(value, (tuple, list, set, frozenset)):
        return tuple(normalize_state(item) for item in value)
    return (normalize_state(value),)


@dataclass(frozen=True)
class TransitionRule:
    """One legal row of §2–§7.6.

    A row written over several `from_state`s or `to_state`s is one rule: the
    matrix states it once, and the engine keeps it once. `self_edge` marks
    §7.4's last row, whose `to_state` column reads *status unchanged* — its
    edges are `(s, s)`, not the cross product.
    """

    axis: Axis
    from_states: tuple
    to_states: tuple
    preconditions: tuple[Precondition, ...]
    required_evidence: tuple[EvidenceRequirement, ...]
    required_capability: CapabilityId
    supervised: Policy
    autonomous: Policy
    row: str
    self_edge: bool = False

    def policy(self, mode: GovernanceMode) -> Policy:
        """This row's verdict column for `mode`. The row itself is shared."""
        return self.supervised if mode is GovernanceMode.SUPERVISED else self.autonomous

    def edges(self) -> tuple:
        """Every `(axis, from, to)` this row carries."""
        if self.self_edge:
            return tuple(
                (self.axis, state, state) for state in self.from_states
            )
        return tuple(
            (self.axis, from_state, to_state)
            for from_state in self.from_states
            for to_state in self.to_states
        )


@dataclass(frozen=True)
class IllegalTransition:
    """One §9.1 or §9.2 row: an edge no capability or mode can authorize.

    `when` is non-empty for the rows the matrix qualifies with a precondition —
    "`any → SATISFIED` where `declared_status` is used as the basis". Such a row
    matches only when every named predicate is observed; without that guard the
    row would delete the legal edge it shadows.
    """

    axis: Axis
    from_states: tuple
    to_states: tuple
    illegal_because: str
    row: str
    when: tuple[Precondition, ...] = ()
    required_capability: CapabilityId = NONE_GRANTABLE
    supervised: Policy = DENY
    autonomous: Policy = DENY

    def matches(
        self,
        axis: Axis,
        from_state: Optional[str],
        to_state: Optional[str],
        facts: Iterable[Precondition] = (),
    ) -> bool:
        if axis is not self.axis:
            return False
        if ANY_STATE not in self.from_states and normalize_state(from_state) not in self.from_states:
            return False
        if ANY_STATE not in self.to_states and normalize_state(to_state) not in self.to_states:
            return False
        return set(self.when).issubset(set(facts))


@dataclass(frozen=True)
class IllegalOperation:
    """One §9.3 row: an operation forbidden to the actor kinds it names."""

    operation: Operation
    actors: frozenset
    illegal_because: str
    row: str
    required_capability: CapabilityId = NONE_GRANTABLE
    supervised: Policy = DENY
    autonomous: Policy = DENY


@dataclass(frozen=True)
class SuspensionGate:
    """One row of the §0.1 axis-3 gate.

    `lifecycle_targets` is the set of axis-1/axis-2 states this suspension
    still permits a transition *to*; `ANY_STATE` means the gate is open.
    """

    new_invocations: bool
    new_validations: bool
    new_commits: bool
    lifecycle_targets: frozenset


def _rule(
    axis: Axis,
    from_state,
    to_state,
    *,
    row: str,
    cap: CapabilityId,
    sup: Policy,
    auto: Policy,
    pre: Iterable[Precondition] = (),
    ev: Iterable[EvidenceRequirement] = (),
    self_edge: bool = False,
) -> TransitionRule:
    return TransitionRule(
        axis=axis,
        from_states=_states(from_state),
        to_states=_states(to_state),
        preconditions=tuple(pre),
        required_evidence=tuple(ev),
        required_capability=cap,
        supervised=sup,
        autonomous=auto,
        row=row,
        self_edge=self_edge,
    )


_P = Precondition
_E = Evidence
_S = StageLifecycle
_L = ProjectLifecycle
_U = SuspensionState
_R = RunLifecycle
_C = ContractStatus
_V = ValidationStatus
_I = InvocationStatus
_F = FindingStatus
_M = CommitIntentStatus
_D = DecisionState
_X = EscalationStatus
_K = DecisionKind


# --- §2 — axis 1, project lifecycle ---------------------------------------

_PROJECT_RULES = (
    _rule(
        Axis.PROJECT, ORIGIN, _L.DRAFT, row="2-1",
        pre=(_P.CREATOR_IS_HUMAN, _P.WORKSPACE_ROOT_EXISTS),
        ev=(_E.SNAP,), cap="project.create", sup=AUTO, auto=DENY,
    ),
    _rule(
        Axis.PROJECT, _L.DRAFT, _L.PLANNING, row="2-2",
        pre=(_P.ROADMAP_PRESENT, _P.ROADMAP_IN_SYNC, _P.DEPENDENCY_EDGES_ACYCLIC),
        ev=(_E.SNAP,), cap="roadmap.import", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.PROJECT, _L.DRAFT, _L.ABANDONED, row="2-3",
        cap="project.abandon", sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.PROJECT, _L.PLANNING, _L.DRAFT, row="2-4",
        pre=(_P.ROADMAP_UNREADABLE_OR_DIVERGED,),
        cap="roadmap.import", sup=NOTIFY, auto=NOTIFY,
    ),
    _rule(
        Axis.PROJECT, _L.PLANNING, _L.ACTIVE, row="2-5",
        pre=(_P.READY_STAGE_EXISTS, _P.CAPABILITY_CEILING_NON_EMPTY, _P.BUDGET_NON_ZERO),
        ev=(_E.SNAP,), cap="project.lifecycle.advance", sup=CONFIRM, auto=AUTO,
    ),
    _rule(
        Axis.PROJECT, _L.PLANNING, _L.ABANDONED, row="2-6",
        cap="project.abandon", sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.PROJECT, _L.ACTIVE, _L.SETTLING, row="2-7",
        pre=(_P.ALL_STAGES_TERMINAL, _P.NO_NON_TERMINAL_RUN),
        ev=(_E.SNAP,), cap="project.lifecycle.advance", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.PROJECT, _L.ACTIVE, _L.ABANDONED, row="2-8",
        cap="project.abandon", sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.PROJECT, _L.SETTLING, _L.ACTIVE, row="2-9",
        pre=(_P.STAGE_DEMOTED_OR_ROADMAP_REVISED,),
        ev=(_E.SNAP,), cap="project.lifecycle.advance", sup=NOTIFY, auto=AUTO,
    ),
    _rule(
        Axis.PROJECT, _L.SETTLING, _L.COMPLETED, row="2-10",
        pre=(
            _P.ALL_STAGES_SATISFIED_OR_RISK_ACCEPTED,
            _P.NO_OPEN_ESCALATION,
            _P.NO_BLOCKING_FINDING,
        ),
        ev=(_E.SNAP, _E.VR_PASS, _E.RVW_PASS),
        cap="project.lifecycle.advance", sup=DECIDE(_K.APPROVE), auto=NOTIFY,
    ),
    _rule(
        Axis.PROJECT, _L.SETTLING, _L.ABANDONED, row="2-11",
        cap="project.abandon", sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.PROJECT, _L.COMPLETED, _L.ACTIVE, row="2-12",
        pre=(_P.ROADMAP_REVISED_OR_STAGE_STALE,),
        ev=(_E.SNAP,), cap="project.lifecycle.advance",
        sup=DECIDE(_K.APPROVE), auto=NOTIFY,
    ),
    _rule(
        Axis.PROJECT, _L.COMPLETED, _L.ARCHIVED, row="2-13",
        pre=(_P.AUDIT_CHAIN_VERIFIES, _P.EPHEMERAL_ARTIFACTS_COLLECTED),
        ev=(_E.SNAP,), cap="project.archive",
        sup=DECIDE(_K.APPROVE), auto=DECIDE(_K.APPROVE),
    ),
    _rule(
        Axis.PROJECT, _L.ABANDONED, _L.ARCHIVED, row="2-14",
        pre=(_P.AUDIT_CHAIN_VERIFIES,),
        cap="project.archive", sup=AUTO, auto=AUTO,
    ),
)


# --- §3 — axis 2, stage lifecycle -----------------------------------------

_STAGE_RULES = (
    _rule(
        Axis.STAGE, ORIGIN, _S.PENDING, row="3-1",
        pre=(_P.STAGE_IN_ROADMAP_ORDER, _P.PROJECT_ADMITS_MATERIALIZATION),
        cap="roadmap.import", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.PENDING, _S.READY, row="3-2",
        pre=(_P.DEPENDENCIES_SATISFIED, _P.PROJECT_ADMITS_MATERIALIZATION),
        ev=(_E.SNAP,), cap="stage.lifecycle.advance", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.PENDING, _S.ABANDONED, row="3-3",
        cap="stage.abandon", sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.STAGE, _S.READY, _S.PENDING, row="3-4",
        pre=(_P.DEPENDENCY_LEFT_SATISFIED,),
        ev=(_E.SNAP,), cap="stage.lifecycle.advance", sup=NOTIFY, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.READY, _S.CONTRACTED, row="3-5",
        pre=(_P.CONTRACT_ACTIVE_FOR_STAGE,),
        ev=(_E.CONTRACT_HASH,), cap="contract.activate", sup=CONFIRM, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.READY, _S.ABANDONED, row="3-6",
        cap="stage.abandon", sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.STAGE, _S.CONTRACTED, _S.RUNNING, row="3-7",
        pre=(_P.RUN_DISPATCHED, _P.ATTEMPTS_REMAIN, _P.BUDGET_REMAINS),
        ev=(_E.ACT, _E.SNAP), cap="run.start", sup=CONFIRM, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.CONTRACTED, _S.READY, row="3-8",
        pre=(_P.CONTRACT_REVOKED_OR_EXPIRED, _P.NO_RUN_STARTED),
        cap="contract.revoke", sup=NOTIFY, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.CONTRACTED, _S.ABANDONED, row="3-9",
        cap="stage.abandon", sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.STAGE, _S.RUNNING, _S.AWAITING_VALIDATION, row="3-10",
        pre=(_P.WORKER_RECEIPT_PRESENT, _P.MECHANICAL_OPERATIONS_EXIST),
        ev=(_E.WR,), cap="stage.lifecycle.advance", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.RUNNING, _S.CONTRACTED, row="3-11",
        pre=(_P.RUN_CLOSED_ABORTED, _P.CONTRACT_STILL_ACTIVE, _P.ATTEMPTS_REMAIN),
        ev=(_E.WR,), cap="run.abort", sup=NOTIFY, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.RUNNING, _S.AWAITING_DECISION, row="3-12",
        pre=(_P.BLOCKING_ESCALATION_BOUND,),
        ev=(_E.ESC_OPEN,), cap="escalation.raise", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.RUNNING, _S.ABANDONED, row="3-13",
        cap="stage.abandon", sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_VALIDATION, _S.AWAITING_REVIEW, row="3-14",
        pre=(_P.MECHANICAL_CRITERIA_MET,),
        ev=(_E.VR_PASS,), cap="stage.lifecycle.advance", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_VALIDATION, _S.RUNNING, row="3-15",
        pre=(_P.MECHANICAL_CRITERION_UNMET, _P.ATTEMPTS_REMAIN, _P.BUDGET_REMAINS),
        ev=(_E.VR_ANY,), cap="run.start", sup=NOTIFY, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_VALIDATION, _S.AWAITING_DECISION, row="3-16",
        pre=(_P.VALIDATION_EXHAUSTED_OR_UNAVAILABLE,),
        ev=(_E.ESC_OPEN,), cap="escalation.raise", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_VALIDATION, _S.ABANDONED, row="3-17",
        cap="stage.abandon", sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_REVIEW, _S.SATISFIED, row="3-18",
        pre=(
            _P.OBSERVED_SATISFACTION_SATISFIED,
            _P.NO_BLOCKING_FINDING,
            _P.REVIEW_SPECS_MET,
            _P.MUTATIONS_LANDED_VIA_COMMIT,
        ),
        ev=(_E.SNAP, _E.VR_PASS, _E.RVW_PASS, _E.CR),
        cap="stage.satisfy", sup=CONFIRM, auto=NOTIFY,
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_REVIEW, _S.RUNNING, row="3-19",
        pre=(_P.BLOCKING_FINDING_PRESENT, _P.ATTEMPTS_REMAIN, _P.BUDGET_REMAINS),
        ev=(_E.RVW_ANY,), cap="run.start", sup=NOTIFY, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_REVIEW, _S.AWAITING_VALIDATION, row="3-20",
        pre=(_P.RECEIPT_INVALIDATED,),
        ev=(_E.SNAP,), cap="stage.lifecycle.advance", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_REVIEW, _S.AWAITING_DECISION, row="3-21",
        pre=(_P.WAIVABLE_BLOCKER_OR_INCONCLUSIVE_REVIEW,),
        ev=(_E.RVW_ANY, _E.ESC_OPEN), cap="escalation.raise", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_REVIEW, _S.ABANDONED, row="3-22",
        cap="stage.abandon", sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_DECISION, _S.SATISFIED, row="3-23",
        pre=(
            _P.BLOCKING_FINDINGS_RESOLVED,
            _P.SHORTFALLS_WAIVED,
            _P.OBSERVED_SATISFACTION_SATISFIED,
        ),
        ev=(_E.DEC, _E.VR_PASS, _E.RVW_ANY, _E.SNAP),
        cap="stage.satisfy", sup=DECIDE(_K.APPROVE), auto=DECIDE(_K.APPROVE),
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_DECISION, _S.RUNNING, row="3-24",
        pre=(_P.REWORK_DIRECTED,),
        ev=(_E.DEC,), cap="run.start",
        sup=DECIDE(_K.OVERRIDE), auto=DECIDE(_K.OVERRIDE),
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_DECISION, _S.REJECTED, row="3-25",
        pre=(_P.REJECTION_RECORDED,),
        ev=(_E.DEC,), cap="stage.reject",
        sup=DECIDE(_K.REJECT), auto=DECIDE(_K.REJECT),
    ),
    _rule(
        Axis.STAGE, _S.AWAITING_DECISION, _S.ABANDONED, row="3-26",
        pre=(_P.ABANDONMENT_RECORDED,),
        ev=(_E.DEC,), cap="stage.abandon",
        sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.STAGE, _S.SATISFIED, _S.READY, row="3-27",
        pre=(_P.SATISFACTION_STALE_OR_CONTRADICTED,),
        ev=(_E.SNAP,), cap="stage.lifecycle.advance", sup=NOTIFY, auto=AUTO,
    ),
    _rule(
        Axis.STAGE, _S.REJECTED, _S.READY, row="3-28",
        pre=(_P.NEW_CONTRACT_DRAFTED, _P.OVERRIDE_PERMITS_RETRY),
        ev=(_E.DEC,), cap="stage.lifecycle.advance",
        sup=DECIDE(_K.OVERRIDE), auto=DECIDE(_K.OVERRIDE),
    ),
)


# --- §4 — axis 3, suspension ----------------------------------------------

#: `SUSPENDED_BY_*` in §4's last two rows.
_SUSPENDED = (
    _U.SUSPENDED_BY_HUMAN,
    _U.SUSPENDED_BY_POLICY,
    _U.SUSPENDED_BY_ESCALATION,
    _U.SUSPENDED_BY_BUDGET,
    _U.SUSPENDED_BY_DRIFT,
    _U.SUSPENDED_BY_INTEGRITY,
)

_SUSPENSION_RULES = (
    _rule(
        Axis.SUSPENSION, _U.NONE, _U.QUIESCING, row="4-1",
        pre=(_P.SUSPENSION_REQUESTED, _P.OPERATIONS_IN_FLIGHT),
        cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.NONE, _U.SUSPENDED_BY_HUMAN, row="4-2",
        pre=(_P.NO_OPERATIONS_IN_FLIGHT,),
        ev=(_E.DEC,), cap="suspension.set",
        sup=DECIDE(_K.SUSPEND), auto=DECIDE(_K.SUSPEND),
    ),
    _rule(
        Axis.SUSPENSION, _U.NONE, _U.SUSPENDED_BY_POLICY, row="4-3",
        pre=(_P.POLICY_RULE_MATCHED,),
        ev=(_E.POLICY_RECORD,), cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.NONE, _U.SUSPENDED_BY_ESCALATION, row="4-4",
        pre=(_P.NON_AUTO_ESCALATION_TARGETS_HOLDER,),
        ev=(_E.ESC_OPEN,), cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.NONE, _U.SUSPENDED_BY_BUDGET, row="4-5",
        pre=(_P.BUDGET_CEILING_REACHED,),
        ev=(any_of(_E.WR, _E.VR_ANY),), cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.NONE, _U.SUSPENDED_BY_DRIFT, row="4-6",
        pre=(_P.UNATTRIBUTED_DRIFT,),
        ev=(_E.SNAP,), cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.NONE, _U.SUSPENDED_BY_INTEGRITY, row="4-7",
        pre=(_P.INTEGRITY_VIOLATION_DETECTED,),
        ev=(any_of(_E.CHAIN_VERIFICATION, _E.ESC_OPEN),),
        cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.QUIESCING, _U.SUSPENDED_BY_HUMAN, row="4-8",
        pre=(_P.NO_OPERATIONS_IN_FLIGHT,),
        ev=(_E.DEC, _E.TERMINAL_RECEIPT), cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.QUIESCING, _U.SUSPENDED_BY_POLICY, row="4-9",
        pre=(_P.NO_OPERATIONS_IN_FLIGHT,),
        ev=(_E.TERMINAL_RECEIPT,), cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.QUIESCING, _U.SUSPENDED_BY_ESCALATION, row="4-10",
        pre=(_P.NO_OPERATIONS_IN_FLIGHT,),
        ev=(_E.ESC_OPEN, _E.TERMINAL_RECEIPT),
        cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.QUIESCING, _U.SUSPENDED_BY_BUDGET, row="4-11",
        pre=(_P.NO_OPERATIONS_IN_FLIGHT,),
        ev=(_E.USAGE_RECORD,), cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.QUIESCING, _U.SUSPENDED_BY_DRIFT, row="4-12",
        pre=(_P.NO_OPERATIONS_IN_FLIGHT,),
        ev=(_E.SNAP,), cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.QUIESCING, _U.SUSPENDED_BY_INTEGRITY, row="4-13",
        pre=(_P.NO_OPERATIONS_IN_FLIGHT,),
        ev=(_E.CHAIN_VERIFICATION,), cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.QUIESCING, _U.NONE, row="4-14",
        pre=(_P.SUSPENSION_REQUEST_WITHDRAWN,),
        ev=(_E.DEC,), cap="suspension.clear", sup=DECIDE(_K.RESUME), auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.SUSPENDED_BY_HUMAN, _U.NONE, row="4-15",
        pre=(_P.RESUME_DECISION_RECORDED,),
        ev=(_E.DEC,), cap="suspension.clear",
        sup=DECIDE(_K.RESUME), auto=DECIDE(_K.RESUME),
    ),
    _rule(
        Axis.SUSPENSION, _U.SUSPENDED_BY_POLICY, _U.NONE, row="4-16",
        pre=(_P.POLICY_RULE_NO_LONGER_MATCHES,),
        ev=(any_of(_E.POLICY_RECORD, _E.DEC),),
        cap="suspension.clear", sup=CONFIRM, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION, _U.SUSPENDED_BY_ESCALATION, _U.NONE, row="4-17",
        pre=(_P.ESCALATIONS_SETTLED,),
        ev=(_E.DEC,), cap="suspension.clear",
        sup=DECIDE(_K.RESUME),
        auto=WHEN(_P.ALL_RESOLUTIONS_AUTO_RESOLVABLE, AUTO, DECIDE(_K.RESUME)),
    ),
    _rule(
        Axis.SUSPENSION, _U.SUSPENDED_BY_BUDGET, _U.NONE, row="4-18",
        pre=(_P.BUDGET_EXTENDED,),
        ev=(_E.DEC,), cap="suspension.clear",
        sup=DECIDE(_K.EXTEND_BUDGET), auto=DECIDE(_K.EXTEND_BUDGET),
    ),
    _rule(
        Axis.SUSPENSION, _U.SUSPENDED_BY_DRIFT, _U.NONE, row="4-19",
        pre=(_P.DRIFT_CLEARED_OR_ACCEPTED,),
        ev=(any_of(_E.SNAP, _E.DEC),), cap="suspension.clear",
        sup=DECIDE(_K.ACCEPT_RISK), auto=CONFIRM,
    ),
    _rule(
        Axis.SUSPENSION, _U.SUSPENDED_BY_INTEGRITY, _U.NONE, row="4-20",
        pre=(_P.CHAIN_REVERIFIED,),
        ev=(_E.CHAIN_VERIFICATION, _E.DEC), cap="suspension.clear",
        sup=DECIDE(_K.OVERRIDE), auto=DECIDE(_K.OVERRIDE),
    ),
    _rule(
        Axis.SUSPENSION,
        tuple(state for state in _SUSPENDED if state is not _U.SUSPENDED_BY_INTEGRITY),
        _U.SUSPENDED_BY_INTEGRITY,
        row="4-21",
        pre=(_P.INTEGRITY_VIOLATION_DETECTED,),
        ev=(_E.CHAIN_VERIFICATION,), cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.SUSPENSION,
        tuple(state for state in _SUSPENDED if state is not _U.SUSPENDED_BY_HUMAN),
        _U.SUSPENDED_BY_HUMAN,
        row="4-22",
        pre=(_P.HUMAN_SUSPENDS_OVER_EXISTING,),
        ev=(_E.DEC,), cap="suspension.set",
        sup=DECIDE(_K.SUSPEND), auto=DECIDE(_K.SUSPEND),
    ),
)


# --- §5 — StageRun.lifecycle ----------------------------------------------

_RUN_RULES = (
    _rule(
        Axis.RUN, ORIGIN, _R.ALLOCATED, row="5-1",
        pre=(_P.ACTIVATION_VALID, _P.RUN_SUSPENSION_NONE),
        ev=(_E.ACT, _E.SNAP), cap="run.start", sup=CONFIRM, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.ALLOCATED, _R.DISPATCHED, row="5-2",
        pre=(_P.PROVIDER_ACCEPTED_INVOCATION, _P.GRANTS_WITHIN_EFFECTIVE),
        cap="worker.invoke", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.ALLOCATED, _R.CLOSED_ABORTED, row="5-3",
        pre=(_P.ACTIVATION_REVOKED_BEFORE_DISPATCH,),
        ev=(_E.REVOCATION_RECORD,), cap="run.abort", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.DISPATCHED, _R.WORKING, row="5-4",
        pre=(_P.PROVIDER_REPORTED_START,),
        cap="worker.invoke", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.DISPATCHED, _R.CLOSED_ABORTED, row="5-5",
        pre=(_P.PROVIDER_REJECTED,),
        ev=(_E.WR,), cap="run.abort", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.WORKING, _R.VALIDATING, row="5-6",
        pre=(_P.WORKER_RECEIPT_PRESENT, _P.VALIDATION_AUTHORIZED),
        ev=(_E.WR,), cap="validation.request", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.WORKING, _R.AWAITING_DECISION, row="5-7",
        pre=(_P.BLOCKING_ESCALATION_BOUND,),
        ev=(_E.ESC_OPEN,), cap="escalation.raise", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.WORKING, _R.CLOSED_EXPIRED, row="5-8",
        pre=(_P.DEADLINE_PASSED,),
        ev=(_E.WR,), cap="run.abort", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.WORKING, _R.CLOSED_ABORTED, row="5-9",
        pre=(_P.BUDGET_OR_STOP_OR_SCOPE_BREACH,),
        ev=(_E.WR,), cap="run.abort", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.VALIDATING, _R.REVIEWING, row="5-10",
        pre=(_P.MECHANICAL_CRITERIA_MET, _P.MANDATORY_REVIEW_SPECS_EXIST),
        ev=(_E.VR_PASS,), cap="review.submit", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.VALIDATING, _R.WORKING, row="5-11",
        pre=(_P.MANDATORY_VALIDATION_FAILED, _P.ATTEMPTS_REMAIN),
        ev=(_E.VR_ANY,), cap="worker.invoke", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.VALIDATING, _R.AWAITING_DECISION, row="5-12",
        pre=(_P.VALIDATION_EXHAUSTED_OR_UNAVAILABLE,),
        ev=(_E.ESC_OPEN,), cap="escalation.raise", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.VALIDATING, _R.CLOSED_EXPIRED, row="5-13",
        pre=(_P.DEADLINE_PASSED,), cap="run.abort", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.REVIEWING, _R.CLOSED_SATISFIED, row="5-14",
        pre=(_P.STAGE_SATISFIED, _P.COMMIT_INTENTS_SETTLED),
        ev=(_E.RVW_PASS, _E.CR, _E.SNAP), cap="stage.satisfy",
        sup=CONFIRM, auto=NOTIFY,
    ),
    _rule(
        Axis.RUN, _R.REVIEWING, _R.WORKING, row="5-15",
        pre=(_P.BLOCKING_FINDING_PRESENT, _P.ATTEMPTS_REMAIN),
        ev=(_E.RVW_ANY,), cap="worker.invoke", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.REVIEWING, _R.AWAITING_DECISION, row="5-16",
        pre=(_P.WAIVABLE_BLOCKER_OR_INCONCLUSIVE_REVIEW,),
        ev=(_E.ESC_OPEN,), cap="escalation.raise", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.REVIEWING, _R.CLOSED_EXPIRED, row="5-17",
        pre=(_P.DEADLINE_PASSED,), cap="run.abort", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.RUN, _R.AWAITING_DECISION, _R.WORKING, row="5-18",
        pre=(_P.REWORK_DIRECTED,),
        ev=(_E.DEC,), cap="worker.invoke",
        sup=DECIDE(_K.OVERRIDE), auto=DECIDE(_K.OVERRIDE),
    ),
    _rule(
        Axis.RUN, _R.AWAITING_DECISION, _R.CLOSED_SATISFIED, row="5-19",
        pre=(_P.SHORTFALLS_WAIVED, _P.STAGE_SATISFIED),
        ev=(_E.DEC, _E.VR_PASS, _E.RVW_PASS), cap="stage.satisfy",
        sup=DECIDE(_K.APPROVE), auto=DECIDE(_K.APPROVE),
    ),
    _rule(
        Axis.RUN, _R.AWAITING_DECISION, _R.CLOSED_REJECTED, row="5-20",
        pre=(_P.REJECTION_RECORDED,),
        ev=(_E.DEC,), cap="stage.reject",
        sup=DECIDE(_K.REJECT), auto=DECIDE(_K.REJECT),
    ),
    _rule(
        Axis.RUN, _R.AWAITING_DECISION, _R.CLOSED_ABORTED, row="5-21",
        pre=(_P.ABANDONMENT_RECORDED,),
        ev=(_E.DEC,), cap="run.abort",
        sup=DECIDE(_K.ABANDON), auto=DECIDE(_K.ABANDON),
    ),
    _rule(
        Axis.RUN,
        (_R.DISPATCHED, _R.WORKING, _R.VALIDATING, _R.REVIEWING),
        _R.AWAITING_DECISION,
        row="5-22",
        pre=(_P.OPERATION_UNRESOLVABLE,),
        ev=(_E.ESC_OPEN,), cap="escalation.raise", sup=AUTO, auto=AUTO,
    ),
)


# --- §6 — StageContract.status --------------------------------------------

_CONTRACT_RULES = (
    _rule(
        Axis.CONTRACT, ORIGIN, _C.DRAFT, row="6-1",
        pre=(_P.SCHEMA_VALID, _P.CONTRACT_HASH_RECOMPUTES),
        cap="contract.author", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.CONTRACT, _C.DRAFT, _C.ACTIVE, row="6-2",
        pre=(
            _P.NO_OTHER_ACTIVE_CONTRACT,
            _P.REQUEST_WITHIN_CEILING,
            _P.BUDGET_WITHIN_PROJECT_REMAINING,
        ),
        ev=(_E.ACTIVATION_RECORD,), cap="contract.activate", sup=CONFIRM, auto=AUTO,
    ),
    _rule(
        Axis.CONTRACT, _C.DRAFT, _C.REVOKED, row="6-3",
        pre=(_P.AUTHOR_WITHDREW,), cap="contract.revoke", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.CONTRACT, _C.ACTIVE, _C.FULFILLED, row="6-4",
        pre=(_P.STAGE_SATISFIED,),
        ev=(_E.CR, _E.VR_PASS, _E.RVW_PASS), cap="stage.satisfy",
        sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.CONTRACT, _C.ACTIVE, _C.SUPERSEDED, row="6-5",
        pre=(_P.SUCCESSOR_ACTIVE, _P.NO_NON_TERMINAL_RUN),
        ev=(_E.SUCCESSOR_ACTIVATION,), cap="contract.supersede",
        sup=CONFIRM, auto=CONFIRM,
    ),
    _rule(
        Axis.CONTRACT, _C.ACTIVE, _C.REVOKED, row="6-6",
        pre=(_P.REVOCATION_TRIGGERED,),
        ev=(any_of(_E.DEC, _E.TRIGGERING_RECORD),), cap="contract.revoke",
        sup=DECIDE(_K.REVOKE_CAPABILITY),
        auto=WHEN(_P.REVOCATION_BY_BREACH_OR_INTEGRITY, AUTO, CONFIRM),
    ),
    _rule(
        Axis.CONTRACT, _C.ACTIVE, _C.EXPIRED, row="6-7",
        pre=(_P.ACTIVATION_EXPIRED,), cap="contract.revoke", sup=AUTO, auto=AUTO,
    ),
)


# --- §7.1 — ValidationOperation.status ------------------------------------

_VALIDATION_RULES = (
    _rule(
        Axis.VALIDATION, ORIGIN, _V.REQUESTED, row="7.1-1",
        pre=(_P.SPEC_IN_PINNED_CONTRACT,),
        cap="validation.request", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.VALIDATION, _V.REQUESTED, _V.AUTHORIZED, row="7.1-2",
        pre=(_P.COMMAND_MATCHES_SPEC, _P.CWD_IN_SCOPE, _P.NETWORK_PERMITTED),
        cap="proc.exec.validation", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.VALIDATION, _V.REQUESTED, _V.DENIED, row="7.1-3",
        pre=(_P.COMMAND_ALTERED_OR_UNAUTHORIZED,),
        cap="proc.exec.validation", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.VALIDATION, _V.AUTHORIZED, _V.EXECUTING, row="7.1-4",
        pre=(_P.SANDBOX_ALLOCATED,),
        ev=(_E.SNAP,), cap="validation.execute", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.VALIDATION, _V.EXECUTING, _V.COMPLETED, row="7.1-5",
        pre=(_P.PROCESS_EXITED_IN_TIME,),
        ev=(_E.VALIDATION_RECEIPT,), cap="validation.attest", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.VALIDATION, _V.EXECUTING, _V.TIMED_OUT, row="7.1-6",
        pre=(_P.TIMEOUT_ELAPSED,),
        ev=(_E.VALIDATION_RECEIPT,), cap="validation.attest", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.VALIDATION, _V.EXECUTING, _V.EXEC_FAILED, row="7.1-7",
        pre=(_P.SANDBOX_OR_TOOLCHAIN_ERROR,),
        ev=(_E.VALIDATION_RECEIPT,), cap="validation.attest", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.VALIDATION,
        (_V.REQUESTED, _V.AUTHORIZED, _V.EXECUTING), _V.CANCELLED, row="7.1-8",
        pre=(_P.HOLDER_QUIESCING_OR_RUN_CLOSED,),
        cap="run.abort", sup=AUTO, auto=AUTO,
    ),
)


# --- §7.2 — WorkerInvocation.status ---------------------------------------

_UNSETTLED_INVOCATION = (_I.PENDING, _I.DISPATCHED, _I.RUNNING)

_INVOCATION_RULES = (
    _rule(
        Axis.INVOCATION, ORIGIN, _I.PENDING, row="7.2-1",
        pre=(_P.RUN_ALLOCATED_OR_WORKING, _P.BUDGET_HEADROOM, _P.BARRIER_CLEAR),
        ev=(_E.ACT, _E.REQUEST_REF), cap="worker.invoke",
        sup=WHEN(_P.FIRST_INVOCATION_OF_RUN, CONFIRM, AUTO), auto=AUTO,
    ),
    _rule(
        Axis.INVOCATION, _I.PENDING, _I.REJECTED_BY_POLICY, row="7.2-2",
        pre=(_P.CAPABILITIES_EXCEEDED_OR_PROVIDER_UNREGISTERED,),
        cap="worker.invoke", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.INVOCATION, _I.PENDING, _I.DISPATCHED, row="7.2-3",
        pre=(_P.PROVIDER_ACCEPTED_INVOCATION, _P.PROMPT_BUNDLE_STORED),
        ev=(_E.PROMPT_BUNDLE_REF,), cap="worker.invoke", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.INVOCATION, _I.DISPATCHED, _I.RUNNING, row="7.2-4",
        pre=(_P.PROVIDER_REPORTED_START,),
        cap="worker.invoke", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.INVOCATION, _I.RUNNING, _I.COMPLETED, row="7.2-5",
        pre=(_P.PROVIDER_RETURNED_OUTPUT,),
        ev=(_E.WR,), cap="worker.invoke", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.INVOCATION, _I.RUNNING, _I.TIMED_OUT, row="7.2-6",
        pre=(_P.DEADLINE_PASSED,),
        ev=(_E.WR,), cap="worker.invoke", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.INVOCATION, _I.RUNNING, _I.FAILED, row="7.2-7",
        pre=(_P.PROVIDER_ERROR,),
        ev=(_E.WR,), cap="worker.invoke", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.INVOCATION, _UNSETTLED_INVOCATION, _I.CANCELLED, row="7.2-8",
        pre=(_P.SUSPENSION_OR_BUDGET_OR_HUMAN_STOP,),
        ev=(_E.WR,), cap="run.abort", sup=AUTO, auto=AUTO,
    ),
    # The reconciliation rows. `recovery.reconcile` is what distinguishes them
    # from the direct rows over the same states: it observes and records, and
    # holds nothing that can execute (`WP-16`).
    _rule(
        Axis.INVOCATION, _UNSETTLED_INVOCATION,
        (_I.COMPLETED, _I.FAILED, _I.TIMED_OUT, _I.CANCELLED), row="7.2-9",
        pre=(_P.OLD_EPOCH, _P.LOOKUP_FINISHED),
        ev=(_E.WR,), cap="recovery.reconcile", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.INVOCATION, _UNSETTLED_INVOCATION, _I.FAILED, row="7.2-10",
        pre=(_P.OLD_EPOCH, _P.LOOKUP_ABSENT),
        ev=(_E.WR,), cap="recovery.reconcile", sup=AUTO, auto=AUTO,
    ),
)


# --- §7.3 — Finding.status ------------------------------------------------

_FINDING_RULES = (
    _rule(
        Axis.FINDING, ORIGIN, _F.OPEN, row="7.3-1",
        pre=(_P.RAISED_WITHIN_ATTESTED_REVIEW,),
        ev=(_E.RVW_ANY,), cap="finding.raise", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.FINDING, _F.OPEN, _F.ACKNOWLEDGED, row="7.3-2",
        pre=(_P.REMEDIATION_ACCEPTED,),
        cap="finding.resolve", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.FINDING, (_F.OPEN, _F.ACKNOWLEDGED), _F.FIXED, row="7.3-3",
        pre=(_P.DEFECT_GONE,),
        ev=(any_of(_E.VR_PASS, _E.RVW_PASS),),
        cap="finding.resolve", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.FINDING, (_F.OPEN, _F.ACKNOWLEDGED, _F.DISPUTED), _F.WAIVED, row="7.3-4",
        pre=(_P.CRITERION_WAIVABLE,),
        ev=(_E.DEC,), cap="finding.waive",
        sup=DECIDE(_K.WAIVE), auto=DECIDE(_K.WAIVE),
    ),
    _rule(
        Axis.FINDING, _F.OPEN, _F.DISPUTED, row="7.3-5",
        pre=(_P.CONTESTED_WITH_COUNTER_EVIDENCE,),
        ev=(_E.COUNTER_EVIDENCE,), cap="finding.resolve", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.FINDING, _F.DISPUTED, _F.INVALID, row="7.3-6",
        pre=(_P.COUNTER_EVIDENCE_ACCEPTED,),
        ev=(any_of(_E.RVW_PASS, _E.DEC),), cap="finding.resolve",
        sup=DECIDE(_K.OVERRIDE),
        auto=WHEN(_P.INDEPENDENT_REVIEW_CLEARED, AUTO, DECIDE(_K.OVERRIDE)),
    ),
    _rule(
        Axis.FINDING, _F.DISPUTED, _F.OPEN, row="7.3-7",
        pre=(_P.COUNTER_EVIDENCE_REJECTED,),
        ev=(_E.RVW_FAIL,), cap="finding.resolve", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.FINDING, _F.WAIVED, _F.OPEN, row="7.3-8",
        pre=(_P.WAIVER_EXPIRED_OR_REVOKED,),
        cap="finding.resolve", sup=AUTO, auto=AUTO,
    ),
)


# --- §7.4 — CommitIntent.status -------------------------------------------

_COMMIT_RULES = (
    _rule(
        Axis.COMMIT_INTENT, ORIGIN, _M.PROPOSED, row="7.4-1",
        pre=(_P.MUTATIONS_IN_SCOPE, _P.BASE_MATCHES_SNAPSHOT, _P.TOKEN_MINTED_AND_CARRIED),
        ev=(_E.WR, _E.SNAP), cap="commit.propose", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, _M.PROPOSED, _M.BLOCKED, row="7.4-2",
        pre=(_P.INTENT_PRECONDITION_UNMET,),
        cap="commit.propose", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, _M.BLOCKED, _M.PROPOSED, row="7.4-3",
        pre=(_P.INTENT_PRECONDITIONS_NOW_MET,),
        ev=(any_of(_E.VR_PASS, _E.RVW_PASS, _E.DEC),),
        cap="commit.propose", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, _M.PROPOSED, _M.AUTHORIZED, row="7.4-4",
        pre=(_P.INTENT_PRECONDITIONS_MET, _P.WORKSPACE_UNCHANGED),
        ev=(_E.SNAP, _E.VR_PASS, _E.RVW_PASS),
        cap="commit.authorize", sup=CONFIRM, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, _M.PROPOSED, _M.DENIED, row="7.4-5",
        pre=(_P.SCOPE_BREACH_OR_PROHIBITION,),
        cap="commit.authorize", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, _M.AUTHORIZED, _M.APPLYING, row="7.4-6",
        pre=(_P.WRITE_LOCK_HELD, _P.TOKEN_DURABLE_BEFORE_MUTATION),
        cap="commit.apply", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, _M.APPLYING, _M.APPLIED, row="7.4-7",
        pre=(_P.APPLICATION_SUCCEEDED, _P.TREE_DIGEST_MATCHES),
        ev=(_E.CR,), cap="commit.apply", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, _M.APPLYING, _M.FAILED, row="7.4-8",
        pre=(_P.APPLICATION_FAILED_OR_DIVERGED,),
        ev=(_E.CR, _E.ESC_OPEN), cap="commit.apply", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, _M.APPLIED, _M.ROLLED_BACK, row="7.4-9",
        pre=(_P.ROLLBACK_POLICY_INVOKED,),
        ev=(_E.CR, _E.SNAP), cap="commit.apply", sup=CONFIRM, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, _M.FAILED, _M.ROLLED_BACK, row="7.4-10",
        pre=(_P.PARTIAL_APPLICATION_REVERTED,),
        ev=(_E.SNAP,), cap="commit.apply", sup=AUTO, auto=AUTO,
    ),
    # The §5 exemption: these initiate nothing, and they are the only
    # transitions a run under the `RUN-INV-3` barrier may take.
    _rule(
        Axis.COMMIT_INTENT, _M.APPLYING, _M.APPLIED, row="7.4-11",
        pre=(_P.OLD_EPOCH, _P.SCAN_FOUND_MATCHING_REVISION),
        ev=(_E.CR,), cap="recovery.reconcile", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, _M.APPLYING, _M.FAILED, row="7.4-12",
        pre=(_P.OLD_EPOCH, _P.SCAN_FOUND_NO_REVISION),
        ev=(_E.SNAP,), cap="recovery.reconcile", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, _M.APPLYING, _M.FAILED, row="7.4-13",
        pre=(_P.OLD_EPOCH, _P.SCAN_FOUND_DIVERGENT_REVISION),
        ev=(_E.CR, _E.ESC_OPEN), cap="recovery.reconcile", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.COMMIT_INTENT, (_M.PROPOSED, _M.BLOCKED, _M.AUTHORIZED), None,
        row="7.4-14", self_edge=True,
        pre=(_P.OLD_EPOCH, _P.NEVER_REACHED_APPLYING, _P.SCAN_FOUND_NO_REVISION),
        ev=(_E.SNAP,), cap="recovery.reconcile", sup=AUTO, auto=AUTO,
    ),
)


# --- §7.5 — HumanDecision.decision_state ----------------------------------

_DECISION_RULES = (
    _rule(
        Axis.DECISION, ORIGIN, _D.VALID, row="7.5-1",
        pre=(_P.RECORDED_PER_HD_INV, _P.SNAPSHOT_BINDING_CURRENT),
        ev=(_E.SNAP,), cap="decision.record", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.DECISION, _D.VALID, _D.CONSUMED, row="7.5-2",
        pre=(_P.DISCHARGED_ITS_TRANSITION,),
        ev=(_E.AUDIT_EVENT,), cap="audit.append", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.DECISION, _D.VALID, _D.STALE, row="7.5-3",
        pre=(_P.NEWER_SNAPSHOT_SUPERSEDES,),
        ev=(_E.SNAP,), cap="audit.append", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.DECISION, _D.VALID, _D.EXPIRED, row="7.5-4",
        pre=(_P.EXPIRED_OR_SCOPE_LEFT,), cap="audit.append", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.DECISION, (_D.VALID, _D.STALE), _D.VOID, row="7.5-5",
        pre=(_P.HD_INV_1_VIOLATED,),
        ev=(_E.CHAIN_VERIFICATION,), cap="suspension.set", sup=AUTO, auto=AUTO,
    ),
)


# --- §7.6 — Escalation.status ---------------------------------------------

_ESCALATION_RULES = (
    _rule(
        Axis.ESCALATION, ORIGIN, _X.OPEN, row="7.6-1",
        pre=(_P.TRIGGER_FIRED,),
        ev=(_E.TRIGGERING_RECORD,), cap="escalation.raise", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.ESCALATION, _X.OPEN, _X.ACKNOWLEDGED, row="7.6-2",
        pre=(_P.ASSIGNEE_ACCEPTED,),
        cap="escalation.resolve", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.ESCALATION, (_X.OPEN, _X.ACKNOWLEDGED), _X.RESOLVED, row="7.6-3",
        pre=(_P.DECISION_OR_CONDITION_CLEARED,),
        ev=(any_of(_E.DEC, _E.SNAP, _E.VR_PASS),), cap="escalation.resolve",
        sup=DECIDE_PER_ESCALATION,
        auto=WHEN(_P.AUTO_RESOLVABLE, AUTO, DECIDE_PER_ESCALATION),
    ),
    _rule(
        Axis.ESCALATION, (_X.OPEN, _X.ACKNOWLEDGED), _X.EXPIRED, row="7.6-4",
        pre=(_P.NO_RESOLUTION_IN_WINDOW,),
        cap="escalation.resolve", sup=AUTO, auto=AUTO,
    ),
    _rule(
        Axis.ESCALATION, _X.OPEN, _X.WITHDRAWN, row="7.6-5",
        pre=(_P.RAISER_RETRACTED,),
        ev=(any_of(_E.SNAP, _E.VR_PASS),), cap="escalation.resolve",
        sup=AUTO, auto=AUTO,
    ),
)


#: §2–§7.6. The single graph both governance profiles resolve over.
LEGAL_TRANSITIONS: tuple[TransitionRule, ...] = (
    _PROJECT_RULES
    + _STAGE_RULES
    + _SUSPENSION_RULES
    + _RUN_RULES
    + _CONTRACT_RULES
    + _VALIDATION_RULES
    + _INVOCATION_RULES
    + _FINDING_RULES
    + _COMMIT_RULES
    + _DECISION_RULES
    + _ESCALATION_RULES
)


#: §9.1 — illegal stage transitions. The last row of §9.1 is the axis-3 gate
#: and lives in :data:`SUSPENSION_GATE`, because the set it excepts *is* the
#: gate; restating it here would be a second copy that could drift.
_ILLEGAL_STAGE = (
    IllegalTransition(
        Axis.STAGE, ("PENDING",), ("SATISFIED",), row="9.1-1",
        illegal_because=(
            "no contract, no run, no receipt can exist; satisfaction without "
            "evidence is unverifiable by construction"
        ),
    ),
    IllegalTransition(
        Axis.STAGE, ("PENDING",), ("RUNNING",), row="9.1-2",
        illegal_because=(
            "skips READY dependency check and CONTRACTED authority grant; work "
            "would run with no activation record"
        ),
    ),
    IllegalTransition(
        Axis.STAGE, ("READY",), ("RUNNING",), row="9.1-3",
        illegal_because=(
            "a run without an ACTIVE contract has no effective_capabilities; "
            "default DENY would make every action illegal"
        ),
    ),
    IllegalTransition(
        Axis.STAGE, ("READY",), ("SATISFIED",), row="9.1-4",
        illegal_because="no StageRun, therefore no receipts bound to this stage",
    ),
    IllegalTransition(
        Axis.STAGE, ("CONTRACTED",), ("SATISFIED",), row="9.1-5",
        illegal_because="activation grants authority but produces no evidence",
    ),
    IllegalTransition(
        Axis.STAGE, ("RUNNING",), ("SATISFIED",), row="9.1-6",
        illegal_because=(
            "bypasses validation and review; only AWAITING_REVIEW and "
            "AWAITING_DECISION may satisfy"
        ),
    ),
    IllegalTransition(
        Axis.STAGE, ("AWAITING_VALIDATION",), ("SATISFIED",), row="9.1-7",
        illegal_because="mandatory judgmental criteria have no Review yet",
    ),
    IllegalTransition(
        Axis.STAGE, (ANY_STATE,), ("SATISFIED",), row="9.1-8",
        when=(Precondition.DECLARED_STATUS_AS_BASIS,),
        illegal_because=(
            "a CLAIM is not EVIDENCE; G-6 forbids declared_status in any "
            "precondition"
        ),
    ),
    IllegalTransition(
        Axis.STAGE, (ANY_STATE,), ("SATISFIED",), row="9.1-9",
        when=(Precondition.OBSERVED_SATISFACTION_NOT_SATISFIED,),
        illegal_because=(
            "satisfaction must be measured against the current snapshot, not "
            "asserted"
        ),
    ),
    IllegalTransition(
        Axis.STAGE, ("SATISFIED",), ("RUNNING",), row="9.1-10",
        illegal_because=(
            "re-entry must pass through READY so dependencies and a fresh "
            "contract are re-checked"
        ),
    ),
    IllegalTransition(
        Axis.STAGE, ("ABANDONED",), (ANY_STATE,), row="9.1-11",
        illegal_because=(
            "terminal by G-7; resumption requires a new stage revision from "
            "the roadmap"
        ),
    ),
    IllegalTransition(
        Axis.STAGE, ("REJECTED",), ("SATISFIED",), row="9.1-12",
        illegal_because=(
            "reverses a recorded human rejection without a new run or new "
            "evidence"
        ),
    ),
)

#: §9.2 — illegal project transitions. Its last row is the integrity gate, in
#: :data:`SUSPENSION_GATE` for the same reason.
_ILLEGAL_PROJECT = (
    IllegalTransition(
        Axis.PROJECT, ("DRAFT",), ("ACTIVE",), row="9.2-1",
        illegal_because="no roadmap imported, so no stage exists to act on",
    ),
    IllegalTransition(
        Axis.PROJECT, ("DRAFT", "PLANNING"), ("COMPLETED",), row="9.2-2",
        illegal_because=(
            "completion asserts every stage satisfied; with no runs there is "
            "nothing to assert over"
        ),
    ),
    IllegalTransition(
        Axis.PROJECT, ("ACTIVE",), ("COMPLETED",), row="9.2-3",
        illegal_because=(
            "must pass through SETTLING, where the all-stages-terminal "
            "predicate is evaluated once against a stable snapshot"
        ),
    ),
    IllegalTransition(
        Axis.PROJECT, ("ARCHIVED",), (ANY_STATE,), row="9.2-4",
        illegal_because=(
            "terminal; the evidence set is sealed and artifacts may have been "
            "collected"
        ),
    ),
    IllegalTransition(
        Axis.PROJECT, (ORIGIN,), ("DRAFT",), row="9.2-5",
        when=(Precondition.CREATOR_IS_NOT_HUMAN,),
        illegal_because=(
            "a runtime or worker cannot originate a project and thereby its "
            "own capability ceiling"
        ),
    ),
)

#: §9.1 and §9.2.
ILLEGAL_TRANSITIONS: tuple[IllegalTransition, ...] = (
    _ILLEGAL_STAGE + _ILLEGAL_PROJECT
)


#: §9.3.
ILLEGAL_OPERATIONS: tuple[IllegalOperation, ...] = (
    IllegalOperation(
        Operation.MINT_VALIDATION_RECEIPT, frozenset({ActorKind.WORKER}), row="9.3-1",
        illegal_because=(
            "collapses CLAIM into EVIDENCE; the measured party would author "
            "the measurement"
        ),
    ),
    IllegalOperation(
        Operation.MINT_COMMIT_RECEIPT, frozenset({ActorKind.WORKER}), row="9.3-2",
        illegal_because="only the applier can attest what was applied",
    ),
    IllegalOperation(
        Operation.CREATE_REALITY_SNAPSHOT,
        frozenset({ActorKind.WORKER, ActorKind.ADAPTER}), row="9.3-3",
        illegal_because=(
            "ground truth must come from the runtime's own observation, not a "
            "reported view"
        ),
    ),
    IllegalOperation(
        Operation.CREATE_HUMAN_DECISION,
        frozenset({ActorKind.RUNTIME, ActorKind.WORKER, ActorKind.ADAPTER}),
        row="9.3-4",
        illegal_because="authority cannot be self-issued; violates HD-INV-1",
    ),
    IllegalOperation(
        Operation.CREATE_HUMAN_DECISION_UNAUTHENTICATED,
        frozenset({ActorKind.HUMAN}), row="9.3-5",
        illegal_because=(
            "unauthenticated authority is indistinguishable from forged "
            "authority"
        ),
    ),
    IllegalOperation(
        Operation.CREATE_HUMAN_DECISION_WITHOUT_EVIDENCE,
        frozenset({ActorKind.HUMAN}), row="9.3-6",
        illegal_because=(
            "an uninformed approval cannot discharge required_evidence"
        ),
    ),
    IllegalOperation(
        Operation.REPLAY_CONSUMED_DECISION_NONCE, ANY_ACTOR, row="9.3-7",
        illegal_because=(
            "one decision would authorize unbounded future actions"
        ),
    ),
    IllegalOperation(
        Operation.MUTATE_ACTIVE_CONTRACT, ANY_ACTOR, row="9.3-8",
        illegal_because=(
            "contract_hash is pinned into the run; mutation silently changes "
            "what was authorized"
        ),
    ),
    IllegalOperation(
        Operation.WIDEN_EFFECTIVE_CAPABILITIES, ANY_ACTOR, row="9.3-9",
        illegal_because=(
            "authority is frozen at activation; widening must produce a new "
            "activation record"
        ),
    ),
    IllegalOperation(
        Operation.GRANT_OUTSIDE_CEILING,
        frozenset({ActorKind.HUMAN, ActorKind.RUNTIME}), row="9.3-10",
        illegal_because=(
            "the ceiling is the project-level bound; per-grant escape makes it "
            "unenforceable"
        ),
    ),
    IllegalOperation(
        Operation.DELEGATE_UNHELD_CAPABILITY, frozenset({ActorKind.WORKER}),
        row="9.3-11",
        illegal_because="privilege escalation by construction",
    ),
    IllegalOperation(
        Operation.REWRITE_AUDIT_EVENT, ANY_ACTOR, row="9.3-12",
        illegal_because=(
            "breaks the hash chain, destroying verifiability of every later "
            "event"
        ),
    ),
    IllegalOperation(
        Operation.WRITE_OBSERVED_SATISFACTION,
        frozenset({ActorKind.WORKER, ActorKind.ADAPTER, ActorKind.HUMAN}),
        row="9.3-13",
        illegal_because=(
            "it is a derived field; a writable one would be a CLAIM wearing an "
            "EVIDENCE label"
        ),
    ),
    IllegalOperation(
        Operation.GATE_ON_DECLARED_STATUS, ANY_ACTOR, row="9.3-14",
        illegal_because=(
            "G-6; the field exists precisely so claims are recorded without "
            "being trusted"
        ),
    ),
    IllegalOperation(
        Operation.EXECUTE_DIVERGENT_COMMAND_SPEC, ANY_ACTOR, row="9.3-15",
        illegal_because=(
            "the validator would no longer be the one the contract was "
            "approved against"
        ),
    ),
    IllegalOperation(
        Operation.WRITE_OUTSIDE_SCOPE, frozenset({ActorKind.WORKER}), row="9.3-16",
        illegal_because=(
            "scope is the blast radius the activation was granted against"
        ),
    ),
    IllegalOperation(
        Operation.SELF_REVIEW_FOR_INDEPENDENT_SPEC, ANY_ACTOR, row="9.3-17",
        illegal_because="RV-INV-1; self-review provides no independent signal",
    ),
    IllegalOperation(
        Operation.WAIVE_NON_WAIVABLE_CRITERION, frozenset({ActorKind.HUMAN}),
        row="9.3-18",
        illegal_because=(
            "the contract declared it non-negotiable at authoring time, before "
            "the outcome was known"
        ),
    ),
    IllegalOperation(
        Operation.RESOLVE_ESCALATION_WITHOUT_DECISION,
        frozenset({ActorKind.RUNTIME}), row="9.3-19",
        illegal_because=(
            "the escalation exists because the runtime declared itself unable "
            "to decide"
        ),
    ),
    IllegalOperation(
        Operation.SET_AUTONOMOUS_WITHOUT_DECISION, ANY_ACTOR, row="9.3-20",
        illegal_because=(
            "mode selection is the root of every policy relaxation in this "
            "document"
        ),
    ),
    IllegalOperation(
        Operation.APPLY_INTENT_WITH_STALE_BASE, ANY_ACTOR, row="9.3-21",
        illegal_because="the reviewed diff is not the diff that would land",
    ),
    IllegalOperation(
        Operation.SATISFY_FROM_INCOMPLETE_SNAPSHOT, ANY_ACTOR, row="9.3-22",
        illegal_because=(
            "RS-INV-1; absence of observation is not observation of absence of "
            "defects"
        ),
    ),
    IllegalOperation(
        Operation.GRANT_WITHOUT_ADMISSIBLE_GRANTOR, frozenset({ActorKind.RUNTIME}),
        row="9.3-23",
        illegal_because=(
            "AX-11; ceiling membership, a role-table cell, and "
            "capability_request bound a grant, they never create one"
        ),
    ),
    IllegalOperation(
        Operation.ACTIVATE_WITHOUT_GRANT_BASIS, frozenset({ActorKind.RUNTIME}),
        row="9.3-24",
        illegal_because=(
            "A-INV-3; an unattributed grant cannot be replayed, so the "
            "authority trace would not answer \"what allowed this?\""
        ),
    ),
    IllegalOperation(
        Operation.DISPATCH_UNDER_BARRIER, frozenset({ActorKind.RUNTIME}),
        row="9.3-25",
        illegal_because=(
            "RUN-INV-3; this is precisely how a restart produces a duplicate "
            "worker or a duplicate commit"
        ),
    ),
    IllegalOperation(
        Operation.REPLACE_UNRECONCILED_INVOCATION, frozenset({ActorKind.RUNTIME}),
        row="9.3-26",
        illegal_because=(
            "a new key defeats WP-6, so the provider would execute the work a "
            "second time and bill it a second time"
        ),
    ),
    IllegalOperation(
        Operation.RESUBMIT_REQUEST_REF, frozenset({ActorKind.RUNTIME}), row="9.3-27",
        illegal_because=(
            "WP-16; against an ABSENT key a resubmission performs the work "
            "instead of reporting that nothing happened"
        ),
    ),
    IllegalOperation(
        Operation.DISPATCH_WITHOUT_LOOKUP, frozenset({ActorKind.RUNTIME}),
        row="9.3-28",
        illegal_because=(
            "WP-17; an effect whose outcome the kernel can never learn is "
            "unreconcilable by construction"
        ),
    ),
    IllegalOperation(
        Operation.MUTATE_BEFORE_TOKEN_DURABLE, frozenset({ActorKind.RUNTIME}),
        row="9.3-29",
        illegal_because=(
            "a landed revision with no recorded identity can never be matched "
            "to the intent that produced it"
        ),
    ),
    IllegalOperation(
        Operation.REAPPLY_UNRECONCILED_INTENT, frozenset({ActorKind.RUNTIME}),
        row="9.3-30",
        illegal_because=(
            "the first application may have landed; blind retry is not "
            "idempotent and would duplicate the change"
        ),
    ),
    IllegalOperation(
        Operation.CITE_INVALID_DECISION, ANY_ACTOR, row="9.3-31",
        illegal_because=(
            "HD-INV-4; a consumed, expired, void, or stale approval no longer "
            "describes the reality it was granted against"
        ),
    ),
    IllegalOperation(
        Operation.MINT_REVIEW_ATTESTATION,
        frozenset({ActorKind.WORKER, ActorKind.ADAPTER, ActorKind.HUMAN}),
        row="9.3-32",
        illegal_because=(
            "review.attest is KERNEL; a self-attested review would promote a "
            "CLAIM to EVIDENCE by assertion"
        ),
    ),
    IllegalOperation(
        Operation.CITE_REVIEW_AS_EVIDENCE, ANY_ACTOR, row="9.3-33",
        illegal_because=(
            "G-1; the Review is the judgement, the ReviewAttestation is the "
            "kernel's measurement of it"
        ),
    ),
)


#: §0.1. Keyed by the holder's `SuspensionState`. `lifecycle_targets` carries
#: the states axes 1 and 2 may still reach; the booleans carry the rest of the
#: row, which §8's composition table reads.
_OPEN = frozenset({ANY_STATE})
_ABORT_ONLY = frozenset({"AWAITING_DECISION", "ABANDONED", "CLOSED_ABORTED"})
_ABANDON_ONLY = frozenset({"ABANDONED"})

SUSPENSION_GATE: Mapping[SuspensionState, SuspensionGate] = {
    SuspensionState.NONE: SuspensionGate(True, True, True, _OPEN),
    SuspensionState.QUIESCING: SuspensionGate(False, True, False, _ABORT_ONLY),
    SuspensionState.SUSPENDED_BY_HUMAN: SuspensionGate(False, False, False, _ABANDON_ONLY),
    SuspensionState.SUSPENDED_BY_POLICY: SuspensionGate(False, False, False, _ABANDON_ONLY),
    SuspensionState.SUSPENDED_BY_ESCALATION: SuspensionGate(False, False, False, _ABANDON_ONLY),
    SuspensionState.SUSPENDED_BY_BUDGET: SuspensionGate(False, False, False, _ABANDON_ONLY),
    SuspensionState.SUSPENDED_BY_DRIFT: SuspensionGate(False, False, False, _ABANDON_ONLY),
    SuspensionState.SUSPENDED_BY_INTEGRITY: SuspensionGate(False, False, False, _ABANDON_ONLY),
}

#: §9.1's last row, enforced through :data:`SUSPENSION_GATE`.
SUSPENSION_GATE_ROW = "9.1-13"
SUSPENSION_GATE_ILLEGAL_BECAUSE = (
    "suspension is a hard gate; allowing progress would make it advisory"
)

#: §9.2's last row, same enforcement.
INTEGRITY_GATE_ROW = "9.2-6"
INTEGRITY_GATE_ILLEGAL_BECAUSE = (
    "the audit chain is untrusted; no state written under it is meaningful"
)

#: §0.1 itself, for a gated axis-1 transition §9.2 gives no row of its own.
GATE_ROW = "0.1"
GATE_ILLEGAL_BECAUSE = (
    "the axis-3 gate permits no transition to this state under this suspension"
)


def _index() -> dict:
    index: dict = {}
    for rule in LEGAL_TRANSITIONS:
        for edge in rule.edges():
            index.setdefault(edge, []).append(rule)
    return {edge: tuple(rules) for edge, rules in index.items()}


_EDGE_INDEX = _index()
_EDGE_KEYS = frozenset(_EDGE_INDEX)


def rules_for(
    axis: Axis, from_state: Optional[str], to_state: str
) -> tuple[TransitionRule, ...]:
    """Every legal row for one edge.

    More than one row can share an edge: §7.2 and §7.4 each carry a direct row
    and a `recovery.reconcile` row between the same two states, distinguished
    by `required_capability`. Resolution picks between them; this returns both.
    """
    return _EDGE_INDEX.get((axis, normalize_state(from_state), normalize_state(to_state)), ())


def illegal_transition_for(
    axis: Axis,
    from_state: Optional[str],
    to_state: Optional[str],
    facts: Iterable[Precondition] = (),
) -> Optional[IllegalTransition]:
    """The §9.1/§9.2 row forbidding this edge, if one does."""
    observed = set(facts)
    for rule in ILLEGAL_TRANSITIONS:
        if rule.matches(axis, from_state, to_state, observed):
            return rule
    return None


def illegal_operation_for(
    operation: Operation, actor_kind: ActorKind
) -> Optional[IllegalOperation]:
    """The §9.3 row forbidding this operation to this actor, if one does."""
    for rule in ILLEGAL_OPERATIONS:
        if rule.operation is operation and actor_kind in rule.actors:
            return rule
    return None


def legal_edges() -> frozenset:
    """Every edge of the graph. Mode-independent by construction (`INV-02`)."""
    return _EDGE_KEYS


def gate_admits(axis: Axis, to_state: str, suspension: SuspensionState) -> bool:
    """§0.1: may an axis-1/axis-2 transition to `to_state` run under this?

    The gate constrains axes 1 and 2 only — it is what a suspension *is*. Axis
    3 is how a suspension is set and cleared, so gating it on itself would make
    every suspension permanent, and the subordinate machines are gated through
    the operations §0.1 names (invocations, validations, commits) rather than
    through their own lifecycle.
    """
    if axis not in (Axis.PROJECT, Axis.STAGE):
        return True
    row = SUSPENSION_GATE[suspension]
    if ANY_STATE in row.lifecycle_targets:
        return True
    return normalize_state(to_state) in row.lifecycle_targets


def gate_citation(axis: Axis, suspension: SuspensionState) -> tuple[str, str]:
    """The §9 row a gate refusal cites, and its `illegal_because`."""
    if axis is Axis.PROJECT and suspension is SuspensionState.SUSPENDED_BY_INTEGRITY:
        return INTEGRITY_GATE_ROW, INTEGRITY_GATE_ILLEGAL_BECAUSE
    if axis is Axis.STAGE:
        return SUSPENSION_GATE_ROW, SUSPENSION_GATE_ILLEGAL_BECAUSE
    return GATE_ROW, GATE_ILLEGAL_BECAUSE
