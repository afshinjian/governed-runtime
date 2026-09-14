"""Invocation-scoped tool authority. All writes are proposals (WP-2/WP-4).

The bridge never hands a worker a shell, a controller, secrets, or live paths.
It remains usable only while its durable lease and original activation hold.
"""
from dataclasses import dataclass
from datetime import datetime
import time

from .canonical import canonical_json
from .contracts import require
from .errors import CapabilityDenied, GovernedRuntimeError
from .models import EpistemicClass, SuspensionState
from .provider import ToolBridge, ToolResult
from .store import now_ts
from .worker_protocol import strict_json


TOOLS = {'fs.read': 'fs.read', 'fs.write': 'fs.write', 'fs.delete': 'fs.delete',
         'commit.propose': 'commit.propose', 'validation.request': 'validation.request'}


@dataclass(frozen=True)
class WorkerLease:
    lease_id: str
    invocation_id: str
    run_id: str
    controller_epoch: int
    expires_at: datetime
    session_id: str


class InvocationBridge(ToolBridge):
    def __init__(self, controller, invocation, request, lease, *, active=True):
        self._controller = controller
        self._invocation = invocation
        self._request = request
        self._lease = lease
        self._active = active
        self.violations = []
        self.scope_breaches = []
        self.calls = {}

    def close(self):
        self._active = False

    def _check(self):
        c, lease = self._controller, self._lease
        require(self._active, 'invocation lease is closed', CapabilityDenied)  # guard:gr07_bridge_closed
        require(now_ts() < lease.expires_at, 'invocation lease expired', CapabilityDenied)  # guard:gr07_bridge_expiry
        run = c.store.get_run(lease.run_id)
        require(c.store.get_project(run.project_id).controller_epoch == lease.controller_epoch,
                'invocation lease fenced by controller epoch', CapabilityDenied)  # guard:gr07_bridge_epoch
        require(run.suspension is SuspensionState.NONE, 'run is suspended', CapabilityDenied)  # guard:gr07_bridge_suspension
        c._assert_may_initiate_effect(run.project_id, 'worker tool')  # guard:gr07_bridge_observation

    def call(self, call):
        c, invocation = self._controller, self._invocation
        tick = time.monotonic()
        capability = TOOLS.get(call.tool_id)
        try:
            self._check()
            require(capability is not None and capability in self._request.granted_capabilities,
                    'tool absent from invocation grant', CapabilityDenied)  # guard:gr07_bridge_grant
            require(call.tool_id in {t.tool_id for t in self._request.tool_surface},
                    'tool absent from invocation surface', CapabilityDenied)  # guard:gr07_bridge_surface
            if call.call_id in self.calls:  # guard:gr07_tool_replay
                digest, prior = self.calls[call.call_id]
                require(digest == call.arguments_ref.digest, 'tool call identity reused', CapabilityDenied)  # guard:gr07_tool_identity
                return prior
            args = strict_json(c.store.artifact_bytes(call.arguments_ref.digest))
            fields = {'fs.read': {'path'}, 'fs.write': {'path', 'content'}, 'fs.delete': {'path'},
                      'commit.propose': {'path', 'content'}, 'validation.request': {'validation_spec_id', 'criterion_refs'}}
            require(type(args) is dict and set(args) == fields[call.tool_id], 'invalid tool arguments', CapabilityDenied)  # guard:gr07_tool_arguments
            path = args.get('path')
            c.require_authority(invocation.run_id, capability, path=path)  # guard:gr07_tool_authority
            if path is not None:  # guard:gr07_tool_path
                c._worker_path(invocation, path, write=call.tool_id != 'fs.read')
            if call.tool_id == 'fs.read':
                index = strict_json(c.store.artifact_bytes(self._request.scope_view.file_index_ref.digest))
                require(path in index, 'path absent from scope view', CapabilityDenied)  # guard:gr07_tool_read_scope
                ref = c.store.store_artifact(c.store.artifact_bytes(index[path]), media_type='application/octet-stream')
            else:
                if call.tool_id == 'validation.request':  # guard:gr07_tool_validation
                    c._worker_validation(invocation, args)
                # Proposal only. No repository operation, process or validation executes here.
                ref = c.store.store_artifact(canonical_json(args), media_type='application/json')
            result = ToolResult(call.call_id, 'OK', int((time.monotonic()-tick)*1000), result_ref=ref)
        except (GovernedRuntimeError, ValueError, KeyError, TypeError) as exc:
            detail = dict(capability=capability or call.tool_id, at=now_ts().isoformat(), detail=str(exc)[:1024])
            self.violations.append(detail)
            result = ToolResult(call.call_id, 'DENIED', int((time.monotonic()-tick)*1000), denial_capability=capability or call.tool_id)
        self.calls[call.call_id] = (call.arguments_ref.digest, result)
        c._append(c._project_of_run(invocation.run_id), event_type='worker.tool',
            epistemic_class=EpistemicClass.EVIDENCE, subject={'invocation_id': invocation.invocation_id},
            payload=dict(call_id=call.call_id, tool_id=call.tool_id, outcome=result.outcome,
                         arguments_digest=call.arguments_ref.digest), capability_used=capability)
        return result

    def progress(self, note):
        self._controller._append(self._controller._project_of_run(self._invocation.run_id),
            event_type='worker.progress', epistemic_class=EpistemicClass.CLAIM,
            subject={'invocation_id': self._invocation.invocation_id}, payload={'note': note})
