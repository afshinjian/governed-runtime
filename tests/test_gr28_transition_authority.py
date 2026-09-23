"""GR-28: the §7.4 declared capability, held at the moment of transition.

Scope is `COMMIT_INTENT` and nothing else. These tests close `F03-002` (the
authorize and apply rows enforced `commit.propose`, not what they declare) and
`F03-003` (`_transition_intent` labelled an event with a capability it never
proved), and the §7.4 instance of `F03-001` (the table's `required_capability`
column had no production consumer at all).

Every refusal is asserted with `match=`: a bare `pytest.raises` accepts
whichever guard happens to fire first, and `guard:controller_snapshot` spent
two stages SURVIVED that way with the suite green (`CLAUDE.md`, F04-002).

The kernel capability set is the holder under test. A test that withholds a
capability builds a narrower holder, exactly as `GovernedProvider` is built
with `RECOVERY_CAPABILITIES` — it does not reach past the check it is testing.
"""

import pytest

from gruntime.authority import KERNEL_CAPABILITIES
from gruntime.commit import APPLY_CAPABILITY, AUTHORIZE_CAPABILITY, PROPOSE_CAPABILITY
from gruntime.errors import CapabilityDenied, IntegrityViolation
from gruntime.models import (
    ActorKind,
    ActorRef,
    AuthMethod,
    CommitIntentStatus,
    CommitPreconditions,
    Ref,
)
from gruntime.provider import RECOVERY_CAPABILITIES
from gruntime.transitions import ORIGIN, Axis, rules_for

from gr03_support import project_with_repo


# --- the table, read here rather than restated -----------------------------


def row_capability(from_state, to_state):
    """What §7.4 declares for this edge, read from the frozen table.

    The tests assert against the table itself. A test that hard-coded the
    string would pass over a channel that consulted nothing, which is the
    defect (`F03-001`).
    """
    rules = rules_for(Axis.COMMIT_INTENT, from_state, to_state)
    assert rules, f"§7.4 carries no row for {from_state} -> {to_state}"
    return {rule.required_capability for rule in rules}


@pytest.fixture
def commits(h):
    """A started project with a repository and a granted run."""
    project = project_with_repo(h, slug="gr28")
    with h.controller(with_repo=True) as c:
        run = c.open_run(project)
        yield c, project, run


def proposed(c, run, *, path="feature.txt", content="feature\n"):
    return c.propose_commit(run, path=path, content=content, message="Add feature")


def withhold(c, *capabilities):
    """A kernel holder that lacks exactly these capabilities."""
    c.kernel_capabilities = KERNEL_CAPABILITIES - frozenset(capabilities)


# --- F03-002: the rows enforce what they declare ---------------------------


def test_authorize_is_not_satisfied_by_commit_propose(commits):
    """Row 7.4-4 declares `commit.authorize`; a proposing grant is not it.

    This is `F03-002` itself. `commit.propose` is granted and live throughout
    — the assertion above the refusal proves it — and the transition is still
    refused, because the capability the row declares is `KERNEL` and is held
    by the kernel alone (`AX-7`).
    """
    c, project, run = commits
    intent = proposed(c, run)
    assert AUTHORIZE_CAPABILITY in row_capability(
        CommitIntentStatus.PROPOSED, CommitIntentStatus.AUTHORIZED
    )
    c.require_authority(run, PROPOSE_CAPABILITY)
    withhold(c, AUTHORIZE_CAPABILITY)

    with pytest.raises(CapabilityDenied, match=AUTHORIZE_CAPABILITY):
        c.authorize_commit(intent.intent_id)

    assert c.store.get_commit_intent(intent.intent_id).status is CommitIntentStatus.PROPOSED


def test_deny_requires_commit_authorize(commits):
    """Row 7.4-5 declares `commit.authorize`. `deny_commit` held nothing."""
    c, project, run = commits
    intent = proposed(c, run)
    assert AUTHORIZE_CAPABILITY in row_capability(
        CommitIntentStatus.PROPOSED, CommitIntentStatus.DENIED
    )
    withhold(c, AUTHORIZE_CAPABILITY)

    with pytest.raises(CapabilityDenied, match=AUTHORIZE_CAPABILITY):
        c.deny_commit(intent.intent_id, "scope breach")

    assert c.store.get_commit_intent(intent.intent_id).status is CommitIntentStatus.PROPOSED


def test_mark_applying_requires_commit_apply(commits):
    """Row 7.4-6 declares `commit.apply`; the barrier and the gate are not it."""
    c, project, run = commits
    intent = proposed(c, run)
    c.authorize_commit(intent.intent_id)
    assert APPLY_CAPABILITY in row_capability(
        CommitIntentStatus.AUTHORIZED, CommitIntentStatus.APPLYING
    )
    withhold(c, APPLY_CAPABILITY)

    with pytest.raises(CapabilityDenied, match=APPLY_CAPABILITY):
        c.mark_applying(intent.intent_id)

    assert c.store.get_commit_intent(intent.intent_id).status is CommitIntentStatus.AUTHORIZED


