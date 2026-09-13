"""GR-09: real processes, OS sandbox boundaries, durable catalog and recovery."""
import ast
from dataclasses import FrozenInstanceError, replace
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import time

import pytest

from gruntime.canonical import digest_json
from gruntime.errors import BarrierViolation, PolicyDenied
from gruntime.models import Completeness, EpistemicClass
from gruntime.validation import ValidationExecutor
from gruntime.validation_catalog import ParameterRef, ParameterSchema, ValidationCatalog, ValidationOperation

PYTHON = str(Path(sys.executable).resolve())


def operation(**changes):
    fields = dict(operation_id='test.check', version='1.0.0',
                  argv=(PYTHON, '-c', 'import sys; print(sys.argv[1])', ParameterRef('value')),
                  parameters={'value': ParameterSchema('string')}, cwd='src', env_allowlist=(),
                  network='NONE', timeout_ms=3000, write_policy='READ_ONLY',
                  side_effect_class='READ_ONLY', safe_to_rerun=True)
    fields.update(changes)
    return ValidationOperation(**fields)


@pytest.fixture
def runtime(h):
    workspace = h.root / 'workspace'
    (workspace / 'src').mkdir(parents=True)
    (workspace / 'src' / 'input.txt').write_text('observed')
    with h.controller() as c:
        project = c.create_project(name='Validation', slug='validation', workspace_root=str(workspace))
        c.start(project)
        run = c.open_run(project)
        snapshot = c.take_snapshot(project)
    return h, project, run, snapshot, workspace


def bind(c, run, op=None, values=None):
    op = op or operation()
    c.validation_catalog.register(op)
    return c.bind_validations(run, {'check': {'operation': op.reference, 'parameters': values or {'value': 'hello'}}})


def output(c, receipt):
    return c.artifacts.get(receipt.stdout_ref.digest).decode().strip()


def test_shell_metacharacters_are_literal_argv(runtime):
    h, project, run, snapshot, workspace = runtime
    marker = workspace / 'SHELL_EXECUTED'
    value = f'x; touch {marker}; $(touch /workspace/SHELL_EXECUTED) `touch /workspace/ALSO` | echo injected > /workspace/SHELL_EXECUTED'
    with h.controller() as c:
        bind(c, run, operation(write_policy='WORKSPACE_COPY', side_effect_class='SANDBOX_WRITE'), {'value': value})
        receipt = c.execute_validation(run, 'check')
        assert receipt.verdict == 'PASS'
        assert output(c, receipt) == value
        assert not marker.exists()
        assert receipt.operation_ref == 'test.check@1.0.0'
        assert receipt.parameters == {'value': value}
        assert receipt.input_snapshot_id == snapshot
        assert receipt.exit_code == 0
        c.store.verify_chain(project)
        recorded = c._validation_attempts(project)[receipt.op_id]['receipt']
        assert recorded == json.loads(json.dumps(receipt.document()))


def test_executor_explicitly_forbids_shell_execution():
    import gruntime.validation as module
    tree = ast.parse(Path(module.__file__).read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'Popen']
    assert calls
    assert all(any(k.arg == 'shell' and isinstance(k.value, ast.Constant) and k.value.value is False for k in n.keywords) for n in calls)


@pytest.mark.parametrize('reference', ['test.check', 'test.check@latest', 'test.check@1', 'test.check@1.0.1', 'absent@1.0.0'])
def test_unknown_or_unversioned_operation_refused(runtime, reference):
    h, _, run, _, _ = runtime
    with h.controller() as c:
        c.validation_catalog.register(operation())
        with pytest.raises(PolicyDenied):
            c.bind_validations(run, {'check': {'operation': reference, 'parameters': {'value': 'x'}}})


