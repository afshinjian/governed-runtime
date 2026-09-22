---
name: governed-repo-reality-check
description: Read-only reality check of the repository before stage work. Observes the git state, the phase line, the CLAUDE.md claims, evidence and the test baseline, then reports every divergence between documented claims and what is on disk. Never mutates anything. Requires a stage authorization.
---

# governed-repo-reality-check

## Purpose

Establish what is true on disk before a stage is planned or authorized, so
that a plan rests on observed reality rather than on assumption. The output
is a report — a set of claims with evidence — and never an edit (SK-12).

## Mode

- `reality-check` — observe and report; read-only.

## Authorization

This skill runs only under a stage authorization
(`.agents/governance/authorization.schema.json`) whose `skill` names this
skill, whose `mode` is `reality-check`, whose `stage` names the stage the
check is taken for (SK-11) and whose `scope` lists the paths it may read.
Without a valid authorization: REFUSED (SK-03).

## Procedure

1. Read the authorization. An absent, malformed or non-human authorization
   means REFUSED before anything else happens (SK-03, SK-08).
2. Read the phase line and the known-gaps section of `CLAUDE.md`.
3. Observe the repository, read-only:
   - `git status --porcelain` and `git log --oneline -5` — tree state and the
     phase line at HEAD;
   - the newest entries under `docs/evidence/` and `.evidence/` where
     readable, against the evidence claims in `CLAUDE.md`;
   - presence and freshness of the last recorded baseline summary.
4. Compare each documented claim with what is on disk. Record every
   divergence as a finding: severity NOTE or MINOR for drift in prose, MAJOR
   for drift in an evidence claim, BLOCKER for drift on a governance
   invariant (phase line, frozen baseline, review-record integrity).
5. Do not write, create, delete or commit anything. If an observation cannot
   be made without a mutation, record it as a finding instead (SK-02).

## Output

A report per `.agents/governance/report.schema.json`: `outcome` COMPLETE, or
BLOCKED when a finding makes stage work unsafe; the paths read in
`scope_observed`; every divergence as a `findings` entry; a `summary` stating
the observed phase and tree state.

## Refusals

- No valid stage authorization (SK-03).
- A scope that does not cover the paths this skill must read (SK-04).
- Any request that this skill fix, clean or prepare what it observes —
  observation never mutates (SK-02).
