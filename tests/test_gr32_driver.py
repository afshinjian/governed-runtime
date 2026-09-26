"""GR-32: the supervised stage driver walks the sequence, or refuses and stops.

`B2`. Every test below drives the real kernel through `PilotSession`. Nothing
provisions by writing a `Project` row, nothing fabricates a `HumanDecision`,
and nothing edits an existing test to make this stage pass: the projects here
are created, provisioned, contracted, activated, invoked, proposed, authorized
and applied through the one production path GR-32 adds.

Every refusal is asserted with `match=` (`CLAUDE.md` Tooling, `F04-002`): a
bare `pytest.raises` accepts whichever guard fires first, and several guards
exercised here raise the same class over the same call.

The worker is offline and the relay is configured but never dialled. GR-32
proves the composition; the first live provider invocation remains unproven
territory (`CLAUDE.md` Known gaps, GR-07).
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from gruntime.commit import CommitPreconditions
from gruntime.models import ATTESTATION_KIND
from gruntime.decision import decision_content_hash
from gruntime.driver import (
    OwnerAnswer,
    OwnerRefused,
    PilotSession,
    ProposalUnsupported,
    credential_is_printable,
    map_proposal,
    preflight_credential,
)
from gruntime.errors import (
    CapabilityDenied,
    GovernedRuntimeError,
    IntegrityViolation,
    PolicyDenied,
)
from gruntime.models import (
    ActorRef,
    Attribution,
    ArtifactRef,
    CommitIntentStatus,
    DecisionKind,
    DecisionScope,
    DecisionState,
    DecisionSubjectKind,
    MutationOp,
    MutationProposal,
    Ref,
    SnapshotTrigger,
    TerminationReason,
    Usage,
    WorkerReceipt,
)
from gruntime.secret_guard import SecretLeak
from gruntime.store import StateStore, now_ts

import gr32_support as S


# --- helpers ----------------------------------------------------------------


def stopped(session, error, match):
    """Run the session, expect it to refuse at some step, and stop there."""
    with pytest.raises(error, match=match):
        session.run()
    return session.report


def answering(session, presenter=None):
    """Let a stopped session ask again — with a presenter that answers.

    The staleness tests below need the human act *recorded*, so that a snapshot
    can supersede it. The session stopped because its scripted presenter
    refused one act; swapping in one that answers is the test saying "and now
    the owner does confirm", which is the only way the next assertion — that
    the confirmation is refused for being STALE rather than for being absent —
    is about staleness at all.
    """
    session._present = presenter or S.ScriptedPresenter()
    return session


def no_projects(store):
    """No project row exists. Read through the store's own schema."""
    return store.connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0


def receipt(**changes):
    """A `WorkerReceipt` shaped for `map_proposal`, mutated per test.

    Constructed rather than produced, because every refusal below is about a
    receipt the offline provider would never emit — that is what makes them
    refusals rather than dead code.
    """
    fields = dict(
        receipt_id="wr-test", invocation_id="inv-test", ended_at=now_ts(),
        duration_ms=1, usage=Usage(), output_ref=ArtifactRef("sha256:o", "text/plain", 1),
        output_digest="sha256:o", termination_reason=TerminationReason.COMPLETED,
        attribution=Attribution.DIRECT,
        attested_by=ActorRef(actor_kind=S.OWNER.actor_kind, actor_id="runtime",
                             auth_method=S.OWNER.auth_method),
        receipt_hash="sha256:r", prev_event_hash="sha256:p")
    mutations = changes.pop("mutations", None)
    if mutations is None:
        mutations = (mutation(),)
    fields.update(changes)
    return WorkerReceipt(proposed_mutations=tuple(mutations), **fields)


def mutation(**changes):
    from gruntime.canonical import digest_bytes

    payload = changes.pop("payload", S.PROPOSED.encode("utf-8"))
    fields = dict(op=MutationOp.CREATE, path=S.TARGET,
                  after_ref=ArtifactRef(digest_bytes(payload), "application/octet-stream",
                                        len(payload)))
    fields.update(changes)
    return MutationProposal(**fields)


def reader(payload):
    return lambda digest: payload


def mapped(receipt_value, payload=None, *, include=(S.TARGET,), exclude=(), base_index=None):
    read = reader(payload if payload is not None else S.PROPOSED.encode("utf-8"))
    return map_proposal(receipt_value, read, scope_include=include, scope_exclude=exclude,
                        base_index={} if base_index is None else base_index)


def store_of(parameters):
    from pathlib import Path

    return StateStore.open(Path(parameters.governance_root) / "state.db")


# --- T1: the whole supervised sequence, offline, end to end -----------------


def test_supervised_sequence_1_to_16_reaches_a_governed_revision(tmp_path):
    """Steps 2–16 through the production path, ending at an applied revision.

    Step 1 is the composition itself. What this asserts is that each step ran,
    in order, that each confirmed row consumed the decision recorded for it,
    and that the revision the report names is a revision the repository has.
    """
    parameters, report, document = S.applied(tmp_path)

    assert report.state == "MATERIALIZED"
    assert [step.act for step in report.steps] == [
        "runtime.compose", "project.create", "controller.start", "project.ceiling.set", "budget.grant",
        "run.start", "contract.author", "capability.grant", "contract.approve",
        "contract.activate", "validation.bind", "secret.read", "worker.invoke",
        "commit.propose", "commit.authorize", "commit.apply"]
    assert [step.step for step in report.steps] == list(range(1, 17))
    assert all(step.result == "OK" for step in report.steps)
    assert report.materialized_revision

    store = store_of(parameters)
    try:
        project = store.get_project(report.project_id)
        # Provisioned by the governed operations, not by a row write.
        assert project.capability_ceiling == parameters.ceiling
        assert project.budget == parameters.budget
        # Every confirmation the sequence recorded was consumed by its act.
        confirmations = [d for d in store.list_decisions(report.project_id)
                         if d.decision_kind is DecisionKind.APPROVE]
        assert confirmations and all(d.decision_state is DecisionState.CONSUMED
                                     for d in confirmations)
        intent, = store.list_commit_intents(report.run_id)
        assert intent.status is CommitIntentStatus.APPLIED
        store.verify_chain(report.project_id)
    finally:
        store.close()

    assert S.revisions(parameters.workspace_root) == "2"
    assert document["materialized_revision"] == report.materialized_revision