def test_catalog_versions_and_nested_entries_are_immutable(tmp_path):
    params = {'value': ParameterSchema('string', choices=['a', 'b'])}
    argv = [PYTHON, '-c', 'pass', ParameterRef('value')]
    op = operation(parameters=params, argv=argv)
    params.clear()
    argv.clear()
    assert op.parameters['value'].choices == ('a', 'b')
    with pytest.raises(TypeError):
        op.parameters['new'] = ParameterSchema('boolean')
    with pytest.raises(FrozenInstanceError):
        op.version = '2.0.0'
    catalog = ValidationCatalog(tmp_path / 'catalog.db')
    catalog.register(op)
    catalog.register(op)
    with pytest.raises(PolicyDenied):
        catalog.register(replace(op, cwd='elsewhere'))
    catalog.register(replace(op, version='2.0.0', cwd='new'))
    reopened = ValidationCatalog(catalog.path)
    assert reopened.resolve(op.reference).cwd == 'src'
    assert reopened.resolve('test.check@2.0.0').cwd == 'new'


@pytest.mark.parametrize('values', [{}, {'value':'x', 'cwd':'elsewhere'}, {'value': True}, {'value': 2}, {'value':'\x00'}, {'value':'long'*2000}])
def test_bad_parameters_refused_before_process(runtime, values):
    h, project, run, _, _ = runtime
    with h.controller() as c:
        c.validation_catalog.register(operation())
        with pytest.raises(PolicyDenied):
            c.bind_validations(run, {'check': {'operation':'test.check@1.0.0', 'parameters':values}})
        assert not c._validation_attempts(project)


@pytest.mark.parametrize('schema,value', [(ParameterSchema('integer', minimum=1, maximum=3), True),
                                         (ParameterSchema('integer', minimum=1, maximum=3), 4),
                                         (ParameterSchema('integer', minimum=1, maximum=3), '2'),
                                         (ParameterSchema('boolean'), 0),
                                         (ParameterSchema('string', choices=('yes',)), 'no')])
def test_type_and_constraint_checks(schema, value):
    with pytest.raises(PolicyDenied):
        schema.validate(value)


@pytest.mark.parametrize('schema,value,expected', [(ParameterSchema('integer', minimum=-3, maximum=3), -3, '-3'),
                                                 (ParameterSchema('boolean'), False, 'false')])
def test_typed_values_pass_as_one_arg(runtime, schema, value, expected):
    h, _, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run, operation(parameters={'value':schema}), {'value':value})
        assert output(c, c.execute_validation(run, 'check')) == expected


@pytest.mark.parametrize('value', ['../input.txt', 'nested/../input.txt', '/etc/passwd', './input.txt', 'a\\b'])
def test_path_traversal_refused(runtime, value):
    h, _, run, _, _ = runtime
    with h.controller() as c:
        with pytest.raises(PolicyDenied):
            bind(c, run, operation(parameters={'value':ParameterSchema('path', root='src')}), {'value':value})


def test_symlink_escape_and_symlink_root_escape_refused(runtime):
    h, _, run, _, workspace = runtime
    (workspace / 'src' / 'escape').symlink_to(h.root, target_is_directory=True)
    (workspace / 'escape').symlink_to(h.root, target_is_directory=True)
    op = operation(parameters={'value':ParameterSchema('path', root='src')})
    with pytest.raises(PolicyDenied):
        op.validate_parameters({'value':'escape/file'}, workspace)
    with pytest.raises(PolicyDenied):
        operation(parameters={'value':ParameterSchema('path', root='escape')}).validate_parameters({'value':'file'}, workspace)
    with pytest.raises(PolicyDenied):
        from gruntime.validation_catalog import contained
        contained(workspace, '../outside')


def test_internal_symlink_canonicalizes_to_declared_root(runtime):
    _, _, _, _, workspace = runtime
    (workspace / 'src' / 'alias').symlink_to('input.txt')
    op = operation(parameters={'value':ParameterSchema('path', root='src')})
    assert op.validate_parameters({'value':'alias'}, workspace)['value'] == '/workspace/src/input.txt'


