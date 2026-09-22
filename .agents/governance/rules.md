# Governed skill rules

Canonical rules for the repository-local governed skill layer. `.agents/` is
the canonical layer (SK-01); everything else — `.claude/skills/`, `AGENTS.md`,
`CLAUDE.md` — is a discovery surface that points here and never restates
procedure. Skills describe procedure, never authority (SK-02): authority
derives only from a human act recorded in a stage authorization, and no skill
text can widen it. Enforcement is structural: `bin/check-governed-skills`
and `tests/test_governed_skills.py` prove this contract on every run.

| id | rule | enforced by |
|---|---|---|
| SK-01 | `.agents/` is the canonical skill layer. Discovery surfaces (`.claude/skills/`, `AGENTS.md`, `CLAUDE.md`) may point to canonical files, never restate their procedure. | check: wrappers, wrapper-dedup |
| SK-02 | A skill describes procedure, never authority. Authority derives only from a human act recorded in a stage authorization; no skill text, wrapper or catalog entry can widen it. | check: authority |
| SK-03 | Every skill invocation requires a stage authorization that validates against `authorization.schema.json`. A mutating or review invocation without one is refused before any effect. | check: authorization-schema, authorization-gate |
| SK-04 | Scope is explicit: an authorization lists the path patterns it covers; anything not listed is out of scope and an edit there is a refusal, not a cleanup. | schema: `scope` |
| SK-05 | Remediation mode requires the original findings it answers, by ID, from the review record being remediated. | schema: `original_findings` |
| SK-06 | Closure review requires the identity of the reviewed candidate, exactly; never whatever is nearby. | schema: `candidate` |
| SK-07 | Author and reviewer are independent: the invocation that reviews a change is never the session or agent that produced it, and the reviewer never edits what it reviews. | check: authorization-gate |
| SK-08 | This repository operates in SUPERVISED mode: every authorization is a live human act naming its principal; a skill never authorizes itself or another skill. | schema: `authorized_by`, `governance_mode` |
| SK-09 | No skill commits, tags or pushes. Git authority is the human owner's alone, and no authorization field can grant it to a skill. | schema: `may_commit_tag_push`; check: authority |
| SK-10 | Historical review records are immutable for skills: read them, never modify them; closure is the owner's act. | check: authorization-gate |
| SK-11 | A skill never opens a stage other than the one its authorization names, and never implements a stage the authorization does not name. | schema: `stage`; check: authorization-gate |
| SK-12 | A skill result is a report, not an effect: reports validate against `report.schema.json`, cite their authorization, and keep every observed path inside the authorized scope. | check: report-schema |

Rule IDs are unique and are the only cross-reference currency: skills,
wrappers, `AGENTS.md` and the catalog cite rules by `SK-nn` and never restate
them at length. Any divergence between a discovery surface and this file
resolves in favor of this file.
