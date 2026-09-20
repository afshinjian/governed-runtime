"""GR-29: a `HumanDecision` names the principal key that made it.

[domain-model.md:58](../design/domain-model.md#L58) makes `principal_key_id`
"required when `actor_kind = HUMAN`". `F04-001` found the runtime enforcing the
other two halves of `HD-INV-1` — the actor kind, and an `auth_method` that is
neither `NONE` nor `DELEGATED` — and not this one, at the recording boundary or
at either persistence boundary. A keyless approval can be attributed to nobody
afterwards, which is the whole of what a decision is for.

The invariant is one implication:

    decided_by.actor_kind == HUMAN  ⇒  bool(principal_key_id)

enforced at three places over one predicate: `record_decision`, before anything
is constructed, appended or persisted; `StateStore.put_decision`, for a write
that reached the store another way; and `_decision_from_row`, the single
hydration point behind both `get_decision` and `list_decisions`, so a malformed
record already on disk is refused rather than handed back.

Nothing repairs, coerces, rewrites or backfills such a record. It fails closed
on every read, permanently: a decision that cannot say who made it is not a
decision, and quietly inventing a key for it would manufacture the very
attribution the record is missing.

Every refusal is asserted with `match=` (`CLAUDE.md`, `F04-002`): a bare
`pytest.raises` accepts whichever guard fires first, and three of the guards
exercised here raise `IntegrityViolation` over the same call.
"""

from __future__ import annotations

import json

import pytest

from gruntime.decision import decision_content_hash
from gruntime.errors import IntegrityViolation, PolicyDenied
from gruntime.models import (
    ActorKind,
    ActorRef,
    AuthMethod,
    DecisionKind,
    DecisionScope,
    DecisionState,
    DecisionSubjectKind,
    EscalationSeverity,
    EscalationStatus,
    EscalationTrigger,
    HumanDecision,
    SnapshotTrigger,
    SuspensionState,
)
from gruntime.store import now_ts

from gr03_support import project_with_repo, snapshot, write

# --- principals -------------------------------------------------------------

#: A named principal: human, authenticated, and keyed.
KEYED = ActorRef(
    actor_kind=ActorKind.HUMAN,
    actor_id="owner@example.invalid",
    auth_method=AuthMethod.SESSION,
    principal_key_id="key-owner",
)

#: The same human with no key at all — `F04-001`'s actor.
KEYLESS = ActorRef(
    actor_kind=ActorKind.HUMAN,
    actor_id="owner@example.invalid",
    auth_method=AuthMethod.SESSION,
    principal_key_id=None,
)

#: A key-shaped field holding nothing. `Str(1..128)` admits no empty string,
#: and an empty key names a principal exactly as well as a missing one does.
EMPTY_KEY = ActorRef(
    actor_kind=ActorKind.HUMAN,
    actor_id="owner@example.invalid",
    auth_method=AuthMethod.SESSION,
    principal_key_id="",
)

#: A human who authenticates by signature, keyed and keyless.
KEYED_SIGNER = ActorRef(
    actor_kind=ActorKind.HUMAN,
    actor_id="signer@example.invalid",
    auth_method=AuthMethod.SIGNATURE,
    principal_key_id="key-signer",
)
KEYLESS_SIGNER = ActorRef(
    actor_kind=ActorKind.HUMAN,
    actor_id="signer@example.invalid",
    auth_method=AuthMethod.SIGNATURE,
    principal_key_id=None,
)

#: Opaque signature evidence. Nothing verifies it; `DESIGN-04-035`.
SIGNATURE = "sig-3f9a2c" * 4

#: The refusal, at each of the three boundaries that raises it.
AT_RECORD = r"must name the principal key it was made with: record_decision"
AT_PUT = r"must name the principal key it was made with: put_decision"
AT_READ = r"must name the principal key it was made with: stored decision dec-"


# --- fixtures ---------------------------------------------------------------


