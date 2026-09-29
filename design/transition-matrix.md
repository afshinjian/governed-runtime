# DESIGN-01 — Transition Matrix

Exhaustive, normative state machine for the governed runtime.
Entities and enumerations are defined in `domain-model.md`.
Capability identifiers are defined in `authority-matrix.md`.

---

## 0. Orthogonality rule

State is **not** a single enum. Three independent fields are carried and
evaluated separately:

| axis | field | carried by | defined in |
|---|---|---|---|
| 1 | `project.lifecycle` : `ProjectLifecycle` | `Project` | domain-model §10.1 |
| 2 | `stage.lifecycle` : `StageLifecycle` | `Stage` | domain-model §10.2 |
| 3 | `*.suspension` : `SuspensionState` | `Project`, `Stage`, `StageRun` | domain-model §10.3 |

**O-1** No axis-1 value implies an axis-2 value, and vice versa.
**O-2** Suspension is never encoded as a lifecycle value on either other axis. A
suspended stage retains its lifecycle value and resumes into it.
**O-3** A transition on one axis MUST NOT write a field of another axis. Cascades
are expressed as separate, separately-audited transitions.
**O-4** Effective permission to act = (axis-1 gate) ∧ (axis-2 gate) ∧ (axis-3 gate).
The most restrictive axis wins.

### 0.1 Axis-3 gate

| suspension value | new worker invocations | new validations | new commits | snapshots | decisions | transitions on axes 1/2 |
|---|---|---|---|---|---|---|
| `NONE` | allowed | allowed | allowed | allowed | allowed | allowed |
| `QUIESCING` | denied | in-flight only | denied | allowed | allowed | only to `*_ABORTED`/`AWAITING_DECISION` |
| `SUSPENDED_BY_HUMAN` | denied | denied | denied | allowed | allowed | only `ABANDONED` or resume |
| `SUSPENDED_BY_POLICY` | denied | denied | denied | allowed | allowed | only `ABANDONED` or resume |
| `SUSPENDED_BY_ESCALATION` | denied | denied | denied | allowed | allowed | only `ABANDONED` or resume |
| `SUSPENDED_BY_BUDGET` | denied | denied | denied | allowed | allowed | only `ABANDONED` or resume |
| `SUSPENDED_BY_DRIFT` | denied | denied | denied | allowed | allowed | only `ABANDONED` or resume |
| `SUSPENDED_BY_INTEGRITY` | denied | denied | denied | allowed | allowed | none except `ABANDONED` |

---

## 1. Column semantics

| column | meaning |
|---|---|
| `preconditions` | boolean predicate over entity fields; ALL must hold |
| `required_evidence` | a conjunction of citations that must exist and be current, each typed on its own and each possibly a disjunction of alternatives (`G-1`): an evidence citation (receipt or snapshot) discharges the row's criterion; a prerequisite citation — an activation, a decision, an `Escalation`, or an `AuditEvent` the row names, including one that persisted a cited artifact or durable identity — must exist and discharges a criterion only where another rule gives it that effect, as a waiver decision does; an element naming no record is a precondition; a citation of any other kind is not admitted by `G-1`; `—` means none |
| `required_capability` | the single `CapabilityId` the actor must hold at the transition, by any authority form in `AX-1` (authority-matrix §5, §5.2, §5.3, `AX-7`) or under `AX-1`'s named `decision.record` exception (`AX-15`); absent ⇒ DENY |
| `supervised_policy` | verdict when `project.governance_mode = SUPERVISED` |
| `autonomous_policy` | verdict when `project.governance_mode = AUTONOMOUS` |
| `illegal_because` | `—` for legal rows; populated only in §9 |

### 1.1 Policy verdict vocabulary

| verdict | meaning |
|---|---|
| `AUTO` | runtime performs it; audit event only |
| `NOTIFY` | runtime performs it and emits an out-of-band notification |
| `CONFIRM` | requires `HumanDecision{kind: APPROVE}` recorded **before** the transition |
| `DECIDE(K)` | requires `HumanDecision{kind: K}` recorded before the transition |
| `DENY` | not permitted in this mode; attempt raises `Escalation(POLICY_CONFLICT)` |

### 1.2 Evidence shorthand

| token | expands to |
|---|---|
| `SNAP` | `RealitySnapshot` with `completeness = COMPLETE` over the relevant scope |
| `VR(pass)` | `ValidationReceipt` with `outcome = PASS`, bound to current `SNAP` |
| `VR(any)` | any `ValidationReceipt` for the op |
| `RVW(v)` | `ReviewAttestation` minted by the kernel under `review.attest` over a `Review` with `verdict = v`, recording that the `ReviewSpec` quorum and `independence_required` are met. The attestation is the EVIDENCE; the verdict inside the `Review` stays CLAIM (`G-1`, evidence-model §2.1) |
| `WR` | `WorkerReceipt` |
| `CR` | `CommitReceipt` with `verification = MATCHED` |
| `DEC(K)` | `HumanDecision{kind: K}` with non-empty `evidence_shown` and `decision_state = VALID` at the moment of the transition (`HD-INV-4`) |
| `ACT` | un-revoked, un-expired `ContractActivationRecord` |
| `ESC(s)` | `Escalation` with `status = s` |

---

## 2. Axis 1 — Project lifecycle

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `∅` | `DRAFT` | `created_by.actor_kind = HUMAN` and `workspace_root` exists | `SNAP` | `project.create` | `AUTO` | `DENY` | — |
| `DRAFT` | `PLANNING` | `roadmap_id` present, naming the `Roadmap` persisted and bound by this transition's own atomic import transaction (§11 `RI-1`), and `roadmap.drift_state = IN_SYNC` and `dependency_edges` acyclic; `capability_ceiling` non-empty and `budget` non-zero, each already written by its §10 row before this transition | `SNAP` | `roadmap.import` | `AUTO` | `AUTO` | — |
| `DRAFT` | `ABANDONED` | none | — | `project.abandon` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `PLANNING` | `DRAFT` | `roadmap.drift_state ∈ {UNREADABLE, DIVERGED}` | — | `roadmap.import` | `NOTIFY` | `NOTIFY` | — |
| `PLANNING` | `ACTIVE` | at least one stage with `lifecycle = READY` and `capability_ceiling` non-empty and `budget` non-zero | `SNAP` | `project.lifecycle.advance` | `CONFIRM` | `AUTO` | — |
| `PLANNING` | `ABANDONED` | none | — | `project.abandon` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `ACTIVE` | `SETTLING` | every stage `lifecycle ∈ {SATISFIED, REJECTED, ABANDONED}` and no non-terminal `StageRun` | `SNAP` | `project.lifecycle.advance` | `AUTO` | `AUTO` | — |
| `ACTIVE` | `ABANDONED` | none | — | `project.abandon` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `SETTLING` | `ACTIVE` | some stage demoted to `READY` or `observed_satisfaction = STALE`, or roadmap revision added a stage | `SNAP` | `project.lifecycle.advance` | `NOTIFY` | `AUTO` | — |
| `SETTLING` | `COMPLETED` | every stage `observed_satisfaction ∈ {SATISFIED}` or terminal with recorded `DEC(ACCEPT_RISK)`; zero open `ESC(OPEN)`; zero `Finding.blocks_satisfaction` | `SNAP`, `VR(pass)` per mandatory mechanical criterion, `RVW(PASS or PASS_WITH_FINDINGS)` per mandatory judgmental criterion | `project.lifecycle.advance` | `DECIDE(APPROVE)` | `NOTIFY` | — |
| `SETTLING` | `ABANDONED` | none | — | `project.abandon` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `COMPLETED` | `ACTIVE` | new roadmap revision or a `SATISFIED` stage demoted to `STALE` | `SNAP` | `project.lifecycle.advance` | `DECIDE(APPROVE)` | `NOTIFY` | — |
| `COMPLETED` | `ARCHIVED` | audit chain verifies end-to-end; all `EPHEMERAL` artifacts collected | `SNAP` | `project.archive` | `DECIDE(APPROVE)` | `DECIDE(APPROVE)` | — |
| `ABANDONED` | `ARCHIVED` | audit chain verifies end-to-end | — | `project.archive` | `AUTO` | `AUTO` | — |

`ARCHIVED` is terminal on axis 1: no outbound legal transitions.

---

## 3. Axis 2 — Stage lifecycle

Every row additionally requires `project.lifecycle ∈ {ACTIVE, SETTLING}` and
`stage.suspension = NONE` and `project.suspension = NONE`, except where stated.

**Startup exception.** The two materialization rows `∅ → PENDING` and
`PENDING → READY` are additionally legal while `project.lifecycle = PLANNING`.
Without this exception no stage could reach `READY` before the project is
`ACTIVE`, while `PLANNING → ACTIVE` (§2) requires a `READY` stage — the project
could never start. No other axis-2 row is legal during `PLANNING`: a stage may be
materialized and made dependency-ready there, and nothing else.

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `∅` | `PENDING` | stage present in `roadmap.stage_order`; `project.lifecycle ∈ {PLANNING, ACTIVE, SETTLING}` per the startup exception | — | `roadmap.import` | `AUTO` | `AUTO` | — |
| `PENDING` | `READY` | every `depends_on` stage has `observed_satisfaction = SATISFIED`, vacuously true for a stage with no dependencies; `project.lifecycle ∈ {PLANNING, ACTIVE, SETTLING}` per the startup exception | `SNAP` plus each dependency's satisfying receipts current against it | `stage.lifecycle.advance` | `AUTO` | `AUTO` | — |
| `PENDING` | `ABANDONED` | none | — | `stage.abandon` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `READY` | `PENDING` | some dependency's `observed_satisfaction` left `SATISFIED` | `SNAP` | `stage.lifecycle.advance` | `NOTIFY` | `AUTO` | — |
| `READY` | `CONTRACTED` | a `StageContract` reached `ACTIVE` for this stage and `C-INV-1` holds | contract `contract_hash` verified | `contract.activate` | `CONFIRM` | `AUTO` | — |
| `READY` | `ABANDONED` | none | — | `stage.abandon` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `CONTRACTED` | `RUNNING` | a `StageRun` reached `DISPATCHED`; `attempt_count < max_attempts`; budget remaining on every dimension | `ACT`, `SNAP` as `input_snapshot_id` | `run.start` | `CONFIRM` | `AUTO` | — |
| `CONTRACTED` | `READY` | active contract reached `REVOKED` or `EXPIRED` and no run started | — | `contract.revoke` | `NOTIFY` | `AUTO` | — |
| `CONTRACTED` | `ABANDONED` | none | — | `stage.abandon` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `RUNNING` | `AWAITING_VALIDATION` | run has ≥1 `WR` and every mandatory mechanical criterion has a `ValidationOperation` in `{REQUESTED, AUTHORIZED, EXECUTING, COMPLETED}` | `WR` | `stage.lifecycle.advance` | `AUTO` | `AUTO` | — |
| `RUNNING` | `CONTRACTED` | run reached `CLOSED_ABORTED` and contract still `ACTIVE` and `attempt_count < max_attempts` | `WR` with `termination_reason` recorded | `run.abort` | `NOTIFY` | `AUTO` | — |
| `RUNNING` | `AWAITING_DECISION` | an `ESC(OPEN)` with `auto_resolvable = false` is bound to this run | `ESC(OPEN)` | `escalation.raise` | `AUTO` | `AUTO` | — |
| `RUNNING` | `ABANDONED` | none | — | `stage.abandon` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `AWAITING_VALIDATION` | `AWAITING_REVIEW` | every mandatory `MECHANICAL` criterion has `CriterionState.outcome ∈ {MET, WAIVED}` against the current snapshot | `VR(pass)` per such criterion, all bound to the same current `SNAP` | `stage.lifecycle.advance` | `AUTO` | `AUTO` | — |
| `AWAITING_VALIDATION` | `RUNNING` | ≥1 mandatory mechanical criterion `UNMET` and `attempt_count < max_attempts` and budget remains | `VR(any)` showing `FAIL` | `run.start` | `NOTIFY` | `AUTO` | — |
| `AWAITING_VALIDATION` | `AWAITING_DECISION` | `attempt_count ≥ max_attempts`, or a required validator is unavailable, or a `DETERMINISTIC` spec produced divergent receipts | `ESC(OPEN)` with trigger `REPEATED_FAILURE`, `VALIDATION_UNAVAILABLE` or `NONDETERMINISM` | `escalation.raise` | `AUTO` | `AUTO` | — |
| `AWAITING_VALIDATION` | `ABANDONED` | none | — | `stage.abandon` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `AWAITING_REVIEW` | `SATISFIED` | `observed_satisfaction = SATISFIED`; zero findings with `blocks_satisfaction = true`; every mandatory review spec met at quorum with `independence_required` honoured; all in-scope mutations landed via `CR` | `SNAP` current, `VR(pass)` set complete, `RVW(PASS)` or `RVW(PASS_WITH_FINDINGS)` per spec, `CR` per mutation | `stage.satisfy` | `CONFIRM` | `NOTIFY` | — |
| `AWAITING_REVIEW` | `RUNNING` | ≥1 finding with `blocks_satisfaction = true` and `attempt_count < max_attempts` and budget remains | `RVW(FAIL)` or `RVW(PASS_WITH_FINDINGS)` carrying a blocking finding | `run.start` | `NOTIFY` | `AUTO` | — |
| `AWAITING_REVIEW` | `AWAITING_VALIDATION` | a review invalidated a prior receipt, or a new snapshot demoted a criterion to `UNEVALUATED` | `SNAP` newer than the cited `VR(pass)` | `stage.lifecycle.advance` | `AUTO` | `AUTO` | — |
| `AWAITING_REVIEW` | `AWAITING_DECISION` | a blocking finding is `waivable` and `attempt_count ≥ max_attempts`, or a mandatory review returned `INCONCLUSIVE`, or only `SELF_REVIEW` is available for an `INDEPENDENT` spec | `RVW` set plus `ESC(OPEN)` | `escalation.raise` | `AUTO` | `AUTO` | — |
| `AWAITING_REVIEW` | `ABANDONED` | none | — | `stage.abandon` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `AWAITING_DECISION` | `SATISFIED` | every blocking finding is `WAIVED` or `FIXED`; every unmet mandatory criterion is `waivable = true` and carries a waiver; `observed_satisfaction ∈ {SATISFIED, PARTIAL}` with each shortfall waived | `DEC(WAIVE)` or `DEC(ACCEPT_RISK)` per shortfall, plus the `VR(pass)` and `RVW` set for everything not waived, plus `SNAP` | `stage.satisfy` | `DECIDE(APPROVE)` | `DECIDE(APPROVE)` | — |
| `AWAITING_DECISION` | `RUNNING` | `DEC(OVERRIDE)` or `DEC(APPROVE)` directs rework; budget extended if exhausted | `DEC(OVERRIDE)` or `DEC(EXTEND_BUDGET)` | `run.start` | `DECIDE(OVERRIDE)` | `DECIDE(OVERRIDE)` | — |
| `AWAITING_DECISION` | `REJECTED` | `DEC(REJECT)` recorded against the stage | `DEC(REJECT)` | `stage.reject` | `DECIDE(REJECT)` | `DECIDE(REJECT)` | — |
| `AWAITING_DECISION` | `ABANDONED` | `DEC(ABANDON)` recorded | `DEC(ABANDON)` | `stage.abandon` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `SATISFIED` | `READY` | `observed_satisfaction` became `STALE` or `CONTRADICTED` under a newer `SNAP`, or a new contract revision supersedes the fulfilled one | `SNAP` newer than `observed_satisfaction_at` with drift inside stage scope | `stage.lifecycle.advance` | `NOTIFY` | `AUTO` | — |
| `REJECTED` | `READY` | a new `StageContract` for this stage reached `DRAFT` and `DEC(OVERRIDE)` permits retry | `DEC(OVERRIDE)` | `stage.lifecycle.advance` | `DECIDE(OVERRIDE)` | `DECIDE(OVERRIDE)` | — |

`ABANDONED` is terminal on axis 2. `SATISFIED` and `REJECTED` are terminal except
for the two demotion rows above, each of which requires fresh evidence or a decision.

---

