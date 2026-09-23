"""GR-31: the three `SUPERVISED` `CONFIRM` cells the pilot actually traverses.

`G1`, `G2`, `G3`. The frozen matrix declares a policy verdict for every row,
and `CONFIRM` means a human confirms the transition before it happens. Three
rows on the pilot path carried that verdict and nothing enforced it:

===========  ==============================  ===========================
row          transition                      matrix line
===========  ==============================  ===========================
5-1          `∅ → ALLOCATED` (`run.start`)   transition-matrix.md:189
7.2-1        `∅ → PENDING`, first of a run   transition-matrix.md:305
7.4-4        `PROPOSED → AUTHORIZED`         transition-matrix.md:349
===========  ==============================  ===========================

`_require_transition_authority` proves the row's `required_capability` and says
in its own docstring that it enforces neither preconditions, evidence nor the
decision step. `policy.resolve` step 10 is the only `CONFIRM`/`DECIDE`
enforcement in the tree and has no production caller. Row 6-2 — contract
activation — was the one cell of the four with a bespoke boundary
(`guard:gr06_activation_confirmation`); these three had none.

What is enforced here is the `SUPERVISED` column only. Every one of these rows
reads `AUTO` under `AUTONOMOUS`, and demanding a confirmation there would be
the runtime inventing a cell the frozen matrix does not declare. Both columns
are asserted below.

Row 7.2-1 is `WHEN(FIRST_INVOCATION_OF_RUN, CONFIRM, AUTO)`, so the
confirmation is asked exactly once per run. Over-applying it would deny a
second invocation the row declares `AUTO`, which is `T9`.

Every refusal is asserted with `match=` naming its row (`CLAUDE.md` Tooling).
"""

from __future__ import annotations

import pytest

from gruntime.controller import Controller
from gruntime.errors import CapabilityDenied
from gruntime.models import (
    CommitIntentStatus,
    DecisionKind,
    DecisionScope,
    DecisionState,
    DecisionSubjectKind,
    GovernanceMode,
    Verification,
)

from genesis_support import OWNER, force_governance_mode
from gr03_support import git
from test_gr31_provisioning import (
    PILOT_BUDGET,
    PILOT_CEILING,
    grant_budget,
    owner_decision,
    set_ceiling,
    supervised_project,
)


# --- helpers ----------------------------------------------------------------


def confirmation(c, project_id, *, subject_kind=DecisionSubjectKind.PROJECT,
                 subject_id=None, scope=DecisionScope.PROJECT):
    """The `CONFIRM` a row declares: an `APPROVE` over the row's subject."""
    return owner_decision(c, project_id, kind=DecisionKind.APPROVE,
                          subject_kind=subject_kind, subject_id=subject_id,
                          scope=scope)


def provisioned(h, slug):
    """A supervised project provisioned through the governed operations."""
    project = supervised_project(h, slug=slug)
    with h.controller(with_repo=True) as c:
        set_ceiling(c, project)
        grant_budget(c, project)
    return project


def granted_run(c, project, *, capabilities=("fs.read", "fs.write", "commit.propose")):
    """Allocate a run under its row-5-1 confirmation and activate a contract."""
    from gr06_support import document

    run = Controller.open_run(
        c, project, confirmation_id=confirmation(c, project).decision_id)
    contract = c.author_contract(document(
        project, c.store.get_run(run).stage_id,
        capability_request=list(capabilities)))
    approval = confirmation(c, project, subject_kind=DecisionSubjectKind.CONTRACT,
                            subject_id=contract.contract_id)
    c.activate_contract(contract.contract_id, run, approval_id=approval.decision_id)
    return run


# --- T8: rows 5-1 and 7.2-1 refuse without their confirmation ---------------


