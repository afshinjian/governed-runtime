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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence

from .artifacts import ArtifactStore
from .canonical import canonical_json, digest_json
from .commit import (
    APPLY_CAPABILITY,
    AUTHORIZE_CAPABILITY,
    PROPOSE_CAPABILITY,
    build_receipt,
    build_trailers,
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
from .errors import BarrierViolation, IntegrityViolation, PolicyDenied
from .gate import (
    AFTER_COMMIT_BEFORE_RECEIPT,
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
from .policy import (
    PolicyOutcome,
    TransitionContext,
    TransitionProposal,
    TransitionResolution,
    resolve,
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


def _runtime_actor(component: str) -> ActorRef:
    """The kernel acting as itself. Never a worker, never a human."""
    return ActorRef(
        actor_kind=ActorKind.RUNTIME,
        actor_id=f"gruntime.{component}",
        auth_method=AuthMethod.NONE,
    )


class Controller:
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
        self.provider = provider
        #: The user's checkout: observed by every snapshot, written by nothing.
        self.repo = repo
        #: Where runtime-owned state that is not the workspace lives — the
        #: governed worktree and the repository lease. Never inside the
        #: workspace, or the runtime's own files would read as workspace drift.
        self.governance_dir = Path(governance_dir or store.db_path.parent)
        self.lease_ttl_ms = lease_ttl_ms

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
        """
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
        component: str = "controller",
    ):
        return self.store.append_event(
            project_id,
            event_type=event_type,
            epistemic_class=epistemic_class,
            actor=_runtime_actor(component),
            subject={key: str(value) for key, value in subject.items()},
            payload=canonical_json(payload),
            capability_used=capability_used,
        )

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
        project = self.store.get_project(project_id)
        if project.suspension is suspension:
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
            suspension_target="RUN" if run_id else "PROJECT",
            status=EscalationStatus.OPEN,
            run_id=run_id,
        )
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
        return escalation.escalation_id

    # -- project and run ---------------------------------------------------

    def create_project(self, *, name: str, slug: str, workspace_root: str) -> Id:
        """Create a project and anchor its chain with the genesis event."""
        project_id = f"prj-{uuid.uuid4().hex}"
        created_at = now_ts()
        event = self._append(
            project_id,
            event_type="project.created",
            epistemic_class=EpistemicClass.AUTHORITY,
            subject={"project_id": project_id},
            payload={
                "name": name,
                "slug": slug,
                "workspace_root": workspace_root,
                "schema_version": SCHEMA_VERSION,
            },
            capability_used="project.create",
        )
        self.store.put_project(
            Project(
                project_id=project_id,
                name=name,
                slug=slug,
                schema_version=SCHEMA_VERSION,
                lifecycle=ProjectLifecycle.ACTIVE,
                suspension=SuspensionState.NONE,
                governance_mode=GovernanceMode.AUTONOMOUS,
                workspace_root=workspace_root,
                created_at=created_at,
                updated_at=created_at,
                created_by=_runtime_actor("controller"),
                event_head=event.event_hash,
                event_seq=event.seq,
                controller_epoch=0,
            )
        )
        return project_id

    def start(self, project_id: Id) -> int:
        """Increment `controller_epoch` and return the new value.

        `P-INV-4`: the increment is committed before this controller does any
        other work, so an operation carrying a lower epoch is provably the
        work of a controller that is gone.
        """
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
        run_id = f"run-{uuid.uuid4().hex}"
        run = StageRun(
            run_id=run_id,
            project_id=project_id,
            stage_id=f"stage-{run_id[4:12]}",
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

    def _observe(self, project_id: Id):
        """Fingerprint the workspace: tracked reality only.

        The user's checkout is what is measured, never the governed worktree:
        the worktree is the runtime's own scratch space and measuring it would
        make the runtime's activity indistinguishable from the world's.
        """
        project = self.store.get_project(project_id)
        if self.repo is not None:
            workspace = Path(project.workspace_root).resolve()
            if workspace == Path(self.repo.root).resolve():
                return observe_repository(self.repo, scope=WHOLE_WORKSPACE)
        return observe_filesystem(Path(project.workspace_root), scope=WHOLE_WORKSPACE)

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
        is ever cleared.
        """
        fingerprint = self._observe(project_id)
        index_ref = self.store.store_artifact(
            canonical_json(fingerprint.document()), media_type="application/json"
        )
        # The baseline is the newest `COMPLETE` snapshot, not merely the last
        # one: a failed observation is neither a baseline nor a comparand
        # (`RS-INV-1`). Comparing against one would report the whole workspace
        # as having vanished and then reappeared.
        previous = self.store.newest_complete_snapshot(project_id)
        attributed = self._attributed_globs(project_id)
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

        snapshot_id = f"snap-{uuid.uuid4().hex}"
        snapshot = RealitySnapshot(
            snapshot_id=snapshot_id,
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
        self._append(
            project_id,
            event_type="snapshot.taken",
            epistemic_class=EpistemicClass.EVIDENCE,
            subject={"snapshot_id": snapshot_id},
            payload={
                "trigger": trigger.value,
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
        )
        self.store.put_snapshot(snapshot)
        # A failed observation is recorded as evidence — it is a true fact
        # about a moment — but it never becomes the current reality. Pointing
        # `snapshot_current` at a snapshot that saw nothing would make "the
        # workspace as the runtime last knew it" mean "nothing is there".
        if snapshot.completeness is Completeness.COMPLETE:
            self.store.set_project_snapshot_current(project_id, snapshot_id)

        if comparable:
            self._stale_decisions_against(project_id, previous, snapshot)
        if drifted:
            self._on_reality_drift(project_id, snapshot, drifted)
        return snapshot_id

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
        escalation_id = self._raise_escalation(
            project_id,
            trigger=EscalationTrigger.REALITY_DRIFT,
            severity=EscalationSeverity.HIGH,
            summary=(
                f"snapshot {snapshot.snapshot_id} found {len(paths)} unattributed "
                f"change(s) in the workspace: {listed}"
            ),
            suspension=SuspensionState.SUSPENDED_BY_DRIFT,
        )
        self._set_suspension(
            project_id,
            SuspensionState.SUSPENDED_BY_DRIFT,
            reason=f"unattributed drift in {snapshot.snapshot_id}",
            suspension_ref=escalation_id,
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
        scope: DecisionScope = DecisionScope.PROJECT,
        expires_at: Optional[datetime] = None,
    ) -> HumanDecision:
        """Record a human's decision. `∅ → VALID` (transition-matrix §7.5-1).

        Refused unless it is a human's: `HD-INV-1` — a runtime or a worker
        cannot manufacture authority. Refused with empty `evidence_shown`:
        `HD-INV-2` — an uninformed approval discharges nothing. A
        snapshot-bound decision is bound here to the newest `COMPLETE`
        snapshot, which is the reality the human was actually shown.
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
        bound = is_snapshot_bound(subject_kind, decision_kind)
        subject_snapshot_id = None
        if bound:
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
            subject_snapshot_id=subject_snapshot_id,
            expires_at=expires_at,
            decision_hash=digest_json(preimage),
            prev_event_hash=self.store.get_project(project_id).event_head,
        )
        self._append(
            project_id,
            event_type="decision.recorded",
            epistemic_class=EpistemicClass.DECISION,
            subject={"decision_id": decision_id},
            payload=preimage,
            capability_used="decision.record",
            component="decision",
        )
        self.store.put_decision(decision)
        return decision

    # -- invocations (worker_provider §6) ----------------------------------

    def create_invocation(self, run_id: Id, *, prompt: bytes) -> WorkerInvocation:
        """Mint the key and persist the request, before any provider call.

        Refuses with `BarrierViolation` while any record of the run is
        unreconciled: a run that outlived a controller initiates no new
        external effect until its records are settled (`RUN-INV-3`).
        """
        self._assert_barrier_clear(run_id, "creating an invocation")
        run = self.store.get_run(run_id)
        self._assert_may_initiate_effect(run.project_id, "creating an invocation")
        project = self.store.get_project(run.project_id)

        invocation_id = f"inv-{uuid.uuid4().hex}"
        prompt_ref = self.store.store_artifact(
            prompt, media_type="application/octet-stream"
        )
        context_digest = digest_json([])
        deadline_at = now_ts() + DEFAULT_DEADLINE

        # `WP-6`: the key is a function of what will be sent. Rebuilding the
        # bundle after a restart would produce a different key and therefore a
        # second execution, so the key is minted once and read back forever.
        preimage = {
            "invocation_id": invocation_id,
            "worker_role": WorkerRole.IMPLEMENTER.value,
            "binding_id": DEFAULT_BINDING,
            "prompt_bundle_digest": prompt_ref.digest,
            "context_digest": context_digest,
            "scope_root": project.workspace_root,
            "deadline_at": deadline_at.isoformat(),
            "granted_capabilities": [],
        }
        idempotency_key = digest_json(preimage)
        request_ref = self.store.store_artifact(
            canonical_json(dict(preimage, idempotency_key=idempotency_key)),
            media_type="application/json",
        )

        invocation = WorkerInvocation(
            invocation_id=invocation_id,
            run_id=run_id,
            stage_id=run.stage_id,
            provider_id=self.provider.describe().provider_id,
            provider_version=self.provider.describe().provider_version,
            worker_role=WorkerRole.IMPLEMENTER,
            prompt_bundle_ref=prompt_ref,
            request_ref=request_ref,
            request_digest=request_ref.digest,
            context_digest=context_digest,
            idempotency_key=idempotency_key,
            controller_epoch=project.controller_epoch,
            status=InvocationStatus.PENDING,
            reconciliation_state=derive_reconciliation_state(
                record_epoch=project.controller_epoch,
                project_epoch=project.controller_epoch,
                status_terminal=False,
            ),
            deadline_at=deadline_at,
        )
        # Evidence-model §3.2.1 step 1: the identity is durable before the
        # effect, so a crash before the receipt is recoverable by key alone.
        self._append(
            run.project_id,
            event_type="invocation.created",
            epistemic_class=EpistemicClass.AUTHORITY,
            subject={"invocation_id": invocation_id, "run_id": run_id},
            payload={
                "idempotency_key": idempotency_key,
                "request_digest": request_ref.digest,
                "controller_epoch": invocation.controller_epoch,
            },
            capability_used="worker.invoke",
        )
        self.store.put_invocation(invocation, run.project_id)
        return invocation

    def mark_dispatched(self, invocation_id: Id) -> None:
        """`PENDING → DISPATCHED` (transition-matrix §7.1)."""
        invocation = self.store.get_invocation(invocation_id)
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

    def _request_for(self, invocation: WorkerInvocation) -> InvocationRequest:
        """Rebuild the request from the bytes that were persisted, verbatim."""
        document = json.loads(self.store.artifact_bytes(invocation.request_digest))
        return InvocationRequest(
            invocation_id=document["invocation_id"],
            worker_role=WorkerRole(document["worker_role"]),
            binding_id=document["binding_id"],
            prompt_bundle_ref=invocation.prompt_bundle_ref,
            scope_view=ScopeView(
                root=document["scope_root"],
                file_index_ref=invocation.prompt_bundle_ref,
                snapshot_id="",
                writable=False,
            ),
            idempotency_key=document["idempotency_key"],
            deadline_at=datetime.fromisoformat(document["deadline_at"]),
        )

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
    ) -> WorkerReceipt:
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
        receipt = WorkerReceipt(
            receipt_id=f"wr-{uuid.uuid4().hex}",
            invocation_id=invocation.invocation_id,
            ended_at=ended_at,
            duration_ms=0,
            usage=usage,
            output_ref=output_ref,
            output_digest=output_ref.digest,
            termination_reason=termination_reason,
            attribution=attribution,
            attested_by=_runtime_actor("worker_receipt"),
            receipt_hash=digest_json(preimage),
            prev_event_hash=project.event_head,
        )
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
        return receipt

    def invoke(self, invocation_id: Id) -> WorkerReceipt:
        """Call the provider and mint the receipt with `attribution = DIRECT`.

        The gate point between those two steps is where the crash tests kill
        the process.
        """
        invocation = self.store.get_invocation(invocation_id)
        project_id = self.store.invocation_project(invocation_id)
        self._assert_barrier_clear(invocation.run_id, "invoking a worker")

        governed = GovernedProvider(self.provider, DISPATCH_CAPABILITIES)
        outcome = governed.invoke(self._request_for(invocation))

        # The execution happened. Nothing below has been written yet: this is
        # the window recovery has to close from the key alone.
        gate(AFTER_INVOKE_BEFORE_RECEIPT)

        return self._mint_worker_receipt(
            invocation,
            project_id,
            output=governed.fetch(outcome.output_ref),
            termination_reason=outcome.termination_reason,
            attribution=Attribution.DIRECT,
            status=status_for_outcome(outcome.status),
            usage=outcome.usage,
        )

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
        path = assert_unprotected(path)

        governed = self.governed_repo(run.project_id)
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
            capability_used=PROPOSE_CAPABILITY,
            component="commit",
        )
        self.store.put_commit_intent(intent, run.project_id)
        return intent

    def _transition_intent(
        self,
        intent: CommitIntent,
        project_id: Id,
        *,
        status: CommitIntentStatus,
        event_type: str,
        payload: dict,
        capability_used: str,
    ) -> None:
        intent.status = status
        self._append(
            project_id,
            event_type=event_type,
            epistemic_class=EpistemicClass.AUTHORITY,
            subject={"intent_id": intent.intent_id},
            payload=payload,
            capability_used=capability_used,
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
            capability_used=PROPOSE_CAPABILITY,
        )

    def authorize_commit(self, intent_id: Id) -> None:
        """`PROPOSED → AUTHORIZED`.

        Re-evaluates the preconditions rather than trusting the stored value:
        a review-backed precondition is refused here even if something wrote
        one directly into the record (`G-1`).
        """
        intent = self.store.get_commit_intent(intent_id)
        project_id = self.store.intent_project(intent_id)
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
                capability_used=AUTHORIZE_CAPABILITY,
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
            capability_used=AUTHORIZE_CAPABILITY,
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
            capability_used=AUTHORIZE_CAPABILITY,
        )

    def mark_applying(self, intent_id: Id) -> None:
        """`AUTHORIZED → APPLYING`.

        The token and epoch are durable before the first repository mutation,
        so a revision that lands afterwards is always matchable back to this
        intent (`CM-INV-2`).
        """
        intent = self.store.get_commit_intent(intent_id)
        self._transition_intent(
            intent,
            self.store.intent_project(intent_id),
            status=CommitIntentStatus.APPLYING,
            event_type="commit_intent.applying",
            payload={
                "operation_token": intent.operation_token,
                "controller_epoch": intent.controller_epoch,
            },
            capability_used=APPLY_CAPABILITY,
        )

    def _settle_commit_receipt(
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
        diff_ref = self.store.store_artifact(diff, media_type="text/x-diff")
        post_snapshot_id = self.take_snapshot(
            project_id, trigger=SnapshotTrigger.POST_COMMIT
        )
        receipt = build_receipt(
            intent,
            revision_id=revision_id,
            parent_revision_ids=parent_revision_ids,
            actual_tree_digest=actual_tree_digest,
            diff_ref=diff_ref,
            post_snapshot_id=post_snapshot_id,
            attribution=attribution,
            prev_event_hash=self.store.get_project(project_id).event_head,
        )
        capability = (
            "recovery.reconcile"
            if attribution is Attribution.RECONCILED
            else APPLY_CAPABILITY
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
            },
            capability_used=capability,
            component="commit",
        )
        self.store.put_commit_receipt(receipt, project_id)

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
                    "tree that differs from the authorized one"
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
            capability_used=capability,
        )
        return receipt

    def apply_commit(self, intent_id: Id) -> CommitReceipt:
        """Apply the intent and mint the receipt with `attribution = DIRECT`.

        Four guards stand between an authorized intent and a landed revision,
        in this order, because each one is cheaper and more conclusive than the
        next:

        1. `RUN-INV-3` — `BarrierViolation` while the run is unreconciled;
        2. the axis-3 gate — `PolicyDenied` while the project is suspended;
        3. protected paths — no grant makes repository metadata writable;
        4. the base — the governed line must still be at `base_revision_id`,
           or the diff that was reviewed is not the diff that would land
           (transition-matrix §9.3).

        Only then is the repository lease taken, and the mutation happens in
        the governed worktree. The user's checkout is neither written to nor
        moved.
        """
        intent = self.store.get_commit_intent(intent_id)
        project_id = self.store.intent_project(intent_id)
        self._assert_barrier_clear(intent.run_id, "applying a commit")
        self._assert_may_initiate_effect(project_id, "applying a commit")
        if intent.status is CommitIntentStatus.AUTHORIZED:
            self.mark_applying(intent_id)
            intent = self.store.get_commit_intent(intent_id)
        if intent.status is not CommitIntentStatus.APPLYING:
            raise IntegrityViolation(
                f"intent {intent_id} is {intent.status.value}, not applying"
            )

        governed = self.governed_repo(project_id)
        for mutation in intent.mutations:
            assert_unprotected(mutation.path)
        verification = verify_head(
            governed,
            expected_revision=intent.base_revision_id,
            expected_ref=intent.target_ref,
        )
        if not verification.matches:
            raise IntegrityViolation(
                f"intent {intent_id} was authorized against "
                f"{intent.base_revision_id} on {intent.target_ref!r}, but "
                f"{verification.reason()}; the reviewed diff is not the diff "
                "that would land (transition-matrix §9.3)"
            )

        with self.repository_lease(project_id):
            # Held across the whole mutation: a second controller writing the
            # governed line here would make `CM-INV-3`'s "one revision, or
            # provably none" a statement about one process rather than about
            # the repository.
            gate(INSIDE_REPOSITORY_LEASE)
            paths = []
            for mutation in intent.mutations:
                governed.write_file(
                    mutation.path,
                    self.store.artifact_bytes(
                        mutation.after_ref.digest
                    ).decode("utf-8"),
                )
                paths.append(mutation.path)

            revision_id = governed.commit(
                message=intent.message, trailers=intent.trailers, paths=paths
            )

        # The revision exists and carries the token. Nothing below is written
        # yet: recovery finds it by that token and adopts it.
        gate(AFTER_COMMIT_BEFORE_RECEIPT)

        return self._settle_commit_receipt(
            intent,
            project_id,
            revision_id=revision_id,
            parent_revision_ids=governed.parents(revision_id),
            actual_tree_digest=governed.tree_digest(revision_id),
            diff=governed.diff(revision_id),
            attribution=Attribution.DIRECT,
        )

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
        attestation = mint_attestation(
            reviews=reviews,
            review_spec_id=review_spec_id,
            quorum=quorum,
            independence_required=True,
            input_snapshot_id=reviews[0].input_snapshot_id,
            contract_hash=digest_json({"review_spec_id": review_spec_id}),
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
        return run_recovery(
            project_id,
            store=self.store,
            provider=self.recovery_provider(),
            repo=None
            if self.repo is None
            else self.governed_repo(project_id, create=False),
            settle=lambda record, resolution: self._settle(
                project_id, record, resolution
            ),
        )

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

        if observation is Observation.FINISHED:
            outcome = resolution.lookup_result.outcome
            # `W-INV-4`: the outcome is adopted as it was. A refusal is a
            # refusal; adoption never upgrades it.
            status = status_for_outcome(outcome.status)
            output = self.recovery_provider().fetch(outcome.output_ref)
            termination_reason = outcome.termination_reason
            usage = outcome.usage
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
                capability_used="recovery.reconcile",
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
            }
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
