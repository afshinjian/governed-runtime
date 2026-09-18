"""GR-27 — GR-23's creation path against `AX-17`'s full predicate set.

Design basis: [DESIGN-04 revision 05 §2.23](../design/DESIGN-04-baseline-correction-05.md)
states the seven predicates a conforming creation witness must satisfy, and
[DESIGN-04-FINDINGS-04 §5](../design/review/DESIGN-04-FINDINGS-04.md) reports
rows 1, 2, 3, 5 and 6 unmet by `GR-23`. One section per finding:

===========  =========  ==================================================
finding      §2.23 row  obligation
===========  =========  ==================================================
`-032`       1          the mode the creating act establishes
`-033`       2, 3       the creator, and the two events' actors
`-034`       5          `chosen ∈ options_offered`
`-035`       5          `SIGNATURE` binds a signature
`-036`       6          the approval is informed and fresh
===========  =========  ==================================================

The `GR-27` remediation sections at the end answer the bounded review's three
findings: `GR27-R1` the explicit `SUPERVISED` creation contract, `GR27-R2` the
presenter-reentrancy boundary, `GR27-R3` inert response materialization and
exact approved-snapshot binding.

Almost nothing here is monkeypatched: a declining human is a real response, a
hostile response value is a real `str` subclass, and a reentrant presenter
makes a real controller call. Two predicates are no longer reachable from
outside — the policy cell a frozen matrix fixes, and the freshness recheck that
`GR27-R2` now stands in front of — and those two say so at their own tests.
"""

from __future__ import annotations

import json

import pytest

from gruntime.decision import decision_content_hash
from gruntime.errors import IntegrityViolation, PolicyDenied
from gruntime import controller as controller_module
from gruntime.controller import (
    CreationResponse,
    creation_is_permitted_in,
    delegation_depth,
)
from gruntime.models import (
    ActorKind,
    ActorRef,
    AuthMethod,
    DecisionKind,
    DecisionSubjectKind,
    GovernanceMode,
    ProjectLifecycle,
)

from gruntime.store import actor_from_json, actor_to_dict
from gruntime.transitions import ORIGIN, Axis, PolicyVerdict, rules_for

from gr06_support import document as contract_document

from genesis_support import (
    CREATE,
    DECLINE,
    OWNER,
    OWNER_OF_OWNER,
    SIGNATURE,
    SIGNER,
    create_project,
)


# --- DESIGN-04-034: a valid choice (§2.23 row 5) ----------------------------


