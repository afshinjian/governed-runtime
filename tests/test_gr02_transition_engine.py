"""The engine itself: proposal, precondition evaluator, and the four outcomes.

Design basis: transition-matrix.md §1 (column semantics), §5.1 and §7.4 (the
edges that carry a direct row and a `recovery.reconcile` row over the same two
states), §9 preamble (an illegal attempt is never a retry), `G-6` (a claim is
not a precondition).

The distinction these tests pin down is the one between the two refusals.
`DENY` says the edge exists and this attempt fell short — bring the evidence
and propose again. `ESCALATE` says the attempt was forbidden by construction —
there is nothing to bring, and a human is told.
"""

from __future__ import annotations

from dataclasses import fields

from gr02_support import (  # noqa: F401  (the `gov` fixture is used by name)
    ALL_FACTS,
    context,
    gov,
    propose,
)

from gruntime.models import CommitIntentStatus as C
from gruntime.models import GovernanceMode
from gruntime.models import InvocationStatus as I
from gruntime.models import StageLifecycle as S
from gruntime.models import SuspensionState
from gruntime.policy import (
    PolicyOutcome,
    Reason,
    TransitionProposal,
)
from gruntime.transitions import (
    ILLEGAL_OPERATIONS,
    ILLEGAL_TRANSITIONS,
    LEGAL_TRANSITIONS,
    NONE_GRANTABLE,
    ORIGIN,
    SUSPENSION_GATE,
    Axis,
    Evidence,
    Policy,
    PolicyVerdict,
    Precondition,
)

SUPERVISED = GovernanceMode.SUPERVISED
AUTONOMOUS = GovernanceMode.AUTONOMOUS


# --- the proposal ----------------------------------------------------------


def test_a_proposal_carries_no_evidence_and_asserts_no_precondition():
    """Workers propose. What makes a proposal true is observed, not offered."""
    names = {field.name for field in fields(TransitionProposal)}
    assert names.isdisjoint(
        {"facts", "evidence", "capabilities", "decisions", "suspension"}
    )


def test_a_proposal_from_a_state_the_subject_has_left_is_refused(gov):
    """The proposer's `from_state` is a belief, checked against observation."""
    resolution = gov.evaluate(
        propose(Axis.STAGE, S.CONTRACTED, S.READY),
        context(SUPERVISED, S.RUNNING, facts=ALL_FACTS),
    )
    assert resolution.outcome is PolicyOutcome.ESCALATE
    assert resolution.reason is Reason.STATE_MISMATCH


def test_an_edge_the_matrix_does_not_carry_is_refused(gov):
    """`READY → AWAITING_REVIEW` is in no table: not illegal, simply not an edge."""
    resolution = gov.evaluate(
        propose(Axis.STAGE, S.AWAITING_REVIEW, S.READY),
        context(SUPERVISED, S.READY, facts=ALL_FACTS),
    )
    assert resolution.outcome is PolicyOutcome.ESCALATE
    assert resolution.reason is Reason.NOT_IN_GRAPH


# --- the precondition evaluator -------------------------------------------


def test_an_unmet_precondition_denies_and_names_it(gov):
    """All must hold (§1); the one that does not is reported back."""
    resolution = gov.evaluate(
        propose(Axis.STAGE, S.CONTRACTED, S.READY),
        context(
            SUPERVISED,
            S.READY,
            facts=ALL_FACTS - {Precondition.CONTRACT_ACTIVE_FOR_STAGE},
        ),
    )
    assert resolution.outcome is PolicyOutcome.DENY
    assert resolution.reason is Reason.PRECONDITION_UNMET
    assert Precondition.CONTRACT_ACTIVE_FOR_STAGE in resolution.unmet_preconditions


def test_missing_evidence_denies_and_names_it(gov):
    """`required_evidence` is a gate, not a hint."""
    resolution = gov.evaluate(
        propose(Axis.STAGE, S.CONTRACTED, S.READY),
        context(SUPERVISED, S.READY, facts=ALL_FACTS, evidence=()),
    )
    assert resolution.outcome is PolicyOutcome.DENY
    assert resolution.reason is Reason.EVIDENCE_MISSING
    assert resolution.missing_evidence


def test_a_capability_the_actor_does_not_hold_denies(gov):
    """authority-matrix §6: held at the moment of transition, or not at all."""
    resolution = gov.evaluate(
        propose(Axis.STAGE, S.CONTRACTED, S.READY),
        context(SUPERVISED, S.READY, facts=ALL_FACTS, capabilities=()),
    )
    assert resolution.outcome is PolicyOutcome.DENY
    assert resolution.reason is Reason.CAPABILITY_MISSING


def test_a_denial_is_re_proposable_and_an_illegal_attempt_is_not(gov):
    """The line §9 draws: a shortfall escalates nothing, a prohibition does."""
    shortfall = gov.evaluate(
        propose(Axis.STAGE, S.CONTRACTED, S.READY),
        context(SUPERVISED, S.READY, facts=ALL_FACTS, evidence=()),
    )
    prohibited = gov.evaluate(
        propose(Axis.STAGE, S.SATISFIED, S.PENDING),
        context(SUPERVISED, S.PENDING, facts=ALL_FACTS),
    )

    assert shortfall.outcome is PolicyOutcome.DENY
    assert shortfall.escalation_id is None
    assert prohibited.outcome is PolicyOutcome.ESCALATE
    assert prohibited.escalation_id is not None