def test_run_start_refuses_without_confirmation(h):
    """Row 5-1. The subject is the `PROJECT`: the run does not exist yet."""
    project = provisioned(h, "gr31-t8a")
    with h.controller(with_repo=True) as c:
        with pytest.raises(CapabilityDenied, match=r"row 5-1 is CONFIRM under SUPERVISED"):
            Controller.open_run(c, project)
        assert c.store.list_runs(project) == []

        # An approval over something else is not this row's confirmation.
        elsewhere = confirmation(c, project, subject_id="not-this-project")
        with pytest.raises(CapabilityDenied, match=r"row 5-1"):
            Controller.open_run(c, project, confirmation_id=elsewhere.decision_id)

        # And a spent one is not authority.
        spent = confirmation(c, project)
        spent.decision_state = DecisionState.CONSUMED
        c.store.put_decision(spent)
        with pytest.raises(CapabilityDenied, match=r"row 5-1"):
            Controller.open_run(c, project, confirmation_id=spent.decision_id)
        assert c.store.list_runs(project) == []


def test_run_start_consumes_its_confirmation(h):
    """The act is spent by the transition it discharged (`HD-INV-3`).

    And the `run.allocated` event is what spent it: a nonce that survived
    would allocate a second run on one human's answer.
    """
    project = provisioned(h, "gr31-t8b")
    with h.controller(with_repo=True) as c:
        approval = confirmation(c, project)
        run = Controller.open_run(c, project, confirmation_id=approval.decision_id)
        assert (c.store.get_decision(approval.decision_id).decision_state
                is DecisionState.CONSUMED)

        with pytest.raises(CapabilityDenied, match=r"row 5-1"):
            Controller.open_run(c, project, confirmation_id=approval.decision_id)
        assert [r.run_id for r in c.store.list_runs(project)] == [run]
        c.store.verify_chain(project)


def test_first_invocation_refuses_without_confirmation(h):
    """Row 7.2-1's `WHEN` branch. The subject is the `RUN`."""
    project = provisioned(h, "gr31-t8c")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        c.register_provider(c.provider)
        with pytest.raises(CapabilityDenied, match=r"row 7\.2-1 is CONFIRM under SUPERVISED"):
            c.create_invocation(run, prompt=b"do the work")
        assert c.store.list_invocations(run) == []

        # An approval over the project is not an approval over this run.
        wrong_subject = confirmation(c, project)
        with pytest.raises(CapabilityDenied, match=r"row 7\.2-1"):
            c.create_invocation(run, prompt=b"do the work",
                                confirmation_id=wrong_subject.decision_id)
        assert c.store.list_invocations(run) == []


# --- T9: the `WHEN` is honoured, not over-applied ---------------------------


def test_second_invocation_needs_no_confirmation(h):
    """Row 7.2-1 confirms the *first* invocation of a run, and only it.

    Demanding a confirmation again would deny a second invocation the frozen
    row declares `AUTO` — over-applying a `CONFIRM` is as much a departure
    from the matrix as failing to apply it.
    """
    project = provisioned(h, "gr31-t9a")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        c.register_provider(c.provider)
        first_confirmation = confirmation(
            c, project, subject_kind=DecisionSubjectKind.RUN, subject_id=run,
            scope=DecisionScope.RUN)
        first = c.create_invocation(run, prompt=b"first",
                                    confirmation_id=first_confirmation.decision_id)
        assert (c.store.get_decision(first_confirmation.decision_id).decision_state
                is DecisionState.CONSUMED)

        second = c.create_invocation(run, prompt=b"second")
        assert second.invocation_id != first.invocation_id
        assert len(c.store.list_invocations(run)) == 2
        c.store.verify_chain(project)


