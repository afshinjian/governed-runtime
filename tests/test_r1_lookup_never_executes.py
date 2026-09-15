"""R-1 — `lookup()` never executes an unknown `idempotency_key`.

Acceptance criterion (MICRO-VERIFY-01, OWNER DISPOSITION):
    unknown key returns ABSENT with zero provider-side side effects.

Design basis: worker_provider.md WP-16, WP-17, CF-12; §6.1 step 4;
transition-matrix §7.2 `ABSENT` row.
"""

from __future__ import annotations

import pytest

from gruntime.errors import CapabilityDenied
from gruntime.models import (
    Attribution,
    InvocationStatus,
    ReconciliationState,
    TerminationReason,
)
from gruntime.provider import LookupAbsent, RECOVERY_CAPABILITIES, GovernedProvider

from genesis_support import OWNER


def _seed_unreachable_invocation(h):
    """An invocation whose request is durable but which the provider never saw."""
    with h.controller() as c:
        project_id = c.create_project(name="R1", slug="r1", workspace_root=str(h.root),
                                      approved_by=OWNER)
        c.start(project_id)
        run_id = c.open_run(project_id)
        inv = c.create_invocation(run_id, prompt=b"unreachable")
        # The controller died between the durable request (WP-15) and the
        # provider call: the key exists in the log, not at the provider.
        c.mark_dispatched(inv.invocation_id)
        return project_id, run_id, inv


def test_unknown_key_returns_absent_and_executes_nothing(h):
    project_id, _run_id, inv = _seed_unreachable_invocation(h)

    provider = h.provider()
    assert provider.executions() == []

    result = GovernedProvider(provider, RECOVERY_CAPABILITIES).lookup(inv.idempotency_key)

    assert isinstance(result, LookupAbsent)
    assert provider.executions() == [], "lookup executed the unknown key"
    assert provider.lookups() == [inv.idempotency_key]


def test_recovery_orphans_the_invocation_without_any_execution(h):
    project_id, _run_id, inv = _seed_unreachable_invocation(h)

    with h.controller() as c:
        c.start(project_id)
        c.recover(project_id)

    provider = h.provider()
    assert provider.executions() == [], "recovery executed an absent key"

    with h.store() as s:
        reloaded = s.get_invocation(inv.invocation_id)
        assert reloaded.status is InvocationStatus.FAILED
        assert reloaded.reconciliation_state is ReconciliationState.ORPHANED

        receipts = s.list_worker_receipts(inv.invocation_id)
        assert len(receipts) == 1
        assert receipts[0].termination_reason is TerminationReason.PROVIDER_ERROR
        assert receipts[0].attribution is Attribution.RECONCILED
        s.verify_chain(project_id)


def test_recovery_holds_no_capability_that_can_execute(h):
    """WP-16: `recovery.reconcile` reaches `lookup` and nothing else."""
    project_id, _run_id, inv = _seed_unreachable_invocation(h)
    governed = GovernedProvider(h.provider(), RECOVERY_CAPABILITIES)

    with pytest.raises(CapabilityDenied):
        governed.invoke(object())
    with pytest.raises(CapabilityDenied):
        governed.preflight(object())

    assert h.provider().executions() == []
    assert "worker.invoke" not in RECOVERY_CAPABILITIES


def test_lookup_takes_a_key_and_nothing_executable(h):
    """D1: `lookup` is a separate operation; it accepts no request bytes."""
    import inspect

    from gruntime.provider import WorkerProvider

    sig = inspect.signature(WorkerProvider.lookup)
    params = [p for p in sig.parameters if p != "self"]
    assert params == ["idempotency_key"]
