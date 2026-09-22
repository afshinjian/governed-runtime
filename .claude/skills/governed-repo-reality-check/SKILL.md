---
name: governed-repo-reality-check
description: Read-only reality check of the repository before stage work. Observes the git state, the phase line, the CLAUDE.md claims, evidence and the test baseline, then reports every divergence between documented claims and what is on disk. Never mutates anything. Requires a stage authorization.
---

Discovery wrapper (SK-01). The canonical procedure this wrapper serves is
`.agents/skills/governed-repo-reality-check/SKILL.md`; read it and follow it
there. Rules: `.agents/governance/rules.md`. Stage authorization required:
`.agents/governance/authorization.schema.json` (SK-03, SK-08).
