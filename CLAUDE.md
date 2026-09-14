# Governed Runtime
Project-agnostic governed AI software-development runtime.
Phase: GR-07 (worker provider layer).
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
- GR-07: ToolBridge exposes no network operation, so no worker can reach an
  inference endpoint. CF-4 permits egress only through the bridge, so this is a
  missing implementation (the governed inference relay), not a policy to relax.
  Blocks every live run. Owned by GR-07b.
