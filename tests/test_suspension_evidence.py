"""A declared suspension must be durable, with a reference iff it is set."""
from dataclasses import replace
import json
import sqlite3

import pytest

from gruntime.controller import Controller
from gruntime.errors import IntegrityViolation, PolicyDenied, ProviderUnavailable
from gruntime.models import (
    EpistemicClass, EscalationSeverity, EscalationTrigger, ReconciliationState,
    SuspensionState,
)


@pytest.fixture
def runtime(h):
    with h.controller() as c:
        project = c.create_project(name="suspension", slug="suspension", workspace_root=str(h.root))
        c.start(project)
        run = Controller.open_run(c, project)
        yield h, c, project, run


def raise_escalation(c, project, **kwargs):
    return c._raise_escalation(
        project, severity=EscalationSeverity.HIGH, summary="suspension evidence",
        trigger=EscalationTrigger.RECOVERY_AMBIGUITY, **kwargs,
    )


@pytest.mark.parametrize("trigger", list(EscalationTrigger))
@pytest.mark.parametrize("target_run", [False, True])
def test_every_escalation_class_applies_its_declared_suspension(runtime, trigger, target_run):
    h, c, project, run = runtime
    before_project, before_run = c.store.get_project(project), c.store.get_run(run)
    escalation_id = c._raise_escalation(
        project, trigger=trigger, severity=EscalationSeverity.HIGH,
        summary="apply declared suspension", run_id=run if target_run else None,
    )
    # Read from another connection: an in-memory assignment is not evidence.
    with h.store() as store:
        escalation, = store.list_escalations(project)
        state = store.get_project(project)
        assert escalation.escalation_id == escalation_id
        assert escalation.suspension_applied is SuspensionState.SUSPENDED_BY_INTEGRITY
        assert escalation.suspension_target == ("RUN" if target_run else "PROJECT")
        assert state.suspension is escalation.suspension_applied
        assert state.suspension_ref == escalation_id
        assert state.lifecycle is before_project.lifecycle
        stored_run = store.get_run(run)
        assert stored_run.lifecycle is before_run.lifecycle
        assert stored_run.suspension is (escalation.suspension_applied if target_run else SuspensionState.NONE)
        events = [e for e in store.list_events(project) if e.event_type == "suspension.set"]
        assert len(events) == (2 if target_run else 1)
        for event in events:
            payload = json.loads(store.artifact_bytes(event.payload_digest))
            assert event.epistemic_class is EpistemicClass.AUTHORITY
            assert payload["to"] == escalation.suspension_applied.value
            assert payload["suspension_ref"] == escalation_id
        store.verify_chain(project)
    with pytest.raises(PolicyDenied, match="Suspension is a hard gate"):
        c.create_invocation(run, prompt=b"blocked")


@pytest.mark.parametrize("suspension", [s for s in SuspensionState if s is not SuspensionState.NONE])
def test_each_suspension_value_is_applied_and_can_be_cleared(runtime, suspension):
    h, c, project, run = runtime
    escalation_id = raise_escalation(c, project, run_id=run, suspension=suspension)
    with h.store() as store:
        assert store.get_project(project).suspension is suspension
        assert store.get_project(project).suspension_ref == escalation_id
        assert store.get_run(run).suspension is suspension
    c._set_suspension(project, SuspensionState.NONE, reason="cleared")
    with h.store() as store:
        assert store.get_project(project).suspension is SuspensionState.NONE
        assert store.get_project(project).suspension_ref is None
        store.verify_chain(project)


@pytest.mark.parametrize("already_suspended", [False, True])
def test_none_escalation_does_not_set_or_clear_suspension(runtime, already_suspended):
    h, c, project, run = runtime
    if already_suspended:
        raise_escalation(c, project, run_id=run)
    before_project, before_run = c.store.get_project(project), c.store.get_run(run)
    before = c.store.list_events(project)
    raise_escalation(c, project, run_id=run, suspension=SuspensionState.NONE)
    with h.store() as store:
        escalation = store.list_escalations(project)[-1]
        assert escalation.suspension_applied is SuspensionState.NONE
        assert escalation.suspension_target == "NONE"
        assert store.get_project(project).suspension is before_project.suspension
        assert store.get_project(project).suspension_ref == before_project.suspension_ref
        assert store.get_run(run).suspension is before_run.suspension
        assert [e.event_type for e in store.list_events(project)[len(before):]] == ["escalation.raised"]
        store.verify_chain(project)


def test_repeated_suspension_links_the_new_escalation_and_audits_it(runtime):
    h, c, project, _ = runtime
    first = raise_escalation(c, project)
    second = raise_escalation(c, project)
    assert second != first
    with h.store() as store:
        assert store.get_project(project).suspension_ref == second
        events = [e for e in store.list_events(project) if e.event_type == "suspension.set"]
        assert [json.loads(store.artifact_bytes(e.payload_digest))["suspension_ref"] for e in events] == [first, second]
        store.verify_chain(project)


