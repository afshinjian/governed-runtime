# FINDINGS-07 — GR-29 independent bounded closure review

Baseline: `df7f0c7ded90b66093768e6f90b28b6c8c7a3483`, plus the reviewed,
uncommitted GR-29 implementation, tests, mutation runner and evidence record
in the working tree (`src/gruntime/controller.py`, `src/gruntime/decision.py`,
`src/gruntime/store.py`, `tests/test_gr23_creation_path.py`,
`tests/test_gr29_decision_principal_key.py`, `bin/check-gr29-mutations`,
`docs/evidence/gr29-mutations.json`).

| Property | Value |
|---|---|
| Record identifier | `FINDINGS-07` |
| Stage | `GR-29`: `F04-001` HumanDecision principal-key integrity |
| Record status | Independent bounded closure review recorded |
| Reviewer | independent GR-29 closure reviewer |
| Findings under review | `GR29-R01` (original severity **HIGH**, **blocking**); `GR29-R02` (original severity **LOW**, **nonblocking**) |
| Closure status | `GR29-R01` **CLOSED**; `GR29-R02` **CLOSED** |
| New direct findings | **NONE** |
| Full suite | **1303 passed** |
| Mutation verification | **21/21 KILLED** |
| Final verdict | **`GR29_CLOSURE_PASS`** |

## 1. Provenance and numbering