def test_policy_is_catalog_owned_and_environment_is_allowlisted(runtime, monkeypatch):
    h, _, run, _, _ = runtime
    monkeypatch.setenv('GR_ALLOWED', 'visible')
    monkeypatch.setenv('GR_SECRET', 'hidden')
    script = 'import os,json; print(json.dumps([os.getcwd(), dict(os.environ)]))'
    with h.controller() as c:
        bind(c, run, operation(argv=(PYTHON, '-c', script), env_allowlist=('GR_ALLOWED',)))
        receipt = c.execute_validation(run, 'check')
        cwd, env = json.loads(output(c, receipt))
        assert cwd == '/workspace/src'
        assert env['GR_ALLOWED'] == 'visible'
        assert 'GR_SECRET' not in env and 'PATH' not in env
        assert receipt.env_digest == digest_json({'GR_ALLOWED':'visible'})
        with pytest.raises(TypeError):
            c.execute_validation(run, 'check', cwd='/tmp')


@pytest.mark.parametrize('field', ['cwd', 'env_allowlist', 'network', 'timeout_ms', 'write_policy', 'command'])
def test_contract_cannot_override_catalog_policy(runtime, field):
    h, _, run, _, _ = runtime
    with h.controller() as c:
        c.validation_catalog.register(operation())
        with pytest.raises(PolicyDenied):
            c.bind_validations(run, {'check': {'operation':'test.check@1.0.0', 'parameters':{'value':'x'}, field:'override'}})


def test_contract_cannot_be_rebound(runtime):
    h, _, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run)
        bind(c, run)
        with pytest.raises(PolicyDenied):
            bind(c, run, values={'value':'different'})
        with pytest.raises(PolicyDenied):
            c.execute_validation(run, 'absent')


def test_catalog_tampering_cannot_change_pinned_command(runtime):
    h, _, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run)
        with sqlite3.connect(c.validation_catalog.path) as db:
            doc = operation(timeout_ms=1000).document()
            db.execute('UPDATE operations SET document=?', (json.dumps(doc),))
        with pytest.raises(PolicyDenied):
            c.execute_validation(run, 'check')
        with sqlite3.connect(c.validation_catalog.path) as db:
            doc['operation_id'] = 'wrong'
            db.execute('UPDATE operations SET document=?', (json.dumps(doc),))
        with pytest.raises(PolicyDenied):
            c.validation_catalog.resolve('test.check@1.0.0')


@pytest.mark.parametrize('policy,side_effect,path,code', [('READ_ONLY','READ_ONLY','/workspace/src/out',1),
                                                       ('READ_ONLY','READ_ONLY','/scratch/out',1),
                                                       ('SCRATCH','SANDBOX_WRITE','/scratch/out',0),
                                                       ('SCRATCH','SANDBOX_WRITE','/workspace/src/out',1),
                                                       ('WORKSPACE_COPY','SANDBOX_WRITE','/workspace/src/out',0)])
def test_write_policy_is_enforced_by_os(runtime, policy, side_effect, path, code):
    h, _, run, _, workspace = runtime
    script = f'from pathlib import Path; Path({path!r}).write_text("output")'
    with h.controller() as c:
        bind(c, run, operation(argv=(PYTHON,'-c',script), write_policy=policy, side_effect_class=side_effect))
        receipt = c.execute_validation(run, 'check')
        assert receipt.exit_code == code
        assert receipt.verdict == ('PASS' if code == 0 else 'FAIL')
    assert not (workspace / 'src' / 'out').exists()


