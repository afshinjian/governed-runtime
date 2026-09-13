"""Controlled argv executor and runtime-produced validation evidence.

Requires Linux bubblewrap. An unavailable sandbox or unsupported network
allowlist produces ERROR; there is no unsandboxed fallback. READ_ONLY permits
no output files, SCRATCH permits /scratch, WORKSPACE_COPY permits writes only
to the disposable copy and /scratch. No policy permits host workspace writes.
"""
from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .canonical import digest_bytes, digest_json
from .errors import PolicyDenied
from .models import ActorKind, ActorRef, ArtifactRef, AuthMethod, Completeness, Encoding, RealitySnapshot, RetentionClass
from .repository import effective_index
from .store import now_ts
from .validation_catalog import ParameterRef, ParameterSchema, ValidationCatalog, ValidationOperation, contained, require

__all__ = ['ParameterRef', 'ParameterSchema', 'ValidationCatalog',
           'ValidationOperation', 'ValidationExecutor', 'ValidationReceipt']


@dataclass(frozen=True)
class ValidationReceipt:
    receipt_id: str
    op_id: str
    run_id: str
    operation_id: str
    operation_version: str
    operation_digest: str
    parameters: Mapping
    input_snapshot_id: str
    snapshot_hash: str
    executed_at: str
    duration_ms: int
    exit_code: int | None
    outcome: str
    stdout_ref: ArtifactRef
    stderr_ref: ArtifactRef
    env_digest: str
    toolchain_digest: str
    prev_event_hash: str
    executor_identity: ActorRef = field(default_factory=lambda: ActorRef(
        actor_kind=ActorKind.RUNTIME, actor_id='gruntime.validation', auth_method=AuthMethod.NONE))
    executor_version: str = '0.1.0'

    def __post_init__(self):
        object.__setattr__(self, 'parameters', MappingProxyType(dict(self.parameters)))

    @property
    def verdict(self):
        return self.outcome

    @property
    def operation_ref(self):
        return f'{self.operation_id}@{self.operation_version}'

    def document(self):
        return {k: dict(v) if k == 'parameters' else asdict(v) if isinstance(v, (ArtifactRef, ActorRef)) else v
                for k, v in vars(self).items()}

    @property
    def receipt_hash(self):
        return digest_json(self.document())

    @classmethod
    def from_document(cls, document):
        doc = dict(document)
        for key in ('stdout_ref', 'stderr_ref'):
            artifact = dict(doc[key])
            artifact['encoding'] = Encoding(artifact['encoding'])
            artifact['retention_class'] = RetentionClass(artifact['retention_class'])
            doc[key] = ArtifactRef(**artifact)
        identity = dict(doc['executor_identity'])
        identity['actor_kind'] = ActorKind(identity['actor_kind'])
        identity['auth_method'] = AuthMethod(identity['auth_method'])
        doc['executor_identity'] = ActorRef(**identity)
        return cls(**doc)


