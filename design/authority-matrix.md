# DESIGN-01 — Authority Matrix

Capability model for the governed runtime. Vendor-neutral: worker roles are
runtime concepts, not provider or model names.

---

## 0. Axioms

| id | axiom |
|---|---|
| `AX-1` | **Default DENY.** An action is denied unless one authority form admits it: a **run grant** (§5), a **project grant** (§5.3), a **per-act exercise** of a `HUMAN`-class capability against a live decision (§5.2), or the **kernel's own holding** of a `KERNEL`-class capability (`AX-7`). `decision.record` held by an authenticated `HUMAN_PRINCIPAL` is the single named exception to the requirement of a form (`AX-15`). There is no fifth form; absence of a rule is never permission. |
| `AX-2` | Every state-changing operation declares exactly one `CapabilityId`. An operation declaring none is denied. |
| `AX-3` | A grant is realized in exactly one of two forms. A **run grant** is per `ContractActivationRecord`, scoped to one `StageRun`, and frozen for that run's life (§5). A **project grant** is realized directly by a live `HumanDecision{kind: GRANT_CAPABILITY}` with `scope = PROJECT`, is scoped to one `Project`, carries only `ORD` capabilities whose §2 `grantable by` column names `HUMAN_PRINCIPAL`, and authorizes exactly the acts §5.3 names — those an activation cannot authorize, because they supply the structure an activation would have to reference. Its lifetime is `AX-19`(a)–(f) and is **not** bounded by the first activation: a later stage's first `contract.author` is the same kind of act as the first project's (§5.3). No third form of grant exists; a `HUMAN`-class capability is granted by neither form and is exercised per act (§5.2). |
| `AX-4` | For a **run grant**: `granted ⊆ capability_request ∩ role_default ∩ mode_allowed ∩ project.capability_ceiling`. For a **project grant** (§5.3): `granted ⊆ decision.grants ∩ mode_allowed ∩ project.capability_ceiling`, a project grant having no `capability_request` and no `worker_role` of its own — those are `StageContract` fields resolved per `WorkerInvocation` (§4.1) and a project grant is neither. A **per-act exercise** (§5.2) produces no `granted` set and is bounded by §5.2 instead. Intersection, never union. |
| `AX-5` | No principal may grant a capability it does not itself hold, except `HUMAN_PRINCIPAL` acting within `capability_ceiling`. |
| `AX-6` | Capabilities marked `NEVER` are not grantable by any principal, in any mode, under any decision. |
| `AX-7` | Capabilities marked `KERNEL` are held only by the runtime kernel, are non-delegable, and are never present in a `WorkerInvocation.granted_capabilities`. |
| `AX-8` | Denial is recorded. For a run grant every denied capability appears in `ContractActivationRecord.denied_capabilities` with a reason from that field's own enum, unchanged. For a project grant (§5.3) or a per-act exercise (§5.2) there is no activation, and the record is the denial `AuditEvent` §6 already requires: `epistemic_class = AUTHORITY`, its payload carrying each denied `CapabilityId` with a reason drawn from `denied_capabilities`' seven values — `NOT_IN_CEILING`, `ROLE_FORBIDDEN`, `MODE_FORBIDDEN`, `NO_GRANTOR`, `BUDGET`, `POLICY`, `NEVER_GRANTABLE` — **together with `REVOKED`**, which records retirement under `AX-10`/`AX-19`(c) and arises only at §5.3 step 5a — never in §5, §5.1 or §5.2, none of which retires anything. That eight-value set is the denial event's vocabulary and is not written into `denied_capabilities`. Silent denial is a defect in either form. |
| `AX-9` | A capability confers permission to *attempt*; it never substitutes for `required_evidence` in `transition-matrix.md`. |
| `AX-10` | Revocation is immediate for future operations and never retroactive for recorded evidence. |
| `AX-11` | **Bounding is not granting.** `project.capability_ceiling`, the §3 mode gate, `capability_request`, and the §4.1 role table only narrow the candidate set. A capability is granted only when a principal named in its §2 `grantable by` column produced an admissible grant record for it — admissibility tested by §5.1 for a run grant and by §5.3 for a project grant — and that record is cited by the grant it produced: in `ContractActivationRecord.capability_grant_basis` for a run grant, and by `AuditEvent.authority_ref` naming the granting `HumanDecision` for a project grant (§5.3, `AX-19`). A per-act exercise is not a grant and produces no basis entry (§5.2). |

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
| `project.ceiling.set` | initial setting of `Project.capability_ceiling`: empty → non-empty, once (transition-matrix §10); no replacement, widening, narrowing or mixed change | `HUMAN` | `HUMAN_PRINCIPAL` | DENY | `SUPERVISED`: `DEC(SET_CEILING)`; `AUTONOMOUS`: DENY. Never grantable to a worker; setting the ceiling bounds and grants nothing (`AX-11`) |
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
| `recovery.reconcile` | adopt or orphan an operation left unreconciled by a controller restart: call `WorkerProvider.lookup(idempotency_key)`, or match a landed revision to a `CommitIntent.operation_token`, and mint the resulting receipt with `attribution = RECONCILED` | `KERNEL` | `RUNTIME_KERNEL` | DENY | never grantable to a worker or adapter; reconciliation is the kernel deciding what already happened. It authorizes **observation only** — it does not permit `invoke`, a repository mutation, or the creation of any operation, and it is the sole capability exempt from the `RUN-INV-3` barrier (transition-matrix §5) |

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
| `project.ceiling.set` | `DEC(SET_CEILING)` | DENY |
| `budget.grant` | `DEC(GRANT_BUDGET)` | DENY |
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