## 4. Axis 3 — Suspension (Project, Stage, Run — evaluated per holder)

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `NONE` | `QUIESCING` | suspension requested and ≥1 in-flight `WorkerInvocation` or `ValidationOperation` on the holder | — | `suspension.set` | `AUTO` | `AUTO` | — |
| `NONE` | `SUSPENDED_BY_HUMAN` | no in-flight operations | `DEC(SUSPEND)` | `suspension.set` | `DECIDE(SUSPEND)` | `DECIDE(SUSPEND)` | — |
| `NONE` | `SUSPENDED_BY_POLICY` | an active policy rule matched | policy evaluation record | `suspension.set` | `AUTO` | `AUTO` | — |
| `NONE` | `SUSPENDED_BY_ESCALATION` | `ESC(OPEN)` with `auto_resolvable = false` targets this holder | `ESC(OPEN)` | `suspension.set` | `AUTO` | `AUTO` | — |
| `NONE` | `SUSPENDED_BY_BUDGET` | any `budget_used` field ≥ its `budget` ceiling | `WR` or `VR(any)` usage records | `suspension.set` | `AUTO` | `AUTO` | — |
| `NONE` | `SUSPENDED_BY_DRIFT` | `SNAP.drift_summary.unattributed > 0` inside the holder's scope | `SNAP` with drift | `suspension.set` | `AUTO` | `AUTO` | — |
| `NONE` | `SUSPENDED_BY_INTEGRITY` | hash-chain break, contract hash mismatch, forged receipt, void `HumanDecision`, or a `reconciliation_state = UNRESOLVABLE` commit intent detected | failing chain verification record, or the `ESC(OPEN)` carrying `RECOVERY_AMBIGUITY` | `suspension.set` | `AUTO` | `AUTO` | — |
| `QUIESCING` | `SUSPENDED_BY_HUMAN` | in-flight set empty | `DEC(SUSPEND)`, terminal receipt per drained operation | `suspension.set` | `AUTO` | `AUTO` | — |
| `QUIESCING` | `SUSPENDED_BY_POLICY` | in-flight set empty | terminal receipt per drained operation | `suspension.set` | `AUTO` | `AUTO` | — |
| `QUIESCING` | `SUSPENDED_BY_ESCALATION` | in-flight set empty | `ESC(OPEN)`, terminal receipt per drained operation | `suspension.set` | `AUTO` | `AUTO` | — |
| `QUIESCING` | `SUSPENDED_BY_BUDGET` | in-flight set empty | usage records | `suspension.set` | `AUTO` | `AUTO` | — |
| `QUIESCING` | `SUSPENDED_BY_DRIFT` | in-flight set empty | `SNAP` with drift | `suspension.set` | `AUTO` | `AUTO` | — |
| `QUIESCING` | `SUSPENDED_BY_INTEGRITY` | in-flight set empty or forcibly terminated | failing verification record | `suspension.set` | `AUTO` | `AUTO` | — |
| `QUIESCING` | `NONE` | suspension request withdrawn before draining completed | `DEC(RESUME)` | `suspension.clear` | `DECIDE(RESUME)` | `AUTO` | — |
| `SUSPENDED_BY_HUMAN` | `NONE` | `DEC(RESUME)` recorded | `DEC(RESUME)` | `suspension.clear` | `DECIDE(RESUME)` | `DECIDE(RESUME)` | — |
| `SUSPENDED_BY_POLICY` | `NONE` | matching policy rule no longer matches, or `DEC(OVERRIDE)` recorded | policy re-evaluation record, or `DEC(OVERRIDE)` | `suspension.clear` | `CONFIRM` | `AUTO` | — |
| `SUSPENDED_BY_ESCALATION` | `NONE` | every bound escalation has `status ∈ {RESOLVED, WITHDRAWN}` | `DEC` referenced by each resolution | `suspension.clear` | `DECIDE(RESUME)` | `AUTO` if all resolutions were `auto_resolvable` else `DECIDE(RESUME)` | — |
| `SUSPENDED_BY_BUDGET` | `NONE` | budget extended so every dimension has headroom | `DEC(EXTEND_BUDGET)` | `suspension.clear` | `DECIDE(EXTEND_BUDGET)` | `DECIDE(EXTEND_BUDGET)` | — |
| `SUSPENDED_BY_DRIFT` | `NONE` | a new `SNAP` has `drift_summary.unattributed = 0`, or drift accepted | `SNAP` clean, or `DEC(ACCEPT_RISK)` | `suspension.clear` | `DECIDE(ACCEPT_RISK)` | `CONFIRM` | — |
| `SUSPENDED_BY_INTEGRITY` | `NONE` | chain re-verified end-to-end and the violating records quarantined | passing chain verification record plus `DEC(OVERRIDE)` | `suspension.clear` | `DECIDE(OVERRIDE)` | `DECIDE(OVERRIDE)` | — |
| `SUSPENDED_BY_*` | `SUSPENDED_BY_INTEGRITY` | integrity violation detected while already suspended | failing verification record | `suspension.set` | `AUTO` | `AUTO` | — |
| `SUSPENDED_BY_*` | `SUSPENDED_BY_HUMAN` | human suspends over an existing automatic suspension | `DEC(SUSPEND)` | `suspension.set` | `DECIDE(SUSPEND)` | `DECIDE(SUSPEND)` | — |

**Precedence when several causes hold:** `SUSPENDED_BY_INTEGRITY` >
`SUSPENDED_BY_HUMAN` > `SUSPENDED_BY_DRIFT` > `SUSPENDED_BY_BUDGET` >
`SUSPENDED_BY_ESCALATION` > `SUSPENDED_BY_POLICY`. Clearing the highest cause
re-evaluates the remainder; the holder returns to `NONE` only when none hold.

---

## 5. `StageRun.lifecycle`

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `∅` | `ALLOCATED` | `project.lifecycle = ACTIVE` and `project.suspension = NONE`; `run.stage_id` names an existing `Stage` with `project_id = run.project_id` and `roadmap_id = project.roadmap_id`, whose `lifecycle ∈ {READY, CONTRACTED}` and `suspension = NONE`; `run.stage_id` equals the `stage_id` of the `StageContract` the `ACT` activates; `ACT` valid and un-expired and minted for this same run (`run_id` of the `ACT` = `run.run_id`); `input_snapshot_id` names a `SNAP`; `run.suspension = NONE`; for the first activation/run pair this row and §6 `DRAFT → ACTIVE` co-commit in one store transaction (§11.1) | `ACT`, `SNAP` as `input_snapshot_id` | `run.start` | `CONFIRM` | `AUTO` | — |
| `ALLOCATED` | `DISPATCHED` | a `WorkerInvocation` accepted by a provider; `granted_capabilities ⊆ effective_capabilities` | — | `worker.invoke` | `AUTO` | `AUTO` | — |
| `ALLOCATED` | `CLOSED_ABORTED` | activation revoked before dispatch | revocation record | `run.abort` | `AUTO` | `AUTO` | — |
| `DISPATCHED` | `WORKING` | provider reported execution started | — | `worker.invoke` | `AUTO` | `AUTO` | — |
| `DISPATCHED` | `CLOSED_ABORTED` | provider rejected or failed to start | `WR` with `termination_reason ∈ {PROVIDER_ERROR, REFUSAL}` | `run.abort` | `AUTO` | `AUTO` | — |
| `WORKING` | `VALIDATING` | ≥1 `WR` present and ≥1 `ValidationOperation` authorized | `WR` | `validation.request` | `AUTO` | `AUTO` | — |
| `WORKING` | `AWAITING_DECISION` | `ESC(OPEN)` non-auto-resolvable bound to run | `ESC(OPEN)` | `escalation.raise` | `AUTO` | `AUTO` | — |
| `WORKING` | `CLOSED_EXPIRED` | `now > deadline_at` | `WR` with `termination_reason = DEADLINE` | `run.abort` | `AUTO` | `AUTO` | — |
| `WORKING` | `CLOSED_ABORTED` | budget exhausted, human stop, or scope breach attempted | `WR` with matching `termination_reason` | `run.abort` | `AUTO` | `AUTO` | — |
| `VALIDATING` | `REVIEWING` | all mandatory mechanical criteria `MET`; mandatory review specs exist | `VR(pass)` set complete over one `SNAP` | `review.submit` | `AUTO` | `AUTO` | — |
| `VALIDATING` | `WORKING` | a mandatory validation returned `FAIL` and retries remain | `VR(any)` | `worker.invoke` | `AUTO` | `AUTO` | — |
| `VALIDATING` | `AWAITING_DECISION` | retries exhausted, validator unavailable, or nondeterminism detected | `ESC(OPEN)` | `escalation.raise` | `AUTO` | `AUTO` | — |
| `VALIDATING` | `CLOSED_EXPIRED` | `now > deadline_at` | — | `run.abort` | `AUTO` | `AUTO` | — |
| `REVIEWING` | `CLOSED_SATISFIED` | stage transitioned to `SATISFIED`; all `CommitIntent` in `{APPLIED}` or none proposed | `RVW` set, `CR` set, `SNAP` as `output_snapshot_id` | `stage.satisfy` | `CONFIRM` | `NOTIFY` | — |
| `REVIEWING` | `WORKING` | blocking finding raised and retries remain | `RVW` carrying a blocking finding | `worker.invoke` | `AUTO` | `AUTO` | — |
| `REVIEWING` | `AWAITING_DECISION` | blocking finding with retries exhausted, or `INCONCLUSIVE` mandatory review | `ESC(OPEN)` | `escalation.raise` | `AUTO` | `AUTO` | — |
| `REVIEWING` | `CLOSED_EXPIRED` | `now > deadline_at` | — | `run.abort` | `AUTO` | `AUTO` | — |
| `AWAITING_DECISION` | `WORKING` | `DEC(OVERRIDE)` directing rework, budget and deadline extended if needed | `DEC(OVERRIDE)` | `worker.invoke` | `DECIDE(OVERRIDE)` | `DECIDE(OVERRIDE)` | — |
| `AWAITING_DECISION` | `CLOSED_SATISFIED` | every shortfall waived and stage reached `SATISFIED` | `DEC(WAIVE)` per shortfall plus remaining `VR(pass)`/`RVW` set | `stage.satisfy` | `DECIDE(APPROVE)` | `DECIDE(APPROVE)` | — |
| `AWAITING_DECISION` | `CLOSED_REJECTED` | `DEC(REJECT)` recorded | `DEC(REJECT)` | `stage.reject` | `DECIDE(REJECT)` | `DECIDE(REJECT)` | — |
| `AWAITING_DECISION` | `CLOSED_ABORTED` | `DEC(ABANDON)` recorded, or escalation withdrawn with no path forward | `DEC(ABANDON)` | `run.abort` | `DECIDE(ABANDON)` | `DECIDE(ABANDON)` | — |
| `DISPATCHED`, `WORKING`, `VALIDATING`, `REVIEWING` | `AWAITING_DECISION` | an operation of this run is `reconciliation_state = UNRESOLVABLE` after a controller restart: the provider cannot say whether an invocation ran, or a repository scan cannot decide whether the intent landed | `ESC(OPEN)` with trigger `RECOVERY_AMBIGUITY` | `escalation.raise` | `AUTO` | `AUTO` | — |

`CLOSED_*` are terminal. A new attempt is a new `StageRun`.

**RUN-INV-3 gate.** A run whose `controller_epoch` precedes
`project.controller_epoch` **initiates no new external effect** — no provider
`invoke`, no repository mutation, and therefore no `WorkerInvocation` dispatch and
no `CommitIntent` transition past `AUTHORIZED` under `commit.apply` — until every
one of its `WorkerInvocation` and `CommitIntent` records has
`reconciliation_state ∈ {NOT_REQUIRED, ADOPTED, ORPHANED}`. This is what makes a
restart unable to produce a duplicate worker or a duplicate commit.

The gate forbids *initiating* effects. It does not forbid the reconciliation
transition itself, which initiates nothing and exists precisely to clear the gate:

| scope | status under the gate |
|---|---|
| dispatching a `WorkerInvocation`, calling `invoke`, mutating the repository, or advancing a `CommitIntent` past `AUTHORIZED` under `commit.apply` | **forbidden** while any record of the run is `PENDING` or `UNRESOLVABLE` |
| **exemption** — any transition whose `required_capability` is `recovery.reconcile`: `lookup` on a persisted `idempotency_key`, a repository scan for an `operation_token`, and the state change that records the result (including `APPLYING → APPLIED` and `APPLYING → FAILED` in §7.4) | **permitted**, and permitted *only* to the operation being reconciled. `recovery.reconcile` cannot call `invoke`, cannot mutate the repository, and cannot create an operation; it can only write down what already happened |

Without this exemption the gate is unsatisfiable: the only transitions that move a
record out of `PENDING` are the ones the gate would otherwise block, so a run
could never leave the barrier it entered at restart.

### 5.1 Reconciliation-state derivation

`WorkerInvocation.reconciliation_state` and `CommitIntent.reconciliation_state`
are derived, never asserted. This is the **single** derivation for both; §7.2,
§7.4, `worker_provider.md` §6.1 and `authority-matrix.md` §6 refer here rather
than restating it.

| condition on the record | `reconciliation_state` |
|---|---|
| `controller_epoch = project.controller_epoch` | `NOT_REQUIRED` |
| `controller_epoch < project.controller_epoch` **and** `status` is non-terminal | `PENDING` — for **every** non-terminal status of either entity, with no exception: `WorkerInvocation` in `PENDING`, `DISPATCHED`, `RUNNING`; `CommitIntent` in `PROPOSED`, `BLOCKED`, `AUTHORIZED`, `APPLYING` |
| `controller_epoch < project.controller_epoch` **and** `status` is terminal | `NOT_REQUIRED` |
| recovery executed under `recovery.reconcile` | `ADOPTED`, `ORPHANED`, or `UNRESOLVABLE` per the outcome it observed — **terminal**, and takes precedence over `NOT_REQUIRED`; a record that was reconciled never reverts to `NOT_REQUIRED`, whatever its epoch or status becomes afterwards |

Two consequences the two sites share:

| case | result |
|---|---|
| an old-epoch record that never initiated its effect — a `WorkerInvocation` still `PENDING` (no provider call made), a `CommitIntent` in `PROPOSED`, `BLOCKED` or `AUTHORIZED` (no repository mutation made, so no revision carries its `operation_token`) | reconciles to `ORPHANED` once recovery confirms no effect token exists outside the kernel. `ORPHANED` here is the positive finding that nothing landed, not an error |
| an old-epoch record whose effect is still running — `lookup` answered `LIVE` | stays `PENDING` until the outcome arrives, then `ADOPTED`. `PENDING` is a state of this table like any other; it is not the absence of one |

`ADOPTED` means the outcome was **established**, not that it succeeded. Both sites
adopt failure as failure: a reconciled `FAILED`/`TIMED_OUT`/`CANCELLED`/`REFUSED`
invocation and a reconciled `DIVERGED` commit receipt are `ADOPTED`.

---

## 6. `StageContract.status`

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `∅` | `DRAFT` | schema-valid; `contract_hash` recomputes; `C-INV-1` holds | — | `contract.author` | `AUTO` | `AUTO` | — |
| `DRAFT` | `ACTIVE` | no other `ACTIVE` contract for the stage; `capability_request ⊆ project.capability_ceiling`; budget ceiling ≤ project remaining | `ContractActivationRecord` minted with non-empty `authority_chain` and a `capability_grant_basis` entry per granted capability (`A-INV-3`) | `contract.activate` | `CONFIRM` | `AUTO` | — |
| `DRAFT` | `REVOKED` | author withdrew before activation | — | `contract.revoke` | `AUTO` | `AUTO` | — |
| `ACTIVE` | `FULFILLED` | bound stage reached `SATISFIED` | `CR`/`VR(pass)`/`RVW` set cited by the satisfying transition | `stage.satisfy` | `AUTO` | `AUTO` | — |
| `ACTIVE` | `SUPERSEDED` | a successor contract with `supersedes = this` reached `ACTIVE`; no non-terminal run under this contract | successor `ContractActivationRecord` | `contract.supersede` | `CONFIRM` | `CONFIRM` | — |
| `ACTIVE` | `REVOKED` | human revocation, policy change, scope breach, or integrity violation | `DEC(REVOKE_CAPABILITY)` or the triggering record | `contract.revoke` | `DECIDE(REVOKE_CAPABILITY)` | `AUTO` when triggered by breach or integrity, else `CONFIRM` | — |
| `ACTIVE` | `EXPIRED` | `now > activation.expires_at` | — | `contract.revoke` | `AUTO` | `AUTO` | — |

`FULFILLED`, `SUPERSEDED`, `REVOKED`, `EXPIRED` are terminal. Reuse requires a new
contract with a new `contract_hash`.

**Status is outside the hash preimage.** `contract_hash` is computed over the
document minus `contract_hash` **and** minus `status` (schema HASHING comment,
`XC-12`, `C-INV-2`). Every row above therefore preserves the hash pinned into
`StageRun.contract_hash` at activation, while `XC-13` still holds because status
remains the only member that may differ between persisted documents sharing a
`contract_id`. Any change to a member inside the preimage after `ACTIVE` remains
an integrity violation (§9.3).

---

## 7. Subordinate state machines

### 7.1 `ValidationOperation.status`

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `∅` | `REQUESTED` | `validation_spec_id` exists in the pinned contract | — | `validation.request` | `AUTO` | `AUTO` | — |
| `REQUESTED` | `AUTHORIZED` | `command` matches the spec byte-for-byte; `cwd` in scope; `network` permitted by grants | — | `proc.exec.validation` | `AUTO` | `AUTO` | — |
| `REQUESTED` | `DENIED` | command altered, out of scope, or capability absent | — | `proc.exec.validation` | `AUTO` | `AUTO` | — |
| `AUTHORIZED` | `EXECUTING` | sandbox allocated | `SNAP` as `input_snapshot_id` | `validation.execute` | `AUTO` | `AUTO` | — |
| `EXECUTING` | `COMPLETED` | process exited within `timeout_ms` | `ValidationReceipt` minted by runtime | `validation.attest` | `AUTO` | `AUTO` | — |
| `EXECUTING` | `TIMED_OUT` | `timeout_ms` elapsed | `ValidationReceipt` with `outcome = TIMEOUT` | `validation.attest` | `AUTO` | `AUTO` | — |
| `EXECUTING` | `EXEC_FAILED` | sandbox or toolchain error | `ValidationReceipt` with `outcome = ERROR` | `validation.attest` | `AUTO` | `AUTO` | — |
| `REQUESTED`, `AUTHORIZED`, `EXECUTING` | `CANCELLED` | holder entered `QUIESCING` or run closed | — | `run.abort` | `AUTO` | `AUTO` | — |

