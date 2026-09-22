---
name: governed-owner-closeout
description: Closeout procedure for the human owner of a stage. Walks the checklist before a stage is closed. The skill drafts text and verifies state; every git act and every blocking-flag decision stays the owner's. Requires a stage authorization.
---

# governed-owner-closeout

## Purpose

This skill is the owner's closeout checklist. The owner is the human; this
skill drafts text, verifies state and lists the owner's acts — it performs
none of them. It never commits, tags or pushes (SK-09), never sets blocking
flags on a review record — those are the owner's, set before the record is
committed — and never edits a historical review record (SK-10).

## Mode

- `closeout` — draft and verify the closeout; the owner performs the acts.

## Authorization

This skill runs only under a stage authorization
(`.agents/governance/authorization.schema.json`) whose `skill` names this
skill, whose `mode` is `closeout` and whose `stage` names the stage being
closed. Without a valid authorization: REFUSED (SK-03).

## Procedure

1. Read the authorization. An absent or malformed authorization means
   REFUSED before any closeout work (SK-03).
2. Verify the preconditions the owner must see before closing, and report
   each as a finding when it does not hold:
   - the stage's review record exists, is committed, and carries the
     reviewer's verdict;
   - every blocking finding is closed, or is explicitly waived by the owner
     on the record;
   - the tree contains only the stage's own changes, and the phase line
     still names the stage being closed;
   - the stage's validation commands pass on the tree exactly as it will be
     committed.
3. Draft, as report content and never as edits: the blocking-flag statement
   for the record, the phase-line wording for the next stage, and the commit
   message. The owner applies them, changes them, or rejects them.
4. List the owner's acts in order — set the flags on the record, commit the
   record, move the phase line, commit the phase line, then tag or push if
   the owner chooses. Each act is the owner's, performed by the owner (SK-09);
   this skill drafts the words and verifies the outcome, and runs nothing.
5. After the owner acts, verify read-only that what was committed is what
   was drafted, and report any divergence as a BLOCKER finding.

## Output

A report per `.agents/governance/report.schema.json`: `outcome` COMPLETE when
the preconditions hold and the drafts are ready, otherwise BLOCKED with the
findings; the drafts in `summary`; the verification results; the owner-act
checklist.

## Refusals

- No valid stage authorization (SK-03).
- Preconditions unmet — unclosed blockers, a dirty tree, failing validation —
  reported BLOCKED; this skill never clears them itself (SK-02).
- Any request to perform a git act, to set blocking flags, or to close a
  stage on the owner's behalf (SK-02, SK-09).
