# DESIGN-01 — Authority Matrix

Capability model for the governed runtime. Vendor-neutral: worker roles are
runtime concepts, not provider or model names.

---

## 0. Axioms

| id | axiom |
|---|---|
| `AX-1` | **Default DENY.** An action with no matching grant is denied. Absence of a rule is never permission. |
| `AX-2` | Every state-changing operation declares exactly one `CapabilityId`. An operation declaring none is denied. |
| `AX-3` | Grants are per `ContractActivationRecord`, scoped to one `StageRun`, and frozen for that run's life. |
| `AX-4` | `granted ⊆ capability_request ∩ role_default ∩ mode_allowed ∩ project.capability_ceiling`. Intersection, never union. |
| `AX-5` | No principal may grant a capability it does not itself hold, except `HUMAN_PRINCIPAL` acting within `capability_ceiling`. |
| `AX-6` | Capabilities marked `NEVER` are not grantable by any principal, in any mode, under any decision. |
| `AX-7` | Capabilities marked `KERNEL` are held only by the runtime kernel, are non-delegable, and are never present in a `WorkerInvocation.granted_capabilities`. |
| `AX-8` | Denial is recorded: every denied capability appears in `ContractActivationRecord.denied_capabilities` with a reason. Silent denial is a defect. |
| `AX-9` | A capability confers permission to *attempt*; it never substitutes for `required_evidence` in `transition-matrix.md`. |
| `AX-10` | Revocation is immediate for future operations and never retroactive for recorded evidence. |
| `AX-11` | **Bounding is not granting.** `project.capability_ceiling`, the §3 mode gate, `capability_request`, and the §4.1 role table only narrow the candidate set. A capability is granted only when a principal named in its §2 `grantable by` column produced an admissible grant record for it (§5.1), and that record is cited in `ContractActivationRecord.capability_grant_basis`. |

---

## 1. Grantor principals

| principal | definition | may grant | constraint |
|---|---|---|---|
| `HUMAN_PRINCIPAL` | authenticated human with `auth_method ∈ {SESSION, SIGNATURE, MTLS}` | anything in `project.capability_ceiling` except `NEVER` | grant is a `HumanDecision{kind: GRANT_CAPABILITY}`; single-use nonce |
| `PROJECT_CEILING` | the `Project.capability_ceiling` set, itself set by `HUMAN_PRINCIPAL` | bounds all other grantors | cannot be widened by runtime or policy |
| `POLICY_ENGINE` | declarative policy at `Project.policy_digest` | `AUTONOMOUS` mode only; subset of ceiling marked `POLICY_GRANTABLE` | policy document itself is human-authored and digest-pinned |
| `ROLE_DEFAULT` | the per-role table in §4 | narrows, never widens | applied after ceiling and mode |
| `RUNTIME_KERNEL` | the runtime process | `KERNEL` capabilities to itself only | cannot delegate; cannot self-grant non-`KERNEL` capabilities |
| `NOBODY` | — | nothing | the grantor of record for `NEVER` capabilities |

### 1.1 Grant kinds

| grant_kind | source record | expiry |
|---|---|---|
| `HUMAN_DECISION` | `HumanDecision.grants` | `expires_at`, `scope` boundary, or `decision_state` leaving `VALID` (domain-model §9.A) |
| `POLICY` | policy evaluation against `policy_digest` | activation expiry |
| `CEILING` | `Project.capability_ceiling` | project lifetime |
| `ROLE_DEFAULT` | §4 | activation expiry |

---

## 2. Capability register

`class` legend: `ORD` ordinary (grantable to workers), `KERNEL` (runtime only,
`AX-7`), `HUMAN` (requires a `HumanDecision` at exercise time, not merely at
grant time), `NEVER` (`AX-6`).

### 2.1 Project and governance

