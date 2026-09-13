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