@pytest.fixture
def decisions(h):
    """A started project with a `COMPLETE` snapshot to bind decisions to."""
    project_id = project_with_repo(h, slug="gr29")
    snapshot(h, project_id)
    return project_id


def record(controller, project_id, *, decided_by, signature=None):
    """One `record_decision` call, so each test varies only its principal."""
    evidence = controller.store.store_artifact(
        b"the diff the human was shown", media_type="text/plain"
    )
    return controller.record_decision(
        project_id,
        decision_kind=DecisionKind.APPROVE,
        subject_kind=DecisionSubjectKind.RUN,
        subject_id="run-1",
        question="Apply this change?",
        chosen="yes",
        justification="reviewed the diff",
        decided_by=decided_by,
        evidence_shown=[evidence],
        options_offered=("yes", "no"),
        signature=signature,
    )


def handmade(project_id, *, decided_by, decision_id="dec-handmade"):
    """A `HumanDecision` built outside the controller, for the store boundary.

    `put_decision` is a public method of the store and is reachable without
    passing through `record_decision` at all; this is the value it would be
    handed.
    """
    decision = HumanDecision(
        decision_id=decision_id,
        project_id=project_id,
        subject_kind=DecisionSubjectKind.RUN,
        subject_id="run-1",
        decision_kind=DecisionKind.APPROVE,
        question="Apply this change?",
        chosen="yes",
        justification="reviewed the diff",
        scope=DecisionScope.PROJECT,
        decided_by=decided_by,
        auth_method=decided_by.auth_method,
        decided_at=now_ts(),
        nonce="0" * 32,
        snapshot_bound=False,
        decision_state=DecisionState.VALID,
        options_offered=("yes", "no"),
    )
    decision.decision_hash = decision_content_hash(decision)
    return decision


def strip_key(store, decision_id):
    """Make an already-stored decision malformed, as a historical record is.

    The row is edited in the database directly, which is the only way such a
    record can exist once `put_decision` refuses one: the point of the read
    guard is what happens to rows that were written before the rule existed.
    """
    raw = store.raw_execute(
        "SELECT decided_by FROM decisions WHERE decision_id=?", (decision_id,)
    )[0][0]
    actor = json.loads(raw)
    actor["principal_key_id"] = None
    store.raw_execute(
        "UPDATE decisions SET decided_by=? WHERE decision_id=?",
        (json.dumps(actor), decision_id),
    )


# --- the recording boundary -------------------------------------------------


def test_record_decision_refuses_a_missing_principal_key(h, decisions):
    """`domain-model.md:58`: a `HUMAN` decider is a named principal."""
    with h.controller(with_repo=True) as controller:
        with pytest.raises(IntegrityViolation, match=AT_RECORD):
            record(controller, decisions, decided_by=KEYLESS)


def test_record_decision_refuses_an_empty_principal_key(h, decisions):
    """An empty key is a key-shaped absence, not a principal."""
    with h.controller(with_repo=True) as controller:
        with pytest.raises(IntegrityViolation, match=AT_RECORD):
            record(controller, decisions, decided_by=EMPTY_KEY)


def test_a_session_is_refused_for_the_key_and_nothing_else(h, decisions):
    """`SESSION` satisfies `guard:decision_actor_authenticated` and not this.

    The two actors differ in the key alone: one is recorded, the other is
    refused. That is what makes the new rule independently load-bearing rather
    than a restatement of the `auth_method` check standing next to it.
    """
    with h.controller(with_repo=True) as controller:
        assert record(controller, decisions, decided_by=KEYED).decision_id
        with pytest.raises(IntegrityViolation, match=AT_RECORD):
            record(controller, decisions, decided_by=KEYLESS)


