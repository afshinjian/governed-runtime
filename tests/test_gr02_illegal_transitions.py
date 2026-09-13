"""Every row of transition-matrix §9.1 and §9.2, refused by the controller.

One test per row of the ILLEGAL SECTION, named for the row. Each proposes the
forbidden edge under a saturated context — every capability the graph names,
every evidence class, a `VALID` `HumanDecision` of every kind — and under both
governance profiles. A refusal that survives all of that is the structural
refusal §9 describes: `required_capability = NONE_GRANTABLE`, both policy
columns `DENY`, and the attempt itself an escalation rather than a retry.

Design basis: transition-matrix.md §9 preamble, §9.1, §9.2, and §0.1 for the
two rows whose permitted set *is* the axis-3 gate.
"""

from __future__ import annotations

from gr02_support import (  # noqa: F401  (the `gov` fixture is used by name)
    gov,
    propose,
    refuse_in_both_modes,
)

from gruntime.models import ProjectLifecycle as P
from gruntime.models import StageLifecycle as S
from gruntime.models import SuspensionState
from gruntime.policy import PolicyOutcome, Reason
from gruntime.transitions import ORIGIN, Axis, Precondition

# --- §9.1 illegal stage transitions ---------------------------------------


def test_9_1_01_pending_to_satisfied(gov):
    """no contract, no run, no receipt can exist."""
    refuse_in_both_modes(
        gov, propose(Axis.STAGE, S.SATISFIED, S.PENDING), row="9.1-1"
    )


def test_9_1_02_pending_to_running(gov):
    """skips the READY dependency check and the CONTRACTED authority grant."""
    refuse_in_both_modes(
        gov, propose(Axis.STAGE, S.RUNNING, S.PENDING), row="9.1-2"
    )


def test_9_1_03_ready_to_running(gov):
    """a run without an ACTIVE contract has no effective_capabilities."""
    refuse_in_both_modes(
        gov, propose(Axis.STAGE, S.RUNNING, S.READY), row="9.1-3"
    )


def test_9_1_04_ready_to_satisfied(gov):
    """no StageRun, therefore no receipts bound to this stage."""
    refuse_in_both_modes(
        gov, propose(Axis.STAGE, S.SATISFIED, S.READY), row="9.1-4"
    )


def test_9_1_05_contracted_to_satisfied(gov):
    """activation grants authority but produces no evidence."""
    refuse_in_both_modes(
        gov, propose(Axis.STAGE, S.SATISFIED, S.CONTRACTED), row="9.1-5"
    )


def test_9_1_06_running_to_satisfied(gov):
    """bypasses validation and review."""
    refuse_in_both_modes(
        gov, propose(Axis.STAGE, S.SATISFIED, S.RUNNING), row="9.1-6"
    )


def test_9_1_07_awaiting_validation_to_satisfied(gov):
    """mandatory judgmental criteria have no Review yet."""
    refuse_in_both_modes(
        gov,
        propose(Axis.STAGE, S.SATISFIED, S.AWAITING_VALIDATION),
        row="9.1-7",
    )


def test_9_1_08_any_to_satisfied_on_declared_status(gov):
    """a CLAIM is not EVIDENCE; `G-6` forbids `declared_status` in a precondition.

    Proposed from `AWAITING_REVIEW`, which is a legal origin for `SATISFIED`:
    the row is what stops the *basis* being a worker's claim, so it has to
    shadow the legal edge exactly when that claim is the basis.
    """
    refuse_in_both_modes(
        gov,
        propose(Axis.STAGE, S.SATISFIED, S.AWAITING_REVIEW),
        row="9.1-8",
        facts=(Precondition.DECLARED_STATUS_AS_BASIS,),
    )


def test_9_1_09_any_to_satisfied_without_observed_satisfaction(gov):
    """satisfaction must be measured against the current snapshot."""
    refuse_in_both_modes(
        gov,
        propose(Axis.STAGE, S.SATISFIED, S.AWAITING_REVIEW),
        row="9.1-9",
        facts=(Precondition.OBSERVED_SATISFACTION_NOT_SATISFIED,),
    )


def test_9_1_10_satisfied_to_running(gov):
    """re-entry must pass through READY."""
    refuse_in_both_modes(
        gov, propose(Axis.STAGE, S.RUNNING, S.SATISFIED), row="9.1-10"
    )


def test_9_1_11_abandoned_to_any(gov):
    """terminal by `G-7`; resumption requires a new stage revision."""
    for target in (S.READY, S.RUNNING, S.SATISFIED, S.PENDING):
        refuse_in_both_modes(
            gov, propose(Axis.STAGE, target, S.ABANDONED), row="9.1-11"
        )


