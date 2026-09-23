"""GR-31: a governed, per-field, human-authorized path to provision a project.

`B1`. `create_project` writes neither `capability_ceiling` nor `budget`; the
model defaults them to `frozenset()` and an all-zero `Budget`
(`models.py:914-916`), and until this stage no production code wrote either.
`guard:gr06_activation_ceiling` requires `capability_request ⊆ ceiling`, and
nothing is a subset of nothing, so a project created through the conforming
creation path could never activate a contract and therefore could never do
anything. Every test in the estate provisioned around that by mutating the
dataclass and calling `store.put_project` directly (`tests/gr06_support.py`),
which is the harness bypassing governance rather than governance working.

Two operations close it, per-field (`Q3`): `set_capability_ceiling` and
`grant_project_budget`. Each is one `BEGIN IMMEDIATE` transaction, each is
authorized by its own `HumanDecision`, and each consumes that decision in the
same transaction that installs the field.

The collision the consumption exists for is `T4` below, and it is the reason
this is not one combined operation with one decision: `authority.human_covers`
accepts a `GRANT_CAPABILITY` over a `PROJECT` scoped `PROJECT` as an
*activation grant basis* for any capability in `.grants`. A ceiling decision
left `VALID` would therefore both bound the ceiling and confer everything in
it, collapsing the two-step containment `AX-4` rests on.

Nothing here provisions through `store.put_project`. A test that did would be
asserting against the very bypass `B1` names (GR31-PLAN-001, refusal
conditions).

Every refusal is asserted with `match=` (`CLAUDE.md` Tooling, `F04-002`): a
bare `pytest.raises` accepts whichever guard fires first, and several guards
exercised here raise the same class over the same call.
"""

from __future__ import annotations

from dataclasses import asdict

import pytest

from gruntime.authority import REGISTER
from gruntime.controller import Controller, CreationResponse
from gruntime.decision import decision_content_hash
from gruntime.errors import CapabilityDenied, IntegrityViolation, PolicyDenied
from gruntime.models import (
    Budget,
    DecisionKind,
    DecisionScope,
    DecisionState,
    DecisionSubjectKind,
    GovernanceMode,
)

from genesis_support import CREATE, DECLINE, OWNER, accepting, create_project

# --- the shape of a provisioned pilot project -------------------------------

#: The ceiling the first supervised pilot needs. `secret.read` is in it because
#: the inference relay is opened under it; it is never a worker capability.
PILOT_CEILING = frozenset({
    "fs.read", "fs.write", "commit.propose", "validation.request",
    "proc.exec.validation", "net.egress.allowlist", "secret.read",
})

PILOT_BUDGET = Budget(7200000, 1000, 1000.0, 1000, 1000, 1000)

#: A capability only a `HUMAN_DECISION` can grant and that `IMPLEMENTER` may
#: hold, so an activation over it has exactly one possible grantor. `T4` needs
#: that: a capability with a `ROLE_DEFAULT` fallback would be granted anyway
#: and would hide whether the consumed decision was refused as a basis.
HUMAN_GRANTED_ONLY = "net.egress.allowlist"


# --- helpers ----------------------------------------------------------------


def supervised_project(h, *, slug="gr-31", workspace=None, controller=None):
    """A project created the conforming way, and provisioned with nothing.

    This is the state `B1` is about: created, started, observed, and unable to
    activate anything at all.
    """
    root = workspace or h.repo_dir
    if not (h.repo_dir / ".git").exists():
        h.init_repo()
    if controller is not None:
        return create_project(controller, name="GR-31", slug=slug,
                              workspace_root=str(root), approved_by=OWNER)
    with h.controller(with_repo=True) as c:
        project_id = create_project(c, name="GR-31", slug=slug,
                                    workspace_root=str(root), approved_by=OWNER)
        c.start(project_id)
        c.take_snapshot(project_id)
    return project_id