### 7.2 `WorkerInvocation.status`

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `∅` | `PENDING` | run `lifecycle = ALLOCATED` or `WORKING`; budget headroom; every earlier invocation and commit intent of the run has `reconciliation_state ∈ {NOT_REQUIRED, ADOPTED, ORPHANED}` (`RUN-INV-3`) | `ACT`, and the `InvocationRequest` persisted as `request_ref` with its `idempotency_key` and `controller_epoch` **before** any provider call | `worker.invoke` | `CONFIRM` first invocation of a run, else `AUTO` | `AUTO` | — |
| `PENDING` | `REJECTED_BY_POLICY` | requested capabilities exceed run's effective set, or provider not in registry (the invocation's pinned `provider_id` and `provider_version`), or `preflight` returned `UNSUPPORTED_ROLE` or `UNKNOWN_BINDING` (worker_provider §2.1, §13 `WD-3`) | — | `worker.invoke` | `AUTO` | `AUTO` | — |
| `PENDING` | `DISPATCHED` | provider accepted; prompt bundle stored content-addressed | `prompt_bundle_ref` persisted | `worker.invoke` | `AUTO` | `AUTO` | — |
| `DISPATCHED` | `RUNNING` | provider reported start | — | `worker.invoke` | `AUTO` | `AUTO` | — |
| `RUNNING` | `COMPLETED` | provider returned output within deadline | `WR` attested by runtime | `worker.invoke` | `AUTO` | `AUTO` | — |
| `RUNNING` | `TIMED_OUT` | `deadline_at` passed | `WR` with `termination_reason = DEADLINE` | `worker.invoke` | `AUTO` | `AUTO` | — |
| `RUNNING` | `FAILED` | provider error | `WR` with `termination_reason = PROVIDER_ERROR` | `worker.invoke` | `AUTO` | `AUTO` | — |
| `PENDING`, `DISPATCHED`, `RUNNING` | `CANCELLED` | suspension, budget exhaustion, or human stop | `WR` with matching `termination_reason` | `run.abort` | `AUTO` | `AUTO` | — |
| `PENDING`, `DISPATCHED`, `RUNNING` | `COMPLETED`, `FAILED`, `TIMED_OUT`, `CANCELLED` | reconciliation: `controller_epoch < project.controller_epoch`; `lookup(idempotency_key)` returned `FINISHED(outcome)` (`WP-16`). The invocation takes the status `outcome.status` maps to — `COMPLETED → COMPLETED`, `FAILED → FAILED`, `TIMED_OUT → TIMED_OUT`, `CANCELLED → CANCELLED`, `REFUSED → FAILED` — and never `COMPLETED` for a non-`COMPLETED` outcome | `WR` attested by the runtime carrying `outcome.termination_reason`, with `attribution = RECONCILED` | `recovery.reconcile` | `AUTO` | `AUTO` | — |
| `PENDING`, `DISPATCHED`, `RUNNING` | `FAILED` | reconciliation: `lookup(idempotency_key)` returned `ABSENT` — the provider holds no outcome and no live invocation under that key, so the invocation never took effect | `WR` with `termination_reason = PROVIDER_ERROR` and `attribution = RECONCILED` | `recovery.reconcile` | `AUTO` | `AUTO` | — |
| `DISPATCHED` | `FAILED` | `invoke` returned an `InvocationOutcome` with exactly `status = REFUSED` and `termination_reason = REFUSAL`: the provider declined the task and execution did not start (worker_provider `WP-18`, §13 `WD-6` row R); never taken through `RUNNING`, never on a `ProviderError`, and never on a `REFUSED` outcome with any other reason | `WR` with `termination_reason = REFUSAL`, `attribution = DIRECT` | `worker.invoke` | `AUTO` | `AUTO` | — |

Reconciliation sets `reconciliation_state` per §5.1: `ADOPTED` on the
`FINISHED(outcome)` row — **for every outcome status, not only `COMPLETED`** —
and `ORPHANED` on the `ABSENT` row. `ADOPTED` states that the outcome was
established, not that it succeeded; a reconciled `FAILED`, `TIMED_OUT`,
`CANCELLED` or `REFUSED` outcome is preserved as that outcome with
`attribution = RECONCILED`, exactly as the commit side preserves a `DIVERGED`
receipt (§7.4). A `LIVE` answer keeps the invocation `PENDING` and tracked under
the same key (§5.1). A `lookup` the provider cannot answer leaves `UNRESOLVABLE`;
the run then takes the §5 reconciliation row to `AWAITING_DECISION` and no
further invocation may be created for it (`RUN-INV-3`). Resubmitting `request_ref`
bytes, rebuilding context, minting a new `idempotency_key`, or starting a new
attempt in place of an unreconciled one is illegal (§9.3).

### 7.3 `Finding.status`

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `∅` | `OPEN` | raised within a `Review` that a `ReviewAttestation` counts in its `review_ids` | `RVW(v)` — the attestation covering that `Review`; the `Review` itself is never cited (`G-1`, §9.3) | `finding.raise` | `AUTO` | `AUTO` | — |
| `OPEN` | `ACKNOWLEDGED` | an actor accepted it for remediation | — | `finding.resolve` | `AUTO` | `AUTO` | — |
| `OPEN`, `ACKNOWLEDGED` | `FIXED` | a later run produced evidence the defect is gone | `VR(pass)` or `RVW(PASS)` over a `SNAP` newer than the finding | `finding.resolve` | `AUTO` | `AUTO` | — |
| `OPEN`, `ACKNOWLEDGED`, `DISPUTED` | `WAIVED` | bound criterion has `waivable = true` | `DEC(WAIVE)` with non-empty `justification` and `evidence_shown` | `finding.waive` | `DECIDE(WAIVE)` | `DECIDE(WAIVE)` | — |
| `OPEN` | `DISPUTED` | an actor contests the finding with counter-evidence | counter `ArtifactRef` set | `finding.resolve` | `AUTO` | `AUTO` | — |
| `DISPUTED` | `INVALID` | counter-evidence accepted by an independent reviewer or a human | `RVW(PASS)` by an `INDEPENDENT` reviewer, or `DEC(OVERRIDE)` | `finding.resolve` | `DECIDE(OVERRIDE)` | `AUTO` when an independent review cleared it, else `DECIDE(OVERRIDE)` | — |
| `DISPUTED` | `OPEN` | counter-evidence rejected | `RVW(FAIL)` | `finding.resolve` | `AUTO` | `AUTO` | — |
| `WAIVED` | `OPEN` | `waiver.expires_at` passed, or waiver revoked | `DEC(REVOKE_CAPABILITY)` or clock | `finding.resolve` | `AUTO` | `AUTO` | — |

### 7.4 `CommitIntent.status`

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `∅` | `PROPOSED` | all `mutations[*].in_scope = true`; `base_revision_id` matches current `SNAP.vcs_state`; `operation_token` minted, unique, and carried in `trailers` | `WR` carrying the proposals, `SNAP` | `commit.propose` | `AUTO` | `AUTO` | — |
| `PROPOSED` | `BLOCKED` | any precondition in `preconditions` unmet | — | `commit.propose` | `AUTO` | `AUTO` | — |
| `BLOCKED` | `PROPOSED` | previously missing preconditions now met | the newly satisfied `VR(pass)`/`RVW`/`DEC` | `commit.propose` | `AUTO` | `AUTO` | — |
| `PROPOSED` | `AUTHORIZED` | `preconditions_met = true`; workspace unchanged since `base_revision_id` | `SNAP` matching `base_revision_id`, cited `VR(pass)` and `RVW` sets | `commit.authorize` | `CONFIRM` | `AUTO` | — |
| `PROPOSED` | `DENIED` | scope breach, capability absent, or policy prohibition | — | `commit.authorize` | `AUTO` | `AUTO` | — |
| `AUTHORIZED` | `APPLYING` | write lock on the workspace acquired; the intent's `operation_token` and `controller_epoch` are durable **before** the first repository mutation, so a landed revision can always be matched back to this intent (evidence-model §3.2.1) | — | `commit.apply` | `AUTO` | `AUTO` | — |
| `APPLYING` | `APPLIED` | application succeeded and `actual_tree_digest = expected_tree_digest` | `CR` with `verification = MATCHED`, `post_snapshot_id` | `commit.apply` | `AUTO` | `AUTO` | — |
| `APPLYING` | `FAILED` | application error, or `verification = DIVERGED` | `CommitReceipt` with `verification = DIVERGED` plus `ESC(OPEN)` | `commit.apply` | `AUTO` | `AUTO` | — |
| `APPLIED` | `ROLLED_BACK` | rollback policy invoked after a later failure | `CR` for the reverting change, `SNAP` after | `commit.apply` | `CONFIRM` | `AUTO` | — |
| `FAILED` | `ROLLED_BACK` | partial application detected and reverted | `SNAP` matching `base_revision_id` | `commit.apply` | `AUTO` | `AUTO` | — |
| `APPLYING` | `APPLIED` | reconciliation: `controller_epoch < project.controller_epoch`; a repository scan finds exactly one revision carrying this `operation_token`, and its tree digest equals `expected_tree_digest` | `CR` with `verification = MATCHED`, `attribution = RECONCILED`, `post_snapshot_id` | `recovery.reconcile` | `AUTO` | `AUTO` | — |
| `APPLYING` | `FAILED` | reconciliation: no revision carries this `operation_token` and a fresh `SNAP` still matches `base_revision_id`, so nothing landed | `SNAP` matching `base_revision_id` | `recovery.reconcile` | `AUTO` | `AUTO` | — |
| `APPLYING` | `FAILED` | reconciliation: exactly one revision carries this `operation_token` but its tree digest differs from `expected_tree_digest` | `CR` with `verification = DIVERGED`, `attribution = RECONCILED`, plus `ESC(OPEN)` | `recovery.reconcile` | `AUTO` | `AUTO` | — |
| `PROPOSED`, `BLOCKED`, `AUTHORIZED` | *status unchanged* | reconciliation: `controller_epoch < project.controller_epoch` and the intent never reached `APPLYING`, so no repository mutation was ever initiated under its `operation_token`; a scan finds no revision carrying the token and a fresh `SNAP` still matches `base_revision_id` | `SNAP` matching `base_revision_id` | `recovery.reconcile` | `AUTO` | `AUTO` | — |

These four rows are the only transitions permitted to a run under the
`RUN-INV-3` barrier, by the §5 exemption; each initiates nothing and only records
what the scan observed.

Reconciliation sets `reconciliation_state` per §5.1: `ADOPTED` on the first row
above and `ORPHANED` on the second. The third row leaves it `ADOPTED` with a
divergent receipt — the outcome was established, and it was a failure — which
`CM-INV-1` turns into `SUSPENDED_BY_INTEGRITY`. The fourth row covers the
old-epoch intents that had not yet reached `APPLYING`: they are `PENDING` like
every other non-terminal old-epoch record (§5.1), they carry no effect token in
the repository, and the scan resolves them `ORPHANED` without touching `status` —
the positive finding that nothing landed, which is what clears the barrier. Any
other scan
result — more than one revision carrying the token, or no such revision while the
workspace no longer matches `base_revision_id` — is `UNRESOLVABLE`: the intent
stays `APPLYING`, `Escalation(RECOVERY_AMBIGUITY)` is raised, and the holder
takes `NONE → SUSPENDED_BY_INTEGRITY` (§4). Re-applying an intent that is not
first reconciled is illegal (§9.3); this is what stops a blind retry from landing
the same change twice.

Publication beyond the local workspace is a distinct capability
(`commit.publish`) and is `DECIDE(APPROVE)` in `SUPERVISED` and `CONFIRM` in
`AUTONOMOUS`; it is never implied by `APPLIED`.

### 7.5 `HumanDecision.decision_state`

Derived, runtime-only. A decision is authority only while `VALID`. A
snapshot-bound decision (`snapshot_bound = true`, domain-model §9.A) is bound to
the `RealitySnapshot` whose evidence the human was shown.

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `∅` | `VALID` | recorded per `HD-INV-1`/`HD-INV-2`; `snapshot_bound = true` ⇒ `subject_snapshot_id` is the newest `COMPLETE` snapshot covering the subject's scope and every `evidence_shown` artifact is current against it | `SNAP` as `subject_snapshot_id` where `snapshot_bound = true`; `—` otherwise | `decision.record` | `AUTO` | `AUTO` | — |
| `VALID` | `CONSUMED` | the decision discharged the transition it was recorded for; `nonce` spent | the transition's own `AuditEvent` | `audit.append` | `AUTO` | `AUTO` | — |
| `VALID` | `STALE` | `snapshot_bound = true` and a newer `COMPLETE` snapshot whose `drift_summary` touches the subject's scope superseded `subject_snapshot_id` | the newer `SNAP` | `audit.append` | `AUTO` | `AUTO` | — |
| `VALID` | `EXPIRED` | `now > expires_at`, or the `scope` boundary was left | — | `audit.append` | `AUTO` | `AUTO` | — |
| `VALID`, `STALE` | `VOID` | `HD-INV-1` violated, or the decision's own record fails verification | failing verification record | `suspension.set` | `AUTO` | `AUTO` | — |

Recording is `AUTO` in both modes because the human act *is* the decision; the
policy verdicts that require one live on the transition being decided, not here.
`CONSUMED`, `EXPIRED` and `VOID` are terminal. `STALE` is terminal too: a stale
decision is never revalidated by a later snapshot, because the human approved
what they were shown and that is gone. The subject must be re-decided, which
produces a new `HumanDecision` with a new nonce. Only `VALID` satisfies `DEC(K)`
or `CONFIRM`; `STALE` and `EXPIRED` are retained as true records of an earlier
choice, exactly as stale evidence is (evidence-model §5).

### 7.6 `Escalation.status`

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `∅` | `OPEN` | a trigger in domain-model §9.B.1 fired | the triggering record | `escalation.raise` | `AUTO` | `AUTO` | — |
| `OPEN` | `ACKNOWLEDGED` | assignee accepted it | — | `escalation.resolve` | `AUTO` | `AUTO` | — |
| `OPEN`, `ACKNOWLEDGED` | `RESOLVED` | a `HumanDecision` of one of `required_decision_kinds` recorded, or `auto_resolvable = true` and the triggering condition no longer holds | `DEC(K)` for `K ∈ required_decision_kinds`, or a `SNAP`/`VR(pass)` showing the condition cleared | `escalation.resolve` | `DECIDE(K)` | `AUTO` when `auto_resolvable`, else `DECIDE(K)` | — |
| `OPEN`, `ACKNOWLEDGED` | `EXPIRED` | no resolution within the configured window | — | `escalation.resolve` | `AUTO` | `AUTO` | — |
| `OPEN` | `WITHDRAWN` | raiser retracted before any action, and the trigger no longer holds | `SNAP` or `VR(pass)` showing the condition cleared | `escalation.resolve` | `AUTO` | `AUTO` | — |

`EXPIRED` does not clear suspension. It escalates severity by one level and
re-opens as a new `Escalation` with the same trigger.

---

## 8. Composition table (axis interaction on the hot path)

| project.lifecycle | stage.lifecycle | any suspension ≠ NONE | may dispatch worker | may execute validation | may apply commit | may satisfy stage |
|---|---|---|---|---|---|---|
| `ACTIVE` | `RUNNING` | no | yes | yes | yes | no |
| `ACTIVE` | `RUNNING` | yes | no | no | no | no |
| `ACTIVE` | `AWAITING_VALIDATION` | no | no | yes | no | no |
| `ACTIVE` | `AWAITING_REVIEW` | no | no | no | yes | yes |
| `ACTIVE` | `AWAITING_DECISION` | no | no | no | no | only with `DEC` |
| `ACTIVE` | `CONTRACTED` | no | yes, the first invocation of the run allocated under the active contract, and only that one | no | no | no |
| `ACTIVE` | `PENDING`, `READY` | no | no | no | no | no |
| `SETTLING` | any | no | no | yes (re-verification only) | no | no |
| `PLANNING`, `DRAFT` | any | any | no | no | no | no |
| `COMPLETED`, `ARCHIVED`, `ABANDONED` | any | any | no | no | no | no |

The `CONTRACTED` row is what breaks the dispatch cycle: `CONTRACTED → RUNNING`
(§3) requires a `DISPATCHED` run, `∅ → ALLOCATED` and `ALLOCATED → DISPATCHED`
(§5) require a `WorkerInvocation` the provider accepted, and that first
invocation is therefore dispatched while the stage is still `CONTRACTED`. Every
later invocation of the run requires `RUNNING`. `READY → RUNNING` remains illegal
(§9.1): the run is allocated against the `ACTIVE` contract, so the activation
record and `effective_capabilities` exist before anything is dispatched.

This table governs the hot-path operations only. Axis-2 lifecycle advancement
during `PLANNING` is governed by the startup exception in §3 and is limited to
`∅ → PENDING` and `PENDING → READY`.

---

## 9. ILLEGAL SECTION

Transitions and operations that are permanently forbidden. Attempting any of
them is an `INTEGRITY_VIOLATION` or `POLICY_CONFLICT` escalation, never a retry.
`required_capability` is shown as `NONE_GRANTABLE` where no capability, decision,
or mode can authorize the action.

### 9.1 Illegal stage transitions

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `PENDING` | `SATISFIED` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | no contract, no run, no receipt can exist; satisfaction without evidence is unverifiable by construction |
| `PENDING` | `RUNNING` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | skips `READY` dependency check and `CONTRACTED` authority grant; work would run with no activation record |
| `READY` | `RUNNING` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | a run without an `ACTIVE` contract has no `effective_capabilities`; default DENY would make every action illegal |
| `READY` | `SATISFIED` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | no `StageRun`, therefore no receipts bound to this stage |
| `CONTRACTED` | `SATISFIED` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | activation grants authority but produces no evidence |
| `RUNNING` | `SATISFIED` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | bypasses validation and review; only `AWAITING_REVIEW` and `AWAITING_DECISION` may satisfy |
| `AWAITING_VALIDATION` | `SATISFIED` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | mandatory judgmental criteria have no `Review` yet |
| any | `SATISFIED` | `declared_status = CLAIMED_COMPLETE` used as the basis | worker `Claim` only | `NONE_GRANTABLE` | `DENY` | `DENY` | a CLAIM is not EVIDENCE; `G-6` forbids `declared_status` in any precondition |
| any | `SATISFIED` | `observed_satisfaction ∈ {UNKNOWN, UNSATISFIED, CONTRADICTED, STALE, INDETERMINATE}` | — | `NONE_GRANTABLE` | `DENY` | `DENY` | satisfaction must be measured against the current snapshot, not asserted |
| `SATISFIED` | `RUNNING` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | re-entry must pass through `READY` so dependencies and a fresh contract are re-checked |
| `ABANDONED` | any | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | terminal by `G-7`; resumption requires a new stage revision from the roadmap |
| `REJECTED` | `SATISFIED` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | reverses a recorded human rejection without a new run or new evidence |
| any | any | performed while `suspension ≠ NONE` other than the rows permitted in §0.1 | — | `NONE_GRANTABLE` | `DENY` | `DENY` | suspension is a hard gate; allowing progress would make it advisory |