def test_a_decision_cannot_choose_an_option_that_was_never_offered(h):
    """[domain-model.md:696](../design/domain-model.md#L696): `chosen` MUST be
    a member of `options_offered`, enforced centrally where the decision is
    recorded rather than at each caller."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
        evidence = controller.store.store_artifact(b"x", media_type="text/plain")
        with pytest.raises(IntegrityViolation, match="options_offered"):
            controller.record_decision(
                project_id,
                decision_kind=DecisionKind.APPROVE,
                subject_kind=DecisionSubjectKind.RUN,
                subject_id="run-1",
                question="Apply this change?",
                chosen="maybe",
                justification="because",
                decided_by=OWNER,
                evidence_shown=[evidence],
                options_offered=("yes", "no"),
            )


def test_an_empty_option_set_offers_nothing_to_choose(h):
    """`options_offered` is required ([:695](../design/domain-model.md#L695)):
    an approval recorded against an empty set is malformed, and a malformed
    decision is authority for nothing."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
        evidence = controller.store.store_artifact(b"x", media_type="text/plain")
        with pytest.raises(IntegrityViolation, match="options_offered"):
            controller.record_decision(
                project_id,
                decision_kind=DecisionKind.APPROVE,
                subject_kind=DecisionSubjectKind.RUN,
                subject_id="run-1",
                question="Apply this change?",
                chosen="yes",
                justification="because",
                decided_by=OWNER,
                evidence_shown=[evidence],
            )


def test_genesis_records_the_options_the_human_was_actually_offered(h):
    """The creation approval is a `HumanDecision` like any other: it offers
    real choices and records the one the human took."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
    with h.store() as store:
        (approval,) = store.list_decisions(project_id)
        assert approval.options_offered == (CREATE, DECLINE)
        assert approval.chosen == CREATE
        assert approval.chosen in approval.options_offered


# --- DESIGN-04-035: signature evidence (§2.23 row 5) ------------------------


def _counts(store, *tables) -> dict:
    return {
        table: store.raw_execute(f"SELECT COUNT(*) FROM {table}")[0][0]
        for table in tables
    }


GENESIS_TABLES = ("projects", "audit_events", "snapshots", "decisions")


def test_a_signature_method_without_a_signature_publishes_nothing(h):
    """[domain-model.md:710](../design/domain-model.md#L710): where
    `auth_method = SIGNATURE` the `signature` is required. The method label
    and a key id are not the evidence, and the refusal happens before any of
    the genesis transaction is durable."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        with pytest.raises(IntegrityViolation, match="SIGNATURE.*signature"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                approved_by=SIGNER,
            )
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_a_signature_method_binds_the_signature_it_was_given(h):
    """The signature is persisted on the decision and inside its content
    hash, so it cannot be attached, swapped or dropped afterwards."""
    with h.controller() as controller:
        project_id = create_project(
            controller,
            name="GR-27",
            slug="gr-27",
            workspace_root=str(h.root),
            approved_by=SIGNER,
            signature=SIGNATURE,
        )
    with h.store() as store:
        (approval,) = store.list_decisions(project_id)
        assert approval.auth_method is AuthMethod.SIGNATURE
        assert approval.signature == SIGNATURE
        # Bound: the stored hash is over the signature the decision carries.
        assert approval.decision_hash == decision_content_hash(approval)
        approval.signature = "sig-forged"
        assert decision_content_hash(approval) != approval.decision_hash


def test_a_session_approval_needs_no_signature(h):
    """[:710](../design/domain-model.md#L710) is conditional on the method:
    `SESSION` is unaffected."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
    with h.store() as store:
        (approval,) = store.list_decisions(project_id)
        assert approval.auth_method is AuthMethod.SESSION
        assert approval.signature is None


# --- DESIGN-04-033a: the creator (§2.23 row 2) ------------------------------


def test_the_project_is_created_by_the_human_who_approved_it(h):
    """[domain-model.md:150](../design/domain-model.md#L150) and
    [transition-matrix.md:485](../design/transition-matrix.md#L485): creation
    by a non-human is `NONE_GRANTABLE`/`DENY`. A runtime cannot originate a
    project and thereby its own ceiling, so `created_by` is the approver."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
    with h.store() as store:
        created_by = store.get_project(project_id).created_by
        assert created_by.actor_kind is ActorKind.HUMAN
        assert created_by == OWNER


# --- DESIGN-04-033b: event 1's actor (§2.23 row 3) --------------------------


def _events(h, project_id):
    with h.store() as store:
        return store.list_events(project_id)


def test_the_decision_record_event_is_held_by_the_deciding_human(h):
    """`AX-15`: `decision.record` requires `actor.actor_kind = HUMAN` with an
    authenticating `auth_method` and an **absent** `authority_ref`. A
    `RUNTIME` actor with `auth_method = NONE` does not hold it, and a `HUMAN`
    value in the decision's own `decided_by` is a field of a different
    record."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
    recorded = _events(h, project_id)[1]
    assert recorded.capability_used == "decision.record"
    assert recorded.actor.actor_kind is ActorKind.HUMAN
    assert recorded.actor == OWNER
    assert recorded.actor.auth_method is AuthMethod.SESSION
    # `AX-15` excepts `AX-1`: the human's own act cites no delegated authority.
    assert recorded.authority_ref is None


def test_the_decision_record_event_preserves_the_authentication_method(h):
    """The event carries the method the human actually authenticated with,
    not a method the runtime chose for them."""
    with h.controller() as controller:
        project_id = create_project(
            controller,
            name="GR-27",
            slug="gr-27",
            workspace_root=str(h.root),
            approved_by=SIGNER,
            signature=SIGNATURE,
        )
    recorded = _events(h, project_id)[1]
    assert recorded.actor == SIGNER
    assert recorded.actor.auth_method is AuthMethod.SIGNATURE


def test_the_observation_and_consumption_events_remain_the_runtime_s(h):
    """Only the two acts §2.23 row 3 constrains change hands. Events 0 and 3
    are the runtime's own work and stay attributed to it."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
    events = _events(h, project_id)
    assert [event.actor.actor_kind for event in (events[0], events[3])] == [
        ActorKind.RUNTIME,
        ActorKind.RUNTIME,
    ]


# --- DESIGN-04-033c: event 2's delegated actor (§2.23 row 3) ----------------


def test_the_creation_event_is_the_runtime_acting_for_the_deciding_human(h):
    """`AX-16`: the `project.create` event may carry a `RUNTIME` actor, but
    only one that names the deciding principal in `on_behalf_of` and cites
    the approval in `authority_ref`."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
    with h.store() as store:
        events = store.list_events(project_id)
        (approval,) = store.list_decisions(project_id)
    created = events[2]
    assert created.capability_used == "project.create"
    assert created.actor.actor_kind is ActorKind.RUNTIME
    assert created.actor.on_behalf_of == OWNER
    assert created.actor.auth_method is AuthMethod.DELEGATED
    assert created.authority_ref == approval.decision_id


def test_the_delegated_actor_stands_at_depth_two(h):
    """Depth is the runtime and the principal it acts for, and no further."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
    created = _events(h, project_id)[2]
    assert delegation_depth(created.actor) == 2
    assert created.actor.on_behalf_of.on_behalf_of is None


def test_a_deeper_delegation_chain_is_refused_and_publishes_nothing(h):
    """`AX-16` caps the chain at two. An approver who is themselves acting
    for someone else would put the mediated creation at depth three."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        with pytest.raises(IntegrityViolation, match="delegation depth"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                approved_by=OWNER_OF_OWNER,
            )
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_an_undelegated_actor_keeps_its_existing_event_preimage(h):
    """The key is written only where the delegation exists, so every event
    recorded in the existing format hashes exactly as it did and the chain
    verifies across both forms."""
    plain = actor_to_dict(OWNER)
    assert "on_behalf_of" not in plain
    assert set(plain) == {"actor_kind", "actor_id", "auth_method", "principal_key_id"}
    delegated = actor_to_dict(
        ActorRef(
            actor_kind=ActorKind.RUNTIME,
            actor_id="gruntime.controller",
            auth_method=AuthMethod.DELEGATED,
            on_behalf_of=OWNER,
        )
    )
    assert delegated["on_behalf_of"] == plain
    assert actor_from_json(json.dumps(delegated)).on_behalf_of == OWNER

    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
    with h.store() as store:
        store.verify_chain(project_id)
        assert [
            event.actor.on_behalf_of is None for event in store.list_events(project_id)
        ] == [True, True, False, True]


# --- DESIGN-04-032: the mode the creating act establishes (§2.23 row 1) -----


def test_a_conforming_creation_installs_supervised(h):
    """§2.23 row 1: the §3 mode gate is evaluated against the mode the
    creating act itself establishes, and `SUPERVISED` is the only value that
    passes it."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
    with h.store() as store:
        assert store.get_project(project_id).governance_mode is (
            GovernanceMode.SUPERVISED
        )


def test_creating_a_project_autonomous_is_denied_and_publishes_nothing(h):
    """[authority-matrix.md:157](../design/authority-matrix.md#L157) and
    [transition-matrix.md:84](../design/transition-matrix.md#L84) make
    `project.create` `DENY` in `AUTONOMOUS`, and `AX-14`'s approval does not
    lift a `DENY` policy cell."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        with pytest.raises(PolicyDenied, match="project.create is DENY in AUTONOMOUS"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                initial_mode=GovernanceMode.AUTONOMOUS,
            )
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_the_refusal_reads_the_matrix_row_rather_than_a_copy_of_it(h):
    """The gate consults row 2-1's own verdict column, so the refusal cannot
    drift away from the frozen cell it enforces."""
    (rule,) = rules_for(Axis.PROJECT, ORIGIN, ProjectLifecycle.DRAFT.value)
    assert rule.required_capability == "project.create"
    assert rule.policy(GovernanceMode.AUTONOMOUS).verdict is PolicyVerdict.DENY
    assert rule.policy(GovernanceMode.SUPERVISED).verdict is not PolicyVerdict.DENY


# --- DESIGN-04-036: informed approval (§2.23 row 6) -------------------------


def test_the_presentation_is_mandatory(h):
    """The boundary is not optional: there is no way to create a project
    without presenting the observation and receiving an answer."""
    with h.controller() as controller:
        with pytest.raises(TypeError, match="present"):
            controller.create_project(
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                approved_by=OWNER,
            )


def test_no_conforming_response_publishes_nothing(h):
    """A presentation that yields no answer is not an approval. The runtime
    cannot supply one on the human's behalf (`HD-INV-2`)."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        with pytest.raises(IntegrityViolation, match="no conforming response"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                present=lambda observation: None,
            )
        assert _counts(controller.store, *GENESIS_TABLES) == before


class _LooksLikeAResponse:
    """Everything a `CreationResponse` carries, and none of its type.

    The exact `snapshot_id` that was presented, the approving choice, and the
    two optional fields the approval would read. Attribute-wise it answers
    the observation; it is simply not the human's answer.
    """

    def __init__(self, observation):
        self.snapshot_id = observation.snapshot_id
        self.chosen = CREATE
        self.justification = "looks conforming"
        self.signature = None


def test_an_answer_shaped_object_is_not_a_human_s_answer(h):
    """`HD-INV-2` is a type invariant, not a shape one: the boundary accepts
    the answer it defined and nothing that merely resembles it, however
    exactly the fields line up.

    The type invariant has one owner: `guard:creation_response`. Every
    later check asks something else — `_answers` asks only the binding
    question, and materialization asks only whether the values are built-ins
    — so this object, carrying the presented `snapshot_id`, the approving
    choice and every field the approval would read as a plain `str`, is
    refused by the type guard and by nothing else.
    """
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        with pytest.raises(IntegrityViolation, match="no conforming response"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                present=_LooksLikeAResponse,
            )
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_a_declining_human_publishes_nothing(h):
    """`DECLINE` is a real offered option, so declining is a decision the
    boundary can actually express — and it creates nothing."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        with pytest.raises(IntegrityViolation, match="declined"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                chosen=DECLINE,
            )
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_a_response_naming_a_different_observation_publishes_nothing(h):
    """[domain-model.md:703](../design/domain-model.md#L703): the approval is
    over "the repository reality the human actually approved". An answer that
    names some other snapshot approves an unknown workspace."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        with pytest.raises(IntegrityViolation, match="answers a different observation"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                present=lambda observation: CreationResponse(
                    snapshot_id="snap-somewhere-else", chosen=CREATE
                ),
            )
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_an_observation_superseded_before_commit_publishes_nothing(h, monkeypatch):
    """Freshness is rechecked after the answer and before the commit: while
    the human was deciding, reality may have been observed again, and what
    they approved is then no longer what would be created.

    This predicate is no longer reachable from outside the runtime. `GR27-R2`
    stands in front of it — a presenter that observes the pending project
    again is refused at the reentrancy boundary — and `GR27-R3` stops a
    response value from observing anything at all. The recheck stays, as the
    last thing the transaction asks before it records the approval, and is
    exercised here the only way that remains: by making the store report the
    approved observation superseded. What a real second observation now does
    is asserted by
    `test_a_presenter_that_mutates_the_pending_project_publishes_nothing`.

    Nothing downstream re-asks this. `record_decision` validates only that the
    approved snapshot is one of this project's `COMPLETE` observations, which
    it still is here — the observation is current in the store and superseded
    only to the predicate patched below — so the refusal is this guard's and
    no other's.
    """
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        monkeypatch.setattr(
            type(controller),
            "_is_current_observation",
            lambda self, project_id, snapshot_id: False,
        )
        with pytest.raises(IntegrityViolation, match="no longer the current observation"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
            )
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_the_approval_is_bound_to_the_exact_observation_presented(h):
    """What is recorded as `evidence_shown` is what the presentation actually
    carried, and `subject_snapshot_id` is the observation that was approved —
    not an index the runtime selected and then labelled human-seen."""
    seen = []

    def present(observation):
        seen.append(observation)
        return CreationResponse(snapshot_id=observation.snapshot_id, chosen=CREATE)

    with h.controller() as controller:
        project_id = create_project(
            controller,
            name="GR-27",
            slug="gr-27",
            workspace_root=str(h.root),
            present=present,
        )
    (observation,) = seen
    with h.store() as store:
        genesis = store.list_snapshots(project_id)[0]
        (approval,) = store.list_decisions(project_id)
    assert observation.project_id == project_id
    assert observation.snapshot_id == genesis.snapshot_id
    assert observation.options_offered == (CREATE, DECLINE)
    assert observation.workspace_root == str(h.root)
    assert approval.subject_snapshot_id == observation.snapshot_id
    assert [ref.digest for ref in approval.evidence_shown] == [
        ref.digest for ref in observation.evidence_shown
    ]
    assert approval.chosen == CREATE
    assert approval.question == observation.question


# ===========================================================================
# GR-27 remediation — the three findings of the bounded Codex review.
# ===========================================================================

# --- GR27-R1: the creation contract is explicitly SUPERVISED ---------------


def test_creation_will_not_choose_the_governance_mode_for_the_caller(h):
    """There is no production default. The mode a creating act establishes is
    a required, human-supplied field (domain-model.md:138), and a runtime that
    supplied it for the caller would be establishing a governance mode nobody
    asked for."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        with pytest.raises(TypeError, match="initial_mode"):
            controller.create_project(
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                approved_by=OWNER,
                present=lambda observation: CreationResponse(
                    snapshot_id=observation.snapshot_id, chosen=CREATE
                ),
            )
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_creation_is_permitted_in_reads_the_frozen_cell():
    """The matrix read is a faithful read of row 2-1's own verdict column, so
    the two tests below may substitute for it without substituting for what it
    says (transition-matrix.md:84, authority-matrix.md:157)."""
    assert creation_is_permitted_in(GovernanceMode.SUPERVISED) is True
    assert creation_is_permitted_in(GovernanceMode.AUTONOMOUS) is False


def test_a_policy_cell_that_denied_supervised_would_refuse_creation(h, monkeypatch):
    """The matrix gate is not decoration beside the `SUPERVISED` contract: it
    is consulted, and its `DENY` refuses creation on its own. With the policy
    lookup reporting `DENY` for every mode, the mode genesis otherwise accepts
    is refused."""
    monkeypatch.setattr(controller_module, "creation_is_permitted_in", lambda mode: False)
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        with pytest.raises(PolicyDenied, match="project.create is DENY in SUPERVISED"):
            create_project(
                controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
            )
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_a_mode_the_policy_stops_denying_is_still_not_a_mode_genesis_accepts(
    h, monkeypatch
):
    """Non-`DENY` is a necessary condition, never a sufficient one. A later
    change that made `AUTONOMOUS` admissible in the matrix must not thereby
    make it a mode a creating act may establish: §2.23 row 1 names
    `SUPERVISED`, and `project.mode.set` — the only route to any other mode —
    still has no legal transition row."""
    monkeypatch.setattr(controller_module, "creation_is_permitted_in", lambda mode: True)
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        with pytest.raises(PolicyDenied, match="created SUPERVISED"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                initial_mode=GovernanceMode.AUTONOMOUS,
            )
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_the_presentation_carries_the_mode_the_creating_act_establishes(h):
    """§2.23 row 1 is a predicate of the act the human authorizes, so the mode
    is part of what they are shown: the approval is over this project *under
    this governance mode*, and the project installed carries exactly it."""
    seen = []

    def present(observation):
        seen.append(observation)
        return CreationResponse(snapshot_id=observation.snapshot_id, chosen=CREATE)

    with h.controller() as controller:
        project_id = create_project(
            controller,
            name="GR-27",
            slug="gr-27",
            workspace_root=str(h.root),
            initial_mode=GovernanceMode.SUPERVISED,
            present=present,
        )
    (observation,) = seen
    assert observation.initial_mode is GovernanceMode.SUPERVISED
    assert GovernanceMode.SUPERVISED.value in observation.question
    with h.store() as store:
        project = store.get_project(project_id)
        (approval,) = store.list_decisions(project_id)
    assert project.governance_mode is observation.initial_mode
    assert approval.question == observation.question


# --- GR27-R2: the presentation boundary may not mutate the pending project --


GENESIS_WITNESS = ("snapshot.take", "decision.record", "project.create", "audit.append")


def test_a_conforming_creation_witnesses_exactly_four_ordered_events(h):
    """`AX-17`, §2.23 row 7: four transitions, four events, one transaction,
    each event naming exactly one capability (`G-4`). This is the witness the
    reentrancy boundary exists to keep intact."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
    with h.store() as store:
        events = store.list_events(project_id)
        project = store.get_project(project_id)
    assert tuple(event.capability_used for event in events) == GENESIS_WITNESS
    assert [event.seq for event in events] == [0, 1, 2, 3]
    assert project.event_seq == 3
    assert project.event_head == events[3].event_hash


def test_a_presenter_that_mutates_the_pending_project_publishes_nothing(h):
    """The presentation boundary is not a place to act from. A presenter that
    calls back into the controller against the very project being created
    would insert an event between the observation and the creation witness,
    and `AX-17`'s four-event transaction would no longer be what committed."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        presented = []

        def present(observation):
            presented.append(observation.project_id)
            controller.start(observation.project_id)
            return CreationResponse(
                snapshot_id=observation.snapshot_id, chosen=CREATE
            )

        with pytest.raises(IntegrityViolation, match="mid-genesis"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                present=present,
            )
        assert len(presented) == 1
        assert _counts(controller.store, *GENESIS_TABLES) == before
        assert controller.store.raw_execute(
            "SELECT COUNT(*) FROM audit_events WHERE project_id=?", (presented[0],)
        )[0][0] == 0


def test_the_boundary_holds_only_the_project_being_created(h):
    """Scoped to the pending project, not to the controller. An unrelated
    project is nobody's open transaction and stays operable."""
    with h.controller() as controller:
        first = create_project(
            controller, name="first", slug="first", workspace_root=str(h.root)
        )
        before = controller.store.get_project(first).controller_epoch
        epochs = []

        def present(observation):
            epochs.append(controller.start(first))
            return CreationResponse(
                snapshot_id=observation.snapshot_id, chosen=CREATE
            )

        second = create_project(
            controller,
            name="second",
            slug="second",
            workspace_root=str(h.root),
            present=present,
        )
    assert epochs == [before + 1]
    with h.store() as store:
        assert store.get_project(first).controller_epoch == before + 1
        assert tuple(
            event.capability_used for event in store.list_events(second)
        ) == GENESIS_WITNESS


def test_a_presenter_that_raises_leaves_no_pending_genesis_behind(h):
    """Cleanup is on every exit, not on the successful one. A presenter that
    fails, and a human who declines, both leave the controller able to create
    the next project."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)

        def exploding(observation):
            raise RuntimeError("the presenter failed")

        with pytest.raises(RuntimeError, match="the presenter failed"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                present=exploding,
            )
        assert controller.pending_genesis() == frozenset()
        with pytest.raises(IntegrityViolation, match="declined"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                chosen=DECLINE,
            )
        assert controller.pending_genesis() == frozenset()
        assert _counts(controller.store, *GENESIS_TABLES) == before
        # Nothing stale is held: the next creation is an ordinary one.
        project_id = create_project(
            controller, name="after", slug="after", workspace_root=str(h.root)
        )
        assert controller.pending_genesis() == frozenset()
    with h.store() as store:
        assert tuple(
            event.capability_used for event in store.list_events(project_id)
        ) == GENESIS_WITNESS


# --- GR27-R3: inert response values, and the exact approved snapshot --------


class _HostileText(str):
    """A `str` that takes a second snapshot whenever anyone evaluates it.

    Value-bearing in every way the approval path would use one: truthiness for
    `justification or ...`, and string conversion for anything that formats
    it. `evaluations` counts how many times the runtime handed control to
    this object after it was received.
    """

    def __new__(cls, value, controller, project_id):
        text = super().__new__(cls, value)
        text.controller = controller
        text.project_id = project_id
        text.evaluations = 0
        return text

    def _fire(self):
        self.evaluations += 1
        self.controller.take_snapshot(self.project_id)

    def __bool__(self):
        self._fire()
        return True

    def __str__(self):
        self._fire()
        return "superseded"


def test_a_response_value_that_executes_when_evaluated_is_never_evaluated(h):
    """The attack the bounded review names: a response field whose evaluation
    runs code, supersedes the observation after freshness was checked, and
    leaves the approval bound to a reality the human never saw.

    The runtime reads each response value exactly once, requires it to be a
    plain built-in, and evaluates nothing afterwards. A value-bearing object
    is refused where it is read, so its code never runs at all: `evaluations`
    stays at zero and no second observation exists to bind to."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        hostile = []

        def present(observation):
            text = _HostileText("approved", controller, observation.project_id)
            hostile.append(text)
            return CreationResponse(
                snapshot_id=observation.snapshot_id,
                chosen=CREATE,
                justification=text,
            )

        with pytest.raises(IntegrityViolation, match="plain built-in"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                present=present,
            )
        (text,) = hostile
        assert text.evaluations == 0
        assert _counts(controller.store, *GENESIS_TABLES) == before
        assert controller.store.raw_execute("SELECT COUNT(*) FROM snapshots")[0][0] == 0
        assert controller.store.raw_execute("SELECT COUNT(*) FROM decisions")[0][0] == 0


def test_a_hostile_snapshot_id_is_refused_before_it_can_be_compared(h):
    """The binding field is read under the same rule: a `snapshot_id` that
    executes on comparison would answer the binding question itself."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        hostile = []

        def present(observation):
            text = _HostileText(
                observation.snapshot_id, controller, observation.project_id
            )
            hostile.append(text)
            return CreationResponse(snapshot_id=text, chosen=CREATE)

        with pytest.raises(IntegrityViolation, match="plain built-in"):
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                present=present,
            )
        (text,) = hostile
        assert text.evaluations == 0
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_the_genesis_approval_binds_the_snapshot_that_was_approved(h):
    """§2.23 row 6: `subject_snapshot_id` is "the repository reality the human
    actually approved", so the creation approval names the observation it was
    given — not whatever the store reports as newest when the decision is
    written."""
    seen = []

    def present(observation):
        seen.append(observation)
        return CreationResponse(snapshot_id=observation.snapshot_id, chosen=CREATE)

    with h.controller() as controller:
        project_id = create_project(
            controller,
            name="GR-27",
            slug="gr-27",
            workspace_root=str(h.root),
            present=present,
        )
    (observation,) = seen
    with h.store() as store:
        (approval,) = store.list_decisions(project_id)
        genesis = store.list_snapshots(project_id)[0]
    assert approval.subject_snapshot_id == observation.snapshot_id
    assert approval.subject_snapshot_id == genesis.snapshot_id
    assert [ref.digest for ref in approval.evidence_shown] == [
        ref.digest for ref in observation.evidence_shown
    ]


def test_an_approved_snapshot_must_be_this_project_s_own_observation(h):
    """The explicit argument is validated, not trusted. An id that names no
    observation, and one that names another project's, are both refused: a
    decision recorded against either would claim a reality that is not this
    project's (domain-model.md:703)."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
        elsewhere = create_project(
            controller, name="other", slug="other", workspace_root=str(h.root)
        )
        foreign = controller.store.newest_complete_snapshot(elsewhere).snapshot_id
        evidence = controller.store.store_artifact(b"x", media_type="text/plain")
        before = _counts(controller.store, "decisions")
        for named in ("snap-nowhere", foreign):
            with pytest.raises(IntegrityViolation, match="COMPLETE observations"):
                controller.record_decision(
                    project_id,
                    decision_kind=DecisionKind.APPROVE,
                    subject_kind=DecisionSubjectKind.PROJECT,
                    subject_id=project_id,
                    question="Apply this change?",
                    chosen="yes",
                    options_offered=("yes", "no"),
                    justification="because",
                    decided_by=OWNER,
                    evidence_shown=[evidence],
                    approved_snapshot_id=named,
                )
        assert _counts(controller.store, "decisions") == before


def test_an_approved_snapshot_is_refused_on_a_decision_that_binds_none(h):
    """The other half of the argument's contract: naming an approved
    observation on a decision that is not snapshot-bound would record a
    binding the decision does not have."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
        current = controller.store.newest_complete_snapshot(project_id).snapshot_id
        evidence = controller.store.store_artifact(b"x", media_type="text/plain")
        before = _counts(controller.store, "decisions")
        with pytest.raises(IntegrityViolation, match="snapshot_bound=False"):
            controller.record_decision(
                project_id,
                decision_kind=DecisionKind.GRANT_CAPABILITY,
                subject_kind=DecisionSubjectKind.CAPABILITY,
                subject_id="cap-1",
                question="Grant this?",
                chosen="yes",
                options_offered=("yes", "no"),
                justification="because",
                decided_by=OWNER,
                evidence_shown=[evidence],
                approved_snapshot_id=current,
            )
        assert _counts(controller.store, "decisions") == before


def test_an_unrelated_caller_still_binds_the_newest_complete_snapshot(h):
    """The explicit argument is bounded: callers that name no snapshot keep
    the behaviour they had, and the central binding is unweakened."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
        controller.take_snapshot(project_id)
        current = controller.store.newest_complete_snapshot(project_id).snapshot_id
        evidence = controller.store.store_artifact(b"x", media_type="text/plain")
        decision = controller.record_decision(
            project_id,
            decision_kind=DecisionKind.APPROVE,
            subject_kind=DecisionSubjectKind.PROJECT,
            subject_id=project_id,
            question="Apply this change?",
            chosen="yes",
            options_offered=("yes", "no"),
            justification="because",
            decided_by=OWNER,
            evidence_shown=[evidence],
        )
        assert decision.subject_snapshot_id == current


# ===========================================================================
# GR-27 remediation, round two — the bounded re-review's findings.
#
# `GR27-R4` and `GR27-R5` both say the same thing about the boundary
# `GR27-R2` installed: it was in the wrong place. It began too late to stop a
# durable write that precedes the append it guards, and it ended too early to
# stop one that arrives after the presentation is over and before the
# transaction closes. Everything below is about the interval, not the check.
# ===========================================================================


def _genesis_state(store, project_id: str) -> dict:
    """Everything a committed genesis durably says about a project.

    The comparand for "durable project state matches a clean genesis": the
    project row's governed fields, the whole event chain by identity and
    capability, and the counts of the two entities genesis creates. A caught
    refusal that left an epoch, an event, a snapshot or a decision behind
    shows up here as an inequality, not as a missing assertion.
    """
    project = store.get_project(project_id)
    return {
        "lifecycle": project.lifecycle,
        "governance_mode": project.governance_mode,
        "suspension": project.suspension,
        "controller_epoch": project.controller_epoch,
        "event_seq": project.event_seq,
        "events": tuple(
            (event.seq, event.event_type, event.capability_used)
            for event in store.list_events(project_id)
        ),
        "snapshots": len(store.list_snapshots(project_id)),
        "decisions": len(store.list_decisions(project_id)),
        "contracts": store.raw_execute(
            "SELECT COUNT(*) FROM contracts WHERE project_id=?", (project_id,)
        )[0][0],
    }


def _artifact_files(h) -> int:
    """Blobs in the artifact store. A content-addressed write is durable and
    survives the rollback of the transaction that caused it, so it is the only
    observable a refusal *before* the store write has and a refusal after it
    does not."""
    return sum(1 for path in h.artifacts_dir.rglob("*") if path.is_file())


# --- GR27-R4: a caught refusal may not leave durable state behind ----------


def test_a_caught_start_refusal_leaves_no_controller_epoch_behind(h):
    """`GR27-R4`, route 1. `start` bumps `controller_epoch` durably and only
    then appends `controller.started`. A presenter that calls it, swallows the
    refusal and answers `CREATE` would have committed the bump inside genesis's
    own transaction, with no event to account for it.

    The boundary is therefore in front of the mutation, not in front of the
    append: the epoch is never bumped, the refusal is all the presenter gets,
    and the creation it then approves is an ordinary one."""
    with h.controller() as controller:
        control = create_project(
            controller, name="control", slug="control", workspace_root=str(h.root)
        )
        caught = []

        def present(observation):
            try:
                controller.start(observation.project_id)
            except IntegrityViolation as exc:
                caught.append(str(exc))
            return CreationResponse(
                snapshot_id=observation.snapshot_id, chosen=CREATE
            )

        project_id = create_project(
            controller,
            name="GR-27",
            slug="gr-27",
            workspace_root=str(h.root),
            present=present,
        )
    assert len(caught) == 1 and "mid-genesis" in caught[0]
    with h.store() as store:
        project = store.get_project(project_id)
        events = store.list_events(project_id)
        assert project.controller_epoch == 0
        assert "controller.started" not in {event.event_type for event in events}
        assert tuple(event.capability_used for event in events) == GENESIS_WITNESS
        assert _genesis_state(store, project_id) == _genesis_state(store, control)


def test_a_caught_author_contract_refusal_leaves_no_contract_behind(h):
    """`GR27-R4`, route 2. `author_contract` persists the contract row and only
    then appends `contract.authored`, so a swallowed refusal there commits a
    contract no event attests. The same boundary stands in front of the row."""
    with h.controller() as controller:
        control = create_project(
            controller, name="control", slug="control", workspace_root=str(h.root)
        )
        caught = []

        def present(observation):
            try:
                controller.author_contract(
                    contract_document(project_id=observation.project_id)
                )
            except IntegrityViolation as exc:
                caught.append(str(exc))
            return CreationResponse(
                snapshot_id=observation.snapshot_id, chosen=CREATE
            )

        project_id = create_project(
            controller,
            name="GR-27",
            slug="gr-27",
            workspace_root=str(h.root),
            present=present,
        )
    assert len(caught) == 1 and "mid-genesis" in caught[0]
    with h.store() as store:
        events = store.list_events(project_id)
        assert store.raw_execute(
            "SELECT COUNT(*) FROM contracts WHERE project_id=?", (project_id,)
        )[0][0] == 0
        assert "contract.authored" not in {event.event_type for event in events}
        assert tuple(event.capability_used for event in events) == GENESIS_WITNESS
        assert _genesis_state(store, project_id) == _genesis_state(store, control)


def test_a_presenter_that_observes_the_pending_project_again_writes_no_blob(h):
    """`take_snapshot` fingerprints the workspace and stores the index as an
    artifact **before** it appends anything, and a content-addressed blob
    survives the rollback of the transaction that wrote it. The boundary is in
    front of the observation, so no blob is written at all — which is what
    distinguishes this refusal from the append guard's."""
    with h.controller() as controller:
        # What a clean genesis costs the artifact store: its own observation
        # index, and one payload blob per event of the witness.
        opening = _artifact_files(h)
        control = create_project(
            controller, name="control", slug="control", workspace_root=str(h.root)
        )
        clean = _artifact_files(h) - opening
        caught = []

        def present(observation):
            # A workspace change, so that an observation taken here would
            # necessarily store an index the genesis observation did not.
            (h.root / "presenter-was-here.txt").write_text("x", encoding="utf-8")
            try:
                controller.take_snapshot(observation.project_id)
            except IntegrityViolation as exc:
                caught.append(str(exc))
            return CreationResponse(
                snapshot_id=observation.snapshot_id, chosen=CREATE
            )

        before = _artifact_files(h)
        project_id = create_project(
            controller,
            name="GR-27",
            slug="gr-27",
            workspace_root=str(h.root),
            present=present,
        )
        assert len(caught) == 1 and "mid-genesis" in caught[0]
        assert _artifact_files(h) - before == clean
    with h.store() as store:
        assert len(store.list_snapshots(project_id)) == 1
        assert _genesis_state(store, project_id) == _genesis_state(store, control)


def test_the_presentation_cannot_record_the_approval_it_is_being_asked_for(h):
    """Genesis appends four events against a project the boundary is holding,
    so it holds an authorization the boundary recognizes. That authorization is
    not on the public API: `record_decision` takes no token, and a presenter
    calling it against the pending project is refused exactly as `start` is —
    while genesis's own approval still lands as event 1."""
    with h.controller() as controller:
        evidence = controller.store.store_artifact(b"x", media_type="text/plain")
        caught = []

        def present(observation):
            try:
                controller.record_decision(
                    observation.project_id,
                    decision_kind=DecisionKind.APPROVE,
                    subject_kind=DecisionSubjectKind.PROJECT,
                    subject_id=observation.project_id,
                    question=observation.question,
                    chosen=CREATE,
                    options_offered=(CREATE, DECLINE),
                    justification="from inside the presentation",
                    decided_by=OWNER,
                    evidence_shown=[evidence],
                )
            except IntegrityViolation as exc:
                caught.append(str(exc))
            return CreationResponse(
                snapshot_id=observation.snapshot_id, chosen=CREATE
            )

        project_id = create_project(
            controller,
            name="GR-27",
            slug="gr-27",
            workspace_root=str(h.root),
            present=present,
        )
    assert len(caught) == 1 and "mid-genesis" in caught[0]
    with h.store() as store:
        (approval,) = store.list_decisions(project_id)
        events = store.list_events(project_id)
        assert approval.justification != "from inside the presentation"
        assert tuple(event.capability_used for event in events) == GENESIS_WITNESS


# --- GR27-R5: the hold runs to the end of the transaction ------------------


class _FinalizingResponse(CreationResponse):
    """A genuine `CreationResponse` with inert fields and a hostile finalizer.

    The reviewer's `GR27-R5` reproduction. Materialization copies this
    object's values into the runtime's own record, but the object itself stays
    alive in `_genesis`'s frame until `_genesis` returns — and `__del__` then
    runs after the freshness recheck, after the approval, and while the
    creation transaction is still open. Nothing here is monkeypatched: it is a
    real subclass whose every field is a plain `str`.
    """

    def arm(self, controller, project_id, log):
        object.__setattr__(self, "_controller", controller)
        object.__setattr__(self, "_project_id", project_id)
        object.__setattr__(self, "_log", log)
        return self

    def __del__(self):
        entry = {"pending": self._controller.pending_genesis(), "refused": None}
        try:
            entry["snapshot_id"] = self._controller.take_snapshot(self._project_id)
        except BaseException as exc:  # noqa: BLE001 — the point is what it is
            entry["refused"] = f"{type(exc).__name__}: {exc}"
        self._log.append(entry)


def test_a_response_finalizer_cannot_supersede_the_approved_observation(h):
    """`GR27-R5`. The finalizer fires inside the open transaction, so the hold
    must still be on when it does — object lifetime is not something the
    runtime gets to arrange.

    What the reviewer reproduced was two snapshots, five events, `event_seq`
    4, and an approval left bound to a snapshot the finalizer had superseded.
    None of it survives: the finalizer runs, is refused, and the witness that
    commits is the four-event one."""
    with h.controller() as controller:
        control = create_project(
            controller, name="control", slug="control", workspace_root=str(h.root)
        )
        log = []

        def present(observation):
            return _FinalizingResponse(
                snapshot_id=observation.snapshot_id, chosen=CREATE
            ).arm(controller, observation.project_id, log)

        project_id = create_project(
            controller,
            name="GR-27",
            slug="gr-27",
            workspace_root=str(h.root),
            present=present,
        )
        assert controller.pending_genesis() == frozenset()
    # The attack ran, and it ran inside the window it was aimed at.
    (entry,) = log
    assert entry["pending"] == frozenset({project_id})
    assert entry["refused"] is not None and "mid-genesis" in entry["refused"]
    with h.store() as store:
        events = store.list_events(project_id)
        project = store.get_project(project_id)
        (approval,) = store.list_decisions(project_id)
        (snapshot,) = store.list_snapshots(project_id)
        assert tuple(event.capability_used for event in events) == GENESIS_WITNESS
        assert [event.seq for event in events] == [0, 1, 2, 3]
        assert project.event_seq == 3
        assert project.event_head == events[3].event_hash
        assert approval.subject_snapshot_id == snapshot.snapshot_id
        assert (
            store.newest_complete_snapshot(project_id).snapshot_id
            == snapshot.snapshot_id
        )
        assert _genesis_state(store, project_id) == _genesis_state(store, control)


def test_the_hold_is_released_once_the_transaction_closes(h):
    """Held to the end of the transaction, and no further. What the boundary
    refuses during genesis is ordinary work the moment the commit lands, and a
    creation that refuses releases the hold just as a successful one does."""
    with h.controller() as controller:
        project_id = create_project(
            controller, name="GR-27", slug="gr-27", workspace_root=str(h.root)
        )
        assert controller.pending_genesis() == frozenset()
        assert controller.start(project_id) == 1
        controller.take_snapshot(project_id)

        def declining(observation):
            assert controller.pending_genesis() == frozenset(
                {observation.project_id}
            )
            return CreationResponse(
                snapshot_id=observation.snapshot_id, chosen=DECLINE
            )

        with pytest.raises(IntegrityViolation, match="declined"):
            create_project(
                controller,
                name="declined",
                slug="declined",
                workspace_root=str(h.root),
                present=declining,
            )
        assert controller.pending_genesis() == frozenset()


# --- GR27-R6: the refusal evaluates nothing the attacker supplied ----------


class _HostileTypeName(type):
    """A metaclass that runs code whenever anyone asks its classes their name."""

    @property
    def __name__(cls):
        cls.asked.append("type.__name__")
        return "str"

    def __repr__(cls):
        cls.asked.append("type.__repr__")
        return "<class 'str'>"


class _NotAString(metaclass=_HostileTypeName):
    """A response value that is not a `str` and reacts to being described."""

    asked: list = []

    def __repr__(self):
        type(self).asked.append("instance __repr__")
        return "'approved'"

    def __str__(self):
        type(self).asked.append("instance __str__")
        return "approved"


def test_the_inert_value_refusal_evaluates_no_attacker_supplied_diagnostic(h):
    """`GR27-R6`. The refusal for a value-bearing response field used to name
    the offending types, and a type name is not a fact the runtime holds — it
    is a lookup on an object the attacker defined. Diagnosing the refusal was
    therefore itself an evaluation of the thing being refused.

    The message is now built from constants alone: the hostile value is
    refused, and nothing it defines is ever consulted."""
    with h.controller() as controller:
        before = _counts(controller.store, *GENESIS_TABLES)
        _NotAString.asked.clear()

        def present(observation):
            return CreationResponse(
                snapshot_id=observation.snapshot_id,
                chosen=CREATE,
                justification=_NotAString(),
            )

        with pytest.raises(IntegrityViolation, match="plain built-in") as raised:
            create_project(
                controller,
                name="GR-27",
                slug="gr-27",
                workspace_root=str(h.root),
                present=present,
            )
        assert _NotAString.asked == []
        assert "approved" not in str(raised.value)
        assert _counts(controller.store, *GENESIS_TABLES) == before


def test_a_presenter_cannot_give_the_pending_project_a_worktree(h):
    """The repository side of `GR27-R4`. A governed worktree is a directory
    and a branch: durable, outside the store transaction, and attested by no
    event, so a rollback does not remove it and no audit accounts for it.

    Creating one is a repository mutation taken under the lease, and the
    boundary stands in front of the lease — which is the whole repository
    side, since a project being created has no worktree to reuse."""
    h.init_repo()
    with h.controller(with_repo=True) as controller:
        caught = []

        def present(observation):
            try:
                controller.governed_repo(observation.project_id)
            except IntegrityViolation as exc:
                caught.append(str(exc))
            return CreationResponse(
                snapshot_id=observation.snapshot_id, chosen=CREATE
            )

        project_id = create_project(
            controller,
            name="GR-27",
            slug="gr-27",
            workspace_root=str(h.repo_dir),
            present=present,
        )
    assert len(caught) == 1 and "mid-genesis" in caught[0]
    assert not h.worktree_dir(project_id).exists()
    with h.store() as store:
        events = store.list_events(project_id)
        assert tuple(event.capability_used for event in events) == GENESIS_WITNESS
        assert store.get_project(project_id).controller_epoch == 0