def owner_decision(c, project_id, *, kind, subject_kind=DecisionSubjectKind.PROJECT,
                   subject_id=None, scope=DecisionScope.PROJECT, grants=(),
                   decided_by=OWNER, signature=None, chosen="yes"):
    """Record one real `HumanDecision`. Never a fabricated row."""
    return c.record_decision(
        project_id,
        decision_kind=kind,
        subject_kind=subject_kind,
        subject_id=subject_id if subject_id is not None else project_id,
        scope=scope,
        question="Authorize this governance act?",
        options_offered=(chosen, "no"),
        chosen=chosen,
        justification="GR-31 test decision",
        decided_by=decided_by,
        signature=signature,
        evidence_shown=(c.store.store_artifact(b"gr-31 evidence", media_type="text/plain"),),
        grants=frozenset(grants),
    )


def set_ceiling(c, project_id, ceiling=PILOT_CEILING):
    """Provision the ceiling through the governed operation, end to end."""
    decision = owner_decision(c, project_id, kind=DecisionKind.GRANT_CAPABILITY,
                              grants=ceiling)
    return c.set_capability_ceiling(project_id, ceiling=ceiling,
                                    decision_id=decision.decision_id), decision


def grant_budget(c, project_id, budget=PILOT_BUDGET):
    decision = owner_decision(c, project_id, kind=DecisionKind.EXTEND_BUDGET)
    return c.grant_project_budget(project_id, budget=budget,
                                  decision_id=decision.decision_id), decision


def run_confirmation(c, project_id):
    """The row 5-1 `CONFIRM`, so a supervised run can be allocated at all."""
    return owner_decision(c, project_id, kind=DecisionKind.APPROVE).decision_id


# --- T1: the blocker is real, and the fix is load-bearing -------------------


def test_activation_refused_without_provisioning(h):
    """A project created only via `create_project` can activate nothing.

    The refusal names the ceiling. This is `B1` stated as a test: without the
    two operations below, the conforming creation path produces a project that
    is inert, and every existing test hid that by writing the row itself.
    """
    project = supervised_project(h, slug="gr31-t1")
    with h.controller(with_repo=True) as c:
        assert c.store.get_project(project).capability_ceiling == frozenset()
        assert c.store.get_project(project).budget == Budget()
        run = Controller.open_run(c, project, confirmation_id=run_confirmation(c, project))
        contract = c.author_contract(_contract_document(c, project, run))

        # Both bounds are unset, and both refuse. The budget is asked first
        # (`guard:gr06_budget_ceiling` precedes `guard:gr06_activation_ceiling`),
        # so the ceiling refusal is only reachable once the budget is granted —
        # which is itself the point: an unprovisioned project fails every bound
        # a contract is resolved against, not just one.
        with pytest.raises(PolicyDenied, match="XC-10: contract budget exceeds"):
            c.activate_contract(contract.contract_id, run)

        grant_budget(c, project)
        with pytest.raises(PolicyDenied, match="XC-8: request outside ceiling"):
            c.activate_contract(contract.contract_id, run)
        assert c.store.get_project(project).capability_ceiling == frozenset()


def test_provisioned_project_can_activate(h):
    """The same project, provisioned through the two governed operations.

    No `store.put_project`. This is the acceptance criterion `B1` is closed
    by: the conforming path now reaches an activation.
    """
    project = supervised_project(h, slug="gr31-t1b")
    with h.controller(with_repo=True) as c:
        set_ceiling(c, project)
        grant_budget(c, project)
        project_row = c.store.get_project(project)
        assert project_row.capability_ceiling == PILOT_CEILING
        assert project_row.budget == PILOT_BUDGET

        run = Controller.open_run(c, project, confirmation_id=run_confirmation(c, project))
        contract = c.author_contract(_contract_document(c, project, run))
        approval = owner_decision(c, project, kind=DecisionKind.APPROVE,
                                  subject_kind=DecisionSubjectKind.CONTRACT,
                                  subject_id=contract.contract_id)
        activation = c.activate_contract(contract.contract_id, run,
                                         approval_id=approval.decision_id)
        assert "fs.write" in activation.granted_capabilities