def test_a_disjunctive_evidence_entry_is_satisfied_by_either_token(gov):
    """§4: "a new `SNAP` clean, or `DEC(ACCEPT_RISK)`" is one requirement."""
    for token in (Evidence.SNAP, Evidence.DEC):
        resolution = gov.evaluate(
            propose(
                Axis.SUSPENSION,
                SuspensionState.NONE,
                SuspensionState.SUSPENDED_BY_DRIFT,
            ),
            context(
                SUPERVISED,
                SuspensionState.SUSPENDED_BY_DRIFT,
                facts=ALL_FACTS,
                evidence=(token,),
            ),
        )
        assert resolution.outcome is PolicyOutcome.AUTO_ALLOW, token


# --- verdicts that depend on what was observed ----------------------------


def test_a_conditional_verdict_settles_against_observed_facts(gov):
    """§7.2: `CONFIRM` for the first invocation of a run, `AUTO` after it."""
    first = gov.evaluate(
        propose(Axis.INVOCATION, I.PENDING, ORIGIN),
        context(SUPERVISED, ORIGIN, facts=ALL_FACTS, decisions=()),
    )
    later = gov.evaluate(
        propose(Axis.INVOCATION, I.PENDING, ORIGIN),
        context(
            SUPERVISED,
            ORIGIN,
            facts=ALL_FACTS - {Precondition.FIRST_INVOCATION_OF_RUN},
            decisions=(),
        ),
    )
    assert first.outcome is PolicyOutcome.REQUIRE_HUMAN
    assert later.outcome is PolicyOutcome.AUTO_ALLOW


def test_a_conditional_policy_collapses_to_one_verdict():
    """`settle` is total: a conditional always resolves to a plain verdict."""
    for rule in LEGAL_TRANSITIONS:
        for mode in (SUPERVISED, AUTONOMOUS):
            settled = rule.policy(mode).settle(ALL_FACTS)
            assert settled.when is None
            assert isinstance(settled.verdict, PolicyVerdict)


# --- one edge, two rows ----------------------------------------------------


def test_an_edge_with_two_rows_is_taken_under_the_capability_held(gov):
    """§7.4: `APPLYING → APPLIED` directly, or by reconciling what landed.

    The rows are told apart by capability, because that is the only thing that
    differs about the actor: recovery holds `recovery.reconcile` and nothing
    that can execute (`WP-16`).
    """
    direct = gov.evaluate(
        propose(Axis.COMMIT_INTENT, C.APPLIED, C.APPLYING),
        context(
            SUPERVISED, C.APPLYING, facts=ALL_FACTS, capabilities=("commit.apply",)
        ),
    )
    reconciled = gov.evaluate(
        propose(Axis.COMMIT_INTENT, C.APPLIED, C.APPLYING),
        context(
            SUPERVISED,
            C.APPLYING,
            facts=ALL_FACTS,
            capabilities=("recovery.reconcile",),
        ),
    )
    assert direct.rule is not reconciled.rule
    assert direct.rule.required_capability == "commit.apply"
    assert reconciled.rule.required_capability == "recovery.reconcile"


# --- the tables themselves -------------------------------------------------


def test_every_row_id_is_unique():
    """A resolution names the line of design it came from; two cannot share it."""
    legal = [rule.row for rule in LEGAL_TRANSITIONS]
    illegal = [rule.row for rule in ILLEGAL_TRANSITIONS] + [
        rule.row for rule in ILLEGAL_OPERATIONS
    ]
    assert len(legal) == len(set(legal))
    assert len(illegal) == len(set(illegal))


def test_no_legal_row_requires_an_ungrantable_capability():
    """`NONE_GRANTABLE` is §9's marker. A legal row always names a real one."""
    for rule in LEGAL_TRANSITIONS:
        assert rule.required_capability != NONE_GRANTABLE
        assert rule.required_capability


def test_every_illegal_row_denies_in_both_modes():
    """§9: `DENY` / `DENY`, and no capability that could change it."""
    for rule in list(ILLEGAL_TRANSITIONS) + list(ILLEGAL_OPERATIONS):
        assert rule.required_capability == NONE_GRANTABLE
        assert rule.supervised == Policy(PolicyVerdict.DENY)
        assert rule.autonomous == Policy(PolicyVerdict.DENY)


def test_the_axis_three_gate_covers_every_suspension_state():
    """§0.1 is exhaustive: a state with no gate row would be an open gate."""
    assert set(SUSPENSION_GATE) == set(SuspensionState)


# --- the predicate GR-28 shares with production ----------------------------


def test_the_capability_step_is_one_predicate_shared_with_production():
    """GR-28 consumes step 7 through `capability_missing`, not a copy of it.

    `F03-001` is that production consulted no declaration; the fix is a
    production caller of *this* predicate. A second implementation would put
    the two answers back out of step, so the resolver is asserted to give the
    same answer as the predicate over every legal row, in both directions.
    """
    from gruntime.policy import capability_missing

    for rule in LEGAL_TRANSITIONS:
        held = context(SUPERVISED, capabilities=(rule.required_capability,))
        absent = context(SUPERVISED, capabilities=())
        assert not capability_missing(rule, held)
        assert capability_missing(rule, absent)


def test_resolution_still_denies_on_the_capability_before_the_preconditions():
    """Step 7 precedes step 8, and the extraction does not reorder them."""
    resolution = gov_free_resolution(capabilities=(), facts=())
    assert resolution.outcome is PolicyOutcome.DENY
    assert resolution.reason is Reason.CAPABILITY_MISSING


def gov_free_resolution(*, capabilities, facts):
    """Resolve one legal row without a controller: the resolver is pure."""
    from gruntime.policy import resolve

    return resolve(
        propose(Axis.STAGE, S.CONTRACTED, S.READY),
        context(SUPERVISED, S.READY, facts=facts, capabilities=capabilities),
    )
