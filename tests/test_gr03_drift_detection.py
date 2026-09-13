"""GR-03 — a dirty file outside the allowed paths is drift, not noise.

Acceptance criterion:
    A dirty file outside allowed paths is detected as drift, not ignored.

Design basis: domain-model §9.B.1 (`REALITY_DRIFT`), §9.D
(`drift_summary.unattributed > 0`), transition-matrix §4
(`NONE → SUSPENDED_BY_DRIFT`) and §0.1 (the axis-3 gate: snapshots stay
allowed under every suspension, everything else stops).
"""

from __future__ import annotations

import pytest

from gruntime.errors import PolicyDenied
from gruntime.models import (
    Completeness,
    EscalationTrigger,
    SnapshotTrigger,
    SuspensionState,
)
from gruntime.repository import derive_drift, unattributed_paths

from gr03_support import commit_in_checkout, git, project_with_repo, snapshot, write


def _drift_of(h, snapshot_id):
    with h.store() as store:
        return store.get_snapshot(snapshot_id).drift_summary


def _suspension(h, project_id):
    with h.store() as store:
        return store.get_project(project_id).suspension


def _declare(h, project_id, path: str) -> str:
    """Have the runtime declare it is changing `path`, as a real intent does."""
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
        intent = controller.propose_commit(
            run_id, path=path, content="governed\n", message="governed change"
        )
        controller.authorize_commit(intent.intent_id)
    return run_id


# --- the derivation ---------------------------------------------------------


def test_drift_counts_additions_removals_and_modifications():
    before = {"kept.txt": "sha256:aa", "gone.txt": "sha256:bb"}
    after = {"kept.txt": "sha256:zz", "new.txt": "sha256:cc"}
    drift = derive_drift(before, after)
    assert (drift.added, drift.removed, drift.modified) == (1, 1, 1)
    assert drift.changed == 3
    assert drift.unattributed == 3


def test_a_declared_path_is_attributed_and_an_undeclared_one_is_not():
    before = {"a.txt": "sha256:aa", "b.txt": "sha256:bb"}
    after = {"a.txt": "sha256:zz", "b.txt": "sha256:yy"}
    drift = derive_drift(before, after, attributed=("a.txt",))
    assert drift.modified == 2
    assert drift.unattributed == 1
    assert unattributed_paths(before, after, attributed=("a.txt",)) == ("b.txt",)


def test_a_protected_path_is_never_attributable():
    """Declaring a protected path does not make a change there the runtime's.

    The runtime cannot mutate repository metadata, so a change there was
    somebody else's however the declaration reads.
    """
    before = {".git/config": "sha256:aa"}
    after = {".git/config": "sha256:bb"}
    assert unattributed_paths(before, after, attributed=(".git/**",)) == (".git/config",)


def test_an_unchanged_index_produces_no_drift():
    index = {"a.txt": "sha256:aa"}
    drift = derive_drift(index, dict(index))
    assert (drift.added, drift.removed, drift.modified, drift.unattributed) == (0, 0, 0, 0)


# --- against a real repository ---------------------------------------------


def test_the_first_snapshot_of_a_project_has_nothing_to_drift_against(h):
    project_id = project_with_repo(h)
    first = snapshot(h, project_id)
    with h.store() as store:
        record = store.get_snapshot(first)
    assert record.drift_vs is None
    assert record.drift_summary is None
    assert _suspension(h, project_id) is SuspensionState.NONE


def test_a_dirty_tracked_file_outside_the_allowed_paths_is_drift(h):
    project_id = project_with_repo(h)
    first = snapshot(h, project_id)

    # A human edits a tracked file and does not commit it.
    write(h, "README.md", "somebody edited this\n")

    second = snapshot(h, project_id, trigger=SnapshotTrigger.DRIFT_CHECK)
    drift = _drift_of(h, second)
    assert drift is not None, "the snapshot did not compare itself to the last one"
    assert drift.modified == 1
    assert drift.unattributed == 1, "a dirty tracked file was ignored"

    with h.store() as store:
        record = store.get_snapshot(second)
        assert record.drift_vs == first
        triggers = [e.trigger for e in store.list_escalations(project_id)]
        assert EscalationTrigger.REALITY_DRIFT in triggers
        store.verify_chain(project_id)

    assert _suspension(h, project_id) is SuspensionState.SUSPENDED_BY_DRIFT


def test_a_committed_change_made_outside_the_runtime_is_drift(h):
    project_id = project_with_repo(h)
    snapshot(h, project_id)
    commit_in_checkout(h, "README.md", "committed behind the runtime's back\n")
    drift = _drift_of(h, snapshot(h, project_id))
    assert drift.unattributed == 1
    assert _suspension(h, project_id) is SuspensionState.SUSPENDED_BY_DRIFT