@pytest.mark.parametrize("table", ["projects", "runs"])
@pytest.mark.parametrize("nested", [False, True])
def test_failed_suspension_write_rolls_back_claim_state_and_audit(runtime, table, nested):
    h, c, project, run = runtime
    if nested:
        c.store.raw_execute("BEGIN IMMEDIATE")
        c._append(project, event_type="test.before_escalation", epistemic_class=EpistemicClass.CLAIM,
                  subject={"project_id": project}, payload={})
    before_project, before_run = c.store.get_project(project), c.store.get_run(run)
    before_events = c.store.list_events(project)
    c.store.raw_execute(f"""CREATE TEMP TRIGGER fail_suspension BEFORE UPDATE OF suspension ON {table}
        BEGIN SELECT RAISE(ABORT, 'suspension write failed'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="suspension write failed"):
        raise_escalation(c, project, run_id=run)
    assert c.store.connection.in_transaction is nested
    assert c.store.list_escalations(project) == []
    assert c.store.get_project(project) == before_project
    assert c.store.get_run(run) == before_run
    assert c.store.list_events(project) == before_events
    if nested:
        c.store.raw_execute("COMMIT")
    with h.store() as store:
        assert store.list_escalations(project) == []
        assert store.get_project(project).suspension is SuspensionState.NONE
        store.verify_chain(project)


INVALID_REFS = [(SuspensionState.NONE, "esc-stale"), (SuspensionState.NONE, "")]
INVALID_REFS += [(state, ref) for state in SuspensionState if state is not SuspensionState.NONE
                 for ref in (None, "")]


@pytest.mark.parametrize("suspension,reference", INVALID_REFS)
@pytest.mark.parametrize("boundary", ["transition", "update", "put", "insert", "read"])
def test_suspension_reference_is_required_iff_non_none(runtime, suspension, reference, boundary):
    _, c, project, _ = runtime
    before = c.store.get_project(project)
    events = c.store.list_events(project)
    with pytest.raises(IntegrityViolation, match="suspension_ref"):
        if boundary == "transition":
            c._set_suspension(project, suspension, suspension_ref=reference, reason="invalid")
        elif boundary == "update":
            c.store.set_project_suspension(project, suspension, suspension_ref=reference)
        elif boundary in ("put", "insert"):
            c.store.put_project(replace(before, suspension=suspension, suspension_ref=reference,
                                        project_id="new-project" if boundary == "insert" else project))
        else:
            c.store.raw_execute("UPDATE projects SET suspension=?, suspension_ref=? WHERE project_id=?",
                                (suspension.value, reference, project))
            c.store.get_project(project)
    if boundary == "read":
        c.store.raw_execute("UPDATE projects SET suspension=?, suspension_ref=? WHERE project_id=?",
                            (before.suspension.value, before.suspension_ref, project))
    assert c.store.get_project(project) == before
    assert c.store.list_events(project) == events
    assert c.store.raw_execute("SELECT project_id FROM projects WHERE project_id='new-project'") == []


def test_same_state_transition_cannot_drop_the_reference(runtime):
    _, c, project, _ = runtime
    raise_escalation(c, project)
    before = c.store.get_project(project)
    with pytest.raises(IntegrityViolation, match="suspension_ref"):
        c._set_suspension(project, before.suspension, reason="missing reference")
    assert c.store.get_project(project) == before


def test_unanswerable_worker_recovery_suspends_run_and_project(h, monkeypatch):
    with h.controller() as c:
        project = c.create_project(name="recovery", slug="recovery", workspace_root=str(h.root))
        c.start(project)
        run = c.open_run(project)
        other_run = c.open_run(project)
        invocation = c.create_invocation(run, prompt=b"pending")
        c.mark_dispatched(invocation.invocation_id)
        c.start(project)
        def unavailable(_key):
            raise ProviderUnavailable("lookup unavailable")
        monkeypatch.setattr(c.provider, "lookup", unavailable)
        outcome = c.recover(project)
        assert invocation.invocation_id in outcome.unresolved
        with pytest.raises(PolicyDenied, match="Suspension is a hard gate"):
            c.create_invocation(other_run, prompt=b"project is suspended")
    with h.store() as store:
        escalation, = store.list_escalations(project)
        assert escalation.trigger is EscalationTrigger.RECOVERY_AMBIGUITY
        assert escalation.suspension_applied is SuspensionState.SUSPENDED_BY_INTEGRITY
        assert store.get_project(project).suspension is escalation.suspension_applied
        assert store.get_project(project).suspension_ref == escalation.escalation_id
        assert store.get_run(run).suspension is escalation.suspension_applied
        assert store.get_invocation(invocation.invocation_id).reconciliation_state is ReconciliationState.UNRESOLVABLE
        assert store.list_worker_receipts(invocation.invocation_id) == []
        store.verify_chain(project)
    assert h.provider().executions() == []
