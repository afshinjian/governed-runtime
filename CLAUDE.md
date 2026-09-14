# Governed Runtime
Project-agnostic governed AI software-development runtime.
Phase: GR-20 (DESIGN-02 candidate observation).
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
- GR-09: network ALLOWLIST fails closed (declared, not implemented). Any
  validation needing network egress is currently impossible, not merely denied.
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
design-01-frozen is amended by design-02-frozen in three places:
- W-INV-2 (domain-model.md:611) — precommit kernel staging now permitted
- transition-matrix.md:429 — commit allowed during AWAITING_VALIDATION
- CM-INV-3 — attributable staging distinguished from an unknown commit
Any review or implementation must read BOTH. design-01-frozen alone is stale.
