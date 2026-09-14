"""Controller-owned worker dispatch, leases, proposal checks and provenance."""
from dataclasses import asdict, replace
from datetime import timedelta
from pathlib import Path
import time
import uuid

from .authority import REGISTER, parse_ts
from .canonical import canonical_json, digest_bytes, digest_json
from .contracts import require
from .errors import BarrierViolation, CapabilityDenied, IntegrityViolation, PolicyDenied, GovernedRuntimeError
from .gate import AFTER_INVOKE_BEFORE_RECEIPT, gate
from .models import (Attribution, Budget, Claim, Completeness, EpistemicClass, Independence,
    InvocationStatus, MutationOp, MutationProposal, OutcomeStatus, ReconciliationState,
    SuspensionState, TerminationReason, Usage, WorkerInvocation, WorkerRole)
from .provider import (DISPATCH_CAPABILITIES, GovernedProvider, InvocationRequest,
    ProviderError, ScopeView, ToolCall, ToolDescriptor, WorkerProvider, status_for_outcome)
from .repository import effective_index
from .reconciliation import derive_reconciliation_state
from .scope import authorize_path, in_scope
from .store import now_ts
from .worker_bridge import InvocationBridge, TOOLS, WorkerLease
from .worker_protocol import request_bytes, request_from_bytes, result_document, strict_json


