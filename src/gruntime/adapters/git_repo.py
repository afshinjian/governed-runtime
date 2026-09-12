"""Git adapter: the vendor-specific half of `vcs_kind = DVCS`.

Core never calls git and never sees a revision as anything but
`Str(1..128)`. Everything git-shaped — trailers, rev-list, tree hashing —
lives here.

The adapter's one structural obligation is `find_by_token`: because the
`operation_token` is written into the revision's trailers before the mutation
is performed, a revision that landed while the controller was down can always
be found again. Without that lookup an `APPLYING` intent would be resolvable
only by a blind retry, which is not idempotent (`CM-INV-2`, `CM-INV-3`).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Mapping, Optional, Sequence

from ..canonical import canonical_json, digest_bytes
from ..models import Hash

#: Trailer key the `operation_token` is written under.
OPERATION_TOKEN_TRAILER = "Operation-Token"


class GitRepository:
    """A git working tree the runtime may mutate through commits."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _git(self, *args: str, text: bool = True):
        return subprocess.run(
            ["git", *args],
            cwd=str(self.root),
            check=True,
            capture_output=True,
            text=text,
        ).stdout

    # -- observation -------------------------------------------------------

    def head_revision(self) -> str:
        """Current `HEAD` revision id."""
        return self._git("rev-parse", "HEAD").strip()

    def revision_count(self) -> int:
        """Number of revisions reachable from `HEAD`."""
        return int(self._git("rev-list", "--count", "HEAD").strip())

    def file_index(self, revision_id: Optional[str] = None) -> dict[str, Hash]:
        """Path to content digest for every tracked file at `revision_id`.

        The index, not git's own tree object, is what core compares: a commit
        intent predicts an index and the adapter re-observes one, so `MATCHED`
        means the workspace holds the authorized content and nothing else.
        """
        revision = revision_id or "HEAD"
        listing = self._git("ls-tree", "-r", "--name-only", "-z", revision, text=True)
        index: dict[str, Hash] = {}
        for name in listing.split("\0"):
            if not name:
                continue
            blob = self._git("show", f"{revision}:{name}", text=False)
            index[name] = digest_bytes(blob)
        return index

    def tree_digest(self, revision_id: Optional[str] = None) -> Hash:
        """Digest of the tree at `revision_id`, defaulting to `HEAD`."""
        return digest_bytes(canonical_json(self.file_index(revision_id)))

    def find_by_token(self, operation_token: str) -> list[str]:
        """Every revision whose trailers carry `operation_token`.

        Zero, one, or more. One is an adoption; zero with an unchanged base is
        the positive finding that nothing landed; anything else is
        `UNRESOLVABLE` and escalates rather than being guessed at — tree
        equality alone never establishes which revision fulfilled which
        intent (`CM-INV-3`).
        """
        output = self._git(
            "log",
            "--all",
            "--format=%H%x00%(trailers:key=" + OPERATION_TOKEN_TRAILER + ",valueonly)%x00%x00",
        )
        found: list[str] = []
        for entry in output.split("\0\0"):
            entry = entry.strip("\n")
            if not entry:
                continue
            revision, _, trailer = entry.partition("\0")
            if operation_token in trailer.split():
                found.append(revision.strip())
        return found

    def is_dirty(self) -> bool:
        """True iff the working tree has uncommitted changes."""
        return bool(self._git("status", "--porcelain").strip())

    # -- mutation ----------------------------------------------------------

    def write_file(self, path: str, content: str) -> None:
        """Write one file inside the repository root."""
        target = self.root / path
        if not target.resolve().is_relative_to(self.root.resolve()):
            raise ValueError(f"{path!r} escapes the repository root")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def commit(
        self,
        *,
        message: str,
        trailers: Mapping[str, str],
        paths: Sequence[str] = (),
    ) -> str:
        """Commit the staged paths, carrying `trailers` outward.

        The token reaches the repository in the same operation that creates
        the revision, so there is no window in which a revision exists without
        its identity (evidence-model §3.2.1 step 2).
        """
        if paths:
            self._git("add", "--", *paths)
        else:
            self._git("add", "-A")
        body = [message, ""]
        body.extend(f"{key}: {value}" for key, value in trailers.items())
        self._git("commit", "-q", "-m", "\n".join(body))
        return self.head_revision()

    def diff(self, revision_id: str) -> bytes:
        """Raw diff introduced by `revision_id`."""
        return self._git(
            "show", "--format=", "--patch", revision_id, text=False
        )

    def parents(self, revision_id: str) -> list[str]:
        """Parent revision ids of `revision_id`."""
        output = self._git("rev-list", "--parents", "-n", "1", revision_id).split()
        return output[1:]
