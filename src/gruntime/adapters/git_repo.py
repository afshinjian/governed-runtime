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

from pathlib import Path
from typing import Mapping, Optional, Sequence

from ..models import Hash

#: Trailer key the `operation_token` is written under.
OPERATION_TOKEN_TRAILER = "Operation-Token"


class GitRepository:
    """A git working tree the runtime may mutate through commits."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    # -- observation -------------------------------------------------------

    def head_revision(self) -> str:
        """Current `HEAD` revision id."""
        raise NotImplementedError

    def revision_count(self) -> int:
        """Number of revisions reachable from `HEAD`."""
        raise NotImplementedError

    def tree_digest(self, revision_id: Optional[str] = None) -> Hash:
        """Digest of the tree at `revision_id`, defaulting to `HEAD`."""
        raise NotImplementedError

    def find_by_token(self, operation_token: str) -> list[str]:
        """Every revision whose trailers carry `operation_token`.

        Zero, one, or more. One is an adoption; zero with an unchanged base is
        the positive finding that nothing landed; anything else is
        `UNRESOLVABLE` and escalates rather than being guessed at — tree
        equality alone never establishes which revision fulfilled which
        intent (`CM-INV-3`).
        """
        raise NotImplementedError

    def is_dirty(self) -> bool:
        """True iff the working tree has uncommitted changes."""
        raise NotImplementedError

    # -- mutation ----------------------------------------------------------

    def write_file(self, path: str, content: str) -> None:
        """Write one file inside the repository root."""
        raise NotImplementedError

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
        raise NotImplementedError

    def diff(self, revision_id: str) -> bytes:
        """Raw diff introduced by `revision_id`."""
        raise NotImplementedError

    def parents(self, revision_id: str) -> list[str]:
        """Parent revision ids of `revision_id`."""
        raise NotImplementedError