def test_a_signature_is_refused_for_the_key_and_nothing_else(h, decisions):
    """`SIGNATURE` with the signature itself still names no key.

    `guard:decision_signature_present` is satisfied by both actors here, so
    the refusal is provably the key rule's: signature evidence identifies no
    principal while nothing verifies it against one (`DESIGN-04-035`).
    """
    with h.controller(with_repo=True) as controller:
        assert record(
            controller, decisions,
            decided_by=KEYED_SIGNER, signature=SIGNATURE,
        ).decision_id
        with pytest.raises(IntegrityViolation, match=AT_RECORD):
            record(
                controller, decisions,
                decided_by=KEYLESS_SIGNER, signature=SIGNATURE,
            )


def test_refusal_precedes_every_decision_and_audit_side_effect(h, decisions):
    """Nothing is constructed, appended or persisted before the refusal.

    A refusal that leaves `decision.recorded` on the chain has already
    published the authority it is refusing to grant, and the event is
    append-only: there is no later moment at which it can be taken back.
    """
    with h.store() as store:
        before = store.get_project(decisions)
        # Creation records and consumes its own approval (`AX-14`), so the
        # project already holds one decision; the count that matters is the
        # delta across the refusal, not zero.
        decisions_before = store.raw_execute("SELECT COUNT(*) FROM decisions")[0][0]
        events_before = store.raw_execute(
            "SELECT COUNT(*) FROM audit_events WHERE project_id=?", (decisions,)
        )[0][0]

    with h.controller(with_repo=True) as controller:
        with pytest.raises(IntegrityViolation, match=AT_RECORD):
            record(controller, decisions, decided_by=KEYLESS)

    with h.store() as store:
        assert store.raw_execute(
            "SELECT COUNT(*) FROM decisions"
        )[0][0] == decisions_before
        assert store.raw_execute(
            "SELECT COUNT(*) FROM audit_events WHERE event_type='decision.recorded'"
            " AND project_id=?", (decisions,)
        )[0][0] == 1
        assert store.raw_execute(
            "SELECT COUNT(*) FROM audit_events WHERE project_id=?", (decisions,)
        )[0][0] == events_before
        after = store.get_project(decisions)
        assert (after.event_seq, after.event_head) == (
            before.event_seq, before.event_head
        )
        store.verify_chain(decisions)


# --- the write boundary -----------------------------------------------------


def test_put_decision_refuses_a_keyless_human_decision(h, decisions):
    """The store enforces the invariant for a writer that never went through
    `record_decision`."""
    with h.store() as store:
        with pytest.raises(IntegrityViolation, match=AT_PUT):
            store.put_decision(handmade(decisions, decided_by=KEYLESS))
        assert store.raw_execute(
            "SELECT COUNT(*) FROM decisions WHERE decision_id='dec-handmade'"
        )[0][0] == 0


def test_put_decision_refuses_an_empty_principal_key(h, decisions):
    with h.store() as store:
        with pytest.raises(IntegrityViolation, match=AT_PUT):
            store.put_decision(handmade(decisions, decided_by=EMPTY_KEY))


# --- the read boundary ------------------------------------------------------


def test_get_decision_refuses_a_malformed_stored_row(h, decisions):
    """A record written before the rule existed is refused, not returned."""
    with h.controller(with_repo=True) as controller:
        decision = record(controller, decisions, decided_by=KEYED)
    with h.store() as store:
        strip_key(store, decision.decision_id)
        with pytest.raises(IntegrityViolation, match=AT_READ):
            store.get_decision(decision.decision_id)


def test_list_decisions_refuses_a_malformed_stored_row(h, decisions):
    """The listing fails closed rather than skipping the malformed row.

    Silently omitting it would let a caller conclude the project holds no such
    decision, which is a different and worse claim than refusing to answer.
    """
    with h.controller(with_repo=True) as controller:
        decision = record(controller, decisions, decided_by=KEYED)
    with h.store() as store:
        strip_key(store, decision.decision_id)
        with pytest.raises(IntegrityViolation, match=AT_READ):
            store.list_decisions(decisions)


