"""Kernel-owned, bounded subprocess transport for offline/model-broker workers.

The worker has a fresh empty home, no repository mount, no ambient environment,
no network and no writable host paths. A production inference broker can be
injected at the adapter boundary; credentials never enter InvocationRequest.
"""
from dataclasses import dataclass
from pathlib import Path
import os
import selectors
import signal
import subprocess
import tempfile
import time

from ..contracts import require
from ..provider import ProviderError
from ..canonical import canonical_json
from ..worker_protocol import RESULT_SCHEMA


@dataclass(frozen=True)
class ProcessResult:
    stdout: bytes
    stderr: bytes = b''
    returncode: int = 0
    timed_out: bool = False
    truncated: bool = False


class ProcessTransport:
    """Fixed executable selected by the operator, never by repository text.

    argv is adapter-owned. This transport deliberately has no network fallback.
    A broker transport must enforce its own fixed inference endpoint and expose
    worker tool calls only through the invocation bridge.
    """
    def __init__(self, executable, *, prefix=(), sandbox='/usr/bin/bwrap'):
        self.executable = str(Path(executable).resolve())
        self.prefix = tuple(prefix)
        self.sandbox = sandbox

    def run(self, argv, payload, *, timeout, max_output_bytes, cancelled=lambda: False):
        with tempfile.TemporaryDirectory(prefix='gr-worker-') as temporary:
            schema = Path(temporary) / 'result.schema.json'
            schema.write_bytes(canonical_json(RESULT_SCHEMA))
            command = [self.sandbox, '--unshare-all', '--die-with-parent', '--new-session', '--cap-drop', 'ALL']  # guard:gr07_process_isolation
            for path in ('/usr', '/bin', '/lib', '/lib64'):
                if Path(path).exists():
                    command += ['--ro-bind', path, path]
            command += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--tmpfs', '/home',
                '--dir', '/home/worker', '--chdir', '/home/worker', '--clearenv',
                '--setenv', 'HOME', '/home/worker', '--setenv', 'PATH', '/usr/local/bin:/usr/bin:/bin']  # guard:gr07_process_environment
            command += ['--', self.executable, *self.prefix, *argv]
            command[1:1] = ['--ro-bind', str(schema), '/result.schema.json']
            # File-backed stdin cannot deadlock against a child filling stdout.
            with tempfile.TemporaryFile() as input_file:
                input_file.write(payload)
                input_file.seek(0)
                with subprocess.Popen(command, stdin=input_file, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, env={}, start_new_session=True) as process:
                    streams = {process.stdout: bytearray(), process.stderr: bytearray()}
                    deadline = time.monotonic() + timeout
                    timed_out = truncated = False
                    try:
                        with selectors.DefaultSelector() as selector:
                            for stream in streams:
                                selector.register(stream, selectors.EVENT_READ)
                            while selector.get_map():
                                if time.monotonic() >= deadline or cancelled():  # guard:gr07_process_deadline
                                    timed_out = not cancelled()
                                    os.killpg(process.pid, signal.SIGKILL)
                                    break
                                for key, _ in selector.select(0.02):
                                    data = os.read(key.fileobj.fileno(), 65536)
                                    if not data:
                                        selector.unregister(key.fileobj)
                                        continue
                                    room = max_output_bytes - sum(map(len, streams.values()))
                                    streams[key.fileobj].extend(data[:max(0, room)])
                                    if len(data) > room:  # guard:gr07_process_output_bound
                                        truncated = True
                                        os.killpg(process.pid, signal.SIGKILL)
                                        break
                                if truncated:
                                    break
                    finally:
                        if process.poll() is None:  # guard:gr07_force_terminate
                            os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
            return ProcessResult(bytes(streams[process.stdout]), bytes(streams[process.stderr]),
                process.returncode, timed_out, truncated)
