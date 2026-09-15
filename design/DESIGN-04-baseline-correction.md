# DESIGN-04 — Baseline Correction

| Property | Statement |
|---|---|
| Baseline | `design-01-frozen`, peeled commit `8fd51193da0f29efb60ddf906fc845bb0dcbaeb3`. Every `file:line` citation below resolves in that tag and was checked with `git show design-01-frozen:design/<file> \| sed -n '<line>p'`. |
| Kind | Proposal. No frozen file is edited by this document, no schema or implementation is changed, and nothing here is in effect. `design-01-frozen` remains the authoritative baseline until these edits land in the frozen files. |
| Corrects | Exactly five findings from [DESIGN-01-FINDINGS-02.md](review/DESIGN-01-FINDINGS-02.md), each with the disposition verified in [DESIGN-01-FINDINGS-02-VERIFY-01.md](review/DESIGN-01-FINDINGS-02-VERIFY-01.md): `D01-F02-001`, `-002` (retained half only), `-003`, `-004`, `-005`. |
| Does not correct | `-006` (REFUTED — no amendment). `-007`, `-008`, `-009`, `-010` (CONFIRMED, out of scope, §1.4). |
| Method | One numbered amendment per correction. Each names the frozen `file:line`, quotes the current frozen text verbatim, gives the proposed text, and names the finding it closes. Every rule stated carries a `basis` of **derived** (follows from frozen text cited in the same row) or **chosen** (does not). |
| Boundary | `design/review/` is immutable evidence and is read-only here. `src/` and `tests/` are untouched. No commit, tag, or other Git mutation. |
| Relationship to DESIGN-02 | None. `DESIGN-02`'s candidate-observation amendment is neither used nor referenced by any rule below. |
| Relationship to DESIGN-03 | `DESIGN-03` revision 02 specifies an overlapping authorization path for five project-holder capabilities. §5 states what it must change once this document freezes. |

---

## 1. Scope

### 1.1 The five findings corrected

Severity and blocking flags are the owner's, as recorded in `DESIGN-01-FINDINGS-02`; this
document reproduces them and changes none.

| id | severity | blocking | VERIFY-01 disposition | what this document corrects | amendments |
|---|---|---|---|---|---|
| `D01-F02-001` | `BLOCKER` | true | **CONFIRMED** — "The universal live-grant audit check cannot represent kernel self-holdings; project creation also has no admissible grant path." | The authority-binding check gains a conforming citation for a kernel self-holding and for a `HUMAN`-class act; `project.create` gains an exercise path. | 1, 2, 3 |
| `D01-F02-002` | `MAJOR` | false | **PARTIALLY CONFIRMED** — "First-append initialization is not specified by the ordinary append algorithm. However, lower event sequence does not require an earlier transaction commit; the claimed referential-integrity impossibility does not follow." | The retained half only: empty-chain initialization of `event_seq`/`event_head` and installation of the first event's project state. | 10, 11, 12 |
| `D01-F02-003` | `MAJOR` | true | **CONFIRMED** — "None of the four lifecycle capabilities survives activation's role intersection. Later activation records can exist, but cannot supply those grants." | `HUMAN`-class capabilities are exercised per act against a live decision instead of being routed through a run grant that can never carry them. | 1, 3 |
| `D01-F02-004` | `MAJOR` | true | **CONFIRMED** — "Mandatory activation, decision, escalation and audit-envelope evidence conflicts with the closed entity allow-list and, for the first three, event classification." | The `required_evidence` column is split into evidence cells (the `G-1` allow-list, unchanged) and prerequisite cells (`ACT`, `DEC(K)`, `ESC(s)`, a cited `AuditEvent`), with the reachability check applied per kind. | 7, 8, 9 |
| `D01-F02-005` | `MAJOR` | true | **CONFIRMED** — "Initial import and first contract creation require activation authority before the stage/contract/run structure supporting that authority has been established." | A project-scope grant form that does not require an activation, for `ORD` capabilities whose register row names `HUMAN_PRINCIPAL`. | 1, 4, 5, 6 |

### 1.2 `D01-F02-002` — what is retained, and what is not asserted

`VERIFY-01` refuted the referential-integrity half of this finding and this document does
not reassert it.

