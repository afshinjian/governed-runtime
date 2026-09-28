# Governed Runtime
Project-agnostic governed AI software-development runtime.
Phase: GR-33 (first supervised automation pilot).
Rules:
- No HIR / automate-implementation identifiers in core.
- No Claude/Codex/Hermes specifics outside adapters.
- Tables and JSON Schema over prose.
- Controller owns all state transitions; workers only propose.

## Suspension evidence
- Choice (a): every escalation declaring non-NONE suspension applies it to
  the project and, when targeted, the run. The claim, state and audit events
  persist atomically. NONE declares no suspension and never clears one.
- Project suspension_ref is required iff suspension != NONE; controller
  transitions and store reads/writes enforce both directions.
- Validation: [suspension closure](docs/suspension-validation.md).

## Known gaps
- GR-09/GR-17: validation egress is gated but unavailable in both forms.
  ALLOWLIST is refused outright (validation.py:130 — no enforcing adapter).
  ANY adds `--share-net` (validation.py:134) and is now gated by
  guard:execute_network_egress (GR-17), but net.egress.any is HUMAN-tier and
  execute_validation has no parameter to present an exercise decision, so it
  is unreachable rather than merely denied. Closing that needs an
  exercise-decision parameter plumbed from the CLI plus atomic consumption in
  the transition, mirroring relay_controller. Ungated egress is closed.
- Validation execution now checks proc.exec.validation, for rows 7.1-2 and
  7.1-3 only. transitions.py:1153 and :1158 declare it; execute_validation
  proves it at guard:gr31_validation_exec_authority (GR-31 C8), immediately
  ahead of guard:execute_network_egress so a denial leaves no
  validation.executing event for recovery to reconcile. Same path as
  FINDINGS-02 F02-001, not covered by it; was deferred from GR-17.
  FINDINGS-03 answered the cap= question: policy.resolve enforces
  required_capability but had no production caller (F03-001). GR-28 closed
  F03-002 and F03-003, and the §7.4 portion of F03-001 — COMMIT_INTENT
  transitions now enforce the capability their row declares (14 of 145 rows).
  GR-31 adds these two. The other 129 rows still consume no declaration, so
  F03-001 remains OPEN, and F04-004 is unaffected — it closes only when all of
  F03-001..003 close.
- GR-09: the missing-bwrap path is untested — this host has bwrap, so no test
  exercises the ERROR receipt. Verify before running on another host.
- Storage v1→…→v5 (STORAGE_VERSION = 5 since GR-07) all refuse older schemas
  with no migration path. Acceptable while pre-release; must be resolved before
  the first persistent pilot database.
- GR-07: no test exercises a live provider. The subprocess transport is offline;
  the full chain has never run against real Claude/Codex output. First live
  invocation is unproven territory.
- GR-08: ToolBridge now provides the governed inference relay. Worker egress
  requires a live grant and stays within one HTTPS origin; ProcessTransport
  and validation isolation are unchanged. See [relay evidence](docs/gr08-validation.md).
- DESIGN gap: no candidate observation exists. W-INV-2 keeps proposals out of the
  workspace until apply_commit, which materializes and commits in one step, so
  there is no moment at which proposed contents are on disk and uncommitted.
  Precommit validation is therefore unimplementable as designed. RealitySnapshot
  has no root field and scope is [Glob] over workspace-relative paths, so this
  cannot be closed by wiring alone. DESIGN-02 is frozen as a proposal
  (design-02-frozen); its amendments are not in frozen text and not implemented.
- GR-24: guard:controller_snapshot and guard:gr07_snapshot. Since GR-23 every
  project has a genesis snapshot, so their `is None` conjunct is unreachable in
  production, and a non-COMPLETE snapshot is refused first by
  _assert_may_initiate_effect. Each guard acts only if a snapshot lands between
  the gate's read and its own; tests cover that by monkeypatch.
