---
name: governed-stage-implementer
description: Implements or remediates exactly the stage its authorization names, within the explicit scope, and leaves the tree uncommitted for review. Runs only the stage's validation commands and records their results. Never commits, tags or pushes. Requires a stage authorization; remediation additionally requires the original findings it answers.
---

Discovery wrapper (SK-01). The canonical procedure this wrapper serves is
`.agents/skills/governed-stage-implementer/SKILL.md`; read it and follow it
there. Rules: `.agents/governance/rules.md`. Stage authorization required:
`.agents/governance/authorization.schema.json` (SK-03, SK-08).
