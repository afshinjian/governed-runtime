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
| `DRAFT` | `PLANNING` | `roadmap_id` present and `roadmap.drift_state = IN_SYNC` and `dependency_edges` acyclic | `SNAP` | `roadmap.import` | `AUTO` | `AUTO` | — |
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
| `∅` | `ALLOCATED` | `ACT` valid and un-expired; `run.suspension = NONE` | `ACT`, `SNAP` as `input_snapshot_id` | `run.start` | `CONFIRM` | `AUTO` | — |
| `ALLOCATED` | `DISPATCHED` | a `WorkerInvocation` accepted by a provider; `granted_capabilities ⊆ effective_capabilities` | — | `worker.invoke` | `AUTO` | `AUTO` | — |
| `ALLOCATED` | `CLOSED_ABORTED` | activation revoked before dispatch | revocation record | `run.abort` | `AUTO` | `AUTO` | — |
| `DISPATCHED` | `WORKING` | provider reported execution started | — | `worker.invoke` | `AUTO` | `AUTO` | — |
| `DISPATCHED` | `CLOSED_ABORTED` | provider rejected or failed to start | `WR` with `termination_reason = PROVIDER_ERROR` | `run.abort` | `AUTO` | `AUTO` | — |
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
| `PENDING` | `REJECTED_BY_POLICY` | requested capabilities exceed run's effective set, or provider not in registry | — | `worker.invoke` | `AUTO` | `AUTO` | — |
| `PENDING` | `DISPATCHED` | provider accepted; prompt bundle stored content-addressed | `prompt_bundle_ref` persisted | `worker.invoke` | `AUTO` | `AUTO` | — |
| `DISPATCHED` | `RUNNING` | provider reported start | — | `worker.invoke` | `AUTO` | `AUTO` | — |
| `RUNNING` | `COMPLETED` | provider returned output within deadline | `WR` attested by runtime | `worker.invoke` | `AUTO` | `AUTO` | — |
| `RUNNING` | `TIMED_OUT` | `deadline_at` passed | `WR` with `termination_reason = DEADLINE` | `worker.invoke` | `AUTO` | `AUTO` | — |
| `RUNNING` | `FAILED` | provider error | `WR` with `termination_reason = PROVIDER_ERROR` | `worker.invoke` | `AUTO` | `AUTO` | — |
| `PENDING`, `DISPATCHED`, `RUNNING` | `CANCELLED` | suspension, budget exhaustion, or human stop | `WR` with matching `termination_reason` | `run.abort` | `AUTO` | `AUTO` | — |
| `PENDING`, `DISPATCHED`, `RUNNING` | `COMPLETED`, `FAILED`, `TIMED_OUT`, `CANCELLED` | reconciliation: `controller_epoch < project.controller_epoch`; `lookup(idempotency_key)` returned `FINISHED(outcome)` (`WP-16`). The invocation takes the status `outcome.status` maps to — `COMPLETED → COMPLETED`, `FAILED → FAILED`, `TIMED_OUT → TIMED_OUT`, `CANCELLED → CANCELLED`, `REFUSED → FAILED` — and never `COMPLETED` for a non-`COMPLETED` outcome | `WR` attested by the runtime carrying `outcome.termination_reason`, with `attribution = RECONCILED` | `recovery.reconcile` | `AUTO` | `AUTO` | — |
| `PENDING`, `DISPATCHED`, `RUNNING` | `FAILED` | reconciliation: `lookup(idempotency_key)` returned `ABSENT` — the provider holds no outcome and no live invocation under that key, so the invocation never took effect | `WR` with `termination_reason = PROVIDER_ERROR` and `attribution = RECONCILED` | `recovery.reconcile` | `AUTO` | `AUTO` | — |

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
