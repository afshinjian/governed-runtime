"""Policy resolution: what a proposal is allowed to become.

Design basis: transition-matrix.md §0.1 (the axis-3 gate), §1 (column semantics
and the `AUTO`/`NOTIFY`/`CONFIRM`/`DECIDE(K)`/`DENY` vocabulary), §9 (the
ILLEGAL SECTION), authority-matrix.md §3 (mode gate) and §6 (enforcement
points).

A `TransitionProposal` is what a worker may hand over: an axis, a subject, and
a target state. It carries **no** evidence and asserts **no** precondition — a
claim is not evidence (`G-6`), so the facts a resolution turns on are the ones
the controller observed, carried separately in a `TransitionContext`.

Resolution answers with one of four outcomes:

| outcome | meaning |
|---|---|
| `AUTO_ALLOW` | the controller may perform it now; audit only, `notify` when the row says `NOTIFY` |
| `REQUIRE_HUMAN` | legal, but a `HumanDecision{kind: K}` must be recorded first — `CONFIRM` is `DECIDE(APPROVE)` |
| `DENY` | refused, and re-proposable: the edge exists but this attempt does not satisfy it (capability absent, precondition unmet, evidence missing) |
| `ESCALATE` | refused, and never re-proposable as-is: the attempt is forbidden by construction, so it raises an `Escalation` instead of a retry (§9) |

The line between the last two is the line §9 draws: a §9 row, an edge that is
not in the graph at all, a mode verdict of `DENY`, or the axis-3 gate are
`ESCALATE`; a shortfall that fresh evidence would close is `DENY`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .models import (
    ActorKind,
    ActorRef,
    CapabilityId,
    DecisionKind,
    EscalationTrigger,
    GovernanceMode,
    Id,
    SuspensionState,
)
from .transitions import (
    Axis,
    Evidence,
    Operation,
    Policy,
    PolicyVerdict,
    Precondition,
    TransitionRule,
    normalize_state,
    gate_admits,
    gate_citation,
    illegal_operation_for,
    illegal_transition_for,
    rules_for,
)


class PolicyOutcome(str, Enum):
    """The four answers resolution gives. See the module docstring."""

    AUTO_ALLOW = "AUTO_ALLOW"
    REQUIRE_HUMAN = "REQUIRE_HUMAN"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


class Reason(str, Enum):
    """Why resolution answered as it did. One per step of §1's evaluation."""

    ALLOWED = "ALLOWED"
    DECISION_DISCHARGED = "DECISION_DISCHARGED"
    DECISION_REQUIRED = "DECISION_REQUIRED"
    CAPABILITY_MISSING = "CAPABILITY_MISSING"
    PRECONDITION_UNMET = "PRECONDITION_UNMET"
    EVIDENCE_MISSING = "EVIDENCE_MISSING"
    MODE_DENIED = "MODE_DENIED"
    SUSPENDED = "SUSPENDED"
    ILLEGAL = "ILLEGAL"
    NOT_IN_GRAPH = "NOT_IN_GRAPH"
    STATE_MISMATCH = "STATE_MISMATCH"


@dataclass(frozen=True)
class TransitionProposal:
    """A proposal to move one subject to one state.

    Workers propose; the controller decides. The proposer's `from_state` is its
    *belief* about where the subject is, and is checked against what the
    controller observed rather than trusted: a proposal built on a state the
    subject has already left is an integrity matter, not a stale retry.
    """

    axis: Axis
    subject_id: Id
    to_state: str
    proposed_by: ActorRef
    from_state: Optional[str] = None
    operation: Optional[Operation] = None
    rationale: str = ""