def test_a_malformed_row_is_never_repaired(h, decisions):
    """No read rewrites, coerces or backfills the missing key.

    The refusal is terminal by design: the runtime holds nothing it could put
    in the field, and writing a plausible one would fabricate attribution.
    """
    with h.controller(with_repo=True) as controller:
        decision = record(controller, decisions, decided_by=KEYED)
    with h.store() as store:
        strip_key(store, decision.decision_id)
        for _ in range(2):
            with pytest.raises(IntegrityViolation, match=AT_READ):
                store.get_decision(decision.decision_id)
        raw = store.raw_execute(
            "SELECT decided_by FROM decisions WHERE decision_id=?",
            (decision.decision_id,),
        )[0][0]
        assert json.loads(raw)["principal_key_id"] is None


# --- what the rule leaves alone ---------------------------------------------


@pytest.mark.parametrize(
    "decided_by, signature",
    [
        pytest.param(KEYED, None, id="session"),
        pytest.param(KEYED_SIGNER, SIGNATURE, id="signature"),
    ],
)
def test_a_keyed_decision_still_round_trips(h, decisions, decided_by, signature):
    """The valid case is unchanged: recorded, persisted, read back, `VALID`."""
    with h.controller(with_repo=True) as controller:
        decision = record(
            controller, decisions, decided_by=decided_by, signature=signature
        )
    with h.store() as store:
        stored = store.get_decision(decision.decision_id)
        assert stored.decided_by == decided_by
        assert stored.decided_by.principal_key_id == decided_by.principal_key_id
        assert stored.decision_state is DecisionState.VALID
        assert stored.decision_hash == decision.decision_hash
        assert stored.signature == signature
        assert decision.decision_id in [
            d.decision_id for d in store.list_decisions(decisions)
        ]
        store.verify_chain(decisions)


# --- the snapshot boundary (`GR29-R01`) -------------------------------------
#
# The read guard fires wherever a decision is hydrated, and one of those places
# is `take_snapshot`: it publishes the observation first and *then* derives
# staleness over every decision (`HD-INV-4`). A malformed row aborts the
# derivation after the new snapshot is already current, which used to leave the
# project holding a superseded reality, approvals still `VALID` against the
# reality they superseded, and `suspension = NONE` — with the drift escalation
# that stage would have raised never reached. Refusing the read is right; doing
# it halfway through publishing a new reality is what is corrected here.


def _drift(h) -> None:
    """Move the workspace, as a human editing their own checkout does."""
    write(h, "README.md", "reality moved on\n")


def _state(store, decision_id) -> str:
    """The stored `decision_state`, read past the hydration guard.

    Read with SQL on purpose: `get_decision` would refuse the malformed row,
    and the question here is what the *other* decision's row still says.
    """
    return store.raw_execute(
        "SELECT decision_state FROM decisions WHERE decision_id=?", (decision_id,)
    )[0][0]


