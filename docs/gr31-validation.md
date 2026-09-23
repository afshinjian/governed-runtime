# GR-31 validation evidence

Per-stage evidence for GR-31, as `docs/gr08-validation.md` is for GR-08.
`CLAUDE.md` records that GR-17, GR-23 and GR-24 have no such file and that
their kills survive only as `bin/mutate` summary lines in
`docs/evidence/recheck-20260916.txt`; this file exists so GR-31 does not join
them. Every mutation summary below is inline. Any log path is stated relative
to a named root.

**Evidence root.** Full `bin/mutate` logs are written under `.evidence/`,
which is gitignored and therefore **not** part of this record. The summaries
below are the committed evidence; the logs are corroboration available only on
the machine that produced them. Paths written `.evidence/<name>` are relative
to the repository root.

Stage: GR-31. Baseline: `dbd7d9a` (`GR-31: persist implementation plan`),
clean tree, 1353 tests passing.
Specification: `docs/gr31-plan.md`, SHA-256
`6cb0f13c6e684cb80419b544bff876da9cebd5c0042d736d8032c56209524812`
(verified before any edit).

## 1. What GR-31 changed

| id | change | file |
|---|---|---|
| C1 | `project.ceiling.set` added to the `HUMAN`/`HUMAN_DECISION` register row | `authority.py` |
| C2 | `set_capability_ceiling(project_id, *, ceiling, decision_id)` | `contract_controller.py` |
| C3 | `grant_project_budget(project_id, *, budget, decision_id)` | `contract_controller.py` |
| C4 | `confirmation_admits` / `require_confirmation`, one predicate behind three `CONFIRM` cells | `decision.py` |
| C5 | Row 5-1 confirmation in `open_run` | `controller.py` |
| C6 | Row 7.2-1 first-invocation confirmation in `create_invocation` | `worker_controller.py` |
| C7 | Row 7.4-4 confirmation and the `Q2a` deferral guard in `authorize_commit` | `controller.py` |
| C8 | `proc.exec.validation` proved in `execute_validation` (rows 7.1-2/7.1-3 only) | `validation_controller.py` |

`C1` is the only vocabulary change: one register entry. No `DecisionKind`
member was added, `LEGAL_TRANSITIONS` is unchanged, and no transition row was
added or edited.

## 2. Guards added, and what kills each

Twelve guards. `bin/check-gr31-mutations` builds every needle from the AST and
never from the `# guard:` tag, because a tag needle mutates only the comment
and reports SURVIVED for a guard that is in fact killed (`CLAUDE.md` Tooling).
Each needle was verified, before the run, to occur exactly once in its file, to
be a single statement, and to leave a parseable module when deleted — so an
ERROR (pytest exit 4) from an orphaned body cannot be mistaken for a result.

| guard | file | killed by |
|---|---|---|
| `gr31_confirmation_admits` | `decision.py` | `test_gr31_supervision_gates.py` (all three rows) |
| `gr31_ceiling_pending_genesis` | `contract_controller.py` | `test_provisioning_refused_mid_genesis` |
| `gr31_ceiling_registered` | `contract_controller.py` | `test_ceiling_entries_must_be_registered` |
| `gr31_ceiling_decision` | `contract_controller.py` | `test_ceiling_requires_valid_decision`, `test_ceiling_decision_cannot_also_grant` |
| `gr31_budget_pending_genesis` | `contract_controller.py` | `test_provisioning_refused_mid_genesis` |
| `gr31_budget_initial_only` | `contract_controller.py` | `test_budget_initial_grant_only` |
| `gr31_budget_decision` | `contract_controller.py` | `test_budget_requires_valid_decision` |
| `gr31_run_start_confirm` | `controller.py` | `test_run_start_refuses_without_confirmation` |
| `gr31_preconditions_deferred` | `controller.py` | `test_gr31_preconditions_deferred.py` |
| `gr31_commit_authorize_confirm` | `controller.py` | `test_commit_authorize_refuses_without_confirmation` |
| `gr31_first_invocation_confirm` | `worker_controller.py` | `test_first_invocation_refuses_without_confirmation` |
| `gr31_validation_exec_authority` | `validation_controller.py` | `test_validation_requires_proc_exec` |

`gr31_budget_pending_genesis` is not in the plan's mutation table. The plan's
`T6` says "**both** operations refuse while the creation transaction is open",
and one guard cannot answer for two transactions, so the budget operation
carries its own and `T6` kills both.

## 3. Mutation results

