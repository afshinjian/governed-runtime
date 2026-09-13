"""`INV-02` — SUPERVISED and AUTONOMOUS are two columns, not two graphs.

The transition matrix gives every row a `supervised_policy` and an
`autonomous_policy`. It gives no row to one mode and withholds it from the
other: there is one edge set, and a governance mode decides the *verdict* on an
edge, never whether the edge exists. These tests hold the engine to that.

The sweep is the load-bearing one: it resolves every edge of the graph under
both profiles and asserts the admitted edge sets are identical. A mode-`DENY`
row — `∅ → DRAFT` is the only one in the matrix — is still an edge; it resolves
to `ESCALATE`/`MODE_DENIED`, which is a verdict about an edge that exists.

Design basis: transition-matrix.md §1.1 (verdict vocabulary), §2 row 1, §3
rows 5 and 27, authority-matrix.md §3 ("`AUTONOMOUS` never widens the set of
`HUMAN`-class capabilities; it only removes per-action confirmation").
"""

from __future__ import annotations

import pytest
from gr02_support import (  # noqa: F401  (the `gov` fixture is used by name)
    ALL_FACTS,
    context,
    gov,
    propose,
)

from gruntime.models import DecisionKind, GovernanceMode
from gruntime.models import ProjectLifecycle as P
from gruntime.models import StageLifecycle as S
from gruntime.policy import PolicyOutcome, Reason
from gruntime.transitions import (
    ILLEGAL_TRANSITIONS,
    LEGAL_TRANSITIONS,
    ORIGIN,
    Axis,
    PolicyVerdict,
    legal_edges,
)

MODES = (GovernanceMode.SUPERVISED, GovernanceMode.AUTONOMOUS)

#: Edges that carry no `HumanDecision`: every `CONFIRM` and `DECIDE(K)` shows
#: as `REQUIRE_HUMAN` rather than being silently discharged.
UNDECIDED: frozenset[DecisionKind] = frozenset()


def _sweep(gov, mode):
    """Resolve every edge of the graph under one profile."""
    resolved = {}
    for axis, from_state, to_state in legal_edges():
        resolved[(axis, from_state, to_state)] = gov.evaluate(
            propose(axis, to_state, from_state),
            context(mode, from_state, facts=ALL_FACTS, decisions=UNDECIDED),
        )
    return resolved


def _admitted(resolved):
    return frozenset(
        key
        for key, resolution in resolved.items()
        if resolution.reason not in (Reason.NOT_IN_GRAPH, Reason.ILLEGAL)
    )


def test_the_two_profiles_resolve_the_same_legal_transition_set(gov):
    """`INV-02`: one graph. Only the verdict column is per-mode."""
    supervised = _sweep(gov, GovernanceMode.SUPERVISED)
    autonomous = _sweep(gov, GovernanceMode.AUTONOMOUS)

    assert _admitted(supervised) == _admitted(autonomous)
    assert _admitted(supervised) == legal_edges()
    assert legal_edges(), "the graph is empty; nothing was proved"


def test_the_profiles_differ_only_in_policy_outcome(gov):
    """Where the modes disagree, they disagree about the verdict and nothing else."""
    supervised = _sweep(gov, GovernanceMode.SUPERVISED)
    autonomous = _sweep(gov, GovernanceMode.AUTONOMOUS)

    differing = {
        key
        for key in supervised
        if supervised[key].outcome is not autonomous[key].outcome
        or supervised[key].required_decision is not autonomous[key].required_decision
    }
    assert differing, "no row differs between the profiles; the test is vacuous"

    for key in differing:
        # The same row object answered both: preconditions, evidence and
        # capability are not per-mode, because they are not per-mode fields.
        assert supervised[key].rule is autonomous[key].rule


def test_a_mode_denied_edge_is_still_an_edge(gov):
    """§2 row 1: `AUTO` supervised, `DENY` autonomous — one row, two verdicts."""
    edge = (Axis.PROJECT, ORIGIN, P.DRAFT.value)
    assert edge in legal_edges()

    supervised = gov.evaluate(
        propose(Axis.PROJECT, P.DRAFT, ORIGIN),
        context(GovernanceMode.SUPERVISED, ORIGIN, facts=ALL_FACTS),
    )
    autonomous = gov.evaluate(
        propose(Axis.PROJECT, P.DRAFT, ORIGIN),
        context(GovernanceMode.AUTONOMOUS, ORIGIN, facts=ALL_FACTS),
    )

    assert supervised.outcome is PolicyOutcome.AUTO_ALLOW
    assert autonomous.outcome is PolicyOutcome.ESCALATE
    assert autonomous.reason is Reason.MODE_DENIED
    assert supervised.rule is autonomous.rule


