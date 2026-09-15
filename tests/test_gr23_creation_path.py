"""GR-23 — the creation path: `∅ → DRAFT`, observed, under four events.

Design basis: `DESIGN-04-baseline-correction-04` `AX-14`/`R3.6` (the creation
approval), `AX-17` (the four-event witness), `R3.7` (the approval is
snapshot-bound to the row's own `SNAP`), amendments 19-21 (genesis installs
the project's chain state, and the empty-chain branches of the append
protocol), transition-matrix §7.5-1/§7.5-2, evidence-model §3.1, §3.2.

Nothing here is monkeypatched. The refusal cases are real: a keyless approver
is a real `ActorRef`, and the rolled-back genesis is a real workspace the
adapter cannot see.
"""

from __future__ import annotations

import pytest

from gruntime.errors import IntegrityViolation
from gruntime.models import (
    ActorKind,
    ActorRef,
    AuthMethod,
    Completeness,
    DecisionKind,
    DecisionState,
    DecisionSubjectKind,
    EpistemicClass,
    ProjectLifecycle,
)

from genesis_support import OWNER


def _created(h, **overrides) -> str:
    with h.controller() as controller:
        return controller.create_project(
            name=overrides.pop("name", "GR-23"),
            slug=overrides.pop("slug", "gr-23"),
            workspace_root=overrides.pop("workspace_root", str(h.root)),
            approved_by=overrides.pop("approved_by", OWNER),
            **overrides,
        )


# --- axis 1: a project is created at DRAFT ---------------------------------


def test_a_created_project_is_a_draft(h):
    """`∅ → DRAFT` is the only creation row; `ACTIVE` is reached later."""
    project_id = _created(h)
    with h.store() as store:
        assert store.get_project(project_id).lifecycle is ProjectLifecycle.DRAFT


# --- the genesis observation ------------------------------------------------


def test_creation_observes_the_workspace_before_the_project_exists(h):
    """Event 0 is a `RealitySnapshot` of the workspace being taken under
    governance, and it is the project's first and current observation."""
    project_id = _created(h)
    with h.store() as store:
        observations = store.list_snapshots(project_id)
        assert len(observations) == 1
        genesis = observations[0]
        assert genesis.completeness is Completeness.COMPLETE
        assert genesis.drift_vs is None and genesis.drift_summary is None
        assert store.get_project(project_id).snapshot_current == genesis.snapshot_id


def test_the_creation_approval_binds_to_the_genesis_snapshot(h):
    """`R3.7`: an `APPROVE` over a project is snapshot-bound, and the snapshot
    it binds to is the one event 0 recorded — never an event id."""
    project_id = _created(h)
    with h.store() as store:
        genesis = store.list_snapshots(project_id)[0]
        (approval,) = store.list_decisions(project_id)
        assert approval.decision_kind is DecisionKind.APPROVE
        assert approval.subject_kind is DecisionSubjectKind.PROJECT
        assert approval.subject_id == project_id
        assert approval.snapshot_bound
        assert approval.subject_snapshot_id == genesis.snapshot_id
        assert approval.decided_by == OWNER
        # `HD-INV-2`: the human was shown the observation, not nothing.
        assert [ref.digest for ref in approval.evidence_shown] == [
            genesis.file_index_ref.digest
        ]
        # `AX-12`: the authorizing decision delegates nothing.
        assert approval.grants == frozenset() and approval.revokes == frozenset()


# --- AX-17: the four-event witness ------------------------------------------


def test_genesis_writes_four_ordered_events(h):
    """Four transitions, four events, one transaction, and no event naming two
    capabilities (`G-4`)."""
    project_id = _created(h)
    with h.store() as store:
        events = store.list_events(project_id)
        assert [event.seq for event in events] == [0, 1, 2, 3]
        assert [event.capability_used for event in events] == [
            "snapshot.take",
            "decision.record",
            "project.create",
            "audit.append",
        ]
        assert [event.event_type for event in events] == [
            "snapshot.taken",
            "decision.recorded",
            "project.created",
            "decision.state_derived",
        ]
        assert [event.epistemic_class for event in events] == [
            EpistemicClass.EVIDENCE,
            EpistemicClass.DECISION,
            EpistemicClass.AUTHORITY,
            EpistemicClass.EVIDENCE,
        ]
        store.verify_chain(project_id)


def test_the_chain_is_anchored_and_the_head_is_the_fourth_event(h):
    """Amendments 19-21: `seq = 0` takes the genesis constant as its
    predecessor and installs the project; at commit the head is event 3."""
    project_id = _created(h)
    with h.store() as store:
        events = store.list_events(project_id)
        project = store.get_project(project_id)
        assert events[0].prev_event_hash == store.genesis_hash(project_id)
        assert project.event_seq == 3
        assert project.event_head == events[3].event_hash


