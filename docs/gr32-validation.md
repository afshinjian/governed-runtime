# GR-32 validation evidence

Per-stage evidence for GR-32, as `docs/gr31-validation.md` is for GR-31. Every
mutation summary below is inline.

**Evidence root.** Full `bin/mutate` logs are written under `.evidence/`,
which is gitignored and therefore **not** part of this record. The summaries
below are the committed evidence; the logs are corroboration available only on
the machine that produced them. Paths written `.evidence/<name>` are relative
to the repository root, and `.evidence/gr32-mutations.json` is the machine
record `bin/check-gr32-mutations` writes as it goes.

Stage: GR-32 — supervised stage driver / composition root.
Baseline: `bc5ae31` (`GR-32: phase line`), clean tree, 1388 tests passing.
Authorization: `gr32-implementation-001`, OWNER decisions `D1`–`D6`.

**Two records.** §1–§11 are the original implementation validation under
`gr32-implementation-001`, kept as they were run; their line numbers, counts
and guard totals describe that tree. Independent review
`gr32-implementation-review-001` then returned `GR32_REMEDIATION_REQUIRED`
with six findings. §12 is the remediation record under `gr32-remediation-001`:
where it and §1–§11 disagree about the current tree, §12 is the current one.
Independent closure review `gr32-closure-review-001` then returned
`GR32_CLOSURE_FAILED` with F-002 and F-004 open and R-001 new; §13 is the
second remediation record under `gr32-remediation-002`, and where it and
§1–§12 disagree about the current tree, §13 is the current one.
Independent closure review `gr32-closure-review-002` then returned
`GR32_CLOSURE_FAILED` with F-002 alone open; §14 is the third remediation
record under `gr32-remediation-003`, and where it and §1–§13 disagree about
the current tree, §14 is the current one.

## 1. What GR-32 closes, and what it does not

GR-32 closes **`B2` only**: the runtime had every governed transition and no
production caller that walked them in order. `controller.main()` offered six
subcommands that between them could not create a project, provision a ceiling
or a budget, record a decision, author or activate a contract, allocate a run,
or configure the inference relay — so a supervised project could be created and
then could do nothing through any production path. Everything between creation
and a first governed revision existed only in test harnesses, which provisioned
by writing rows.

`B3` (native candidate observation), `B4` (independent worker review), `B6`
(review-precondition correctness) and `B7` (validation-precondition
correctness) are **untouched and open**. So are DESIGN-02, DESIGN-03, the
blanket `F03-001`, `F04-004`, the `F04-002` estate cleanup, `SET_MODE`,
AUTONOMOUS implementation changes, multi-mutation `propose_commit`, storage
migration and the GR-33 live run. `guard:gr31_preconditions_deferred` is
neither bypassed nor weakened; §7 below shows it refusing through the driver.

## 2. What changed

| id | change | file |
|---|---|---|
| C1 | `driver.py`: `PilotSession`, `OwnerPresenter`, `StepOutcome`/`DriverReport`, `ProposalMapping` | `src/gruntime/driver.py` (new) |
| C2 | `PilotParameters` / `ValidationPlan`: every pilot value an input (`D5`) | `src/gruntime/driver.py` |
| C3 | `preflight_credential`: the `D2` pre-consumption check | `src/gruntime/driver.py` |
| C4 | `build_provider` / `open_runtime`: the one place adapters are named (`D1`) | `src/gruntime/driver.py` |
| C5 | `map_proposal`: one worker mutation, in `propose_commit`'s terms | `src/gruntime/driver.py` |
| C6 | `LEGACY_COMMANDS`/`GATED_COMMANDS`/`legacy_command_admits`: the `D6` gate | `src/gruntime/controller.py` |
| C7 | `build_parser`: the parser built *from* the command mappings, plus `--provider` | `src/gruntime/controller.py` |
| C8 | `main()` delegates `pilot`, `observe` and `resume` to the driver; no provider is hardcoded | `src/gruntime/controller.py` |
| C9 | `bin/pilot-run` rewritten from a refusal into a truthful preflight (`D4`) | `bin/pilot-run` |

No kernel transition was changed. No `DecisionKind` member, register entry,
`LEGAL_TRANSITIONS` row or frozen design file was touched. `propose_commit`'s
signature is unchanged and is asserted so
(`test_propose_commit_was_not_widened`).

## 3. `GR32-P-001` — the corrected ordering, recorded here

`docs/gr31-plan.md` orders contract construction **before** `open_run`. The
code cannot do that and never could: `guard:gr06_run_identity` requires
`contract.stage_id == run.stage_id`, and `stage_id` is minted by `open_run`.
The historical plan is **not edited**. The order the driver implements is:

| step | act | why it is here and not earlier |
|---|---|---|
| 2 | `project.create` | genesis, under the four-event witness (`AX-17`) |
| 3 | `controller.start` | once per session; `P-INV-4` |
| 4 | `project.ceiling.set` | `guard:gr06_activation_ceiling` needs a ceiling |
| 5 | `budget.grant` | `guard:gr06_budget_ceiling` needs a budget |
| 6 | `run.start` | **row 5-1**; mints the `stage_id` step 7 needs |
| 7 | `contract.author` | binds *this run's* `stage_id` — hence after step 6 |
| 8 | `capability.grant` | a grant separate from the ceiling decision |
| 9 | `contract.approve` | **row 6-2**, immediately before step 10 |
| 10 | `contract.activate` | consumes the approval; snapshot-bound |
| 11 | `validation.bind` | pins the run's `network='NONE'` slice |
| 12 | `secret.read` | preflight, grant, single-action approval, relay |
| 13 | `worker.invoke` | **row 7.2-1**, immediately before `create_invocation` |
| 14 | `commit.propose` | the receipt's one mutation |
| 15 | `commit.authorize` | **row 7.4-4**, immediately before `authorize_commit` |
| 16 | `commit.apply` | the materialization boundary |
| 17 | *stop* | no snapshot, no validation, no further transition |

Step 1 is the composition itself (`open_runtime`).

**Why each confirmation sits where it does.** `APPROVE` is in
`SNAPSHOT_BOUND_KINDS`, so every one of the four confirmations is
snapshot-bound and a snapshot landing between recording it and consuming it
makes it `STALE` (`HD-INV-4`). Each is recorded immediately before the act it
discharges, with no observation between the two. Provisioning decisions
(`GRANT_CAPABILITY`, `EXTEND_BUDGET` over a `PROJECT`) are governance acts, are
not snapshot-bound, and do not go stale.

## 4. `GR32-P-002` — the kernel sharp edge, stated accurately

`RelayController.configure_inference_relay` consumes the secret grant and the
single-action approval in one `BEGIN IMMEDIATE` transaction that **commits**,
and only then calls `resolve_secret`. A resolver that raises therefore leaves
two spent human acts and no relay. The comment in `relay_controller.py` says
why the ordering is that way — "a failed resolver never makes this
single-action approval reusable" — and GR-32 does not alter it.

What GR-32 adds is `driver.preflight_credential`, run **before either decision
is recorded**: the variable must exist, hold a non-empty value, and hold one
whose every character is printable ASCII — the same predicate as
`guard:gr08_credential_value`. Nothing is stripped, trimmed, normalized or
repaired. A failed preflight records **zero** secret decisions, which is
asserted directly.

**The edge remains** for anything the preflight cannot see: the environment
changing between the preflight and the resolver call, or the resolver failing
for a reason that is not the value's shape. GR-32 makes the ordinary
misconfigurations unreachable; it does not close the window, and no claim is
made here that it does. Closing it would mean reordering the kernel's
consumption, which is outside this stage.

## 5. `GR32-P-003` — `D6`, and the historical evidence

`invoke`, `validate` and `commit` carry no confirmation plumbing: they cannot
present rows 7.2-1 or 7.4-4. Under `SUPERVISED` they would reach GR-31's
guards with `confirmation_id=None` and be refused — but only after
`Controller(...)` had built a live provider, `start` had bumped the epoch and
`controller.started` had been appended. A refusal that costs an epoch and an
event is not a structural refusal.

`legacy_command_admits` is asked in front of all of that, and answers for the
mode the project is actually in. `start`, `recover` and `snapshot` are not
gated and do not even read the project.

The five historical evidence files drive **`AUTONOMOUS`** projects through
these commands, so the gate cannot reach them and none of them was edited.
That is asserted twice: their bytes are compared against `HEAD`
(`test_the_historical_evidence_files_are_unmodified`) and they are run as a
group in §8.

