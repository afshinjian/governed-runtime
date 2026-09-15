"""GR-03 — an approval bound to snapshot A is stale against snapshot B.

Acceptance criterion:
    An approval bound to snapshot A is STALE against snapshot B.

Design basis: domain-model §9.A (`HD-INV-1`..`HD-INV-4`), transition-matrix
§7.5 (`VALID → STALE`) and §9.3 (citing a decision whose `decision_state` is
not `VALID`), evidence-model §5.2.

The negative case matters as much as the positive one and is tested here too:
re-observing an *unchanged* repository must leave an approval alone. That only
works because the fingerprint excludes untracked and ignored files — if it did
not, one test run would invalidate every approval in the project.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from gruntime.decision import (
    derive_decision_state,
    is_authority,
    is_snapshot_bound,
    refuse_unless_authority,
)
from gruntime.errors import IntegrityViolation
from gruntime.models import (
    ActorKind,
    ActorRef,
    AuthMethod,
    DecisionKind,
    DecisionState,
    DecisionSubjectKind,
    SnapshotTrigger,
)

from gr03_support import commit_in_checkout, project_with_repo, snapshot, write

HUMAN = ActorRef(
    actor_kind=ActorKind.HUMAN,
    actor_id="reviewer@example.invalid",
    auth_method=AuthMethod.SESSION,
    principal_key_id="key-1",
)


def _approve(controller, project_id, *, subject_kind=DecisionSubjectKind.RUN,
             subject_id="run-1", kind=DecisionKind.APPROVE):
    evidence = controller.store.store_artifact(
        b"the diff the human was shown", media_type="text/plain"
    )
    return controller.record_decision(
        project_id,
        decision_kind=kind,
        subject_kind=subject_kind,
        subject_id=subject_id,
        question="Apply this change?",
        chosen="yes",
        justification="reviewed the diff",
        decided_by=HUMAN,
        evidence_shown=[evidence],
        options_offered=["yes", "no"],
    )


def _state(h, decision_id) -> DecisionState:
    with h.store() as store:
        return store.get_decision(decision_id).decision_state


# --- the derivation ---------------------------------------------------------


@pytest.mark.parametrize(
    ("subject", "kind", "bound"),
    [
        (DecisionSubjectKind.RUN, DecisionKind.APPROVE, True),
        (DecisionSubjectKind.STAGE, DecisionKind.RESUME, True),
        (DecisionSubjectKind.COMMIT_INTENT, DecisionKind.APPROVE, True),
        (DecisionSubjectKind.FINDING, DecisionKind.WAIVE, True),
        (DecisionSubjectKind.PROJECT, DecisionKind.ACCEPT_RISK, True),
        (DecisionSubjectKind.PROJECT, DecisionKind.SET_MODE, False),
        (DecisionSubjectKind.PROJECT, DecisionKind.EXTEND_BUDGET, False),
        (DecisionSubjectKind.CAPABILITY, DecisionKind.GRANT_CAPABILITY, False),
    ],
)
def test_snapshot_binding_follows_the_subject_and_the_act(subject, kind, bound):
    assert is_snapshot_bound(subject, kind) is bound


def _decision(state=DecisionState.VALID, *, bound=True, expires_at=None):
    from gruntime.models import DecisionScope, HumanDecision

    return HumanDecision(
        decision_id="dec-1",
        project_id="prj-1",
        subject_kind=DecisionSubjectKind.RUN,
        subject_id="run-1",
        decision_kind=DecisionKind.APPROVE,
        question="?",
        chosen="yes",
        justification="because",
        scope=DecisionScope.RUN,
        decided_by=HUMAN,
        auth_method=AuthMethod.SESSION,
        decided_at=datetime.now(timezone.utc),
        nonce="n",
        snapshot_bound=bound,
        decision_state=state,
        expires_at=expires_at,
    )


def test_supersession_makes_a_bound_decision_stale():
    now = datetime.now(timezone.utc)
    assert derive_decision_state(
        _decision(), now=now, superseded_by_drift=True
    ) is DecisionState.STALE


def test_supersession_leaves_an_unbound_decision_alone():
    now = datetime.now(timezone.utc)
    assert derive_decision_state(
        _decision(bound=False), now=now, superseded_by_drift=True
    ) is DecisionState.VALID


@pytest.mark.parametrize(
    "state",
    [
        DecisionState.CONSUMED,
        DecisionState.EXPIRED,
        DecisionState.STALE,
        DecisionState.VOID,
    ],
    ids=str,
)
def test_every_terminal_state_is_terminal(state):
    """§7.5: a decision is never revived; renewal is a new decision."""
    now = datetime.now(timezone.utc)
    assert derive_decision_state(_decision(state), now=now) is state
    assert derive_decision_state(
        _decision(state), now=now, superseded_by_drift=False
    ) is state


def test_an_integrity_violation_outranks_everything():
    now = datetime.now(timezone.utc)
    assert derive_decision_state(
        _decision(), now=now, integrity_violated=True, consumed=True
    ) is DecisionState.VOID


def test_a_spent_nonce_consumes_the_decision():
    now = datetime.now(timezone.utc)
    assert derive_decision_state(
        _decision(), now=now, consumed=True
    ) is DecisionState.CONSUMED


def test_elapsed_time_expires_a_decision_with_no_snapshot_involved():
    now = datetime.now(timezone.utc)
    decision = _decision(expires_at=now - timedelta(seconds=1))
    assert derive_decision_state(decision, now=now) is DecisionState.EXPIRED


def test_only_valid_is_authority():
    for state in DecisionState:
        expected = state is DecisionState.VALID
        assert is_authority(_decision(state)) is expected
    with pytest.raises(IntegrityViolation):
        refuse_unless_authority(_decision(DecisionState.STALE), "applying a commit")
    with pytest.raises(IntegrityViolation):
        refuse_unless_authority(None, "applying a commit")
    assert refuse_unless_authority(_decision(), "applying").decision_id == "dec-1"


# --- through the controller -------------------------------------------------


def test_an_approval_is_bound_to_the_snapshot_the_human_was_shown(h):
    project_id = project_with_repo(h, slug="approval")
    first = snapshot(h, project_id)
    with h.controller(with_repo=True) as controller:
        decision = _approve(controller, project_id)

    assert decision.snapshot_bound is True
    assert decision.subject_snapshot_id == first
    assert _state(h, decision.decision_id) is DecisionState.VALID


def test_an_approval_bound_to_snapshot_a_is_stale_against_snapshot_b(h):
    project_id = project_with_repo(h, slug="stale")
    snapshot_a = snapshot(h, project_id)
    with h.controller(with_repo=True) as controller:
        decision = _approve(controller, project_id)
    assert decision.subject_snapshot_id == snapshot_a

    write(h, "README.md", "reality moved on\n")
    snapshot_b = snapshot(h, project_id, trigger=SnapshotTrigger.DRIFT_CHECK)
    assert snapshot_b != snapshot_a

    assert _state(h, decision.decision_id) is DecisionState.STALE
    with h.store() as store:
        assert not is_authority(store.get_decision(decision.decision_id))
        store.verify_chain(project_id)


def test_a_committed_change_stales_an_approval_too(h):
    project_id = project_with_repo(h, slug="stale-commit")
    snapshot(h, project_id)
    with h.controller(with_repo=True) as controller:
        decision = _approve(controller, project_id)
    commit_in_checkout(h, "README.md", "committed elsewhere\n")
    snapshot(h, project_id)
    assert _state(h, decision.decision_id) is DecisionState.STALE


def test_re_observing_an_unchanged_repository_leaves_an_approval_valid(h):
    """The rule the exclusion list exists for."""
    project_id = project_with_repo(h, slug="survives")
    snapshot(h, project_id)
    with h.controller(with_repo=True) as controller:
        decision = _approve(controller, project_id)

    # Everything a tool run leaves behind, and nothing a human changed.
    write(h, "pytest-report.xml", "<report/>\n")
    write(h, "build/out.o", "binary\n")
    for _ in range(3):
        snapshot(h, project_id, trigger=SnapshotTrigger.DRIFT_CHECK)

    assert _state(h, decision.decision_id) is DecisionState.VALID


def test_a_stale_approval_is_never_revived_by_a_later_clean_snapshot(h):
    project_id = project_with_repo(h, slug="never-revived")
    snapshot(h, project_id)
    with h.controller(with_repo=True) as controller:
        decision = _approve(controller, project_id)

    write(h, "README.md", "moved\n")
    snapshot(h, project_id)
    assert _state(h, decision.decision_id) is DecisionState.STALE

    # Put it back exactly as it was, and look again. Still stale: the human
    # approved artifacts that were superseded, and that fact does not unhappen.
    write(h, "README.md", "base\n")
    snapshot(h, project_id)
    assert _state(h, decision.decision_id) is DecisionState.STALE


def test_a_governance_decision_is_not_snapshot_bound_and_survives_drift(h):
    project_id = project_with_repo(h, slug="unbound")
    snapshot(h, project_id)
    with h.controller(with_repo=True) as controller:
        decision = _approve(
            controller,
            project_id,
            subject_kind=DecisionSubjectKind.PROJECT,
            subject_id=project_id,
            kind=DecisionKind.SET_MODE,
        )
    assert decision.snapshot_bound is False
    assert decision.subject_snapshot_id is None

    write(h, "README.md", "moved\n")
    snapshot(h, project_id)
    assert _state(h, decision.decision_id) is DecisionState.VALID


def test_an_unreadable_workspace_does_not_stale_an_approval(h):
    """`RS-INV-1`: a snapshot that failed supersedes nothing.

    Staling an approval because the disk was briefly unreachable would make
    every transient fault cost a human round-trip.
    """
    import shutil

    project_id = project_with_repo(h, slug="failed-observation")
    snapshot(h, project_id)
    with h.controller(with_repo=True) as controller:
        decision = _approve(controller, project_id)

    shutil.rmtree(h.repo_dir)
    snapshot(h, project_id)
    assert _state(h, decision.decision_id) is DecisionState.VALID


def test_the_staling_is_audited(h):
    project_id = project_with_repo(h, slug="audited")
    snapshot(h, project_id)
    with h.controller(with_repo=True) as controller:
        decision = _approve(controller, project_id)
    write(h, "README.md", "moved\n")
    snapshot(h, project_id)

    with h.store() as store:
        derived = [
            event
            for event in store.list_events(project_id)
            if event.event_type == "decision.state_derived"
            # Genesis derives one of its own — the creation approval reaching
            # `CONSUMED` — over a different subject.
            and event.subject["decision_id"] == decision.decision_id
        ]
        assert len(derived) == 1
        store.verify_chain(project_id)


# --- HD-INV-1 and HD-INV-2 --------------------------------------------------


def test_a_runtime_cannot_manufacture_authority(h):
    project_id = project_with_repo(h, slug="hd-inv-1")
    snapshot(h, project_id)
    robot = ActorRef(
        actor_kind=ActorKind.RUNTIME,
        actor_id="gruntime.controller",
        auth_method=AuthMethod.SESSION,
    )
    with h.controller(with_repo=True) as controller:
        evidence = controller.store.store_artifact(b"x", media_type="text/plain")
        with pytest.raises(IntegrityViolation):
            controller.record_decision(
                project_id,
                decision_kind=DecisionKind.APPROVE,
                subject_kind=DecisionSubjectKind.RUN,
                subject_id="run-1",
                question="?",
                chosen="yes",
                justification="because",
                decided_by=robot,
                evidence_shown=[evidence],
            )


@pytest.mark.parametrize("method", [AuthMethod.NONE, AuthMethod.DELEGATED])
def test_unauthenticated_authority_is_refused(h, method):
    project_id = project_with_repo(h, slug="unauthenticated")
    snapshot(h, project_id)
    actor = ActorRef(
        actor_kind=ActorKind.HUMAN, actor_id="someone", auth_method=method
    )
    with h.controller(with_repo=True) as controller:
        evidence = controller.store.store_artifact(b"x", media_type="text/plain")
        with pytest.raises(IntegrityViolation):
            controller.record_decision(
                project_id,
                decision_kind=DecisionKind.APPROVE,
                subject_kind=DecisionSubjectKind.RUN,
                subject_id="run-1",
                question="?",
                chosen="yes",
                justification="because",
                decided_by=actor,
                evidence_shown=[evidence],
            )


def test_an_uninformed_approval_is_refused(h):
    """`HD-INV-2`: empty `evidence_shown` discharges nothing."""
    project_id = project_with_repo(h, slug="uninformed")
    snapshot(h, project_id)
    with h.controller(with_repo=True) as controller:
        with pytest.raises(IntegrityViolation):
            controller.record_decision(
                project_id,
                decision_kind=DecisionKind.APPROVE,
                subject_kind=DecisionSubjectKind.RUN,
                subject_id="run-1",
                question="?",
                chosen="yes",
                justification="because",
                decided_by=HUMAN,
                evidence_shown=[],
            )