- GR-29 closed F04-001. record_decision used to accept a HUMAN actor with no
  principal_key_id, which domain-model.md:58 requires; key presence was
  checked only where some decisions are used — genesis
  (_is_authenticated_human), contract activation (contract_controller.py
  approval; authority.py human_covers and basis check), exercise decisions
  (guard:gr06_exercise_decision) and secret-read approval
  (guard:gr08_secret_approval). One predicate now enforces
  `actor_kind = HUMAN ⇒ principal_key_id` at three boundaries:
  decision.require_principal_key (guard:decision_principal_key_iff), called
  from _record_decision before anything is built, appended or persisted
  (guard:decision_principal_key_record), from StateStore.put_decision
  (guard:decision_principal_key_put) and from _decision_from_row, the single
  hydration point behind get_decision and list_decisions
  (guard:decision_principal_key_read). A malformed row already on disk fails
  closed with IntegrityViolation on every read and is never repaired,
  coerced, migrated or backfilled; a listing refuses whole rather than
  omitting the row. No pre-release database is known to hold one, and nothing
  scans for one — the first read of such a row is where it would surface.
  Estate-wide F04-002 cleanup was not done: only the one match= that keeps
  guard:genesis_approver killed was added.
  GR29-R01: one of the places that first read happens is take_snapshot, which
  publishes the new observation and only then derives staleness over every
  decision (HD-INV-4), with the drift escalation after that. A refusal there
  used to leave the project holding a superseded reality, approvals still
  VALID against it, suspension NONE and REALITY_DRIFT unreached. The refusal
  is unchanged; controller.py _suspend_uninterpreted_snapshot
  (guard:snapshot_interpretation_suspends) now raises an INTEGRITY_VIOLATION
  escalation applying SUSPENDED_BY_INTEGRITY (§4 row 4-7) before re-raising,
  so the published-but-uninterpreted observation bars every new invocation,
  validation and commit exactly as the drift suspension it could not reach
  would have. It answers any failure of that derivation step, not only an
  integrity refusal, and where take_snapshot is nested in a caller's
  transaction (_settle_commit_receipt) the suspension rolls back with the
  publication it answers for. Clearing it is a human's act (§4 row 4-20); the
  malformed row is still never repaired, so on such a project the derivation
  refuses again on every later snapshot.
- No per-stage mutation evidence file exists for GR-17, GR-23 or GR-24; their
  kills are persisted only as bin/mutate summary lines in
  docs/evidence/recheck-20260916.txt. GR-31 and GR-32 do not join them:
  docs/gr31-validation.md inlines every summary and states its one log root,
  and docs/gr32-validation.md does the same for GR-32.
  Of the committed JSON records, gr07 and
  gr08 inline their summaries and cite no logs; gr06 inlines summaries and also
  cites logs; gr06, gr09, gr10 and suspension cite full logs that exist only
  under the gitignored .evidence/ (gr09's paths are relative to
  .evidence/gr09/, with no root field).

## Supervision gates
GR-31 gives the runtime a governed, per-field, human-authorized path to
provision a project, and makes the three SUPERVISED CONFIRM cells the first
supervised pilot traverses refuse without the human act their row declares.
Evidence: [GR-31 validation](docs/gr31-validation.md).

- Provisioning is two operations, not one: `set_capability_ceiling` and
  `grant_project_budget` (contract_controller.py). Each is one BEGIN IMMEDIATE
  transaction that appends its event, consumes its decision and writes its
  field together. Before GR-31 no production code wrote either field, so a
  project created through `create_project` could activate nothing; every test
  provisioned by writing the project row directly.
- The ceiling decision is CONSUMED by provisioning, deliberately. `human_covers`
  accepts a GRANT_CAPABILITY over PROJECT scoped PROJECT as an *activation
  grant basis*, so a ceiling decision left VALID would both bound the ceiling
  and confer everything in it. Activation needs its own, separate grant
  decision (test_ceiling_decision_cannot_also_grant).