### 9.2 Illegal project transitions

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `DRAFT` | `ACTIVE` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | no roadmap imported, so no stage exists to act on |
| `DRAFT`, `PLANNING` | `COMPLETED` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | completion asserts every stage satisfied; with no runs there is nothing to assert over |
| `ACTIVE` | `COMPLETED` | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | must pass through `SETTLING`, where the all-stages-terminal predicate is evaluated once against a stable snapshot |
| `ARCHIVED` | any | — | — | `NONE_GRANTABLE` | `DENY` | `DENY` | terminal; the evidence set is sealed and artifacts may have been collected |
| `∅` | `DRAFT` | `created_by.actor_kind ≠ HUMAN` | — | `NONE_GRANTABLE` | `DENY` | `DENY` | a runtime or worker cannot originate a project and thereby its own capability ceiling |
| any | any | while `suspension = SUSPENDED_BY_INTEGRITY` | — | `NONE_GRANTABLE` | `DENY` | `DENY` | the audit chain is untrusted; no state written under it is meaningful |

### 9.3 Illegal authority and evidence operations

| operation | actor | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|
| mint `ValidationReceipt` | `WORKER` | `NONE_GRANTABLE` | `DENY` | `DENY` | collapses CLAIM into EVIDENCE; the measured party would author the measurement |
| mint `CommitReceipt` | `WORKER` | `NONE_GRANTABLE` | `DENY` | `DENY` | only the applier can attest what was applied |
| create `RealitySnapshot` | `WORKER`, `ADAPTER` | `NONE_GRANTABLE` | `DENY` | `DENY` | ground truth must come from the runtime's own observation, not a reported view |
| create `HumanDecision` | `RUNTIME`, `WORKER`, `ADAPTER` | `NONE_GRANTABLE` | `DENY` | `DENY` | authority cannot be self-issued; violates `HD-INV-1` |
| create `HumanDecision` with `auth_method ∈ {NONE, DELEGATED}` | `HUMAN` | `NONE_GRANTABLE` | `DENY` | `DENY` | unauthenticated authority is indistinguishable from forged authority |
| create `HumanDecision` with empty `evidence_shown` | `HUMAN` | `NONE_GRANTABLE` | `DENY` | `DENY` | an uninformed approval cannot discharge `required_evidence` |
| replay a consumed `HumanDecision` nonce | any | `NONE_GRANTABLE` | `DENY` | `DENY` | one decision would authorize unbounded future actions |
| mutate a field of an `ACTIVE` `StageContract` | any | `NONE_GRANTABLE` | `DENY` | `DENY` | `contract_hash` is pinned into the run; mutation silently changes what was authorized |
| widen `StageRun.effective_capabilities` in place | any | `NONE_GRANTABLE` | `DENY` | `DENY` | authority is frozen at activation; widening must produce a new activation record |
| grant a capability outside `project.capability_ceiling` | `HUMAN`, `RUNTIME` | `NONE_GRANTABLE` | `DENY` | `DENY` | the ceiling is the project-level bound; per-grant escape makes it unenforceable |
| delegate a capability a worker does not hold | `WORKER` | `NONE_GRANTABLE` | `DENY` | `DENY` | privilege escalation by construction |
| rewrite or delete an `AuditEvent` | any | `NONE_GRANTABLE` | `DENY` | `DENY` | breaks the hash chain, destroying verifiability of every later event |
| write `observed_satisfaction` directly | `WORKER`, `ADAPTER`, `HUMAN` | `NONE_GRANTABLE` | `DENY` | `DENY` | it is a derived field; a writable one would be a CLAIM wearing an EVIDENCE label |
| write `declared_status` and have it gate a transition | any | `NONE_GRANTABLE` | `DENY` | `DENY` | `G-6`; the field exists precisely so claims are recorded without being trusted |
| execute a `CommandSpec` whose `argv` differs from the contract's `ValidationSpec` | any | `NONE_GRANTABLE` | `DENY` | `DENY` | the validator would no longer be the one the contract was approved against |
| write outside `scope_include` minus `scope_exclude` | `WORKER` | `NONE_GRANTABLE` | `DENY` | `DENY` | scope is the blast radius the activation was granted against |
| satisfy an `INDEPENDENT` `ReviewSpec` with `independence = SELF_REVIEW` | any | `NONE_GRANTABLE` | `DENY` | `DENY` | `RV-INV-1`; self-review provides no independent signal |
| waive a criterion with `waivable = false` | `HUMAN` | `NONE_GRANTABLE` | `DENY` | `DENY` | the contract declared it non-negotiable at authoring time, before the outcome was known |
| resolve an `Escalation` with `auto_resolvable = false` without a `HumanDecision` | `RUNTIME` | `NONE_GRANTABLE` | `DENY` | `DENY` | the escalation exists because the runtime declared itself unable to decide |
| set `governance_mode = AUTONOMOUS` without a `HumanDecision` | any | `NONE_GRANTABLE` | `DENY` | `DENY` | mode selection is the root of every policy relaxation in this document |
| apply a `CommitIntent` whose `base_revision_id` no longer matches reality | any | `NONE_GRANTABLE` | `DENY` | `DENY` | the reviewed diff is not the diff that would land |
| mark a stage `SATISFIED` from a snapshot with `completeness ≠ COMPLETE` | any | `NONE_GRANTABLE` | `DENY` | `DENY` | `RS-INV-1`; absence of observation is not observation of absence of defects |
| grant a capability whose §2 `grantable by` column names no principal that produced an admissible grant record | `RUNTIME` | `NONE_GRANTABLE` | `DENY` | `DENY` | `AX-11`; ceiling membership, a role-table cell, and `capability_request` bound a grant, they never create one |
| write a `ContractActivationRecord` whose `capability_grant_basis` does not cover every granted capability | `RUNTIME` | `NONE_GRANTABLE` | `DENY` | `DENY` | `A-INV-3`; an unattributed grant cannot be replayed, so the authority trace would not answer "what allowed this?" |
| dispatch a `WorkerInvocation`, or advance a `CommitIntent` past `AUTHORIZED` **under `commit.apply`**, for a run holding an unreconciled operation | `RUNTIME` | `NONE_GRANTABLE` | `DENY` | `DENY` | `RUN-INV-3`; this is precisely how a restart produces a duplicate worker or a duplicate commit. The bar is on *initiating* an effect: transitions taken under `recovery.reconcile`, including the §7.4 reconciliation rows out of `APPLYING`, are exempt by the §5 gate and are the only way the barrier is ever cleared |
| replace an unreconciled `WorkerInvocation` with a new `idempotency_key`, rebuilt context, or a new attempt | `RUNTIME` | `NONE_GRANTABLE` | `DENY` | `DENY` | a new key defeats `WP-6`, so the provider would execute the work a second time and bill it a second time |
| resubmit a persisted `request_ref` to `invoke` as a means of reconciling an invocation | `RUNTIME` | `NONE_GRANTABLE` | `DENY` | `DENY` | `WP-16`; against an `ABSENT` key a resubmission *performs* the work instead of reporting that nothing happened, so the one branch recovery exists to detect is the branch it would destroy. Reconciliation reads by `lookup` only |
| dispatch a governed mutation to a provider that does not implement `lookup` | `RUNTIME` | `NONE_GRANTABLE` | `DENY` | `DENY` | `WP-17`; an effect whose outcome the kernel can never learn is unreconcilable by construction, so `G-9` would be satisfied in form and empty in fact |
| mutate the repository before the intent's `operation_token` is durable | `RUNTIME` | `NONE_GRANTABLE` | `DENY` | `DENY` | a landed revision with no recorded identity can never be matched to the intent that produced it; the commit becomes permanently unreceipted |
| re-apply a `CommitIntent` in `APPLYING` without reconciling it first | `RUNTIME` | `NONE_GRANTABLE` | `DENY` | `DENY` | the first application may have landed; blind retry is not idempotent and would duplicate the change |
| cite a `HumanDecision` with `decision_state ≠ VALID` as `DEC(K)` or `CONFIRM` | any | `NONE_GRANTABLE` | `DENY` | `DENY` | `HD-INV-4`; a consumed, expired, void, or stale approval no longer describes the reality it was granted against |
| mint a `ReviewAttestation` | `WORKER`, `ADAPTER`, `HUMAN` | `NONE_GRANTABLE` | `DENY` | `DENY` | `review.attest` is `KERNEL`; a self-attested review would promote a CLAIM to EVIDENCE by assertion |
| cite a `Review` directly as `required_evidence` | any | `NONE_GRANTABLE` | `DENY` | `DENY` | `G-1`; the `Review` is the judgement, the `ReviewAttestation` is the kernel's measurement of it |
| call `WorkerProvider.invoke` for a `WorkerInvocation` whose `request_ref`, `idempotency_key` and `controller_epoch` are not yet durable, or that is not in `DISPATCHED` committed under the current `project.controller_epoch` | `RUNTIME` | `NONE_GRANTABLE` | `DENY` | `DENY` | `G-9`, evidence-model §3.2.1: an effect with no durable identity is unreconcilable; outside current-epoch `DISPATCHED` the call is either a second execution after an outcome was recorded or a post-restart re-execution `WP-16` forbids. A same-key re-send while still `DISPATCHED` in the current epoch and before `deadline_at` is the `WP-6`/`CF-11` retry and is not this row |
| write `project.controller_epoch` other than by §14 `T_start`, or to any value other than current + 1 | any | `NONE_GRANTABLE` | `DENY` | `DENY` | `P-INV-4`, §14 `CS-5`; the epoch is the fence every epoch-bound boundary re-reads and the source of every `reconciliation_state` derivation (§5.1), so a decrement, skip, reset or unrecorded write would either re-admit an outlived controller or hide an operation from recovery |

---

## 10. Project governance field writes

Two legal rows that write a `Project` governance field. They are **not** an axis:
neither reads or writes `lifecycle` or `suspension` (`O-3`); each is gated by
axis 1 and axis 3 (`O-4`) and leaves both unchanged. `from_state` and `to_state`
name the field's value before and after. Each is a `HUMAN`-class per-act exercise
(authority-matrix §5.2) and is legal while the project is `DRAFT`: neither depends
on a roadmap, `Stage`, `StageContract`, activation or `StageRun`.

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `capability_ceiling = ∅` | `capability_ceiling = C`, `C ≠ ∅` | `project.lifecycle = DRAFT`; `project.suspension = NONE`; the current ceiling is empty — this is the first assignment only; `C` is non-empty; every member of `C` is a `CapabilityId` registered in authority-matrix §2 and none has class `KERNEL` or `NEVER`; the decision's `evidence_shown` holds exactly one `ArtifactRef`, the provisioning-value artifact, and the decision binds `C` to it per `PG-8`..`PG-10`; the decision has `subject = {kind: PROJECT, id: project_id}`, `scope = PROJECT`, `grants = ∅`, `revokes = ∅` | `DEC(SET_CEILING)` | `project.ceiling.set` | `DECIDE(SET_CEILING)` | `DENY` | — |
| `budget = 0` | `budget = B`, every field of `B` > 0 | `project.lifecycle = DRAFT`; `project.suspension = NONE`; every field of the current `budget` is zero — the initial value — and every field of `budget_used` is zero; every field of `B` is positive, so every `Budget` dimension (domain-model §1.3) has positive headroom; the decision's `evidence_shown` holds exactly one `ArtifactRef`, the provisioning-value artifact, and the decision binds `B` to it per `PG-8`..`PG-10`; the decision has `subject = {kind: PROJECT, id: project_id}`, `scope = PROJECT`, `grants = ∅`, `revokes = ∅` | `DEC(GRANT_BUDGET)` | `budget.grant` | `DECIDE(GRANT_BUDGET)` | `DENY` | — |

Both rows share these semantics:

| id | rule |
|---|---|
| `PG-1` | **One decision, one act, consumed.** Exactly one `HumanDecision` authorizes each act, of the kind its verdict names — `SET_CEILING` for the ceiling, `GRANT_BUDGET` for the budget. The act consumes it: the decision takes `VALID → CONSUMED` (§7.5) in the same store transaction as the field write and the act's event, so decision consumption, field write and event commit together or not at all. A consumed decision authorizes nothing further (§9.3, replayed nonce). |
| `PG-2` | **Events.** The act emits one state-changing `AuditEvent` with `capability_used` = the row's `required_capability`, `authority_ref` = the authorizing `decision_id`, `subject = {kind: PROJECT, id: project_id}`, and `actor` / `on_behalf_of` per authority-matrix `AX-16`. Its payload names the field, its previous value (`∅`, or the zero `Budget`) and its new value (`C` or `B`). The decision's `VALID → CONSUMED` is recorded by its own event under `audit.append` citing the act's event, as in `AX-17`. |
| `PG-3` | **No grant.** Neither decision is `GRANT_CAPABILITY`, so neither is admitted by authority-matrix §5.1 or §5.3 step 1, and each is consumed by its act, so neither stands as a project grant. Membership in `capability_ceiling` bounds grants and confers none (`AX-11`, `P-INV-2`). Neither act writes `HumanDecision.grants`, `ContractActivationRecord.granted_capabilities`, `WorkerInvocation.granted_capabilities` or `StageRun.effective_capabilities` (`AX-12`), and neither confers authority on a worker or run. |
| `PG-4` | **Not bounded by the ceiling.** Each act is a per-act exercise, bounded by its register row, the §3 mode gate, its row and one live decision, and not by `project.capability_ceiling` (`AX-13`); the empty initial ceiling therefore does not block setting it. |
| `PG-5` | **Distinct budget kinds.** `GRANT_BUDGET` authorizes only the initial assignment on this row. `EXTEND_BUDGET` is unchanged: it discharges the §3 `AWAITING_DECISION → RUNNING` and §4 `SUSPENDED_BY_BUDGET → NONE` rows, and neither kind discharges the other's rows. |
| `PG-6` | **Mode.** Both acts are legal under `SUPERVISED` only. Under `AUTONOMOUS` both are `DENY` (authority-matrix §3), and no policy evaluation, `CONFIRM` or `AUTO` verdict admits them. |
| `PG-7` | **Outside these rows.** Any write to a non-empty `capability_ceiling` — replacement, widening, narrowing or a mixed change — and any write to a non-zero `budget` are not authorized by these rows or their decisions and remain undefined here; budget extension is `budget.extend` and is not defined by this section. |
| `PG-8` | **Value carrier (D-N2-06).** The exact proposed value is carried by one immutable, content-addressed artifact (evidence-model §1): the one `ArtifactRef` in the decision's `evidence_shown`. That artifact is at once the exact value presented to the human and the only carrier of the value the act may write. Its octets are `JCS(payload)` per RFC 8785, as in evidence-model §3.1 step 2, with `media_type = application/json`, and `ArtifactRef.digest` is their key per evidence-model §1.1. For `SET_CEILING` the payload is `{"kind": "SET_CEILING", "project_id": <project id>, "capability_ceiling": [<CapabilityId>, …]}`, with the list in canonical order: strictly ascending by UTF-16 code units, the order RFC 8785 applies to member names, so no member repeats. For `GRANT_BUDGET` the payload is `{"kind": "GRANT_BUDGET", "project_id": <project id>, "budget": <Budget>}`, where `<Budget>` is the existing `Budget` of domain-model §1.3 as a JSON object with exactly its six field names, each holding that field's value in the encoding below; no second `Budget` type is defined. Neither payload has any other member. **`GRANT_BUDGET` field encoding (D-N2-07).** This is an encoding of the existing `Budget` in this artifact only; it changes no `Budget` field type and narrows no range. Each field whose domain-model §1.3 type is `uint64` — `wall_clock_ms` (`Ms`) and `cost_units` (`Unit`), domain-model §0.1 — is a JSON string, never a JSON number, holding the field's value in canonical unsigned decimal: ASCII digits `0`–`9` only; zero is exactly `"0"`; a non-zero value has no leading zero; and its value `v` satisfies `0 ≤ v ≤ 18446744073709551615`. Each `uint32` field — `worker_invocations`, `validation_executions`, `commits` and `escalations` — is a JSON number that is an integer `v` with `0 ≤ v ≤ 4294967295`; every such integer is exact in the RFC 8785 number model, which serializes it as its plain decimal. Every value of every `Budget` field therefore has exactly one representation in the artifact, and that representation is lossless. |
| `PG-9` | **Choice vocabulary (D-N2-06).** For `SET_CEILING` and `GRANT_BUDGET`, `options_offered = ["ACCEPT_PROPOSED_VALUE", "REJECT_PROPOSED_VALUE"]` and `chosen` is exactly one of them. `chosen` expresses acceptance or rejection of the artifact and encodes no value: no ceiling or `Budget` is ever inferred from `chosen`. Only `chosen = ACCEPT_PROPOSED_VALUE` can authorize either act; a decision with `REJECT_PROPOSED_VALUE` authorizes neither. |
| `PG-10` | **Binding checks (D-N2-06).** The act is legal only when `chosen = ACCEPT_PROPOSED_VALUE` and all of these hold: the one `ArtifactRef` resolves to a stored, unredacted and untruncated artifact; the digest of its decoded octets verifies against `ArtifactRef.digest`, and those octets are exactly `JCS` of the payload they parse to, in the `PG-8` shape; the payload's `kind` equals the decision's `decision_kind`; the payload's `project_id` equals the decision's `project_id`, its `subject.id` and the project the act writes; and the value the act writes equals the payload's value. For `SET_CEILING`, `JCS` of `C` in `PG-8` canonical order equals `JCS` of `capability_ceiling`. For `GRANT_BUDGET`, equality is typed `Budget` equality (D-N2-07): the payload's `budget` is validated in its `PG-8` encoding; each `uint64` decimal string is parsed exactly into its `uint64`, and each `uint32` field is read as the exact integer its canonical decimal denotes; the existing `Budget` is reconstructed from those values; and that `Budget` equals `B` field by field. No `Budget` value is compared through, or converted by way of, an IEEE-754 number. For `GRANT_BUDGET` each of these refuses the act before anything is written — no `budget` write, no `AuditEvent`, no decision consumption: a JSON number where the `uint64` decimal string is required; an invalid character, a sign or whitespace in that string; a leading zero other than `"0"`; an empty string; a value above `18446744073709551615`; a `uint32` field that is not an integer JSON number within its range; a missing or extra `Budget` field; failed `JCS` validation; a failed digest; and a typed `Budget` mismatch. Every check is evaluated before anything is written. Any failure refuses the act: no field write, no act event, and the decision is not consumed by these rows. Only after every check succeeds do the decision consumption, field write and `AuditEvent` commit together per `PG-1` and `PG-2`. |
| `PG-11` | **Bounded (D-N2-06).** `PG-8`..`PG-10` apply only to `SET_CEILING` and `GRANT_BUDGET` on these two rows. No `HumanDecision` field is added, no schema is added, and `HumanDecision`, `evidence_shown` (domain-model §9.A, `HD-INV-2`), every other `DecisionKind`, every other transition row and artifact semantics elsewhere are unchanged. |