Run on the final tree, sequentially, no concurrent mutants. Every needle was
built from the AST. Every restored suite came back **1388 passed**, which is
what makes each KILLED a real result rather than a broken checkout.

The GR-31 and GR-28 tables below are the **re-run after the `GR31-R01`
remediation** (§8), measured against the tree this record describes; the line
numbers are that tree's. The GR-29 table is the one run that was **not**
re-run, and says so in its own subsection. Counts and sites from the
pre-remediation run were 1386 and a `controller.py` 19-28 lines shallower;
they are superseded, not additional.

**Totals: 39 guards, 39 KILLED, 0 SURVIVED, 0 ERROR** — 32 of them re-measured
after the remediation, 7 (GR-29) before it.

### `bin/check-gr31-mutations` — 12/12 KILLED

Summary line: `All 12 guards killed; every restored suite passed.`
Machine record: `.evidence/gr31-mutations.json` (12 entries, every `passed` true).

| guard | site | result |
|---|---|---|
| `gr31_confirmation_admits` | `src/gruntime/decision.py:209` | KILLED |
| `gr31_ceiling_pending_genesis` | `src/gruntime/contract_controller.py:115` | KILLED |
| `gr31_ceiling_registered` | `src/gruntime/contract_controller.py:130` | KILLED |
| `gr31_ceiling_decision` | `src/gruntime/contract_controller.py:132` | KILLED |
| `gr31_budget_pending_genesis` | `src/gruntime/contract_controller.py:164` | KILLED |
| `gr31_budget_initial_only` | `src/gruntime/contract_controller.py:178` | KILLED |
| `gr31_budget_decision` | `src/gruntime/contract_controller.py:180` | KILLED |
| `gr31_run_start_confirm` | `src/gruntime/controller.py:1193` | KILLED |
| `gr31_preconditions_deferred` | `src/gruntime/controller.py:2163` | KILLED |
| `gr31_commit_authorize_confirm` | `src/gruntime/controller.py:2167` | KILLED |
| `gr31_first_invocation_confirm` | `src/gruntime/worker_controller.py:103` | KILLED |
| `gr31_validation_exec_authority` | `src/gruntime/validation_controller.py:107` | KILLED |

### `bin/check-gr28-mutations --adjacent` — 20/20 KILLED

Summary line: `All 20 guards killed; every restored suite passed.`

Run with `--adjacent`, not bare. The plan asks only for the plain run, but
GR-31 inserted two guards **into `authorize_commit` itself**, and
`commit_authorize_status`, `gr06_commit_authorize` and `commit_authorize_base`
are that function's existing guards. All three are in GR-28's adjacent set and
all three were killed, which is the direct evidence that GR-31 did not hollow
an earlier kill. `CLAUDE.md` records why that question has to be asked out
loud: GR-23 left `guard:controller_snapshot` SURVIVED for two stages with the
suite green.

| guard | site | result |
|---|---|---|
| `gr06_commit_propose_grant` | `src/gruntime/controller.py:1887` | KILLED |
| `gr06_commit_propose_path` | `src/gruntime/controller.py:1889` | KILLED |
| `commit_proposal_message` | `src/gruntime/controller.py:1927` | KILLED |
| `transition_ord_grant` | `src/gruntime/controller.py:1984` | KILLED |
| `transition_kernel_holder` | `src/gruntime/controller.py:1996` | KILLED |
| `transition_row_declared` | `src/gruntime/controller.py:2062` | KILLED |
| `transition_capability_held` | `src/gruntime/controller.py:2071` | KILLED |
| `commit_authorize_status` | `src/gruntime/controller.py:2160` | KILLED |
| `gr06_commit_authorize` | `src/gruntime/controller.py:2169` | KILLED |
| `commit_authorize_base` | `src/gruntime/controller.py:2172` | KILLED |
| `commit_mark_barrier` | `src/gruntime/controller.py:2242` | KILLED |
| `commit_mark_completeness` | `src/gruntime/controller.py:2243` | KILLED |
| `commit_mark_status` | `src/gruntime/controller.py:2244` | KILLED |
| `commit_single_receipt` | `src/gruntime/controller.py:2280` | KILLED |
| `commit_no_reapply` | `src/gruntime/controller.py:2370` | KILLED |
| `gr06_commit_apply` | `src/gruntime/controller.py:2380` | KILLED |
| `commit_apply_base` | `src/gruntime/controller.py:2389` | KILLED |
| `gr06_commit_intent_grant` | `src/gruntime/contract_controller.py:366` | KILLED |
| `gr06_commit_source_scope` | `src/gruntime/contract_controller.py:368` | KILLED |
| `gr06_commit_destination_scope` | `src/gruntime/contract_controller.py:369` | KILLED |

