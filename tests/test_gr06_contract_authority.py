"""Frozen schema, authority provenance and GR-10 integration adversaries."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path

import pytest
import rfc8785

from gruntime.authority import (ContractActivationRecord, REGISTER, ROLE_TABLE, ROLES,
    evaluate_authority, resolve_grants, runtime_actor, ts)
from gruntime.canonical import canonical_json, digest_bytes, digest_json
from gruntime.contracts import SCHEMA_BYTES, StageContract, contract_hash, new_id
from gruntime.controller import Controller
from gruntime.errors import CapabilityDenied, IntegrityViolation, PolicyDenied, ProtectedPathViolation
from gruntime.models import (ActorKind, ActorRef, AuthMethod, Budget, BudgetUsage, DecisionKind,
    DecisionScope, DecisionState, DecisionSubjectKind, GovernanceMode, MutationOp)
from gruntime.scope import authorize_path, canonical_path, canonical_pattern, matches
from gruntime.store import now_ts
from gr03_support import git, project_with_repo
from gr06_support import document, provision


@pytest.fixture
def ctx(h):
    project_id = project_with_repo(h, slug="gr06")
    with h.controller(with_repo=True) as c:
        run_id = Controller.open_run(c, project_id)
        yield c, project_id, run_id


def setup_contract(ctx, **overrides):
    c, project_id, run_id = ctx
    run = c.store.get_run(run_id)
    doc = document(project_id, run.stage_id, **overrides)
    project = c.store.get_project(project_id)
    project.capability_ceiling = frozenset(doc['capability_request'])
    project.budget = Budget(7200000, 1000, 1000, 1000, 1000, 1000)
    c.store.put_project(project)
    c.take_snapshot(project_id)
    contract = c.author_contract(doc)
    return contract


def activate(ctx, **overrides):
    contract = setup_contract(ctx, **overrides)
    c, _, run = ctx
    return contract, c.activate_contract(contract.contract_id, run)


def resolve(contract, **overrides):
    args = dict(ceiling=set(REGISTER), mode='AUTONOMOUS', remaining_budget=contract.budget_ceiling,
        now=now_ts(), run_id=new_id(), snapshot_id='snapshot')
    args.update(overrides)
    return resolve_grants(contract, **args)


def resign_activation(activation, **updates):
    doc = activation.document()
    doc.pop('record_hash')
    doc.update(updates)
    return ContractActivationRecord.mint(**doc)


def human_grant(ctx, contract, *, scope=DecisionScope.PROJECT, **overrides):
    c, project_id, run = ctx
    subject_kind = {'PROJECT': DecisionSubjectKind.PROJECT, 'RUN': DecisionSubjectKind.RUN,
        'STAGE': DecisionSubjectKind.STAGE, 'SINGLE_ACTION': DecisionSubjectKind.CONTRACT}[scope.value]
    subject = {'PROJECT': project_id, 'RUN': run, 'STAGE': contract.stage_id,
        'SINGLE_ACTION': contract.contract_id}[scope.value]
    args = dict(decision_kind=DecisionKind.GRANT_CAPABILITY, subject_kind=subject_kind,
        subject_id=subject, question='Grant?', chosen='yes', justification='test', options_offered=('yes',),
        decided_by=ActorRef(ActorKind.HUMAN, 'owner', AuthMethod.SESSION, principal_key_id='owner-key'),
        evidence_shown=(c.store.store_artifact(b'grant evidence', media_type='text/plain'),),
        scope=scope, grants=frozenset(contract.capability_request))
    args.update(overrides)
    return c.record_decision(project_id, **args)


def test_schema_is_frozen_copy():
    assert SCHEMA_BYTES == (Path(__file__).resolve().parents[1] / 'design/schema/stage_contract.schema.json').read_bytes()


@pytest.mark.parametrize('status', ['DRAFT', 'ACTIVE', 'REVOKED', 'EXPIRED', 'FULFILLED', 'SUPERSEDED'])
def test_status_is_outside_jcs_hash(status):
    contract = StageContract.author(document())
    transitioned = contract.with_status(status)
    assert transitioned.contract_hash == contract.contract_hash
    preimage = {k: v for k, v in contract.document().items() if k not in ('status', 'contract_hash')}
    assert contract.contract_hash == digest_bytes(rfc8785.dumps(preimage))


def test_absent_is_not_null_and_accessors_do_not_mutate_contract():
    contract = StageContract.author(document())
    other = StageContract.author(dict(contract.document(), supersedes=None))
    assert other.contract_hash != contract.contract_hash
    contract.scope_include.append('outside/**')
    contract.document()['required_reviews'][0]['quorum'] = 8
    assert contract.scope_include == ['**']
    assert contract.required_reviews[0]['quorum'] == 1


@pytest.mark.parametrize('change', [
    {'objective': ''}, {'objective': 'line\nbreak'}, {'objective': 'e\u0301'},
    {'unknown': True}, {'non_goals': ['unfrozen extension']}, {'commit_policy': {}},
    {'contract_version': 0}, {'contract_version': True}, {'contract_id': 'not-ulid'},
    {'authored_at': '2026-02-30T00:00:00.000Z'}, {'budget_ceiling': {}},
    {'worker_role': 'REVIEWER', 'capability_request': ['fs.write']},
    {'worker_role': 'PLANNER', 'capability_request': ['proc.exec.validation']},
    {'required_reviews': []}, {'scope_include': ['./src/**']},
])
def test_schema_and_authoring_constraints(change):
    with pytest.raises((PolicyDenied, ProtectedPathViolation)):
        StageContract.author(document(**change))


def test_author_cannot_mint_active_document():
    with pytest.raises(PolicyDenied, match='DRAFT'):
        StageContract.author(document(status='ACTIVE'))


def test_integrity_mismatch_is_not_schema_error():
    doc = StageContract.author(document()).document()
    doc['objective'] = 'Changed with original hash'
    with pytest.raises(IntegrityViolation, match='hash'):
        StageContract(doc)


@pytest.mark.parametrize('case', ['criteria', 'reviews', 'overlap', 'unbound', 'mandatory', 'mechanical'])
def test_cross_constraints(case):
    doc = document()
    if case == 'criteria':
        doc['acceptance_criteria'] *= 2
    elif case == 'reviews':
        doc['required_reviews'] *= 2
    elif case == 'overlap':
        doc['required_validations'] = [validation(spec_id='review')]
    elif case == 'unbound':
        doc['acceptance_criteria'][0]['verifier_ref'] = 'absent'
    elif case == 'mandatory':
        doc['acceptance_criteria'][0]['mandatory'] = False
    else:
        doc['acceptance_criteria'][0]['kind'] = 'MECHANICAL'
        doc['required_validations'] = [validation()]
    with pytest.raises(PolicyDenied):
        StageContract.author(doc)


def validation(**overrides):
    spec = dict(spec_id='test', command=dict(argv=['/usr/bin/true'], cwd='src', env_allowlist=[],
        network='NONE', timeout_ms=1000), expected_exit_codes=[0], determinism_class='DETERMINISTIC',
        max_retries=0, result_parser='EXIT_CODE')
    spec.update(overrides)
    return spec


def test_unactivated_contract_has_no_authority_even_with_active_label(ctx):
    c, project, run = ctx
    contract = setup_contract(ctx)
    assert c.store.get_run(run).effective_capabilities == frozenset()
    with pytest.raises(CapabilityDenied, match='unactivated'):
        evaluate_authority(contract.with_status('ACTIVE'), None, 'fs.write', run_id=run,
            project_id=project, now=now_ts())
    before = git(c.repo.root, 'for-each-ref', '--format=%(refname)')
    with pytest.raises(CapabilityDenied, match='unactivated'):
        c.propose_commit(run, path='feature.txt', content='x', message='x')
    assert git(c.repo.root, 'for-each-ref', '--format=%(refname)') == before
    assert c.store.list_commit_intents(run) == []
    assert c.store.list_events(project)[-1].event_type == 'authority.denied'


@pytest.mark.parametrize('mode', ['AUTONOMOUS', 'SUPERVISED'])
@pytest.mark.parametrize('capability,role', [('roadmap.writeback','PLANNER'), ('contract.author','PLANNER'),
    ('audit.read','REVIEWER'), ('fs.delete','IMPLEMENTER'), ('net.egress.allowlist','IMPLEMENTER')])
def test_ceiling_role_and_request_are_not_grantors(mode, capability, role):
    contract = StageContract.author(document(capability_request=[capability], worker_role=role))
    grants, denied, basis = resolve(contract, mode=mode)
    assert grants == frozenset()
    assert denied == {capability: 'NO_GRANTOR'}
    assert basis == {}


@pytest.mark.parametrize('capability,role,kwargs,reason', [
    ('fs.write','IMPLEMENTER',{'ceiling':set()},'NOT_IN_CEILING'),
    ('fs.read.outside_scope','ANALYST',{},'MODE_FORBIDDEN'),
    ('fs.write','ANALYST',{},'ROLE_FORBIDDEN'),
    ('worker.invoke','IMPLEMENTER',{},'NEVER_GRANTABLE'),
    ('worker.delegate','IMPLEMENTER',{},'NEVER_GRANTABLE'),
    ('unknown.capability','IMPLEMENTER',{'ceiling':{'unknown.capability'}},'NEVER_GRANTABLE'),
    ('fs.write','IMPLEMENTER',{'remaining_budget':{'commits':0}},'BUDGET'),
])
def test_resolution_denials_are_recorded(capability, role, kwargs, reason):
    contract = StageContract.author(document(capability_request=[capability], worker_role=role))
    grants, denied, basis = resolve(contract, **kwargs)
    assert not grants and not basis
    assert denied == {capability:reason}


def test_unknown_mode_fails_closed():
    with pytest.raises(IntegrityViolation):
        resolve(StageContract.author(document()), mode='unexpected')


def test_role_grants_require_requests():
    contract = StageContract.author(document(capability_request=[]))
    assert resolve(contract) == (frozenset(), {}, {})


def test_empty_activation_is_recorded_and_escalated(ctx):
    contract, activation = activate(ctx, worker_role='PLANNER', capability_request=['roadmap.writeback'])
    c, project, run = ctx
    assert activation.denied_capabilities == {'roadmap.writeback':'NO_GRANTOR'}
    assert activation.granted_capabilities == []
    assert c.store.list_escalations(project)[-1].trigger.value == 'CAPABILITY_DENIED'
    with pytest.raises(CapabilityDenied):
        c.require_authority(run, 'roadmap.writeback')


@pytest.mark.parametrize('scope', list(DecisionScope))
def test_live_human_grant_is_bound_once_and_replayed(ctx, scope):
    c, project, run = ctx
    contract = setup_contract(ctx, worker_role='PLANNER', capability_request=['roadmap.writeback'])
    decision = human_grant(ctx, contract, scope=scope)
    activation = c.activate_contract(contract.contract_id, run, decision_ids=[decision.decision_id])
    assert activation.capability_grant_basis['roadmap.writeback']['ref'] == decision.decision_id
    assert c.require_authority(run, 'roadmap.writeback') is True
    assert c.store.get_decision(decision.decision_id).grants == frozenset({'roadmap.writeback'})
    decision.decision_state = DecisionState.VOID
    c.store.put_decision(decision)
    with pytest.raises(CapabilityDenied):
        c.require_authority(run, 'roadmap.writeback')


@pytest.mark.parametrize('change', [
    {'decision_state': DecisionState.CONSUMED}, {'decision_state': DecisionState.STALE},
    {'expires_at': now_ts()-timedelta(days=1)}, {'project_id':'other'}, {'subject_id':'other'},
    {'scope':DecisionScope.RUN}, {'grants':frozenset()}, {'revokes':frozenset({'roadmap.writeback'})},
    {'decision_kind':DecisionKind.APPROVE}, {'evidence_shown':()}, {'nonce':'short'},
    {'decided_by':ActorRef(ActorKind.RUNTIME, 'imposter', AuthMethod.NONE)},
    {'decided_by':ActorRef(ActorKind.HUMAN, 'owner', AuthMethod.NONE, principal_key_id='owner')},
    {'decided_by':ActorRef(ActorKind.HUMAN, 'owner', AuthMethod.SESSION)},
])
def test_inadmissible_human_decisions_do_not_grant(ctx, change):
    contract = setup_contract(ctx, worker_role='PLANNER', capability_request=['roadmap.writeback'])
    decision = replace(human_grant(ctx, contract), **change)
    grants, denied, basis = resolve(contract, run_id=ctx[2], decisions=[decision])
    assert not grants and not basis and denied['roadmap.writeback'] == 'NO_GRANTOR'


def test_nonce_cannot_activate_a_second_run(ctx):
    c, project, run = ctx
    contract = setup_contract(ctx, worker_role='PLANNER', capability_request=['roadmap.writeback'])
    decision = human_grant(ctx, contract)
    c.activate_contract(contract.contract_id, run, decision_ids=[decision.decision_id])
    run2 = Controller.open_run(c, project)
    contract2 = c.author_contract(document(project, c.store.get_run(run2).stage_id,
        worker_role='PLANNER', capability_request=['roadmap.writeback']))
    with pytest.raises(CapabilityDenied, match='nonce'):
        c.activate_contract(contract2.contract_id, run2, decision_ids=[decision.decision_id])
    assert c.store.activation_for_run(run2) is None
    assert c.store.get_contract(contract2.contract_id).status == 'DRAFT'


def policy(ctx, capabilities):
    c, project_id, _ = ctx
    doc = dict(authored_by=dict(actor_kind='HUMAN', actor_id='owner', auth_method='SESSION', principal_key_id='key'),
        policy_grantable=capabilities)
    ref = c.store.store_artifact(canonical_json(doc), media_type='application/json')
    project = c.store.get_project(project_id)
    project.policy_digest = ref.digest
    c.store.put_project(project)
    return c.evaluate_grant_policy(project_id)


def test_persisted_policy_can_only_grant_registered_capabilities(ctx):
    c, project, run = ctx
    contract = setup_contract(ctx, worker_role='PLANNER', capability_request=['contract.author','roadmap.writeback'])
    evaluation_id = policy(ctx, contract.capability_request)
    activation = c.activate_contract(contract.contract_id, run, policy_evaluation_ids=[evaluation_id])
    assert activation.granted_capabilities == ['contract.author']
    assert activation.denied_capabilities == {'roadmap.writeback':'NO_GRANTOR'}
    assert activation.capability_grant_basis['contract.author']['ref'] == evaluation_id
    assert c.require_authority(run, 'contract.author') is True


@pytest.mark.parametrize('mode', ['SUPERVISED', 'AUTONOMOUS'])
def test_policy_grant_requires_matching_mode_digest_and_project(mode):
    contract = StageContract.author(document(worker_role='PLANNER', capability_request=['contract.author']))
    eval_doc = dict(evaluation_id=new_id(), policy_digest='pinned', project_id=contract.project_id, policy_grantable=['contract.author'])
    for evaluation, digest in [(eval_doc, 'different'), (dict(eval_doc, project_id='other'), 'pinned'), (dict(eval_doc, policy_grantable=[]),'pinned')]:
        assert resolve(contract, mode=mode, policy_evaluations=[evaluation], policy_digest=digest)[1] == {'contract.author':'NO_GRANTOR'}
    if mode == 'SUPERVISED':
        assert resolve(contract, mode=mode, policy_evaluations=[eval_doc], policy_digest='pinned')[1] == {'contract.author':'NO_GRANTOR'}


@pytest.mark.parametrize('field,value', [('objective','expanded'), ('scope_include',['**','outside/**']),
    ('scope_exclude',['secret/**']), ('prohibited_actions',['non-goal']), ('acceptance_criteria',[]),
    ('required_reviews',[]), ('capability_request',['fs.delete']), ('rollback_policy','NONE'),
    ('budget_ceiling',{}), ('deadline_ms',1000), ('evidence_retention_class','PERMANENT')])
def test_frozen_content_cannot_be_replaced_even_with_recomputed_hash(ctx, field, value):
    contract, activation = activate(ctx)
    c, project, run = ctx
    doc = c.store.get_contract(contract.contract_id).document()
    doc[field] = value
    doc['contract_hash'] = contract_hash(doc)
    with pytest.raises((IntegrityViolation, PolicyDenied)):
        c.store.put_contract(StageContract(doc))
    assert c.store.get_contract(contract.contract_id).contract_hash == activation.contract_hash


def test_persisted_status_transition_preserves_hash_and_revokes_immediately(ctx):
    contract, activation = activate(ctx)
    c, project, run = ctx
    c.revoke_contract(contract.contract_id)
    assert c.store.get_contract(contract.contract_id).contract_hash == contract.contract_hash
    assert c.store.get_run(run).contract_hash == contract.contract_hash
    with pytest.raises(CapabilityDenied):
        c.require_authority(run, 'commit.propose')
    with pytest.raises(IntegrityViolation, match='lifecycle'):
        c.store.put_contract(contract.with_status('ACTIVE'))


def test_activation_and_run_grants_are_immutable(ctx):
    contract, record = activate(ctx)
    c, _, run = ctx
    with pytest.raises(IntegrityViolation, match='immutable'):
        c.store.put_activation(resign_activation(record, expires_at=ts(now_ts()+timedelta(days=1))))
    c.store.get_run(run).effective_capabilities = frozenset({'commit.apply'})
    assert c.store.get_run(run).effective_capabilities == frozenset(record.granted_capabilities)


@pytest.mark.parametrize('change', [dict(capability_grant_basis={}), dict(authority_chain=[]),
    dict(activated_by=runtime_actor('worker') | {'actor_kind':'WORKER'})])
def test_activation_structure_refuses_incomplete_authority(ctx, change):
    _, activation = activate(ctx)
    with pytest.raises(IntegrityViolation):
        resign_activation(activation, **change)


@pytest.mark.parametrize('kind,actor,ref', [('CEILING',runtime_actor('PROJECT_CEILING'),None),
    ('POLICY',runtime_actor('POLICY_ENGINE'),'evaluation'), ('ROLE_DEFAULT',runtime_actor('wrong'),None),
    ('HUMAN_DECISION',runtime_actor('imposter'),'decision')])
def test_basis_cannot_claim_inadmissible_grantor(ctx, kind, actor, ref):
    _, activation = activate(ctx)
    basis = activation.capability_grant_basis
    entry = dict(grant_kind=kind, grantor=actor, at=activation.activated_at)
    if ref:
        entry['ref'] = ref
    basis['commit.propose'] = entry
    with pytest.raises(IntegrityViolation):
        resign_activation(activation, capability_grant_basis=basis, authority_chain=activation.authority_chain+[entry])


def test_activation_hash_is_verified(ctx):
    _, activation = activate(ctx)
    doc = activation.document()
    doc['expires_at'] = ts(now_ts()+timedelta(days=2))
    with pytest.raises(IntegrityViolation, match='hash'):
        ContractActivationRecord(doc)


@pytest.mark.parametrize('change', [{'contract_hash':'sha256:'+'0'*64}, {'contract_id':new_id()},
    {'run_id':new_id()}, {'project_id':new_id()}])
def test_activation_binding_is_verified(ctx, change):
    contract, activation = activate(ctx)
    with pytest.raises(IntegrityViolation, match='binding'):
        evaluate_authority(contract.with_status('ACTIVE'), resign_activation(activation, **change),
            'commit.propose', run_id=ctx[2], project_id=ctx[1], now=now_ts())


@pytest.mark.parametrize('capability', [None, '', 'commit.apply', 'worker.delegate', 'arbitrary.unknown'])
def test_default_deny_operations(ctx, capability):
    contract, activation = activate(ctx)
    with pytest.raises(CapabilityDenied):
        evaluate_authority(contract.with_status('ACTIVE'), activation, capability,
            run_id=ctx[2], project_id=ctx[1], now=now_ts())


@pytest.mark.parametrize('when', ['expired','future','revoked','draft'])
def test_inactive_authority_is_refused(ctx, when):
    contract, activation = activate(ctx)
    contract = contract.with_status('ACTIVE')
    if when == 'expired':
        activation = resign_activation(activation, expires_at=ts(now_ts()-timedelta(seconds=1)))
    elif when == 'future':
        activation = resign_activation(activation, activated_at=ts(now_ts()+timedelta(seconds=1)))
    elif when == 'revoked':
        activation = resign_activation(activation, revoked_at=ts(now_ts()))
    else:
        contract = contract.with_status('DRAFT')
    with pytest.raises(CapabilityDenied):
        evaluate_authority(contract, activation, 'commit.propose', run_id=ctx[2], project_id=ctx[1], now=now_ts())


@pytest.mark.parametrize('path', ['../outside', 'src/../../outside', '/absolute', './src', 'src//file',
    'src/./file', 'src/../file', 'src\\file', 'C:/file', 'src/\x7ffile', 'src/\nfile', ''])
def test_canonical_path_refuses_aliases(tmp_path, path):
    with pytest.raises(ProtectedPathViolation):
        canonical_path(tmp_path, path)


@pytest.mark.parametrize('path,pattern,expected', [('src/x.py','src/*.py',True),
    ('src/deep/x.py','src/*.py',False), ('src/x.py','src/**/*.py',True),
    ('src/deep/x.py','src/**/*.py',True), ('src/x.py','**',True),
    ('src/x.py','src/[xy].py',True), ('other/x.py','src/**',False)])
def test_component_globs(path, pattern, expected):
    assert matches(path, pattern) is expected


def test_symlink_escape_and_exclusion_alias_are_refused(tmp_path):
    root = tmp_path/'workspace'
    root.mkdir()
    (root/'src').mkdir()
    (root/'private').mkdir()
    (root/'src/escape').symlink_to(tmp_path, target_is_directory=True)
    (root/'src/alias').symlink_to(root/'private', target_is_directory=True)
    contract = StageContract.author(document(scope_include=['src/**'], scope_exclude=['private/**']))
    with pytest.raises(ProtectedPathViolation, match='symlink'):
        authorize_path(contract, root, 'src/escape/file')
    with pytest.raises(CapabilityDenied, match='scope'):
        authorize_path(contract, root, 'src/alias/file')
    (root/'src/real').mkdir()
    (root/'src/link').symlink_to(root/'src/real', target_is_directory=True)
    assert authorize_path(contract, root, 'src/link/new') == 'src/real/new'


@pytest.mark.parametrize('initialized', [True, False])
def test_submodule_escape_is_refused_including_uninitialized(ctx, initialized):
    c, project, run = ctx
    repo = c.governed_repo(project)
    revision = repo.head_revision()
    git(repo.root, 'update-index', '--add', '--cacheinfo', f'160000,{revision},vendor/module')
    if initialized:
        (repo.root/'vendor/module').mkdir(parents=True)
        (repo.root/'vendor/module/.git').write_text('gitdir: outside')
    assert repo.submodule_paths() == frozenset({'vendor/module'})
    with pytest.raises(ProtectedPathViolation, match='submodule'):
        canonical_path(repo.root, 'vendor/module/file', submodules=repo.submodule_paths())


def test_nested_checkout_escape_without_gitlink_is_refused(tmp_path):
    (tmp_path/'module/.git').mkdir(parents=True)
    with pytest.raises(ProtectedPathViolation, match='submodule'):
        canonical_path(tmp_path, 'module/file')


def test_commit_uses_activated_scope_at_proposal_authorization_and_apply(ctx):
    c, project, run = ctx
    contract, record = activate(ctx, scope_include=['src/**'], scope_exclude=['src/private/**'])
    repo = c.governed_repo(project)
    for path in ('outside.txt', 'src/private/key'):
        with pytest.raises(CapabilityDenied):
            c.propose_commit(run, path=path, content='x', message='x')
    intent = c.propose_commit(run, path='src/allowed.txt', content='allowed', message='Allowed')
    original = c.store.connection.execute('SELECT mutations FROM commit_intents WHERE intent_id=?', (intent.intent_id,)).fetchone()[0]
    corrupt = json.loads(original)
    corrupt[0]['path'] = 'outside.txt'
    corrupt[0]['in_scope'] = True
    c.store.raw_execute('UPDATE commit_intents SET mutations=? WHERE intent_id=?', (json.dumps(corrupt), intent.intent_id))
    with pytest.raises(CapabilityDenied):
        c.authorize_commit(intent.intent_id)
    c.store.raw_execute('UPDATE commit_intents SET mutations=? WHERE intent_id=?', (original, intent.intent_id))
    c.authorize_commit(intent.intent_id)
    c.store.raw_execute('UPDATE commit_intents SET mutations=? WHERE intent_id=?', (json.dumps(corrupt), intent.intent_id))
    before = repo.head_revision()
    with pytest.raises(CapabilityDenied):
        c.apply_commit(intent.intent_id)
    assert repo.head_revision() == before and not (repo.root/'outside.txt').exists()
    c.store.raw_execute('UPDATE commit_intents SET mutations=? WHERE intent_id=?', (original, intent.intent_id))
    assert c.apply_commit(intent.intent_id).committed_paths == ('src/allowed.txt',)


def test_commit_checks_rename_destination(ctx):
    c, project, run = ctx
    activate(ctx, scope_include=['README.md'])
    intent = c.propose_commit(run, path='README.md', content='new', message='Change')
    mutation = replace(intent.mutations[0], op=MutationOp.RENAME, rename_to='outside')
    intent.mutations = (mutation,)
    with pytest.raises(CapabilityDenied):
        c._require_commit_authority(intent, c.governed_repo(project))


def test_commit_refuses_symlink_swapped_after_authorization(ctx, tmp_path):
    c, project, run = ctx
    activate(ctx, scope_include=['src/**'])
    intent = c.propose_commit(run, path='src/file', content='new', message='Change')
    c.authorize_commit(intent.intent_id)
    repo = c.governed_repo(project)
    (repo.root/'src').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ProtectedPathViolation):
        c.apply_commit(intent.intent_id)
    assert not (tmp_path/'file').exists()


def test_revoke_between_authorize_and_apply_stops_effect(ctx):
    c, project, run = ctx
    contract, _ = activate(ctx)
    intent = c.propose_commit(run, path='file', content='new', message='Change')
    c.authorize_commit(intent.intent_id)
    c.revoke_contract(contract.contract_id)
    with pytest.raises(CapabilityDenied):
        c.apply_commit(intent.intent_id)
    assert c.store.list_commit_receipts(intent.intent_id) == []


def frozen_role_rows():
    source = Path(__file__).resolve().parents[1] / 'design/authority-matrix.md'
    rows = []
    for line in source.read_text().splitlines():
        cells = [c.strip().replace('`', '') for c in line.split('|')[1:-1]]
        if len(cells) == 6 and '.' in cells[0] and all(c in ('G', 'C', 'D') for c in cells[1:]):
            rows.extend((cells[0], role, cell != 'D') for role, cell in zip(ROLES, cells[1:]))
    return rows


@pytest.mark.parametrize('capability,role,expected', frozen_role_rows())
def test_register_and_role_cells_are_bounds(capability, role, expected):
    from gruntime.authority import role_allows
    assert role_allows(capability, role) is expected


def test_direct_persistence_does_not_activate_document(ctx):
    c, project, run = ctx
    contract = setup_contract(ctx)
    with pytest.raises(IntegrityViolation, match='activation record'):
        c.store.put_contract(contract.with_status('ACTIVE'))
    with pytest.raises(IntegrityViolation, match='DRAFT'):
        c.store.put_contract(StageContract.author(document(project, new_id())).with_status('REVOKED'))


def test_persistence_checks_stored_contract_bindings(ctx):
    c, project, run = ctx
    contract = setup_contract(ctx)
    c.store.raw_execute('UPDATE contracts SET stage_id=? WHERE contract_id=?', (new_id(), contract.contract_id))
    with pytest.raises(IntegrityViolation, match='binding'):
        c.store.get_contract(contract.contract_id)


def test_persistence_checks_activation_bindings(ctx):
    c, project, run = ctx
    contract, record = activate(ctx)
    # A valid hash over a mismatched contract cannot change the durable binding.
    with pytest.raises(IntegrityViolation, match='binding'):
        c.store.put_activation(resign_activation(record, contract_hash='sha256:'+'f'*64))
    c.store.raw_execute('UPDATE activations SET contract_id=? WHERE activation_id=?',
        (c.author_contract(document(project, new_id())).contract_id, record.activation_id))
    with pytest.raises(IntegrityViolation, match='binding'):
        c.store.get_activation(record.activation_id)


def test_activation_refuses_reuse(ctx):
    c, project, run = ctx
    contract, record = activate(ctx)
    with pytest.raises(PolicyDenied, match='already activated'):
        c.activate_contract(contract.contract_id, run)


def test_activation_refuses_run_from_different_stage(ctx):
    c, project, run = ctx
    contract = setup_contract(ctx)
    other = Controller.open_run(c, project)
    with pytest.raises(IntegrityViolation, match='run'):
        c.activate_contract(contract.contract_id, other)


def test_only_one_active_contract_per_stage(ctx):
    c, project, run = ctx
    contract, record = activate(ctx)
    other = Controller.open_run(c, project)
    c.store.raw_execute('UPDATE runs SET stage_id=? WHERE run_id=?', (contract.stage_id, other))
    successor = c.author_contract(document(project, contract.stage_id, contract_version=2))
    before = len(c.store.list_events(project))
    with pytest.raises(IntegrityViolation, match='another contract'):
        c.activate_contract(successor.contract_id, other)
    assert c.store.activation_for_run(other) is None
    assert len(c.store.list_events(project)) == before


def test_activation_needs_complete_snapshot(ctx):
    c, project, run = ctx
    contract = setup_contract(ctx)
    c.store.raw_execute("UPDATE snapshots SET completeness='PARTIAL' WHERE project_id=?", (project,))
    with pytest.raises(PolicyDenied, match='COMPLETE'):
        c.activate_contract(contract.contract_id, run)


@pytest.mark.parametrize('case', ['budget','ceiling','kernel','never','unknown','cwd','timeout','network','supersedes'])
def test_activation_cross_constraints_refuse(ctx, case):
    c, project_id, run = ctx
    overrides = {}
    if case in ('kernel','never','unknown'):
        overrides['capability_request'] = [{'kernel':'commit.apply','never':'worker.delegate','unknown':'future.capability'}[case]]
    if case in ('cwd','timeout','network'):
        spec = validation()
        if case == 'cwd':
            overrides['scope_include'] = ['allowed/**']
        elif case == 'timeout':
            spec['command']['timeout_ms'] = 3600001
        else:
            spec['command']['network'] = 'ALLOWLIST'
        overrides['required_validations'] = [spec]
    if case == 'supersedes':
        prior = c.author_contract(document(project_id, new_id(), contract_version=2))
        overrides['supersedes'] = prior.contract_id
    contract = setup_contract(ctx, **overrides)
    project = c.store.get_project(project_id)
    if case == 'budget':
        project.budget = Budget()
    if case == 'ceiling':
        project.capability_ceiling = frozenset()
    c.store.put_project(project)
    with pytest.raises((CapabilityDenied, PolicyDenied)):
        c.activate_contract(contract.contract_id, run)
    assert c.store.activation_for_run(run) is None


def test_supervised_activation_requires_live_approval(ctx):
    c, project_id, run = ctx
    contract = setup_contract(ctx)
    project = c.store.get_project(project_id)
    project.governance_mode = GovernanceMode.SUPERVISED
    c.store.put_project(project)
    with pytest.raises(CapabilityDenied, match='approval'):
        c.activate_contract(contract.contract_id, run)
    approval = human_grant(ctx, contract, scope=DecisionScope.SINGLE_ACTION, decision_kind=DecisionKind.APPROVE)
    activation = c.activate_contract(contract.contract_id, run, approval_id=approval.decision_id)
    assert activation.governance_mode_at_activation == 'SUPERVISED'
    assert c.store.get_decision(approval.decision_id).decision_state is DecisionState.CONSUMED


def test_policy_document_requires_human_author(ctx):
    c, project_id, _ = ctx
    setup_contract(ctx)
    doc = dict(authored_by=runtime_actor('self-grant'), policy_grantable=['fs.delete'])
    project = c.store.get_project(project_id)
    project.policy_digest = c.store.store_artifact(canonical_json(doc), media_type='application/json').digest
    c.store.put_project(project)
    with pytest.raises(IntegrityViolation, match='human-authored'):
        c.evaluate_grant_policy(project_id)


def test_policy_evaluation_is_immutable_and_replayed_against_document(ctx):
    c, project, run = ctx
    contract = setup_contract(ctx, worker_role='PLANNER', capability_request=['contract.author'])
    evaluation_id = policy(ctx, ['contract.author'])
    evaluation = c.store.get_policy_evaluation(evaluation_id)
    corrupted = dict(evaluation, policy_grantable=['roadmap.writeback'])
    with pytest.raises(IntegrityViolation, match='immutable'):
        c.store.put_policy_evaluation(corrupted)
    c.store.raw_execute('UPDATE policy_evaluations SET document=? WHERE evaluation_id=?', (json.dumps(corrupted), evaluation_id))
    with pytest.raises(IntegrityViolation, match='binding'):
        c.activate_contract(contract.contract_id, run, policy_evaluation_ids=[evaluation_id])


@pytest.mark.parametrize('change', ['mode','policy','ceiling','budget'])
def test_live_authority_rechecks_project_bounds(ctx, change):
    c, project_id, run = ctx
    activate(ctx)
    project = c.store.get_project(project_id)
    if change == 'mode':
        project.governance_mode = GovernanceMode.SUPERVISED
    elif change == 'policy':
        project.policy_digest = digest_json({'new':'policy'})
    elif change == 'ceiling':
        project.capability_ceiling = frozenset({'fs.read'})
    else:
        project.budget_used = BudgetUsage(commits=1000)
    c.store.put_project(project)
    with pytest.raises(CapabilityDenied):
        c.require_authority(run, 'commit.propose')
    if change in ('ceiling','budget'):
        assert c.require_authority(run, 'fs.read', path='README.md') == 'README.md'


def test_prohibited_action_is_not_permitted_by_grant(ctx):
    c, project, run = ctx
    activate(ctx, prohibited_actions=['commit.propose'])
    with pytest.raises(CapabilityDenied, match='prohibits'):
        c.require_authority(run, 'commit.propose')


def test_fs_capability_requires_path(ctx):
    contract, record = activate(ctx)
    with pytest.raises(CapabilityDenied, match='target'):
        evaluate_authority(contract.with_status('ACTIVE'), record, 'fs.read', run_id=ctx[2], project_id=ctx[1], now=now_ts())


def test_valid_record_cannot_expand_request_or_role(ctx):
    contract, record = activate(ctx)
    doc = contract.document()
    doc['capability_request'] = ['fs.read']
    other = StageContract.author(doc).with_status('ACTIVE')
    expanded = resign_activation(record, contract_hash=other.contract_hash)
    with pytest.raises(IntegrityViolation, match='exceeds'):
        evaluate_authority(other, expanded, 'commit.propose', run_id=ctx[2], project_id=ctx[1], now=now_ts())


def test_commit_proposal_requires_both_propose_and_write(ctx):
    c, project, run = ctx
    activate(ctx, capability_request=['fs.write'])
    with pytest.raises(CapabilityDenied):
        c.propose_commit(run, path='feature', content='x', message='x')
    assert c.store.list_commit_intents(run) == []


def test_persisted_intent_cannot_bypass_missing_propose_capability(ctx):
    c, project, run = ctx
    activate(ctx, capability_request=['fs.write'])
    from gruntime.models import CommitIntent, CommitIntentStatus, ReconciliationState, VcsKind, MutationProposal
    from gruntime.commit import mint_operation_token, build_trailers
    repo = c.governed_repo(project)
    token = mint_operation_token()
    intent = CommitIntent(intent_id='fake-intent', run_id=run, stage_id=c.store.get_run(run).stage_id,
        vcs_kind=VcsKind.DVCS, base_revision_id=repo.head_revision(), target_ref='any', expected_tree_digest='unused',
        message='fake', operation_token=token, controller_epoch=1, status=CommitIntentStatus.PROPOSED,
        reconciliation_state=ReconciliationState.NOT_REQUIRED, mutations=(MutationProposal(op=MutationOp.CREATE,
            path='file', in_scope=True),), trailers=build_trailers(token))
    with pytest.raises(CapabilityDenied):
        c._require_commit_authority(intent, repo)


def test_commit_source_guard_independently_checks_scope(ctx):
    c, project, run = ctx
    activate(ctx, scope_include=['README.md'])
    intent = c.propose_commit(run, path='README.md', content='new', message='Change')
    intent.mutations = (replace(intent.mutations[0], path='outside'),)
    with pytest.raises(CapabilityDenied):
        c._require_commit_authority(intent, c.governed_repo(project))


def test_grant_basis_and_contract_survive_database_reopen(ctx):
    c, project, run = ctx
    contract, record = activate(ctx)
    from gruntime.store import StateStore
    reopened = StateStore.open(c.store.db_path)
    try:
        assert reopened.get_activation(record.activation_id) == record
        assert reopened.get_run(run).contract_hash == contract.contract_hash
        assert reopened.get_run(run).effective_capabilities == frozenset(record.granted_capabilities)
        reopened.verify_chain(project)
    finally:
        reopened.close()


def test_activation_must_record_denials_for_every_ungranted_request(ctx):
    c, project, run = ctx
    contract, record = activate(ctx, capability_request=['fs.read','audit.read'])
    incomplete = resign_activation(record, denied_capabilities={})
    with pytest.raises(IntegrityViolation, match='every request'):
        evaluate_authority(contract.with_status('ACTIVE'), incomplete, 'fs.read',
            run_id=run, project_id=project, now=now_ts(), root=c.governed_repo(project).root, path='README.md')


def test_activation_deadline_cannot_expand_frozen_contract(ctx):
    contract, record = activate(ctx)
    longer = resign_activation(record, expires_at=ts(now_ts()+timedelta(days=3)))
    with pytest.raises(IntegrityViolation, match='deadline'):
        evaluate_authority(contract.with_status('ACTIVE'), longer, 'commit.propose',
            run_id=ctx[2], project_id=ctx[1], now=now_ts())


@pytest.mark.parametrize('direction', ['lexical','resolved'])
def test_protected_paths_cannot_use_symlink_aliases(tmp_path, direction):
    (tmp_path/'src').mkdir()
    if direction == 'lexical':
        (tmp_path/'.git').symlink_to(tmp_path/'src', target_is_directory=True)
        path = '.git/secret'
    else:
        (tmp_path/'.git').mkdir()
        (tmp_path/'src/alias').symlink_to(tmp_path/'.git', target_is_directory=True)
        path = 'src/alias/secret'
    with pytest.raises(ProtectedPathViolation, match='protected'):
        authorize_path(StageContract.author(document()), tmp_path, path, write=True)


def test_directly_persisted_policy_evaluation_cannot_supply_nonhuman_policy(ctx):
    c, project_id, run = ctx
    contract = setup_contract(ctx, capability_request=['fs.delete'])
    doc = dict(authored_by=runtime_actor('self-grant'), policy_grantable=['fs.delete'])
    project = c.store.get_project(project_id)
    project.policy_digest = c.store.store_artifact(canonical_json(doc), media_type='application/json').digest
    c.store.put_project(project)
    evaluation = dict(evaluation_id=new_id(), project_id=project_id, policy_digest=project.policy_digest,
        policy_grantable=['fs.delete'], at=ts(now_ts()))
    c.store.put_policy_evaluation(evaluation)
    with pytest.raises(IntegrityViolation, match='human-authored'):
        c.activate_contract(contract.contract_id, run, policy_evaluation_ids=[evaluation['evaluation_id']])


def test_human_class_grant_does_not_replace_exercise_decision(ctx):
    c, project, run = ctx
    contract = setup_contract(ctx, capability_request=['secret.read'])
    decision = human_grant(ctx, contract)
    record = c.activate_contract(contract.contract_id, run, decision_ids=[decision.decision_id])
    with pytest.raises(CapabilityDenied, match='exercise time'):
        c.require_authority(run, 'secret.read')
    approval = human_grant(ctx, contract, scope=DecisionScope.SINGLE_ACTION,
        decision_kind=DecisionKind.APPROVE, subject_kind=DecisionSubjectKind.CAPABILITY, subject_id='secret.read')
    assert c.require_authority(run, 'secret.read', exercise_decision_id=approval.decision_id) is True
    approval.decision_state = DecisionState.CONSUMED
    c.store.put_decision(approval)
    with pytest.raises(CapabilityDenied, match='exercise time'):
        c.require_authority(run, 'secret.read', exercise_decision_id=approval.decision_id)


def test_unchanged_snapshot_preserves_scoped_human_grant(ctx):
    c, project, run = ctx
    contract = setup_contract(ctx, worker_role='PLANNER', capability_request=['roadmap.writeback'])
    decision = human_grant(ctx, contract, scope=DecisionScope.RUN)
    c.activate_contract(contract.contract_id, run, decision_ids=[decision.decision_id])
    c.take_snapshot(project)
    assert c.require_authority(run, 'roadmap.writeback') is True


def test_even_an_empty_grant_needs_an_authority_chain(ctx):
    contract, record = activate(ctx, capability_request=[])
    with pytest.raises(IntegrityViolation, match='chain'):
        resign_activation(record, authority_chain=[])


@pytest.mark.parametrize('field,value', [('grants','["roadmap.writeback"]'), ('scope','RUN'), ('nonce','edited-nonce-0000000')])
def test_persisted_human_grant_tampering_is_refused(ctx, field, value):
    c, project, run = ctx
    contract = setup_contract(ctx, worker_role='PLANNER', capability_request=['roadmap.writeback'])
    decision = human_grant(ctx, contract, grants=frozenset())
    c.store.raw_execute(f'UPDATE decisions SET {field}=? WHERE decision_id=?', (value, decision.decision_id))
    with pytest.raises(IntegrityViolation, match='decision integrity'):
        c.activate_contract(contract.contract_id, run, decision_ids=[decision.decision_id])
    assert c.store.activation_for_run(run) is None
