"""GR-10: real Git transactions and failures before the commit command."""
import json
from dataclasses import replace
from pathlib import Path
import subprocess

import pytest

from gruntime.adapters.git_repo import GitRepository
from gruntime.canonical import digest_bytes
from gruntime.commit import (
    commit_message, exact_paths, expected_entries, expected_tree_digest,
    message_fields, verification_errors, verify_receipt,
)
from gruntime.errors import BarrierViolation, IntegrityViolation, PolicyDenied, ProtectedPathViolation
from gruntime.models import (
    CommitIntentStatus, MutationOp, MutationProposal, Verification,
    SuspensionState, Completeness, ReconciliationState,
)
from gr03_support import git, project_with_repo
from gruntime.store import mutation_to_dict


@pytest.fixture
def tx(h):
    project = project_with_repo(h, slug="gr10")
    with h.controller(with_repo=True) as c:
        run = c.open_run(project)
        intent = c.propose_commit(run, path="feature.txt", content="feature\n",
                                  message="Add feature\n\nDetailed explanation.\n")
        c.authorize_commit(intent.intent_id)
        yield c, project, c.store.get_commit_intent(intent.intent_id), c.governed_repo(project)


def persist(c, project, intent):
    c.store.put_commit_intent(intent, project)
    # Deliberately corrupt immutable fields to exercise consuming guards.
    c.store.raw_execute("UPDATE commit_intents SET message=?, mutations=? WHERE intent_id=?",
                        (intent.message, json.dumps([mutation_to_dict(m) for m in intent.mutations]), intent.intent_id))


def test_transaction_receipt_records_and_verifies_every_field(tx):
    c, project, intent, repo = tx
    receipt = c.apply_commit(intent.intent_id)
    observed = repo.observe_commit(receipt.revision_id, intent=intent)
    assert receipt.verification is Verification.MATCHED
    assert receipt.revision_id == git(repo.root, 'rev-parse', 'HEAD')
    assert receipt.parent_revision_ids == (intent.base_revision_id,)
    assert receipt.tree_id == git(repo.root, 'rev-parse', 'HEAD^{tree}')
    assert receipt.actual_tree_digest == intent.expected_tree_digest
    assert (receipt.subject, receipt.body_hash) == message_fields(commit_message(intent))
    assert receipt.committed_paths == ('feature.txt',)
    assert receipt.files_changed == ({'path': 'feature.txt', 'op': 'CREATE',
        'before_digest': None, 'after_digest': digest_bytes(b'feature\n')},)
    assert verify_receipt(intent, receipt, observed) is Verification.MATCHED
    assert c.store.list_commit_receipts(intent.intent_id) == [receipt]
    assert c.verify_commit(intent.intent_id) is Verification.MATCHED
    c.store.verify_chain(project)


@pytest.mark.parametrize('args', [('add', '.'), ('add', '-A'), ('add', '--all'),
                                  ('add', '-A', 'README.md'), ('add', '--', '.'),
                                  ('add', '--', 'subdir')])
def test_blanket_staging_is_rejected_before_subprocess(tx, monkeypatch, args):
    c, project, intent, repo = tx
    (repo.root / 'subdir').mkdir()
    calls = []
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: calls.append(a))
    with pytest.raises((PolicyDenied, ProtectedPathViolation)):
        repo._git(*args)
    assert calls == []


@pytest.mark.parametrize('path', ['../escape', '.git', '.gitmodules', './README.md',
                                 '-A', ':/*', 'README.md\0other'])
def test_staging_rejects_unsafe_paths(tx, monkeypatch, path):
    repo = tx[3]
    calls = []
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: calls.append(a))
    with pytest.raises((PolicyDenied, ProtectedPathViolation)):
        repo.stage([path])
    assert calls == []


def test_empty_exact_paths_are_refused(tx):
    with pytest.raises(PolicyDenied):
        tx[3]._exact_paths(())


@pytest.mark.parametrize('method,args', [('publish', ()), ('_git', ('push',)),
                                       ('_git', ('-c', 'alias.send=push', 'send'))])
def test_adapter_push_capability_never_reaches_a_subprocess(tx, monkeypatch, method, args):
    calls = []
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: calls.append(a))
    with pytest.raises(PolicyDenied, match='DENIED'):
        getattr(tx[3], method)(*args)
    assert calls == []