class WorkerController:
    def cancel_invocation(self, invocation_id, *, reason='HUMAN_STOP'):
        invocation = self.store.get_invocation(invocation_id)
        result = GovernedProvider(self._worker_provider(invocation), {'run.abort'}).cancel(invocation_id, reason)
        self._append(self._project_of_run(invocation.run_id), event_type='worker.cancel_requested',
            epistemic_class=EpistemicClass.AUTHORITY, subject={'invocation_id': invocation_id},
            payload=dict(reason=reason, acknowledged=result.acknowledged), capability_used='run.abort')
        return result

    def register_provider(self, provider):
        require(type(provider).lookup is not WorkerProvider.lookup and callable(provider.lookup),
                'governed providers must implement lookup', PolicyDenied)  # guard:gr07_lookup_registration
        descriptor = provider.describe()
        provider.secret_guard = self.secret_guard
        if hasattr(provider, 'artifacts'):
            provider.artifacts.secret_guard = self.secret_guard
        self.providers[descriptor.provider_id] = provider
        return descriptor.provider_id

    def _worker_provider(self, invocation):
        provider = self.providers.get(invocation.provider_id)
        require(provider is not None and provider.describe().provider_version == invocation.provider_version,
                'pinned provider unavailable', PolicyDenied)  # guard:gr07_provider_pin
        return provider

    def _worker_contract(self, run_id):
        activation = self.store.activation_for_run(run_id)
        require(activation is not None, 'unactivated run grants nothing', CapabilityDenied)  # guard:gr07_activation
        contract = self.store.get_contract(activation.contract_id)
        require(contract.status == 'ACTIVE' and now_ts() < parse_ts(activation.expires_at),
                'worker activation is no longer live', CapabilityDenied)  # guard:gr07_activation_live
        require(all(REGISTER.get(cap, ('NEVER',))[0] == 'ORD' for cap in activation.granted_capabilities),
                'workers may receive only ORD capabilities', CapabilityDenied)  # guard:gr07_worker_classes
        for capability in activation.granted_capabilities:
            self.require_authority(run_id, capability, _grant_only=True)  # guard:gr07_activation_replay
        return contract, activation

    def _worker_gate(self, run_id):
        run = self.store.get_run(run_id)
        self._assert_barrier_clear(run_id, 'worker dispatch')  # guard:gr07_dispatch_barrier
        self._assert_may_initiate_effect(run.project_id, 'worker dispatch')  # guard:gr07_dispatch_observation
        require(run.suspension is SuspensionState.NONE, 'run is suspended', PolicyDenied)  # guard:gr07_run_suspension
        snapshot = self.store.latest_snapshot(run.project_id)
        require(snapshot is not None and snapshot.completeness is Completeness.COMPLETE,
                'worker requires COMPLETE observation', PolicyDenied)  # guard:gr07_snapshot
        return run, snapshot

    def create_invocation(self, run_id, *, prompt, provider_id=None, binding_id='default',
                          context_refs=(), author_invocation_id=None):
        run, snapshot = self._worker_gate(run_id)
        contract, activation = self._worker_contract(run_id)
        provider_id = provider_id or self.provider.describe().provider_id
        require(provider_id in self.providers, 'provider not registered', PolicyDenied)  # guard:gr07_registered
        provider = self.providers[provider_id]
        descriptor = provider.describe()
        role = WorkerRole(contract.worker_role)
        require(role in descriptor.supported_roles, 'UNSUPPORTED_ROLE', PolicyDenied)  # guard:gr07_role
        require(binding_id in {b.binding_id for b in descriptor.bindings}, 'UNKNOWN_BINDING', PolicyDenied)  # guard:gr07_binding
        prior = self.store.list_invocations(run_id)
        require(len(prior) < contract.budget_ceiling['worker_invocations'], 'worker budget exhausted', PolicyDenied)  # guard:gr07_invocation_budget
        refused = any(i.provider_id == provider_id and i.execution_binding == binding_id
            and any(r.termination_reason is TerminationReason.REFUSAL for r in self.store.list_worker_receipts(i.invocation_id)) for i in prior)
        require(not refused, 'refused binding cannot be retried in this run', PolicyDenied)  # guard:gr07_refusal_retry
        invocation_id = f'inv-{uuid.uuid4().hex}'
        session_id = str(uuid.uuid4())
        project = self.store.get_project(run.project_id)
        root = Path(project.workspace_root).resolve()
        index = effective_index(**{k: self.store.snapshot_document(snapshot)[k] for k in ('committed', 'dirty')})
        if 'fs.read' not in activation.granted_capabilities:  # guard:gr07_context_read
            index = {}
        view_index = {}
        for path, expected in index.items():
            if not in_scope(path, contract.scope_include, contract.scope_exclude):  # guard:gr07_context_scope
                continue
            source = root / path
            # Runtime-owned stores are never worker context, even for a non-VCS project.
            if source == self.store.db_path or any(source.is_relative_to(p) for p in
                (self.artifacts.root, self.store.artifacts.root)) or source.name in ('state.db-wal', 'state.db-shm'):  # guard:gr07_internal_context
                continue
            authorize_path(contract, root, path)
            data = source.read_bytes()
            require(digest_bytes(data) == expected, 'scope changed since snapshot', PolicyDenied)  # guard:gr07_scope_snapshot
            view_index[path] = self.store.store_artifact(data, media_type='application/octet-stream').digest
        index_ref = self.store.store_artifact(canonical_json(view_index), media_type='application/json')
        # A pathless materialized view: the adapter reads these content addresses via
        # its input broker. It is never handed the live repository root.
        prompt_ref = self.store.store_artifact(canonical_json(dict(
            contract_hash=contract.contract_hash, objective=contract.objective,
            instructions=prompt.decode('utf-8'), worker_role=role.value,
            repository_content_trust='UNTRUSTED_DATA', file_index=view_index)), media_type='application/json')
        context_refs = tuple(context_refs)
        context_digest = digest_json([prompt_ref.digest, *[r.digest for r in context_refs]])
        require(sum(len(self.store.artifact_bytes(r.digest)) for r in (prompt_ref, *context_refs))
                + sum(len(self.store.artifact_bytes(d)) for d in view_index.values()) <= descriptor.max_context_bytes,
                'CONTEXT_TOO_LARGE', PolicyDenied)  # guard:gr07_context_budget
        schema_ref = self.store.store_artifact(b'{"type":"object"}', media_type='application/json')
        granted = frozenset(activation.granted_capabilities)
        request = InvocationRequest(invocation_id=invocation_id, worker_role=role, binding_id=binding_id,
            prompt_bundle_ref=prompt_ref, scope_view=ScopeView(root='artifact://scope', file_index_ref=index_ref,
                snapshot_id=snapshot.snapshot_id, writable=False, include=tuple(contract.scope_include), exclude=tuple(contract.scope_exclude)),
            idempotency_key='', deadline_at=parse_ts(activation.expires_at), context_refs=context_refs,
            granted_capabilities=granted, tool_surface=tuple(ToolDescriptor(t, cap, schema_ref, schema_ref, t != 'fs.read')
                for t, cap in TOOLS.items() if cap in granted), budget=Budget(**contract.budget_ceiling),
            session_id=session_id, fresh_session=True, contract_hash=contract.contract_hash)
        request = replace(request, idempotency_key=digest_bytes(request_bytes(request)))
        ref = self.store.store_artifact(request_bytes(request), media_type='application/json')
        invocation = WorkerInvocation(invocation_id=invocation_id, run_id=run_id, stage_id=run.stage_id,
            provider_id=provider_id, provider_version=descriptor.provider_version, worker_role=role,
            prompt_bundle_ref=prompt_ref, request_ref=ref, request_digest=ref.digest,
            context_digest=context_digest, idempotency_key=request.idempotency_key,
            controller_epoch=project.controller_epoch, status=InvocationStatus.PENDING,
            reconciliation_state=derive_reconciliation_state(record_epoch=project.controller_epoch,
                project_epoch=project.controller_epoch, status_terminal=False), execution_binding=binding_id,
            context_refs=context_refs, granted_capabilities=granted, budget_allocated=request.budget,
            deadline_at=request.deadline_at, sandbox_profile_id='worker-proposal-only')
        if author_invocation_id is not None:
            self._check_worker_independence(invocation, request, author_invocation_id)
        db = self.store.connection
        db.execute('BEGIN IMMEDIATE')
        try:
            self._append(run.project_id, event_type='invocation.created', epistemic_class=EpistemicClass.AUTHORITY,
                subject={'invocation_id': invocation_id, 'run_id': run_id},
                payload=dict(idempotency_key=request.idempotency_key, request_digest=ref.digest,
                    controller_epoch=project.controller_epoch, activation_id=activation.activation_id,
                    author_invocation_id=author_invocation_id), capability_used='worker.invoke')
            self.store.put_invocation(invocation, run.project_id)
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK')
            raise
        return invocation

    def _request_for(self, invocation):
        return request_from_bytes(self.store.artifact_bytes(invocation.request_digest))

    def _worker_path(self, invocation, path, *, write=True):
        contract = self.store.get_contract(self.store.activation_for_run(invocation.run_id).contract_id)
        root = self.store.get_project(self._project_of_run(invocation.run_id)).workspace_root
        authorize_path(contract, root, path, write=write)  # guard:gr07_proposal_scope
        # Roadmap mutation is a distinct authority, never implied by fs.write.
        roadmap = any(Path(part).stem.lower() == 'roadmap' for part in Path(path).parts)
        require(not write or not roadmap, 'worker cannot modify the roadmap', CapabilityDenied)  # guard:gr07_roadmap

    def _worker_validation(self, invocation, draft):
        contract = self.store.get_contract(self.store.activation_for_run(invocation.run_id).contract_id)
        specs = {s['spec_id'] for s in contract.required_validations}
        criteria = {c['criterion_id'] for c in contract.acceptance_criteria if c['verifier_ref'] == draft['validation_spec_id']}
        require(draft['validation_spec_id'] in specs and set(draft['criterion_refs']) <= criteria,
                'validation is not bound to this contract', CapabilityDenied)  # guard:gr07_validation_pin

    def _check_worker_independence(self, reviewer, request, author_id):
        author = self.store.get_invocation(author_id)
        author_request = self._request_for(author)
        require(reviewer.stage_id == author.stage_id, 'review author belongs to another stage', PolicyDenied)  # guard:gr07_review_stage
        require(reviewer.worker_role is WorkerRole.REVIEWER and author.worker_role is WorkerRole.IMPLEMENTER,
                'ROLE_SEPARATED required', PolicyDenied)  # guard:gr07_review_role
        require(reviewer.invocation_id != author_id and request.fresh_session and request.session_id
                and request.session_id != author_request.session_id, 'FRESH_SESSION required; self-review refused', PolicyDenied)  # guard:gr07_review_session
        require(reviewer.provider_id != author.provider_id, 'PROVIDER_DISTINCT_FROM_AUTHOR required', PolicyDenied)  # guard:gr07_review_provider
        require(reviewer.prompt_bundle_ref.digest != author.prompt_bundle_ref.digest
                and reviewer.context_digest != author.context_digest
                and not ({r.digest for r in reviewer.context_refs} & {r.digest for r in author.context_refs}),
                'review shares author context', PolicyDenied)  # guard:gr07_review_context
        return Independence.INDEPENDENT

    def record_worker_review(self, invocation_id, author_invocation_id, *, review_spec_id, verdict):
        """Accept a worker judgement only after measuring all three independence axes.

        This is the worker-facing review entry point. record_review remains the
        trusted kernel's CLAIM import primitive, and is never on a tool surface.
        """
        from .models import ReviewerKind
        invocation = self.store.get_invocation(invocation_id)
        request = self._request_for(invocation)
        independence = self._check_worker_independence(invocation, request, author_invocation_id)
        receipts = self.store.list_worker_receipts(invocation_id)
        require(invocation.status is InvocationStatus.COMPLETED and len(receipts) == 1,
                'review requires completed invocation receipt', PolicyDenied)  # guard:gr07_review_receipt
        document = result_document(self.store.artifact_bytes(receipts[0].output_digest), invocation_id)
        self._worker_session(request, document)
        contract, _ = self._worker_contract(invocation.run_id)
        require(review_spec_id in {s['spec_id'] for s in contract.required_reviews},
                'review spec absent from contract', PolicyDenied)  # guard:gr07_review_spec
        require(document['review'] == dict(review_spec_id=review_spec_id, verdict=verdict.value),
                'review verdict differs from structured worker judgement', PolicyDenied)  # guard:gr07_review_envelope
        self.require_authority(invocation.run_id, 'review.submit')  # guard:gr07_review_grant
        record = self.record_review(invocation.run_id, review_spec_id=review_spec_id, verdict=verdict,
            reviewer_kind=ReviewerKind.PEER_WORKER, independence=independence,
            input_snapshot_id=request.scope_view.snapshot_id)
        self._append(self._project_of_run(invocation.run_id), event_type='worker.review_provenance',
            epistemic_class=EpistemicClass.EVIDENCE, subject={'review_id': record.review_id},
            payload=dict(invocation_id=invocation_id, author_invocation_id=author_invocation_id,
                receipt_id=receipts[0].receipt_id), capability_used='review.attest')
        return record

    def _worker_review_contract(self, run_id, review_spec_id, reviews, quorum):
        """Recheck worker provenance at the evidence boundary, including imports."""
        run = self.store.get_run(run_id)
        if not self.store.list_invocations(run_id):  # guard:gr07_review_import_boundary
            return None  # Trusted legacy CLAIM imports have no worker execution.
        proofs = {e.subject['review_id']: strict_json(self.store.artifact_bytes(e.payload_digest))
            for e in self.store.list_events(run.project_id) if e.event_type == 'worker.review_provenance'}
        for review in reviews:
            require(review.review_id in proofs, 'worker review has no controller provenance', PolicyDenied)  # guard:gr07_attest_provenance
            proof = proofs[review.review_id]
            inv = self.store.get_invocation(proof['invocation_id'])
            self._check_worker_independence(inv, self._request_for(inv), proof['author_invocation_id'])
            require(review == self.store.get_review(review.review_id) and review.run_id == run_id
                    and inv.run_id == run_id and inv.receipt_id == proof['receipt_id'],
                    'review provenance binding mismatch', PolicyDenied)  # guard:gr07_attest_binding
        contract, _ = self._worker_contract(run_id)
        specs = {s['spec_id']: s for s in contract.required_reviews}
        require(review_spec_id in specs and quorum == specs[review_spec_id]['quorum'],
                'review quorum differs from active contract', PolicyDenied)  # guard:gr07_attest_contract
        return contract.contract_hash

    def _worker_session(self, request, document):
        require(document['session']['id'] == request.session_id and document['session']['fresh']
                and document['session']['continued_from'] is None, 'provider reused session', PolicyDenied)  # guard:gr07_result_session

    def invoke(self, invocation_id):
        invocation = self.store.get_invocation(invocation_id)
        if invocation.receipt_id:  # guard:gr07_receipt_reuse
            return self.store.list_worker_receipts(invocation_id)[0]
        run, snapshot = self._worker_gate(invocation.run_id)
        contract, activation = self._worker_contract(invocation.run_id)
        request = self._request_for(invocation)
        require(request.invocation_id == invocation_id and request.idempotency_key == invocation.idempotency_key,
                'persisted invocation identity mismatch', PolicyDenied)  # guard:gr07_request_identity
        require(request.contract_hash == contract.contract_hash and request.worker_role.value == contract.worker_role
                and request.granted_capabilities == frozenset(activation.granted_capabilities),
                'request differs from activated contract', CapabilityDenied)  # guard:gr07_request_grant
        require(request.scope_view.snapshot_id == snapshot.snapshot_id, 'request snapshot superseded', PolicyDenied)  # guard:gr07_request_snapshot
        require(invocation.status in (InvocationStatus.PENDING, InvocationStatus.DISPATCHED),
                'dispatch already attempted; reconcile without resubmission', PolicyDenied)  # guard:gr07_dispatch_once
        require(now_ts() < request.deadline_at, 'invocation deadline expired', PolicyDenied)  # guard:gr07_deadline
        provider = self._worker_provider(invocation)
        governed = GovernedProvider(provider, DISPATCH_CAPABILITIES)
        accepted = governed.preflight(request)
        require(accepted.accepted, 'provider rejected preflight', PolicyDenied)  # guard:gr07_preflight
        lease_deadline = min(request.deadline_at, now_ts() + timedelta(milliseconds=request.budget.wall_clock_ms))  # guard:gr08_worker_lease
        lease = WorkerLease(str(uuid.uuid4()), invocation_id, invocation.run_id,
            invocation.controller_epoch, lease_deadline, request.session_id)
        db = self.store.connection
        db.execute('BEGIN IMMEDIATE')
        try:
            current = self.store.get_invocation(invocation_id)
            require(current.status in (InvocationStatus.PENDING, InvocationStatus.DISPATCHED) and not current.receipt_id,
                    'concurrent dispatch', PolicyDenied)  # guard:gr07_dispatch_cas
            invocation.status = InvocationStatus.DISPATCHING
            invocation.dispatched_at = now_ts()
            self.store.put_invocation(invocation, run.project_id)
            self._append(run.project_id, event_type='invocation.dispatching', epistemic_class=EpistemicClass.AUTHORITY,
                subject={'invocation_id': invocation_id, 'run_id': invocation.run_id},
                payload=dict(lease={**asdict(lease), 'expires_at': lease.expires_at.isoformat()},
                    request_digest=invocation.request_digest, idempotency_key=invocation.idempotency_key), capability_used='worker.invoke')
            db.execute('COMMIT')  # guard:gr07_durable_before_launch
        except BaseException:
            if db.in_transaction:
                db.execute('ROLLBACK')
            raise
        bridge = InvocationBridge(self, invocation, request, lease)
        tick = time.monotonic()
        try:
            outcome = governed.invoke(request, bridge)
            output = governed.fetch(outcome.output_ref)
            self.secret_guard.check(output)  # guard:gr08_worker_output
            status, reason = status_for_outcome(outcome.status), outcome.termination_reason
            extras = {}
            # Structured providers mark their wire media type, never their prose.
            if outcome.output_ref.media_type == 'application/vnd.gruntime.worker-result+json':  # guard:gr07_structured_dispatch
                doc = result_document(output, invocation_id)
                self._worker_session(request, doc)
                extras = self._worker_result(invocation, doc, bridge)
            if bridge.secret_failure:  # guard:gr08_bridge_leak_failure
                from .secret_guard import SecretLeak
                raise SecretLeak()
            if now_ts() >= request.deadline_at:  # guard:gr07_result_deadline
                status, reason = InvocationStatus.TIMED_OUT, TerminationReason.DEADLINE
            elif int((time.monotonic()-tick)*1000) > request.budget.wall_clock_ms:  # guard:gr07_result_budget
                status, reason = InvocationStatus.FAILED, TerminationReason.BUDGET
        except (ProviderError, GovernedRuntimeError, ValueError, TypeError, KeyError, OSError) as exc:
            from .secret_guard import SecretLeak
            try:
                self.secret_guard.check(str(exc))  # guard:gr08_worker_diagnostic
            except SecretLeak as safe:
                exc = safe
            bridge.violations.append(dict(capability='worker.result', at=now_ts().isoformat(), detail=str(exc)[:1024]))
            output = canonical_json({'error': type(exc).__name__, 'detail': str(exc)[:1024]})
            status, reason, extras = InvocationStatus.FAILED, TerminationReason.PROVIDER_ERROR, {}
        finally:
            bridge.close()
        require(self.store.get_project(run.project_id).controller_epoch == invocation.controller_epoch,
                'controller epoch changed during invocation; reconcile by lookup', BarrierViolation)  # guard:gr07_receipt_epoch
        # Preserve the existing post-effect crash seam. DISPATCHING was durable
        # during launch; DISPATCHED now records the provider call has returned.
        invocation.status = InvocationStatus.DISPATCHED
        self._append(run.project_id, event_type='invocation.dispatched', epistemic_class=EpistemicClass.AUTHORITY,
            subject={'invocation_id': invocation_id, 'run_id': invocation.run_id},
            payload={'idempotency_key': invocation.idempotency_key}, capability_used='worker.invoke')
        self.store.put_invocation(invocation, run.project_id)
        gate(AFTER_INVOKE_BEFORE_RECEIPT)
        measured = Usage(tool_calls=len(bridge.calls), wall_clock_ms=int((time.monotonic()-tick)*1000))
        return self._mint_worker_receipt(invocation, run.project_id, output=output, termination_reason=reason,
            attribution=Attribution.DIRECT, status=status, usage=measured,
            capability_violations_attempted=tuple(bridge.violations), **extras)

    def _worker_result(self, invocation, doc, bridge):
        for mutation in doc['proposed_mutations']:
            capability = 'fs.delete' if mutation['op'] == 'DELETE' else 'fs.write'
            self.require_authority(invocation.run_id, capability, path=mutation['path'])  # guard:gr07_mutation_grant
            self._worker_path(invocation, mutation['path'])
            if mutation['rename_to'] is not None:  # guard:gr07_rename_scope
                self._worker_path(invocation, mutation['rename_to'])
        for draft in doc['requested_validations']:
            self.require_authority(invocation.run_id, 'validation.request')  # guard:gr07_validation_grant
            self._worker_validation(invocation, draft)
        for call in doc['tool_calls']:
            ref = self.store.store_artifact(canonical_json(call['arguments']), media_type='application/json')
            bridge.call(ToolCall(call['call_id'], call['tool_id'], ref, now_ts()))
        return self._worker_claim_fields(invocation, doc)

    def _worker_claim_fields(self, invocation, doc):
        """Copy structured claims into kernel artifacts; never execute requests.

        Used by recovery as well as direct dispatch. Scope is checked again by
        the commit controller; a proposal cannot attest its own admissibility.
        """
        mutations = []
        for mutation in doc['proposed_mutations']:
            ref = self.store.store_artifact(mutation['content'].encode(), media_type='application/octet-stream') if mutation['content'] is not None else None
            mutations.append(MutationProposal(op=MutationOp(mutation['op']), path=mutation['path'],
                rename_to=mutation['rename_to'], before_digest=mutation['before_digest'], after_ref=ref,
                mode=mutation['mode'], in_scope=False))
        return dict(claims=tuple(Claim(claim_id=digest_json([invocation.invocation_id, index]), **claim)
                for index, claim in enumerate(doc['claims'])),
            proposed_mutations=tuple(mutations), requested_validations=tuple(d['validation_spec_id'] for d in doc['requested_validations']))