| CapabilityId | permits | class | grantable by | default | mode restriction |
|---|---|---|---|---|---|
| `project.create` | create a `Project` in `DRAFT` | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | `AUTONOMOUS`: DENY |
| `project.mode.set` | change `governance_mode` | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | both modes require `DEC(SET_MODE)` |
| `project.lifecycle.advance` | axis-1 transitions other than abandon/archive | `KERNEL` | `RUNTIME_KERNEL` | DENY | — |
| `project.abandon` | axis-1 → `ABANDONED` | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | — |
| `project.archive` | axis-1 → `ARCHIVED` | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | — |
| `policy.set` | replace the policy document | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | — |
| `policy.override` | act contrary to a policy verdict once | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | never delegable to a worker |
| `budget.grant` | set initial `Budget` | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | — |
| `budget.extend` | raise a ceiling on a live project or run | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | — |
| `suspension.set` | set axis-3 to a non-`NONE` value | `KERNEL` | `RUNTIME_KERNEL`, `HUMAN_PRINCIPAL` | DENY | humans may always suspend |
| `suspension.clear` | return axis-3 to `NONE` | `KERNEL` | `RUNTIME_KERNEL`, `HUMAN_PRINCIPAL` | DENY | `SUSPENDED_BY_HUMAN` clears only by `DEC(RESUME)` |

### 2.2 Roadmap and stage

| CapabilityId | permits | class | grantable by | default | mode restriction |
|---|---|---|---|---|---|
| `roadmap.import` | fetch, normalize, and materialize stages | `ORD` | `HUMAN_PRINCIPAL`, `POLICY_ENGINE` | DENY | — |
| `roadmap.writeback` | write state back to the roadmap source | `ORD` | `HUMAN_PRINCIPAL` | DENY | `SUPERVISED`: requires `CONFIRM` per write |
| `stage.lifecycle.advance` | axis-2 transitions other than satisfy/reject/abandon | `KERNEL` | `RUNTIME_KERNEL` | DENY | — |
| `stage.satisfy` | axis-2 → `SATISFIED` | `KERNEL` | `RUNTIME_KERNEL` | DENY | evidence-gated per transition matrix §3 |
| `stage.reject` | axis-2 → `REJECTED` | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | — |
| `stage.abandon` | axis-2 → `ABANDONED` | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | — |
| `stage.declare` | write `declared_status` | `ORD` | `ROLE_DEFAULT` | DENY | never gates a transition (`G-6`) |

### 2.3 Contract and run

| CapabilityId | permits | class | grantable by | default | mode restriction |
|---|---|---|---|---|---|
| `contract.author` | create a `StageContract` in `DRAFT` | `ORD` | `HUMAN_PRINCIPAL`, `POLICY_ENGINE` | DENY | — |
| `contract.activate` | mint a `ContractActivationRecord` | `KERNEL` | `RUNTIME_KERNEL` | DENY | `SUPERVISED`: requires `CONFIRM` |
| `contract.revoke` | revoke or expire a contract | `KERNEL` | `RUNTIME_KERNEL`, `HUMAN_PRINCIPAL` | DENY | — |
| `contract.supersede` | activate a successor contract | `ORD` | `HUMAN_PRINCIPAL` | DENY | — |
| `run.start` | allocate and dispatch a `StageRun` | `KERNEL` | `RUNTIME_KERNEL` | DENY | `SUPERVISED`: first run of a stage requires `CONFIRM` |
| `run.abort` | terminate a run and drain its operations | `KERNEL` | `RUNTIME_KERNEL`, `HUMAN_PRINCIPAL` | DENY | — |
| `worker.invoke` | dispatch a `WorkerInvocation` | `KERNEL` | `RUNTIME_KERNEL` | DENY | workers never hold this; see `AX-7` |
| `worker.delegate` | a worker spawning a sub-worker | `NEVER` | `NOBODY` | DENY | delegation must route through the kernel so grants stay bounded |
| `recovery.reconcile` | adopt or orphan an operation left unreconciled by a controller restart: replay a persisted `InvocationRequest` under its `idempotency_key`, or match a landed revision to a `CommitIntent.operation_token`, and mint the resulting receipt with `attribution = RECONCILED` | `KERNEL` | `RUNTIME_KERNEL` | DENY | never grantable to a worker or adapter; reconciliation is the kernel deciding what already happened |

### 2.4 Workspace and execution