### 5.2 Per-act exercise of a `HUMAN`-class capability

§5 and §5.1 resolve a contract's request into a run's grant. A `HUMAN`-class capability
never reaches a run that way: §4.1 denies every one of them to every role, and `D` is not
overridable by request. Such a capability is not granted and never stands; it is **held
for one act** by the live decision that authorizes that act, and the holding ends when
that decision is consumed. This is the possession `AX-1` and §6 require, obtained without
a grant, and it is one of `AX-1`'s four forms.

| step | check |
|---|---|
| 1 | the capability is registered in §2 with class `HUMAN` and a `grantable by` column naming `HUMAN_PRINCIPAL` |
| 2 | a legal row in `transition-matrix.md` names it as `required_capability`, and the act is that row. This procedure covers only such rows; §5.2.1 lists them |
| 3 | the §3 mode gate permits the capability under `governance_mode` as it stands before the act |
| 4 | a `HumanDecision` authorizing this act is live at the moment of the act: `decision_state = VALID`, unexpired, nonce unconsumed, and `HD-INV-4` satisfied where it is snapshot-bound (§6, decision freshness) |
| 5 | that decision's `decision_kind` is the kind the row's verdict names — `K` for `DECIDE(K)`, `APPROVE` for `CONFIRM` — or `APPROVE` where the row's verdict is `AUTO` (`AX-14`) |
| 6 | that decision's `grants` and `revokes` are both empty: it authorizes one act and delegates nothing (`AX-12`) |
| 7 | `decided_by.actor_kind = HUMAN` with `auth_method ∈ {SESSION, SIGNATURE, MTLS}`; the event's `actor` is the actor that performed the act, carrying `on_behalf_of` where that is not the deciding principal (`AX-16`) |
| 8 | the row's own preconditions and `required_evidence` hold, unchanged and unsubstituted (`AX-9`) |
| 9 | the event sets `authority_ref` to that `decision_id`; possession ends at `VALID → CONSUMED` |

### 5.2.1 The rows this procedure covers

Ten of the eighteen `HUMAN`-class capabilities in §2 are named as `required_capability`
by a legal row, on twenty-one rows in total: `project.create`, `project.abandon`,
`project.archive`, `project.ceiling.set`, `budget.grant`, `stage.reject`, `stage.abandon`,
`finding.waive`, `decision.record` and `secret.read`. The other eight have no legal row and
no exercise this procedure can bind; §5.2 supplies their authority form and not their
procedure.