@pytest.mark.parametrize('network,expected', [('NONE','FAIL'), ('ANY','PASS'), ('ALLOWLIST','ERROR')])
def test_network_policy_is_enforced_by_os(runtime, network, expected):
    h, _, run, _, _ = runtime
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0))
        listener.listen()
        script = f'import socket; socket.create_connection(("127.0.0.1",{listener.getsockname()[1]}),timeout=.2)'
        with h.controller() as c:
            bind(c, run, operation(argv=(PYTHON,'-c',script), network=network, side_effect_class='EXTERNAL'))
            receipt = c.execute_validation(run, 'check')
            assert receipt.verdict == expected
            if network == 'ALLOWLIST':
                assert receipt.exit_code is None


def test_timeout_terminates_process_and_children(runtime):
    h, _, run, _, _ = runtime
    script = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"]); time.sleep(30)'
    with h.controller() as c:
        bind(c, run, operation(argv=(PYTHON,'-c',script), timeout_ms=200))
        receipt = c.execute_validation(run, 'check')
        assert receipt.verdict == 'TIMEOUT'
        assert receipt.duration_ms < 4000
        assert receipt.exit_code < 0


def test_unavailable_executable_returns_error(runtime):
    h, _, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run, operation(argv=('/usr/bin/missing-gr09-executable',)))
        assert c.execute_validation(run, 'check').verdict == 'ERROR'


def test_expected_exit_codes_control_verdict(runtime):
    h, _, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run, operation(argv=(PYTHON,'-c','raise SystemExit(7)'), expected_exit_codes=(7,)))
        receipt = c.execute_validation(run, 'check')
        assert (receipt.exit_code, receipt.verdict) == (7, 'PASS')


@pytest.mark.parametrize('completeness', [Completeness.PARTIAL, Completeness.TRUNCATED, Completeness.FAILED])
def test_incomplete_observations_block_controller_and_executor(runtime, completeness):
    h, project, run, snapshot_id, workspace = runtime
    with h.controller() as c:
        bind(c, run)
        snapshot = c.store.get_snapshot(snapshot_id)
        incomplete = replace(snapshot, snapshot_id='incomplete', completeness=completeness)
        executor = ValidationExecutor(c.validation_catalog, c.artifacts)
        with pytest.raises(PolicyDenied):
            executor.execute('test.check@1.0.0', {'value':'x'}, snapshot=incomplete,
                             snapshot_document=c.store.snapshot_document(snapshot), workspace_root=workspace,
                             run_id=run, op_id='x', prev_event_hash='x')
        c.store.put_snapshot(incomplete)
        assert c.store.get_project(project).snapshot_current == snapshot_id
        with pytest.raises(PolicyDenied):
            c.execute_validation(run, 'check')
        assert not c._validation_attempts(project)


def test_validation_requires_snapshot_even_before_first_observation(h):
    workspace = h.root / 'w'
    workspace.mkdir()
    with h.controller() as c:
        project = c.create_project(name='No snapshot',slug='none',workspace_root=str(workspace))
        run = c.open_run(project)
        bind(c, run)
        with pytest.raises(PolicyDenied):
            c.execute_validation(run, 'check')


def test_changed_snapshot_content_and_document_are_refused(runtime):
    h, _, run, snapshot_id, workspace = runtime
    with h.controller() as c:
        bind(c, run)
        snapshot = c.store.get_snapshot(snapshot_id)
        executor = ValidationExecutor(c.validation_catalog, c.artifacts)
        with pytest.raises(PolicyDenied):
            executor.execute('test.check@1.0.0', {'value':'x'}, snapshot=snapshot,
                             snapshot_document={'committed':{},'dirty':{}}, workspace_root=workspace,
                             run_id=run, op_id='x', prev_event_hash='x')
        (workspace / 'src' / 'input.txt').write_text('unobserved')
        with pytest.raises(PolicyDenied):
            c.execute_validation(run, 'check')


