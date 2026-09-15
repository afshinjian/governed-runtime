# DESIGN-03 — Project Provisioning

| Property | Amendment |
|---|---|
| Baseline | `design-01-frozen`; this document is the amendment, not a replacement of that baseline. `DESIGN-02` is unaffected and unreferenced by any rule here. |
| Gap | The frozen design registers `project.mode.set`, `policy.set`, `budget.grant` and `budget.extend` as `HUMAN` capabilities, and requires `DEC(SET_MODE)` for a mode change, but names no capability for setting `capability_ceiling`, no decision kind for an initial budget or a policy replacement, no authorization path for a `HumanDecision` recorded before any activation record exists, and no transition row for any of them. A project therefore cannot be provisioned by any specified operation. |
| Decision | Name the missing capability, the missing decision kinds, and the authorization path — **direct exercise** by the `HUMAN_PRINCIPAL`, recorded by the `HumanDecision` itself under `G-2` — and specify one transition row per governance-field write plus the initial `Project` state at creation. |
| Boundary | **Direct exercise is not a grant.** It confers nothing on any run. A run's authority still comes only from a `ContractActivationRecord` (`A-INV-2`, `AX-3`), and `capability_ceiling` still bounds every such grant (`AX-4`, `P-INV-2`). |
| Scope | The `Project` holder only: `capability_ceiling`, `budget`, `policy_digest`, `governance_mode`, and the field values a project is created with. No stage-, contract- or run-scope budget operation, no policy document content model, no new entity, no new lifecycle axis. |
| Compatibility | Normative additions and replacements are specified here only. No frozen document, schema file, or implementation is changed by this amendment. |

## 1. What the frozen design determines, and what it leaves open

| Frozen statement | What it settles | What it leaves unspecified |
|---|---|---|
| `authority-matrix.md` §2.1: `project.mode.set`, `policy.set`, `budget.grant`, `budget.extend` are `HUMAN`, grantable by `HUMAN_PRINCIPAL`, default `DENY` (lines 59, 63, 65, 66) | Who may ever perform these acts, and that each needs a `HumanDecision` at exercise time | No transition row names any of them as its `required_capability`; no row writes the field |
| `authority-matrix.md` §1: `PROJECT_CEILING` "cannot be widened by runtime or policy" (line 31); `domain-model.md` §2: `capability_ceiling` is `src = H` | That the ceiling is human-supplied and is not runtime- or policy-writable | No `CapabilityId`, no decision kind, no row — the one field the whole grant algebra is bounded by has no named operation |
| `domain-model.md` §9.A `decision_kind` enum (line 693) | `SET_MODE` for a mode change, `EXTEND_BUDGET` for a raise | No kind for an initial budget and none for a policy replacement |
| `authority-matrix.md` `AX-3` (line 14), §5 (line 241), §5.1 (line 263); `evidence-model.md` §2.2 (line 95) | How a decision's `grants` reach a run: per activation record, scoped to one run | What a `HumanDecision` is checked against when the act is on the project record and no contract, activation or run exists |
| `domain-model.md` `P-INV-1` (line 152); `transition-matrix.md` §9.3 (line 511) | A mode change needs `DEC(SET_MODE)`; `AUTONOMOUS` without a `HumanDecision` is illegal in both modes | The row that performs the change |
| `transition-matrix.md` §2, `PLANNING → ACTIVE` (line 88) | A project reaches `ACTIVE` only with a non-empty ceiling and a non-zero budget | What "non-zero" means dimension-wise, and how either value got there |

### 1.1 The contradiction in the current implementation

Verified by reading `src/gruntime/controller.py` and `src/gruntime/models.py` at this baseline. `create_project` (`controller.py:489`) takes `name`, `slug` and `workspace_root`, and no governance parameter.

| Observed | Frozen statement contradicted |
|---|---|
| `lifecycle=ProjectLifecycle.ACTIVE` (`controller.py:512`) | §2 has exactly one inbound `∅` row and it lands in `DRAFT`. There is no `∅ → ACTIVE` row, and §9.2 makes even `DRAFT → ACTIVE` `NONE_GRANTABLE`. The project skips `PLANNING → ACTIVE` and so is never tested against line 88. |
| `governance_mode=GovernanceMode.AUTONOMOUS` (`controller.py:514`), hardcoded, with no decision | §9.3 line 511: setting `AUTONOMOUS` without a `HumanDecision` is `NONE_GRANTABLE` in both modes; `P-INV-1`. |
| The same event records `capability_used="project.create"` (`controller.py:504`) | §3 mode gate: `project.create` is `DENY` in `AUTONOMOUS`. The project declares a mode in which its own creation capability is denied. |
| `capability_ceiling` takes the empty default (`models.py:914`) and `budget` the zero default (`models.py:915`, `Budget` dimensions default to `0` at `models.py:489–496`), on a project already `ACTIVE` | Line 88 requires a non-empty ceiling and a non-zero budget *before* `ACTIVE`. Additionally, every zero dimension satisfies §4's `NONE → SUSPENDED_BY_BUDGET` precondition (`budget_used ≥ budget`) at zero usage. |
| `created_by=_runtime_actor("controller")` (`controller.py:518`; `_runtime_actor` yields `ActorKind.RUNTIME` at `controller.py:177`) | `domain-model.md` §2 line 150: `created_by.actor_kind` MUST be `HUMAN`. §9.2 line 485 makes `∅ → DRAFT` with a non-human creator `NONE_GRANTABLE`. §2 line 84's precondition is not met. |
| `policy_digest` defaults to `None` (`models.py:913`) | `domain-model.md` §2 line 142: `policy_digest` is required (`req = Y`). |

