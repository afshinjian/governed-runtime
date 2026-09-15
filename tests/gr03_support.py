"""Shared setup for the GR-03 tests.

Every helper here works against the real git repository the `h` fixture
creates. Nothing is monkeypatched: a "dirty file" is a file written to disk, a
"tracked change" is a real commit, and an "untracked file" is a file git has
never been told about.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from genesis_support import OWNER


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True
    )
    return proc.stdout.strip()


def project_with_repo(h, *, slug: str = "gr-03") -> str:
    """A started project whose workspace *is* the user's checkout."""
    h.init_repo()
    with h.controller(with_repo=True) as controller:
        project_id = controller.create_project(
            name="GR-03", slug=slug, workspace_root=str(h.repo_dir),
            approved_by=OWNER,
        )
        controller.start(project_id)
    return project_id


def snapshot(h, project_id: str, **kwargs) -> str:
    """Take one snapshot through a fresh controller and return its id."""
    with h.controller(with_repo=True) as controller:
        return controller.take_snapshot(project_id, **kwargs)


def snapshot_hash(h, project_id: str) -> str:
    """The fingerprint of the workspace as it stands right now."""
    snapshot_id = snapshot(h, project_id)
    with h.store() as store:
        return store.get_snapshot(snapshot_id).snapshot_hash


def write(h, path: str, content: str) -> None:
    """Write a file into the user's checkout, as a human would."""
    target = h.repo_dir / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def commit_in_checkout(h, path: str, content: str, message: str = "human edit") -> str:
    """Commit a change in the user's checkout, outside the runtime."""
    write(h, path, content)
    git(h.repo_dir, "add", "--", path)
    git(h.repo_dir, "commit", "-q", "-m", message)
    return git(h.repo_dir, "rev-parse", "HEAD")
