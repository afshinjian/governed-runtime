---
name: governed-stage-planner
description: Produces a bounded stage plan as a proposal for the human owner to authorize. The plan names the goal, the file-level scope, the validation commands, the refusal conditions and the open questions. Never edits files, never implements, never opens a stage by itself. Requires a stage authorization.
---

# governed-stage-planner

## Purpose

Turn an owner's stage intent into a bounded, checkable plan. Planning output
is a proposal, not a change: this skill writes nothing, and its plan binds
no one until the owner separately authorizes implementation (SK-03).

## Mode

- `planning` — read and propose; no mutation.

## Authorization

This skill runs only under a stage authorization
(`.agents/governance/authorization.schema.json`) whose `skill` names this
skill, whose `mode` is `planning` and whose `stage` names the one stage being
planned. Without a valid authorization: REFUSED (SK-03).

## Procedure

1. Read the authorization. An absent or malformed authorization means
   REFUSED before any planning (SK-03).
2. Establish the baseline the plan rests on: the `CLAUDE.md` phase line must
   name the stage being planned; the known-gaps section and the frozen design
   baseline are read, not the proposals. A plan against a dirty tree or a
   different phase is BLOCKED, with the observation as a finding.
3. Draft the plan, as report content only:
   - goal — one sentence, naming the stage by its exact identifier;
   - bounded scope — every file the stage may touch, each with a reason;
   - explicit non-goals — what the stage must not touch: historical review
     records (SK-10), frozen design text, and anything outside its scope
     (SK-04);
   - validation — the exact commands that will prove the stage;
   - refusal conditions — what will make implementation refuse mid-stage;
   - open questions — what only the owner can answer.
4. State in the plan that implementation requires a separate authorization
   naming this stage and its scope (SK-03, SK-11). The plan proposes; it
   never authorizes, and it never schedules another stage (SK-11).

## Output

A report per `.agents/governance/report.schema.json`: `outcome` COMPLETE with
the plan in `summary`, or BLOCKED with the blocking observation as a
`findings` entry. `scope_observed` lists the paths read; nothing is mutated.

## Refusals

- No valid stage authorization (SK-03).
- The intent names no stage, or names a stage other than the current phase
  line (SK-11).
- The intent asks for implementing, provisioning, piloting or opening
  another stage — those are not planning acts (SK-11).
- Any request to write the plan into the repository: plans are proposals in
  the report (SK-02).