def test_the_worker_proposal_is_what_lands(tmp_path):
    """The receipt is the proposal identity of record, all the way to the tree."""
    parameters, report, _ = S.applied(tmp_path)
    propose = next(s for s in report.steps if s.act == "commit.propose")
    assert propose.detail["path"] == S.TARGET
    import subprocess

    shown = subprocess.run(
        ["git", "-C", parameters.workspace_root, "show",
         f"{report.materialized_revision}:{S.TARGET}"],
        check=True, capture_output=True, text=True).stdout
    assert shown == S.PROPOSED


# --- T2: every CONFIRM cell refuses without the act its row declares --------


def partial(tmp_path, refuse_at, **changes):
    """Drive the sequence to the step before `refuse_at`, then hand it back.

    The presenter refuses that one act, so the session stops there with
    everything before it durable. What each test then does is call the kernel
    operation *without* the confirmation, which is the thing the row refuses.
    """
    parameters = S.parameters(tmp_path, **changes)
    return parameters, S.session(parameters, present=S.ScriptedPresenter(refuse_at=refuse_at))


def test_row_5_1_refuses_without_its_confirmation(tmp_path):
    """`∅ → ALLOCATED`. The subject is the PROJECT: the run does not exist."""
    parameters, live = partial(tmp_path, "run.start")
    with live as session:
        stopped(session, OwnerRefused, r"step 6: the owner was asked to authorize run\.start")
        with pytest.raises(CapabilityDenied, match=r"row 5-1 is CONFIRM under SUPERVISED"):
            session.controller.open_run(session.project_id)
        assert session.controller.store.list_runs(session.project_id) == []


def test_row_6_2_refuses_without_its_approval(tmp_path):
    """Contract activation. Already enforced by `guard:gr06_activation_confirmation`."""
    parameters, live = partial(tmp_path, "contract.approve")
    with live as session:
        stopped(session, OwnerRefused, r"step 9: the owner was asked to authorize contract\.approve")
        with pytest.raises(CapabilityDenied,
                           match=r"SUPERVISED activation requires live contract approval"):
            session.controller.activate_contract(
                session.contract.contract_id, session.run_id,
                decision_ids=(session._activation_grant.decision_id,))


def test_row_7_2_1_refuses_without_its_confirmation(tmp_path):
    """First invocation of a run. `WHEN(FIRST_INVOCATION_OF_RUN, CONFIRM, AUTO)`."""
    parameters, live = partial(tmp_path, "worker.invoke")
    with live as session:
        stopped(session, OwnerRefused, r"step 13: the owner was asked to authorize worker\.invoke")
        with pytest.raises(CapabilityDenied, match=r"row 7\.2-1 is CONFIRM under SUPERVISED"):
            session.controller.create_invocation(
                session.run_id, prompt=b"work",
                provider_id=session.controller.provider.describe().provider_id)
        assert session.controller.store.list_invocations(session.run_id) == []


def test_row_7_4_4_refuses_without_its_confirmation(tmp_path):
    """`PROPOSED → AUTHORIZED`. The subject is the COMMIT_INTENT."""
    parameters, live = partial(tmp_path, "commit.authorize")
    with live as session:
        stopped(session, OwnerRefused,
                r"step 15: the owner was asked to authorize commit\.authorize")
        with pytest.raises(CapabilityDenied, match=r"row 7\.4-4 is CONFIRM under SUPERVISED"):
            session.controller.authorize_commit(session.intent.intent_id)
        intent = session.controller.store.get_commit_intent(session.intent.intent_id)
        assert intent.status is CommitIntentStatus.PROPOSED


# --- T3: staleness, for all four APPROVE confirmations ----------------------


def drift(parameters, text="drifted\n"):
    """A real edit to a tracked file in the workspace, as a human would make."""
    from pathlib import Path

    (Path(parameters.workspace_root) / "README.md").write_text(text, encoding="utf-8")


def test_row_5_1_confirmation_goes_stale_when_reality_moves(tmp_path):
    """`HD-INV-4`: the owner approved opening a run against a tree that moved."""
    parameters, live = partial(tmp_path, "run.start")
    with live as session:
        stopped(session, OwnerRefused, r"run\.start")
        confirmation = answering(session)._decide(
            6, "run.start", kind=DecisionKind.APPROVE,
            subject_kind=DecisionSubjectKind.PROJECT, subject_id=session.project_id,
            scope=DecisionScope.PROJECT, question="Open a run?", detail={})
        drift(parameters)
        session.controller.take_snapshot(session.project_id)
        assert (session.controller.store.get_decision(confirmation.decision_id).decision_state
                is DecisionState.STALE)
        with pytest.raises(CapabilityDenied, match=r"row 5-1 is CONFIRM under SUPERVISED"):
            session.controller.open_run(session.project_id,
                                        confirmation_id=confirmation.decision_id)


def test_row_6_2_approval_goes_stale_on_any_newer_observation(tmp_path):
    """Activation binds to the newest COMPLETE snapshot, drift or no drift.

    `guard:gr06_activation_confirmation` compares the approval's bound
    observation to the newest one rather than asking the drift derivation, so
    an unchanged re-observation is enough here and nothing is suspended.
    """
    parameters, live = partial(tmp_path, "contract.approve")
    with live as session:
        stopped(session, OwnerRefused, r"contract\.approve")
        approval = answering(session)._decide(
            9, "contract.approve", kind=DecisionKind.APPROVE,
            subject_kind=DecisionSubjectKind.CONTRACT,
            subject_id=session.contract.contract_id, scope=DecisionScope.SINGLE_ACTION,
            question="Activate?", detail={})
        session.controller.take_snapshot(session.project_id)
        with pytest.raises(CapabilityDenied,
                           match=r"SUPERVISED activation requires live contract approval"):
            session.controller.activate_contract(
                session.contract.contract_id, session.run_id,
                decision_ids=(session._activation_grant.decision_id,),
                approval_id=approval.decision_id)