| CapabilityId | permits | class | grantable by | default | mode restriction |
|---|---|---|---|---|---|
| `fs.read` | read paths matching contract scope | `ORD` | `ROLE_DEFAULT`, `POLICY_ENGINE` | DENY | scope-bounded always |
| `fs.read.outside_scope` | read outside contract scope, inside workspace | `ORD` | `HUMAN_PRINCIPAL` | DENY | `AUTONOMOUS`: DENY |
| `fs.read.outside_workspace` | read outside `workspace_root` | `NEVER` | `NOBODY` | DENY | workspace is the containment boundary |
| `fs.write` | create or modify in-scope paths in a staging area | `ORD` | `ROLE_DEFAULT` | DENY | never writes the live tree; see `commit.apply` |
| `fs.delete` | propose deletion of in-scope paths | `ORD` | `HUMAN_PRINCIPAL`, `POLICY_ENGINE` | DENY | `SUPERVISED`: `CONFIRM` per intent |
| `fs.write.outside_scope` | write outside contract scope | `NEVER` | `NOBODY` | DENY | scope is what the activation was approved against |
| `proc.exec.validation` | run a `CommandSpec` byte-identical to a contract `ValidationSpec` | `ORD` | `ROLE_DEFAULT` | DENY | — |
| `proc.exec.arbitrary` | run a command not declared in the contract | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | `AUTONOMOUS`: DENY; results are never EVIDENCE |
| `net.egress.allowlist` | network to policy-allowlisted hosts | `ORD` | `HUMAN_PRINCIPAL`, `POLICY_ENGINE` | DENY | — |
| `net.egress.any` | unrestricted network | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | `AUTONOMOUS`: DENY |
| `secret.read` | resolve a named secret into an execution environment | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | values never enter artifacts or the audit log |
| `snapshot.take` | create a `RealitySnapshot` | `KERNEL` | `RUNTIME_KERNEL` | DENY | — |

### 2.5 Evidence and review

| CapabilityId | permits | class | grantable by | default | mode restriction |
|---|---|---|---|---|---|
| `validation.request` | create a `ValidationOperation` | `ORD` | `ROLE_DEFAULT` | DENY | — |
| `validation.execute` | run the operation in a sandbox | `KERNEL` | `RUNTIME_KERNEL` | DENY | — |
| `validation.attest` | mint a `ValidationReceipt` | `KERNEL` | `RUNTIME_KERNEL` | DENY | external executors only via signed attestation binding |
| `review.submit` | create a `Review` with a verdict | `ORD` | `ROLE_DEFAULT` | DENY | — |
| `review.attest` | mint a `ReviewAttestation` over an existing `Review`: the kernel's EVIDENCE record that a review meeting its spec's quorum and independence exists and carries a stated verdict | `KERNEL` | `RUNTIME_KERNEL` | DENY | the attestation measures the review's provenance, never its judgement |
| `review.attest.independent` | mark a review as satisfying an `INDEPENDENT` spec | `KERNEL` | `RUNTIME_KERNEL` | DENY | independence is computed from provenance, never asserted |
| `finding.raise` | create a `Finding` | `ORD` | `ROLE_DEFAULT` | DENY | — |
| `finding.resolve` | move a finding to `ACKNOWLEDGED`, `FIXED`, `DISPUTED`, `INVALID` | `ORD` | `ROLE_DEFAULT` | DENY | `FIXED` still requires fresh evidence |
| `finding.waive` | move a finding to `WAIVED` | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | only when the bound criterion is `waivable` |

### 2.6 Integration

| CapabilityId | permits | class | grantable by | default | mode restriction |
|---|---|---|---|---|---|
| `commit.propose` | create a `CommitIntent` | `ORD` | `ROLE_DEFAULT` | DENY | — |
| `commit.authorize` | move an intent to `AUTHORIZED` | `KERNEL` | `RUNTIME_KERNEL` | DENY | `SUPERVISED`: `CONFIRM` |
| `commit.apply` | write the mutations to the live workspace | `KERNEL` | `RUNTIME_KERNEL` | DENY | — |
| `commit.publish` | push beyond the local workspace | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | `SUPERVISED`: `DECIDE(APPROVE)`; `AUTONOMOUS`: `CONFIRM` |
| `commit.rewrite_history` | alter already-published revisions | `NEVER` | `NOBODY` | DENY | destroys the correspondence between evidence and what others received |

