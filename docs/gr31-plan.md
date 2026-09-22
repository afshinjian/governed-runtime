# GR-31 Implementation Plan

## Context

The runtime is at `gr-30-passed` (e490fed, clean tree, 1353 tests passing). The
declared phase is First Supervised Automation Pilot readiness and minimal path.
Planning pass GR31-PLAN-001 established that the pilot is **not** blocked by a
missing live transport — `WorkerRelayTransport` (`adapters/relay_process.py`),
`InferenceRelay` and `RelayController.configure_inference_relay` ship and are
tested, and the installed `claude 2.1.259` accepts all eleven flags
`ClaudeCodeProvider.argv` passes. `bin/pilot-run` says otherwise and is stale:
`git show --stat 361e06e` shows it and `relay_process.py` were added in the same
commit.

What actually blocks the pilot is narrower and more fundamental:

1. **No project can be provisioned.** `create_project` sets neither
   `capability_ceiling` nor `budget`; `models.py:914-916` defaults them to
   `frozenset()` and a zero `Budget`, and no production code writes them.
   `guard:gr06_activation_ceiling` (`contract_controller.py:102`) therefore
   refuses every contract on a genuinely created project. Every test provisions
   by mutating the dataclass and calling `store.put_project` directly
   (`tests/gr06_support.py:37`) — the harness bypasses governance.
2. **Three of the four SUPERVISED CONFIRM cells the pilot traverses are
   unenforced.** `_require_transition_authority` proves the capability and
   documents at `controller.py:2003-2008` that it enforces neither preconditions,
   evidence nor the decision step; `policy.resolve` step 10 — the only
   CONFIRM/DECIDE enforcement in the tree — has no production caller. Only row
   6-2 (contract activation) is enforced, by a bespoke boundary.
3. **One capability declaration the pilot exercises is consumed by nothing** —
   `proc.exec.validation` on rows 7.1-2/7.1-3, the gap `CLAUDE.md:26-28` records.

GR-31 closes exactly those. It is the authority surface the pilot stands on, and
it is sized to be reviewed as authority rather than as plumbing. The driver
(GR-32) and the live run (GR-33) follow on a frozen surface.

## BLOCKER DEFINITIONS

The blocker identifiers B1-B7 used throughout this plan are those established by
GR31-PLAN-001 section 2, ACTUAL PILOT BLOCKERS. They are reproduced here so every
reference below resolves within this document.

| id | Blocker | Evidence | Severity |
|---|---|---|---|
| B1 | No governed provisioning. `create_project` sets neither `capability_ceiling` nor `budget`; the model defaults are `frozenset()` and an all-zero `Budget` (`models.py:914-916`), and no production code writes them. `guard:gr06_activation_ceiling` requires `capability_request` to be a subset of the ceiling and `guard:gr06_budget_ceiling` requires the contract budget within project remaining. A genuinely created project therefore cannot activate any contract. Every test provisions by mutating the dataclass and calling `store.put_project` directly (`tests/gr06_support.py:37`, `test_gr08_inference_relay.py:126`) — the harness bypasses governance. This is exactly the gap DESIGN-03 names in its Gap row, and DESIGN-03 is not frozen. | `controller.py:946`, `contract_controller.py:103-104` | BLOCKER |
| B2 | No composition root for a live pilot. `controller.py:2704` `main()` hardcodes `FakeProvider`, has no command for project creation, contract authoring/activation, run allocation, decision recording, relay configuration, review or attestation, and no way to pass `protocol_headers=ClaudeCodeProvider.relay_headers` (used only in tests, `test_gr08_inference_relay.py:154`). | `controller.py:2704-2812` | BLOCKER |
| B3 | The candidate is never observed. `execute_validation` runs against `project.workspace_root` (`validation_controller.py:121`); `propose_commit` and `apply_commit` write the governed worktree (`controller.py:1843`); and `_observe` explicitly refuses to measure that worktree (`controller.py:1186-1193`). A validation receipt taken at any point in the current flow is evidence about the unchanged workspace, not about the candidate. | `controller.py:1184`, `worktree.py`, DESIGN-02 section 1 | BLOCKER (governance meaning) |
| B4 | Governed independent worker review is unreachable. `_check_worker_independence` requires `reviewer.provider_id != author.provider_id` (`guard:gr07_review_provider`), but `configure_inference_relay` permits exactly one origin per controller (`guard:gr08_single_origin`) and `CodexProvider` overrides no `relay_environment`, so the base raises `UNAVAILABLE`. Two live providers cannot coexist. | `worker_controller.py:182`, `relay_controller.py:13`, `journaled_worker.py` | BLOCKER for the review leg only |
| B5 | Owner-confirmed commit is not enforceable by any existing mechanism. Row 7.4-4 is CONFIRM under SUPERVISED, but `_require_transition_authority` proves only the capability and documents at `controller.py:2003-2008` that it enforces neither preconditions, evidence nor the decision step; `policy.resolve` step 10, the only CONFIRM/DECIDE enforcement in the tree, has no production caller. `authorize_commit` instead stamps `authorized_by = _runtime_actor("commit")` (`controller.py:2114`). And the escape hatch is nailed shut: `resolve_decision=lambda ref: False` (`controller.py:2105`) makes a decision-backed precondition permanently unsatisfiable. | `controller.py:2078-2122`, `policy.py:384` | BLOCKER |
| B6 | `evaluate_preconditions` calls `resolve_attestation(ref)` and discards the result (`commit.py:101-104`), so a FAIL `ReviewAttestation` discharges a review precondition. The predicate written for this, `rvw()` (`review.py:160`), has no production caller — only `tests/test_r5_attestation_required.py:124`. Same shape as F03-001. | `commit.py:101-104`, `review.py:160` | MAJOR |
| B7 | A validation precondition is discharged by artifact existence, not by a passing receipt: `resolve_validation=lambda digest: self.store.artifacts.has(digest)` (`controller.py:2104`). | `controller.py:2104` | MAJOR |