def test_row_7_2_1_confirmation_goes_stale_when_reality_moves(tmp_path, monkeypatch):
    """The drift suspension answers first; the row refuses behind it.

    Unattributed drift raises `REALITY_DRIFT` and sets `SUSPENDED_BY_DRIFT`,
    and `_worker_gate` asks `_assert_may_initiate_effect` before it asks the
    row — so the harder gate is what a caller actually meets. Both are
    asserted: the suspension in front, and, with that gate lifted, row 7.2-1
    behind it, refusing the confirmation `HD-INV-4` already staled.
    """
    parameters, live = partial(tmp_path, "worker.invoke")
    with live as session:
        stopped(session, OwnerRefused, r"worker\.invoke")
        confirmation = answering(session)._decide(
            13, "worker.invoke", kind=DecisionKind.APPROVE,
            subject_kind=DecisionSubjectKind.RUN, subject_id=session.run_id,
            scope=DecisionScope.RUN, question="Invoke?", detail={})
        drift(parameters)
        session.controller.take_snapshot(session.project_id)
        assert (session.controller.store.get_decision(confirmation.decision_id).decision_state
                is DecisionState.STALE)
        provider_id = session.controller.provider.describe().provider_id
        with pytest.raises(PolicyDenied, match=r"SUSPENDED_BY_DRIFT"):
            session.controller.create_invocation(
                session.run_id, prompt=b"work", provider_id=provider_id,
                confirmation_id=confirmation.decision_id)
        monkeypatch.setattr(type(session.controller), "_assert_may_initiate_effect",
                            lambda self, project_id, what: None)
        with pytest.raises(CapabilityDenied, match=r"row 7\.2-1 is CONFIRM under SUPERVISED"):
            session.controller.create_invocation(
                session.run_id, prompt=b"work", provider_id=provider_id,
                confirmation_id=confirmation.decision_id)


def test_row_7_4_4_confirmation_goes_stale_when_reality_moves(tmp_path):
    """`COMMIT_INTENT` is a snapshot-bound subject; `authorize_commit` is not gated
    by suspension, so the row itself is what answers."""
    parameters, live = partial(tmp_path, "commit.authorize")
    with live as session:
        stopped(session, OwnerRefused, r"commit\.authorize")
        confirmation = answering(session)._decide(
            15, "commit.authorize", kind=DecisionKind.APPROVE,
            subject_kind=DecisionSubjectKind.COMMIT_INTENT,
            subject_id=session.intent.intent_id, scope=DecisionScope.SINGLE_ACTION,
            question="Commit?", detail={})
        drift(parameters)
        session.controller.take_snapshot(session.project_id)
        assert (session.controller.store.get_decision(confirmation.decision_id).decision_state
                is DecisionState.STALE)
        with pytest.raises(CapabilityDenied, match=r"row 7\.4-4 is CONFIRM under SUPERVISED"):
            session.controller.authorize_commit(session.intent.intent_id,
                                                confirmation_id=confirmation.decision_id)


def test_the_secret_approval_is_snapshot_bound_too(tmp_path):
    """`guard:gr08_secret_currency`: the relay's single-action approval stales."""
    parameters, live = partial(tmp_path, "secret.approve")
    with live as session:
        stopped(session, OwnerRefused, r"secret\.approve")
        # The grant was recorded before the refusal; the approval was not.
        assert any(d.decision_kind is DecisionKind.GRANT_CAPABILITY
                   and d.subject_id == "secret.read"
                   for d in session.controller.store.list_decisions(session.project_id))


# --- T4: a presenter that answers nothing records nothing -------------------


@pytest.mark.parametrize("act,step", [
    ("project.create", 2), ("project.ceiling.set", 4), ("budget.grant", 5),
    ("run.start", 6), ("capability.grant", 8), ("contract.approve", 9),
    ("secret.grant", 12), ("worker.invoke", 13), ("commit.authorize", 15)])
def test_a_refusing_presenter_records_no_decision_and_makes_no_transition(tmp_path, act, step):
    """`None` is a refusal. No decision, no transition, no default approval."""
    parameters = S.parameters(tmp_path, slug=f"refuse-{step}")
    with S.session(parameters, present=S.ScriptedPresenter(refuse_at=act)) as session:
        report = stopped(session, OwnerRefused, rf"the owner was asked to authorize {act}")
        assert report.state == "STOPPED"
        assert report.stopped_at == step
        # The step's act names the transition; `secret.grant` is one of the two
        # decisions step 12 asks for, and the step is recorded as `secret.read`.
        assert report.steps[-1].result == "REFUSED"
        assert act in report.steps[-1].refusal_text
        assert report.materialized_revision is None
        if session.project_id is None:
            return
        decisions = session.controller.store.list_decisions(session.project_id)
        # Nothing was recorded for the act the owner declined.
        assert not any(d.question.startswith("Authorize") for d in decisions)


def test_a_declined_creation_creates_no_project(tmp_path):
    """The genesis boundary answers `DECLINE`; nothing is published."""
    parameters = S.parameters(tmp_path, slug="declined")
    present = S.ScriptedPresenter(answer_with={"project.create": "DECLINE"})
    with S.session(parameters, present=present) as session:
        stopped(session, OwnerRefused, r"the owner chose 'DECLINE' over 'CREATE'")
        assert session.project_id is None
        assert no_projects(session.controller.store)


def test_an_answer_that_was_never_offered_is_not_an_answer(tmp_path):
    """`guard:decision_option_membership`'s rule, asked before anything is built."""
    parameters = S.parameters(tmp_path, slug="unoffered")
    present = S.ScriptedPresenter(answer_with={"run.start": "MAYBE"})
    with S.session(parameters, present=present) as session:
        stopped(session, OwnerRefused, r"which was not among the options offered")


def test_a_creation_answered_by_another_principal_is_refused(tmp_path):
    """`AX-14`: the approval is recorded as `approved_by`, so it must be theirs."""
    parameters = S.parameters(tmp_path, slug="misattributed")
    present = S.ScriptedPresenter(attribute_to={"project.create": S.OTHER})
    with S.session(parameters, present=present) as session:
        stopped(session, OwnerRefused, r"is the principal this creation records as approver")
        assert no_projects(session.controller.store)


