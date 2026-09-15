"""R-4 — one reconciliation-state derivation, derived from §5.1.

Acceptance criterion (MICRO-VERIFY-01, OWNER DISPOSITION):
    reconciliation_state is computed by one function derived from §5.1; no
    second implementation exists. Test: every old-epoch status maps as
    specified, PROPOSED/BLOCKED/AUTHORIZED -> ORPHANED.

Design basis: transition-matrix §5.1 (the four-row table and its two shared
consequences), domain-model `WorkerInvocation.reconciliation_state` and
`CommitIntent.reconciliation_state`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from genesis_support import OWNER
from gruntime.errors import IntegrityViolation
from gruntime.models import (
    CommitIntentStatus,
    InvocationStatus,
    ReconciliationState,
    is_terminal_status,
)
from gruntime.reconciliation import (
    Observation,
    clears_barrier,
    derive_reconciliation_state,
    requires_lookup,
)

SRC = Path(__file__).resolve().parents[1] / "src" / "gruntime"

NON_TERMINAL = [
    InvocationStatus.PENDING,
    InvocationStatus.DISPATCHED,
    InvocationStatus.RUNNING,
    CommitIntentStatus.PROPOSED,
    CommitIntentStatus.BLOCKED,
    CommitIntentStatus.AUTHORIZED,
    CommitIntentStatus.APPLYING,
]

TERMINAL = [
    InvocationStatus.COMPLETED,
    InvocationStatus.FAILED,
    InvocationStatus.TIMED_OUT,
    InvocationStatus.CANCELLED,
    InvocationStatus.REJECTED_BY_POLICY,
    CommitIntentStatus.DENIED,
    CommitIntentStatus.APPLIED,
    CommitIntentStatus.FAILED,
    CommitIntentStatus.ROLLED_BACK,
]


def _derive(status, record_epoch, project_epoch, **kw):
    return derive_reconciliation_state(
        record_epoch=record_epoch,
        project_epoch=project_epoch,
        status_terminal=is_terminal_status(status),
        **kw,
    )


@pytest.mark.parametrize("status", NON_TERMINAL + TERMINAL, ids=str)
def test_current_epoch_is_not_required(status):
    assert _derive(status, 7, 7) is ReconciliationState.NOT_REQUIRED


@pytest.mark.parametrize("status", NON_TERMINAL, ids=str)
def test_old_epoch_non_terminal_is_pending(status):
    """Row 2 holds for *every* non-terminal status of either entity."""
    assert _derive(status, 6, 7) is ReconciliationState.PENDING


@pytest.mark.parametrize("status", TERMINAL, ids=str)
def test_old_epoch_terminal_is_not_required(status):
    assert _derive(status, 6, 7) is ReconciliationState.NOT_REQUIRED


@pytest.mark.parametrize(
    ("observation", "expected"),
    [
        (Observation.FINISHED, ReconciliationState.ADOPTED),
        (Observation.ABSENT, ReconciliationState.ORPHANED),
        (Observation.LIVE, ReconciliationState.PENDING),
        (Observation.UNANSWERABLE, ReconciliationState.UNRESOLVABLE),
        (Observation.TOKEN_MATCHED, ReconciliationState.ADOPTED),
        (Observation.TOKEN_MATCHED_DIVERGED, ReconciliationState.ADOPTED),
        (Observation.NO_TOKEN_BASE_UNCHANGED, ReconciliationState.ORPHANED),
        (Observation.AMBIGUOUS, ReconciliationState.UNRESOLVABLE),
    ],
    ids=lambda v: str(v),
)
def test_observations_map_to_row_four(observation, expected):
    assert _derive(
        InvocationStatus.DISPATCHED, 6, 7, observation=observation
    ) is expected


@pytest.mark.parametrize(
    "prior",
    [
        ReconciliationState.ADOPTED,
        ReconciliationState.ORPHANED,
        ReconciliationState.UNRESOLVABLE,
    ],
    ids=str,
)
def test_a_reconciled_record_never_reverts_to_not_required(prior):
    """Row 4 is terminal and takes precedence over NOT_REQUIRED."""
    for record_epoch, project_epoch in ((7, 7), (6, 7), (3, 99)):
        for status in (InvocationStatus.DISPATCHED, InvocationStatus.COMPLETED):
            assert _derive(status, record_epoch, project_epoch, prior=prior) is prior


def test_a_record_from_the_future_is_an_integrity_violation():
    with pytest.raises(IntegrityViolation):
        _derive(InvocationStatus.DISPATCHED, 8, 7)


def test_barrier_and_lookup_predicates_follow_the_same_table():
    blocking = {ReconciliationState.PENDING, ReconciliationState.UNRESOLVABLE}
    for state in ReconciliationState:
        assert clears_barrier(state) is (state not in blocking)
    assert requires_lookup(ReconciliationState.PENDING) is True
    for state in ReconciliationState:
        if state is not ReconciliationState.PENDING:
            assert requires_lookup(state) is False


def test_pre_applying_intents_reconcile_to_orphaned_without_changing_status(h):
    """The explicit PROPOSED/BLOCKED/AUTHORIZED -> ORPHANED requirement."""
    h.init_repo()
    with h.controller(with_repo=True) as c:
        project_id = c.create_project(
            name="R4", slug="r4", workspace_root=str(h.repo_dir),
            approved_by=OWNER,
        )
        c.start(project_id)
        run_id = c.open_run(project_id)

        proposed = c.propose_commit(run_id, path="a.txt", content="a\n", message="a")

        blocked = c.propose_commit(run_id, path="b.txt", content="b\n", message="b")
        c.block_commit(blocked.intent_id)

        authorized = c.propose_commit(run_id, path="c.txt", content="c\n", message="c")
        c.authorize_commit(authorized.intent_id)

    expected_status = {
        proposed.intent_id: CommitIntentStatus.PROPOSED,
        blocked.intent_id: CommitIntentStatus.BLOCKED,
        authorized.intent_id: CommitIntentStatus.AUTHORIZED,
    }

    with h.store() as s:
        for intent_id in expected_status:
            assert (
                s.get_commit_intent(intent_id).reconciliation_state
                is ReconciliationState.NOT_REQUIRED
            )

    with h.controller(with_repo=True) as c:
        c.start(project_id)
        with h.store() as s:
            for intent_id in expected_status:
                assert (
                    s.get_commit_intent(intent_id).reconciliation_state
                    is ReconciliationState.PENDING
                )
        c.recover(project_id)

    with h.store() as s:
        for intent_id, status in expected_status.items():
            intent = s.get_commit_intent(intent_id)
            assert intent.status is status, "recovery changed a pre-APPLYING status"
            assert intent.reconciliation_state is ReconciliationState.ORPHANED
        s.verify_chain(project_id)
        s.audit_reconciliation_closure(project_id)

    # ORPHANED clears the barrier: the run may initiate effects again.
    with h.controller(with_repo=True) as c:
        c.create_invocation(run_id, prompt=b"after orphaning")


def test_no_second_implementation_of_the_derivation():
    """Only `reconciliation.py` may name a `ReconciliationState` member."""
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        if path.name == "reconciliation.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "ReconciliationState"
            ):
                offenders.append(f"{path.name}:{node.lineno} ReconciliationState.{node.attr}")
    assert offenders == [], (
        "reconciliation state is derived outside the single §5.1 derivation:\n"
        + "\n".join(offenders)
    )


def test_the_derivation_table_has_exactly_the_four_rows():
    """Documented provenance: the function is the §5.1 table, not a paraphrase."""
    doc = derive_reconciliation_state.__doc__ or ""
    assert "§5.1" in doc
    assert "single" in doc.lower()
