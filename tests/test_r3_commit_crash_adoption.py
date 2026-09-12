"""R-3 — kill -9 between commit and receipt.

Acceptance criterion (MICRO-VERIFY-01, OWNER DISPOSITION):
    restart adopts the landed commit exactly once, never commits twice,
    never exempts the gate.

The controller runs as a real subprocess and is SIGKILLed after the repository
mutation landed and before the `CommitReceipt` is durable. Assertions read the
real git repository and the on-disk state store.

Design basis: CM-INV-2, CM-INV-3, transition-matrix §5 (RUN-INV-3 gate and its
`recovery.reconcile` exemption), §7.4 reconciliation rows.
"""

from __future__ import annotations

import pytest

from gruntime.errors import BarrierViolation
from gruntime.models import (
    Attribution,
    CommitIntentStatus,
    ReconciliationState,
    Verification,
)


def _setup(h):
    h.init_repo()
    with h.controller(with_repo=True) as c:
        project_id = c.create_project(
            name="R3", slug="r3", workspace_root=str(h.repo_dir)
        )
        c.start(project_id)
        run_id = c.open_run(project_id)
    return project_id, run_id


def _only_intent(store, run_id):
    intents = store.list_commit_intents(run_id)
    assert len(intents) == 1, f"expected one intent, got {len(intents)}"
    return intents[0]


def test_crash_between_commit_and_receipt_adopts_the_landed_commit_once(h):
    project_id, run_id = _setup(h)
    base_revisions = h.revision_count()

    proc = h.spawn(
        project_id, "commit", "--run", run_id,
        "--path", "feature.txt", "--content", "implemented\n",
        gate="after_commit_before_receipt",
    )
    h.wait_for_gate("after_commit_before_receipt", proc)
    h.kill9(proc)

    repo = h.repo()
    with h.store() as s:
        intent = _only_intent(s, run_id)
        intent_id = intent.intent_id
        token = intent.operation_token
        assert intent.status is CommitIntentStatus.APPLYING
        assert s.list_commit_receipts(intent_id) == []
        assert s.get_project(project_id).controller_epoch == 2
        s.verify_chain(project_id)

    landed = repo.find_by_token(token)
    assert len(landed) == 1, "the commit did not land before the kill"
    assert h.revision_count() == base_revisions + 1

    # --- the gate is not exempted while the intent is unreconciled.
    with h.controller(with_repo=True) as c:
        c.start(project_id)  # epoch 3
        with pytest.raises(BarrierViolation):
            c.create_invocation(run_id, prompt=b"more work")
        second = c.propose_commit(
            run_id, path="other.txt", content="other\n", message="second"
        )
        c.authorize_commit(second.intent_id)
        with pytest.raises(BarrierViolation):
            c.apply_commit(second.intent_id)

        assert h.revision_count() == base_revisions + 1

        # --- reconciliation itself is permitted, and clears the barrier.
        c.recover(project_id)

    assert len(repo.find_by_token(token)) == 1, "the commit landed twice"
    assert h.revision_count() == base_revisions + 1

    with h.store() as s:
        intent = s.get_commit_intent(intent_id)
        assert intent.status is CommitIntentStatus.APPLIED
        assert intent.reconciliation_state is ReconciliationState.ADOPTED

        receipts = s.list_commit_receipts(intent_id)
        assert len(receipts) == 1, "the commit was adopted more than once"
        receipt = receipts[0]
        assert receipt.attribution is Attribution.RECONCILED
        assert receipt.verification is Verification.MATCHED
        assert receipt.revision_id == landed[0]
        assert receipt.operation_token == token
        s.verify_chain(project_id)
        s.audit_reconciliation_closure(project_id)

    # --- with the run reconciled, new external effects are permitted again.
    with h.controller(with_repo=True) as c:
        invocation = c.create_invocation(run_id, prompt=b"next")
        assert invocation.invocation_id

    # --- a further restart neither re-adopts nor re-commits.
    h.run(project_id, "recover")
    assert h.revision_count() == base_revisions + 1
    with h.store() as s:
        assert len(s.list_commit_receipts(intent_id)) == 1
        assert (
            s.get_commit_intent(intent_id).reconciliation_state
            is ReconciliationState.ADOPTED
        )
        s.verify_chain(project_id)


def test_nothing_landed_is_reconciled_as_orphaned_not_retried(h):
    """§7.4 row 2: no revision carries the token and the base still matches."""
    project_id, run_id = _setup(h)
    base_revisions = h.revision_count()

    with h.controller(with_repo=True) as c:
        intent = c.propose_commit(
            run_id, path="never.txt", content="never\n", message="never applied"
        )
        c.authorize_commit(intent.intent_id)
        c.mark_applying(intent.intent_id)

    with h.controller(with_repo=True) as c:
        c.start(project_id)
        c.recover(project_id)

    assert h.revision_count() == base_revisions, "recovery retried the commit"
    with h.store() as s:
        reloaded = s.get_commit_intent(intent.intent_id)
        assert reloaded.status is CommitIntentStatus.FAILED
        assert reloaded.reconciliation_state is ReconciliationState.ORPHANED
        assert s.list_commit_receipts(intent.intent_id) == []
        s.verify_chain(project_id)


def test_divergent_landed_tree_is_adopted_as_a_failure(h):
    """§7.4 row 3: the outcome was established, and it was a failure."""
    project_id, run_id = _setup(h)

    proc = h.spawn(
        project_id, "commit", "--run", run_id,
        "--path", "feature.txt", "--content", "implemented\n",
        gate="after_commit_before_receipt",
    )
    h.wait_for_gate("after_commit_before_receipt", proc)
    h.kill9(proc)

    with h.store() as s:
        intent_id = _only_intent(s, run_id).intent_id
        s.force_expected_tree_digest(intent_id, "sha256:" + "00" * 32)

    with h.controller(with_repo=True) as c:
        c.start(project_id)
        c.recover(project_id)

    with h.store() as s:
        intent = s.get_commit_intent(intent_id)
        assert intent.status is CommitIntentStatus.FAILED
        assert intent.reconciliation_state is ReconciliationState.ADOPTED
        receipts = s.list_commit_receipts(intent_id)
        assert len(receipts) == 1
        assert receipts[0].verification is Verification.DIVERGED
        assert receipts[0].attribution is Attribution.RECONCILED
        assert any(
            e.trigger == "INTEGRITY_VIOLATION" for e in s.list_escalations(project_id)
        )
        s.verify_chain(project_id)
