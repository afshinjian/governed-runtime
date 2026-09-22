# Stage authorization template

A stage authorization is a human act (SK-08): the owner — or a human the owner
delegates to — writes it and hands it to the skill with the work. An agent
never writes its own. The document must validate against
`.agents/governance/authorization.schema.json`; unknown fields are rejected
there, so this template is the whole surface.

## Example

```json
{
  "authorization_id": "gr30-impl-001",
  "skill": "governed-stage-implementer",
  "mode": "implementation",
  "stage": "GR-30",
  "scope": [
    "AGENTS.md",
    ".agents/**",
    ".claude/skills/**",
    "CLAUDE.md",
    "bin/check-governed-skills",
    "tests/test_governed_skills.py"
  ],
  "authorized_by": { "actor_kind": "HUMAN", "principal": "owner" },
  "created_at": "2026-09-20T00:00:00Z",
  "governance_mode": "SUPERVISED",
  "may_commit_tag_push": false
}
```

## Fields

| field | required | meaning |
|---|---|---|
| `authorization_id` | yes | unique id of this authorization |
| `skill` | yes | one of the six catalog skills |
| `mode` | yes | one of that skill's modes |
| `stage` | yes | the one stage opened (SK-11) |
| `scope` | yes | explicit path patterns covered (SK-04) |
| `authorized_by` | yes | human principal; `actor_kind` is `HUMAN` (SK-08) |
| `created_at` | yes | when the human authorized |
| `governance_mode` | yes | `SUPERVISED`, the only value here |
| `may_commit_tag_push` | yes | `false`, the only value (SK-09) |
| `original_findings` | remediation mode | the finding IDs answered (SK-05) |
| `candidate` | closure-review mode | the reviewed candidate identity (SK-06) |
| `notes` | no | anything else the human wants on record |

## Mode additions

Remediation adds the findings it answers:

```json
"original_findings": ["GR30-F-001", "GR30-F-002"]
```

Closure review adds the candidate it reviews:

```json
"candidate": { "candidate_ref": "<commit sha or candidate id>", "review_record": "design/review/RECORD.md" }
```

A warrant field is refused on every mode that does not exercise it:
`original_findings` appears only on a remediation authorization, `candidate`
only on a closure-review authorization.

Scope patterns are `fnmatch` globs matched against workspace-relative paths;
one authorization per invocation, and nothing outside its `scope` is in scope
even if the skill could reach it.
