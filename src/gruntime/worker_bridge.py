"""Invocation-scoped tool authority. All writes are proposals (WP-2/WP-4).

The bridge never hands a worker a shell, a controller, secrets, or live paths.
It remains usable only while its durable lease and original activation hold.
"""
from dataclasses import dataclass
from datetime import datetime
import http.client
import time

from .canonical import canonical_json
from .contracts import require
from .errors import CapabilityDenied, GovernedRuntimeError
from .models import EpistemicClass, SuspensionState
from .provider import ToolBridge, ToolResult
from .store import now_ts
from .worker_protocol import strict_json
from .inference_relay import CAPABILITY, TOOL
from .secret_guard import SecretLeak


TOOLS = {'fs.read': 'fs.read', 'fs.write': 'fs.write', 'fs.delete': 'fs.delete',
         'commit.propose': 'commit.propose', 'validation.request': 'validation.request', TOOL: CAPABILITY}


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
        self.secret_failure = False

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
            c.secret_guard.check(call)  # guard:gr08_tool_metadata
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
                      'commit.propose': {'path', 'content'}, 'validation.request': {'validation_spec_id', 'criterion_refs'},
                      TOOL: {'url', 'method', 'headers', 'body'}}
            require(type(args) is dict and set(args) == fields[call.tool_id], 'invalid tool arguments', CapabilityDenied)  # guard:gr07_tool_arguments
            path = args.get('path')
            c.require_authority(invocation.run_id, capability, path=path)  # guard:gr07_tool_authority
            if path is not None:  # guard:gr07_tool_path
                c._worker_path(invocation, path, write=call.tool_id != 'fs.read')
            if call.tool_id == TOOL:
                relay = c._inference_relay
                require(relay is not None and relay.run_id == invocation.run_id,
                        'RELAY_UNAVAILABLE', CapabilityDenied)  # guard:gr08_relay_binding
                response = relay.execute(args, authorize=self._network_authority,
                    timeout=(self._lease.expires_at - now_ts()).total_seconds())
                ref = c.store.store_artifact(canonical_json(response), media_type='application/json')
            elif call.tool_id == 'fs.read':
                index = strict_json(c.store.artifact_bytes(self._request.scope_view.file_index_ref.digest))
                require(path in index, 'path absent from scope view', CapabilityDenied)  # guard:gr07_tool_read_scope
                ref = c.store.store_artifact(c.store.artifact_bytes(index[path]), media_type='application/octet-stream')
            else:
                if call.tool_id == 'validation.request':  # guard:gr07_tool_validation
                    c._worker_validation(invocation, args)
                # Proposal only. No repository operation, process or validation executes here.
                ref = c.store.store_artifact(canonical_json(args), media_type='application/json')
            result = ToolResult(call.call_id, 'OK', int((time.monotonic()-tick)*1000), result_ref=ref)
        except (GovernedRuntimeError, ValueError, KeyError, TypeError, OSError, http.client.HTTPException) as exc:
            try:
                c.secret_guard.check((str(exc), call.call_id, call.tool_id))  # guard:gr08_tool_diagnostic
            except SecretLeak as safe:
                exc = safe
            if isinstance(exc, SecretLeak):
                self.secret_failure = True
                # Discard identifiers as well: a worker may plant secrets there.
                safe_ref = c.store.store_artifact(b'{"error":"SECRET_LEAK"}', media_type='application/json')
                call = type(call)('discarded', TOOL if capability == CAPABILITY else 'discarded', safe_ref, call.requested_at)
            detail = dict(capability=capability or call.tool_id, at=now_ts().isoformat(), detail=str(exc)[:1024])
            self.violations.append(detail)
            result = ToolResult(call.call_id, 'DENIED', int((time.monotonic()-tick)*1000), denial_capability=capability or call.tool_id)
        self.calls[call.call_id] = (call.arguments_ref.digest, result)
        c._append(c._project_of_run(invocation.run_id), event_type='worker.tool',
            epistemic_class=EpistemicClass.AUTHORITY if result.outcome == 'DENIED' else EpistemicClass.EVIDENCE, subject={'invocation_id': invocation.invocation_id},
            payload=dict(call_id=call.call_id, tool_id=call.tool_id, outcome=result.outcome,
                         arguments_digest=call.arguments_ref.digest), capability_used=capability)
        return result

    def _network_authority(self):
        self._check()
        require(CAPABILITY in self._request.granted_capabilities,
                'RELAY_GRANT_DENIED', CapabilityDenied)  # guard:gr08_network_grant
        self._controller.require_authority(self._invocation.run_id, CAPABILITY)  # guard:gr08_network_live

    def request_network(self, method, path, headers, body):
        """Kernel HTTP listener translates one worker request to ToolBridge.call."""
        import uuid
        from .provider import ToolCall
        c = self._controller
        relay = c._inference_relay
        require(relay is not None and path.startswith('/') and not path.startswith('//'),
                'RELAY_DESTINATION_DENIED', CapabilityDenied)  # guard:gr08_local_target
        try:
            args = dict(url=relay.origin + path, method=method, headers=headers, body=body.decode('utf-8'))
            ref = c.store.store_artifact(canonical_json(args), media_type='application/json')
            result = self.call(ToolCall(str(uuid.uuid4()), TOOL, ref, now_ts()))
            if result.outcome != 'OK':
                raise CapabilityDenied('SECRET_LEAK' if self.secret_failure else 'RELAY_DENIED')
            return strict_json(c.store.artifact_bytes(result.result_ref.digest))
        except SecretLeak:
            self.secret_failure = True
            raise

    def progress(self, note):
        try:
            self._controller.secret_guard.check(note)  # guard:gr08_progress
        except SecretLeak:
            note = 'SECRET_LEAK'
            self.secret_failure = True
        self._controller._append(self._controller._project_of_run(self._invocation.run_id),
            event_type='worker.progress', epistemic_class=EpistemicClass.CLAIM,
            subject={'invocation_id': self._invocation.invocation_id}, payload={'note': note})