`project.ceiling.set` and `budget.grant` each have one row, in transition-matrix §10,
authorized by `DEC(SET_CEILING)` and `DEC(GRANT_BUDGET)` respectively under `SUPERVISED`
and denied under `AUTONOMOUS`. Neither decision is a grant record: §5.1 and §5.3 step 1
admit only `decision_kind = GRANT_CAPABILITY`, step 6 above leaves both `grants` and
`revokes` empty, and step 9 consumes each decision by its own act. Writing a
`CapabilityId` into `capability_ceiling` confers it on no principal (`AX-11`), and neither
act reaches a run, an activation or a worker.

`secret.read` has one row, in transition-matrix §12, authorized by `CONFIRM` — one
`HumanDecision{kind: APPROVE}` per act — under `SUPERVISED` and denied under `AUTONOMOUS`.
That `APPROVE` is per-act exercise authority and not a grant record: §5.1 and §5.3 step 1
admit only `decision_kind = GRANT_CAPABILITY`, step 6 above leaves both `grants` and
`revokes` empty, and step 9 consumes the decision by its own act. A project
`GRANT_CAPABILITY` naming `secret.read` is neither required nor consumed by that row, and
`capability_ceiling` membership is not a precondition of it (`AX-11`, `AX-13`).
`secret.read` enters no grant set and no run set (`AX-12`), and no worker, adapter or
provider performs the act.

| id | rule |
|---|---|
| `AX-12` | Per-act possession is not a grant and never becomes one. The capability is never written into `HumanDecision.grants`, `ContractActivationRecord.granted_capabilities`, `WorkerInvocation.granted_capabilities` or `StageRun.effective_capabilities`, and the authorizing decision's `grants` and `revokes` are both empty. §5, §5.1, §4.1 and `AX-4`'s run-grant intersection are unchanged. |
| `AX-13` | Per-act exercise is bounded by §2's register row, the §3 mode gate, the row that names the capability, and one live decision per act. It is not bounded by `project.capability_ceiling`, which bounds grants (`AX-11`, `P-INV-2`). |
| `AX-14` | A `HUMAN`-class row whose verdict names a decision (`DECIDE(K)` or `CONFIRM`) is authorized by that decision. Where the verdict is `AUTO`, a `HumanDecision{kind: APPROVE}` over the row's subject is required instead; the frozen matrix contains exactly three such rows — `∅ → DRAFT` under `project.create`, `ABANDONED → ARCHIVED` under `project.archive`, and `∅ → VALID` under `decision.record`, the last exempt by `AX-15`. `AUTO` states the policy engine's contribution; it does not remove the §2 class legend's exercise-time decision. |
| `AX-15` | `decision.record` is held by an authenticated `HUMAN_PRINCIPAL` without a decision of its own, because the human act *is* the decision — which is why recording is `AUTO` in both modes (transition-matrix §7.5). It is the single named exception in `AX-1`, and it is not an instance of `AX-7`. No **other non-`KERNEL`** capability is self-held by any principal; the kernel's own holding of `KERNEL` capabilities stands untouched (`AX-7`, §1). |
| `AX-16` | The event's `actor` is the actor that performed the act. Where that actor is not the deciding principal — the controller writing a project record, the kernel resolving a secret for an adapter — it carries `on_behalf_of` naming the deciding principal, at delegation depth ≤ 2. A `WORKER` actor never performs a `HUMAN`-class exercise. The kernel self-grants nothing: the authority is the human's decision, named by `authority_ref`. |
| `AX-17` | `project.create` is exercised inside the store transaction that installs the project, over an allocated identifier. One conforming witness, unrelated defects held aside: `seq = 0` the `RealitySnapshot` under `snapshot.take`; `seq = 1` the creation approval reaching `VALID` under `decision.record`, citing event 0 as its `subject_snapshot_id`; `seq = 2` `∅ → DRAFT` under `project.create`, citing the decision as `authority_ref` and event 0 as its `SNAP`; `seq = 3` `VALID → CONSUMED` under `audit.append`, citing event 2. At commit `Project.event_seq = 3` and `event_head` is event 3's hash. Four transitions, four events, one transaction, no event merging two capability identities. |

### 5.3 Project-scope grants

