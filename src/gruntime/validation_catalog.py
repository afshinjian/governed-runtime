"""GR-09 catalog. Frozen design basis: CommandSpec, WP-3, V-INV-1/2.

The catalog is trusted runtime configuration. Contracts pin an id@SemVer and
its digest; callers can supply only values for the declared parameter schema.
No command text is interpolated, split, formatted, or passed to a shell.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .canonical import canonical_json, digest_json
from .errors import PolicyDenied

REFERENCE = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}@(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")


def require(condition, reason):
    """Fail closed with the same refusal taxonomy at every boundary."""
    if not condition:  # guard:policy_refusal
        raise PolicyDenied(reason)


def text_ok(value):
    return type(value) is str and 0 < len(value) <= 4096 and not any(ord(c) < 32 or ord(c) == 127 for c in value)


def relative_path(value):
    return text_ok(value) and not value.startswith('/') and '\\' not in value and all(p not in ('', '.', '..') for p in value.split('/'))


def contained(root: Path, value: str) -> Path:
    require(relative_path(value), "path must be relative without traversal")  # guard:path_syntax
    target = (root / value).resolve()
    require(target.is_relative_to(root.resolve()), "canonical path escapes declared root")  # guard:path_containment
    return target


@dataclass(frozen=True)
class ParameterSchema:
    kind: str
    root: str | None = None
    minimum: int = 0
    maximum: int = 4096
    choices: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, 'choices', tuple(self.choices))
        valid = (self.kind in ('string', 'integer', 'boolean', 'path')
                 and type(self.minimum) is int and type(self.maximum) is int
                 and self.minimum <= self.maximum
                 and all(text_ok(v) for v in self.choices)
                 and ((self.kind == 'path' and relative_path(self.root))
                      or (self.kind != 'path' and self.root is None)))
        require(valid, "invalid typed parameter schema")  # guard:parameter_schema

    def validate(self, value, workspace: Path | None = None):
        valid_type = (type(value) is {'string': str, 'path': str, 'integer': int, 'boolean': bool}[self.kind])
        require(valid_type, "parameter has wrong type")  # guard:parameter_type
        if self.kind in ('string', 'path'):
            valid = text_ok(value) and self.minimum <= len(value) <= self.maximum and (not self.choices or value in self.choices)
        elif self.kind == 'integer':
            valid = self.minimum <= value <= self.maximum
        else:
            valid = True
        require(valid, "parameter violates constraints")  # guard:parameter_constraints
        if self.kind == 'path':
            require(relative_path(value), "path parameter contains traversal")  # guard:parameter_path
            if workspace is not None:
                root = contained(workspace, self.root)
                target = contained(root, value)
                return '/workspace/' + target.relative_to(workspace.resolve()).as_posix()
        return value


@dataclass(frozen=True)
class ParameterRef:
    name: str


@dataclass(frozen=True)
class ValidationOperation:
    operation_id: str
    version: str
    argv: tuple[str | ParameterRef, ...]
    parameters: Mapping[str, ParameterSchema]
    cwd: str
    env_allowlist: tuple[str, ...]
    network: str
    timeout_ms: int
    write_policy: str
    side_effect_class: str
    safe_to_rerun: bool
    expected_exit_codes: tuple[int, ...] = (0,)

    def __post_init__(self):
        object.__setattr__(self, 'argv', tuple(self.argv))
        object.__setattr__(self, 'parameters', MappingProxyType(dict(self.parameters)))
        object.__setattr__(self, 'env_allowlist', tuple(self.env_allowlist))
        object.__setattr__(self, 'expected_exit_codes', tuple(self.expected_exit_codes))
        require(type(self.operation_id) is str and type(self.version) is str and REFERENCE.fullmatch(self.reference), "operation requires id@SemVer")  # guard:operation_reference
        valid_argv = (bool(self.argv) and len(self.argv) <= 128
                      and type(self.argv[0]) is str and Path(self.argv[0]).is_absolute()
                      and all(text_ok(v) if type(v) is str else isinstance(v, ParameterRef) and v.name in self.parameters for v in self.argv))
        require(valid_argv, "argv requires a fixed absolute executable and declared parameter refs")  # guard:argv_schema
        # Pin the actual executable rather than a virtualenv/symlink alias that
        # would not exist in the isolated filesystem.
        object.__setattr__(self, 'argv', (str(Path(self.argv[0]).resolve()), *self.argv[1:]))
        valid_parameters = all(type(k) is str and NAME.fullmatch(k) and isinstance(v, ParameterSchema) for k, v in self.parameters.items())
        require(valid_parameters, "invalid parameter names or schemas")  # guard:parameter_names
        valid_policy = (relative_path(self.cwd)
                        and all(type(k) is str and re.fullmatch(r'[A-Z_][A-Z0-9_]{0,127}', k) for k in self.env_allowlist)
                        and len(set(self.env_allowlist)) == len(self.env_allowlist)
                        and self.network in ('NONE', 'ANY', 'ALLOWLIST')
                        and type(self.timeout_ms) is int and 1 <= self.timeout_ms <= 86400000
                        and self.write_policy in ('READ_ONLY', 'SCRATCH', 'WORKSPACE_COPY')
                        and self.side_effect_class in ('READ_ONLY', 'SANDBOX_WRITE', 'EXTERNAL')
                        and type(self.safe_to_rerun) is bool
                        and bool(self.expected_exit_codes)
                        and all(type(c) is int and 0 <= c <= 255 for c in self.expected_exit_codes))
        require(valid_policy, "invalid catalog execution policy")  # guard:execution_policy
        consistent = ((self.side_effect_class != 'READ_ONLY' or self.write_policy == 'READ_ONLY')
                      and (self.network == 'NONE' or self.side_effect_class == 'EXTERNAL'))
        require(consistent, "side effect declaration understates execution policy")  # guard:side_effect_policy

    @property
    def reference(self):
        return f'{self.operation_id}@{self.version}'

    def document(self):
        return dict(operation_id=self.operation_id, version=self.version,
                    argv=[{'parameter': v.name} if isinstance(v, ParameterRef) else v for v in self.argv],
                    parameters={k: asdict(v) for k, v in self.parameters.items()},
                    cwd=self.cwd, env_allowlist=list(self.env_allowlist), network=self.network,
                    timeout_ms=self.timeout_ms, write_policy=self.write_policy,
                    side_effect_class=self.side_effect_class, safe_to_rerun=self.safe_to_rerun,
                    expected_exit_codes=list(self.expected_exit_codes))

    @property
    def digest(self):
        return digest_json(self.document())

    @classmethod
    def from_document(cls, document):
        doc = dict(document)
        doc['argv'] = tuple(ParameterRef(v['parameter']) if isinstance(v, dict) else v for v in doc['argv'])
        doc['parameters'] = {k: ParameterSchema(**v) for k, v in doc['parameters'].items()}
        return cls(**doc)

    def validate_parameters(self, values, workspace=None):
        require(set(values) == set(self.parameters), "missing or unknown parameters")  # guard:parameter_set
        return {k: schema.validate(values[k], workspace) for k, schema in self.parameters.items()}


class ValidationCatalog:
    """Append-only versioned catalog, durable across controller restarts."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS operations (reference TEXT PRIMARY KEY, document TEXT NOT NULL) STRICT')

    def register(self, operation: ValidationOperation):
        document = canonical_json(operation.document()).decode()
        with sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT document FROM operations WHERE reference=?', (operation.reference,)).fetchone()
            require(row is None or row[0] == document, "catalog versions are immutable")  # guard:catalog_immutable
            db.execute('INSERT OR IGNORE INTO operations VALUES (?, ?)', (operation.reference, document))
        return operation.reference

    def resolve(self, reference: str) -> ValidationOperation:
        require(type(reference) is str and REFERENCE.fullmatch(reference), "explicit id@version required; latest is forbidden")  # guard:resolve_version
        with sqlite3.connect(self.path) as db:
            row = db.execute('SELECT document FROM operations WHERE reference=?', (reference,)).fetchone()
        require(row is not None, "unknown validation operation")  # guard:resolve_known
        operation = ValidationOperation.from_document(json.loads(row[0]))
        require(operation.reference == reference, "catalog identity mismatch")  # guard:catalog_identity
        return operation
