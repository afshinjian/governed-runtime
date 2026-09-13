"""Shared harness for the GR-01 acceptance tests (R-1..R-5).

R-2 and R-3 terminate a *real* controller subprocess with SIGKILL. Nothing is
monkeypatched and no fault is injected in-process: `gruntime.gate` publishes a
readiness file at a named point when `GRUNTIME_GATE` names that point, then
blocks. The test observes the file, sends SIGKILL from outside, and every
assertion afterwards reads on-disk state (SQLite, the artifact store, the
provider journal, the git repository) rather than call counts on a mock.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gruntime.adapters.fake_provider import FakeProvider  # noqa: E402
from gruntime.adapters.git_repo import GitRepository  # noqa: E402
from gruntime.artifacts import ArtifactStore  # noqa: E402
from gruntime.controller import Controller  # noqa: E402
from gruntime.store import StateStore  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


@dataclass
class Harness:
    root: Path

    @property
    def db_path(self) -> Path:
        return self.root / "state.db"

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

    @property
    def journal_dir(self) -> Path:
        return self.root / "provider"

    @property
    def repo_dir(self) -> Path:
        return self.root / "repo"

    @property
    def gate_dir(self) -> Path:
        return self.root / "gates"

    # -- collaborators ----------------------------------------------------

    def provider(self) -> FakeProvider:
        return FakeProvider(self.journal_dir)

    def repo(self) -> GitRepository:
        return GitRepository(self.repo_dir)

    def init_repo(self) -> GitRepository:
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        _git(self.repo_dir, "init", "-q", "-b", "main")
        _git(self.repo_dir, "config", "user.email", "gr01@example.invalid")
        _git(self.repo_dir, "config", "user.name", "GR-01")
        _git(self.repo_dir, "config", "commit.gpgsign", "false")
        (self.repo_dir / "README.md").write_text("base\n", encoding="utf-8")
        _git(self.repo_dir, "add", "-A")
        _git(self.repo_dir, "commit", "-q", "-m", "base")
        return self.repo()

    def revision_count(self) -> int:
        """Revisions in the repository, on every line.

        Counted over `--all`, not over the checkout's `HEAD`: governed
        mutation lands on the dedicated worktree's branch (GR-03), so a count
        of one branch would miss the very commits "did this land exactly
        once?" is asking about.
        """
        return int(_git(self.repo_dir, "rev-list", "--count", "--all"))

    def worktree_dir(self, project_id: str) -> Path:
        """Where the controller puts this project's governed worktree."""
        return self.root / "worktrees" / project_id

    # -- in-process access ------------------------------------------------

    @contextmanager
    def store(self):
        store = StateStore.open(self.db_path)
        try:
            yield store
        finally:
            store.close()

    @contextmanager
    def controller(self, *, with_repo: bool = False):
        store = StateStore.open(self.db_path)
        try:
            yield Controller(
                store=store,
                artifacts=ArtifactStore(self.artifacts_dir),
                provider=self.provider(),
                repo=self.repo() if with_repo else None,
            )
        finally:
            store.close()

    # -- subprocess control -----------------------------------------------

    def spawn(
        self,
        project_id: str,
        *args: str,
        gate: str | None = None,
        lease_ttl_ms: int | None = None,
    ):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
        if gate is not None:
            env["GRUNTIME_GATE"] = gate
            env["GRUNTIME_GATE_DIR"] = str(self.gate_dir)
        cmd = [
            sys.executable,
            "-m",
            "gruntime.controller",
            "--db",
            str(self.db_path),
            "--artifacts",
            str(self.artifacts_dir),
            "--journal",
            str(self.journal_dir),
        ]
        if self.repo_dir.exists():
            cmd += ["--repo", str(self.repo_dir)]
        cmd += ["--project", project_id]
        if lease_ttl_ms is not None:
            cmd += ["--lease-ttl-ms", str(lease_ttl_ms)]
        cmd += [*args]
        return subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

    def run(self, project_id: str, *args: str) -> str:
        proc = self.spawn(project_id, *args)
        out, err = proc.communicate(timeout=120)
        assert proc.returncode == 0, f"controller failed ({proc.returncode})\n{out}\n{err}"
        return out

    def wait_for_gate(self, name: str, proc, timeout: float = 60.0) -> None:
        ready = self.gate_dir / f"{name}.ready"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if ready.exists():
                return
            if proc.poll() is not None:
                out, err = proc.communicate()
                raise AssertionError(
                    f"controller exited {proc.returncode} before reaching gate "
                    f"{name!r}\nstdout:\n{out}\nstderr:\n{err}"
                )
            time.sleep(0.01)
        proc.kill()
        raise AssertionError(f"controller never reached gate {name!r}")

    def kill9(self, proc) -> None:
        """Real process termination: SIGKILL, uncatchable, no cleanup runs."""
        proc.kill()
        try:
            proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:  # pragma: no cover
            raise AssertionError("controller survived SIGKILL")
        assert proc.returncode == -signal.SIGKILL, (
            f"expected SIGKILL, got returncode {proc.returncode}"
        )


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return Harness(root=tmp_path)