def test_controller_publication_is_denied_before_adapter(tx, monkeypatch):
    c, project, intent, repo = tx
    monkeypatch.setattr(repo, 'publish', lambda: pytest.fail('publication reached adapter'))
    with pytest.raises(PolicyDenied, match='commit.publish'):
        c.publish_commit(intent.intent_id)


def test_no_transaction_or_recovery_command_is_push(tx, monkeypatch):
    c, project, intent, repo = tx
    original = subprocess.run
    calls = []
    def trace(argv, *args, **kwargs):
        calls.append(argv)
        assert 'push' not in argv
        return original(argv, *args, **kwargs)
    monkeypatch.setattr(subprocess, 'run', trace)
    c.apply_commit(intent.intent_id)
    c.start(project)
    c.recover(project)
    assert any('commit' in argv for argv in calls)


@pytest.mark.parametrize('contamination', ['extra', 'protected', 'content', 'mode', 'delete'])
def test_staged_divergence_aborts_before_commit(tx, monkeypatch, contamination):
    c, project, intent, repo = tx
    original = GitRepository.stage
    commits = []
    raw = GitRepository._git
    def stage(self, paths):
        original(self, paths)
        if contamination in ('extra', 'protected'):
            name = '.gitmodules' if contamination == 'protected' else 'extra.txt'
            (self.root / name).write_text('surprise\n')
            git(self.root, 'add', '--', name)
        elif contamination == 'content':
            (self.root / 'feature.txt').write_text('different\n')
            git(self.root, 'add', '--', 'feature.txt')
        elif contamination == 'mode':
            git(self.root, 'update-index', '--chmod=+x', 'feature.txt')
        else:
            git(self.root, 'rm', '--', 'README.md')
    def trace(self, *args, **kwargs):
        if args[0] == 'commit':
            commits.append(args)
        return raw(self, *args, **kwargs)
    monkeypatch.setattr(GitRepository, 'stage', stage)
    monkeypatch.setattr(GitRepository, '_git', trace)
    with pytest.raises(IntegrityViolation, match='staged'):
        c.apply_commit(intent.intent_id)
    assert commits == []
    assert repo.head_revision() == intent.base_revision_id
    assert c.store.list_commit_receipts(intent.intent_id) == []


def test_staging_leaves_unrelated_untracked_and_dirty_files_out(tx):
    c, _, intent, repo = tx
    (repo.root / 'scratch.txt').write_text('scratch')
    (repo.root / 'README.md').write_text('user edit')
    receipt = c.apply_commit(intent.intent_id)
    assert receipt.committed_paths == ('feature.txt',)
    assert git(repo.root, 'show', 'HEAD:README.md') == 'base'
    assert (repo.root / 'README.md').read_text() == 'user edit'
    assert 'scratch.txt' not in repo.file_index()


def test_literal_glob_filename_never_expands(tx):
    c, project, _, repo = tx
    (repo.root / 'surprise.txt').write_text('untracked')
    intent = c.propose_commit(tx[2].run_id, path='*.txt', content='literal', message='Literal')
    c.authorize_commit(intent.intent_id)
    receipt = c.apply_commit(intent.intent_id)
    assert receipt.committed_paths == ('*.txt',)
    assert 'surprise.txt' not in repo.file_index()


@pytest.mark.parametrize('change', ['parent', 'branch', 'detached'])
def test_expected_parent_and_branch_checked_after_staging(tx, monkeypatch, change):
    c, _, intent, repo = tx
    original = GitRepository.stage
    def stage(self, paths):
        original(self, paths)
        if change == 'parent':
            git(self.root, 'commit', '--allow-empty', '--only', '-m', 'external')
        elif change == 'branch':
            git(self.root, 'checkout', '-b', 'unexpected')
        else:
            git(self.root, 'checkout', '--detach')
    monkeypatch.setattr(GitRepository, 'stage', stage)
    with pytest.raises(IntegrityViolation):
        c.apply_commit(intent.intent_id)
    assert repo.find_by_token(intent.operation_token) == []


def test_verified_index_is_pinned_against_later_index_edits(tx, monkeypatch):
    c, _, intent, repo = tx
    original = GitRepository.verify_staged
    def verify(self, *args, **kwargs):
        tree = original(self, *args, **kwargs)
        (self.root / 'extra').write_text('too late')
        git(self.root, 'add', '--', 'extra')
        return tree
    monkeypatch.setattr(GitRepository, 'verify_staged', verify)
    receipt = c.apply_commit(intent.intent_id)
    assert receipt.committed_paths == ('feature.txt',)