def test_a_commit_confirmation_superseded_by_a_snapshot_is_stale(h):
    """`HD-INV-4` over row 7.4-4, and the ordering it imposes on a driver.

    `COMMIT_INTENT` is in `SNAPSHOT_BOUND_SUBJECTS` and `APPROVE` is in
    `SNAPSHOT_BOUND_KINDS`, so a commit confirmation speaks about a reality.
    An observation that finds the workspace has moved supersedes it, and the
    human's answer to "commit this against this reality" is no longer an
    answer about the reality in front of us.

    So a driver must record the confirmation immediately before authorizing,
    with no observation in between. This is that constraint, asserted.
    """
    project = provisioned(h, "gr31-t9b")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        intent = c.propose_commit(run, path="x.txt", content="x\n", message="x")
        approval = confirmation(c, project,
                                subject_kind=DecisionSubjectKind.COMMIT_INTENT,
                                subject_id=intent.intent_id)
        assert approval.snapshot_bound is True

        # Reality moves, and is observed.
        (h.repo_dir / "unrelated.txt").write_text("moved\n", encoding="utf-8")
        git(h.repo_dir, "add", "-A")
        git(h.repo_dir, "commit", "-q", "-m", "someone else's commit")
        c.take_snapshot(project)
        assert (c.store.get_decision(approval.decision_id).decision_state
                is DecisionState.STALE)

        with pytest.raises(CapabilityDenied, match=r"row 7\.4-4"):
            c.authorize_commit(intent.intent_id, confirmation_id=approval.decision_id)
        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.PROPOSED)


# --- T10: row 7.4-4 ---------------------------------------------------------


def test_commit_authorize_refuses_without_confirmation(h):
    project = provisioned(h, "gr31-t10a")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        intent = c.propose_commit(run, path="y.txt", content="y\n", message="y")
        with pytest.raises(CapabilityDenied, match=r"row 7\.4-4 is CONFIRM under SUPERVISED"):
            c.authorize_commit(intent.intent_id)
        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.PROPOSED)

        # An approval over a different intent discharges nothing here.
        other = c.propose_commit(run, path="z.txt", content="z\n", message="z")
        misdirected = confirmation(c, project,
                                   subject_kind=DecisionSubjectKind.COMMIT_INTENT,
                                   subject_id=other.intent_id)
        with pytest.raises(CapabilityDenied, match=r"row 7\.4-4"):
            c.authorize_commit(intent.intent_id, confirmation_id=misdirected.decision_id)


def test_commit_authorize_consumes_its_confirmation_and_refuses_replay(h):
    project = provisioned(h, "gr31-t10b")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        intent = c.propose_commit(run, path="w.txt", content="w\n", message="w")
        approval = confirmation(c, project,
                                subject_kind=DecisionSubjectKind.COMMIT_INTENT,
                                subject_id=intent.intent_id)
        c.authorize_commit(intent.intent_id, confirmation_id=approval.decision_id)

        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.AUTHORIZED)
        assert (c.store.get_decision(approval.decision_id).decision_state
                is DecisionState.CONSUMED)

        # The runtime performed the write; the human's act is the decision the
        # event cites, not the `authorized_by` field (`AX-16`).
        assert c.store.get_commit_intent(intent.intent_id).authorized_by.actor_kind.value == "RUNTIME"

        replay = c.propose_commit(run, path="v.txt", content="v\n", message="v")
        with pytest.raises(CapabilityDenied, match=r"row 7\.4-4"):
            c.authorize_commit(replay.intent_id, confirmation_id=approval.decision_id)
        c.store.verify_chain(project)


# --- the `AUTONOMOUS` column: these rows ask for nothing --------------------


def test_autonomous_rows_require_no_confirmation(h):
    """All three cells read `AUTO` under `AUTONOMOUS`.

    Enforcing the `SUPERVISED` column here would be this runtime inventing a
    confirmation the frozen matrix does not declare, which is the mirror image
    of the gap `G1`-`G3` name.
    """
    project = provisioned(h, "gr31-auto")
    with h.controller(with_repo=True) as c:
        force_governance_mode(c.store, project, GovernanceMode.AUTONOMOUS)
        run = Controller.open_run(c, project)
        from gr06_support import document
        contract = c.author_contract(document(
            project, c.store.get_run(run).stage_id,
            capability_request=["fs.read", "fs.write", "commit.propose"]))
        c.activate_contract(contract.contract_id, run)
        c.register_provider(c.provider)
        c.create_invocation(run, prompt=b"autonomous")
        intent = c.propose_commit(run, path="a.txt", content="a\n", message="a")
        c.authorize_commit(intent.intent_id)
        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.AUTHORIZED)


