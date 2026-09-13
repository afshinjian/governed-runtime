# Governed Runtime
Project-agnostic governed AI software-development runtime.
Phase: GR-09 (validation catalog and controlled executor).
Rules:
- No HIR / automate-implementation identifiers in core.
- No Claude/Codex/Hermes specifics outside adapters.
- Tables and JSON Schema over prose.
- Controller owns all state transitions; workers only propose.

## Known gaps
- GR-03: only drift suspension writes project.suspension. Other escalations
  record suspension_applied without applying it. Must close before GR-07
  (real workers) — a recorded-but-unapplied suspension is a false evidence claim.
- GR-09: network ALLOWLIST fails closed (declared, not implemented). Any
  validation needing network egress is currently impossible, not merely denied.
- GR-09: the missing-bwrap path is untested — this host has bwrap, so no test
  exercises the ERROR receipt. Verify before running on another host.