---

## 11. First roadmap import, stage materialization and composition gates

These rules bind the first roadmap import to the rows it takes — §2 `DRAFT → PLANNING`
and §3 `∅ → PENDING` — and bind §8 to the rows that admit, dispatch and apply. They add
no row, change no verdict and name no capability beyond those the cited rows already
declare. `roadmap.import` is held for the import as those rows already require, by one
of `AX-1`'s forms (authority-matrix §5.3).

| id | rule |
|---|---|
| `RI-1` | **Atomic import.** The first import is one store transaction. Persisting the `Roadmap` (domain-model §3), binding `Project.roadmap_id` to it, the project's `DRAFT → PLANNING` (§2) and `∅ → PENDING` (§3) for every stage the roadmap names commit together or not at all. `fetch` and `normalize` (roadmap_adapter §3) precede the transaction; nothing they produce is authoritative until an event of this transaction cites it. |
| `RI-2` | **Deterministic event order.** The transaction emits the project's `DRAFT → PLANNING` event first, then one `∅ → PENDING` event per stage in `roadmap.stage_order` order. Each event carries `capability_used = roadmap.import`. |
| `RI-3` | **Referential integrity.** Every `Project`, `Roadmap` and `Stage` reference the transaction writes — `Project.roadmap_id`, `Roadmap.stage_order`, `Roadmap.dependency_edges`, `Stage.roadmap_id`, `Stage.project_id`, `Stage.depends_on` — is valid at commit. `DRAFT → PLANNING`'s preconditions are evaluated over the `Roadmap` this transaction binds. No committed `DRAFT` project exposes a partial authoritative roadmap or stage set. |
| `RI-4` | **Descriptor correspondence.** Exactly one `Stage` is materialized per `StageDescriptor` of the `NormalizedRoadmap` whose digest is `roadmap.normalized_digest`. Each stage's `key` equals its descriptor's `key`; its `project_id` is the project's and its `roadmap_id` the bound roadmap's; `roadmap.stage_order` lists exactly the materialized stages; and each stage's `depends_on`, and `roadmap.dependency_edges`, are exactly its descriptor's `depends_on_keys` resolved within that set. |
| `RI-5` | **Refusal.** Any import failure refuses and rolls back the whole import transaction: an adapter error (roadmap_adapter §2.1), an `ERROR` diagnostic, a duplicate key, an unresolved dependency, a dependency cycle, a digest mismatch, any other failure of the import that is not an authority denial, and an authority or capability denial. The project remains `DRAFT` with no `roadmap_id`, and no `Roadmap` or `Stage` is authoritative. Only an authority or capability denial is governed by authority-matrix `AX-8`: its denial `AuditEvent` is durably recorded in a separate legal audit transaction, which is not part of the rolled-back import transaction and survives its rollback. A non-authority import failure is not an `AX-8` denial and this rule requires no denial event for it. |
| `RI-6` | **Human import values.** `Stage.max_attempts` and `Roadmap.writeback_mode` (`src = H`, domain-model §3, §4) are supplied by the human as import inputs and are recorded in the payload of the import's `DRAFT → PLANNING` event. No adapter supplies them (roadmap_adapter `RA-6`), and this section defines no default for either. |
| `RI-7` | **Readiness separate.** `PENDING → READY` (§3) is not part of the import transaction. It remains its own transition under its own row, taken after the import commits. |
| `RI-8` | **Mandatory §8 gate.** §8 is an admission gate, checked against `project.lifecycle` of `run.project_id`, `stage.lifecycle` of the `Stage` named by `run.stage_id`, `run.lifecycle`, and the `suspension` of project, stage and run, at exactly three rows: (a) §7.2 `∅ → PENDING`, worker admission; (b) again at §7.2 `PENDING → DISPATCHED`, the provider-dispatch boundary, before the provider is called; (c) §7.4 `AUTHORIZED → APPLYING`, before any repository mutation. For (a) and (b) the first invocation of a run requires project `ACTIVE`, stage `CONTRACTED`, run `ALLOCATED`; every later invocation requires project `ACTIVE`, stage `RUNNING`, run `WORKING`. For (c) apply requires project `ACTIVE` and stage `RUNNING` or `AWAITING_REVIEW`. In every case project, stage and run suspension are `NONE`. The gate is conjoined with each row's own preconditions and evidence and replaces none of them. A run whose `stage_id` names no `Stage` of its project has no §8 row and is admitted at none of the three. This rule does not bind validation execution. |
| `RI-9` | **Bounded scope.** This section adds no entity, field, enum, `DecisionKind`, `CapabilityId` or lifecycle value, and it does not restrict a roadmap to one stage. authority-matrix §5.2 and §5.3 and §10 of this document are unchanged. |

### 11.1 Activation and allocation composition

For the first activation/run pair, §6 `DRAFT → ACTIVE` (row 6-2) and §5 `∅ → ALLOCATED`
(row 5-1) form one atomic composition, because `ContractActivationRecord.run_id` and
`StageRun.activation_id` reference each other (domain-model §5, §6.2) and row 5-1 cites the
`ACT` row 6-2 mints.

| id | rule |
|---|---|
| `AC-1` | **One transaction.** A conforming composition is one store transaction that: (1) begins with a `DRAFT` `StageContract`, a current `SNAP`, and — only where the governing policy column requires a decision, i.e. under `SUPERVISED`, where both rows are `CONFIRM` — two distinct live `HumanDecision{kind: APPROVE}` records; (2) reserves `activation_id` and `run_id`; (3) constructs the `ContractActivationRecord` and the `StageRun`, each referencing the other; (4) persists the activation's `AUTHORITY` record and event first; (5) emits row 6-2 `DRAFT → ACTIVE`; (6) under `SUPERVISED`, consumes row 6-2's approval; (7) emits row 5-1 `∅ → ALLOCATED`, citing the `ACT` and the `SNAP`; (8) under `SUPERVISED`, consumes row 5-1's separate confirmation; (9) commits every entity, transition, event and consumption together. Any failure rolls back the whole transaction. Under `AUTONOMOUS`, where both rows are `AUTO`, steps (1)–(9) apply without the two decisions and steps (6) and (8) do not occur; the composition remains one atomic transaction in both modes. |
| `AC-2` | **Two decisions under `SUPERVISED`.** Under `SUPERVISED`, rows 6-2 and 5-1 keep their own `CONFIRM`, each discharged by its own `APPROVE`, and neither decision discharges the other transition (§7.5, `HD-INV-3`). Under `AUTONOMOUS` both rows remain `AUTO` and require no decision; this section changes neither row's policy columns. |
| `AC-3` | **Distinct confirmations.** The `CONFIRM`s of §2 `PLANNING → ACTIVE`, §6 `DRAFT → ACTIVE`, §5 `∅ → ALLOCATED`, §3 `READY → CONTRACTED` and every later §3 row are each a distinct human act. None is merged with another, and no one decision discharges two of them. |

---

## 12. Kernel secret resolution

One legal row for the `secret.read` act. It is **not** an axis, following the precedent of
§10: it reads axis 1, axis 2 and axis 3 and writes no lifecycle, suspension or entity
field (`O-3`, `O-4`). It is not part of the `StageRun` or `WorkerInvocation` machinery and
adds no `DISPATCHING` or other lifecycle value. `from_state` `∅` means no act; `to_state`
is the `secret.read` act recorded, event e1 of §12.1. The act is a `HUMAN`-class per-act
exercise (authority-matrix §5.2). The row is checked at the kernel secret-resolution
boundary, before the resolver runs: worker admission is not that boundary, provider
dispatch is not that boundary, and `RI-8` is not extended.

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `∅` | `secret.read` act recorded (e1, §12.1) | `project.governance_mode = SUPERVISED`; `project.lifecycle = ACTIVE`; `stage.lifecycle ∈ {CONTRACTED, RUNNING}` for `run.stage_id`; `run.lifecycle ∈ {ALLOCATED, WORKING}`; project, stage and run `suspension = NONE`; the run's activation is un-revoked and un-expired, and `activation_id = run.activation_id`; the value binding of §12.3 holds | `ACT`, the run's activation; `SNAP` as the decision's `subject_snapshot_id`; `DEC(APPROVE)`, the one decision §12.3 binds | `secret.read` | `CONFIRM` | `DENY` | — |

| id | rule |
|---|---|
| `SR-1` | **One decision, one act.** Exactly one `HumanDecision{kind: APPROVE}` authorizes each act. Every authority-matrix §5.2 step applies unchanged: step 2 is satisfied by this row, and step 5 is satisfied because `CONFIRM`→`APPROVE`. The decision has `grants = revokes = ∅` (`AX-12`, authority-matrix §5.2 step 6). Nothing else is authority for the act. A PROJECT-scope `GRANT_CAPABILITY` that names `secret.read` confers nothing (authority-matrix §5.3 step 4). It is neither cited nor required, and the act never consumes it (`AX-19`(a)). |
| `SR-2` | **Not bounded by the ceiling.** Following `AX-13`, the act is bounded only by four things: the authority-matrix §2 register row, the authority-matrix §3 mode gate, this row, and the one live decision. `secret.read ∈ capability_ceiling` is **not** a precondition, and ceiling membership is not exercise authority (`AX-11`). |
| `SR-3` | **Kernel-performed.** The act resolves one named secret into an execution environment that the kernel holds. The event actor is `RUNTIME`, with `on_behalf_of` set to the deciding principal (`AX-16`). (a) No `WORKER`, adapter or provider performs the act. (b) None of them holds `secret.read` (`AX-12`, authority-matrix §4.1 :224, worker_provider `WP-7`). This row defines exactly one target kind: `INFERENCE_RELAY`, identified by its HTTPS origin. The row does not cover any other target kind. |
| `SR-4` | **No grant.** `secret.read` is never written into `HumanDecision.grants`, `ContractActivationRecord.granted_capabilities`, `WorkerInvocation.granted_capabilities` or `StageRun.effective_capabilities` (`AX-12`, `AX-18`). |
| `SR-5` | **Checks before writes.** Every check in §12.2 is evaluated before anything is written. A refusal writes no act event and consumes no decision. |
| `SR-6` | **Durable before effect.** The act event e1 and the decision's `VALID → CONSUMED` (e2) commit in one store transaction *before* the resolver is called. The outcome is recorded afterwards, in its own event (§12.1). |
| `SR-7` | **Consumption is final.** The decision is consumed when e1 commits and is never restored. If the resolver fails, or the process is lost after that commit, the decision stays `CONSUMED`. Any further exercise needs a new decision, recorded and bound anew. After a restart there is a new `controller_epoch`, so a new act and a new decision are needed. |
| `SR-8` | **Use is not re-exercise.** Once resolved, the kernel may use the value inside the target execution environment for the run and `controller_epoch` the act bound, and each such use is not a new exercise. Using it for any other run, epoch or target is not authorized. |
| `SR-9` | **Secrecy by provenance.** The rule works from where data comes from; it never compares secret bytes against anything. **(a) Before resolution.** Every persistent field written before the resolver is called is built only from already-authorized, non-secret metadata: the decision, the §12.3 artifact, the `AX-8` denial events, e1 and e2. The metadata is the §12.3 tuple, identifiers, the artifact digest, `decision_id` and fixed-text reasons. None of these fields can be derived from secret bytes, because the secret has not been resolved yet. **(b) After resolution.** Raw secret bytes stay in kernel memory only. They are handed to the bound target environment and nowhere else. **(c) Forbidden sinks.** No serialization, logging, exception text, event payload, report, journal, artifact or decision may receive any of the following: a raw secret byte; the secret's length; any substring, prefix, suffix or fragment; any encoding; or any other reversible representation. **(d) The one permitted persistent form.** Besides the secret name, the only secret-derived value that may persist is the salted digest evidence-model `AS-4` already allows. It is computed in memory with a salt that does not depend on the secret. Only `{name, salt, digest}` may reach e3. **(e) Failures.** Failures are recorded only with fixed classifications: `RESOLUTION_FAILED` when the resolver fails, and `TARGET_CONFIGURATION_FAILED` when the bound target refuses or fails to be configured (§12.1). No exception text, cause or value-dependent detail is persisted or propagated. Secret bytes are never compared against `project_id`, `run_id`, `activation_id`, `controller_epoch`, `secret_name`, `origin`, artifact text or earlier event fields. |
| `SR-10` | **Bounded.** This section adds no entity, field, enum, `DecisionKind`, `CapabilityId` or lifecycle value. The following stay unchanged: authority-matrix §3, §4.1, §5, §5.1, the §5.2 steps, §5.3 and `AX-1`..`AX-20`, and §7.5, §8, §10 and §11 of this document (including `RI-8` and `AC-*`). The authority-matrix §3 `secret.read` `AUTONOMOUS` cell ("grantable, allowlist-pinned") is not edited, and this section defines no allowlist. The row's `DENY` is the narrower of the two bounds, and authority-matrix §5.2 applies both. |

### 12.1 Act ordering and events

| step | operation |
|---|---|
| 1 | **Evaluate, with no writes.** Every §12.2 check is run against the current state: the register and the row; the mode and the verdict; the axis preconditions; the activation; the decision predicates; the §12.3 value binding; `HD-INV-4` currency. |
| 2 | **Transaction T1, one `BEGIN IMMEDIATE`.** (1) Re-check that the decision is `VALID`, its nonce is unspent, and its `subject_snapshot_id` is still the newest `COMPLETE` snapshot. (2) Append **e1**, the act event: `epistemic_class = AUTHORITY`; `capability_used = secret.read`; `authority_ref = decision_id`; actor `RUNTIME` with `on_behalf_of` = the decider; `subject = {run_id}`; payload the §12.3 tuple, the artifact digest and `decision_id`. (3) Set the decision to `CONSUMED` and append **e2**: `VALID → CONSUMED` under `audit.append`, citing e1 (§7.5 :394, the `AX-17`/`PG-2` pattern). (4) `COMMIT`. Any failure rolls back all of T1. e1 precedes e2 in chain order and both are durable together, so T1 emits the authority-use record and then consumes the decision; committing them separately would leave a window, after a crash, in which the authority-use record is durable while its decision is still `VALID` and reusable. |
| 3 | **Call the resolver**, only after T1 has committed. |
| 4 | **Resolver failure.** The environment is not configured. T2 records e3 with `outcome = FAILED` and `reason = "RESOLUTION_FAILED"`. The decision stays `CONSUMED`. |
| 5 | **Resolver success.** The raw secret stays in kernel memory only. The kernel then tries to configure exactly the bound target environment: the `INFERENCE_RELAY` at the approved canonical origin, for the bound run and epoch. That configuration is the only place the raw value is transferred (`SR-9`(b)). |
| 6 | **Target configuration refused or failed.** The kernel discards the raw value. T2 records e3 with `outcome = FAILED` and `reason = "TARGET_CONFIGURATION_FAILED"`. No exception text, secret-derived detail, value, length, fragment or reversible representation is persisted. The decision stays `CONSUMED`. |
| 7 | **Target accepted.** Only when the target environment has accepted and been configured with the value does T2 record e3 with `outcome = RESOLVED`. |
| 8 | **e3**, written in T2: `epistemic_class = AUTHORITY`; `capability_used = audit.append`, citing e1; no `authority_ref`, because a consumed decision is not re-cited as authority (DESIGN-04 Revision 05 §6.4 case A is avoided); payload either `{outcome: RESOLVED, secret_name, salted_digest: {salt, digest}}` or `{outcome: FAILED, secret_name, reason: <"RESOLUTION_FAILED" \| "TARGET_CONFIGURATION_FAILED">}`. The salted digest is computed in memory, over the raw secret octets, with a freshly generated salt. Apart from `secret_name`, the payload contains no other secret-derived member (`SR-9`(d)). e3 records the completed outcome of the `secret.read` act into its bound target, not merely a successful resolver lookup. |
| 9 | **Crash after T1.** If the process is lost after T1 and before T2, the decision stays `CONSUMED`. The value is gone with the process. The next epoch requires a new act and a new decision. No reconciliation row is added. |

### 12.2 Denials and refusals

An **authority denial** writes exactly one `AX-8` event in its own transaction, following
the `RI-5` precedent: `epistemic_class = AUTHORITY`; `capability = secret.read`; the
reason; a fine-grained cause in the payload; the presented `decision_id`, if there is one;
`subject = {run_id}`. It writes no e1 and consumes nothing. A **precondition refusal** is
not a capability denial under `RI-5`, so this section requires no `AX-8` event for it; it
also writes no e1 and consumes nothing.

