"""The governed worktree: where mutation happens, and where it does not.

Design basis: authority-matrix §2.4 (`fs.write` "never writes the live tree"),
§2.6 (`commit.apply`), transition-matrix §9.3 (applying an intent whose
`base_revision_id` no longer matches reality), domain-model §9.D.

The workspace the runtime *observes* and the tree the runtime *mutates* are
two different directories, and keeping them apart is what makes both halves of
the runtime honest:

| directory | role | the runtime |
|---|---|---|
| `project.workspace_root` | the user's checkout — the reality snapshots measure | reads it, never writes a file into it, never moves its `HEAD` |
| the governed worktree | a dedicated checkout of the governed line | writes every authorized mutation here, and commits here |

Both are views of the same repository, so a governed revision is a first-class
part of the repository the moment it lands: `find_by_token` sees it, its
objects are shared, and a human can inspect, merge or discard it. What does not
happen is a file appearing under someone's editor, or a branch moving beneath a
half-finished edit. `RS-INV-1` stays meaningful because the thing being
measured is not the thing being written.

The worktree lives in the governance directory, outside the workspace, so it
never shows up as untracked content in a snapshot of the workspace.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .errors import IntegrityViolation

#: Prefix of the line governed mutation is committed onto. Namespaced so a
#: governed branch is never mistaken for a human's.
GOVERNED_BRANCH_PREFIX = "gruntime"


def governed_branch(project_id: str) -> str:
    """The line one project's governed mutations are committed onto."""
    return f"{GOVERNED_BRANCH_PREFIX}/{project_id}"


def worktree_root(governance_dir: Path, project_id: str) -> Path:
    """Where one project's governed worktree lives.

    Under the governance directory — never under the workspace, or the
    worktree's own files would show up as untracked content in every snapshot
    of the workspace it is meant to stay out of.
    """
    return Path(governance_dir) / "worktrees" / project_id


@dataclass(frozen=True)
class WorktreePlacement:
    """Where a governed worktree is to be put, and on what line."""

    path: Path
    branch: str
    workspace_root: Path

    def verify(self) -> "WorktreePlacement":
        """Refuse a placement that is the user's checkout, or inside it.

        One condition covers both, because `is_relative_to` holds for a path
        against itself. Saying it once is deliberate: a second branch for the
        equality case would be unreachable behaviour that no test could
        distinguish from this one, and unreachable guards are how a rule rots
        without anything going red.

        A worktree *at* the workspace is the thing this module exists to
        forbid; one nested inside it would make governed mutation
        indistinguishable from workspace drift on the very next snapshot.
        Both are integrity violations, not configuration mistakes.
        """
        path = self.path.resolve()
        workspace = self.workspace_root.resolve()
        if path.is_relative_to(workspace):
            raise IntegrityViolation(
                f"the governed worktree {path} is the workspace {workspace}, "
                "or inside it; governed mutation must not touch the user's "
                "checkout"
            )
        return self


def ensure_worktree(repo, placement: WorktreePlacement, *, base_revision: Optional[str] = None):
    """Return an adapter rooted at the governed worktree, creating it if absent.

    Idempotent: an existing worktree is adopted at whatever revision its line
    has reached, so a controller restart continues the governed line rather
    than resetting it to the workspace's `HEAD` and stranding revisions that
    already landed.
    """
    placement.verify()
    if placement.path.exists():
        return repo.open_worktree(placement.path)
    return repo.add_worktree(
        placement.path,
        branch=placement.branch,
        revision=base_revision or repo.head_revision(),
    )