The acts that establish a project's structure cannot be authorized by §5: a
`roadmap.import` supplies the stages, and a `contract.author` supplies the contract, that
an activation would have to reference, so neither can cite an activation of its own. A
project grant authorizes exactly those acts, and is one of `AX-1`'s four forms. The
delimitation is by **which act**, not by when: a later stage's first `contract.author` has
the same circularity as the first project's, so the grant is not bounded by the first
activation (`AX-3`, `AX-19`(d)).

Two decisions of this project are ordered by their position on its audit chain, and by
nothing else. For a `HumanDecision` `D` whose `project_id` is this project, `pos(D)` is the
`seq` of the `AuditEvent` that `AE-INV-2` requires for `D`'s `∅ → VALID` transition
(`transition-matrix.md:393`), the least such `seq` where that transition emits more than
one; that event lies on this project's chain, because the chain is per project
(`domain-model.md:778`). `pos` totally orders this project's decisions: `seq` is monotonic
and gapless (`domain-model.md:779`), `Project → AuditEvent` is a total order
(`domain-model.md:877`), and `seq` within a project is the authoritative total order
(`evidence-model.md:187`). `pos` is a position in the recorded history, not a clock reading
and not a commit time: a lower `seq` does not imply an earlier commit, and nothing below
needs it to. No field, entity, clock or sequence is introduced: `pos` names the frozen `seq`
of an event `AE-INV-2` already requires.

| step | operation |
|---|---|
| 0 | this resolution runs **at every act** under the grant, against the state at that act (`AX-19`(b)); no earlier result is reused |
| 1 | `P₀` = the `grants` set of the granting decision `G`, a `HumanDecision{kind: GRANT_CAPABILITY, scope: PROJECT}` whose `project_id` is this project — that field alone binds the grant to the project (`domain-model.md:691`) — and whose `subject.kind ∈ {PROJECT, CAPABILITY}`, with `subject.id` equal to `project_id` where the kind is `PROJECT` and unconstrained where it is `CAPABILITY`, and which is live at the moment of the act: `decision_state = VALID` and unexpired. No other subject profile is admitted, and a decision outside it realizes no project grant (`AX-19`(e), `R13.25`). Its nonce is spent once, at realization, and stays spent for the grant's life (`AX-19`(a)) |
| 2 | `P₁ = P₀ ∩ project.capability_ceiling`; differences denied `NOT_IN_CEILING` (`AX-4`, `P-INV-2`) |
| 3 | `P₂ = P₁` minus capabilities denied by the §3 mode gate; denied `MODE_FORBIDDEN` |
| 4 | `P₃ = P₂` minus every `KERNEL`, `HUMAN` and `NEVER` capability; denied `NEVER_GRANTABLE` (`AX-6`, `AX-7`, §5.2) |
| 5 | `P₄ = P₃` minus every capability whose §2 `grantable by` column does not name `HUMAN_PRINCIPAL`; denied `NO_GRANTOR` |
| 5a | `P₅ = P₄` minus every capability retired **from this grant** by revocation: `c` is retired from `G` if **any** `HumanDecision` `R{kind: REVOKE_CAPABILITY}` whose `project_id` is this project, whose `scope` covers this project, and whose `revokes` names `c` has **reached** `decision_state = VALID`, is not `VOID`, and has `pos(R) > pos(G)`. Denied `REVOKED` (`AX-10`, `AX-19`(c)). Both conjuncts are facts about the record and never stop holding: retirement does **not** depend on `R`'s current state, so a later expiry, consumption or staling of `R` restores nothing, and `pos(R) > pos(G)` is fixed when the two decisions are recorded. A revocation with `pos(R) < pos(G)` is **not** a revocation of this grant and does not reach it: `AX-10` makes revocation immediate for future operations, not for a grant a human records after it, so step 5a removes nothing from a `G` later on the chain than every revocation of `c`, and whether that `G` confers `c` is then decided by steps 2–5 alone (`AX-19`(c)). `pos(R) = pos(G)` would need one `AuditEvent` to record both decisions, and an event carries a single `subject` (`domain-model.md:786`); the inequality is strict, so nothing is retired on that case either. The step-2 and step-3 removals are **bounding**, not retirement, and are re-tested each act |
| 6 | the granted set is `P₅`, and it is what `G` confers. An act exercising a project grant cites one granting `decision_id` as its `authority_ref` (`AX-19`), so this resolution runs against that one decision; where a project has more than one admitted grant, each is resolved on its own and no union or intersection is taken across them. §4.1 is not applied: it is the per-`WorkerInvocation` role table and a project grant reaches no invocation (`AX-4`) |
| 7 | every denial from steps 2–5a is recorded in the denial `AuditEvent` per `AX-8`, with a reason from that axiom's eight-value vocabulary — the seven `denied_capabilities` values plus `REVOKED` for step 5a (`R13.24`) |

