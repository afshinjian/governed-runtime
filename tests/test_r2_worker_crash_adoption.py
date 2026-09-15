"""R-2 — kill -9 between a FINISHED lookup and a durable receipt.

Acceptance criterion (MICRO-VERIFY-01, OWNER DISPOSITION):
    on restart the operation is adopted exactly once, outcome preserved.

The controller runs as a real subprocess and is terminated with SIGKILL at two
distinct points: after the provider execution finished but before the direct
receipt (CF-11), and after a FINISHED lookup but before the reconciled receipt
(WP-16, transition-matrix §7.2). Every assertion reads on-disk state.

The seeded outcome is `REFUSED` / `REFUSAL`, the case F01-002 identified as
unrepresentable in the frozen design: adoption must preserve it as a refusal
mapped to `FAILED`, never upgrade it to `COMPLETED` (D3, W-INV-4).
"""

from __future__ import annotations

from genesis_support import OWNER
from gruntime.models import (
    Attribution,
    InvocationStatus,
    OutcomeStatus,
    ReconciliationState,
    TerminationReason,
)


def _setup(h):
    provider = h.provider()
    provider.set_default_outcome(
        status=OutcomeStatus.REFUSED,
        termination_reason=TerminationReason.REFUSAL,
        output=b"declined: outside the contract objective",
    )
    with h.controller() as c:
        project_id = c.create_project(name="R2", slug="r2", workspace_root=str(h.root),
                                      approved_by=OWNER)
        c.start(project_id)
        run_id = c.open_run(project_id)
    return project_id, run_id


def _only_invocation(store, run_id):
    invocations = store.list_invocations(run_id)
    assert len(invocations) == 1, f"expected one invocation, got {len(invocations)}"
    return invocations[0]


def test_crash_between_finished_lookup_and_receipt_adopts_exactly_once(h):
    project_id, run_id = _setup(h)

    # --- controller #1: dies after the provider executed, before the receipt.
    proc = h.spawn(project_id, "invoke", "--run", run_id,
                   gate="after_invoke_before_receipt")
    h.wait_for_gate("after_invoke_before_receipt", proc)
    h.kill9(proc)

    assert len(h.provider().executions()) == 1
    with h.store() as s:
        inv = _only_invocation(s, run_id)
        invocation_id = inv.invocation_id
        key = inv.idempotency_key
        assert inv.status is InvocationStatus.DISPATCHED
        assert s.list_worker_receipts(invocation_id) == []
        assert s.get_project(project_id).controller_epoch == 2
        s.verify_chain(project_id)

    # --- controller #2: dies after a FINISHED lookup, before the receipt.
    proc = h.spawn(project_id, "recover", gate="after_lookup_before_receipt")
    h.wait_for_gate("after_lookup_before_receipt", proc)
    h.kill9(proc)

    provider = h.provider()
    assert len(provider.executions()) == 1, "recovery re-executed the invocation"
    assert provider.lookups() == [key]
    with h.store() as s:
        inv = s.get_invocation(invocation_id)
        assert inv.status is InvocationStatus.DISPATCHED
        assert inv.reconciliation_state is ReconciliationState.PENDING
        assert s.list_worker_receipts(invocation_id) == []
        assert s.get_project(project_id).controller_epoch == 3
        s.verify_chain(project_id)

    # --- controller #3: completes the adoption.
    h.run(project_id, "recover")

    provider = h.provider()
    assert len(provider.executions()) == 1, "adoption re-executed the invocation"
    assert provider.lookups() == [key, key]
    with h.store() as s:
        inv = s.get_invocation(invocation_id)
        assert inv.status is InvocationStatus.FAILED  # REFUSED => FAILED
        assert inv.reconciliation_state is ReconciliationState.ADOPTED

        receipts = s.list_worker_receipts(invocation_id)
        assert len(receipts) == 1, "the outcome was adopted more than once"
        receipt = receipts[0]
        assert receipt.attribution is Attribution.RECONCILED
        assert receipt.termination_reason is TerminationReason.REFUSAL
        assert s.artifact_bytes(receipt.output_digest) == (
            b"declined: outside the contract objective"
        )
        s.verify_chain(project_id)

    # --- controller #4: §5.1 precedence. A reconciled record stays reconciled.
    h.run(project_id, "recover")

    assert len(h.provider().executions()) == 1
    assert len(h.provider().lookups()) == 2, "a settled record was looked up again"
    with h.store() as s:
        inv = s.get_invocation(invocation_id)
        assert inv.reconciliation_state is ReconciliationState.ADOPTED
        assert len(s.list_worker_receipts(invocation_id)) == 1
        assert s.get_project(project_id).controller_epoch == 5
        s.verify_chain(project_id)


def test_adoption_bills_once_and_keeps_the_durable_key(h):
    """WP-6/WP-15: the key survives the restart and is never re-minted."""
    project_id, run_id = _setup(h)

    proc = h.spawn(project_id, "invoke", "--run", run_id,
                   gate="after_invoke_before_receipt")
    h.wait_for_gate("after_invoke_before_receipt", proc)
    h.kill9(proc)

    with h.store() as s:
        key_before = _only_invocation(s, run_id).idempotency_key

    h.run(project_id, "recover")

    with h.store() as s:
        inv = _only_invocation(s, run_id)
        assert inv.idempotency_key == key_before
        # The persisted request is auditable and was never re-sent.
        assert s.artifact_bytes(inv.request_digest)
    executions = h.provider().executions()
    assert [e["idempotency_key"] for e in executions] == [key_before]
