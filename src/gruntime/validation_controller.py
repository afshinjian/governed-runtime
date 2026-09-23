"""Controller-owned validation transitions, projected from the durable log.

The validation slice of a contract is pinned once per run. Its materialized
catalog digest and parameters are immutable event payloads, preserving the
frozen design's byte-identical command rule without accepting CommandSpec
from a caller. This uses the existing append-only log rather than a second
mutable status table. Recovery only classifies attempts; retry is a new,
explicit validation.execute action and must pass all gates again.
"""
from pathlib import Path
from dataclasses import replace
import uuid

from .authority import network_capability
from .canonical import digest_json
from .errors import PolicyDenied
from .gate import AFTER_VALIDATION_BEFORE_RECEIPT, gate
from .models import Completeness, EpistemicClass, EscalationSeverity, EscalationTrigger, SuspensionState
from .repository import WHOLE_WORKSPACE
from .validation import ValidationExecutor, ValidationReceipt
from .validation_catalog import ValidationCatalog, require


class ValidationController:
    @property
    def validation_catalog(self):
        return ValidationCatalog(self.governance_dir / 'validation-catalog.db')

    def _validation_events(self, project_id, run_id=None):
        import json
        return [(event, json.loads(self.store.artifact_bytes(event.payload_digest)))
                for event in self.store.list_events(project_id)
                if event.event_type.startswith('validation.')
                and (run_id is None or event.subject.get('run_id') == run_id)]

    def bind_validations(self, run_id, specifications):
        """Pin {spec_id: {operation: 'id@version', parameters: {...}}} once.

        Unknown fields (including command/policy overrides) are refused.
        The returned digest identifies this immutable contract slice.
        """
        run = self.store.get_run(run_id)
        pinned = {}
        for spec_id, spec in specifications.items():
            require(set(spec) == {'operation', 'parameters'}, 'validation spec accepts operation and parameters only')  # guard:spec_fields
            operation = self.validation_catalog.resolve(spec['operation'])
            operation.validate_parameters(spec['parameters'])
            pinned[spec_id] = dict(operation=operation.reference, operation_digest=operation.digest,
                                   parameters=dict(spec['parameters']))
        existing = [body for ev, body in self._validation_events(run.project_id, run_id)
                    if ev.event_type == 'validation.contract_bound']
        document = {'required_validations': pinned}
        require(not existing or existing[0] == document, 'validation contract is immutable')  # guard:contract_immutable
        if not existing:
            self._append(run.project_id, event_type='validation.contract_bound',
                         epistemic_class=EpistemicClass.AUTHORITY, subject={'run_id': run_id},
                         payload=document, capability_used='contract.author')
        return digest_json(document)

    def _validation_spec(self, run_id, spec_id):
        project_id = self._project_of_run(run_id)
        contracts = [body['required_validations'] for ev, body in self._validation_events(project_id, run_id)
                     if ev.event_type == 'validation.contract_bound']
        require(bool(contracts) and spec_id in contracts[0], 'validation spec is absent from pinned contract')  # guard:contract_spec
        spec = contracts[0][spec_id]
        operation = self.validation_catalog.resolve(spec['operation'])
        require(operation.digest == spec['operation_digest'], 'catalog differs from pinned contract')  # guard:contract_digest
        return spec, operation

    def _validation_attempts(self, project_id, run_id=None):
        attempts = {}
        for event, body in self._validation_events(project_id, run_id):
            if event.event_type == 'validation.executing':
                attempts[body['op_id']] = dict(body, status='EXECUTING')
            elif event.event_type in ('validation.receipt', 'validation.recovered'):
                attempts[body['op_id']].update(body)
        return attempts

    def _pending_validations(self, run_id):
        return [a['op_id'] for a in self._validation_attempts(self._project_of_run(run_id), run_id).values()
                if a['status'] in ('EXECUTING', 'UNRESOLVABLE')]

    def _require_egress_authority(self, run_id, network):
        """A catalog network policy declares egress; only the activation grants it.

        NONE names no capability, so a confined validation is checked against
        nothing. The mapping stays in authority.py beside the register, shared
        with the activation-time request check.
        """
        egress = network_capability(network)
        if egress is None:
            return
        self.require_authority(run_id, egress)

    def execute_validation(self, run_id, spec_id):
        run = self.store.get_run(run_id)
        self._assert_barrier_clear(run_id, 'executing validation')  # guard:execute_barrier
        self._assert_may_initiate_effect(run.project_id, 'executing validation')  # guard:effect_gate
        spec, operation = self._validation_spec(run_id, spec_id)
        # Both checked ahead of validation.executing, so a denial leaves no
        # attempt for recovery to reconcile and no executor is ever built.
        # Rows 7.1-2 and 7.1-3 declare `proc.exec.validation` as the capability
        # required to authorize or deny a validation (transitions.py:1153,
        # :1158). The declaration existed and nothing consumed it: the same
        # shape as `F03-001`, on the one path the supervised pilot executes.
        # This closes it for those two rows and for no others.
        self.require_authority(run_id, 'proc.exec.validation')  # guard:gr31_validation_exec_authority
        self._require_egress_authority(run_id, operation.network)  # guard:execute_network_egress
        snapshot = self.store.latest_snapshot(run.project_id)
        require(snapshot is not None and snapshot.completeness is Completeness.COMPLETE, 'validation needs a COMPLETE snapshot')  # guard:controller_snapshot
        require(tuple(snapshot.scope) == WHOLE_WORKSPACE, 'validator requires a whole-workspace observation')  # guard:snapshot_scope
        project = self.store.get_project(run.project_id)
        op_id = f'val-{uuid.uuid4().hex}'
        payload = dict(op_id=op_id, run_id=run_id, spec_id=spec_id,
                       operation=spec['operation'], operation_digest=operation.digest,
                       parameters=spec['parameters'], input_snapshot_id=snapshot.snapshot_id,
                       controller_epoch=project.controller_epoch)
        self._append(run.project_id, event_type='validation.executing',
                     epistemic_class=EpistemicClass.AUTHORITY, subject={'op_id': op_id, 'run_id': run_id},
                     payload=payload, capability_used='validation.execute')
        try:
            receipt = ValidationExecutor(self.validation_catalog, self.artifacts).execute(
                spec['operation'], spec['parameters'], snapshot=snapshot,
                snapshot_document=self.store.snapshot_document(snapshot),
                workspace_root=Path(project.workspace_root), run_id=run_id, op_id=op_id,
                prev_event_hash=self.store.get_project(run.project_id).event_head)
        except (PolicyDenied, OSError) as exc:
            self._append(run.project_id, event_type='validation.recovered',
                         epistemic_class=EpistemicClass.AUTHORITY, subject={'op_id': op_id, 'run_id': run_id},
                         payload=dict(op_id=op_id, status='DENIED', reason=str(exc)), capability_used='validation.execute')
            raise
        gate(AFTER_VALIDATION_BEFORE_RECEIPT)
        receipt = replace(receipt, prev_event_hash=self.store.get_project(run.project_id).event_head)  # guard:receipt_head_binding
        self._append(run.project_id, event_type='validation.receipt',
                     epistemic_class=EpistemicClass.EVIDENCE, subject={'op_id': op_id, 'run_id': run_id},
                     payload=dict(op_id=op_id, status={'TIMEOUT': 'TIMED_OUT', 'ERROR': 'EXEC_FAILED'}.get(receipt.outcome, 'COMPLETED'),
                                  receipt=receipt.document(), receipt_hash=receipt.receipt_hash),
                     capability_used='validation.attest', component='validation')
        return receipt

    def recover_validations(self, project_id):
        """Reconcile old attempts without executing a process or claiming PASS."""
        from .recovery import validation_rerun_permitted
        project = self.store.get_project(project_id)
        attempts = self._validation_attempts(project_id)
        settled = []
        unresolved = [a['op_id'] for a in attempts.values() if a['status'] == 'UNRESOLVABLE']
        for attempt in attempts.values():
            if attempt['status'] != 'EXECUTING' or attempt['controller_epoch'] >= project.controller_epoch:  # guard:recovery_eligibility
                continue
            spec, operation = self._validation_spec(attempt['run_id'], attempt['spec_id'])
            allowed = validation_rerun_permitted(operation)
            self._append(project_id, event_type='validation.recovered',
                         epistemic_class=EpistemicClass.AUTHORITY,
                         subject={'op_id': attempt['op_id'], 'run_id': attempt['run_id']},
                         payload=dict(op_id=attempt['op_id'], status='CANCELLED' if allowed else 'UNRESOLVABLE'),
                         capability_used='recovery.reconcile')
            if allowed:
                settled.append(attempt['op_id'])
            else:
                unresolved.append(attempt['op_id'])
                self._raise_escalation(project_id, trigger=EscalationTrigger.RECOVERY_AMBIGUITY,
                                       severity=EscalationSeverity.HIGH, run_id=attempt['run_id'],
                                       suspension=SuspensionState.NONE,
                                       summary=f"Validation {attempt['op_id']} cannot safely be rerun")
        return settled, unresolved

    def retry_validation(self, run_id, op_id):
        from .recovery import validation_rerun_permitted
        attempts = self._validation_attempts(self._project_of_run(run_id), run_id)
        require(op_id in attempts and attempts[op_id]['status'] == 'CANCELLED', 'only reconciled interrupted validations may retry')  # guard:retry_status
        attempt = attempts[op_id]
        spec, operation = self._validation_spec(run_id, attempt['spec_id'])
        require(validation_rerun_permitted(operation), 'recovery forbids rerunning this operation')  # guard:retry_policy
        return self.execute_validation(run_id, attempt['spec_id'])
