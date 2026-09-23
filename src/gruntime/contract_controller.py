"""Controller-owned authoring, activation, revocation and authority mediation."""
from dataclasses import asdict
from datetime import timedelta
import json

from .authority import (ContractActivationRecord, REGISTER, evaluate_authority,
    network_capability, parse_ts, resolve_grants, runtime_actor, ts)
from .canonical import canonical_json, digest_json
from .contracts import StageContract, new_id, require
from .decision import decision_content_hash, derive_decision_state
from .errors import CapabilityDenied, IntegrityViolation, PolicyDenied, ProtectedPathViolation
from .models import (ActorKind, AuthMethod, Budget, Completeness, DecisionKind,
    DecisionScope, DecisionState, DecisionSubjectKind, EpistemicClass,
    EscalationSeverity, EscalationTrigger)
from .store import now_ts
from .scope import authorize_path


class ContractController:
    def author_contract(self, document):
        """Store a stage contract and record that it was authored.

        The contract row is persisted before `contract.authored` is appended,
        so the pending-genesis boundary is asked in front of the row rather
        than in front of the append: a presenter that authored a contract
        against the project being created and swallowed the append's refusal
        would have committed a contract no event attests (`GR27-R4`).
        """
        contract = StageContract.author(document)
        require(self._genesis_admits(contract.project_id), f"project {contract.project_id} is mid-genesis: its creation transaction is open, and storing a contract against it would durably mutate a project that no commit has yet established", IntegrityViolation)  # guard:author_contract_pending_genesis
        self.store.get_project(contract.project_id)
        self.store.put_contract(contract)
        self._append(contract.project_id, event_type="contract.authored",
            epistemic_class=EpistemicClass.CLAIM, subject={"contract_id": contract.contract_id},
            payload=contract.document(), capability_used="contract.author")
        return contract

    def _provisioning_decision_admits(self, decision, project_id, *, decision_kind, now):
        """The conjuncts every per-field provisioning decision must satisfy.

        Shared by the ceiling and the budget so the two cannot drift apart:
        they differ only in the `DecisionKind` the field's act is recorded as,
        and in the field-specific conjunct each adds on top of this.

        Subject `PROJECT`/`project_id` and scope `PROJECT`: provisioning is an
        act over the whole project, and a decision scoped to one action or to
        a stage is not authority for the bound every later contract is
        resolved against. The authentication, evidence, nonce and hash
        conjuncts are `human_covers`' — the same test the activation grant
        basis is held to (`HD-INV-1`..`HD-INV-3`) — and the last is the single
        derivation: only `VALID` is authority (`HD-INV-4`).
        """
        if decision is None:
            return False
        actor = decision.decided_by
        authenticated = (actor.actor_kind is ActorKind.HUMAN and bool(actor.principal_key_id)
            and actor.auth_method in (AuthMethod.SESSION, AuthMethod.SIGNATURE, AuthMethod.MTLS)
            and decision.auth_method == actor.auth_method
            and (actor.auth_method is not AuthMethod.SIGNATURE or bool(decision.signature)))
        return (authenticated and decision.project_id == project_id
            and decision.decision_kind is decision_kind
            and decision.subject_kind is DecisionSubjectKind.PROJECT
            and decision.subject_id == project_id
            and decision.scope is DecisionScope.PROJECT
            and bool(decision.evidence_shown) and 16 <= len(decision.nonce) <= 64
            and decision.decided_at <= now
            and decision.decision_hash == decision_content_hash(decision)
            and derive_decision_state(decision, now=now) is DecisionState.VALID)

    def _ceiling_decision_admits(self, decision, project_id, ceiling, now):
        """A `GRANT_CAPABILITY` that names exactly the ceiling being set.

        `grants == frozenset(ceiling)` rather than a superset: the human
        decided *this* bound, and admitting a decision that named more would
        install a ceiling wider than the one they approved.
        """
        return (self._provisioning_decision_admits(decision, project_id,
                    decision_kind=DecisionKind.GRANT_CAPABILITY, now=now)
                and decision.grants == frozenset(ceiling))

    def _budget_decision_admits(self, decision, project_id, now):
        """An `EXTEND_BUDGET` over the project.

        `EXTEND_BUDGET` is the only budget-shaped member of the frozen
        `DecisionKind` enum. DESIGN-03 §3 proposes a `GRANT_BUDGET` for the
        initial grant; adding an enum member is a frozen-vocabulary change
        this stage does not make, so the initial grant is recorded as the
        budget decision the frozen enum has.
        """
        return self._provisioning_decision_admits(decision, project_id,
            decision_kind=DecisionKind.EXTEND_BUDGET, now=now)

    def set_capability_ceiling(self, project_id, *, ceiling, decision_id):
        """Set `Project.capability_ceiling` from one human decision.

        The first of the two per-field provisioning operations. Until it runs,
        a project created through `create_project` has the model's default
        empty ceiling, and `guard:gr06_activation_ceiling` refuses every
        contract against it: `XC-8` requires `capability_request ⊆ ceiling`,
        and nothing is a subset of nothing. That is the state the runtime
        shipped in — a project could be created and then could do nothing —
        and no production code wrote the field.

        Per-field, not one combined provisioning act: the ceiling and the
        budget are separate bounds, separately decided, and a single decision
        covering both would make a human approving a budget also approve a
        capability bound they were not asked about.

        One `BEGIN IMMEDIATE` transaction. The event, the decision's
        consumption and the field all land together or not at all: a ceiling
        installed without the event that attests it is an authority bound no
        audit accounts for, and a consumed decision without the ceiling would
        spend the human's act on nothing.
        """
        require(self._genesis_admits(project_id), f"project {project_id} is mid-genesis: its creation transaction is open, and installing a capability ceiling would durably mutate a project that no commit has yet established", IntegrityViolation)  # guard:gr31_ceiling_pending_genesis
        db = self.store.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            record = self._set_capability_ceiling(project_id, ceiling, decision_id)
            db.execute("COMMIT")
            return record
        except BaseException:
            db.execute("ROLLBACK")
            raise

    def _set_capability_ceiling(self, project_id, ceiling, decision_id):
        project = self.store.get_project(project_id)
        now = now_ts()
        ceiling = frozenset(ceiling)
        require(all(c in REGISTER for c in sorted(ceiling)), f"a capability ceiling bounds the register's capabilities: {sorted(ceiling - set(REGISTER))} name nothing the register defines, and a bound over an unknown identifier is the unbacked label F03-003 condemned", PolicyDenied)  # guard:gr31_ceiling_registered
        decision = self.store.get_decision(decision_id) if decision_id else None
        require(self._ceiling_decision_admits(decision, project_id, ceiling, now), f"setting a project capability ceiling is project.ceiling.set, a HUMAN-class capability: it needs a live GRANT_CAPABILITY by an authenticated, named human over PROJECT {project_id}, scoped PROJECT, granting exactly the ceiling being set", CapabilityDenied)  # guard:gr31_ceiling_decision
        event = self._append(project_id, event_type="project.ceiling_set",
            epistemic_class=EpistemicClass.DECISION, subject={"project_id": project_id},
            payload={"previous": sorted(project.capability_ceiling), "ceiling": sorted(ceiling)},
            capability_used="project.ceiling.set", authority_ref=decision.decision_id,
            actor=decision.decided_by)
        # Consumed here, in this transaction, and for this reason: `human_covers`
        # accepts a GRANT_CAPABILITY over PROJECT scoped PROJECT as an
        # activation grant basis for any capability in `.grants`. Left VALID,
        # the one decision that *bounds* the ceiling would also *confer* every
        # capability in it, and the two-step containment `AX-4` rests on would
        # collapse into one. `human_covers`' last conjunct requires VALID, so
        # consuming it makes that impossible by construction rather than by
        # convention.
        self._consume_decision(project_id, decision, discharged=event)
        # Re-read before writing: the two appends above advanced this
        # project's `event_seq` and `event_head`, and putting back the row
        # read before them would roll the chain state back to a seq the log
        # has already used.
        project = self.store.get_project(project_id)
        project.capability_ceiling = ceiling
        self.store.put_project(project)
        return ceiling

    def grant_project_budget(self, project_id, *, budget, decision_id):
        """Set `Project.budget` from one human decision. Initial grant only.

        The second per-field provisioning operation. `budget.grant`'s register
        verb is "set initial Budget"; raising an existing one is
        `budget.extend`, a different capability and a different act, and this
        operation refuses it rather than quietly serving as both.
        """
        require(self._genesis_admits(project_id), f"project {project_id} is mid-genesis: its creation transaction is open, and granting a budget would durably mutate a project that no commit has yet established", IntegrityViolation)  # guard:gr31_budget_pending_genesis
        db = self.store.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            record = self._grant_project_budget(project_id, budget, decision_id)
            db.execute("COMMIT")
            return record
        except BaseException:
            db.execute("ROLLBACK")
            raise

    def _grant_project_budget(self, project_id, budget, decision_id):
        project = self.store.get_project(project_id)
        now = now_ts()
        require(project.budget == Budget(), f"budget.grant sets a project's initial Budget; {project_id} already holds {asdict(project.budget)}, and raising it is budget.extend, a capability this operation does not exercise", PolicyDenied)  # guard:gr31_budget_initial_only
        decision = self.store.get_decision(decision_id) if decision_id else None
        require(self._budget_decision_admits(decision, project_id, now), f"granting a project budget is budget.grant, a HUMAN-class capability: it needs a live EXTEND_BUDGET by an authenticated, named human over PROJECT {project_id}, scoped PROJECT", CapabilityDenied)  # guard:gr31_budget_decision
        event = self._append(project_id, event_type="project.budget_granted",
            epistemic_class=EpistemicClass.DECISION, subject={"project_id": project_id},
            payload={"previous": asdict(project.budget), "budget": asdict(budget)},
            capability_used="budget.grant", authority_ref=decision.decision_id,
            actor=decision.decided_by)
        self._consume_decision(project_id, decision, discharged=event)
        project = self.store.get_project(project_id)
        project.budget = budget
        self.store.put_project(project)
        return budget

    def evaluate_grant_policy(self, project_id):
        """Persist evaluation of a human-authored, content-addressed policy.

        `policy_grantable` is a list of register keys; the register still decides
        which of those the policy engine is permitted to grant.
        """
        project = self.store.get_project(project_id)
        policy = self._grant_policy_document(project.policy_digest)
        evaluation = dict(evaluation_id=new_id(), project_id=project_id,
            policy_digest=project.policy_digest, policy_grantable=policy["policy_grantable"], at=ts(now_ts()))
        self.store.put_policy_evaluation(evaluation)
        self._append(project_id, event_type="policy.evaluated", epistemic_class=EpistemicClass.AUTHORITY,
            subject={"evaluation_id": evaluation["evaluation_id"]}, payload=evaluation)
        return evaluation["evaluation_id"]

    def _grant_policy_document(self, digest):
        policy = json.loads(self.store.artifact_bytes(digest))
        actor = policy.get("authored_by", {})
        valid = (digest_json(policy) == digest and actor.get("actor_kind") == "HUMAN"
            and actor.get("principal_key_id") and actor.get("auth_method") in ("SESSION", "SIGNATURE", "MTLS")
            and isinstance(policy.get("policy_grantable"), list)
            and all(c in REGISTER for c in policy["policy_grantable"]))
        require(valid, "policy must be human-authored and digest-pinned")  # guard:gr06_policy_document
        return policy

    def _grant_inputs(self, contract, run, decision_ids, evaluation_ids, now, activation_id=None):
        decisions, evaluations = [], []
        for decision_id in decision_ids:
            decision = self.store.get_decision(decision_id)
            require(decision.decision_hash == decision_content_hash(decision), "human grant decision integrity mismatch")  # guard:gr06_decision_integrity
            owner = self.store.connection.execute("SELECT activation_id FROM grant_nonces WHERE nonce=? OR decision_id=?", (decision.nonce, decision_id)).fetchone()
            require((owner is None if activation_id is None else owner is not None and owner[0] == activation_id), "human grant nonce already consumed or missing its activation binding", CapabilityDenied)  # guard:gr06_nonce
            decisions.append(decision)
        project = self.store.get_project(run.project_id)
        for evaluation_id in evaluation_ids:
            evaluation = self.store.get_policy_evaluation(evaluation_id)
            policy = self._grant_policy_document(evaluation["policy_digest"])
            require(evaluation["evaluation_id"] == evaluation_id and evaluation["project_id"] == project.project_id and evaluation["policy_digest"] == project.policy_digest and evaluation["policy_grantable"] == policy["policy_grantable"] and parse_ts(evaluation["at"]) <= now, "policy evaluation binding mismatch")  # guard:gr06_policy_binding
            evaluations.append(evaluation)
        return decisions, evaluations

    def activate_contract(self, contract_id, run_id, *, decision_ids=(), policy_evaluation_ids=(), approval_id=None):
        """Mint AUTHORITY and bind exactly one contract to one run atomically."""
        db = self.store.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            record = self._activate_contract(contract_id, run_id, decision_ids,
                policy_evaluation_ids, approval_id)
            db.execute("COMMIT")
            return record
        except BaseException:
            db.execute("ROLLBACK")
            raise

    def _activate_contract(self, contract_id, run_id, decision_ids, evaluation_ids, approval_id):
        contract = self.store.get_contract(contract_id)
        run = self.store.get_run(run_id)
        project = self.store.get_project(run.project_id)
        now = now_ts()
        require(contract.status == "DRAFT" and self.store.activation_for_run(run_id) is None, "contract/run already activated", PolicyDenied)  # guard:gr06_activate_once
        require(contract.project_id == run.project_id and contract.stage_id == run.stage_id, "contract does not bind this run")  # guard:gr06_run_identity
        snapshot = self.store.newest_complete_snapshot(run.project_id)
        require(snapshot is not None and snapshot.completeness is Completeness.COMPLETE, "activation requires COMPLETE snapshot", PolicyDenied)  # guard:gr06_activation_snapshot
        remaining = {k: v - asdict(project.budget_used)[k] for k, v in asdict(project.budget).items()}
        require(all(v <= remaining[k] for k, v in contract.budget_ceiling.items()), "XC-10: contract budget exceeds project remaining", PolicyDenied)  # guard:gr06_budget_ceiling
        require(set(contract.capability_request) <= project.capability_ceiling and all(REGISTER.get(c, ("NEVER",))[0] not in ("KERNEL", "NEVER") for c in contract.capability_request), "XC-8: request outside ceiling or nondelegable", PolicyDenied)  # guard:gr06_activation_ceiling
        repo = self.governed_repo(run.project_id) if self.repo else None
        root = repo.root if repo else project.workspace_root
        submodules = repo.submodule_paths() if repo else ()
        for spec in contract.required_validations:
            command = spec["command"]
            authorize_path(contract, root, command["cwd"], submodules=submodules)  # guard:gr06_validation_cwd
            require(command["timeout_ms"] <= contract.deadline_ms, "XC-7: validation exceeds deadline", PolicyDenied)  # guard:gr06_validation_deadline
            needed = network_capability(command["network"])
            require(needed is None or needed in contract.capability_request, "XC-9: missing network request", PolicyDenied)  # guard:gr06_validation_network
        if contract.document().get("supersedes"):
            prior = self.store.get_contract(contract.supersedes)
            require(prior.stage_id == contract.stage_id and prior.project_id == contract.project_id and prior.contract_version < contract.contract_version, "XC-11: invalid successor", PolicyDenied)  # guard:gr06_successor
        if project.governance_mode.value == "SUPERVISED":
            approval = self.store.get_decision(approval_id) if approval_id else None
            valid = (approval is not None and approval.project_id == project.project_id
                and approval.decision_kind is DecisionKind.APPROVE
                and approval.subject_kind.value == "CONTRACT" and approval.subject_id == contract_id
                and approval.decided_by.actor_kind is ActorKind.HUMAN
                and approval.decided_by.principal_key_id
                and approval.auth_method in (AuthMethod.SESSION, AuthMethod.SIGNATURE, AuthMethod.MTLS)
                and approval.evidence_shown and derive_decision_state(approval, now=now,
                    superseded_by_drift=approval.subject_snapshot_id != snapshot.snapshot_id) is DecisionState.VALID)
            require(valid, "SUPERVISED activation requires live contract approval", CapabilityDenied)  # guard:gr06_activation_confirmation
            approval.decision_state = DecisionState.CONSUMED
            self.store.put_decision(approval)
        decisions, evaluations = self._grant_inputs(contract, run, decision_ids, evaluation_ids, now)
        granted, denied, basis = resolve_grants(contract, ceiling=project.capability_ceiling,
            mode=project.governance_mode.value, remaining_budget=remaining, now=now, run_id=run_id,
            snapshot_id=snapshot.snapshot_id, decisions=decisions, policy_evaluations=evaluations,
            policy_digest=project.policy_digest)
        chain = [dict(grantor=runtime_actor("PROJECT_CEILING"), grant_kind="CEILING", at=ts(now))] + list(basis.values())
        record = ContractActivationRecord.mint(activation_id=new_id(), contract_id=contract_id,
            contract_hash=contract.contract_hash, run_id=run_id, project_id=run.project_id,
            granted_capabilities=sorted(granted), denied_capabilities=denied, capability_grant_basis=basis,
            authority_chain=chain, governance_mode_at_activation=project.governance_mode.value,
            policy_digest=project.policy_digest or digest_json({}), input_snapshot_id=snapshot.snapshot_id,
            activated_by=runtime_actor("gruntime.contract"), activated_at=ts(now),
            expires_at=ts(now + timedelta(milliseconds=contract.deadline_ms)), prev_event_hash=project.event_head)
        self.store.put_activation(record)
        for decision in decisions:
            if any(e.get("ref") == decision.decision_id for e in basis.values()):
                self.store.connection.execute("INSERT INTO grant_nonces VALUES (?,?,?)", (decision.nonce, decision.decision_id, record.activation_id))
        self.store.put_contract(contract.with_status("ACTIVE"))
        run.input_snapshot_id = snapshot.snapshot_id
        run.deadline_at = parse_ts(record.expires_at)
        self.store.put_run(run)
        self._append(run.project_id, event_type="contract.activated", epistemic_class=EpistemicClass.AUTHORITY,
            subject={"contract_id": contract_id, "activation_id": record.activation_id, "run_id": run_id},
            payload=record.document(), capability_used="contract.activate")
        if not granted:
            self._raise_escalation(run.project_id, trigger=EscalationTrigger.CAPABILITY_DENIED,
                severity=EscalationSeverity.HIGH, summary="activation grants no capabilities", run_id=run_id)
        return record

    def require_authority(self, run_id, capability, *, path=None, repo=None, exercise_decision_id=None, _grant_only=False):
        run = self.store.get_run(run_id)
        try:
            activation = self.store.activation_for_run(run_id)
            require(activation is not None, "unactivated run grants nothing", CapabilityDenied)  # guard:gr06_run_activation
            contract = self.store.get_contract(activation.contract_id)
            project = self.store.get_project(run.project_id)
            now = now_ts()
            require(activation.governance_mode_at_activation == project.governance_mode.value and activation.policy_digest == (project.policy_digest or digest_json({})), "activation governance changed", CapabilityDenied)  # guard:gr06_live_governance
            basis = activation.capability_grant_basis
            decision_ids = {e["ref"] for e in basis.values() if e["grant_kind"] == "HUMAN_DECISION"}
            evaluation_ids = {e["ref"] for e in basis.values() if e["grant_kind"] == "POLICY"}
            decisions, evaluations = self._grant_inputs(contract, run, decision_ids, evaluation_ids, now, activation.activation_id)
            snapshot = self.store.newest_complete_snapshot(run.project_id)
            remaining = {k: v - asdict(project.budget_used)[k] for k, v in asdict(project.budget).items()}
            grants, _, replayed = resolve_grants(contract, ceiling=project.capability_ceiling,
                mode=project.governance_mode.value, remaining_budget=remaining, now=now, run_id=run_id,
                snapshot_id=snapshot.snapshot_id if snapshot else None,
                decisions=decisions, policy_evaluations=evaluations, policy_digest=project.policy_digest)
            # Replay each actual basis, rather than accepting a different grantor
            # that happens to permit the same capability today.
            entry = basis.get(capability, {}) if type(capability) is str else {}
            valid_basis = bool(entry) and capability in replayed and all(replayed[capability].get(k) == entry.get(k) for k in ("grant_kind", "grantor", "ref"))
            require(valid_basis and type(capability) is str and capability in grants, "grant source expired, revoked, exhausted or inadmissible", CapabilityDenied)  # guard:gr06_live_basis
            root = repo.root if repo else project.workspace_root
            result = evaluate_authority(contract, activation, capability, run_id=run_id,
                project_id=run.project_id, now=now, root=root, path=path,
                exercise_decision=self.store.get_decision(exercise_decision_id) if exercise_decision_id else None,
                submodules=repo.submodule_paths() if repo else (), grant_only=_grant_only)
            return result
        except (CapabilityDenied, IntegrityViolation, PolicyDenied, ProtectedPathViolation) as exc:
            self._append(run.project_id, event_type="authority.denied", epistemic_class=EpistemicClass.AUTHORITY,
                subject={"run_id": run_id}, payload={"capability": capability, "path": path, "reason": str(exc)})
            raise

    def _require_commit_authority(self, intent, repo):
        """Re-prove the proposing contract's mutation authority over this intent.

        This is authority-matrix §6's *syscall or tool mediation* row, not its
        *transition* row: it asks whether the activation that proposed these
        mutations is still live and whether every path is still inside the
        scope it was granted for. It is asked again at authorize and at apply
        because a contract can be revoked or expire in between.

        It is **not** the transition's authority and never stands in for it.
        Rows 7.4-4 and 7.4-5 declare `commit.authorize` and 7.4-6 onward
        declare `commit.apply`; both are `KERNEL` and are proved by
        `_require_transition_authority` against the kernel's own capability
        set. Checking `commit.propose` here and calling that the authority for
        a kernel transition is what `F03-002` recorded — it put two kernel
        transitions onto authority a contract can hold.
        """
        # The caller's `in_scope` flag cannot confer permission. Both ends of
        # a rename are checked against the stored, activated contract.
        self.require_authority(intent.run_id, "commit.propose", repo=repo)  # guard:gr06_commit_intent_grant
        for mutation in intent.mutations:
            self.require_authority(intent.run_id, "fs.delete" if mutation.op.value == "DELETE" else "fs.write", path=mutation.path, repo=repo)  # guard:gr06_commit_source_scope
            if mutation.rename_to is not None:
                self.require_authority(intent.run_id, "fs.write", path=mutation.rename_to, repo=repo)  # guard:gr06_commit_destination_scope

    def revoke_contract(self, contract_id, *, reason="INTEGRITY"):
        """Revoke future authority; retain activation and past evidence intact."""
        contract = self.store.get_contract(contract_id)
        self.store.put_contract(contract.with_status("REVOKED"))
        self._append(contract.project_id, event_type="contract.revoked", epistemic_class=EpistemicClass.AUTHORITY,
            subject={"contract_id": contract_id}, payload={"reason": reason}, capability_used="contract.revoke")