- `project.ceiling.set` is the one register entry GR-31 adds (authority.py:26).
  No DecisionKind member was added; DESIGN-03's proposed GRANT_BUDGET was NOT
  added, and the initial budget grant is recorded as EXTEND_BUDGET, the only
  budget-shaped member of the frozen enum. LEGAL_TRANSITIONS is unchanged.
- CONFIRM is enforced on rows 5-1 (open_run, subject PROJECT — the run does not
  exist yet), 7.2-1 (first invocation of a run, subject RUN) and 7.4-4
  (authorize_commit, subject COMMIT_INTENT), through one predicate,
  decision.require_confirmation. Row 6-2 was already enforced by
  guard:gr06_activation_confirmation. No other row is gated.
- Enforcement is the SUPERVISED column only. All three rows read AUTO under
  AUTONOMOUS, so `confirmation_id` is required by the row, not by Python:
  the keyword defaults to None and an autonomous project is asked for nothing.
  Demanding it there would invent a cell the frozen matrix does not declare
  (test_autonomous_rows_require_no_confirmation).
- 7.2-1 is WHEN(FIRST_INVOCATION_OF_RUN, CONFIRM, AUTO). The confirmation is
  asked once per run; over-applying it would deny a second invocation the row
  declares AUTO.
- A commit confirmation is snapshot-bound (COMMIT_INTENT ∈ SNAPSHOT_BOUND_SUBJECTS,
  APPROVE ∈ SNAPSHOT_BOUND_KINDS), so a snapshot landing between recording it
  and authorizing makes it STALE. Any driver must record the confirmation
  immediately before the act it discharges, with no observation in between.
  Provisioning decisions are *not* snapshot-bound and do not go STALE.
