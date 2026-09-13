"""Every row of transition-matrix §9.3, refused by the controller.

§9.3 forbids *operations*, not edges: acts on authority and evidence that no
capability, decision, or governance mode authorizes, for the actor kinds each
row names. One test per row, named for the row, refused under both profiles
with a saturated context.

The actor kind is the whole of several rows — minting a `ValidationReceipt` is
the runtime's job and the worker's forgery — so a last test checks that the
prohibition is keyed to the actor and not to the act.

Design basis: transition-matrix.md §9.3; authority-matrix.md §2 (`NEVER` class)
and §6 (enforcement points).
"""

from __future__ import annotations

from gr02_support import (  # noqa: F401  (the `gov` fixture is used by name)
    gov,
    propose,
    refuse_operation,
)

from gruntime.models import ActorKind
from gruntime.policy import Reason
from gruntime.transitions import Axis, Operation

HUMAN = ActorKind.HUMAN
WORKER = ActorKind.WORKER
RUNTIME = ActorKind.RUNTIME
ADAPTER = ActorKind.ADAPTER


def test_9_3_01_worker_mints_a_validation_receipt(gov):
    refuse_operation(gov, Operation.MINT_VALIDATION_RECEIPT, WORKER, row="9.3-1")


def test_9_3_02_worker_mints_a_commit_receipt(gov):
    refuse_operation(gov, Operation.MINT_COMMIT_RECEIPT, WORKER, row="9.3-2")


def test_9_3_03_worker_or_adapter_creates_a_reality_snapshot(gov):
    for kind in (WORKER, ADAPTER):
        refuse_operation(gov, Operation.CREATE_REALITY_SNAPSHOT, kind, row="9.3-3")


def test_9_3_04_non_human_creates_a_human_decision(gov):
    for kind in (RUNTIME, WORKER, ADAPTER):
        refuse_operation(gov, Operation.CREATE_HUMAN_DECISION, kind, row="9.3-4")


def test_9_3_05_human_decision_without_authentication(gov):
    refuse_operation(
        gov, Operation.CREATE_HUMAN_DECISION_UNAUTHENTICATED, HUMAN, row="9.3-5"
    )


def test_9_3_06_human_decision_with_empty_evidence_shown(gov):
    refuse_operation(
        gov, Operation.CREATE_HUMAN_DECISION_WITHOUT_EVIDENCE, HUMAN, row="9.3-6"
    )


def test_9_3_07_replay_a_consumed_decision_nonce(gov):
    for kind in ActorKind:
        refuse_operation(
            gov, Operation.REPLAY_CONSUMED_DECISION_NONCE, kind, row="9.3-7"
        )


def test_9_3_08_mutate_a_field_of_an_active_contract(gov):
    refuse_operation(gov, Operation.MUTATE_ACTIVE_CONTRACT, RUNTIME, row="9.3-8")


def test_9_3_09_widen_effective_capabilities_in_place(gov):
    refuse_operation(
        gov, Operation.WIDEN_EFFECTIVE_CAPABILITIES, RUNTIME, row="9.3-9"
    )


def test_9_3_10_grant_a_capability_outside_the_ceiling(gov):
    for kind in (HUMAN, RUNTIME):
        refuse_operation(gov, Operation.GRANT_OUTSIDE_CEILING, kind, row="9.3-10")


def test_9_3_11_worker_delegates_a_capability_it_does_not_hold(gov):
    refuse_operation(gov, Operation.DELEGATE_UNHELD_CAPABILITY, WORKER, row="9.3-11")


def test_9_3_12_rewrite_or_delete_an_audit_event(gov):
    for kind in ActorKind:
        refuse_operation(gov, Operation.REWRITE_AUDIT_EVENT, kind, row="9.3-12")


def test_9_3_13_write_observed_satisfaction_directly(gov):
    for kind in (WORKER, ADAPTER, HUMAN):
        refuse_operation(gov, Operation.WRITE_OBSERVED_SATISFACTION, kind, row="9.3-13")


def test_9_3_14_let_declared_status_gate_a_transition(gov):
    for kind in ActorKind:
        refuse_operation(gov, Operation.GATE_ON_DECLARED_STATUS, kind, row="9.3-14")


def test_9_3_15_execute_a_command_spec_that_differs_from_the_contract(gov):
    refuse_operation(
        gov, Operation.EXECUTE_DIVERGENT_COMMAND_SPEC, RUNTIME, row="9.3-15"
    )


def test_9_3_16_worker_writes_outside_scope(gov):
    refuse_operation(gov, Operation.WRITE_OUTSIDE_SCOPE, WORKER, row="9.3-16")


