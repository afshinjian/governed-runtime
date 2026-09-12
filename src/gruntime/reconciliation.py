"""The one reconciliation-state derivation.

Design basis: transition-matrix §5.1. `WorkerInvocation.reconciliation_state`
and `CommitIntent.reconciliation_state` are derived here and nowhere else;
§7.2, §7.4, `worker_provider.md` §6.1 and `authority-matrix.md` §6 refer here
rather than restating the table. No other module may name a member of
`ReconciliationState`.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from .models import ReconciliationState


class Observation(Enum):
    """What recovery observed for one record, under `recovery.reconcile`.

    The first four are the `lookup` answers plus the unanswerable case
    (`WP-16`); the last four are the repository-scan outcomes (§7.4). Both
    feed row 4 of the same table.
    """

    #: `lookup` returned `FINISHED(outcome)` — the outcome is established.
    FINISHED = "FINISHED"
    #: `lookup` returned `ABSENT` — nothing ran under the key.
    ABSENT = "ABSENT"
    #: `lookup` returned `LIVE(handle)` — the execution is still running.
    LIVE = "LIVE"
    #: `lookup` errored or cannot decide for this key.
    UNANSWERABLE = "UNANSWERABLE"
    #: Exactly one revision carries the token and its tree matches.
    TOKEN_MATCHED = "TOKEN_MATCHED"
    #: Exactly one revision carries the token and its tree differs.
    TOKEN_MATCHED_DIVERGED = "TOKEN_MATCHED_DIVERGED"
    #: No revision carries the token and the base still matches: nothing landed.
    NO_TOKEN_BASE_UNCHANGED = "NO_TOKEN_BASE_UNCHANGED"
    #: More than one revision carries the token, or none while the base moved.
    AMBIGUOUS = "AMBIGUOUS"


def derive_reconciliation_state(
    *,
    record_epoch: int,
    project_epoch: int,
    status_terminal: bool,
    observation: Optional[Observation] = None,
    prior: Optional[ReconciliationState] = None,
) -> ReconciliationState:
    """Derive a record's `reconciliation_state` — transition-matrix §5.1.

    This is the **single** derivation shared by `WorkerInvocation` and
    `CommitIntent`; it is the §5.1 table itself, not a paraphrase of it, and
    no second implementation exists.

    The four rows, in precedence order:

    1. `prior` is already one of the row-4 outcomes — it is terminal and takes
       precedence: a reconciled record never reverts to `NOT_REQUIRED`,
       whatever its epoch or status becomes afterwards.
    2. `observation` is present — recovery ran under `recovery.reconcile`, and
       the state is `ADOPTED`, `ORPHANED` or `UNRESOLVABLE` per what it saw.
       `ADOPTED` means the outcome was *established*, not that it succeeded.
    3. `record_epoch == project_epoch` — `NOT_REQUIRED`.
    4. `record_epoch < project_epoch` — `PENDING` for every non-terminal
       status of either entity without exception, `NOT_REQUIRED` for a
       terminal one.

    A `record_epoch` greater than `project_epoch` is a record from the future:
    `IntegrityViolation`, never a state.
    """
    raise NotImplementedError


def clears_barrier(state: ReconciliationState) -> bool:
    """True iff `state` lets its run initiate new external effects.

    `RUN-INV-3` (transition-matrix §5): `NOT_REQUIRED`, `ADOPTED` and
    `ORPHANED` clear the barrier; `PENDING` and `UNRESOLVABLE` hold it.
    """
    raise NotImplementedError


def requires_lookup(state: ReconciliationState) -> bool:
    """True iff the record still has to be resolved against the outside world.

    Only `PENDING`. `UNRESOLVABLE` is not retried by lookup — it escalates
    (`Escalation(RECOVERY_AMBIGUITY)`) — and the other three are settled.
    """
    raise NotImplementedError
