"""Review aggregation and attestation minting.

Design basis: domain-model §7.3, §7.3.1 (`RA-INV-1..4`), evidence-model §4
(`R` is the attestation set), `G-1`.

A reviewer's judgement is CLAIM class. A `ReviewAttestation` is the kernel's
measurement *of* that judgement: it attests that reviews meeting a named
spec's quorum and independence exist, were computed over a stated snapshot,
and carry a stated aggregate verdict. `RVW(v)` matches that aggregate, never a
member review's own verdict.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Mapping, Sequence

from .canonical import canonical_json, digest_bytes
from .errors import IntegrityViolation
from .models import (
    ActorKind,
    ActorRef,
    AuthMethod,
    Hash,
    Id,
    Independence,
    Review,
    ReviewAttestation,
    Verdict,
)

#: Minting capability (`RA-INV-1`). KERNEL class: a worker-authored or
#: human-authored attestation is an integrity violation, not a review result.
ATTEST_CAPABILITY = "review.attest"

#: Marking a review as satisfying an `INDEPENDENT` spec.
ATTEST_INDEPENDENT_CAPABILITY = "review.attest.independent"

#: Strictest-first ordering used by :func:`aggregate_verdict`. The aggregate is
#: the strictest verdict among the counted reviews, so one `FAIL` decides the
#: set and `INCONCLUSIVE` never outranks a `FAIL`.
VERDICT_STRICTNESS: tuple[Verdict, ...] = (
    Verdict.FAIL,
    Verdict.INCONCLUSIVE,
    Verdict.PASS_WITH_FINDINGS,
    Verdict.PASS,
    Verdict.ABSTAIN,
)


def aggregate_verdict(verdicts: Sequence[Verdict], *, quorum: int) -> Verdict:
    """Aggregate `verdicts` into the spec's single verdict.

    The result is the strictest verdict counted toward `quorum`, per
    :data:`VERDICT_STRICTNESS`. An `ABSTAIN` is not a judgement and does not
    count; if too few reviews remain to reach `quorum` the spec produced no
    usable answer, which is `INCONCLUSIVE` rather than a pass.
    """
    counted = [verdict for verdict in verdicts if verdict is not Verdict.ABSTAIN]
    if len(counted) < quorum:
        return Verdict.INCONCLUSIVE
    return min(counted, key=VERDICT_STRICTNESS.index)


def mint_attestation(
    *,
    reviews: Sequence[Review],
    review_spec_id: str,
    quorum: int,
    independence_required: bool,
    input_snapshot_id: Id,
    contract_hash: Hash,
    run_id: Id,
    stage_id: Id,
    attested_by: Mapping[str, str],
    capabilities: frozenset[str] = frozenset(),
) -> ReviewAttestation:
    """Mint a `ReviewAttestation` over `reviews`.

    Raises `IntegrityViolation` when `review.attest` is absent from
    `capabilities` (`RA-INV-1`), and when the spec cannot be satisfied —
    quorum unmet, or a `SELF_REVIEW` counted toward an independent spec
    (`RV-INV-1`, `RA-INV-2`). A spec that cannot be satisfied produces no
    attestation at all; the stage takes `AWAITING_REVIEW → AWAITING_DECISION`
    instead of receiving a weaker one.
    """
    if ATTEST_CAPABILITY not in capabilities:
        raise IntegrityViolation(
            f"minting an attestation requires {ATTEST_CAPABILITY!r}, a KERNEL "
            "capability; an attestation minted by anyone else is an integrity "
            "violation, not a review result (RA-INV-1)"
        )
    if not reviews:
        raise IntegrityViolation(f"no reviews offered for spec {review_spec_id!r}")
    for review in reviews:
        if review.review_spec_id != review_spec_id:
            raise IntegrityViolation(
                f"review {review.review_id} belongs to spec "
                f"{review.review_spec_id!r}, not {review_spec_id!r}"
            )
        if review.input_snapshot_id != input_snapshot_id:
            raise IntegrityViolation(
                f"review {review.review_id} was computed over a different snapshot"
            )

    counted = [r for r in reviews if r.verdict is not Verdict.ABSTAIN]
    quorum_met = len(counted) >= quorum
    if not quorum_met:
        raise IntegrityViolation(
            f"spec {review_spec_id!r} requires {quorum} counted reviews, "
            f"{len(counted)} present"
        )
    if not independence_satisfied(reviews, independence_required=independence_required):
        raise IntegrityViolation(
            f"spec {review_spec_id!r} requires independent review; a SELF_REVIEW "
            "cannot be counted toward it (RV-INV-1, RA-INV-2)"
        )

    attested_at = datetime.now(timezone.utc)
    review_ids = frozenset(review.review_id for review in reviews)
    verdict = aggregate_verdict([r.verdict for r in reviews], quorum=quorum)
    actor = ActorRef(
        actor_kind=ActorKind(attested_by["actor_kind"]),
        actor_id=attested_by["actor_id"],
        auth_method=AuthMethod(attested_by["auth_method"]),
    )
    preimage = {
        "review_spec_id": review_spec_id,
        "review_ids": sorted(review_ids),
        "verdict": verdict.value,
        "quorum": quorum,
        "independence_required": independence_required,
        "input_snapshot_id": input_snapshot_id,
        "contract_hash": contract_hash,
        "run_id": run_id,
        "stage_id": stage_id,
        "attested_at": attested_at.isoformat(),
    }
    return ReviewAttestation(
        attestation_id=f"ra-{uuid.uuid4().hex}",
        run_id=run_id,
        stage_id=stage_id,
        review_spec_id=review_spec_id,
        review_ids=review_ids,
        verdict=verdict,
        quorum_met=quorum_met,
        independence_satisfied=True,
        input_snapshot_id=input_snapshot_id,
        contract_hash=contract_hash,
        attested_by=actor,
        attested_at=attested_at,
        attestation_hash=digest_bytes(canonical_json(preimage)),
        prev_event_hash="",
        criteria_addressed=frozenset(),
        blocking_findings=frozenset(),
    )


def rvw(attestation: ReviewAttestation, verdict: Verdict) -> bool:
    """`RVW(v)` — evidence-model §4.

    True iff the attestation's *aggregate* verdict is `verdict`. A member
    review's verdict never satisfies this predicate; with `quorum > 1` the two
    are different questions.
    """
    return attestation.verdict is verdict


def independence_satisfied(
    reviews: Sequence[Review], *, independence_required: bool
) -> bool:
    """Computed from provenance (`WP-12`, `RC-2`), never asserted.

    A spec that does not require independence is satisfied by anything; one
    that does accepts only INDEPENDENT provenance, never shared context.
    """
    if not independence_required:
        return True
    return all(
        review.independence is Independence.INDEPENDENT for review in reviews
    )  # guard:gr07_independence_attestation