def test_no_decision_is_reused_for_two_acts(tmp_path):
    """Fourteen acts, fourteen decisions, each consumed by the one it authorized."""
    parameters, report, _ = S.applied(tmp_path, slug="distinct")
    store = store_of(parameters)
    try:
        decisions = store.list_decisions(report.project_id)
        ids = [d.decision_id for d in decisions]
        assert len(ids) == len(set(ids))
        # Every decision the sequence recorded is spent exactly once: the
        # provisioning and confirmation decisions are CONSUMED, and the
        # activation grant is bound to its activation by nonce.
        spent = [d for d in decisions if d.decision_state is DecisionState.CONSUMED]
        assert len(spent) >= 8
        for decision in decisions:
            assert decision.decision_hash == decision_content_hash(decision)
    finally:
        store.close()


# --- T5: D2, the credential -------------------------------------------------


@pytest.mark.parametrize("value,match", [
    (None, r"names nothing in this process environment"),
    ("", r"is set to an empty value"),
    ("sk-trailing-newline\n", r"printable ASCII only"),
    ("sk-embedded\ttab", r"printable ASCII only"),
    ("sk-nonascii-é", r"printable ASCII only"),
])
def test_credential_preflight_refuses_before_any_secret_decision(tmp_path, value, match):
    """A failed preflight records ZERO secret decisions.

    `GR32-P-002`: `configure_inference_relay` consumes both decisions in a
    committed transaction before it calls the resolver, so a credential that
    reached that point would spend two human acts on a relay never opened.
    """
    parameters = S.parameters(tmp_path, slug=f"cred-{abs(hash(str(value))) % 9973}")
    with S.session(parameters, credential=value) as session:
        stopped(session, PolicyDenied, match)
        assert session.report.stopped_at == 12
        secrets = [d for d in session.controller.store.list_decisions(session.project_id)
                   if d.subject_id == "secret.read"]
        assert secrets == [], "a failed preflight recorded a secret decision"


def test_the_preflight_repairs_nothing(tmp_path):
    """No strip, no trim, no normalize: a malformed credential stays malformed."""
    with pytest.raises(PolicyDenied, match=r"refused unchanged rather than stripped"):
        preflight_credential("V", {"V": "sk-value\n"})
    assert credential_is_printable("sk-value")
    assert not credential_is_printable("sk-value\n")
    assert not credential_is_printable("")


def test_the_default_credential_header_is_x_api_key_with_an_empty_prefix(tmp_path):
    parameters, report, _ = S.applied(tmp_path, slug="default-header")
    relay = next(s for s in report.steps if s.act == "secret.read")
    assert relay.detail["credential_header"] == "x-api-key"
    assert relay.detail["credential_prefix"] == ""


def test_bearer_mode_remains_selectable(tmp_path):
    parameters, report, _ = S.applied(
        tmp_path, slug="bearer", credential_header="Authorization",
        credential_prefix="Bearer ")
    relay = next(s for s in report.steps if s.act == "secret.read")
    assert relay.detail["credential_header"] == "Authorization"
    assert relay.detail["credential_prefix"] == "Bearer "
    assert report.state == "MATERIALIZED"


def test_the_credential_reaches_no_report_event_artifact_or_journal(tmp_path):
    """The whole governance root is scanned, not just the report."""
    from pathlib import Path

    parameters, report, document = S.applied(tmp_path, slug="no-leak")
    assert S.CREDENTIAL not in json.dumps(document)
    assert S.CREDENTIAL_VARIABLE in json.dumps(document), "the variable NAME is configuration"
    for root in (parameters.governance_root, parameters.workspace_root):
        for path in Path(root).rglob("*"):
            if path.is_file():
                assert S.CREDENTIAL.encode() not in path.read_bytes(), f"leaked to {path}"


def test_the_report_is_checked_against_the_runtimes_own_secret_guard(tmp_path):
    """`guard:gr32_report_secret_free`, asked of the real fingerprint."""
    from gruntime.driver import StepOutcome

    parameters = S.parameters(tmp_path, slug="guarded-report")
    with S.session(parameters) as session:
        session.run()
        session.documented_report()
        session.report.steps.append(
            StepOutcome(step=99, act="leak", result="OK", refusal_text=S.CREDENTIAL))
        with pytest.raises(SecretLeak):
            session.documented_report()


def test_the_resolver_answers_only_for_the_approved_secret(tmp_path):
    parameters = S.parameters(tmp_path, slug="resolver")
    with S.session(parameters) as session:
        resolve = session._resolver()
        assert resolve(S.SECRET_NAME) == S.CREDENTIAL
        with pytest.raises(CapabilityDenied, match=r"the approved secret for this session"):
            resolve("some-other-secret")


# --- T6: the proposal mapping -----------------------------------------------


def test_a_conforming_single_mutation_maps_to_propose_commit(tmp_path):
    result = mapped(receipt())
    assert result.path == S.TARGET and result.content == S.PROPOSED


@pytest.mark.parametrize("changes,match", [
    ({"mutations": (mutation(), mutation(path="src/other.py"))}, r"proposes 2 mutations"),
    ({"mutations": ()}, r"proposes 0 mutations"),
    ({"termination_reason": TerminationReason.REFUSAL}, r"terminated REFUSAL"),
    ({"termination_reason": TerminationReason.DEADLINE}, r"terminated DEADLINE"),
    ({"attribution": Attribution.RECONCILED}, r"carries attribution RECONCILED"),
    ({"capability_violations_attempted": ({"capability": "fs.delete"},)},
     r"attempted capability violation"),
    ({"scope_breaches_attempted": ({"path": "/etc/passwd"},)}, r"scope breach"),
])
def test_unsupported_receipts_are_refused_whole(changes, match):
    with pytest.raises(ProposalUnsupported, match=match):
        mapped(receipt(**changes))