class ValidationExecutor:
    def __init__(self, catalog: ValidationCatalog, artifacts, *, environment=None):
        self.catalog = catalog
        self.artifacts = artifacts
        # Runtime configuration, captured once; never accepted on execute().
        self.environment = dict(os.environ if environment is None else environment)

    def execute(self, reference, parameters, *, snapshot: RealitySnapshot,
                snapshot_document, workspace_root: Path, run_id: str, op_id: str,
                prev_event_hash: str) -> ValidationReceipt:
        operation = self.catalog.resolve(reference)
        require(snapshot.completeness is Completeness.COMPLETE, 'validation requires COMPLETE observation')  # guard:executor_complete
        require(digest_json(snapshot_document) == snapshot.file_index_ref.digest, 'snapshot document is not bound to observation')  # guard:snapshot_document
        source = Path(workspace_root).resolve()
        normalized = operation.validate_parameters(parameters, source)
        cwd = contained(source, operation.cwd)
        require(cwd.is_dir(), 'catalog cwd is not an existing directory')  # guard:cwd_directory
        argv = [str(normalized[v.name]).lower() if isinstance(v, ParameterRef) and type(normalized[v.name]) is bool
                else str(normalized[v.name]) if isinstance(v, ParameterRef) else v for v in operation.argv]
        environment = dict(self.environment)
        environment = {key: value for key, value in environment.items() if key in operation.env_allowlist}  # guard:environment_allowlist
        started = now_ts().isoformat()
        tick = time.monotonic()
        exit_code, outcome, stdout, stderr = None, 'ERROR', b'', b''
        toolchain_digest = digest_bytes(Path(argv[0]).read_bytes()) if Path(argv[0]).is_file() else digest_json(argv[0])
        with tempfile.TemporaryDirectory(prefix='gr-validation-') as temporary:
            copy = Path(temporary) / 'workspace'
            copy.mkdir()
            index = effective_index(snapshot_document['committed'], snapshot_document['dirty'])
            for name, expected in index.items():
                original = contained(source, name)
                content = original.read_bytes()
                require(digest_bytes(content) == expected, 'workspace changed since input snapshot')  # guard:snapshot_content
                target = copy / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                target.chmod(original.stat().st_mode & 0o777)
            relative_cwd = cwd.relative_to(source)
            (copy / relative_cwd).mkdir(parents=True, exist_ok=True)
            try:
                require(operation.network != 'ALLOWLIST', 'network ALLOWLIST requires an enforcing adapter; unavailable')  # guard:network_allowlist
                command = ['/usr/bin/bwrap']
                command += ['--unshare-all', '--die-with-parent', '--new-session', '--cap-drop', 'ALL']  # guard:sandbox_isolation
                if operation.network == 'ANY':
                    command += ['--share-net']
                for system in ('/usr', '/bin', '/lib', '/lib64', '/etc'):
                    if Path(system).exists():
                        command += ['--ro-bind', system, system]
                command += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp']
                command += ['--remount-ro', '/tmp', '--remount-ro', '/dev', '--remount-ro', '/proc']  # guard:readonly_temporary
                mount = '--bind'
                if operation.write_policy != 'WORKSPACE_COPY':
                    mount = '--ro-bind'  # guard:workspace_readonly
                command += [mount, str(copy), '/workspace']
                if operation.write_policy in ('SCRATCH', 'WORKSPACE_COPY'):
                    command += ['--tmpfs', '/scratch']
                command += ['--clearenv', '--chdir', '/workspace/' + relative_cwd.as_posix()]  # guard:sandbox_context
                for key, value in environment.items():
                    command += ['--setenv', key, value]
                command += ['--', *argv]
                # Keep this explicit: shell metacharacters are literal argv bytes.
                with subprocess.Popen(command,
                                      shell=False,  # guard:no_shell
                                      stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, env={}, start_new_session=True) as process:
                    try:
                        stdout, stderr = process.communicate(
                            timeout=operation.timeout_ms / 1000,  # guard:process_timeout
                        )
                        exit_code = process.returncode
                        outcome = 'PASS' if exit_code in operation.expected_exit_codes else 'FAIL'
                        if stderr.startswith(b'bwrap:'):
                            outcome = 'ERROR'
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        stdout, stderr = process.communicate()
                        exit_code, outcome = process.returncode, 'TIMEOUT'
            except (OSError, PolicyDenied) as exc:
                stderr = str(exc).encode()
        return ValidationReceipt(
            receipt_id=f'vr-{uuid.uuid4().hex}', op_id=op_id, run_id=run_id,
            operation_id=operation.operation_id, operation_version=operation.version,
            operation_digest=operation.digest, parameters=dict(parameters),
            input_snapshot_id=snapshot.snapshot_id, snapshot_hash=snapshot.snapshot_hash,
            executed_at=started, duration_ms=int((time.monotonic() - tick) * 1000),
            exit_code=exit_code, outcome=outcome,
            stdout_ref=self.artifacts.put(stdout, media_type='text/plain'),
            stderr_ref=self.artifacts.put(stderr, media_type='text/plain'),
            env_digest=digest_json(environment), toolchain_digest=toolchain_digest,
            prev_event_hash=prev_event_hash)
