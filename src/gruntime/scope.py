"""Workspace-relative, component-aware scope matching and containment.

Canonical spelling and resolved targets must both match. Gitlinks are supplied
by the repository adapter, including uninitialized submodules; nested checkouts
are also boundaries. No symlink may bypass an exclusion or the workspace root.
"""
from functools import lru_cache
from fnmatch import fnmatchcase
from pathlib import Path
import re
import unicodedata

from .contracts import require
from .errors import CapabilityDenied, ProtectedPathViolation
from .repository import assert_unprotected


def canonical_pattern(value):
    valid = (type(value) is str and 0 < len(value) <= 1024
             and not value.startswith("/") and not re.match(r"^[A-Za-z]:", value)
             and "\\" not in value and unicodedata.normalize("NFC", value) == value
             and not any(ord(c) < 32 or ord(c) == 127 for c in value)
             and all(p not in ("", ".", "..") for p in value.split("/")))
    require(valid, "path must be canonical, relative and without traversal", ProtectedPathViolation)  # guard:gr06_path_syntax
    return value


def matches(path, pattern):
    parts, pats = tuple(path.split("/")), tuple(pattern.split("/"))

    @lru_cache(None)
    def match(i, j):
        if j == len(pats):
            return i == len(parts)
        if pats[j] == "**":
            return match(i, j + 1) or (i < len(parts) and match(i + 1, j))
        return i < len(parts) and fnmatchcase(parts[i], pats[j]) and match(i + 1, j + 1)

    return match(0, 0)


def in_scope(path, includes, excludes):
    return any(matches(path, p) for p in includes) and not any(matches(path, p) for p in excludes)


def canonical_path(root, path, *, submodules=()):
    canonical_pattern(path)
    root = Path(root).resolve()
    try:
        target = (root / path).resolve()
    except (OSError, RuntimeError) as exc:
        raise ProtectedPathViolation("unresolvable path") from exc
    require(target.is_relative_to(root), "symlink escapes workspace", ProtectedPathViolation)  # guard:gr06_symlink_escape
    resolved = target.relative_to(root).as_posix()
    for spelling in (path, resolved):
        parts = spelling.split("/")
        prefixes = ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]
        crosses = any(p in submodules or (root / p / ".git").exists() for p in prefixes)
        require(not crosses, "submodule or nested repository escape", ProtectedPathViolation)  # guard:gr06_submodule_escape
    return resolved


def authorize_path(contract, root, path, *, submodules=(), outside_scope=False, write=False):
    resolved = canonical_path(root, path, submodules=submodules)
    if write:
        assert_unprotected(path)  # guard:gr06_lexical_protection
        assert_unprotected(resolved)  # guard:gr06_resolved_protection
    allowed = outside_scope or all(in_scope(p, contract.scope_include, contract.scope_exclude) for p in (path, resolved))
    require(allowed, "path is outside activated contract scope", CapabilityDenied)  # guard:gr06_scope
    return resolved