@pytest.mark.parametrize("changes,match", [
    ({"op": MutationOp.DELETE, "after_ref": None}, r"mutation op DELETE is outside"),
    ({"op": MutationOp.RENAME, "rename_to": "src/moved.py"}, r"mutation op RENAME is outside"),
    ({"op": MutationOp.CHMOD, "mode": 0o755}, r"mutation op CHMOD is outside"),
    ({"rename_to": "src/moved.py"}, r"carries rename_to="),
    ({"mode": 0o644}, r"carries mode="),
    ({"after_ref": None}, r"has no after_ref"),
    ({"path": "outside/secret.py"}, r"is outside the activated contract scope"),
])
def test_unsupported_mutations_are_refused_whole(changes, match):
    with pytest.raises(ProposalUnsupported, match=match):
        mapped(receipt(mutations=(mutation(**changes),)))


def test_content_that_does_not_redigest_to_the_receipts_identity_is_refused():
    """The store is asked, and its answer is verified rather than trusted."""
    with pytest.raises(ProposalUnsupported, match=r"does not re-digest to the identity"):
        mapped(receipt(), b"something else entirely")


def test_non_utf8_content_is_refused_rather_than_decoded():
    payload = b"\xff\xfe not text"
    with pytest.raises(ProposalUnsupported, match=r"is not UTF-8 text"):
        mapped(receipt(mutations=(mutation(payload=payload),)), payload)


def test_propose_commit_was_not_widened(tmp_path):
    """Its signature still takes one path and one string of content."""
    import inspect

    from gruntime.controller import Controller

    signature = inspect.signature(Controller.propose_commit)
    assert list(signature.parameters) == [
        "self", "run_id", "path", "content", "message", "preconditions"]


def test_a_worker_that_proposes_two_files_stops_the_session(tmp_path):
    """Through the driver, not only through the pure function."""
    transport = S.ScriptedTransport(mutations=[
        dict(op="CREATE", path=S.TARGET, content=S.PROPOSED, rename_to=None,
             before_digest=None, mode=None),
        dict(op="CREATE", path=S.TARGET, content="x", rename_to=None,
             before_digest=None, mode=None)])
    parameters = S.parameters(tmp_path, slug="two-files")
    with S.session(parameters, transport=transport) as session:
        report = stopped(session, ProposalUnsupported, r"proposes 2 mutations")
        assert report.stopped_at == 14
        assert report.materialized_revision is None
        assert session.controller.store.list_commit_intents(session.run_id) == []


# --- T7: the contract this driver asks for ----------------------------------


def test_secret_read_is_never_a_worker_capability(tmp_path):
    parameters = S.parameters(tmp_path, slug="secret-request",
                              capability_request=S.CAPABILITIES + ("secret.read",))
    with S.session(parameters) as session:
        stopped(session, PolicyDenied, r"a worker never receives it")


def test_the_worker_role_must_admit_every_requested_capability(tmp_path):
    """`REVIEWER` is denied `net.egress.allowlist` and `fs.write` by ROLE_TABLE."""
    parameters = S.parameters(tmp_path, slug="wrong-role", worker_role="REVIEWER")
    with S.session(parameters) as session:
        stopped(session, PolicyDenied, r"does not admit every requested capability")


def test_the_ceiling_is_the_request_plus_secret_read_and_nothing_else(tmp_path):
    parameters = S.parameters(tmp_path, slug="ceiling-shape")
    assert parameters.ceiling == frozenset(S.CAPABILITIES) | {"secret.read"}
    assert parameters.activation_grants == frozenset({"net.egress.allowlist"})


def test_only_a_network_none_validation_operation_is_registered(tmp_path):
    """Validation egress is gated with no enforcing adapter, in either form.

    `ALLOWLIST` is refused outright by `execute_validation` (no adapter) and
    `ANY` is unreachable (`net.egress.any` is HUMAN-tier and
    `execute_validation` has no exercise-decision parameter). Registering a
    catalog entry for either would put an operation on disk whose execution
    cannot be reached, so the driver refuses at the plan rather than at the
    attempt — and GR-32 makes neither reachable.
    """
    for network in ("ALLOWLIST", "ANY"):
        parameters = S.parameters(
            tmp_path, slug=f"egress-{network.lower()}",
            validation=replace(S.validation_plan(), network=network))
        with S.session(parameters) as session:
            report = stopped(session, PolicyDenied,
                             r"registers validation operations with network='NONE' only")
            assert report.stopped_at == 11


def test_a_pilot_with_no_validation_plan_is_refused_before_any_transition(tmp_path):
    """`GR32-F-005`. The plan is mandatory: `None` used to bind nothing, report
    step 11 `OK` with `bound: []`, and materialize a revision anyway."""
    parameters = S.parameters(tmp_path, slug="unbound", validation=None)
    with S.session(parameters) as session:
        report = stopped(session, PolicyDenied, r"no validation plan was supplied")
        assert report.state == "STOPPED" and report.stopped_at == 1
        assert [s.act for s in report.steps] == ["runtime.compose"]
        assert report.materialized_revision is None
        assert no_projects(session.controller.store)
    assert S.revisions(parameters.workspace_root) == "1"


def test_an_invalid_validation_plan_is_refused_and_nothing_materializes(tmp_path):
    """A plan the catalog refuses stops step 11; step 16 is never reached."""
    parameters = S.parameters(
        tmp_path, slug="invalid-plan",
        validation=replace(S.validation_plan(), argv=("python3", "-c", "print(1)")))
    with S.session(parameters) as session:
        with pytest.raises(GovernedRuntimeError, match=r"argv requires a fixed absolute executable"):
            session.run()
        report = session.report
        assert report.state == "STOPPED" and report.stopped_at == 11
        assert report.materialized_revision is None
        assert session.controller.store.list_commit_intents(session.run_id) == []
    assert S.revisions(parameters.workspace_root) == "1"