def test_commit_hooks_cannot_mutate_or_publish(tx):
    c, _, intent, repo = tx
    hook = Path(git(repo.root, 'rev-parse', '--git-common-dir')) / 'hooks' / 'pre-commit'
    hook.write_text('#!/bin/sh\necho ran > hook-ran\nexit 99\n')
    hook.chmod(0o755)
    assert c.apply_commit(intent.intent_id).verification is Verification.MATCHED
    assert not (repo.root / 'hook-ran').exists()


def test_git_environment_cannot_redirect_the_index_or_repository(tx, monkeypatch, tmp_path):
    c, _, intent, _ = tx
    monkeypatch.setenv('GIT_DIR', str(tmp_path / 'absent'))
    monkeypatch.setenv('GIT_INDEX_FILE', str(tmp_path / 'unrelated-index'))
    assert c.apply_commit(intent.intent_id).verification is Verification.MATCHED


def test_noop_intent_does_not_create_a_commit(tx):
    c, _, original, repo = tx
    intent = c.propose_commit(original.run_id, path='README.md', content='base\n', message='Noop')
    c.authorize_commit(intent.intent_id)
    with pytest.raises(IntegrityViolation, match='staged paths'):
        c.apply_commit(intent.intent_id)
    assert repo.head_revision() == intent.base_revision_id


@pytest.mark.parametrize('field,value', [('subject', 'other'), ('body_hash', 'sha256:bad'),
    ('parent_revision_ids', ('wrong',)), ('actual_tree_digest', 'sha256:bad'),
    ('tree_id', 'bad'), ('revision_id', 'bad'), ('committed_paths', ('extra',)),
    ('operation_token', 'wrong'), ('intent_id', 'wrong'), ('files_changed', ())])
def test_receipt_tampering_is_detected(tx, field, value):
    c, _, intent, repo = tx
    receipt = c.apply_commit(intent.intent_id)
    observation = repo.observe_commit(receipt.revision_id, intent=intent)
    assert verify_receipt(intent, replace(receipt, **{field: value}), observation) is Verification.DIVERGED


@pytest.mark.parametrize('field,value', [('subject', 'other'), ('body_hash', 'sha256:bad'),
    ('parent_revision_ids', ('wrong',)), ('actual_tree_digest', 'sha256:bad'),
    ('committed_paths', ('extra',)), ('operation_tokens', ('wrong',)),
    ('matching_revisions', ('one', 'two')), ('entries', {})])
def test_observed_revision_is_compared_against_intent(tx, field, value):
    c, _, intent, repo = tx
    receipt = c.apply_commit(intent.intent_id)
    observation = repo.observe_commit(receipt.revision_id, intent=intent)
    observation[field] = value
    assert field in verification_errors(intent, observation)


@pytest.mark.parametrize('field,value', [('message', 'Changed subject'),
    ('message', 'Add feature\n\nDifferent body'), ('expected_tree_digest', 'sha256:bad')])
def test_recovery_checks_full_receipt_and_applies_integrity_suspension(tx, monkeypatch, field, value):
    c, project, intent, repo = tx
    # Exception has the same durable boundary as the SIGKILL test below.
    def crash(*args, **kwargs):
        raise RuntimeError('receipt crash')
    with monkeypatch.context() as patch:
        patch.setattr(c, '_settle_commit_receipt', crash)
        with pytest.raises(RuntimeError):
            c.apply_commit(intent.intent_id)
    landed = repo.head_revision()
    interrupted = c.store.get_commit_intent(intent.intent_id)
    setattr(interrupted, field, value)
    persist(c, project, interrupted)
    c.start(project)
    c.recover(project)
    assert repo.head_revision() == landed
    receipt, = c.store.list_commit_receipts(intent.intent_id)
    assert receipt.verification is Verification.DIVERGED
    assert c.store.get_commit_intent(intent.intent_id).reconciliation_state is ReconciliationState.ADOPTED
    assert c.store.get_project(project).suspension is SuspensionState.SUSPENDED_BY_INTEGRITY