- guard:gr31_preconditions_deferred is TEMPORARY. authorize_commit refuses any
  non-empty review or validation precondition because B6 (commit.py:101-104
  discards resolve_attestation's result, so a FAIL attestation discharges) and
  B7 (a validation precondition is discharged by artifact existence, not by a
  passing receipt) are both OPEN. It defers them; it closes neither, and
  commit.py, review.py, rvw() and generic precondition resolution are
  untouched. resolve_decision stays `lambda ref: False`, so a decisions
  precondition still routes to BLOCKED. GR-33 must not bypass or weaken it.
- B4 remains open: governed independent worker review is still unreachable
  (one relay origin per controller; CodexProvider overrides no
  relay_environment). Do not claim the production review leg is complete.
- DESIGN-03 is neither revised nor frozen by GR-31 and no DESIGN-03 finding is
  claimed closed. policy_digest provisioning is omitted; policy.set untouched.

## Composition root
GR-32 gives the runtime a production caller that walks the supervised sequence
in order. B2 is closed: before it, a project created through `create_project`
could be provisioned only by a test writing rows, and `main()`'s six
subcommands could not create a project, record a decision, author or activate a
contract, allocate a run or configure the relay. B3, B4, B6 and B7 are
untouched and open, and no claim here bears on them.
Evidence: [GR-32 validation](docs/gr32-validation.md).

- `src/gruntime/driver.py` is the orchestration half of the composition root
  and is the only place outside `controller.main()` that names concrete
  adapters (`build_provider`). It adds four concepts and no sixth subsystem:
  PilotSession, OwnerPresenter, StepOutcome/DriverReport and ProposalMapping.
  No second controller, transport, provider architecture, registry, plugin
  layer or state machine; every transition it calls is the kernel's existing
  one.
- The ordering `docs/gr31-plan.md` records is wrong and the plan is NOT edited.
  It puts contract construction before `open_run`; `guard:gr06_run_identity`
  binds a contract to `run.stage_id`, which `open_run` mints, so `open_run`
  must come first. The corrected order is the table in
  docs/gr32-validation.md §3 (GR32-P-001).
- All four confirmations — rows 5-1, 6-2, 7.2-1 and 7.4-4 — are APPROVEs and
  so snapshot-bound. The driver records each immediately before the act it
  discharges, with no observation between. Provisioning decisions are not
  snapshot-bound and do not go stale.
- The session stops after apply_commit. It takes no snapshot and runs no
  validation afterwards; `apply_commit`'s own POST_COMMIT snapshot is the
  kernel settling the commit. Observation is `PilotSession.observe`, a
  separate entry taken after the owner advances the workspace to the reported
  revision, and nothing it produces discharges a commit precondition.
  `guard:gr31_preconditions_deferred` still refuses any non-empty review or
  validation precondition, through the driver as everywhere else; GR-32
  neither bypasses nor weakens it.
- A restart is a new epoch and a new relay, never a continuation:
  `PilotSession.resume` starts, recovers, reports and stops for the owner. It
  never resumes steps 12-16.
- Credential handling (D2): the credential is named by an environment
  VARIABLE NAME supplied as a runtime parameter. Nothing reads a credential
  file, a home directory or Claude Code's credential storage, and the value,
  its length and any fragment of it reach no report, event, artifact, journal
  or subprocess output — `guard:gr32_report_secret_free` asks the runtime's
  own SecretGuard. Defaults are header `x-api-key` and an empty prefix; both
  are configurable and Bearer remains selectable.
- GR32-P-002 is answered by the driver, not by a kernel fix.
  `configure_inference_relay` consumes both secret decisions in a transaction
  that commits before it calls the resolver, so a failing resolver spends two
  human acts. `driver.preflight_credential` runs before either decision is
  recorded and refuses an unset, empty or non-printable-ASCII credential
  unchanged, recording zero secret decisions. The kernel window remains for
  anything the preflight cannot see — the environment changing between the two
  points, or a resolver failing for another reason. It is narrowed, not closed.
- Only a `network='NONE'` validation operation is registered
  (`guard:gr32_validation_network_none`). The GR-09/GR-17 egress gap recorded
  under Known gaps is unchanged, and neither ALLOWLIST nor ANY validation
  execution is made reachable.
- `propose_commit` is not widened. The driver maps exactly one conforming
  worker mutation into it, taking the path from the receipt and the content
  from the artifact `after_ref.digest` names, re-digested before use. Multiple
  mutations, DELETE, RENAME, CHMOD, `rename_to`, `mode`, a missing
  `after_ref`, non-UTF-8 content, a non-COMPLETED or reconciled termination,
  an attempted capability violation and a scope breach are each refused whole
  and stop the session. The worker's op and `before_digest` are proved against
  the governed base first (GR32-F-003): CREATE only where the path is absent
  and with no `before_digest`, MODIFY only where it exists and its
  `before_digest` is the base content digest. Nothing is translated between
  them, and a refusal leaves no CommitIntent.
- Budget and validation plan are runtime inputs, both mandatory (GR32-F-005,
  F-006). `pilot` requires one `--budget-<field>` flag per `models.Budget`
  field, derived from the model; step 1 refuses an absent or all-zero budget
  and a missing validation plan before any transition, so step 11 never
  reports OK with nothing bound. Step 1 also refuses a budget the contract
  cannot carry — validated against stage_contract.schema.json's own
  `$defs/Budget`, where every field is an integer — so a fractional
  `cost_units` stops before project creation rather than at step 7
  (guard:gr32_budget_contract_shape, GR32-R-001). Nothing is rounded; `100.0`
  passes. The `Unit = float` vs schema `integer` mismatch itself is unresolved.
- Every typed refusal on the driver surface, composition included, is a
  STOPPED report with the refusing step (GR32-F-001). Only
  GovernedRuntimeError is a refusal; a defect still propagates as a traceback.
- D6: `invoke`, `validate` and `commit` carry no confirmation plumbing and are
  admissible only under AUTONOMOUS. `legacy_command_admits` refuses them on a
  SUPERVISED project before `Controller(...)`, before the epoch bump and
  before `controller.started`. `start`, `recover` and `snapshot` are ungated
  and do not read the project. `build_parser` builds its subparsers from
  LEGACY_COMMANDS and DRIVER_COMMANDS and GATED_COMMANDS is derived from the
  first, so the parser surface and the gated set cannot drift apart. This is
  what keeps tests/test_r2_worker_crash_adoption.py,
  tests/test_r3_commit_crash_adoption.py, tests/test_gr09_validation.py,
  tests/test_gr10_git_transaction.py and tests/test_gr03_repository_lease.py
  passing unedited; their bytes are asserted against HEAD.
- `main()` hardcodes no provider. `--provider` selects one and defaults to
  `fake`, which is what the historical AUTONOMOUS evidence has always run on.
- `bin/pilot-run` is a preflight and performs no transition. It no longer
  asserts that no composition root exists or that `main()` hardcodes
  FakeProvider, and no longer probes a credential file; every pilot-specific
  value is an argument. Running the pilot is GR-33 and `bin/pilot-run` does
  not do it. Its provider `--version` probe launches the executable by the
  absolute path the preflight resolved, with only `LC_ALL` and a `PATH` built
  from that executable's directories and `/usr/local/bin:/usr/bin:/bin` —
  never the caller's (guard:gr32_probe_environment); immediately before
  launch its argv, executable realpath, working directory and every
  environment key and value are refused if they hold the credential
  (guard:gr32_probe_launch_secret_free). Secret filtering reads raw and
  parsed values, never serialized JSON (GR32-F-002): the probe's raw stdout
  and stderr are checked before entering the report
  (guard:gr32_probe_output_secret_free), and every parsed report string plus
  the exact text to be printed are checked last
  (guard:gr32_preflight_report_secret_free); either match is a fixed-text
  BLOCKED report. No re-exec marker exists (GR32-F-004): the script re-execs
  unless `sys.prefix` is the project venv (guard:gr32_reexec_identity), and
  the exec'd child, launched by the interpreter's own path, never execs again
  (guard:gr32_reexec_once).
- No Pilot-1 constant is compiled into `src/`: no sandbox path, no database
  path, no base revision, no objective, no target path and no budget. Two different
  parameter sets drive two different compositions through the same code.

## Design baseline
design-01-frozen is the frozen design and is unchanged. `git diff
design-01-frozen design-02-frozen -- design/` shows only two ADDED documents
(387 insertions, 0 deletions); no frozen file was edited.

DESIGN-02 records a proposed amendment in three places, as a design document
only — not yet reflected in frozen text and not implemented:
- W-INV-2 (domain-model.md:611) — proposes permitting precommit kernel staging
- transition-matrix.md:429 — proposes allowing commit during AWAITING_VALIDATION
- CM-INV-3 — proposes distinguishing attributable staging from an unknown commit

Until those edits land in the frozen files, design-01-frozen remains the
authoritative baseline and the amendment lives only in
design/DESIGN-02-candidate-observation.md. Read both: the frozen baseline for
what the design says, DESIGN-02 for what is proposed to change.

design-04-frozen, like design-02-frozen, adds documents only; no
design-01-frozen file changed. DESIGN-04's amendments live in
design/DESIGN-04-baseline-correction-04.md; its §8 registers KD-1..KD-13 as not
closed at freeze (KD-9 is closed only on chosen premises).
DESIGN-04-FINDINGS-04 (review of revision 04) found that design-04-frozen does
not stand as an accepted corrective baseline; design-01-frozen remains
operative. Revision 05 (design/DESIGN-04-baseline-correction-05.md) was
independently re-reviewed and ACCEPTED at GR-26; the record is
design/review/DESIGN-04-FINDINGS-05.md, which binds the revision by SHA-256.
GR-23 implemented the four-event genesis sequence without AX-17's creation
witness; GR-27 conformed project creation to AX-17 and closed
DESIGN-04-032..036.

GR-33 N1 (accepted and committed, 56765add09d5009f1af3ff46594a8090211a2e58):
the 23 amendments of the accepted Revision 05 (SHA-256 35f283c3…2c54) are
transcribed verbatim into design/authority-matrix.md, domain-model.md,
evidence-model.md and transition-matrix.md, each at its stated target with
its quoted frozen text verified first. §5.2 and §5.3 are inserted after
authority-matrix §5.1; every §3 untouched location is unchanged. No KD item is
closed.

GR-33 N2 (accepted and committed, 13b1297a481047c33ddd1b38b43fa1d80813eb86)
and GR-33 N3 (accepted and committed,
8ad2c1012d127d882a5e8f792f85e335e7a51548) are unchanged here.

GR-33 N4 (normative candidate, implemented, under independent review; not
accepted): transition-matrix §12 adds one non-axis `secret.read` row
(SUPERVISED CONFIRM, AUTONOMOUS DENY) and authority-matrix §5.2.1 recounts to
ten of eighteen HUMAN-class capabilities on twenty-one rows. N4 is normative
only: production code does NOT yet conform, and F-N4-01..F-N4-07 remain open
for later production conformance. F-N4-06 (`secret.resolved` persists the
secret's length) contradicts the GR-32 D2 credential claim under Composition
root, which N4 does not edit. Pilot-1 remains BLOCKED.

DESIGN-03 is not frozen and, per DESIGN-04 §5, must be revised against
DESIGN-04, reviewed by the reviewer that raised DESIGN-03-FINDINGS-01.

Owner blocking flags: DESIGN-03-001..025 and DESIGN-04-001..028 are in
design/review/DISPOSITION-01.md (its prose at :20–21 still says the cells are
blank; the tables are authoritative); DESIGN-04-029..036 are in
DESIGN-04-FINDINGS-04.

## Review method
- A record freezes findings, not dispositions. Blocking flags are the owner's
  and are set before the record is committed.
- Re-review after a revision covers the fix and everything it touches: verify
  each claimed-closed finding against the frozen text rather than against the
  new wording, read every section the fix edited in full, check what the fix
  cites, and ask explicitly whether the fix introduced new material. A fix to
  one finding has twice introduced a defect in an adjacent cell the finding
  never named.
- Delta review does not replace a full independent pass before a freeze. Take
  one full pass at the end, not one per revision.
- The reviewer of a revision is the reviewer that raised the findings; the
  author of a document never reviews it.

## Tooling
- bin/mutate deletes the matched line, so a guard must be a single deletable
  line. A multi-line guard orphans its condition or its body and fails as a
  syntax error — pytest exit 4, reported as ERROR rather than KILLED, which
  proves nothing about whether the guard is tested. Put any multi-step check
  in a helper and leave one deletable call at the guard site.
- bin/mutate takes the whole guard statement as its needle, never the `# guard:`
  tag: a tag needle mutates only the comment and reports SURVIVED for a killed
  guard. Build the needle from the AST (bin/check-gr09-mutations does).
- An interrupted bin/mutate (timeout, SIGKILL) skips its restore trap and leaves
  the mutant in src/. Allow at least 10 minutes. After any interruption, run
  `git diff --quiet -- src` before anything else and restore from the retained
  /tmp backup.
- A later stage can hollow an earlier guard's killing test without failing it:
  GR-23's genesis snapshot left guard:controller_snapshot surviving until
  GR-24. A passing suite does not re-verify earlier kills. Assert refusals with
  match=.

## Skill layer
`.agents/` is the canonical governed-skill layer (SK-01): the rules are
`.agents/governance/rules.md`, the catalog is
`.agents/governance/catalog.json`, and each skill's procedure lives in
`.agents/skills/<skill>/SKILL.md`. `.claude/skills/`, `AGENTS.md` and this
file are discovery surfaces that point there and restate no procedure.
Every skill invocation requires a stage authorization (SK-03); the contract
is enforced structurally by `bin/check-governed-skills` and
`tests/test_governed_skills.py`.