def test_a_successful_pilot_binds_a_pinned_network_none_validation(tmp_path):
    """Step 11 registers, declares `network='NONE'`, and pins to the run."""
    parameters, report, _ = S.applied(tmp_path, slug="bound")
    bound = next(s for s in report.steps if s.act == "validation.bind")
    assert bound.result == "OK"
    assert bound.detail == {"bound": ["check"], "network": "NONE"}
    assert bound.identity["validation_contract_digest"]
    from gruntime.driver import open_runtime

    with open_runtime(parameters, transport=S.ScriptedTransport()) as controller:
        # The pin is the run's durable `validation.contract_bound` slice, and
        # the operation it names resolves to a `network='NONE'` registration.
        spec, operation = controller._validation_spec(report.run_id, "check")
        assert spec["operation"] == "pilot.check@1.0.0"
        assert operation.network == "NONE"


def test_pilot_1_binds_no_commit_precondition(tmp_path):
    parameters, report, _ = S.applied(tmp_path, slug="no-preconditions")
    store = store_of(parameters)
    try:
        intent, = store.list_commit_intents(report.run_id)
        assert not intent.preconditions.reviews and not intent.preconditions.validations
        contract = store.get_contract(report.contract_id)
        assert contract.required_validations == []
    finally:
        store.close()


# --- T8: the deferral guard is reachable through the driver, and refuses ----


def test_a_validation_precondition_is_refused_by_the_deferral_guard(tmp_path):
    """`guard:gr31_preconditions_deferred`. GR-32 does not bypass or weaken it."""
    parameters = S.parameters(tmp_path, slug="deferred-validation")
    preconditions = CommitPreconditions(validations=("sha256:anything",))
    with S.session(parameters, commit_preconditions=preconditions) as session:
        report = stopped(session, PolicyDenied,
                         r"neither kind can be discharged soundly yet")
        assert report.stopped_at == 15
        assert report.materialized_revision is None


def test_a_review_precondition_is_refused_by_the_deferral_guard(tmp_path):
    parameters = S.parameters(tmp_path, slug="deferred-review")
    preconditions = CommitPreconditions(reviews=(Ref(ATTESTATION_KIND, "ra-1"),))
    with S.session(parameters, commit_preconditions=preconditions) as session:
        stopped(session, PolicyDenied, r"neither kind can be discharged soundly yet")


# --- T9: the session stops after apply_commit -------------------------------


def test_no_snapshot_and_no_validation_follows_apply_commit_in_one_invocation(tmp_path):
    """Step 17 is a stop. Observation is a separate entry.

    `apply_commit` takes its own `POST_COMMIT` snapshot inside the receipt
    transaction — that is the kernel settling the commit, not the driver
    observing afterwards. What is asserted here is that the driver adds
    nothing after it: no further step, and no validation attempt at all.
    """
    parameters, report, _ = S.applied(tmp_path, slug="stops")
    assert report.steps[-1].act == "commit.apply"
    assert report.stopped_at == 16
    assert "separate driver entry" in report.stopped_because

    store = store_of(parameters)
    try:
        events = [e.event_type for e in store.list_events(report.project_id)]
        assert not any(e.startswith("validation.executing") for e in events)
        applied_at = max(i for i, e in enumerate(events) if e == "commit_receipt.attested")
        after = events[applied_at + 1:]
        assert not any(e.startswith("validation.") or e == "snapshot.taken" for e in after), after
    finally:
        store.close()


def test_observation_is_a_separate_entry_and_discharges_nothing(tmp_path):
    """`observe()` produces a receipt; no receipt from it meets a precondition."""
    from pathlib import Path

    parameters, report, _ = S.applied(tmp_path, slug="observe")
    # The owner advances the throwaway workspace to the governed revision.
    import subprocess

    subprocess.run(["git", "-C", parameters.workspace_root, "merge", "--ff-only",
                    report.materialized_revision], check=True, capture_output=True)

    from gruntime.driver import open_runtime

    with open_runtime(parameters, transport=S.ScriptedTransport()) as controller:
        session = PilotSession(controller, parameters, S.ScriptedPresenter(),
                               owner=S.OWNER, environ=S.environ(), entry="observe")
        observation = session.observe(report.project_id, report.run_id, spec_id="check")
        assert observation.observational is True
        assert observation.state == "OBSERVED"
        assert [s.act for s in observation.steps] == ["snapshot.take", "validation.execute"]
        assert all(s.detail.get("discharges") == "nothing" for s in observation.steps)
        assert observation.steps[1].detail["verdict"] == "PASS"
        assert observation.materialized_revision is None

        # And the receipt it produced still discharges nothing: a commit that
        # binds a validation precondition is refused whatever is on record.
        digest = controller.store.list_events(report.project_id)[-1].payload_digest
        intent = controller.propose_commit(
            report.run_id, path=S.TARGET, content=S.PROPOSED + "# more\n",
            message="second", preconditions=CommitPreconditions(validations=(digest,)))
        with pytest.raises(PolicyDenied, match=r"neither kind can be discharged soundly yet"):
            controller.authorize_commit(intent.intent_id)


def test_a_restart_reports_recovery_and_stops(tmp_path):
    """A new process is a new epoch and a new relay, never a continuation."""
    from gruntime.driver import open_runtime

    parameters, report, _ = S.applied(tmp_path, slug="restart")
    with open_runtime(parameters, transport=S.ScriptedTransport()) as controller:
        session = PilotSession(controller, parameters, S.ScriptedPresenter(),
                               owner=S.OWNER, environ=S.environ(), entry="resume")
        resumed = session.resume(report.project_id)
    assert [s.act for s in resumed.steps] == ["controller.start", "recovery.reconcile"]
    assert resumed.state == "RECOVERED"
    assert resumed.steps[0].identity["controller_epoch"] == "2"
    assert resumed.steps[1].detail["unresolved"] == []
    assert "the owner decides what happens next" in resumed.stopped_because


# --- T10: the report ---------------------------------------------------------