def _contract_document(c, project_id, run_id, **overrides):
    from gr06_support import document
    overrides.setdefault("capability_request", ["fs.read", "fs.write", "commit.propose"])
    return document(project_id, c.store.get_run(run_id).stage_id, **overrides)


# --- T2: every conjunct of the ceiling decision -----------------------------


def test_ceiling_requires_valid_decision(h):
    """Each conjunct of `guard:gr31_ceiling_decision`, refused on its own.

    `project.ceiling.set` is a `HUMAN`-class capability: the only thing that
    exercises it is a live decision by a named human. The variants below walk
    the ways a record can fail to be that.
    """
    project = supervised_project(h, slug="gr31-t2")
    with h.controller(with_repo=True) as c:
        cited = "live GRANT_CAPABILITY by an authenticated, named human"

        # No decision at all.
        with pytest.raises(CapabilityDenied, match=cited):
            c.set_capability_ceiling(project, ceiling=PILOT_CEILING, decision_id=None)

        # APPROVE where GRANT_CAPABILITY is what the act is.
        approve = owner_decision(c, project, kind=DecisionKind.APPROVE)
        with pytest.raises(CapabilityDenied, match=cited):
            c.set_capability_ceiling(project, ceiling=PILOT_CEILING,
                                     decision_id=approve.decision_id)

        # A grant over some other subject.
        other = owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                               subject_id="not-this-project", grants=PILOT_CEILING)
        with pytest.raises(CapabilityDenied, match=cited):
            c.set_capability_ceiling(project, ceiling=PILOT_CEILING,
                                     decision_id=other.decision_id)

        # A grant scoped to a single action is not a project-wide bound.
        narrow = owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                                scope=DecisionScope.SINGLE_ACTION, grants=PILOT_CEILING)
        with pytest.raises(CapabilityDenied, match=cited):
            c.set_capability_ceiling(project, ceiling=PILOT_CEILING,
                                     decision_id=narrow.decision_id)

        # `grants` must be exactly the ceiling: a decision that named less
        # cannot install more, and one that named more installs what the human
        # was not asked about.
        partial = owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                                 grants=PILOT_CEILING - {"secret.read"})
        with pytest.raises(CapabilityDenied, match=cited):
            c.set_capability_ceiling(project, ceiling=PILOT_CEILING,
                                     decision_id=partial.decision_id)

        # A tampered content hash. `put_decision` updates only
        # `decision_state` on conflict, so the row is edited underneath the
        # runtime — which is the case `decision_hash` exists to catch.
        tampered = owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                                  grants=PILOT_CEILING)
        c.store.connection.execute(
            "UPDATE decisions SET decision_hash=? WHERE decision_id=?",
            ("sha256:" + "0" * 64, tampered.decision_id))
        assert (c.store.get_decision(tampered.decision_id).decision_hash
                != decision_content_hash(tampered))
        with pytest.raises(CapabilityDenied, match=cited):
            c.set_capability_ceiling(project, ceiling=PILOT_CEILING,
                                     decision_id=tampered.decision_id)

        # Every terminal state. None of them is authority (`HD-INV-4`).
        for state in (DecisionState.CONSUMED, DecisionState.EXPIRED,
                      DecisionState.STALE, DecisionState.VOID):
            spent = owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                                   grants=PILOT_CEILING)
            spent.decision_state = state
            c.store.put_decision(spent)
            with pytest.raises(CapabilityDenied, match=cited):
                c.set_capability_ceiling(project, ceiling=PILOT_CEILING,
                                         decision_id=spent.decision_id)

        # Nothing above moved the ceiling.
        assert c.store.get_project(project).capability_ceiling == frozenset()