These are statements about the implementation at this baseline, recorded because the amendment replaces the implementation's choices with specified ones (§6). This document specifies no code.

## 2. Authorization at provisioning time

This is the load-bearing section. The frozen design has one written authorization
path — resolution to a run's grant set — and provisioning happens before any run.

| Path | Actor | What records the authority | When it can exist |
|---|---|---|---|
| Delegated grant | kernel or worker acting within a run | `ContractActivationRecord.capability_grant_basis`, citing the `HumanDecision{GRANT_CAPABILITY}` that supplied each capability (`AX-3`, §5.1, `A-INV-3`) | only after a contract is activated for a run |
| Kernel self-held | the runtime kernel | none; `KERNEL` class is held by `RUNTIME_KERNEL`, non-delegable, never in `granted_capabilities` (`AX-7`) | always |
| **Direct exercise** (named by this amendment) | the `HUMAN_PRINCIPAL` itself | the `HumanDecision` for the act, cited as the event's `authority_ref` (`G-2`) | whenever the subject record exists, including `DRAFT` |

| id | Rule |
|---|---|
| `PP-1` | **Direct exercise already exists in the frozen design; it was never named.** `decision.record` and `project.create` are both `HUMAN` class with `HUMAN_PRINCIPAL` as their only grantor (§2.1, §2.7). `∅ → DRAFT` (§2) is a project's first transition, so no contract, activation or run can precede it; and every `DEC(K)` token in the matrix presupposes a decision recorded under `decision.record`, including `DRAFT → ABANDONED`. If a `HUMAN`-class capability could be conferred only through an activation record scoped to one run (`AX-3`), no project could be created and no decision could be recorded, so no run could ever exist and `AX-3` would have nothing to bound. The frozen design therefore requires this path by construction. |
| `PP-2` | **The decision is the authority record.** `G-2` admits `HumanDecision` as `required_capability` authority alongside `ContractActivationRecord`, with no activation-record precondition on the first member. For a direct exercise the two halves are: the §2 register row is the *standing* authority — who may ever perform this act — and the `HumanDecision` is the *per-act* authorization, naming this project, this kind, this evidence, this nonce. Both are required; neither substitutes for the other (`AX-9`). |
| `PP-3` | **Reconciliation with `evidence-model.md` §2.2 (line 95).** That row governs `HumanDecision.grants` — the capabilities a decision confers on *another* actor — and says those are realized only through an activation record. A provisioning decision has `grants = ∅` and `revokes = ∅`: it delegates nothing, so there is nothing for an activation record to realize. `SET_CEILING` changes the bound on future grants and is not itself a grant (`AX-11`: bounding is not granting). The row is unchanged and still governs every decision that does carry `grants`. |
| `PP-4` | **The ceiling does not bound direct exercise.** `PROJECT_CEILING` "bounds all other grantors" (§1) and `AX-4` bounds `granted`; both are about grants. If the ceiling bounded direct exercise, `project.ceiling.set` could never be exercised on a project whose ceiling is `∅` — which is every project at creation — and `project.create` could never be exercised at all, there being no project and therefore no ceiling to check against. What bounds direct exercise instead is `PP-5`. |
| `PP-5` | **What bounds a direct exercise**, in order: (i) the §2 register row — the capability exists, its class is `HUMAN`, and its `grantable by` column names `HUMAN_PRINCIPAL`; (ii) the §3 mode gate, read against `governance_mode` as it stands *before* the transition; (iii) the per-act admissibility table below; (iv) the row's own preconditions in §5; (v) the payload predicate for the field being written (§5.1). A capability failing any of these is denied and the denial is audited (`AX-1`, `AX-8`). |
| `PP-6` | **No self-authorization.** `RUNTIME_KERNEL` grants `KERNEL` capabilities to itself only and "cannot self-grant non-`KERNEL` capabilities" (§1). An `AuditEvent` whose `capability_used` is one of the four project-governance capabilities and whose `actor.actor_kind` is `RUNTIME`, `WORKER` or `ADAPTER` is an integrity violation, not a transition. The kernel is the *writer* of the `Project` record — it owns state transitions — but the actor of record is the deciding principal, and the kernel performs the write only against an admissible decision. |
| `PP-7` | **One decision, one field, one write.** The nonce consumption (`VALID → CONSUMED`, §7.5), the field write, and the `AuditEvent` persist atomically. A decision cannot be consumed without its effect landing, and a governance field cannot change without its decision being spent. This is the same atomicity `CLAUDE.md` records for suspension evidence, applied to provisioning. |
| `PP-8` | **`∅ → DRAFT` cannot be decision-gated, and needs no amendment to become so.** `domain-model.md` §9.A requires `HumanDecision.project_id : Ref<Project>` under referential integrity, so no decision can name a project that does not yet exist. The frozen row is correspondingly `AUTO`, and its authority is the authenticated creating principal carried in `created_by` and in the event's `actor`. This is why the row's only authority check is `created_by.actor_kind = HUMAN` (§9.2 line 485) — a check that is meaningless unless direct exercise is a real path. |