### 2.7 Governance records

| CapabilityId | permits | class | grantable by | default | mode restriction |
|---|---|---|---|---|---|
| `escalation.raise` | create an `Escalation` | `ORD` | `ROLE_DEFAULT` | DENY | granted to every role; raising is never restricted |
| `escalation.resolve` | move an escalation out of `OPEN`/`ACKNOWLEDGED` | `KERNEL` | `RUNTIME_KERNEL`, `HUMAN_PRINCIPAL` | DENY | `auto_resolvable = false` requires a `HumanDecision` |
| `decision.record` | persist a `HumanDecision` | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | actor must be `HUMAN`; `HD-INV-1` |
| `audit.append` | append an `AuditEvent` | `KERNEL` | `RUNTIME_KERNEL` | DENY | — |
| `audit.read` | read the event log and artifact store | `ORD` | `HUMAN_PRINCIPAL`, `POLICY_ENGINE` | DENY | redaction-aware |
| `audit.redact` | replace an artifact payload with a tombstone | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | digests and chain untouched |
| `audit.rewrite` | alter or delete an `AuditEvent` | `NEVER` | `NOBODY` | DENY | the chain is the only thing making every other guarantee checkable |

---

## 3. Mode gate

Applied after ceiling, before role defaults.

| CapabilityId | `SUPERVISED` | `AUTONOMOUS` |
|---|---|---|
| `project.create` | grantable | DENY |
| `project.mode.set` | `DEC(SET_MODE)` | `DEC(SET_MODE)` |
| `fs.read.outside_scope` | grantable | DENY |
| `proc.exec.arbitrary` | grantable | DENY |
| `net.egress.any` | grantable | DENY |
| `secret.read` | grantable | grantable, allowlist-pinned |
| `roadmap.writeback` | `CONFIRM` per write | grantable |
| `commit.publish` | `DEC(APPROVE)` | `CONFIRM` |
| `fs.delete` | `CONFIRM` per intent | grantable |
| `finding.waive` | `DEC(WAIVE)` | `DEC(WAIVE)` |
| `contract.activate`, `run.start` | `CONFIRM` | grantable |
| all others in §2 with class `ORD` | grantable | grantable |
| all with class `KERNEL` | kernel only | kernel only |
| all with class `NEVER` | DENY | DENY |

`AUTONOMOUS` never widens the set of `HUMAN`-class capabilities; it only removes
per-action confirmation on `ORD`-class ones.

---

## 4. Worker roles and per-invocation grants

Roles are runtime-defined. A provider is bound to a role by the contract's
`worker_role`; the provider cannot select its own role.

| role | purpose | may produce |
|---|---|---|
| `PLANNER` | decompose intent into contracts and criteria | `StageContract` drafts, `Claim` |
| `IMPLEMENTER` | produce mutations that satisfy criteria | `MutationProposal`, `CommitIntent`, `ValidationOperation`, `Claim` |
| `REVIEWER` | assess a diff or snapshot against criteria | `Review`, `Finding` |
| `INTEGRATOR` | reconcile mutations with the live workspace | `CommitIntent`, `ValidationOperation` |
| `ANALYST` | read-only investigation and evidence gathering | `Claim`, `Finding`, `ValidationOperation` |

### 4.1 Grant table (per `WorkerInvocation`)

`G` granted by role default. `C` conditional — granted only if also present in
`capability_request`, the ceiling, and the mode gate. `D` denied to this role.
Every cell is additionally bounded by `AX-4`; `D` is not overridable by request.