def test_ceiling_decision_cannot_be_recorded_unauthenticated(h):
    """The remaining `HD-INV-1` variants are refused before a decision exists.

    A keyless human, an unauthenticated `auth_method`, a `SIGNATURE` with no
    signature and an uninformed approval are all refused by
    `record_decision` (`GR-29`, `HD-INV-2`, domain-model.md:710), so the
    provisioning boundary can never be handed one. Asserted here rather than
    assumed: the predicate still tests for them, and this is what makes that
    defence-in-depth rather than an untested branch.
    """
    from gruntime.models import ActorKind, ActorRef, AuthMethod

    project = supervised_project(h, slug="gr31-t2b")
    with h.controller(with_repo=True) as c:
        keyless = ActorRef(actor_kind=ActorKind.HUMAN, actor_id="owner@example.invalid",
                           auth_method=AuthMethod.SESSION, principal_key_id=None)
        with pytest.raises(IntegrityViolation, match="must name the principal key"):
            owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                           grants=PILOT_CEILING, decided_by=keyless)

        unauthenticated = ActorRef(actor_kind=ActorKind.HUMAN, actor_id="owner@example.invalid",
                                   auth_method=AuthMethod.NONE, principal_key_id="key-owner")
        with pytest.raises(IntegrityViolation, match="unauthenticated authority"):
            owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                           grants=PILOT_CEILING, decided_by=unauthenticated)

        signer = ActorRef(actor_kind=ActorKind.HUMAN, actor_id="signer@example.invalid",
                          auth_method=AuthMethod.SIGNATURE, principal_key_id="key-signer")
        with pytest.raises(IntegrityViolation, match="auth_method=SIGNATURE requires the signature"):
            owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                           grants=PILOT_CEILING, decided_by=signer)

        with pytest.raises(IntegrityViolation, match="uninformed approval"):
            c.record_decision(project, decision_kind=DecisionKind.GRANT_CAPABILITY,
                              subject_kind=DecisionSubjectKind.PROJECT, subject_id=project,
                              scope=DecisionScope.PROJECT, question="?",
                              options_offered=("yes",), chosen="yes", justification="j",
                              decided_by=OWNER, evidence_shown=(), grants=PILOT_CEILING)


# --- T3: the ceiling bounds the register ------------------------------------


def test_ceiling_entries_must_be_registered(h):
    """An unregistered identifier is not a capability and cannot be a bound.

    `_append` does not validate `capability_used` against the register, so a
    ceiling carrying an invented string would let a later activation cite an
    identifier that names nothing — the unbacked label `F03-003` condemned.
    """
    project = supervised_project(h, slug="gr31-t3")
    with h.controller(with_repo=True) as c:
        invented = frozenset({"fs.read", "fs.teleport"})
        decision = owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                                  grants=invented)
        with pytest.raises(PolicyDenied, match="name nothing the register defines"):
            c.set_capability_ceiling(project, ceiling=invented,
                                     decision_id=decision.decision_id)
        assert c.store.get_project(project).capability_ceiling == frozenset()
        assert "fs.teleport" not in REGISTER


# --- T4: the collision consumption closes -----------------------------------


