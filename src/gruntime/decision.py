"""The one `HumanDecision.decision_state` derivation.

Design basis: transition-matrix §7.5, domain-model §9.A (`HD-INV-1`..`HD-INV-4`),
evidence-model §5.2.

Only `VALID` is authority. The rule this module exists for is `HD-INV-4`: an
approval is bound to the `RealitySnapshot` whose evidence the human was shown,
and when a newer snapshot supersedes it inside the subject's scope the approval
goes `STALE` — whatever its `expires_at` says, and whether or not it was ever
used. The human approved artifacts that no longer describe the workspace.

`STALE` is terminal. A stale decision is never revived by later validations
over the new reality: the subject is re-decided, producing a new decision with
a new nonce (§7.5, evidence-model §5.2 "renewal").

The mirror-image rule matters just as much and is why the fingerprint in
`repository.py` excludes untracked files: re-observing an *unchanged*
repository produces an equal `snapshot_hash` and supersedes nothing, so
approvals survive tool runs, builds and editor scratch files. If looking
invalidated approvals, nothing could ever be approved.
"""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Optional, Sequence

from .errors import IntegrityViolation
from .models import (
    DecisionKind,
    DecisionState,
    DecisionSubjectKind,
    Glob,
    Hash,
    HumanDecision,
    PathStr,
)
from .repository import WHOLE_WORKSPACE, changed_paths, matches_any

#: `snapshot_bound` subject kinds (domain-model §9.A): a decision about any of
#: these speaks about the state of the workspace.
SNAPSHOT_BOUND_SUBJECTS: frozenset[DecisionSubjectKind] = frozenset(
    {
        DecisionSubjectKind.STAGE,
        DecisionSubjectKind.RUN,
        DecisionSubjectKind.COMMIT_INTENT,
        DecisionSubjectKind.FINDING,
    }
)

#: `snapshot_bound` decision kinds. `SET_MODE`, `SUSPEND`, `RESUME`, `ABANDON`,
#: `EXTEND_BUDGET`, `GRANT_CAPABILITY` and `REVOKE_CAPABILITY` over a `PROJECT`
#: or `CAPABILITY` subject are governance acts, not statements about the tree.
SNAPSHOT_BOUND_KINDS: frozenset[DecisionKind] = frozenset(
    {
        DecisionKind.APPROVE,
        DecisionKind.WAIVE,
        DecisionKind.ACCEPT_RISK,
        DecisionKind.OVERRIDE,
        DecisionKind.REJECT,
    }
)

#: States a decision never leaves. `CONSUMED`, `EXPIRED`, `VOID` and `STALE`
#: are all terminal (§7.5); each is retained as a true record of an earlier
#: choice and discharges nothing.
TERMINAL_STATES: frozenset[DecisionState] = frozenset(
    {
        DecisionState.CONSUMED,
        DecisionState.EXPIRED,
        DecisionState.STALE,
        DecisionState.VOID,
    }
)


def is_snapshot_bound(
    subject_kind: DecisionSubjectKind, decision_kind: DecisionKind
) -> bool:
    """`HumanDecision.snapshot_bound`, derived per domain-model §9.A.

    Either the subject is a thing in the workspace, or the act is a judgement
    about what is in the workspace. Both make the decision a statement about a
    reality that can change underneath it.
    """
    return (
        subject_kind in SNAPSHOT_BOUND_SUBJECTS
        or decision_kind in SNAPSHOT_BOUND_KINDS
    )


def subject_scope(decision: HumanDecision) -> tuple[Glob, ...]:
    """The paths a decision's subject covers.

    A decision over a `STAGE`, `RUN` or `COMMIT_INTENT` is scoped by the
    contract those were activated under; until contracts are materialized every
    subject is the whole workspace, which is the conservative direction — a
    wider scope stales *more* decisions, never fewer, and `HD-INV-4` is a
    safety rule.
    """
    return WHOLE_WORKSPACE


def drift_touches_scope(
    before: Mapping[PathStr, Hash],
    after: Mapping[PathStr, Hash],
    scope: Sequence[Glob],
) -> bool:
    """True iff anything inside `scope` differs between two effective indexes."""
    added, removed, modified = changed_paths(before, after)
    return any(
        matches_any(path, scope) for path in (added | removed | modified)
    )


def derive_decision_state(
    decision: HumanDecision,
    *,
    now: datetime,
    superseded_by_drift: bool = False,
    consumed: bool = False,
    integrity_violated: bool = False,
) -> DecisionState:
    """Derive `decision_state` — transition-matrix §7.5.

    This is the **single** derivation; no other module decides whether a
    decision is authority. The rows, in precedence order:

    1. Already terminal (`CONSUMED`, `EXPIRED`, `STALE`, `VOID`) — unchanged.
       A decision never re-enters `VALID`; renewal is a new decision (§7.5).
    2. `integrity_violated` — `VOID` (row 5). `HD-INV-1` outranks every other
       consideration: a forged or unverifiable record was never authority.
    3. `consumed` — `CONSUMED` (row 2); the nonce is spent (`HD-INV-3`).
    4. `now > expires_at`, or the `scope` boundary was left — `EXPIRED` (row 4).
       Checked before staleness because it needs no snapshot: a decision whose
       time ran out is expired even if the workspace never moved.
    5. not snapshot-bound — `VALID`. A governance act does not speak about the
       workspace, so no amount of workspace change can supersede it. This is
       the single place that distinction is applied; a caller never has to
       decide whether to pass `superseded_by_drift`.
    6. `superseded_by_drift` — `STALE` (row 3): a newer `COMPLETE` snapshot
       with drift inside the subject's scope superseded `subject_snapshot_id`
       (`HD-INV-4`).
    7. Otherwise `VALID`.
    """
    if decision.decision_state in TERMINAL_STATES:
        return decision.decision_state
    if integrity_violated:
        return DecisionState.VOID
    if consumed:
        return DecisionState.CONSUMED
    if decision.expires_at is not None and now > decision.expires_at:
        return DecisionState.EXPIRED
    if not decision.snapshot_bound:
        return DecisionState.VALID
    if superseded_by_drift:
        return DecisionState.STALE
    return DecisionState.VALID


def is_authority(decision: HumanDecision) -> bool:
    """True iff `decision` discharges a `CONFIRM` or `DECIDE(K)` right now.

    Only `VALID` (transition-matrix §9.3, last row; `HD-INV-4`). Kept as a
    predicate so no call site re-states the enum comparison and quietly admits
    a second state later.
    """
    return decision.decision_state is DecisionState.VALID


def refuse_unless_authority(decision: Optional[HumanDecision], what: str) -> HumanDecision:
    """Return `decision` if it is authority, else raise.

    Raises `IntegrityViolation` rather than returning `False`: citing a
    consumed, expired, void or stale approval is an illegal operation
    (transition-matrix §9.3), not an unmet precondition.
    """
    if decision is None:
        raise IntegrityViolation(f"{what} requires a HumanDecision; none was cited")
    if not is_authority(decision):
        raise IntegrityViolation(
            f"{what} cited decision {decision.decision_id} in state "
            f"{decision.decision_state.value}; only VALID is authority (HD-INV-4)"
        )
    return decision
