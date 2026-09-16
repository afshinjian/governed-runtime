# Governed Runtime
Project-agnostic governed AI software-development runtime.
Phase: GR-24 (restore snapshot-guard coverage lost at GR-23).
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
- Validation execution does not check proc.exec.validation. transitions.py:1153
  and :1158 declare it as the capability required by the validation
  transitions; no require_authority call consumes that declaration. Same path
  as FINDINGS-02 F02-001, not covered by it. Deferred from GR-17. FINDINGS-03
  answers the cap= question: policy.resolve enforces required_capability but
  has no production caller (F03-001); F03-002 and F03-003 are also open.
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
- record_decision (controller.py) accepts a HUMAN actor with no
  principal_key_id; domain-model.md:58 requires one. Key presence is checked
  where some decisions are used, not when one is recorded: genesis
  (_is_authenticated_human), contract activation (contract_controller.py
  approval; authority.py human_covers and basis check), exercise decisions
  (guard:gr06_exercise_decision) and secret-read approval
  (guard:gr08_secret_approval).
- No per-stage mutation evidence file exists for GR-17, GR-23 or GR-24; their
  kills are persisted only as bin/mutate summary lines in
  docs/evidence/recheck-20260916.txt. Of the committed JSON records, gr07 and
  gr08 inline their summaries and cite no logs; gr06 inlines summaries and also
  cites logs; gr06, gr09, gr10 and suspension cite full logs that exist only
  under the gitignored .evidence/ (gr09's paths are relative to
  .evidence/gr09/, with no root field).

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
closed at freeze (KD-9 is closed only on chosen premises). GR-23 implements its
AX-17 four-event genesis. DESIGN-03 is not frozen (DESIGN-03-FINDINGS-02: 3
blocking) and per DESIGN-04 §5 must be revised against it, reviewed by the
reviewer that raised DESIGN-03-FINDINGS-01.

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