def test_ceiling_decision_cannot_also_grant(h):
    """One decision bounds the ceiling; it does not also confer it.

    `human_covers` accepts a `GRANT_CAPABILITY` over `PROJECT` scoped
    `PROJECT` as an activation grant basis for any capability in `.grants`.
    Without the consumption inside `set_capability_ceiling`'s transaction, the
    very decision that set the bound would also hand out everything inside it
    and `AX-4`'s two-step containment would be one step.

    `net.egress.allowlist` is the probe because `HUMAN_DECISION` is its only
    admissible grantor here: a capability with a `ROLE_DEFAULT` fallback would
    be granted regardless and would prove nothing.
    """
    project = supervised_project(h, slug="gr31-t4")
    with h.controller(with_repo=True) as c:
        _, ceiling_decision = set_ceiling(c, project)
        grant_budget(c, project)

        assert (c.store.get_decision(ceiling_decision.decision_id).decision_state
                is DecisionState.CONSUMED), "the ceiling decision must be spent by provisioning"

        run = Controller.open_run(c, project, confirmation_id=run_confirmation(c, project))
        contract = c.author_contract(_contract_document(
            c, project, run,
            capability_request=["fs.read", "fs.write", "commit.propose", HUMAN_GRANTED_ONLY]))
        approval = owner_decision(c, project, kind=DecisionKind.APPROVE,
                                  subject_kind=DecisionSubjectKind.CONTRACT,
                                  subject_id=contract.contract_id)

        # Presenting the spent ceiling decision as the grant basis.
        activation = c.activate_contract(contract.contract_id, run,
                                         decision_ids=[ceiling_decision.decision_id],
                                         approval_id=approval.decision_id)
        assert HUMAN_GRANTED_ONLY not in activation.granted_capabilities
        assert activation.denied_capabilities[HUMAN_GRANTED_ONLY] == "NO_GRANTOR"


def test_a_separate_grant_decision_confers_what_the_ceiling_bounds(h):
    """The other half of `T4`: activation needs its own, different decision."""
    project = supervised_project(h, slug="gr31-t4b")
    with h.controller(with_repo=True) as c:
        set_ceiling(c, project)
        grant_budget(c, project)
        run = Controller.open_run(c, project, confirmation_id=run_confirmation(c, project))
        contract = c.author_contract(_contract_document(
            c, project, run,
            capability_request=["fs.read", "fs.write", "commit.propose", HUMAN_GRANTED_ONLY]))
        grant = owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                               grants=[HUMAN_GRANTED_ONLY])
        approval = owner_decision(c, project, kind=DecisionKind.APPROVE,
                                  subject_kind=DecisionSubjectKind.CONTRACT,
                                  subject_id=contract.contract_id)
        activation = c.activate_contract(contract.contract_id, run,
                                         decision_ids=[grant.decision_id],
                                         approval_id=approval.decision_id)
        assert HUMAN_GRANTED_ONLY in activation.granted_capabilities


# --- T5: budget, initial grant only -----------------------------------------


def test_budget_initial_grant_only(h):
    """`budget.grant` sets the initial `Budget`; raising one is `budget.extend`.

    The register's verb for `budget.grant` is "set initial Budget". Extension
    is a different capability and a different act, and this operation refuses
    to serve as both rather than quietly becoming the only budget path.
    """
    project = supervised_project(h, slug="gr31-t5")
    with h.controller(with_repo=True) as c:
        granted, _ = grant_budget(c, project)
        assert c.store.get_project(project).budget == PILOT_BUDGET == granted

        again = owner_decision(c, project, kind=DecisionKind.EXTEND_BUDGET)
        with pytest.raises(PolicyDenied, match="already holds"):
            c.grant_project_budget(project, budget=Budget(1, 1, 1.0, 1, 1, 1),
                                   decision_id=again.decision_id)
        assert c.store.get_project(project).budget == PILOT_BUDGET
        assert (c.store.get_decision(again.decision_id).decision_state
                is DecisionState.VALID), "a refused grant spends nothing"


