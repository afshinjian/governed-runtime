"""Secret authority and resolution belong to the kernel, never the provider."""
from .authority import human_covers
from .contracts import require
from .decision import decision_content_hash, derive_decision_state
from .errors import CapabilityDenied
from .inference_relay import InferenceRelay
from .models import ActorKind, AuthMethod, DecisionKind, DecisionState, EpistemicClass
from .store import now_ts


class RelayController:
    def configure_inference_relay(self, run_id, *, origin, secret_name, resolve_secret,
                                 grant_decision_id, approval_id, **options):
        require(self._inference_relay is None, 'RELAY_ALREADY_CONFIGURED', CapabilityDenied)  # guard:gr08_single_origin
        run = self.store.get_run(run_id)
        self._worker_gate(run_id)
        contract, activation = self._worker_contract(run_id)
        project = self.store.get_project(run.project_id)
        grant = self.store.get_decision(grant_decision_id)
        approval = self.store.get_decision(approval_id)
        now = now_ts()
        require('secret.read' in project.capability_ceiling
                and human_covers(grant, contract, run_id, 'secret.read', now, run.input_snapshot_id),
                'SECRET_GRANT_DENIED', CapabilityDenied)  # guard:gr08_secret_grant
        actor = approval.decided_by
        require(approval.project_id == run.project_id and approval.decision_kind is DecisionKind.APPROVE
                and approval.subject_kind.value == 'CAPABILITY' and approval.subject_id == 'secret.read'
                and approval.scope.value == 'SINGLE_ACTION' and approval.chosen == secret_name
                and actor.actor_kind is ActorKind.HUMAN and bool(actor.principal_key_id)
                and actor.auth_method in (AuthMethod.SESSION, AuthMethod.SIGNATURE, AuthMethod.MTLS)
                and approval.auth_method == actor.auth_method
                and (actor.auth_method is not AuthMethod.SIGNATURE or bool(approval.signature))
                and approval.evidence_shown and 16 <= len(approval.nonce) <= 64
                and approval.decided_at <= now
                and derive_decision_state(approval, now=now) is DecisionState.VALID,
                'SECRET_APPROVAL_DENIED', CapabilityDenied)  # guard:gr08_secret_approval
        require(all(d.decision_hash == decision_content_hash(d) for d in (grant, approval)),
                'SECRET_DECISION_INTEGRITY', CapabilityDenied)  # guard:gr08_secret_integrity
        require(not approval.snapshot_bound or approval.subject_snapshot_id == self.store.newest_complete_snapshot(run.project_id).snapshot_id,
                'SECRET_APPROVAL_STALE', CapabilityDenied)  # guard:gr08_secret_currency
        require(self.store.connection.execute('SELECT 1 FROM grant_nonces WHERE nonce=? OR decision_id=?',
                (grant.nonce, grant.decision_id)).fetchone() is None,
                'SECRET_GRANT_CONSUMED', CapabilityDenied)  # guard:gr08_secret_nonce
        # Consume the exercise before resolving. A failed resolver never makes
        # this single-action approval reusable.
        db = self.store.connection
        db.execute('BEGIN IMMEDIATE')
        try:
            for decision in (grant, approval):
                decision.decision_state = DecisionState.CONSUMED
                self.store.put_decision(decision)
            self._append(run.project_id, event_type='secret.resolution_authorized',
                epistemic_class=EpistemicClass.AUTHORITY, subject={'run_id': run_id},
                payload=dict(name=secret_name, origin=origin, grant_decision_id=grant_decision_id,
                             approval_id=approval_id), capability_used='secret.read')
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK')
            raise
        try:
            secret = resolve_secret(secret_name)
        except Exception:
            raise CapabilityDenied('SECRET_RESOLUTION_FAILED') from None
        fingerprint = self.secret_guard.register(secret_name, secret)
        relay = InferenceRelay(run_id=run_id, origin=origin, secret=secret,
                               secret_guard=self.secret_guard, **options)
        del secret
        self._append(run.project_id, event_type='secret.resolved', epistemic_class=EpistemicClass.AUTHORITY,
            subject={'run_id': run_id}, payload=fingerprint, capability_used='secret.read')
        self._inference_relay = relay