| CapabilityId | `PLANNER` | `IMPLEMENTER` | `REVIEWER` | `INTEGRATOR` | `ANALYST` |
|---|---|---|---|---|---|
| `fs.read` | `G` | `G` | `G` | `G` | `G` |
| `fs.read.outside_scope` | `C` | `D` | `C` | `D` | `C` |
| `fs.write` | `D` | `G` | `D` | `G` | `D` |
| `fs.delete` | `D` | `C` | `D` | `C` | `D` |
| `proc.exec.validation` | `D` | `G` | `G` | `G` | `G` |
| `proc.exec.arbitrary` | `D` | `D` | `D` | `D` | `C` |
| `net.egress.allowlist` | `C` | `C` | `D` | `C` | `C` |
| `net.egress.any` | `D` | `D` | `D` | `D` | `D` |
| `secret.read` | `D` | `C` | `D` | `C` | `D` |
| `validation.request` | `D` | `G` | `G` | `G` | `G` |
| `review.submit` | `D` | `D` | `G` | `D` | `D` |
| `finding.raise` | `G` | `G` | `G` | `G` | `G` |
| `finding.resolve` | `D` | `C` | `G` | `C` | `D` |
| `finding.waive` | `D` | `D` | `D` | `D` | `D` |
| `commit.propose` | `D` | `G` | `D` | `G` | `D` |
| `contract.author` | `G` | `D` | `D` | `D` | `D` |
| `contract.supersede` | `C` | `D` | `D` | `D` | `D` |
| `stage.declare` | `G` | `G` | `G` | `G` | `G` |
| `escalation.raise` | `G` | `G` | `G` | `G` | `G` |
| `audit.read` | `C` | `C` | `G` | `C` | `G` |
| `roadmap.import` | `C` | `D` | `D` | `D` | `D` |
| `roadmap.writeback` | `C` | `D` | `D` | `D` | `D` |
| every `KERNEL` capability | `D` | `D` | `D` | `D` | `D` |
| every `HUMAN` capability | `D` | `D` | `D` | `D` | `D` |
| every `NEVER` capability | `D` | `D` | `D` | `D` | `D` |

### 4.2 Role constraints

| id | constraint |
|---|---|
| `RC-1` | `REVIEWER` never holds `fs.write`, `fs.delete`, or `commit.propose`. A reviewer that can change the artifact cannot independently assess it. |
| `RC-2` | An invocation whose provider, prompt bundle, or context digest overlaps the `IMPLEMENTER` invocation under review yields `independence = SHARED_CONTEXT`; identical provider session yields `SELF_REVIEW`. Neither satisfies an `INDEPENDENT` `ReviewSpec`. |
| `RC-3` | `PLANNER` never holds `fs.write`: planning output is a contract, not a change. |
| `RC-4` | `ANALYST` is read-only with respect to the workspace; its `proc.exec.arbitrary` results are recorded as `Claim`, never as `ValidationReceipt`. |
| `RC-5` | `INTEGRATOR` holds `commit.propose` but never `commit.authorize` or `commit.apply`; proposal and application are separated. |
| `RC-6` | No role holds `worker.invoke`. Fan-out is a kernel decision so that grants stay bounded by `AX-4`. |

---

## 5. Resolution algorithm

| step | operation |
|---|---|
| 1 | `S₀ = contract.capability_request` |
| 2 | `S₁ = S₀ ∩ project.capability_ceiling`; differences recorded as `NOT_IN_CEILING` |
| 3 | `S₂ = S₁` minus capabilities denied by the §3 mode gate; recorded as `MODE_FORBIDDEN` |
| 4 | `S₃ = S₂ ∩ role_default(worker_role)` per §4.1, with `C` cells retained only if requested; differences recorded as `ROLE_FORBIDDEN` |
| 5 | `S₄ = S₃` minus every `KERNEL` and `NEVER` capability; recorded as `NEVER_GRANTABLE` |
| 6 | for each remaining capability, require an admissible grantor per §5.1 and record the grant record that supplied it; otherwise drop and record `NO_GRANTOR`. Class is not a shortcut: an `ORD` capability whose `grantable by` column names only `HUMAN_PRINCIPAL` needs the same live `HumanDecision{kind: GRANT_CAPABILITY}` an `HUMAN`-class one needs |
| 7 | if any budget dimension is exhausted, drop every capability with a cost side effect and record `BUDGET` |
| 8 | `granted_capabilities = S₄` after step 7; write `ContractActivationRecord` with `granted_capabilities`, `denied_capabilities`, and `capability_grant_basis` carrying exactly one §5.1 grant record per granted capability. A granted capability with no basis entry is an integrity violation, not a grant (`A-INV-3`) |
| 9 | freeze: `StageRun.effective_capabilities = granted_capabilities`, immutable for the run |

