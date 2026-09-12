# Governed Runtime
Project-agnostic governed AI software-development runtime.
Phase: GR-02 (transition engine; GR-01 passed at tag gr-01-passed).
Rules:
- No HIR / automate-implementation identifiers in core.
- No Claude/Codex/Hermes specifics outside adapters.
- Tables and JSON Schema over prose.
- Controller owns all state transitions; workers only propose.
