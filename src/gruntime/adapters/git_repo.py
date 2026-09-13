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

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Mapping, Optional, Sequence

from ..canonical import canonical_json, digest_bytes
from ..models import Hash, MutationOp
from ..errors import IntegrityViolation, PolicyDenied
from ..repository import assert_unprotected, verify_head
from ..commit import commit_message, exact_paths, expected_entries, message_fields

#: Trailer key the `operation_token` is written under.
OPERATION_TOKEN_TRAILER = "Operation-Token"


class GitRepository:
    """A git working tree the runtime may mutate through commits."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _git(self, *args: str, text: bool = True, index_file=None, input=None):
        # A closed command surface also denies push through option/alias tricks.
        allowed = {"rev-parse", "rev-list", "ls-tree", "show", "ls-files", "log",
                   "status", "worktree", "add", "write-tree", "diff", "diff-tree",
                   "cat-file", "read-tree", "commit"}
        if not args or args[0] not in allowed:  # guard:git_command_capability
            raise PolicyDenied("commit.publish is DENIED; unsupported Git command")
        if args[0] == "add":
            if len(args) < 3 or args[1] != "--":  # guard:git_blanket_staging
                raise PolicyDenied("only exact-path staging is permitted")
            self._exact_paths(args[2:])  # guard:git_add_paths
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        if index_file is not None:
            env["GIT_INDEX_FILE"] = str(index_file)
        return subprocess.run(
            ["git",
             "--literal-pathspecs",  # guard:git_literal_pathspec_mode
             "-c", "core.hooksPath=/dev/null",  # guard:git_disable_hooks
             "-c", "commit.gpgsign=false",  # guard:git_disable_signing
             *args],
            cwd=str(self.root), check=True, capture_output=True,
            text=text, input=input,
            env=env,  # guard:git_environment
        ).stdout

    def _exact_paths(self, paths):
        if not paths:  # guard:git_nonempty_paths
            raise PolicyDenied("blanket staging is refused; name exact paths")
        for path in paths:
            normalized = assert_unprotected(path)
            if normalized != path or path.startswith(("-", ":")) or "\0" in path:
                raise PolicyDenied("only canonical literal paths are permitted")  # guard:git_literal_paths
            target = self.root / path
            if (target.is_dir() or target.is_symlink()
                    or not target.resolve().is_relative_to(self.root.resolve())):
                raise PolicyDenied("directories and symlink paths cannot be staged")  # guard:git_path_boundary
        return tuple(paths)

    def stage(self, paths: Sequence[str]) -> None:
        self._git("add", "--", *paths)

    def publish(self, *args, **kwargs):
        """Publication is a separate capability with no grant in this build."""
        raise PolicyDenied("commit.publish is DENIED")  # guard:git_publish_denied

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

    def current_branch(self) -> Optional[str]:
        """The checked-out branch, or `None` when `HEAD` is detached."""
        name = self._git("rev-parse", "--abbrev-ref", "HEAD").strip()
        return None if name == "HEAD" else name

    def tracked_paths(self) -> list[str]:
        """Every path git tracks in this working tree.

        `ls-files` is the tracked set, so a path that is untracked or matched
        by an ignore rule never appears — which is what keeps a build directory
        or an editor scratch file out of every fingerprint.
        """
        listing = self._git("ls-files", "-z")
        return [name for name in listing.split("\0") if name]

    def worktree_index(self) -> dict[str, Hash]:
        """Tracked path to digest of the bytes **on disk**.

        Deleted-but-tracked paths are absent rather than raising: their absence
        is the observation, and `repository.derive_dirty` records it as such.
        """
        index: dict[str, Hash] = {}
        for name in self.tracked_paths():
            target = self.root / name
            try:
                index[name] = digest_bytes(target.read_bytes())
            except (FileNotFoundError, IsADirectoryError):
                continue
        return index

    def worktree_byte_count(self) -> int:
        """Total bytes of tracked content on disk."""
        total = 0
        for name in self.tracked_paths():
            target = self.root / name
            try:
                total += target.stat().st_size
            except (FileNotFoundError, NotADirectoryError):
                continue
        return total

    def untracked_count(self) -> int:
        """How many untracked, non-ignored files exist.

        `--exclude-standard` applies `.gitignore`, so an ignored file is
        neither tracked nor counted here. Recorded on the snapshot for
        observability; never part of the hash preimage.
        """
        listing = self._git("ls-files", "--others", "--exclude-standard", "-z")
        return len([name for name in listing.split("\0") if name])

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
            "--reflog",
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

    # -- worktrees ---------------------------------------------------------

    def add_worktree(
        self, path: Path, *, branch: str, revision: str
    ) -> "GitRepository":
        """Create a dedicated worktree at `path`, on `branch`, from `revision`.

        The branch is created only if it does not already exist. Reusing an
        existing governed branch matters: resetting it to `revision` would
        strand revisions that already landed on the governed line, and those
        are exactly the ones a restart has to be able to find by token
        (`CM-INV-2`).
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Drop registrations whose directories are gone, so a worktree removed
        # out from under git does not block re-creating it.
        self._git("worktree", "prune")
        if self._branch_exists(branch):
            self._git("worktree", "add", str(path), branch)
        else:
            self._git("worktree", "add", "-b", branch, str(path), revision)
        return GitRepository(path)

    def open_worktree(self, path: Path) -> "GitRepository":
        """An adapter rooted at an existing worktree of this repository."""
        return GitRepository(Path(path))

    def _branch_exists(self, branch: str) -> bool:
        try:
            self._git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")
        except subprocess.CalledProcessError:
            return False
        return True

    # -- mutation ----------------------------------------------------------

    def write_file(self, path: str, content: str | bytes) -> None:
        self._exact_paths((path,))  # guard:git_write_boundary
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)

    def apply_mutations(self, intent, artifact_bytes):
        paths = exact_paths(intent)
        self._exact_paths(paths)  # guard:git_mutation_boundary
        # Validate every proposal before writing any of them.
        expected_entries(intent, self.tree_entries(intent.base_revision_id))
        for mutation in intent.mutations:
            target = self.root / mutation.path
            if mutation.op is MutationOp.DELETE:
                target.unlink()
            elif mutation.op is MutationOp.RENAME:
                destination = self.root / mutation.rename_to
                destination.parent.mkdir(parents=True, exist_ok=True)
                target.rename(destination)
                if mutation.after_ref is not None:
                    self.write_file(mutation.rename_to, artifact_bytes(mutation.after_ref.digest))
            elif mutation.op is MutationOp.CHMOD:
                target.chmod(mutation.mode)
            else:
                self.write_file(mutation.path, artifact_bytes(mutation.after_ref.digest))
        return paths

    def tree_entries(self, revision: str) -> dict[str, tuple[str, Hash]]:
        entries = {}
        for entry in self._git("ls-tree", "-r", "-z", revision).split("\0"):
            if not entry:
                continue
            header, path = entry.split("\t", 1)
            mode, kind, object_id = header.split()
            entries[path] = (mode, digest_bytes(self._git("cat-file", kind, object_id, text=False)))
        return entries

    def changed_paths(self, parent: str, revision: str) -> tuple[str, ...]:
        return tuple(sorted(filter(None, self._git(
            "diff", "--no-ext-diff", "--no-renames", "--name-only", "-z", parent, revision, "--"
        ).split("\0"))))

    def verify_staged(self, intent, *, tree=None) -> str:
        tree = tree or self._git("write-tree").strip()
        actual = self.tree_entries(tree)
        predicted = expected_entries(intent, self.tree_entries(intent.base_revision_id))
        digest = digest_bytes(canonical_json({p: value[1] for p, value in actual.items()}))
        if actual != predicted or digest != intent.expected_tree_digest:  # guard:git_staged_tree
            raise IntegrityViolation("staged tree differs from the commit intent")
        if self.changed_paths(intent.base_revision_id, tree) != exact_paths(intent):  # guard:git_staged_paths
            raise IntegrityViolation("staged paths differ from the commit intent")
        return tree

    def commit(self, *, intent) -> str:
        """Verify, freeze the index, check parent/branch, then commit that index.

        Git hooks are disabled: they cannot rewrite a verified transaction or
        execute a publication command. A private index pins the verified tree.
        """
        message = commit_message(intent)
        tree = self._git("write-tree").strip()
        self.verify_staged(intent, tree=tree)  # guard:git_verify_before_commit
        with tempfile.TemporaryDirectory(prefix="gruntime-index-") as temporary:
            index = Path(temporary) / "index"
            self._git("read-tree", tree, index_file=index)
            head = verify_head(self, expected_revision=intent.base_revision_id,
                               expected_ref=intent.target_ref)
            merge_head = self.root / self._git("rev-parse", "--git-path", "MERGE_HEAD").strip()
            if merge_head.exists() or not intent.target_ref or not head.matches:  # guard:git_expected_parent_branch
                raise IntegrityViolation(f"{intent.base_revision_id}: unexpected parent/branch or pending merge; {head.reason()}")
            self._git("commit", "-q", "--file=-",
                      "--cleanup=verbatim",  # guard:git_message_verbatim
                      index_file=index,  # guard:git_commit_private_index
                      input=message, text=False)
        return self.head_revision()

    def observe_commit(self, revision_id: str, *, intent) -> dict:
        raw = self._git("cat-file", "commit", revision_id, text=False)
        headers, _, message = raw.partition(b"\n\n")
        tree = next(line[5:].decode() for line in headers.splitlines() if line.startswith(b"tree "))
        parents = tuple(line[7:].decode() for line in headers.splitlines() if line.startswith(b"parent "))
        subject, body_hash = message_fields(message)
        entries = self.tree_entries(revision_id)
        before = self.tree_entries(parents[0]) if parents else {}
        paths = tuple(sorted(p for p in entries.keys() | before.keys() if entries.get(p) != before.get(p)))
        changes = []
        for path in paths:
            old, new = before.get(path), entries.get(path)
            op = ("CREATE" if old is None else "DELETE" if new is None
                  else "CHMOD" if old[1] == new[1] else "MODIFY")
            changes.append(dict(path=path, op=op, before_digest=old[1] if old else None,
                                after_digest=new[1] if new else None))
        tokens = tuple(self._git("show", "-s", "--format=%(trailers:key=" +
                                OPERATION_TOKEN_TRAILER + ",valueonly)", revision_id).split())
        return dict(revision_id=revision_id, parent_revision_ids=parents,
                    actual_tree_digest=self.tree_digest(revision_id), tree_id=tree,
                    subject=subject, body_hash=body_hash, committed_paths=paths,
                    files_changed=tuple(changes), operation_tokens=tokens,
                    entries=entries, base_entries=self.tree_entries(intent.base_revision_id),
                    matching_revisions=tuple(self.find_by_token(intent.operation_token)))

    def diff(self, revision_id: str) -> bytes:
        """Raw diff introduced by `revision_id`."""
        return self._git(
            "show", "--no-ext-diff", "--no-textconv", "--format=", "--patch", revision_id, text=False
        )

    def parents(self, revision_id: str) -> list[str]:
        """Parent revision ids of `revision_id`."""
        output = self._git("rev-list", "--parents", "-n", "1", revision_id).split()
        return output[1:]
