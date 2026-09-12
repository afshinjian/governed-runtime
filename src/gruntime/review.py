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

from typing import Mapping, Sequence

from .models import Hash, Id, Review, ReviewAttestation, Verdict

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
    :data:`VERDICT_STRICTNESS`.
    """
    raise NotImplementedError


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
    raise NotImplementedError


def rvw(attestation: ReviewAttestation, verdict: Verdict) -> bool:
    """`RVW(v)` — evidence-model §4.

    True iff the attestation's *aggregate* verdict is `verdict`. A member
    review's verdict never satisfies this predicate; with `quorum > 1` the two
    are different questions.
    """
    raise NotImplementedError


def independence_satisfied(
    reviews: Sequence[Review], *, independence_required: bool
) -> bool:
    """Computed from provenance (`WP-12`, `RC-2`), never asserted."""
    raise NotImplementedError