def test_receipt_and_settlement_roll_back_together(tx, monkeypatch):
    c, project, intent, repo = tx
    original = c._transition_intent
    def interrupted(*args, **kwargs):
        if kwargs['event_type'] == 'commit_intent.settled':
            raise RuntimeError('crash after receipt insert')
        return original(*args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(c, '_transition_intent', interrupted)
        with pytest.raises(RuntimeError):
            c.apply_commit(intent.intent_id)
    assert c.store.list_commit_receipts(intent.intent_id) == []
    assert not any(e.event_type == 'commit_receipt.attested' for e in c.store.list_events(project))
    assert c.store.get_commit_intent(intent.intent_id).status is CommitIntentStatus.APPLYING
    landed = repo.head_revision()
    c.start(project)
    c.recover(project)
    c.start(project)
    c.recover(project)
    assert repo.head_revision() == landed
    assert len(c.store.list_commit_receipts(intent.intent_id)) == 1
    c.store.verify_chain(project)
    c.store.audit_reconciliation_closure(project)


def test_same_epoch_apply_is_never_retried(tx):
    c, _, intent, repo = tx
    c.mark_applying(intent.intent_id)
    with pytest.raises(IntegrityViolation, match='reconcile'):
        c.apply_commit(intent.intent_id)
    assert repo.head_revision() == intent.base_revision_id


@pytest.mark.parametrize('operation, refusal', [
    ('authorize', 'only a proposed intent can be authorized'),
    ('mark', 'only an authorized intent may start applying'),
])
def test_illegal_commit_statuses_are_refused(tx, operation, refusal):
    """Each status guard, asserted by its own refusal.

    These raises carried no `match=`, and GR-28 showed what that costs: the
    transition channel also refuses `PROPOSED -> APPLYING` — §7.4 carries no
    such row — with the same `IntegrityViolation`, so deleting
    `guard:commit_mark_status` left this test green and the guard SURVIVED.
    Naming the message is what makes this test the guard's killer rather than
    a test of whichever refusal happens to fire first (`F04-002`).
    """
    c, project, intent, _ = tx
    if operation == 'authorize':
        with pytest.raises(IntegrityViolation, match=refusal):
            c.authorize_commit(intent.intent_id)
    else:
        intent.status = CommitIntentStatus.PROPOSED
        persist(c, project, intent)
        with pytest.raises(IntegrityViolation, match=refusal):
            c.mark_applying(intent.intent_id)


def test_authorization_requires_current_base(tx):
    c, project, intent, repo = tx
    intent.status = CommitIntentStatus.PROPOSED
    persist(c, project, intent)
    git(repo.root, 'checkout', '-b', 'different')
    with pytest.raises(IntegrityViolation):
        c.authorize_commit(intent.intent_id)


def test_apply_base_is_checked_before_worktree_writes(tx):
    c, _, intent, repo = tx
    git(repo.root, 'checkout', '-b', 'different')
    with pytest.raises(IntegrityViolation):
        c.apply_commit(intent.intent_id)
    assert not (repo.root / 'feature.txt').exists()


def test_mark_applying_obeys_reconciliation_barrier(tx):
    c, project, intent, _ = tx
    c.start(project)
    with pytest.raises(BarrierViolation):
        c.mark_applying(intent.intent_id)


@pytest.mark.parametrize('completeness', [Completeness.FAILED, Completeness.PARTIAL, Completeness.TRUNCATED])
def test_mark_applying_obeys_completeness_gate(tx, completeness):
    c, project, intent, _ = tx
    snapshot_id = c.take_snapshot(project)
    c.store.raw_execute('UPDATE snapshots SET completeness=? WHERE snapshot_id=?', (completeness.value, snapshot_id))
    with pytest.raises(PolicyDenied):
        c.mark_applying(intent.intent_id)


def test_missing_receipt_cannot_verify(tx):
    with pytest.raises(IntegrityViolation, match='exactly one receipt'):
        tx[0].verify_commit(tx[2].intent_id)


@pytest.mark.parametrize('message', ['', '\nsubject', 'x\0y', 'x\ry', 'x' * 8193])
def test_invalid_message_rejected_at_proposal(tx, message):
    c, _, intent, _ = tx
    with pytest.raises(IntegrityViolation):
        c.propose_commit(intent.run_id, path='other', content='x', message=message)
    assert len(c.store.list_commit_intents(intent.run_id)) == 1


@pytest.mark.parametrize('trailers', [{}, {'Operation-Token': 'wrong'}, {'x\nY': 'bad'}, {'x': 'bad\nY: z'}])
def test_invalid_token_or_trailers_are_refused(tx, trailers):
    with pytest.raises(IntegrityViolation):
        commit_message(replace(tx[2], trailers=trailers))


@pytest.mark.parametrize('kind', ['scope', 'empty', 'duplicate', 'source', 'destination'])
def test_exact_intent_paths_are_guarded(tx, kind):
    intent = tx[2]
    mutation = intent.mutations[0]
    mutations = {
        'scope': (replace(mutation, in_scope=False),), 'empty': (),
        'duplicate': (mutation, mutation),
        'source': (replace(mutation, path='.git/config'),),
        'destination': (replace(mutation, op=MutationOp.RENAME, rename_to='.git/config'),),
    }[kind]
    with pytest.raises((IntegrityViolation, ProtectedPathViolation)):
        exact_paths(replace(intent, mutations=mutations))


@pytest.mark.parametrize('bad', ['preimage', 'missing_after', 'bad_rename', 'bad_mode'])
def test_invalid_mutations_are_refused_before_any_write(tx, bad):
    c, project, intent, repo = tx
    mutation = intent.mutations[0]
    bad_mutation = {
        'preimage': replace(mutation, before_digest='sha256:wrong'),
        'missing_after': replace(mutation, after_ref=None),
        'bad_rename': replace(mutation, rename_to='extra'),
        'bad_mode': replace(mutation, op=MutationOp.CHMOD, path='README.md',
                            before_digest=digest_bytes(b'base\n'), mode=0o777),
    }[bad]
    persist(c, project, replace(intent, mutations=(bad_mutation,)))
    with pytest.raises(IntegrityViolation):
        c.apply_commit(intent.intent_id)
    assert not (repo.root / 'feature.txt').exists()


def test_writing_through_symlink_is_refused(tx, tmp_path):
    repo = tx[3]
    victim = tmp_path / 'victim'
    victim.write_text('safe')
    (repo.root / 'link').symlink_to(victim)
    with pytest.raises(PolicyDenied):
        repo.write_file('link', 'unsafe')
    assert victim.read_text() == 'safe'


def test_delete_cannot_traverse_symlink_to_outside(tx, tmp_path):
    c, _, intent, repo = tx
    victim = tmp_path / 'victim'
    victim.write_text('safe')
    (repo.root / 'link').symlink_to(tmp_path, target_is_directory=True)
    bad = replace(intent, mutations=(MutationProposal(op=MutationOp.DELETE,
                    path='link/victim', before_digest=digest_bytes(b'safe'), in_scope=True),))
    # Valid base preimage supplied independently; the filesystem boundary must
    # still refuse before unlink, rather than relying on a later stage check.
    with pytest.raises(PolicyDenied):
        repo.apply_mutations(bad, c.store.artifact_bytes)
    assert victim.read_text() == 'safe'


@pytest.mark.parametrize('op', [MutationOp.MODIFY, MutationOp.DELETE, MutationOp.RENAME, MutationOp.CHMOD])
def test_all_mutation_operations_use_exact_paths(tx, op):
    c, project, intent, repo = tx
    before = repo.file_index()
    mutation = MutationProposal(op=op, path='README.md', before_digest=before['README.md'],
        after_ref=c.store.store_artifact(b'updated\n', media_type='application/octet-stream') if op is MutationOp.MODIFY else None,
        rename_to='renamed.md' if op is MutationOp.RENAME else None,
        mode=0o755 if op is MutationOp.CHMOD else None, in_scope=True)
    intent = replace(intent, mutations=(mutation,), expected_tree_digest=expected_tree_digest(before, (mutation,)))
    persist(c, project, intent)
    receipt = c.apply_commit(intent.intent_id)
    assert receipt.verification is Verification.MATCHED
    assert receipt.committed_paths == (('README.md', 'renamed.md') if op is MutationOp.RENAME else ('README.md',))
    assert c.verify_commit(intent.intent_id) is Verification.MATCHED


def test_repeated_settlement_of_stale_intent_returns_existing_receipt(tx):
    c, project, intent, repo = tx
    first = c.apply_commit(intent.intent_id)
    second = c._settle_commit_receipt(intent, project,
        revision_id=first.revision_id, parent_revision_ids=first.parent_revision_ids,
        actual_tree_digest=first.actual_tree_digest, diff=repo.diff(first.revision_id),
        attribution=first.attribution)
    assert second == first
    assert len(c.store.list_commit_receipts(intent.intent_id)) == 1


def test_ambiguous_token_suspends_run_and_project(tx):
    c, project, intent, repo = tx
    c.mark_applying(intent.intent_id)
    git(repo.root, 'commit', '--allow-empty', '-m', 'external')
    c.start(project)
    c.recover(project)
    assert c.store.get_commit_intent(intent.intent_id).reconciliation_state is ReconciliationState.UNRESOLVABLE
    assert c.store.get_run(intent.run_id).suspension is SuspensionState.SUSPENDED_BY_INTEGRITY
    assert c.store.get_project(project).suspension is SuspensionState.SUSPENDED_BY_INTEGRITY


def test_sigkill_during_receipt_transaction_and_during_adoption_adopts_once(h):
    project = project_with_repo(h, slug='receipt-crash')
    with h.controller(with_repo=True) as c:
        run = c.open_run(project)
    proc = h.spawn(project, 'commit', '--run', run, '--path', 'feature.txt',
                   '--content', 'landed', gate='after_commit_receipt_insert')
    h.wait_for_gate('after_commit_receipt_insert', proc)
    h.kill9(proc)
    with h.store() as store:
        intent, = store.list_commit_intents(run)
        assert intent.status is CommitIntentStatus.APPLYING
        assert store.list_commit_receipts(intent.intent_id) == []
        store.verify_chain(project)
    assert h.revision_count() == 2
    # Kill adoption inside its receipt transaction too. Remove readiness from
    # the previous process so this wait proves the second process got there.
    (h.gate_dir / 'after_commit_receipt_insert.ready').unlink()
    proc = h.spawn(project, 'recover', gate='after_commit_receipt_insert')
    h.wait_for_gate('after_commit_receipt_insert', proc)
    h.kill9(proc)
    h.run(project, 'recover')
    h.run(project, 'recover')
    assert h.revision_count() == 2
    with h.store() as store:
        receipt, = store.list_commit_receipts(intent.intent_id)
        assert receipt.verification is Verification.MATCHED
        assert receipt.committed_paths == ('feature.txt',)
        store.verify_chain(project)
        store.audit_reconciliation_closure(project)


def test_reverification_divergence_suspends_run_and_project(tx):
    c, project, intent, _ = tx
    receipt = c.apply_commit(intent.intent_id)
    c.store.raw_execute('UPDATE commit_receipts SET subject=? WHERE receipt_id=?',
                        ('tampered', receipt.receipt_id))
    assert c.verify_commit(intent.intent_id) is Verification.DIVERGED
    assert c.store.get_run(intent.run_id).suspension is SuspensionState.SUSPENDED_BY_INTEGRITY
    assert c.store.get_project(project).suspension is SuspensionState.SUSPENDED_BY_INTEGRITY


def test_nonexistent_literal_path_cannot_expand_to_untracked_files(tx):
    repo = tx[3]
    (repo.root / 'accidental.txt').write_text('must stay untracked')
    with pytest.raises(subprocess.CalledProcessError):
        repo.stage(['*.txt'])
    assert git(repo.root, 'diff', '--cached', '--name-only') == ''


def test_pending_merge_cannot_add_an_unexpected_parent(tx):
    c, _, intent, repo = tx
    git(repo.root, 'checkout', '-b', 'side')
    git(repo.root, 'commit', '--allow-empty', '-m', 'side')
    git(repo.root, 'checkout', intent.target_ref)
    git(repo.root, 'merge', '--no-ff', '--no-commit', 'side')
    assert repo.head_revision() == intent.base_revision_id
    with pytest.raises(IntegrityViolation, match='pending merge'):
        c.apply_commit(intent.intent_id)
    assert repo.head_revision() == intent.base_revision_id
    assert repo.find_by_token(intent.operation_token) == []


def test_signing_configuration_cannot_execute_an_external_program(tx, tmp_path):
    c, _, intent, repo = tx
    signer = tmp_path / 'signer'
    signer.write_text('#!/bin/sh\necho ran > signer-ran\nexit 99\n')
    signer.chmod(0o755)
    git(repo.root, 'config', 'commit.gpgsign', 'true')
    git(repo.root, 'config', 'gpg.program', str(signer))
    assert c.apply_commit(intent.intent_id).verification is Verification.MATCHED
    assert not (repo.root / 'signer-ran').exists()


def test_commit_message_bytes_are_not_rewritten_by_git_cleanup(tx):
    c, project, original, repo = tx
    message = 'Subject  \n\nBody with trailing spaces  \n'
    intent = c.propose_commit(original.run_id, path='whitespace', content='x', message=message)
    c.authorize_commit(intent.intent_id)
    receipt = c.apply_commit(intent.intent_id)
    raw = repo._git('cat-file', 'commit', receipt.revision_id, text=False).partition(b'\n\n')[2]
    assert raw == commit_message(intent)
    assert receipt.verification is Verification.MATCHED