### 2.1 Admissibility of a provisioning decision

The project-scope analogue of `authority-matrix.md` §5. It resolves one capability
for one act, not a set for a run; there is no `capability_request`, no role, and no
activation record to write.

| step | check | frozen basis |
|---|---|---|
| 1 | the capability is registered, its class is `HUMAN`, and §2.1 names `HUMAN_PRINCIPAL` in its `grantable by` column | `AX-2`, `AX-5`, §2.1 |
| 2 | `decision.decided_by.actor_kind = HUMAN` with `principal_key_id` present, `auth_method ∈ {SESSION, SIGNATURE, MTLS}` equal to `decision.auth_method`, and `signature` present iff `SIGNATURE` | `HD-INV-1`, §1, §9.3 |
| 3 | `decision.project_id` is this project; `subject = {kind: PROJECT, id: project_id}`; `scope = PROJECT` | §9.A |
| 4 | `decision.decision_kind` equals the kind the row's `DEC(K)` names — not merely some kind of decision over this project | §1.1 verdict vocabulary |
| 5 | `evidence_shown` is non-empty and shows the current field value and the proposed one | `HD-INV-2`, §9.3 |
| 6 | `decision_state = VALID` at the instant of the transition, with the nonce unconsumed | `HD-INV-3`, `HD-INV-4`, §9.3 line 522 |
| 7 | `grants = ∅` and `revokes = ∅` | `PP-3`; a provisioning decision delegates nothing, so it never needs an activation record |
| 8 | the §3 mode gate permits the capability under `governance_mode` as it stands before this transition | §3 |
| 9 | the payload predicate for the target field holds (§5.1) | this amendment |
| 10 | consumption, field write and audit event are one atomic persistence | `PP-7`, `AE-INV-2` |

A decision that fails any step discharges nothing and is not consumed. Steps 1–8
are equally the check for `project.mode.set`, which the frozen design already
requires and never specified how to check.

### 2.2 `ProvisioningDecision` — a profile of `HumanDecision`, not a new entity

| Field | Required value | Why |
|---|---|---|
| `subject.kind` | `PROJECT` | the act is on the project record |
| `subject.id` | `project_id` | `PP-7` binds one decision to one project |
| `scope` | `PROJECT` | the act has no stage, run or single-action boundary to be scoped by |
| `decision_kind` | `SET_CEILING`, `GRANT_BUDGET`, `SET_POLICY`, `EXTEND_BUDGET` or `SET_MODE` | §4 |
| `grants` / `revokes` | `∅` / `∅` | `PP-3` |
| `snapshot_bound` | `false` (derived) | §4.1 |
| `subject_snapshot_id` | absent | required iff `snapshot_bound` (§9.A) |
| `evidence_shown` | non-empty | `HD-INV-2` |
| every other field | as `domain-model.md` §9.A | no schema change |

No entity is added. A rejected alternative was a `ProjectAuthorityRecord` mirroring
`ContractActivationRecord` at project scope: it would duplicate the decision's
content, introduce a second `AUTHORITY` record with no delegation to record, and
require its own expiry and revocation rules — while `G-2` already admits the
decision itself.

## 3. Capability register additions

Added to `authority-matrix.md` §2.1, in its own format.

| CapabilityId | permits | class | grantable by | default | mode restriction |
|---|---|---|---|---|---|
| `project.ceiling.set` (new) | replace `Project.capability_ceiling` | `HUMAN` | `HUMAN_PRINCIPAL` | `DENY` | both modes require `DEC(SET_CEILING)` |