B1, B2 and B5 are what GR-31 closes. B3 is answered for Pilot 1 only by owner
decision Q1. B4, B6 and B7 remain open and deferred, and the Q2a guard exists
precisely because B6 and B7 are open.

### Authority-gap identifiers

G1-G4 are the authority gaps GR31-PLAN-001 section 3 found to be exercised by the
pilot and in scope for GR-31. Each names a declaration the frozen transition matrix
already carries that no production path consumes. They are reproduced here so every
G-reference below resolves within this document.

| id | Gap | Row | Closed by |
|---|---|---|---|
| G1 | SUPERVISED CONFIRM enforcement for `run.start` | 5-1, origin to ALLOCATED | C5, `guard:gr31_run_start_confirm` |
| G2 | SUPERVISED CONFIRM enforcement for the first worker invocation of a run | 7.2-1, origin to PENDING, `WHEN(FIRST_INVOCATION_OF_RUN, CONFIRM, AUTO)` | C6, `guard:gr31_first_invocation_confirm` |
| G3 | SUPERVISED CONFIRM enforcement for `commit.authorize` | 7.4-4, PROPOSED to AUTHORIZED | C7, `guard:gr31_commit_authorize_confirm` |
| G4 | Capability enforcement for `proc.exec.validation` | 7.1-2 and 7.1-3, REQUESTED to AUTHORIZED/DENIED | C8, `guard:gr31_validation_exec_authority` |

G1, G2 and G3 are the three unenforced SUPERVISED CONFIRM cells named in the
Context; row 6-2, contract activation, is the fourth such cell on the pilot path
and is already enforced by `guard:gr06_activation_confirmation`. G4 closes the
declaration for rows 7.1-2 and 7.1-3 only; F03-001 remains open for every other row.

## FROZEN OWNER DECISIONS

