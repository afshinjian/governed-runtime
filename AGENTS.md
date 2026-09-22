# Governed agent procedures

Agent procedure in this repository is governed. The canonical layer is
`.agents/` (SK-01); this file and every other discovery surface only point
there and restate no procedure.

- Rules: `.agents/governance/rules.md`
- Catalog: `.agents/governance/catalog.json`
- Stage authorization schema: `.agents/governance/authorization.schema.json`
- Skill report schema: `.agents/governance/report.schema.json`

| skill | canonical text |
|---|---|
| governed-repo-reality-check | `.agents/skills/governed-repo-reality-check/SKILL.md` |
| governed-stage-planner | `.agents/skills/governed-stage-planner/SKILL.md` |
| governed-stage-implementer | `.agents/skills/governed-stage-implementer/SKILL.md` |
| governed-independent-reviewer | `.agents/skills/governed-independent-reviewer/SKILL.md` |
| governed-owner-closeout | `.agents/skills/governed-owner-closeout/SKILL.md` |
| governed-pilot-readiness | `.agents/skills/governed-pilot-readiness/SKILL.md` |

No skill invocation runs without a stage authorization (SK-03); no skill
commits, tags or pushes (SK-09). The contract is enforced structurally by
`bin/check-governed-skills` and `tests/test_governed_skills.py`.