| case | class | `AX-8` reason |
|---|---|---|
| `governance_mode = AUTONOMOUS` (row `DENY`) | authority denial; `ESC(POLICY_CONFLICT)` is raised per §1.1 `DENY` | `MODE_FORBIDDEN` |
| No decision presented; or the decision is not `APPROVE`; or its `grants`/`revokes` are non-empty | authority denial | `NO_GRANTOR` |
| A PROJECT `GRANT_CAPABILITY` is presented instead of an `APPROVE` | authority denial; the grant is left untouched | `NO_GRANTOR` |
| The decision's `subject` is not `{RUN, run_id}`, or its `scope ≠ SINGLE_ACTION`, or its `project_id` is not the run's project | authority denial | `NO_GRANTOR` |
| `chosen = REJECT_PROPOSED_VALUE`, or `options_offered` is not exactly the two values | authority denial; the decision is not consumed | `NO_GRANTOR` |
| An artifact check fails: the artifact is missing or redacted, the digest fails, it is not exact `JCS`, it has an extra or missing member, or any tuple field mismatches (project, run, activation, `controller_epoch`, secret name, target); or `target.origin` is non-canonical; or the configured origin fails the canonical origin rule or is not byte-identical once canonicalized (§12.3) | authority denial | `NO_GRANTOR` |
| The target kind is not `INFERENCE_RELAY` (no row covers it) | authority denial | `NO_GRANTOR` |
| The decision is `STALE`, `EXPIRED`, `VOID` or `CONSUMED`; or its nonce is spent; or `subject_snapshot_id` is not the newest `COMPLETE` snapshot | authority denial | `NO_GRANTOR` |
| The decider is not an authenticated `HUMAN` with a `principal_key_id`, or `auth_method ∉ {SESSION, SIGNATURE, MTLS}` | authority denial; the existing `HD-INV-1` and GR-29 integrity handling is unchanged | `NO_GRANTOR` |
| Project, stage or run lifecycle is not as the row requires; any suspension is not `NONE`; or the activation is revoked, expired or mismatched | precondition refusal | — |
| The resolver fails | not a denial, because it happens after T1. The environment is not configured, e3 is `FAILED` with reason `RESOLUTION_FAILED`, and the decision stays `CONSUMED` | — |
| The target environment refuses, or fails to be configured with, the resolved value | not a denial, because it happens after T1. The raw value is discarded, e3 is `FAILED` with reason `TARGET_CONFIGURATION_FAILED`, and the decision stays `CONSUMED` | — |

`NO_GRANTOR` is used wherever no admissible authorization exists for *this* act, because
none of the other seven `AX-8` values names that cause. `REVOKED` never arises in this
procedure (`AX-8`).

### 12.3 Evidence and value binding

| id | rule |
|---|---|
| `SB-1` | **The decision.** Every one of these is required: `decision_kind = APPROVE`; `subject = {kind: RUN, id: run_id}`; `scope = SINGLE_ACTION`; `grants = revokes = ∅`; `options_offered = ["ACCEPT_PROPOSED_VALUE", "REJECT_PROPOSED_VALUE"]`; `chosen = ACCEPT_PROPOSED_VALUE`; `snapshot_bound = true`, with `subject_snapshot_id` = the newest `COMPLETE` snapshot (`HD-INV-4`); `evidence_shown` = exactly one `ArtifactRef`; `project_id` = the run's project; decided by an authenticated `HUMAN` with a `principal_key_id`. The human approves the whole tuple, never the value. |
| `SB-2` | **The artifact** is immutable and content-addressed, and it is the sole carrier of the approved value. Its octets are `JCS(payload)` (RFC 8785), with `media_type = application/json`, and `ArtifactRef.digest` is their key (evidence-model §1.1). The payload has exactly these members: `{"act": "secret.read", "project_id": <project id>, "run_id": <run id>, "activation_id": <run.activation_id>, "controller_epoch": <uint64 as canonical unsigned decimal string>, "secret_name": <Str(1..128), a name>, "target": {"kind": "INFERENCE_RELAY", "origin": <canonical HTTPS origin, per SB-4>}}`. The artifact never contains the secret value, its length, a prefix, or a fragment. |
| `SB-3` | **Encoding of `controller_epoch`.** ASCII digits, with no sign, no whitespace, and no leading zero other than `"0"`; its value must be ≤ 18446744073709551615. This rule is stated for §12 because `PG-11` confines `PG-8`..`PG-10` to §10. |
| `SB-4` | **Canonical origin.** `target.kind` is exactly `"INFERENCE_RELAY"`. `target.origin` is an HTTPS origin, not a URL, written as `"https://" host [":" port]`. **Scheme:** exactly `https`, in lowercase; no other scheme. **Host:** exactly one of two disjoint forms. **(A) Canonical DNS hostname:** lowercase ASCII only; one or more labels joined by `.`; each label 1–63 characters drawn only from `a`–`z`, `0`–`9` and `-`; no label begins or ends with `-`; the whole hostname at most 253 characters; an internationalized name must already appear in lowercase A-label form; `%`-encoding is forbidden; and the final label must not be a numeric form — it must not consist entirely of decimal digits `0`–`9`, and it must not be a legacy hexadecimal numeric spelling, `0x` followed by zero or more characters from `0`–`9` and `a`–`f`. The final label **may begin with a digit**, so `relay.3m` is admitted when every other rule holds. The hexadecimal clause is kept because the network stack would otherwise read such a host as an IP address through non-canonical numeric syntax (glibc `inet_aton`, which `getaddrinfo` uses for numeric hosts, accepts `0x7f`, `0x7f.0.0.1` and `127.1` as IPv4). These two clauses are the WHATWG URL Standard's "ends in a number" test, not a requirement that the label begin with a letter. **(B) Canonical IPv4 literal:** exactly four decimal octets joined by `.`; each octet ASCII digits only with a value of 0–255; no octet has a leading zero, except an octet that is exactly `0`. Valid: `127.0.0.1`, `10.0.0.1`, `255.255.255.255`. Invalid: `127.000.0.1`, `256.0.0.1`, `01.2.3.4`, `127.0.0`, `127.0.0.1.5`. **Classification**, deterministic and in this order: (1) a canonical IPv4 literal is form B; (2) otherwise the host is form A only if it satisfies every DNS rule above, including the final-label rule; (3) otherwise it is refused. A string that fails strict IPv4 never falls through to DNS by default, because its final label is numeric: `127.000.0.1`, `256.0.0.1`, `01.2.3.4`, `127.0.0`, `127.0.0.1.5`, `127.1`, `0x7f` and `0x7f.0.0.1` are all refused, and by the same rules `relay.3m` is form A. **Excluded:** IPv6 literals, bracketed or not, are refused because no §12 target representation covers them; so is any host matching neither A nor B. **Port:** in the range 1–65535, ASCII decimal with no leading zero; port 443 must be omitted, so `":443"` is not canonical; any other port appears explicitly as `":"` followed by the port. **Nothing else:** no userinfo and no `@`; no path, not even `/`; no `?` or query; no `#` or fragment; no whitespace, control character, backslash or `%`. |
| `SB-5` | **Equality.** An approved `target.origin` must already be canonical; a non-canonical value is a binding failure. The environment the act configures is taken from the relay configuration's origin input. Only that input may have a path, and the path may only be empty or exactly `/`. It is compared with the approved origin in five steps: (1) parse and validate it — the scheme must be `https`; there must be no userinfo, query or fragment; the path must be empty or exactly `/`; no `%`, whitespace, control character or backslash may appear; (2) require its host to be in the admitted set, form A or form B, refusing anything else, including an IPv6 literal; (3) canonicalize the host and port under `SB-4` — lowercase the host, drop the port if it is 443, and otherwise write the port explicitly; (4) remove the trailing `/`; (5) compare the resulting canonical origin **byte for byte** with the approved artifact's `target.origin`. The act is legal only if they are identical. |
| `SB-6` | **Runtime-key correspondence, qualified.** The runtime compares relay destinations by one key, the pair `(hostname.lower(), port)` with the port defaulting to 443; `SB-4` gives that key exactly one string form and adds no entity, field, enum or `CapabilityId`. The correspondence holds **only for the admitted host set**: canonical DNS hostnames and canonical IPv4 literals. Over that set the canonical origin corresponds one-to-one with the runtime's `(host, port)` destination key, so the relay's request-time destination check compares the same origin the human approved. No equivalence is claimed for IPv6 or for any other excluded host representation. |
| `SB-7` | **Binding checks.** The act is legal only if every one of these holds: (1) the artifact resolves to a stored, unredacted, untruncated artifact; (2) its digest verifies; (3) its octets are exactly the `JCS` of the payload they parse to, with no member missing or extra; (4) `act = "secret.read"`; (5) `project_id` equals the decision's `project_id` and the run's project; (6) `run_id` equals the decision's `subject.id` and the acted run; (7) `activation_id` equals `run.activation_id`, and that activation is live; (8) `controller_epoch` equals `project.controller_epoch` at the act; (9) `secret_name` is exactly the name the resolver is called with; (10) `target.kind = "INFERENCE_RELAY"`, `target.origin` is canonical, and it is byte-identical to the canonical form of the configured relay origin (`SB-5`). |

---

## 13. Worker dispatch lifecycle

One ordered, crash-safe procedure that ties together the `RI-8` gates (a) and (b), the
§7.2 `WorkerInvocation`, §5 `StageRun` and §3 `Stage` rows, and the provider `invoke`
call. It is **not** an axis, following the precedent of §10 and §12, and it uses the
existing lifecycle vocabulary only. The durable pre-provider record is the
`WorkerInvocation` in `DISPATCHED`, committed in T2 (§13.1) of the current
`controller_epoch`; `PENDING` (T1) carries the durable identity. The dispatch record is
owned by the `WorkerInvocation` (`status`, `request_ref`, `idempotency_key`,
`controller_epoch`); the `StageRun` and `Stage` carry only the first-invocation lifecycle
consequence. `DISPATCHED` is a subordinate lifecycle state (domain-model §10.4), not a
grant. Transition events are `AUTHORITY`-class envelopes: kernel capability, actor
`RUNTIME`, no `authority_ref` (`AX-7`, evidence-model §3.3 authority binding). The receipt is `EVIDENCE`.
Provider reports are `CLAIM` (worker_provider `WP-1`); "provider reported start" reads the
`WP-18` report.

Four facts are kept apart:

| fact | recorded by |
|---|---|
| A0: durable identity | T1 `∅ → PENDING` event |
| A: durable intent to dispatch | T2 `PENDING → DISPATCHED` event |
| B: the provider side effect | the `invoke` call carrying the key. Never recorded directly |
| C: execution established | T3 `DISPATCHED → RUNNING`, only on a non-`REFUSED` outcome (`WP-18`) |
| D: the result | T3 receipt plus a terminal row, where a legal row exists (`WD-6`) |

Execution-truth categories:

| category | source | consequence |
|---|---|---|
| established | `InvocationOutcome` with `status ≠ REFUSED`, returned by `invoke` or by `lookup` `FINISHED` | may support `RUNNING` / `WORKING` |
| not started | `InvocationOutcome` with the exact pair `status = REFUSED`, `termination_reason = REFUSAL`; recovery-only `lookup` `ABSENT` | `DISPATCHED → FAILED` (direct) or the §7.2 `ABSENT` reconciliation row (recovery); never `RUNNING` |
| ambiguous | any `ProviderError` (every code, including `REFUSED` raised as an error); an `InvocationOutcome` with `status = REFUSED` and `termination_reason ≠ REFUSAL` (a malformed report, `WP-18`); transport loss; no answer; kernel-forced termination | stays `DISPATCHED`: re-send the same key only in the current epoch while `DISPATCHED` and before `deadline_at`; afterwards wait for restart and reconciliation |

**Evidence-pair rule.** A returned `InvocationOutcome`'s `status` and
`termination_reason` form one evidence pair. The kernel never rewrites, replaces or
synthesizes either member to satisfy a lifecycle row. A direct terminal transition is
legal only when the complete pair satisfies that row's required evidence and the row's
own preconditions hold. Otherwise no direct terminal row is taken and no direct receipt
is minted. Recovery and adoption (7.2-9) record the same true pair. Kernel-observed
deadline or budget state never changes the pair: it can only fail a row's precondition.
Budget exhaustion is handled separately by the §4 `SUSPENDED_BY_BUDGET` row.

Rows are cited by section and ordinal: 7.2-1 is §7.2 `∅ → PENDING`, 7.2-2
`PENDING → REJECTED_BY_POLICY`, 7.2-4 `DISPATCHED → RUNNING`, 7.2-5..7.2-8 the
`RUNNING → COMPLETED`, `TIMED_OUT`, `FAILED` and `→ CANCELLED` rows, 7.2-9 the
`FINISHED(outcome)` reconciliation row and 7.2-10 the `ABSENT` reconciliation row; 5-2..5-5
are §5 `ALLOCATED → DISPATCHED`, `ALLOCATED → CLOSED_ABORTED`, `DISPATCHED → WORKING` and
`DISPATCHED → CLOSED_ABORTED`; 3-7, 3-8 and 3-11 are §3 `CONTRACTED → RUNNING`,
`CONTRACTED → READY` and `RUNNING → CONTRACTED`.

| id | rule |
|---|---|
| `WD-1` | **Dispatch record.** As above. §13 adds no entity, field, lifecycle value, `DecisionKind` or `CapabilityId`, and no `DISPATCHING`. The one enum value this lifecycle adds is `REFUSAL` in `WorkerReceipt.termination_reason` (domain-model §8.2). |
| `WD-2` | **Admission and key (T1).** Checks per §13.2 A. `attempt = ⟨run_id, invocation_ordinal_within_run⟩`, where the ordinal is 1 + the number of invocation records of the same `run_id` admitted before this one, of any status, counted inside the `∅ → PENDING` transaction. The key is `H(context_digest ‖ role ‖ attempt)`, where `‖` is defined by the canonical `KEY_PREIMAGE` encoding (§13.3) and `idempotency_key = "sha256:" + lowerhex(sha256(KEY_PREIMAGE))`, the default `Hash` form (domain-model §0.1). `run_id` is immutable and globally unique, and the ordinal is deterministic, so keys are distinct within a run and across runs, and stable across a restart. No field is added. **Collision refusal (fail-closed backstop):** if the computed key equals the key of any invocation record in the kernel's store (any project, run or status), `∅ → PENDING` is refused before any write — no event, no invocation, no decision consumed. |
| `WD-3` | **Preflight.** `preflight` runs only after T1 has made `PENDING` durable and before T2; it is the first provider call. Its dispositions are §13.2 B (record 7.2-2 in its own transaction) and §13.2 C (not recorded). A preflight call that returns nothing writes nothing. |
| `WD-4` | **Dispatch (T2).** As §13.1. Every check runs before any write. Any failure rolls back all of T2 and consumes nothing. |
| `WD-5` | **Invoke and re-send.** `invoke` is called only for an invocation committed `DISPATCHED` in the current epoch (§9.3). The same key may be re-sent (`WP-6`, `CF-11`) only while the invocation is still `DISPATCHED`, in the current epoch, and before `deadline_at`. That includes `UNAVAILABLE`/`RATE_LIMITED` retries with backoff (worker_provider §2.1). There is no re-send after `deadline_at` and no `invoke` after a restart (`WP-16`). |
| `WD-6` | **Outcome recording (T3).** Per §13.4. |
| `WD-7` | **Ambiguity and deadline.** An ambiguous invocation stays `DISPATCHED` and the run and stage do not advance. At `deadline_at` the kernel terminates the call regardless of provider state (`WP-10`) and may request `cancel` with reason `DEADLINE` under `run.abort`; neither the request nor its acknowledgement takes a row. After `deadline_at` there is no re-send, no same-epoch `lookup` (`recovery.reconcile` is not widened) and no direct timeout row from `DISPATCHED`. Final resolution depends on a controller restart, which requires GR-33 N6 `controller.start`, and on the existing reconciliation (7.2-9, 7.2-10 and the §5 `RECOVERY_AMBIGUITY` row). The session stops for the owner. |
| `WD-8` | **Stage after a first-invocation run abort.** Row 3-11 `RUNNING → CONTRACTED` is taken in T4 only if its preconditions hold, `attempt_count < max_attempts` included. At equality see `WD-12`. |
| `WD-9` | **Recovery (existing rows unchanged).** After the barrier clears, each run consequence is taken under its own row and capability in its own transaction, never under `recovery.reconcile`. 7.2-9 always records the outcome's true pair: the status mapping 7.2-9 already defines, with the receipt carrying `outcome.termination_reason` unchanged. A run consequence is justified by the complete reconciled pair, or by the recovery observation itself (`ABSENT`). A receipt's `termination_reason` alone never selects a run row. `FINISHED(outcome)`, `status ≠ REFUSED` (any reason): 7.2-9 terminal, then run 5-4 `DISPATCHED → WORKING`, justified by the status, which establishes execution (`WP-18`). `FINISHED(REFUSED + REFUSAL)`: 7.2-9 `→ FAILED` with the reconciled receipt carrying `REFUSAL`; for a first invocation, run 5-5 `DISPATCHED → CLOSED_ABORTED`, citing that receipt as its "provider rejected" evidence. `FINISHED(REFUSED + any reason ≠ REFUSAL)` — a malformed pair: 7.2-9 `→ FAILED` with the reconciled receipt carrying that true reason, unchanged. The pair establishes neither start nor non-start, so **neither 5-4 nor 5-5 is taken**, even when the reason is `PROVIDER_ERROR`. The run stays `DISPATCHED` and its disposition is left to existing human and escalation handling. This section adds no transition, receipt reason or authority for it. `ABSENT`: 7.2-10, then 5-5 (receipt `PROVIDER_ERROR`). `LIVE`: keep tracking, then adopt. Unanswerable: `UNRESOLVABLE`, a `RECOVERY_AMBIGUITY` escalation and the §5 `RECOVERY_AMBIGUITY` row. Then `WD-8`. |
| `WD-10` | **Retries.** Transport level: `WD-5` only. Invocation level: a new invocation in the same run only through a fresh E1/T1/P/E2/T2 under the §8 "later" branch; never a replacement for an unreconciled invocation (§9.3). `REFUSED` is never retried on the same binding (`WP-13`). Attempt level: a new `StageRun`, bounded by `attempt_count < max_attempts`. `max_attempts` stays a human import value (`RI-6`); Pilot-1's value of 1 is a pilot parameter, not a default. |
| `WD-11` | **Disposal of a run spent before T2.** See §13.5. |
| `WD-12` | **Attempts exhausted.** When a first-invocation run closes and `attempt_count = max_attempts`, 3-11 is barred and the stage stays `RUNNING` with no open run. No new run can start: 5-1 needs the stage `READY` or `CONTRACTED`, and 3-7 needs `attempt_count < max_attempts`. No `REPEATED_FAILURE` is raised automatically; that trigger stays `attempt_count > max_attempts` (domain-model §9.B :768). The exits are the existing human-controlled rows where their predicates hold: `RUNNING → ABANDONED` (`DECIDE(ABANDON)`), or `RUNNING → AWAITING_DECISION` only if a non-auto-resolvable escalation already exists. The pre-existing `>` (domain-model :768) versus `≥` (§3 `AWAITING_VALIDATION → AWAITING_DECISION` and `AWAITING_REVIEW → AWAITING_DECISION`) inconsistency is left unchanged and is not claimed closed. |
| `WD-13` | **Suspension.** At E1/T1 and E2/T2, project, stage and run suspension are all `NONE`; `QUIESCING` denies both. An invocation in flight is drained through `QUIESCING` (§4 `NONE → QUIESCING`) and 7.2-8. Reconciliation is not gated by §8 (`RI-8` names exactly three rows). |
| `WD-14` | **After a restart.** Any provider call is a new invocation and passes gates (a) and (b) afresh. The run's `secret.read` must be re-exercised per `SR-7`. §12 admits `secret.read` only at run `ALLOCATED`/`WORKING`, so a relay secret for the first invocation is resolved before T2. This is an observation, not a §12 change. |
| `WD-15` | **Bounded.** §0–§4, §6, §7.1, §7.3–§7.6, §8, §10, §11 (`RI-8`, `AC-*`) and §12 are unchanged. The other edits this lifecycle makes to this document are exactly: the 7.2-2 preconditions cell, the 5-5 required_evidence cell, the appended §7.2 `DISPATCHED → FAILED` row and the appended §9.3 `invoke` row. |