def test_budget_requires_valid_decision(h):
    """`guard:gr31_budget_decision`, over the same conjuncts as the ceiling."""
    project = supervised_project(h, slug="gr31-t5b")
    with h.controller(with_repo=True) as c:
        cited = "live EXTEND_BUDGET by an authenticated, named human"

        with pytest.raises(CapabilityDenied, match=cited):
            c.grant_project_budget(project, budget=PILOT_BUDGET, decision_id=None)

        # `GRANT_CAPABILITY` is the ceiling's act, not the budget's.
        wrong_kind = owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                                    grants=PILOT_CEILING)
        with pytest.raises(CapabilityDenied, match=cited):
            c.grant_project_budget(project, budget=PILOT_BUDGET,
                                   decision_id=wrong_kind.decision_id)

        narrow = owner_decision(c, project, kind=DecisionKind.EXTEND_BUDGET,
                                scope=DecisionScope.SINGLE_ACTION)
        with pytest.raises(CapabilityDenied, match=cited):
            c.grant_project_budget(project, budget=PILOT_BUDGET,
                                   decision_id=narrow.decision_id)

        elsewhere = owner_decision(c, project, kind=DecisionKind.EXTEND_BUDGET,
                                   subject_id="not-this-project")
        with pytest.raises(CapabilityDenied, match=cited):
            c.grant_project_budget(project, budget=PILOT_BUDGET,
                                   decision_id=elsewhere.decision_id)

        spent = owner_decision(c, project, kind=DecisionKind.EXTEND_BUDGET)
        spent.decision_state = DecisionState.CONSUMED
        c.store.put_decision(spent)
        with pytest.raises(CapabilityDenied, match=cited):
            c.grant_project_budget(project, budget=PILOT_BUDGET,
                                   decision_id=spent.decision_id)

        assert c.store.get_project(project).budget == Budget()


# --- T6: neither operation runs against a project mid-genesis ---------------


def test_provisioning_refused_mid_genesis(h):
    """Both operations refuse while the creation transaction is open.

    `AX-17` is one transaction of four ordered events, and a presenter is code
    the runtime does not own running inside it. Provisioning from there would
    durably mutate a project no commit has yet established, and would append a
    fifth event inside the four-event witness (`GR27-R4`, `GR27-R5`).
    """
    h.init_repo()
    seen = {}

    def provisioning_presenter(observation):
        with pytest.raises(IntegrityViolation, match="mid-genesis") as ceiling:
            controller.set_capability_ceiling(observation.project_id,
                                              ceiling=PILOT_CEILING, decision_id=None)
        with pytest.raises(IntegrityViolation, match="mid-genesis") as budget:
            controller.grant_project_budget(observation.project_id,
                                            budget=PILOT_BUDGET, decision_id=None)
        seen["ceiling"] = str(ceiling.value)
        seen["budget"] = str(budget.value)
        return CreationResponse(snapshot_id=observation.snapshot_id, chosen=CREATE)

    with h.controller(with_repo=True) as controller:
        project = create_project(controller, name="GR-31", slug="gr31-t6",
                                 workspace_root=str(h.repo_dir), approved_by=OWNER,
                                 present=provisioning_presenter)
        assert "capability ceiling" in seen["ceiling"]
        assert "budget" in seen["budget"]
        # Genesis still committed exactly its four events, and neither
        # operation left anything behind.
        row = controller.store.get_project(project)
        assert row.capability_ceiling == frozenset() and row.budget == Budget()
        assert row.event_seq == 3
        controller.store.verify_chain(project)


# --- T7: both operations are atomic -----------------------------------------


@pytest.mark.parametrize("operation", ["ceiling", "budget"])
def test_provisioning_is_atomic(h, monkeypatch, operation):
    """A failure after the append leaves neither the event nor the field.

    And the decision is still `VALID`: an act that did not happen spends
    nothing. Without the transaction, the audit would carry a `ceiling_set`
    for a ceiling that is not installed and a human's decision would have been
    consumed by nothing.
    """
    project = supervised_project(h, slug=f"gr31-t7-{operation}")
    with h.controller(with_repo=True) as c:
        if operation == "ceiling":
            decision = owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                                      grants=PILOT_CEILING)
            call = lambda: c.set_capability_ceiling(  # noqa: E731
                project, ceiling=PILOT_CEILING, decision_id=decision.decision_id)
            event_type = "project.ceiling_set"
        else:
            decision = owner_decision(c, project, kind=DecisionKind.EXTEND_BUDGET)
            call = lambda: c.grant_project_budget(  # noqa: E731
                project, budget=PILOT_BUDGET, decision_id=decision.decision_id)
            event_type = "project.budget_granted"

        boom = RuntimeError("store failed after the append")

        def explode(*args, **kwargs):
            raise boom

        monkeypatch.setattr(c.store, "put_project", explode)
        with pytest.raises(RuntimeError, match="store failed after the append"):
            call()
        monkeypatch.undo()

        row = c.store.get_project(project)
        assert row.capability_ceiling == frozenset() and row.budget == Budget()
        assert not [e for e in c.store.list_events(project) if e.event_type == event_type]
        assert (c.store.get_decision(decision.decision_id).decision_state
                is DecisionState.VALID)
        c.store.verify_chain(project)


