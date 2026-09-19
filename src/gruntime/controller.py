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
        --project PROJECT_ID [--lease-ttl-ms MS]
        {start | invoke --run RUN_ID | commit --run RUN_ID --path P --content C
         | snapshot | recover}

`--repo` names the **user's checkout**: the runtime observes it and never
writes a file into it. Governed mutation happens in a dedicated worktree under
the governance directory (`worktree.py`), held under a repository lease
(`lease.py`).

`start` prints one JSON object carrying `controller_epoch`. The process is
always launched as `sys.executable -m gruntime.controller`; the runtime never
shells out to a bare interpreter name.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from .artifacts import ArtifactStore
from .canonical import canonical_json, digest_json
from .commit import (
    # `commit.authorize` and `commit.propose` are no longer named here: since
    # GR-28 a §7.4 event is labelled with the capability its row declares and
    # this channel proved, never with a literal chosen at the call site
    # (`F03-003`). `APPLY_CAPABILITY` remains for the receipt's own attribution.
    APPLY_CAPABILITY,
    build_receipt,
    build_trailers,
    commit_message,
    exact_paths,
    verify_receipt,
    evaluate_preconditions,
    expected_tree_digest,
    mint_operation_token,
)
from .decision import (
    derive_decision_state,
    drift_touches_scope,
    is_snapshot_bound,
    subject_scope,
)
from .errors import (
    BarrierViolation,
    CapabilityDenied,
    IntegrityViolation,
    PolicyDenied,
    ProtectedPathViolation,
)
from .gate import (
    AFTER_COMMIT_BEFORE_RECEIPT,
    AFTER_COMMIT_RECEIPT_INSERT,
    AFTER_INVOKE_BEFORE_RECEIPT,
    INSIDE_REPOSITORY_LEASE,
    gate,
)
from .lease import DEFAULT_TTL_MS, RepositoryLease
from .models import (
    ActorKind,
    ActorRef,
    ArtifactRef,
    Attribution,
    AuthMethod,
    CommitIntent,
    CommitIntentStatus,
    CommitPreconditions,
    CommitReceipt,
    Completeness,
    DecisionKind,
    DecisionScope,
    DecisionState,
    DecisionSubjectKind,
    EpistemicClass,
    Escalation,
    EscalationSeverity,
    EscalationStatus,
    EscalationTrigger,
    GovernanceMode,
    HumanDecision,
    Id,
    Independence,
    InvocationStatus,
    MutationOp,
    MutationProposal,
    Project,
    ProjectLifecycle,
    RealitySnapshot,
    ReviewAttestation,
    ReviewerKind,
    RunLifecycle,
    SnapshotTrigger,
    StageRun,
    SuspensionState,
    TerminationReason,
    Usage,
    VcsKind,
    Verdict,
    Verification,
    WorkerInvocation,
    WorkerReceipt,
    WorkerRole,
    is_terminal_status,
)
from .models import Review as ReviewRecord
from .repository import (
    WHOLE_WORKSPACE,
    assert_unprotected,
    derive_drift,
    effective_index,
    observe_filesystem,
    observe_repository,
    unattributed_paths,
    verify_head,
)
from .worktree import WorktreePlacement, ensure_worktree, governed_branch, worktree_root
from .authority import KERNEL_CAPABILITIES, REGISTER
from .policy import (
    PolicyOutcome,
    TransitionContext,
    TransitionProposal,
    TransitionResolution,
    capability_missing,
    resolve,
    select_rule,
)
from .transitions import normalize_state
from .provider import (
    DISPATCH_CAPABILITIES,
    RECOVERY_CAPABILITIES,
    GovernedProvider,
    InvocationRequest,
    ScopeView,
    WorkerProvider,
    status_for_outcome,
)
from .reconciliation import (
    Observation,
    clears_barrier,
    derive_reconciliation_state,
)
from .recovery import RecoveryOutcome, Resolution, Settlement, run_recovery
from .review import ATTEST_CAPABILITY, mint_attestation
from .store import SCHEMA_VERSION, StateStore, now_ts
from .transitions import ORIGIN, Axis, PolicyVerdict, rules_for
from .validation_controller import ValidationController

#: The binding the reference controller asks every provider for. Opaque to
#: core; the adapter decides what it means.
DEFAULT_BINDING = "default"

#: How long an invocation may run before `deadline_at` passes.
DEFAULT_DEADLINE = timedelta(hours=1)

#: Suspension values under which no new external effect may be initiated
#: (transition-matrix §0.1). Snapshots stay allowed in every one of them:
#: observing reality is how a suspension is ever cleared.
EFFECT_BARRING_SUSPENSIONS: frozenset[SuspensionState] = frozenset(
    state for state in SuspensionState if state is not SuspensionState.NONE
)


@dataclass(frozen=True)
class CreationObservation:
    """What a human is shown before they decide whether to create a project.

    Every field is taken from the observation event 0 actually recorded. It
    is the presentation, not a summary of one: `evidence_shown` carries the
    artifacts themselves, and `snapshot_id` names the reality they measure
    (domain-model.md:703, :709).
    """

    project_id: Id
    name: str
    slug: str
    workspace_root: str
    #: The governance mode the creating act would establish. Part of the
    #: presentation because it is part of the act: §2.23 row 1 makes the mode
    #: a predicate of `project.create` itself, so an approval that did not
    #: name it would be an approval of something less than the act.
    initial_mode: GovernanceMode
    snapshot_id: Id
    question: str
    options_offered: tuple[str, ...]
    evidence_shown: tuple[ArtifactRef, ...]


@dataclass(frozen=True)
class CreationResponse:
    """A human's answer, bound to the observation they were shown.

    `snapshot_id` is the answer's own statement of what it answers, and it is
    checked against the observation that was presented: an answer that names
    a different reality approves an unknown workspace. `signature` carries
    signature evidence where the approver authenticates by `SIGNATURE`.
    """

    snapshot_id: Id
    chosen: str
    justification: Optional[str] = None
    signature: Optional[str] = None


#: The presentation boundary: shown one observation, it returns the human's
#: answer to it. Mandatory — `HD-INV-2` makes an uninformed approval discharge
#: nothing, and a runtime-selected artifact index is a record of what the
#: runtime chose to show, not evidence that a human saw it (`DESIGN-04-036`).
CreationPresenter = Callable[[CreationObservation], Optional[CreationResponse]]


def _is_inert(value) -> bool:
    """Whether `value` is a built-in the runtime can hold without holding code.

    `type(value) is str` and not `isinstance`: a `str` subclass is a `str`
    everywhere except where it matters here, since it may define `__bool__`,
    `__str__`, `__eq__` or a property and take control at the moment the
    runtime evaluates it.
    """
    return value is None or type(value) is str


def _materialize(response: CreationResponse) -> CreationResponse:
    """The response's values, read once each and held as inert built-ins.

    A response arrives from outside the runtime, and every field on it is a
    place where someone else's code can run: an attribute access can be a
    property, a truthiness test can be `__bool__`, a format can be `__str__`.
    Evaluating any of them late — after the observation's freshness has been
    rechecked — would let the answer supersede the very thing it answers, and
    the approval would commit bound to a reality the human never saw
    (`GR27-R3`).

    So each field is read exactly once, here, while the project is still held
    against mutation (`_pending_genesis`) and before the freshness recheck;
    each must already be a plain built-in; and what the rest of the
    transaction sees is this record, on which nothing further can execute.
    A value-bearing field is refused at the read, so its code never runs at
    all rather than running somewhere the runtime has decided is safe.

    The refusal says so in constants. Naming the offending values' types
    would look up `__name__` on classes the same caller defined, and a
    metaclass property answers that lookup with code: diagnosing the refusal
    would be one more evaluation of the thing being refused, on the one path
    that exists precisely because the value must not be evaluated
    (`GR27-R6`). Which field is at fault is recoverable from the response the
    caller still holds; it is not worth an execution.
    """
    fields = (
        response.snapshot_id,
        response.chosen,
        response.justification,
        response.signature,
    )
    require(all(_is_inert(field) for field in fields), "a creation response carries plain built-in values and nothing that executes when it is read: each of (snapshot_id, chosen, justification, signature) must be a str, or None where the field is optional (GR27-R3)", IntegrityViolation)  # guard:creation_response_inert
    return CreationResponse(*fields)


def _answers(response: CreationResponse, observation: CreationObservation) -> bool:
    """Whether `response` is this observation's own answer.

    Binding only. That `response` is a `CreationResponse` at all is
    `guard:creation_response`'s invariant, and that its values are inert is
    `guard:creation_response_inert`'s; both are established before this is
    called, and re-checking either here would make its deletion unobservable.
    """
    return response.snapshot_id == observation.snapshot_id


#: The governance mode a creating act establishes. `AX-14`'s approval
#: authorizes the act; it does not choose the mode, and neither does the
#: runtime. A project reaches any other mode only by a later `SET_MODE`
#: decision under `project.mode.set`, which has no legal transition row in the
#: frozen matrix and is not implemented (DESIGN-04 §2.23 row 1, §6.1).
GENESIS_MODE = GovernanceMode.SUPERVISED


def creation_is_permitted_in(mode: GovernanceMode) -> bool:
    """Whether the `∅ → DRAFT` row admits `project.create` in `mode`.

    Read off row 2-1's own verdict column rather than copied from it, so the
    gate cannot drift away from the frozen cell it enforces
    (transition-matrix.md:84, authority-matrix.md:157). `AX-14`'s approval
    authorizes the act; it does not lift a `DENY`.
    """
    (rule,) = rules_for(Axis.PROJECT, ORIGIN, ProjectLifecycle.DRAFT.value)
    return rule.policy(mode).settle(()).verdict is not PolicyVerdict.DENY


#: The choices a creation presentation offers. `chosen` must be one of them
#: (domain-model.md:695-696, DESIGN-04 §2.23 row 5): a creation nobody could
#: have declined is not a decision.
CREATE_CHOICE = "CREATE"
DECLINE_CHOICE = "DECLINE"
CREATION_OPTIONS: tuple[str, ...] = (CREATE_CHOICE, DECLINE_CHOICE)


def _runtime_actor(component: str) -> ActorRef:
    """The kernel acting as itself. Never a worker, never a human."""
    return ActorRef(
        actor_kind=ActorKind.RUNTIME,
        actor_id=f"gruntime.{component}",
        auth_method=AuthMethod.NONE,
    )


#: `AX-16` caps a delegation chain at two links: the actor performing the act
#: and the principal whose decision authorizes it. Nobody acts for someone who
#: is themselves acting for a third party.
MAX_DELEGATION_DEPTH = 2


def _delegated_actor(component: str, principal: ActorRef) -> ActorRef:
    """The kernel performing an act the named principal decided (`AX-16`).

    The act stays the runtime's — it is the runtime that writes — but the
    authority is the human's, and the event says so rather than leaving the
    reader to find a `HUMAN` on some other record.
    """
    return ActorRef(
        actor_kind=ActorKind.RUNTIME,
        actor_id=f"gruntime.{component}",
        auth_method=AuthMethod.DELEGATED,
        on_behalf_of=principal,
    )


def delegation_depth(actor: ActorRef) -> int:
    """Links in this actor's delegation chain, the actor itself counting as 1."""
    depth = 1
    while actor.on_behalf_of is not None:
        depth += 1
        actor = actor.on_behalf_of
    return depth


#: Authentication methods that identify a principal. `NONE` and `DELEGATED`
#: do not: unauthenticated authority is indistinguishable from forged
#: authority (`HD-INV-1`).
AUTHENTICATED_METHODS: frozenset[AuthMethod] = frozenset(
    {AuthMethod.SESSION, AuthMethod.SIGNATURE, AuthMethod.MTLS}
)


def _is_authenticated_human(actor: ActorRef) -> bool:
    """Whether `actor` can hold a `HUMAN`-class exercise decision.

    A named principal, not merely a human-shaped record: the decision this
    actor authorizes is the whole authority for `∅ → DRAFT`, and an approval
    naming no key cannot be attributed to anyone afterwards.
    """
    return (
        actor.actor_kind is ActorKind.HUMAN
        and actor.auth_method in AUTHENTICATED_METHODS
        and bool(actor.principal_key_id)
    )


from .contract_controller import ContractController
from .contracts import new_id, require
from .decision import decision_content_hash


from .worker_controller import WorkerController
from .relay_controller import RelayController


