# Governed Runtime
Project-agnostic governed AI software-development runtime.
Phase: GR-17 (validation execution authority gate).
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
- GR-09: network policy has no constrained middle. ALLOWLIST is refused outright
  (validation.py:130 — no enforcing adapter), so scoped egress is unavailable,
  not merely denied. ANY adds `--share-net` (validation.py:133) with no
  require_authority on the execute_validation path, so the only way to get
  network is the unconstrained one, and it is ungated.
- GR-09: the missing-bwrap path is untested — this host has bwrap, so no test
  exercises the ERROR receipt. Verify before running on another host.
- Storage v1→v2→v3→v4 all refuse older schemas with no migration path. Acceptable
  while pre-release; must be resolved before the first persistent pilot database.
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
  cannot be closed by wiring alone. Requires DESIGN-02.

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
