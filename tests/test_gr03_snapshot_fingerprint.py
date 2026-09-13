"""GR-03 — the snapshot fingerprint is deterministic, and covers exactly the
tracked reality.

Acceptance criteria:
    Deterministic: same repo state -> same snapshot hash; any tracked change
    -> different hash.
    The snapshot must NOT hash untracked or gitignored files — otherwise every
    tool run invalidates every approval.

Design basis: domain-model §9.D (`RealitySnapshot`, `RS-INV-1`), and the hash
preimage table in `gruntime/repository.py`, which this file holds to its word:
the members named there are hashed, and the exclusions named there are not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gruntime.canonical import canonical_json, digest_bytes, is_digest
from gruntime.models import Completeness, SnapshotTrigger
from gruntime.repository import (
    PREIMAGE_VERSION,
    RepositoryFingerprint,
    derive_dirty,
    effective_index,
    observe_filesystem,
    observe_repository,
    verify_head,
)

from gr03_support import (
    commit_in_checkout,
    git,
    project_with_repo,
    snapshot,
    snapshot_hash,
    write,
)

#: Exactly the members `repository.py` documents as hashed. Kept literal: a
#: preimage that quietly grows or shrinks changes what an approval is bound to.
PREIMAGE_MEMBERS = {
    "preimage_version",
    "completeness",
    "scope",
    "revision_id",
    "target_ref",
    "tree_digest",
    "dirty_digest",
}


# --- the preimage itself ---------------------------------------------------


def test_the_preimage_has_exactly_the_documented_members():
    fingerprint = RepositoryFingerprint(
        completeness=Completeness.COMPLETE,
        committed={"a.txt": digest_bytes(b"a")},
        dirty={},
        revision_id="rev",
        target_ref="main",
        untracked_count=12,
        byte_count=99,
    )
    assert set(fingerprint.preimage()) == PREIMAGE_MEMBERS
    assert fingerprint.preimage()["preimage_version"] == PREIMAGE_VERSION
    assert is_digest(fingerprint.snapshot_hash)


def test_the_hash_is_the_digest_of_the_canonical_preimage():
    """No second construction: the hash *is* the documented preimage."""
    fingerprint = RepositoryFingerprint(
        completeness=Completeness.COMPLETE,
        committed={"a.txt": digest_bytes(b"a")},
        dirty={"a.txt": digest_bytes(b"a2")},
        revision_id="rev",
        target_ref="main",
    )
    assert fingerprint.snapshot_hash == digest_bytes(
        canonical_json(fingerprint.preimage())
    )


def test_observability_fields_are_recorded_but_not_hashed():
    """`untracked_count` and `byte_count` are on the record, never in the hash.

    Hashing the count would reintroduce untracked files through the back door:
    one `mypy` cache directory and every approval bound to the snapshot dies.
    """
    base = dict(
        completeness=Completeness.COMPLETE,
        committed={"a.txt": digest_bytes(b"a")},
        dirty={},
        revision_id="rev",
        target_ref="main",
    )
    quiet = RepositoryFingerprint(**base, untracked_count=0, byte_count=1)
    noisy = RepositoryFingerprint(**base, untracked_count=400, byte_count=99999)
    assert quiet.snapshot_hash == noisy.snapshot_hash
    assert noisy.document()["untracked_count"] == 400


def test_a_failed_observation_never_hashes_as_an_empty_repository():
    """`RS-INV-1`: absence of observation is not observation of absence."""
    empty = RepositoryFingerprint(
        completeness=Completeness.COMPLETE, committed={}, dirty={}
    )
    failed = RepositoryFingerprint(
        completeness=Completeness.FAILED, committed={}, dirty={}
    )
    assert empty.snapshot_hash != failed.snapshot_hash


def test_the_dirty_index_is_derived_from_committed_versus_worktree():
    committed = {"kept.txt": "sha256:aa", "gone.txt": "sha256:bb", "same.txt": "sha256:cc"}
    worktree = {"kept.txt": "sha256:zz", "same.txt": "sha256:cc", "new.txt": "sha256:dd"}
    assert derive_dirty(committed, worktree) == {
        "kept.txt": "sha256:zz",
        "gone.txt": None,
        "new.txt": "sha256:dd",
    }
    assert effective_index(committed, derive_dirty(committed, worktree)) == {
        "kept.txt": "sha256:zz",
        "same.txt": "sha256:cc",
        "new.txt": "sha256:dd",
    }


def test_the_dirty_digest_is_not_derivable_from_the_committed_one():
    """Both halves are load-bearing.

    `tree_digest` keeps meaning "as committed", because that is what a
    `CommitReceipt.actual_tree_digest` is compared against. Uncommitted edits
    therefore have to move a digest of their own or they would be invisible.
    """
    clean = RepositoryFingerprint(
        completeness=Completeness.COMPLETE,
        committed={"a.txt": "sha256:aa"},
        dirty={},
        revision_id="rev",
    )
    dirty = RepositoryFingerprint(
        completeness=Completeness.COMPLETE,
        committed={"a.txt": "sha256:aa"},
        dirty={"a.txt": "sha256:bb"},
        revision_id="rev",
    )
    assert clean.tree_digest == dirty.tree_digest
    assert clean.dirty_digest != dirty.dirty_digest
    assert clean.snapshot_hash != dirty.snapshot_hash


# --- against a real repository ---------------------------------------------


def test_the_same_repository_state_produces_the_same_snapshot_hash(h):
    project_id = project_with_repo(h)
    first = snapshot_hash(h, project_id)
    second = snapshot_hash(h, project_id)
    assert first == second, "looking twice changed the fingerprint"

    with h.store() as store:
        snapshots = store.list_snapshots(project_id)
        assert len({s.snapshot_id for s in snapshots}) == len(snapshots)
        assert snapshots[-1].completeness is Completeness.COMPLETE


def test_the_hash_is_of_reality_not_of_the_record(h):
    """Two distinct records over one reality carry one hash, deliberately."""
    project_id = project_with_repo(h)
    first_id = snapshot(h, project_id)
    second_id = snapshot(h, project_id, trigger=SnapshotTrigger.DRIFT_CHECK)
    with h.store() as store:
        first = store.get_snapshot(first_id)
        second = store.get_snapshot(second_id)
    assert first.snapshot_id != second.snapshot_id
    assert first.taken_at <= second.taken_at
    assert first.trigger is not second.trigger
    assert first.snapshot_hash == second.snapshot_hash


def test_a_committed_tracked_change_moves_the_hash(h):
    project_id = project_with_repo(h)
    before = snapshot_hash(h, project_id)
    commit_in_checkout(h, "README.md", "changed\n")
    assert snapshot_hash(h, project_id) != before


def test_an_uncommitted_tracked_change_moves_the_hash(h):
    """A dirty tracked file is a change to reality, committed or not."""
    project_id = project_with_repo(h)
    before = snapshot_hash(h, project_id)
    write(h, "README.md", "dirty\n")
    assert snapshot_hash(h, project_id) != before


def test_deleting_a_tracked_file_moves_the_hash(h):
    project_id = project_with_repo(h)
    before = snapshot_hash(h, project_id)
    (h.repo_dir / "README.md").unlink()
    assert snapshot_hash(h, project_id) != before


def test_a_staged_new_file_moves_the_hash(h):
    """`git add` makes a path tracked, so it counts from that moment on."""
    project_id = project_with_repo(h)
    before = snapshot_hash(h, project_id)
    write(h, "staged.txt", "staged\n")
    git(h.repo_dir, "add", "--", "staged.txt")
    assert snapshot_hash(h, project_id) != before


def test_an_untracked_file_does_not_move_the_hash(h):
    """The rule the whole design rests on: tool output is not reality."""
    project_id = project_with_repo(h)
    before = snapshot_hash(h, project_id)
    write(h, "coverage.xml", "<coverage/>\n")
    write(h, "build/output.o", "binary\n")
    assert snapshot_hash(h, project_id) == before


def test_a_gitignored_file_does_not_move_the_hash(h):
    project_id = project_with_repo(h)
    commit_in_checkout(h, ".gitignore", "*.log\ncache/\n", message="ignore rules")
    before = snapshot_hash(h, project_id)
    write(h, "run.log", "chatty\n")
    write(h, "cache/blob", "cached\n")
    assert snapshot_hash(h, project_id) == before


def test_repository_metadata_does_not_move_the_hash(h):
    """`.git` internals churn on every fetch, tag and reflog write."""
    project_id = project_with_repo(h)
    before = snapshot_hash(h, project_id)
    git(h.repo_dir, "tag", "some-tag")
    (h.repo_dir / ".git" / "description").write_text("edited\n", encoding="utf-8")
    assert snapshot_hash(h, project_id) == before


def test_untracked_files_are_counted_on_the_record_even_though_unhashed(h):
    project_id = project_with_repo(h)
    write(h, "scratch.tmp", "x\n")
    snapshot_id = snapshot(h, project_id)
    with h.store() as store:
        record = store.get_snapshot(snapshot_id)
        document = store.snapshot_document(record)
    assert record.vcs_state["untracked"] == 1
    assert document["untracked_count"] == 1
    assert "scratch.tmp" not in document["committed"]
    assert "scratch.tmp" not in document["dirty"]


def test_the_stored_file_index_reproduces_every_digest(h):
    """An auditor can recompute the hash from the artifact alone."""
    project_id = project_with_repo(h)
    write(h, "README.md", "dirty\n")
    snapshot_id = snapshot(h, project_id)
    with h.store() as store:
        record = store.get_snapshot(snapshot_id)
        document = store.snapshot_document(record)

    assert record.tree_digest == digest_bytes(canonical_json(document["committed"]))
    recomputed = digest_bytes(
        canonical_json(
            {
                "preimage_version": document["preimage_version"],
                "completeness": document["completeness"],
                "scope": document["scope"],
                "revision_id": document["revision_id"],
                "target_ref": document["target_ref"],
                "tree_digest": digest_bytes(canonical_json(document["committed"])),
                "dirty_digest": digest_bytes(canonical_json(document["dirty"])),
            }
        )
    )
    assert recomputed == record.snapshot_hash


def test_the_snapshot_records_head_and_branch(h):
    project_id = project_with_repo(h)
    snapshot_id = snapshot(h, project_id)
    with h.store() as store:
        record = store.get_snapshot(snapshot_id)
    assert record.vcs_state["revision_id"] == git(h.repo_dir, "rev-parse", "HEAD")
    assert record.vcs_state["target_ref"] == "main"
    assert record.vcs_state["dirty"] is False


# --- HEAD and branch verification ------------------------------------------


def test_verify_head_accepts_the_repository_it_was_measured_against(h):
    h.init_repo()
    repo = h.repo()
    result = verify_head(
        repo, expected_revision=repo.head_revision(), expected_ref="main"
    )
    assert result.matches is True


def test_verify_head_detects_a_moved_head(h):
    h.init_repo()
    repo = h.repo()
    stale = repo.head_revision()
    commit_in_checkout(h, "README.md", "moved\n")
    result = verify_head(repo, expected_revision=stale, expected_ref="main")
    assert result.matches is False
    assert stale in result.reason()


def test_verify_head_detects_a_switched_branch(h):
    """The same revision on a different line is a different place to land."""
    h.init_repo()
    repo = h.repo()
    revision = repo.head_revision()
    git(h.repo_dir, "checkout", "-q", "-b", "somebody-elses-work")
    result = verify_head(repo, expected_revision=revision, expected_ref="main")
    assert result.matches is False
    assert result.actual_revision == revision
    assert "somebody-elses-work" in result.reason()


def test_a_detached_head_reports_no_branch(h):
    h.init_repo()
    repo = h.repo()
    git(h.repo_dir, "checkout", "-q", "--detach")
    assert repo.current_branch() is None


def test_an_adapter_failure_is_an_observation_not_a_crash(tmp_path: Path):
    """A repository that cannot be read is `FAILED`, never silently empty."""

    class Broken:
        def head_revision(self):
            raise OSError("the repository is gone")

    fingerprint = observe_repository(Broken())
    assert fingerprint.completeness is Completeness.FAILED
    assert fingerprint.vcs_state() is None


@pytest.mark.parametrize("kind", ["committed", "dirty", "deleted"])
def test_every_kind_of_tracked_change_is_visible_to_the_adapter(h, kind):
    """The adapter reports the tracked set, and only the tracked set."""
    h.init_repo()
    repo = h.repo()
    write(h, "untracked-noise.txt", "noise\n")
    before = observe_repository(repo)
    assert "untracked-noise.txt" not in before.effective_index()

    if kind == "committed":
        commit_in_checkout(h, "README.md", "committed\n")
    elif kind == "dirty":
        write(h, "README.md", "dirty\n")
    else:
        (h.repo_dir / "README.md").unlink()

    after = observe_repository(repo)
    assert after.snapshot_hash != before.snapshot_hash
    assert after.untracked_count == 1


# --- workspaces with no version control ------------------------------------


def test_a_workspace_without_a_vcs_is_still_fingerprinted(tmp_path: Path):
    """No tracked set exists, so every file under the root is content."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("a\n", encoding="utf-8")
    fingerprint = observe_filesystem(tmp_path)
    assert fingerprint.completeness is Completeness.COMPLETE
    assert set(fingerprint.effective_index()) == {"src/a.py"}
    assert fingerprint.revision_id is None
    assert fingerprint.vcs_state() is None


def test_repository_metadata_is_excluded_even_without_a_vcs(tmp_path: Path):
    """The same exclusion, applied by directory name rather than by `ls-files`."""
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    before = observe_filesystem(tmp_path).snapshot_hash
    for metadata in (".git", ".hg", ".svn"):
        nested = tmp_path / metadata / "internals"
        nested.mkdir(parents=True)
        (nested / "state").write_text("churn\n", encoding="utf-8")
    after = observe_filesystem(tmp_path)
    assert after.snapshot_hash == before
    assert set(after.effective_index()) == {"a.txt"}


def test_a_missing_workspace_is_an_empty_walk_not_a_crash(tmp_path: Path):
    fingerprint = observe_filesystem(tmp_path / "does-not-exist")
    assert fingerprint.effective_index() == {}
    assert fingerprint.completeness is Completeness.COMPLETE