def test_creation_cites_its_authority_and_its_snapshot(h):
    """Event 2 names the decision recorded at event 1 as `authority_ref` and
    the snapshot recorded at event 0; event 3 cites event 2."""
    project_id = _created(h)
    with h.store() as store:
        events = store.list_events(project_id)
        (approval,) = store.list_decisions(project_id)
        genesis = store.list_snapshots(project_id)[0]
        assert events[2].authority_ref == approval.decision_id
        payload = store.artifact_bytes(events[2].payload_digest)
        assert genesis.snapshot_id.encode() in payload
        assert ProjectLifecycle.DRAFT.value.encode() in payload
        assert events[3].causal_parent == events[2].event_id
        assert events[3].subject["decision_id"] == approval.decision_id


def test_the_creation_approval_is_consumed_by_the_creation(h):
    """§7.5-2: the decision is spent by the transition it discharged, so the
    nonce cannot authorize a second creation."""
    project_id = _created(h)
    with h.store() as store:
        (approval,) = store.list_decisions(project_id)
        assert approval.decision_state is DecisionState.CONSUMED
        events = store.list_events(project_id)
        payload = store.artifact_bytes(events[3].payload_digest)
        assert b'"from":"VALID"' in payload and b'"to":"CONSUMED"' in payload


# --- one transaction: a failure publishes nothing ---------------------------


def _counts(store, *tables) -> dict:
    return {
        table: store.raw_execute(f"SELECT COUNT(*) FROM {table}")[0][0]
        for table in tables
    }


def test_a_failed_genesis_publishes_nothing(h):
    """The whole creation is one store transaction.

    The workspace here is a directory the git adapter cannot read, so event 0
    is a `FAILED` observation and the snapshot-bound approval has nothing to
    bind to. The failure is therefore raised *after* an append, which is the
    only interesting case: the refusal leaves no project row, no event and no
    snapshot, and advances no existing chain.

    Everything is read back on the **same connection**, which is where an
    unrolled transaction would still be visible; a second connection would
    read the last committed state and could not tell the difference.
    (Content-addressed artifacts written before the refusal are unreferenced,
    not published state.)
    """
    h.repo_dir.mkdir(parents=True, exist_ok=True)
    with h.controller() as controller:
        neighbour = controller.create_project(
            name="Neighbour", slug="neighbour",
            workspace_root=str(h.root), approved_by=OWNER,
        )
        before = controller.store.get_project(neighbour)
        settled = _counts(
            controller.store, "projects", "audit_events", "snapshots", "decisions"
        )

    with h.controller(with_repo=True) as controller:
        with pytest.raises(IntegrityViolation):
            controller.create_project(
                name="Unseen", slug="unseen",
                workspace_root=str(h.repo_dir), approved_by=OWNER,
            )
        # No row of the refused project, and nothing appended anywhere.
        assert _counts(
            controller.store, "projects", "audit_events", "snapshots", "decisions"
        ) == settled
        assert controller.store.raw_execute(
            "SELECT COUNT(*) FROM projects WHERE slug='unseen'"
        )[0][0] == 0
        # No head advance on the chain that already existed.
        after = controller.store.get_project(neighbour)
        assert (after.event_seq, after.event_head) == (
            before.event_seq, before.event_head
        )
        controller.store.verify_chain(neighbour)


# --- AX-14: who may approve a creation --------------------------------------


@pytest.mark.parametrize(
    "approver",
    [
        pytest.param(
            ActorRef(actor_kind=ActorKind.RUNTIME, actor_id="gruntime.controller",
                     auth_method=AuthMethod.SESSION, principal_key_id="key-runtime"),
            id="runtime",
        ),
        pytest.param(
            ActorRef(actor_kind=ActorKind.WORKER, actor_id="worker-1",
                     auth_method=AuthMethod.SESSION, principal_key_id="key-worker"),
            id="worker",
        ),
        pytest.param(
            ActorRef(actor_kind=ActorKind.HUMAN, actor_id="someone",
                     auth_method=AuthMethod.NONE, principal_key_id="key-someone"),
            id="unauthenticated",
        ),
        pytest.param(
            ActorRef(actor_kind=ActorKind.HUMAN, actor_id="someone",
                     auth_method=AuthMethod.DELEGATED, principal_key_id="key-someone"),
            id="delegated",
        ),
        pytest.param(
            ActorRef(actor_kind=ActorKind.HUMAN, actor_id="someone",
                     auth_method=AuthMethod.SESSION, principal_key_id=None),
            id="keyless",
        ),
    ],
)
def test_creation_requires_an_authenticated_human_approval(h, approver):
    """`HD-INV-1` and `AX-14`: the authority for `∅ → DRAFT` is one human's
    decision, and an approval naming no principal key can be attributed to
    nobody afterwards."""
    with h.controller() as controller:
        with pytest.raises(IntegrityViolation):
            controller.create_project(
                name="GR-23", slug="gr-23",
                workspace_root=str(h.root), approved_by=approver,
            )
        assert controller.store.raw_execute(
            "SELECT COUNT(*) FROM projects"
        )[0][0] == 0