| id | Decision | Binding consequence for GR-31 |
|---|---|---|
| Q1 | ACCEPT post-commit validation for Pilot 1. After the governed commit is applied, the OWNER may advance the throwaway workspace to that exact governed revision before validation. DESIGN-02 candidate observation/materialization remains deferred. A bounded Pilot-1 accommodation, not the permanent candidate-observation architecture. | GR-31 writes no materialization code. The procedure is documented and executed by the owner in GR-33. Verified safe: `_attributed_globs` (`controller.py:1200`) covers paths of non-PROPOSED intents, so the advance is attributed and raises no REALITY_DRIFT. |
| Q2 | DEFER governed independent worker review. Pilot 1 binds neither review nor validation preconditions. Validation may still execute after owner materialization as observational evidence, but is not a commit precondition. B4, B6, B7 remain explicitly open. Do not claim the production review leg is complete. | GR-31 adds `guard:gr31_preconditions_deferred` (below) so the deferral is structural, not conventional. |
| Q2a | Fail closed on non-empty review/validation preconditions while B6/B7 are open. A temporary GR-31 safety boundary, not closure of B6/B7 and not the final precondition architecture. Do not change review-attestation semantics, validation-precondition semantics, `rvw()`, or generic precondition resolution. GR-33 must not bypass or weaken this guard. | One deletable `require` in `authorize_commit`. `commit.py`, `review.py` untouched. |
| Q3 | Per-field provisioning — separate HUMAN decisions per governance field, not one combined decision. Minimal, aligned with DESIGN-03's per-field direction, without freezing or revising DESIGN-03. Do not claim closure of DESIGN-03 findings. | Two independent operations: ceiling, budget. `policy_digest` provisioning is out of scope (see Assumption A1). |
| Q3a | Minimum vocabulary extension. Add only `project.ceiling.set` to REGISTER. Use existing `DecisionKind.GRANT_CAPABILITY` for the ceiling decision; existing `budget.grant` capability and `DecisionKind.EXTEND_BUDGET` for budget. No new `DecisionKind`. No change to `LEGAL_TRANSITIONS`. No other frozen vocabulary widened. | Exactly one line added to `authority.py`. `models.py` and `transitions.py` row data untouched. |
| Q4 | Consume the commit confirmation directly inside `authorize_commit`, mirroring the existing bounded human-act pattern. Do not route production through `policy.resolve`. Do not change generic `resolve_decision` or commit-precondition semantics. | `controller.py:2105` `resolve_decision=lambda ref: False` stays exactly as it is. `policy.py` untouched. |
| Q5 | The GR-31 implementation authorization must be schema-complete, including `created_at`. | Template supplied below. |

### Assumptions stated, not decided

**A1 — `policy_digest` provisioning is omitted.** It is unnecessary for Pilot 1:
`require_authority` compares
`activation.policy_digest == (project.policy_digest or digest_json({}))`,
so `None` is admissible, and `guard:gr06_policy_document` only runs for POLICY
grantors. Pilot 1 uses HUMAN_DECISION and ROLE_DEFAULT grantors only. This
keeps GR-31 from touching `policy.set`, whose initial-vs-replace semantics
DESIGN-03 §6 records as unsettled. If the owner wants policy provisioning in
GR-31, say so — it is additive, not structural.

## FINAL GR-31 GOAL

> GR-31 gives the runtime a governed, per-field, human-authorized path to
> provision a project's `capability_ceiling` and `budget`, and makes the three
> SUPERVISED CONFIRM cells and the one capability declaration that the First
> Supervised Automation Pilot actually traverses refuse without the human act
> their row declares — while structurally refusing the hollow commit
> preconditions B6/B7 would otherwise admit.

Four transition rows, two provisioning operations, one deferral guard. Nothing else.

## AUTHORIZED IMPLEMENTATION FILES

| Path | Change | Why |
|---|---|---|
| `src/gruntime/authority.py` | One line: add `project.ceiling.set` to the HUMAN/HUMAN_DECISION register row (line 26) | Q3a. DESIGN-03 §3's identifier; the only capability covering a `capability_ceiling` write. `_append` does not validate `capability_used` against REGISTER, so citing an unregistered string would be the unbacked label F03-003 condemned |
| `src/gruntime/decision.py` | New `require_confirmation(...)` predicate — the multi-step check, so each call site leaves one deletable line | CLAUDE.md Tooling: a multi-line guard orphans its body and reports ERROR (pytest exit 4), proving nothing. Mirrors `require_principal_key`'s one-predicate/three-call-sites shape |
| `src/gruntime/contract_controller.py` | New `set_capability_ceiling(...)` and `grant_project_budget(...)` | B1 / Q3. Placed beside `guard:gr06_activation_confirmation` so all bounded human-act boundaries read alike |
| `src/gruntime/controller.py` | `open_run` (row 5-1), `create_invocation` first-invocation branch (row 7.2-1), `authorize_commit` (row 7.4-4 + Q2a guard) | G1, G2, G3, Q2a |
| `src/gruntime/worker_controller.py` | `create_invocation` signature + first-invocation confirmation call | Row 7.2-1 lives here (`worker_controller.py:73`) |
| `src/gruntime/validation_controller.py` | One `require_authority` call in `execute_validation` | G4 — rows 7.1-2/7.1-3 only |
| `tests/test_gr31_provisioning.py` (new) | Ceiling + budget provisioning, incl. the grant-collision test | Kills provisioning guards |
| `tests/test_gr31_supervision_gates.py` (new) | Rows 5-1, 7.2-1, 7.4-4 | Kills confirmation guards |
| `tests/test_gr31_validation_authority.py` (new) | `proc.exec.validation` | Kills G4 |
| `tests/test_gr31_preconditions_deferred.py` (new) | Q2a fail-closed boundary | Kills the deferral guard |
| `bin/check-gr31-mutations` (new) | AST-built needles, per `bin/check-gr09-mutations` | Tag needles report SURVIVED for killed guards |
| `docs/gr31-validation.md` (new) | Per-stage evidence, mutation summaries inline, any log path stated relative to a named root | Answers the CLAUDE.md evidence-gap note; GR-17/23/24 have no per-stage file |
| `CLAUDE.md` | Known-gaps edits + new §"Supervision gates" + correct the `bin/pilot-run` staleness | Accuracy |
| `bin/pilot-run` | Replace the false "only shipped transport" claim with the true blocker; keep it refusing | Stops GR-32 rebuilding `WorkerRelayTransport` |