class Controller(WorkerController, ContractController, ValidationController, RelayController):
    """Owns every state transition for one store."""

    def __init__(
        self,
        *,
        store: StateStore,
        artifacts: ArtifactStore,
        provider: WorkerProvider,
        repo: Optional[object] = None,
        governance_dir: Optional[Path] = None,
        lease_ttl_ms: int = DEFAULT_TTL_MS,
    ) -> None:
        self.store = store
        self.artifacts = artifacts
        self.secret_guard = store.secret_guard
        self.artifacts.secret_guard = self.secret_guard
        self._inference_relay = None
        self.provider = provider
        self.providers = {}
        self.register_provider(provider)
        #: The user's checkout: observed by every snapshot, written by nothing.
        self.repo = repo
        #: Where runtime-owned state that is not the workspace lives — the
        #: governed worktree and the repository lease. Never inside the
        #: workspace, or the runtime's own files would read as workspace drift.
        self.governance_dir = Path(governance_dir or store.db_path.parent)
        self.lease_ttl_ms = lease_ttl_ms
        #: Projects whose genesis transaction is open, each mapped to the
        #: token that authorizes *that* transaction's own appends. In memory
        #: and nowhere else: it is a property of this uncommitted transaction,
        #: not a durable fact about the project, and a controller that dies
        #: mid-genesis leaves nothing behind to clear — the transaction rolled
        #: back and the project never existed.
        self._genesis_pending: dict[Id, object] = {}
        #: The capabilities this controller holds as the runtime kernel
        #: (`AX-7`; authority-matrix §1 `RUNTIME_KERNEL`). One holder for the
        #: process, narrowed per call only where the design already narrows
        #: it: a reconciling settlement acts with `RECOVERY_CAPABILITIES`,
        #: which holds `recovery.reconcile` and nothing executable (`WP-16`).
        self.kernel_capabilities: frozenset[str] = KERNEL_CAPABILITIES

    # -- repository handles -------------------------------------------------

    def governed_repo(self, project_id: Id, *, create: bool = True):
        """The adapter rooted at this project's governed worktree.

        Every governed mutation goes here and the user's checkout goes
        untouched (`worktree.py`). With `create = False` the worktree is used
        only if it already exists, which is what recovery needs: creating one
        is a repository mutation, and `recovery.reconcile` authorizes
        observation only (authority-matrix §2.3).
        """
        if self.repo is None:
            raise IntegrityViolation("no repository adapter is configured")
        placement = self._placement(project_id)
        if placement.path.exists():
            return ensure_worktree(self.repo, placement)
        if not create:
            return self.repo
        # Creating a worktree writes to the repository, so it is taken under
        # the lease exactly as a commit is.
        with self.repository_lease(project_id):
            return ensure_worktree(self.repo, placement)

    def _placement(self, project_id: Id) -> WorktreePlacement:
        project = self.store.get_project(project_id)
        return WorktreePlacement(
            path=worktree_root(self.governance_dir, project_id),
            branch=governed_branch(project_id),
            workspace_root=Path(project.workspace_root),
        )

    def repository_lease(self, project_id: Id) -> RepositoryLease:
        """A fresh lease handle on the repository this project mutates.

        Held only across a mutation. A controller killed mid-mutation leaves
        the record behind, and the next controller waits out its expiry rather
        than asking whether a pid is still alive (`lease.py`).

        Not issued against a project whose creation transaction is still open.
        Everything taken under this lease is a mutation of the repository, not
        of the store — a worktree directory, a branch, a lease record — and
        none of it is inside the transaction that would roll back, nor
        attested by any event. `governed_repo` creates a worktree under this
        lease and a pending project can have none already, so refusing here
        refuses that too, and one boundary covers the whole repository side
        (`GR27-R4`).
        """
        require(self._genesis_admits(project_id), f"project {project_id} is mid-genesis: its creation transaction is open, and a repository mutation taken under this lease would outlive a rollback with no event attesting it", IntegrityViolation)  # guard:repository_lease_pending_genesis
        if self.repo is None:
            raise IntegrityViolation("no repository adapter is configured")
        project = self.store.get_project(project_id)
        return RepositoryLease(
            self.governance_dir / "leases",
            Path(self.repo.root),
            holder_id=f"{project_id}:{project.controller_epoch}:{os.getpid()}",
            ttl_ms=self.lease_ttl_ms,
            controller_epoch=project.controller_epoch,
        )

    # -- internals ---------------------------------------------------------

    def _append(
        self,
        project_id: Id,
        *,
        event_type: str,
        epistemic_class: EpistemicClass,
        subject: dict,
        payload: dict,
        capability_used: Optional[str] = None,
        authority_ref: Optional[Id] = None,
        causal_parent: Optional[Id] = None,
        component: str = "controller",
        actor: Optional[ActorRef] = None,
        genesis_token: object = None,
    ):
        """Append one event, by default as the kernel acting as itself.

        `actor` names a different holder for the few acts the design does not
        let the runtime hold: `decision.record` is `AX-15`'s, held by the
        deciding human, and a runtime-performed act mediated under `AX-16`
        carries that human in `on_behalf_of`. Everything else is the
        runtime's own work and takes the default.

        `genesis_token` is how `_genesis` appends its own four events against
        a project it is simultaneously holding against everyone else. It is
        not a parameter of any public method: nothing a presenter, a response
        or a finalizer can call passes one, so every such caller arrives with
        the default and is measured against the hold (`GR27-R5`).
        """
        require(self._genesis_admits(project_id, genesis_token), f"project {project_id} is mid-genesis: its creation transaction is open from the presentation boundary to the commit, and appending {event_type!r} would put a fifth event inside AX-17's four-event witness", IntegrityViolation)  # guard:genesis_pending_mutation
        holder = actor or _runtime_actor(component)
        require(delegation_depth(holder) <= MAX_DELEGATION_DEPTH, f"an event's actor may delegate once: {holder.actor_id} stands at delegation depth {delegation_depth(holder)}, over the maximum of {MAX_DELEGATION_DEPTH} (AX-16)", IntegrityViolation)  # guard:delegation_depth
        return self.store.append_event(
            project_id,
            event_type=event_type,
            epistemic_class=epistemic_class,
            actor=holder,
            subject={key: str(value) for key, value in subject.items()},
            payload=canonical_json(payload),
            capability_used=capability_used,
            authority_ref=authority_ref,
            causal_parent=causal_parent,
        )

    def pending_genesis(self) -> frozenset:
        """The projects this controller is mid-genesis on. Diagnostic.

        The ids only. The tokens that authorize each transaction's own appends
        are not published here, and no other method publishes them either.
        """
        return frozenset(self._genesis_pending)

    def _genesis_admits(self, project_id: Id, genesis_token: object = None) -> bool:
        """Whether a mutation of `project_id` may proceed at all.

        One question, asked in front of every durable write that can reach a
        project whose creation transaction is still open — not only in front
        of the append. `GR27-R4` is what happens when it is asked too late:
        `start` bumps the controller epoch and `author_contract` stores the
        contract row *before* either appends, so a presenter that swallowed
        the append's refusal committed a durable mutation with no event to
        account for it.

        Admission is by token identity, never by a time window. A window
        would be open during genesis's own writes, and a finalizer runs
        exactly there: it would inherit whatever the runtime had granted
        itself for the instant it was running in (`GR27-R5`). The token is a
        fresh object held only by the transaction that created it and passed
        only down `_genesis`'s own calls, so possession is the whole
        predicate.

        Python offers no privacy stronger than this, and none is claimed: code
        that reaches into `_genesis_pending` could equally reach into
        `store.connection`. What the boundary guarantees is that no *public*
        controller API carries a token parameter, so no presenter, response
        value or finalizer acquires one by calling the runtime normally.
        """
        return self._genesis_pending.get(project_id, genesis_token) is genesis_token  # guard:genesis_admission

    @contextmanager
    def _pending_genesis(self, project_id: Id):
        """Hold `project_id` against everyone but this transaction, and yield
        the token that excepts this transaction.

        `AX-17` is one transaction of four ordered events, and events 0 and 2
        sit either side of a callback into code the runtime does not own. A
        presenter that calls back into the controller against the project
        being created would append a fifth event between them, and what
        committed would no longer be the witness (`GR27-R2`).

        The hold spans the **whole** transaction — `BEGIN` to `COMMIT` or
        `ROLLBACK` — and not merely the presentation. A response object stays
        alive until `_genesis`'s frame is torn down, and its finalizer then
        runs after the freshness recheck, after the approval and before the
        commit; a hold that ended with the presentation left exactly that
        interval open (`GR27-R5`). Nothing here depends on when the finalizer
        runs, because there is no moment inside the transaction at which the
        hold is off.

        The hold is released on every exit, not the successful one: a
        presenter that raises, a human who declines and a refused response all
        leave the controller able to create the next project. It names one
        project, so an unrelated project — nobody's open transaction — stays
        operable from inside a presentation.
        """
        token = object()
        self._genesis_pending[project_id] = token
        try:
            yield token
        finally:
            self._genesis_pending.pop(project_id, None)

    def _project_of_run(self, run_id: Id) -> Id:
        return self.store.get_run(run_id).project_id

    def _state_of(self, record, project_epoch: int):
        """This record's reconciliation state, through the single derivation."""
        status = getattr(record, "status")
        return derive_reconciliation_state(
            record_epoch=record.controller_epoch,
            project_epoch=project_epoch,
            status_terminal=is_terminal_status(status),
            prior=record.reconciliation_state,
        )

    def _assert_barrier_clear(self, run_id: Id, what: str) -> None:
        """`RUN-INV-3`: no new external effect while a record is unsettled.

        The state is re-derived here rather than read, so a run that outlived a
        controller is held even if nothing has refreshed its stored value yet.
        """
        project_id = self._project_of_run(run_id)
        project_epoch = self.store.get_project(project_id).controller_epoch
        held: list[str] = []
        held.extend(self._pending_validations(run_id))  # guard:validation_barrier
        for invocation in self.store.list_invocations(run_id):
            if not clears_barrier(self._state_of(invocation, project_epoch)):
                held.append(invocation.invocation_id)
        for intent in self.store.list_commit_intents(run_id):
            if not clears_barrier(self._state_of(intent, project_epoch)):
                held.append(intent.intent_id)
        if held:
            raise BarrierViolation(
                f"{what} refused: run {run_id} has unreconciled operations "
                + ", ".join(held)
                + " (RUN-INV-3). Reconcile them first; recovery is the only "
                "thing permitted under the barrier."
            )

    def _assert_may_initiate_effect(self, project_id: Id, what: str) -> None:
        """The gate in front of every new external effect.

        Two conditions, both hard, neither of which gates observation:

        1. **Suspension** (transition-matrix §0.1). Every non-`NONE` value
           denies new worker invocations, new validations and new commits.
        2. **Completeness.** If the last look at the workspace did not succeed,
           the runtime does not know what it would be acting on. "Cannot
           observe" and "observed no change" are different claims, and only
           the second one licenses an effect.

        Condition 2 reads the *latest* snapshot, not `snapshot_current`, which
        by construction names the newest `COMPLETE` one — a failed observation
        would otherwise be invisible to the gate that exists to notice it.

        A single failure does not suspend the project: it is a fact about one
        observation, not a finding about the workspace, and the next successful
        snapshot lifts the gate with no human in the loop. Snapshots are never
        gated here, which is what makes that recovery possible.
        """
        suspension = self.store.get_project(project_id).suspension
        if suspension in EFFECT_BARRING_SUSPENSIONS:
            raise PolicyDenied(
                f"{what} refused: project {project_id} is {suspension.value}. "
                "Suspension is a hard gate; allowing progress would make it "
                "advisory (transition-matrix §0.1, §9.1 last row)."
            )
        latest = self.store.latest_snapshot(project_id)
        if latest is not None and latest.completeness is not Completeness.COMPLETE:
            raise PolicyDenied(
                f"{what} refused: the last observation of the workspace "
                f"({latest.snapshot_id}) is {latest.completeness.value}, so "
                "the runtime cannot say what it would be acting on. Take a "
                "COMPLETE snapshot first (RS-INV-1)."
            )

    def _set_suspension(
        self,
        project_id: Id,
        suspension: SuspensionState,
        *,
        reason: str,
        suspension_ref: Optional[Id] = None,
    ) -> None:
        """Write axis 3, and only axis 3 (`O-3`, `G-8`).

        The lifecycle value is left exactly as it was: a suspended project
        resumes into the value it held, because suspension is read alongside a
        lifecycle and never encodes one.
        """
        self.store.validate_suspension_ref(suspension, suspension_ref)  # guard:suspension_ref_transition
        project = self.store.get_project(project_id)
        if project.suspension is suspension and project.suspension_ref == suspension_ref:
            return
        capability = (
            "suspension.clear"
            if suspension is SuspensionState.NONE
            else "suspension.set"
        )
        self._append(
            project_id,
            event_type="suspension.set",
            epistemic_class=EpistemicClass.AUTHORITY,
            subject={"project_id": project_id},
            payload={
                "from": project.suspension.value,
                "to": suspension.value,
                "reason": reason,
                "suspension_ref": suspension_ref,
            },
            capability_used=capability,
        )
        # Written through a targeted update: the append above already advanced
        # `event_head` and `event_seq`, and a whole-row write from the copy
        # read before it would roll the chain back onto a spent sequence.
        self.store.set_project_suspension(
            project_id, suspension, suspension_ref=suspension_ref
        )

    def _raise_escalation(
        self,
        project_id: Id,
        *,
        trigger: EscalationTrigger,
        severity: EscalationSeverity,
        summary: str,
        run_id: Optional[Id] = None,
        suspension: SuspensionState = SuspensionState.SUSPENDED_BY_INTEGRITY,
    ) -> Id:
        escalation = Escalation(
            escalation_id=f"esc-{uuid.uuid4().hex}",
            project_id=project_id,
            trigger=trigger,
            severity=severity,
            summary=summary,
            raised_by=_runtime_actor("escalation"),
            raised_at=now_ts(),
            suspension_applied=suspension,
            suspension_target=(
                "NONE" if suspension is SuspensionState.NONE else ("RUN" if run_id else "PROJECT")
            ),
            status=EscalationStatus.OPEN,
            run_id=run_id,
        )
        # A suspension claim and its axis-3 writes become observable together.
        # SAVEPOINT also composes with activation and commit receipt transactions.
        db = self.store.connection
        db.execute("SAVEPOINT escalation_raise")
        try:
            self._append(
                project_id,
                event_type="escalation.raised",
                epistemic_class=EpistemicClass.CLAIM,
                subject={"escalation_id": escalation.escalation_id},
                payload={
                    "trigger": trigger.value,
                    "severity": severity.value,
                    "summary": summary,
                    "run_id": run_id,
                },
                capability_used="escalation.raise",
            )
            self.store.put_escalation(escalation)
            self._apply_escalation_suspension(escalation)  # guard:escalation_suspension_applied
            db.execute("RELEASE escalation_raise")
        except BaseException:
            db.execute("ROLLBACK TO escalation_raise")
            db.execute("RELEASE escalation_raise")
            raise
        return escalation.escalation_id

    def _apply_escalation_suspension(self, escalation: Escalation) -> None:
        suspension = escalation.suspension_applied
        if suspension is SuspensionState.NONE:
            return
        self._set_suspension(
            escalation.project_id, suspension,
            reason=escalation.summary, suspension_ref=escalation.escalation_id,
        )
        if escalation.run_id is not None:
            run = self.store.get_run(escalation.run_id)
            self._append(
                escalation.project_id,
                event_type="suspension.set",
                epistemic_class=EpistemicClass.AUTHORITY,
                subject={"run_id": run.run_id},
                payload={"from": run.suspension.value, "to": suspension.value,
                         "reason": escalation.summary, "suspension_ref": escalation.escalation_id},
                capability_used="suspension.set",
            )
            run.suspension = suspension
            self.store.put_run(run)  # guard:escalation_run_suspension

    # -- project and run ---------------------------------------------------

    def create_project(
        self,
        *,
        name: str,
        slug: str,
        workspace_root: str,
        approved_by: ActorRef,
        present: CreationPresenter,
        initial_mode: GovernanceMode,
        justification: str = "project creation approved",
    ) -> Id:
        """Create a project at `DRAFT`, under the four-event genesis witness.

        `∅ → DRAFT` is a `HUMAN`-class row whose policy verdict is `AUTO`
        **under `SUPERVISED` only**: its `AUTONOMOUS` cell is `DENY`
        (transition-matrix.md:84, authority-matrix.md:157). Where the row is
        admitted the policy engine contributes nothing further to its
        authority, and a `HumanDecision{kind: APPROVE}` over the project is
        what authorizes it (`AX-14`, `R3.6`). `approved_by` is the human who
        made it; what they were shown and what they answered come from
        `present`, below.

        `initial_mode` is the mode the creating act establishes — a required,
        human-supplied field of the created `Project` (domain-model.md:138) —
        and it is the value the mode gate is evaluated against, since creation
        is the one act with no prior project to read. It has no default: a
        runtime that chose it would be establishing a governance mode nobody
        asked for, and the caller must name it.

        Two independent conditions admit it, and both are necessary:

        1. the frozen policy cell for `∅ → DRAFT` must not be `DENY` in that
           mode (transition-matrix.md:84, authority-matrix.md:157), read off
           the matrix row itself rather than copied from it;
        2. it must be `GENESIS_MODE`. Non-`DENY` is not sufficient. `AX-17`'s
           creating act is specified at `SUPERVISED` (§2.23 row 1), and a
           later change that made some other cell admissible would not thereby
           make that mode one a creating act may establish — the only route to
           another mode is a `SET_MODE` decision under `project.mode.set`,
           which has no legal transition row in the frozen matrix and is not
           implemented here (`DESIGN-04-032`, DESIGN-04 §2.23 row 1, §6.1).

        The mode is also part of the presentation: what the human approves is
        this project *under this governance mode*, and the value they are
        shown is the value installed.

        One store transaction, four ordered events (`AX-17`):

        ===  ===============================  ====================
        seq  event                            capability
        ===  ===============================  ====================
        0    the `RealitySnapshot`            `snapshot.take`
        1    the approval reaching `VALID`    `decision.record`
        2    `∅ → DRAFT`                      `project.create`
        3    the approval `VALID → CONSUMED`  `audit.append`
        ===  ===============================  ====================

        Each event names exactly one capability (`G-4`), which is why the
        recording cannot be merged into the creation. The project row is
        installed by the `seq = 0` write, so the chain state is never
        uninitialized for any reader (evidence-model §3.1 step 6 as amended),
        and at commit `event_seq = 3` with `event_head` at event 3.

        Nothing is observable until the transaction commits: a failure
        anywhere in the four publishes no project, no event and no snapshot.
        The approval is snapshot-bound (`R3.7`), so it binds to event 0's
        snapshot and an observation that did not succeed refuses the creation
        rather than approving an unknown workspace.

        `present` is the presentation boundary and is mandatory. It is shown
        event 0's observation — the snapshot it recorded and the artifacts
        themselves — and returns the human's `CreationResponse` to *that*
        observation. Creation is refused if no conforming response comes
        back, if the response names a different observation, if the human
        declines, or if reality was observed again while the presentation was
        open. Its `signature` is the approver's signature evidence, required
        where they authenticate by `SIGNATURE`. Nothing here labels a
        runtime-selected artifact index as human-seen: what is recorded as
        `evidence_shown` is what the presentation carried
        (domain-model.md:703, :709, `HD-INV-2`, `DESIGN-04-036`).
        """
        require(_is_authenticated_human(approved_by), "project creation requires an authenticated human approval (AX-14)", IntegrityViolation)  # guard:genesis_approver
        require(creation_is_permitted_in(initial_mode), f"project.create is DENY in {initial_mode.value} (authority-matrix.md:157, transition-matrix.md:84); the frozen policy cell for this mode admits no creating act", PolicyDenied)  # guard:genesis_initial_mode
        require(initial_mode is GENESIS_MODE, f"a project is created {GENESIS_MODE.value} and reaches another mode only by a later SET_MODE decision: {initial_mode.value} is not a mode a creating act establishes, whatever its policy cell says (DESIGN-04 §2.23 row 1)", PolicyDenied)  # guard:genesis_mode_is_supervised
        project_id = new_id()
        db = self.store.connection
        # The hold is taken around the transaction, not around the
        # presentation: it must still be on when the last thing the
        # transaction touched is finalized, and off once the transaction is
        # closed either way (`GR27-R5`).
        with self._pending_genesis(project_id) as genesis_token:
            db.execute("BEGIN IMMEDIATE")
            try:
                self._genesis(
                    project_id,
                    name=name,
                    slug=slug,
                    workspace_root=workspace_root,
                    approved_by=approved_by,
                    present=present,
                    initial_mode=initial_mode,
                    justification=justification,
                    genesis_token=genesis_token,
                )
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")  # guard:genesis_rollback
                raise
        return project_id

    def _genesis(
        self,
        project_id: Id,
        *,
        name: str,
        slug: str,
        workspace_root: str,
        approved_by: ActorRef,
        present: CreationPresenter,
        initial_mode: GovernanceMode,
        justification: str,
        genesis_token: object,
    ) -> None:
        """The four appends of `AX-17`, inside the caller's transaction.

        The caller holds the project and hands the hold's token down. Every
        append below carries it and no other caller has it, which is what lets
        one transaction write four events against a project that is otherwise
        immutable for the whole time it is open.
        """
        created_at = now_ts()
        snapshot, fingerprint, _ = self._observe_reality(
            project_id,
            workspace_root=workspace_root,
            trigger=SnapshotTrigger.ON_DEMAND,
            previous=None,
            attributed=(),
        )
        genesis = self._append_snapshot(
            project_id, snapshot, fingerprint, genesis_token=genesis_token
        )
        # The `seq = 0` write installs the project and initializes its chain
        # state together; events 1-3 reserve their `seq` from this row.
        self.store.put_project(
            Project(
                project_id=project_id,
                name=name,
                slug=slug,
                schema_version=SCHEMA_VERSION,
                lifecycle=ProjectLifecycle.DRAFT,
                suspension=SuspensionState.NONE,
                governance_mode=initial_mode,
                workspace_root=workspace_root,
                created_at=created_at,
                updated_at=created_at,
                # `Project.created_by` is the approving human, never the
                # runtime that performed the write: a runtime cannot
                # originate a project and thereby its own ceiling
                # (domain-model.md:150, transition-matrix.md:485).
                created_by=approved_by,
                event_head=genesis.event_hash,
                event_seq=genesis.seq,
                controller_epoch=0,
            )
        )
        self._publish_snapshot(project_id, snapshot)
        # The observation is *shown* and answered before anything is decided.
        # What the human was shown is the observation event 0 recorded: the
        # index of the workspace being taken under governance.
        observation = CreationObservation(
            project_id=project_id,
            name=name,
            slug=slug,
            workspace_root=workspace_root,
            initial_mode=initial_mode,
            snapshot_id=snapshot.snapshot_id,
            question=(
                f"Create project {name} ({slug}) at {workspace_root} "
                f"under {initial_mode.value} governance?"
            ),
            options_offered=CREATION_OPTIONS,
            evidence_shown=(snapshot.file_index_ref,),
        )
        # Everything from here to the commit happens with the project held
        # against mutation, and the presentation ends with the freshness
        # recheck — so nothing the runtime does not own runs between that
        # recheck and the decision it authorizes, and nothing it does not own
        # writes at all until the transaction is closed.
        response = present(observation)
        require(isinstance(response, CreationResponse), "creation needs a human's answer to the observation it presented; no conforming response was given (HD-INV-2, domain-model.md:709)", IntegrityViolation)  # guard:creation_response
        answer = _materialize(response)
        require(_answers(answer, observation), f"the response answers a different observation: it names {answer.snapshot_id!r}, and {observation.snapshot_id!r} is what was presented (domain-model.md:703)", IntegrityViolation)  # guard:creation_response_binding
        require(answer.chosen == CREATE_CHOICE, f"the human declined: they chose {answer.chosen!r} over {CREATE_CHOICE!r}", IntegrityViolation)  # guard:creation_response_approves
        require(self._is_current_observation(project_id, observation.snapshot_id), f"reality was observed again while the presentation was open: {observation.snapshot_id} is no longer the current observation, so what was approved is not what would be created (HD-INV-4)", IntegrityViolation)  # guard:creation_observation_fresh
        approval = self._record_decision(
            project_id,
            decision_kind=DecisionKind.APPROVE,
            subject_kind=DecisionSubjectKind.PROJECT,
            subject_id=project_id,
            question=observation.question,
            options_offered=observation.options_offered,
            chosen=answer.chosen,
            justification=answer.justification or justification,
            decided_by=approved_by,
            signature=answer.signature,
            # The observation that was approved, named rather than looked up:
            # `subject_snapshot_id` is the reality the human actually approved
            # (domain-model.md:703), which is not necessarily whatever the
            # store would report as newest at this instant.
            approved_snapshot_id=observation.snapshot_id,
            evidence_shown=observation.evidence_shown,
            genesis_token=genesis_token,
        )
        created = self._append(
            project_id,
            event_type="project.created",
            epistemic_class=EpistemicClass.AUTHORITY,
            subject={"project_id": project_id},
            payload={
                "name": name,
                "slug": slug,
                "workspace_root": workspace_root,
                "schema_version": SCHEMA_VERSION,
                "lifecycle": ProjectLifecycle.DRAFT.value,
                "snapshot_id": snapshot.snapshot_id,
            },
            capability_used="project.create",
            # `AX-16`: the runtime writes, the human decided, and the event
            # carries both — the delegation and the decision it rests on.
            actor=_delegated_actor("controller", approved_by),
            genesis_token=genesis_token,
            authority_ref=approval.decision_id,  # guard:genesis_authority_ref
        )
        self._consume_decision(project_id, approval, discharged=created, genesis_token=genesis_token)  # guard:genesis_consumed

    def _is_own_complete_observation(self, project_id: Id, snapshot_id: Id) -> bool:
        """Whether `snapshot_id` is a `COMPLETE` observation of this project.

        Identity, not currency. This is what makes an explicitly named
        approved snapshot a real observation of the right workspace rather
        than an id the caller invented or borrowed from elsewhere. Whether it
        is still the *current* observation is a different question, asked by
        `_is_current_observation` at the boundary that presented it — keeping
        the two apart is what stops either check from standing in for the
        other (`GR27-R3`).
        """
        try:
            snapshot = self.store.get_snapshot(snapshot_id)
        except KeyError:
            return False
        return (
            snapshot.project_id == project_id
            and snapshot.completeness is Completeness.COMPLETE
        )

    def _is_current_observation(self, project_id: Id, snapshot_id: Id) -> bool:
        """Whether `snapshot_id` is still this project's newest `COMPLETE` one.

        Rechecked after the human answers and before the transaction commits:
        an approval over a superseded observation is `HD-INV-4`'s stale
        approval, and creating from one would publish a project nobody
        approved the reality of.
        """
        current = self.store.newest_complete_snapshot(project_id)
        return current is not None and current.snapshot_id == snapshot_id

    def _consume_decision(
        self,
        project_id: Id,
        decision: HumanDecision,
        *,
        discharged,
        genesis_token: object = None,
    ) -> None:
        """`VALID → CONSUMED` (transition-matrix §7.5-2).

        A decision recorded for a transition is spent by the transition it
        discharged; the event cites that transition's event and the nonce is
        never replayable (`HD-INV-3`).
        """
        state = derive_decision_state(decision, now=now_ts(), consumed=True)
        self._append(
            project_id,
            event_type="decision.state_derived",
            epistemic_class=EpistemicClass.EVIDENCE,
            subject={"decision_id": decision.decision_id},
            payload={
                "from": decision.decision_state.value,
                "to": state.value,
                "discharged": discharged.event_id,
            },
            capability_used="audit.append",
            causal_parent=discharged.event_id,
            component="decision",
            genesis_token=genesis_token,
        )
        decision.decision_state = state
        self.store.put_decision(decision)

    def start(self, project_id: Id) -> int:
        """Increment `controller_epoch` and return the new value.

        `P-INV-4`: the increment is committed before this controller does any
        other work, so an operation carrying a lower epoch is provably the
        work of a controller that is gone.

        The bump is durable and precedes its own event, so the pending-genesis
        boundary is asked in front of it rather than in front of the append: a
        presenter that called this against the project being created and
        swallowed the append's refusal would have committed an epoch no
        `controller.started` event accounts for (`GR27-R4`).
        """
        require(self._genesis_admits(project_id), f"project {project_id} is mid-genesis: its creation transaction is open, and bumping the controller epoch would durably mutate a project that no commit has yet established", IntegrityViolation)  # guard:start_pending_genesis
        epoch = self.store.bump_controller_epoch(project_id)
        self._append(
            project_id,
            event_type="controller.started",
            epistemic_class=EpistemicClass.AUTHORITY,
            subject={"project_id": project_id},
            payload={"controller_epoch": epoch, "pid": os.getpid()},
            capability_used="controller.start",
        )
        self._refresh_reconciliation_states(project_id, epoch)
        return epoch

    def _refresh_reconciliation_states(self, project_id: Id, epoch: int) -> None:
        """Re-derive every older record's state under the new epoch.

        This records the barrier the restart just raised. It is a derivation,
        not a resolution: nothing is looked up and nothing is settled here.
        """
        changed: list[dict] = []
        for invocation in self.store.list_unreconciled_invocations(project_id):
            state = self._state_of(invocation, epoch)
            if state is not invocation.reconciliation_state:
                invocation.reconciliation_state = state
                changed.append(
                    {"id": invocation.invocation_id, "state": state.value}
                )
                self.store.put_invocation(invocation, project_id)
        for intent in self.store.list_unreconciled_intents(project_id):
            state = self._state_of(intent, epoch)
            if state is not intent.reconciliation_state:
                intent.reconciliation_state = state
                changed.append({"id": intent.intent_id, "state": state.value})
                self.store.put_commit_intent(intent, project_id)
        if changed:
            self._append(
                project_id,
                event_type="reconciliation.derived",
                epistemic_class=EpistemicClass.EVIDENCE,
                subject={"project_id": project_id},
                payload={"controller_epoch": epoch, "records": changed},
            )

    def open_run(self, project_id: Id) -> Id:
        """Allocate a `StageRun` under the current epoch."""
        project = self.store.get_project(project_id)
        run_id = new_id()
        run = StageRun(
            run_id=run_id,
            project_id=project_id,
            stage_id=new_id(),
            lifecycle=RunLifecycle.ALLOCATED,
            suspension=SuspensionState.NONE,
            controller_epoch=project.controller_epoch,
            started_at=now_ts(),
        )
        self._append(
            project_id,
            event_type="run.allocated",
            epistemic_class=EpistemicClass.AUTHORITY,
            subject={"run_id": run_id, "stage_id": run.stage_id},
            payload={"controller_epoch": run.controller_epoch},
            capability_used="run.start",
        )
        self.store.put_run(run)
        return run_id

    # -- reality (domain-model §9.D) ---------------------------------------

    def _observe(self, workspace_root: str):
        """Fingerprint the workspace: tracked reality only.

        The user's checkout is what is measured, never the governed worktree:
        the worktree is the runtime's own scratch space and measuring it would
        make the runtime's activity indistinguishable from the world's.

        Takes the root rather than a project id because the genesis
        observation happens before the project row exists (`AX-17`).
        """
        if self.repo is not None:
            workspace = Path(workspace_root).resolve()
            if workspace == Path(self.repo.root).resolve():
                return observe_repository(self.repo, scope=WHOLE_WORKSPACE)
        return observe_filesystem(Path(workspace_root), scope=WHOLE_WORKSPACE)

    def _attributed_globs(self, project_id: Id) -> tuple[str, ...]:
        """The paths the runtime declared it was changing.

        Every path named by a `CommitIntent` of this project that has been
        authorized or applied. A change anywhere else is not the runtime's, and
        that is precisely what `unattributed` counts (domain-model §9.B.1).
        """
        declared: set[str] = set()
        for run in self.store.list_runs(project_id):
            for intent in self.store.list_commit_intents(run.run_id):
                if intent.status is CommitIntentStatus.PROPOSED:
                    continue
                for mutation in intent.mutations:
                    declared.add(mutation.path)
                    if mutation.rename_to is not None:
                        declared.add(mutation.rename_to)
        return tuple(sorted(declared))

    def take_snapshot(
        self,
        project_id: Id,
        *,
        trigger: SnapshotTrigger = SnapshotTrigger.ON_DEMAND,
    ) -> Id:
        """Take a `RealitySnapshot` — the only source of truth about the
        workspace (`RS-INV-1`).

        Three things happen, in this order, and each one is separately audited:

        1. the workspace is fingerprinted (`repository.py`, which documents
           exactly what the hash covers and what it deliberately does not);
        2. drift against the previous snapshot is derived, and
           `unattributed > 0` raises `REALITY_DRIFT` and sets
           `SUSPENDED_BY_DRIFT` (transition-matrix §4);
        3. every snapshot-bound `HumanDecision` whose bound snapshot this one
           supersedes inside the subject's scope goes `STALE` (`HD-INV-4`).

        Taking a snapshot is always permitted, under every suspension value
        (§0.1): observing reality is the only way a suspension raised by drift
        is ever cleared. It is not permitted against a project whose creation
        transaction is still open: the observation is stored as a
        content-addressed artifact before any event is appended, and a blob
        outlives the rollback of the transaction that wrote it. The boundary
        is therefore in front of the observation, and a second observation of
        the pending project never happens rather than happening and then
        failing to be recorded (`GR27-R4`, `GR27-R5`).
        """
        require(self._genesis_admits(project_id), f"project {project_id} is mid-genesis: its creation transaction is open, and observing it again would supersede the very observation its approval is bound to", IntegrityViolation)  # guard:snapshot_pending_genesis
        project = self.store.get_project(project_id)
        # The baseline is the newest `COMPLETE` snapshot, not merely the last
        # one: a failed observation is neither a baseline nor a comparand
        # (`RS-INV-1`). Comparing against one would report the whole workspace
        # as having vanished and then reappeared.
        previous = self.store.newest_complete_snapshot(project_id)
        snapshot, fingerprint, drifted = self._observe_reality(
            project_id,
            workspace_root=project.workspace_root,
            trigger=trigger,
            previous=previous,
            attributed=self._attributed_globs(project_id),
        )
        self._append_snapshot(project_id, snapshot, fingerprint)
        self._publish_snapshot(project_id, snapshot)
        # A derived `drift_summary` is exactly the comparable case: both ends
        # were real observations of the same project.
        if snapshot.drift_summary is not None:
            self._stale_decisions_against(project_id, previous, snapshot)
        if drifted:
            self._on_reality_drift(project_id, snapshot, drifted)
        return snapshot.snapshot_id

    def _observe_reality(
        self,
        project_id: Id,
        *,
        workspace_root: str,
        trigger: SnapshotTrigger,
        previous: Optional[RealitySnapshot],
        attributed: Sequence[str],
    ) -> tuple[RealitySnapshot, object, tuple[str, ...]]:
        """Fingerprint the workspace and derive the `RealitySnapshot` for it.

        Nothing here reads or writes the project row, which is what lets the
        genesis observation precede the project's existence (`AX-17`).
        """
        fingerprint = self._observe(workspace_root)
        index_ref = self.store.store_artifact(
            canonical_json(fingerprint.document()), media_type="application/json"
        )
        drift = None
        drifted: tuple[str, ...] = ()
        after = fingerprint.effective_index()
        # Both ends must be real observations. Comparing a `FAILED` one to a
        # `COMPLETE` one reports the whole workspace as having vanished, which
        # would suspend the project for a transient disk fault.
        comparable = (
            previous is not None
            and fingerprint.completeness is Completeness.COMPLETE
        )
        if comparable:
            before = self._effective_index_of(previous)
            drift = derive_drift(before, after, attributed=attributed)
            drifted = unattributed_paths(before, after, attributed=attributed)

        snapshot = RealitySnapshot(
            snapshot_id=f"snap-{uuid.uuid4().hex}",
            project_id=project_id,
            taken_at=now_ts(),
            taken_by=_runtime_actor("snapshot"),
            trigger=trigger,
            completeness=fingerprint.completeness,
            tree_digest=fingerprint.tree_digest,
            file_index_ref=index_ref,
            file_count=len(after),
            byte_count=fingerprint.byte_count,
            snapshot_hash=fingerprint.snapshot_hash,
            scope=fingerprint.scope,
            vcs_state=fingerprint.vcs_state(),
            drift_vs=None if previous is None else previous.snapshot_id,
            drift_summary=drift,
        )
        return snapshot, fingerprint, drifted

    def _append_snapshot(
        self,
        project_id: Id,
        snapshot: RealitySnapshot,
        fingerprint,
        *,
        genesis_token: object = None,
    ):
        """Record the observation under `snapshot.take`."""
        drift = snapshot.drift_summary
        return self._append(
            project_id,
            event_type="snapshot.taken",
            epistemic_class=EpistemicClass.EVIDENCE,
            subject={"snapshot_id": snapshot.snapshot_id},
            payload={
                "trigger": snapshot.trigger.value,
                "completeness": snapshot.completeness.value,
                "snapshot_hash": snapshot.snapshot_hash,
                "tree_digest": snapshot.tree_digest,
                "dirty_digest": fingerprint.dirty_digest,
                "file_count": snapshot.file_count,
                "byte_count": snapshot.byte_count,
                "untracked_excluded": fingerprint.untracked_count,
                "drift_vs": snapshot.drift_vs,
                "drift_summary": None
                if drift is None
                else {
                    "added": drift.added,
                    "removed": drift.removed,
                    "modified": drift.modified,
                    "unattributed": drift.unattributed,
                },
            },
            capability_used="snapshot.take",
            component="snapshot",
            genesis_token=genesis_token,
        )

    def _publish_snapshot(self, project_id: Id, snapshot: RealitySnapshot) -> None:
        """Persist the snapshot, and point the project at it if it is real.

        A failed observation is recorded as evidence — it is a true fact about
        a moment — but it never becomes the current reality. Pointing
        `snapshot_current` at a snapshot that saw nothing would make "the
        workspace as the runtime last knew it" mean "nothing is there".
        """
        self.store.put_snapshot(snapshot)
        if snapshot.completeness is Completeness.COMPLETE:
            self.store.set_project_snapshot_current(
                project_id, snapshot.snapshot_id
            )

    def _effective_index_of(self, snapshot: RealitySnapshot) -> dict:
        """A stored snapshot's committed index overlaid with its dirty index."""
        document = self.store.snapshot_document(snapshot)
        return effective_index(
            document.get("committed", {}), document.get("dirty", {})
        )

    def _on_reality_drift(
        self, project_id: Id, snapshot: RealitySnapshot, paths: Sequence[str]
    ) -> None:
        """`REALITY_DRIFT`: the workspace moved outside runtime-mediated change.

        Raised whether the change was committed or merely left dirty in the
        working tree. A dirty tracked file outside the paths the runtime
        declared it was changing is somebody else's edit, and treating it as
        noise is exactly how a runtime ends up validating one tree and
        committing another.
        """
        listed = ", ".join(paths[:10]) + (" …" if len(paths) > 10 else "")
        self._raise_escalation(
            project_id,
            trigger=EscalationTrigger.REALITY_DRIFT,
            severity=EscalationSeverity.HIGH,
            summary=(
                f"snapshot {snapshot.snapshot_id} found {len(paths)} unattributed "
                f"change(s) in the workspace: {listed}"
            ),
            suspension=SuspensionState.SUSPENDED_BY_DRIFT,
        )

    def _stale_decisions_against(
        self,
        project_id: Id,
        previous: RealitySnapshot,
        snapshot: RealitySnapshot,
    ) -> None:
        """`HD-INV-4`: a superseded approval stops being authority.

        A snapshot that found nothing changed supersedes nothing, so approvals
        survive being looked at again. That is only true because the
        fingerprint excludes untracked and ignored files; if it did not, every
        tool run would invalidate every approval (`repository.py`).
        """
        before = self._effective_index_of(previous)
        after = self._effective_index_of(snapshot)
        for decision in self.store.list_decisions(project_id):
            if decision.subject_snapshot_id == snapshot.snapshot_id:
                continue
            touched = drift_touches_scope(before, after, subject_scope(decision))
            state = derive_decision_state(
                decision,
                now=now_ts(),
                superseded_by_drift=touched,
            )
            if state is decision.decision_state:
                continue
            self._append(
                project_id,
                event_type="decision.state_derived",
                epistemic_class=EpistemicClass.EVIDENCE,
                subject={"decision_id": decision.decision_id},
                payload={
                    "from": decision.decision_state.value,
                    "to": state.value,
                    "subject_snapshot_id": decision.subject_snapshot_id,
                    "superseded_by": snapshot.snapshot_id,
                },
                capability_used="audit.append",
                component="decision",
            )
            decision.decision_state = state
            self.store.put_decision(decision)

    # -- human decisions (domain-model §9.A) --------------------------------

    def record_decision(
        self,
        project_id: Id,
        *,
        decision_kind: DecisionKind,
        subject_kind: DecisionSubjectKind,
        subject_id: Id,
        question: str,
        chosen: str,
        justification: str,
        decided_by: ActorRef,
        evidence_shown: Sequence[ArtifactRef],
        options_offered: Sequence[str] = (),
        signature: Optional[str] = None,
        approved_snapshot_id: Optional[Id] = None,
        scope: DecisionScope = DecisionScope.PROJECT,
        expires_at: Optional[datetime] = None,
        grants: frozenset[str] = frozenset(),
        revokes: frozenset[str] = frozenset(),
    ) -> HumanDecision:
        """Record a human's decision, from outside the runtime.

        The public form, and it carries no genesis token: a caller reached
        through this method is measured against the pending-genesis hold like
        any other, including a presenter or a finalizer that calls it against
        the project being created. Genesis records its own approval through
        `_record_decision`, which is not on the public surface (`GR27-R5`).

        Everything else about the two is the same; the predicates and what
        they are for are documented on the implementation below.
        """
        return self._record_decision(
            project_id,
            decision_kind=decision_kind,
            subject_kind=subject_kind,
            subject_id=subject_id,
            question=question,
            chosen=chosen,
            justification=justification,
            decided_by=decided_by,
            evidence_shown=evidence_shown,
            options_offered=options_offered,
            signature=signature,
            approved_snapshot_id=approved_snapshot_id,
            scope=scope,
            expires_at=expires_at,
            grants=grants,
            revokes=revokes,
        )

    def _record_decision(
        self,
        project_id: Id,
        *,
        decision_kind: DecisionKind,
        subject_kind: DecisionSubjectKind,
        subject_id: Id,
        question: str,
        chosen: str,
        justification: str,
        decided_by: ActorRef,
        evidence_shown: Sequence[ArtifactRef],
        options_offered: Sequence[str] = (),
        signature: Optional[str] = None,
        approved_snapshot_id: Optional[Id] = None,
        scope: DecisionScope = DecisionScope.PROJECT,
        expires_at: Optional[datetime] = None,
        grants: frozenset[str] = frozenset(),
        revokes: frozenset[str] = frozenset(),
        genesis_token: object = None,
    ) -> HumanDecision:
        """Record a human's decision. `∅ → VALID` (transition-matrix §7.5-1).

        Refused unless it is a human's: `HD-INV-1` — a runtime or a worker
        cannot manufacture authority. Refused with empty `evidence_shown`:
        `HD-INV-2` — an uninformed approval discharges nothing. A
        snapshot-bound decision is bound here to the newest `COMPLETE`
        snapshot, which is the reality the human was actually shown.

        Refused unless `chosen` is one of `options_offered`
        (domain-model.md:695-696): a choice that was never offered is not a
        choice the human made, and a
        malformed decision is authority for nothing (`DESIGN-04-034`). The
        predicate is enforced here, once, rather than at each caller.

        `signature` is required exactly when `decided_by.auth_method` is
        `SIGNATURE` (domain-model.md:710) and is bound into `decision_hash`,
        so it can be neither attached afterwards nor dropped. Nothing here
        verifies it: no key infrastructure exists, and an unverified signature
        is recorded as the evidence it is, not as proof of anything
        (`DESIGN-04-035`).

        `approved_snapshot_id` names the observation the decider was actually
        shown, for the callers that presented one. Where it is given the
        decision binds to **that** snapshot and to no other: the newest
        `COMPLETE` snapshot is not re-selected, because rebinding an approval
        to a reality its approver did not see is exactly what
        `subject_snapshot_id` exists to prevent (domain-model.md:703). It is
        validated, not trusted: the decision must be snapshot-bound and the
        named observation must be a `COMPLETE` observation of **this**
        project, or it is refused rather than recorded against an id the
        caller invented. What it does not re-ask is whether that observation
        is still current. That is the presenting caller's invariant, asked at
        the boundary that showed it and immediately before this call
        (`guard:creation_observation_fresh`); asking it again here would put
        one predicate behind two guards, and neither could then be shown to
        be doing any work (`GR27-R3`). Callers that name nothing keep the
        central binding unchanged.
        """
        if decided_by.actor_kind is not ActorKind.HUMAN:
            raise IntegrityViolation(
                f"a HumanDecision must be decided by a HUMAN; got "
                f"{decided_by.actor_kind.value} (HD-INV-1)"
            )
        if decided_by.auth_method in (AuthMethod.NONE, AuthMethod.DELEGATED):
            raise IntegrityViolation(
                "unauthenticated authority is indistinguishable from forged "
                f"authority: auth_method={decided_by.auth_method.value}"
            )
        if not evidence_shown:
            raise IntegrityViolation(
                "an uninformed approval cannot discharge required_evidence "
                "(HD-INV-2)"
            )
        require(chosen in tuple(options_offered), f"a decision must choose an offered option: chosen={chosen!r} is not in options_offered={list(options_offered)!r} (domain-model.md:695-696)", IntegrityViolation)  # guard:decision_option_membership
        require(decided_by.auth_method is not AuthMethod.SIGNATURE or bool(signature), "auth_method=SIGNATURE requires the signature itself; a method label and a key id are not the evidence (domain-model.md:710)", IntegrityViolation)  # guard:decision_signature_present
        bound = is_snapshot_bound(subject_kind, decision_kind)
        subject_snapshot_id = None
        if approved_snapshot_id is not None:
            require(bound and self._is_own_complete_observation(project_id, approved_snapshot_id), f"an explicitly approved observation must be a COMPLETE observation of this project, on a snapshot-bound decision: snapshot_bound={bound} and {approved_snapshot_id} is not one of {project_id}'s COMPLETE observations (domain-model.md:703)", IntegrityViolation)  # guard:decision_approved_snapshot
            subject_snapshot_id = approved_snapshot_id
        elif bound:
            snapshot = self.store.newest_complete_snapshot(project_id)
            if snapshot is None:
                raise IntegrityViolation(
                    "a snapshot-bound decision needs a COMPLETE snapshot to be "
                    "bound to; none exists for this project"
                )
            subject_snapshot_id = snapshot.snapshot_id

        decision_id = f"dec-{uuid.uuid4().hex}"
        decided_at = now_ts()
        preimage = {
            "decision_id": decision_id,
            "project_id": project_id,
            "subject": {"kind": subject_kind.value, "id": subject_id},
            "decision_kind": decision_kind.value,
            "chosen": chosen,
            "decided_at": decided_at.isoformat(),
            "subject_snapshot_id": subject_snapshot_id,
            "evidence_shown": [ref.digest for ref in evidence_shown],
            "grants": sorted(grants),
            "revokes": sorted(revokes),
        }
        decision = HumanDecision(
            decision_id=decision_id,
            project_id=project_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            decision_kind=decision_kind,
            question=question,
            chosen=chosen,
            justification=justification,
            scope=scope,
            decided_by=decided_by,
            auth_method=decided_by.auth_method,
            decided_at=decided_at,
            nonce=uuid.uuid4().hex,
            snapshot_bound=bound,
            decision_state=DecisionState.VALID,
            options_offered=tuple(options_offered),
            evidence_shown=tuple(evidence_shown),
            grants=frozenset(grants),
            revokes=frozenset(revokes),
            subject_snapshot_id=subject_snapshot_id,
            expires_at=expires_at,
            signature=signature,
            prev_event_hash=self.store.get_project(project_id).event_head,
        )
        decision.decision_hash = decision_content_hash(decision)
        self._append(
            project_id,
            event_type="decision.recorded",
            epistemic_class=EpistemicClass.DECISION,
            subject={"decision_id": decision_id},
            payload=preimage,
            capability_used="decision.record",
            component="decision",
            # `AX-15`: this event is the human's own act, so they hold it and
            # it cites no delegated authority.
            actor=decided_by,
            genesis_token=genesis_token,
        )
        self.store.put_decision(decision)
        return decision

    # -- invocations (worker_provider §6) ----------------------------------


    def mark_dispatched(self, invocation_id: Id) -> None:
        """`PENDING → DISPATCHED` (transition-matrix §7.1)."""
        invocation = self.store.get_invocation(invocation_id)
        from .contracts import require
        require(invocation.status is InvocationStatus.PENDING, 'dispatch status cannot be reset', PolicyDenied)  # guard:gr07_dispatch_reset
        project_id = self.store.invocation_project(invocation_id)
        invocation.status = InvocationStatus.DISPATCHED
        invocation.dispatched_at = now_ts()
        self._append(
            project_id,
            event_type="invocation.dispatched",
            epistemic_class=EpistemicClass.AUTHORITY,
            subject={"invocation_id": invocation_id},
            payload={"idempotency_key": invocation.idempotency_key},
            capability_used="worker.invoke",
        )
        self.store.put_invocation(invocation, project_id)


    def _mint_worker_receipt(
        self,
        invocation: WorkerInvocation,
        project_id: Id,
        *,
        output: bytes,
        termination_reason: TerminationReason,
        attribution: Attribution,
        status: InvocationStatus,
        usage: Usage,
        **extras,
    ) -> WorkerReceipt:
        from .secret_guard import SecretLeak
        from .store import _worker_value
        try:
            self.secret_guard.check((output, _worker_value(extras)))  # guard:gr08_receipt_check
        except SecretLeak:
            output, extras = b'{"error":"SECRET_LEAK"}', {}
            status, termination_reason = InvocationStatus.FAILED, TerminationReason.PROVIDER_ERROR
        output_ref = self.store.store_artifact(
            output, media_type="application/octet-stream"
        )
        project = self.store.get_project(project_id)
        ended_at = now_ts()
        preimage = {
            "invocation_id": invocation.invocation_id,
            "idempotency_key": invocation.idempotency_key,
            "output_digest": output_ref.digest,
            "termination_reason": termination_reason.value,
            "attribution": attribution.value,
            "ended_at": ended_at.isoformat(),
        }
        from .store import _worker_value
        preimage['details'] = {k: _worker_value(v) for k, v in extras.items()}
        preimage['usage'] = _worker_value(usage)
        receipt = WorkerReceipt(
            receipt_id=f"wr-{uuid.uuid4().hex}",
            invocation_id=invocation.invocation_id,
            ended_at=ended_at,
            duration_ms=usage.wall_clock_ms,
            usage=usage,
            output_ref=output_ref,
            output_digest=output_ref.digest,
            termination_reason=termination_reason,
            attribution=attribution,
            attested_by=_runtime_actor("worker_receipt"),
            receipt_hash=digest_json(preimage),
            prev_event_hash=project.event_head,
            **extras,
        )
        db = self.store.connection
        db.execute('SAVEPOINT worker_receipt')
        try:
            self._append(
                project_id,
                event_type="worker_receipt.attested",
                epistemic_class=EpistemicClass.EVIDENCE,
                subject={
                    "invocation_id": invocation.invocation_id,
                    "receipt_id": receipt.receipt_id,
                },
                payload=preimage,
                capability_used=(
                    "recovery.reconcile"
                    if attribution is Attribution.RECONCILED
                    else "worker.invoke"
                ),
            )
            self.store.put_worker_receipt(receipt, project_id)
            invocation.status = status
            invocation.receipt_id = receipt.receipt_id
            self.store.put_invocation(invocation, project_id)
            db.execute('RELEASE worker_receipt')
        except BaseException:
            db.execute('ROLLBACK TO worker_receipt')
            db.execute('RELEASE worker_receipt')
            raise
        return receipt


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
        """`∅ → PROPOSED`, minting `operation_token` into the trailers.

        The base is the head of the **governed line**, not of the user's
        checkout: governed revisions accumulate in the dedicated worktree, and
        predicting a tree against a base the runtime is not committing onto
        would make every `expected_tree_digest` wrong after the first commit.
        """
        run = self.store.get_run(run_id)
        self._assert_may_initiate_effect(run.project_id, "proposing a commit")
        project = self.store.get_project(run.project_id)
        if self.repo is None:
            raise IntegrityViolation("no repository adapter is configured")

        # Refused before anything is stored: no capability, decision or mode
        # makes repository metadata or an escaping path writable.
        self.require_authority(run_id, "commit.propose")  # guard:gr06_commit_propose_grant
        governed = self.governed_repo(run.project_id)
        self.require_authority(run_id, "fs.write", path=path, repo=governed)  # guard:gr06_commit_propose_path
        path = assert_unprotected(path)
        payload = content.encode("utf-8")
        after_ref = self.store.store_artifact(
            payload, media_type="application/octet-stream"
        )
        base_revision_id = governed.head_revision()
        base_index = governed.file_index(base_revision_id)
        mutation = MutationProposal(
            op=MutationOp.MODIFY if path in base_index else MutationOp.CREATE,
            path=path,
            after_ref=after_ref,
            before_digest=base_index.get(path),
            in_scope=True,
        )
        token = mint_operation_token()
        intent = CommitIntent(
            intent_id=f"ci-{uuid.uuid4().hex}",
            run_id=run_id,
            stage_id=run.stage_id,
            vcs_kind=VcsKind.DVCS,
            base_revision_id=base_revision_id,
            target_ref=governed_branch(run.project_id),
            expected_tree_digest=expected_tree_digest(base_index, [mutation]),
            message=message,
            operation_token=token,
            controller_epoch=project.controller_epoch,
            status=CommitIntentStatus.PROPOSED,
            reconciliation_state=derive_reconciliation_state(
                record_epoch=project.controller_epoch,
                project_epoch=project.controller_epoch,
                status_terminal=False,
            ),
            preconditions=preconditions or CommitPreconditions(),
            preconditions_met=False,
            mutations=(mutation,),
            trailers=build_trailers(token),
        )
        commit_message(intent)  # guard:commit_proposal_message
        rule = self._require_transition_authority(
            Axis.COMMIT_INTENT,
            ORIGIN,
            CommitIntentStatus.PROPOSED,
            project_id=run.project_id,
            run_id=run_id,
        )
        # `CM-INV-2`: the token is durable before anything touches the
        # repository, so a revision that lands is always matchable back here.
        self._append(
            run.project_id,
            event_type="commit_intent.proposed",
            epistemic_class=EpistemicClass.AUTHORITY,
            subject={"intent_id": intent.intent_id, "run_id": run_id},
            payload={
                "operation_token": token,
                "base_revision_id": base_revision_id,
                "expected_tree_digest": intent.expected_tree_digest,
                "controller_epoch": intent.controller_epoch,
            },
            capability_used=rule.required_capability,
            component="commit",
        )
        self.store.put_commit_intent(intent, run.project_id)
        return intent

    # -- transition authority (authority-matrix §6, `G-4`) ------------------

    def _grant_permits(self, run_id: Id, capability: str) -> bool:
        """Whether the run's activation grants `capability`, as a value.

        `require_authority` answers by raising, and audits its own refusal as
        `authority.denied`. Here the answer is wanted as a predicate: what
        reports the shortfall is the transition's refusal, which names the row
        and the capability the row declares.
        """
        try:
            self.require_authority(run_id, capability, _grant_only=True)
        except (
            CapabilityDenied,
            IntegrityViolation,
            PolicyDenied,
            ProtectedPathViolation,
        ):
            return False
        return True

    def _ord_holds(self, capability: str, run_id: Optional[Id]) -> bool:
        """Whether an `ORD` row's capability is held — from the activation only.

        `AX-11`: a capability is granted only where a principal the register
        names as its grantor produced an admissible record, cited in
        `capability_grant_basis`. `RUNTIME_KERNEL` "cannot self-grant
        non-`KERNEL` capabilities", so the kernel set is not consulted here and
        can never stand in for a grant.
        """
        return run_id is not None and self._grant_permits(run_id, capability)  # guard:transition_ord_grant

    def _kernel_holds(
        self, capability: str, kernel_capabilities: frozenset, actor: ActorRef
    ) -> bool:
        """Whether this holder may take a `KERNEL` row.

        Both conjuncts are `AX-7`: the capability is in the set this holder is
        acting with, and the holder is the runtime acting as itself. A
        delegated or worker actor holds no `KERNEL` capability however wide the
        set it is handed (authority-matrix §1, §6:288).
        """
        return capability in kernel_capabilities and actor.actor_kind is ActorKind.RUNTIME  # guard:transition_kernel_holder

    def _transition_capabilities(
        self,
        candidates: Sequence,
        run_id: Optional[Id],
        kernel_capabilities: frozenset,
        actor: ActorRef,
    ) -> frozenset:
        """Which capabilities these rows declare that this holder actually holds.

        Two sources, chosen by the register's own class column and never
        merged: `KERNEL` from the acting kernel set, `ORD` from the run's
        activation. Neither can supply the other's class, so neither can stand
        in for the other — which is the substitution `F03-002` records.
        `HUMAN` and `NEVER` are held by nothing here: a `HUMAN` row needs an
        exercise decision presented at the transition, and no §7.4 row declares
        one, so the channel refuses rather than inventing a path to it.
        """
        held = set()
        for capability in sorted(
            {rule.required_capability for rule in candidates}
        ):
            kind = REGISTER.get(capability, ("NEVER", ()))[0]
            if kind == "KERNEL":
                holds = self._kernel_holds(capability, kernel_capabilities, actor)
            elif kind == "ORD":
                holds = self._ord_holds(capability, run_id)
            else:
                holds = False
            if holds:
                held.add(capability)
        return frozenset(held)

    def _require_transition_authority(
        self,
        axis: Axis,
        from_state,
        to_state,
        *,
        project_id: Id,
        run_id: Optional[Id] = None,
        kernel_capabilities: Optional[frozenset] = None,
        actor: Optional[ActorRef] = None,
    ):
        """Prove the row's declared capability, and return the row.

        authority-matrix.md:292 — `required_capability` from the transition
        matrix, held at the moment of transition. The row comes from the frozen
        table rather than from the caller, and the capability it names is what
        the caller then labels its event with, so an operation cannot name one
        capability and hold another (`G-4`).

        Deciding the capability is all this does. Preconditions and
        `required_evidence` are the other half of authority-matrix §6's
        transition row and are **not** enforced here; `policy.resolve` is where
        they live, and routing production through it is a larger change than
        this one.
        """
        kernel = (
            self.kernel_capabilities
            if kernel_capabilities is None
            else kernel_capabilities
        )
        holder = actor or _runtime_actor("controller")
        candidates = rules_for(axis, from_state, to_state)
        require(bool(candidates), f"no row of the transition matrix carries {axis.value} {normalize_state(from_state)} → {normalize_state(to_state)}; an operation that names no CapabilityId is denied (G-4, AX-2)", IntegrityViolation)  # guard:transition_row_declared
        context = TransitionContext(
            governance_mode=self.store.get_project(project_id).governance_mode,
            from_state=normalize_state(from_state),
            capabilities=self._transition_capabilities(
                candidates, run_id, kernel, holder
            ),
        )
        rule = select_rule(candidates, context)
        require(not capability_missing(rule, context), f"row {rule.row} requires {rule.required_capability!r}, which {holder.actor_id} does not hold at the moment of transition (authority-matrix.md:292)", CapabilityDenied)  # guard:transition_capability_held
        return rule

    def _transition_intent(
        self,
        intent: CommitIntent,
        project_id: Id,
        *,
        status: CommitIntentStatus,
        event_type: str,
        payload: dict,
        kernel_capabilities: Optional[frozenset] = None,
    ) -> None:
        """Write one §7.4 status under the capability its row declares.

        The capability is proved before the status is assigned and then labels
        the event. No caller supplies it: `G-4` requires a state-changing
        operation to name exactly one `CapabilityId`, and a label the caller
        chose is a claim about authority rather than evidence of it
        (`F03-003`).
        """
        rule = self._require_transition_authority(
            Axis.COMMIT_INTENT,
            intent.status,
            status,
            project_id=project_id,
            run_id=intent.run_id,
            kernel_capabilities=kernel_capabilities,
        )
        intent.status = status
        self._append(
            project_id,
            event_type=event_type,
            epistemic_class=EpistemicClass.AUTHORITY,
            subject={"intent_id": intent.intent_id},
            payload=payload,
            capability_used=rule.required_capability,
            component="commit",
        )
        self.store.put_commit_intent(intent, project_id)

    def block_commit(self, intent_id: Id) -> None:
        """`PROPOSED → BLOCKED` when a precondition is unmet."""
        intent = self.store.get_commit_intent(intent_id)
        self._transition_intent(
            intent,
            self.store.intent_project(intent_id),
            status=CommitIntentStatus.BLOCKED,
            event_type="commit_intent.blocked",
            payload={"operation_token": intent.operation_token},
        )

    def authorize_commit(self, intent_id: Id) -> None:
        """`PROPOSED → AUTHORIZED`.

        Re-evaluates the preconditions rather than trusting the stored value:
        a review-backed precondition is refused here even if something wrote
        one directly into the record (`G-1`).
        """
        intent = self.store.get_commit_intent(intent_id)
        project_id = self.store.intent_project(intent_id)
        if intent.status is not CommitIntentStatus.PROPOSED:  # guard:commit_authorize_status
            raise IntegrityViolation("only a proposed intent can be authorized")
        governed = self.governed_repo(project_id)
        self._require_commit_authority(intent, governed)  # guard:gr06_commit_authorize
        head = verify_head(governed, expected_revision=intent.base_revision_id,
                           expected_ref=intent.target_ref)
        if not head.matches:  # guard:commit_authorize_base
            raise IntegrityViolation(head.reason())
        met = evaluate_preconditions(
            intent.preconditions or CommitPreconditions(),
            resolve_attestation=self.store.resolve_review_evidence,
            resolve_validation=lambda digest: self.store.artifacts.has(digest),
            resolve_decision=lambda ref: False,
        )
        intent.preconditions_met = met
        if not met:
            self._transition_intent(
                intent,
                project_id,
                status=CommitIntentStatus.BLOCKED,
                event_type="commit_intent.blocked",
                payload={"operation_token": intent.operation_token},
            )
            return
        intent.authorized_by = _runtime_actor("commit")
        intent.authorized_at = now_ts()
        self._transition_intent(
            intent,
            project_id,
            status=CommitIntentStatus.AUTHORIZED,
            event_type="commit_intent.authorized",
            payload={
                "operation_token": intent.operation_token,
                "preconditions_met": True,
            },
        )

    def deny_commit(self, intent_id: Id, reason: str) -> None:
        """`PROPOSED → DENIED`."""
        intent = self.store.get_commit_intent(intent_id)
        intent.denial_reason = reason
        self._transition_intent(
            intent,
            self.store.intent_project(intent_id),
            status=CommitIntentStatus.DENIED,
            event_type="commit_intent.denied",
            payload={"reason": reason},
        )

    def mark_applying(self, intent_id: Id) -> None:
        """`AUTHORIZED → APPLYING`.

        The token and epoch are durable before the first repository mutation,
        so a revision that lands afterwards is always matchable back to this
        intent (`CM-INV-2`).
        """
        intent = self.store.get_commit_intent(intent_id)
        self._assert_barrier_clear(intent.run_id, "marking a commit applying")  # guard:commit_mark_barrier
        self._assert_may_initiate_effect(self.store.intent_project(intent_id), "marking a commit applying")  # guard:commit_mark_completeness
        if intent.status is not CommitIntentStatus.AUTHORIZED:  # guard:commit_mark_status
            raise IntegrityViolation("only an authorized intent may start applying")
        self._transition_intent(
            intent,
            self.store.intent_project(intent_id),
            status=CommitIntentStatus.APPLYING,
            event_type="commit_intent.applying",
            payload={
                "operation_token": intent.operation_token,
                "controller_epoch": intent.controller_epoch,
            },
        )

    def _settle_commit_receipt(self, intent, project_id, **kwargs):
        connection = self.store.connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            receipt = self._record_commit_receipt(intent, project_id, **kwargs)
            connection.execute("COMMIT")
            return receipt
        except BaseException:
            connection.execute("ROLLBACK")
            raise

    def _record_commit_receipt(
        self,
        intent: CommitIntent,
        project_id: Id,
        *,
        revision_id: str,
        parent_revision_ids: Sequence[str],
        actual_tree_digest: str,
        diff: bytes,
        attribution: Attribution,
    ) -> CommitReceipt:
        existing = self.store.list_commit_receipts(intent.intent_id)
        if existing:  # guard:commit_single_receipt
            return existing[0]
        diff_ref = self.store.store_artifact(diff, media_type="text/x-diff")
        post_snapshot_id = self.take_snapshot(
            project_id, trigger=SnapshotTrigger.POST_COMMIT
        )
        observation = self.governed_repo(project_id, create=False).observe_commit(revision_id, intent=intent)
        receipt = build_receipt(
            intent, observation=observation, diff_ref=diff_ref,
            post_snapshot_id=post_snapshot_id, attribution=attribution,
            prev_event_hash=self.store.get_project(project_id).event_head,
        )
        capability = (
            "recovery.reconcile"
            if attribution is Attribution.RECONCILED
            else APPLY_CAPABILITY
        )
        # `WP-16`: a reconciling settlement acts with `recovery.reconcile` and
        # nothing executable, which is also what tells §7.4's two rows over
        # `APPLYING → APPLIED` apart (`select_rule`).
        reconciling = (
            RECOVERY_CAPABILITIES if attribution is Attribution.RECONCILED else None
        )
        self._append(
            project_id,
            event_type="commit_receipt.attested",
            epistemic_class=EpistemicClass.EVIDENCE,
            subject={
                "intent_id": intent.intent_id,
                "receipt_id": receipt.receipt_id,
            },
            payload={
                "revision_id": revision_id,
                "operation_token": receipt.operation_token,
                "verification": receipt.verification.value,
                "actual_tree_digest": actual_tree_digest,
                "attribution": attribution.value,
                "receipt_hash": receipt.receipt_hash,
            },
            capability_used=capability,
            component="commit",
        )
        self.store.put_commit_receipt(receipt, project_id)
        gate(AFTER_COMMIT_RECEIPT_INSERT)

        intent.receipt_id = receipt.receipt_id
        if receipt.verification is Verification.MATCHED:
            status = CommitIntentStatus.APPLIED
        else:
            status = CommitIntentStatus.FAILED
            # `CM-INV-1`: a divergent tree is an established outcome and a
            # failure; it escalates rather than being quietly retried.
            self._raise_escalation(
                project_id,
                trigger=EscalationTrigger.INTEGRITY_VIOLATION,
                severity=EscalationSeverity.CRITICAL,
                summary=(
                    f"commit {revision_id} for intent {intent.intent_id} landed a "
                    "revision that differs from the authorized intent"
                ),
                run_id=intent.run_id,
            )
        self._transition_intent(
            intent,
            project_id,
            status=status,
            event_type="commit_intent.settled",
            payload={
                "operation_token": intent.operation_token,
                "receipt_id": receipt.receipt_id,
                "verification": receipt.verification.value,
            },
            kernel_capabilities=reconciling,
        )
        return receipt

    def apply_commit(self, intent_id: Id) -> CommitReceipt:
        """Apply the intent and mint the receipt with `attribution = DIRECT`.

        The reconciliation and completeness gates precede all effects. Under
        the repository lease, persist APPLYING, verify the base, apply only the
        intent's paths and stage them literally. The adapter verifies the full
        staged tree and exact diff, pins that index, rechecks parent and branch,
        and commits. Receipt, snapshot and settlement then persist atomically.
        An interrupted APPLYING intent is observed by recovery, never retried.
        """
        intent = self.store.get_commit_intent(intent_id)
        project_id = self.store.intent_project(intent_id)
        self._assert_barrier_clear(intent.run_id, "applying a commit")
        self._assert_may_initiate_effect(project_id, "applying a commit")
        if intent.status is not CommitIntentStatus.AUTHORIZED:  # guard:commit_no_reapply
            raise IntegrityViolation("commit requires AUTHORIZED; reconcile any prior application")
        governed = self.governed_repo(project_id)
        exact_paths(intent)
        commit_message(intent)
        with self.repository_lease(project_id):
            gate(INSIDE_REPOSITORY_LEASE)
            # Re-read state under the write lease, including the barrier and
            # observation gate. Persist APPLYING before any mutation.
            intent = self.store.get_commit_intent(intent_id)
            self._require_commit_authority(intent, governed)  # guard:gr06_commit_apply
            self.mark_applying(intent_id)
            # `mark_applying` persisted `APPLYING`; re-read so the settlement
            # transitions from where the intent actually is. The edge the
            # receipt settles is `APPLYING → APPLIED` (row 7.4-7), and a stale
            # `AUTHORIZED` in this frame would name an edge §7.4 does not carry.
            intent = self.store.get_commit_intent(intent_id)
            head = verify_head(governed, expected_revision=intent.base_revision_id,
                               expected_ref=intent.target_ref)
            if not head.matches:  # guard:commit_apply_base
                raise IntegrityViolation(f"{intent.base_revision_id}: {head.reason()}")
            paths = governed.apply_mutations(intent, self.store.artifact_bytes)
            governed.stage(paths)
            revision_id = governed.commit(intent=intent)

        gate(AFTER_COMMIT_BEFORE_RECEIPT)
        return self._settle_commit_receipt(
            intent, project_id, revision_id=revision_id,
            parent_revision_ids=governed.parents(revision_id),
            actual_tree_digest=governed.tree_digest(revision_id),
            diff=governed.diff(revision_id), attribution=Attribution.DIRECT,
        )

    def verify_commit(self, intent_id: Id) -> Verification:
        """Re-observe the recorded revision and compare every receipt field."""
        intent = self.store.get_commit_intent(intent_id)
        receipts = self.store.list_commit_receipts(intent_id)
        if len(receipts) != 1:  # guard:commit_receipt_required
            raise IntegrityViolation("commit verification requires exactly one receipt")
        receipt = receipts[0]
        repo = self.governed_repo(self.store.intent_project(intent_id), create=False)
        verification = verify_receipt(intent, receipt, repo.observe_commit(receipt.revision_id, intent=intent))
        if verification is Verification.DIVERGED:  # guard:commit_reverification_suspends
            project_id = self.store.intent_project(intent_id)
            self._raise_escalation(
                project_id, trigger=EscalationTrigger.INTEGRITY_VIOLATION,
                severity=EscalationSeverity.CRITICAL,
                summary=f"commit receipt {receipt.receipt_id} failed verification",
                run_id=intent.run_id,
            )
        return verification

    def publish_commit(self, intent_id: Id) -> None:
        """Publication is a separate, denied capability in this runtime."""
        raise PolicyDenied("commit.publish is DENIED")  # guard:commit_publish_denied

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
        run = self.store.get_run(run_id)
        review_id = f"rv-{uuid.uuid4().hex}"
        snapshot = self.store.get_snapshot(input_snapshot_id)
        record = ReviewRecord(
            review_id=review_id,
            run_id=run_id,
            stage_id=run.stage_id,
            review_spec_id=review_spec_id,
            reviewer=ActorRef(
                actor_kind=ActorKind.WORKER,
                actor_id=f"reviewer-{review_id[3:11]}",
                auth_method=AuthMethod.SESSION,
            ),
            reviewer_kind=reviewer_kind,
            independence=independence,
            inputs_digest=snapshot.tree_digest,
            input_snapshot_id=input_snapshot_id,
            verdict=verdict,
            review_hash=digest_json(
                {
                    "review_id": review_id,
                    "review_spec_id": review_spec_id,
                    "verdict": verdict.value,
                    "input_snapshot_id": input_snapshot_id,
                }
            ),
            completed_at=now_ts(),
        )
        # CLAIM class: a judgement, recorded as one. It never discharges a
        # precondition; only the kernel's measurement of it does.
        self._append(
            run.project_id,
            event_type="review.recorded",
            epistemic_class=EpistemicClass.CLAIM,
            subject={"review_id": review_id, "run_id": run_id},
            payload={
                "review_spec_id": review_spec_id,
                "verdict": verdict.value,
                "independence": independence.value,
                "input_snapshot_id": input_snapshot_id,
            },
            capability_used="review.submit",
            component="review",
        )
        self.store.put_review(record, run.project_id)
        return record

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
        run = self.store.get_run(run_id)
        worker_contract_hash = self._worker_review_contract(run_id, review_spec_id, reviews, quorum)
        attestation = mint_attestation(
            reviews=reviews,
            review_spec_id=review_spec_id,
            quorum=quorum,
            independence_required=True,
            input_snapshot_id=reviews[0].input_snapshot_id,
            contract_hash=worker_contract_hash or digest_json({"review_spec_id": review_spec_id}),
            run_id=run_id,
            stage_id=run.stage_id,
            attested_by={
                "actor_kind": ActorKind.RUNTIME.value,
                "actor_id": "gruntime.review",
                "auth_method": AuthMethod.NONE.value,
            },
            capabilities=frozenset({ATTEST_CAPABILITY}),
        )
        self._append(
            run.project_id,
            event_type="review_attestation.minted",
            epistemic_class=EpistemicClass.EVIDENCE,
            subject={
                "attestation_id": attestation.attestation_id,
                "run_id": run_id,
            },
            payload={
                "review_spec_id": review_spec_id,
                "verdict": attestation.verdict.value,
                "review_ids": sorted(attestation.review_ids),
                "quorum_met": attestation.quorum_met,
                "independence_satisfied": attestation.independence_satisfied,
            },
            capability_used=ATTEST_CAPABILITY,
            component="review",
        )
        self.store.put_attestation(attestation, run.project_id)
        return attestation

    # -- transitions (transition-matrix §1, §9) -----------------------------

    def evaluate_transition(
        self,
        project_id: Id,
        proposal: TransitionProposal,
        context: TransitionContext,
    ) -> TransitionResolution:
        """Resolve a proposal, audit the answer, and escalate a refusal.

        The controller is the only thing that may decide (`G-3`): a worker
        hands over a `TransitionProposal` and learns the outcome, never the
        other way round. Every resolution is appended as an `AuditEvent` of
        class `AUTHORITY`, including the permitting ones, so "what allowed
        this?" and "what refused this?" are answered from the same chain
        (authority-matrix §6).

        An `ESCALATE` outcome also raises the `Escalation` §9 requires: those
        attempts are never a retry. The escalation applies no suspension —
        nothing happened, so there is nothing to quiesce; the record exists so
        a human sees the attempt.

        Deciding is all this does. Writing the new state onto the entity is the
        caller's, on an `AUTO_ALLOW` and not otherwise.
        """
        resolution = resolve(proposal, context)
        self._append(
            project_id,
            event_type="transition.resolved",
            epistemic_class=EpistemicClass.AUTHORITY,
            subject={
                "axis": proposal.axis.value,
                "subject_id": proposal.subject_id,
            },
            payload={
                "axis": proposal.axis.value,
                "from_state": normalize_state(proposal.from_state),
                "to_state": normalize_state(proposal.to_state),
                "operation": (
                    proposal.operation.value if proposal.operation else None
                ),
                "proposed_by": proposal.proposed_by.actor_kind.value,
                "governance_mode": context.governance_mode.value,
                "suspension": context.suspension.value,
                "outcome": resolution.outcome.value,
                "reason": resolution.reason.value,
                "row": resolution.row,
                "detail": resolution.detail,
                "required_decision": (
                    resolution.required_decision.value
                    if resolution.required_decision
                    else None
                ),
                "notify": resolution.notify,
                "unmet_preconditions": [
                    predicate.value for predicate in resolution.unmet_preconditions
                ],
                "missing_evidence": list(resolution.missing_evidence),
            },
            capability_used=(
                resolution.rule.required_capability if resolution.rule else None
            ),
        )
        if resolution.outcome is not PolicyOutcome.ESCALATE:
            return resolution

        escalation_id = self._raise_escalation(
            project_id,
            trigger=(
                resolution.escalation_trigger
                or EscalationTrigger.POLICY_CONFLICT
            ),
            severity=EscalationSeverity.HIGH,
            summary=(
                f"refused {proposal.axis.value} "
                f"{proposal.from_state} → {proposal.to_state} "
                f"({resolution.reason.value}): {resolution.detail}"
            ),
            # Nothing happened, so there is nothing to quiesce. The record is
            # the notice, not a state change.
            suspension=SuspensionState.NONE,
        )
        return resolution.with_escalation(escalation_id)

    # -- recovery (worker_provider §6.1) -----------------------------------

    def recovery_provider(self) -> GovernedProvider:
        """The provider as recovery sees it: `lookup`, and nothing else."""
        return GovernedProvider(self.provider, RECOVERY_CAPABILITIES)

    def recover(self, project_id: Id) -> RecoveryOutcome:
        """Reconcile every old-epoch record, under `recovery.reconcile` only.

        Holds no capability that can execute: the provider is reached through
        a gate that exposes `lookup` and nothing else (`WP-16`).

        The repository is scanned through the governed worktree when one
        exists, because that is the line the intents were based on. It is
        never *created* here: `recovery.reconcile` authorizes observation only,
        and a worktree that does not exist proves no governed commit was ever
        proposed against it.
        """
        result = run_recovery(
            project_id,
            store=self.store,
            provider=self.recovery_provider(),
            provider_for=lambda invocation: GovernedProvider(self._worker_provider(invocation), RECOVERY_CAPABILITIES),
            repo=None
            if self.repo is None
            else self.governed_repo(project_id, create=False),
            settle=lambda record, resolution: self._settle(
                project_id, record, resolution
            ),
        )
        settled, unresolved = self.recover_validations(project_id)
        result.validations_reconciled = tuple(settled)
        result.unresolved = tuple(result.unresolved) + tuple(unresolved)
        return result

    def _settle(
        self, project_id: Id, record, resolution: Resolution
    ) -> Settlement:
        """Write down what recovery observed. The only writer of row 4."""
        if isinstance(record, WorkerInvocation):
            return self._settle_invocation(project_id, record, resolution)
        return self._settle_intent(project_id, record, resolution)

    def _settled_state(self, record, project_id: Id, observation: Observation):
        return derive_reconciliation_state(
            record_epoch=record.controller_epoch,
            project_epoch=self.store.get_project(project_id).controller_epoch,
            status_terminal=is_terminal_status(record.status),
            observation=observation,
            prior=record.reconciliation_state,
        )

    def _settle_invocation(
        self, project_id: Id, invocation: WorkerInvocation, resolution: Resolution
    ) -> Settlement:
        observation = resolution.observation
        state = self._settled_state(invocation, project_id, observation)
        escalation_id = None
        status = invocation.status
        extras = {}

        if observation is Observation.FINISHED:
            outcome = resolution.lookup_result.outcome
            # `W-INV-4`: the outcome is adopted as it was. A refusal is a
            # refusal; adoption never upgrades it.
            status = status_for_outcome(outcome.status)
            output = GovernedProvider(self._worker_provider(invocation), RECOVERY_CAPABILITIES).fetch(outcome.output_ref)
            termination_reason = outcome.termination_reason
            usage = Usage()
            if outcome.output_ref.media_type == 'application/vnd.gruntime.worker-result+json':  # guard:gr07_structured_recovery
                from .worker_protocol import result_document
                from .errors import GovernedRuntimeError
                try:
                    document = result_document(output, invocation.invocation_id)
                    self._worker_session(self._request_for(invocation), document)
                    extras = self._worker_claim_fields(invocation, document)
                except (GovernedRuntimeError, ValueError, KeyError, TypeError):
                    status = InvocationStatus.FAILED
                    termination_reason = TerminationReason.PROVIDER_ERROR
        elif observation is Observation.ABSENT:
            # Nothing ran under the key: the positive finding that the
            # invocation never took effect (transition-matrix §7.2).
            status = InvocationStatus.FAILED
            output = b""
            termination_reason = TerminationReason.PROVIDER_ERROR
            usage = Usage()
        elif observation is Observation.LIVE:
            invocation.reconciliation_state = state
            self.store.put_invocation(invocation, project_id)
            return Settlement(state=state)
        else:
            escalation_id = self._raise_escalation(
                project_id,
                trigger=EscalationTrigger.RECOVERY_AMBIGUITY,
                severity=EscalationSeverity.HIGH,
                summary=(
                    f"lookup cannot say whether invocation "
                    f"{invocation.invocation_id} ran"
                ),
                run_id=invocation.run_id,
            )
            invocation.reconciliation_state = state
            self.store.put_invocation(invocation, project_id)
            return Settlement(state=state, escalation_id=escalation_id)

        invocation.reconciliation_state = state
        self._mint_worker_receipt(
            invocation,
            project_id,
            output=output,
            termination_reason=termination_reason,
            attribution=Attribution.RECONCILED,
            status=status,
            usage=usage,
            **extras,
        )
        return Settlement(state=state)

    def _settle_intent(
        self, project_id: Id, intent: CommitIntent, resolution: Resolution
    ) -> Settlement:
        observation = resolution.observation
        state = self._settled_state(intent, project_id, observation)
        intent.reconciliation_state = state

        if observation in (
            Observation.TOKEN_MATCHED,
            Observation.TOKEN_MATCHED_DIVERGED,
        ):
            self._settle_commit_receipt(
                intent,
                project_id,
                revision_id=resolution.revision_id,
                parent_revision_ids=resolution.parent_revision_ids,
                actual_tree_digest=resolution.actual_tree_digest,
                diff=self.governed_repo(project_id, create=False).diff(
                    resolution.revision_id
                ),
                attribution=Attribution.RECONCILED,
            )
            return Settlement(state=state)

        if observation is Observation.NO_TOKEN_BASE_UNCHANGED:
            # §7.4: nothing landed. An intent that had reached `APPLYING`
            # failed to apply; one that had not is left exactly as it was —
            # the scan is a finding about the repository, not a verdict on a
            # status it never reached.
            status = (
                CommitIntentStatus.FAILED
                if intent.status is CommitIntentStatus.APPLYING
                else intent.status
            )
            self._transition_intent(
                intent,
                project_id,
                status=status,
                event_type="commit_intent.orphaned",
                payload={
                    "operation_token": intent.operation_token,
                    "base_revision_id": intent.base_revision_id,
                    "reconciliation_state": state.value,
                },
                kernel_capabilities=RECOVERY_CAPABILITIES,
            )
            return Settlement(state=state)

        escalation_id = self._raise_escalation(
            project_id,
            trigger=EscalationTrigger.RECOVERY_AMBIGUITY,
            severity=EscalationSeverity.HIGH,
            summary=(
                f"repository scan cannot decide whether intent "
                f"{intent.intent_id} landed"
            ),
            run_id=intent.run_id,
        )
        self.store.put_commit_intent(intent, project_id)
        return Settlement(state=state, escalation_id=escalation_id)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for `python -m gruntime.controller`.

    Parses the command line documented in the module docstring, opens the
    store, runs the named command, and prints its JSON result on stdout.

    This is the composition root: the only place that names concrete adapters.
    """
    import argparse

    from .adapters.fake_provider import FakeProvider
    from .adapters.git_repo import GitRepository

    parser = argparse.ArgumentParser(prog="gruntime.controller")
    parser.add_argument("--db", required=True)
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--journal", required=True)
    parser.add_argument("--repo")
    parser.add_argument("--project", required=True)
    parser.add_argument(
        "--lease-ttl-ms",
        type=int,
        default=DEFAULT_TTL_MS,
        help=(
            "how long this controller's repository lease is honoured without "
            "renewal; a crashed holder blocks the repository for this long"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start")
    subparsers.add_parser("recover")
    subparsers.add_parser("snapshot")

    invoke_parser = subparsers.add_parser("invoke")
    invoke_parser.add_argument("--run", required=True)
    invoke_parser.add_argument("--prompt", default="work")

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--run", required=True)
    validate_parser.add_argument("--spec", required=True)

    commit_parser = subparsers.add_parser("commit")
    commit_parser.add_argument("--run", required=True)
    commit_parser.add_argument("--path", required=True)
    commit_parser.add_argument("--content", required=True)
    commit_parser.add_argument("--message", default="governed change")

    args = parser.parse_args(argv)

    store = StateStore.open(Path(args.db))
    try:
        controller = Controller(
            store=store,
            artifacts=ArtifactStore(Path(args.artifacts)),
            provider=FakeProvider(Path(args.journal)),
            repo=GitRepository(Path(args.repo)) if args.repo else None,
            lease_ttl_ms=args.lease_ttl_ms,
        )
        project_id = args.project
        epoch = controller.start(project_id)
        result: dict = {"project_id": project_id, "controller_epoch": epoch}

        if args.command == "start":
            pass
        elif args.command == "snapshot":
            snapshot_id = controller.take_snapshot(project_id)
            snapshot = store.get_snapshot(snapshot_id)
            result["snapshot_id"] = snapshot_id
            result["snapshot_hash"] = snapshot.snapshot_hash
            result["suspension"] = store.get_project(project_id).suspension.value
        elif args.command == "recover":
            outcome = controller.recover(project_id)
            result["reconciled"] = {
                "invocations": list(outcome.invocations_reconciled),
                "intents": list(outcome.intents_reconciled),
                "escalations": list(outcome.escalations_raised),
                "unresolved": list(outcome.unresolved),
                "validations": list(outcome.validations_reconciled),
            }
        elif args.command == "validate":
            controller.recover(project_id)
            receipt = controller.execute_validation(args.run, args.spec)
            result["receipt_id"] = receipt.receipt_id
            result["verdict"] = receipt.verdict
        elif args.command == "invoke":
            controller.recover(project_id)
            invocation = controller.create_invocation(
                args.run, prompt=args.prompt.encode("utf-8")
            )
            controller.mark_dispatched(invocation.invocation_id)
            receipt = controller.invoke(invocation.invocation_id)
            result["invocation_id"] = invocation.invocation_id
            result["receipt_id"] = receipt.receipt_id
        elif args.command == "commit":
            controller.recover(project_id)
            intent = controller.propose_commit(
                args.run,
                path=args.path,
                content=args.content,
                message=args.message,
            )
            controller.authorize_commit(intent.intent_id)
            receipt = controller.apply_commit(intent.intent_id)
            result["intent_id"] = intent.intent_id
            result["revision_id"] = receipt.revision_id

        print(json.dumps(result))
        return 0
    finally:
        store.close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