# --- the events these operations leave behind -------------------------------


def test_provisioning_events_cite_their_capability_and_decision(h):
    """`G-4`: one `CapabilityId` per state-changing operation, and the human.

    The ceiling event names `project.ceiling.set` — the one register entry
    `Q3a` admits — and the budget event names `budget.grant`. Each cites the
    decision that authorized it on `authority_ref`, and each is held by the
    human who decided rather than by the runtime that wrote it (`AX-15`).
    """
    project = supervised_project(h, slug="gr31-events")
    with h.controller(with_repo=True) as c:
        _, ceiling_decision = set_ceiling(c, project)
        _, budget_decision = grant_budget(c, project)
        events = {e.event_type: e for e in c.store.list_events(project)}

        ceiling_event = events["project.ceiling_set"]
        assert ceiling_event.capability_used == "project.ceiling.set"
        assert ceiling_event.authority_ref == ceiling_decision.decision_id
        assert ceiling_event.actor.actor_id == OWNER.actor_id

        budget_event = events["project.budget_granted"]
        assert budget_event.capability_used == "budget.grant"
        assert budget_event.authority_ref == budget_decision.decision_id

        assert REGISTER["project.ceiling.set"] == ("HUMAN", ("HUMAN_DECISION",))
        c.store.verify_chain(project)


def test_provisioning_decisions_do_not_go_stale_on_the_next_snapshot(h):
    """Provisioning is a governance act, not a statement about the tree.

    Neither `GRANT_CAPABILITY` nor `EXTEND_BUDGET` is in
    `SNAPSHOT_BOUND_KINDS`, and `PROJECT` is not in
    `SNAPSHOT_BOUND_SUBJECTS`, so a provisioning decision recorded before an
    observation is still authority after it. That is why `GRANT_CAPABILITY` is
    the right kind here and `APPROVE` is not.
    """
    project = supervised_project(h, slug="gr31-stale")
    with h.controller(with_repo=True) as c:
        decision = owner_decision(c, project, kind=DecisionKind.GRANT_CAPABILITY,
                                  grants=PILOT_CEILING)
        assert decision.snapshot_bound is False
        (h.repo_dir / "moved.txt").write_text("moved\n", encoding="utf-8")
        from gr03_support import git
        git(h.repo_dir, "add", "-A")
        git(h.repo_dir, "commit", "-q", "-m", "reality moved")
        c.take_snapshot(project)
        assert (c.store.get_decision(decision.decision_id).decision_state
                is DecisionState.VALID)
        c.set_capability_ceiling(project, ceiling=PILOT_CEILING,
                                 decision_id=decision.decision_id)
        assert c.store.get_project(project).capability_ceiling == PILOT_CEILING


def test_a_declined_creation_provisions_nothing(h):
    """Guards the fixture, not the runtime: `supervised_project` must create."""
    h.init_repo()
    with h.controller(with_repo=True) as c:
        with pytest.raises(IntegrityViolation, match="the human declined"):
            create_project(c, name="GR-31", slug="gr31-declined",
                           workspace_root=str(h.repo_dir), approved_by=OWNER,
                           present=accepting(chosen=DECLINE))
