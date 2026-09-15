# DESIGN-03 — Project Provisioning (revision 02)

Revises `design/DESIGN-03-project-provisioning.md` against
`design/review/DESIGN-03-FINDINGS-01.md`. The reviewed draft is committed
evidence and is unchanged; this document replaces it as the amendment. Where the
two differ, this one governs.

| Property | Amendment |
|---|---|
| Baseline | `design-01-frozen`; this document is the amendment, not a replacement of that baseline. `DESIGN-02` is unaffected and unreferenced by any rule here. |
| Gap | The frozen design registers `project.mode.set`, `policy.set`, `budget.grant` and `budget.extend` as `HUMAN` capabilities ([authority-matrix.md:59](authority-matrix.md#L59), [:63](authority-matrix.md#L63), [:65](authority-matrix.md#L65), [:66](authority-matrix.md#L66)) and requires `DEC(SET_MODE)` for a mode change ([domain-model.md:152](domain-model.md#L152)), but names no capability for setting `capability_ceiling`, no decision kind for an initial budget or a policy replacement ([domain-model.md:693](domain-model.md#L693)), no authorization path for a `HumanDecision` recorded before any activation record exists, and no transition row for any of them. A project cannot be provisioned by any specified operation. |
| Decision | Specify the missing capability, the missing decision kinds, the authorization path — **direct exercise** by the `HUMAN_PRINCIPAL`, a path the frozen design requires and does not specify — one transition row per governance-field write, and the initial `Project` state at creation. |
| Boundary | **Direct exercise is not a grant and is not `AUTHORITY` class.** It confers nothing on any run, and it is unbounded by `capability_ceiling` for exactly the five capabilities in §3 and §5 — no others. A run's authority still comes only from a `ContractActivationRecord` ([domain-model.md:410](domain-model.md#L410)), bounded by the ceiling ([authority-matrix.md:15](authority-matrix.md#L15)). |
| Scope | The `Project` holder only: `capability_ceiling`, `budget`, `policy_digest`, `governance_mode`, and the values a project is created with. No stage- or run-scope budget operation, no policy document content model, no new entity, no new lifecycle axis, and no path for any other `HUMAN`-class capability. |
| Compatibility | Every frozen statement this amendment supersedes, extends or reads narrowly is named in §9 with `file:line`. No frozen document, schema file, or implementation is changed by this amendment. |

### Disposition of `DESIGN-03-FINDINGS-01`

| id | Disposition |
|---|---|
| `-001` | Closed. `PP-4` scoped to the five capabilities; direct exercise of every other `HUMAN` capability is declared out of scope and left ceiling-bounded (§2, `PP-4`). |
| `-002` | Closed. The axis-3 gate gains an explicit column, listed in §9 as extended; the rule behind it is labelled DESIGN-03's, not the frozen design's (§5.3). |
| `-003` | Closed by the review's alternative, not by an exception. `HD-INV-3` is untouched; the frozen §4 row is amended instead, with a predicate naming holder, event and capability (§5.2). |
| `-004` | Closed. `PP-8`'s `Ref<Project>` argument is withdrawn and replaced by atomic creation over an allocated `project_id`; `event_seq = 1`, `event_head` = the creation event's hash (`PP-8`, §6). |
| `-005` | Closed. No runtime-fabricated policy document. The initial policy document is supplied by the creating human; the register's verb "replace" is what leaves the initial one to the creating act (§5.1, §6). |
| `-006` | Closed. §1.1's charge restated: the defect is a zero budget **on an `ACTIVE` project**, not at `DRAFT`. §6 keeps the zero `Budget` and states the frozen guard that makes it safe (§1.1, §6). |
| `-007` | Closed by `evidence_shown` content rather than a new `EscalationTrigger`: the narrowing decision must show the live activations the new ceiling excludes (§5, §5.1). Residual risk recorded (§8). |
| `-008` | Closed. Premise corrected and the precondition strengthened to cover `CONTRACTED` stages and minted activations (§5). |
| `-009` | Closed by option two: the provisioning events are `DECISION` class; [evidence-model.md:65](evidence-model.md#L65), [:82](evidence-model.md#L82), [:84](evidence-model.md#L84) and [:95](evidence-model.md#L95) are untouched for them, and only [:176](evidence-model.md#L176) is amended (`PP-3`, `PP-10`). |
| `-010` | Closed. `PP-1` claims necessity, not recovery. |
| `-011` | Closed. Identity is forced for `project.mode.set` ([authority-matrix.md:59](authority-matrix.md#L59)) and chosen for the other four (§3). |
| `-012` | Closed. §4.1 deleted; no `snapshot_bound` amendment is needed or claimed. |
| `-013` | Closed. `roadmap_id` added to §6. |
| `-014` | Closed. `controller_epoch = 1`, labelled a choice; the invented epoch-0 rule is deleted. |
| `-015` | Closed. `capability_ceiling = ∅` relabelled a choice on the `AX-2`/`G-4` basis the review supplies. |
| `-016` | Closed. Every basis cell carries `file:line`. |
| `-017` | Closed. Reachability qualified to the `Project` holder; the run-holder gap is recorded as frozen and deferred (§5.2, §8). |

## 1. What the frozen design determines, and what it leaves open

| Frozen statement | What it settles | What it leaves unspecified |
|---|---|---|
| `project.mode.set`, `policy.set`, `budget.grant`, `budget.extend` are `HUMAN`, grantable by `HUMAN_PRINCIPAL`, default `DENY` ([authority-matrix.md:59](authority-matrix.md#L59), [:63](authority-matrix.md#L63), [:65](authority-matrix.md#L65), [:66](authority-matrix.md#L66)) | Who may ever perform these acts | No transition row names any of them as `required_capability`; no row writes the field |
| `capability_ceiling` is `src = H`, "upper bound on all grants" ([domain-model.md:141](domain-model.md#L141)); `PROJECT_CEILING` "cannot be widened by runtime or policy" ([authority-matrix.md:31](authority-matrix.md#L31)) | The ceiling is human-supplied and not runtime- or policy-writable | No `CapabilityId`, no decision kind, no row. The field the whole grant algebra is bounded by ([authority-matrix.md:15](authority-matrix.md#L15)) has no named operation |
| `decision_kind` is a closed enumeration ([domain-model.md:693](domain-model.md#L693), [:37](domain-model.md#L37)) with `SET_MODE` and `EXTEND_BUDGET` | The kinds for a mode change and a raise | No kind for an initial budget, none for a policy replacement |
| `AX-3` scopes grants per activation record to one run ([authority-matrix.md:14](authority-matrix.md#L14)); §5 resolves a contract's request ([authority-matrix.md:239](authority-matrix.md#L239)–[:253](authority-matrix.md#L253)); §5.1 lists admissible grantors ([authority-matrix.md:261](authority-matrix.md#L261)–[:267](authority-matrix.md#L267)) | How a decision's `grants` reach a run | What a `HumanDecision` is checked against when the act is on the project record and no contract, activation or run exists |
| `P-INV-1` ([domain-model.md:152](domain-model.md#L152)); `AUTONOMOUS` without a `HumanDecision` is illegal ([transition-matrix.md:511](transition-matrix.md#L511)) | A mode change needs `DEC(SET_MODE)` | The row that performs the change |
| `PLANNING → ACTIVE` requires "`capability_ceiling` non-empty and `budget` non-zero" ([transition-matrix.md:88](transition-matrix.md#L88)) | A project reaches `ACTIVE` only with both | What "non-zero" means dimension-wise, and how either value got there |

### 1.1 The contradiction in the current implementation

Verified by reading `src/gruntime/controller.py` and `src/gruntime/models.py` at
this baseline. `create_project` (`controller.py:489`) takes `name`, `slug` and
`workspace_root`, and no governance parameter.

| Observed | Frozen statement contradicted |
|---|---|
| `lifecycle=ProjectLifecycle.ACTIVE` (`controller.py:512`) | §2 has one inbound `∅` row and it lands in `DRAFT` ([transition-matrix.md:84](transition-matrix.md#L84)). There is no `∅ → ACTIVE` row, and even `DRAFT → ACTIVE` is `NONE_GRANTABLE` ([transition-matrix.md:481](transition-matrix.md#L481)). The project never passes `PLANNING → ACTIVE`, so [transition-matrix.md:88](transition-matrix.md#L88) is never evaluated. |
| `governance_mode=GovernanceMode.AUTONOMOUS` (`controller.py:514`), hardcoded, no decision | [transition-matrix.md:511](transition-matrix.md#L511); `P-INV-1` ([domain-model.md:152](domain-model.md#L152)) |
| The same event records `capability_used="project.create"` (`controller.py:504`) | `project.create` is `DENY` in `AUTONOMOUS` ([authority-matrix.md:157](authority-matrix.md#L157), [transition-matrix.md:84](transition-matrix.md#L84)). The project declares a mode in which its own creation capability is denied. |
| Empty `capability_ceiling` (`models.py:914`) on a project already `ACTIVE` | [transition-matrix.md:88](transition-matrix.md#L88) is bypassed, and §5 step 2 denies every requested capability `NOT_IN_CEILING` ([authority-matrix.md:242](authority-matrix.md#L242)), so no contract can be activated: the project is `ACTIVE` and inert. |
| Zero `Budget` (`models.py:915`; dimensions default to `0` at `models.py:489–496`) on a project already `ACTIVE` | [transition-matrix.md:88](transition-matrix.md#L88) is bypassed; and once `ACTIVE`, the first `WR` or `VR(any)` usage record makes `NONE → SUSPENDED_BY_BUDGET` takeable, since `budget_used ≥ budget` holds for every zero dimension at zero usage ([transition-matrix.md:159](transition-matrix.md#L159)). **The charge is the value on an `ACTIVE` project, not the value itself**: at `DRAFT` or `PLANNING` that row's `required_evidence` cannot exist, because no worker may be dispatched ([transition-matrix.md:435](transition-matrix.md#L435)). §6 therefore specifies the same zero `Budget` at creation without reproducing this defect. |
| `created_by=_runtime_actor("controller")` (`controller.py:518`; `_runtime_actor` yields `ActorKind.RUNTIME` at `controller.py:177`) | `actor_kind` MUST be `HUMAN` ([domain-model.md:150](domain-model.md#L150)); the row's precondition ([transition-matrix.md:84](transition-matrix.md#L84)); `NONE_GRANTABLE` for any other creator ([transition-matrix.md:485](transition-matrix.md#L485)) |
| `policy_digest` defaults to `None` (`models.py:913`) | `req = Y` ([domain-model.md:142](domain-model.md#L142)) |

These are statements about the implementation at this baseline, recorded because
§6 replaces the implementation's choices with specified ones. This document
specifies no code.

## 2. Authorization at provisioning time

| id | Rule |
|---|---|
| `PP-1` | **The frozen design requires a non-delegated path and specifies none.** Three frozen rows carry a `HUMAN`-class `required_capability` at a point where no `ContractActivationRecord` can exist: `∅ → DRAFT` under `project.create` ([transition-matrix.md:84](transition-matrix.md#L84)), `DRAFT → ABANDONED` under `project.abandon` ([transition-matrix.md:86](transition-matrix.md#L86)), and `PENDING → ABANDONED` under `stage.abandon` during `PLANNING` ([transition-matrix.md:119](transition-matrix.md#L119)). Grants are per activation record scoped to one run ([authority-matrix.md:14](authority-matrix.md#L14)), and every `HUMAN` capability is `D` for every role ([authority-matrix.md:221](authority-matrix.md#L221)), so §5 resolution can deliver none of them to any actor. Those rows are unperformable unless a path exists that is not §5 resolution. This amendment **specifies** that path. It does not claim to recover one: the frozen text names no such path, and the `HUMAN` class legend — "requires a `HumanDecision` at exercise time, not merely at grant time" ([authority-matrix.md:51](authority-matrix.md#L51)) — presupposes a grant time rather than dispensing with one. For the five capabilities in §3 and §5 there is no grant time, and saying so is an addition, not a reading. |
| `PP-2` | **What is cited for `required_capability`.** `G-2` is an exclusion: "no entity **outside** `{HumanDecision, ContractActivationRecord}`" may be cited ([domain-model.md:888](domain-model.md#L888)). It confers nothing. What it does is leave exactly two admissible citations, one of which cannot exist at provisioning time (`PP-1`). This amendment specifies that the other is cited: the `HumanDecision` the row's `DECIDE(K)` verdict required, named in `AuditEvent.authority_ref`, a field the frozen schema defines as "activation **or decision** that permitted it" ([domain-model.md:790](domain-model.md#L790)). Standing permission — who may ever perform the act — comes from the §2.1 register row ([authority-matrix.md:56](authority-matrix.md#L56)–[:68](authority-matrix.md#L68)); per-act authorization comes from the decision. Neither substitutes for the other, and neither substitutes for `required_evidence` (`AX-9`, [authority-matrix.md:20](authority-matrix.md#L20)). |
| `PP-3` | **A provisioning decision is `DECISION` class and is not promoted.** The frozen taxonomy classes the decision record `DECISION` and only `HumanDecision.grants`/`revokes` `AUTHORITY` ([evidence-model.md:82](evidence-model.md#L82), [:84](evidence-model.md#L84)), names the `AUTHORITY` producers as `ContractActivationRecord` and `HumanDecision.grants` ([evidence-model.md:65](evidence-model.md#L65)), and admits `DECISION → AUTHORITY` only for a decision with non-empty `grants` ([evidence-model.md:95](evidence-model.md#L95)). A provisioning decision has `grants = ∅` and `revokes = ∅`; it is outside `:95` by that row's own wording, and it is **not** claimed to be `AUTHORITY`. It gates its transition the way the taxonomy says a `DECISION` gates one: "yes, as `DECIDE(K)`/`CONFIRM`" ([evidence-model.md:64](evidence-model.md#L64)), which is exactly the verdict column of every §5 row. Setting a ceiling widens no grant — it moves the bound future grants are checked against, and bounding is not granting (`AX-11`, [authority-matrix.md:22](authority-matrix.md#L22)). |
| `PP-4` | **`capability_ceiling` does not bound direct exercise of the five capabilities named in §3 and §5**, and of nothing else. For `project.ceiling.set` this is forced: the ceiling is `∅` at creation (§6), so an operation bounded by the value it writes could never run. For `project.mode.set`, `policy.set`, `budget.grant` and `budget.extend` it is **chosen**; the alternative — requiring each to appear in the ceiling before exercise — is rejected because it adds ceremony without containment, since `project.ceiling.set` cannot itself be ceiling-bounded and whoever holds it can add the other four in the preceding act. The affirmative bounds that replace the ceiling for these five are `PP-5`. |
| `PP-4a` | **Every other `HUMAN`-class capability is out of scope and stays bounded.** `secret.read`, `net.egress.any`, `proc.exec.arbitrary` ([authority-matrix.md:107](authority-matrix.md#L107)–[:110](authority-matrix.md#L110)), `policy.override` ([authority-matrix.md:64](authority-matrix.md#L64)), `finding.waive` ([authority-matrix.md:125](authority-matrix.md#L125)), `commit.publish` ([authority-matrix.md:134](authority-matrix.md#L134)), `audit.redact` ([authority-matrix.md:146](authority-matrix.md#L146)), `stage.reject`, `stage.abandon`, `project.abandon` and `project.archive` all have effects inside a run, a stage, or the evidence store. This amendment specifies no path for any of them, unbounds none of them, and leaves `AX-4` ([authority-matrix.md:15](authority-matrix.md#L15)), `AX-5` ([authority-matrix.md:16](authority-matrix.md#L16)) and the illegal row on granting outside the ceiling ([transition-matrix.md:501](transition-matrix.md#L501)) governing them unchanged. That `project.abandon` and `stage.abandon` are reachable by no specified path remains an open frozen gap (§8). |
| `PP-5` | **What bounds a direct exercise of the five**, in order: (i) the §2.1 register row exists, its class is `HUMAN`, and its `grantable by` column names `HUMAN_PRINCIPAL` ([authority-matrix.md:56](authority-matrix.md#L56)–[:68](authority-matrix.md#L68)); (ii) the §3 mode gate ([authority-matrix.md:155](authority-matrix.md#L155)–[:170](authority-matrix.md#L170)), read against `governance_mode` as it stands before the transition; (iii) the §2.1 admissibility table below; (iv) the row's own preconditions (§5); (v) the payload predicate for the field written (§5.1). None of the five has any effect outside the `Project` record: none reaches a run, a workspace, or the artifact store except to pin a digest. |
| `PP-6` | **No self-authorization.** `RUNTIME_KERNEL` grants `KERNEL` capabilities to itself only and "cannot self-grant non-`KERNEL` capabilities" ([authority-matrix.md:34](authority-matrix.md#L34)). An `AuditEvent` whose `capability_used` is one of the five and whose `actor.actor_kind` is `RUNTIME`, `WORKER` or `ADAPTER` is an integrity violation, not a transition. The kernel writes the `Project` record — the controller owns state transitions — but the actor of record is the deciding principal, and the kernel performs the write only against an admissible decision. |
| `PP-7` | **One decision, one field, one write.** Unqualified, with no exception anywhere in this amendment. The nonce consumption (`VALID → CONSUMED`, [transition-matrix.md:394](transition-matrix.md#L394)), the field write, and the `AuditEvent` persist atomically. `HD-INV-3` ([domain-model.md:718](domain-model.md#L718)) and the anti-pattern it defends ([evidence-model.md:107](evidence-model.md#L107)) are untouched. |
| `PP-8` | **The creating act is one atomic persistence over an allocated `project_id`.** The identifier is allocated first; the `RealitySnapshot` the row cites, the `Project` record, and both `AuditEvent`s become durable together, so no reader ever observes a `Ref<Project>` that does not resolve ([domain-model.md:38](domain-model.md#L38), [evidence-model.md:139](evidence-model.md#L139)). The genesis constant is computable from the allocated id and `schema_version` before either record is persisted ([evidence-model.md:127](evidence-model.md#L127)). This is what makes the frozen row's `SNAP` ([transition-matrix.md:84](transition-matrix.md#L84)) satisfiable against `RealitySnapshot.project_id : Ref<Project>` ([domain-model.md:805](domain-model.md#L805)), and it fixes the chain values in §6. The reviewed draft argued instead that referential integrity bars any record naming a project that does not yet exist, and concluded that `∅ → DRAFT` cannot be decision-gated; **that argument is withdrawn**, because it bars the row's own snapshot exactly as it bars a decision. The row is not decision-gated for the simpler reason that the frozen text writes it `AUTO` with `required_evidence = SNAP` and no `DEC(K)` ([transition-matrix.md:84](transition-matrix.md#L84)); its authority checks are `created_by.actor_kind = HUMAN` **and** `required_capability = project.create`, both on that row. This amendment adds no decision requirement to it. |

### 2.1 Admissibility of a provisioning decision

The project-scope analogue of the §5 resolution algorithm
([authority-matrix.md:239](authority-matrix.md#L239)–[:253](authority-matrix.md#L253)).
It resolves one capability for one act; there is no `capability_request`, no role,
and no activation record to write.

| step | check | basis |
|---|---|---|
| 1 | the capability is registered, class `HUMAN`, and its `grantable by` column names `HUMAN_PRINCIPAL` | [authority-matrix.md:56](authority-matrix.md#L56)–[:68](authority-matrix.md#L68); `AX-2` [authority-matrix.md:13](authority-matrix.md#L13) |
| 2 | `decided_by.actor_kind = HUMAN` with `principal_key_id` present and `auth_method ∈ {SESSION, SIGNATURE, MTLS}` equal to `decision.auth_method`; `signature` present iff `SIGNATURE` | `HD-INV-1` [domain-model.md:714](domain-model.md#L714); [domain-model.md:706](domain-model.md#L706); [transition-matrix.md:496](transition-matrix.md#L496) |
| 3 | `decision.project_id` is this project; `subject = {kind: PROJECT, id: project_id}`; `scope = PROJECT` | [domain-model.md:691](domain-model.md#L691)–[:700](domain-model.md#L700) |
| 4 | `decision_kind` equals the kind the row's `DECIDE(K)` names — not merely some kind over this project | [transition-matrix.md:61](transition-matrix.md#L61) |
| 5 | `evidence_shown` is non-empty **and** shows the current field value, the proposed value, and for a ceiling narrowing the list required by §5.1 | non-emptiness is `HD-INV-2` [domain-model.md:716](domain-model.md#L716); the content requirement is **added by this amendment** and is not attributed to `HD-INV-2` |
| 6 | `decision_state = VALID` at the instant of the transition, nonce unconsumed | `HD-INV-3` [domain-model.md:718](domain-model.md#L718); `HD-INV-4` [domain-model.md:719](domain-model.md#L719); [transition-matrix.md:522](transition-matrix.md#L522) |
| 7 | `grants = ∅` and `revokes = ∅` | `PP-3`; a provisioning decision delegates nothing, so [evidence-model.md:95](evidence-model.md#L95) does not reach it |
| 8 | the §3 mode gate permits the capability under `governance_mode` as it stands before this transition | [authority-matrix.md:155](authority-matrix.md#L155)–[:170](authority-matrix.md#L170) |
| 9 | the payload predicate for the target field holds | §5.1 |
| 10 | consumption, field write and audit event are one atomic persistence | `PP-7`; `AE-INV-2` [domain-model.md:797](domain-model.md#L797) |

A decision failing any step discharges nothing and is not consumed. Steps 1–8 are
equally the check for `project.mode.set`, which the frozen design requires
([domain-model.md:152](domain-model.md#L152)) and never specified how to check.

### 2.2 `ProvisioningDecision` — a profile of `HumanDecision`, not a new entity

| Field | Required value | Why |
|---|---|---|
| `subject.kind` / `subject.id` | `PROJECT` / this `project_id` | the act is on the project record |
| `scope` | `PROJECT` | no stage, run or single-action boundary applies ([domain-model.md:700](domain-model.md#L700)) |
| `decision_kind` | `SET_CEILING`, `GRANT_BUDGET`, `SET_POLICY`, `EXTEND_BUDGET` or `SET_MODE` | §4 |
| `grants` / `revokes` | `∅` / `∅` | `PP-3` |
| `snapshot_bound` | `false`, by the frozen derivation with no amendment | [domain-model.md:702](domain-model.md#L702) is an `iff` over two disjuncts; a `PROJECT` subject fails the first and these five kinds fail the second |
| `subject_snapshot_id` | absent | required iff `snapshot_bound` ([domain-model.md:703](domain-model.md#L703)) |
| every other field | as [domain-model.md:686](domain-model.md#L686)–[:712](domain-model.md#L712) | no schema change |

No entity is added. A `ProjectAuthorityRecord` mirroring `ContractActivationRecord`
at project scope was rejected: it would duplicate the decision's content, add a
second record with no delegation to record, and require its own expiry and
revocation rules, while `G-2` already admits the decision
([domain-model.md:888](domain-model.md#L888)).

## 3. Capability register additions

Added to the register at [authority-matrix.md:56](authority-matrix.md#L56)–[:68](authority-matrix.md#L68), in its format.

| CapabilityId | permits | class | grantable by | default | mode restriction |
|---|---|---|---|---|---|
| `project.ceiling.set` (new) | **set or replace** `Project.capability_ceiling` | `HUMAN` | `HUMAN_PRINCIPAL` | `DENY` | both modes require `DEC(SET_CEILING)` |

The name parallels `project.mode.set` ([authority-matrix.md:59](authority-matrix.md#L59)); the spelling is
free, since the register is not a naming convention. "Set or replace" is
deliberate and parallels `budget.grant`, "set initial `Budget`"
([authority-matrix.md:65](authority-matrix.md#L65)): the capability covers the first
write as well as later ones, which is what makes `∅` the creation value (§6) and
the first ceiling write a named operation. It is never grantable to a worker
([authority-matrix.md:221](authority-matrix.md#L221)), never held by the kernel
(`PP-6`), and not bounded by the ceiling it writes (`PP-4`).

Added to the §3 mode gate, which carries a row for `project.mode.set`
([authority-matrix.md:158](authority-matrix.md#L158)) and none for the other three;
the catch-all rows cover `ORD`, `KERNEL` and `NEVER` classes only
([authority-matrix.md:168](authority-matrix.md#L168)–[:170](authority-matrix.md#L170)).

| CapabilityId | `SUPERVISED` | `AUTONOMOUS` |
|---|---|---|
| `project.ceiling.set` | `DEC(SET_CEILING)` | `DEC(SET_CEILING)` |
| `policy.set` | `DEC(SET_POLICY)` | `DEC(SET_POLICY)` |
| `budget.grant` | `DEC(GRANT_BUDGET)` | `DEC(GRANT_BUDGET)` |
| `budget.extend` | `DEC(EXTEND_BUDGET)` | `DEC(EXTEND_BUDGET)` |

Identical columns are **forced** for `project.mode.set`, whose register row already
reads "both modes require `DEC(SET_MODE)`" ([authority-matrix.md:59](authority-matrix.md#L59)),
and **chosen** for these four. [authority-matrix.md:172](authority-matrix.md#L172)
forbids `AUTONOMOUS` widening the `HUMAN` set; it permits a narrower `AUTONOMOUS`
column, as `project.create`'s own `DENY` shows ([authority-matrix.md:157](authority-matrix.md#L157)).
The alternative — `DENY` in `AUTONOMOUS` for some of the four — is rejected because
`project.mode.set` must remain exercisable in `AUTONOMOUS` for a project to return
to supervision, and a split between the five would make the set inconsistent
without making it safer.

## 4. Decision kinds

Added to the closed enumeration at [domain-model.md:693](domain-model.md#L693). No
frozen schema file enumerates `decision_kind`, so no schema changes.

| Kind | Names the act | Rejected reuse, and why |
|---|---|---|
| `SET_CEILING` | replace `capability_ceiling` | `GRANT_CAPABILITY`. Rejected: that kind means a capability may be delegated to a run and is what `capability_grant_basis` cites ([domain-model.md:395](domain-model.md#L395)). Widening a ceiling authorizes nobody to do anything; reusing one kind for both collapses the distinction `AX-11` ([authority-matrix.md:22](authority-matrix.md#L22)) and `A-INV-3` ([domain-model.md:411](domain-model.md#L411)) exist to draw, and would let a ceiling decision be mistaken for a grant at §5.1 step 6 ([authority-matrix.md:246](authority-matrix.md#L246)). |
| `GRANT_BUDGET` | set the initial `Budget` | `EXTEND_BUDGET`. Rejected: that token is checked by name at [transition-matrix.md:172](transition-matrix.md#L172) and [:140](transition-matrix.md#L140). One kind would make a decision recorded to provision a new project indistinguishable, at the point of check, from one recorded to lift a budget suspension. The register already separates the capabilities ([authority-matrix.md:65](authority-matrix.md#L65), [:66](authority-matrix.md#L66)). |
| `SET_POLICY` | replace the policy document and `policy_digest` | `APPROVE`. Rejected: `snapshot_bound` is `true` for `APPROVE` ([domain-model.md:702](domain-model.md#L702)), so the decision would require a `COMPLETE` workspace snapshot and go `STALE` on any drift ([domain-model.md:719](domain-model.md#L719)). A policy replacement is a statement about the policy document, not the workspace. |

`SET_MODE` and `EXTEND_BUDGET` are reused unchanged. The `snapshot_bound`
derivation needs no extension: `:702` is an `iff` over two disjuncts, and the three
new kinds over a `PROJECT` subject satisfy neither, so they are already not
snapshot-bound. The reviewed draft claimed an amendment here; none is made.

## 5. Transition rows

A new subsection `transition-matrix.md` §7.7, **Project governance fields**, in the
matrix's format ([transition-matrix.md:45](transition-matrix.md#L45)–[:52](transition-matrix.md#L52)).
`illegal_because` is omitted; every row here is legal. `from_state` and `to_state`
name the value of the field written: these are field writes on the `Project`
record, not a fourth state axis (`O-1`, [transition-matrix.md:20](transition-matrix.md#L20)).

Every row additionally requires `project.lifecycle ∉ {COMPLETED, ARCHIVED,
ABANDONED}`, the §2.1 admissibility table, the §5.3 suspension column, and `PP-7`
atomicity. `C` is the current ceiling, `B` the current budget, `H` the current
`policy_digest`.

| Field: from → to | preconditions | effect | required_evidence | required_capability | supervised_policy | autonomous_policy |
|---|---|---|---|---|---|---|
| `capability_ceiling`: `C → C'`, `C' \ C ≠ ∅` (widening) | `C'` well-formed per §5.1 | future activations only; no minted `ContractActivationRecord` and no `StageRun.effective_capabilities` changes ([domain-model.md:293](domain-model.md#L293), [transition-matrix.md:500](transition-matrix.md#L500)) | `DEC(SET_CEILING)` | `project.ceiling.set` | `DECIDE(SET_CEILING)` | `DECIDE(SET_CEILING)` |
| `capability_ceiling`: `C → C'`, `C' ⊊ C` (narrowing) | `C'` well-formed per §5.1; the decision's `evidence_shown` lists every un-revoked activation whose `granted_capabilities ⊄ C'` (§5.1) | future activations only (§5.2); the payload records that same list | `DEC(SET_CEILING)` | `project.ceiling.set` | `DECIDE(SET_CEILING)` | `DECIDE(SET_CEILING)` |
| `budget`: `0⃗ → B'` (initial grant) | `lifecycle ∈ {DRAFT, PLANNING}`; `budget` and `budget_used` are both the zero vector; every dimension of `B'` is `> 0` (§5.1) | — | `DEC(GRANT_BUDGET)` | `budget.grant` | `DECIDE(GRANT_BUDGET)` | `DECIDE(GRANT_BUDGET)` |
| `budget`: `B → B'` (extension) | `lifecycle ∈ {PLANNING, ACTIVE, SETTLING}`; `B'ᵢ ≥ Bᵢ` for every dimension and `B' ≠ B` | may make `SUSPENDED_BY_BUDGET → NONE` satisfiable for the `Project` holder alone (§5.2) | `DEC(EXTEND_BUDGET)` | `budget.extend` | `DECIDE(EXTEND_BUDGET)` | `DECIDE(EXTEND_BUDGET)` |
| `policy_digest`: `H → H'` | `H'` is the digest of a persisted, human-authored policy document; `H' ≠ H` (§5.1) | governs future activations; `ContractActivationRecord.policy_digest` is immutable ([domain-model.md:397](domain-model.md#L397)) | `DEC(SET_POLICY)` | `policy.set` | `DECIDE(SET_POLICY)` | `DECIDE(SET_POLICY)` |
| `governance_mode`: `SUPERVISED → AUTONOMOUS` | every stage has `lifecycle ∈ {PENDING, READY, SATISFIED, REJECTED, ABANDONED}`; no non-terminal `StageRun`; no `ACTIVE` `StageContract` | — | `DEC(SET_MODE)` | `project.mode.set` | `DECIDE(SET_MODE)` | `DECIDE(SET_MODE)` |
| `governance_mode`: `AUTONOMOUS → SUPERVISED` | — | — | `DEC(SET_MODE)` | `project.mode.set` | `DECIDE(SET_MODE)` | `DECIDE(SET_MODE)` |

The `SUPERVISED → AUTONOMOUS` precondition covers contracted work, not only
running work. `governance_mode_at_activation` is pinned per activation record
([domain-model.md:396](domain-model.md#L396)), so grant resolution is durable; but a
transition row selects its verdict column by `project.governance_mode` as it stands
([transition-matrix.md:50](transition-matrix.md#L50)–[:51](transition-matrix.md#L51)),
so a mid-flight flip would drop `∅ → ALLOCATED` from `CONFIRM` to `AUTO`
([transition-matrix.md:189](transition-matrix.md#L189)) and `READY → CONTRACTED`
likewise ([transition-matrix.md:121](transition-matrix.md#L121)) for work already
contracted under supervision. Requiring no `ACTIVE` contract and no stage past
`READY` closes both. This is a choice; the alternative — permit the flip at any
time and let each row read the current mode — is rejected for that reason.
`AUTONOMOUS → SUPERVISED` adds confirmations and carries no such precondition.

### 5.1 Payload predicates

| Field | Predicate | Status |
|---|---|---|
| `capability_ceiling` | every member is a `CapabilityId` registered at [authority-matrix.md:56](authority-matrix.md#L56)–[:147](authority-matrix.md#L147) whose class is `ORD` or `HUMAN`. `NEVER` and `KERNEL` members are refused. The empty set is well-formed. | **Chosen.** A `KERNEL` or `NEVER` member is inert, not illegal: `AX-11` means the ceiling grants nothing ([authority-matrix.md:22](authority-matrix.md#L22)), §5 step 5 removes both classes ([authority-matrix.md:245](authority-matrix.md#L245)), and `AX-6`/`AX-7` bar them from any grant ([authority-matrix.md:17](authority-matrix.md#L17), [:18](authority-matrix.md#L18)). Refusing them keeps the ceiling from stating an authority that can never exist; the alternative is to accept and silently drop them. |
| `capability_ceiling`, narrowing | the decision's `evidence_shown` and the transition payload both carry the list of un-revoked `ContractActivationRecord`s whose `granted_capabilities ⊄ C'`, with the excess capabilities per record | **Added by this amendment** (§8 records why no `EscalationTrigger` is added). It uses only frozen mechanism: `evidence_shown` is what makes an approval informed ([domain-model.md:716](domain-model.md#L716)), and the authority trace reads the event ([evidence-model.md:282](evidence-model.md#L282)). |
| `budget` at `budget.grant` | every dimension `> 0` | **Derived.** Once `ACTIVE`, any `WR` or `VR(any)` usage record makes `NONE → SUSPENDED_BY_BUDGET` takeable for a zero dimension, since `budget_used ≥ budget` holds at zero usage ([transition-matrix.md:159](transition-matrix.md#L159)). This also fixes "`budget` non-zero" at [transition-matrix.md:88](transition-matrix.md#L88) as *every* dimension, not some. |
| `budget` at `budget.extend` | no dimension decreases; at least one increases | **Derived** from "raise a ceiling" ([authority-matrix.md:66](authority-matrix.md#L66)); lowering is out of scope (§8). |
| `policy_digest` | equals the artifact-store digest ([evidence-model.md:19](evidence-model.md#L19)) of a persisted policy document whose artifact `producer` is a `HUMAN` principal ([evidence-model.md:35](evidence-model.md#L35)) | **Derived** from "policy document itself is human-authored and digest-pinned" ([authority-matrix.md:32](authority-matrix.md#L32)). No runtime-fabricated document satisfies it, which is why §6 has the creating human supply the first one. |

A policy write always requires `suspension = NONE` in both directions, because the
runtime reads only `POLICY_GRANTABLE` out of the document
([authority-matrix.md:32](authority-matrix.md#L32), [:264](authority-matrix.md#L264))
and cannot decide whether a replacement widens or narrows; it must treat every
replacement as a widening. Chosen; the alternative is to permit a "narrowing"
policy write while suspended, which is undecidable as specified.

### 5.2 Consequences for frozen rules

| Frozen rule | Reading under this amendment |
|---|---|
| `P-INV-2` ([domain-model.md:153](domain-model.md#L153)) and `A-INV-1` ([domain-model.md:408](domain-model.md#L408)), both written as standing set-inclusion | Evaluated **at grant time**, against the ceiling in force at activation and pinned by `capability_grant_basis` ([domain-model.md:395](domain-model.md#L395)). A later narrowing does not invalidate a minted activation record or a frozen `effective_capabilities`, which cannot shrink in place ([domain-model.md:293](domain-model.md#L293), [transition-matrix.md:500](transition-matrix.md#L500)). The `AX-10` support is partial and is stated as such: its second clause protects recorded evidence, while an activation record is `AUTHORITY`, not evidence ([authority-matrix.md:21](authority-matrix.md#L21), [evidence-model.md:83](evidence-model.md#L83)), and its first clause — revocation immediate for future operations — points the other way for a live run's mediated operations ([authority-matrix.md:287](authority-matrix.md#L287)). The exposure is therefore real and bounded by `expires_at = activated_at + deadline_ms` ([domain-model.md:401](domain-model.md#L401)) with `deadline_ms` `src = H/W` ([domain-model.md:331](domain-model.md#L331)); it is made visible by the narrowing row's `evidence_shown` and payload list (§5.1), and contained by `contract.revoke` and `suspension.set` ([authority-matrix.md:88](authority-matrix.md#L88), [:67](authority-matrix.md#L67)). |
| §4 `SUSPENDED_BY_BUDGET → NONE` ([transition-matrix.md:172](transition-matrix.md#L172)) | **Amended for the `Project` holder only**, in both the `required_evidence` and the two policy columns, so that no second `HumanDecision` and no exception to `HD-INV-3` is needed. The predicate: `holder = Project`; there exists an `AuditEvent` with `capability_used = budget.extend`, `subject = {kind: "project", id: project_id}`, and `seq` greater than the `seq` of the event that set this suspension; and every dimension of `budget_used` is now strictly below `budget`. `required_evidence` becomes that `AuditEvent` together with the current budget state; `supervised_policy` and `autonomous_policy` become `AUTO`, as they already are for other causes that demonstrably stopped holding ([transition-matrix.md:170](transition-matrix.md#L170)). The clearing transition is then taken by the kernel under `suspension.clear`, a `KERNEL` capability ([authority-matrix.md:68](authority-matrix.md#L68)), with `actor_kind = RUNTIME` — which is why `PP-6`'s human-actor rule does not need to reach it. |
| `HD-INV-3` ([domain-model.md:718](domain-model.md#L718)), the consumption row ([transition-matrix.md:394](transition-matrix.md#L394)), and [evidence-model.md:107](evidence-model.md#L107) | **Untouched.** One decision discharges one transition and is consumed by that transition's own `AuditEvent`, singular. The reviewed draft's exception is withdrawn. |
| `AWAITING_DECISION → RUNNING` ([transition-matrix.md:140](transition-matrix.md#L140)), the third consumer of `DEC(EXTEND_BUDGET)` | Unaffected and uncontested. Its `required_evidence` is `DEC(OVERRIDE)` **or** `DEC(EXTEND_BUDGET)`, but its verdict is `DECIDE(OVERRIDE)` in both modes, so a `DEC(EXTEND_BUDGET)` alone never discharges it. A project-budget extension consumes its own decision (`PP-7`); a rework through `:140` needs its own `DEC(OVERRIDE)` regardless. Separately, that row's "budget extended if exhausted" remains unsatisfiable for a run holder — see below. |
| §4 reachability, per holder ([transition-matrix.md:151](transition-matrix.md#L151)) | `Stage` carries no budget field at all ([domain-model.md:190](domain-model.md#L190)–[:217](domain-model.md#L217)), so it can never enter `SUSPENDED_BY_BUDGET`. `StageRun.budget_allocated` is immutable ([domain-model.md:284](domain-model.md#L284)) and no run-scope extension is specified here, so the run holder's clearing row stays unreachable. **The claim is exactly: reachable for the `Project` holder.** The run-holder gap is a frozen gap this amendment records and does not close (§8). |
| `PLANNING → ACTIVE` ([transition-matrix.md:88](transition-matrix.md#L88)) | Unchanged and now satisfiable: the ceiling row and the budget-grant row are the only specified ways its two preconditions can be met. |

### 5.3 Suspension and governance writes

The frozen axis-3 gate enumerates what each suspension value permits, by column
([transition-matrix.md:30](transition-matrix.md#L30)–[:39](transition-matrix.md#L39)),
and no column covers a write to a `Project` governance field. Under `AX-1`,
"absence of a rule is never permission" ([authority-matrix.md:12](authority-matrix.md#L12)),
that absence is a denial. **This amendment therefore adds a column**; the rule
behind its values is DESIGN-03's, not the frozen design's, and §9 lists §0.1 as
extended.

| suspension value | project governance writes |
|---|---|
| `NONE` | all §7.7 rows |
| `QUIESCING` | ceiling narrowing, `AUTONOMOUS → SUPERVISED`, `budget.extend` |
| `SUSPENDED_BY_BUDGET` | ceiling narrowing, `AUTONOMOUS → SUPERVISED`, `budget.extend` |
| `SUSPENDED_BY_HUMAN`, `_POLICY`, `_ESCALATION`, `_DRIFT` | ceiling narrowing, `AUTONOMOUS → SUPERVISED` |
| `SUSPENDED_BY_INTEGRITY` | none |

The rule: a write that cannot increase authority is permitted while suspended,
plus the one increase that exists to lift a budget suspension.
`SUSPENDED_BY_INTEGRITY` permits nothing, which is the one value the frozen text
already settles
([transition-matrix.md:486](transition-matrix.md#L486)). The `budget.extend` cell is
not optional: without it §5.2's clearing predicate can never be satisfied and a
budget-suspended project deadlocks, since the grant row requires
`lifecycle ∈ {DRAFT, PLANNING}`. A narrowing under suspension reduces no *live*
authority under §5.2's grant-time reading — it bounds future activations, which is
what containment during an incident means, and the payload list (§5.1) is what
makes the residue visible.

## 6. Specified initial `Project` state

The value of every field in the `Project` table
([domain-model.md:129](domain-model.md#L129)–[:150](domain-model.md#L150)) at
`∅ → DRAFT`, persisted atomically per `PP-8`. This replaces the implementation's
choices recorded in §1.1; it is not a schema change.

| Field | Value at creation | Basis |
|---|---|---|
| `project_id` | the `Id` allocated before the atomic persistence | `PP-8` |
| `name`, `slug`, `workspace_root` | human-supplied; `workspace_root` exists | [domain-model.md:132](domain-model.md#L132)–[:139](domain-model.md#L139); row precondition [transition-matrix.md:84](transition-matrix.md#L84) |
| `schema_version` | the runtime's domain-model version | [domain-model.md:134](domain-model.md#L134) |
| `lifecycle` | `DRAFT` | one inbound `∅` row, landing in `DRAFT` ([transition-matrix.md:84](transition-matrix.md#L84)) |
| `suspension` / `suspension_ref` | `NONE` / absent | required iff `suspension ≠ NONE` ([domain-model.md:137](domain-model.md#L137)) |
| `governance_mode` | **`SUPERVISED`** — forced | `project.create` is `DENY` in `AUTONOMOUS` ([authority-matrix.md:157](authority-matrix.md#L157), [transition-matrix.md:84](transition-matrix.md#L84)), so no project can be created autonomous; and `AUTONOMOUS` without a `HumanDecision` is illegal ([transition-matrix.md:511](transition-matrix.md#L511)). Independent of `PP-8`. |
| `roadmap_id` | absent | `N`, "absent while `DRAFT`" ([domain-model.md:140](domain-model.md#L140)) |
| `capability_ceiling` | `∅` — **chosen** | `AX-1` denies by default ([authority-matrix.md:12](authority-matrix.md#L12)), and supplying a ceiling inside the creating act would exercise `project.ceiling.set` under `project.create`, which `AX-2`/`G-4` forbid ([authority-matrix.md:13](authority-matrix.md#L13), [domain-model.md:890](domain-model.md#L890)). The alternative — accept it as a creation parameter, as `workspace_root` is — is rejected on that one-capability-per-operation ground, which does not apply to `name`, `slug` or `workspace_root` because no capability covers those fields. |
| `policy_digest` | the digest of a policy document **supplied by the creating human** in the creating act | `req = Y` so it cannot be absent ([domain-model.md:142](domain-model.md#L142)); the document must be human-authored ([authority-matrix.md:32](authority-matrix.md#L32)) and the digest is `src = R`, computed by the runtime. The `AX-2` objection does not apply: `policy.set` "**replace**s the policy document" ([authority-matrix.md:63](authority-matrix.md#L63)), and a replacement presupposes an existing one, so establishing the first is not an exercise of it — unlike `budget.grant`, whose verb is "set initial `Budget`" ([authority-matrix.md:65](authority-matrix.md#L65)), and unlike `project.ceiling.set`, defined in §3 to cover the initial write. A document marking nothing `POLICY_GRANTABLE` is admissible; a runtime-fabricated one is not. |
| `budget` | the zero `Budget` | `budget.grant` "set**s** initial `Budget`" ([authority-matrix.md:65](authority-matrix.md#L65)), so there must be one for it to set. Safe at `DRAFT`/`PLANNING`: `NONE → SUSPENDED_BY_BUDGET` requires `WR` or `VR(any)` usage records ([transition-matrix.md:159](transition-matrix.md#L159)), which cannot exist while no worker may be dispatched ([transition-matrix.md:435](transition-matrix.md#L435)). The grant row runs under `suspension = NONE` at `DRAFT`, so no deadlock arises. |
| `budget_used` | the zero `BudgetUsage` | `D`/`A`, derived from receipts ([domain-model.md:84](domain-model.md#L84)–[:86](domain-model.md#L86)) |
| `event_seq` | `1` | two events are required: `seq 0` carries the `RealitySnapshot` (`EVIDENCE`), `seq 1` the creation, because evidence reachability demands a strictly lower `seq` for cited evidence ([evidence-model.md:178](evidence-model.md#L178)) |
| `event_head` | the `event_hash` of the creation event at `seq 1` | head of the highest `seq` ([evidence-model.md:128](evidence-model.md#L128)); the genesis constant is `prev_event_hash` of `seq 0` ([evidence-model.md:127](evidence-model.md#L127)) |
| `controller_epoch` | `1` — **chosen** | `P-INV-4` says the epoch increments before the controller performs any work ([domain-model.md:155](domain-model.md#L155)), and a controller performed the creation, so `≥ 1` is the reading its own words support. The alternative — `0` at creation, raised by the first `start()` — is rejected for that reason. The reviewed draft's added rule "no dispatch or apply under epoch `0`" has no frozen counterpart and is deleted. |
| `snapshot_current` | the `snapshot_id` of the `seq 0` snapshot | the row cites `SNAP` as `required_evidence` ([transition-matrix.md:84](transition-matrix.md#L84)) and the field is the derived newest snapshot ([domain-model.md:148](domain-model.md#L148)) |
| `created_at`, `updated_at` | the creation instant | [domain-model.md:149](domain-model.md#L149) |
| `created_by` | the authenticated `HUMAN` principal, with `principal_key_id` and `auth_method ∈ {SESSION, SIGNATURE, MTLS}` | [domain-model.md:150](domain-model.md#L150), [:58](domain-model.md#L58)–[:59](domain-model.md#L59); any other creator is `NONE_GRANTABLE` ([transition-matrix.md:485](transition-matrix.md#L485)) |

A project created this way can do nothing until a human sets a ceiling and grants a
budget: every capability request is denied `NOT_IN_CEILING`
([authority-matrix.md:242](authority-matrix.md#L242)) and no stage can be worked.
That is the intended reading of `AX-1`, and the provisioning rows are how the state
is left.

## 7. Audit and event shape

| id | Rule |
|---|---|
| `PP-9` | Each §7.7 row emits one `AuditEvent` with `epistemic_class = DECISION` (`PP-3`; [evidence-model.md:82](evidence-model.md#L82)), `event_type ∈ {project.ceiling_set, project.budget_granted, project.budget_extended, project.policy_set, project.mode_set}` — `<entity>.<verb>` per [domain-model.md:784](domain-model.md#L784) — `actor` = the decision's `decided_by`, `capability_used` = the row's `required_capability`, `authority_ref = decision_id` ([domain-model.md:790](domain-model.md#L790)), and `subject = {kind: "project", id: project_id}`. The payload records the previous and new field values, plus the §5.1 list for a narrowing. |
| `PP-10` | **Authority binding.** [evidence-model.md:176](evidence-model.md#L176) requires every event with `capability_used` to have an `authority_ref` "resolving to a live grant at `recorded_at`". Read literally it is unsatisfiable for any event whose capability was never granted — every `KERNEL`-capability event outside a run, `snapshot.take` at creation included, and the frozen `∅ → DRAFT` itself, none of which has a grant record; `authority_ref` is `req = N` in the frozen schema ([domain-model.md:790](domain-model.md#L790)), which the check cannot override. The check is therefore amended to read: an event whose capability was **delegated** resolves `authority_ref` to the activation record or granting decision that supplied it; an event whose capability is **held** — a `KERNEL` capability held by the kernel (`AX-7`, [authority-matrix.md:18](authority-matrix.md#L18)) or one of the five exercised by the `HUMAN_PRINCIPAL` — names no grant, and its binding is satisfied by the register row plus, where the transition's verdict is `DECIDE(K)`, an `authority_ref` resolving to a `HumanDecision` of that kind with `decision_state = VALID` at `recorded_at`. Its transition to `CONSUMED` in the same atomic write does not fail the check: the decision consumed *by* the event it authorized is the expected outcome. |
| `PP-11` | The `project.created` event carries `epistemic_class = AUTHORITY` and **no** `authority_ref`: it records the project's authority root — `created_by`, the initial ceiling, the initial mode — and no decision or activation can be cited for it (`PP-1`, `PP-8`). This extends the `AUTHORITY` producer list at [evidence-model.md:65](evidence-model.md#L65), which names only `ContractActivationRecord` and `HumanDecision.grants`; the extension is limited to this one event type and is listed in §9. The other three classes do not fit: it measures nothing, asserts nothing, and carries no `HumanDecision`. The `seq 0` snapshot event is ordinary `EVIDENCE` under `snapshot.take` ([evidence-model.md:80](evidence-model.md#L80)). |
| `PP-12` | The `AuditEvent` precedes observability of the new field value (`AE-INV-2`, [domain-model.md:797](domain-model.md#L797)), and consumption, write and event are one persistence (`PP-7`). A crash leaves either the whole provisioning act or none of it. |
| `PP-13` | A denied provisioning attempt emits an `AuditEvent` with `epistemic_class = AUTHORITY` recording the failed step of §2.1 — `AX-8`: silent denial is a defect ([authority-matrix.md:19](authority-matrix.md#L19)). |

Provisioning initiates no effect outside the kernel's own store, so `G-9`
([domain-model.md:895](domain-model.md#L895)), `RUN-INV-3` and the reconciliation
machinery do not reach these rows: there is no provider call and no repository
mutation whose identity must be made durable in advance.

## 8. Design choices and what is left unspecified

| Choice | Alternative rejected |
|---|---|
| `project.ceiling.set` as the identifier, covering the initial write | `project.capability_ceiling.set`; `ceiling.set`. Free — the register is not a naming convention. |
| Three new decision kinds rather than reuse | §4 records each rejected reuse with its frozen consequence |
| The `HumanDecision` is what is cited, and stays `DECISION` class | A `ProjectAuthorityRecord` at project scope (§2.2); and promoting the decision to `AUTHORITY`, rejected because it would amend [evidence-model.md:65](evidence-model.md#L65), [:84](evidence-model.md#L84) and [:95](evidence-model.md#L95) to gain nothing `DECIDE(K)` does not already give |
| `KERNEL` and `NEVER` members refused from a ceiling | Accept them and let §5 step 5 drop them. Both refusals are choices, not `AX-6`/`AX-7` derivations (§5.1). |
| `P-INV-2` at grant time, with the narrowing made visible by `evidence_shown` and payload | Forbid narrowing while a run is live — rejected: containment would be hostage to a running worker. Raise an `Escalation` — rejected: `EscalationTrigger` is a closed enumeration ([domain-model.md:37](domain-model.md#L37), [:753](domain-model.md#L753)–[:771](domain-model.md#L771)) with no fitting member, and adding one enlarges the frozen surface for a fact the transition payload already carries. **Residual risk:** an operator who narrows during an incident gets a recorded list, not an automatic stop; the stop remains `contract.revoke` or `suspension.set`. |
| Amend the §4 clearing row rather than `HD-INV-3` | One decision discharging two transitions — rejected: `HD-INV-3` is the rule [evidence-model.md:107](evidence-model.md#L107) names against one approval authorizing a series of actions, and it should not be the thing that bends. |
| `SUPERVISED → AUTONOMOUS` barred while any contract is `ACTIVE` or any stage is past `READY` | "No non-terminal `StageRun`" alone — rejected: too weak (§5). Permit at any time — rejected: supervised confirmations would vanish for contracted work. |
| Policy writes always require `suspension = NONE` | Permit a narrowing policy write — undecidable as specified (§5.1) |
| The creating human supplies the first policy document | A runtime-fabricated canonical empty document — rejected: not human-authored ([authority-matrix.md:32](authority-matrix.md#L32)), with no named producer ([evidence-model.md:35](evidence-model.md#L35)). Making `policy_digest` optional — rejected: `req = Y`. |
| `governance_mode` mode-gate columns identical for the four new rows | A narrower `AUTONOMOUS` column (§3) |
| `controller_epoch = 1`; `capability_ceiling = ∅` | §6 records both alternatives |
| No guard "`policy_digest` present" on `SUPERVISED → AUTONOMOUS` | The reviewed draft carried one; it is vacuous for a `req = Y` field ([domain-model.md:142](domain-model.md#L142)) and is deleted rather than replaced. Requiring a non-empty `POLICY_GRANTABLE` set was considered and rejected: `ROLE_DEFAULT` remains a grantor in both modes ([authority-matrix.md:265](authority-matrix.md#L265)), so an autonomous project with no policy grants is coherent. |

Left unspecified, deliberately:

| Not specified | Why |
|---|---|
| Lowering a live `budget` | Forced: no register row permits it ([authority-matrix.md:65](authority-matrix.md#L65), [:66](authority-matrix.md#L66)) and `AX-1` denies by default. Lowering below `budget_used` would manufacture retroactive exhaustion. |
| Run- and contract-scope budget extension | `budget.extend` names "a live project **or run**" ([authority-matrix.md:66](authority-matrix.md#L66)); only the `Project` holder is specified here. Consequences recorded: `StageRun.budget_allocated` is immutable ([domain-model.md:284](domain-model.md#L284)), so a run's `SUSPENDED_BY_BUDGET → NONE` ([transition-matrix.md:172](transition-matrix.md#L172)) and "budget extended if exhausted" ([transition-matrix.md:140](transition-matrix.md#L140)) remain unsatisfiable for a run. That is a frozen gap, recorded and not closed. |
| A path for `project.abandon`, `project.archive`, `stage.reject`, `stage.abandon` | `PP-1` shows these frozen rows are unperformable by §5 resolution too. This amendment specifies the path only for the five it is scoped to; the rest is the same gap, unclosed and now named. |
| The policy document's content model beyond `POLICY_GRANTABLE` | The frozen design reads only that set ([authority-matrix.md:32](authority-matrix.md#L32), [:264](authority-matrix.md#L264)). No well-formedness notion beyond §5.1's producer and digest predicate is asserted. |
| `budget_used` accumulation from execution | Usage is already specified as derived from receipts ([domain-model.md:84](domain-model.md#L84)–[:86](domain-model.md#L86)); the absence of an accruing path is an implementation gap recorded as `FINDINGS-02` F02-007 ([review/FINDINGS-02.md:18](review/FINDINGS-02.md#L18)), not a design gap. |
| Any implementation | This document states what must be true. |

## 9. Statements in `design-01-frozen` amended and left untouched

Only the named deltas below supersede, extend, or narrow frozen statements. All
other DESIGN-01 statements remain in force; the frozen files remain unchanged.

| Frozen source / statement | Amendment |
|---|---|
| Register §2.1 ([authority-matrix.md:56](authority-matrix.md#L56)–[:68](authority-matrix.md#L68)) | Adds `project.ceiling.set` (§3). The four existing project-governance rows are unchanged. |
| Mode gate §3 ([authority-matrix.md:155](authority-matrix.md#L155)–[:170](authority-matrix.md#L170)) | Adds four rows (§3) |
| Class legend ([authority-matrix.md:51](authority-matrix.md#L51)) | For the five, a `HUMAN` capability has an exercise time and no grant time (`PP-1`) |
| `AX-3` ([authority-matrix.md:14](authority-matrix.md#L14)), §5 ([:239](authority-matrix.md#L239)–[:253](authority-matrix.md#L253)), §5.1 ([:261](authority-matrix.md#L261)–[:267](authority-matrix.md#L267)) | Read as governing **delegated** grants to a run; direct exercise is a separate path with its own admissibility table (§2.1) |
| `AX-4` ([authority-matrix.md:15](authority-matrix.md#L15)), `AX-5` ([:16](authority-matrix.md#L16)), `PROJECT_CEILING` ([:31](authority-matrix.md#L31)) | Do not bound direct exercise of the five, and bound everything else unchanged (`PP-4`, `PP-4a`) |
| Enforcement points §6 ([authority-matrix.md:283](authority-matrix.md#L283)–[:293](authority-matrix.md#L293)) | Adds the project-scope point: the §2.1 table, checked at the field write (§2.1, §7) |
| `decision_kind` ([domain-model.md:693](domain-model.md#L693)) | Adds `SET_CEILING`, `GRANT_BUDGET`, `SET_POLICY` (§4) |
| `P-INV-2` ([domain-model.md:153](domain-model.md#L153)), `A-INV-1` ([domain-model.md:408](domain-model.md#L408)) | Act-time rather than standing set-inclusion, with the narrowing made visible (§5.1, §5.2) |
| `Project` table ([domain-model.md:129](domain-model.md#L129)–[:150](domain-model.md#L150)) | No field, type, `req`, `mut` or `src` changes. The §7.7 rows write `governance_mode`, `capability_ceiling` and `budget` (`src = H`) and `policy_digest` (`src = R` — the runtime computing the digest of a human-authored document, [domain-model.md:142](domain-model.md#L142)). §6 fixes every field's value at creation. |
| Axis-3 gate §0.1 ([transition-matrix.md:30](transition-matrix.md#L30)–[:39](transition-matrix.md#L39)) | **Extended** with a "project governance writes" column (§5.3). The rule behind its values is this amendment's. |
| §7 subordinate machines | Adds §7.7, seven rows over `Project` governance fields (§5) |
| §4 `SUSPENDED_BY_BUDGET → NONE` ([transition-matrix.md:172](transition-matrix.md#L172)) | `required_evidence` and both policy columns amended, **for the `Project` holder only** (§5.2) |
| `PLANNING → ACTIVE` ([transition-matrix.md:88](transition-matrix.md#L88)) | Row unchanged; "`budget` non-zero" defined as every dimension `> 0` (§5.1) |
| Authority binding ([evidence-model.md:176](evidence-model.md#L176)) | Amended to distinguish delegated from held capabilities (`PP-10`) |
| `AUTHORITY` producers ([evidence-model.md:65](evidence-model.md#L65)) | Extended for the `project.created` event only (`PP-11`) |

| Frozen source / statement | Left untouched |
|---|---|
| `HD-INV-3` ([domain-model.md:718](domain-model.md#L718)), consumption row ([transition-matrix.md:394](transition-matrix.md#L394)), one-approval anti-pattern ([evidence-model.md:107](evidence-model.md#L107)) | Single consumption, one transition per decision (`PP-7`) |
| `DECISION → AUTHORITY` ([evidence-model.md:95](evidence-model.md#L95)); decision classification ([evidence-model.md:82](evidence-model.md#L82), [:84](evidence-model.md#L84)) | Not scoped, not amended, not relied on: a `grants = ∅` decision is outside `:95` by its own wording and is never promoted (`PP-3`) |
| `snapshot_bound` derivation ([domain-model.md:702](domain-model.md#L702)) | No extension needed; the three new kinds over a `PROJECT` subject already fail both disjuncts (§4) |
| `AX-1`, `AX-2`, `AX-6`–`AX-11` ([authority-matrix.md:12](authority-matrix.md#L12)–[:22](authority-matrix.md#L22)); §4, §4.1, §4.2 ([authority-matrix.md:177](authority-matrix.md#L177)–[:233](authority-matrix.md#L233)) | Default deny, one capability per operation, kernel confinement, denial recording, and every worker grant. No worker gains any project-governance capability ([authority-matrix.md:221](authority-matrix.md#L221)) |
| `A-INV-2`, `A-INV-3` ([domain-model.md:410](domain-model.md#L410), [:411](domain-model.md#L411)); `C-INV-3` ([domain-model.md:380](domain-model.md#L380)) | Activation is the only conferrer of a run's authority, with a grant basis per capability |
| `HD-INV-1`, `HD-INV-2`, `HD-INV-4` ([domain-model.md:714](domain-model.md#L714)–[:727](domain-model.md#L727)); §7.5 ([transition-matrix.md:385](transition-matrix.md#L385)–[:406](transition-matrix.md#L406)) | Authentication, mandatory `evidence_shown`, staleness, and the decision-state machine |
| `RUN-INV-1`–`RUN-INV-3`, `S-INV-*`, `W-INV-*`, `V-INV-*`, `RA-INV-*`, `CM-INV-*`, `G-1`, `G-3`–`G-10` | Run, stage, worker, validation, review and commit semantics. `G-2` is read as the exclusion it is, not amended (`PP-2`) |
| `transition-matrix.md` §1–§3, §5, §6, §7.1–§7.6, §8, §9 | Every lifecycle row, subordinate machine, the composition table, and the whole illegal section — in particular [:500](transition-matrix.md#L500), [:501](transition-matrix.md#L501) and [:511](transition-matrix.md#L511), which the §5 rows satisfy rather than amend |
| `evidence-model.md` §1, §2.1–§2.3, §3.1–§3.2.1, §3.3 other checks, §4–§7 | Artifact store, taxonomy, chain construction, append protocol, satisfaction derivation, currency, retention and export |
| `worker_provider.md`, `roadmap_adapter.md`, `schema/*`, frozen `design/review/*` | Unaffected |
| `design/DESIGN-02-candidate-observation.md` | No interaction in either direction |

## 10. Entry required in `CLAUDE.md`

This document does not edit `CLAUDE.md`. The "Design baseline" section needs an
entry reading:

> DESIGN-03 records a proposed amendment as a design document only — not yet
> reflected in frozen text and not implemented. Revision 02
> (`design/DESIGN-03-project-provisioning-02.md`) supersedes the reviewed draft
> (`design/DESIGN-03-project-provisioning.md`), which remains as evidence
> alongside `design/review/DESIGN-03-FINDINGS-01.md`. It specifies the
> direct-exercise authorization path (`PP-1`..`PP-13`), adds the capability
> `project.ceiling.set` and the decision kinds `SET_CEILING`, `GRANT_BUDGET` and
> `SET_POLICY`, adds transition-matrix §7.7 (seven rows over `Project` governance
> fields), and fixes the initial `Project` state at creation. It amends:
> - `authority-matrix.md:14` (`AX-3`), `:239`–`:253`, `:261`–`:267` — scoped to delegated grants
> - `authority-matrix.md:15`, `:16`, `:31`, `:51` — the ceiling does not bound direct exercise of five named capabilities, and of no others
> - `domain-model.md:153` (`P-INV-2`), `:408` (`A-INV-1`) — checked at grant time
> - `domain-model.md:693` — three added decision kinds
> - `transition-matrix.md:30`–`:39` — a project-governance-writes column on the axis-3 gate
> - `transition-matrix.md:172` — `required_evidence` and both policy columns, `Project` holder only
> - `evidence-model.md:176` — authority binding for held rather than delegated capabilities
> - `evidence-model.md:65` — `AUTHORITY` producers, for the `project.created` event only
>
> `HD-INV-3` and `evidence-model.md:95` are untouched. The current
> `create_project` (`controller.py:489`) contradicts the frozen design in six
> respects recorded in §1.1: it enters `ACTIVE` directly, sets `AUTONOMOUS` with
> no decision, leaves the ceiling empty and the budget zero on an `ACTIVE`
> project, names a `RUNTIME` creator, and leaves `policy_digest` absent. Until
> DESIGN-03's edits land in the frozen files, `design-01-frozen` remains the
> authoritative baseline.
