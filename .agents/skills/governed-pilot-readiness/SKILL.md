---
name: governed-pilot-readiness
description: Read-only readiness assessment for the first persistent pilot. Enumerates the gates that must close first and reports each one open or closed with the evidence on disk. Never provisions, never runs the pilot, never orchestrates. Requires a stage authorization.
---

# governed-pilot-readiness

## Purpose

Assess whether the runtime is ready for its first persistent pilot, gate by
gate, against the current `CLAUDE.md` known gaps and the frozen design
baseline. This skill assesses; it does not implement, provision, transport
or orchestrate the pilot — those are future stages' work, each needing its
own authorization (SK-11).

## Mode

- `pilot-readiness` — assess and report; read-only.

## Authorization

This skill runs only under a stage authorization
(`.agents/governance/authorization.schema.json`) whose `skill` names this
skill, whose `mode` is `pilot-readiness`, whose `stage` names the one stage
this assessment runs in (SK-11) and whose `scope` lists the paths it may
read. Without a valid authorization: REFUSED (SK-03).

## Procedure

1. Read the authorization. An absent or malformed authorization means
   REFUSED before any assessment (SK-03).
2. Enumerate the readiness gates from the current `CLAUDE.md` known gaps and
   the frozen design baseline — read the frozen text, not the proposals:
   - a live provider has exercised the full chain end to end;
   - storage schemas have a migration path, or a first-pilot decision is on
     record;
   - validation egress is available in some authorized form on every host
     the pilot will run on;
   - isolation coverage is verified on hosts without `bwrap`;
   - every finding the owner marked blocking is closed or waived on the
     record.
3. For each gate: status OPEN or CLOSED, the evidence on disk that shows it,
   and what closing it requires. A gate with no evidence on disk is OPEN,
   however likely closing it looks.
4. Do not close gates by interpretation, and do not run the pilot, provision
   an environment, or start a live provider (SK-11): this assessment never
   becomes the pilot.

## Output

A report per `.agents/governance/report.schema.json`: `outcome` COMPLETE only
when every gate is CLOSED; otherwise BLOCKED, with each open gate as a
`findings` entry and the full gate table in `summary`.

## Refusals

- No valid stage authorization (SK-03).
- Any request to provision, run or orchestrate the pilot, or to open the
  pilot stage (SK-11).
- A scope that does not cover the paths this skill must read (SK-04).