def test_partial_scope_and_missing_cwd_refused(runtime):
    h, project, run, snapshot_id, workspace = runtime
    with h.controller() as c:
        bind(c, run)
        snapshot = c.store.get_snapshot(snapshot_id)
        c.store.put_snapshot(replace(snapshot, snapshot_id='partial-scope', scope=('elsewhere/**',)))
        with pytest.raises(PolicyDenied):
            c.execute_validation(run, 'check')
        c.store.put_snapshot(replace(snapshot, snapshot_id='whole-again'))
        (workspace / 'src' / 'input.txt').unlink()
        (workspace / 'src').rmdir()
        with pytest.raises(PolicyDenied):
            c.execute_validation(run, 'check')


@pytest.mark.parametrize('changes', [
    {'version':'latest'}, {'version':'01.0.0'}, {'operation_id':'bad/id'}, {'operation_id':123},
    {'argv':()}, {'argv':('python',)}, {'argv':(ParameterRef('value'),)},
    {'argv':(PYTHON, ParameterRef('missing'))}, {'argv':(PYTHON, '\x00')},
    {'parameters':{'BAD':ParameterSchema('string')}, 'argv':(PYTHON,)},
    {'parameters':{'value':'string'}, 'argv':(PYTHON,)},
    {'cwd':'../escape'}, {'cwd':'/tmp'}, {'env_allowlist':('bad-name',)},
    {'env_allowlist':('PATH','PATH')}, {'network':'UNKNOWN'}, {'timeout_ms':0},
    {'timeout_ms':True}, {'timeout_ms':86400001}, {'write_policy':'HOST'},
    {'side_effect_class':'UNKNOWN'}, {'safe_to_rerun':'yes'},
    {'expected_exit_codes':()}, {'expected_exit_codes':(True,)},
    {'write_policy':'WORKSPACE_COPY'}, {'network':'ANY'},
])
def test_malformed_catalog_entries_are_refused(changes):
    with pytest.raises(PolicyDenied):
        operation(**changes)


@pytest.mark.parametrize('fields', [dict(kind='unknown'), dict(kind='path'),
                                  dict(kind='path',root='../out'), dict(kind='string',root='src'),
                                  dict(kind='integer',minimum=5,maximum=3), dict(kind='string',choices=['\x00'])])
def test_malformed_parameter_schemas_refused(fields):
    with pytest.raises(PolicyDenied):
        ParameterSchema(**fields)


@pytest.mark.parametrize('safe,side_effect,expected', [(True,'READ_ONLY',True), (False,'READ_ONLY',False),
                                                     (True,'SANDBOX_WRITE',True), (True,'EXTERNAL',False)])
def test_crash_recovery_enforces_both_rerun_declarations(runtime, safe, side_effect, expected):
    h, project, run, _, _ = runtime
    policy = 'SCRATCH' if side_effect == 'SANDBOX_WRITE' else 'READ_ONLY'
    with h.controller() as c:
        bind(c, run, operation(safe_to_rerun=safe, side_effect_class=side_effect, write_policy=policy))
    proc = h.spawn(project, 'validate', '--run', run, '--spec', 'check', gate='after_validation_before_receipt')
    try:
        h.wait_for_gate('after_validation_before_receipt', proc, timeout=10)
    finally:
        h.kill9(proc)
    with h.controller() as c:
        attempts = c._validation_attempts(project)
        assert len(attempts) == 1
        op_id = next(iter(attempts))
        assert attempts[op_id]['status'] == 'EXECUTING'
        assert 'receipt' not in attempts[op_id]
        with pytest.raises(BarrierViolation):
            c.create_invocation(run, prompt=b'blocked')
        with pytest.raises(BarrierViolation):
            c.execute_validation(run, 'check')
        with pytest.raises(PolicyDenied):
            c.retry_validation(run, op_id)
        c.start(project)
        recovered = c.recover(project)
        assert len(c._validation_attempts(project)) == 1, 'recovery ran a process'
        if expected:
            assert list(recovered.validations_reconciled) == [op_id]
            receipt = c.retry_validation(run, op_id)
            assert receipt.verdict == 'PASS'
            assert receipt.op_id != op_id
        else:
            assert op_id in recovered.unresolved
            assert c.store.list_escalations(project)[-1].trigger.value == 'RECOVERY_AMBIGUITY'
            with pytest.raises(PolicyDenied):
                c.retry_validation(run, op_id)
            with pytest.raises(BarrierViolation):
                c.execute_validation(run, 'check')
        c.start(project)
        repeated = c.recover(project)
        if not expected:
            assert op_id in repeated.unresolved
        assert len(c._validation_attempts(project)) == (2 if expected else 1)
        c.store.verify_chain(project)