### 13.1 Ordering

| step | writes | content |
|---|---|---|
| E1 | none | Every pre-T1 check (§13.2 A, `WD-2`). |
| T1 | one immediate transaction | Re-run every E1 check. Compute the ordinal and key; refuse on collision. Append the `∅ → PENDING` event (payload: key, request digest, `controller_epoch`, `activation_id`, ordinal). Write the invocation. First invocation under `SUPERVISED`: consume the 7.2-1 approval (`VALID → CONSUMED` under `audit.append`, citing the act event). Commit. |
| P | its own transaction only for a 7.2-2 rejection | `preflight(request)`: the first provider call. Disposition per `WD-3`. |
| E2 | none | Every T2 check (§13.2). |
| T2 | one immediate transaction | Re-run every E2 check. First invocation: `e_wi` `PENDING → DISPATCHED`; `e_run` run `ALLOCATED → DISPATCHED`; `e_stage` stage `CONTRACTED → RUNNING` with `attempt_count` n → n+1; `SUPERVISED` only: `e_consume` of the 3-7 approval. Later invocations: `e_wi` only. Commit. |
| B | — | `invoke(request, bridge)` only after T2 has committed, in the same epoch. Same-key re-send only under `WD-5`. |
| T3 | one immediate transaction | Refuse and write nothing if the epoch changed. Otherwise classify and record per `WD-6`. Commit. |
| T4 | own transaction | Stage consequence after a first-invocation run abort (`WD-8`). |

Invocation `PENDING → DISPATCHED` and run `ALLOCATED → DISPATCHED` co-commit in T2 as
separate events; stage `CONTRACTED → RUNNING` co-commits with them, and its distinct
`SUPERVISED` `CONFIRM` (`AC-3`) is validated and consumed in T2. `attempt_count` is the
number of `StageRun`s that have entered `RUNNING`; it increments atomically with
`CONTRACTED → RUNNING` and is checked on the prior value. "First invocation" is the first
invocation record admitted for the run; `RI-8` is read literally.

### 13.2 Admission partition

**A. Before T1; a refusal writes nothing and spends no first-invocation slot:**

| # | check |
|---|---|
| 1 | §8 gate (a), `RI-8` |
| 2 | run `lifecycle ∈ {ALLOCATED, WORKING}` |
| 3 | budget headroom |
| 4 | `RUN-INV-3` barrier: every earlier invocation and commit intent is reconciled |
| 5 | the run's activation is live (un-revoked, un-expired) |
| 6 | first invocation under `SUPERVISED`: the 7.2-1 `APPROVE` is valid, current and has an unspent nonce |
| 7 | the provider resolves in the registry to `(provider_id, provider_version)` |
| 8 | the provider supports the contract's role, the chosen binding, and the assembled context fits the declared context limit |
| 9 | deterministic key derivation and key collision refusal (`WD-2`) |

Items 7 and 8 read the `ProviderDescriptor` the registry obtained from `describe` at
registration. No provider call is made before T1.

**B. After `PENDING`, recorded as 7.2-2 `PENDING → REJECTED_BY_POLICY`, only for causes
existing semantics support:**

- `preflight` returned `UNSUPPORTED_ROLE` or `UNKNOWN_BINDING` (worker_provider §2.1:
  "invocation `REJECTED_BY_POLICY`");
- the invocation's pinned `(provider_id, provider_version)` is no longer in the registry:
  the row's existing "provider not in registry";
- the requested capabilities exceed the run's effective set: the row's existing cause.

**C. After `PENDING`, not recorded; the invocation stays `PENDING` unless an existing row
applies:**

- `preflight` returned `CONTEXT_TOO_LARGE`: the worker_provider §2.1 response applies
  ("kernel re-bundles or escalates `CONTRACT_AMBIGUITY`"). Re-bundling means a new
  invocation, which for a run's first invocation is not admissible, so the kernel
  escalates `CONTRACT_AMBIGUITY` per §2.1.
- `preflight` returned a bare `accepted = false` with no mapped code: no row and no §2.1
  response exist, so nothing is written.
- `RI-8`(b) fails; a suspension is not `NONE`; the barrier is held; the epoch changed; the
  activation was revoked or expired; the 3-7 approval is missing, stale or used; the
  prompt bundle is missing.
- No direct row is used to clear such an invocation. No receipt is minted for an
  invocation that was never invoked, and `PENDING → CANCELLED` is not taken to clear a
  run. The invocation stays `PENDING` until a controller restart reconciles it (7.2-10 on
  `ABSENT`; `WD-11`).

Case C spends the first-invocation slot. If the invocation cannot proceed, the run follows
the `WD-11` disposition, which depends on a controller restart (GR-33 N6).

**E2 checks (before T2):**

- §8 gate (b), evaluated on the state before T2;
- barrier clear;
- invocation epoch equals project epoch;
- status is `PENDING`;
- prompt bundle stored;
- preflight accepted;
- no case C condition;
- first invocation only:
  - row 5-2 preconditions;
  - row 3-7 preconditions: run reaches `DISPATCHED` in this transaction;
    `attempt_count < max_attempts` on the prior count; budget remaining; activation live;
    run `input_snapshot_id` present; project `ACTIVE`/`SETTLING`; project and stage
    suspension `NONE`;
  - `SUPERVISED` 3-7 `APPROVE`: subject `{STAGE, stage_id}`; `grants = revokes = ∅`;
    snapshot-bound to the newest `COMPLETE` snapshot; valid, with an unspent nonce;
    distinct from every other confirmation (`AC-3`); recorded after preflight,
    immediately before T2.

### 13.3 `KEY_PREIMAGE`

The `WD-2` tuple is encoded canonically and injectively, components in this fixed order:

```
KEY_PREIMAGE =
  u32be(len(C)) || C ||   C = ASCII octets of context_digest in its canonical Hash
                          form "<alg>:<lowerhex>" (domain-model §0.1)
  u32be(len(R)) || R ||   R = UTF-8 octets of the WorkerRole member name,
                          e.g. "IMPLEMENTER"
  u32be(len(I)) || I ||   I = UTF-8 octets of StageRun.run_id exactly as recorded
                          (an Id string; no case folding or other normalization)
  u64be(n)                n = invocation_ordinal_within_run, 1 ≤ n ≤ 2^64 − 1
```

- `u32be(x)` is the unsigned 32-bit big-endian encoding of the octet length `x`. Each
  variable-length component must be at most 2^32 − 1 octets, otherwise `∅ → PENDING` is
  refused before any write.
- `u64be(n)` is the unsigned 64-bit big-endian encoding. `n = 0` is invalid.
- Every variable-length component is length-prefixed and the ordinal has a fixed width, so
  parsing is unambiguous. The same logical tuple always yields the same octets, and
  distinct tuples always yield distinct octets.
- The key is `"sha256:" + lowerhex(sha256(KEY_PREIMAGE))`.
- The collision refusal (`WD-2`) remains the fail-closed backstop against digest
  collision.
- No field is added. This defines only the byte encoding of the `WD-2` tuple.

### 13.4 Outcome recording

In every case the receipt event precedes the terminal event (evidence-model §3.3 evidence reachability). T3
evaluates in this fixed order:

1. **Classify the result.** Was a `ProviderError` raised, or no answer received (step 2)?
   Otherwise take the returned pair `(status, termination_reason)`.
2. **`ProviderError`, no answer, transport loss:** ambiguous (row X below).
3. **`status = REFUSED`:** only the exact pair `REFUSED + REFUSAL` is the refusal path
   (row R). Any other `REFUSED` pair is malformed (row M).
4. **`status ≠ REFUSED`:** execution is established (`WP-18`). Record 7.2-4
   `DISPATCHED → RUNNING` and, for a first invocation, 5-4 run `DISPATCHED → WORKING`.
   Then look up the exact pair in rows D1–D6. A direct terminal row is taken only if the
   pair matches exactly **and** that row's own precondition holds.
5. **Anything else:** fail closed (row F).

The rows are keyed on exact pairs, and each row's precondition is a separate condition, so
a result matches at most one row. No branch substitutes kernel observation for the
returned pair.

| row | returned pair / result | row precondition that must also hold | T3 records |
|---|---|---|---|
| R | `REFUSED` + `REFUSAL` | — | receipt `REFUSAL`, `DIRECT`; §7.2 `DISPATCHED → FAILED`, never `RUNNING`; first invocation: 5-5 run `DISPATCHED → CLOSED_ABORTED` (evidence cell accepts `REFUSAL`); later invocation: run stays `WORKING` |
| M | `REFUSED` + any reason ≠ `REFUSAL` | — | Malformed provider evidence. Not classified as execution established and not as not started: **no** `RUNNING`, **no** receipt, **no** refusal row, no run or stage transition. Nothing is written and the invocation stays `DISPATCHED` (as row X). The true pair is preserved (see `WD-9`). |
| D1 | `COMPLETED` + `COMPLETED` | 7.2-5 "provider returned output within deadline": the kernel-measured end is before `deadline_at` | receipt `COMPLETED`; 7.2-5 `RUNNING → COMPLETED` |
| D2 | `TIMED_OUT` + `DEADLINE` | 7.2-6 "`deadline_at` passed" | receipt `DEADLINE`; 7.2-6 `RUNNING → TIMED_OUT` |
| D3 | `FAILED` + `PROVIDER_ERROR` | 7.2-7 "provider error" (the pair itself) | receipt `PROVIDER_ERROR`; 7.2-7 `RUNNING → FAILED` |
| D4 | `CANCELLED` + `BUDGET` | 7.2-8 "budget exhaustion": the kernel observed budget exhaustion and requested `cancel` with reason `BUDGET` | receipt `BUDGET`; 7.2-8 `RUNNING → CANCELLED` |
| D5 | `CANCELLED` + `POLICY_STOP` | 7.2-8 "suspension": a suspension of the project, stage or run held and the kernel requested `cancel` with reason `SUSPENSION` | receipt `POLICY_STOP`; 7.2-8 `RUNNING → CANCELLED` |
| D6 | `CANCELLED` + `HUMAN_STOP` | 7.2-8 "human stop": a human stop was recorded and the kernel requested `cancel` with reason `HUMAN_STOP` | receipt `HUMAN_STOP`; 7.2-8 `RUNNING → CANCELLED` |
| F | a non-`REFUSED` pair not in D1–D6, or a D-pair whose row precondition fails. Examples: `COMPLETED + COMPLETED` after the kernel-measured deadline; `FAILED` with `BUDGET` / `POLICY_STOP` / `HUMAN_STOP` / `DEADLINE` / `COMPLETED` / `REFUSAL`; `CANCELLED + DEADLINE`; `CANCELLED + BUDGET` with no observed exhaustion; `TIMED_OUT + DEADLINE` before `deadline_at`; any pair whose reason contradicts its status | — | **Fail closed.** Step 4's 7.2-4 and 5-4 stand (execution is established). No receipt is minted, no reason is substituted, and no terminal row is taken. The invocation stays `RUNNING`, so `WD-5` forbids any re-send. The output is retained under the key (`WP-6`). After the next controller start, 7.2-9 records the true pair with `RECONCILED` attribution. No escalation is invented. |
| X | any `ProviderError` raised by `invoke`, whatever its code (`REFUSED`, `PROVIDER_ERROR`, `CANCELLED`, `UNAVAILABLE`, `RATE_LIMITED`, `UNSUPPORTED_ROLE`, `UNKNOWN_BINDING`, `CONTEXT_TOO_LARGE`); no answer; transport loss | — | Ambiguous (`WD-7`, `WP-18`). The code alone authorizes no terminal invocation transition and no run or stage transition, and no direct receipt is minted from it. It implies neither that execution started nor that it did not. Nothing is written and the invocation stays `DISPATCHED`. A same-key re-issue is allowed only under `WD-5` (current epoch, still `DISPATCHED`, before `deadline_at`). After `deadline_at`, resolution needs a restart and reconciliation. |

Kernel-observed deadline or budget state never selects a row by itself and never rewrites a
pair. It only decides whether a D-row's precondition holds. When the kernel observation
and the provider's pair disagree, the result is row F (or M), never a receipt with a
substituted reason.

### 13.5 Disposal of a run spent before T2

Applies when a run is `ALLOCATED` and its first-invocation slot is spent. That happens
after a §13.2 B rejection (the invocation is terminal `REJECTED_BY_POLICY`), after a §13.2
C residual or a refused E2 check (the invocation is still `PENDING`), or after a crash
between T1 and T2 (an old-epoch `PENDING` invocation). "No run started" in 3-8 means no run
has been `ALLOCATED` (has `started_at`, domain-model §5), so a run spent before T2 is
disposed of by human revocation and the stage stays `CONTRACTED`.

Phase 1 — only while any invocation of the run is still `PENDING`:

| step | act | authority |
|---|---|---|
| 1 | Do not mint a direct `WorkerReceipt`. Do not take `PENDING → CANCELLED` to clear the run. | truthful receipts (domain-model §8.2); no invented drain |
| 2 | A controller restart and recovery boundary is required: `project.controller_epoch` increments, which requires GR-33 N6 `controller.start`. The `PENDING` invocation is now old-epoch, so its `reconciliation_state` is `PENDING` (§5.1). | `P-INV-4`; §5.1; worker_provider §6.1 |
| 3 | Reconcile it by `lookup(idempotency_key)` under `recovery.reconcile` only. **`ABSENT`:** 7.2-10 `→ FAILED`, `ORPHANED`, receipt `PROVIDER_ERROR` with `attribution = RECONCILED` (a truthful record that nothing ran). **`FINISHED(outcome)`:** 7.2-9, `ADOPTED`, receipt carrying the outcome's reason (`REFUSAL` is representable). **`LIVE`:** keep tracking under the same key until the outcome arrives, then adopt. **Unanswerable:** `UNRESOLVABLE` and a `RECOVERY_AMBIGUITY` escalation. | 7.2-9, 7.2-10 and the paragraph after the §7.2 table; `WP-16` |
| 4 | The run is not closed until every one of its invocation records is terminal and reconciled (`NOT_REQUIRED`, `ADOPTED` or `ORPHANED`). An `UNRESOLVABLE` invocation keeps the run `ALLOCATED`, waiting on the human resolution of its `RECOVERY_AMBIGUITY` escalation. No further exit is added for that case: the §5 `RECOVERY_AMBIGUITY` row does not cover `ALLOCATED`. | `RUN-INV-3`; §5 `RECOVERY_AMBIGUITY` row |

Phase 2 — once every invocation of the run is terminal and reconciled (a §13.2 B rejection
enters here directly, with no restart):

| step | act | authority |
|---|---|---|
| 5 | A `HUMAN` records `DEC(REVOKE_CAPABILITY)`: subject `{CONTRACT, contract_id}`, `scope ≠ PROJECT` (so `AX-19`(c) retires no project grant). This decision kind is not snapshot-bound. Under `AUTONOMOUS` the row verdict is `CONFIRM` (an `APPROVE`). | §6 `ACTIVE → REVOKED`: `SUPERVISED` `DECIDE(REVOKE_CAPABILITY)`; `AUTONOMOUS` "else `CONFIRM`" |
| 6 | Transaction TR1: contract `ACTIVE → REVOKED` (`contract.revoke`, `KERNEL`, actor `RUNTIME`). **In the same transaction**, write the run's activation `revoked_at` (the event time), `revoked_by` (the event actor, with `on_behalf_of` the deciding human, `AX-16`) and `revocation_reason = HUMAN_REVOKE`. Consume the decision, citing the revocation event. | §6 `ACTIVE → REVOKED`; domain-model §6.2 (`revoked_at`, `revoked_by`, `revocation_reason`). No other row writes these fields, and 5-3 requires "activation revoked" |
| 7 | Transaction TR2: run 5-3 `ALLOCATED → CLOSED_ABORTED` (`run.abort`), citing the TR1 revocation event as its "revocation record". No invocation is drained, and none is still non-terminal. | 5-3 |
| 8 | `attempt_count` is unchanged: the run never entered `RUNNING`. | domain-model §4 `attempt_count` |
| 9 | The stage stays `CONTRACTED`. 3-8 is barred because an `ALLOCATED` run has started. | 3-8; domain-model §5 `started_at` |
| 10 | A later attempt needs a new contract: `∅ → DRAFT` (`contract.author`), then that contract's first activation/run pair — 6-2 + 5-1 under `AC-1`, with two `CONFIRM`s under `SUPERVISED`. 5-1 admits a `CONTRACTED` stage. The revoked contract is never reused (§6). There is no automatic revocation. | 5-1, §6 `∅ → DRAFT` and `DRAFT → ACTIVE`, §6 terminal note; `AC-1`..`AC-3` |

