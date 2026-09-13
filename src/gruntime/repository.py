"""Repository reality: what the workspace *is*, fingerprinted.

Design basis: domain-model §9.D (`RealitySnapshot`, `RS-INV-1`), §9.B.1
(`REALITY_DRIFT`), transition-matrix §4 (`NONE → SUSPENDED_BY_DRIFT`), §9.3
(applying an intent whose `base_revision_id` no longer matches reality;
`fs.write.outside_scope` and `fs.read.outside_workspace` as `NEVER`).

Core observes the repository through the `RepositoryView` surface below and
never runs a version-control command itself; the git-shaped half lives in
`adapters/git_repo.py`. Everything here is a derivation over what the adapter
reported, so it is testable without a repository and identical for any VCS.

## The snapshot hash preimage

`snapshot_hash` is a fingerprint of **reality**, not of the record. Two
snapshots taken a day apart over an unchanged repository carry the same hash on
purpose: that equality is how "has anything changed?" is answered, and it is
what keeps an approval bound to one snapshot from being invalidated by the mere
act of looking again. Record identity lives in `snapshot_id`.

The preimage is canonical JSON (RFC 8785, `canonical.py`) over exactly these
members, and nothing else:

| member | value |
|---|---|
| `preimage_version` | :data:`PREIMAGE_VERSION`, so a preimage change is visible |
| `completeness` | `Completeness` of the walk; a failed walk never hashes as an empty repository |
| `scope` | the globs actually walked, sorted |
| `revision_id` | the committed revision the working tree is based on, or `null` outside a VCS |
| `target_ref` | branch or line identifier, `null` when detached or outside a VCS |
| `tree_digest` | digest of canonical JSON of `{tracked path: content digest}` **as committed at `revision_id`** |
| `dirty_digest` | digest of canonical JSON of `{tracked path: worktree digest, or null when deleted on disk}`, for every tracked path whose working-tree content differs from `revision_id` |

Everything else is **excluded**, deliberately:

| excluded | why |
|---|---|
| untracked files | a build, a test run, an editor swap file, or a tool's scratch output would otherwise change the fingerprint and stale every approval bound to it |
| ignored files | same, and they are declared not to be part of the tracked reality |
| `.git`, `.hg`, `.svn` internals | repository metadata is not workspace content; it changes on every fetch and reflog write |
| `untracked_count`, `byte_count` | recorded on the snapshot for observability, never hashed — hashing the count would reintroduce untracked files through the back door |
| mtimes, inodes, ownership, permissions of unchanged content | not content; they differ across clones and CI runners |
| `snapshot_id`, `taken_at`, `taken_by`, `trigger` | record identity and provenance, not reality |
| anything outside the observed root | the root is the containment boundary (`fs.read.outside_workspace` is `NEVER`) |

A tracked file that changes — committed or merely dirty — moves `tree_digest`
or `dirty_digest` and therefore the fingerprint. That is the whole contract:
untracked churn is invisible, tracked change never is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from .canonical import canonical_json, digest_bytes, digest_json
from .errors import ProtectedPathViolation
from .models import Completeness, DriftSummary, Glob, Hash, PathStr

#: Version tag carried in the hash preimage. Changing what is hashed changes
#: this, so an old `snapshot_hash` can never be silently compared with a new one.
PREIMAGE_VERSION = "gr03.reality.1"

#: Paths no activation can make writable, and whose change is never
#: attributable to the runtime. Repository metadata is not workspace content.
PROTECTED_PATHS: tuple[Glob, ...] = (
    ".git",
    ".git/**",
    ".gitmodules",
    ".hg",
    ".hg/**",
    ".svn",
    ".svn/**",
)

#: Directory names a non-VCS walk never descends into. The same set the
#: fingerprint excludes for a VCS-backed root.
METADATA_DIRS: frozenset[str] = frozenset({".git", ".hg", ".svn"})

#: Scope of a whole-workspace observation.
WHOLE_WORKSPACE: tuple[Glob, ...] = ("**",)


# --- glob matching ---------------------------------------------------------


def _glob_regex(pattern: Glob) -> re.Pattern[str]:
    """Compile a POSIX glob over `Path` to a regex.

    `**` crosses separators, `*` and `?` do not, and a pattern naming a
    directory (`.git`) also matches everything beneath it only if it says so
    (`.git/**`). Nothing here is anchored to the filesystem: matching is over
    the workspace-relative path string alone.
    """
    out = ["^"]
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if pattern.startswith("**", index):
            out.append(".*")
            index += 2
            continue
        if char == "*":
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(char))
        index += 1
    out.append("$")
    return re.compile("".join(out))


def matches_glob(path: PathStr, pattern: Glob) -> bool:
    """True iff `path` matches `pattern`."""
    return _glob_regex(pattern).match(path) is not None


def matches_any(path: PathStr, patterns: Iterable[Glob]) -> bool:
    """True iff `path` matches at least one of `patterns`."""
    return any(matches_glob(path, pattern) for pattern in patterns)


# --- protected paths -------------------------------------------------------


def normalize_path(path: PathStr) -> PathStr:
    """Return `path` as a `Path` scalar (domain-model §0.1), or refuse it.

    A `Path` is workspace-rooted, POSIX, has no `..` segment and no leading
    `/`. A path that escapes the root is not a scope question — no grant can
    reach outside the workspace (`fs.read.outside_workspace` is `NEVER`) — so
    the refusal happens here, before any scope is consulted.
    """
    if not isinstance(path, str) or not path:
        raise ProtectedPathViolation(f"not a path: {path!r}")
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise ProtectedPathViolation(f"absolute path outside the workspace: {path!r}")
    parts = path.replace("\\", "/").split("/")
    if any(part == ".." for part in parts):
        raise ProtectedPathViolation(f"path escapes the workspace root: {path!r}")
    cleaned = "/".join(part for part in parts if part not in ("", "."))
    if not cleaned:
        raise ProtectedPathViolation(f"path names no file: {path!r}")
    return cleaned


def is_protected(path: PathStr, extra: Iterable[Glob] = ()) -> bool:
    """True iff `path` is repository metadata or a caller-declared protected path."""
    return matches_any(path, tuple(PROTECTED_PATHS) + tuple(extra))


def assert_unprotected(path: PathStr, extra: Iterable[Glob] = ()) -> PathStr:
    """Normalize `path` and refuse it if it is protected.

    Raises `ProtectedPathViolation`, which is not a policy verdict and not a
    scope miss: no capability, decision, or mode makes these paths writable.
    """
    cleaned = normalize_path(path)
    if is_protected(cleaned, extra):
        raise ProtectedPathViolation(
            f"{cleaned!r} is a protected path; no activation grants write access "
            "to repository metadata or outside the workspace root"
        )
    return cleaned


# --- the surface core requires of a VCS adapter ----------------------------


class RepositoryView:
    """What core needs to observe a repository (`vcs_kind = DVCS` or `CVCS`).

    Core never parses a revision id, a branch name, or a diff; they are
    `Str(1..128)`, `Str(1..256)` and bytes. An adapter implements this; nothing
    in core imports an adapter.
    """

    def head_revision(self) -> str:
        """The committed revision the working tree is based on."""
        raise NotImplementedError

    def current_branch(self) -> Optional[str]:
        """The checked-out line identifier, or `None` when detached."""
        raise NotImplementedError

    def file_index(self, revision_id: Optional[str] = None) -> Mapping[PathStr, Hash]:
        """Tracked path to content digest **as committed** at `revision_id`."""
        raise NotImplementedError

    def worktree_index(self) -> Mapping[PathStr, Hash]:
        """Tracked path to digest of the bytes **on disk**.

        Tracked paths deleted from the working tree are absent. Untracked and
        ignored files never appear.
        """
        raise NotImplementedError

    def untracked_count(self) -> int:
        """How many untracked, non-ignored files exist. Recorded, never hashed."""
        raise NotImplementedError

    def worktree_byte_count(self) -> int:
        """Total bytes of tracked content on disk. Recorded, never hashed."""
        raise NotImplementedError


# --- the fingerprint -------------------------------------------------------


@dataclass(frozen=True)
class RepositoryFingerprint:
    """One observation of repository reality, and its digests.

    Construct through :func:`observe_repository` or :func:`observe_filesystem`;
    the digests are derived here so there is one preimage, documented in the
    module docstring, rather than one per call site.
    """

    completeness: Completeness
    committed: Mapping[PathStr, Hash]
    dirty: Mapping[PathStr, Optional[Hash]]
    scope: tuple[Glob, ...] = WHOLE_WORKSPACE
    revision_id: Optional[str] = None
    target_ref: Optional[str] = None
    untracked_count: int = 0
    byte_count: int = 0

    @property
    def tree_digest(self) -> Hash:
        """Merkle root over the committed tracked index (domain-model §9.D)."""
        return digest_bytes(canonical_json(dict(self.committed)))

    @property
    def dirty_digest(self) -> Hash:
        """Digest over the working-tree deviations from `revision_id`.

        Load-bearing and not derivable from `tree_digest`: the committed index
        is what `CommitReceipt.actual_tree_digest` is compared against, so it
        must keep meaning "as committed". Uncommitted edits to tracked files
        live here and nowhere else.
        """
        return digest_bytes(canonical_json(dict(self.dirty)))

    def preimage(self) -> dict:
        """The exact members hashed into `snapshot_hash` (module docstring)."""
        return {
            "preimage_version": PREIMAGE_VERSION,
            "completeness": self.completeness.value,
            "scope": sorted(self.scope),
            "revision_id": self.revision_id,
            "target_ref": self.target_ref,
            "tree_digest": self.tree_digest,
            "dirty_digest": self.dirty_digest,
        }

    @property
    def snapshot_hash(self) -> Hash:
        """Digest of :meth:`preimage`. Equal for equal reality, by design."""
        return digest_json(self.preimage())

    def document(self) -> dict:
        """The `file_index_ref` payload: the whole observation, in full.

        The digests above are over slices of this document, so an auditor can
        recompute every one of them from the stored artifact alone.
        """
        return {
            "preimage_version": PREIMAGE_VERSION,
            "revision_id": self.revision_id,
            "target_ref": self.target_ref,
            "completeness": self.completeness.value,
            "scope": sorted(self.scope),
            "committed": dict(self.committed),
            "dirty": dict(self.dirty),
            "untracked_count": self.untracked_count,
            "byte_count": self.byte_count,
            "excluded": ["untracked", "ignored", *sorted(METADATA_DIRS)],
        }

    def effective_index(self) -> dict[PathStr, Hash]:
        """Committed content overlaid with the working tree.

        This — not the committed index — is what drift is computed over: a
        change a human made and did not commit is a change to reality.
        """
        return effective_index(self.committed, self.dirty)

    def vcs_state(self) -> Optional[dict]:
        """`RealitySnapshot.vcs_state` (domain-model §9.D), or `None`."""
        if self.revision_id is None:
            return None
        return {
            "revision_id": self.revision_id,
            "target_ref": self.target_ref or "",
            "dirty": bool(self.dirty),
            "untracked": self.untracked_count,
            "ahead": 0,
            "behind": 0,
        }


def effective_index(
    committed: Mapping[PathStr, Hash],
    dirty: Mapping[PathStr, Optional[Hash]],
) -> dict[PathStr, Hash]:
    """Apply working-tree deviations to a committed index. `None` = deleted."""
    index = dict(committed)
    for path, digest in dirty.items():
        if digest is None:
            index.pop(path, None)
        else:
            index[path] = digest
    return index


def derive_dirty(
    committed: Mapping[PathStr, Hash],
    worktree: Mapping[PathStr, Hash],
) -> dict[PathStr, Optional[Hash]]:
    """The working tree's deviations from the committed index.

    A tracked path present in both with differing content is dirty at its
    on-disk digest; one tracked but not yet committed is dirty at its digest;
    one committed but missing from the working tree is dirty at `None`.
    """
    dirty: dict[PathStr, Optional[Hash]] = {}
    for path, digest in worktree.items():
        if committed.get(path) != digest:
            dirty[path] = digest
    for path in committed:
        if path not in worktree:
            dirty[path] = None
    return dirty


def observe_repository(
    repo: RepositoryView,
    *,
    scope: Sequence[Glob] = WHOLE_WORKSPACE,
) -> RepositoryFingerprint:
    """Fingerprint a VCS-backed workspace through `repo`.

    Only tracked paths are read. An adapter failure is reported as
    `completeness = FAILED` rather than as an empty repository: absence of
    observation is never observation of absence (`RS-INV-1`).
    """
    try:
        revision_id = repo.head_revision()
        target_ref = repo.current_branch()
        committed = {
            path: digest
            for path, digest in repo.file_index(revision_id).items()
            if _in_scope(path, scope)
        }
        worktree = {
            path: digest
            for path, digest in repo.worktree_index().items()
            if _in_scope(path, scope)
        }
        untracked = repo.untracked_count()
        byte_count = repo.worktree_byte_count()
    except Exception:  # adapter failures are observations, not crashes
        return RepositoryFingerprint(
            completeness=Completeness.FAILED,
            committed={},
            dirty={},
            scope=tuple(scope),
        )
    return RepositoryFingerprint(
        completeness=Completeness.COMPLETE,
        committed=committed,
        dirty=derive_dirty(committed, worktree),
        scope=tuple(scope),
        revision_id=revision_id,
        target_ref=target_ref,
        untracked_count=untracked,
        byte_count=byte_count,
    )


def observe_filesystem(
    root: Path,
    *,
    scope: Sequence[Glob] = WHOLE_WORKSPACE,
) -> RepositoryFingerprint:
    """Fingerprint a workspace with no version control.

    Without a VCS there is no tracked set, so every file under `root` outside
    :data:`METADATA_DIRS` is content. Everything observed is reported as
    committed and nothing as dirty: with no revision to deviate from, "dirty"
    has no referent.
    """
    root = Path(root)
    index: dict[PathStr, Hash] = {}
    byte_count = 0
    if root.exists():
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if any(part in METADATA_DIRS for part in relative.parts):
                continue
            if not path.is_file():
                continue
            name = relative.as_posix()
            if not _in_scope(name, scope):
                continue
            data = path.read_bytes()
            index[name] = digest_bytes(data)
            byte_count += len(data)
    return RepositoryFingerprint(
        completeness=Completeness.COMPLETE,
        committed=index,
        dirty={},
        scope=tuple(scope),
        byte_count=byte_count,
    )


def _in_scope(path: PathStr, scope: Sequence[Glob]) -> bool:
    return not scope or matches_any(path, scope)


# --- HEAD and branch verification ------------------------------------------


@dataclass(frozen=True)
class HeadVerification:
    """Whether the repository is still where a record said it was."""

    matches: bool
    expected_revision: Optional[str]
    actual_revision: Optional[str]
    expected_ref: Optional[str] = None
    actual_ref: Optional[str] = None

    def reason(self) -> str:
        """Why it does not match, for the refusal message."""
        if self.expected_revision != self.actual_revision:
            return (
                f"HEAD is {self.actual_revision!r}, not the "
                f"{self.expected_revision!r} this was authorized against"
            )
        if self.expected_ref != self.actual_ref:
            return (
                f"the checked-out line is {self.actual_ref!r}, not the "
                f"{self.expected_ref!r} this was authorized against"
            )
        return "HEAD matches"


def verify_head(
    repo: RepositoryView,
    *,
    expected_revision: str,
    expected_ref: Optional[str] = None,
) -> HeadVerification:
    """Check the repository is at `expected_revision`, and on `expected_ref`.

    This is the check behind transition-matrix §9.3: applying a `CommitIntent`
    whose `base_revision_id` no longer matches reality is illegal, because the
    diff that was reviewed is not the diff that would land. A branch switch is
    caught for the same reason — the same revision on a different line is a
    different place to land a commit.
    """
    actual_revision = repo.head_revision()
    actual_ref = repo.current_branch()
    matches = actual_revision == expected_revision and (
        expected_ref is None or actual_ref == expected_ref
    )
    return HeadVerification(
        matches=matches,
        expected_revision=expected_revision,
        actual_revision=actual_revision,
        expected_ref=expected_ref,
        actual_ref=actual_ref,
    )


# --- drift ------------------------------------------------------------------


def changed_paths(
    before: Mapping[PathStr, Hash],
    after: Mapping[PathStr, Hash],
) -> tuple[frozenset[PathStr], frozenset[PathStr], frozenset[PathStr]]:
    """`(added, removed, modified)` between two effective indexes."""
    added = frozenset(after) - frozenset(before)
    removed = frozenset(before) - frozenset(after)
    modified = frozenset(
        path
        for path in frozenset(before) & frozenset(after)
        if before[path] != after[path]
    )
    return added, removed, modified


def is_attributable(path: PathStr, attributed: Sequence[Glob]) -> bool:
    """True iff a change at `path` is one the runtime declared it was making.

    A protected path is never attributable, whatever `attributed` says: the
    runtime cannot have authorized a mutation it is incapable of making, so a
    change there is always somebody else's.
    """
    if is_protected(path):
        return False
    return matches_any(path, attributed)


def unattributed_paths(
    before: Mapping[PathStr, Hash],
    after: Mapping[PathStr, Hash],
    *,
    attributed: Sequence[Glob] = (),
) -> tuple[PathStr, ...]:
    """Changed paths the runtime's own mutations do not account for.

    `attributed` names the paths the runtime declared it was changing — the
    paths of the `CommitIntent`s it has authorized. A change anywhere else
    happened outside runtime-mediated mutation, which is the definition of
    `REALITY_DRIFT` (domain-model §9.B.1).
    """
    added, removed, modified = changed_paths(before, after)
    return tuple(
        path
        for path in sorted(added | removed | modified)
        if not is_attributable(path, attributed)
    )


def derive_drift(
    before: Mapping[PathStr, Hash],
    after: Mapping[PathStr, Hash],
    *,
    attributed: Sequence[Glob] = (),
) -> DriftSummary:
    """`RealitySnapshot.drift_summary` between two effective indexes.

    A dirty tracked file shows up here exactly as a committed one does,
    because `after` is the *effective* index: uncommitted change is change.
    """
    added, removed, modified = changed_paths(before, after)
    return DriftSummary(
        added=len(added),
        removed=len(removed),
        modified=len(modified),
        unattributed=len(unattributed_paths(before, after, attributed=attributed)),
    )