def test_apply_refuses_without_commit_apply_and_lands_no_revision(commits, h):
    """The whole apply path, not only its helper: nothing reaches the repository."""
    c, project, run = commits
    intent = proposed(c, run)
    c.authorize_commit(intent.intent_id)
    before = h.revision_count()
    withhold(c, APPLY_CAPABILITY)

    with pytest.raises(CapabilityDenied, match=APPLY_CAPABILITY):
        c.apply_commit(intent.intent_id)

    assert h.revision_count() == before
    assert c.store.list_commit_receipts(intent.intent_id) == []


# --- F03-003: the label is the proven capability ---------------------------


def test_every_commit_transition_is_labelled_with_its_rows_capability(commits):
    """`G-4`: the operation names the capability it holds, not one it chose.

    Read off the table for the edge each event records, so a channel that
    consulted nothing could not pass. The blocked exit of `authorize_commit`
    is included deliberately: it labelled `commit.authorize` over row 7.4-2,
    which declares `commit.propose`.
    """
    c, project, run = commits
    intent = proposed(c, run)
    c.authorize_commit(intent.intent_id)
    c.apply_commit(intent.intent_id)
    blocked = proposed(c, run, path="second.txt", content="second\n")
    c.block_commit(blocked.intent_id)

    seen = {
        (event.event_type, event.capability_used)
        for event in c.store.list_events(project)
        if event.event_type.startswith("commit_intent.")
    }
    expected = {
        ("commit_intent.proposed", ORIGIN, CommitIntentStatus.PROPOSED),
        ("commit_intent.authorized", CommitIntentStatus.PROPOSED, CommitIntentStatus.AUTHORIZED),
        ("commit_intent.applying", CommitIntentStatus.AUTHORIZED, CommitIntentStatus.APPLYING),
        ("commit_intent.settled", CommitIntentStatus.APPLYING, CommitIntentStatus.APPLIED),
        ("commit_intent.blocked", CommitIntentStatus.PROPOSED, CommitIntentStatus.BLOCKED),
    }
    for event_type, from_state, to_state in expected:
        labels = {label for name, label in seen if name == event_type}
        assert labels, f"no {event_type} event was written"
        assert labels <= row_capability(from_state, to_state), (
            f"{event_type} is labelled {labels}, not what §7.4 declares"
        )


def test_the_blocked_exit_of_authorize_is_labelled_by_row_7_4_2(commits):
    """Row 7.4-2 declares `commit.propose`, whatever entry point reaches it.

    `authorize_commit`'s unmet-precondition exit wrote `commit.authorize` over
    this row. The edge decides the label, not the method that took it.
    """
    c, project, run = commits
    # The vehicle is a *decision* precondition, not a validation one: GR-31
    # `Q2a` refuses review- and validation-backed preconditions outright
    # (`guard:gr31_preconditions_deferred`), so those no longer reach any
    # transition. `resolve_decision` remains `lambda ref: False` (`Q4`), so a
    # decision precondition is permanently unmet and takes exactly the
    # unmet-precondition exit this test is about.
    intent = c.propose_commit(
        run,
        path="gated.txt",
        content="gated\n",
        message="Add gated",
        preconditions=CommitPreconditions(decisions=(Ref("HumanDecision", "dec-unmet"),)),
    )
    c.authorize_commit(intent.intent_id)

    assert c.store.get_commit_intent(intent.intent_id).status is CommitIntentStatus.BLOCKED
    blocked = {
        event.capability_used
        for event in c.store.list_events(project)
        if event.event_type == "commit_intent.blocked"
    }
    assert blocked == row_capability(
        CommitIntentStatus.PROPOSED, CommitIntentStatus.BLOCKED
    )
    assert AUTHORIZE_CAPABILITY not in blocked


def test_transition_intent_takes_no_capability_from_its_caller():
    """`F03-003`: the label cannot be supplied, so no caller can mislabel one."""
    from inspect import signature

    from gruntime.controller import Controller

    assert "capability_used" not in signature(Controller._transition_intent).parameters


# --- the two sources, neither standing in for the other --------------------


def test_the_kernel_set_does_not_satisfy_an_ord_row(commits):
    """`AX-11`: `RUNTIME_KERNEL` cannot self-grant a non-`KERNEL` capability.

    Row 7.4-2 declares `commit.propose`, which is `ORD`. A kernel holder that
    carries the string anyway must not satisfy it: the only admissible source
    is the activation's grant basis.
    """
    c, project, run = commits
    intent = proposed(c, run)
    c.revoke_contract(c.store.activation_for_run(run).contract_id)
    c.kernel_capabilities = KERNEL_CAPABILITIES | {PROPOSE_CAPABILITY}

    with pytest.raises(CapabilityDenied, match=PROPOSE_CAPABILITY):
        c.block_commit(intent.intent_id)


def test_block_requires_a_live_proposing_grant(commits):
    """Row 7.4-2's capability is `ORD`, so a revoked contract refuses it."""
    c, project, run = commits
    intent = proposed(c, run)
    c.revoke_contract(c.store.activation_for_run(run).contract_id)

    with pytest.raises(CapabilityDenied, match=PROPOSE_CAPABILITY):
        c.block_commit(intent.intent_id)

    assert c.store.get_commit_intent(intent.intent_id).status is CommitIntentStatus.PROPOSED