The committed general implementation-review sequence ends at
[FINDINGS-06:1](FINDINGS-06.md#L1); the next record under the existing
convention is `FINDINGS-07.md`. This record documents the disposition of an
independent bounded closure review already performed and reported to the
OWNER; it does not re-run that review. Per [review method](../../CLAUDE.md)
this record freezes findings and their closure statuses; it sets no owner
blocking disposition of its own, since both findings under review are
reported closed by the closure review it records.

## 2. `GR29-R01` — HIGH / blocking

`GR29-R01` found that `take_snapshot` publishes a new observation
(`_append_snapshot`, then `_publish_snapshot`) and only afterward derives
`HD-INV-4` staleness over every `HumanDecision`
([controller.py:1247](../../src/gruntime/controller.py#L1247) through
[controller.py:1252](../../src/gruntime/controller.py#L1252)). A malformed
row refused at hydration (`_decision_from_row`, behind `get_decision` and
`list_decisions`) aborted that derivation after publication. The project was
then left holding a reality nothing had been measured against: prior
approvals stayed `VALID` against a reality they should have been staled
against, `suspension` stayed `NONE`, and the `REALITY_DRIFT` escalation that
stage would have raised was never reached.

The recorded correction: `_suspend_uninterpreted_snapshot`
(`guard:snapshot_interpretation_suspends`,
[controller.py:1278](../../src/gruntime/controller.py#L1278)) raises an
`INTEGRITY_VIOLATION` escalation applying `SUSPENDED_BY_INTEGRITY`
(transition-matrix §4 row 4-7) and re-raises, before any caller sees the
failure. `SUSPENSION_GATE` gives `SUSPENDED_BY_INTEGRITY` and
`SUSPENDED_BY_DRIFT` the same row — no new invocation, validation or commit,
`ABANDONED` the only lifecycle target — so the project is barred exactly as
the unreached drift suspension would have barred it. Because the guard is
reached through `_raise_escalation`, where `take_snapshot` is nested inside a
caller's own transaction (`_settle_commit_receipt`) the suspension rolls back
together with the publication it answers for. The read guard, the refusal
itself and the no-repair rule for malformed rows are unchanged; the
correction adds no repair, coercion, migration or scan.

Closure basis reviewed:

- Regression `test_a_failed_staleness_derivation_suspends_the_project`
  ([test_gr29_decision_principal_key.py:450](../../tests/test_gr29_decision_principal_key.py#L450))
  reproduces the reviewer's exact sequence — a keyed authorization, a
  keyless historical decision stripped of its `principal_key_id`, a drifted
  workspace, then a snapshot — and asserts the resulting durable state twice
  through independently opened store/controller pairs
  ([test_gr29_decision_principal_key.py:397](../../tests/test_gr29_decision_principal_key.py#L397)
  through
  [test_gr29_decision_principal_key.py:447](../../tests/test_gr29_decision_principal_key.py#L447)):
  the project carries `SUSPENDED_BY_INTEGRITY` with a project-scoped `OPEN`
  `INTEGRITY_VIOLATION` escalation naming it by `suspension_ref`; the
  malformed row is still unreadable by both readers and still malformed on
  disk; the audit chain still verifies; the prior authorization is still
  `VALID` on disk yet unusable, since `propose_commit` is refused with
  `PolicyDenied` matching `SUSPENDED_BY_INTEGRITY`.
- `test_a_readable_project_is_not_suspended_by_the_new_gate` holds the
  healthy path to `REALITY_DRIFT` / `SUSPENDED_BY_DRIFT`, so the new gate
  does not fire when nothing is malformed.
- Mutation evidence: guard `snapshot_interpretation_suspends`
  (`kind: gr29`) is recorded **KILLED** at
  [gr29-mutations.json:158](../../docs/evidence/gr29-mutations.json#L158)
  through
  [gr29-mutations.json:174](../../docs/evidence/gr29-mutations.json#L174) —
  deleting the guarded call turned the regression red
  (`test_a_failed_staleness_derivation_suspends_the_project` failing) and the
  restored suite returned to 1303 passed.
- The evidence record's own `remediation.GR29-R01` block
  ([gr29-mutations.json:622](../../docs/evidence/gr29-mutations.json#L622)
  through
  [gr29-mutations.json:630](../../docs/evidence/gr29-mutations.json#L630))
  states the same finding, correction, suspension-routing rationale,
  transaction-nesting behavior, regression and explicit non-closures
  (no storage migration, no repair or backfill of malformed rows, no scan
  for them, clearing an integrity suspension remains a human's act under §4
  row 4-20) that this section reviews.

**Disposition: CLOSED.** The correction is bounded to the interpretation
window `GR29-R01` identified, is reached on the exact reviewer sequence, is
covered by a killed mutation guard, and introduces no repair, coercion,
migration or scope change beyond suspending the project.

## 3. `GR29-R02` — LOW / nonblocking

`GR29-R02` found that the `hollowed_and_repaired` explanation for guard
`genesis_approver` undercounted its own regression: the explanation as
originally written said the recording boundary refused three of the five
actors `test_creation_requires_an_authenticated_human_approval` parametrizes,
when the guard-independent refusals in fact cover five of five — two by
`guard:decision_actor_human`, two by `guard:decision_actor_authenticated`,
and, added this stage, the keyless case by
`guard:decision_principal_key_record`.

The recorded correction is confined to prose and a test docstring: the
`hollowed_and_repaired[0].cause` field in the evidence record
([gr29-mutations.json:47](../../docs/evidence/gr29-mutations.json#L47)
through
[gr29-mutations.json:52](../../docs/evidence/gr29-mutations.json#L52)) now
states five-of-five with the three guard names, and the docstring of
`test_creation_requires_an_authenticated_human_approval` in
[tests/test_gr23_creation_path.py](../../tests/test_gr23_creation_path.py)
was corrected to match. The evidence record states explicitly that no
mutation count changed as a result
([gr29-mutations.json:631](../../docs/evidence/gr29-mutations.json#L631)).

Closure basis reviewed:

- The correction is textual only; it does not touch `src/gruntime/`
  production code.
- Guard `genesis_approver` (`kind: adjacent`) is independently recorded
  **KILLED** with all five parametrizations red before restoration
  ([gr29-mutations.json:86](../../docs/evidence/gr29-mutations.json#L86)
  through
  [gr29-mutations.json:106](../../docs/evidence/gr29-mutations.json#L106)),
  consistent with the corrected five-of-five description and with the
  `match=` repair already recorded for this guard at GR-29 in
  [gr29-mutations.json:46](../../docs/evidence/gr29-mutations.json#L46)
  through
  [gr29-mutations.json:53](../../docs/evidence/gr29-mutations.json#L53).
- No functional claim, invariant, or closure status elsewhere in the
  evidence record depended on the undercounted wording; the finding is
  editorial accuracy of a mutation-evidence explanation, not a gap in
  enforcement or test coverage.

**Disposition: CLOSED.** The correction matches the evidence the guard
itself already produced, changes no guard, no mutation count and no
production code, and is confined to the explanation and docstring text the
finding named.

## 4. Independent closure verification

| Verification | Result reviewed |
|---|---|
| Full suite | **1303 passed**, matching every `Restored:` line in [gr29-mutations.json](../../docs/evidence/gr29-mutations.json) and the top-level `tests_passed` field at [gr29-mutations.json:17](../../docs/evidence/gr29-mutations.json#L17). |
| Mutation guards | **21/21 KILLED** — 7 `gr29` guards plus 14 `adjacent` guards rechecked, listed at [gr29-mutations.json:21](../../docs/evidence/gr29-mutations.json#L21) through [gr29-mutations.json:45](../../docs/evidence/gr29-mutations.json#L45), each with `"passed": true` in its own guard object; `guards_not_killed` is empty at [gr29-mutations.json:20](../../docs/evidence/gr29-mutations.json#L20). |
| New direct findings | **NONE** raised against `F04-001`, `GR29-R01`, or `GR29-R02` beyond the two findings this record closes. |
| Repository boundary | Only this new file was added under `design/review/`. No production code, test, `CLAUDE.md`, or existing review record was modified by this recording action. |

## 5. Residual state

The malformed `HumanDecision` row that either finding's regression exercises
remains, exactly as `CLAUDE.md`'s GR-29 phase line and
[gr29-mutations.json:15](../../docs/evidence/gr29-mutations.json#L15)
describe it: refused with `IntegrityViolation` on every read, at
`StateStore._decision_from_row`, behind both `get_decision` and
`list_decisions`; never repaired, coerced, migrated or backfilled; a listing
refuses whole rather than omitting the row. `GR29-R01`'s closure does not
change that. What changes is that the corresponding authorization, though it
may remain `VALID` on disk — the staleness derivation that would have marked
it `STALE` never runs, because it cannot enumerate a row it cannot read — is
unusable: the durable, atomically-applied `SUSPENDED_BY_INTEGRITY`
suspension gates every subsequent effect against the project
(`SUSPENSION_GATE`), the same bar `SUSPENDED_BY_DRIFT` would have applied had
the derivation been able to reach it. Clearing that suspension remains a
human's act under transition-matrix §4 row 4-20; on a project holding such a
row, the derivation will refuse again on every later snapshot.

No non-`F04-001` scope is claimed closed here. `F03-001` (overall, 131 of 145
rows), `F04-002` (estate-wide backfill), `F04-003` (evidence-file
standardization) and `F04-004` (all-three-of-`F03-001..003` closure) remain
open exactly as recorded in
[gr29-mutations.json:7](../../docs/evidence/gr29-mutations.json#L7) through
[gr29-mutations.json:12](../../docs/evidence/gr29-mutations.json#L12); this
record does not reinterpret the bounded GR-29 closure as touching them.

## 6. Final verdict

**`GR29_CLOSURE_PASS`.** Both `GR29-R01` (HIGH/blocking) and `GR29-R02`
(LOW/nonblocking) are independently verified CLOSED against the frozen
evidence and regression tests cited above; the full suite passes at 1303;
mutation verification is 21/21 KILLED; no new direct finding was raised. This
is closure of the two findings named, not of `F03-001`, `F04-002`,
`F04-003`, `F04-004`, or any other open item.