def test_confirm_in_supervised_is_auto_in_autonomous(gov):
    """§3 row 5, `READY → CONTRACTED`: `CONFIRM` / `AUTO`."""
    supervised = gov.evaluate(
        propose(Axis.STAGE, S.CONTRACTED, S.READY),
        context(
            GovernanceMode.SUPERVISED, S.READY, facts=ALL_FACTS, decisions=UNDECIDED
        ),
    )
    autonomous = gov.evaluate(
        propose(Axis.STAGE, S.CONTRACTED, S.READY),
        context(
            GovernanceMode.AUTONOMOUS, S.READY, facts=ALL_FACTS, decisions=UNDECIDED
        ),
    )

    assert supervised.outcome is PolicyOutcome.REQUIRE_HUMAN
    # §1.1: `CONFIRM` is a `HumanDecision{kind: APPROVE}` under another name.
    assert supervised.required_decision is DecisionKind.APPROVE
    assert autonomous.outcome is PolicyOutcome.AUTO_ALLOW


def test_a_recorded_decision_discharges_a_confirm(gov):
    """The decision is what `CONFIRM` asks for, and having it is enough."""
    resolution = gov.evaluate(
        propose(Axis.STAGE, S.CONTRACTED, S.READY),
        context(
            GovernanceMode.SUPERVISED,
            S.READY,
            facts=ALL_FACTS,
            decisions=(DecisionKind.APPROVE,),
        ),
    )
    assert resolution.outcome is PolicyOutcome.AUTO_ALLOW
    assert resolution.reason is Reason.DECISION_DISCHARGED


def test_a_decision_of_the_wrong_kind_discharges_nothing(gov):
    """`DECIDE(ABANDON)` is not satisfied by an `APPROVE` lying around."""
    resolution = gov.evaluate(
        propose(Axis.STAGE, S.ABANDONED, S.READY),
        context(
            GovernanceMode.SUPERVISED,
            S.READY,
            facts=ALL_FACTS,
            decisions=(DecisionKind.APPROVE,),
        ),
    )
    assert resolution.outcome is PolicyOutcome.REQUIRE_HUMAN
    assert resolution.required_decision is DecisionKind.ABANDON


def test_notify_is_allowed_and_flagged(gov):
    """§1.1 `NOTIFY`: the runtime performs it and says so out of band."""
    resolution = gov.evaluate(
        propose(Axis.PROJECT, P.ACTIVE, P.SETTLING),
        context(GovernanceMode.SUPERVISED, P.SETTLING, facts=ALL_FACTS),
    )
    assert resolution.outcome is PolicyOutcome.AUTO_ALLOW
    assert resolution.notify is True


def test_project_creation_is_the_only_row_a_mode_denies():
    """authority-matrix §3: `AUTONOMOUS` never widens `HUMAN`-class capability.

    `project.create` is the one place the matrix spends a `DENY` verdict, and
    it spends it on the mode that would otherwise let a runtime originate the
    project that sets its own ceiling. Every other disagreement between the
    profiles is about *how* an edge is taken, not whether it can be.
    """
    denied = {
        (rule.row, mode)
        for rule in LEGAL_TRANSITIONS
        for mode in MODES
        if rule.policy(mode).settle(ALL_FACTS).verdict is PolicyVerdict.DENY
    }
    assert denied == {("2-1", GovernanceMode.AUTONOMOUS)}


@pytest.mark.parametrize("mode", MODES)
def test_no_illegal_row_shadows_a_legal_edge_unconditionally(gov, mode):
    """A §9 row that matched a legal edge with no trigger would delete it.

    The conditional rows (`any → SATISFIED` on a claimed status, `∅ → DRAFT`
    by a non-human creator) shadow legal edges deliberately, and only while
    their trigger holds. Every other §9 row must miss the graph entirely.
    """
    unconditional = [rule for rule in ILLEGAL_TRANSITIONS if not rule.when]
    for rule in unconditional:
        for axis, from_state, to_state in legal_edges():
            assert not rule.matches(axis, from_state, to_state, ()), (
                f"§{rule.row} shadows the legal edge "
                f"{axis.value} {from_state} → {to_state}"
            )