# --- T13: the whole GR-33 sequence, on a fake provider ----------------------


def test_gr31_happy_path(h):
    """create → provision → author → activate → run → invoke → commit.

    The sequence GR-33 will drive against a live provider, driven here against
    `FakeProvider` so the authority surface is proved before any network
    exists. Every confirmed step carries a real recorded `HumanDecision`, and
    every one of them is consumed by the transition it discharged.

    Nothing here writes a project row directly. That is the point: this is the
    first end-to-end path through the runtime that provisions itself the way
    the design says a project is provisioned.
    """
    project = supervised_project(h, slug="gr31-t13")
    with h.controller(with_repo=True) as c:
        ceiling, ceiling_decision = set_ceiling(c, project)
        budget, budget_decision = grant_budget(c, project)
        assert ceiling == PILOT_CEILING and budget == PILOT_BUDGET

        run_approval = confirmation(c, project)
        run = Controller.open_run(c, project, confirmation_id=run_approval.decision_id)

        from gr06_support import document
        contract = c.author_contract(document(
            project, c.store.get_run(run).stage_id,
            capability_request=["fs.read", "fs.write", "commit.propose"]))
        contract_approval = confirmation(c, project,
                                         subject_kind=DecisionSubjectKind.CONTRACT,
                                         subject_id=contract.contract_id)
        activation = c.activate_contract(contract.contract_id, run,
                                         approval_id=contract_approval.decision_id)
        assert "commit.propose" in activation.granted_capabilities

        c.register_provider(c.provider)
        invoke_approval = confirmation(c, project,
                                       subject_kind=DecisionSubjectKind.RUN,
                                       subject_id=run, scope=DecisionScope.RUN)
        invocation = c.create_invocation(run, prompt=b"implement the change",
                                         confirmation_id=invoke_approval.decision_id)
        assert invocation.run_id == run

        intent = c.propose_commit(run, path="pilot.txt", content="pilot\n",
                                  message="Add pilot")
        commit_approval = confirmation(c, project,
                                       subject_kind=DecisionSubjectKind.COMMIT_INTENT,
                                       subject_id=intent.intent_id)
        c.authorize_commit(intent.intent_id, confirmation_id=commit_approval.decision_id)
        receipt = c.apply_commit(intent.intent_id)

        assert receipt.verification is Verification.MATCHED
        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.APPLIED)

        # Every human act on the path is spent, and none is replayable.
        for decision in (ceiling_decision, budget_decision, run_approval,
                         contract_approval, invoke_approval, commit_approval):
            assert (c.store.get_decision(decision.decision_id).decision_state
                    is DecisionState.CONSUMED), decision.decision_id
        c.store.verify_chain(project)


# --- GR31-R01: the authorized act and its confirmation are one act ----------


def _explode(message):
    """A failure injected between two durable steps."""

    def boom(*args, **kwargs):
        raise RuntimeError(message)

    return boom


