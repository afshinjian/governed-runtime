"""GR-31 `Q2a`: fail closed on review and validation preconditions.

This guard closes nothing. It is a temporary Pilot-1 safety boundary over two
open findings, and it exists so that the deferral is structural rather than
conventional — a rule the runtime enforces, not a rule the driver is trusted
to follow.

The two findings it stands in front of:

`B6` — `evaluate_preconditions` calls `resolve_attestation(ref)` and discards
the result (`commit.py:101-104`), so a `ReviewAttestation` whose verdict is
`FAIL` discharges a review precondition exactly as a passing one does. The
predicate written for this, `rvw()` (`review.py:160`), has no production
caller at all. Same shape as `F03-001`.

`B7` — a validation precondition is discharged by artifact existence, not by a
passing receipt: `resolve_validation=lambda digest: self.store.artifacts.has(digest)`.
Any blob at that digest satisfies it.

Both are open and deferred. Until they close, a commit intent that binds
either kind of precondition would be authorized on evidence that was never
actually measured, and "the preconditions were met" would be a false
statement in the audit. So `authorize_commit` refuses to authorize such an
intent at all, rather than meeting its preconditions hollowly.

What this is **not**: it is not a fix for `B6` or `B7`, it does not change
review-attestation semantics, validation-precondition semantics, `rvw()`, or
generic precondition resolution, and `commit.py` and `review.py` are
untouched. GR-33 must not bypass or weaken it (`Q2a`).

The `decisions` precondition is deliberately left alone: `resolve_decision`
stays `lambda ref: False` (`Q4`), so a decision-backed precondition is
permanently unmet and routes to `BLOCKED` — the existing behaviour, unchanged.
"""

from __future__ import annotations

import pytest

from gruntime.errors import PolicyDenied
from gruntime.models import (
    CommitIntentStatus,
    CommitPreconditions,
    DecisionSubjectKind,
    Ref,
)

from test_gr31_supervision_gates import confirmation, granted_run, provisioned


def commit_confirmation(c, project, intent):
    return confirmation(c, project, subject_kind=DecisionSubjectKind.COMMIT_INTENT,
                        subject_id=intent.intent_id).decision_id


def test_a_validation_precondition_is_refused(h):
    """`B7`: artifact existence is not a passing receipt."""
    project = provisioned(h, "gr31-q2a-v")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        intent = c.propose_commit(
            run, path="v.txt", content="v\n", message="v",
            preconditions=CommitPreconditions(validations=("sha256:" + "0" * 64,)))
        with pytest.raises(PolicyDenied, match="discharged by artifact existence"):
            c.authorize_commit(intent.intent_id,
                               confirmation_id=commit_confirmation(c, project, intent))
        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.PROPOSED)


def test_a_review_precondition_is_refused(h):
    """`B6`: a discarded `resolve_attestation` result discharges a FAIL."""
    project = provisioned(h, "gr31-q2a-r")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        intent = c.propose_commit(
            run, path="r.txt", content="r\n", message="r",
            preconditions=CommitPreconditions(
                reviews=(Ref("ReviewAttestation", "att-does-not-matter"),)))
        with pytest.raises(PolicyDenied, match="discards the result"):
            c.authorize_commit(intent.intent_id,
                               confirmation_id=commit_confirmation(c, project, intent))
        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.PROPOSED)


def test_the_refusal_names_both_findings(h):
    """The message cites `B6` and `B7` by their code locations.

    A deferral that did not say what it was deferring would read as a rule,
    and the next stage would have no way to know which findings closing would
    let it be removed.
    """
    project = provisioned(h, "gr31-q2a-msg")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        intent = c.propose_commit(
            run, path="m.txt", content="m\n", message="m",
            preconditions=CommitPreconditions(validations=("sha256:" + "1" * 64,)))
        with pytest.raises(PolicyDenied) as refused:
            c.authorize_commit(intent.intent_id,
                               confirmation_id=commit_confirmation(c, project, intent))
        message = str(refused.value)
        assert "commit.py:101-104" in message
        assert "resolve_validation" in message
        assert "1 validation precondition" in message


def test_an_empty_precondition_set_passes(h):
    """The boundary defers two kinds of precondition; it bans nothing else.

    An intent that binds neither is authorized exactly as before.
    """
    project = provisioned(h, "gr31-q2a-empty")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        intent = c.propose_commit(run, path="e.txt", content="e\n", message="e",
                                  preconditions=CommitPreconditions())
        c.authorize_commit(intent.intent_id,
                           confirmation_id=commit_confirmation(c, project, intent))
        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.AUTHORIZED)


def test_a_decision_precondition_still_routes_to_blocked(h):
    """`Q4`: `resolve_decision` is unchanged, and so is what it does.

    A decision-backed precondition is permanently unmet and blocks the intent.
    This guard did not widen into it, and this test is what says so.
    """
    project = provisioned(h, "gr31-q2a-dec")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        intent = c.propose_commit(
            run, path="d.txt", content="d\n", message="d",
            preconditions=CommitPreconditions(decisions=(Ref("HumanDecision", "dec-x"),)))
        c.authorize_commit(intent.intent_id,
                           confirmation_id=commit_confirmation(c, project, intent))
        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.BLOCKED)


def test_the_refusal_precedes_every_status_write(h):
    """Refused before the intent moves, and before the repository is touched.

    The guard sits ahead of the confirmation, the commit-authority replay and
    the head check, so a deferred precondition never reaches a transition at
    all — not `AUTHORIZED`, and not `BLOCKED` either. Blocking it would be a
    verdict about evidence the runtime has just said it cannot evaluate.
    """
    project = provisioned(h, "gr31-q2a-order")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        intent = c.propose_commit(
            run, path="o.txt", content="o\n", message="o",
            preconditions=CommitPreconditions(validations=("sha256:" + "2" * 64,)))
        before = len(c.store.list_events(project))

        # No confirmation at all: the deferral is asked first, so this is the
        # refusal that comes back rather than row 7.4-4's.
        with pytest.raises(PolicyDenied, match="neither kind can be discharged soundly"):
            c.authorize_commit(intent.intent_id)

        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.PROPOSED)
        assert len(c.store.list_events(project)) == before
        c.store.verify_chain(project)