def test_a_change_inside_a_declared_path_is_attributed(h):
    """Drift is about *unattributed* change, not about any change at all."""
    project_id = project_with_repo(h)
    snapshot(h, project_id)
    _declare(h, project_id, "README.md")

    write(h, "README.md", "the runtime said it was changing this\n")

    drift = _drift_of(h, snapshot(h, project_id))
    assert drift.modified == 1
    assert drift.unattributed == 0
    assert _suspension(h, project_id) is SuspensionState.NONE


def test_untracked_churn_produces_no_drift_at_all(h):
    """The same exclusion the fingerprint makes, seen from the drift side."""
    project_id = project_with_repo(h)
    snapshot(h, project_id)
    write(h, "build/artifact.bin", "compiled\n")
    write(h, "pytest-report.xml", "<report/>\n")
    git(h.repo_dir, "tag", "release-1")

    drift = _drift_of(h, snapshot(h, project_id))
    assert drift.changed == 0
    assert drift.unattributed == 0
    assert _suspension(h, project_id) is SuspensionState.NONE


def test_drift_suspension_bars_new_effects_but_never_observation(h):
    """Transition-matrix §0.1: suspension is a hard gate, snapshots excepted."""
    project_id = project_with_repo(h)
    snapshot(h, project_id)
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
        # Authorized while the workspace was still trustworthy: the intent
        # survives the suspension, its application does not.
        intent = controller.propose_commit(
            run_id, path="pending.txt", content="pending\n", message="pending"
        )
        controller.authorize_commit(intent.intent_id)
        authorized_before_the_drift = intent.intent_id

    write(h, "README.md", "drifted\n")
    snapshot(h, project_id, trigger=SnapshotTrigger.DRIFT_CHECK)
    assert _suspension(h, project_id) is SuspensionState.SUSPENDED_BY_DRIFT

    with h.controller(with_repo=True) as controller:
        with pytest.raises(PolicyDenied):
            controller.create_invocation(run_id, prompt=b"work anyway")
        with pytest.raises(PolicyDenied):
            controller.propose_commit(
                run_id, path="feature.txt", content="x\n", message="x"
            )
        with pytest.raises(PolicyDenied):
            controller.apply_commit(authorized_before_the_drift)
        # Observation is never gated: it is how the suspension is ever lifted.
        further = controller.take_snapshot(
            project_id, trigger=SnapshotTrigger.DRIFT_CHECK
        )
    with h.store() as store:
        assert store.get_snapshot(further).completeness is Completeness.COMPLETE
        store.verify_chain(project_id)


def test_a_failed_observation_is_neither_a_comparand_nor_a_baseline(h):
    """`RS-INV-1`: an unreadable repository is not an emptied one.

    Comparing *to* a failed observation reports the whole workspace as having
    vanished; comparing *from* one reports it as having appeared. Both would
    suspend the project for a transient disk fault, so drift is derived only
    between two `COMPLETE` observations.
    """
    import shutil

    project_id = project_with_repo(h)
    baseline = snapshot(h, project_id)

    shutil.rmtree(h.repo_dir)
    failed = snapshot(h, project_id)
    with h.store() as store:
        record = store.get_snapshot(failed)
    assert record.completeness is Completeness.FAILED
    assert record.drift_summary is None, "a failed observation was compared"
    assert _suspension(h, project_id) is SuspensionState.NONE

    # The same content comes back. The baseline is the last snapshot that
    # actually observed something, so the comparison is meaningful again.
    h.init_repo()
    recovered = snapshot(h, project_id)
    with h.store() as store:
        record = store.get_snapshot(recovered)
    assert record.completeness is Completeness.COMPLETE
    assert record.drift_vs == baseline, "a failed snapshot was used as a baseline"
    assert record.drift_summary.changed == 0
    assert _suspension(h, project_id) is SuspensionState.NONE


def test_suspension_does_not_overwrite_the_lifecycle(h):
    """`G-8`/`O-3`: axis 3 is read alongside axis 1, never instead of it."""
    project_id = project_with_repo(h)
    with h.store() as store:
        lifecycle = store.get_project(project_id).lifecycle
    snapshot(h, project_id)
    write(h, "README.md", "drifted\n")
    snapshot(h, project_id)
    with h.store() as store:
        project = store.get_project(project_id)
    assert project.lifecycle is lifecycle
    assert project.suspension is SuspensionState.SUSPENDED_BY_DRIFT
    assert project.suspension_ref is not None


def test_repeated_drift_snapshots_do_not_re_suspend(h):
    """The axis-3 write is a transition, so it happens once per change."""
    project_id = project_with_repo(h)
    snapshot(h, project_id)
    write(h, "README.md", "drifted\n")
    snapshot(h, project_id)
    with h.store() as store:
        events_before = len(store.list_events(project_id))
    snapshot(h, project_id)
    with h.store() as store:
        suspensions = [
            event
            for event in store.list_events(project_id)
            if event.event_type == "suspension.set"
        ]
        assert len(suspensions) == 1
        assert len(store.list_events(project_id)) > events_before  # the snapshot itself
        store.verify_chain(project_id)