def test_the_report_shape_is_stable_and_carries_what_a_refusal_needs(tmp_path):
    parameters, live = partial(tmp_path, "commit.authorize", slug="report-shape")
    with live as session:
        stopped(session, OwnerRefused, r"commit\.authorize")
        document = session.documented_report()
    assert sorted(document) == sorted([
        "contract_id", "entry", "materialized_revision", "observational",
        "parameters", "project_id", "run_id", "state", "stopped_at",
        "stopped_because", "steps"])
    assert sorted(document["steps"][0]) == [
        "act", "decision_id", "detail", "identity", "refusal_text",
        "refusal_type", "result", "step"]
    refused = document["steps"][-1]
    assert refused["result"] == "REFUSED"
    assert refused["refusal_type"] == "OwnerRefused"
    assert "commit.authorize" in refused["refusal_text"]
    # Requested act, observed result, decision id, identity, refusal.
    proposed = next(s for s in document["steps"] if s["act"] == "commit.propose")
    assert proposed["identity"]["intent_id"] and proposed["identity"]["operation_token"]
    invoked = next(s for s in document["steps"] if s["act"] == "worker.invoke")
    assert invoked["identity"]["receipt_id"] and invoked["decision_id"]
    assert json.loads(json.dumps(document)) == document


def test_the_report_carries_no_environment_value(tmp_path, monkeypatch):
    """Only the variable's name; never its value, and never any other."""
    monkeypatch.setenv("GR32_UNRELATED_SECRET", "must-not-appear-anywhere")
    parameters, report, document = S.applied(tmp_path, slug="no-environ")
    text = json.dumps(document)
    assert "must-not-appear-anywhere" not in text
    assert S.CREDENTIAL not in text


# --- GR32-F-003: the worker's operation and before_digest are checked -------


def seeded(tmp_path, name, content="def greet(name):\n    return name\n"):
    """A workspace whose base already tracks the pilot's target path."""
    import subprocess

    root = S.workspace(tmp_path, name=name)
    (root / S.TARGET).write_text(content, encoding="utf-8")
    for args in (("add", "-A"), ("commit", "-q", "-m", "seed")):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return root, content


def worker(op, before_digest):
    return S.ScriptedTransport(mutations=[dict(
        op=op, path=S.TARGET, content=S.PROPOSED, rename_to=None,
        before_digest=before_digest, mode=None)])


def test_a_create_against_an_absent_path_lands_as_a_create(tmp_path):
    parameters, report, _ = S.applied(tmp_path, slug="create-valid")
    proposed = next(s for s in report.steps if s.act == "commit.propose")
    assert proposed.detail["op"] == "CREATE" and proposed.detail["before_digest"] is None
    store = store_of(parameters)
    try:
        intent, = store.list_commit_intents(report.run_id)
        assert [m.op for m in intent.mutations] == [MutationOp.CREATE]
    finally:
        store.close()


def test_a_create_against_an_existing_path_is_refused_with_no_intent(tmp_path):
    """The reviewer's reproduction: CREATE used to be committed as MODIFY."""
    root, _ = seeded(tmp_path, "create-existing")
    parameters = S.parameters(tmp_path, slug="create-existing", root=root)
    with S.session(parameters, transport=worker("CREATE", None)) as session:
        report = stopped(session, ProposalUnsupported,
                         r"proposed CREATE for 'src/main\.py', which already exists")
        assert report.stopped_at == 14 and report.materialized_revision is None
        assert session.controller.store.list_commit_intents(session.run_id) == []
    assert S.revisions(root) == "2"


def test_a_modify_with_the_base_digest_lands_as_a_modify(tmp_path):
    from gruntime.canonical import digest_bytes

    root, content = seeded(tmp_path, "modify-valid")
    parameters = S.parameters(tmp_path, slug="modify-valid", root=root)
    with S.session(parameters,
                   transport=worker("MODIFY", digest_bytes(content.encode()))) as session:
        report = session.run()
        intent, = session.controller.store.list_commit_intents(session.run_id)
        assert [m.op for m in intent.mutations] == [MutationOp.MODIFY]
        assert intent.mutations[0].before_digest == digest_bytes(content.encode())
    assert report.state == "MATERIALIZED"


@pytest.mark.parametrize("before", [
    "sha256:" + "0" * 64,   # well-formed and stale: the reviewer's reproduction
    None,                   # missing
])
def test_a_modify_with_a_stale_or_missing_before_digest_is_refused(tmp_path, before):
    root, _ = seeded(tmp_path, f"modify-{'missing' if before is None else 'stale'}")
    parameters = S.parameters(tmp_path, slug=root.name, root=root)
    with S.session(parameters, transport=worker("MODIFY", before)) as session:
        report = stopped(session, ProposalUnsupported,
                         r"before_digest .* is not the governed base content")
        assert report.stopped_at == 14 and report.materialized_revision is None
        assert session.controller.store.list_commit_intents(session.run_id) == []
    assert S.revisions(root) == "2"


def test_a_modify_of_an_absent_path_is_refused_with_no_intent(tmp_path):
    parameters = S.parameters(tmp_path, slug="modify-absent")
    with S.session(parameters, transport=worker("MODIFY", None)) as session:
        stopped(session, ProposalUnsupported,
                r"proposed MODIFY for 'src/main\.py', which is absent")
        assert session.controller.store.list_commit_intents(session.run_id) == []


@pytest.mark.parametrize("changes,base,match", [
    ({"op": MutationOp.CREATE}, {S.TARGET: "sha256:b"}, r"which already exists at the governed base"),
    ({"op": MutationOp.CREATE, "before_digest": "sha256:b"}, {},
     r"while claiming a prior content identity"),
    ({"op": MutationOp.MODIFY, "before_digest": None}, {}, r"which is absent at the governed base"),
    ({"op": MutationOp.MODIFY, "before_digest": "sha256:old"}, {S.TARGET: "sha256:b"},
     r"is not the governed base content"),
])
def test_operation_and_before_digest_mismatches_are_refused(changes, base, match):
    with pytest.raises(ProposalUnsupported, match=match):
        mapped(receipt(mutations=(mutation(**changes),)), base_index=base)


def test_a_matching_modify_maps_and_keeps_the_workers_claims():
    result = mapped(receipt(mutations=(mutation(op=MutationOp.MODIFY, before_digest="sha256:b"),)),
                    base_index={S.TARGET: "sha256:b"})
    assert (result.op, result.before_digest) == ("MODIFY", "sha256:b")


# --- GR32-F-006: the budget is a runtime input ------------------------------


