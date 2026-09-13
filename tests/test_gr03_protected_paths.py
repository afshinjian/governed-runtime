"""GR-03 — protected paths are refused by the path, not by the grant.

Design basis: authority-matrix §2.4 — `fs.write.outside_scope` and
`fs.read.outside_workspace` are `NEVER` capabilities (`AX-6`), so no
capability, decision or governance mode makes these paths writable.
Transition-matrix §9.3 forbids writing outside scope outright.

The refusal is therefore not a policy verdict. It is checked twice — when the
intent is proposed and again when it is applied — because the second check is
the one that holds if a record ever reaches `APPLYING` by another route.
"""

from __future__ import annotations

import pytest

from gruntime.errors import ProtectedPathViolation
from gruntime.repository import (
    PROTECTED_PATHS,
    assert_unprotected,
    is_protected,
    matches_any,
    matches_glob,
    normalize_path,
)

from gr03_support import project_with_repo

REFUSED_PATHS = [
    ".git",
    ".git/config",
    ".git/hooks/pre-commit",
    ".gitmodules",
    ".hg/store/data",
    ".svn/entries",
    "../outside.txt",
    "a/../../outside.txt",
    "/etc/passwd",
    "",
]

ALLOWED_PATHS = [
    "README.md",
    "src/gruntime/controller.py",
    "docs/.gitkeep",
    "not-.git/file",
    "gitignore",
]


# --- the matcher ------------------------------------------------------------


def test_a_single_star_does_not_cross_a_separator():
    assert matches_glob("src/a.py", "src/*") is True
    assert matches_glob("src/deep/a.py", "src/*") is False
    assert matches_glob("src/deep/a.py", "src/**") is True


def test_a_question_mark_matches_one_non_separator_character():
    assert matches_glob("ab", "a?") is True
    assert matches_glob("a/b", "a?b") is False


def test_matching_is_anchored_at_both_ends():
    assert matches_glob("prefix-README.md", "README.md") is False
    assert matches_glob("README.md.bak", "README.md") is False
    assert matches_any("README.md", ("nope", "README.md")) is True


def test_glob_metacharacters_in_a_literal_pattern_are_escaped():
    assert matches_glob("a.txt", "a.txt") is True
    assert matches_glob("axtxt", "a.txt") is False


# --- the rule ---------------------------------------------------------------


@pytest.mark.parametrize("path", REFUSED_PATHS, ids=lambda p: p or "<empty>")
def test_a_protected_or_escaping_path_is_refused(path):
    with pytest.raises(ProtectedPathViolation):
        assert_unprotected(path)


@pytest.mark.parametrize("path", ALLOWED_PATHS)
def test_an_ordinary_workspace_path_is_allowed(path):
    assert assert_unprotected(path) == path


def test_normalization_keeps_the_path_scalar_shape():
    """domain-model §0.1: POSIX, relative, no `..`, no leading `/`."""
    assert normalize_path("./a//b/c.txt") == "a/b/c.txt"
    assert normalize_path("a\\b.txt") == "a/b.txt"


def test_the_protected_set_covers_every_supported_vcs():
    for metadata in (".git", ".hg", ".svn"):
        assert is_protected(metadata)
        assert is_protected(f"{metadata}/anything/at/all")
    assert PROTECTED_PATHS, "the protected set must not be empty"


def test_a_caller_may_protect_more_but_never_less():
    assert is_protected("secrets.env") is False
    assert is_protected("secrets.env", ("*.env",)) is True
    with pytest.raises(ProtectedPathViolation):
        assert_unprotected("secrets.env", ("*.env",))


# --- through the controller -------------------------------------------------


@pytest.mark.parametrize("path", [".git/config", "../escape.txt", "/etc/passwd"])
def test_proposing_a_mutation_of_a_protected_path_is_refused(h, path):
    project_id = project_with_repo(h, slug="protected")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
        with pytest.raises(ProtectedPathViolation):
            controller.propose_commit(
                run_id, path=path, content="owned\n", message="owned"
            )

    with h.store() as store:
        assert store.list_commit_intents(run_id) == [], "a refused intent was recorded"
        store.verify_chain(project_id)


def test_the_refusal_happens_before_anything_is_written(h):
    project_id = project_with_repo(h, slug="untouched")
    hooks = h.repo_dir / ".git" / "hooks" / "pre-commit"
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
        with pytest.raises(ProtectedPathViolation):
            controller.propose_commit(
                run_id,
                path=".git/hooks/pre-commit",
                content="#!/bin/sh\nexit 0\n",
                message="hook",
            )
    assert not hooks.exists()


def test_applying_a_protected_path_is_refused_even_if_the_record_carries_one(h):
    """The second guard. A record the proposing guard would never have made."""
    project_id = project_with_repo(h, slug="apply-guard")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
        intent = controller.propose_commit(
            run_id, path="feature.txt", content="fine\n", message="fine"
        )
        controller.authorize_commit(intent.intent_id)

    with h.store() as store:
        store.force_mutation_path(intent.intent_id, ".git/config")

    with h.controller(with_repo=True) as controller:
        with pytest.raises(ProtectedPathViolation):
            controller.apply_commit(intent.intent_id)

    worktree = h.worktree_dir(project_id)
    assert not (worktree / ".git" / "config").exists()
    assert h.revision_count() == 1, "a protected mutation landed anyway"