An empty `granted_capabilities` is legal and means the run can do nothing; it is
recorded rather than treated as an error, and raises
`Escalation(CAPABILITY_DENIED)`.

### 5.1 Admissible grantors

A grantor is admissible for capability `c` only if it appears in `c`'s
`grantable by` column in §2 **and** the matching record below exists at
activation time.

| grantor named in §2 | admissible only when | recorded in `capability_grant_basis` |
|---|---|---|
| `HUMAN_PRINCIPAL` | a `HumanDecision{kind: GRANT_CAPABILITY}` naming `c` is live: `decision_state = VALID`, nonce unconsumed, unexpired, and its `scope` covers this run | `grant_kind = HUMAN_DECISION`, `ref = decision_id` |
| `POLICY_ENGINE` | `governance_mode = AUTONOMOUS`, the policy document at `policy_digest` marks `c` `POLICY_GRANTABLE`, and the evaluation is persisted | `grant_kind = POLICY`, `ref = policy evaluation id` |
| `ROLE_DEFAULT` | §4.1 gives `c` a `G` cell for `worker_role`, or a `C` cell with `c ∈ capability_request` | `grant_kind = ROLE_DEFAULT`, `ref` absent |
| `RUNTIME_KERNEL` | never for a run's grant: `KERNEL` capabilities are removed at step 5 and never appear in `granted_capabilities` (`AX-7`) | — |
| `NOBODY` | never (`AX-6`) | — |

`PROJECT_CEILING` is never an admissible grantor. It is the bound every other
grantor is checked against, and membership in it grants nothing (`AX-11`).
Likewise a `G` or `C` cell in §4.1 supplies a grant only where §2 names
`ROLE_DEFAULT` as a grantor of that capability; for every other capability the
cell only decides whether an otherwise-granted capability survives. So
`roadmap.writeback`, whose §2 grantor is `HUMAN_PRINCIPAL` alone, is denied with
`NO_GRANTOR` for a `PLANNER` in either governance mode unless a live human grant
covers it — its `ORD` class, its presence in the ceiling, its `C` cell, and its
presence in `capability_request` change nothing.

---

## 6. Enforcement points

| point | check |
|---|---|
| activation | §5 resolution; `AX-4` |
| invocation dispatch | `WorkerInvocation.granted_capabilities ⊆ StageRun.effective_capabilities` |
| syscall or tool mediation | requested capability present, and target inside the scope it was granted for |
| receipt minting | `validation.attest`, `review.attest`, `commit.apply` and `recovery.reconcile` held by a `RUNTIME` actor only; a receipt minted under `recovery.reconcile` carries `attribution = RECONCILED` |
| decision freshness | every cited `HumanDecision` has `decision_state = VALID`; a decision with `snapshot_bound = true` whose `subject_snapshot_id` is no longer the newest `COMPLETE` snapshot over the subject's scope is `STALE` and discharges nothing (`HD-INV-4`) |
| operation identity | no provider call before `request_ref` and its `idempotency_key` are durable; no repository mutation before `operation_token` is durable (`G-9`) |
| controller recovery | before a run dispatches new work or applies a commit, every `WorkerInvocation` and `CommitIntent` of that run whose `controller_epoch` precedes `project.controller_epoch` has `reconciliation_state ∈ {NOT_REQUIRED, ADOPTED, ORPHANED}`, resolved by replaying `request_ref` under its original key or by scanning for `operation_token` under `recovery.reconcile`; an `UNRESOLVABLE` one raises `Escalation(RECOVERY_AMBIGUITY)` (`RUN-INV-3`) |
| transition | `required_capability` from `transition-matrix.md` held at the moment of transition, plus `required_evidence` present |
| audit append | every enforced denial emits an `AuditEvent` with `epistemic_class = AUTHORITY` |
