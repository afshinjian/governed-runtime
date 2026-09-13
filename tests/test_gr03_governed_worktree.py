"""GR-03 — governed mutation lands in a dedicated worktree, never the user's
checkout.

Acceptance criterion:
    Governed mutation happens in a dedicated worktree, never the user's
    checkout.

Design basis: `gruntime/worktree.py`, authority-matrix §2.4 (`fs.write` "never
writes the live tree"), §2.6 (`commit.apply`), domain-model §9.D.
"""

from __future__ import annotations

import pytest

from gruntime.errors import IntegrityViolation
from gruntime.worktree import (
    WorktreePlacement,
    ensure_worktree,
    governed_branch,
    worktree_root,
)

from gr03_support import git, project_with_repo, snapshot_hash, write


def _apply(h, project_id, run_id, *, path="feature.txt", content="governed\n"):
    with h.controller(with_repo=True) as controller:
        intent = controller.propose_commit(
            run_id, path=path, content=content, message="governed change"
        )
        controller.authorize_commit(intent.intent_id)
        receipt = controller.apply_commit(intent.intent_id)
    return intent, receipt


def _checkout_state(h) -> dict:
    return {
        "head": git(h.repo_dir, "rev-parse", "HEAD"),
        "branch": git(h.repo_dir, "rev-parse", "--abbrev-ref", "HEAD"),
        "status": git(h.repo_dir, "status", "--porcelain"),
    }


# --- placement --------------------------------------------------------------


def test_a_worktree_at_the_workspace_is_refused(tmp_path):
    workspace = tmp_path / "checkout"
    workspace.mkdir()
    with pytest.raises(IntegrityViolation):
        WorktreePlacement(
            path=workspace, branch="gruntime/x", workspace_root=workspace
        ).verify()


def test_a_worktree_inside_the_workspace_is_refused(tmp_path):
    """Nested, it would read as untracked churn in every later snapshot."""
    workspace = tmp_path / "checkout"
    (workspace / ".gruntime").mkdir(parents=True)
    with pytest.raises(IntegrityViolation):
        WorktreePlacement(
            path=workspace / ".gruntime" / "wt",
            branch="gruntime/x",
            workspace_root=workspace,
        ).verify()


def test_creating_a_worktree_verifies_its_placement_first(h):
    """The check is on the creation path, not only available to callers."""
    h.init_repo()
    inside = h.repo_dir / "nested-worktree"
    with pytest.raises(IntegrityViolation):
        ensure_worktree(
            h.repo(),
            WorktreePlacement(
                path=inside,
                branch="gruntime/nested",
                workspace_root=h.repo_dir,
            ),
        )
    assert not inside.exists(), "a refused worktree was created anyway"


def test_the_placement_lives_beside_the_governance_state(tmp_path):
    placement = worktree_root(tmp_path / "governance", "prj-1")
    assert placement == tmp_path / "governance" / "worktrees" / "prj-1"
    assert governed_branch("prj-1") == "gruntime/prj-1"


# --- against a real repository ---------------------------------------------


def test_the_mutation_lands_in_the_worktree_and_not_in_the_checkout(h):
    project_id = project_with_repo(h, slug="worktree")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
    before = _checkout_state(h)

    intent, receipt = _apply(h, project_id, run_id)

    worktree = h.worktree_dir(project_id)
    assert worktree.is_dir(), "no dedicated worktree was created"
    assert (worktree / "feature.txt").read_text() == "governed\n"
    assert not (h.repo_dir / "feature.txt").exists(), (
        "the governed mutation was written into the user's checkout"
    )
    assert _checkout_state(h) == before, "the user's checkout moved"
    assert receipt.revision_id == git(worktree, "rev-parse", "HEAD")


def test_the_worktree_is_outside_the_workspace(h):
    project_id = project_with_repo(h, slug="outside")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
    _apply(h, project_id, run_id)
    worktree = h.worktree_dir(project_id).resolve()
    assert not worktree.is_relative_to(h.repo_dir.resolve())


def test_the_governed_revision_is_on_the_governed_line(h):
    project_id = project_with_repo(h, slug="line")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
    intent, receipt = _apply(h, project_id, run_id)

    assert intent.target_ref == governed_branch(project_id)
    branch_head = git(h.repo_dir, "rev-parse", governed_branch(project_id))
    assert branch_head == receipt.revision_id
    assert receipt.revision_id != git(h.repo_dir, "rev-parse", "main")


def test_the_landed_revision_is_findable_from_the_users_checkout(h):
    """Same repository, so recovery from the checkout still sees it."""
    project_id = project_with_repo(h, slug="findable")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
    intent, receipt = _apply(h, project_id, run_id)

    found = h.repo().find_by_token(intent.operation_token)
    assert found == [receipt.revision_id]


def test_governed_mutation_does_not_register_as_workspace_drift(h):
    """The corollary: writing elsewhere means the observed reality is unmoved.

    If governed commits landed in the checkout they would show up in the very
    next snapshot as change, and the runtime would be unable to tell its own
    work from a human's.
    """
    project_id = project_with_repo(h, slug="nodrift")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
    before = snapshot_hash(h, project_id)

    _apply(h, project_id, run_id)

    with h.store() as store:
        project = store.get_project(project_id)
        post = store.get_snapshot(project.snapshot_current)
    assert post.snapshot_hash == before
    assert post.drift_summary.unattributed == 0
    assert not (h.repo_dir / "feature.txt").exists()


def test_the_governed_line_accumulates_and_is_never_reset(h):
    """A second controller adopts the worktree rather than rewinding it."""
    project_id = project_with_repo(h, slug="accumulate")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)

    first_intent, first = _apply(h, project_id, run_id, path="one.txt", content="1\n")
    second_intent, second = _apply(h, project_id, run_id, path="two.txt", content="2\n")

    assert second_intent.base_revision_id == first.revision_id
    assert second.parent_revision_ids == (first.revision_id,)
    worktree = h.worktree_dir(project_id)
    assert (worktree / "one.txt").exists() and (worktree / "two.txt").exists()
    assert h.revision_count() == 3  # the base, plus two governed revisions


def test_applying_against_a_moved_governed_line_is_refused(h):
    """Transition-matrix §9.3: the reviewed diff must be the diff that lands."""
    project_id = project_with_repo(h, slug="moved-base")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
        stale = controller.propose_commit(
            run_id, path="stale.txt", content="stale\n", message="stale"
        )
        controller.authorize_commit(stale.intent_id)

    # Somebody advances the governed line underneath the authorized intent.
    worktree = h.worktree_dir(project_id)
    write_target = worktree / "sideways.txt"
    write_target.write_text("sideways\n", encoding="utf-8")
    git(worktree, "add", "-A")
    git(worktree, "commit", "-q", "-m", "sideways")

    with h.controller(with_repo=True) as controller:
        with pytest.raises(IntegrityViolation) as refusal:
            controller.apply_commit(stale.intent_id)
    assert stale.base_revision_id in str(refusal.value)


def test_a_dirty_users_checkout_does_not_block_governed_mutation(h):
    """The two trees are independent, which is the point of separating them."""
    project_id = project_with_repo(h, slug="dirty-checkout")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
    write(h, "README.md", "the user is mid-edit\n")

    _intent, receipt = _apply(h, project_id, run_id)
    assert receipt.revision_id
    assert (h.repo_dir / "README.md").read_text() == "the user is mid-edit\n"
