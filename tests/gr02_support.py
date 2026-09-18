"""Scaffolding for the GR-02 transition-engine tests.

Fake workers only. Nothing here reaches a provider, a repository, or a
sandbox: the engine under test *decides*, and deciding initiates no effect.
The controller is constructed without a repository for exactly that reason.

Two conventions the illegal-row tests depend on:

* **Saturated context.** Unless a test says otherwise, the context carries
  every capability the graph names, every evidence class, and a valid
  `HumanDecision` of every kind. A refusal under saturation is structural: it
  is not an artifact of missing evidence, and no capability or decision would
  have changed it. That is what §9 means by "never a retry".
* **Both modes.** An illegal row reads `DENY` in both policy columns, so every
  illegal-row test asserts the refusal under `SUPERVISED` and `AUTONOMOUS`.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, Optional

import pytest

from gruntime.models import (
    ActorKind,
    ActorRef,
    AuthMethod,
    DecisionKind,
    GovernanceMode,
    Id,
    SuspensionState,
)
from gruntime.policy import (
    PolicyOutcome,
    Reason,
    TransitionContext,
    TransitionProposal,
    TransitionResolution,
)
from gruntime.transitions import (
    ILLEGAL_TRANSITIONS,
    LEGAL_TRANSITIONS,
    NONE_GRANTABLE,
    Axis,
    Evidence,
    Operation,
    Precondition,
)

from genesis_support import AUTONOMOUS, OWNER, create_project

SUBJECT = "subj-gr02"

#: Every capability the legal graph names. `NONE_GRANTABLE` is never held: it
#: is the matrix's way of writing "no capability authorizes this".
GRAPH_CAPABILITIES = frozenset(
    rule.required_capability for rule in LEGAL_TRANSITIONS
) - {NONE_GRANTABLE}

ALL_EVIDENCE = frozenset(Evidence)
ALL_DECISIONS = frozenset(DecisionKind)

#: Predicates that *cause* a §9 row to match. Saturating facts with these would
#: make every conditionally-illegal row fire, so the legal-graph sweeps exclude
#: them and the rows that need them pass them explicitly.
ILLEGALITY_TRIGGERS = frozenset(
    predicate for rule in ILLEGAL_TRANSITIONS for predicate in rule.when
)

ALL_FACTS = frozenset(Precondition) - ILLEGALITY_TRIGGERS


def actor(kind: ActorKind = ActorKind.RUNTIME) -> ActorRef:
    """A proposer of the given kind. §9.3 rows turn on `actor_kind` alone."""
    return ActorRef(
        actor_kind=kind,
        actor_id=f"gr02.{kind.value.lower()}",
        auth_method=(
            AuthMethod.NONE if kind is ActorKind.RUNTIME else AuthMethod.SESSION
        ),
    )


def propose(
    axis: Axis,
    to_state: str,
    from_state: Optional[str] = None,
    *,
    actor_kind: ActorKind = ActorKind.RUNTIME,
    operation: Optional[Operation] = None,
    subject_id: Id = SUBJECT,
) -> TransitionProposal:
    return TransitionProposal(
        axis=axis,
        subject_id=subject_id,
        to_state=to_state,
        from_state=from_state,
        proposed_by=actor(actor_kind),
        operation=operation,
    )


def context(
    mode: GovernanceMode,
    from_state: Optional[str] = None,
    *,
    facts: Iterable[Precondition] = (),
    evidence: Optional[Iterable[Evidence]] = None,
    capabilities: Optional[Iterable[str]] = None,
    decisions: Optional[Iterable[DecisionKind]] = None,
    suspension: SuspensionState = SuspensionState.NONE,
    required_decision_kinds: Iterable[DecisionKind] = (),
) -> TransitionContext:
    """A context that is saturated except where the caller narrows it."""
    return TransitionContext(
        governance_mode=mode,
        from_state=from_state,
        facts=frozenset(facts),
        evidence=ALL_EVIDENCE if evidence is None else frozenset(evidence),
        capabilities=(
            GRAPH_CAPABILITIES if capabilities is None else frozenset(capabilities)
        ),
        decisions=ALL_DECISIONS if decisions is None else frozenset(decisions),
        suspension=suspension,
        required_decision_kinds=frozenset(required_decision_kinds),
    )


@dataclass
class Governor:
    """A controller over one project, for proposals the tests hand it."""

    controller: object
    project_id: Id

    def evaluate(self, proposal, ctx) -> TransitionResolution:
        return self.controller.evaluate_transition(self.project_id, proposal, ctx)

    def escalations(self):
        return self.controller.store.list_escalations(self.project_id)

    def events(self):
        return self.controller.store.list_events(self.project_id)


@contextmanager
def governed(h):
    with h.controller() as controller:
        project_id = create_project(controller, then_mode=AUTONOMOUS,
            name="GR-02", slug="gr-02", workspace_root=str(h.root),
            approved_by=OWNER,
        )
        yield Governor(controller=controller, project_id=project_id)


@pytest.fixture
def gov(h):
    """A controller with a project, and no repository: GR-02 decides only."""
    with governed(h) as governor:
        yield governor


def refuse_in_both_modes(
    gov: Governor,
    proposal: TransitionProposal,
    *,
    row: str,
    reason: Reason = Reason.ILLEGAL,
    facts: Iterable[Precondition] = (),
    suspension: SuspensionState = SuspensionState.NONE,
) -> TransitionResolution:
    """Assert the controller refuses a proposal under both policy profiles.

    Everything is saturated but the facts the row itself needs, so the refusal
    cannot be explained by anything the proposer could go and fetch.
    """
    last = None
    for mode in (GovernanceMode.SUPERVISED, GovernanceMode.AUTONOMOUS):
        resolution = gov.evaluate(
            proposal,
            context(
                mode,
                proposal.from_state,
                facts=facts,
                suspension=suspension,
            ),
        )
        assert resolution.outcome is PolicyOutcome.ESCALATE, (
            f"{mode.value}: expected ESCALATE, got {resolution.outcome.value} "
            f"({resolution.reason.value}: {resolution.detail})"
        )
        assert resolution.reason is reason, (
            f"{mode.value}: expected {reason.value}, got {resolution.reason.value}"
        )
        assert resolution.row == row, (
            f"{mode.value}: expected row {row}, got {resolution.row!r}"
        )
        # §9's `illegal_because` column travels with the refusal.
        assert resolution.detail
        # "Attempting any of them is an escalation, never a retry" (§9).
        assert resolution.escalation_id is not None
        last = resolution
    assert last is not None
    return last


def refuse_operation(
    gov: Governor,
    operation: Operation,
    actor_kind: ActorKind,
    *,
    row: str,
) -> TransitionResolution:
    """The §9.3 form: an operation, an actor kind, and no legal counterpart."""
    return refuse_in_both_modes(
        gov,
        propose(
            Axis.OPERATION,
            operation.value,
            actor_kind=actor_kind,
            operation=operation,
        ),
        row=row,
    )