def test_run_start_is_atomic_with_its_confirmation(h, monkeypatch):
    """`GR31-R01`, row 5-1. The run and the spent confirmation are one write.

    The confirmation is what authorizes *this* allocation, and its subject is
    the `PROJECT` because the run does not exist yet. A `run.allocated` that
    outlived a failure to spend the decision would leave that project-scoped
    answer `VALID` and able to authorize a second, different run — one human
    act, two allocations, which is exactly what `HD-INV-3` forbids.

    So the failure is injected where the finding puts it: after the run is
    written, before the consumption completes. Nothing may survive it.
    """
    project = provisioned(h, "gr31-r01-run")
    with h.controller(with_repo=True) as c:
        approval = confirmation(c, project)
        before = c.store.get_project(project).event_seq

        monkeypatch.setattr(c, "_consume_decision",
                            _explode("crash after the run.allocated write"))
        with pytest.raises(RuntimeError, match="crash after the run.allocated write"):
            Controller.open_run(c, project, confirmation_id=approval.decision_id)
        monkeypatch.undo()

        # No partially durable run, and no authority event claiming one.
        assert c.store.list_runs(project) == []
        assert not [e for e in c.store.list_events(project)
                    if e.event_type == "run.allocated"]
        assert c.store.get_project(project).event_seq == before
        c.store.verify_chain(project)

        # The act did not happen, so the human's answer is unspent — still
        # `VALID`, still this project's, still good for the one allocation it
        # was recorded for.
        assert (c.store.get_decision(approval.decision_id).decision_state
                is DecisionState.VALID)

        run = Controller.open_run(c, project, confirmation_id=approval.decision_id)
        assert [r.run_id for r in c.store.list_runs(project)] == [run]
        assert (c.store.get_decision(approval.decision_id).decision_state
                is DecisionState.CONSUMED)

        # And they landed together: the consumption cites the allocation it
        # discharged and is the very next event on the chain.
        events = c.store.list_events(project)
        allocated = next(e for e in events if e.event_type == "run.allocated")
        consumed = next(e for e in events if e.event_type == "decision.state_derived"
                        and e.causal_parent == allocated.event_id)
        assert consumed.seq == allocated.seq + 1
        c.store.verify_chain(project)


def test_commit_authorize_is_atomic_with_its_confirmation(h, monkeypatch):
    """`GR31-R01`, row 7.4-4. `AUTHORIZED` and the spent confirmation together.

    An `AUTHORIZED` intent is the runtime's standing permission to mutate the
    repository (`mark_applying` accepts nothing else). Leaving one durable
    while the human act that authorized it is still `VALID` would put an
    authorized commit and an unspent approval on disk at the same time: the
    audit would show a commit authorized by a decision nothing ever
    discharged.
    """
    project = provisioned(h, "gr31-r01-commit")
    with h.controller(with_repo=True) as c:
        run = granted_run(c, project)
        intent = c.propose_commit(run, path="r01.txt", content="r01\n", message="r01")
        approval = confirmation(c, project,
                                subject_kind=DecisionSubjectKind.COMMIT_INTENT,
                                subject_id=intent.intent_id)
        before = c.store.get_project(project).event_seq

        monkeypatch.setattr(c, "_consume_decision",
                            _explode("crash after the commit_intent.authorized write"))
        with pytest.raises(RuntimeError,
                           match="crash after the commit_intent.authorized write"):
            c.authorize_commit(intent.intent_id, confirmation_id=approval.decision_id)
        monkeypatch.undo()

        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.PROPOSED)
        assert not [e for e in c.store.list_events(project)
                    if e.event_type == "commit_intent.authorized"]
        assert c.store.get_project(project).event_seq == before
        c.store.verify_chain(project)

        assert (c.store.get_decision(approval.decision_id).decision_state
                is DecisionState.VALID)

        # No snapshot intervened, so the same confirmation still speaks about
        # the reality in front of us, and the retry commits both halves.
        c.authorize_commit(intent.intent_id, confirmation_id=approval.decision_id)
        assert (c.store.get_commit_intent(intent.intent_id).status
                is CommitIntentStatus.AUTHORIZED)
        assert (c.store.get_decision(approval.decision_id).decision_state
                is DecisionState.CONSUMED)

        events = c.store.list_events(project)
        authorized = next(e for e in events
                          if e.event_type == "commit_intent.authorized")
        consumed = next(e for e in events if e.event_type == "decision.state_derived"
                        and e.causal_parent == authorized.event_id)
        assert consumed.seq == authorized.seq + 1
        c.store.verify_chain(project)