Phase 1 depends on the controller restart and recovery mechanism, so this disposal path
does **not** make Pilot-1 runnable before GR-33 N6. The
restart-boundary semantics of `WD-7` are unchanged.

### 13.6 Crash and restart

| crash point | durable state | resolution |
|---|---|---|
| before T1 commits | nothing | approval unspent; start again |
| after T1, before T2 (including during preflight) | invocation `PENDING`, run `ALLOCATED`, stage `CONTRACTED` | §13.5 phase 1 (`lookup`; `ABSENT` → 7.2-10 `FAILED`/`ORPHANED`), then phase 2 |
| after T2, before `invoke` | invocation and run `DISPATCHED`; stage `RUNNING`; `attempt_count` +1 | `ABSENT` → 7.2-10 → 5-5 → `WD-8` / `WD-12` |
| during `invoke`, or ambiguous (`WD-7`) | as above | `LIVE`: track; `FINISHED`: per `WD-9`; `ABSENT`: 5-5; unanswerable: the §5 `RECOVERY_AMBIGUITY` row |
| after return, before T3 | as above | `FINISHED` (`WP-6` retention) → `WD-9` |
| after a fail-closed T3 (`RUNNING`, no receipt) | invocation `RUNNING`, run `WORKING` | 7.2-9 records the true status and reason |

Duplicate execution is impossible: `invoke` is reachable only from a current-epoch
`DISPATCHED` (§9.3); there is no re-send once the invocation has left `DISPATCHED` or after
`deadline_at`; there is no `invoke` after a restart; keys are distinct per invocation and
per run (`WD-2`), with collision refusal behind that; and at most one run per stage is
unfinished (`RUN-INV-1`). It is detectable by evidence-model §3.2.1 effect attribution and
worker_provider `CF-1`, `CF-11`, `CF-13` and `CF-16`.

### 13.7 Events and refusals

| event | class | capability | payload |
|---|---|---|---|
| `∅ → PENDING` | `AUTHORITY` | `worker.invoke` | key, request digest, epoch, activation, ordinal |
| `PENDING → REJECTED_BY_POLICY` | `AUTHORITY` | `worker.invoke` | §13.2 B cause |
| `PENDING → DISPATCHED`; run `ALLOCATED → DISPATCHED`, `DISPATCHED → WORKING` | `AUTHORITY` | `worker.invoke` | key / invocation id |
| stage `CONTRACTED → RUNNING` | `AUTHORITY` | `run.start` | run, activation, `input_snapshot_id`, `attempt_count` n→n+1 |
| approval consumed | per §7.5 | `audit.append` | cites the act event |
| receipt | `EVIDENCE` | `worker.invoke` / `recovery.reconcile` | actual termination reason; `DIRECT`/`RECONCILED` |
| `DISPATCHED → FAILED` | `AUTHORITY` | `worker.invoke` | receipt reference (`REFUSAL`) |
| run `DISPATCHED → CLOSED_ABORTED` | `AUTHORITY` | `run.abort` | receipt reference (`PROVIDER_ERROR` or `REFUSAL`) |
| contract `ACTIVE → REVOKED` plus activation revocation fields | `AUTHORITY` | `contract.revoke` | `revoked_at`, `revoked_by`, `revocation_reason` |
| run 5-3 | `AUTHORITY` | `run.abort` | cites the revocation event |

| case | handling |
|---|---|
| capability or mode denial | an `AX-8` event in its own transaction (`RI-5` precedent). A policy `DENY` also raises a `POLICY_CONFLICT` escalation |
| precondition refusal (§13.2 A, §13.2 C, E2) | no event, nothing consumed (§12.2 precedent) |
| `CONTEXT_TOO_LARGE` after T1 | raises a `CONTRACT_AMBIGUITY` escalation per worker_provider §2.1 |

---

## 14. Controller start

One legal row for the `controller.start` act (authority-matrix §2.3). It is **not** an
axis, following the precedent of §10, §12 and §13: it reads axis 1 and writes no
lifecycle, suspension or entity field other than `Project.controller_epoch` (and the
`event_head`/`event_seq` advance of its own event). `from_state` and `to_state` name the
value of `project.controller_epoch`. The act is the one transition that begins a controller
epoch, and it is what domain-model `P-INV-4`, worker_provider §6.1 and §13 `WD-7`, §13.2 C
and §13.5 step 2 refer to as "controller start".

| from_state | to_state | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy | illegal_because |
|---|---|---|---|---|---|---|---|
| `controller_epoch = e` | `controller_epoch = e + 1` | the starting controller holds the project's controller hold (`CS-3`); the project's creation transaction has committed (`AX-17`); `project.lifecycle ≠ ARCHIVED`; `e < 18446744073709551615`; this controller has made no earlier write on the project | — | `controller.start` | `AUTO` | `AUTO` | — |

| id | rule |
|---|---|
| `CS-1` | **Exact act.** `controller.start` permits exactly one thing: `controller_epoch` `e → e + 1` on one project, recorded by the `controller.started` event (§14.3). It initiates no effect, reconciles nothing, observes nothing, and consumes and grants nothing. |
| `CS-2` | **Kernel-performed.** The actor is `RUNTIME`, acting as `RUNTIME_KERNEL`, the sole grantor (`AX-7`). `authority_ref` is absent (evidence-model §3.3). There is no `on_behalf_of`, because no deciding principal exists (`AX-16`). No `WORKER`, adapter, provider or `HUMAN` performs the act or holds the capability. The verdict is `AUTO` in both modes: authority-matrix §3 "all with class `KERNEL` → kernel only" and §4.1 cover it unchanged. No `HumanDecision` is required for, recorded for, or consumed by any start. |
| `CS-3` | **Controller hold.** Exclusivity is normative, per `CS-3a`..`CS-3h` below. |
| `CS-3a` | There is exactly one controller hold per project, and at most one live controller per project. |
| `CS-3b` | `controller.start` requires the hold. A start without it is refused before any write. |
| `CS-3c` | **One start per hold.** The hold admits exactly one `T_start`; a new epoch needs a new controller and a new hold. |
| `CS-3d` | The hold is released only after the controller **and every effect process it spawned** have ended. |
| `CS-3e` | Elapsed time never ends a hold. There is no TTL-based expiry, reclamation or lease-style takeover. A repository mutex, such as a `RepositoryLease`, does not satisfy `CS-3`. |
| `CS-3f` | This section prescribes only the property. The mechanism is the implementation's choice. The hold is not a domain entity, field or enum and is not written to the store. |
| `CS-3g` | A start attempted while another controller holds the hold is a precondition refusal and writes nothing. |
| `CS-3h` | **The hold covers local processes only.** It does not have to outlive a network request sent before the local process tree ended. Safety for such a request after a handoff comes from provider-side `ABSENT` finality (worker_provider `WP-19`, `CS-13`), not from the hold. |
| `CS-4` | **First write, once per hold.** `T_start` is the controller's first write on the project and happens once per hold. A second start by the same hold, or a start after any earlier write by this controller, is a precondition refusal. |
| `CS-5` | **`T_start` is atomic.** Exactly two things are written, in one `BEGIN IMMEDIATE` transaction: the `controller.started` event and `controller_epoch = e + 1`, in the same atomic write that advances `event_head`/`event_seq` (`AE-INV-2`; evidence-model §3.2 step 5). Run, stage, invocation, intent and decision rows are **not** written. Only `T_start` changes `controller_epoch`, and every change is +1: no decrement, no skip, no reset (§9.3). Each epoch value is taken by exactly one start. |
| `CS-6` | **Barrier by derivation.** From the commit of `T_start`, a record with `controller_epoch ≤ e` and a non-terminal `status` is `PENDING` by the §5.1 derivation **only while it is still awaiting reconciliation**, that is, while no recovery under `recovery.reconcile` has recorded a terminal `reconciliation_state` for it; no per-record write is required. A record whose `reconciliation_state` is already terminal under §5.1 — `ADOPTED`, `ORPHANED` or `UNRESOLVABLE` — keeps that state whatever its epoch or `status`, and an old-epoch record with a terminal `status` stays `NOT_REQUIRED`. `T_start` does not reset, reopen or rewrite a previously terminal `reconciliation_state`; in particular `UNRESOLVABLE` never reverts to `PENDING`. Any persisted copy of `reconciliation_state` is either written in `T_start` or never read by a gate. |
| `CS-7` | **Recovery is separate.** Reconciliation (worker_provider §6.1, the §7.2 and §7.4 reconciliation rows) runs after `T_start`, in its own transactions, under `recovery.reconcile` and never under `controller.start`. There is no recovery pre-flight inside the act. |
| `CS-8` | **Clear is per run.** The barrier clears per run exactly as `RUN-INV-3` defines. There is no project-wide flag and no "recovery complete" event. An `UNRESOLVABLE` record's run follows the §5 `RECOVERY_AMBIGUITY` row, or §13.5 step 4 for `ALLOCATED` runs. |
| `CS-9` | **Epoch fencing is defense in depth.** Every epoch-bound boundary re-reads `project.controller_epoch` in its own transaction: 7.2-1 carries the epoch; §13.2 E2 requires invocation epoch = project epoch; §13.1 T3 refuses if the epoch changed; §9.3 bars `invoke` outside current-epoch `DISPATCHED`; §12.3 `SB-7`(8) requires artifact epoch = project epoch; and `RUN-INV-3` is derived inside the `AUTHORIZED → APPLYING` transaction. Fencing cannot close the window between a check and an external `invoke` or repository mutation, so it never substitutes for `CS-3`. |
| `CS-10` | **No decision and no grant.** `T_start` changes no `decision_state`. `controller.start` never enters `HumanDecision.grants`, `ContractActivationRecord.granted_capabilities`, `WorkerInvocation.granted_capabilities`, `StageRun.effective_capabilities` or any project grant, and `T_start` writes none of them (`AX-7`). |
| `CS-11` | **Gates.** `controller.start` is none of the three `RI-8` rows; it is not gated by §8 and does not widen §8. It is admissible under every `SuspensionState`, `SUSPENDED_BY_INTEGRITY` included: refusing it there would leave no controller able to record the `DEC(OVERRIDE)` that the §4 `SUSPENDED_BY_INTEGRITY → NONE` row requires, and the act initiates no effect and only widens the barrier. It is refused when `project.lifecycle = ARCHIVED`, whose evidence set is sealed (§9.2). |
| `CS-12` | **Bounded.** This section adds one `CapabilityId` (`controller.start`, `KERNEL`) and no entity, field, enum value, `DecisionKind`, lifecycle value or `SuspensionState`. `controller.started` is a value of the existing free-text `event_type`. §0–§13 are unchanged except for the appended §9.3 `project.controller_epoch` row; `RI-8`, `AC-*`, §12 and §13 are unchanged, and the §13 references to "GR-33 N6 `controller.start`" are resolved by this section as their referent, not by edit. The epoch at genesis is not defined here: the `AX-17` genesis transaction creates no operation, and the project's first `controller.start` precedes every other act on it (`P-INV-4`, read per project). |
| `CS-13` | **`ABSENT` is final.** Recovery acts on a `lookup` `ABSENT` only as the final, tombstoned answer of worker_provider `WP-19`. The hold covers local processes only (`CS-3h`). |

### 14.1 Ordering

| step | phase | writes | content |
|---|---|---|---|
| A | process start | none | Composition only. Nothing is governed and nothing is written to any project. |
| H | controller hold taken (`CS-3`) | none to the store | Refuse, writing nothing, if the hold is unavailable. |
| E | read-only checks | none | Project exists; its genesis transaction has committed; `lifecycle ≠ ARCHIVED`; `e < 18446744073709551615`; no earlier write by this controller. |
| **T_start** | epoch advance, event, barrier | one `BEGIN IMMEDIATE` | (1) Re-read `e` and re-check every E check. (2) Append the `controller.started` event (§14.3). (3) Write `controller_epoch = e + 1` in the same atomic write that advances `event_head`/`event_seq`. (4) Commit. The barrier holds from this commit **by derivation** (`CS-6`). |
| R | reconciliation | its own transactions | worker_provider §6.1 plus the §7.2 and §7.4 reconciliation rows, under `recovery.reconcile`, never under `controller.start` (`CS-7`). An `ABSENT` answer is acted on only as the final, tombstoned `ABSENT` of `WP-19` (`CS-13`). |
| F | barrier clears | none added | Per run, when `RUN-INV-3` holds for it (`CS-8`). No event and no state are added. |

Before a run's records are reconciled, the only provider call on that run is `lookup`
under `recovery.reconcile`. A run with no `PENDING` or `UNRESOLVABLE` record may dispatch
after `T_start`, subject to every existing gate; its relay secret is re-exercised per
`SR-7` and `WD-14`.

Meaning of a recovery `lookup(k)` after `T_start`. Only `ABSENT` is qualified; the rows
acted on are the existing ones, unchanged:

| answer | meaning | kernel act |
|---|---|---|
| `FINISHED(outcome)` | execution was established, or the pair was reported (`WP-18`) | adopt the existing outcome: 7.2-9, `ADOPTED`, then `WD-9` |
| `LIVE(handle)` | execution began and is still running | stays `PENDING`, tracked under the same key, adopted when finished (worker_provider §6.1 step 5) |
| `ABSENT` | never received, **and** permanently barred: the provider committed the tombstone before answering (`WP-19`) | only then may 7.2-10 (`→ FAILED`, `ORPHANED`, receipt `PROVIDER_ERROR`, `RECONCILED`) and the subsequent §13.5 / `WD-9` rows proceed |
| error or unanswerable, including a failure to commit the tombstone | undecided | `UNRESOLVABLE` and `RECOVERY_AMBIGUITY` (`WP-16`, worker_provider §6.1 step 6) |

Once recovery has recorded `ABSENT`/`ORPHANED` for `k`, no delayed prior-epoch `invoke(k)`
can begin.

### 14.2 Crash and restart

| crash point | durable state | resolution |
|---|---|---|
| before `T_start` | nothing; the hold is released by process end | the next start proceeds normally |
| during `T_start` | rolled back: no event, epoch unchanged | as above |
| after `T_start`, before recovery | `e + 1` and its event are durable; the barrier is active by derivation and no work was done in `e + 1` | the next start writes `e + 2`; records of `≤ e` still awaiting reconciliation remain or become `PENDING` under the §5.1 derivation, records whose `reconciliation_state` is already terminal (`ADOPTED`, `ORPHANED`, `UNRESOLVABLE`) remain terminal and `UNRESOLVABLE` never reverts to `PENDING` (`CS-6`), and recovery runs under `e + 2` over the `PENDING` records only. An epoch in which no work happened is legitimate history |
| during recovery | each settled record is terminal (`ADOPTED`, `ORPHANED` and `UNRESOLVABLE` never revert, §5.1); the rest stay `PENDING`; `LIVE` tracking is lost | the next start re-runs worker_provider §6.1 over the remainder; `lookup` executes nothing, so repeating it is safe |
| after a provider committed an `ABSENT` tombstone, before the kernel recorded 7.2-10 | invocation still `PENDING`; key tombstoned at the provider | the next recovery's `lookup(k)` returns `ABSENT` again (`WP-19`), and 7.2-10 proceeds; `k` can never begin |
| old process tree ended with an `invoke(k)` still in transit | invocation old-epoch, not terminal | if the request arrives before recovery's `lookup(k)`: `LIVE` or `FINISHED`, then adopted. If it arrives after the `ABSENT` tombstone: it never begins (`WP-19`) |

### 14.3 Events and refusals

| field | value |
|---|---|
| `event_type` | `controller.started` |
| `epistemic_class` | `AUTHORITY`, the `KERNEL` transition envelope (§13 precedent) |
| `actor` | `RUNTIME`; no `on_behalf_of` (`AX-16`) |
| `capability_used` | `controller.start` |
| `authority_ref` | absent (`AX-7`; evidence-model §3.3) |
| `subject` | `{kind: PROJECT, id: project_id}` |
| `payload` | exactly `{"controller_epoch_from": <e>, "controller_epoch_to": <e + 1>}`, each a canonical unsigned decimal string: ASCII digits, no sign, no whitespace, no leading zero other than `"0"`, value ≤ 18446744073709551615 (the `SB-3` encoding, restated for §14 because `SB-3` is §12-scoped). No host, pid, credential or secret-derived member |

This event is the proof that a start happened. It is `AE-INV-2`'s event for the row, and
the chain's own `seq` orders successive starts.

| case | class | writes |
|---|---|---|
| hold unavailable (another live controller) | precondition refusal | none (§12.2, §13.7 precedent) |
| project absent, or its genesis transaction is not committed | precondition refusal | none |
| `lifecycle = ARCHIVED` | precondition refusal | none |
| `e = 18446744073709551615` | precondition refusal | none |
| a second start by the same hold, or any earlier write by this controller | precondition refusal | none |
| any non-`RUNTIME` actor, or any `controller_epoch` write outside `T_start` | the §9.3 `project.controller_epoch` row, `NONE_GRANTABLE`; recorded per `AX-8` (`NEVER_GRANTABLE`) where a started controller observes it | per the §13.7 capability-denial rule |
