"""The recovery sequence: decide what already happened, and write it down.

Design basis: worker_provider.md §6.1, transition-matrix §5 (the `RUN-INV-3`
barrier and its `recovery.reconcile` exemption), §7.4, evidence-model §3.2.1.

Runs once per controller start, after `project.controller_epoch` increments
and before any dispatch or apply on the affected runs.

No step here creates an invocation, a key, an attempt, a provider execution or
a repository mutation. `lookup` and the repository scan are the only outward
calls, and neither executes anything. The sequence only decides what already
happened — which is exactly why it is permitted under a barrier that forbids
everything else, and why it is the only thing that can clear that barrier.

Deciding and writing are kept apart: this module observes and the controller
transitions, because the controller owns every state transition. `run_recovery`
hands each observation to a `settle` callback and records what came back.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from .errors import ProviderUnavailable, GovernedRuntimeError
from .gate import AFTER_LOOKUP_BEFORE_RECEIPT, gate
from .models import CommitIntent, Id, ReconciliationState, WorkerInvocation
from .provider import (
    GovernedProvider,
    LookupAbsent,
    LookupFinished,
    LookupLive,
    LookupResult,
    ProviderError,
)
from .reconciliation import Observation, clears_barrier, requires_lookup


@dataclass
class RecoveryOutcome:
    """What one recovery pass settled, for the caller to audit."""

    project_id: Id
    epoch: int
    invocations_reconciled: Sequence[Id] = ()
    intents_reconciled: Sequence[Id] = ()
    escalations_raised: Sequence[Id] = ()
    unresolved: Sequence[Id] = field(default_factory=tuple)
    validations_reconciled: Sequence[Id] = ()


def validation_rerun_permitted(operation) -> bool:
    """Only explicitly repeatable, confined operations can be retried.

    This classifies an interrupted validation; recovery itself never executes
    it. Network effects are external even if a catalog author claims they are
    repeatable, so EXTERNAL always requires reconciliation by an operator.
    """
    if not operation.safe_to_rerun:  # guard:rerun_flag
        return False
    if operation.side_effect_class not in ('READ_ONLY', 'SANDBOX_WRITE'):  # guard:rerun_class
        return False
    return True


@dataclass(frozen=True)
class Resolution:
    """One record's observation plus the evidence the observation rests on.

    Carried to the controller so the adopting receipt cites what was actually
    seen, rather than being re-derived from a second look at the outside world.
    """

    observation: Observation
    lookup_result: Optional[LookupResult] = None
    revision_id: Optional[str] = None
    actual_tree_digest: Optional[str] = None
    parent_revision_ids: Sequence[str] = ()


@dataclass(frozen=True)
class Settlement:
    """What the controller wrote down for one record."""

    state: ReconciliationState
    escalation_id: Optional[Id] = None


def observe_lookup(result: LookupResult) -> Observation:
    """Map a `LookupResult` onto the observation row it satisfies.

    `FINISHED` → `FINISHED`, `ABSENT` → `ABSENT`, `LIVE` → `LIVE`. A `lookup`
    that errors or cannot decide for the key is `UNANSWERABLE`, which leaves
    the record unresolvable and escalates rather than permitting a replacement
    dispatch (`WP-16`).
    """
    if isinstance(result, LookupFinished):
        return Observation.FINISHED
    if isinstance(result, LookupAbsent):
        return Observation.ABSENT
    if isinstance(result, LookupLive):
        return Observation.LIVE
    return Observation.UNANSWERABLE


def observe_scan(
    intent: CommitIntent,
    *,
    matching_revisions: Sequence[str],
    tree_digests: Sequence[str],
    base_unchanged: bool,
) -> Observation:
    """Map a repository scan for `operation_token` onto its §7.4 row.

    One revision with a matching tree is `TOKEN_MATCHED`; one with a differing
    tree is `TOKEN_MATCHED_DIVERGED`; none while the base still matches is
    `NO_TOKEN_BASE_UNCHANGED`. Anything else — several revisions carrying the
    token, or none while the workspace has moved — is `AMBIGUOUS`
    (`CM-INV-3`). Tree equality alone never establishes which revision
    fulfilled which intent.
    """
    if len(matching_revisions) == 1:
        digest = tree_digests[0] if tree_digests else None
        if digest == intent.expected_tree_digest:
            return Observation.TOKEN_MATCHED
        return Observation.TOKEN_MATCHED_DIVERGED
    if not matching_revisions and base_unchanged:
        return Observation.NO_TOKEN_BASE_UNCHANGED
    return Observation.AMBIGUOUS


def reconcile_invocation(
    invocation: WorkerInvocation,
    *,
    provider: GovernedProvider,
    project_epoch: int,
) -> Resolution:
    """Resolve one invocation by `lookup(idempotency_key)` alone.

    The stored `request_ref` bytes are never re-sent and context is never
    rebuilt: a rebuilt bundle yields a different `context_digest`, a different
    `idempotency_key`, and therefore a second execution (`WP-15`, `WP-16`).

    The gate between the answer and the receipt is a real seam, not a test
    hook: a controller that dies here has learned the outcome and not yet
    recorded it, and the next start must reach the same answer from the same
    key.
    """
    try:
        result = provider.lookup(invocation.idempotency_key)
    except (ProviderError, ProviderUnavailable):
        return Resolution(observation=Observation.UNANSWERABLE)
    gate(AFTER_LOOKUP_BEFORE_RECEIPT)
    return Resolution(observation=observe_lookup(result), lookup_result=result)


def reconcile_intent(
    intent: CommitIntent,
    *,
    repo,
    project_epoch: int,
) -> Resolution:
    """Resolve one commit intent by scanning for its `operation_token`.

    Never by re-applying it: a blind retry is not idempotent and would land
    the same change twice (`CM-INV-2`, transition-matrix §9.3).
    """
    if repo is None:
        return Resolution(observation=Observation.UNANSWERABLE)
    revisions = repo.find_by_token(intent.operation_token)
    digests = [repo.tree_digest(revision) for revision in revisions]
    observation = observe_scan(
        intent,
        matching_revisions=revisions,
        tree_digests=digests,
        base_unchanged=repo.head_revision() == intent.base_revision_id,
    )
    revision_id = revisions[0] if len(revisions) == 1 else None
    return Resolution(
        observation=observation,
        revision_id=revision_id,
        actual_tree_digest=digests[0] if len(digests) == 1 else None,
        parent_revision_ids=(
            tuple(repo.parents(revision_id)) if revision_id is not None else ()
        ),
    )


def run_recovery(
    project_id: Id,
    *,
    store,
    provider: GovernedProvider,
    repo: Optional[object] = None,
    settle: Optional[Callable[[object, Resolution], Settlement]] = None,
    provider_for=None,
) -> RecoveryOutcome:
    """Run the full §6.1 sequence for one project.

    Selects every `WorkerInvocation` and `CommitIntent` whose
    `controller_epoch` precedes the project's, and resolves the ones the
    single derivation (transition-matrix §5.1) reports as still pending —
    settled records are not looked up again, which is what keeps a repeated
    restart from repeating a query the record already answered.

    `settle` performs the transition and returns the state the controller
    wrote; without it the pass observes and records nothing.
    """
    epoch = store.get_project(project_id).controller_epoch
    invocations_reconciled: list[Id] = []
    intents_reconciled: list[Id] = []
    escalations: list[Id] = []
    unresolved: list[Id] = []

    for invocation in store.list_unreconciled_invocations(project_id):
        if not requires_lookup(invocation.reconciliation_state):
            continue
        try:
            resolution = reconcile_invocation(
                invocation, provider=provider_for(invocation) if provider_for else provider, project_epoch=epoch
            )
        except (GovernedRuntimeError, ProviderError):
            resolution = Resolution(observation=Observation.UNANSWERABLE)
        if settle is None:
            continue
        settlement = settle(invocation, resolution)
        if settlement.escalation_id is not None:
            escalations.append(settlement.escalation_id)
        if clears_barrier(settlement.state):
            invocations_reconciled.append(invocation.invocation_id)
        else:
            unresolved.append(invocation.invocation_id)

    for intent in store.list_unreconciled_intents(project_id):
        if not requires_lookup(intent.reconciliation_state):
            continue
        resolution = reconcile_intent(intent, repo=repo, project_epoch=epoch)
        if settle is None:
            continue
        settlement = settle(intent, resolution)
        if settlement.escalation_id is not None:
            escalations.append(settlement.escalation_id)
        if clears_barrier(settlement.state):
            intents_reconciled.append(intent.intent_id)
        else:
            unresolved.append(intent.intent_id)

    return RecoveryOutcome(
        project_id=project_id,
        epoch=epoch,
        invocations_reconciled=tuple(invocations_reconciled),
        intents_reconciled=tuple(intents_reconciled),
        escalations_raised=tuple(escalations),
        unresolved=tuple(unresolved),
    )
