# Governed Runtime
Project-agnostic governed AI software-development runtime.
Phase: GR-32 (supervised stage driver / composition root).
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
  docs/evidence/recheck-20260916.txt. GR-31 does not join them:
  docs/gr31-validation.md inlines every summary and states its one log root.
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
