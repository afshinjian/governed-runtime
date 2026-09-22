---
name: governed-independent-reviewer
description: Independent review of a stage implementation or of a candidate for closure. Verifies claims against evidence on disk, checks scope, authority boundaries and deduplication, and raises findings with stable IDs. Never edits files. Requires a stage authorization; closure review additionally requires the reviewed candidate identity.
---

# governed-independent-reviewer

## Modes

| mode | additional warrant | procedure |
|---|---|---|
| `implementation-review` | — | review the uncommitted implementation of the stage |
| `closure-review` | `candidate` (SK-06) | review the named candidate exactly |

## Independence (SK-07)

Refuse if the change under review was produced in this same session or by
this same agent instance. The reviewer never edits what it reviews: this
skill is read-only, and its output is findings, never a patch.

## Authorization

This skill runs only under a stage authorization
(`.agents/governance/authorization.schema.json`) whose `skill` names this
skill, whose `mode` is one of the two above and whose `stage` names the stage
under review (SK-11). Closure review is REFUSED without `candidate` — the
identity of the reviewed candidate (SK-06). Without a valid authorization:
REFUSED (SK-03).

## Procedure

1. Read the authorization. An absent or malformed authorization, or closure
   review without a candidate identity, means REFUSED before any review
   (SK-03, SK-06).
2. Establish the reviewed subject exactly:
   - implementation review — the working-tree change for the authorized
     stage;
   - closure review — the candidate named by `candidate_ref`, never whatever
     is nearby (SK-06).
3. Verify against the frozen design baseline and `CLAUDE.md`, in this order:
   - scope — every mutated path is inside the authorized scope (SK-04);
   - authority — no git act was performed and no runtime authority was
     claimed (SK-09); historical review records are untouched (SK-10);
   - claims — every claim in the implementation summary is checked against
     evidence on disk: file contents, test output, logs, schemas;
   - completeness — the stage's validation commands, run by the reviewer,
     produce the claimed results;
   - deduplication — procedure that belongs in the canonical layer has not
     been copied into a discovery surface (SK-01);
   - residue — nothing outside the stage was opened or changed (SK-11).
4. Raise findings with stable IDs (`<STAGE>-F-NNN`), each with a severity and
   a claim that names the file and the evidence. Findings are the review's
   only output; the reviewer never fixes what it finds (SK-02, SK-07).
5. Verdict: report COMPLETE only when no BLOCKER finding stands; otherwise
   BLOCKED with the findings. The stage's own verdict token, when it defines
   one, goes in `verdict`.

## Output

A report per `.agents/governance/report.schema.json`: `outcome`; every
finding; the commands run with results; in closure review, the candidate
identity reviewed and the records it was checked against.

## Refusals

- No valid authorization, or closure review without a candidate identity
  (SK-03, SK-06).
- The session authored the work under review (SK-07).
- Any step that would mutate the repository, including small fixes — the
  reviewer reports, the implementer remediates (SK-02).
- Any request to edit a historical review record (SK-10).