| id | rule |
|---|---|
| `AX-18` | A project grant is never copied into `ContractActivationRecord.granted_capabilities`, `WorkerInvocation.granted_capabilities` or `StageRun.effective_capabilities`. A worker's authority remains exactly `AX-3`'s run grant, resolved by §5 and bounded by `AX-4`'s first clause. `A-INV-2` **as amendment 23 amends it** therefore holds with every run set still sourced from the activation: activation remains the only entity conferring a run's **execution** authority. Frozen `A-INV-2`'s unqualified wording is **not** preserved and amendment 23 is required, because [transition-matrix.md:208](transition-matrix.md#L208) already confers authority over a run from outside it (`R13.22`). |
| `AX-19` | An event exercising a project grant sets `authority_ref` to the granting `decision_id`, live at `recorded_at` (evidence-model §3.3). That citation is the grant's basis record under `AX-11`. `G-2` is unchanged: a `HumanDecision` is already an admissible authority citation. The rest of this axiom is the project grant's **lifetime, chosen here and not derived** (`R6.5`). **(a) Realization and nonce.** The decision is realized once, as one standing project grant, at the moment it becomes `VALID`. That moment has a position on the project's audit chain — `pos(G)` as §5.3 defines it, the `seq` of the `AuditEvent` `AE-INV-2` requires for the `∅ → VALID` transition at `transition-matrix.md:393` — and clause (c) uses that position and no other ordering. Anchoring realization there is not a claim that the grant was recorded *for* a transition: `∅ → VALID` is the transition that **records** the decision, while `transition-matrix.md:394` consumes a decision that discharged the transition it was recorded **for**, and a project grant discharges none — which is the next sentence but one. That single realization is the one use `HD-INV-3` permits, and `AX-18` keeps the grant out of every run set, so it is never replayed across runs. It is **recorded for no transition**, so `transition-matrix.md:394`'s discharge predicate never holds of it and it never takes `VALID → CONSUMED`. **(b) Per-act re-test.** Every act under the grant re-runs §5.3 steps 1–6 against the state at that act: the decision must still be `VALID` and unexpired, and the granted set is recomputed from scratch. No result of an earlier act carries forward, and nothing is cached. **(c) Revocation retires the grants it follows; bounding does not.** A `HumanDecision` `R{kind: REVOKE_CAPABILITY}` whose `project_id` is this project, whose `scope` covers this project and whose `revokes` names `c` **permanently retires** `c` from every project grant `G` with `pos(G) < pos(R)`, from the moment `R` reaches `VALID`, per `AX-10`'s immediacy for future operations. The retirement is a **historical fact about two records and their order**, not a property of `R`'s current state: once `R` has reached `VALID` and is not `VOID`, `c` stays retired from those grants however `R`'s `decision_state` later moves, so a revocation that expires, is consumed or goes stale resurrects nothing, and `pos(G) < pos(R)` never stops holding either. `R` does **not** reach a grant realized after it. A `GRANT_CAPABILITY` decision `G′` with `pos(G′) > pos(R)` is a grant `R` precedes, and `AX-10` makes revocation immediate for future **operations**, not for grants a human records afterwards; `AX-10`'s other half — never retroactive for recorded evidence — is untouched, since nothing here reopens an act already performed under `G`. That is how `c` is restored: not by a ceiling widening, not by `R` leaving `VALID`, but only by a later `GRANT_CAPABILITY` decision, which must itself pass §5.3 steps 1–5 and is in turn retired by any revocation of `c` later on the chain than it. §5.3 gains this as step 5a, denied `REVOKED` (`AX-8`'s vocabulary, `R13.24`). An implementation must therefore retain or reconstruct that effect from the recorded revocation **and its chain position**; filtering only currently `VALID` revocation records does not implement this clause, and neither does applying every recorded revocation to every grant. Removal of `c` by `project.capability_ceiling` or the §3 mode gate is **bounding**: it is re-evaluated at every act, and a later widening makes `c` eligible again. Neither operation alters the immutable `decision.grants` or the granting decision's own `decision_state`. **(d) Scope end.** `expires_at` is optional, and when absent the `scope` bounds the decision (`domain-model.md:701`). A `scope = PROJECT` grant leaves its `scope` boundary — and so takes `transition-matrix.md:396`'s `VALID → EXPIRED` — when the project reaches a terminal lifecycle state (`ARCHIVED`, terminal at `transition-matrix.md:99`, or `ABANDONED`). Until then the grant is bounded by the project's life and **not** by activation: it survives the first activation, because §5.3 defines the acts it authorizes and the absence of a run is not one of its predicates. **(e) Other endings.** `now > expires_at` where one was set takes the same `:396`; `:397`'s `VOID` remains available and its own evidence cell is unclosed (§6.4, `KD-2`). `:395`'s `STALE` cannot apply, and the reason is the admission rule, not an assumption about it: §5.3 step 1 admits **only** `subject.kind ∈ {PROJECT, CAPABILITY}` on a decision whose `project_id` is this project, and `domain-model.md:702` makes exactly that subject profile of `GRANT_CAPABILITY` not snapshot-bound, so `snapshot_bound = false`, `subject_snapshot_id` is absent, `:395`'s precondition is unsatisfiable and `HD-INV-4` and authority-matrix `:289` have nothing to stale. A `GRANT_CAPABILITY` with `scope = PROJECT` but a `STAGE`, `RUN`, `COMMIT_INTENT` or `FINDING` subject **is** snapshot-bound by `domain-model.md:702`'s first disjunct and can go `STALE`; one over a `CONTRACT` or `ESCALATION` subject is not snapshot-bound but is not the profile `:702`'s final sentence names either. Step 1 admits none of these six as a project grant, and no clause of this axiom speaks about them. **(f) Exhaustive, over the profile step 1 admits.** For a grant `G` admitted by §5.3 step 1, (c), (d) and (e) are the complete set of endings: retirement of a capability by a revocation with `pos(R) > pos(G)` ((c)), the `scope` boundary or `expires_at` at `:396`, and `:397`'s `VOID`. No other condition ends such a grant or removes a capability from it, and no row of transition-matrix §7.5 is amended. The exhaustiveness is over that admitted profile and claims nothing about decisions step 1 rejects. Retirement under (c) reaches only the grants a revocation follows: it is not an ending of a grant recorded after that revocation, which is why a later `GRANT_CAPABILITY` can confer `c` again without any clause of this axiom being reopened or any row of §7.5 changing. |
| `AX-20` | `POLICY_ENGINE` is not an admissible grantor of a project grant. An `AUTONOMOUS` project's first import and first contract still require a live human grant, exactly as `roadmap.writeback` does in either mode (§5.1). |

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
| controller recovery | before a run **initiates any new external effect** — a dispatch, or an apply — every `WorkerInvocation` and `CommitIntent` of that run whose `controller_epoch` precedes `project.controller_epoch` has `reconciliation_state ∈ {NOT_REQUIRED, ADOPTED, ORPHANED}`, derived by transition-matrix §5.1 and resolved by `lookup(idempotency_key)` or by scanning for `operation_token`, both under `recovery.reconcile`; `PENDING` names the unresolved state and `UNRESOLVABLE` raises `Escalation(RECOVERY_AMBIGUITY)` (`RUN-INV-3`). The check does not gate the reconciling transitions themselves, which hold `recovery.reconcile` and initiate nothing |
| transition | `required_capability` from `transition-matrix.md` held at the moment of transition by one of `AX-1`'s forms — a run grant, a project grant, the kernel's own holding, or for this one act by a live decision under §5.2 — or held under `AX-1`'s named `decision.record` exception (`AX-15`), plus `required_evidence` present |
| audit append | every enforced denial emits an `AuditEvent` with `epistemic_class = AUTHORITY` |