**Drift is structural, not conventional.** `build_parser` builds its
subparsers *from* `LEGACY_COMMANDS` and `DRIVER_COMMANDS`, and
`GATED_COMMANDS` is derived from the first, so the parser surface and the
gated set cannot disagree without one edit changing both.
`test_the_gated_set_cannot_drift_from_the_parser_surface` additionally pins
the intended sets, so a silent widening fails a test rather than changing
policy quietly.

## 6. `D2` — the credential

| requirement | how it is met |
|---|---|
| no hardcoded credential | the value is read only in the step-12 resolver closure |
| no hardcoded private credential-file path | no path is read; the variable's **name** is a parameter |
| does not read Claude Code credential storage | asserted by scanning every file under `src/` and `bin/pilot-run` |
| not persisted | scanned: the whole governance root and workspace after a full run |
| never in reports, events, artifacts, journals or subprocess output | same scan, plus `guard:gr32_report_secret_free`, which asks the runtime's own `SecretGuard` |
| default header `x-api-key`, empty prefix | `DEFAULT_CREDENTIAL_HEADER` / `DEFAULT_CREDENTIAL_PREFIX` |
| both configurable; Bearer still selectable | `--credential-header` / `--credential-prefix`, asserted both ways |
| preflight immediately before the secret decisions | `_configure_relay` calls it first; zero decisions on failure |
| no repair of a malformed credential | `test_the_preflight_repairs_nothing` |

The variable's **name** does appear in the report. It is configuration the
owner supplied, not a secret, and it is what a reader needs in order to know
which variable a refusal is about. The value, its length and any fragment of
it appear nowhere.

## 7. Guards added, and what kills each

Twenty-seven guards; §7.1 gives each one's site on the final tree. `bin/check-gr32-mutations` builds every needle from the
AST and never from the `# guard:` tag, because a tag needle mutates only the
comment and reports SURVIVED for a guard that is in fact killed (`CLAUDE.md`
Tooling). Before the first mutant runs it verifies, for every needle, that it
occurs exactly once in its file and that deleting it leaves a parseable
module — so an ERROR from an orphaned body can never be mistaken for a result.

| guard | file | killed by |
|---|---|---|
| `gr32_credential_declared` | `driver.py` | `test_credential_preflight_refuses_before_any_secret_decision[None]` |
| `gr32_credential_nonempty` | `driver.py` | `…[""]` |
| `gr32_credential_printable` | `driver.py` | `…[trailing newline]`, `…[tab]`, `…[non-ascii]` |
| `gr32_known_provider` | `driver.py` | `test_build_provider_names_the_adapters_and_refuses_the_rest` |
| `gr32_provider_executable` | `driver.py` | `test_build_provider_names_the_adapters_and_refuses_the_rest` |
| `gr32_proposal_direct` | `driver.py` | `test_unsupported_receipts_are_refused_whole[RECONCILED]` |
| `gr32_proposal_completed` | `driver.py` | `…[REFUSAL]`, `…[DEADLINE]` |
| `gr32_proposal_clean` | `driver.py` | `…[capability violation]`, `…[scope breach]` |
| `gr32_proposal_single` | `driver.py` | `…[2 mutations]`, `…[0 mutations]`, `test_a_worker_that_proposes_two_files_stops_the_session` |
| `gr32_proposal_op` | `driver.py` | `test_unsupported_mutations_are_refused_whole[DELETE/RENAME/CHMOD]` |
| `gr32_proposal_rename` | `driver.py` | `…[rename_to on a MODIFY]` |
| `gr32_proposal_mode` | `driver.py` | `…[mode on a MODIFY]` |
| `gr32_proposal_after_ref` | `driver.py` | `…[no after_ref]` |
| `gr32_proposal_scope` | `driver.py` | `…[path outside scope]` |
| `gr32_proposal_digest` | `driver.py` | `test_content_that_does_not_redigest_to_the_receipts_identity_is_refused` |
| `gr32_proposal_utf8` | `driver.py` | `test_non_utf8_content_is_refused_rather_than_decoded` |
| `gr32_owner_answer` | `driver.py` | `test_a_refusing_presenter_records_no_decision_and_makes_no_transition` (9 acts) |
| `gr32_owner_option` | `driver.py` | `test_an_answer_that_was_never_offered_is_not_an_answer` |
| `gr32_owner_approves` | `driver.py` | `test_a_declined_creation_creates_no_project` |
| `gr32_report_secret_free` | `driver.py` | `test_the_report_is_checked_against_the_runtimes_own_secret_guard` |
| `gr32_secret_name_binding` | `driver.py` | `test_the_resolver_answers_only_for_the_approved_secret` |
| `gr32_secret_not_worker_capability` | `driver.py` | `test_secret_read_is_never_a_worker_capability` |
| `gr32_role_admits_request` | `driver.py` | `test_the_worker_role_must_admit_every_requested_capability` |
| `gr32_pilot_parameters_complete` | `driver.py` | `test_running_a_pilot_on_an_observation_parameter_set_is_refused` |
| `gr32_creation_principal` | `driver.py` | `test_a_creation_answered_by_another_principal_is_refused` |
| `gr32_validation_network_none` | `driver.py` | `test_only_a_network_none_validation_operation_is_registered` |
| `gr32_legacy_command_mode` | `controller.py` | `test_every_gated_command_refuses_under_supervised` (3 commands) |

### 7.1 Mutation results

Run on the final tree, sequentially, no concurrent mutants. Every needle was
built from the AST, and every needle was verified before the first mutant ran
to occur exactly once in its file and to leave a parseable module when deleted.
Every restored suite came back **1490 passed**, which is what makes each
KILLED a real result rather than a broken checkout.

**Totals: 39 guards, 39 KILLED, 0 SURVIVED, 0 ERROR** — 27 GR-32 guards and
the 12 GR-31 guards re-verified against this tree.

#### `bin/check-gr32-mutations` — 27/27 KILLED

Summary line: `All 27 guards killed; every restored suite passed.`
Machine record: `.evidence/gr32-mutations.json` (27 entries, every `passed` true).

| guard | site | result |
|---|---|---|
| `gr32_credential_declared` | `src/gruntime/driver.py:151` | KILLED |
| `gr32_credential_nonempty` | `src/gruntime/driver.py:153` | KILLED |
| `gr32_credential_printable` | `src/gruntime/driver.py:154` | KILLED |
| `gr32_known_provider` | `src/gruntime/driver.py:474` | KILLED |
| `gr32_provider_executable` | `src/gruntime/driver.py:480` | KILLED |
| `gr32_proposal_direct` | `src/gruntime/driver.py:533` | KILLED |
| `gr32_proposal_completed` | `src/gruntime/driver.py:534` | KILLED |
| `gr32_proposal_clean` | `src/gruntime/driver.py:535` | KILLED |
| `gr32_proposal_single` | `src/gruntime/driver.py:536` | KILLED |
| `gr32_proposal_op` | `src/gruntime/driver.py:538` | KILLED |
| `gr32_proposal_rename` | `src/gruntime/driver.py:539` | KILLED |
| `gr32_proposal_mode` | `src/gruntime/driver.py:540` | KILLED |
| `gr32_proposal_after_ref` | `src/gruntime/driver.py:541` | KILLED |
| `gr32_proposal_scope` | `src/gruntime/driver.py:542` | KILLED |
| `gr32_proposal_digest` | `src/gruntime/driver.py:544` | KILLED |
| `gr32_proposal_utf8` | `src/gruntime/driver.py:545` | KILLED |
| `gr32_owner_answer` | `src/gruntime/driver.py:598` | KILLED |
| `gr32_owner_option` | `src/gruntime/driver.py:599` | KILLED |
| `gr32_owner_approves` | `src/gruntime/driver.py:600` | KILLED |
| `gr32_report_secret_free` | `src/gruntime/driver.py:663` | KILLED |
| `gr32_secret_name_binding` | `src/gruntime/driver.py:681` | KILLED |
| `gr32_secret_not_worker_capability` | `src/gruntime/driver.py:698` | KILLED |
| `gr32_role_admits_request` | `src/gruntime/driver.py:699` | KILLED |
| `gr32_pilot_parameters_complete` | `src/gruntime/driver.py:743` | KILLED |
| `gr32_creation_principal` | `src/gruntime/driver.py:902` | KILLED |
| `gr32_validation_network_none` | `src/gruntime/driver.py:921` | KILLED |
| `gr32_legacy_command_mode` | `src/gruntime/controller.py:2977` | KILLED |

`gr32_credential_declared` was re-verified a second time, on its own, after
`bin/pilot-run` and its two tests changed (§8.1): `All 1 guards killed; every
restored suite passed`, restored suite 1490 passed. It is the one guard whose
killing set those files touch, and it has an independent killer in
`test_gr32_driver.py` besides.

