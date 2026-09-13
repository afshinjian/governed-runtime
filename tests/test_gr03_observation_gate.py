"""GR-03 — a failed observation bars new effects, and never becomes reality.

FIX-1: a non-`COMPLETE` observation must not permit new external effects.
       "Cannot observe" blocks dispatch and commit application the same way a
       suspension does.
FIX-2: `snapshot_current` advances only on a `COMPLETE` snapshot. A failed
       observation is recorded as evidence but never becomes current reality.

Design basis: `RS-INV-1` (absence of observation is not observation of
absence), transition-matrix §0.1 (the axis-3 gate, under which snapshots stay
allowed whatever else stops).

The distinction this file draws is between *failing* to observe and *not having
observed*. A project nobody has looked at yet is not gated: the runtime has
made no failed claim about it. A project whose last look failed is gated,
because it has one.
"""

from __future__ import annotations

import shutil

import pytest

from gruntime.errors import PolicyDenied
from gruntime.models import Completeness, SuspensionState

from gr03_support import project_with_repo, snapshot, write


def _blind(h, project_id) -> str:
    """Make the next observation fail, and take it. Returns its snapshot id."""
    shutil.rmtree(h.repo_dir)
    snapshot_id = snapshot(h, project_id)
    with h.store() as store:
        assert store.get_snapshot(snapshot_id).completeness is Completeness.FAILED
    return snapshot_id


def _authorized_intent(h, project_id, run_id) -> str:
    with h.controller(with_repo=True) as controller:
        intent = controller.propose_commit(
            run_id, path="feature.txt", content="governed\n", message="governed"
        )
        controller.authorize_commit(intent.intent_id)
    return intent.intent_id


# --- FIX-1: the gate --------------------------------------------------------


def test_a_failed_observation_bars_new_invocations(h):
    project_id = project_with_repo(h, slug="blind-invoke")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
    snapshot(h, project_id)

    _blind(h, project_id)

    with h.controller(with_repo=True) as controller:
        with pytest.raises(PolicyDenied) as refusal:
            controller.create_invocation(run_id, prompt=b"work blind")
    assert "FAILED" in str(refusal.value)


def test_a_failed_observation_bars_proposing_and_applying_commits(h):
    project_id = project_with_repo(h, slug="blind-commit")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
    snapshot(h, project_id)
    intent_id = _authorized_intent(h, project_id, run_id)

    _blind(h, project_id)

    with h.controller(with_repo=True) as controller:
        with pytest.raises(PolicyDenied):
            controller.propose_commit(
                run_id, path="another.txt", content="x\n", message="x"
            )
        with pytest.raises(PolicyDenied):
            controller.apply_commit(intent_id)


def test_a_single_failed_observation_does_not_suspend_the_project(h):
    """It is a fact about one look, not a finding about the workspace.

    Suspension needs a human to clear it; this must not, or a flaky mount
    would cost a round-trip every time.
    """
    project_id = project_with_repo(h, slug="no-suspend")
    snapshot(h, project_id)
    _blind(h, project_id)

    with h.store() as store:
        project = store.get_project(project_id)
        assert project.suspension is SuspensionState.NONE
        assert project.suspension_ref is None
        assert store.list_escalations(project_id) == []
        store.verify_chain(project_id)


def test_observation_itself_is_never_gated(h):
    """The gate must not be able to lock itself shut.

    Only a later `COMPLETE` snapshot lifts it, so gating snapshots would make
    a single transient failure permanent.
    """
    project_id = project_with_repo(h, slug="observation-open")
    snapshot(h, project_id)
    _blind(h, project_id)

    with h.controller(with_repo=True) as controller:
        again = controller.take_snapshot(project_id)
    with h.store() as store:
        assert store.get_snapshot(again).completeness is Completeness.FAILED


def test_a_later_complete_observation_lifts_the_gate(h):
    project_id = project_with_repo(h, slug="recovers")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
    snapshot(h, project_id)
    _blind(h, project_id)

    h.init_repo()
    snapshot(h, project_id)

    with h.controller(with_repo=True) as controller:
        invocation = controller.create_invocation(run_id, prompt=b"work again")
    assert invocation.invocation_id
    with h.store() as store:
        assert store.get_project(project_id).suspension is SuspensionState.NONE


def test_a_project_that_has_never_been_observed_is_not_gated(h):
    """Absence of an observation is not a failed one.

    Requiring a snapshot before any effect is a different rule — a `SNAP`
    precondition — and GR-03 does not implement it. Conflating the two here
    would bar the first action of every project.
    """
    project_id = project_with_repo(h, slug="never-looked")
    with h.store() as store:
        assert store.latest_snapshot(project_id) is None

    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
        assert controller.create_invocation(run_id, prompt=b"first work")


def test_the_gate_reads_the_latest_observation_not_the_current_one(h):
    """The two diverge exactly when it matters.

    `snapshot_current` is the newest `COMPLETE` snapshot (FIX-2), so a gate
    reading it could never see a failure. The gate reads the latest snapshot
    of any completeness.
    """
    project_id = project_with_repo(h, slug="latest-vs-current")
    complete = snapshot(h, project_id)
    failed = _blind(h, project_id)

    with h.store() as store:
        assert store.get_project(project_id).snapshot_current == complete
        assert store.latest_snapshot(project_id).snapshot_id == failed
        assert store.newest_complete_snapshot(project_id).snapshot_id == complete


# --- FIX-2: what becomes current -------------------------------------------


def test_snapshot_current_does_not_advance_to_a_failed_observation(h):
    project_id = project_with_repo(h, slug="current-holds")
    complete = snapshot(h, project_id)
    _blind(h, project_id)

    with h.store() as store:
        assert store.get_project(project_id).snapshot_current == complete


def test_a_failed_observation_is_still_recorded_as_evidence(h):
    """Recorded, chained and auditable — just not authoritative."""
    project_id = project_with_repo(h, slug="recorded")
    snapshot(h, project_id)
    failed = _blind(h, project_id)

    with h.store() as store:
        record = store.get_snapshot(failed)
        assert record.completeness is Completeness.FAILED
        assert record.snapshot_hash
        assert failed in {s.snapshot_id for s in store.list_snapshots(project_id)}
        taken = [
            event
            for event in store.list_events(project_id)
            if event.event_type == "snapshot.taken"
        ]
        assert len(taken) == 2
        store.verify_chain(project_id)


def test_a_recovered_observation_becomes_current_again(h):
    project_id = project_with_repo(h, slug="current-resumes")
    first = snapshot(h, project_id)
    _blind(h, project_id)

    h.init_repo()
    write(h, "README.md", "base\n")
    recovered = snapshot(h, project_id)

    with h.store() as store:
        assert store.get_project(project_id).snapshot_current == recovered
        assert recovered != first
