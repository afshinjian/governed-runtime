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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from .models import CommitIntent, Id, WorkerInvocation
from .provider import GovernedProvider, LookupResult
from .reconciliation import Observation


@dataclass
class RecoveryOutcome:
    """What one recovery pass settled, for the caller to audit."""

    project_id: Id
    epoch: int
    invocations_reconciled: Sequence[Id] = ()
    intents_reconciled: Sequence[Id] = ()
    escalations_raised: Sequence[Id] = ()
    unresolved: Sequence[Id] = field(default_factory=tuple)


def observe_lookup(result: LookupResult) -> Observation:
    """Map a `LookupResult` onto the observation row it satisfies.

    `FINISHED` → `FINISHED`, `ABSENT` → `ABSENT`, `LIVE` → `LIVE`. A `lookup`
    that errors or cannot decide for the key is `UNANSWERABLE`, which leaves
    the record unresolvable and escalates rather than permitting a replacement
    dispatch (`WP-16`).
    """
    raise NotImplementedError


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
    raise NotImplementedError


def reconcile_invocation(
    invocation: WorkerInvocation,
    *,
    provider: GovernedProvider,
    project_epoch: int,
) -> Observation:
    """Resolve one invocation by `lookup(idempotency_key)` alone.

    The stored `request_ref` bytes are never re-sent and context is never
    rebuilt: a rebuilt bundle yields a different `context_digest`, a different
    `idempotency_key`, and therefore a second execution (`WP-15`, `WP-16`).
    """
    raise NotImplementedError


def reconcile_intent(
    intent: CommitIntent,
    *,
    repo,
    project_epoch: int,
) -> Observation:
    """Resolve one commit intent by scanning for its `operation_token`.

    Never by re-applying it: a blind retry is not idempotent and would land
    the same change twice (`CM-INV-2`, transition-matrix §9.3).
    """
    raise NotImplementedError


def run_recovery(
    project_id: Id,
    *,
    store,
    provider: GovernedProvider,
    repo: Optional[object] = None,
) -> RecoveryOutcome:
    """Run the full §6.1 sequence for one project.

    Selects every `WorkerInvocation` and `CommitIntent` whose
    `controller_epoch` precedes the project's, derives each record's state
    through the single derivation (transition-matrix §5.1), resolves the
    pending ones by observation, and appends the receipt or the record that
    nothing happened — all under `recovery.reconcile`.
    """
    raise NotImplementedError