Everything not listed is out of scope (SK-04).

## EXACT BEHAVIORAL CHANGES

### C1 — Register (`authority.py:26`)

Append `project.ceiling.set` to the `("HUMAN", ("HUMAN_DECISION",), ...)` row.
One identifier. `KERNEL_CAPABILITIES` is derived and unaffected;
`AUTONOMOUS_DENY`, `ROLE_TABLE`, `COST_CAPABILITIES` unchanged — a HUMAN
capability exercised directly by the owner is never role-granted or worker-held.

### C2 — `set_capability_ceiling(project_id, *, ceiling, decision_id)`

One `BEGIN IMMEDIATE` transaction:

1. `require(self._genesis_admits(project_id), ...)` — `# guard:gr31_ceiling_pending_genesis`
   (mirrors `guard:author_contract_pending_genesis`).
2. `require(all(c in REGISTER for c in ceiling), ...)` — `# guard:gr31_ceiling_registered`.
3. `require(_ceiling_decision_admits(decision, project_id, ceiling, now), ...)` —
   `# guard:gr31_ceiling_decision`. The helper requires: `decision_kind` is GRANT_CAPABILITY;
   `subject_kind` PROJECT and `subject_id == project_id`;
   `scope` PROJECT; `decision.grants == frozenset(ceiling)`;
   `decided_by.actor_kind` is HUMAN with `principal_key_id`; `auth_method` ∈ {SESSION, SIGNATURE, MTLS}
   and `decision.auth_method == decided_by.auth_method`, signature present iff
   SIGNATURE; `evidence_shown` non-empty; `16 <= len(nonce) <= 64`;
   `decision.decision_hash == decision_content_hash(decision)`;
   `derive_decision_state(decision, now=now)` is VALID.
4. Append `project.ceiling_set`, `epistemic_class=DECISION`,
   `capability_used="project.ceiling.set"`, `authority_ref=decision_id`,
   `actor=decision.decided_by`, payload recording previous and new ceiling.
5. `self._consume_decision(project_id, decision, discharged=<that event>)`.
6. `project.capability_ceiling = frozenset(ceiling)`; `store.put_project`.

> **The collision this closes.** `human_covers` (`authority.py:84-105`) accepts a
> GRANT_CAPABILITY decision with `subject_kind` PROJECT + `scope` PROJECT as an
> activation grant basis for any capability in `.grants`. Without step 5, one
> decision would both bound the ceiling and confer every capability in it,
> collapsing the two-step containment AX-4 depends on. `human_covers`' final
> conjunct requires VALID, so immediate consumption makes that impossible by
> construction. This is the same discipline `_activate_contract` and
> `configure_inference_relay` already apply. It gets its own test (T4).

### C3 — `grant_project_budget(project_id, *, budget, decision_id)`

Same transaction shape. Differences:

1. `require(project.budget == Budget(), ...)` — `# guard:gr31_budget_initial_only`.
   `budget.grant`'s register verb is "set initial Budget"; extension is
   `budget.extend`, deferred.
2. Decision predicate — `# guard:gr31_budget_decision` — requires
   `decision_kind` is EXTEND_BUDGET (the only budget-shaped member of the frozen
   enum; DESIGN-03 §3 proposes GRANT_BUDGET, which Q3a forbids adding), subject
   PROJECT/`project_id`, scope PROJECT, plus the same authentication,
   evidence, nonce, hash and VALID conjuncts.
3. Event `project.budget_granted`, `capability_used="budget.grant"`.