def _assert_safe(h, project_id, run_id, authorization, malformed):
    """Everything `GR29-R01` requires of the durable state, at one moment.

    Every assertion opens its own store or controller, so what is checked is
    what the database holds rather than what some live object remembers. The
    test calls this twice, the second time through a second pair opened after
    the first closed: a safe state that reading changes is not a safe state,
    and the read guard is the one thing here that fires on every read.
    """
    with h.store() as store:
        project = store.get_project(project_id)
        # (4) protection, by the runtime's existing integrity semantics: one
        # OPEN escalation whose suspension is the project's, named by the ref.
        assert project.suspension is SuspensionState.SUSPENDED_BY_INTEGRITY
        escalations = store.list_escalations(project_id)
        assert [e.trigger for e in escalations] == [
            EscalationTrigger.INTEGRITY_VIOLATION
        ]
        escalation = escalations[0]
        assert escalation.severity is EscalationSeverity.CRITICAL
        assert escalation.status is EscalationStatus.OPEN
        assert escalation.suspension_applied is project.suspension
        assert escalation.suspension_target == "PROJECT"
        assert project.suspension_ref == escalation.escalation_id
        # Project-scoped, exactly as `REALITY_DRIFT` is: the gate that bars
        # every new effect reads the project.
        assert escalation.run_id is None
        assert store.get_run(run_id).suspension is SuspensionState.NONE
        # (1) the malformed decision is still unreadable, by either reader.
        with pytest.raises(IntegrityViolation, match=AT_READ):
            store.get_decision(malformed)
        with pytest.raises(IntegrityViolation, match=AT_READ):
            store.list_decisions(project_id)
        # (2) and still malformed: nothing repaired, coerced or backfilled it.
        raw = store.raw_execute(
            "SELECT decided_by FROM decisions WHERE decision_id=?", (malformed,)
        )[0][0]
        assert json.loads(raw)["principal_key_id"] is None
        # The audit chain still verifies over everything that was written.
        store.verify_chain(project_id)

    # (3) the prior authorization cannot be exercised. It is still `VALID` on
    # disk — the derivation that would have staled it never ran, and nothing
    # rewrites a decision it could not enumerate — so what makes it unusable
    # is the suspension, and that is what is asserted.
    with h.controller(with_repo=True) as controller:
        assert _state(controller.store, authorization) == DecisionState.VALID.value
        with pytest.raises(PolicyDenied, match="SUSPENDED_BY_INTEGRITY"):
            controller.propose_commit(
                run_id, path="a.txt", content="x", message="probe"
            )


def test_a_failed_staleness_derivation_suspends_the_project(h):
    """`GR29-R01`: the reviewer's sequence, and the durable state after it.

    A well-formed approval, a historical keyless row beside it, and a workspace
    that moved. The snapshot publishes, the derivation refuses the keyless row,
    and the project must not come out of that still able to act.
    """
    project_id = project_with_repo(h, slug="gr29-snapshot")
    first = snapshot(h, project_id)
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)
        authorization = record(controller, project_id, decided_by=KEYED)
        historical = record(controller, project_id, decided_by=KEYED)
    assert authorization.subject_snapshot_id == first
    with h.store() as store:
        strip_key(store, historical.decision_id)

    _drift(h)
    with h.controller(with_repo=True) as controller:
        with pytest.raises(IntegrityViolation, match=AT_READ):
            controller.take_snapshot(project_id, trigger=SnapshotTrigger.DRIFT_CHECK)
        # The observation itself stands: it is a true fact about a moment, and
        # it is the reality the approval no longer matches.
        assert controller.store.get_project(project_id).snapshot_current != first

    # The durable state, read through a store and a controller opened after
    # the failing one closed.
    _assert_safe(h, project_id, run_id, authorization.decision_id,
                 historical.decision_id)
    # (5) and again through another pair: reopening preserves it, and nothing
    # the first pass read repaired, cleared or advanced.
    _assert_safe(h, project_id, run_id, authorization.decision_id,
                 historical.decision_id)


def test_a_readable_project_is_not_suspended_by_the_new_gate(h):
    """The correction costs the healthy path nothing.

    Same drift, no malformed row: the derivation completes, the approval goes
    `STALE` on its own account, and the only escalation is `REALITY_DRIFT`'s.
    A guard that suspended here would make every observation an incident.
    """
    project_id = project_with_repo(h, slug="gr29-healthy")
    with h.controller(with_repo=True) as controller:
        authorization = record(controller, project_id, decided_by=KEYED)

    _drift(h)
    snapshot(h, project_id, trigger=SnapshotTrigger.DRIFT_CHECK)

    with h.store() as store:
        assert _state(store, authorization.decision_id) == DecisionState.STALE.value
        assert [e.trigger for e in store.list_escalations(project_id)] == [
            EscalationTrigger.REALITY_DRIFT
        ]
        assert store.get_project(project_id).suspension is (
            SuspensionState.SUSPENDED_BY_DRIFT
        )