@dataclass(frozen=True)
class TransitionContext:
    """What the controller observed, and under whose authority.

    Every field is measured by the runtime. Nothing here may be filled in from
    a worker's report: `facts` are predicates the controller evaluated,
    `evidence` are receipt and snapshot classes it found present and current,
    and `decisions` are `HumanDecision` kinds whose `decision_state` is `VALID`
    at this moment (`HD-INV-4`).
    """

    governance_mode: GovernanceMode
    from_state: Optional[str] = None
    facts: frozenset[Precondition] = frozenset()
    evidence: frozenset[Evidence] = frozenset()
    capabilities: frozenset[CapabilityId] = frozenset()
    decisions: frozenset[DecisionKind] = frozenset()
    suspension: SuspensionState = SuspensionState.NONE
    required_decision_kinds: frozenset[DecisionKind] = frozenset()


@dataclass(frozen=True)
class TransitionResolution:
    """The answer, with everything needed to audit it."""

    outcome: PolicyOutcome
    reason: Reason
    detail: str = ""
    row: str = ""
    rule: Optional[TransitionRule] = None
    settled_policy: Optional[Policy] = None
    required_decision: Optional[DecisionKind] = None
    notify: bool = False
    escalation_trigger: Optional[EscalationTrigger] = None
    unmet_preconditions: tuple[Precondition, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    escalation_id: Optional[Id] = None

    @property
    def permitted(self) -> bool:
        """True only for `AUTO_ALLOW`: the one outcome that may be acted on."""
        return self.outcome is PolicyOutcome.AUTO_ALLOW

    def with_escalation(self, escalation_id: Id) -> "TransitionResolution":
        """The same resolution, carrying the escalation the controller raised."""
        return TransitionResolution(
            outcome=self.outcome,
            reason=self.reason,
            detail=self.detail,
            row=self.row,
            rule=self.rule,
            settled_policy=self.settled_policy,
            required_decision=self.required_decision,
            notify=self.notify,
            escalation_trigger=self.escalation_trigger,
            unmet_preconditions=self.unmet_preconditions,
            missing_evidence=self.missing_evidence,
            escalation_id=escalation_id,
        )


def unmet_preconditions(
    rule: TransitionRule, context: TransitionContext
) -> tuple[Precondition, ...]:
    """The rule's preconditions the context does not report as holding.

    Conjunctive: the matrix says ALL must hold (§1). A disjunction in the
    matrix is one `Precondition` named for the disjunction, never two members
    the evaluator would have to OR together.
    """
    return tuple(
        predicate
        for predicate in rule.preconditions
        if predicate not in context.facts
    )


def missing_evidence(
    rule: TransitionRule, context: TransitionContext
) -> tuple[str, ...]:
    """The rule's `required_evidence` entries the context cannot satisfy.

    An entry that is a set of tokens is satisfied by any one of them — the
    matrix's "a clean `SNAP`, or `DEC(ACCEPT_RISK)`".
    """
    missing: list[str] = []
    for requirement in rule.required_evidence:
        if isinstance(requirement, frozenset):
            if not (requirement & context.evidence):
                missing.append(
                    " or ".join(sorted(token.value for token in requirement))
                )
        elif requirement not in context.evidence:
            missing.append(requirement.value)
    return tuple(missing)


def capability_missing(rule: TransitionRule, context: TransitionContext) -> bool:
    """Whether the row's `required_capability` is absent from the holder's set.

    Step 7, on its own, because production consumes it on its own: the
    controller enforces the declared capability at the transition site without
    re-deciding preconditions or evidence, and must do so through this
    predicate rather than a second copy of it (`F03-001`).

    authority-matrix.md:292 — held at the moment of transition, or not at all.
    """
    return rule.required_capability not in context.capabilities


def select_rule(
    rules: tuple[TransitionRule, ...], context: TransitionContext
) -> TransitionRule:
    """Pick the row an edge with more than one is being taken under.

    §7.2 and §7.4 each carry a direct row and a `recovery.reconcile` row over
    the same two states. They are told apart by the capability actually held:
    recovery holds `recovery.reconcile` and nothing executable (`WP-16`), so
    the row whose `required_capability` the actor holds is the row being taken.
    Where that still leaves more than one — §5 and §7.2 each state a general
    row and a recovery row under the same capability — the observed
    preconditions choose, and the matrix's order breaks a remaining tie.
    """
    if len(rules) == 1:
        return rules[0]
    held = [
        rule for rule in rules if rule.required_capability in context.capabilities
    ]
    pool = held or list(rules)
    satisfied = [rule for rule in pool if not unmet_preconditions(rule, context)]
    return (satisfied or pool)[0]


def resolve(
    proposal: TransitionProposal, context: TransitionContext
) -> TransitionResolution:
    """Resolve one proposal against the graph and the mode's policy profile.

    The order is §0.4's "most restrictive axis wins", made concrete:

    | step | check | outcome when it fires |
    |---|---|---|
    | 1 | proposer's `from_state` disagrees with the observed one | `ESCALATE` / `STATE_MISMATCH` |
    | 2 | a §9.3 row forbids the operation to this actor kind | `ESCALATE` / `ILLEGAL` |
    | 3 | a §9.1 or §9.2 row forbids the edge | `ESCALATE` / `ILLEGAL` |
    | 4 | no legal row carries the edge | `ESCALATE` / `NOT_IN_GRAPH` |
    | 5 | the §0.1 axis-3 gate forbids it under the holder's suspension | `ESCALATE` / `SUSPENDED` |
    | 6 | the row's verdict in this mode is `DENY` | `ESCALATE` / `MODE_DENIED` |
    | 7 | the actor does not hold `required_capability` | `DENY` / `CAPABILITY_MISSING` |
    | 8 | a precondition does not hold | `DENY` / `PRECONDITION_UNMET` |
    | 9 | required evidence is absent | `DENY` / `EVIDENCE_MISSING` |
    | 10 | the verdict needs a `HumanDecision` that is not recorded | `REQUIRE_HUMAN` / `DECISION_REQUIRED` |
    | 11 | otherwise | `AUTO_ALLOW` |

    Steps 2–6 are `ESCALATE` because none of them is closable by bringing more
    evidence; steps 7–9 are `DENY` because all of them are.
    """
    observed_from = normalize_state(context.from_state)
    proposed_from = normalize_state(proposal.from_state)
    to_state = normalize_state(proposal.to_state)

    # 1. The proposer believed the subject was somewhere it is not.
    if proposed_from != observed_from:
        return TransitionResolution(
            outcome=PolicyOutcome.ESCALATE,
            reason=Reason.STATE_MISMATCH,
            detail=(
                f"proposed from {proposed_from!r}; the subject is "
                f"{observed_from!r}"
            ),
            escalation_trigger=EscalationTrigger.INTEGRITY_VIOLATION,
        )

    # 2. §9.3 — an operation forbidden to this actor kind.
    if proposal.operation is not None:
        forbidden = illegal_operation_for(
            proposal.operation, proposal.proposed_by.actor_kind
        )
        if forbidden is not None:
            return TransitionResolution(
                outcome=PolicyOutcome.ESCALATE,
                reason=Reason.ILLEGAL,
                detail=forbidden.illegal_because,
                row=forbidden.row,
                escalation_trigger=EscalationTrigger.INTEGRITY_VIOLATION,
            )

    # 3. §9.1 / §9.2 — a forbidden edge.
    illegal = illegal_transition_for(
        proposal.axis, observed_from, to_state, context.facts
    )
    if illegal is not None:
        return TransitionResolution(
            outcome=PolicyOutcome.ESCALATE,
            reason=Reason.ILLEGAL,
            detail=illegal.illegal_because,
            row=illegal.row,
            escalation_trigger=EscalationTrigger.INTEGRITY_VIOLATION,
        )

    # 4. The matrix carries no such edge. Not forbidden — simply not defined,
    #    and a transition the design never wrote down is not one to invent.
    rules = rules_for(proposal.axis, observed_from, to_state)
    if not rules:
        return TransitionResolution(
            outcome=PolicyOutcome.ESCALATE,
            reason=Reason.NOT_IN_GRAPH,
            detail=(
                f"no row of the transition matrix carries "
                f"{proposal.axis.value} {observed_from} → {to_state}"
            ),
            escalation_trigger=EscalationTrigger.INTEGRITY_VIOLATION,
        )

    # 5. §0.1 — the most restrictive axis wins (`O-4`).
    if not gate_admits(proposal.axis, to_state, context.suspension):
        row, because = gate_citation(proposal.axis, context.suspension)
        return TransitionResolution(
            outcome=PolicyOutcome.ESCALATE,
            reason=Reason.SUSPENDED,
            detail=f"{because} (holder is {context.suspension.value})",
            row=row,
            escalation_trigger=EscalationTrigger.POLICY_CONFLICT,
        )

    rule = select_rule(rules, context)
    verdict = rule.policy(context.governance_mode).settle(context.facts)

    # 6. §1.1 — `DENY` in this mode. The edge exists; this profile refuses it.
    if verdict.verdict is PolicyVerdict.DENY:
        return TransitionResolution(
            outcome=PolicyOutcome.ESCALATE,
            reason=Reason.MODE_DENIED,
            detail=(
                f"row {rule.row} is DENY under "
                f"{context.governance_mode.value}"
            ),
            row=rule.row,
            rule=rule,
            settled_policy=verdict,
            escalation_trigger=EscalationTrigger.POLICY_CONFLICT,
        )

    common = {
        "row": rule.row,
        "rule": rule,
        "settled_policy": verdict,
    }

    # 7. The capability, held at the moment of transition or not at all.
    if capability_missing(rule, context):
        return TransitionResolution(
            outcome=PolicyOutcome.DENY,
            reason=Reason.CAPABILITY_MISSING,
            detail=f"{rule.required_capability} is not held",
            **common,
        )

    # 8. The preconditions, all of them.
    unmet = unmet_preconditions(rule, context)
    if unmet:
        return TransitionResolution(
            outcome=PolicyOutcome.DENY,
            reason=Reason.PRECONDITION_UNMET,
            detail=", ".join(predicate.value for predicate in unmet),
            unmet_preconditions=unmet,
            **common,
        )

    # 9. The evidence, present and current.
    missing = missing_evidence(rule, context)
    if missing:
        return TransitionResolution(
            outcome=PolicyOutcome.DENY,
            reason=Reason.EVIDENCE_MISSING,
            detail=", ".join(missing),
            missing_evidence=missing,
            **common,
        )

    # 10. `CONFIRM` and `DECIDE(K)` — the decision comes first, or not at all.
    if verdict.verdict in (PolicyVerdict.CONFIRM, PolicyVerdict.DECIDE):
        needed = verdict.required_decision
        if needed is None:
            # §7.6: `DECIDE(K)` for `K ∈ escalation.required_decision_kinds`.
            available = context.required_decision_kinds & context.decisions
            if not available:
                return TransitionResolution(
                    outcome=PolicyOutcome.REQUIRE_HUMAN,
                    reason=Reason.DECISION_REQUIRED,
                    detail=(
                        "a HumanDecision of one of the escalation's "
                        "required_decision_kinds must be recorded first"
                    ),
                    **common,
                )
        elif needed not in context.decisions:
            return TransitionResolution(
                outcome=PolicyOutcome.REQUIRE_HUMAN,
                reason=Reason.DECISION_REQUIRED,
                detail=f"DECIDE({needed.value}) must be recorded first",
                required_decision=needed,
                **common,
            )
        return TransitionResolution(
            outcome=PolicyOutcome.AUTO_ALLOW,
            reason=Reason.DECISION_DISCHARGED,
            detail=f"discharged by a VALID HumanDecision under row {rule.row}",
            required_decision=needed,
            **common,
        )

    # 11. `AUTO`, or `NOTIFY` with its out-of-band notification.
    return TransitionResolution(
        outcome=PolicyOutcome.AUTO_ALLOW,
        reason=Reason.ALLOWED,
        detail=f"row {rule.row} is {verdict.verdict.value}",
        notify=verdict.verdict is PolicyVerdict.NOTIFY,
        **common,
    )