def test_9_1_12_rejected_to_satisfied(gov):
    """reverses a recorded human rejection without a new run or new evidence."""
    refuse_in_both_modes(
        gov, propose(Axis.STAGE, S.SATISFIED, S.REJECTED), row="9.1-12"
    )


def test_9_1_13_any_transition_while_suspended(gov):
    """suspension is a hard gate; allowing progress would make it advisory.

    The legal `AWAITING_REVIEW → SATISFIED` edge, refused solely because the
    holder is suspended — and the same edge to `ABANDONED` still permitted,
    because §0.1 is the permitted set this row defers to.
    """
    refuse_in_both_modes(
        gov,
        propose(Axis.STAGE, S.SATISFIED, S.AWAITING_REVIEW),
        row="9.1-13",
        reason=Reason.SUSPENDED,
        suspension=SuspensionState.SUSPENDED_BY_HUMAN,
    )


def test_9_1_13_gate_still_permits_abandonment(gov):
    """§0.1: a suspended holder may still reach `ABANDONED`."""
    from gr02_support import context

    from gruntime.models import GovernanceMode

    resolution = gov.evaluate(
        propose(Axis.STAGE, S.ABANDONED, S.AWAITING_REVIEW),
        context(
            GovernanceMode.SUPERVISED,
            S.AWAITING_REVIEW,
            suspension=SuspensionState.SUSPENDED_BY_HUMAN,
        ),
    )
    assert resolution.reason is not Reason.SUSPENDED


# --- §9.2 illegal project transitions -------------------------------------


def test_9_2_01_draft_to_active(gov):
    """no roadmap imported, so no stage exists to act on."""
    refuse_in_both_modes(
        gov, propose(Axis.PROJECT, P.ACTIVE, P.DRAFT), row="9.2-1"
    )


def test_9_2_02_draft_or_planning_to_completed(gov):
    """with no runs there is nothing to assert satisfaction over."""
    for origin in (P.DRAFT, P.PLANNING):
        refuse_in_both_modes(
            gov, propose(Axis.PROJECT, P.COMPLETED, origin), row="9.2-2"
        )


def test_9_2_03_active_to_completed(gov):
    """must pass through SETTLING."""
    refuse_in_both_modes(
        gov, propose(Axis.PROJECT, P.COMPLETED, P.ACTIVE), row="9.2-3"
    )


def test_9_2_04_archived_to_any(gov):
    """terminal; the evidence set is sealed."""
    for target in (P.ACTIVE, P.SETTLING, P.COMPLETED, P.DRAFT):
        refuse_in_both_modes(
            gov, propose(Axis.PROJECT, target, P.ARCHIVED), row="9.2-4"
        )


def test_9_2_05_origin_to_draft_by_a_non_human_creator(gov):
    """a runtime or worker cannot originate a project and its own ceiling."""
    refuse_in_both_modes(
        gov,
        propose(Axis.PROJECT, P.DRAFT, ORIGIN),
        row="9.2-5",
        facts=(Precondition.CREATOR_IS_NOT_HUMAN,),
    )


def test_9_2_06_any_transition_under_integrity_suspension(gov):
    """the audit chain is untrusted; no state written under it is meaningful."""
    refuse_in_both_modes(
        gov,
        propose(Axis.PROJECT, P.SETTLING, P.ACTIVE),
        row="9.2-6",
        reason=Reason.SUSPENDED,
        suspension=SuspensionState.SUSPENDED_BY_INTEGRITY,
    )


# --- the shape of a §9 refusal --------------------------------------------


def test_an_illegal_attempt_raises_an_escalation_and_changes_nothing(gov):
    """§9: the attempt is an escalation, and it suspends nothing by itself."""
    resolution = refuse_in_both_modes(
        gov, propose(Axis.STAGE, S.SATISFIED, S.PENDING), row="9.1-1"
    )
    assert resolution.outcome is PolicyOutcome.ESCALATE
    raised = [
        escalation
        for escalation in gov.escalations()
        if escalation.escalation_id == resolution.escalation_id
    ]
    assert len(raised) == 1
    assert raised[0].suspension_applied is SuspensionState.NONE


def test_every_resolution_is_audited(gov):
    """authority-matrix §6: an enforced denial emits an AUTHORITY event."""
    before = len(gov.events())
    refuse_in_both_modes(
        gov, propose(Axis.STAGE, S.SATISFIED, S.READY), row="9.1-4"
    )
    resolved = [
        event
        for event in gov.events()
        if event.event_type == "transition.resolved"
    ]
    assert len(gov.events()) > before
    assert len(resolved) == 2  # one per governance profile
    assert all(event.epistemic_class.value == "AUTHORITY" for event in resolved)