def test_retry_rechecks_policy_and_completeness(runtime):
    h, project, run, snapshot_id, _ = runtime
    with h.controller() as c:
        bind(c, run, operation(safe_to_rerun=False))
        # Adversarial durable state: a legacy reconciler incorrectly cancelled
        # an unsafe operation. Retry must independently consult the catalog.
        c._append(project,event_type='validation.executing',epistemic_class=EpistemicClass.AUTHORITY,
                  subject={'run_id':run,'op_id':'unsafe'},payload={'op_id':'unsafe','run_id':run,'spec_id':'check','controller_epoch':0},
                  capability_used='validation.execute')
        c._append(project,event_type='validation.recovered',epistemic_class=EpistemicClass.AUTHORITY,
                  subject={'run_id':run,'op_id':'unsafe'},payload={'op_id':'unsafe','status':'CANCELLED'},
                  capability_used='recovery.reconcile')
        with pytest.raises(PolicyDenied, match='recovery forbids'):
            c.retry_validation(run, 'unsafe')


def test_receipt_round_trip_is_immutable_and_recovery_adopts_without_rerun(runtime):
    from gruntime.validation import ValidationReceipt
    from gruntime.models import ActorKind, Encoding
    h, project, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run)
        receipt = c.execute_validation(run,'check')
        restored = ValidationReceipt.from_document(json.loads(json.dumps(receipt.document())))
        assert restored.receipt_hash == receipt.receipt_hash
        assert restored.executor_identity.actor_kind is ActorKind.RUNTIME
        assert restored.stdout_ref.encoding is Encoding.IDENTITY
        with pytest.raises(TypeError):
            restored.parameters['value'] = 'new'
        c.start(project)
        c.recover(project)
        assert len(c._validation_attempts(project)) == 1
        assert c._validation_attempts(project)[receipt.op_id]['receipt_hash'] == receipt.receipt_hash


def test_path_syntax_rejects_traversal_even_when_destination_is_contained(runtime):
    from gruntime.validation_catalog import contained
    _, _, _, _, workspace = runtime
    with pytest.raises(PolicyDenied, match='without traversal'):
        contained(workspace, 'src/../src/input.txt')


@pytest.mark.parametrize('reference', ['test.check', 'test.check@latest', 'test.check@1'])
def test_version_refusal_is_explicit_before_catalog_lookup(tmp_path, reference):
    with pytest.raises(PolicyDenied, match='explicit id@version'):
        ValidationCatalog(tmp_path / 'catalog.db').resolve(reference)


@pytest.mark.parametrize('path', ['/tmp/out', '/dev/shm/out', '/etc/gr09-out'])
def test_readonly_policy_has_no_implicit_output_directory(runtime, path):
    h, _, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run, operation(argv=(PYTHON,'-c',f'from pathlib import Path; Path({path!r}).write_text("x")')))
        assert c.execute_validation(run,'check').verdict == 'FAIL'


def test_suspension_blocks_validation(runtime):
    from gruntime.models import SuspensionState
    h, project, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run)
        c.store.set_project_suspension(project,SuspensionState.SUSPENDED_BY_POLICY)
        with pytest.raises(PolicyDenied):
            c.execute_validation(run,'check')
        assert not c._validation_attempts(project)


