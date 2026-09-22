---
name: governed-pilot-readiness
description: Read-only readiness assessment for the first persistent pilot. Enumerates the gates that must close first and reports each one open or closed with the evidence on disk. Never provisions, never runs the pilot, never orchestrates. Requires a stage authorization.
---

Discovery wrapper (SK-01). The canonical procedure this wrapper serves is
`.agents/skills/governed-pilot-readiness/SKILL.md`; read it and follow it
there. Rules: `.agents/governance/rules.md`. Stage authorization required:
`.agents/governance/authorization.schema.json` (SK-03, SK-08).