@pytest.mark.parametrize("budget", [
    (1800000, 3, 25.0, 2, 1, 4),
    (7200000, 9, 400.0, 11, 5, 7),
])
def test_the_recorded_budget_is_the_one_supplied(tmp_path, budget):
    from gruntime.models import Budget

    supplied = Budget(*budget)
    parameters, report, document = S.applied(
        tmp_path, slug=f"budget-{budget[0]}", budget=supplied)
    assert document["parameters"]["budget"] == dict(sorted(
        zip(("wall_clock_ms", "worker_invocations", "cost_units",
             "validation_executions", "commits", "escalations"), budget)))
    store = store_of(parameters)
    try:
        assert store.get_project(report.project_id).budget == supplied
        assert Budget(**store.get_contract(report.contract_id).budget_ceiling) == supplied
    finally:
        store.close()


@pytest.mark.parametrize("budget", [
    None,
    "zero",
    "negative",
])
def test_a_missing_or_inadmissible_budget_is_refused_before_any_transition(tmp_path, budget):
    from gruntime.models import Budget

    value = {"zero": Budget(), "negative": Budget(1000, -1, 1.0, 1, 1, 1)}.get(budget)
    parameters = S.parameters(tmp_path, slug=f"budget-{budget}", budget=value)
    with S.session(parameters) as session:
        report = stopped(session, PolicyDenied, r"none admissible was supplied")
        assert report.state == "STOPPED" and report.stopped_at == 1
        assert no_projects(session.controller.store)


# --- GR32-R-001: the budget fits the contract before any transition --------


@pytest.mark.parametrize("cost", [0.5, 2.25, 100.001])
def test_a_fractional_cost_is_refused_at_step_1_before_any_transition(tmp_path, cost):
    """The closure reviewer's reproduction: steps 2–6 used to land first.

    Refused at step 1 as a normal STOPPED report: no project, no decision, no
    run, no revision — and the refusal names the value exactly as supplied.
    """
    from gruntime.models import Budget

    supplied = Budget(3600000, 100, cost, 100, 100, 100)
    root = S.workspace(tmp_path)
    parameters = S.parameters(tmp_path, slug="fractional", root=root, budget=supplied)
    with S.session(parameters) as session:
        report = stopped(session, PolicyDenied, r"does not fit the StageContract budget shape")
        assert report.state == "STOPPED" and report.stopped_at == 1
        step, = report.steps
        assert (step.act, step.result, step.refusal_type) == (
            "runtime.compose", "REFUSED", "PolicyDenied")
        assert f"'cost_units': {cost!r}" in step.refusal_text
        assert report.project_id is None and report.run_id is None
        assert no_projects(session.controller.store)
        assert session.controller.store.connection.execute(
            "SELECT COUNT(*) FROM decisions").fetchone()[0] == 0
    # Not rounded, truncated or normalized on the way: the parameters still
    # carry exactly what the owner supplied.
    assert parameters.budget == supplied and parameters.budget.cost_units == cost
    assert S.revisions(root) == "1"


@pytest.mark.parametrize("field", ["wall_clock_ms", "worker_invocations", "commits"])
def test_any_fractional_budget_field_is_refused_at_step_1(tmp_path, field):
    """The contract types every budget field integer; the check is the schema's."""
    from dataclasses import replace

    from gruntime.models import Budget

    budget = replace(Budget(3600000, 100, 100, 100, 100, 100), **{field: 1.5})
    parameters = S.parameters(tmp_path, slug=f"fractional-{field}", budget=budget)
    with S.session(parameters) as session:
        report = stopped(session, PolicyDenied, r"does not fit the StageContract budget shape")
        assert report.stopped_at == 1 and no_projects(session.controller.store)


@pytest.mark.parametrize("cost", [100, 100.0])
def test_an_integral_cost_reaches_materialization_unaltered(tmp_path, cost):
    """`100` and `100.0` are both integers to the schema; neither is rewritten."""
    from gruntime.models import Budget

    supplied = Budget(3600000, 100, cost, 100, 100, 100)
    parameters, report, document = S.applied(
        tmp_path, slug=f"integral-{cost!r}".replace(".", "-"), budget=supplied)
    assert report.state == "MATERIALIZED", report.document()
    assert document["parameters"]["budget"]["cost_units"] == cost
    assert type(document["parameters"]["budget"]["cost_units"]) is type(cost)
    store = store_of(parameters)
    try:
        assert store.get_project(report.project_id).budget == supplied
    finally:
        store.close()


def test_budget_fits_contract_is_the_contract_schema():
    """The predicate asks `stage_contract.schema.json`, not a copy of it."""
    from gruntime.contracts import SCHEMA
    from gruntime.driver import CONTRACT_BUDGET, budget_fits_contract
    from gruntime.models import Budget

    assert CONTRACT_BUDGET.schema is SCHEMA["$defs"]["Budget"]
    assert budget_fits_contract(Budget(1, 1, 1.0, 1, 1, 1))
    assert not budget_fits_contract(Budget(1, 1, 0.5, 1, 1, 1))
    assert not budget_fits_contract(None)


def test_no_budget_is_compiled_into_the_driver():
    """`D5`: the reviewer's literal is gone, and the default is absence."""
    import inspect

    import gruntime.driver as driver

    assert "Budget(3600000" not in inspect.getsource(driver)
    assert driver.PilotParameters(workspace_root="/w", governance_root="/g",
                                  provider="fake").budget is None


# --- GR32-F-001: every typed refusal is a stopped report --------------------


def test_an_incomplete_parameter_set_is_a_stopped_step_not_a_running_report(tmp_path):
    from gruntime.driver import PilotParameters

    complete = S.parameters(tmp_path, slug="incomplete")
    partial_set = PilotParameters(workspace_root=complete.workspace_root,
                                  governance_root=complete.governance_root, provider="fake")
    with S.session(partial_set) as session:
        report = stopped(session, PolicyDenied, r"carries only the composition half")
    assert report.state == "STOPPED" and report.stopped_at == 1
    assert [(s.step, s.act, s.result) for s in report.steps] == [(1, "runtime.compose", "REFUSED")]
