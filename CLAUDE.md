# Governed Runtime
Project-agnostic governed AI software-development runtime.
Phase: GR-03 (repository reality and SCM safety).
Rules:
- No HIR / automate-implementation identifiers in core.
- No Claude/Codex/Hermes specifics outside adapters.
- Tables and JSON Schema over prose.
- Controller owns all state transitions; workers only propose.