#### `bin/check-gr31-mutations` — 12/12 KILLED (re-verification)

Summary line: `All 12 guards killed; every restored suite passed.`
Machine record: `.evidence/gr31-mutations.json` (12 entries, every `passed` true).

Run after the GR-32 implementation, against this tree. `CLAUDE.md` records why
this has to be asked out loud: a later stage can hollow an earlier guard's
killing test without failing it — GR-23's genesis snapshot left
`guard:controller_snapshot` surviving until GR-24, with the suite green
throughout. GR-32 adds a production caller that traverses all four `CONFIRM`
rows, so the question is live.

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

#### Residue

After both runs: `grep -rn '# mutation: removed' src/` returns nothing but the
tooling's own literals in `bin/mutate`, `bin/check-gr29-mutations` and
`bin/check-gr32-mutations`, and `git diff -- src` shows only the authorized
`controller.py` change. `driver.py` is untracked, so git cannot speak to it;
it was checked directly for the mutation marker and for its full guard count.

One interruption is on record and is accounted for. An earlier GR-32 run was
stopped deliberately at guard 6 of 27, to make a one-line correction in
`_creation_presenter` (it derived the approving choice positionally rather
than naming the kernel's `CREATE_CHOICE`). `bin/mutate`'s restore trap fired,
`driver.py` came back intact, residue was verified absent, and the run above
was restarted from guard 1 against the corrected tree. The five results from
the abandoned run are superseded, not additional.

## 8. Validation commands and results

Run with the project interpreter, on the final tree.

| command | result |
|---|---|
| `./.venv/bin/python -m pytest -q` | **1490 passed** in 182.07s |
| `./.venv/bin/python -m pytest -q tests/test_gr32_driver.py tests/test_gr32_composition.py` | **102 passed** in 23.77s |
| `./.venv/bin/python bin/check-governed-skills` | **OK** (wrappers, wrapper-dedup, authority, authorization-schema, authorization-gate, report-schema), exit 0 |
| `./bin/baseline` | `Collected: 1489 tests` / **1489 passed** in 187.03s |
| `./bin/check-gr32-mutations` | `All 27 guards killed; every restored suite passed.` exit 0 |
| `./bin/check-gr31-mutations` | `All 12 guards killed; every restored suite passed.` exit 0 |
| the five historical evidence files, together | **222 passed** in 39.25s |

`./bin/baseline` reports 1489 because it ran before the 102nd GR-32 test was
added in §8.1; the full-suite line above is the later, larger run. Both are
recorded as they happened rather than reconciled after the fact.

The five historical files were run as one group, exactly as the authorization
asks:

```
./.venv/bin/python -m pytest -q tests/test_r2_worker_crash_adoption.py \
  tests/test_r3_commit_crash_adoption.py tests/test_gr09_validation.py \
  tests/test_gr10_git_transaction.py tests/test_gr03_repository_lease.py
```

### 8.1 The GR-32 preflight, and a defect its first invocation exposed

The preflight was run against a throwaway repository created for the purpose,
both ways. The exact invocation:

```
GR32_PILOT_CREDENTIAL=<set> ./bin/pilot-run \
  --target <throwaway>/pilot-target \
  --governance-root <throwaway>/governance \
  --base-revision <that repository's HEAD> \
  --objective 'Add greet(name) to src/main.py, returning a greeting.' \
  --allow-path src/main.py --tracked-path src/main.py \
  --provider claude-code --origin https://api.anthropic.com \
  --secret-name pilot-inference-key --secret-env GR32_PILOT_CREDENTIAL
```

**Result: exit 0**, `"state": "READY"`, `"blocked_before": null`,
`"runtime_transitions_performed": 0`, every step `NOT_ATTEMPTED`,
`credential_observation.accepted: true`, and no governance root created. The
same invocation with the credential variable unset: **exit 1**,
`"state": "BLOCKED"`, `"blocked_before": "project.create"`, the reason naming
the variable and nothing about any value.

Nothing was invented to reach exit 0. The credential is a value supplied to
that invocation through the named variable; the provider check passed because
`claude 2.1.259` is genuinely on this host's `PATH`; no live inference was
attempted and no transition was performed.

**The defect.** The first invocation failed with
`ModuleNotFoundError: No module named 'rfc8785'`. `bin/pilot-run` carries a
`#!/usr/bin/env python3` shebang and now imports `gruntime.driver` — because
the credential check is `driver.preflight_credential` itself rather than a
second implementation of it — and the bare `python3` on `PATH` does not have
the runtime's dependencies. The test did not catch it: it invoked the script
through `sys.executable`, which is the suite's own interpreter, so the script
was always handed an environment it should have had to find for itself.

Both halves were fixed. `bin/pilot-run` re-execs once under the project
interpreter, located relative to the script rather than by an absolute path,
guarded by an environment marker so it cannot loop. "Already under it" is
decided by **where the interpreter was launched from**, not by what it
resolves to: a virtualenv's `bin/python` is a symlink to the system
interpreter, so a resolved comparison calls a bare `python3` "already the
project interpreter" and skips the re-exec — which is exactly the bug the
first fix attempt reproduced. The two tests now invoke the script through its
own shebang, and a third
(`test_bin_pilot_run_finds_the_runtime_without_being_handed_an_interpreter`)
runs it with `PYTHONPATH`, `VIRTUAL_ENV` and the re-exec marker scrubbed from
the environment, so the property is asserted directly rather than implied.

## 9. What the tests prove, by owner requirement

| requirement | test |
|---|---|
| 1. full offline supervised sequence 1–16 | `test_supervised_sequence_1_to_16_reaches_a_governed_revision`, `test_the_worker_proposal_is_what_lands` |
| 2. every CONFIRM cell refuses without its act, `match=` | `test_row_5_1_…`, `test_row_6_2_…`, `test_row_7_2_1_…`, `test_row_7_4_4_refuses_without_its_confirmation` |
| 3. snapshot staleness for all four APPROVE confirmations | the four `…_goes_stale_…` tests, plus `test_the_secret_approval_is_snapshot_bound_too` |
| 4. presenter `None` records nothing, transitions nothing | `test_a_refusing_presenter_records_no_decision_and_makes_no_transition` (9 acts), `test_a_declined_creation_creates_no_project` |
| 5. D2 credential preflight and non-leakage | the eight `…credential…` tests, the two source scans, and `test_bin_pilot_run_finds_the_runtime_without_being_handed_an_interpreter` |
| 6. D5 parameterization | `test_no_pilot_1_constant_is_compiled_into_src` (6 literals), `test_two_different_parameter_sets_compose_two_different_projects` |
| 7. D6 legacy gate | the six `…gated_command…` / `…unaffected…` tests and `test_the_gated_set_cannot_drift_from_the_parser_surface` |
| 8. five historical files pass unchanged | `test_the_historical_evidence_files_are_unmodified`, plus §8's grouped run |
| 9. `guard:gr31_preconditions_deferred` reachable and refusing | `test_a_validation_precondition_is_refused_by_the_deferral_guard`, `…review…` |
| 10. stable report shape, no secrets or environment values | `test_the_report_shape_is_stable_…`, `test_the_report_carries_no_environment_value` |
| 11. no snapshot or validation after `apply_commit` | `test_no_snapshot_and_no_validation_follows_apply_commit_in_one_invocation` |
| 12. post-materialization validation is observational | `test_observation_is_a_separate_entry_and_discharges_nothing` |

On requirement 11: `apply_commit` takes its own `POST_COMMIT` snapshot inside
the receipt transaction. That is the kernel settling the commit, not the driver
observing afterwards. What the test asserts is that the driver adds nothing
after it — no further step, and no `validation.executing` event at all.

On requirement 3: row 7.2-1 is the one case where a harder gate answers first.
Unattributed drift raises `REALITY_DRIFT` and sets `SUSPENDED_BY_DRIFT`, and
`_worker_gate` asks `_assert_may_initiate_effect` before it asks the row. The
test asserts both: the suspension in front, and — with that gate lifted by
monkeypatch, the pattern `CLAUDE.md` records for GR-24 — row 7.2-1 behind it,
refusing the confirmation `HD-INV-4` had already staled.

## 10. Session lifetime and restart

One process, one controller epoch, one relay. The relay lives in the memory of
the process that configured it and the epoch fences worker effects, so steps
12–16 are one uninterrupted session by construction; two CLI processes are two
epochs and two relays. A restart is `PilotSession.resume`: a new epoch,
`recover(project_id)`, a report, and a stop for the owner. It never resumes
steps 12–16 (`test_a_restart_reports_recovery_and_stops`).

## 11. Failure contract

At every step: refuse, report, stop. The session records the step — requested
act, observed result, decision id, receipt or escalation identity, refusal type
and refusal text — and re-raises the kernel's own typed error, so the caller
sees the refusal that happened rather than a driver's paraphrase of it.
Nothing retries, substitutes, fabricates a decision, resets, rolls back a
repository effect that already landed, or continues past a typed refusal.

A stale decision, a reconciled or ambiguous worker or commit effect, and a
suspension each arrive as one of those typed errors and each stops the session
for the owner. Nothing clears a suspension.

**The boundary of the report, stated deliberately.** `_step` records and
re-raises `GovernedRuntimeError` — the runtime's whole refusal taxonomy. An
exception outside it is not a governed outcome, is not dressed up as one, and
propagates with the step still marked `NOT_ATTEMPTED`; `drive()` likewise
catches only `GovernedRuntimeError`, so such a failure produces a traceback
rather than a report claiming a governed refusal took place. That is the
intended reading: a bug in the driver is a bug, not a refusal, and the report
is a record of governed acts.

## 12. Remediation — `gr32-remediation-001`

Authorization `gr32-remediation-001` (skill `governed-stage-implementer`, mode
`remediation`, OWNER, `2026-09-24T08:03:50Z`), answering the six findings of
`gr32-implementation-review-001`. Bounded to the same nine paths; `D1`–`D6`,
the plan, every deferred item (`B3`, `B4`, `B6`, `B7`, the GR-09/GR-17 egress
gap) and the uncommitted candidate are preserved. No tenth path was touched,
and no historical review or design record was edited.

Pre-edit verification: `HEAD` `bc5ae31cb729f4c4aac678e39419b10aa1524f48`,
phase line `GR-32`, working tree exactly the nine-path candidate, nothing
staged, `git diff -- src` showing only the candidate's `controller.py` change
and no mutation marker in `src/`.

**RED evidence.** Each finding was reproduced against the unremediated
candidate with an offline probe (a fixture credential, a fake `claude`
executable, throwaway repositories), before any edit:

| finding | reproduction on the unremediated candidate |
|---|---|
| F-001 | `python -m gruntime.controller --provider nonesuch pilot …` → exit 1, **empty stdout**, `PolicyDenied: unknown provider 'nonesuch'` traceback on stderr. An incomplete `PilotParameters` → `PolicyDenied` raised with the report left `state RUNNING`, `stopped_at None`, **0 steps** |
| F-002 | `bin/pilot-run --provider claude-code` with a `claude` that echoes `$GR32_PILOT_CREDENTIAL` → exit 0, `READY`, **credential in stdout: True**; the probe's environment contained both the variable and its value |
| F-003 | worker `CREATE` over an existing `src/main.py` → `MATERIALIZED`, intent op **`MODIFY`**; worker `MODIFY` with `before_digest sha256:000…0` → `MATERIALIZED` |
| F-004 | `/usr/bin/python3 bin/pilot-run …` with `GRUNTIME_PILOT_REEXEC=1`, `PATH=/usr/bin:/bin` → exit 1, stdout not JSON, `ModuleNotFoundError: No module named 'rfc8785'` traceback |
| F-005 | `validation=None` → step 11 `OK` with `{'bound': []}`, `MATERIALIZED` at a new revision |
| F-006 | `Budget(3600000, 100, 100.0, 100, 100, 100)` present in `driver.py` as the `PilotParameters.budget` default; `pilot --help` offered **no** `--budget-*` flag |

The RED tests below were written after the probes and run green against the
remediated tree; they were not separately run red against the unremediated
one, because the candidate is uncommitted and no pre-remediation copy of it
was retained. The probe output above is the RED evidence of record.

### 12.1 Finding by finding

**GR32-F-001 — BLOCKER — FIXED.** *Every typed refusal on the driver surface
is a stopped report.*
- `driver.compose_runtime` is the composition, split out of `open_runtime`
  (which now wraps it); on a typed refusal it closes the store it opened and
  re-raises. `drive()` catches `GovernedRuntimeError` from it and returns a
  `STOPPED` report whose step 1 is `runtime.compose`, `REFUSED`, with the
  kernel's type and text, exit 1.
- `run()`'s pre-step checks are now step 1 (`runtime.compose`) inside `_step`,
  so a refused parameter set is a stopped step, never a `RUNNING` report with
  nothing recorded.
- `record_refusal` is the one refusal record, shared by `_step` and the
  composition path.
- Unchanged: only `GovernedRuntimeError` is a refusal. Nothing catches
  `BaseException` to produce JSON; a defect still propagates as one (§11).
  Nothing retries, substitutes or continues.
- `test_an_unknown_provider_is_a_stopped_json_report_not_a_traceback`
  (the reviewer's reproduction, as a subprocess through the module entry
  point), `test_a_missing_provider_executable_is_a_stopped_report`,
  `test_an_incomplete_parameter_set_is_a_stopped_step_not_a_running_report`;
  `test_running_a_pilot_on_an_observation_parameter_set_is_refused` previously
  asserted `steps == []` — the defect itself — and now asserts `STOPPED` at
  step 1.

**GR32-F-002 — BLOCKER — FIXED.** *The preflight neither hands the credential
to the provider probe nor emits it.*
- `bin/pilot-run` `probe_environment`: the `--version` probe runs with `PATH`
  and `LC_ALL=C` only — no credential variable, no credential name, nothing
  else inherited (`guard:gr32_probe_environment`).
- `secret_free`: the last act before printing, over the whole serialized
  report, against the value the named variable actually holds — not a fixture.
  A report containing it is replaced by a `BLOCKED` report that repeats
  nothing of the original (`guard:gr32_preflight_report_secret_free`). `main`
  now has one emit point, so no path prints around the check.
- No credential store is read; the variable's **name** is still reported, its
  value never.
- `test_a_hostile_provider_probe_cannot_see_or_echo_the_credential` (the
  reviewer's reproduction: a `claude` that dumps its environment to a spy file
  and echoes the variable on stdout and stderr — the spy shows neither the
  value nor the name, and the only keys are `PATH`, `LC_ALL` and what the
  shell adds itself); `test_a_provider_that_prints_the_credential_anyway_blocks_the_whole_report`
  (a provider that knows a *different* offline value without the environment —
  proves the output check follows the configured value).

**GR32-F-003 — BLOCKER — FIXED.** *The worker's operation and `before_digest`
are proved against the governed base before `propose_commit`.*
- `map_proposal` takes `base_index` and `ProposalMapping` keeps `op` and
  `before_digest`. Four guards, each one line:
  `gr32_proposal_create_absent` (CREATE only where the path is absent),
  `gr32_proposal_create_before` (a CREATE claims no prior identity),
  `gr32_proposal_modify_present` (MODIFY only where the path exists),
  `gr32_proposal_modify_before` (MODIFY's `before_digest` equals the base
  content digest — missing, stale or wrong is refused). Nothing is translated
  between CREATE and MODIFY.
- `_propose` reads the base through the existing
  `Controller.governed_repo(project_id, create=False)` → `head_revision()` →
  `file_index()`: the governed worktree once it exists, before that the
  workspace repository whose `HEAD` `ensure_worktree` would create it at. It
  creates no worktree and takes no lease. The refusal precedes
  `propose_commit`, so it leaves no `CommitIntent`. The report records the
  revision validated against (`validated_against`).
- `propose_commit` and every kernel transition are unchanged
  (`test_propose_commit_was_not_widened` still passes).
- End to end: valid CREATE, CREATE over an existing file (refused, no
  intent, no revision), valid MODIFY with the matching digest, MODIFY with a
  stale and with a missing `before_digest` (refused, no intent, no revision),
  MODIFY of an absent path; plus unit cases for all four guards.
- Residual, stated: the base is read, then `propose_commit` reads it again.
  Both happen in the one session process under one epoch with nothing between
  them, so there is no in-session writer; a concurrent writer to the governed
  line outside the runtime is what `verify_head` at `authorize_commit`
  (`guard:commit_authorize_base`) already refuses.

**GR32-F-004 — MINOR — FIXED.** *The re-exec marker is not trusted because a
caller set it.*
- The launch-path check alone stops the second invocation from re-execing.
  The marker is now only a loop guard and is honoured only when its value is
  `<current pid>:<project interpreter>`: `execve` keeps the pid, so the
  marker the script sets names the process that re-exec'd, and a caller's
  `GRUNTIME_PILOT_REEXEC=1` (or any other value) is ignored.
- An `ImportError` from the runtime is now a `BLOCKED` preflight naming the
  interpreter, not a traceback.
- Direct shebang execution (the three existing tests) and symlink execution
  (the script resolves `__file__` before re-exec, unchanged) remain supported.
- `test_a_caller_supplied_reexec_marker_does_not_skip_the_reexec` (the
  reviewer's reproduction: `/usr/bin/python3`, scrubbed `PATH`,
  `GRUNTIME_PILOT_REEXEC=1` → exit 0, JSON, no traceback);
  `test_an_unimportable_runtime_is_a_blocked_preflight_not_a_traceback`.

**GR32-F-005 — BLOCKER — FIXED.** *The validation plan is mandatory.*
- Step 1 refuses a pilot with no `ValidationPlan`
  (`guard:gr32_validation_plan_required`) before any transition, so no
  project, no decision and no revision. `_bind_validations` lost its
  `plan is None → OK, bound: []` branch; step 11 cannot report `OK` with
  nothing bound.
- Unchanged: `guard:gr32_validation_network_none` still refuses `ALLOWLIST`
  and `ANY` at step 11; the catalog's own checks still refuse a malformed
  plan there; `contract.required_validations` is still empty and no commit
  validation precondition is bound (`B6`/`B7` deferred,
  `guard:gr31_preconditions_deferred` untouched); observational validation is
  still the separate `observe` entry and discharges nothing.
- `test_a_pilot_with_no_validation_plan_is_refused_before_any_transition`
  replaces `test_a_pilot_with_no_validation_plan_binds_nothing`, which asserted
  the defect; `test_an_invalid_validation_plan_is_refused_and_nothing_materializes`;
  `test_only_a_network_none_validation_operation_is_registered` (unchanged);
  `test_a_successful_pilot_binds_a_pinned_network_none_validation` (non-empty
  binding, the run's pinned slice resolves to a `network='NONE'` operation);
  `test_a_cli_pilot_without_a_validation_plan_is_a_stopped_report`.

**GR32-F-006 — BLOCKER — FIXED.** *The pilot budget is a runtime input.*
- The literal is gone. `PilotParameters.budget` defaults to `None`, and step 1
  refuses a budget that is absent, negative, non-numeric or the all-zero
  `Budget()` an unprovisioned project already holds
  (`guard:gr32_budget_supplied`, predicate `budget_is_supplied`).
- `BUDGET_FIELDS` is read off `models.Budget`; `build_parser` derives one
  **required** `--budget-<field>` flag per field, typed as the model types it,
  with no default, and `parameters_from` constructs the existing `Budget` from
  them. No second budget model.
- The requested budget is reported in `parameters.budget` and step 1's
  detail; step 5 still records the owner's decision on it.
- `test_the_recorded_budget_is_the_one_supplied` (two distinct budgets; the
  project row and the contract ceiling each equal what was supplied),
  `test_a_missing_or_inadmissible_budget_is_refused_before_any_transition`
  (`None`, zero, negative), `test_no_budget_is_compiled_into_the_driver`,
  `test_the_cli_budget_is_constructed_from_the_flags` (two distinct CLI sets),
  `test_the_cli_refuses_a_pilot_with_no_budget_flags`.
- Observed, not changed: `StageContract`'s schema types `cost_units` as an
  integer while `Budget.cost_units` is a float, so a fractional cost is
  granted at step 5 and then refused at step 7. That is the kernel's existing
  schema, outside these findings, and is recorded rather than altered.

### 12.2 Paths changed by the remediation

All within the authorization's nine; no tenth path.

| path | change |
|---|---|
| `src/gruntime/driver.py` | F-001, F-003, F-005, F-006 |
| `src/gruntime/controller.py` | F-006: `--budget-*` flags in `build_parser` |
| `bin/pilot-run` | F-002, F-004 |
| `bin/check-gr32-mutations` | covers `bin/pilot-run`; `FILES` now repository-relative |
| `tests/test_gr32_driver.py` | F-001, F-003, F-005, F-006 regressions; two defect-encoding assertions replaced |
| `tests/test_gr32_composition.py` | F-001, F-002, F-004, F-005, F-006 regressions; CLI helper supplies budget and plan |
| `docs/gr32-validation.md` | this section, and the two-records note at the top |
| `CLAUDE.md` | GR-32 statements the remediation made incomplete |

`tests/gr32_support.py` needed no change: it already supplied an explicit
fixture budget and a validation plan.

### 12.3 Mutation results (remediation)

Run sequentially, after every source edit, with no edit during either run;
needles are AST-derived whole guard statements. Each mutant turned the suite
red; each restored suite passed 1520. Logs: the session's scratch
`gr32-mutations.out` and `gr31-mutations.out`; machine record
`.evidence/gr32-mutations.json` (gitignored).

`bin/check-gr32-mutations` — **35/35 KILLED, 0 SURVIVED, 0 ERROR** (27 original,
8 added by the remediation). The eight new:

| guard | site | killed by |
|---|---|---|
| `gr32_proposal_create_absent` | `driver.py:588` | CREATE over an existing file |
| `gr32_proposal_create_before` | `driver.py:589` | CREATE claiming a `before_digest` |
| `gr32_proposal_modify_present` | `driver.py:590` | MODIFY of an absent path |
| `gr32_proposal_modify_before` | `driver.py:591` | stale / missing `before_digest` |
| `gr32_budget_supplied` | `driver.py:799` | budget `None`, zero, negative |
| `gr32_validation_plan_required` | `driver.py:800` | pilot without a plan (API and CLI) |
| `gr32_probe_environment` | `bin/pilot-run:210` | hostile provider probe |
| `gr32_preflight_report_secret_free` | `bin/pilot-run:310` | provider printing the credential |

`gr32_pilot_parameters_complete` moved from `run()`'s preamble into step 1 at
`driver.py:798` and is still killed. Line numbers of the other 26 shifted;
none was removed or weakened.

`bin/check-gr31-mutations` — **12/12 KILLED, 0 SURVIVED, 0 ERROR**
(re-verification; all 12 GR-31 guards unchanged).

Residue: after both runs `git diff -- src` shows only the candidate's
`controller.py` change, `src/` and `bin/pilot-run` hold no
`# mutation: removed` marker, and nothing is staged.

### 12.4 Validation results (remediation, final tree)

| command | result |
|---|---|
| `python -m pytest -q` | 1520 passed |
| `python -m pytest -q tests/test_gr32_driver.py tests/test_gr32_composition.py` | 132 passed |
| `python bin/check-governed-skills` | OK, exit 0 |
| the five historical files (§5) | 222 passed; bytes identical to `HEAD` |
| `./bin/check-gr32-mutations` | 35/35 KILLED, exit 0 |
| `./bin/check-gr31-mutations` | 12/12 KILLED, exit 0 |
| `git diff --check HEAD` | clean, exit 0 |

### 12.5 Open after remediation

None of GR32-F-001..006. Unchanged and still open, as before: `B3`, `B4`,
`B6`, `B7`, the GR-09/GR-17 egress gap, and the GR32-P-002 kernel window (§4).
Noted in F-006 and not changed: the fractional `cost_units` schema mismatch.

## 13. Second remediation — `gr32-remediation-002`

Authorization `gr32-remediation-002` (skill `governed-stage-implementer`, mode
`remediation`, OWNER, `2026-09-25T05:12:54Z`), answering the three findings
independent closure review `gr32-closure-review-001` left open under its
verdict `GR32_CLOSURE_FAILED`: `GR32-F-002` (OPEN, BLOCKER), `GR32-F-004`
(OPEN, MINOR) and `GR32-R-001` (NEW, BLOCKER). That review recorded F-001,
F-003, F-005 and F-006 CLOSED; they are not reopened here. Scope was eight
paths: the nine-path candidate minus `src/gruntime/controller.py`, which this
remediation did not touch (last modified `2026-09-24T08:14:57Z`, under
`gr32-remediation-001`; SHA-256 at the end of this remediation
`faba0783d245daa5d7f0ffba5ab9a75d3209fe46c344c85298510081d28b537f`). No kernel
file, schema, model, historical review or design record changed. Where §13
and §12 disagree about the current tree, §13 is the current one.

Pre-edit verification: authorization validated against
`.agents/governance/authorization.schema.json` (Draft 2020-12, format
checking); `HEAD` `bc5ae31cb729f4c4aac678e39419b10aa1524f48`; phase line
`GR-32`; working tree exactly the nine-path candidate; nothing staged; no
`bin/mutate` backup directory retained and every `src/` module compiles.

**Closure-review evidence, as the owner transmitted it.** F-002: a printable
fixture credential containing `"`, printed by an offline provider, passed
`secret_free`'s substring search over `json.dumps(report)` — JSON escaping
rewrote it — while the parsed READY report's `provider_observation.version`
held it whole. F-004: `GRUNTIME_PILOT_REEXEC=<caller pid>:<project
interpreter>` followed by `exec /usr/bin/python3` satisfied the marker
(`execve` keeps the pid) and skipped the re-exec. R-001: `cost_units = 0.5`
passed step 1, steps 2–6 created, provisioned, granted and allocated, and step
7 refused because `stage_contract.schema.json` types `cost_units` `integer`.

**RED evidence.** Reproduced against the unremediated candidate with offline
probes before any edit (fixture credentials, a fake `claude`, throwaway
repositories):

| finding | reproduction on the unremediated candidate |
|---|---|
| F-002 | credential `sk-gr32"quoted"-fixture-7a1` printed by `claude --version` → exit 0, `READY`; raw stdout contains the credential: **False**; parsed report contains it: **True**, in `provider_observation.version`. Same with `sk-gr32\back\slash-fixture-3c9`: `READY`, parsed report **True** |
| F-002 (control) | a probe that dumps its environment and echoes `$GR32_FIXTURE_CRED`: spy file holds neither value nor name — the F-001 remediation's sanitized probe environment already held |
| F-004 | `sh -c 'export GRUNTIME_PILOT_REEXEC="$$:<repo>/.venv/bin/python"; exec /usr/bin/python3 bin/pilot-run …'`, `PATH=/usr/bin:/bin`, no `PYTHONPATH`/`VIRTUAL_ENV` → exit 1, `BLOCKED`: `The runtime is not importable under /usr/bin/python3 (ModuleNotFoundError: No module named 'rfc8785')` — the re-exec was skipped |
| R-001 | `Budget(3600000, 100, 0.5, 100, 100, 100)` → step 1 `OK`, steps 2–6 `OK`, step 7 `contract.author` `REFUSED PolicyDenied`, **1 project row**. `2.25`: identical. `100.0`: `MATERIALIZED` at step 16 |

The new tests were written after the probes and run green against the
remediated tree; the probe output above is the RED evidence of record. The
same probe script, rerun after the edits, is the GREEN reproduction below.

### 13.1 Finding by finding

**GR32-F-002 — BLOCKER — FIXED.** *Secret filtering reads raw and semantic
values; nothing depends on searching serialized JSON.*
- `report_strings` yields every string of a structure — keys and values, at
  any depth — as it is. `carries_secret(secret, *texts)` is a plain substring
  test of the value the named variable actually holds against each raw
  string. Stdlib only, deliberately not the runtime's `SecretGuard`: this
  check must hold on the one path where the runtime is not importable, which
  is itself a report the script emits.
- Before the report: `refuse_secret_bearing_output` checks the provider
  probe's raw stdout **and** stderr, before either is put into any report
  object (`guard:gr32_probe_output_secret_free`, `bin/pilot-run:267`). A match
  raises a fixed-text refusal — the report is `BLOCKED`, carries no
  `provider_observation`, and repeats nothing the provider printed.
- At the end: `secret_free(report, text, secret)` asks two questions and emits
  only when both answers are no — does any parsed string of the report hold
  the credential, and does the exact text about to be printed hold it (an
  escape can spell a `\"`-bearing credential in output even where no one
  string holds it). Either yes replaces the report with a fixed-wording
  `BLOCKED` one (`guard:gr32_preflight_report_secret_free`,
  `bin/pilot-run:366`). The report is serialized once, the check is over that
  text, and that text is what is printed; the guard is one deletable line
  whose removal still prints, so a killed mutant is a test observing the leak,
  not a `NameError`.
- Unchanged: the probe environment is `PATH` and `LC_ALL=C` only
  (`guard:gr32_probe_environment`); no credential store is read; the variable
  is named, never discovered. No refusal text quotes the value.
- Tests (`tests/test_gr32_composition.py`):
  `test_provider_output_holding_a_json_sensitive_credential_is_blocked`
  (`"`, `\`, both), `test_provider_stderr_holding_the_credential_is_blocked`,
  `test_a_json_sensitive_credential_never_reaches_a_hostile_probe`,
  `test_a_credential_reaching_the_report_by_any_other_field_withholds_it`
  (`--objective`, `--secret-name`),
  `test_a_credential_spelled_only_by_an_escape_in_the_output_is_withheld`,
  `test_ordinary_provider_version_output_is_still_reported` (a version line
  with its own `"` and `\` is reported verbatim, `READY`). Each asserts: the
  credential in neither stdout nor stderr, in no parsed string of the report,
  and a deterministic `BLOCKED`/exit 1 with a fixed reason.
  `test_a_provider_that_prints_the_credential_anyway_blocks_the_whole_report`
  now asserts the probe-output refusal, which answers first.

**GR32-F-004 — MINOR — FIXED.** *No caller-set value decides the re-exec.*
- The marker is gone: `bin/pilot-run` neither sets nor reads
  `GRUNTIME_PILOT_REEXEC` (`test_the_script_no_longer_reads_a_reexec_marker`,
  over the AST, docstrings excepted).
- `running_in_project_venv()`: `Path(sys.prefix).resolve() ==
  (<runtime>/.venv).resolve()`. `site` sets `sys.prefix` to a virtualenv's
  root only when it has activated it, i.e. put its `site-packages` on the
  path. `reexec_under_project_interpreter` returns when that holds or no
  project interpreter exists (`guard:gr32_reexec_identity`,
  `bin/pilot-run:88`), and otherwise `execv`s `<runtime>/.venv/bin/python`.
- Loop prevention without a sentinel: the exec launches the interpreter by
  its own path, so the child's `sys.executable` is that path and it does not
  exec again (`guard:gr32_reexec_once`, `bin/pilot-run:90`) — even an
  interpreter that failed to activate the venv, which then fails to import
  the runtime and reports `BLOCKED`, never `READY`.
- **Why an environment value cannot bypass it**, observed on this host
  (Python 3.13.5): `PYTHONHOME=<venv>` under `/usr/bin/python3` does not start
  (fatal, no `encodings`: the venv has no standard library).
  `PYTHONEXECUTABLE=<venv>/bin/python` and `exec -a <venv>/bin/python` do
  yield `sys.prefix == <venv>` — and `import rfc8785, jsonschema` then
  succeeds, because `site` really activated the venv: what they produce *is*
  an interpreter in it. `-S` (no `site`) leaves `sys.prefix` at `/usr`, and
  combined with `PYTHONEXECUTABLE` it satisfies only the loop guard, which
  yields the `BLOCKED` import-failure report, not a skipped check. So every
  route to "not re-exec'd" is either the project interpreter or a BLOCKED
  preflight.
- Tests: `test_a_pid_forged_reexec_marker_does_not_skip_the_reexec` (the
  closure reproduction: `sh` exports `$$:<interpreter>` and execs a bare
  `python3` → exit 0, `READY`, credential accepted);
  `test_a_caller_supplied_reexec_marker_does_not_skip_the_reexec` (`=1`,
  unchanged); `test_a_symlinked_pilot_run_reaches_the_project_interpreter`;
  the three shebang tests (unchanged); unit tests on the decision with
  `os.execv` recorded — in the venv by prefix under either launch path: no
  exec; outside it with no marker, `1`, or `<pid>:<interpreter>`: exactly one
  exec of the project interpreter; the exec'd child: no second exec; no
  project interpreter: no exec.
  `test_an_unimportable_runtime_is_a_blocked_preflight_not_a_traceback`
  (unchanged) covers the import-failure report.

**GR32-R-001 — BLOCKER — FIXED.** *A budget the contract cannot carry is
refused at step 1.*
- `driver.budget_fits_contract(budget)` validates `_budget_document(budget)`
  — the very document step 7 writes as `budget_ceiling` — against
  `CONTRACT_BUDGET`, a `Draft202012Validator` over
  `contracts.SCHEMA["$defs"]["Budget"]`: the contract's own schema object,
  not a copy (`test_budget_fits_contract_is_the_contract_schema`).
- One guard line in step 1, after `gr32_budget_supplied` and before
  `gr32_validation_plan_required`: `guard:gr32_budget_contract_shape`
  (`driver.py:822`). Refusal is the normal `STOPPED` report at step 1
  (`runtime.compose`, `REFUSED`, `PolicyDenied`), quoting the budget exactly
  as supplied; zero transitions.
- It covers every field the schema types `integer`, not only `cost_units`. It
  changes no model: nothing is rounded, truncated or normalized, and
  `Budget`, `StageContract` and the schema are untouched. The underlying
  `Unit = float` vs `integer` mismatch is not solved and stays recorded
  (§12.1 F-006).
- An integral value written as a float is an integer to the schema, so
  `100.0` passes, as it always did at step 7.
- Tests (`tests/test_gr32_driver.py`):
  `test_a_fractional_cost_is_refused_at_step_1_before_any_transition`
  (`0.5`, `2.25`, `100.001`: stopped at 1, no project row, no decision row,
  no run, one revision, the parameters still carry the value supplied and the
  refusal quotes it); `test_any_fractional_budget_field_is_refused_at_step_1`
  (`wall_clock_ms`, `worker_invocations`, `commits` at `1.5`);
  `test_an_integral_cost_reaches_materialization_unaltered` (`100`, `100.0`:
  `MATERIALIZED`, reported and stored with the supplied value and type);
  `test_the_recorded_budget_is_the_one_supplied` (F-006's two distinct
  budgets, unchanged, still recorded exactly).

### 13.2 GREEN reproductions

The RED probe script, rerun on the remediated tree:

| probe | result |
|---|---|
| `"` credential printed by `--version` | exit 1, `BLOCKED`; raw stdout/stderr contain it: False/False; parsed report: False |
| `\` credential printed by `--version` | exit 1, `BLOCKED`; False/False; parsed: False |
| ordinary version output | exit 0, `READY` |
| hostile environment probe (`"` and `\` in the credential) | exit 0, `READY`; spy holds neither value nor name |
| pid-forged marker, `exec /usr/bin/python3` | exit 0, `READY` — re-exec'd |
| direct shebang, scrubbed `PYTHONPATH`/`VIRTUAL_ENV` | exit 0, `READY` |
| symlink | exit 0, `READY` |
| bare `/usr/bin/python3`, no marker | exit 0, `READY` |
| `cost_units` `0.5` / `2.25` | `STOPPED` at 1, `runtime.compose` `REFUSED PolicyDenied`, 0 project rows |
| `cost_units` `100.0` | `MATERIALIZED` at step 16 |

### 13.3 Regression preservation

| closed item | rechecked by |
|---|---|
| F-001 stopped refusal reports | its three tests, unchanged, pass; R-001's refusal is itself a step-1 `STOPPED` report |
| F-003 operation / `before_digest` fidelity | its four guards and every end-to-end case, unchanged, pass and are killed |
| F-005 mandatory `network='NONE'` plan | `gr32_validation_plan_required`, `gr32_validation_network_none`, unchanged, killed |
| F-006 explicit runtime budget | `gr32_budget_supplied` unchanged and killed; CLI flags unchanged; two distinct budgets recorded exactly |
| `D2` credential-shape preflight, `D6` legacy gate | unchanged guards, killed; `controller.py` not touched |
| four confirmation boundaries, run-before-contract, stop after `apply_commit`, separate observation, `guard:gr31_preconditions_deferred` | unchanged code; their tests pass; GR-31 mutations re-run |
| five historical evidence files | 222 passed; bytes identical to `HEAD` |

### 13.4 Paths changed by this remediation

| path | change |
|---|---|
| `bin/pilot-run` | F-002 raw/semantic secret checks; F-004 identity-based re-exec, marker removed |
| `src/gruntime/driver.py` | R-001 `budget_fits_contract`, `CONTRACT_BUDGET`, one step-1 guard |
| `bin/check-gr32-mutations` | `FILES` comment only; discovery already covers the new tags |
| `tests/test_gr32_composition.py` | F-002 and F-004 regressions; one assertion updated to the refusal that now answers first |
| `tests/test_gr32_driver.py` | R-001 regressions |
| `docs/gr32-validation.md` | this section and the records note at the top |
| `CLAUDE.md` | the three GR-32 statements this remediation made inaccurate |

`tests/gr32_support.py` needed no change. `src/gruntime/controller.py` was
outside scope and was not touched.

### 13.5 Mutation results (second remediation)

Run sequentially after the last source edit, with no edit to the tree during
either run; needles are AST-derived whole guard statements. Each mutant turned
the suite red and each restored suite passed; the trees under test were the
final `src/`, `bin/` and `tests/` recorded here (documentation was edited only
afterwards, and the full suite re-run, §13.6). Logs: the session's scratch
`gr32-mutations.out` and `gr31-mutations.out`; machine record
`.evidence/gr32-mutations.json` (gitignored).

`bin/check-gr32-mutations` — **39/39 KILLED, 0 SURVIVED, 0 ERROR** (35 from
§12.3, 4 added here). The four new:

| guard | site | killed by |
|---|---|---|
| `gr32_budget_contract_shape` | `driver.py:822` | fractional `cost_units` / other fields refused at step 1 |
| `gr32_reexec_identity` | `bin/pilot-run:88` | in-venv interpreter is not re-exec'd |
| `gr32_reexec_once` | `bin/pilot-run:90` | the exec'd child never execs again |
| `gr32_probe_output_secret_free` | `bin/pilot-run:267` | `"` / `\` / stderr credential in probe output |

`gr32_preflight_report_secret_free` (`bin/pilot-run:366`) is the same tag at
a reshaped site and is killed by the objective / secret-name / escape-only
tests. Line numbers of the other guards shifted; none was removed or
weakened.

`bin/check-gr31-mutations` — **12/12 KILLED, 0 SURVIVED, 0 ERROR**
(re-verification after the GR-32 run).

Residue: after both runs `src/gruntime/controller.py` matches its recorded
SHA-256, no `# mutation: removed` marker exists outside the mutation tools'
own source, no `bin/mutate` backup is retained, and nothing is staged.

### 13.6 Validation results (second remediation, final tree)

| command | result |
|---|---|
| `python -m pytest -q` | 1547 passed |
| `python -m pytest -q tests/test_gr32_driver.py tests/test_gr32_composition.py` | 159 passed |
| `python bin/check-governed-skills` | OK, exit 0 |
| the five historical files (§5) | 222 passed; bytes identical to `HEAD` |
| `./bin/check-gr32-mutations` | 39/39 KILLED, exit 0 |
| `./bin/check-gr31-mutations` | 12/12 KILLED, exit 0 |
| `git diff --check HEAD` | clean, exit 0 |

The suite figures are from the final tree, after `CLAUDE.md` was edited; this
section is the only later edit, and no test reads it.

### 13.7 Open after the second remediation

None of GR32-F-001..006 or GR32-R-001. Unchanged and still open: `B3`, `B4`,
`B6`, `B7`, the GR-09/GR-17 egress gap, the GR32-P-002 kernel window (§4),
and the underlying `Budget.cost_units` float vs contract-schema `integer`
mismatch, which R-001 guards against at the driver surface and does not
resolve.

## 14. Third remediation — `gr32-remediation-003`

Authorization `gr32-remediation-003` (skill `governed-stage-implementer`, mode
`remediation`, OWNER, `2026-09-25T16:07:44Z`), answering the one finding
independent closure review `gr32-closure-review-002` left open under its
verdict `GR32_CLOSURE_FAILED`: `GR32-F-002` (OPEN, BLOCKER). That review
recorded F-004 and R-001 CLOSED and raised no new finding; neither is
reopened here. Scope was six paths: `bin/pilot-run`,
`bin/check-gr32-mutations`, `tests/gr32_support.py`,
`tests/test_gr32_composition.py`, `docs/gr32-validation.md`, `CLAUDE.md`.
`src/gruntime/driver.py` and `src/gruntime/controller.py` were outside scope
and were not touched: their SHA-256 at the end of this remediation are
`58bd4cb43315f388d1d8a9a2a58a6fe50f713ed078c2069255df6264c360b664` (last
modified `2026-09-25T05:25:34Z`, under `gr32-remediation-002`) and
`faba0783d245daa5d7f0ffba5ab9a75d3209fe46c344c85298510081d28b537f` (unchanged
since §13). No kernel file, schema, model, historical review or design record
changed.

Pre-edit verification: authorization validated against
`.agents/governance/authorization.schema.json` (Draft 2020-12, format
checking); `HEAD` `bc5ae31cb729f4c4aac678e39419b10aa1524f48`; phase line
`GR-32`; working tree exactly the nine-path candidate; nothing staged; no
`bin/mutate` backup retained.

### 14.1 `GR32-F-002` — the provider probe's launch surface

**Closure-review evidence, as the owner transmitted it.** `bin/pilot-run`
forwarded the caller's `PATH` verbatim to the provider `--version` probe
(`probe_environment` returned `{'PATH': environment['PATH'], 'LC_ALL': 'C'}`).
A non-sensitive fixture credential placed in `PATH` was recovered whole by a
hostile offline provider that dumped its environment. The later BLOCKED
report did not cure it: the provider had already received the value.

**RED evidence.** The new tests, run against the remediation-002 tree before
any edit to `bin/pilot-run`:

| test | result on the unremediated candidate |
|---|---|
| A. credential as a `PATH` entry, spying provider | FAILED: `the credential reached the probe via PATH`; the spy file held `PATH=…/sk-gr32-offline-4f21a8c07bd94e3f:…` |
| B. credential in an unrelated variable's value and in an unrelated key | passed — remediation-002's two-key environment already excluded it; kept as regression coverage |
| C. credential in the executable's directory | FAILED: `the provider executed despite a secret-bearing launch path` |
| C′. credential in the executable's symlink target filename | FAILED: the provider executed |
| D. launch-surface invariant, per element (argv, executable, env key, env value, cwd) | FAILED: `refuse_secret_bearing_launch` did not exist |
| probe environment built from the executable, not the caller | FAILED: `probe_environment` read the caller's `PATH` |

9 failed, 1 passed.

**Remediation.** `bin/pilot-run` only:

- The executable is resolved in the preflight process (`shutil.which` against
  this process's `PATH`) and made absolute (`os.path.abspath`), so the child
  never needs the caller's `PATH` to find it and a relative `PATH` entry can
  no longer resolve against the child's different working directory.
- `probe_environment(executable)` now takes the resolved executable and reads
  nothing of the caller's environment. It returns exactly `PATH` and
  `LC_ALL=C`, where `PATH` is constructed: the executable's own directory, its
  link target's directory, then the fixed `PROBE_SYSTEM_PATH`
  (`/usr/local/bin`, `/usr/bin`, `/bin`), deduplicated. The first two let a
  `#!/usr/bin/env node` shim find the `node` installed beside it; the last lets
  a shell launcher find ordinary utilities. The caller's `PATH` is never
  forwarded. `guard:gr32_probe_environment` keeps its tag at the new
  assignment; the line before it is `environment = None` (subprocess's
  "inherit everything"), so deleting the guard is a real exposure.
- New `refuse_secret_bearing_launch(secret, argv, environment, cwd)`, called
  on the line immediately before `subprocess.run`
  (`guard:gr32_probe_launch_secret_free`). It checks every argv string
  (`argv[0]` is the executable path), the realpath of `argv[0]`, the working
  directory (`PROBE_CWD = '/tmp'`), and every environment key and value —
  `None` treated as this process's own environment, which is what subprocess
  would pass — for the value the named variable holds, with the existing
  `carries_secret` substring test. Any hit raises a fixed-text `ValueError`;
  nothing is normalized, encoded, truncated or redacted to let the launch
  proceed, and the probe is not started. The argv is fixed at
  `[executable, '--version']`, so the only caller-influenced argv material is
  the executable path, which this checks.
- `refuse_secret_bearing_output` (`guard:gr32_probe_output_secret_free`) and
  `secret_free` (`guard:gr32_preflight_report_secret_free`) are unchanged and
  remain defense in depth.

No credential discovery changed: nothing reads a credential file or home
directory, and `driver.preflight_credential`, the relay and D2 are untouched.

**Test changes** (`tests/test_gr32_composition.py`): the `preflight` helper
takes an optional `label` for its target and governance directory names
(default `bindir.name`, as before), so a test whose provider directory holds
the credential does not also put it in those paths. New helper `spying` and
six tests (ten cases): A, B, C, C′, D ×5, and
`test_the_probe_environment_is_built_not_inherited`. Every earlier F-002
test is unchanged, including the `"`, `\` and both-kinds output cases, the
stderr case, the escape-only case and the ordinary-version case.
`tests/gr32_support.py` needed no change.

**GREEN.** `tests/test_gr32_driver.py tests/test_gr32_composition.py`: 169
passed. A: the provider runs, its full environment dump, `$0` and arguments
hold no occurrence of the credential, stdout/stderr hold none, `READY`, version
`claude 3.1`. B: the dump holds neither the value nor the unrelated variable,
`READY`. C and C′: the provider's `ran` marker is never created, exit 1,
`BLOCKED`, reason names the launch surface, and the credential is in no stream
and no parsed report string. D: each of the five elements refuses with
`match="launch surface"`, the refusal text holds none of the secret, and an
empty secret or a clean surface passes. E (ordinary safe provider): A itself
and the existing `test_ordinary_provider_version_output_is_still_reported`,
`READY`.

**Status: FIXED.**

### 14.2 Regression preservation

| closed item | rechecked by |
|---|---|
| F-004 identity-based re-exec | `gr32_reexec_identity`, `gr32_reexec_once` unchanged and KILLED; every F-004 test passes unedited |
| R-001 contract-shape budget | `gr32_budget_contract_shape` in `driver.py`, not touched, KILLED |
| F-001, F-003, F-005, F-006 | their guards unchanged and KILLED; their tests pass |
| D2 credential preflight, D6 legacy gate | `driver.py` / `controller.py` not touched; guards KILLED |
| four confirmation boundaries, proposal fidelity, run-before-contract, stop after `apply_commit`, separate observation, `guard:gr31_preconditions_deferred` | unchanged code; tests pass; GR-31 mutations 12/12 |
| five historical evidence files | 222 passed; bytes identical to `HEAD` |

### 14.3 Paths changed by this remediation

| path | change |
|---|---|
| `bin/pilot-run` | resolved-executable launch, constructed probe `PATH`, `refuse_secret_bearing_launch` and its guard |
| `bin/check-gr32-mutations` | `FILES` comment only (four F-002 guards); discovery already covers the new tag |
| `tests/test_gr32_composition.py` | `preflight` `label`, `spying`, six new tests (ten cases) |
| `docs/gr32-validation.md` | this section and one sentence appended to the records note |
| `CLAUDE.md` | the one GR-32 sentence about the probe environment |

### 14.4 Mutation results (third remediation)

Run sequentially after the last source edit, with no edit to the tree during
either run; needles are AST-derived whole guard statements. Documentation was
edited only afterwards and the suite re-run (§14.5). SHA-256 of every
`src/gruntime/*.py` and `bin/pilot-run` was recorded before the runs and
matched after them. Logs: the session's scratch `gr32-mutations.out` and
`gr31-mutations.out`; machine record `.evidence/gr32-mutations.json`
(gitignored).

`bin/check-gr32-mutations` — **40 total / 40 KILLED / 0 SURVIVED / 0 ERROR**
(39 from §13.5, 1 added here). Each restored suite: 1557 passed.

| guard | site | mutant | killed by |
|---|---|---|---|
| `gr32_probe_launch_secret_free` (new) | `bin/pilot-run:310` | 2 failed | C and C′: with the guard deleted, the secret-bearing executable path is launched and the hostile provider runs and dumps it — the exposure itself, not an unrelated exception |
| `gr32_probe_environment` | `bin/pilot-run:309` | 10 failed | with it deleted `environment` stays `None`, the child would inherit everything, and the launch invariant refuses on the credential variable, so every READY probe test goes BLOCKED |
| `gr32_probe_output_secret_free` | `bin/pilot-run:313` | killed | `"` / `\` / stderr credential in probe output |
| `gr32_preflight_report_secret_free` | `bin/pilot-run:412` | killed | objective / secret-name / escape-only |

Every other guard is at the site §13.5 lists, or shifted by line only; none was
removed or weakened.

`bin/check-gr31-mutations` — **12 total / 12 KILLED / 0 SURVIVED / 0 ERROR**.

Residue: after both runs every recorded SHA-256 matched, no
`# mutation: removed` marker exists outside the mutation tools' own source, no
`bin/mutate` backup is retained, and nothing is staged.

### 14.5 Validation results (third remediation, final tree)

| command | result |
|---|---|
| `python -m pytest -q` | 1557 passed |
| `python -m pytest -q tests/test_gr32_driver.py tests/test_gr32_composition.py` | 169 passed |
| `python bin/check-governed-skills` | OK, exit 0 |
| the five historical files (§5) | 222 passed; bytes identical to `HEAD` |
| `./bin/check-gr32-mutations` | 40/40 KILLED, exit 0 |
| `./bin/check-gr31-mutations` | 12/12 KILLED, exit 0 |
| `git diff --check HEAD` | clean, exit 0 |

The suite figures were re-run on the final tree, after `CLAUDE.md` and this
document were edited.

### 14.6 Open after the third remediation

None of GR32-F-001..006 or GR32-R-001. Unchanged and still open: `B3`, `B4`,
`B6`, `B7`, the GR-09/GR-17 egress gap, the GR32-P-002 kernel window (§4),
and the `Budget.cost_units` float vs contract-schema `integer` mismatch. The
`git` subprocesses `inspect_target` runs still inherit the caller's
environment minus `GIT_*`; they are not the provider probe, launch no
provider code, and are outside this finding.