The name parallels `project.mode.set`: the same subject, the same class, the same
grantor, the same shape of decision. `project.ceiling.set` is never grantable to a
worker (§4.1's `every HUMAN capability` row), is never held by the kernel
(`PP-6`), and is not itself bounded by the ceiling it writes (`PP-4`).

Added to the §3 mode gate, which today has a row for `project.mode.set` and none
for the other three; the catch-all rows cover `ORD`, `KERNEL` and `NEVER` classes
only, so these four had no gate row at all.

| CapabilityId | `SUPERVISED` | `AUTONOMOUS` |
|---|---|---|
| `project.ceiling.set` | `DEC(SET_CEILING)` | `DEC(SET_CEILING)` |
| `policy.set` | `DEC(SET_POLICY)` | `DEC(SET_POLICY)` |
| `budget.grant` | `DEC(GRANT_BUDGET)` | `DEC(GRANT_BUDGET)` |
| `budget.extend` | `DEC(EXTEND_BUDGET)` | `DEC(EXTEND_BUDGET)` |

Both columns are identical by §3's closing rule: `AUTONOMOUS` never widens the set
of `HUMAN`-class capabilities, it only removes per-action confirmation on `ORD`
ones. A project cannot relax its own provisioning by declaring itself autonomous.

## 4. Decision kinds

Added to the `domain-model.md` §9.A `decision_kind` enumeration.

| Kind | Names the act | Rejected reuse, and why |
|---|---|---|
| `SET_CEILING` | replace `capability_ceiling` | `GRANT_CAPABILITY`. Rejected: that kind means "this capability may be delegated to this run" and is the record `capability_grant_basis` cites. Widening the ceiling authorizes no one to do anything — it moves the bound future grants are checked against. Reusing one kind for both would collapse exactly the distinction `AX-11` and `A-INV-3` exist to draw, and would let a ceiling decision be mistaken for a grant at §5.1 step 6. |
| `GRANT_BUDGET` | set the initial `Budget` | `EXTEND_BUDGET`. Rejected: `DEC(EXTEND_BUDGET)` is the token that clears `SUSPENDED_BY_BUDGET` (§4) and directs rework at `AWAITING_DECISION → RUNNING` (§3). Those rows check the kind. One kind would make a decision recorded to provision a new project indistinguishable, at the point of check, from one recorded to lift a budget suspension on a live one. The register already separates the capabilities (`budget.grant` "set initial `Budget`" versus `budget.extend` "raise a ceiling on a live project or run"); the decision kinds follow that separation. |
| `SET_POLICY` | replace the policy document and `policy_digest` | `APPROVE`. Rejected: `snapshot_bound` is derived `true` for `decision_kind ∈ {APPROVE, WAIVE, ACCEPT_RISK, OVERRIDE, REJECT}` (§9.A line 702), so an `APPROVE` would require a `COMPLETE` workspace snapshot and would go `STALE` on any workspace drift (`HD-INV-4`). A policy replacement is a statement about the policy document, not about the workspace; binding it to a tree digest would make governance unsettable on a busy project. |

`SET_MODE` and `EXTEND_BUDGET` are reused unchanged; both already exist and both
already appear as `DEC(K)` tokens in frozen rows.

### 4.1 `snapshot_bound` derivation

`domain-model.md` §9.A already excludes `SET_MODE`, `SUSPEND`, `RESUME`,
`ABANDON`, `EXTEND_BUDGET`, `GRANT_CAPABILITY` and `REVOKE_CAPABILITY` over a
`PROJECT` or `CAPABILITY` subject. The derivation is extended so that
`SET_CEILING`, `GRANT_BUDGET` and `SET_POLICY` over a `PROJECT` subject are
likewise **not** snapshot-bound, for the same stated reason: these decisions speak
about the project record, not about the state of the workspace. Their currency is
governed by `expires_at`, `scope` and the nonce alone. `HD-INV-4` is unchanged and
continues to stale every decision that *is* snapshot-bound.

## 5. Transition rows

A new subsection `transition-matrix.md` §7.7, **Project governance fields**, in the
matrix's own format. `illegal_because` is omitted: every row here is legal.
`from_state` and `to_state` name the value of the field the row writes; these are
field writes on the `Project` record, not a fourth state axis (`O-1`, §10.4).

Every row additionally requires: `project.lifecycle ∉ {COMPLETED, ARCHIVED,
ABANDONED}`; the §2.1 admissibility table passes; and `PP-7` atomicity. `C` denotes
the current `capability_ceiling`, `B` the current `budget`, `H` the current
`policy_digest`.

| Field: from → to | preconditions | required_evidence | required_capability | supervised_policy | autonomous_policy |
|---|---|---|---|---|---|
| `capability_ceiling`: `C → C'`, `C' \ C ≠ ∅` (widening) | `project.suspension = NONE`; `C'` well-formed per §5.1; alters no minted `ContractActivationRecord` and no `StageRun.effective_capabilities` | `DEC(SET_CEILING)` | `project.ceiling.set` | `DECIDE(SET_CEILING)` | `DECIDE(SET_CEILING)` |
| `capability_ceiling`: `C → C'`, `C' ⊊ C` (narrowing) | `project.suspension ≠ SUSPENDED_BY_INTEGRITY`; `C'` well-formed per §5.1; takes effect on future activations only (`AX-10`) | `DEC(SET_CEILING)` | `project.ceiling.set` | `DECIDE(SET_CEILING)` | `DECIDE(SET_CEILING)` |
| `budget`: `0⃗ → B'` (initial grant) | `project.lifecycle ∈ {DRAFT, PLANNING}`; `project.suspension = NONE`; `budget` is the zero vector and `budget_used` is the zero vector; every dimension of `B'` is `> 0` (§5.1) | `DEC(GRANT_BUDGET)` | `budget.grant` | `DECIDE(GRANT_BUDGET)` | `DECIDE(GRANT_BUDGET)` |
| `budget`: `B → B'` (extension) | `project.lifecycle ∈ {PLANNING, ACTIVE, SETTLING}`; `project.suspension ∈ {NONE, SUSPENDED_BY_BUDGET}`; `B'ᵢ ≥ Bᵢ` for every dimension and `B' ≠ B` | `DEC(EXTEND_BUDGET)` | `budget.extend` | `DECIDE(EXTEND_BUDGET)` | `DECIDE(EXTEND_BUDGET)` |
| `policy_digest`: `H → H'` | `project.suspension = NONE`; `H'` is the digest of a persisted, human-authored policy document artifact; `H' ≠ H`; pins nothing already activated (`ContractActivationRecord.policy_digest` is immutable) | `DEC(SET_POLICY)` | `policy.set` | `DECIDE(SET_POLICY)` | `DECIDE(SET_POLICY)` |
| `governance_mode`: `SUPERVISED → AUTONOMOUS` | `project.suspension = NONE`; no non-terminal `StageRun` in the project; `policy_digest` present | `DEC(SET_MODE)` | `project.mode.set` | `DECIDE(SET_MODE)` | `DECIDE(SET_MODE)` |
| `governance_mode`: `AUTONOMOUS → SUPERVISED` | `project.suspension ≠ SUSPENDED_BY_INTEGRITY` | `DEC(SET_MODE)` | `project.mode.set` | `DECIDE(SET_MODE)` | `DECIDE(SET_MODE)` |

The suspension columns follow one rule: **a governance write that can only reduce
authority is permitted while suspended; one that can increase it is not.** Ceiling
narrowing and `AUTONOMOUS → SUPERVISED` reduce; ceiling widening, the initial
budget grant, a policy replacement and `SUPERVISED → AUTONOMOUS` increase. Nothing
is permitted under `SUSPENDED_BY_INTEGRITY` (§9.2: no state written under an
untrusted chain is meaningful). The budget extension is the one increase permitted
under a suspension, and only under the suspension it exists to lift.

`SUPERVISED → AUTONOMOUS` requires no live run because a mode change is the one
authority change that reaches a run without a new activation: transition rows read
`project.governance_mode` to select their verdict column, so a mid-run relaxation
would remove a live run's `CONFIRM` gates — the effect `RUN-INV-2` and §9.3 forbid
for capabilities. `AUTONOMOUS → SUPERVISED` adds confirmations and needs no such
precondition.

### 5.1 Payload predicates

| Field | Predicate | Derivation |
|---|---|---|
| `capability_ceiling` | every member is a `CapabilityId` registered in `authority-matrix.md` §2 whose class is `ORD` or `HUMAN`. A `NEVER` member is refused (`AX-6`); a `KERNEL` member is refused (`AX-7`, §5 step 5 — it can never appear in `granted_capabilities`, so admitting it into the bound states an authority that cannot exist). The empty set is well-formed and means the project may delegate nothing. | `AX-6`, `AX-7`; the `KERNEL` exclusion is a design choice, §8 |
| `budget` at `budget.grant` | every dimension `> 0` | §4's `NONE → SUSPENDED_BY_BUDGET` precondition is `any budget_used field ≥ its budget ceiling`; with a zero dimension that holds at zero usage, so a project granted a budget with any zero dimension is suspended from its first evaluation. This also fixes the meaning of "`budget` non-zero" in §2 line 88: every dimension, not some dimension. |
| `budget` at `budget.extend` | no dimension decreases; at least one increases | `budget.extend` "raises a ceiling" (§2.1); lowering is not an extension and is out of scope (§8) |
| `policy_digest` | equals the artifact-store digest of a persisted policy document (`evidence-model.md` §1.1); the document is human-authored (§1, `POLICY_ENGINE` row) | §1, §2.1 |

A policy write always requires `suspension = NONE`, in both directions, because the
runtime does not compare two policy documents for monotonicity: it cannot know
whether a replacement widens or narrows, so it must treat every replacement as a
widening.

### 5.2 Consequences for frozen rules

| Frozen rule | Reading under this amendment |
|---|---|
| `P-INV-2`, "no grant anywhere in the project may exceed `capability_ceiling`" | Evaluated **at grant time**, against the ceiling in force at activation, and pinned there by `capability_grant_basis`. A later narrowing does not retroactively invalidate a minted activation record or a frozen `StageRun.effective_capabilities`; that would be a retroactive revocation, which `AX-10` forbids, and an in-place change to a live run's authority, which §9.3 forbids. To stop a live run, the frozen mechanisms are `contract.revoke` and `suspension.set`. |
| §4, `SUSPENDED_BY_BUDGET → NONE` | Becomes reachable. Its precondition, "budget extended so every dimension has headroom", presupposes an extension operation that the frozen matrix never specified; the extension row above is that operation. |
| `HD-INV-3`, single consumption | One `DEC(EXTEND_BUDGET)` discharges the extension row **and** the `SUSPENDED_BY_BUDGET → NONE` row it makes satisfiable, consumed once, both transitions persisting atomically with the consumption and each emitting its own `AuditEvent`. This is a narrow exception for this pair only: the clearing is the mechanical consequence of the human's act, and the alternative — two decisions for one act — leaves the project suspended by a cause that demonstrably no longer holds until a second human round-trip. `HD-INV-3` is otherwise unchanged: no decision discharges two unrelated transitions, and none is replayed across runs. |
| §2, `PLANNING → ACTIVE` | Unchanged and now satisfiable by specified operations: the ceiling row and the budget-grant row are the only ways its two preconditions can be met. |

## 6. Specified initial `Project` state

The value of every `domain-model.md` §2 field at `∅ → DRAFT`. This replaces the
implementation's choices recorded in §1.1; it is not a schema change.

| Field | Value at creation | Basis |
|---|---|---|
| `project_id` | fresh `Id` | §2 |
| `name`, `slug`, `workspace_root` | human-supplied; `workspace_root` exists | §2 (`src = H`), §2 row precondition |
| `schema_version` | the runtime's domain-model version | §2 |
| `lifecycle` | `DRAFT` | §2 has one inbound `∅` row and it lands in `DRAFT`; `ACTIVE` is reachable only through `PLANNING` |
| `suspension` | `NONE`; `suspension_ref` absent | §2 field table: `suspension_ref` required iff `suspension ≠ NONE` |
| `governance_mode` | **`SUPERVISED`** | Derived, not chosen: §3 makes `project.create` `DENY` in `AUTONOMOUS`, so no project can be created in autonomous mode; and §9.3 line 511 forbids `AUTONOMOUS` without a `HumanDecision`, which `PP-8` shows cannot exist at creation. `SUPERVISED` is the only legal initial value. |
| `capability_ceiling` | `∅` | `AX-1` default `DENY`; the ceiling is human-supplied and no decision can precede the project (`PP-8`). It stays `∅` until the §5 ceiling row runs. |
| `policy_digest` | the digest of the **canonical empty policy document**: a well-formed document containing no rules, whose `POLICY_GRANTABLE` set is empty | The field is required (`req = Y`), so it cannot be absent; and under `AX-1` "no policy" and "a policy that grants nothing" must be the same thing, so they are the same document. |
| `budget` | the zero `Budget` | Correct as an initial value: `budget.grant` "sets the initial `Budget`", so there is one to replace. A zero budget is why a `DRAFT` project can do nothing. |
| `budget_used` | the zero `BudgetUsage` | `D`/`A`, runtime-derived from receipts |
| `event_head`, `event_seq` | the genesis event's `event_hash`, and `0` | `evidence-model.md` §3.1 step 5 |
| `controller_epoch` | `0`; the first controller start raises it to `≥ 1` before any work | `P-INV-4`. No dispatch or apply may be initiated under epoch `0`. |
| `snapshot_current` | the `snapshot_id` of the `SNAP` the `∅ → DRAFT` row cites as `required_evidence` | §2 line 84 requires that snapshot to exist; `snapshot_current` is the derived newest snapshot, so it is that one |
| `created_at`, `updated_at` | creation instant | §2 |
| `created_by` | the authenticated `HUMAN` principal performing the creation, with `principal_key_id` and `auth_method ∈ {SESSION, SIGNATURE, MTLS}` | §2 line 150; §9.2 line 485 makes any other creator `NONE_GRANTABLE` |

A project created this way can do nothing until a human sets a ceiling and grants a
budget. That is the intended reading of `AX-1`: the provisioned state is the
permissive one, and it is reached by named, decided, audited operations.

## 7. Audit and event shape

| Rule | Required behavior |
|---|---|
| `PP-9` | Each §5 row emits one `AuditEvent` with `epistemic_class = AUTHORITY`, `event_type = project.<field>.set`, `actor` = the decision's `decided_by`, `capability_used` = the row's `required_capability`, and `authority_ref = decision_id`. `subject = {kind: "project", id: project_id}`. The payload records the previous and new field values. |
| `PP-10` | `evidence-model.md` §3.3's authority-binding check — "every event with `capability_used` has an `authority_ref` resolving to a live grant at `recorded_at`" — resolves, for a direct exercise, to the `HumanDecision`, which must be `VALID` at `recorded_at`. Its subsequent transition to `CONSUMED` in the same atomic write does not fail the check: the check is evaluated at `recorded_at`, and a decision consumed *by* the event it authorized is the expected outcome. |
| `PP-11` | `∅ → DRAFT` is the sole event whose `capability_used` has no `authority_ref`, because no decision can name a project that does not yet exist (`PP-8`). Its authority binding is satisfied by `actor` being an authenticated `HUMAN` with `principal_key_id` and `auth_method ≠ NONE`, equal to `created_by`. |
| `PP-12` | The `AuditEvent` precedes observability of the new field value (`AE-INV-2`), and the nonce consumption, field write and event are one persistence (`PP-7`). A crash leaves either the whole provisioning act or none of it. |
| `PP-13` | A denied provisioning attempt emits an `AuditEvent` with `epistemic_class = AUTHORITY` recording the failed step of §2.1 (`AX-8`: silent denial is a defect). |

Provisioning initiates no effect outside the kernel's own store, so `G-9`,
`RUN-INV-3` and the reconciliation machinery do not apply to these rows: there is
no provider call and no repository mutation to make durable in advance.

## 8. Design choices and what is left unspecified

| Choice | Alternative rejected |
|---|---|
| `project.ceiling.set` as the identifier | `project.capability_ceiling.set` (exact field name, but no other register row spells a field in full) and `ceiling.set` (drops the subject that every project-governance identifier carries) |
| Three new decision kinds rather than reuse | §4 records the rejected reuse and the reason for each |
| No new entity; the `HumanDecision` is the authority record | A `ProjectAuthorityRecord` mirroring `ContractActivationRecord` at project scope (§2.2) |
| A `KERNEL` member in a ceiling is refused | Accepting any registered identifier and letting §5 step 5 drop the non-grantable ones. Rejected: the ceiling would then state an authority that can never be granted, and a reader could not tell an over-broad ceiling from an ordinary one. |
| Narrowing does not revoke live grants (`P-INV-2` at grant time) | Forbidding a narrowing while any non-terminal `StageRun` exists. Rejected: it makes containment hostage to a running worker, precisely when narrowing is most needed, and the frozen design already supplies `contract.revoke` and `suspension.set` for stopping live work. |
| One `DEC(EXTEND_BUDGET)` covers the extension and the suspension clearing | Two decisions. Rejected in §5.2. |
| `SUPERVISED → AUTONOMOUS` requires no non-terminal run | Permitting it mid-run and letting each transition read the current mode. Rejected: a live run's supervised confirmations would vanish without a new activation. |
| A policy write always requires `suspension = NONE` | Permitting a "narrowing" policy write under suspension. Rejected: the runtime cannot decide whether one policy document is narrower than another. |
| The canonical empty policy document as the initial `policy_digest` | Making `policy_digest` optional. Rejected: the field is required in the frozen table, and an absent policy and a policy granting nothing must not be two different states. |

Left unspecified, deliberately:

| Not specified | Why |
|---|---|
| Lowering a live `budget` | No register capability permits it, and lowering below `budget_used` would manufacture retroactive exhaustion. A project whose budget must shrink is suspended or abandoned by frozen means. |
| Run- and contract-scope budget extension | `budget.extend` names "a live project or run"; this amendment specifies the `Project` holder only. The run-scope row remains open. |
| The policy document's content model beyond `POLICY_GRANTABLE` | The frozen design reads only that set (§1, §5.1); specifying more would invent policy semantics no frozen rule consumes. |
| `budget_used` accumulation from execution | An extension is only meaningful against accrued usage. That accrual is an implementation gap recorded as `FINDINGS-02` F02-007, not a design gap: `domain-model.md` §1.3 already specifies usage as derived from receipts. |
| Any implementation | This document states what must be true. |

## 9. Statements in `design-01-frozen` amended and left untouched

Only the named deltas below supersede or extend frozen statements. All other
DESIGN-01 statements remain in force; the frozen files themselves remain unchanged.

| Frozen source / statement | Amendment |
|---|---|
| `authority-matrix.md` §2.1 register | Adds `project.ceiling.set` (§3). The four existing project-governance rows are unchanged. |
| `authority-matrix.md` §3 mode gate | Adds rows for `project.ceiling.set`, `policy.set`, `budget.grant`, `budget.extend`; all `DECIDE(K)` in both modes, per §3's own closing rule (§3) |
| `authority-matrix.md` `AX-3`, §5, §5.1 | Scoped explicitly to **delegated** grants to a run. Direct exercise by the `HUMAN_PRINCIPAL` is the separate path, with its own admissibility table and no activation record (§2, §2.1) |
| `authority-matrix.md` §1 `PROJECT_CEILING`, `AX-4`, `AX-11` | Unchanged as bounds on grants; stated not to bound a direct exercise, which is not a grant (`PP-4`) |
| `authority-matrix.md` §6 enforcement points | Adds a project-scope enforcement point: the §2.1 admissibility table, checked at the moment of the field write (§2.1, §7) |
| `domain-model.md` §2 `Project` field table | No field, type, mutability or `src` changes. Names the operation and transition by which each `src = H` governance field is supplied (§5), and fixes the value of every field at creation (§6) |
| `domain-model.md` `P-INV-1` | Unchanged; §5 supplies the two missing rows that carry `DEC(SET_MODE)` |
| `domain-model.md` `P-INV-2` | Read as a constraint on the act of granting, evaluated against the ceiling in force at activation; narrowing is not retroactive (§5.2) |
| `domain-model.md` §9.A `decision_kind` enum | Adds `SET_CEILING`, `GRANT_BUDGET`, `SET_POLICY` (§4) |
| `domain-model.md` §9.A `snapshot_bound` derivation | The three new kinds over a `PROJECT` subject are not snapshot-bound, for the reason the existing exclusions give (§4.1) |
| `domain-model.md` `HD-INV-3` | One narrow exception: a single `DEC(EXTEND_BUDGET)` discharges the extension and the `SUSPENDED_BY_BUDGET → NONE` it enables, atomically (§5.2) |
| `transition-matrix.md` §7 | Adds §7.7, seven rows over `Project` governance fields (§5). These are field writes, not a state axis (`O-1` holds) |
| `transition-matrix.md` §2 `PLANNING → ACTIVE` | Row unchanged; "`budget` non-zero" is defined as every dimension `> 0`, derived from §4's budget-suspension precondition (§5.1) |
| `transition-matrix.md` §4 `SUSPENDED_BY_BUDGET → NONE` | Row unchanged and now reachable: the extension operation its precondition presupposes is specified (§5, §5.2) |
| `evidence-model.md` §2.2 `DECISION → AUTHORITY` | Scoped explicitly to `HumanDecision.grants`; a decision carrying no grants delegates nothing and needs no activation record (`PP-3`) |
| `evidence-model.md` §3.3 authority binding | For a direct exercise, `authority_ref` resolves to the `HumanDecision` valid at `recorded_at`; `∅ → DRAFT` is the sole event with no `authority_ref`, its binding satisfied by an authenticated `HUMAN` actor (`PP-10`, `PP-11`) |

| Frozen source / statement | Left untouched |
|---|---|
| `authority-matrix.md` `AX-1`, `AX-2`, `AX-5`–`AX-11`; §4, §4.1, §4.2 role tables and constraints | Default deny, one capability per operation, non-delegation, kernel confinement, denial recording, revocation semantics, and every worker grant. No worker gains any project-governance capability |
| `authority-matrix.md` §5 steps 1–9; §5.1 admissible grantors; `A-INV-1`–`A-INV-3` | The run-grant resolution algorithm, `capability_grant_basis`, and the rule that ceiling membership grants nothing are unchanged and still govern every run |
| `domain-model.md` `HD-INV-1`, `HD-INV-2`, `HD-INV-4`; `transition-matrix.md` §7.5 | Human authentication, mandatory `evidence_shown`, staleness of snapshot-bound decisions, and the decision-state machine. `decision.record` remains `AUTO` in both modes |
| `domain-model.md` `RUN-INV-1`–`RUN-INV-3`, `C-INV-1`–`C-INV-3`, `S-INV-*`, `W-INV-*`, `V-INV-*`, `RA-INV-*`, `CM-INV-*`, `G-1`, `G-3`–`G-10` | Run, contract, stage, worker, validation, review and commit semantics. `G-2` is relied on, not changed |
| `transition-matrix.md` §0–§6, §7.1–§7.6, §8, §9 | The three axes, their gates, every lifecycle row, every subordinate state machine, the composition table and the whole illegal section. In particular line 511 is satisfied by the mode rows, not amended, and line 500's ban on widening `effective_capabilities` in place is preserved by §5.2 |
| `evidence-model.md` §1, §2.1, §2.3, §3.1–§3.2.1, §4–§7 | Artifact store, record classification, promotion rules, chain construction and append protocol, external-effect ordering, satisfaction derivation, currency, retention and export |
| `worker_provider.md`, `roadmap_adapter.md`, `schema/*`, frozen `design/review/*` | No provider, adapter, schema or historical review record is affected |
| `design/DESIGN-02-candidate-observation.md` | No interaction. DESIGN-03 adds no candidate, materialization or commit rule, and DESIGN-02 adds no project-governance rule |

## 10. Entry required in `CLAUDE.md`

This document does not edit `CLAUDE.md`. The "Design baseline" section needs an
entry reading:

> DESIGN-03 records a proposed amendment as a design document only — not yet
> reflected in frozen text and not implemented. It names the authorization path
> for project provisioning (`PP-1`..`PP-13`), adds the capability
> `project.ceiling.set` and the decision kinds `SET_CEILING`, `GRANT_BUDGET` and
> `SET_POLICY`, adds transition-matrix §7.7 (seven rows over `Project` governance
> fields), and specifies the initial `Project` state at creation. It amends:
> - `evidence-model.md:95` — scopes `DECISION → AUTHORITY` to `HumanDecision.grants`
> - `authority-matrix.md:14` (`AX-3`) — scopes per-activation grants to delegation
> - `domain-model.md:153` (`P-INV-2`) — ceiling checked at grant time, not retroactively
> - `domain-model.md:693` — three added decision kinds
>
> The current `create_project` (`controller.py:489`) contradicts the frozen design
> in six respects recorded in DESIGN-03 §1.1: it enters `ACTIVE` directly, sets
> `AUTONOMOUS` with no decision, leaves the ceiling empty and the budget zero,
> names a `RUNTIME` creator, and leaves `policy_digest` absent. Until DESIGN-03's
> edits land in the frozen files, `design-01-frozen` remains the authoritative
> baseline and the amendment lives only in
> `design/DESIGN-03-project-provisioning.md`.