def test_recovery_leaves_current_epoch_and_completed_attempts_alone(runtime):
    h, project, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run)
        receipt = c.execute_validation(run,'check')
        c.start(project)
        c.recover(project)
        assert c._validation_attempts(project)[receipt.op_id]['status'] == 'COMPLETED'
        epoch = c.store.get_project(project).controller_epoch
        c._append(project,event_type='validation.executing',epistemic_class=EpistemicClass.AUTHORITY,
                  subject={'run_id':run,'op_id':'live'},payload={'op_id':'live','run_id':run,'spec_id':'check','controller_epoch':epoch},
                  capability_used='validation.execute')
        c.recover(project)
        assert c._validation_attempts(project)['live']['status'] == 'EXECUTING'


def test_retry_is_blocked_by_a_later_failed_observation(runtime):
    h, project, run, snapshot_id, _ = runtime
    with h.controller() as c:
        bind(c, run)
        c._append(project,event_type='validation.executing',epistemic_class=EpistemicClass.AUTHORITY,
                  subject={'run_id':run,'op_id':'safe'},payload={'op_id':'safe','run_id':run,'spec_id':'check','controller_epoch':0},
                  capability_used='validation.execute')
        c.recover(project)
        assert c._validation_attempts(project)['safe']['status'] == 'CANCELLED'
        c.store.put_snapshot(replace(c.store.get_snapshot(snapshot_id),snapshot_id='failed',completeness=Completeness.FAILED))
        with pytest.raises(PolicyDenied):
            c.retry_validation(run,'safe')
        assert len(c._validation_attempts(project)) == 1


def test_catalog_pins_canonical_executable(runtime):
    h, _, run, _, _ = runtime
    with h.controller() as c:
        op = operation(argv=(sys.executable,'-c','print("canonical")'))
        assert op.argv[0] == PYTHON
        bind(c,run,op)
        assert output(c,c.execute_validation(run,'check')) == 'canonical'


def test_path_parameter_reads_observed_copy_and_excludes_unobserved_files(runtime):
    h, _, run, _, workspace = runtime
    (workspace / 'src' / 'unobserved.txt').write_text('outside the snapshot')
    script = 'import sys,json; from pathlib import Path; p=Path(sys.argv[1]); print(json.dumps([str(p),p.read_text(),sorted(x.name for x in p.parent.iterdir())]))'
    with h.controller() as c:
        bind(c,run,operation(argv=(PYTHON,'-c',script,ParameterRef('value')),
                             parameters={'value':ParameterSchema('path',root='src')}),
             {'value':'input.txt'})
        receipt=c.execute_validation(run,'check')
        assert receipt.verdict == 'PASS'
        assert json.loads(output(c,receipt)) == ['/workspace/src/input.txt','observed',['input.txt']]
        assert receipt.parameters == {'value':'input.txt'}


def test_receipt_binds_to_event_head_at_attestation(runtime):
    import threading
    h, project, run, _, _ = runtime
    with h.controller() as c:
        bind(c,run,operation(argv=(PYTHON,'-c','import time; time.sleep(1)')))
    receipts, failures = [], []
    def execute():
        try:
            with h.controller() as c:
                receipts.append(c.execute_validation(run,'check'))
        except BaseException as exc:
            failures.append(exc)
    thread=threading.Thread(target=execute)
    thread.start()
    try:
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            with h.controller() as c:
                if c._validation_attempts(project):
                    c._append(project,event_type='observation.concurrent',epistemic_class=EpistemicClass.CLAIM,
                              subject={'run_id':run},payload={'note':'arrived during execution'})
                    break
            time.sleep(.01)
        else:
            pytest.fail('validation never started')
    finally:
        thread.join(timeout=5)
    assert not thread.is_alive() and not failures
    with h.controller() as c:
        event=c.store.list_events(project)[-1]
        assert event.event_type == 'validation.receipt'
        assert receipts[0].prev_event_hash == event.prev_event_hash
        c.store.verify_chain(project)
