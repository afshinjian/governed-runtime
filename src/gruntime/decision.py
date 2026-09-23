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
from dataclasses import asdict
from typing import Mapping, Optional, Sequence

from .contracts import require
from .errors import CapabilityDenied, IntegrityViolation
from .canonical import digest_json
from .models import (
    ActorKind,
    ActorRef,
    AuthMethod,
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


def require_principal_key(decided_by: ActorRef, where: str) -> None:
    """`decided_by.actor_kind = HUMAN` ⇒ `principal_key_id` — domain-model:58.

    The third half of `HD-INV-1`, and the one the runtime did not enforce
    (`F04-001`). The actor kind and the `auth_method` say that *a* human
    authenticated; only the key says **which** one, and a decision that names
    no principal can be attributed to nobody the moment it is read back.

    Stated as the implication rather than as an unconditional test, because
    that is what [domain-model.md:58](../../design/domain-model.md#L58) says:
    a non-`HUMAN` actor is out of its scope and is refused, where it must be,
    by the actor-kind rule instead.

    One predicate behind three call sites — the recording boundary and both
    persistence boundaries — so a record that reaches the store another way,
    and a record already on disk from before the rule existed, are refused by
    the same rule rather than by three restatements of it that can drift
    apart. Refusal is all of it: nothing here repairs, coerces or backfills a
    missing key, because the runtime holds nothing it could put there and a
    plausible substitute would fabricate the very attribution the record is
    missing.
    """
    require(decided_by.actor_kind is not ActorKind.HUMAN or bool(decided_by.principal_key_id), f"a HumanDecision decided by a HUMAN must name the principal key it was made with: {where} has actor_id={decided_by.actor_id!r} with principal_key_id={decided_by.principal_key_id!r} (domain-model.md:58, HD-INV-1)", IntegrityViolation)  # guard:decision_principal_key_iff


#: Where each `CONFIRM` cell this module enforces is written down. The row is
#: cited by the refusal so a denial names the frozen line it comes from rather
#: than the code that raised it.
CONFIRM_ROWS: dict[str, str] = {
    "5-1": "transition-matrix.md:189",
    "7.2-1": "transition-matrix.md:305",
    "7.4-4": "transition-matrix.md:349",
}


def confirmation_admits(
    decision: Optional[HumanDecision],
    *,
    project_id: str,
    subject_kind: DecisionSubjectKind,
    subject_id: str,
    now: datetime,
) -> bool:
    """Whether `decision` is the human act a `CONFIRM` cell declares.

    `CONFIRM` in the transition matrix's policy vocabulary (§1.1) is "a human
    confirms this transition before it happens", and the record of that is an
    `APPROVE` over the subject the transition is about. Every conjunct below
    is one of the things that makes such a record authority rather than a row
    in a table:

    * it is an `APPROVE`, over **this** project and **this** subject — an
      approval of something else discharges nothing here;
    * the decider is an authenticated, named human (`HD-INV-1`,
      domain-model.md:58), with the signature itself where they authenticate
      by `SIGNATURE` (domain-model.md:710);
    * they were shown something (`HD-INV-2`) and the nonce is a real one
      (`HD-INV-3`);
    * `decision_hash` still recomputes, so the authority-bearing fields were
      not edited between recording and presenting;
    * and the single derivation says `VALID` — the only state that is
      authority (`HD-INV-4`).

    Written as the same shape as `authority.human_covers`, which asks the
    sibling question for a `GRANT_CAPABILITY` basis, so the two read alike and
    neither can quietly admit what the other refuses. A predicate rather than
    a raiser, so `require_confirmation` has exactly one deletable line.

    Staleness is not passed in. `take_snapshot` persists `STALE` onto every
    superseded decision as it publishes the observation
    (`_stale_decisions_against`), and `derive_decision_state` treats it as
    terminal, so a confirmation overtaken by a newer reality is already
    `STALE` on the row by the time it is read back.
    """
    if decision is None:
        return False
    actor = decision.decided_by
    authenticated = (
        actor.actor_kind is ActorKind.HUMAN
        and bool(actor.principal_key_id)
        and actor.auth_method in (AuthMethod.SESSION, AuthMethod.SIGNATURE, AuthMethod.MTLS)
        and decision.auth_method == actor.auth_method
        and (actor.auth_method is not AuthMethod.SIGNATURE or bool(decision.signature))
    )
    return (
        authenticated
        and decision.project_id == project_id
        and decision.decision_kind is DecisionKind.APPROVE
        and decision.subject_kind is subject_kind
        and decision.subject_id == subject_id
        and bool(decision.evidence_shown)
        and 16 <= len(decision.nonce) <= 64
        and decision.decided_at <= now
        and decision.decision_hash == decision_content_hash(decision)
        and derive_decision_state(decision, now=now) is DecisionState.VALID
    )


def require_confirmation(
    decision: Optional[HumanDecision],
    *,
    project_id: str,
    subject_kind: DecisionSubjectKind,
    subject_id: str,
    row: str,
    now: datetime,
) -> HumanDecision:
    """Refuse unless `decision` is the `CONFIRM` that row declares.

    One predicate behind every `CONFIRM` cell the runtime enforces, for the
    reason `require_principal_key` is one predicate behind three call sites:
    three restatements of the same rule drift apart, and the row that drifts
    is the one nobody tested. The call sites differ only in the subject the
    approval must be over and the row they cite.

    The caller decides *whether* the cell applies — `CONFIRM` is the
    `SUPERVISED` column, and every row here reads `AUTO` under `AUTONOMOUS`,
    so asking this of an autonomous project would enforce a cell the frozen
    matrix does not declare. What this decides is whether the act presented is
    the human act, and it never looks one up: the caller hands over what it
    was given, and a caller that was given nothing hands over `None`.

    Raises `CapabilityDenied`: a transition whose policy verdict is `CONFIRM`
    and which has no confirmation is an operation its caller has no authority
    for, not an unmet precondition.
    """
    require(confirmation_admits(decision, project_id=project_id, subject_kind=subject_kind, subject_id=subject_id, now=now), f"row {row} is CONFIRM under SUPERVISED ({CONFIRM_ROWS.get(row, 'transition-matrix.md')}): it needs a live APPROVE by an authenticated, named human over {subject_kind.value} {subject_id}, and {'none was cited' if decision is None else repr(decision.decision_id) + ' is not one'}", CapabilityDenied)  # guard:gr31_confirmation_admits
    return decision


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


def decision_content_hash(decision: HumanDecision) -> str:
    """Pin immutable authority-bearing fields; lifecycle state stays outside.

    Evidence is identified by content digest, as in the persisted decision.
    This prevents editing a grant's actor, nonce, scope or capabilities before
    presenting its ID to activation.
    """
    body = asdict(decision)
    body.pop("decision_hash")
    body.pop("decision_state")
    body["evidence_shown"] = [ref.digest for ref in decision.evidence_shown]
    body["grants"] = sorted(decision.grants)
    body["revokes"] = sorted(decision.revokes)
    body["options_offered"] = list(decision.options_offered)
    body["decided_at"] = decision.decided_at.isoformat()
    body["expires_at"] = decision.expires_at.isoformat() if decision.expires_at else None
    return digest_json(body)


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
