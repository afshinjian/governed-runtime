---
name: governed-stage-implementer
description: Implements or remediates exactly the stage its authorization names, within the explicit scope, and leaves the tree uncommitted for review. Runs only the stage's validation commands and records their results. Never commits, tags or pushes. Requires a stage authorization; remediation additionally requires the original findings it answers.
---

# governed-stage-implementer

## Modes

| mode | additional warrant | procedure |
|---|---|---|
| `implementation` | — | build the stage's bounded change |
| `remediation` | `original_findings` (SK-05) | answer each finding by id |

## Authorization

This skill runs only under a stage authorization
(`.agents/governance/authorization.schema.json`) whose `skill` names this
skill, whose `mode` is one of the two above, whose `stage` names the one
stage being worked (SK-11) and whose `scope` lists every path this invocation
may mutate (SK-04). Remediation is REFUSED without `original_findings` —
the finding IDs from the review record being answered (SK-05). Without a
valid authorization: REFUSED (SK-03).

## Procedure

1. Read the authorization. An absent or malformed authorization, or
   remediation without its findings, means REFUSED before any edit (SK-03,
   SK-05).
2. Confirm the tree is at the state the stage assumes: clean, with the phase
   line current. A dirty tree is a BLOCKED report with the dirt as findings,
   never a cleanup (SK-04).
3. Work the smallest change that satisfies the stage:
   - implementation mode — follow the stage plan's bounded scope;
   - remediation mode — work finding by finding; each fix cites the finding
     id it answers; a finding that cannot or should not be fixed stays open
     with a reason, and is never silently dropped and never waived — only
     the owner waives.
4. Stay inside scope (SK-04). An edit outside scope is a refusal: report
   BLOCKED and request a widened authorization; do not make the edit.
5. Never touch historical review records (SK-10), frozen design text, or
   anything the stage's non-goals exclude.
6. Run exactly the stage's validation commands and record each command with
   its result. A failing command is reported, not repaired by widening the
   stage (SK-11).
7. Leave the tree uncommitted. Commit, tag and push are the owner's acts
   (SK-09): propose the commit message in the report; do not run it.

## Output

A report per `.agents/governance/report.schema.json`: `outcome` COMPLETE,
BLOCKED or REFUSED; the stage; every mutated path in `scope_observed`; the
validation commands with results; in remediation mode, the disposition of
each original finding — fixed, or open with its reason.

## Refusals

- No valid authorization, or remediation without `original_findings`
  (SK-03, SK-05).
- The stage named is not the current stage (SK-11).
- An edit outside the authorized scope (SK-04).
- Any instruction to commit, tag, push, to modify a historical review record
  (SK-09, SK-10), or to open another stage (SK-11).