def test_9_3_17_self_review_satisfies_an_independent_spec(gov):
    refuse_operation(
        gov, Operation.SELF_REVIEW_FOR_INDEPENDENT_SPEC, RUNTIME, row="9.3-17"
    )


def test_9_3_18_waive_a_criterion_that_is_not_waivable(gov):
    refuse_operation(gov, Operation.WAIVE_NON_WAIVABLE_CRITERION, HUMAN, row="9.3-18")


def test_9_3_19_runtime_resolves_a_non_auto_resolvable_escalation(gov):
    refuse_operation(
        gov, Operation.RESOLVE_ESCALATION_WITHOUT_DECISION, RUNTIME, row="9.3-19"
    )


def test_9_3_20_set_autonomous_mode_without_a_human_decision(gov):
    for kind in ActorKind:
        refuse_operation(
            gov, Operation.SET_AUTONOMOUS_WITHOUT_DECISION, kind, row="9.3-20"
        )


def test_9_3_21_apply_an_intent_whose_base_revision_is_stale(gov):
    refuse_operation(gov, Operation.APPLY_INTENT_WITH_STALE_BASE, RUNTIME, row="9.3-21")


def test_9_3_22_satisfy_a_stage_from_an_incomplete_snapshot(gov):
    refuse_operation(
        gov, Operation.SATISFY_FROM_INCOMPLETE_SNAPSHOT, RUNTIME, row="9.3-22"
    )


def test_9_3_23_grant_a_capability_with_no_admissible_grantor(gov):
    refuse_operation(
        gov, Operation.GRANT_WITHOUT_ADMISSIBLE_GRANTOR, RUNTIME, row="9.3-23"
    )


def test_9_3_24_activate_without_a_grant_basis_for_every_capability(gov):
    refuse_operation(gov, Operation.ACTIVATE_WITHOUT_GRANT_BASIS, RUNTIME, row="9.3-24")


def test_9_3_25_dispatch_for_a_run_holding_an_unreconciled_operation(gov):
    refuse_operation(gov, Operation.DISPATCH_UNDER_BARRIER, RUNTIME, row="9.3-25")


def test_9_3_26_replace_an_unreconciled_invocation(gov):
    refuse_operation(
        gov, Operation.REPLACE_UNRECONCILED_INVOCATION, RUNTIME, row="9.3-26"
    )


def test_9_3_27_resubmit_a_request_ref_to_reconcile(gov):
    refuse_operation(gov, Operation.RESUBMIT_REQUEST_REF, RUNTIME, row="9.3-27")


def test_9_3_28_dispatch_to_a_provider_without_lookup(gov):
    refuse_operation(gov, Operation.DISPATCH_WITHOUT_LOOKUP, RUNTIME, row="9.3-28")


def test_9_3_29_mutate_the_repository_before_the_token_is_durable(gov):
    refuse_operation(gov, Operation.MUTATE_BEFORE_TOKEN_DURABLE, RUNTIME, row="9.3-29")


def test_9_3_30_reapply_an_intent_in_applying_without_reconciling(gov):
    refuse_operation(gov, Operation.REAPPLY_UNRECONCILED_INTENT, RUNTIME, row="9.3-30")


def test_9_3_31_cite_a_human_decision_that_is_not_valid(gov):
    for kind in ActorKind:
        refuse_operation(gov, Operation.CITE_INVALID_DECISION, kind, row="9.3-31")


def test_9_3_32_non_kernel_actor_mints_a_review_attestation(gov):
    for kind in (WORKER, ADAPTER, HUMAN):
        refuse_operation(gov, Operation.MINT_REVIEW_ATTESTATION, kind, row="9.3-32")


def test_9_3_33_cite_a_review_directly_as_required_evidence(gov):
    for kind in ActorKind:
        refuse_operation(gov, Operation.CITE_REVIEW_AS_EVIDENCE, kind, row="9.3-33")


# --- the prohibition is keyed to the actor --------------------------------


def test_a_row_naming_an_actor_does_not_forbid_the_runtime_the_same_act(gov):
    """`mint ValidationReceipt` is illegal for a `WORKER`, not for the kernel.

    The kernel's minting is governed by `validation.attest` in §7.1, not by
    §9.3. The engine says so by not matching the row — and, since §9.3 is a
    prohibition list rather than an authorization, by still refusing an
    operation proposal it has no legal row for.
    """
    from gr02_support import context

    from gruntime.models import GovernanceMode

    resolution = gov.evaluate(
        propose(
            Axis.OPERATION,
            Operation.MINT_VALIDATION_RECEIPT.value,
            actor_kind=RUNTIME,
            operation=Operation.MINT_VALIDATION_RECEIPT,
        ),
        context(GovernanceMode.SUPERVISED),
    )
    assert resolution.reason is Reason.NOT_IN_GRAPH