Neither GRANT_CAPABILITY nor EXTEND_BUDGET is in `SNAPSHOT_BOUND_KINDS`
(`decision.py:60-68`), and PROJECT is not in `SNAPSHOT_BOUND_SUBJECTS`, so
provisioning decisions do not go STALE on the next snapshot. That is the
correct semantics — provisioning is a governance act, not a statement about the
tree — and it is why GRANT_CAPABILITY is right here and APPROVE is not.

### C4 — `require_confirmation(...)` in `decision.py`

One predicate behind all three CONFIRM cells. Requires `decision_kind` is
APPROVE, matching `subject_kind`/`subject_id`, authenticated HUMAN with
`principal_key_id` (delegating to the existing `require_principal_key`),
`evidence_shown` non-empty, nonce length, `decision_hash` recomputes, and
`derive_decision_state(...)` is VALID. Raises `CapabilityDenied` naming the row
(5-1, 7.2-1, 7.4-4) and the transition-matrix line.

### C5 — Row 5-1, `Controller.open_run(project_id, *, confirmation_id)`

New required keyword. One deletable call:
`require_confirmation(decision, project_id=project_id, subject_kind=PROJECT, subject_id=project_id, row="5-1", now=now)`
— `# guard:gr31_run_start_confirm`. Subject is PROJECT because the run does not
exist yet. Consumed via `_consume_decision` citing the `run.allocated` event.

### C6 — Row 7.2-1, `WorkerController.create_invocation(..., confirmation_id=None)`

Confirmation required only when `not self.store.list_invocations(run_id)` —
row 7.2-1 is `WHEN(FIRST_INVOCATION_OF_RUN, CONFIRM, AUTO)`, and over-applying it
would deny a legal second invocation. Subject RUN/`run_id`. One deletable call
— `# guard:gr31_first_invocation_confirm` — inside the first-invocation branch.
Consumed citing the `invocation.created` event, inside that method's existing
`BEGIN IMMEDIATE`.

### C7 — Row 7.4-4 + Q2a, `Controller.authorize_commit(intent_id, *, confirmation_id)`

Two additions, both before any status write:

1. `require(not intent.preconditions.reviews and not intent.preconditions.validations, ...)`
   — `# guard:gr31_preconditions_deferred`. Message cites B6 (`commit.py:101-104`
   discards `resolve_attestation`'s result, so a FAIL attestation discharges)
   and B7 (`controller.py:2104` discharges on artifact existence). Raises
   `PolicyDenied`.
2. `require_confirmation(decision, subject_kind=COMMIT_INTENT, subject_id=intent_id, row="7.4-4", ...)`
   — `# guard:gr31_commit_authorize_confirm`. Consumed citing the
   `commit_intent.authorized` event.

`intent.authorized_by` continues to name `_runtime_actor("commit")` — the runtime
performed the write; the human's act is the consumed decision on `authority_ref`.
`resolve_decision=lambda ref: False` (`controller.py:2105`) is unchanged (Q4).

> COMMIT_INTENT is in `SNAPSHOT_BOUND_SUBJECTS` and APPROVE is in
> `SNAPSHOT_BOUND_KINDS`. A commit confirmation therefore goes STALE if a
> snapshot lands between recording and authorizing. That is HD-INV-4 working
> correctly on "I approve committing this against this reality", and it imposes
> an ordering constraint on GR-33: record the confirmation, then authorize,
> with no intervening snapshot. Tested explicitly (T9).

### C8 — G4, `execute_validation`

`self.require_authority(run_id, 'proc.exec.validation')` —
`# guard:gr31_validation_exec_authority` — immediately before
`_require_egress_authority`, so a denial leaves no `validation.executing` event
for recovery to reconcile. Closes the declaration on rows 7.1-2/7.1-3 only.

## TDD PLAN

Red first, one guard at a time. Every refusal asserted with `pytest.raises(..., match=...)`
— CLAUDE.md Tooling: a passing suite does not re-verify earlier kills.

| # | Test | Asserts |
|---|---|---|
| T1 | `test_activation_refused_without_provisioning` | A project created only via `create_project` cannot activate any contract; refusal names the ceiling. Proves B1 is real and that the fix is load-bearing |
| T2 | `test_ceiling_requires_valid_decision` | Refused with: no decision; APPROVE instead of GRANT_CAPABILITY; wrong subject; SINGLE_ACTION scope; grants != ceiling; missing `principal_key_id`; `auth_method` NONE; SIGNATURE without signature; empty `evidence_shown`; tampered `decision_hash`; CONSUMED/EXPIRED/STALE/VOID state |
| T3 | `test_ceiling_entries_must_be_registered` | An unregistered capability in `ceiling` is refused |
| T4 | `test_ceiling_decision_cannot_also_grant` | The collision. After `set_capability_ceiling`, the same `decision_id` passed as `decision_ids=` to `activate_contract` is refused — `human_covers` sees CONSUMED. Activation requires its own, separate grant decision |
| T5 | `test_budget_initial_grant_only` | Succeeds on a zero `Budget`; refused on a non-zero one (extension is `budget.extend`, deferred) |
| T6 | `test_provisioning_refused_mid_genesis` | Both operations refuse while the creation transaction is open |
| T7 | `test_provisioning_is_atomic` | A failure after the append leaves neither the event nor the field change; the decision stays VALID |
| T8 | `test_run_start_and_first_invocation_confirm` | 5-1 and 7.2-1 refuse without confirmation; refusals name their rows |
| T9 | `test_second_invocation_needs_no_confirmation` | The WHEN is honoured, not over-applied. Plus: a commit confirmation invalidated by an intervening snapshot is refused as STALE |
| T10 | `test_commit_authorize_confirm` | 7.4-4 refuses without confirmation; the decision is CONSUMED after; replay refused |
| T11 | `test_preconditions_deferred` | Non-empty `preconditions.reviews` or `.validations` refused; empty passes. Message cites B6/B7 |
| T12 | `test_validation_requires_proc_exec` | `execute_validation` refused without `proc.exec.validation` in the activation; no `validation.executing` event appended on refusal |
| T13 | `test_gr31_happy_path` | create → provision ceiling → provision budget → author → activate → `open_run` → invoke → propose → authorize → apply, each with its confirmation. The GR-33 sequence, on `FakeProvider` |

## MUTATION PLAN

`bin/check-gr31-mutations`, needles built from the AST (`bin/check-gr09-mutations`
is the model — a `# guard:` tag needle mutates only the comment and reports
SURVIVED for a killed guard).

| Guard | Killed by |
|---|---|
| `gr31_ceiling_pending_genesis` | T6 |
| `gr31_ceiling_registered` | T3 |
| `gr31_ceiling_decision` | T2, T4 |
| `gr31_budget_initial_only` | T5 |
| `gr31_budget_decision` | T2 (budget variants) |
| `gr31_run_start_confirm` | T8 |
| `gr31_first_invocation_confirm` | T8, T9 |
| `gr31_commit_authorize_confirm` | T10 |
| `gr31_preconditions_deferred` | T11 |
| `gr31_validation_exec_authority` | T12 |
| `require_confirmation` internal predicate | T8, T10 |

Operating rules, from CLAUDE.md Tooling:

- Allow ≥ 10 minutes. An interrupted run skips its restore trap and leaves
  the mutant in `src/`.
- After any interruption: `git diff --quiet -- src` before anything else, then
  restore from the retained `/tmp` backup.
- An ERROR (pytest exit 4) means the guard is multi-line and orphaned its
  body — refactor into the helper and retry. Never record an ERROR as evidence.
- Re-run `bin/check-gr28-mutations` and `bin/check-gr29-mutations`. GR-31
  changes `authorize_commit` and `create_invocation`; a later stage hollowing an
  earlier kill without failing it is the GR-23→GR-24 failure CLAUDE.md records.

## ACCEPTANCE CRITERIA

1. A project provisioned only through `create_project` + `set_capability_ceiling`
   + `grant_project_budget` can activate a contract; one without cannot, and the
   refusal names the ceiling.
2. Every predicate in T2 refuses; each refusal is asserted with `match=`.
3. A ceiling decision cannot serve as an activation grant basis (T4).
4. `open_run`, first `create_invocation`, and `authorize_commit` each refuse
   without their row's confirmation, citing 5-1, 7.2-1, 7.4-4.
5. The second invocation of a run requires no new confirmation.
6. A commit confirmation superseded by an intervening snapshot refuses as STALE.
7. `authorize_commit` refuses any non-empty review or validation precondition,
   citing B6/B7.
8. `execute_validation` refuses without `proc.exec.validation`, appending no
   `validation.executing` event.
9. `bin/check-gr31-mutations`: every new guard KILLED; zero SURVIVED, zero ERROR.
10. `bin/check-gr28-mutations` and `bin/check-gr29-mutations` still fully kill.
11. Full suite ≥ 1353 + new, zero failures. `bin/check-governed-skills` passes.
12. `docs/gr31-validation.md` exists, mutation summaries inline, log paths rooted.
13. CLAUDE.md records: `proc.exec.validation` closed for rows 7.1-2/7.1-3
    only; F03-001 open for the remaining rows; F04-004 unaffected; B4/B6/B7
    open and deferred; the Q2a guard temporary; DESIGN-03 not revised and no
    DESIGN-03 finding closed; `project.ceiling.set` added as the minimum
    vocabulary extension.
14. `bin/pilot-run` no longer claims `ProcessTransport` is the only shipped
    transport, and still refuses.
15. `git diff --check HEAD` clean; tree left uncommitted for independent
    review (SK-09).

## EXPLICIT NON-GOALS

- The live transport — `WorkerRelayTransport` already exists. Rebuilding it
  is the single most likely wrong turn, and `bin/pilot-run` is why.
- Any live provider invocation, relay configuration against a real origin, or
  network egress. No `claude` subprocess is spawned by GR-31.
- The composition root / stage driver (GR-32) and the pilot run itself (GR-33).
- Candidate observation / materialization; any root or target field on
  `RealitySnapshot`; DESIGN-02.
- B6/B7 themselves — `commit.py`, `review.py`, `rvw()`, `resolve_review_evidence`
  and generic precondition resolution are untouched. The Q2a guard defers; it
  does not close.
- B4 / independent review binding. Do not claim the production review leg is
  complete.
- Confirmation enforcement on any row outside {5-1, 7.2-1, 7.4-4}.
- Routing production through `policy.resolve`; changing `resolve_decision`;
  any blanket F03-001 work.
- New `DecisionKind` members; changes to `LEGAL_TRANSITIONS`; new transition rows;
  any register entry beyond `project.ceiling.set`.
- `policy_digest` provisioning (Assumption A1); `budget.extend`; `project.mode.set`;
  SET_MODE; AUTONOMOUS.
- Stage entity, StageLifecycle, project/run lifecycle advance, suspension clearing.
- Any edit to frozen design text or to any record under `design/review/` (SK-10).
- Freezing or revising DESIGN-03; claiming closure of any DESIGN-03 finding.
- Any commit, tag, push, staging, or opening of GR-32 (SK-09, SK-11).
- Repairing, coercing or scanning for malformed decision rows — GR-29 fails
  closed by design.

## VERIFICATION

```
.venv/bin/python -m pytest -q                       # >= 1353 + new, 0 failures
.venv/bin/python -m pytest -q tests/test_gr31_*.py
bin/check-governed-skills
bin/check-gr31-mutations                            # allow >= 10 min
bin/check-gr28-mutations && bin/check-gr29-mutations  # earlier kills intact
git diff --quiet -- src || echo "MUTANT LEFT IN TREE — restore before proceeding"
git diff --check HEAD
bin/pilot-run; test $? -eq 2                        # still refuses, honestly now
```

End-to-end without a live provider: T13 drives the full GR-33 sequence on
`FakeProvider` through `python -m gruntime.controller`-equivalent calls, proving
the authority surface before any network exists.

### Refusal conditions — implementation stops, does not improvise

- Any change required under `design/` frozen text → refuse; that is a DESIGN-03
  revision, not GR-31.
- `bin/mutate` reports ERROR → the guard is multi-line; refactor into the helper.
  Never record the ERROR as evidence.
- `bin/mutate` interrupted → `git diff --quiet -- src` first, restore, then continue.
- A guard's kill needs monkeypatching a path the pilot never takes → the guard is
  in the wrong place.
- A second register entry or a `DecisionKind` member turns out to be needed →
  stop and return to the owner (Q3a is explicit).
- Any test provisioning via `store.put_project` instead of the new operations →
  B1 is not actually closed.

## GR-32 HANDOFF

**Goal:** a supervised stage driver — the composition root that wires the already-shipped
live transport, one owner-confirmed step at a time. Implements nothing new in the kernel.

**Given by GR-31:** a frozen authority surface; provisioning; three enforced CONFIRM cells.

**Scope:**

- Replace `controller.py:2704` `main()`'s hardcoded `FakeProvider` with selectable
  adapters; add `ClaudeCodeProvider(state_dir, transport=WorkerRelayTransport(...), read_artifact=...)`.
- Wire `protocol_headers=ClaudeCodeProvider.relay_headers` into
  `configure_inference_relay` — currently used only in `test_gr08_inference_relay.py:154`.
- Commands for: project creation, ceiling/budget provisioning, decision recording
  (the `confirmation_id` producers), contract authoring/activation, run allocation,
  relay configuration, invoke, propose/authorize/apply, snapshot, validate.
- Every confirmed step prompts the owner and records a real `HumanDecision`;
  the driver never fabricates one.
- Rewrite `bin/pilot-run` as a true preflight against the GR-31 surface.

**Known constraints to carry:** one relay origin per controller
(`guard:gr08_single_origin`); `ANTHROPIC_BASE_URL` + the governed-local-bridge
placeholder come from `ClaudeCodeProvider.relay_environment`; `secret.read` must be
in the ceiling but never in worker capabilities; `/usr/local/bin/claude` is under
`/usr`, so the existing ro-binds cover it.

## GR-33 HANDOFF

**Goal:** first live invocation — fresh store, throwaway repository, one owner-confirmed
step at a time.

**Ordering constraints inherited from GR-31** (violating these fails closed):

- Record each confirmation immediately before the act it discharges, with no
  intervening snapshot. APPROVE is snapshot-bound; a snapshot in between
  makes it STALE.
- The ceiling decision and the activation grant decisions are **different
  decisions**. The ceiling decision is CONSUMED by provisioning (T4).
- Bind no review and no validation precondition — `guard:gr31_preconditions_deferred`
  refuses them, and GR-33 must not bypass or weaken it (Q2a).

**Sequence:** create → provision ceiling → provision budget → author contract →
record activation grants → activate → `open_run` (confirm) → configure relay
(grant + approval) → `create_invocation` (confirm) → invoke → `propose_commit` →
`authorize_commit` (confirm) → `apply_commit` → owner advances the throwaway
workspace to the governed revision (Q1) → `take_snapshot` → `execute_validation`
as observational evidence.

Ceiling must include at least: `fs.read`, `fs.write`, `commit.propose`,
`validation.request`, `proc.exec.validation`, `net.egress.allowlist`, `secret.read`.
Validation operation must declare `network=NONE` — ALLOWLIST has no enforcing
adapter and ANY is unreachable (`CLAUDE.md:20-25`).

Q1's accommodation is Pilot-1 only and must be recorded as such in the GR-33
evidence: the validation receipt is evidence about a materialized post-commit
workspace, not about a candidate, and it discharges no precondition.

## IMPLEMENTATION AUTHORIZATION TEMPLATE

Schema-complete per `.agents/governance/authorization.schema.json` (Q5). The owner
supplies `authorization_id`, `principal` and a real `created_at`; a skill never
signs one (SK-08).

```json
{
  "authorization_id": "gr31-implementation-001",
  "skill": "governed-stage-implementer",
  "mode": "implementation",
  "stage": "GR-31",
  "scope": [
    "src/gruntime/authority.py",
    "src/gruntime/decision.py",
    "src/gruntime/contract_controller.py",
    "src/gruntime/controller.py",
    "src/gruntime/worker_controller.py",
    "src/gruntime/validation_controller.py",
    "tests/test_gr31_provisioning.py",
    "tests/test_gr31_supervision_gates.py",
    "tests/test_gr31_validation_authority.py",
    "tests/test_gr31_preconditions_deferred.py",
    "bin/check-gr31-mutations",
    "bin/pilot-run",
    "docs/gr31-validation.md",
    "CLAUDE.md"
  ],
  "authorized_by": {
    "actor_kind": "HUMAN",
    "principal": "<owner name or principal key id>"
  },
  "created_at": "2026-09-22T00:00:00Z",
  "governance_mode": "SUPERVISED",
  "may_commit_tag_push": false,
  "notes": "Implements GR31-PLAN-001 as finalized under owner decisions Q1-Q5, Q3a and Q2a. Adds exactly one REGISTER entry (project.ceiling.set); adds no DecisionKind member and no LEGAL_TRANSITIONS change. Enforces SUPERVISED CONFIRM on rows 5-1, 7.2-1 and 7.4-4 only. Closes proc.exec.validation for rows 7.1-2/7.1-3 only; F03-001 remains open for the other rows and F04-004 is unaffected. The non-empty-precondition refusal is a temporary Pilot-1 safety boundary and is not closure of B6/B7. B4, B6 and B7 remain open and deferred; the production review leg is not complete. DESIGN-02 and DESIGN-03 are neither implemented nor revised and no DESIGN-03 finding is claimed closed. No commit, tag, push or stage (SK-09); the tree is left uncommitted for independent review."
}
```

Implementation review afterwards requires a separate authorization naming
`governed-independent-reviewer` / `implementation-review`, by a reviewer that is
not the session that produced the change (SK-07).

## VERDICT

GR31_IMPLEMENTATION_PLAN_READY