def test_a_kernel_row_is_refused_to_a_non_runtime_actor(commits):
    """`AX-7`: `KERNEL` capabilities are the kernel's, acting as itself.

    Unreachable through any public entry point today — every one of them
    appends as the runtime — so the channel is called directly, as `GR-24`
    covers its own unreachable conjuncts.
    """
    c, project, run = commits
    worker = ActorRef(
        actor_kind=ActorKind.WORKER,
        actor_id="worker-1",
        auth_method=AuthMethod.NONE,
    )

    with pytest.raises(CapabilityDenied, match=APPLY_CAPABILITY):
        c._require_transition_authority(
            Axis.COMMIT_INTENT,
            CommitIntentStatus.AUTHORIZED,
            CommitIntentStatus.APPLYING,
            project_id=project,
            run_id=run,
            actor=worker,
        )


def test_a_runtime_actor_takes_the_same_row(commits):
    """The actor check refuses a worker, not the transition itself."""
    c, project, run = commits
    rule = c._require_transition_authority(
        Axis.COMMIT_INTENT,
        CommitIntentStatus.AUTHORIZED,
        CommitIntentStatus.APPLYING,
        project_id=project,
        run_id=run,
    )
    assert rule.row == "7.4-6"
    assert rule.required_capability == APPLY_CAPABILITY


# --- the duplicate rows, told apart by the holder --------------------------


def test_a_reconciling_holder_takes_the_recovery_row(commits):
    """§7.4 carries two rows over `APPLYING -> APPLIED`; `WP-16` tells them apart."""
    c, project, run = commits
    direct = c._require_transition_authority(
        Axis.COMMIT_INTENT,
        CommitIntentStatus.APPLYING,
        CommitIntentStatus.APPLIED,
        project_id=project,
        run_id=run,
    )
    reconciled = c._require_transition_authority(
        Axis.COMMIT_INTENT,
        CommitIntentStatus.APPLYING,
        CommitIntentStatus.APPLIED,
        project_id=project,
        run_id=run,
        kernel_capabilities=RECOVERY_CAPABILITIES,
    )
    assert direct.required_capability == APPLY_CAPABILITY
    assert reconciled.required_capability == "recovery.reconcile"
    assert direct.row != reconciled.row


def test_a_reconciling_holder_cannot_take_the_direct_row(commits):
    """A holder of `recovery.reconcile` alone holds nothing that can execute."""
    c, project, run = commits

    with pytest.raises(CapabilityDenied, match=APPLY_CAPABILITY):
        c._require_transition_authority(
            Axis.COMMIT_INTENT,
            CommitIntentStatus.AUTHORIZED,
            CommitIntentStatus.APPLYING,
            project_id=project,
            run_id=run,
            kernel_capabilities=RECOVERY_CAPABILITIES,
        )


# --- an edge the matrix does not carry -------------------------------------


def test_an_edge_with_no_row_is_refused(commits, monkeypatch):
    """`G-4`/`AX-2`: an operation naming no `CapabilityId` is denied.

    Production takes no such edge, so the graph is emptied for this call the
    way `GR-24` covers a conjunct a later stage made unreachable.
    """
    c, project, run = commits
    monkeypatch.setattr("gruntime.controller.rules_for", lambda *a, **kw: ())

    with pytest.raises(IntegrityViolation, match="no row"):
        c._require_transition_authority(
            Axis.COMMIT_INTENT,
            CommitIntentStatus.AUTHORIZED,
            CommitIntentStatus.APPLYING,
            project_id=project,
            run_id=run,
        )


# --- the kernel set itself -------------------------------------------------


def test_kernel_capabilities_is_the_register_not_a_second_list():
    """One classifier. A hand-kept list would drift from `authority-matrix` §2."""
    from gruntime.authority import REGISTER

    assert KERNEL_CAPABILITIES == frozenset(
        name for name, (kind, _) in REGISTER.items() if kind == "KERNEL"
    )
    assert {APPLY_CAPABILITY, AUTHORIZE_CAPABILITY} <= KERNEL_CAPABILITIES
    assert PROPOSE_CAPABILITY not in KERNEL_CAPABILITIES


def test_a_controller_holds_the_kernel_set(commits):
    """The holder is the controller's, not a literal at each call site."""
    c, project, run = commits
    assert c.kernel_capabilities == KERNEL_CAPABILITIES


# --- the whole lifecycle still runs ----------------------------------------


def test_the_granted_lifecycle_is_unchanged(commits, h):
    """Enforcement refuses what is not held; it does not refuse what is."""
    c, project, run = commits
    before = h.revision_count()
    intent = proposed(c, run)
    c.authorize_commit(intent.intent_id)
    receipt = c.apply_commit(intent.intent_id)

    assert h.revision_count() == before + 1
    assert c.store.get_commit_intent(intent.intent_id).status is CommitIntentStatus.APPLIED
    assert receipt.revision_id
    c.store.verify_chain(project)
