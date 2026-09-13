"""Explicit authority provisioning for tests predating GR-06.

Production open_run leaves authority empty. The legacy harness supplies its
own test contract/activation; subprocesses subsequently consume that record.
"""
from dataclasses import asdict

from gruntime.contracts import new_id
from gruntime.models import Budget
from gruntime.authority import ts
from gruntime.store import now_ts
from gruntime.canonical import canonical_json


def document(project_id=None, stage_id=None, **overrides):
    doc = dict(schema_version="0.1.0", contract_id=new_id(),
        project_id=project_id or new_id(), stage_id=stage_id or new_id(),
        contract_version=1, status="DRAFT", objective="Implement the accepted change",
        scope_include=["**"], scope_exclude=[],
        acceptance_criteria=[dict(criterion_id="review", text="Meets the objective",
            kind="JUDGMENTAL", verifier_ref="review", mandatory=True, waivable=False)],
        required_validations=[], required_reviews=[dict(spec_id="review", reviewer_kind="HUMAN",
            independence_required="INDEPENDENT", blocking_severity="BLOCKER", quorum=1)],
        prohibited_actions=[], capability_request=["fs.read", "fs.write", "commit.propose"],
        worker_role="IMPLEMENTER", budget_ceiling=asdict(Budget(3600000, 100, 100, 100, 100, 100)),
        deadline_ms=3600000, escalation_triggers=[], rollback_policy="REVERT_COMMITS",
        evidence_retention_class="STANDARD", authored_by=dict(actor_kind="WORKER",
            actor_id="test-author", auth_method="NONE"), authored_at=ts(now_ts()))
    doc.update(overrides)
    return doc


def provision(c, run_id, **overrides):
    run = c.store.get_run(run_id)
    doc = document(run.project_id, run.stage_id, **overrides)
    project = c.store.get_project(run.project_id)
    project.capability_ceiling = project.capability_ceiling | frozenset(doc["capability_request"])
    project.budget = Budget(7200000, 1000, 1000, 1000, 1000, 1000)
    evaluation_ids = []
    if 'fs.delete' in doc['capability_request']:
        policy = dict(authored_by=dict(actor_kind='HUMAN', actor_id='test-owner',
            auth_method='SESSION', principal_key_id='test-key'), policy_grantable=['fs.delete'])
        project.policy_digest = c.store.store_artifact(canonical_json(policy), media_type='application/json').digest
    c.store.put_project(project)
    if 'fs.delete' in doc['capability_request']:
        evaluation_ids.append(c.evaluate_grant_policy(run.project_id))
    if c.store.newest_complete_snapshot(run.project_id) is None:
        c.take_snapshot(run.project_id)
    contract = c.author_contract(doc)
    return contract, c.activate_contract(contract.contract_id, run_id, policy_evaluation_ids=evaluation_ids)


def provision_legacy_run(controller, project_id):
    from gruntime.controller import Controller
    run_id = Controller.open_run(controller, project_id)
    provision(controller, run_id, capability_request=['fs.read', 'fs.write', 'fs.delete', 'commit.propose'])
    return run_id