| half of the finding | status here |
|---|---|
| The ordinary append algorithm reads `event_seq` and `event_head` that have no prior event in a new project ([evidence-model.md:135](evidence-model.md#L135), [:136](evidence-model.md#L136), [domain-model.md:145](domain-model.md#L145), [:146](domain-model.md#L146)), and the genesis rule ([evidence-model.md:127](evidence-model.md#L127)) specifies event zero without specifying installation of the project/head state the later steps read. | **Retained and corrected** by amendments 10–12. |
| Satisfying `SNAP` before the creation event necessarily exposes a committed reference to a project that does not yet exist, so no mechanism satisfies both requirements. | **Not asserted.** `VERIFY-01` establishes that a single transaction containing ordered appends satisfies reference integrity and the lower-`seq` requirement together, and that [evidence-model.md:138](evidence-model.md#L138), [:139](evidence-model.md#L139) and [:143](evidence-model.md#L143) do not require one commit per event. No amendment below changes [domain-model.md:38](domain-model.md#L38), [:778](domain-model.md#L778), [:805](domain-model.md#L805), [transition-matrix.md:84](transition-matrix.md#L84), or the append protocol's atomicity and observability steps. |

### 1.3 `D01-F02-006` — refuted, no amendment

`VERIFY-01` records `D01-F02-006` as **REFUTED**: "Mutually referencing activation/run
records can be inserted with deferred reference checks, ordered events and one commit. The
separate `ACT` admissibility failure remains `D01-F02-004`." This document proposes no
amendment for it. [domain-model.md:273](domain-model.md#L273),
[:390](domain-model.md#L390), [:865](domain-model.md#L865) and
[transition-matrix.md:189](transition-matrix.md#L189)'s `ACT` precondition are untouched
(§3). The admissibility half that survives is `D01-F02-004`, corrected by amendments 7–9.

### 1.4 Out of scope: `-007`, `-008`, `-009`, `-010`

All four are **CONFIRMED** by `VERIFY-01`. None is addressed here, and no amendment below
touches the lines they cite. Each governs an operation that cannot be reached until after a
project has been provisioned, a stage materialized, a contract activated, and a run
executed — so none of them blocks provisioning, and none of them is repaired by the
provisioning corrections either.

| id | blocking (owner) | what it governs | why it does not block provisioning | when it must be closed |
|---|---|---|---|---|
| `D01-F02-007` | true | Reaching predecessor status `SUPERSEDED` from an `ACTIVE` predecessor and a `DRAFT` successor ([transition-matrix.md:269](transition-matrix.md#L269), [:266](transition-matrix.md#L266), [:273](transition-matrix.md#L273)). | Requires an already-`ACTIVE` contract and a second contract for the same stage. Provisioning authors and activates a first contract; it never replaces one. `VERIFY-01` also records a conforming replacement route — revoke the predecessor, then activate the successor — reaching `REVOKED`/`ACTIVE`; only the `SUPERSEDED` status is unreachable. | Before the first contract replacement is attempted. |
| `D01-F02-008` | true | Clearing a budget suspension or reworking a run whose allocation is exhausted or whose deadline has passed ([transition-matrix.md:172](transition-matrix.md#L172), [:206](transition-matrix.md#L206), [domain-model.md:284](domain-model.md#L284), [:287](domain-model.md#L287)). | Requires a run that has consumed its immutable allocation. No run exists during provisioning, and no worker may be dispatched while the project is `DRAFT` or `PLANNING` ([transition-matrix.md:435](transition-matrix.md#L435)). A new run remains available as a different holder. | Before the first run exhausts a budget dimension or passes its deadline. |
| `D01-F02-009` | false | Dispatch or apply on a run that still carries a non-terminal prior-epoch operation after reconciliation ([evidence-model.md:167](evidence-model.md#L167), [transition-matrix.md:359](transition-matrix.md#L359)). | Requires a controller restart with operations created under an earlier `controller_epoch`. A project being provisioned has dispatched nothing ([transition-matrix.md:435](transition-matrix.md#L435)), so the closure predicate has no old operation to reject. | Before the first controller restart that leaves a live operation behind. |
| `D01-F02-010` | true | The divergent-commit reconciliation row's `CR with verification = DIVERGED` against the `CR` expansion ([transition-matrix.md:358](transition-matrix.md#L358), [:73](transition-matrix.md#L73)). | Requires a `CommitIntent` that reached `APPLYING` and a landed revision. Provisioning applies no commit. | Before the first divergent apply is reconciled. |

---

## 2. Amendments

Twelve amendments. Each closes at least one of the five findings; an amendment that closes
none is not present.

### Amendment 1 — the authority-binding verification check

**Target** [evidence-model.md:176](evidence-model.md#L176) (§3.3 Verification).

**Current frozen text**

```
| authority binding | every event with `capability_used` has an `authority_ref` resolving to a live grant at `recorded_at` | same |
```

**Proposed text**

```
| authority binding | every event with `capability_used` resolves it at `recorded_at` by exactly one admissible form: a `KERNEL`-class capability requires `actor.actor_kind = RUNTIME` and absent `authority_ref` (kernel self-holding, `AX-7`); a `HUMAN`-class capability requires `authority_ref` to name the live `HumanDecision` that authorized this act (§5.2), except `decision.record`, which requires `actor.actor_kind = HUMAN` with `auth_method ∈ {SESSION, SIGNATURE, MTLS}` and absent `authority_ref` (`AX-15`); every other capability requires `authority_ref` to name a live grant carrying it — a `ContractActivationRecord` whose `granted_capabilities` contains it, or a project-scope grant decision per authority-matrix §5.3 | same |
```

**Closes** `D01-F02-001`, both halves. Also supplies the verification-side form the
citations introduced by amendments 3 and 6 must satisfy, so `D01-F02-003` and
`D01-F02-005` depend on it.

| id | rule | basis |
|---|---|---|
| `R1.1` | A `KERNEL`-class exercise cites no grant, because none can exist: the kernel holds these capabilities itself, non-delegably, and they are removed from a run's grant and never appear in `granted_capabilities`. | **derived** — [authority-matrix.md:18](authority-matrix.md#L18), [:34](authority-matrix.md#L34), [:245](authority-matrix.md#L245), [:266](authority-matrix.md#L266) |
| `R1.2` | That holding is represented by an absent `authority_ref` together with `actor.actor_kind = RUNTIME`. | **chosen** — the frozen text states the holding and supplies no citable representation of it. The rejected alternative is a new kernel authority record, which would also require amending `G-2` ([domain-model.md:888](domain-model.md#L888)); this form requires no new entity and leaves `G-2` untouched. |
| `R1.3` | A live grant for any other capability is an activation whose `granted_capabilities` contains the capability. | **derived** — [evidence-model.md:65](evidence-model.md#L65), [domain-model.md:392](domain-model.md#L392), [:888](domain-model.md#L888) |
| `R1.4` | A `HUMAN`-class exercise cites the live decision that authorized the act rather than a grant. | **chosen** for the sufficiency of a decision in place of a grant; **derived** that a decision is an admissible citation at all ([domain-model.md:790](domain-model.md#L790), [:888](domain-model.md#L888)). The frozen class legend requires a decision at exercise time ([authority-matrix.md:51](authority-matrix.md#L51)) and never says what the event cites. |
| `R1.5` | `decision.record` by an authenticated human cites nothing. | **chosen** — see `AX-15` in amendment 3; without it the first decision must be authorized by a decision. |
| `R1.6` | The four forms are exhaustive and mutually exclusive: exactly one applies to any event carrying `capability_used`. | **chosen** — replaces one universal clause with a closed case split. `AX-1` ([authority-matrix.md:12](authority-matrix.md#L12)) keeps the default at DENY for an event matching none of them. |

### Amendment 2 — the `authority_ref` field note

**Target** [domain-model.md:790](domain-model.md#L790) (§9.C `AuditEvent`).

**Current frozen text**

```
| `authority_ref` | `Id?` | N | I | R | activation or decision that permitted it |
```

**Proposed text**

```
| `authority_ref` | `Id?` | N | I | R | activation or decision that permitted it; absent exactly when `capability_used` is `KERNEL`-class or is `decision.record` (evidence-model §3.3) |
```

**Closes** `D01-F02-001`. The field is already optional, which is what makes the kernel
form expressible; without this note "absent" is indistinguishable from an omission the
check must reject.

| id | rule | basis |
|---|---|---|
| `R2.1` | `authority_ref` is absent exactly in the two self-holding cases and present in every other case where `capability_used` is present. | **chosen** — it records amendment 1's case split in the field table. `G-2`'s allow-list of citable entities is unchanged, because these two cases cite nothing. |

### Amendment 3 — direct exercise of a `HUMAN`-class capability (new authority-matrix §5.2)

**Target** insertion into `authority-matrix.md` immediately after
[authority-matrix.md:277](authority-matrix.md#L277), the last line of §5.1.

**Current frozen text at the anchor**

```
presence in `capability_request` change nothing.
```

**Proposed text** (inserted after that line; the anchor line itself is unchanged)

```
### 5.2 Direct exercise of a `HUMAN`-class capability

§5 and §5.1 resolve a contract's request into a run's grant. A `HUMAN`-class capability
never reaches a run that way: §4.1 denies every one of them to every role, and `D` is not
overridable. Such a capability is therefore not granted and not held. It is exercised, one
act at a time, against the decision the act requires.

| step | check |
|---|---|
| 1 | the capability is registered in §2 with class `HUMAN` and a `grantable by` column naming `HUMAN_PRINCIPAL` |
| 2 | the §3 mode gate permits it under `governance_mode` as it stands before the act |
| 3 | a `HumanDecision` authorizing this act is live at the moment of the act: `decision_state = VALID`, unexpired, nonce unconsumed, and `HD-INV-4` satisfied if it is snapshot-bound |
| 4 | that decision's `decision_kind` is the kind the row's verdict names, or `APPROVE` where the row's verdict is `AUTO` (`AX-14`) |
| 5 | `decided_by.actor_kind = HUMAN` with `auth_method ∈ {SESSION, SIGNATURE, MTLS}`, and the event's `actor` is that principal |
| 6 | the row's own preconditions and `required_evidence` hold, unchanged and unsubstituted (`AX-9`) |
| 7 | the event sets `authority_ref` to that `decision_id` (evidence-model §3.3) |

| id | rule |
|---|---|
| `AX-12` | Direct exercise grants nothing. The capability is never written into `HumanDecision.grants`, `ContractActivationRecord.granted_capabilities`, `WorkerInvocation.granted_capabilities` or `StageRun.effective_capabilities`, and no worker, adapter or kernel actor ever exercises it. §5, §5.1 and §4.1 are unchanged. |
| `AX-13` | Direct exercise is not bounded by `project.capability_ceiling`, which is the upper bound on grants. It is bounded by §2's register row, the §3 mode gate, and a live decision per act. For `project.create` this is forced: neither the project nor its ceiling exists when the act occurs. |
| `AX-14` | A `HUMAN`-class row whose policy verdict names a decision (`DECIDE(K)` or `CONFIRM`) is authorized by that decision. Where the verdict is `AUTO`, a `HumanDecision{kind: APPROVE}` over the row's subject is required instead; the frozen matrix contains exactly three such rows — `∅ → DRAFT` under `project.create`, `ABANDONED → ARCHIVED` under `project.archive`, and `∅ → VALID` under `decision.record`, the last exempt by `AX-15`. `AUTO` removes the policy engine's additional confirmation; it does not remove the class legend's exercise-time decision. |
| `AX-15` | `decision.record` is held by an authenticated `HUMAN_PRINCIPAL` and is neither granted nor directly exercised against a further decision. Recording one's own authenticated decision is the root of the authority chain; no other capability is self-held by a principal. |
| `AX-16` | The exercise decision for `project.create` names the identifier allocated for the project being created, and is made durable by the same store transaction that installs the `Project` record and its first two events (evidence-model §3.2). For every other capability the decision is recorded against an existing project. |
```

**Closes** `D01-F02-003` in full, and the `project.create` half of `D01-F02-001`.

| id | rule | basis |
|---|---|---|
| `R3.1` | A `HUMAN`-class capability requires a decision at the moment of exercise, not merely at grant time. | **derived** — [authority-matrix.md:51](authority-matrix.md#L51) |
| `R3.2` | No run grant can carry one: §4.1 denies every `HUMAN` capability to every role and `D` is not overridable by request, and activation intersects the role table before checking grantors. | **derived** — [authority-matrix.md:221](authority-matrix.md#L221), [:194](authority-matrix.md#L194), [:244](authority-matrix.md#L244) |
| `R3.3` | Therefore these capabilities are exercised per act and never held (`AX-12`). | **chosen** for the general statement; **derived** for worker roles from `R3.2`. The rejected alternative — a project-scope grant of a `HUMAN`-class capability — would place a capability that `AX-14` requires a fresh decision for into a standing set, and would make [authority-matrix.md:221](authority-matrix.md#L221) contingent. |
| `R3.4` | The authorizing decision is the one the row's verdict names. | **derived** — [transition-matrix.md:61](transition-matrix.md#L61), [:74](transition-matrix.md#L74) |
| `R3.5` | The frozen matrix's only `HUMAN`-class rows with an `AUTO` verdict are [transition-matrix.md:84](transition-matrix.md#L84), [:97](transition-matrix.md#L97) and [:393](transition-matrix.md#L393). | **derived** — enumerated over every row of the frozen matrix by its `required_capability` cell against the seventeen `HUMAN`-class register rows: [authority-matrix.md:58](authority-matrix.md#L58), [:59](authority-matrix.md#L59), [:61](authority-matrix.md#L61), [:62](authority-matrix.md#L62), [:63](authority-matrix.md#L63), [:64](authority-matrix.md#L64), [:65](authority-matrix.md#L65), [:66](authority-matrix.md#L66), [:78](authority-matrix.md#L78), [:79](authority-matrix.md#L79), [:107](authority-matrix.md#L107), [:109](authority-matrix.md#L109), [:110](authority-matrix.md#L110), [:125](authority-matrix.md#L125), [:134](authority-matrix.md#L134), [:143](authority-matrix.md#L143), [:146](authority-matrix.md#L146). Every other row carrying one of those capabilities carries `DECIDE(K)`; the four registered writes `project.mode.set`, `policy.set`, `budget.grant` and `budget.extend` appear in no row at all (§6). |
| `R3.6` | For those `AUTO` rows the required kind is `APPROVE`. | **chosen** — the matrix names no kind. `APPROVE` is in the closed enum ([domain-model.md:693](domain-model.md#L693)) and is what the sibling archive row already requires ([transition-matrix.md:96](transition-matrix.md#L96)). The rejected alternative — no decision on an `AUTO` row — leaves [authority-matrix.md:51](authority-matrix.md#L51) unsatisfied for `project.create` and `project.archive`, which is the state `D01-F02-003` records. |
| `R3.7` | An `APPROVE` decision over a project subject is snapshot-bound, so the `project.create` decision binds to the `SNAP` that row already requires, and an `ABANDONED → ARCHIVED` decision needs a current snapshot although that row's `required_evidence` is `—`. | **derived** — [domain-model.md:702](domain-model.md#L702), [:703](domain-model.md#L703), `HD-INV-4` [domain-model.md:719](domain-model.md#L719), [transition-matrix.md:84](transition-matrix.md#L84), [:97](transition-matrix.md#L97). Disclosed as a consequence of `R3.6`; no row's `required_evidence` cell is amended. |
| `R3.8` | `decision.record` is self-held by an authenticated principal (`AX-15`). | **chosen** — the frozen register makes it `HUMAN`-class with `HUMAN_PRINCIPAL` as grantor ([authority-matrix.md:143](authority-matrix.md#L143)), which under `R3.1` would require a prior decision to record the first decision. The rejected alternative is that regress. |
| `R3.9` | Direct exercise is not ceiling-bounded (`AX-13`). | **chosen** for every capability except `project.create`, where it is forced because the project and its ceiling do not exist at the moment of the act. The frozen ceiling is defined as the "upper bound on all grants" ([domain-model.md:141](domain-model.md#L141)) and `AX-11` calls it a narrowing of the candidate set for a grant ([authority-matrix.md:22](authority-matrix.md#L22)); direct exercise is not a grant. The containment that replaces it is `AX-12` plus steps 1–7. |
| `R3.10` | Direct exercise produces no `AUTHORITY` record and is not a promotion of the decision. | **derived** — [evidence-model.md:82](evidence-model.md#L82) classes the decision `DECISION`; only `grants`/`revokes` are `AUTHORITY` ([evidence-model.md:84](evidence-model.md#L84)); a directly exercised act leaves `grants` empty, so [evidence-model.md:95](evidence-model.md#L95) does not reach it. |
| `R3.11` | The event's actor is the deciding principal; a `RUNTIME`, `WORKER` or `ADAPTER` actor with a `HUMAN`-class `capability_used` is an integrity violation, not a transition. | **derived** — [authority-matrix.md:34](authority-matrix.md#L34) (the kernel cannot self-grant a non-`KERNEL` capability), `HD-INV-1` [domain-model.md:714](domain-model.md#L714) |
| `R3.12` | The `project.create` decision and the project record are made durable together (`AX-16`). | **chosen** — [domain-model.md:38](domain-model.md#L38) enforces referential integrity without prescribing when each reference is checked, so one transaction may contain the decision, the project, the snapshot and both events. This is the same transactional reading `VERIFY-01` used to refute the second half of `D01-F02-002`. |

### Amendment 4 — `AX-3`

**Target** [authority-matrix.md:14](authority-matrix.md#L14) (§0 Axioms).

**Current frozen text**

```
| `AX-3` | Grants are per `ContractActivationRecord`, scoped to one `StageRun`, and frozen for that run's life. |
```

**Proposed text**

```
| `AX-3` | A grant is realized in exactly one of two forms. A **run grant** is per `ContractActivationRecord`, scoped to one `StageRun`, and frozen for that run's life (§5). A **project grant** is realized directly by a live `HumanDecision{kind: GRANT_CAPABILITY}` with `scope = PROJECT`, is scoped to one `Project`, carries only `ORD` capabilities whose §2 `grantable by` column names `HUMAN_PRINCIPAL`, and exists for the acts that precede any activation (§5.3). No third form of grant exists, and a `HUMAN`-class capability is granted by neither (§5.2, `AX-12`). |
```

**Closes** `D01-F02-005`.

| id | rule | basis |
|---|---|---|
| `R4.1` | A second grant form exists, scoped to a project instead of a run. | **chosen** — the frozen axiom admits one form, which is what makes the first import and the first contract authoring circular: both are prerequisites of the structure their own grant would need ([transition-matrix.md:85](transition-matrix.md#L85), [:117](transition-matrix.md#L117), [:265](transition-matrix.md#L265), [domain-model.md:316](domain-model.md#L316), [:388](domain-model.md#L388), [:390](domain-model.md#L390)). |
| `R4.2` | The project form carries only `ORD` capabilities, and only those whose register row names `HUMAN_PRINCIPAL`. | **chosen** — `HUMAN`-class capabilities are excluded because `AX-12` exercises them per act; a capability whose only grantor is `ROLE_DEFAULT` is excluded because there is no role outside an invocation ([authority-matrix.md:190](authority-matrix.md#L190)); a `POLICY_ENGINE` grant is excluded by `R6.6`. |
| `R4.3` | The two forms are exhaustive. | **chosen** — with `AX-1` ([authority-matrix.md:12](authority-matrix.md#L12)) this keeps any other claimed grant at DENY. |

### Amendment 5 — the `DECISION → AUTHORITY` promotion rule

**Target** [evidence-model.md:95](evidence-model.md#L95) (§2.2 Promotion rules).

**Current frozen text**

```
| `DECISION` → `AUTHORITY` | a `HumanDecision` with non-empty `grants` | the grant is realized only through an activation record |
```

**Proposed text**

```
| `DECISION` → `AUTHORITY` | a `HumanDecision` with non-empty `grants` | a run grant is realized through an activation record; a project grant is realized by the decision itself and is never written into an activation (`AX-3`, authority-matrix §5.3). A decision with empty `grants` promotes to nothing: it authorizes its own act and delegates no capability (authority-matrix §5.2) |
```

**Closes** `D01-F02-005`.

| id | rule | basis |
|---|---|---|
| `R5.1` | A project grant is realized by the granting decision, with no activation record. | **chosen** — it is the promotion-rule half of `R4.1`. The frozen clause is the strongest statement that every realized grant passes through an activation, and `VERIFY-01` cites it as the reason the bootstrap is circular. |
| `R5.2` | A decision with empty `grants` promotes to nothing and is outside this row. | **derived** — the row's own predicate is "non-empty `grants`"; [evidence-model.md:82](evidence-model.md#L82) and [:84](evidence-model.md#L84) class the record `DECISION` and only the capability delta `AUTHORITY`. Stated to keep amendment 3 visibly outside this row. |

### Amendment 6 — project-scope grants (new authority-matrix §5.3)

**Target** insertion into `authority-matrix.md` immediately after the §5.2 block inserted
by amendment 3, i.e. after [authority-matrix.md:277](authority-matrix.md#L277).

**Current frozen text at the anchor**

```
presence in `capability_request` change nothing.
```

**Proposed text** (inserted after amendment 3's §5.2)

```
### 5.3 Project-scope grants

The acts that establish a project's structure cannot be authorized by §5: the first
`roadmap.import` supplies the stages, and the first `contract.author` supplies the
contract, that an activation would have to reference. A project grant authorizes exactly
those acts.

| step | operation |
|---|---|
| 1 | `P₀` = the `grants` set of a `HumanDecision{kind: GRANT_CAPABILITY, scope: PROJECT}` that is live at the moment of the act: `decision_state = VALID`, unexpired, nonce unconsumed |
| 2 | `P₁ = P₀ ∩ project.capability_ceiling`; differences recorded `NOT_IN_CEILING` |
| 3 | `P₂ = P₁` minus capabilities denied by the §3 mode gate; recorded `MODE_FORBIDDEN` |
| 4 | `P₃ = P₂` minus every `KERNEL`, `HUMAN` and `NEVER` capability; recorded `NEVER_GRANTABLE` |
| 5 | `P₄ = P₃` minus every capability whose §2 `grantable by` column does not name `HUMAN_PRINCIPAL`; recorded `NO_GRANTOR` |
| 6 | the granted set is `P₄`. §4.1 is not applied: it is the per-`WorkerInvocation` role table and a project grant reaches no invocation |

| id | rule |
|---|---|
| `AX-17` | A project grant is never copied into `ContractActivationRecord.granted_capabilities`, `WorkerInvocation.granted_capabilities` or `StageRun.effective_capabilities`. A worker's authority remains exactly `AX-3`'s run grant, resolved by §5 and bounded by `AX-4`. |
| `AX-18` | An event exercising a project grant sets `authority_ref` to the granting `decision_id`, which must be live at `recorded_at` (evidence-model §3.3). `G-2` is unchanged: a `HumanDecision` is already an admissible authority citation. |
| `AX-19` | A `GRANT_CAPABILITY` decision is not recorded for a transition and is not consumed by exercising the grant. It ends only as §1.1 states: `expires_at`, the `scope` boundary, or `decision_state` leaving `VALID`. An exercise-time decision under §5.2 is consumed by the transition it discharges. |
| `AX-20` | `POLICY_ENGINE` is not an admissible grantor of a project grant. An `AUTONOMOUS` project's first import and first contract still require a live human grant, exactly as `roadmap.writeback` does in either mode (§5.1). |
```

**Closes** `D01-F02-005`.

| id | rule | basis |
|---|---|---|
| `R6.1` | The first import and the first contract authoring can be authorized by a project grant, with no activation. | **derived** that both capabilities name `HUMAN_PRINCIPAL` as a grantor and are `ORD` — [authority-matrix.md:74](authority-matrix.md#L74), [:86](authority-matrix.md#L86); **chosen** that a project grant authorizes them. |
| `R6.2` | The grant is bounded by `project.capability_ceiling`. | **derived** — [domain-model.md:141](domain-model.md#L141) makes the ceiling the upper bound on all grants, and a project grant is a grant. |
| `R6.3` | It is bounded by the §3 mode gate and excludes `KERNEL` and `NEVER` capabilities. | **chosen** — mirrors §5 steps 3 and 5 ([authority-matrix.md:243](authority-matrix.md#L243), [:245](authority-matrix.md#L245)) for a resolution the frozen §5 does not cover. `AX-6` and `AX-7` independently forbid the excluded classes ([authority-matrix.md:17](authority-matrix.md#L17), [:18](authority-matrix.md#L18)). |
| `R6.4` | §4.1 is not applied. | **derived** — §4.1 is the grant table "per `WorkerInvocation`" ([authority-matrix.md:190](authority-matrix.md#L190)); a project grant reaches no invocation, by `AX-17`. |
| `R6.5` | A `GRANT_CAPABILITY` decision survives the exercise of its grant. | **derived** — [transition-matrix.md:394](transition-matrix.md#L394) consumes a decision that "discharged the transition it was recorded for", and [authority-matrix.md:41](authority-matrix.md#L41) names the three ways a `HUMAN_DECISION` grant ends. `HD-INV-3` ([domain-model.md:718](domain-model.md#L718)) is untouched, and continues to consume the per-act decisions of §5.2. |
| `R6.6` | `POLICY_ENGINE` cannot grant at project scope (`AX-20`). | **chosen** — a persisted policy evaluation is not among the entities `G-2` admits as an authority citation ([domain-model.md:888](domain-model.md#L888)), so admitting it would require amending `G-2` as well. The human path is available in both modes, so no row is left unreachable by this restriction. |
| `R6.7` | A project grant carries no `HUMAN`-class capability. | **chosen** — those are exercised per act under §5.2 (`R3.3`). |

### Amendment 7 — `G-1`

**Target** [domain-model.md:887](domain-model.md#L887) (§12 Global invariants).

**Current frozen text**

```
| `G-1` | No entity outside `{ValidationReceipt, WorkerReceipt, CommitReceipt, ReviewAttestation, RealitySnapshot}` may be cited as `required_evidence`. A `Review` is never cited directly: the kernel-minted `ReviewAttestation` is what the `RVW(v)` token in `transition-matrix.md` resolves to, so a judgmental criterion is discharged by the kernel's measurement of the review, not by the reviewer's own verdict. |
```

**Proposed text**

```
| `G-1` | A `required_evidence` cell is of exactly one of two kinds. An **evidence cell** cites a record that measures reality, and no entity outside `{ValidationReceipt, WorkerReceipt, CommitReceipt, ReviewAttestation, RealitySnapshot}` may be cited there; a `Review` is never cited directly, the kernel-minted `ReviewAttestation` being what the `RVW(v)` token in `transition-matrix.md` resolves to, so a judgmental criterion is discharged by the kernel's measurement of the review, not by the reviewer's own verdict. A **prerequisite cell** cites a governance record the row requires to exist — `ACT`, `DEC(K)`, `ESC(s)`, a named `ContractActivationRecord` or revocation record, or the discharged transition's own `AuditEvent`. A prerequisite cell discharges no criterion and proves no satisfaction (`AX-9`); only an evidence cell does. No record satisfies both kinds. |
```

**Closes** `D01-F02-004`.

| id | rule | basis |
|---|---|---|
| `R7.1` | The `required_evidence` column already holds records of both kinds. | **derived** — [transition-matrix.md:189](transition-matrix.md#L189) (`ACT`), [:266](transition-matrix.md#L266) (`ContractActivationRecord`), [:141](transition-matrix.md#L141) (`DEC(REJECT)`), [:128](transition-matrix.md#L128) (`ESC(OPEN)`), [:394](transition-matrix.md#L394) (`AuditEvent`), against the five-entity allow-list and the classifications at [evidence-model.md:82](evidence-model.md#L82)–[:85](evidence-model.md#L85). |
| `R7.2` | The five-entity allow-list is unchanged, and is now stated of evidence cells. | **derived** — the allow-list and the `Review`/`ReviewAttestation` clause are carried over verbatim from the frozen text. |
| `R7.3` | A prerequisite cell never discharges a criterion or substitutes for evidence. | **derived** — `AX-9` [authority-matrix.md:20](authority-matrix.md#L20); `HD-INV-2` [domain-model.md:716](domain-model.md#L716) already says an uninformed approval satisfies no `required_evidence`. |
| `R7.4` | Splitting the column is the correction, rather than adding these record types to the allow-list. | **chosen** — the rejected alternative admits an activation, a decision and an escalation as evidence of satisfaction, which is the confusion the epistemic taxonomy exists to prevent ([evidence-model.md:55](evidence-model.md#L55)–[:65](evidence-model.md#L65)). |

### Amendment 8 — the evidence-reachability verification check

**Target** [evidence-model.md:178](evidence-model.md#L178) (§3.3 Verification).

**Current frozen text**

```
| evidence reachability | every `required_evidence` cited by a transition event resolves to an event of class `EVIDENCE` with `seq` lower than the transition's | `INTEGRITY_VIOLATION` |
```

**Proposed text**

```
| evidence reachability | every `required_evidence` cited by a transition event resolves to an earlier event in the same project, with `seq` lower than the transition's: an evidence cell (`G-1`) to an event of class `EVIDENCE`, and a prerequisite cell (`G-1`) to an event of the class its record carries — `AUTHORITY` for an activation, `DECISION` for a decision, `CLAIM` for an escalation, and any class for a cited `AuditEvent` | `INTEGRITY_VIOLATION` |
```

**Closes** `D01-F02-004`.

| id | rule | basis |
|---|---|---|
| `R8.1` | The lower-`seq` requirement applies to both kinds of cell, unchanged. | **derived** — carried over from the frozen check. |
| `R8.2` | The class test is per cell kind, using the frozen classification of each record. | **chosen** as a check; **derived** in its content — [evidence-model.md:83](evidence-model.md#L83) (activation is `AUTHORITY`), [:82](evidence-model.md#L82) (decision is `DECISION`), [:85](evidence-model.md#L85) (escalation is `CLAIM`), [:86](evidence-model.md#L86) (the `AuditEvent` is the envelope and carries one of the four). |
| `R8.3` | A cited `AuditEvent` is exempt from the class test. | **derived** — it is the envelope, not a class ([evidence-model.md:86](evidence-model.md#L86)); the row that cites one cites the discharged transition's own event ([transition-matrix.md:394](transition-matrix.md#L394)). |

### Amendment 9 — the `required_evidence` column semantics

**Target** [transition-matrix.md:48](transition-matrix.md#L48) (§1 Column semantics).

**Current frozen text**

```
| `required_evidence` | receipt/snapshot classes that must exist and be current; `—` means none |
```

**Proposed text**

```
| `required_evidence` | records that must exist and be current, of the two kinds `G-1` distinguishes: an evidence cell (receipt or snapshot) discharges the row's criterion, a prerequisite cell (`ACT`, `DEC(K)`, `ESC(s)`, a named activation or revocation record, an `AuditEvent`) is required to exist and discharges nothing; `—` means none |
```

**Closes** `D01-F02-004`.

| id | rule | basis |
|---|---|---|
| `R9.1` | The column holds more than receipts and snapshots. | **derived** — the frozen cells listed in `R7.1`. The current wording describes only one of the two kinds its own table contains. |
| `R9.2` | The two kinds are named here as they are in `G-1`. | **chosen** — wording, so the column legend and the invariant agree. |

### Amendment 10 — genesis installs the project's chain state

**Target** [evidence-model.md:128](evidence-model.md#L128) (§3.1, step 6).

**Current frozen text**

```
| 6 | `Project.event_head = event_hash` of the highest `seq`; updated in the same atomic write as the append |
```

**Proposed text**

```
| 6 | `Project.event_head = event_hash` of the highest `seq`; updated in the same atomic write as the append. At `seq = 0` that write also installs the `Project` record and initializes `event_seq = 0`: a project and its first event become durable together, and no reader ever observes a project whose chain state is uninitialized |
```

**Closes** `D01-F02-002` (retained half).

| id | rule | basis |
|---|---|---|
| `R10.1` | The first append installs the project record and initializes `event_seq` and `event_head` in one atomic write. | **chosen** — the frozen genesis rule specifies event zero's `prev_event_hash` ([evidence-model.md:127](evidence-model.md#L127)) and step 6 specifies the head update for an existing chain; neither specifies the installation, which is the gap `VERIFY-01` retains. |
| `R10.2` | `event_head` and `event_seq` remain derived, runtime-owned project fields. | **derived** — [domain-model.md:145](domain-model.md#L145), [:146](domain-model.md#L146); no field table is amended. |
| `R10.3` | The `schema_version` term in the genesis preimage is the domain-model `SCHEMA_VERSION` that feeds the genesis hash, not the storage schema version (`PRAGMA user_version`, `STORAGE_VERSION`). | **derived** — [evidence-model.md:127](evidence-model.md#L127) is a rule about the domain model's event chain and names no storage concept. Line 127 is **not** amended by this document; this rule exists so the amendment above cannot be read as conflating the two versions. |

### Amendment 11 — append step 2 on an empty chain

**Target** [evidence-model.md:135](evidence-model.md#L135) (§3.2, step 2).

**Current frozen text**

```
| 2 | reserve `seq = event_seq + 1` under a per-project lock | contention retries; `seq` is never skipped |
```

**Proposed text**

```
| 2 | reserve `seq = event_seq + 1` under a per-project lock; for a project with no prior event, `event_seq` is unset and the reserved value is `seq = 0` | contention retries; `seq` is never skipped |
```

**Closes** `D01-F02-002` (retained half).

| id | rule | basis |
|---|---|---|
| `R11.1` | The empty-chain case reserves `seq = 0` rather than reading an unset `event_seq`. | **chosen** — the frozen step reads a derived field that has no value before the first event. `seq = 0` is what the genesis rule requires of that event ([evidence-model.md:127](evidence-model.md#L127)), and gaplessness from 0 is unchanged ([evidence-model.md:174](evidence-model.md#L174), [domain-model.md:779](domain-model.md#L779)). |
| `R11.2` | The per-project lock and the no-skip rule are unchanged, including for the first append. | **derived** — carried over; [evidence-model.md:190](evidence-model.md#L190) is untouched. |

### Amendment 12 — append step 3 on an empty chain

**Target** [evidence-model.md:136](evidence-model.md#L136) (§3.2, step 3).

**Current frozen text**

```
| 3 | read `prev_event_hash = event_head` | — |
```

**Proposed text**

```
| 3 | read `prev_event_hash = event_head`; at `seq = 0`, `event_head` is unset and `prev_event_hash` is the §3.1 genesis constant instead |
```

**Closes** `D01-F02-002` (retained half).

| id | rule | basis |
|---|---|---|
| `R12.1` | The first event's `prev_event_hash` comes from the genesis formula, not from `event_head`. | **derived** — [evidence-model.md:127](evidence-model.md#L127) and [domain-model.md:780](domain-model.md#L780) already say `seq = 0` takes the genesis constant; the append step does not, which is the residue. |

---

## 3. Frozen locations this document leaves untouched

Every location a reader might reasonably expect these five corrections to touch, and why it
is not touched. Nothing outside amendments 1–12 is proposed for change.

| frozen location | current content, in brief | why untouched |
|---|---|---|
| [authority-matrix.md:12](authority-matrix.md#L12) `AX-1` | Default DENY; absence of a rule is never permission. | Load-bearing for `R1.6` and `R4.3`: an act matching no admissible authority form stays denied. |
| [authority-matrix.md:15](authority-matrix.md#L15) `AX-4` | `granted ⊆ capability_request ∩ role_default ∩ mode_allowed ∩ ceiling`. | Governs run grants, which are unchanged. `AX-17` keeps project grants out of the sets it bounds. |
| [authority-matrix.md:16](authority-matrix.md#L16) `AX-5` | No principal grants what it does not hold, except `HUMAN_PRINCIPAL` within the ceiling. | Unaffected: direct exercise delegates nothing (`R3.10`), and a project grant is a `HUMAN_PRINCIPAL` grant within the ceiling (`R6.2`). |
| [authority-matrix.md:18](authority-matrix.md#L18) `AX-7` | `KERNEL` capabilities are kernel-held, non-delegable, never in an invocation's grants. | This is the holding amendment 1 represents; it needs no change, only a citable form. |
| [authority-matrix.md:20](authority-matrix.md#L20) `AX-9` | A capability never substitutes for `required_evidence`. | Load-bearing for `R7.3`; the `G-1` split preserves it rather than relaxing it. |
| [authority-matrix.md:22](authority-matrix.md#L22) `AX-11` | Bounding is not granting. | Unchanged, and the reason `AX-13` and `R6.2` treat the ceiling as a bound on grants only. |
| [authority-matrix.md:34](authority-matrix.md#L34) | `RUNTIME_KERNEL` grants `KERNEL` capabilities to itself only; cannot self-grant non-`KERNEL`. | Unchanged, and the basis for `R3.11`. The kernel gains no `HUMAN`-class capability anywhere in this document. |
| [authority-matrix.md:51](authority-matrix.md#L51) | `HUMAN` class requires a decision at exercise time, not merely at grant time. | Unchanged; §5.2 implements it. `AX-14` is how it is satisfied on the three `AUTO` rows. |
| [authority-matrix.md:58](authority-matrix.md#L58)–[:68](authority-matrix.md#L68), [:74](authority-matrix.md#L74)–[:80](authority-matrix.md#L80), [:86](authority-matrix.md#L86)–[:94](authority-matrix.md#L94), [:100](authority-matrix.md#L100)–[:147](authority-matrix.md#L147) | The capability register. | No class, grantor, default or mode restriction changes. `AX-15` states a holding the register does not describe, exactly as `AX-7` states one for the kernel without a register change. |
| [authority-matrix.md:143](authority-matrix.md#L143) | `decision.record`, `HUMAN`, grantable by `HUMAN_PRINCIPAL`, default DENY. | Untouched on purpose. `AX-15` adds a holding; the row keeps describing grantability, and the default stays DENY for anyone who is not the authenticated principal recording their own decision. |
| [authority-matrix.md:155](authority-matrix.md#L155)–[:173](authority-matrix.md#L173) | The §3 mode gate, including `project.create` DENY in `AUTONOMOUS`. | Applied unchanged by §5.2 step 2 and §5.3 step 3. No capability becomes available in a mode that denied it. |
| [authority-matrix.md:194](authority-matrix.md#L194) | Every §4.1 cell is bounded by `AX-4`; `D` is not overridable by request. | Load-bearing for `R3.2`. |
| [authority-matrix.md:203](authority-matrix.md#L203), [:206](authority-matrix.md#L206) | `C` cells for `proc.exec.arbitrary` and `secret.read`. | Not touched. These `HUMAN`-class capabilities have `C` cells while [:221](authority-matrix.md#L221) denies every `HUMAN` capability to every role. That tension is frozen, predates this document, and is not one of the five findings; `AX-12` neither resolves nor relies on it, since §5 already reaches `D` for them through [:221](authority-matrix.md#L221) and [:194](authority-matrix.md#L194). |
| [authority-matrix.md:221](authority-matrix.md#L221) | Every `HUMAN` capability is `D` for every role. | Unchanged, and the reason a `HUMAN`-class capability cannot be delivered by a grant at all (`R3.2`). No worker gains one. |
| [authority-matrix.md:239](authority-matrix.md#L239)–[:277](authority-matrix.md#L277) | §5 resolution algorithm and §5.1 admissible grantors. | Unchanged. §5.2 and §5.3 are additive sections after §5.1; step 5's removal of `KERNEL` capabilities and [:266](authority-matrix.md#L266)'s "never for a run's grant" both stand. |
| [authority-matrix.md:245](authority-matrix.md#L245), [:266](authority-matrix.md#L266) | `KERNEL` capabilities removed at step 5; `RUNTIME_KERNEL` never an admissible grantor of a run grant. | Amendment 1 represents the kernel holding without a grant, so neither line needs to change. |
| [domain-model.md:38](domain-model.md#L38) | `Ref<E>`: referential integrity enforced. | Untouched. `VERIFY-01` refuted the claim that this forces a dangling committed reference, and `R3.12` relies on the timing of checks being unspecified rather than on a change here. |
| [domain-model.md:141](domain-model.md#L141) | `capability_ceiling`, "upper bound on all grants". | Untouched; the basis for `R6.2` and for `AX-13`'s limit. No operation writing this field is specified here — see §6. |
| [domain-model.md:145](domain-model.md#L145), [:146](domain-model.md#L146) | `event_head`, `event_seq`: derived, mutable, runtime. | Untouched. Initialization belongs to the append protocol, not the field table. |
| [domain-model.md:273](domain-model.md#L273), [:390](domain-model.md#L390), [:865](domain-model.md#L865) | `StageRun.activation_id`, `ContractActivationRecord.run_id`, the 1:1 relation. | Untouched: `D01-F02-006` is REFUTED. |
| [domain-model.md:284](domain-model.md#L284), [:285](domain-model.md#L285), [:287](domain-model.md#L287) | Run `budget_allocated` immutable, `budget_used` append-only, `deadline_at` immutable. | Untouched: `D01-F02-008` is out of scope (§1.4). |
| [domain-model.md:691](domain-model.md#L691)–[:712](domain-model.md#L712) | `HumanDecision` fields, including `project_id`, `decision_kind`, `scope`, `snapshot_bound`, `nonce`. | No field, type, or enum changes. `decision_kind` stays the closed enum; §5.2 and §5.3 use `APPROVE` and `GRANT_CAPABILITY` from it. No new entity and no profile requiring a schema change. |
| [domain-model.md:714](domain-model.md#L714)–[:727](domain-model.md#L727) | `HD-INV-1` … `HD-INV-4`. | Untouched. `AX-19` reads `HD-INV-3` alongside [transition-matrix.md:394](transition-matrix.md#L394) rather than excepting it; `HD-INV-4` continues to stale a snapshot-bound decision, including the ones `R3.7` identifies. |
| [domain-model.md:789](domain-model.md#L789) | `capability_used` required for state-changing events. | Untouched. Amendment 1 changes how it is discharged, not whether it is required. |
| [domain-model.md:797](domain-model.md#L797) `AE-INV-2` | Every transition emits an event before the new state is observable. | Untouched, including for the creation transaction: `R3.12` and `R10.1` make records durable together, and publication still follows emission. |
| [domain-model.md:805](domain-model.md#L805), [:778](domain-model.md#L778) | `RealitySnapshot.project_id`, `AuditEvent.project_id` as enforced `Ref<Project>`. | Untouched, for the same reason as [:38](domain-model.md#L38). |
| [domain-model.md:888](domain-model.md#L888) `G-2` | Only `HumanDecision` and `ContractActivationRecord` may be cited as `required_capability` authority. | Untouched, and deliberately: every citation this document introduces is one of those two, or is absent. This is why `R1.2` chose absence over a new kernel record and `R6.6` excluded a policy-evaluation citation. |
| [domain-model.md:890](domain-model.md#L890) `G-4`, [authority-matrix.md:13](authority-matrix.md#L13) `AX-2` | Every state-changing operation names exactly one capability; absence ⇒ DENY. | Untouched. No act below is performed without a named capability. |
| [evidence-model.md:55](evidence-model.md#L55)–[:86](evidence-model.md#L86) | The four-class taxonomy and the record classification table. | Untouched. Amendment 8's class tests read this table; amendment 7 keeps decisions, activations and escalations out of the evidence role rather than reclassifying them. |
| [evidence-model.md:127](evidence-model.md#L127) | The genesis `prev_event_hash` formula over `project_id ‖ 0x00 ‖ schema_version`. | Untouched. See `R10.3`: the `schema_version` term is the domain-model `SCHEMA_VERSION`, not `STORAGE_VERSION`. |
| [evidence-model.md:138](evidence-model.md#L138), [:139](evidence-model.md#L139), [:143](evidence-model.md#L143) | Atomic event/head persistence, observability only after persistence, and the external-effect exclusion. | Untouched. `VERIFY-01`'s countersequence needs no change to them, and amendments 10–12 add only the empty-chain case. |
| [evidence-model.md:167](evidence-model.md#L167) | The reconciliation-closure check. | Untouched: `D01-F02-009` is out of scope (§1.4). |
| [evidence-model.md:173](evidence-model.md#L173)–[:175](evidence-model.md#L175), [:177](evidence-model.md#L177) | Chain continuity, gaplessness, payload binding, monotonic time. | Untouched. Only the two checks named in amendments 1 and 8 change. |
| [evidence-model.md:190](evidence-model.md#L190) | Appends serialize on the per-project lock. | Untouched; serial appends inside one transaction remain serial. |
| [transition-matrix.md:49](transition-matrix.md#L49) | `required_capability`: the single capability the actor must hold. | Untouched. A `HUMAN`-class capability is exercised rather than held (`AX-12`), which is a statement about how the column is satisfied, not a change to the column. |
| [transition-matrix.md:58](transition-matrix.md#L58)–[:62](transition-matrix.md#L62) | The policy verdict vocabulary, including `AUTO`. | Untouched. `AX-14` reads `AUTO` as the policy engine's verdict, leaving the class legend's requirement in force; the vocabulary entry is unchanged. |
| [transition-matrix.md:64](transition-matrix.md#L64)–[:76](transition-matrix.md#L76) | The evidence shorthand: `SNAP`, `VR`, `RVW`, `WR`, `CR`, `DEC(K)`, `ACT`, `ESC(s)`. | No token is redefined. `G-1` classifies the cells that use them; `CR` in particular is untouched, since `D01-F02-010` is out of scope. |
| [transition-matrix.md:84](transition-matrix.md#L84) | `∅ → DRAFT`: `created_by.actor_kind = HUMAN`, `SNAP`, `project.create`, `AUTO`/`DENY`. | No cell is amended. Its `SNAP` requirement stands, and `AX-14`/`AX-16` supply the authority the row could not previously cite. |
| [transition-matrix.md:85](transition-matrix.md#L85), [:117](transition-matrix.md#L117), [:265](transition-matrix.md#L265) | The rows requiring `roadmap.import` and `contract.author`. | No cell is amended; amendment 6 supplies the grant form they lacked. |
| [transition-matrix.md:86](transition-matrix.md#L86)–[:97](transition-matrix.md#L97), [:119](transition-matrix.md#L119)–[:142](transition-matrix.md#L142), [:208](transition-matrix.md#L208), [:336](transition-matrix.md#L336) | The fifteen `HUMAN` lifecycle rows of `D01-F02-003`'s inventory, plus `finding.waive`. | No cell is amended. Each becomes performable through §5.2 with the decision its own verdict already names. |
| [transition-matrix.md:108](transition-matrix.md#L108)–[:113](transition-matrix.md#L113) | The startup exception for `∅ → PENDING` and `PENDING → READY`. | Untouched, and not widened. This document adds no row to `PLANNING`. |
| [transition-matrix.md:189](transition-matrix.md#L189), [:266](transition-matrix.md#L266), [:141](transition-matrix.md#L141), [:128](transition-matrix.md#L128), [:394](transition-matrix.md#L394) | The five `required_evidence` cells `D01-F02-004` names. | No cell is amended. They become admissible through `G-1` and the reachability check, which is what keeps the correction in one place instead of five. |
| [transition-matrix.md:269](transition-matrix.md#L269), [:273](transition-matrix.md#L273), [:172](transition-matrix.md#L172), [:206](transition-matrix.md#L206), [:358](transition-matrix.md#L358), [:359](transition-matrix.md#L359) | Supersession, budget-suspension clearing, run rework, divergent reconciliation. | Untouched: `-007`, `-008`, `-010` and `-009` are out of scope (§1.4). |
| [transition-matrix.md:393](transition-matrix.md#L393) | `∅ → VALID` under `decision.record`, verdict `AUTO`. | No cell is amended; `AX-15` supplies the holding, and the row's `AUTO` stays `AUTO`. |
| [transition-matrix.md:435](transition-matrix.md#L435) | No worker dispatch during `DRAFT` or `PLANNING`. | Untouched, and relied on by §1.4. |
| `design/schema/**`, [roadmap_adapter.md](roadmap_adapter.md), [worker_provider.md](worker_provider.md) | Frozen schemas and adapter interfaces. | No amendment reaches them. In particular the adapter's `roadmap.import` requirement ([roadmap_adapter.md:56](roadmap_adapter.md#L56), [:57](roadmap_adapter.md#L57)) is satisfied by amendment 6 without an interface change. |

---

## 4. Chosen and derived

Convention: every rule above carries a `basis` cell. **Derived** means the rule follows from
frozen text cited in that same cell. **Chosen** means it does not — the frozen text is
silent, or says something the rule replaces. A rule with both marks says which half is
which. A derivation is never claimed for a choice, and a citation in a `chosen` cell is
context for the choice, not its proof.

The choices a reviewer should attack first, by id, with no restatement of their content:

| chosen rule | one-line label |
|---|---|
| `R1.2` | Kernel holding is represented by an absent `authority_ref`, not a record. |
| `R1.4` | A live decision is sufficient authority for a `HUMAN`-class act. |
| `R1.5`, `R3.8` | `decision.record` is self-held by an authenticated principal. |
| `R1.6` | The four authority forms are a closed case split. |
| `R3.3`, `R6.7` | `HUMAN`-class capabilities are never held, in any set. |
| `R3.6` | `APPROVE` is the kind required on the two `AUTO` rows. |
| `R3.9` | Direct exercise is not ceiling-bounded (forced only for `project.create`). |
| `R3.12` | Decision, project and first events are made durable in one transaction. |
| `R4.1`, `R4.2`, `R4.3`, `R5.1` | A project-scope grant form exists, carrying `ORD` human-grantable capabilities only. |
| `R6.3` | Project grants take §5's mode gate and class exclusions. |
| `R6.6` | `POLICY_ENGINE` cannot grant at project scope. |
| `R7.4` | `required_evidence` is split rather than the `G-1` allow-list widened. |
| `R8.2` | A per-kind class test replaces the universal `EVIDENCE` test. |
| `R9.2` | The column legend adopts `G-1`'s two names. |
| `R10.1`, `R11.1` | The first append installs the project's chain state and reserves `seq = 0`. |

Derived rules, by id: `R1.1`, `R1.3`, `R2.1` (of amendment 1's case split), `R3.1`, `R3.2`,
`R3.4`, `R3.5`, `R3.7`, `R3.10`, `R3.11`, `R5.2`, `R6.1` (grantor half), `R6.2`, `R6.4`,
`R6.5`, `R7.1`, `R7.2`, `R7.3`, `R8.1`, `R8.3`, `R9.1`, `R10.2`, `R10.3`, `R11.2`, `R12.1`.

---

## 5. What `DESIGN-03` must change once this freezes

`DESIGN-03` revision 02 ([DESIGN-03-project-provisioning-02.md](DESIGN-03-project-provisioning-02.md))
specifies **direct exercise** for five project-holder capabilities, against the same frozen
baseline, and amends [evidence-model.md:176](evidence-model.md#L176) itself. Amendments 1
and 3 above generalize that mechanism to every `HUMAN`-class capability, which makes parts of
`DESIGN-03` redundant, parts of it a special case, and one of its statements wrong. The two
documents cannot both freeze as written.

| `DESIGN-03` location | why it must change | required change |
|---|---|---|
| `PP-1` — "The frozen design requires a non-delegated path and specifies none … This amendment **specifies** that path." | Amendment 3 specifies that path for all `HUMAN`-class capabilities, in the frozen document rather than in an amendment. `PP-1` also names only three rows; `D01-F02-003`'s inventory has fifteen plus `finding.waive` and `decision.record`. | Restate as a reference to authority-matrix §5.2, keeping only the claim that `project.mode.set`, `policy.set`, `budget.grant`, `budget.extend` and `project.ceiling.set` need **transition rows**, which §5.2 does not supply. |
| `PP-2` — what is cited for `required_capability`. | Same reading as `R1.4`, but stated as `DESIGN-03`'s own specification. Once amendment 1 is frozen it is the baseline's. | Cite [evidence-model.md:176](evidence-model.md#L176) as amended; drop the specification claim. |
| `PP-3` — a provisioning decision is `DECISION` class and is not promoted; disposition `-009`'s "only `:176` is amended". | Compatible in substance with `R3.10` and `R5.2`, but the scope claim is no longer true: this document also amends [evidence-model.md:95](evidence-model.md#L95), [:128](evidence-model.md#L128), [:135](evidence-model.md#L135), [:136](evidence-model.md#L136), [:178](evidence-model.md#L178), [authority-matrix.md:14](authority-matrix.md#L14), [domain-model.md:790](domain-model.md#L790), [:887](domain-model.md#L887) and [transition-matrix.md:48](transition-matrix.md#L48). | Re-verify disposition `-009` against the amended baseline and restate its scope sentence. |
| `PP-4`, `PP-5` — the ceiling does not bound direct exercise of the five; what bounds it instead. | `AX-13` makes this general and `R3.9` marks it chosen for every capability except `project.create`. `PP-4`'s per-capability forced/chosen split is superseded. | Delete the mechanism and keep only what is specific to the five fields: the payload predicates and the `evidence_shown` content requirement. |
| `PP-4a` — every other `HUMAN`-class capability is out of scope, and "`project.abandon` and `stage.abandon` are reachable by no specified path remains an open frozen gap (§8)". | **Wrong once this freezes.** Amendment 3 closes exactly that gap, which is `D01-F02-003`. | Remove the open-gap entry from `DESIGN-03` §8 and point to §5.2. |
| `PP-6` — no self-authorization; a `RUNTIME`/`WORKER`/`ADAPTER` actor with one of the five is an integrity violation. | Agrees with `R3.11`, which states it for all `HUMAN`-class capabilities. | Keep as an instance, or drop as redundant. |
| `PP-7` — one decision, one field, one write; nonce consumption with the field write. | Consistent with `AX-19`, which distinguishes an exercise decision (consumed) from a `GRANT_CAPABILITY` decision (not consumed). `DESIGN-03` has no grant decisions, so nothing of substance changes. | Add the `AX-19` distinction so the unqualified "one decision, one write" is not read across §5.3. |
| `PP-8` — the creating act is one atomic persistence over an allocated `project_id`; "This amendment adds no decision requirement to it." | The first half is `R3.12` and agrees. The second half conflicts with `AX-14`: the `∅ → DRAFT` row's `AUTO` verdict does not discharge [authority-matrix.md:51](authority-matrix.md#L51), so `project.create` needs a `HumanDecision{kind: APPROVE}` bound to the row's own `SNAP` (`R3.6`, `R3.7`). | Adopt the decision requirement, or contest `R3.6`/`AX-14` on the record. This is the one substantive disagreement between the two documents, and it must be settled before either freezes. |
| §2.1 — admissibility of a provisioning decision, ten steps. | Overlaps §5.2's seven steps. Steps 1–4, 6 and 8 restate them; steps 5, 7, 9 and 10 are `DESIGN-03`-specific. | Rewrite as a delta over §5.2, keeping the `evidence_shown` content requirement, the empty-`grants` condition, the payload predicates and the atomicity rule. |
| §2.2 — `ProvisioningDecision` as a profile of `HumanDecision`. | Unaffected: no field, enum or entity changes here. | No change. |
| §3 — `project.ceiling.set` and the mode-gate additions. | Unaffected, and now more important: §5.3 step 2 bounds a project grant by the ceiling, so the first `roadmap.import` grant needs the ceiling written. See §6. | No change, beyond noting that §5.3 depends on it. |
| §6 — the initial `Project` state, `event_seq = 1`, `event_head` = the creation event's hash. | Must be checked against amendments 10–12. Under `R10.1` and `R11.1` the snapshot event is `seq = 0` and the creation event `seq = 1`, so `DESIGN-03` §6's values are consistent; what changes is that the initialization is now specified in the frozen append protocol rather than asserted by `DESIGN-03`. | Cite the amended [evidence-model.md:128](evidence-model.md#L128), [:135](evidence-model.md#L135), [:136](evidence-model.md#L136) instead of asserting the values. |

Ordering: `DESIGN-04` should freeze first. `DESIGN-03` is a `Project`-holder amendment
standing on an authority path that does not exist in the frozen baseline; once amendments 1,
3 and 6 land, that path is baseline text and `DESIGN-03` shrinks to the five fields, their
rows, their payload predicates and the initial state. Per the review method, the reviewer of
the revised `DESIGN-03` is the reviewer that raised `DESIGN-03-FINDINGS-01`, and this
document's author does not review it.

---

## 6. What this document does not close

| item | statement |
|---|---|
| The ceiling write that §5.3 depends on | A project grant is bounded by `project.capability_ceiling` (`R6.2`), and the frozen design names no capability, decision kind or row that writes that field. So the authority path for the first `roadmap.import` is specified here, while the act of putting `roadmap.import` into the ceiling is `DESIGN-03`'s `project.ceiling.set`. `D01-F02-005` is closed — its defect is the circular grant path, and a conforming path now exists — but provisioning a project end to end needs `DESIGN-03` as well. This is the one dependency outside the five findings, and it is named rather than absorbed. |
| Kernel exercise of an `ORD` capability whose only grantor is `ROLE_DEFAULT` | Rows such as [transition-matrix.md:128](transition-matrix.md#L128) require `escalation.raise`, an `ORD` capability whose register grantor is `ROLE_DEFAULT` alone ([authority-matrix.md:141](authority-matrix.md#L141)), on a transition the controller performs. Neither a run grant (no worker role outside an invocation), nor a project grant (`R4.2` excludes it), nor the kernel holding (`AX-7` covers `KERNEL` capabilities only) supplies an authority form. This is observed while checking amendment 1's case split against the matrix. It is **not** one of the ten findings in `DESIGN-01-FINDINGS-02`, no amendment above addresses it, and it is recorded here so the case split is not read as exhaustive over every frozen row. It belongs in the next findings record, not in this document. |
| Transition rows for the four registered `HUMAN` governance writes | `project.mode.set`, `policy.set`, `budget.grant` and `budget.extend` gain an authority form from amendment 3 and still have no row naming them as `required_capability`. `D01-F02-003` is about the missing authority path, which is closed; the missing rows are `DESIGN-03`'s subject. |
| Implementation | Nothing here is implemented. `src/` and `tests/` are untouched, and the known gaps in `CLAUDE.md` — including whether `transitions.py` `cap=` declarations are enforced anywhere — are unaffected by a design proposal. |

---

## 7. Verification of this document

| check | result |
|---|---|
| Citation resolution | Every `file:line` in this document was resolved against the tag with `git show design-01-frozen:design/<file> \| sed -n '<line>p'` before it was written, and all 143 distinct citations were re-resolved afterwards: 50 in `authority-matrix.md`, 33 in `domain-model.md`, 23 in `evidence-model.md`, 35 in `transition-matrix.md`, 2 in `roadmap_adapter.md`. None is out of range and none lands on a blank line. The twelve amendment targets were quoted from that output verbatim. |
| Exhaustive claim | `R3.5`'s claim about `HUMAN`-class rows with an `AUTO` verdict was checked by enumerating every table row of the frozen `transition-matrix.md` and matching its `required_capability` cell against §2's `HUMAN`-class register rows. |
| Finding coverage | Each of the five findings is named by at least one amendment, and each of the twelve amendments names at least one of the five. `-006` receives none; `-007`, `-008`, `-009`, `-010` receive none and are declared in §1.4. |
| Dispositions | Severity and blocking flags are reproduced from `DESIGN-01-FINDINGS-02` and `VERIFY-01` as recorded. No disposition, blocking flag, or review record was changed, and no file under `design/review/` was modified. |
| Frozen text | No frozen design file, schema, or implementation file was edited. No commit, tag, or branch operation was performed. |
| Version terms | `SCHEMA_VERSION` appears only as the domain-model version feeding the genesis hash (`R10.3`). `STORAGE_VERSION` and `PRAGMA user_version` appear only to say they are a different thing. The two are not conflated anywhere above. |