### `bin/check-gr29-mutations` — 7/7 KILLED

Summary line: `All 7 guards killed; every restored suite passed.`

**Measured on the pre-remediation candidate and not re-run** (restored suite
1386; the `controller.py` site below is that tree's). The remediation
authorization scopes the re-run to the GR-31 suite and the GR-28 adjacent set,
and no GR-29 guard lies in either edited function: `decision_principal_key_put`
is in `StateStore.put_decision`, which the new transactions now call *inside*
themselves, but the transaction re-raises after `ROLLBACK` and swallows
nothing, and every test that kills that guard calls `put_decision` directly.
Stated rather than assumed: this set was not re-measured.

| guard | site | result |
|---|---|---|
| `decision_principal_key_iff` | `src/gruntime/decision.py:105` | KILLED |
| `snapshot_interpretation_suspends` | `src/gruntime/controller.py:1304` | KILLED |
| `decision_actor_human` | `src/gruntime/controller.py:1660` | KILLED |
| `decision_actor_authenticated` | `src/gruntime/controller.py:1661` | KILLED |
| `decision_principal_key_record` | `src/gruntime/controller.py:1662` | KILLED |
| `decision_principal_key_put` | `src/gruntime/store.py:1760` | KILLED |
| `decision_principal_key_read` | `src/gruntime/store.py:1814` | KILLED |

### One interrupted run, and what was done about it

The first GR-31 run was **cancelled deliberately** and restarted from scratch.
Two docstrings in `contract_controller.py` were edited while that run was
mutating that same file; `bin/mutate` restores from a backup taken before the
edit, so the evidence would have been measured against a tree that no longer
existed and the edit would have been silently reverted. Per `CLAUDE.md`
Tooling, `git diff --quiet -- src` was checked first: no mutant was left
behind, the edit was intact, and the suite was re-run green at 1386 before the
run was restarted. **Every result above comes from the restarted run, against
the final tree.** No repository file was touched between the restart and the
end of the last run — `tests/test_governed_skills.py` copies `CLAUDE.md` into
its fixture, so even a documentation edit mid-run can move the suite under a
mutant.


## 4. Test results

```
.venv/bin/python -m pytest -q                      -> 1388 passed, 0 failed
.venv/bin/python -m pytest -q tests/test_gr31_*.py -> 35 passed
.venv/bin/python bin/check-governed-skills         -> OK (wrappers, wrapper-dedup,
                                                      authority, authorization-schema,
                                                      authorization-gate, report-schema)
git diff --check HEAD                              -> clean
git diff --quiet -- src                            -> no mutant in the tree
bin/pilot-run                                      -> exit 1 (see section 7), still refuses
```

Baseline was 1353. The 35 new tests are 15 provisioning, 11 supervision-gate,
3 validation-authority and 6 precondition-deferral. Two of the eleven
supervision-gate tests are the `GR31-R01` atomicity regressions (§8).

`bin/check-governed-skills` must be run with the virtualenv interpreter: the
bare `bin/check-governed-skills` shebang resolves to a Python without
`jsonschema` and fails on import rather than on the contract. That is
pre-existing and untouched by this stage, but it is worth knowing before
reading an import error as a contract failure.


## 5. Scope

The authorization for this implementation named fourteen paths. Seven further
files were mutated, each under an explicit, separately granted OWNER scope
expansion, and each is test-harness compatibility only — no production
behaviour was changed to accommodate any of them.

| file | why it had to change | authorization |
|---|---|---|
| `tests/gr06_support.py` | `provision_legacy_run` never requested `proc.exec.validation`; `C8` now proves it | expansion 1 |
| `tests/test_gr08_inference_relay.py` | `bridge_for` reaches a first invocation on a `SUPERVISED` project; `C6` now requires the row's confirmation | expansion 1 |
| `tests/test_gr08_relay_boundaries.py` | imports `bridge_for` above | expansion 1 (no edit needed) |
| `tests/test_gr09_validation.py` | covered by the `gr06_support.py` fix | expansion 1 (no edit needed) |
| `tests/test_gr17_validation_authority.py` | `granted_run` builds its own contract and reaches the executor | expansion 1 |
| `tests/test_r5_attestation_required.py` | two tests authorize on review-backed preconditions, which `Q2a` defers | expansion 2 |
| `tests/test_gr28_transition_authority.py` | one test used a validation precondition as a vehicle to reach the `BLOCKED` exit | expansion 2 |

Measured before any edit, on the clean baseline: `C8` alone failed 33 existing
tests and `C6` alone reached 86, in files the original authorization did not
cover. A probe over the whole suite found 690 `open_run` and 135
`authorize_commit` calls, every one of them `AUTONOMOUS`, which is why `C5` and
`C7` needed no harness change at all.

### What the harness edits did and did not do

- `gr06_support.py` and `test_gr17_validation_authority.py`: added
  `proc.exec.validation` to the capability request of the runs that already
  execute a validation successfully. Nothing was added to a run whose test
  asserts a refusal — `test_declared_egress_without_a_grant_never_reaches_the_executor`
  still denies on the egress capability alone, and its assertion that exactly
  one denial is recorded is what proves it.
- `test_gr08_inference_relay.py`: `bridge_for` now records a real
  `HumanDecision` — an `APPROVE` over the run, scoped `RUN` — and passes it as
  `confirmation_id`. These fixtures were **not** switched to `AUTONOMOUS` to
  make the gate go away.
- `test_r5_attestation_required.py`: `test_authorization_refuses_a_review_backed_precondition`
  still asserts a refusal; only the class moved, from `IntegrityViolation` to
  the `PolicyDenied` `Q2a` raises earlier. `test_preconditions_accept_an_attestation_reference`
  keeps its constructor-level assertion — a typed `ReviewAttestation` ref is
  accepted into `CommitPreconditions` — and now asserts the `Q2a` deferral of
  authorizing on one, which is the boundary GR-31 deliberately moved.
- `test_gr28_transition_authority.py`: the unmet precondition that reaches the
  `BLOCKED` exit is now a `decisions` one rather than a `validations` one.
  `resolve_decision` remains `lambda ref: False` (`Q4`), so it is permanently
  unmet and takes exactly the same edge. The row-7.4-2 event-label assertion
  is unchanged, which is the whole point of that test.

## 6. What GR-31 did not close

Recorded here because the value of this stage depends on not being read as
more than it is.

- **`F03-001` is open.** `C8` closes the declaration for rows 7.1-2 and 7.1-3
  and for no others. GR-28 closed 14 of 145 rows; this adds two. The remaining
  129 consume no declaration.
- **`F04-004` is unaffected.** It closes only when all of `F03-001`..`003`
  close, and `F03-001` is open.
- **`B4`, `B6` and `B7` are open and deferred.** The production independent
  review leg is **not** complete. `guard:gr31_preconditions_deferred` defers
  `B6` and `B7`; it does not close them. `commit.py`, `review.py`, `rvw()`,
  `resolve_review_evidence` and generic precondition resolution are untouched.
  The guard is a temporary Pilot-1 safety boundary and GR-33 must not bypass
  or weaken it.
- **`B2` is open.** There is still no composition root; `bin/pilot-run` refuses
  and now says so accurately. That is GR-32.
- **`B3` is open.** No candidate observation exists. `Q1` accepts post-commit
  validation for Pilot 1 only, as an owner-executed procedure in GR-33, and
  GR-31 writes no materialization code. DESIGN-02 is untouched.
- **DESIGN-03 is neither revised nor frozen, and no DESIGN-03 finding is
  claimed closed.** The per-field direction was followed; the document was not
  adopted. `GRANT_BUDGET`, which DESIGN-03 §3 proposes, was **not** added —
  `EXTEND_BUDGET` is the only budget-shaped member of the frozen enum and is
  what the initial grant is recorded as.
- **`policy_digest` provisioning is omitted** (assumption `A1`). `policy.set`
  is untouched.
- **Confirmation is enforced on rows 5-1, 7.2-1 and 7.4-4 only**, and in the
  `SUPERVISED` column only. Every one of those rows reads `AUTO` under
  `AUTONOMOUS`, and `test_autonomous_rows_require_no_confirmation` asserts
  that the runtime does not invent a cell the frozen matrix does not declare.
- **Storage schema is unchanged.** `STORAGE_VERSION` is still 5, and the
  v1→v5 refusal-without-migration gap is untouched.

## 7. Known limitation of this record

`bin/pilot-run` returns exit **1**, not the exit 2 the plan's verification
block expects, because `/tmp/pilot-sandbox` does not exist on this host: the
target check refuses before the missing-prerequisite branch is reached. Both
are refusals and the script still refuses, but the exit-2 path — and with it
the new `missing`/`shipped_already` report body — is **unexercised here** and
was verified only by reading. Verify it on a host that has the pilot target at
`27e6c88` before relying on that branch.

## 8. `GR31-R01` — the authorized act and its confirmation are one write

Raised by independent review of the GR-31 candidate; remediated under OWNER
authorization `gr31-remediation-001`, which bounds the work to this finding and
preserves the candidate. `GR31-R02` is NONBLOCKING and required no repository
change, so none was made.

### The finding

> `open_run` and `authorize_commit` persist the operation they authorize and
> consume their confirming `HumanDecision` in separate top-level transactions.
> A crash or exception after the operation write but before `_consume_decision`
> can therefore leave the authorized act durable while the `HumanDecision`
> remains `VALID`. For `open_run` this can permit the same `PROJECT`-scoped
> confirmation to authorize a later different run.

### Root cause

`C5` and `C7` added the confirmation and its consumption to methods that had no
transaction of their own, and did not open one. Every durable step in them was
therefore its own top-level transaction:

| method | step | transaction, before remediation |
|---|---|---|
| `open_run` | `_append("run.allocated")` | its own (`store.append` → `BEGIN IMMEDIATE`) |
| | `store.put_run` | its own (autocommit) |
| | `_consume_decision` → append + `put_decision` | its own, twice |
| `authorize_commit` | `_transition_intent` → append + `put_commit_intent` | its own |
| | `_consume_decision` → append + `put_decision` | its own, twice |

`C2`, `C3`, `activate_contract` and `create_invocation` each already wrapped
their event, their field write and their `_consume_decision` in one
`BEGIN IMMEDIATE`; `C5` and `C7` are the two boundaries GR-31 added that did
not. Nothing about the confirmation predicates is at fault: both guards refuse
exactly as before, and neither was weakened.

Why it matters differs per row, and the second is the sharper one:

- Row 7.4-4 — an `AUTHORIZED` intent is the runtime's standing permission to
  mutate the repository (`mark_applying` accepts no other status). One left
  durable beside a confirmation still `VALID` is a commit authorized by an act
  the audit shows nothing ever discharged.
- Row 5-1 — the confirmation's subject is the `PROJECT`, because the run does
  not exist when the human answers. A surviving `VALID` answer is therefore
  good for *any* later `open_run` on that project: one human act, two
  allocations, which is exactly what `HD-INV-3` exists to forbid.

### RED reproduction

Two regressions, one per boundary, in `tests/test_gr31_supervision_gates.py`.
Each records a real confirmation, injects a failure at the window the finding
names — after the authorized operation's write, inside the consumption — and
then asserts that nothing survived it.

```
tests/test_gr31_supervision_gates.py::test_run_start_is_atomic_with_its_confirmation
tests/test_gr31_supervision_gates.py::test_commit_authorize_is_atomic_with_its_confirmation
```

Against the unremediated candidate, both failed, each on the first assertion
after the injected failure — which is the finding itself, reproduced:

```
>   assert c.store.list_runs(project) == []
E   AssertionError: assert [StageRun(run...=frozenset())] == []
E     Left contains one more item: StageRun(run_id='01M365N82ERYYQQV6HVQDTN1B5', ...)

>   assert (c.store.get_commit_intent(intent.intent_id).status
            is CommitIntentStatus.PROPOSED)
E   AssertionError: assert <CommitIntentStatus.AUTHORIZED: 'AUTHORIZED'> is <CommitIntentStatus.PROPOSED: 'PROPOSED'>

2 failed, 9 deselected
```

The run was durable and the intent was `AUTHORIZED` while, in both cases, the
confirmation that authorized them was still `VALID`.

### Remediation

One `BEGIN IMMEDIATE` transaction per boundary, in the shape `C2`/`C3`,
`activate_contract` and `create_invocation` already use: the durable half moves
into a private helper called inside the transaction, and the public method
commits it or rolls it back whole.

| method | helper | inside the transaction |
|---|---|---|
| `Controller.open_run` | `_allocate_run(run, confirmation)` | `run.allocated`, `put_run`, `_consume_decision` |
| `Controller.authorize_commit` | `_settle_commit_authorization(intent, project_id, met=, confirmation=)` | `_transition_intent` (`AUTHORIZED` or `BLOCKED`), `_consume_decision` |

What deliberately stayed outside:

- Both confirmation guards, unchanged and still refusing first — a transaction
  is not where a refusal belongs.
- `authorize_commit`'s repository reads (`governed_repo`, `verify_head`) and
  `evaluate_preconditions`. They write nothing, and holding the database's
  write lock across a repository read would widen the transaction for no gain.
- The `BLOCKED` branch consumes nothing, as before: an intent that never
  reached `AUTHORIZED` discharged no confirmation, so the human's answer stays
  `VALID` — unspent, because the act it authorizes did not happen. It is now
  atomic with respect to its own status write.

Not changed, per the authorization: confirmation subject semantics, the
transition rows, `policy.resolve` (still no production caller), generic
`resolve_decision` (still `lambda ref: False`), and every existing guard.

### Atomicity verification

With the transactions in place both regressions pass, and each asserts more
than "it did not happen":

| asserted | `open_run` | `authorize_commit` |
|---|---|---|
| no partially durable operation | `store.list_runs(project) == []` | intent still `PROPOSED` |
| no misleading authority/audit state | no `run.allocated` event; `project.event_seq` unchanged; `verify_chain` | no `commit_intent.authorized` event; `event_seq` unchanged; `verify_chain` |
| the confirmation is still `VALID` | re-read from the store | re-read from the store |
| the success path commits both halves | the same confirmation then allocates the run and is `CONSUMED` | the same confirmation then authorizes and is `CONSUMED` |
| …and commits them *together* | `decision.state_derived` cites the `run.allocated` it discharged and is `seq + 1` on the chain | `decision.state_derived` cites the `commit_intent.authorized` and is `seq + 1` |

The `seq + 1` adjacency is the positive evidence: the consumption is the next
event on the project's hash chain after the act it discharged, with nothing
between them, which only one transaction can produce.

### Mutation

Inspected, as the authorization asks, and **no guard was added**. The
atomicity boundary is a three-line `BEGIN IMMEDIATE` / `COMMIT` /
`ROLLBACK` wrapper, not a single deletable statement: `bin/mutate` deletes the
matched line, so deleting any one of the three orphans the other two and
reports ERROR (pytest exit 4), which `CLAUDE.md` Tooling records as proving
nothing either way. Tagging it `# guard:` would put a guaranteed ERROR into
`bin/check-gr31-mutations` and inflate its count with a result that is not a
result. The same is true of `C2`/`C3`, whose wrappers carry no tag either and
whose atomicity is proved by `test_provisioning_is_atomic` — the same evidence
shape used here. `bin/check-gr31-mutations --list` names the same twelve guards
before and after this remediation.

The mutation suites were re-run in full afterwards, and the GR-28 adjacent set
with them, because `authorize_commit` was edited again.

### Final verification, after remediation

```
.venv/bin/python -m pytest -q tests/test_gr31_*.py -> 35 passed
.venv/bin/python -m pytest -q                      -> 1388 passed, 0 failed
.venv/bin/python -B bin/check-governed-skills      -> OK (wrappers, wrapper-dedup,
                                                      authority, authorization-schema,
                                                      authorization-gate, report-schema)
.venv/bin/python bin/check-gr31-mutations          -> All 12 guards killed
.venv/bin/python bin/check-gr28-mutations --adjacent -> All 20 guards killed
git diff --check HEAD                              -> clean
git diff --quiet -- docs/gr31-plan.md              -> unchanged (frozen specification)
```

`git diff --quiet -- src` is **not** a pass/fail check on this tree: the GR-31
candidate is uncommitted, so `src` always differs from `HEAD`. The check
`CLAUDE.md` Tooling actually asks for — that no mutant was left behind — was
made instead by grepping the tree for `# mutation: removed`, which appears only
inside `bin/mutate` and `bin/check-gr29-mutations` as their own source string.

### Scope of the remediation

Authorization `gr31-remediation-001` named five paths. Three were mutated:

| path | change |
|---|---|
| `src/gruntime/controller.py` | the two transactions and their helpers |
| `tests/test_gr31_supervision_gates.py` | the two atomicity regressions |
| `docs/gr31-validation.md` | this section, and the re-measured §3/§4 |

`bin/check-gr31-mutations` was inspected and left unchanged (above).
`CLAUDE.md` was inspected and left unchanged: its `Supervision gates` section
claims which rows are enforced, through which predicate, and that *provisioning*
is one `BEGIN IMMEDIATE` transaction — every one of those claims is as true
after this remediation as before, and the authorization permits an edit there
only if a current claim would otherwise become inaccurate. Nothing outside
those paths was touched, and nothing was committed, staged, tagged or pushed.
