# DESIGN-04 — Baseline Correction (revision 03)

Revises [DESIGN-04-baseline-correction-02.md](DESIGN-04-baseline-correction-02.md) against
[DESIGN-04-FINDINGS-02.md](review/DESIGN-04-FINDINGS-02.md). Revisions 01 and 02 are
committed evidence and are unchanged; this document replaces them as the amendment. Where
they differ, this one governs.

| Property | Statement |
|---|---|
| Size | **952 lines, 23 amendments.** Revision 02 was 966 lines with 21. Two amendments are added (`-017`'s two consumers), one axiom is deleted (`AX-20`) and one rule withdrawn (`R13.17`); the rest is repair and compression — §2.21, §2.22, §3, §5, §6 and every amendment's scaffolding are tighter, and no quoted frozen text is abbreviated. |
| Baseline | `design-01-frozen`, peeled commit `8fd51193da0f29efb60ddf906fc845bb0dcbaeb3`. Every `file:line` citation resolves in that tag and was checked with `git show design-01-frozen:design/<file> \| sed -n '<line>p'`. |
| Kind | Proposal. No frozen file is edited, no schema or implementation is changed, nothing here is in effect. `design-01-frozen` remains authoritative until these edits land in the frozen files. |
| Corrects | The same five findings as revisions 01 and 02: `D01-F02-001`, `-002` (retained half only), `-003` (partially — §6.1), `-004`, `-005`. |
| Changes in this revision | Three one-sentence repairs (`AX-1`'s exception added to the two holding checks; `AX-15` scoped to non-`KERNEL`; `AX-11`'s admissibility clause scoped per form). One lifecycle withdrawn rather than patched: `AX-20` goes, and a project grant now ends by the frozen expiry row with no new consumption transition. Every `CLAIM` typing of policy and verification records deleted, those cells stated unclosed. `G-1`, the reachability check and the column legend reduced to one admissible-kind set. The `CLAIM` gate given an explicit control-field boundary. Two consumers amended for the new forms: the authority trace and `A-INV-2`. Six labels corrected, three claims withdrawn, and `D01-F02-003`'s closure narrowed. |
| Rule ids | Inherited from revisions 01 and 02 so the reviews' audits stay traceable: `R1.1` … `R12.1`, `R13.1` … `R13.20` less the withdrawn `R13.17`, plus `R13.21` and `R13.22`. |

## 0. Disposition of all twenty-four `DESIGN-04` findings

`DESIGN-04-FINDINGS-02` sustains nine of the first record's fourteen as closed and records
five as partially closed, then raises ten more. Judged against the frozen text each finding
cites, not against whether the reviewer's wording was engaged.

| id | disposition | what closes it |
|---|---|---|
| `-001` | **CLOSED** | Amendments 4 and 5 now admit `AX-1`'s `decision.record` exception at [authority-matrix.md:292](authority-matrix.md#L292) and [transition-matrix.md:49](transition-matrix.md#L49) (`-015`); `AX-15` is scoped (`-016`); the remaining possession consumers are amendments 22 and 23 (`-017`). |
| `-002` | **CLOSED** | Amendment 7: [authority-matrix.md:22](authority-matrix.md#L22)'s admissibility clause is tested by §5.1 for a run grant and §5.3 for a project grant. Amendment 6's request/role wording is corrected against [domain-model.md:328](domain-model.md#L328)–[:329](domain-model.md#L329). |
| `-003` | **CLOSED** | Amendment 9: [authority-matrix.md:19](authority-matrix.md#L19) gains the denial `AuditEvent` destination already required at [:293](authority-matrix.md#L293). The worked case is `R13.10` (revision 02 misnamed it `R13.3`). |
| `-004` | **CLOSED** | `AX-17`'s four-event witness, with `R13.15` stating that `subject_snapshot_id` names the snapshot **recorded by** event 0, never an event id. |
| `-005` | **CLOSED** | Amendments 15–17: typing per citation and per alternative, verified row by row in §2.22. |
| `-006` | **CLOSED** | Amendment 15 preserves the `WAIVED` route ([evidence-model.md:204](evidence-model.md#L204), [:210](evidence-model.md#L210), [domain-model.md:246](domain-model.md#L246)). |
| `-007` | **CLOSED** | Amendment 18 and `R13.19`: the `CLAIM` cell now names the control fields that may gate — `trigger`, `status`, `severity`, `auto_resolvable`, holder bindings — and the asserted fields that may not. |
| `-008` | **CLOSED on the delimitation branch** the finding itself offers: §2.21 maps every kind `G-1` admits, §2.22 resolves all 44 rows, and §6.4 lists the four rows and the record kinds that remain unclosed. No total mapping is claimed. |
| `-009` | **CLOSED** | Amendment 13's closure line and §6.1 no longer say "in full"; `D01-F02-003` is partially closed in §0, §1.1, amendment 13 and §6.1. |
| `-010` | **CLOSED** | Amendment 12 (rev 02), with `R13.12` corrected so the stage rows are not covered by a project-subject argument (`-023`). |
| `-011` | **CLOSED** | §4 (rev 02), extended by this revision's label corrections (`-024`). |
| `-012` | **CLOSED** | Amendment 2's guarded biconditional (rev 02). |
| `-013` | **CLOSED** | Amendment 21 keeps the third cell (rev 02). |
| `-014` | **CLOSED** | §6.2's chosen premise (rev 02), now also naming the amendments `D01-F02-005` actually rests on. |
| `-015` | **CLOSED** | One clause each in amendments 4 and 5: possession may be held under `AX-1`'s named `decision.record` exception, so [transition-matrix.md:393](transition-matrix.md#L393) can record the first decision. |
| `-016` | **CLOSED** | `AX-15`'s final sentence is scoped to non-`KERNEL` capabilities; the kernel's own holding under [authority-matrix.md:18](authority-matrix.md#L18) and [:34](authority-matrix.md#L34) stands. |
| `-017` | **CLOSED** | Amendment 22 amends [evidence-model.md:282](evidence-model.md#L282) so the trace names whichever form was used; amendment 23 scopes [domain-model.md:410](domain-model.md#L410) to a run's execution authority, with [transition-matrix.md:208](transition-matrix.md#L208) as the case that forces the distinction. |
| `-018` | **CLOSED by withdrawal** | `AX-20`'s standing-grant lifecycle is deleted. `AX-19` now says the grant is never "recorded for" a transition, so it never takes [transition-matrix.md:394](transition-matrix.md#L394) and ends by [:396](transition-matrix.md#L396) — the same unconsumed-nonce state [authority-matrix.md:263](authority-matrix.md#L263) already requires of a run grant's basis decision. No row of §7.5 is amended, and [:401](transition-matrix.md#L401)'s terminality is untouched. |
| `-019` | **CLOSED** | Every `CLAIM` typing of policy and chain-verification records is deleted — amendment 16, `R13.17`, §2.21, §2.22, §3 and §6 — and those cells are stated unclosed for a later corrective record alongside `D01-F02-007`/`-008`/`-009`/`-010` (§6.4). |
| `-020` | **CLOSED** | `G-1`, amendment 16 and amendment 17 now admit one identical set: an evidence citation, an activation, a `HumanDecision`, an `Escalation`, or an `AuditEvent` the row names — the last covering the artifacts and identities at [transition-matrix.md:305](transition-matrix.md#L305), [:307](transition-matrix.md#L307), [:337](transition-matrix.md#L337). They are in all three. Anything else is outside `G-1` and not closed. |
| `-021` | **CLOSED** | Amendment 18 names the gating fields; §2.22 stops calling [transition-matrix.md:132](transition-matrix.md#L132)'s trigger qualifier a precondition and treats it as the in-cell control field it is. |
| `-022` | **CLOSED by withdrawal, row retained unclosed** | The "live at that resolution" reading is deleted. [transition-matrix.md:171](transition-matrix.md#L171) needs a `DEC` that is `VALID` at the consuming transition ([:74](transition-matrix.md#L74), [authority-matrix.md:289](authority-matrix.md#L289), [transition-matrix.md:522](transition-matrix.md#L522)) while a resolution's decision is `CONSUMED` and terminal ([:394](transition-matrix.md#L394), [:401](transition-matrix.md#L401)); the row is **NOT CLOSED** and is carried to §6.4. |
| `-023` | **CLOSED** | `R13.12` and §2.22 state that a `STAGE`-subject `ABANDON` is snapshot-bound ([domain-model.md:702](domain-model.md#L702)) and keeps its `SNAP`; the project-subject profile covers only [transition-matrix.md:86](transition-matrix.md#L86), [:89](transition-matrix.md#L89), [:91](transition-matrix.md#L91), [:94](transition-matrix.md#L94). |
| `-024` | **CLOSED** | §4 relabels `R13.5` (split), `R13.10`, `R13.14`, `R13.15` (conditional) and `R13.11` (chosen); `R13.17` is withdrawn; §2.21 drops the "nothing else optional" claim; the `ESC` count is twelve and the remaining semantic columns four. |

Four rows and two record kinds are **NOT CLOSED** and are listed in §6.4 rather than
claimed: the policy-evaluation and verification-record cells, [transition-matrix.md:171](transition-matrix.md#L171),
[:412](transition-matrix.md#L412) for comparison triggers, and the six `HUMAN` capabilities
with no legal row. `D01-F02-003` is partially closed for that last reason.

## 1. Scope

### 1.1 The five findings corrected

Severity and blocking flags are the owner's, as recorded in `DESIGN-01-FINDINGS-02`; this
document reproduces them and changes none.

| id | severity | blocking | VERIFY-01 disposition | amendments |
|---|---|---|---|---|
| `D01-F02-001` | `BLOCKER` | true | **CONFIRMED** — "The universal live-grant audit check cannot represent kernel self-holdings; project creation also has no admissible grant path." | 1, 2, 3, 4, 5, 12, 13 |
| `D01-F02-002` | `MAJOR` | false | **PARTIALLY CONFIRMED** — "First-append initialization is not specified by the ordinary append algorithm. However, lower event sequence does not require an earlier transaction commit; the claimed referential-integrity impossibility does not follow." | 19, 20, 21 |
| `D01-F02-003` | `MAJOR` | true | **CONFIRMED** — "None of the four lifecycle capabilities survives activation's role intersection. Later activation records can exist, but cannot supply those grants." | 1, 3, 4, 5, 12, 13 |
| `D01-F02-004` | `MAJOR` | true | **CONFIRMED** — "Mandatory activation, decision, escalation and audit-envelope evidence conflicts with the closed entity allow-list and, for the first three, event classification." | 15, 16, 17, 18 |
| `D01-F02-005` | `MAJOR` | true | **CONFIRMED** — "Initial import and first contract creation require activation authority before the stage/contract/run structure supporting that authority has been established." | 1, 6, 7, 8, 9, 10, 11, 12, 14 |

`D01-F02-001`, `-002`, `-004` and `-005` are closed by these amendments. `D01-F02-003` is
**partially** closed: for the seven `HUMAN` capabilities with legal rows, including its four
named ones, and not for the six further operations it cites (§6.1, §6.4).
### 1.2 `D01-F02-002` — what is retained, and what is not asserted

`VERIFY-01` refuted the referential-integrity half and this document does not reassert it.
**Retained and corrected** by amendments 19–21: the append algorithm reads `event_seq` and
`event_head` that have no prior event in a new project ([evidence-model.md:135](evidence-model.md#L135),
[:136](evidence-model.md#L136), [domain-model.md:145](domain-model.md#L145), [:146](domain-model.md#L146)),
and the genesis rule ([evidence-model.md:127](evidence-model.md#L127)) specifies event zero
without specifying installation of the project/head state the later steps read — the residue
narrowed at [VERIFY-01:59](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L59). **Not asserted
and used as a basis nowhere:** that satisfying `SNAP` before the creation event necessarily
exposes a committed reference to a project that does not yet exist. Where this document
needs transaction-local ordering it cites the `D01-F02-006` refutation instead
([VERIFY-01:98](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L98),
[:104](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L104)–[:109](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L109)),
with the project/snapshot instance at [VERIFY-01:50](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L50)–[:55](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L55).

### 1.3 `D01-F02-006` — refuted, no amendment

`VERIFY-01` records it **REFUTED**. No amendment addresses it;
[domain-model.md:273](domain-model.md#L273), [:390](domain-model.md#L390),
[:865](domain-model.md#L865) and [transition-matrix.md:189](transition-matrix.md#L189)'s
`ACT` precondition are untouched. Its refutation is used here only as the transactional
basis the reviews asked for.

### 1.4 Out of scope: `-007`, `-008`, `-009`, `-010`

All four are **CONFIRMED** by `VERIFY-01` and none is addressed. Each governs an operation
unreachable until after a project is provisioned, a stage materialized, a contract
activated and a run executed, so none blocks provisioning and none is repaired by these
corrections: `-007` needs an `ACTIVE` contract and a second contract for the same stage
([transition-matrix.md:269](transition-matrix.md#L269), [:273](transition-matrix.md#L273));
`-008` needs a run that consumed its immutable allocation ([:172](transition-matrix.md#L172),
[:206](transition-matrix.md#L206), [domain-model.md:284](domain-model.md#L284),
[:287](domain-model.md#L287)); `-009` needs a controller restart with prior-epoch operations
([evidence-model.md:167](evidence-model.md#L167)); `-010` needs an intent that reached
`APPLYING` ([transition-matrix.md:358](transition-matrix.md#L358), [:73](transition-matrix.md#L73)).
No worker may be dispatched while `DRAFT` or `PLANNING` ([:435](transition-matrix.md#L435)).
Amendments 15–18 do change the **admissibility** of records some of their rows cite; the
underlying defects are untouched, and §2.22 marks each such row. They must be closed before
the first contract replacement, the first exhausted budget or passed deadline, the first
restart leaving a live operation, and the first divergent apply, respectively.

## 2. Amendments

Twenty-three amendments in four groups: the authority forms (1–14), evidence typing
(15–18), genesis (19–21), and the two consumers the new forms reach (22–23). Each closes
at least one of the five findings.

### Amendment 1 — the authority-binding verification check

**Target** [evidence-model.md:176](evidence-model.md#L176) (§3.3 Verification). **Current frozen text:**

```
| authority binding | every event with `capability_used` has an `authority_ref` resolving to a live grant at `recorded_at` | same |
```

**Proposed text**

```
| authority binding | every event with `capability_used` resolves it at `recorded_at` by exactly one authority form (`AX-1`): a `KERNEL`-class capability by the kernel's own holding, requiring `actor.actor_kind = RUNTIME` and absent `authority_ref` (`AX-7`); `decision.record` by the principal's own holding, requiring `actor.actor_kind = HUMAN` with `auth_method ∈ {SESSION, SIGNATURE, MTLS}` and absent `authority_ref` (`AX-15`); any other `HUMAN`-class capability by `authority_ref` naming the live `HumanDecision` that authorized this act (authority-matrix §5.2); every other capability by `authority_ref` naming a live grant carrying it — a `ContractActivationRecord` whose `granted_capabilities` contains it, or a project grant per authority-matrix §5.3 | same |
```

**Closes** `D01-F02-001`, both halves; the verification-side form for `D01-F02-003` and
`D01-F02-005`.

| id | rule | basis |
|---|---|---|
| `R1.1` | A `KERNEL`-class exercise cites no grant, because none can exist. | **derived** — [authority-matrix.md:18](authority-matrix.md#L18), [:34](authority-matrix.md#L34), [:245](authority-matrix.md#L245), [:266](authority-matrix.md#L266) |
| `R1.2` | That holding is represented by an absent `authority_ref` with `actor_kind = RUNTIME`. | **chosen** — [domain-model.md:790](domain-model.md#L790) permits an absent reference but does not make omission sufficient under frozen [evidence-model.md:176](evidence-model.md#L176); this amendment supplies the sufficiency. The rejected alternative is a new kernel authority record, which would also require amending `G-2` ([domain-model.md:888](domain-model.md#L888)). |
| `R1.3` | In the frozen baseline a realized grant is an activation whose `granted_capabilities` contains the capability, and nothing else. | **derived as a statement about the baseline** — the decisive rule is that a decision's grant is realized only through an activation ([evidence-model.md:95](evidence-model.md#L95)) with grants scoped per activation ([authority-matrix.md:14](authority-matrix.md#L14)); [evidence-model.md:65](evidence-model.md#L65) names `HumanDecision.grants` among `AUTHORITY` producers and `G-2` limits citation types only ([domain-model.md:888](domain-model.md#L888)). Amendments 10 and 11 change this baseline statement, which is why the rule is stated of the baseline and not of the amended design. |
| `R1.4` | A `HUMAN`-class exercise cites the live decision that authorized the act. | **chosen** for sufficiency in place of a grant; **derived** that a decision is an admissible citation type ([domain-model.md:790](domain-model.md#L790), [:888](domain-model.md#L888)). Neither derives a bypass of possession; amendments 3–5 supply that. |
| `R1.5` | `decision.record` by an authenticated human cites nothing. | **chosen** — see `AX-15`. [transition-matrix.md:399](transition-matrix.md#L399) supports that recording needs no further policy decision; it does not state a self-held capability. |
| `R1.6` | The four forms are exhaustive and mutually exclusive for any event carrying `capability_used`. | **chosen** — a case split is not an implicit `AX-1` amendment, which is why amendment 3 amends `AX-1` explicitly. With `AX-1` as amended, an event matching no form is denied. |

### Amendment 2 — the `authority_ref` field note

**Target** [domain-model.md:790](domain-model.md#L790) (§9.C `AuditEvent`). **Current frozen text:**

```
| `authority_ref` | `Id?` | N | I | R | activation or decision that permitted it |
```

**Proposed text**

```
| `authority_ref` | `Id?` | N | I | R | activation or decision that permitted it; on an event carrying `capability_used`, absent exactly when that capability is `KERNEL`-class or is `decision.record` (evidence-model §3.3), and otherwise required. An event carrying no `capability_used` is unconstrained by this note |
```

**Closes** `D01-F02-001`. Fixes `DESIGN-04-012`.

| id | rule | basis |
|---|---|---|
| `R2.1` | The biconditional binds only events that carry `capability_used`; an event without one keeps the frozen optionality. | **chosen** — it records amendment 1's case split in the field table. A non-state-changing event may omit `capability_used` ([domain-model.md:789](domain-model.md#L789)) and its absent `authority_ref` was already permitted ([:790](domain-model.md#L790)) and unexamined by the frozen check; revision 01's unguarded wording rejected that valid case. `G-2`'s allow-list is unchanged: these two cases cite nothing. |

### Amendment 3 — `AX-1`

**Target** [authority-matrix.md:12](authority-matrix.md#L12) (§0 Axioms). **Current frozen text:**

```
| `AX-1` | **Default DENY.** An action with no matching grant is denied. Absence of a rule is never permission. |
```

**Proposed text**

```
| `AX-1` | **Default DENY.** An action is denied unless one authority form admits it: a **run grant** (§5), a **project grant** (§5.3), a **per-act exercise** of a `HUMAN`-class capability against a live decision (§5.2), or the **kernel's own holding** of a `KERNEL`-class capability (`AX-7`). `decision.record` held by an authenticated `HUMAN_PRINCIPAL` is the single named exception to the requirement of a form (`AX-15`). There is no fifth form; absence of a rule is never permission. |
```

**Closes** `D01-F02-001` and `D01-F02-003`. Fixes `DESIGN-04-001`.

| id | rule | basis |
|---|---|---|
| `R13.1` | Grantless human exercise needs an exception in `AX-1` itself, not only a changed audit predicate. | **derived** — the frozen axiom's first operative sentence denies "an action with no matching grant"; revision 01's human path expressly had no grant and did not amend this line. |
| `R13.2` | The four forms plus the `decision.record` exception are the complete admissible set. | **chosen** — exhaustiveness is imposed here, as in `R1.6` and `R4.3`. Default DENY at this line is what makes the closure safe rather than permissive. |

### Amendment 4 — the transition enforcement point

**Target** [authority-matrix.md:292](authority-matrix.md#L292) (§6 Enforcement points). **Current frozen text:**

```
| transition | `required_capability` from `transition-matrix.md` held at the moment of transition, plus `required_evidence` present |
```

**Proposed text**

```
| transition | `required_capability` from `transition-matrix.md` held at the moment of transition by one of `AX-1`'s forms — a run grant, a project grant, the kernel's own holding, or for this one act by a live decision under §5.2 — or held under `AX-1`'s named `decision.record` exception (`AX-15`), plus `required_evidence` present |
```

**Closes** `D01-F02-001` and `D01-F02-003`. Fixes `DESIGN-04-001`.

| id | rule | basis |
|---|---|---|
| `R13.3` | Per-act exercise is a way of holding a capability at the transition, not a way of dispensing with possession. | **chosen** — this is the substantive repair of revision 01's "never held" framing, which contradicted this enforcement point and [transition-matrix.md:49](transition-matrix.md#L49). Possession begins when the authorizing decision becomes live and ends at `VALID → CONSUMED` ([transition-matrix.md:394](transition-matrix.md#L394)). §6's decision-freshness point ([authority-matrix.md:289](authority-matrix.md#L289)) already enforces the liveness this relies on and is untouched. |

### Amendment 5 — the `required_capability` column

**Target** [transition-matrix.md:49](transition-matrix.md#L49) (§1 Column semantics). **Current frozen text:**

```
| `required_capability` | the single `CapabilityId` the actor must hold; absent ⇒ DENY |
```

**Proposed text**

```
| `required_capability` | the single `CapabilityId` the actor must hold at the transition, by any authority form in `AX-1` (authority-matrix §5, §5.2, §5.3, `AX-7`) or under `AX-1`'s named `decision.record` exception (`AX-15`); absent ⇒ DENY |
```

**Closes** `D01-F02-001` and `D01-F02-003`. Fixes `DESIGN-04-001`.

| id | rule | basis |
|---|---|---|
| `R13.4` | The column's meaning is possession by an admissible form, and the set of forms is the thing amended. | **derived** that the column requires possession — its own frozen wording; **chosen** that per-act possession counts, which is `R13.3`. `AX-2` and `G-4` are untouched: exactly one capability per operation. |

### Amendment 6 — `AX-4`

**Target** [authority-matrix.md:15](authority-matrix.md#L15) (§0 Axioms). **Current frozen text:**

```
| `AX-4` | `granted ⊆ capability_request ∩ role_default ∩ mode_allowed ∩ project.capability_ceiling`. Intersection, never union. |
```

**Proposed text**

```
| `AX-4` | For a **run grant**: `granted ⊆ capability_request ∩ role_default ∩ mode_allowed ∩ project.capability_ceiling`. For a **project grant** (§5.3): `granted ⊆ decision.grants ∩ mode_allowed ∩ project.capability_ceiling`, a project grant having no `capability_request` and no `worker_role` of its own — those are `StageContract` fields resolved per `WorkerInvocation` (§4.1) and a project grant is neither. A **per-act exercise** (§5.2) produces no `granted` set and is bounded by §5.2 instead. Intersection, never union. |
```

**Closes** `D01-F02-005`. Fixes `DESIGN-04-002`.

| id | rule | basis |
|---|---|---|
| `R6.4` | §4.1's role table does not apply to a project grant. | **conditional on the project-grant form** — [authority-matrix.md:190](authority-matrix.md#L190) heads that table "per `WorkerInvocation`", which supports not applying it to a non-invocation grant but does not narrow this axiom's unqualified wording. That narrowing is what this amendment does, which is why revision 01's additive heading was insufficient. |
| `R13.5` | The ceiling still bounds a project grant, and the mode gate is applied to it. | **derived** for the ceiling — [domain-model.md:141](domain-model.md#L141) makes it the upper bound on all grants and `P-INV-2` says no grant anywhere may exceed it ([domain-model.md:153](domain-model.md#L153)); **chosen** for the mode gate, which is `R6.3`'s choice to mirror §5 step 3. The conjunction is therefore not a single derivation. |

### Amendment 7 — `AX-11`

**Target** [authority-matrix.md:22](authority-matrix.md#L22) (§0 Axioms). **Current frozen text:**

```
| `AX-11` | **Bounding is not granting.** `project.capability_ceiling`, the §3 mode gate, `capability_request`, and the §4.1 role table only narrow the candidate set. A capability is granted only when a principal named in its §2 `grantable by` column produced an admissible grant record for it (§5.1), and that record is cited in `ContractActivationRecord.capability_grant_basis`. |
```

**Proposed text**

```
| `AX-11` | **Bounding is not granting.** `project.capability_ceiling`, the §3 mode gate, `capability_request`, and the §4.1 role table only narrow the candidate set. A capability is granted only when a principal named in its §2 `grantable by` column produced an admissible grant record for it — admissibility tested by §5.1 for a run grant and by §5.3 for a project grant — and that record is cited by the grant it produced: in `ContractActivationRecord.capability_grant_basis` for a run grant, and by `AuditEvent.authority_ref` naming the granting `HumanDecision` for a project grant (§5.3, `AX-19`). A per-act exercise is not a grant and produces no basis entry (§5.2). |
```

**Closes** `D01-F02-005`. Fixes `DESIGN-04-002`.

| id | rule | basis |
|---|---|---|
| `R13.6` | A project grant's basis citation is the granting decision itself, cited at the point of exercise. | **chosen** — the frozen final clause admits exactly one destination, an activation's `capability_grant_basis`, which a pre-activation grant cannot have. `G-2` already admits a `HumanDecision` as an authority citation ([domain-model.md:888](domain-model.md#L888)), so no new entity or citation type is needed. |
| `R13.7` | "Bounding is not granting" is unchanged, including for the initial ceiling. | **derived** — the amendment retains the first two sentences verbatim. A non-empty initial ceiling therefore grants nothing (§6.2). |

### Amendment 8 — `C-INV-3`

**Target** [domain-model.md:380](domain-model.md#L380)–[:381](domain-model.md#L381) (§5 `StageContract` invariants), one two-line invariant. **Current frozen text:**

```
**C-INV-3** `capability_request` is a request. Grants come only from
`ContractActivationRecord`.
```

**Proposed text**

```
**C-INV-3** `capability_request` is a request. A run's grants come only from
`ContractActivationRecord`; a project grant comes only from a live
`HumanDecision{kind: GRANT_CAPABILITY, scope: PROJECT}` (authority-matrix §5.3) and never
reaches a run.
```

**Closes** `D01-F02-005`. Fixes `DESIGN-04-002`.

| id | rule | basis |
|---|---|---|
| `R13.8` | The activation-only rule is scoped to a run's grants rather than repealed. | **chosen** — the frozen sentence is unqualified. Scoping it keeps `A-INV-2` ([domain-model.md:410](domain-model.md#L410)) literally true: activation remains the only entity conferring authority **on a run**, because `AX-18` keeps project grants out of every run set. That is why `A-INV-2` needs no amendment. |

### Amendment 9 — `AX-8`

**Target** [authority-matrix.md:19](authority-matrix.md#L19) (§0 Axioms). **Current frozen text:**

```
| `AX-8` | Denial is recorded: every denied capability appears in `ContractActivationRecord.denied_capabilities` with a reason. Silent denial is a defect. |
```

**Proposed text**

```
| `AX-8` | Denial is recorded. For a run grant every denied capability appears in `ContractActivationRecord.denied_capabilities` with a reason. For a project grant (§5.3) or a per-act exercise (§5.2) there is no activation, and the record is the denial `AuditEvent` §6 already requires: `epistemic_class = AUTHORITY`, carrying each denied `CapabilityId` with the same reason vocabulary as `denied_capabilities`. Silent denial is a defect in either form. |
```

**Closes** `D01-F02-005`. Fixes `DESIGN-04-003`.

| id | rule | basis |
|---|---|---|
| `R13.9` | A project-scope denial has a conforming destination. | **chosen** — the frozen axiom names one destination that cannot exist before a contract and run do ([domain-model.md:388](domain-model.md#L388), [:390](domain-model.md#L390)). The granting decision cannot hold it either: `grants` is immutable and there is no denied field ([domain-model.md:698](domain-model.md#L698), [:699](domain-model.md#L699)). The denial event is already mandatory ([authority-matrix.md:293](authority-matrix.md#L293)), so this reuses a frozen record rather than adding one. |
| `R13.10` | Worked failure case: a decision whose `grants` contains one capability outside `project.capability_ceiling`. | **conditional** — it needs amendment 6's project-grant intersection **and** this amendment's destination together. Step 2 of §5.3 drops the capability with `NOT_IN_CEILING`, and the reason and capability then appear in the denial `AuditEvent`. Frozen [domain-model.md:393](domain-model.md#L393) supplies the reason vocabulary, not the destination; before these amendments the reason had nowhere conforming to go. |

### Amendment 10 — `AX-3`

**Target** [authority-matrix.md:14](authority-matrix.md#L14) (§0 Axioms). **Current frozen text:**

```
| `AX-3` | Grants are per `ContractActivationRecord`, scoped to one `StageRun`, and frozen for that run's life. |
```

**Proposed text**

```
| `AX-3` | A grant is realized in exactly one of two forms. A **run grant** is per `ContractActivationRecord`, scoped to one `StageRun`, and frozen for that run's life (§5). A **project grant** is realized directly by a live `HumanDecision{kind: GRANT_CAPABILITY}` with `scope = PROJECT`, is scoped to one `Project`, carries only `ORD` capabilities whose §2 `grantable by` column names `HUMAN_PRINCIPAL`, and exists for the acts that precede any activation (§5.3). No third form of grant exists; a `HUMAN`-class capability is granted by neither form and is exercised per act (§5.2). |
```

**Closes** `D01-F02-005`.

| id | rule | basis |
|---|---|---|
| `R4.1` | A second grant form exists, scoped to a project. | **chosen** — one form is what makes the first import and first contract authoring circular ([transition-matrix.md:85](transition-matrix.md#L85), [:117](transition-matrix.md#L117), [:265](transition-matrix.md#L265), [domain-model.md:316](domain-model.md#L316), [:388](domain-model.md#L388), [:390](domain-model.md#L390)). Amendments 6–8 carry the rest of the realization change this form requires. |
| `R4.2` | The project form carries only `ORD` capabilities whose register row names `HUMAN_PRINCIPAL`. | **chosen** — `HUMAN`-class capabilities are excluded because §5.2 exercises them per act; a `ROLE_DEFAULT`-only capability is excluded because there is no role outside an invocation ([authority-matrix.md:190](authority-matrix.md#L190)); `POLICY_ENGINE` is excluded by `R6.6`. This selects one subset, and is not a theorem about every possible project-scope design. |
| `R4.3` | The two grant forms are exhaustive. | **chosen** — imposed here and enforced by `AX-1` as amended. Default DENY does not itself define the forms. |

### Amendment 11 — the `DECISION → AUTHORITY` promotion rule

**Target** [evidence-model.md:95](evidence-model.md#L95) (§2.2 Promotion rules). **Current frozen text:**

```
| `DECISION` → `AUTHORITY` | a `HumanDecision` with non-empty `grants` | the grant is realized only through an activation record |
```

**Proposed text**

```
| `DECISION` → `AUTHORITY` | a `HumanDecision` with non-empty `grants` or `revokes` | a run grant is realized through an activation record; a project grant is realized by the decision itself and is never written into an activation (`AX-3`, authority-matrix §5.3). A decision with empty `grants` and empty `revokes` promotes to nothing: it authorizes its own act and delegates no capability (authority-matrix §5.2) |
```

**Closes** `D01-F02-005`.

| id | rule | basis |
|---|---|---|
| `R5.1` | A project grant is realized by the granting decision, with no activation record. | **chosen** — this is the promotion-rule half of `R4.1`, and this line is the frozen text that makes every realized grant pass through an activation. |
| `R5.2` | A decision promotes to nothing only when both `grants` and `revokes` are empty. | **derived** — [evidence-model.md:84](evidence-model.md#L84) classes `grants` **and** `revokes` as `AUTHORITY`, so revision 01's empty-`grants` test was insufficient; the frozen row's own predicate names `grants` alone, which this amendment widens to match [:84](evidence-model.md#L84). Exclusion from this row confers no authority for an act: §5.2 step 6 requires both sets empty, and the authority is the decision's citation under amendment 1. |

### Amendment 12 — the decision-recording row

**Target** [transition-matrix.md:393](transition-matrix.md#L393) (§7.5 `HumanDecision.decision_state`). **Current frozen text:**

```
| `∅` | `VALID` | recorded per `HD-INV-1`/`HD-INV-2`; `snapshot_bound = true` ⇒ `subject_snapshot_id` is the newest `COMPLETE` snapshot covering the subject's scope and every `evidence_shown` artifact is current against it | `SNAP` as `subject_snapshot_id` | `decision.record` | `AUTO` | `AUTO` | — |
```

**Proposed text**

```
| `∅` | `VALID` | recorded per `HD-INV-1`/`HD-INV-2`; `snapshot_bound = true` ⇒ `subject_snapshot_id` is the newest `COMPLETE` snapshot covering the subject's scope and every `evidence_shown` artifact is current against it | `SNAP` as `subject_snapshot_id` where `snapshot_bound = true`; `—` otherwise | `decision.record` | `AUTO` | `AUTO` | — |
```

**Closes** `D01-F02-003` and `D01-F02-005`. Fixes `DESIGN-04-010`.

| id | rule | basis |
|---|---|---|
| `R13.11` | The row's evidence cell is conditional on `snapshot_bound`. | **chosen** — [domain-model.md:703](domain-model.md#L703) and [:876](domain-model.md#L876) make `subject_snapshot_id` required and present iff `snapshot_bound`, while the frozen cell demands it unconditionally. The two obligations contradict each other for a non-bound decision, and choosing to amend the cell rather than the field rules is this document's selection among them, not a reading of an already-conditional cell. |
| `R13.12` | This is load-bearing for two findings, not only for project grants. | **derived** for the profiles named — `GRANT_CAPABILITY` and `ABANDON` over a `PROJECT` or `CAPABILITY` subject are not snapshot-bound ([domain-model.md:702](domain-model.md#L702)), and a `PROJECT`-subject `ABANDON` is the decision the four `project.abandon` rows require ([transition-matrix.md:86](transition-matrix.md#L86), [:89](transition-matrix.md#L89), [:91](transition-matrix.md#L91), [:94](transition-matrix.md#L94)), which `D01-F02-003` names. It says nothing about the stage rows: a `STAGE`-subject `ABANDON` **is** bound by subject ([:702](domain-model.md#L702)) and keeps its `SNAP`. |
| `R13.13` | `APPROVE`, `WAIVE`, `ACCEPT_RISK`, `OVERRIDE` and `REJECT` decisions remain snapshot-bound and keep the cell. | **derived** — [domain-model.md:702](domain-model.md#L702)'s first disjunct and kind list; `HD-INV-4` ([domain-model.md:719](domain-model.md#L719)) is untouched. |

### Amendment 13 — per-act exercise of a `HUMAN`-class capability (new authority-matrix §5.2)

**Target** insertion into `authority-matrix.md` immediately after
[authority-matrix.md:277](authority-matrix.md#L277), the last line of §5.1. **Current frozen text at the anchor:**

```
presence in `capability_request` change nothing.
```

**Proposed text** (inserted after that line; the anchor line itself is unchanged)

```
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

Seven of the seventeen `HUMAN`-class capabilities in §2 are named as `required_capability`
by a legal row, on eighteen rows in total: `project.create`, `project.abandon`,
`project.archive`, `stage.reject`, `stage.abandon`, `finding.waive` and `decision.record`.
The other ten have no legal row and no exercise this procedure can bind; §5.2 supplies
their authority form and not their procedure.

| id | rule |
|---|---|
| `AX-12` | Per-act possession is not a grant and never becomes one. The capability is never written into `HumanDecision.grants`, `ContractActivationRecord.granted_capabilities`, `WorkerInvocation.granted_capabilities` or `StageRun.effective_capabilities`, and the authorizing decision's `grants` and `revokes` are both empty. §5, §5.1, §4.1 and `AX-4`'s run-grant intersection are unchanged. |
| `AX-13` | Per-act exercise is bounded by §2's register row, the §3 mode gate, the row that names the capability, and one live decision per act. It is not bounded by `project.capability_ceiling`, which bounds grants (`AX-11`, `P-INV-2`). |
| `AX-14` | A `HUMAN`-class row whose verdict names a decision (`DECIDE(K)` or `CONFIRM`) is authorized by that decision. Where the verdict is `AUTO`, a `HumanDecision{kind: APPROVE}` over the row's subject is required instead; the frozen matrix contains exactly three such rows — `∅ → DRAFT` under `project.create`, `ABANDONED → ARCHIVED` under `project.archive`, and `∅ → VALID` under `decision.record`, the last exempt by `AX-15`. `AUTO` states the policy engine's contribution; it does not remove the §2 class legend's exercise-time decision. |
| `AX-15` | `decision.record` is held by an authenticated `HUMAN_PRINCIPAL` without a decision of its own, because the human act *is* the decision — which is why recording is `AUTO` in both modes (transition-matrix §7.5). It is the single named exception in `AX-1`, and it is not an instance of `AX-7`. No **other non-`KERNEL`** capability is self-held by any principal; the kernel's own holding of `KERNEL` capabilities stands untouched (`AX-7`, §1). |
| `AX-16` | The event's `actor` is the actor that performed the act. Where that actor is not the deciding principal — the controller writing a project record, the kernel resolving a secret for an adapter — it carries `on_behalf_of` naming the deciding principal, at delegation depth ≤ 2. A `WORKER` actor never performs a `HUMAN`-class exercise. The kernel self-grants nothing: the authority is the human's decision, named by `authority_ref`. |
| `AX-17` | `project.create` is exercised inside the store transaction that installs the project, over an allocated identifier. One conforming witness, unrelated defects held aside: `seq = 0` the `RealitySnapshot` under `snapshot.take`; `seq = 1` the creation approval reaching `VALID` under `decision.record`, citing event 0 as its `subject_snapshot_id`; `seq = 2` `∅ → DRAFT` under `project.create`, citing the decision as `authority_ref` and event 0 as its `SNAP`; `seq = 3` `VALID → CONSUMED` under `audit.append`, citing event 2. At commit `Project.event_seq = 3` and `event_head` is event 3's hash. Four transitions, four events, one transaction, no event merging two capability identities. |
```

**Closes** `D01-F02-003` for the seven `HUMAN` capabilities that have legal rows — its four named lifecycle capabilities, `decision.record` and `finding.waive` among them — and the `project.create` half of `D01-F02-001`. It does **not** close `D01-F02-003` in full: §6.1. Fixes
`DESIGN-04-001`, `-004`, `-009`, and the `R3.10`/`R3.11` halves of `-011`.

| id | rule | basis |
|---|---|---|
| `R3.1` | A `HUMAN`-class capability requires a decision at the moment of exercise, not merely at grant time. | **derived** — [authority-matrix.md:51](authority-matrix.md#L51)–[:52](authority-matrix.md#L52). It does not remove grant-time requirements, which is why amendments 3–5 are needed. |
| `R3.2` | No run grant can carry one. | **derived** — [authority-matrix.md:221](authority-matrix.md#L221) with [:194](authority-matrix.md#L194) and [:244](authority-matrix.md#L244). The `C` cells at [:203](authority-matrix.md#L203) and [:206](authority-matrix.md#L206) are a disclosed frozen tension, not a second path. |
| `R3.3` | These capabilities are therefore held per act and never stand. | **chosen** for the general statement; **derived** for worker roles from `R3.2`. `decision.record` is the stated exception (`AX-15`); revision 01's "never held, in any set" is withdrawn as both overbroad and inconsistent with [transition-matrix.md:49](transition-matrix.md#L49). |
| `R3.4` | The authorizing decision is the one the row's verdict names. | **derived** — `DECIDE(K)` at [transition-matrix.md:61](transition-matrix.md#L61) and [:74](transition-matrix.md#L74); `CONFIRM` explicitly fixes `APPROVE` at [:60](transition-matrix.md#L60). Neither invents a verdict for an operation with no row, which is why step 2 exists. |
| `R3.5` | The only `HUMAN`-class rows with an `AUTO` verdict are [transition-matrix.md:84](transition-matrix.md#L84), [:97](transition-matrix.md#L97) and [:393](transition-matrix.md#L393). | **derived** — enumerated over every row of the frozen matrix by its `required_capability` cell against the seventeen `HUMAN`-class register rows ([authority-matrix.md:58](authority-matrix.md#L58), [:59](authority-matrix.md#L59), [:61](authority-matrix.md#L61)–[:66](authority-matrix.md#L66), [:78](authority-matrix.md#L78), [:79](authority-matrix.md#L79), [:107](authority-matrix.md#L107), [:109](authority-matrix.md#L109), [:110](authority-matrix.md#L110), [:125](authority-matrix.md#L125), [:134](authority-matrix.md#L134), [:143](authority-matrix.md#L143), [:146](authority-matrix.md#L146)); the other fifteen rows carry `DECIDE(K)`. This enumerates rows, not coverage of the ten capabilities with none (§6.1). |
| `R3.6` | For the two non-exempt `AUTO` rows the required kind is `APPROVE`. | **chosen** — the matrix names no kind. `APPROVE` exists in the closed enum ([domain-model.md:693](domain-model.md#L693)) and the sibling archive row requires it ([transition-matrix.md:96](transition-matrix.md#L96)). The class requires a decision, not this kind. |
| `R3.7` | Given `R3.6`, the creation decision is snapshot-bound and binds to the row's own `SNAP`, and the `ABANDONED → ARCHIVED` decision needs a current snapshot although that row's evidence cell is `—`. | **conditional derivation** from `R3.6` plus [domain-model.md:702](domain-model.md#L702), [:703](domain-model.md#L703), [:719](domain-model.md#L719), [transition-matrix.md:84](transition-matrix.md#L84), [:97](transition-matrix.md#L97). Disclosed as a semantic change to the archive row; no cell of it is amended. |
| `R3.8` | `decision.record` is self-held. | **chosen** — [transition-matrix.md:399](transition-matrix.md#L399) says the human act *is* the decision, which supports the absence of a further policy decision but not the holding. Revision 01's claim that the alternative is an unavoidable regress is withdrawn: the real gap is frozen grant possession, and this is the named exception that closes it. |
| `R3.9` | Per-act exercise is not ceiling-bounded (`AX-13`). | **chosen in whole** — revision 01 called the creation case forced; that is withdrawn. [domain-model.md:141](domain-model.md#L141) requires a human-supplied ceiling without prescribing an empty one, and a prospective project's fields are available inside the creating transaction ([VERIFY-01:52](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L52)–[:55](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L55)), so nothing forces the exemption. The containment that replaces the ceiling is `AX-12`, `AX-13` and steps 1–9. |
| `R3.10` | The authorizing decision delegates nothing, by an explicit predicate. | **chosen** — step 6 *requires* `grants = ∅` and `revokes = ∅`. Revision 01 inferred that profile from classification; [domain-model.md:698](domain-model.md#L698) and [:699](domain-model.md#L699) permit non-empty sets, so the profile is a choice and is now written as a check. Given the predicate, [evidence-model.md:82](evidence-model.md#L82), [:84](evidence-model.md#L84) and [:95](evidence-model.md#L95) then place the record outside the promotion row. |
| `R3.11` | The event's actor is the performer, with `on_behalf_of` for a runtime-mediated act (`AX-16`). | **chosen** — revision 01 equated the event's actor with the decider, which no frozen rule states. [authority-matrix.md:34](authority-matrix.md#L34) forbids kernel self-granting and [domain-model.md:714](domain-model.md#L714) forbids a non-human decision author; neither fixes the authorized event's actor. `on_behalf_of` is frozen machinery ([domain-model.md:60](domain-model.md#L60)) and is what lets the kernel's credential resolution under `secret.read` ([roadmap_adapter.md:78](roadmap_adapter.md#L78), [:90](roadmap_adapter.md#L90)) be attributed without a `HUMAN` actor on a kernel-mediated event. |
| `R3.12` | The creation transaction is one store transaction containing four ordered appends (`AX-17`). | **chosen** — [domain-model.md:38](domain-model.md#L38) enforces referential integrity without prescribing when each reference is checked. The basis is `VERIFY-01`'s `D01-F02-006` refutation ([VERIFY-01:98](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L98), [:104](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L104)–[:109](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L109)) — deferred reference checks with ordered events under one commit — with its project/snapshot instance at [VERIFY-01:50](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L50)–[:55](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L55). The refuted half of `D01-F02-002` is not cited. |
| `R13.14` | Four events are required, not two. | **conditional** on `AX-14`/`R3.6`'s chosen approval and `AX-17`'s consumption, and then **derived**: every transition emits an event before the new state is observable ([domain-model.md:797](domain-model.md#L797)), each names exactly one capability ([domain-model.md:789](domain-model.md#L789), [:890](domain-model.md#L890)) so recording under `decision.record` cannot merge with creation under `project.create`, the decision is recorded by [transition-matrix.md:393](transition-matrix.md#L393) and consumed by [:394](transition-matrix.md#L394), and chain order is authoritative for replay ([evidence-model.md:187](evidence-model.md#L187)). Given a different chosen kind or no approval the count would differ; revision 01's snapshot-0/creation-1 account is withdrawn. |
| `R13.15` | Each event's cited records have lower `seq`. | **conditional** on the witness above. Event 1 cites the snapshot recorded by event 0, event 2 cites that snapshot and the decision recorded at 1, event 3 cites event 2. [evidence-model.md:178](evidence-model.md#L178) orders `required_evidence` and is retained by amendment 16; it does not order `authority_ref`, so event 2's decision reference is ordered by this witness rather than by that check. `subject_snapshot_id` names the `RealitySnapshot` recorded by event 0, never an `AuditEvent` id ([domain-model.md:703](domain-model.md#L703)). |
| `R13.16` | The procedure covers seven capabilities, not seventeen. | **derived** — steps 2, 5 and 8 read the row; ten `HUMAN` capabilities are named by no legal row (§6.1). Revision 01 claimed the whole class. |

### Amendment 14 — project-scope grants (new authority-matrix §5.3)

**Target** insertion into `authority-matrix.md` immediately after amendment 13's §5.2,
anchored at [authority-matrix.md:277](authority-matrix.md#L277). **Current frozen text at the anchor:**

```
presence in `capability_request` change nothing.
```

**Proposed text** (inserted after amendment 13's §5.2)

```
### 5.3 Project-scope grants

The acts that establish a project's structure cannot be authorized by §5: the first
`roadmap.import` supplies the stages, and the first `contract.author` supplies the
contract, that an activation would have to reference. A project grant authorizes exactly
those acts, and is one of `AX-1`'s four forms.

| step | operation |
|---|---|
| 1 | `P₀` = the `grants` set of a `HumanDecision{kind: GRANT_CAPABILITY, scope: PROJECT}` live at the moment of the act: `decision_state = VALID`, unexpired, nonce unconsumed |
| 2 | `P₁ = P₀ ∩ project.capability_ceiling`; differences denied `NOT_IN_CEILING` (`AX-4`, `P-INV-2`) |
| 3 | `P₂ = P₁` minus capabilities denied by the §3 mode gate; denied `MODE_FORBIDDEN` |
| 4 | `P₃ = P₂` minus every `KERNEL`, `HUMAN` and `NEVER` capability; denied `NEVER_GRANTABLE` (`AX-6`, `AX-7`, §5.2) |
| 5 | `P₄ = P₃` minus every capability whose §2 `grantable by` column does not name `HUMAN_PRINCIPAL`; denied `NO_GRANTOR` |
| 6 | the granted set is `P₄`. §4.1 is not applied: it is the per-`WorkerInvocation` role table and a project grant reaches no invocation (`AX-4`) |
| 7 | every denial from steps 2–5 is recorded in the denial `AuditEvent` per `AX-8` |

| id | rule |
|---|---|
| `AX-18` | A project grant is never copied into `ContractActivationRecord.granted_capabilities`, `WorkerInvocation.granted_capabilities` or `StageRun.effective_capabilities`. A worker's authority remains exactly `AX-3`'s run grant, resolved by §5 and bounded by `AX-4`'s first clause, so `A-INV-2` holds unchanged: activation is still the only entity conferring authority on a run. |
| `AX-19` | An event exercising a project grant sets `authority_ref` to the granting `decision_id`, live at `recorded_at` (evidence-model §3.3). That citation is the grant's basis record under `AX-11`. `G-2` is unchanged: a `HumanDecision` is already an admissible authority citation. The grant is never "recorded for" a transition and so never takes `VALID → CONSUMED`: it ends exactly as §1.1 says, at `expires_at`, at the `scope` boundary, or on leaving `VALID`, by the frozen rows of transition-matrix §7.5 — precisely as a run grant's own basis decision (§5.1) is never consumed by the activation it grounds. Its nonce therefore stays unconsumed for the grant's life, which is what §5.1 already requires of a live grant, and `HD-INV-3` is untouched: the decision is used once, as one grant, and `AX-18` keeps it out of every run set. |
| `AX-20` | `POLICY_ENGINE` is not an admissible grantor of a project grant. An `AUTONOMOUS` project's first import and first contract still require a live human grant, exactly as `roadmap.writeback` does in either mode (§5.1). |
```

**Closes** `D01-F02-005`. Fixes the `R6.5` half of `DESIGN-04-011`.

| id | rule | basis |
|---|---|---|
| `R6.1` | The first import and first contract authoring can be authorized by a project grant with no activation. | **derived** that both are `ORD` with `HUMAN_PRINCIPAL` as a named grantor — [authority-matrix.md:74](authority-matrix.md#L74), [:86](authority-matrix.md#L86); **chosen** that a project grant authorizes them, with amendments 6–8 supplying the realization change. |
| `R6.2` | The grant is bounded by `project.capability_ceiling`. | **derived** — [domain-model.md:141](domain-model.md#L141), [:153](domain-model.md#L153) bound every grant in the project by the ceiling. |
| `R6.3` | The §3 mode gate is retained; the `KERNEL`/`NEVER` exclusion is not optional. | **chosen** for adopting the mode gate in a new resolution, mirroring §5 step 3 ([authority-matrix.md:243](authority-matrix.md#L243)); **derived** for the `KERNEL`/`NEVER` exclusion, which [authority-matrix.md:17](authority-matrix.md#L17) and [:18](authority-matrix.md#L18) require independently of this step. |
| `R6.4` | §4.1 is not applied. | **conditional** — see amendment 6, which performs the `AX-4` narrowing this depends on. |
| `R6.5` | A `GRANT_CAPABILITY` decision survives the exercise of its grant and is never consumed by it. | **derived** — [transition-matrix.md:394](transition-matrix.md#L394) consumes a decision that "discharged the transition it was recorded for", which a standing grant is not; [:396](transition-matrix.md#L396) is the frozen route for expiry or leaving the `scope` boundary, needing no evidence and no new row; and [authority-matrix.md:263](authority-matrix.md#L263) already requires a run grant's basis decision to be live with its **nonce unconsumed** at activation time, so the frozen design already carries an unconsumed grant decision. [authority-matrix.md:41](authority-matrix.md#L41) gives the three ways such a grant ends. Revision 02's `AX-20` lifecycle is **withdrawn**: it invoked `VALID → CONSUMED` without a discharge, overlapped [:396](transition-matrix.md#L396), and was unreachable after [:401](transition-matrix.md#L401) makes those states terminal. No row of §7.5 is amended. Per-act decisions under §5.2 are unaffected and are consumed by the transition they discharge. |
| `R6.6` | `POLICY_ENGINE` cannot grant at project scope. | **chosen** — a persisted policy evaluation ([authority-matrix.md:264](authority-matrix.md#L264)) is not an entity `G-2` admits as an authority citation ([domain-model.md:888](domain-model.md#L888)), so admitting it needs a further change. The human path exists in both modes, so no row is left unreachable. |
| `R6.7` | A project grant carries no `HUMAN`-class capability. | **chosen** — those are exercised per act under §5.2 (`R3.3`), with `decision.record` the stated exception. |

### Amendment 15 — `G-1`

**Target** [domain-model.md:887](domain-model.md#L887) (§12 Global invariants). **Current frozen text:**

```
| `G-1` | No entity outside `{ValidationReceipt, WorkerReceipt, CommitReceipt, ReviewAttestation, RealitySnapshot}` may be cited as `required_evidence`. A `Review` is never cited directly: the kernel-minted `ReviewAttestation` is what the `RVW(v)` token in `transition-matrix.md` resolves to, so a judgmental criterion is discharged by the kernel's measurement of the review, not by the reviewer's own verdict. |
```

**Proposed text**

```
| `G-1` | A `required_evidence` cell is a conjunction of **citations**, each of which may itself be a disjunction of alternatives; a cell is not typed as a whole, and each citation carries its own kind. An **evidence citation** names a record that measures reality, and no entity outside `{ValidationReceipt, WorkerReceipt, CommitReceipt, ReviewAttestation, RealitySnapshot}` may be cited as one; a `Review` is never cited directly, the kernel-minted `ReviewAttestation` being what the `RVW(v)` token in `transition-matrix.md` resolves to, so a judgmental criterion is discharged by the kernel's measurement of the review, not by the reviewer's own verdict. A **prerequisite citation** names a record of one of exactly four kinds: an activation, a `HumanDecision`, an `Escalation`, or an `AuditEvent` the row names — the last including a persisted artifact or durable identity, cited as the event that persisted it. These four and the evidence citation are the **only** admissible kinds; a cell naming a record of any other kind is outside this rule and is not closed by it. A prerequisite citation is never a measurement and never makes a criterion `MET`. It has exactly the effect another rule of this design gives it: a `HumanDecision{kind ∈ {WAIVE, ACCEPT_RISK}}` discharges the shortfall it names by producing the `WAIVED` outcome `evidence-model.md` §4 reads, and an `Escalation` gates only as §2's `CLAIM` row permits. Where a cell element names no record at all — a clock reading, a recomputation — it is a precondition, not a citation. |
```

**Closes** `D01-F02-004`. Fixes `DESIGN-04-005`, `-006` and part of `-008`.

| id | rule | basis |
|---|---|---|
| `R7.1` | The `required_evidence` column already holds records of both kinds. | **derived** — [transition-matrix.md:189](transition-matrix.md#L189) (`ACT`), [:266](transition-matrix.md#L266) (activation), [:141](transition-matrix.md#L141) (`DEC`), [:128](transition-matrix.md#L128) (`ESC`), [:394](transition-matrix.md#L394) (`AuditEvent`) against the five-entity allow-list and [evidence-model.md:82](evidence-model.md#L82)–[:86](evidence-model.md#L86). It exposes the mismatch; it does not derive this repair. |
| `R7.2` | The five-entity allow-list is carried over verbatim and now binds evidence citations. | **chosen** — only the five names and the `Review` exclusion are verbatim; restricting the allow-list's reach to a subcategory of citation changes the domain of [domain-model.md:887](domain-model.md#L887), which is part of the choice in `R7.4`, not a frozen derivation. |
| `R7.3` | A prerequisite citation is never a measurement, and a waiver decision nonetheless discharges the shortfall it names. | **derived** — `W` is an input to `observed_satisfaction` at [evidence-model.md:204](evidence-model.md#L204), the `SATISFIED` row reads `MET` **or** `WAIVED` at [:210](evidence-model.md#L210), and `WAIVED` is a `CriterionState.outcome` at [domain-model.md:246](domain-model.md#L246). The rows that use waivers per shortfall are [transition-matrix.md:139](transition-matrix.md#L139), [:207](transition-matrix.md#L207) and [:336](transition-matrix.md#L336). Revision 01's blanket "discharges no criterion" is withdrawn, and so is its attribution to `AX-9`: [authority-matrix.md:20](authority-matrix.md#L20) forbids a **capability** substituting for evidence and says nothing about an informed waiver, while [domain-model.md:716](domain-model.md#L716) governs uninformed approvals. |
| `R7.4` | Typing per citation, rather than widening the allow-list, is the correction. | **chosen** — the rejected alternative admits an activation, a decision or an escalation as evidence of satisfaction, which is the confusion the taxonomy exists to prevent ([evidence-model.md:55](evidence-model.md#L55)–[:65](evidence-model.md#L65)). Revision 01's whole-cell rule is withdrawn: it cannot express `ACT` + `SNAP` ([transition-matrix.md:123](transition-matrix.md#L123), [:189](transition-matrix.md#L189)) or `RVW` + `ESC` ([:137](transition-matrix.md#L137)). |

### Amendment 16 — the evidence-reachability verification check

**Target** [evidence-model.md:178](evidence-model.md#L178) (§3.3 Verification). **Current frozen text:**

```
| evidence reachability | every `required_evidence` cited by a transition event resolves to an event of class `EVIDENCE` with `seq` lower than the transition's | `INTEGRITY_VIOLATION` |
```

**Proposed text**

```
| evidence reachability | for each citation in the row's `required_evidence` (`G-1`), and for a disjunctive citation the one alternative the transition event names, that citation resolves to an earlier event of the same project with `seq` lower than the transition's, of the class its record carries: `EVIDENCE` for an evidence citation; `AUTHORITY` for an activation; `DECISION` for a `HumanDecision`; `CLAIM` for an `Escalation`; and any class for an `AuditEvent` the row names, including one that persisted a cited artifact or durable identity. A cell element naming no record is a precondition and resolves to no event. A citation of any other kind is not resolved by this check and its row is not closed (`G-1`) | `INTEGRITY_VIOLATION` |
```

**Closes** `D01-F02-004`. Fixes `DESIGN-04-005` and `-008`.

| id | rule | basis |
|---|---|---|
| `R8.1` | The strictly-lower-`seq` requirement is retained for every citation. | **derived** — carried over from the frozen check. An earlier `seq` still does not imply an earlier commit (`R3.12`). |
| `R8.2` | The class test is per citation, using the frozen classification. | **chosen** as a check; **derived** in its content for the four named record types — [evidence-model.md:83](evidence-model.md#L83) (activation is `AUTHORITY`), [:82](evidence-model.md#L82) (decision is `DECISION`), [:85](evidence-model.md#L85) (escalation is `CLAIM`), [:86](evidence-model.md#L86) (the `AuditEvent` is the envelope). |
| `R8.3` | An `AuditEvent` the row names — including one that persisted a cited artifact or durable identity — is exempt from the class test. | **chosen** — being an envelope at [evidence-model.md:86](evidence-model.md#L86) does not derive an exception to the frozen `EVIDENCE` test; the exemption is justified by the consuming row's target ([transition-matrix.md:394](transition-matrix.md#L394)) and by the durable-identity rule the matrix cites ([evidence-model.md:151](evidence-model.md#L151), [transition-matrix.md:305](transition-matrix.md#L305), [:307](transition-matrix.md#L307)). It is one kind in `G-1`, amendment 16 and amendment 17 alike, so all three admit the same set; [evidence-model.md:151](evidence-model.md#L151) orders the identity before the external effect and not before this transition, so the earlier persisting event is part of the choice. |

### Amendment 17 — the `required_evidence` column semantics

**Target** [transition-matrix.md:48](transition-matrix.md#L48) (§1 Column semantics). **Current frozen text:**

```
| `required_evidence` | receipt/snapshot classes that must exist and be current; `—` means none |
```

**Proposed text**

```
| `required_evidence` | a conjunction of citations that must exist and be current, each typed on its own and each possibly a disjunction of alternatives (`G-1`): an evidence citation (receipt or snapshot) discharges the row's criterion; a prerequisite citation — an activation, a decision, an `Escalation`, or an `AuditEvent` the row names, including one that persisted a cited artifact or durable identity — must exist and discharges a criterion only where another rule gives it that effect, as a waiver decision does; an element naming no record is a precondition; a citation of any other kind is not admitted by `G-1`; `—` means none |
```

**Closes** `D01-F02-004`. Fixes `DESIGN-04-005`.

| id | rule | basis |
|---|---|---|
| `R9.1` | The column holds more than receipts and snapshots. | **derived** — the frozen cells in `R7.1` and the 44-row inventory in §2.22. |
| `R9.2` | The legend adopts `G-1`'s vocabulary, including the conjunction/disjunction structure. | **chosen** — wording, so the legend and the invariant agree. No seventh column is added, so the disclosed change stays inside the six semantic columns at [transition-matrix.md:45](transition-matrix.md#L45)–[:52](transition-matrix.md#L52). |

### Amendment 18 — `CLAIM` gating

**Target** [evidence-model.md:62](evidence-model.md#L62) (§2, the four-class table). **Current frozen text:**

```
| `CLAIM` | "what does someone say is true?" | any actor, typically a worker | no — only its provenance is verifiable | **never** | yes, trivially |
```

**Proposed text**

```
| `CLAIM` | "what does someone say is true?" | any actor, typically a worker | no — only its provenance is verifiable | **never on its asserted content**; a row may name it as a prerequisite (`G-1`) and gate on its existence, its provenance, and the control fields the runtime establishes — for an `Escalation`, `trigger`, `status`, `severity`, `auto_resolvable` and the holder bindings — which prove only what the runtime recorded. The asserted fields, `summary` and `evidence_refs` and any `Claim` they carry, gate nothing | yes, trivially |
```

**Closes** `D01-F02-004`. Fixes `DESIGN-04-007`.

| id | rule | basis |
|---|---|---|
| `R13.18` | Admitting an escalation as a mandatory prerequisite requires amending this cell, not only retaining the class label. | **derived** — this cell says `CLAIM` can **never** gate a transition, and [evidence-model.md:85](evidence-model.md#L85) classes `Escalation` as `CLAIM`, while the frozen matrix makes an `ESC` citation mandatory on twelve rows of the inventory in §2.22 ([transition-matrix.md:128](transition-matrix.md#L128), [:132](transition-matrix.md#L132), [:137](transition-matrix.md#L137), [:158](transition-matrix.md#L158), [:161](transition-matrix.md#L161), [:164](transition-matrix.md#L164), [:195](transition-matrix.md#L195), [:200](transition-matrix.md#L200), [:204](transition-matrix.md#L204), [:210](transition-matrix.md#L210), [:353](transition-matrix.md#L353), [:358](transition-matrix.md#L358)). Revision 01 left the contradiction in place; revision 02 miscounted them as thirteen. |
| `R13.19` | The boundary is asserted content versus runtime-established control fields, not existence versus everything else. | **chosen** — the cell now names which fields may gate. It is available because the same row already says a claim's provenance *is* verifiable while its content is not; the named fields are the ones the frozen model sources to the runtime ([domain-model.md:737](domain-model.md#L737), [:738](domain-model.md#L738), [:743](domain-model.md#L743)–[:746](domain-model.md#L746), [:748](domain-model.md#L748)) and the trigger must have actually fired for the escalation to exist ([transition-matrix.md:412](transition-matrix.md#L412)), while `summary` and `evidence_refs` ([domain-model.md:739](domain-model.md#L739), [:740](domain-model.md#L740)) carry what the reporter said. `G-3` ([domain-model.md:889](domain-model.md#L889)) and the bare `Claim`'s own never-gates rule ([domain-model.md:113](domain-model.md#L113)) are untouched, so no worker assertion becomes a gate: a worker can cause a legitimate escalation to exist and thereby stop work, which is the fail-stop path, and can neither choose an unfired trigger nor assert `auto_resolvable`. Revision 02 called [transition-matrix.md:132](transition-matrix.md#L132)'s trigger qualifier an unchanged precondition; it is inside that row's `required_evidence` cell and is corrected in §2.22. |

### Amendment 19 — genesis installs the project's chain state

**Target** [evidence-model.md:128](evidence-model.md#L128) (§3.1, step 6). **Current frozen text:**

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
| `R10.1` | The first append installs the project record and initializes the chain fields in one atomic write. | **chosen** — [evidence-model.md:127](evidence-model.md#L127) specifies event zero's predecessor hash and this step specifies the head update for an existing chain; neither specifies the installation, which is the residue `VERIFY-01` retains. Installing a transaction-local project at genesis does not by itself fix the creation transition's `seq`, which is `AX-17`'s business. |
| `R10.2` | `event_head` and `event_seq` remain derived, mutable, runtime-owned project fields. | **derived** — [domain-model.md:145](domain-model.md#L145), [:146](domain-model.md#L146); no field table is amended. |
| `R10.3` | The `schema_version` term in the genesis preimage is the domain model's version, not a storage schema version. | **derived** for the semantics — [evidence-model.md:127](evidence-model.md#L127) names `schema_version` and [domain-model.md:134](domain-model.md#L134) defines `Project.schema_version` as the domain model version. Separately and **chosen**: an implementation binding this to a `SCHEMA_VERSION` constant, distinct from a storage `STORAGE_VERSION` / `PRAGMA user_version`, is an implementation convention; no frozen design blob defines either constant, and the absence of a storage term does not define one. Line 127 is not amended. |

### Amendment 20 — append step 2 on an empty chain

**Target** [evidence-model.md:135](evidence-model.md#L135) (§3.2, step 2). **Current frozen text:**

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
| `R11.1` | The empty-chain branch reserves `seq = 0`. | **chosen** that an explicit branch is added, since the frozen step reads a field with no value before the first event; **derived** that the reserved value is zero — [evidence-model.md:127](evidence-model.md#L127), [:174](evidence-model.md#L174), [domain-model.md:779](domain-model.md#L779). |
| `R11.2` | The per-project lock and the no-skip rule are unchanged, including for the first append. | **derived** — carried over; [evidence-model.md:190](evidence-model.md#L190) untouched. |

### Amendment 21 — append step 3 on an empty chain

**Target** [evidence-model.md:136](evidence-model.md#L136) (§3.2, step 3). **Current frozen text:**

```
| 3 | read `prev_event_hash = event_head` | — |
```

**Proposed text**

```
| 3 | read `prev_event_hash = event_head`; at `seq = 0`, `event_head` is unset and `prev_event_hash` is the §3.1 genesis constant instead | — |
```

**Closes** `D01-F02-002` (retained half). Fixes `DESIGN-04-013`.

| id | rule | basis |
|---|---|---|
| `R12.1` | The first event's predecessor hash comes from the genesis formula. | **derived** — [evidence-model.md:127](evidence-model.md#L127) and [domain-model.md:780](domain-model.md#L780) already specify it for `seq = 0`; the append step does not, which is the residue. |
| `R13.20` | The row keeps all three cells of the append table. | **derived** — the table's columns are `step`, `operation`, `failure handling` ([evidence-model.md:132](evidence-model.md#L132)) and the frozen row's third cell is `—` ([:136](evidence-model.md#L136)). Revision 01's two-cell replacement was malformed. |

### Amendment 22 — the authority trace

**Target** [evidence-model.md:282](evidence-model.md#L282) (§7 Export). **Current frozen text:**

```
| authority trace | for one action: capability used, activation record, grant chain, mode, policy digest | answering "what allowed this?" |
```

**Proposed text**

```
| authority trace | for one action: capability used, mode, policy digest, and the authority the action was exercised under — the activation record and grant chain for a run grant; the granting `HumanDecision` for a project grant; the authorizing `HumanDecision` for a per-act exercise; the kernel's own holding for a `KERNEL` capability | answering "what allowed this?" |
```

**Closes** `D01-F02-001` and `D01-F02-005`.

| id | rule | basis |
|---|---|---|
| `R13.21` | The export that answers "what allowed this?" must name whichever authority form the action used. | **chosen** — the frozen row names an activation record unconditionally, so a pre-activation `project.create` or first `roadmap.import` has nothing to put in the field and the trace is unrealizable for exactly the acts amendments 3–5, 13 and 14 make legal. The alternative — stating that pre-activation acts have no exportable trace — is rejected: the authority exists and is already cited by `AuditEvent.authority_ref` ([domain-model.md:790](domain-model.md#L790)), so the trace can name it. The other two export artifacts ([evidence-model.md:280](evidence-model.md#L280), [:281](evidence-model.md#L281)) are untouched, and every export remains itself appended ([:285](evidence-model.md#L285)–[:286](evidence-model.md#L286)). |

### Amendment 23 — `A-INV-2`

**Target** [domain-model.md:410](domain-model.md#L410) (§7 `ContractActivationRecord` invariants). **Current frozen text:**

```
**A-INV-2** Activation is the **only** entity that confers authority on a run.
```

**Proposed text**

```
**A-INV-2** Activation is the **only** entity that confers a run's **execution authority**:
its `granted_capabilities`, and the `StageRun.effective_capabilities` frozen from them.
Authority to govern a run from outside it — a human decision authorizing `stage.reject` on
the run's own row — is not execution authority, confers no capability on the run, and adds
nothing to either set (authority-matrix §5.2, `AX-18`).
```

**Closes** `D01-F02-003`.

| id | rule | basis |
|---|---|---|
| `R13.22` | Governing a run and executing within it are different authorities, and the frozen wording covers only the second. | **derived** that the distinction is required — [transition-matrix.md:208](transition-matrix.md#L208) is a run transition whose `required_capability` is the `HUMAN` capability `stage.reject`, which [authority-matrix.md:221](authority-matrix.md#L221) denies to every role, so no activation can supply it and §5.2 must; **chosen** to scope this invariant rather than leave it unqualified and assert that keeping the run's sets unchanged is equivalent, which is what revision 02 did. `AX-18` and amendment 8's `C-INV-3` keep every run set sourced from the activation, so nothing a worker holds changes. |

### 2.21 The kinds `G-1` admits, and the kinds it does not

Amendment 16 assigns a class by the kind of record cited. `G-1`, amendment 16 and
amendment 17 admit the same five kinds and no others.

| admissible kind, as the frozen cells name it | citation kind | class |
|---|---|---|
| `SNAP`, `VR(pass)`, `VR(any)`, `WR`, `CR`, `RVW(v)`, a named `CommitReceipt`, "usage records", "terminal receipt per drained operation" — each resolving to one of the five entities | evidence | `EVIDENCE` |
| `ACT`, a named `ContractActivationRecord`, a successor activation | prerequisite | `AUTHORITY` |
| `DEC(K)` for every `K`, "`DEC` referenced by each resolution" | prerequisite | `DECISION` |
| `ESC(s)`, with or without a trigger qualifier | prerequisite | `CLAIM`, on existence, provenance and runtime-established control fields (amendment 18) |
| an `AuditEvent` the row names: the discharged transition's own event, a revocation event, a denial event, or the event that persisted a cited artifact or durable identity | prerequisite | envelope, any class |

| inadmissible | consequence |
|---|---|
| A policy-evaluation record ([transition-matrix.md:157](transition-matrix.md#L157), [:170](transition-matrix.md#L170)) or a chain-verification record ([:161](transition-matrix.md#L161), [:167](transition-matrix.md#L167), [:174](transition-matrix.md#L174), [:175](transition-matrix.md#L175), [:397](transition-matrix.md#L397)) | Neither is one of the five entities nor any prerequisite kind above. `G-1` admits no kind for them, and revision 02's `CLAIM`-by-the-runtime typing is withdrawn: [evidence-model.md:63](evidence-model.md#L63) restricts `EVIDENCE` minting to five `KERNEL` capabilities but does not make a non-qualifying record a `CLAIM`, and [:85](evidence-model.md#L85) classifies `Escalation` only. Those cells are **unclosed** (§6.4). |
| A cell element naming no record: a clock reading ([:340](transition-matrix.md#L340)), a recomputation ([:121](transition-matrix.md#L121)), a comparison trigger ([domain-model.md:761](domain-model.md#L761), [:762](domain-model.md#L762)) | It is a precondition and resolves to no event. Where the row nonetheless prints a separate record cell, as [:412](transition-matrix.md#L412) does, a precondition does not discharge that cell and it stays unclosed. |

Two representations in the admissible set are **chosen**, not forced by the frozen words:
the revocation event for [:191](transition-matrix.md#L191), against the activation's own
revocation fields ([domain-model.md:402](domain-model.md#L402)–[:404](domain-model.md#L404)),
and the persisting event for [:305](transition-matrix.md#L305), [:307](transition-matrix.md#L307)
and [:337](transition-matrix.md#L337) (`R8.3`). Revision 02's claim that nothing else in
this table is optional is withdrawn.

### 2.22 The review's 44-row inventory

Every row the reviews' scans identified as naming `ACT`, `DEC`, `ESC`, an
activation/revocation record, or an `AuditEvent`, grouped by the citation shape that
resolves it. `M`, `U`, `C` and `W` are `DESIGN-04-FINDINGS-01`'s codes for mixed, untyped,
`CLAIM`-gate and waiver rows. Independent lifecycle and authority findings are noted where
they survive; typing them changes admissibility and nothing else.

| rows | citations, typed per citation and per alternative | resolved |
|---|---|---|
| [:123](transition-matrix.md#L123), [:189](transition-matrix.md#L189) | `ACT` → `AUTHORITY`; `SNAP` → `EVIDENCE` | **M** — two citations, two kinds, no cell-level class. [:189](transition-matrix.md#L189) is one of `D01-F02-004`'s original examples. |
| [:140](transition-matrix.md#L140), [:141](transition-matrix.md#L141), [:142](transition-matrix.md#L142), [:144](transition-matrix.md#L144), [:156](transition-matrix.md#L156), [:168](transition-matrix.md#L168), [:169](transition-matrix.md#L169), [:172](transition-matrix.md#L172), [:176](transition-matrix.md#L176), [:206](transition-matrix.md#L206), [:208](transition-matrix.md#L208), [:209](transition-matrix.md#L209), [:336](transition-matrix.md#L336) | one `DEC(K)` citation → `DECISION`, live and informed at this transition ([:74](transition-matrix.md#L74)) | **P** — each row's own guards, kinds and policy verdicts are retained. [:142](transition-matrix.md#L142) is a **stage**-subject `ABANDON`, so it is snapshot-bound and keeps the `SNAP` its recording row requires; amendment 12's conditional does not reach it (`R13.12`). [:336](transition-matrix.md#L336) is **W**: its waiver discharges the waivable criterion. [:172](transition-matrix.md#L172) and [:206](transition-matrix.md#L206) keep `D01-F02-008`. [:208](transition-matrix.md#L208) is a run row under `HUMAN` `stage.reject` and is the counterexample amendment 23 addresses. |
| [:128](transition-matrix.md#L128), [:132](transition-matrix.md#L132), [:158](transition-matrix.md#L158), [:195](transition-matrix.md#L195), [:200](transition-matrix.md#L200), [:204](transition-matrix.md#L204), [:210](transition-matrix.md#L210) | `ESC(s)` → `CLAIM`, gating on existence, provenance and the runtime-established control fields | **P, C** — closed by amendment 18. At [:132](transition-matrix.md#L132) and [:210](transition-matrix.md#L210) the cell itself selects by `trigger`; that qualifier is **inside `required_evidence`**, not a precondition as revision 02 said, and it gates as a control field. `status`, the holder binding and `auto_resolvable` gate the same way at [:128](transition-matrix.md#L128) and [:158](transition-matrix.md#L158). |
| [:137](transition-matrix.md#L137), [:139](transition-matrix.md#L139), [:162](transition-matrix.md#L162), [:164](transition-matrix.md#L164), [:173](transition-matrix.md#L173), [:207](transition-matrix.md#L207), [:338](transition-matrix.md#L338), [:348](transition-matrix.md#L348), [:353](transition-matrix.md#L353), [:358](transition-matrix.md#L358), [:414](transition-matrix.md#L414) | mixed and disjunctive cells: `RVW`/`VR`/`SNAP`/receipts → `EVIDENCE`, `DEC` → `DECISION`, `ESC` → `CLAIM`, each conjunct on its own and each disjunction resolved by the alternative the event names | **M, C, W** — no whole-cell class is assigned anywhere. [:139](transition-matrix.md#L139) and [:207](transition-matrix.md#L207) are **W**: the per-shortfall waiver discharges that shortfall as `WAIVED` while the remaining criteria stay `MET` by evidence. [:173](transition-matrix.md#L173), [:338](transition-matrix.md#L338) and [:414](transition-matrix.md#L414) are typed per alternative, not as a fixed cell type. [:358](transition-matrix.md#L358) keeps `D01-F02-010`. |
| [:266](transition-matrix.md#L266), [:269](transition-matrix.md#L269) | the named activation → `AUTHORITY` | **P** — `authority_chain` and the per-capability basis stay mandatory (`A-INV-3`), and amendment 7 keeps that clause in force for run grants. [:269](transition-matrix.md#L269) keeps `D01-F02-007`. |
| [:394](transition-matrix.md#L394) | the discharged transition's own `AuditEvent` → envelope, any class, lower `seq` than the consuming event | **P** — under `R8.3`'s disclosed exemption. `AX-19`'s grant never reaches this row (`R6.5`). |
| [:305](transition-matrix.md#L305) | `ACT` → `AUTHORITY`; the persisted `InvocationRequest` and its `idempotency_key` → the `AuditEvent` that made that identity durable | **U** — closed as one admissible kind in `G-1`, amendment 16 and amendment 17 alike. The earlier persisting event is a **chosen** representation: [evidence-model.md:151](evidence-model.md#L151) orders the identity before the external effect, not before this transition (`R8.3`). |
| [:191](transition-matrix.md#L191) | the revocation record → the `AuditEvent` of the `contract.revoke` transition | **U** — closed as the same kind, and **chosen**: the frozen words name no particular record, and the activation's own revocation fields ([domain-model.md:402](domain-model.md#L402)–[:404](domain-model.md#L404)) are an equally available representation. |
| [:270](transition-matrix.md#L270) | `DEC(REVOKE_CAPABILITY)` → `DECISION`, **or** the triggering record → typed only where it is one of `G-1`'s kinds | **P / U** — the decision branch is typed. A triggering condition that names no record is a precondition; one that names a record outside `G-1`'s kinds is not closed (§6.4). |
| [:340](transition-matrix.md#L340) | `DEC(REVOKE_CAPABILITY)` → `DECISION`, **or** the clock → a precondition, no citation | **P** — a clock reading is not made into a record. |
| [:161](transition-matrix.md#L161), [:170](transition-matrix.md#L170), [:174](transition-matrix.md#L174) | the `ESC(OPEN)` alternative at [:161](transition-matrix.md#L161) → `CLAIM`; the `DEC(OVERRIDE)` alternative at [:170](transition-matrix.md#L170) and conjunct at [:174](transition-matrix.md#L174) → `DECISION`; the chain-verification and policy-re-evaluation records → **no admissible kind** | **NOT CLOSED.** `G-1` admits no kind for them and this document proposes none; revision 02's `CLAIM` typing is withdrawn. At [:161](transition-matrix.md#L161) and [:170](transition-matrix.md#L170) one alternative is typed and the other is not; at [:174](transition-matrix.md#L174) the unclosed record is a conjunct that `DEC(OVERRIDE)` cannot replace. Carried to §6.4. |
| [:171](transition-matrix.md#L171) | the `DEC` each resolution referenced → `DECISION` by kind | **NOT CLOSED.** Typing is not the obstruction: a resolution's decision is `CONSUMED` by the resolution it discharged ([:394](transition-matrix.md#L394), terminal per [:401](transition-matrix.md#L401)), while a cited `DEC` must be `VALID` here ([:74](transition-matrix.md#L74), [authority-matrix.md:289](authority-matrix.md#L289), [transition-matrix.md:522](transition-matrix.md#L522)). Revision 02's "live at that resolution" reading is withdrawn. Carried to §6.4. |

Forty of the 44 rows are typed end to end. Four are not:
[:161](transition-matrix.md#L161) and [:170](transition-matrix.md#L170) have one typed
alternative and one unclosed, [:174](transition-matrix.md#L174) has an unclosed conjunct,
and [:171](transition-matrix.md#L171) is unclosed outright (§6.4). Revision 02's claim that
all 44 receive a total typing is withdrawn. The adjacent cells at
[:121](transition-matrix.md#L121), [:157](transition-matrix.md#L157),
[:159](transition-matrix.md#L159), [:163](transition-matrix.md#L163),
[:165](transition-matrix.md#L165), [:167](transition-matrix.md#L167),
[:175](transition-matrix.md#L175), [:307](transition-matrix.md#L307),
[:337](transition-matrix.md#L337), [:397](transition-matrix.md#L397) and
[:412](transition-matrix.md#L412) resolve by §2.21's table, which says which of them are
unclosed.
---

## 3. Frozen locations this document leaves untouched

Every location a reader might expect these corrections to touch. Eleven locations listed as
untouched in revision 01 or 02 are now **amended** and appear in §2 instead:
[authority-matrix.md:12](authority-matrix.md#L12), [:15](authority-matrix.md#L15),
[:19](authority-matrix.md#L19), [:22](authority-matrix.md#L22), [:292](authority-matrix.md#L292),
[domain-model.md:380](domain-model.md#L380)–[:381](domain-model.md#L381), [:410](domain-model.md#L410),
[transition-matrix.md:49](transition-matrix.md#L49), [:393](transition-matrix.md#L393),
[evidence-model.md:62](evidence-model.md#L62) and [:282](evidence-model.md#L282).

| frozen location | current content, in brief | why untouched |
|---|---|---|
| [authority-matrix.md:13](authority-matrix.md#L13) `AX-2`, [domain-model.md:890](domain-model.md#L890) `G-4` | Exactly one capability per state-changing operation; absence ⇒ DENY. | Untouched and load-bearing: it is why the creation witness needs four events rather than a merged one (`R13.14`). |
| [authority-matrix.md:16](authority-matrix.md#L16) `AX-5` | No principal grants what it does not hold, except `HUMAN_PRINCIPAL` within the ceiling. | Compatible. A project grant is human-issued and ceiling-bounded (`R6.2`); a per-act exercise delegates nothing, now by the explicit predicate at §5.2 step 6 rather than by inference. |
| [authority-matrix.md:17](authority-matrix.md#L17) `AX-6`, [:18](authority-matrix.md#L18) `AX-7` | `NEVER` is never grantable; `KERNEL` is kernel-held, non-delegable, never in an invocation. | Untouched in substance. `AX-7` is the kernel form amendment 1 represents; it is **not** the rule `AX-15` excepts, which is `AX-1`. No amendment grants a `KERNEL` capability to a non-kernel actor or puts one in an invocation. |
| [authority-matrix.md:20](authority-matrix.md#L20) `AX-9` | A capability never substitutes for `required_evidence`. | Untouched, and its meaning is no longer overstated: it governs capabilities, not the effect of a waiver decision (`R7.3`). §5.2 step 8 invokes it only to keep a row's evidence unsubstituted. |
| [authority-matrix.md:30](authority-matrix.md#L30), [:34](authority-matrix.md#L34) | `HUMAN_PRINCIPAL`'s and `RUNTIME_KERNEL`'s grant powers. | Untouched. [:34](authority-matrix.md#L34) still forbids kernel self-granting a non-`KERNEL` capability; under `AX-16` the kernel never does, since the authority cited is the human's decision. It is not the basis of any actor-equality rule (`R3.11`). |
| [authority-matrix.md:41](authority-matrix.md#L41), [:263](authority-matrix.md#L263) | When a `HUMAN_DECISION` grant expires; a run grant's basis decision must be live with its nonce unconsumed. | Untouched, and together they are `R6.5`'s basis: the frozen design already carries an unconsumed grant decision, so a project grant needs no consumption transition. |
| [authority-matrix.md:51](authority-matrix.md#L51)–[:52](authority-matrix.md#L52), [:56](authority-matrix.md#L56)–[:147](authority-matrix.md#L147) | The `HUMAN` class legend and the capability register. | Untouched; §5.2 implements the legend and `AX-14` satisfies it on the `AUTO` rows. No class, grantor, default or mode restriction changes. `AX-15` states a holding the register does not describe; [:143](authority-matrix.md#L143) keeps describing grantability and keeps `DENY` as the default for anyone but the authenticated principal recording their own decision. |
| [authority-matrix.md:155](authority-matrix.md#L155)–[:173](authority-matrix.md#L173) | The §3 mode gate. | Applied unchanged by §5.2 step 3 and §5.3 step 3. No capability becomes available in a mode that denied it; `project.create` stays `DENY` in `AUTONOMOUS`. |
| [authority-matrix.md:190](authority-matrix.md#L190)–[:222](authority-matrix.md#L222) | §4.1's per-invocation grant table, including [:221](authority-matrix.md#L221). | Untouched, and the reason no run grant can carry a `HUMAN`-class capability (`R3.2`). The `C`/`D` tension at [:203](authority-matrix.md#L203), [:206](authority-matrix.md#L206) against [:221](authority-matrix.md#L221) predates this document and is not one of the five findings; no amendment relies on resolving it. Amendment 6 is what stops the table's inapplicability to project grants from being a silent change. |
| [authority-matrix.md:239](authority-matrix.md#L239)–[:277](authority-matrix.md#L277) | §5 resolution and §5.1 admissible grantors. | Unchanged for run grants. §5.2 and §5.3 are additive sections after §5.1; step 5's `KERNEL` removal and [:266](authority-matrix.md#L266)'s "never for a run's grant" both stand. |
| [authority-matrix.md:285](authority-matrix.md#L285)–[:291](authority-matrix.md#L291), [:293](authority-matrix.md#L293) | §6's other enforcement points. | Untouched, and two are relied on: decision freshness at [:289](authority-matrix.md#L289) enforces the liveness §5.2 step 4 and `AX-19` require, and the denial `AuditEvent` at [:293](authority-matrix.md#L293) is the destination amendment 9 uses. |
| [domain-model.md:38](domain-model.md#L38), [:273](domain-model.md#L273), [:390](domain-model.md#L390), [:778](domain-model.md#L778), [:805](domain-model.md#L805), [:865](domain-model.md#L865) | Reference integrity and the activation/run cardinality. | Untouched. They are compatible with one transaction and deferred checks; `R3.12` applies that reading rather than weakening them. |
| [domain-model.md:141](domain-model.md#L141), [:153](domain-model.md#L153), [:145](domain-model.md#L145), [:146](domain-model.md#L146) | The ceiling and `P-INV-2`; `event_head` and `event_seq`. | Untouched. The ceiling is the basis for `R6.2` and prescribes no empty initial value (§6.2); chain-field initialization belongs to the append protocol. |
| [domain-model.md:284](domain-model.md#L284), [:285](domain-model.md#L285), [:287](domain-model.md#L287) | Run budget and deadline mutability. | Untouched: `D01-F02-008` is out of scope. Retyping `DEC(EXTEND_BUDGET)` does not extend them. |
| [domain-model.md:686](domain-model.md#L686)–[:712](domain-model.md#L712) | `HumanDecision` fields. | No field, type or enum changes. Two profiles are now written as explicit checks rather than assumed: `grants = revokes = ∅` for a per-act decision (§5.2 step 6), and `kind: GRANT_CAPABILITY, scope: PROJECT` for a project grant (§5.3 step 1). |
| [domain-model.md:714](domain-model.md#L714)–[:727](domain-model.md#L727) | `HD-INV-1` … `HD-INV-4`. | Untouched. `HD-INV-3`'s single use is the grant itself, never consumed (`R6.5`); `HD-INV-4` continues to stale a snapshot-bound decision, including those `R13.13` identifies. |
| [domain-model.md:789](domain-model.md#L789), [:797](domain-model.md#L797), [:888](domain-model.md#L888) `G-2`, [:889](domain-model.md#L889) `G-3` | `capability_used` and event emission; the authority-citation allow-list; worker values are `CLAIM`. | Untouched. The first two are why the creation witness has four events. Every citation introduced is a `HumanDecision` or a `ContractActivationRecord`, or is absent; amendment 18 changes what a `CLAIM` may gate, not what a worker-authored value is, and the bare `Claim`'s own never-gates rule ([:113](domain-model.md#L113)) stands. |
| [evidence-model.md:63](evidence-model.md#L63)–[:86](evidence-model.md#L86) | The `EVIDENCE`/`DECISION`/`AUTHORITY` rows and the classification table. | Untouched. Amendment 18 changes only the `CLAIM` row's gating cell; amendment 16 reads the classification table rather than adding to it. `EVIDENCE` minting still requires one of five `KERNEL` capabilities ([:63](evidence-model.md#L63)), which is why no policy-evaluation or verification record is typed anywhere in this document, and why those cells stay unclosed (§6.4). |
| [evidence-model.md:127](evidence-model.md#L127), [:132](evidence-model.md#L132) | The genesis hash formula; the append table's three columns. | Untouched; see `R10.3` on `schema_version`, and amendment 21 keeps all three cells. |
| [evidence-model.md:138](evidence-model.md#L138), [:139](evidence-model.md#L139), [:143](evidence-model.md#L143), [:173](evidence-model.md#L173)–[:175](evidence-model.md#L175), [:177](evidence-model.md#L177), [:187](evidence-model.md#L187), [:190](evidence-model.md#L190) | Atomicity, observability, the external-effect exclusion, the other chain checks, replay order, the lock. | Untouched. The four-event witness preserves all of them: one atomic write per append inside one transaction, no publication before persistence, chain order authoritative. |
| [evidence-model.md:167](evidence-model.md#L167) | Reconciliation closure. | Untouched: `D01-F02-009` is out of scope. |
| [evidence-model.md:194](evidence-model.md#L194)–[:214](evidence-model.md#L214) | `observed_satisfaction`, including `W` and the `WAIVED` disjunct. | Untouched — and this is the point of amendment 15's waiver clause: the derivation keeps reading waivers exactly as frozen. |
| [transition-matrix.md:45](transition-matrix.md#L45)–[:47](transition-matrix.md#L47), [:50](transition-matrix.md#L50)–[:52](transition-matrix.md#L52) | The remaining four semantic columns: preconditions, both policy columns, `illegal_because`. | Untouched. Amendment 5 changes `required_capability` and amendment 17 changes `required_evidence`, so four of the six remain, not five as revision 02 said. No seventh column is added. |
| [transition-matrix.md:58](transition-matrix.md#L58)–[:76](transition-matrix.md#L76) | The policy verdict vocabulary and the evidence shorthand. | Untouched. `AX-14` reads `AUTO` as the policy engine's contribution and [:60](transition-matrix.md#L60)'s `CONFIRM` as already fixing `APPROVE`. No token is redefined: `CR` keeps its `MATCHED` expansion, and `DEC(K)` keeps requiring `decision_state = VALID` at the moment of the transition ([:74](transition-matrix.md#L74)), which is why [:171](transition-matrix.md#L171) stays unclosed (§6.4). |
| [transition-matrix.md:84](transition-matrix.md#L84), [:85](transition-matrix.md#L85), [:117](transition-matrix.md#L117), [:265](transition-matrix.md#L265) | Creation, first import, first authoring. | No cell is amended. `AX-17` supplies creation's witness and authority; amendments 10–14 supply the import/authoring grant. |
| [transition-matrix.md:86](transition-matrix.md#L86)–[:97](transition-matrix.md#L97), [:119](transition-matrix.md#L119)–[:142](transition-matrix.md#L142), [:208](transition-matrix.md#L208), [:336](transition-matrix.md#L336) | The eighteen `HUMAN`-class rows. | No cell is amended. Fifteen are authorized by the decision their own verdict names; [:84](transition-matrix.md#L84) and [:97](transition-matrix.md#L97) need the chosen `APPROVE` (`R3.6`), which for [:97](transition-matrix.md#L97) adds a snapshot its evidence cell does not name (`R3.7`). Revision 01's claim that each row already names its decision is withdrawn. |
| [transition-matrix.md:108](transition-matrix.md#L108)–[:113](transition-matrix.md#L113), [:435](transition-matrix.md#L435) | The startup exception; no dispatch during `DRAFT`/`PLANNING`. | Untouched and not widened. No authority form adds a row to `PLANNING` or permits a dispatch there. |
| [transition-matrix.md:394](transition-matrix.md#L394)–[:397](transition-matrix.md#L397), [:399](transition-matrix.md#L399)–[:401](transition-matrix.md#L401) | The rest of §7.5 and its prose, including terminality. | Untouched, and now genuinely so: `AX-19`'s grant ends by [:396](transition-matrix.md#L396) and takes no `VALID → CONSUMED`, so [:394](transition-matrix.md#L394)'s discharge predicate and [:401](transition-matrix.md#L401)'s terminal states need no change (`R6.5`). Only [:393](transition-matrix.md#L393)'s evidence cell is amended; [:399](transition-matrix.md#L399) supports `AX-15`'s `AUTO`, not the holding. |
| [transition-matrix.md:485](transition-matrix.md#L485) | Creation by a non-human is `NONE_GRANTABLE`. | Untouched, and cited in §6.2: it connects human origination of a project with its ceiling. |
| `design/schema/**`, [roadmap_adapter.md](roadmap_adapter.md), [worker_provider.md](worker_provider.md) | Frozen schemas and adapter interfaces. | No JSON field or enum is added. The adapter's import requirement ([roadmap_adapter.md:56](roadmap_adapter.md#L56), [:57](roadmap_adapter.md#L57)) is satisfied by amendments 10–14 without an interface change, and its secret resolution ([:78](roadmap_adapter.md#L78), [:90](roadmap_adapter.md#L90)) is attributed by `AX-16`'s `on_behalf_of` rather than by requiring a `HUMAN` actor on a kernel-mediated event. |

---

## 4. Chosen and derived

Convention: every rule in §2 carries a `basis` cell. **Derived** means the rule follows
from frozen text cited in that same cell. **Chosen** means it does not — the frozen text is
silent, or says something the rule replaces. **Conditional** means it follows from frozen
text *given* a choice made elsewhere in this document, and is marked as such rather than as
derived. A rule with two marks says which half is which.

This section makes no claim about the set as a whole; each label stands or falls on its own
cell. Revision 01's assurance that no choice was presented as a derivation is deleted and is
not replaced by an equivalent assurance. Labels corrected in revision 02 are below, followed
by the labels this revision corrects.

| rule | revision 01 label | label here | what changed |
|---|---|---|---|
| `R1.3` | derived | derived, scoped to the baseline | Cites the decisive rules ([evidence-model.md:95](evidence-model.md#L95), [authority-matrix.md:14](authority-matrix.md#L14)) and says it describes the baseline, which amendments 10–11 change. |
| `R2.1` | chosen in §2, derived in §4 | chosen | The §4 relabelling is gone; a field note following from a proposed case split is a consequence of a choice. |
| `R3.3` | chosen / derived | chosen / derived, with the `AX-15` exception named | "Never held, in any set" is withdrawn in favour of per-act possession. |
| `R3.4` | derived | derived, with [:60](transition-matrix.md#L60) added | `CONFIRM` already fixes `APPROVE`; and the rule reaches only rows that exist. |
| `R3.9` | chosen except "forced" for creation | chosen in whole | The forced half is withdrawn: nothing in frozen text forces an empty or unavailable initial ceiling. |
| `R3.10` | derived | chosen, with an explicit predicate | The empty-delta profile is now §5.2 step 6, not an inference from classification. |
| `R3.11` | derived | chosen | Actor attribution is a choice; it now uses `on_behalf_of` instead of asserting actor equality. |
| `R5.2` | derived | derived, widened to `revokes` | Empty `grants` alone did not exclude an `AUTHORITY` delta ([evidence-model.md:84](evidence-model.md#L84)). |
| `R6.3` | chosen | chosen / derived | The `KERNEL`/`NEVER` exclusion is independently required, not an optional mirror of §5. |
| `R6.4` | derived | conditional | It depends on amendment 6's `AX-4` narrowing, which revision 01 did not make. |
| `R6.5` | derived | derived, on a different basis | The `AX-20` lifecycle it relied on is withdrawn; the rule is now that a grant decision is never consumed, which [transition-matrix.md:394](transition-matrix.md#L394), [:396](transition-matrix.md#L396) and [authority-matrix.md:263](authority-matrix.md#L263) do supply. |
| `R7.2` | derived | chosen | Restricting the allow-list's reach to evidence citations changes its domain. |
| `R7.3` | derived | derived, and rewritten | The universal no-discharge rule was false; the waiver route is preserved and the `AX-9` attribution withdrawn. |
| `R8.3` | derived | chosen | An envelope exemption to the frozen `EVIDENCE` test is a choice, justified by the consuming row. |
| `R10.3` | derived | derived / chosen, split | The domain-vs-storage semantics are derived with [domain-model.md:134](domain-model.md#L134) added; binding either to a named implementation constant is a separate, chosen convention. |
| `R11.1` | chosen | chosen / derived, split | The branch is new; the value zero is forced. |

Labels this revision corrects, per `DESIGN-04-024`: `R13.5` split into a derived ceiling
bound and a chosen mode gate; `R13.10` conditional, not derived; `R13.11` chosen, being a
selection between two contradictory frozen obligations; `R13.14` and `R13.15` conditional
on the chosen creation witness, noting that [evidence-model.md:178](evidence-model.md#L178)
orders `required_evidence` and not `authority_ref`; `R13.12` narrowed to the project-subject
profiles it establishes; `R13.19` restated as the asserted-content boundary. `R13.17` is
withdrawn (§6.3), and §2.21 no longer claims its representations are forced.

Rules here: `R13.1`–`R13.20` less the withdrawn `R13.17`, plus `R13.21` and `R13.22`.
Chosen: `R13.2`, `R13.3`, `R13.6`, `R13.8`, `R13.9`, `R13.11`, `R13.19`, `R13.21`.
Conditional: `R13.10`, `R13.14`, `R13.15`. Derived: `R13.1`, `R13.4` (possession half),
`R13.7`, `R13.12`, `R13.13`, `R13.16`, `R13.18`, `R13.20`, `R13.22`. Split: `R13.5`.

---

## 5. What `DESIGN-03` must change once this freezes

`DESIGN-03` revision 02 specifies **direct exercise** for five project-holder capabilities
and amends [evidence-model.md:176](evidence-model.md#L176) itself. Amendments 1–5 and 13
generalize that mechanism and carry the enforcement-point changes it also needs. The two
documents cannot both freeze as written. Claims below are limited to what the amendments in
§2 deliver.

| `DESIGN-03` location | required change |
|---|---|
| `PP-1`, `PP-2` — the missing non-delegated path, and what is cited for `required_capability`. | Restate both as references to authority-matrix §5.2 and the amended [evidence-model.md:176](evidence-model.md#L176), [authority-matrix.md:12](authority-matrix.md#L12), [:292](authority-matrix.md#L292) and [transition-matrix.md:49](transition-matrix.md#L49); drop the specification claims. `PP-1` cites three rows where the inventory has eighteen, and the procedure binds only the seven capabilities with rows (§6.1), so the four governance writes still need **transition rows** — which is what `DESIGN-03` should keep claiming. |
| `PP-3` — `DECISION` class; disposition `-009`'s "only `:176` is amended". | Re-verify that disposition: this document amends twenty-three locations, including [evidence-model.md:62](evidence-model.md#L62), [:95](evidence-model.md#L95), [:178](evidence-model.md#L178), [:282](evidence-model.md#L282), [domain-model.md:410](domain-model.md#L410) and six authority-matrix lines. `PP-3`'s empty-delta premise must become an explicit predicate, as §5.2 step 6 now is. |
| `PP-4`, `PP-4a`, `PP-5` — the ceiling exemption, the out-of-scope class, and what bounds direct exercise. | Delete the mechanism and keep only the payload predicates and the `evidence_shown` content requirement. `AX-13` states the exemption generally and `R3.9` marks it chosen in whole, so `PP-4`'s forced/chosen split goes. `PP-4a`'s open-gap entry for `project.abandon` and `stage.abandon` is closed by amendments 3–5, 12 and 13 and should point to §5.2; its other six capabilities remain open and should point to §6.4. |
| `PP-6`, `PP-7` — no self-authorization; one decision, one field, one write. | Adopt `AX-16` or contest `R3.11` on the record: the performing actor may be `RUNTIME` with `on_behalf_of`, which `PP-6` treats as an integrity violation. This is the one substantive disagreement left between the documents. `PP-7` is consistent with §5.2 and, now that `AX-20` is withdrawn, needs no carve-out for a standing grant beyond `AX-19`'s no-consumption rule. |
| `PP-8` — "This amendment adds no decision requirement to it." | Settled against `PP-8` by `DESIGN-04-FINDINGS-01` §5 and by `AX-14`: `AUTO` states the policy engine's contribution and does not discharge [authority-matrix.md:51](authority-matrix.md#L51). Adopt the decision requirement and `AX-17`'s four-event witness; the kind `APPROVE` keeps its chosen label. |
| §2.1, §2.2, §3 — ten-step admissibility, the decision profile, `project.ceiling.set`. | Rewrite §2.1 as a delta over §5.2, whose steps 1, 3, 4, 5, 7 and 9 it restates, keeping the `evidence_shown` content requirement, the payload predicates and the atomicity rule. §2.2 is unaffected: no field, enum or entity changes here. §3 is unaffected and is no longer a prerequisite of the first project grant (§6.2), though it remains the only specified way to change a ceiling after creation. |
| §6 — the initial `Project` state, `event_seq = 1`. | Superseded by `AX-17` and amendments 19–21: the witness ends at `event_seq = 3`. Cite the amended [evidence-model.md:128](evidence-model.md#L128), [:135](evidence-model.md#L135), [:136](evidence-model.md#L136); if `DESIGN-03` keeps an empty initial ceiling, state it as its own choice (§6.2). |

Ordering: `DESIGN-04` should freeze first, since `DESIGN-03` stands on an authority path
that is not baseline text until these amendments land. Per the review method, the reviewer
of a revised `DESIGN-03` is the reviewer that raised `DESIGN-03-FINDINGS-01`, and this
document's author does not review it.

---

## 6. Delimitations

### 6.1 The ten `HUMAN` capabilities with no legal row

§5.2 supplies the authority form for all seventeen `HUMAN`-class capabilities. Its
procedure binds only the seven that a legal row names as `required_capability`, because
steps 2, 5 and 8 read that row. Revision 01 claimed the whole class; that is withdrawn.
Four of the other ten close in `DESIGN-03`; six close nowhere yet.

| capability | register row | where its exercise closes |
|---|---|---|
| `project.mode.set` | [authority-matrix.md:59](authority-matrix.md#L59) | `DESIGN-03` §5: a transition row per governance-field write. `P-INV-1` ([domain-model.md:152](domain-model.md#L152)) already requires `DEC(SET_MODE)`. |
| `policy.set`, `budget.grant` | [authority-matrix.md:63](authority-matrix.md#L63), [:65](authority-matrix.md#L65) | `DESIGN-03` §5, each with its new decision kind. |
| `budget.extend` | [authority-matrix.md:66](authority-matrix.md#L66) | `DESIGN-03` §5 for the project holder; for a run holder the obstruction is `D01-F02-008`, out of scope here. |
| `policy.override`, `commit.publish`, `audit.redact`, `secret.read`, `net.egress.any`, `proc.exec.arbitrary` | [authority-matrix.md:64](authority-matrix.md#L64), [:134](authority-matrix.md#L134), [:146](authority-matrix.md#L146), [:110](authority-matrix.md#L110), [:109](authority-matrix.md#L109), [:107](authority-matrix.md#L107) | **Nowhere.** None is named by a legal row: publication has prose only ([transition-matrix.md:381](transition-matrix.md#L381)–[:383](transition-matrix.md#L383)), redaction names its authority at [evidence-model.md:270](evidence-model.md#L270), and the last three are exercised inside execution rather than at a transition, so §5.2's procedure cannot bind them. `AX-16` supplies the attribution for a kernel-mediated resolution ([roadmap_adapter.md:78](roadmap_adapter.md#L78), [:90](roadmap_adapter.md#L90)); what is missing is a point at which the exercise decision is presented and consumed, which is `CLAUDE.md`'s `GR-17` gap. §6.4. |

`D01-F02-003` is therefore **partially closed**. The four capabilities it names —
`project.abandon`, `project.archive`, `stage.reject`, `stage.abandon` — are among the seven
with legal rows, as are `decision.record` and `finding.waive`, the two further operations it
names as stranded by the same mechanism; for those seven it is closed. The six above are
**not** closed: each has an authority form, and a form with no passing admission path
authorizes nothing. This document claims nothing further for them, here or in §0.

### 6.2 The initial `capability_ceiling`

This document **chooses** the premise that the creating human supplies a non-empty
`capability_ceiling` in the creating act, containing at least what the project will grant
at project scope. The premise is permitted, not forced: [domain-model.md:141](domain-model.md#L141)
makes the ceiling required and human-sourced without prescribing an initial value, and
[transition-matrix.md:485](transition-matrix.md#L485) connects human origination of a
project with its own ceiling. `DESIGN-03-015` already rejected a frozen derivation of an
empty ceiling. Under this premise the first project grant of `roadmap.import` or
`contract.author` needs no later setter, and `D01-F02-005`'s closure rests on amendments 1,
6–8, 10–12 and 14; revision 01's claim that the first grant necessarily depends on
`DESIGN-03`'s `project.ceiling.set` is withdrawn. A non-empty initial ceiling grants
nothing — amendment 7 keeps "bounding is not granting" verbatim (`R13.7`). If a project is
instead created with an empty ceiling, as `DESIGN-03` §6 proposes, a ceiling-setting
operation becomes a genuine prerequisite of the first project grant: a conditional
dependency of that choice, not of this correction.

### 6.3 Claims withdrawn

| claim | revision | disposition |
|---|---|---|
| An empty initial ceiling is forced, making the ceiling exemption forced for `project.create`. | 01 | **Withdrawn** (§6.2, `R3.9`). |
| The run-bound `escalation.raise` at [transition-matrix.md:128](transition-matrix.md#L128) has no authority form. | 01 | **Withdrawn.** `escalation.raise` has a `G` cell for every role ([authority-matrix.md:216](authority-matrix.md#L216)) with `ROLE_DEFAULT` admissible ([:265](authority-matrix.md#L265)), so that run's activation can carry it ([domain-model.md:392](domain-model.md#L392), [:410](domain-model.md#L410)) and amendment 1's grant branch accepts it. No finding is promoted from it. |
| `AX-20`'s standing-grant consumption lifecycle. | 02 | **Withdrawn** (`R6.5`). It invoked `VALID → CONSUMED` with no discharge, overlapped [transition-matrix.md:396](transition-matrix.md#L396), and was unreachable once [:401](transition-matrix.md#L401) makes those states terminal. The replacement needs no amendment to §7.5. |
| Policy-evaluation and chain-verification records are `CLAIM` by the runtime (`R13.17`). | 02 | **Withdrawn** in full: from amendment 16, §2.21, the inventory, §3 and §6. Those cells are unclosed (§6.4). |
| `DEC` at [transition-matrix.md:171](transition-matrix.md#L171) is satisfied by a decision "live at that resolution". | 02 | **Withdrawn.** A cited decision must be `VALID` at the consuming transition ([:74](transition-matrix.md#L74), [authority-matrix.md:289](authority-matrix.md#L289), [transition-matrix.md:522](transition-matrix.md#L522)). The row is retained as unclosed (§6.4). |
| All fourteen `DESIGN-04-FINDINGS-01` findings are closed, and all 44 inventory rows are typed. | 02 | **Withdrawn.** The review sustains nine of fourteen as closed; §0 records this revision's own dispositions, and §2.22 separates typed rows from unclosed ones. |

### 6.4 Cells and acts these amendments do not close

Carried forward as work for a later corrective record, alongside `D01-F02-007`, `-008`,
`-009` and `-010`. None is claimed closed anywhere in this document.

| unclosed item | why, and what a later record must decide |
|---|---|
| The policy-evaluation cells at [transition-matrix.md:157](transition-matrix.md#L157) and [:170](transition-matrix.md#L170) | A policy evaluation is not one of `G-1`'s five evidence entities and is not an activation, decision, escalation or an `AuditEvent` the row names, so `G-1` admits no kind for it. Revision 02 typed it `CLAIM` by the runtime; that typing is **withdrawn** — [evidence-model.md:63](evidence-model.md#L63) and [:85](evidence-model.md#L85) do not supply it. Closing these cells means either a new admissible kind or a widened `G-1`, which is outside these five findings. |
| The verification-record cells at [transition-matrix.md:161](transition-matrix.md#L161), [:167](transition-matrix.md#L167), [:174](transition-matrix.md#L174), [:175](transition-matrix.md#L175) and [:397](transition-matrix.md#L397) | Same reason. At [:161](transition-matrix.md#L161) the `ESC(OPEN)` alternative is typed and usable, which does not close the verification alternative; at [:174](transition-matrix.md#L174) the verification record is a conjunct that `DEC(OVERRIDE)` cannot replace. |
| [transition-matrix.md:171](transition-matrix.md#L171) | The cell requires the `DEC` each resolution referenced, and [:74](transition-matrix.md#L74), [authority-matrix.md:289](authority-matrix.md#L289) and [transition-matrix.md:522](transition-matrix.md#L522) require a cited decision to be `VALID` at *this* transition — while a resolution decision is `CONSUMED` by the resolution it discharged ([:394](transition-matrix.md#L394)), and `CONSUMED` is terminal ([:401](transition-matrix.md#L401)). Typing cannot close it, and revision 02's "live at that resolution" reading is withdrawn: it weakened decision currency. |
| The triggering-record cell at [transition-matrix.md:412](transition-matrix.md#L412) for comparison triggers | Where the fired trigger is a comparison over entity fields — `DEADLINE_EXCEEDED`, `REPEATED_FAILURE` ([domain-model.md:761](domain-model.md#L761), [:762](domain-model.md#L762)) — no record is persisted to cite, and a precondition cannot discharge a separately printed cell. Triggers that do name a record, such as `CAPABILITY_DENIED` ([domain-model.md:758](domain-model.md#L758)) citing the denial event, are typed. |
| `policy.override`, `commit.publish`, `audit.redact`, `secret.read`, `net.egress.any`, `proc.exec.arbitrary` | Each has an authority form and no legal row, so §5.2's procedure cannot bind it; the last three are exercised inside execution rather than at a transition (§6.1). |
| Rows for the four governance writes | `project.mode.set`, `policy.set`, `budget.grant`, `budget.extend` have an authority form and no row; that is `DESIGN-03`'s subject (§5). |
| The `C`/`D` tension in §4.1 | [authority-matrix.md:203](authority-matrix.md#L203) and [:206](authority-matrix.md#L206) give `C` cells to `HUMAN`-class capabilities that [:221](authority-matrix.md#L221) denies to every role. Pre-existing, not one of the five findings, and no amendment depends on resolving it. |
| Implementation | Nothing here is implemented. `src/` and `tests/` are untouched. |

## 7. Verification of this document

| check | result |
|---|---|
| Citation resolution | Every `file:line` was resolved against the tag with `git show design-01-frozen:design/<file> \| sed -n '<line>p'` before it was written, and all citations were re-resolved afterwards. None is out of range; none lands on a blank line. Citations into `design/review/` were resolved against the working-tree records, which are committed evidence. |
| Quoted frozen text | All twenty-three amendment targets were compared byte-for-byte against their frozen lines, including the two-line `C-INV-3` block and the repeated §5.1 insertion anchor. |
| Inventory coverage | §2.22 accounts for all 44 rows of the review's inventory and states which are typed and which remain unclosed; §2.21 types every record kind `G-1` admits and names the kinds it does not. The count of `ESC` evidence rows is twelve. |
| Exhaustive claims | `R3.5`'s `AUTO`-row claim and `R13.16`'s seven-of-seventeen claim were re-derived from the frozen matrix's `required_capability` column against the seventeen `HUMAN`-class register rows. |
| Finding coverage | Each of the twenty-three amendments names at least one `D01-F02` finding. All twenty-four `DESIGN-04` findings have a disposition in §0 with the `file:line` that closes them. Four `D01-F02` findings are closed; `D01-F02-003` is partially closed and says so in §0, §1.1, amendment 13 and §6.1. |
| Dispositions | Severity and blocking flags are reproduced as recorded. No disposition, blocking flag or review record was changed, and no file under `design/review/` was modified. |
| Frozen text | No frozen design file, schema or implementation file was edited. Revisions 01 and 02 are unchanged. No commit, tag or branch operation was performed. |
| Version terms | `SCHEMA_VERSION` appears only as the domain-model version feeding the genesis hash, with the implementation binding labelled separately (`R10.3`). `STORAGE_VERSION` and `PRAGMA user_version` appear only to say they are a different thing. |
