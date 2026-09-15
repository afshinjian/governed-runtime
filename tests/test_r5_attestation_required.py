"""R-5 — no code path accepts a `Review` where a `ReviewAttestation` is required.

Acceptance criterion (MICRO-VERIFY-01, OWNER DISPOSITION).

Design basis: G-1, RA-INV-1..4, domain-model §7.3.1, `CommitIntent.preconditions`
(`reviews: Set<Ref<ReviewAttestation>>`), evidence-model §4 (`R` is the
attestation set; the evaluator never reads `Review` records directly).

This file also closes the F01-007 residue: `RVW(v)` matches the attestation's
*aggregate* verdict, not a member review's verdict.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from genesis_support import OWNER
from gruntime.errors import IntegrityViolation
from gruntime.models import (
    CommitPreconditions,
    Independence,
    Ref,
    ReviewerKind,
    Verdict,
)
from gruntime.review import aggregate_verdict, mint_attestation, rvw

SRC = Path(__file__).resolve().parents[1] / "src" / "gruntime"


def _project(h, with_repo=True):
    if with_repo:
        h.init_repo()
    with h.controller(with_repo=with_repo) as c:
        project_id = c.create_project(
            name="R5", slug="r5", workspace_root=str(h.repo_dir),
            approved_by=OWNER,
        )
        c.start(project_id)
        run_id = c.open_run(project_id)
        snapshot_id = c.take_snapshot(project_id)
    return project_id, run_id, snapshot_id


def _review(c, run_id, snapshot_id, verdict, *, independence=Independence.INDEPENDENT):
    return c.record_review(
        run_id,
        review_spec_id="rs-1",
        verdict=verdict,
        reviewer_kind=ReviewerKind.PEER_WORKER,
        independence=independence,
        input_snapshot_id=snapshot_id,
    )


def test_preconditions_reject_a_review_reference(h):
    project_id, run_id, snapshot_id = _project(h)
    with h.controller(with_repo=True) as c:
        review = _review(c, run_id, snapshot_id, Verdict.PASS)

        with pytest.raises(IntegrityViolation):
            CommitPreconditions(reviews=(Ref("Review", review.review_id),))

        # A bare id string is not a typed reference either.
        with pytest.raises(IntegrityViolation):
            CommitPreconditions(reviews=(review.review_id,))


def test_preconditions_accept_an_attestation_reference(h):
    project_id, run_id, snapshot_id = _project(h)
    with h.controller(with_repo=True) as c:
        reviews = [_review(c, run_id, snapshot_id, Verdict.PASS) for _ in range(2)]
        attestation = c.attest_reviews(run_id, "rs-1", reviews, quorum=2)

        preconditions = CommitPreconditions(
            reviews=(Ref("ReviewAttestation", attestation.attestation_id),)
        )
        intent = c.propose_commit(
            run_id,
            path="x.txt",
            content="x\n",
            message="x",
            preconditions=preconditions,
        )
        c.authorize_commit(intent.intent_id)
        assert c.store.get_commit_intent(intent.intent_id).preconditions_met is True


def test_authorization_refuses_a_review_backed_precondition(h):
    project_id, run_id, snapshot_id = _project(h)
    with h.controller(with_repo=True) as c:
        review = _review(c, run_id, snapshot_id, Verdict.PASS)
        intent = c.propose_commit(run_id, path="y.txt", content="y\n", message="y")

        # Bypass the constructor the way a careless caller would, and check the
        # consuming path refuses it rather than trusting the stored value.
        c.store.force_precondition_reviews(intent.intent_id, [review.review_id])
        with pytest.raises(IntegrityViolation):
            c.authorize_commit(intent.intent_id)


def test_evidence_resolution_rejects_a_review_record(h):
    project_id, run_id, snapshot_id = _project(h)
    with h.controller(with_repo=True) as c:
        review = _review(c, run_id, snapshot_id, Verdict.PASS)
        with pytest.raises(IntegrityViolation):
            c.store.resolve_review_evidence(Ref("Review", review.review_id))
        with pytest.raises(IntegrityViolation):
            c.store.resolve_review_evidence(Ref("ReviewAttestation", review.review_id))


def test_rvw_matches_the_aggregate_verdict_not_a_member(h):
    """F01-007 residue: quorum > 1 makes the two predicates different."""
    project_id, run_id, snapshot_id = _project(h)
    with h.controller(with_repo=True) as c:
        passing = _review(c, run_id, snapshot_id, Verdict.PASS)
        failing = _review(c, run_id, snapshot_id, Verdict.FAIL)
        attestation = c.attest_reviews(run_id, "rs-1", [passing, failing], quorum=2)

        assert attestation.verdict is Verdict.FAIL
        assert rvw(attestation, Verdict.FAIL) is True
        assert rvw(attestation, Verdict.PASS) is False, (
            "a member review's verdict satisfied RVW(PASS)"
        )


@pytest.mark.parametrize(
    ("verdicts", "expected"),
    [
        ([Verdict.PASS, Verdict.PASS], Verdict.PASS),
        ([Verdict.PASS, Verdict.PASS_WITH_FINDINGS], Verdict.PASS_WITH_FINDINGS),
        ([Verdict.PASS, Verdict.FAIL], Verdict.FAIL),
        ([Verdict.PASS, Verdict.INCONCLUSIVE], Verdict.INCONCLUSIVE),
        ([Verdict.FAIL, Verdict.INCONCLUSIVE], Verdict.FAIL),
    ],
    ids=lambda v: str(v),
)
def test_aggregate_verdict_is_the_strictest_counted_verdict(verdicts, expected):
    assert aggregate_verdict(verdicts, quorum=2) is expected


def test_self_review_cannot_be_attested_for_an_independent_spec(h):
    """RV-INV-1 / RA-INV-2: no attestation at all, rather than a weak one."""
    project_id, run_id, snapshot_id = _project(h)
    with h.controller(with_repo=True) as c:
        reviews = [
            _review(c, run_id, snapshot_id, Verdict.PASS),
            _review(
                c, run_id, snapshot_id, Verdict.PASS,
                independence=Independence.SELF_REVIEW,
            ),
        ]
        with pytest.raises(IntegrityViolation):
            c.attest_reviews(run_id, "rs-1", reviews, quorum=2)


def test_mint_attestation_requires_the_kernel_capability(h):
    project_id, run_id, snapshot_id = _project(h)
    with h.controller(with_repo=True) as c:
        reviews = [_review(c, run_id, snapshot_id, Verdict.PASS) for _ in range(2)]
        with pytest.raises(IntegrityViolation):
            mint_attestation(
                reviews=reviews,
                review_spec_id="rs-1",
                quorum=2,
                independence_required=True,
                input_snapshot_id=snapshot_id,
                contract_hash="sha256:" + "11" * 32,
                run_id=run_id,
                stage_id="stage",
                attested_by={"actor_kind": "WORKER", "actor_id": "w-1",
                             "auth_method": "NONE"},
            )


def test_no_evidence_consumer_names_the_review_type():
    """`Review` may be recorded and attested; it may never be consumed."""
    consumers = {"controller.py", "recovery.py", "reconciliation.py", "commit.py"}
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        if path.name not in consumers:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "Review":
                offenders.append(f"{path.name}:{node.lineno}")
            if isinstance(node, ast.Constant) and node.value == "Review":
                offenders.append(f"{path.name}:{node.lineno} (literal)")
    assert offenders == [], (
        "an evidence consumer names the Review type:\n" + "\n".join(offenders)
    )
