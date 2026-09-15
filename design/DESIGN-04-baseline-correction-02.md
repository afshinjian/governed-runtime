# DESIGN-04 — Baseline Correction (revision 02)

Revises [DESIGN-04-baseline-correction.md](DESIGN-04-baseline-correction.md) against
[DESIGN-04-FINDINGS-01.md](review/DESIGN-04-FINDINGS-01.md). Revision 01 is committed
evidence and is unchanged; this document replaces it as the amendment. Where the two
differ, this one governs.

| Property | Statement |
|---|---|
| Baseline | `design-01-frozen`, peeled commit `8fd51193da0f29efb60ddf906fc845bb0dcbaeb3`. Every `file:line` citation resolves in that tag and was checked with `git show design-01-frozen:design/<file> \| sed -n '<line>p'`. |
| Kind | Proposal. No frozen file is edited, no schema or implementation is changed, nothing here is in effect. `design-01-frozen` remains authoritative until these edits land in the frozen files. |
| Corrects | The same five findings as revision 01: `D01-F02-001`, `-002` (retained half only), `-003`, `-004`, `-005`. |
| Changes in this revision | Twenty-one amendments, up from twelve. Nine are new: the four enforcement points the human path had to but did not amend (`AX-1`, §6 transition, `required_capability`, `C-INV-3`), the three grant-algebra rules a project grant had to but did not amend (`AX-4`, `AX-8`, `AX-11`), the decision-recording row, and the `CLAIM` gating rule. Whole-cell evidence typing is replaced by per-citation and per-alternative typing; the waiver route is preserved; the creation account has four events; §4 no longer asserts that no choice is presented as a derivation. |
| Rule ids | Inherited from revision 01 (`R1.1` … `R12.1`) so the review's §2 audit stays traceable, with `R13.1` onward for new rules. Every label the review corrected is corrected here. |
| Boundary | `design/review/` is immutable evidence and is read-only here. `src/` and `tests/` are untouched. No commit, tag, or other Git mutation. |

## 0. Disposition of `DESIGN-04-FINDINGS-01`

Judged against the frozen text each finding cites, not against whether the reviewer's
wording was engaged. "Closes it" names the amendment in §2 and the frozen `file:line` it
changes.

| id | severity | disposition | what closes it |
|---|---|---|---|
| `DESIGN-04-001` | MAJOR | **CLOSED** | Amendments 3, 4, 5: [authority-matrix.md:12](authority-matrix.md#L12) (`AX-1` gains the four authority forms), [authority-matrix.md:292](authority-matrix.md#L292) (§6's transition point names them), [transition-matrix.md:49](transition-matrix.md#L49) (the column reads "held … by any authority form"). `AX-12` no longer says "never held": a `HUMAN`-class capability is **held for one act** by its live decision. `AX-15` is stated as a named exception to `AX-1`, not as an instance of `AX-7`. |
| `DESIGN-04-002` | MAJOR | **CLOSED** | Amendments 6, 7, 8: [authority-matrix.md:15](authority-matrix.md#L15) (`AX-4` intersection stated per form), [authority-matrix.md:22](authority-matrix.md#L22) (`AX-11`'s final clause admits the granting decision as the basis citation), [domain-model.md:380](domain-model.md#L380)–[:381](domain-model.md#L381) (`C-INV-3` scoped to a run's grants). |
| `DESIGN-04-003` | MAJOR | **CLOSED** | Amendment 9: [authority-matrix.md:19](authority-matrix.md#L19) (`AX-8` gains the project-scope and per-act destination, the denial `AuditEvent` already required at [authority-matrix.md:293](authority-matrix.md#L293)). The out-of-ceiling failure case is worked in `R13.3`. |
| `DESIGN-04-004` | MAJOR | **CLOSED** | Amendment 13, `AX-17`: the four-event witness (0 snapshot, 1 decision recorded, 2 project created, 3 decision consumed), one transaction, head at 3. Its transactional basis cites `VERIFY-01`'s `D01-F02-006` refutation ([VERIFY-01:98](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L98), [:104](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L104)–[:109](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L109)) and not the refuted half of `D01-F02-002`. |
| `DESIGN-04-005` | MAJOR | **CLOSED** | Amendments 15, 16, 17: typing is per citation and per alternative, never per cell. §2.22 verifies it against all 44 rows of the review's inventory, including every `M` row. |
| `DESIGN-04-006` | MAJOR | **CLOSED** | Amendment 15: `G-1`'s prerequisite clause preserves the waiver route — a `HumanDecision{kind ∈ {WAIVE, ACCEPT_RISK}}` produces the `WAIVED` outcome that [evidence-model.md:204](evidence-model.md#L204) and [:210](evidence-model.md#L210) read, with [domain-model.md:246](domain-model.md#L246). The `AX-9` attribution is withdrawn; `R7.3` is relabelled and rewritten. |
| `DESIGN-04-007` | MAJOR | **CLOSED** | Amendment 18: [evidence-model.md:62](evidence-model.md#L62) is amended so `CLAIM` never gates on its **content** while its existence, provenance and status may be a named prerequisite. |
| `DESIGN-04-008` | MAJOR | **CLOSED** | Amendment 16 plus §2.21's total mapping: every record kind named anywhere in a `required_evidence` cell gets a class, including the revocation record at [transition-matrix.md:191](transition-matrix.md#L191), the policy and verification records, the `InvocationRequest` at [:305](transition-matrix.md#L305), and the cell elements that name no record at all. One disclosed choice is recorded in `R13.6`. |
| `DESIGN-04-009` | MAJOR | **CLOSED** | §5.2 step 2 narrows the procedure to the seven `HUMAN` capabilities that have legal rows; §6.1 states where each of the other ten closes. `AX-16` replaces the actor-equality rule with `on_behalf_of`, which is what reaches [roadmap_adapter.md:90](roadmap_adapter.md#L90). |
| `DESIGN-04-010` | MAJOR | **CLOSED** | Amendment 12: [transition-matrix.md:393](transition-matrix.md#L393)'s `required_evidence` cell becomes conditional on `snapshot_bound`, matching [domain-model.md:703](domain-model.md#L703) and [:876](domain-model.md#L876). This is load-bearing for `D01-F02-003` as well: a project-subject `ABANDON` decision is not snapshot-bound either. |
| `DESIGN-04-011` | MINOR | **CLOSED** | §4: the assurance sentence is deleted, and every label the review's §2 corrected is corrected — `R1.3`, `R2.1`, `R3.3`, `R3.4`, `R3.9`, `R3.10`, `R3.11`, `R5.2`, `R6.3`, `R6.4`, `R6.5`, `R7.2`, `R7.3`, `R8.3`, `R10.3`, `R11.1`. |
| `DESIGN-04-012` | MINOR | **CLOSED** | Amendment 2: the biconditional is guarded — "absent exactly when `capability_used` is present and is …"; an event with no `capability_used` is unconstrained. |
| `DESIGN-04-013` | MINOR | **CLOSED** | Amendment 21: the third `failure handling` cell is restored, matching [evidence-model.md:132](evidence-model.md#L132). |
| `DESIGN-04-014` | MINOR | **CLOSED** | §6.2: the non-empty initial ceiling is stated as this document's chosen premise on [domain-model.md:141](domain-model.md#L141) and [transition-matrix.md:485](transition-matrix.md#L485); the claim that the first grant needs a later setter is withdrawn, and `D01-F02-005`'s closure rests on amendments 6–8, 10, 11, 12 and 14 instead. |

Two revision-01 claims the review refuted are withdrawn outright, not renegotiated: the
assertion that an empty initial ceiling is forced (§6.2), and the assertion that the
run-bound `escalation.raise` at [transition-matrix.md:128](transition-matrix.md#L128) has
no authority form (§6.3). The review's counterexamples are accepted as correct.

---

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

### 1.2 `D01-F02-002` — what is retained, and what is not asserted

`VERIFY-01` refuted the referential-integrity half of this finding and this document does
not reassert it.

| half of the finding | status here |
|---|---|
| The append algorithm reads `event_seq` and `event_head` that have no prior event in a new project ([evidence-model.md:135](evidence-model.md#L135), [:136](evidence-model.md#L136), [domain-model.md:145](domain-model.md#L145), [:146](domain-model.md#L146)), and the genesis rule ([evidence-model.md:127](evidence-model.md#L127)) specifies event zero without specifying installation of the project/head state the later steps read. | **Retained and corrected** by amendments 19–21. This is the residue narrowed at [VERIFY-01:59](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L59). |
| Satisfying `SNAP` before the creation event necessarily exposes a committed reference to a project that does not yet exist. | **Not asserted, and not used as a basis anywhere.** Where this document needs transaction-local ordering it cites the `D01-F02-006` refutation instead ([VERIFY-01:98](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L98), [:104](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L104)–[:109](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L109)), with the project/snapshot instance at [VERIFY-01:50](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L50)–[:55](review/DESIGN-01-FINDINGS-02-VERIFY-01.md#L55). |

### 1.3 `D01-F02-006` — refuted, no amendment

`VERIFY-01` records it **REFUTED**. No amendment addresses it.
[domain-model.md:273](domain-model.md#L273), [:390](domain-model.md#L390),
[:865](domain-model.md#L865) and [transition-matrix.md:189](transition-matrix.md#L189)'s
`ACT` precondition are untouched. Its refutation is used here only as the transactional
basis the review asked for.

### 1.4 Out of scope: `-007`, `-008`, `-009`, `-010`

All four are **CONFIRMED** by `VERIFY-01`. None is addressed. Each governs an operation
unreachable until after a project is provisioned, a stage materialized, a contract
activated and a run executed, so none blocks provisioning and none is repaired by these
corrections. Amendments 15–18 do change the **admissibility** of records cited by some of
their rows ([transition-matrix.md:269](transition-matrix.md#L269),
[:172](transition-matrix.md#L172), [:206](transition-matrix.md#L206),
[:358](transition-matrix.md#L358)); the underlying defects are untouched, and §2.22 marks
each such row.

| id | blocking | what it governs | why it does not block provisioning | when it must be closed |
|---|---|---|---|---|
| `D01-F02-007` | true | Predecessor status `SUPERSEDED` ([transition-matrix.md:269](transition-matrix.md#L269), [:266](transition-matrix.md#L266), [:273](transition-matrix.md#L273)). | Needs an `ACTIVE` contract and a second contract for the same stage. `VERIFY-01` records a conforming replacement route (revoke, then activate the successor); only the `SUPERSEDED` status is unreachable. | Before the first contract replacement. |
| `D01-F02-008` | true | Clearing a budget suspension or reworking an exhausted run ([transition-matrix.md:172](transition-matrix.md#L172), [:206](transition-matrix.md#L206), [domain-model.md:284](domain-model.md#L284), [:287](domain-model.md#L287)). | Needs a run that consumed its immutable allocation. No worker may be dispatched while `DRAFT` or `PLANNING` ([transition-matrix.md:435](transition-matrix.md#L435)). | Before the first exhausted dimension or passed deadline. |
| `D01-F02-009` | false | Dispatch or apply with a non-terminal prior-epoch operation ([evidence-model.md:167](evidence-model.md#L167), [transition-matrix.md:359](transition-matrix.md#L359)). | Needs a controller restart with operations from an earlier epoch; provisioning dispatches nothing. | Before the first restart leaving a live operation. |
| `D01-F02-010` | true | `CR with verification = DIVERGED` against the `CR` expansion ([transition-matrix.md:358](transition-matrix.md#L358), [:73](transition-matrix.md#L73)). | Needs an intent that reached `APPLYING`; provisioning applies no commit. | Before the first divergent apply is reconciled. |

---

## 2. Amendments

Twenty-one amendments in three groups: the authority forms (1–14), evidence typing
(15–18), and genesis (19–21). Each closes at least one of the five findings.

### Amendment 1 — the authority-binding verification check

**Target** [evidence-model.md:176](evidence-model.md#L176) (§3.3 Verification).

**Current frozen text**

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

**Target** [domain-model.md:790](domain-model.md#L790) (§9.C `AuditEvent`).

**Current frozen text**

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

**Target** [authority-matrix.md:12](authority-matrix.md#L12) (§0 Axioms).

**Current frozen text**

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

**Target** [authority-matrix.md:292](authority-matrix.md#L292) (§6 Enforcement points).

**Current frozen text**

```
| transition | `required_capability` from `transition-matrix.md` held at the moment of transition, plus `required_evidence` present |
```

**Proposed text**

```
| transition | `required_capability` from `transition-matrix.md` held at the moment of transition by one of `AX-1`'s forms — a run grant, a project grant, the kernel's own holding, or for this one act by a live decision under §5.2 — plus `required_evidence` present |
```

**Closes** `D01-F02-001` and `D01-F02-003`. Fixes `DESIGN-04-001`.

| id | rule | basis |
|---|---|---|
| `R13.3` | Per-act exercise is a way of holding a capability at the transition, not a way of dispensing with possession. | **chosen** — this is the substantive repair of revision 01's "never held" framing, which contradicted this enforcement point and [transition-matrix.md:49](transition-matrix.md#L49). Possession begins when the authorizing decision becomes live and ends at `VALID → CONSUMED` ([transition-matrix.md:394](transition-matrix.md#L394)). §6's decision-freshness point ([authority-matrix.md:289](authority-matrix.md#L289)) already enforces the liveness this relies on and is untouched. |

### Amendment 5 — the `required_capability` column

**Target** [transition-matrix.md:49](transition-matrix.md#L49) (§1 Column semantics).

**Current frozen text**

```
| `required_capability` | the single `CapabilityId` the actor must hold; absent ⇒ DENY |
```

**Proposed text**

```
| `required_capability` | the single `CapabilityId` the actor must hold at the transition, by any authority form in `AX-1` (authority-matrix §5, §5.2, §5.3, `AX-7`); absent ⇒ DENY |
```

**Closes** `D01-F02-001` and `D01-F02-003`. Fixes `DESIGN-04-001`.

| id | rule | basis |
|---|---|---|
| `R13.4` | The column's meaning is possession by an admissible form, and the set of forms is the thing amended. | **derived** that the column requires possession — its own frozen wording; **chosen** that per-act possession counts, which is `R13.3`. `AX-2` and `G-4` are untouched: exactly one capability per operation. |

### Amendment 6 — `AX-4`

**Target** [authority-matrix.md:15](authority-matrix.md#L15) (§0 Axioms).

**Current frozen text**

```
| `AX-4` | `granted ⊆ capability_request ∩ role_default ∩ mode_allowed ∩ project.capability_ceiling`. Intersection, never union. |
```

**Proposed text**

```
| `AX-4` | For a **run grant**: `granted ⊆ capability_request ∩ role_default ∩ mode_allowed ∩ project.capability_ceiling`. For a **project grant** (§5.3): `granted ⊆ decision.grants ∩ mode_allowed ∩ project.capability_ceiling`, there being no `capability_request` and no `worker_role` outside a `WorkerInvocation` (§4.1). A **per-act exercise** (§5.2) produces no `granted` set and is bounded by §5.2 instead. Intersection, never union. |
```

**Closes** `D01-F02-005`. Fixes `DESIGN-04-002`.

| id | rule | basis |
|---|---|---|
| `R6.4` | §4.1's role table does not apply to a project grant. | **conditional on the project-grant form** — [authority-matrix.md:190](authority-matrix.md#L190) heads that table "per `WorkerInvocation`", which supports not applying it to a non-invocation grant but does not narrow this axiom's unqualified wording. That narrowing is what this amendment does, which is why revision 01's additive heading was insufficient. |
| `R13.5` | The ceiling and the mode gate still bound a project grant. | **derived** — [domain-model.md:141](domain-model.md#L141) makes the ceiling the upper bound on all grants and `P-INV-2` says no grant anywhere may exceed it ([domain-model.md:153](domain-model.md#L153)); the mode gate is retained by choice (`R6.3`). |

### Amendment 7 — `AX-11`

**Target** [authority-matrix.md:22](authority-matrix.md#L22) (§0 Axioms).

**Current frozen text**

```
| `AX-11` | **Bounding is not granting.** `project.capability_ceiling`, the §3 mode gate, `capability_request`, and the §4.1 role table only narrow the candidate set. A capability is granted only when a principal named in its §2 `grantable by` column produced an admissible grant record for it (§5.1), and that record is cited in `ContractActivationRecord.capability_grant_basis`. |
```

**Proposed text**

```
| `AX-11` | **Bounding is not granting.** `project.capability_ceiling`, the §3 mode gate, `capability_request`, and the §4.1 role table only narrow the candidate set. A capability is granted only when a principal named in its §2 `grantable by` column produced an admissible grant record for it (§5.1), and that record is cited by the grant it produced: in `ContractActivationRecord.capability_grant_basis` for a run grant, and by `AuditEvent.authority_ref` naming the granting `HumanDecision` for a project grant (§5.3, `AX-19`). A per-act exercise is not a grant and produces no basis entry (§5.2). |
```

**Closes** `D01-F02-005`. Fixes `DESIGN-04-002`.

| id | rule | basis |
|---|---|---|
| `R13.6` | A project grant's basis citation is the granting decision itself, cited at the point of exercise. | **chosen** — the frozen final clause admits exactly one destination, an activation's `capability_grant_basis`, which a pre-activation grant cannot have. `G-2` already admits a `HumanDecision` as an authority citation ([domain-model.md:888](domain-model.md#L888)), so no new entity or citation type is needed. |
| `R13.7` | "Bounding is not granting" is unchanged, including for the initial ceiling. | **derived** — the amendment retains the first two sentences verbatim. A non-empty initial ceiling therefore grants nothing (§6.2). |

### Amendment 8 — `C-INV-3`

**Target** [domain-model.md:380](domain-model.md#L380)–[:381](domain-model.md#L381) (§5 `StageContract` invariants), one two-line invariant.

**Current frozen text**

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

**Target** [authority-matrix.md:19](authority-matrix.md#L19) (§0 Axioms).

**Current frozen text**

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
| `R13.10` | Worked failure case: a decision whose `grants` contains one capability outside `project.capability_ceiling`. | **derived** given amendment 6 — step 2 of §5.3 drops it with `NOT_IN_CEILING`, and under this amendment that reason and capability appear in the denial `AuditEvent`. Before this amendment the reason had nowhere conforming to go. |

### Amendment 10 — `AX-3`

**Target** [authority-matrix.md:14](authority-matrix.md#L14) (§0 Axioms).

**Current frozen text**

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

**Target** [evidence-model.md:95](evidence-model.md#L95) (§2.2 Promotion rules).

**Current frozen text**

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

**Target** [transition-matrix.md:393](transition-matrix.md#L393) (§7.5 `HumanDecision.decision_state`).

**Current frozen text**

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
| `R13.11` | The row's evidence cell is conditional on `snapshot_bound`, as its own preconditions column and the field rules already are. | **derived** — `subject_snapshot_id` is required iff `snapshot_bound` ([domain-model.md:703](domain-model.md#L703)) and present iff `snapshot_bound` ([domain-model.md:876](domain-model.md#L876)); the frozen cell demands it unconditionally, so a non-snapshot-bound decision could not be recorded without violating one rule or the other. |
| `R13.12` | This is load-bearing for two findings, not only for project grants. | **derived** — `GRANT_CAPABILITY` over a `PROJECT` subject is not snapshot-bound, and neither is `ABANDON` over a `PROJECT` or `CAPABILITY` subject ([domain-model.md:702](domain-model.md#L702)). The second is the decision the `project.abandon` rows require ([transition-matrix.md:86](transition-matrix.md#L86), [:89](transition-matrix.md#L89), [:91](transition-matrix.md#L91), [:94](transition-matrix.md#L94)), which `D01-F02-003` names. |
| `R13.13` | `APPROVE`, `WAIVE`, `ACCEPT_RISK`, `OVERRIDE` and `REJECT` decisions remain snapshot-bound and keep the cell. | **derived** — [domain-model.md:702](domain-model.md#L702)'s first disjunct and kind list; `HD-INV-4` ([domain-model.md:719](domain-model.md#L719)) is untouched. |

### Amendment 13 — per-act exercise of a `HUMAN`-class capability (new authority-matrix §5.2)

**Target** insertion into `authority-matrix.md` immediately after
[authority-matrix.md:277](authority-matrix.md#L277), the last line of §5.1.

**Current frozen text at the anchor**

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
| `AX-15` | `decision.record` is held by an authenticated `HUMAN_PRINCIPAL` without a decision of its own, because the human act *is* the decision — which is why recording is `AUTO` in both modes (transition-matrix §7.5). It is the single named exception in `AX-1`, not an instance of `AX-7`, and no other capability is self-held by a principal. |
| `AX-16` | The event's `actor` is the actor that performed the act. Where that actor is not the deciding principal — the controller writing a project record, the kernel resolving a secret for an adapter — it carries `on_behalf_of` naming the deciding principal, at delegation depth ≤ 2. A `WORKER` actor never performs a `HUMAN`-class exercise. The kernel self-grants nothing: the authority is the human's decision, named by `authority_ref`. |
| `AX-17` | `project.create` is exercised inside the store transaction that installs the project, over an allocated identifier. One conforming witness, unrelated defects held aside: `seq = 0` the `RealitySnapshot` under `snapshot.take`; `seq = 1` the creation approval reaching `VALID` under `decision.record`, citing event 0 as its `subject_snapshot_id`; `seq = 2` `∅ → DRAFT` under `project.create`, citing the decision as `authority_ref` and event 0 as its `SNAP`; `seq = 3` `VALID → CONSUMED` under `audit.append`, citing event 2. At commit `Project.event_seq = 3` and `event_head` is event 3's hash. Four transitions, four events, one transaction, no event merging two capability identities. |
```

**Closes** `D01-F02-003` in full and the `project.create` half of `D01-F02-001`. Fixes
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
| `R13.14` | Four events are required, not two. | **derived** — every transition emits an event before the new state is observable ([domain-model.md:797](domain-model.md#L797)); each names exactly one capability ([domain-model.md:789](domain-model.md#L789), [:890](domain-model.md#L890)), so recording under `decision.record` cannot merge with creation under `project.create`; the decision is recorded by [transition-matrix.md:393](transition-matrix.md#L393) and consumed by [:394](transition-matrix.md#L394); chain order is authoritative for replay ([evidence-model.md:187](evidence-model.md#L187)). Revision 01's snapshot-0/creation-1 account is withdrawn. |
| `R13.15` | Each event's cited records have lower `seq`. | **derived** — event 1 cites event 0's snapshot; event 2 cites event 0's snapshot and the decision recorded at 1; event 3 cites event 2. Amendment 16 keeps the strictly-lower-`seq` requirement of [evidence-model.md:178](evidence-model.md#L178). |
| `R13.16` | The procedure covers seven capabilities, not seventeen. | **derived** — steps 2, 5 and 8 read the row; ten `HUMAN` capabilities are named by no legal row (§6.1). Revision 01 claimed the whole class. |

### Amendment 14 — project-scope grants (new authority-matrix §5.3)

**Target** insertion into `authority-matrix.md` immediately after amendment 13's §5.2,
anchored at [authority-matrix.md:277](authority-matrix.md#L277).

**Current frozen text at the anchor**

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
| `AX-19` | An event exercising a project grant sets `authority_ref` to the granting `decision_id`, live at `recorded_at` (evidence-model §3.3). That citation is the grant's basis record under `AX-11`. `G-2` is unchanged: a `HumanDecision` is already an admissible authority citation. |
| `AX-20` | A `GRANT_CAPABILITY` decision is a standing grant, not a discharge of one transition. Its nonce is spent when the grant ends, not when the grant is exercised: the grant ends at `expires_at`, at the `scope` boundary, or when `decision_state` leaves `VALID` (§1.1), and the `VALID → CONSUMED` transition is taken at that point with the ending recorded. `HD-INV-3` is preserved — one consumption, and a project-scope grant is never replayed into a run, since `AX-18` keeps it out of every run set. |
| `AX-21` | `POLICY_ENGINE` is not an admissible grantor of a project grant. An `AUTONOMOUS` project's first import and first contract still require a live human grant, exactly as `roadmap.writeback` does in either mode (§5.1). |
```

**Closes** `D01-F02-005`. Fixes the `R6.5` half of `DESIGN-04-011`.

| id | rule | basis |
|---|---|---|
| `R6.1` | The first import and first contract authoring can be authorized by a project grant with no activation. | **derived** that both are `ORD` with `HUMAN_PRINCIPAL` as a named grantor — [authority-matrix.md:74](authority-matrix.md#L74), [:86](authority-matrix.md#L86); **chosen** that a project grant authorizes them, with amendments 6–8 supplying the realization change. |
| `R6.2` | The grant is bounded by `project.capability_ceiling`. | **derived** — [domain-model.md:141](domain-model.md#L141), [:153](domain-model.md#L153) bound every grant in the project by the ceiling. |
| `R6.3` | The §3 mode gate is retained; the `KERNEL`/`NEVER` exclusion is not optional. | **chosen** for adopting the mode gate in a new resolution, mirroring §5 step 3 ([authority-matrix.md:243](authority-matrix.md#L243)); **derived** for the `KERNEL`/`NEVER` exclusion, which [authority-matrix.md:17](authority-matrix.md#L17) and [:18](authority-matrix.md#L18) require independently of this step. |
| `R6.4` | §4.1 is not applied. | **conditional** — see amendment 6, which performs the `AX-4` narrowing this depends on. |
| `R6.5` | A `GRANT_CAPABILITY` decision survives the exercise of its grant, and spends its nonce when the grant ends. | **chosen** — [transition-matrix.md:394](transition-matrix.md#L394) gives a consumption trigger for a decision "recorded for" a transition but does not place a standing grant outside it, and [authority-matrix.md:41](authority-matrix.md#L41) says when a `HUMAN_DECISION` grant expires, not how its nonce is spent. `AX-20` therefore chooses the lifecycle and states the consumption boundary explicitly, which is what `HD-INV-3` ([domain-model.md:718](domain-model.md#L718)) requires of it. Per-act decisions under §5.2 are unaffected and are consumed by the transition they discharge. |
| `R6.6` | `POLICY_ENGINE` cannot grant at project scope. | **chosen** — a persisted policy evaluation ([authority-matrix.md:264](authority-matrix.md#L264)) is not an entity `G-2` admits as an authority citation ([domain-model.md:888](domain-model.md#L888)), so admitting it needs a further change. The human path exists in both modes, so no row is left unreachable. |
| `R6.7` | A project grant carries no `HUMAN`-class capability. | **chosen** — those are exercised per act under §5.2 (`R3.3`), with `decision.record` the stated exception. |

### Amendment 15 — `G-1`

**Target** [domain-model.md:887](domain-model.md#L887) (§12 Global invariants).

**Current frozen text**

```
| `G-1` | No entity outside `{ValidationReceipt, WorkerReceipt, CommitReceipt, ReviewAttestation, RealitySnapshot}` may be cited as `required_evidence`. A `Review` is never cited directly: the kernel-minted `ReviewAttestation` is what the `RVW(v)` token in `transition-matrix.md` resolves to, so a judgmental criterion is discharged by the kernel's measurement of the review, not by the reviewer's own verdict. |
```

**Proposed text**

```
| `G-1` | A `required_evidence` cell is a conjunction of **citations**, each of which may itself be a disjunction of alternatives; a cell is not typed as a whole, and each citation carries its own kind. An **evidence citation** names a record that measures reality, and no entity outside `{ValidationReceipt, WorkerReceipt, CommitReceipt, ReviewAttestation, RealitySnapshot}` may be cited as one; a `Review` is never cited directly, the kernel-minted `ReviewAttestation` being what the `RVW(v)` token in `transition-matrix.md` resolves to, so a judgmental criterion is discharged by the kernel's measurement of the review, not by the reviewer's own verdict. A **prerequisite citation** names a governance record the row requires to exist — an activation, a decision, an escalation, another persisted governance or verification record, or the discharged transition's own `AuditEvent`. A prerequisite citation is never a measurement and never makes a criterion `MET`. It has exactly the effect another rule of this design gives it: a `HumanDecision{kind ∈ {WAIVE, ACCEPT_RISK}}` discharges the shortfall it names by producing the `WAIVED` outcome `evidence-model.md` §4 reads, and an escalation or other claim-class record gates only on its existence, provenance and status, never on its content (evidence-model §2). Where a cell element names no record at all — a clock reading, a recomputation — it is a precondition, not a citation. |
```

**Closes** `D01-F02-004`. Fixes `DESIGN-04-005`, `-006` and part of `-008`.

| id | rule | basis |
|---|---|---|
| `R7.1` | The `required_evidence` column already holds records of both kinds. | **derived** — [transition-matrix.md:189](transition-matrix.md#L189) (`ACT`), [:266](transition-matrix.md#L266) (activation), [:141](transition-matrix.md#L141) (`DEC`), [:128](transition-matrix.md#L128) (`ESC`), [:394](transition-matrix.md#L394) (`AuditEvent`) against the five-entity allow-list and [evidence-model.md:82](evidence-model.md#L82)–[:86](evidence-model.md#L86). It exposes the mismatch; it does not derive this repair. |
| `R7.2` | The five-entity allow-list is carried over verbatim and now binds evidence citations. | **chosen** — only the five names and the `Review` exclusion are verbatim; restricting the allow-list's reach to a subcategory of citation changes the domain of [domain-model.md:887](domain-model.md#L887), which is part of the choice in `R7.4`, not a frozen derivation. |
| `R7.3` | A prerequisite citation is never a measurement, and a waiver decision nonetheless discharges the shortfall it names. | **derived** — `W` is an input to `observed_satisfaction` at [evidence-model.md:204](evidence-model.md#L204), the `SATISFIED` row reads `MET` **or** `WAIVED` at [:210](evidence-model.md#L210), and `WAIVED` is a `CriterionState.outcome` at [domain-model.md:246](domain-model.md#L246). The rows that use waivers per shortfall are [transition-matrix.md:139](transition-matrix.md#L139), [:207](transition-matrix.md#L207) and [:336](transition-matrix.md#L336). Revision 01's blanket "discharges no criterion" is withdrawn, and so is its attribution to `AX-9`: [authority-matrix.md:20](authority-matrix.md#L20) forbids a **capability** substituting for evidence and says nothing about an informed waiver, while [domain-model.md:716](domain-model.md#L716) governs uninformed approvals. |
| `R7.4` | Typing per citation, rather than widening the allow-list, is the correction. | **chosen** — the rejected alternative admits an activation, a decision or an escalation as evidence of satisfaction, which is the confusion the taxonomy exists to prevent ([evidence-model.md:55](evidence-model.md#L55)–[:65](evidence-model.md#L65)). Revision 01's whole-cell rule is withdrawn: it cannot express `ACT` + `SNAP` ([transition-matrix.md:123](transition-matrix.md#L123), [:189](transition-matrix.md#L189)) or `RVW` + `ESC` ([:137](transition-matrix.md#L137)). |

### Amendment 16 — the evidence-reachability verification check

**Target** [evidence-model.md:178](evidence-model.md#L178) (§3.3 Verification).

**Current frozen text**

```
| evidence reachability | every `required_evidence` cited by a transition event resolves to an event of class `EVIDENCE` with `seq` lower than the transition's | `INTEGRITY_VIOLATION` |
```

**Proposed text**

```
| evidence reachability | for each citation in the row's `required_evidence` (`G-1`), and for a disjunctive citation the one alternative the transition event names, that citation resolves to an earlier event of the same project with `seq` lower than the transition's, of the class its record carries: `EVIDENCE` for an evidence citation; `AUTHORITY` for an activation; `DECISION` for a `HumanDecision`; `CLAIM` for an escalation or another runtime-asserted governance or verification record; and any class for a cited `AuditEvent` or a cited persisted artifact or durable identity, which resolves to the event that persisted it. A cell element naming no record is a precondition and resolves to no event | `INTEGRITY_VIOLATION` |
```

**Closes** `D01-F02-004`. Fixes `DESIGN-04-005` and `-008`.

| id | rule | basis |
|---|---|---|
| `R8.1` | The strictly-lower-`seq` requirement is retained for every citation. | **derived** — carried over from the frozen check. An earlier `seq` still does not imply an earlier commit (`R3.12`). |
| `R8.2` | The class test is per citation, using the frozen classification. | **chosen** as a check; **derived** in its content for the four named record types — [evidence-model.md:83](evidence-model.md#L83) (activation is `AUTHORITY`), [:82](evidence-model.md#L82) (decision is `DECISION`), [:85](evidence-model.md#L85) (escalation is `CLAIM`), [:86](evidence-model.md#L86) (the `AuditEvent` is the envelope). |
| `R8.3` | A cited `AuditEvent`, artifact or durable identity is exempt from the class test. | **chosen** — being an envelope at [evidence-model.md:86](evidence-model.md#L86) does not derive an exception to the frozen `EVIDENCE` test; the exemption is justified by the consuming row's target ([transition-matrix.md:394](transition-matrix.md#L394)) and by the durable-identity rule the matrix cites ([evidence-model.md:151](evidence-model.md#L151), [transition-matrix.md:305](transition-matrix.md#L305), [:307](transition-matrix.md#L307)). |
| `R13.17` | A runtime-asserted governance or verification record is `CLAIM`-class and gates on existence and provenance. | **chosen** — a policy evaluation ([transition-matrix.md:157](transition-matrix.md#L157), [:170](transition-matrix.md#L170)) and a chain verification record ([:161](transition-matrix.md#L161), [:167](transition-matrix.md#L167), [:174](transition-matrix.md#L174), [:175](transition-matrix.md#L175), [:397](transition-matrix.md#L397)) are neither one of the five allow-list entities nor mintable as `EVIDENCE`, which requires one of five `KERNEL` capabilities ([evidence-model.md:63](evidence-model.md#L63)). Typing them `CLAIM` by the runtime follows the frozen treatment of `Escalation` ([evidence-model.md:85](evidence-model.md#L85)) and is a typing of records the rows already require, not a statement that the checks are untrustworthy. The rejected alternative — a sixth allow-list entity such as a `VerificationRecord` — would widen `G-1` beyond these five findings. |

### Amendment 17 — the `required_evidence` column semantics

**Target** [transition-matrix.md:48](transition-matrix.md#L48) (§1 Column semantics).

**Current frozen text**

```
| `required_evidence` | receipt/snapshot classes that must exist and be current; `—` means none |
```

**Proposed text**

```
| `required_evidence` | a conjunction of citations that must exist and be current, each typed on its own and each possibly a disjunction of alternatives (`G-1`): an evidence citation (receipt or snapshot) discharges the row's criterion, a prerequisite citation (an activation, a decision, an escalation, another governance or verification record, an `AuditEvent`, a persisted artifact or identity) must exist and discharges a criterion only where another rule gives it that effect, as a waiver decision does; an element naming no record is a precondition; `—` means none |
```

**Closes** `D01-F02-004`. Fixes `DESIGN-04-005`.

| id | rule | basis |
|---|---|---|
| `R9.1` | The column holds more than receipts and snapshots. | **derived** — the frozen cells in `R7.1` and the 44-row inventory in §2.22. |
| `R9.2` | The legend adopts `G-1`'s vocabulary, including the conjunction/disjunction structure. | **chosen** — wording, so the legend and the invariant agree. No seventh column is added, so the disclosed change stays inside the six semantic columns at [transition-matrix.md:45](transition-matrix.md#L45)–[:52](transition-matrix.md#L52). |

### Amendment 18 — `CLAIM` gating

**Target** [evidence-model.md:62](evidence-model.md#L62) (§2, the four-class table).

**Current frozen text**

```
| `CLAIM` | "what does someone say is true?" | any actor, typically a worker | no — only its provenance is verifiable | **never** | yes, trivially |
```

**Proposed text**

```
| `CLAIM` | "what does someone say is true?" | any actor, typically a worker | no — only its provenance is verifiable | **never on its content**; its existence, provenance and status may be a named prerequisite (`G-1`), which proves only that the claim was recorded | yes, trivially |
```

**Closes** `D01-F02-004`. Fixes `DESIGN-04-007`.

| id | rule | basis |
|---|---|---|
| `R13.18` | Admitting an escalation as a mandatory prerequisite requires amending this cell, not only retaining the class label. | **derived** — this cell says `CLAIM` can **never** gate a transition, and [evidence-model.md:85](evidence-model.md#L85) classes `Escalation` as `CLAIM`, while the frozen matrix makes `ESC(OPEN)` mandatory on thirteen rows of the inventory in §2.22. Revision 01 left the contradiction in place. |
| `R13.19` | Gating on existence and provenance is distinguished from trusting content. | **chosen** — the distinction is written into the cell itself. It is available because the same row already says a claim's provenance *is* verifiable while its content is not, and `G-3` ([domain-model.md:889](domain-model.md#L889)) is untouched. An escalation's own predicates — `status`, `auto_resolvable`, trigger, holder binding — remain preconditions of their rows. |

### Amendment 19 — genesis installs the project's chain state

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
| `R10.1` | The first append installs the project record and initializes the chain fields in one atomic write. | **chosen** — [evidence-model.md:127](evidence-model.md#L127) specifies event zero's predecessor hash and this step specifies the head update for an existing chain; neither specifies the installation, which is the residue `VERIFY-01` retains. Installing a transaction-local project at genesis does not by itself fix the creation transition's `seq`, which is `AX-17`'s business. |
| `R10.2` | `event_head` and `event_seq` remain derived, mutable, runtime-owned project fields. | **derived** — [domain-model.md:145](domain-model.md#L145), [:146](domain-model.md#L146); no field table is amended. |
| `R10.3` | The `schema_version` term in the genesis preimage is the domain model's version, not a storage schema version. | **derived** for the semantics — [evidence-model.md:127](evidence-model.md#L127) names `schema_version` and [domain-model.md:134](domain-model.md#L134) defines `Project.schema_version` as the domain model version. Separately and **chosen**: an implementation binding this to a `SCHEMA_VERSION` constant, distinct from a storage `STORAGE_VERSION` / `PRAGMA user_version`, is an implementation convention; no frozen design blob defines either constant, and the absence of a storage term does not define one. Line 127 is not amended. |

### Amendment 20 — append step 2 on an empty chain

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
| `R11.1` | The empty-chain branch reserves `seq = 0`. | **chosen** that an explicit branch is added, since the frozen step reads a field with no value before the first event; **derived** that the reserved value is zero — [evidence-model.md:127](evidence-model.md#L127), [:174](evidence-model.md#L174), [domain-model.md:779](domain-model.md#L779). |
| `R11.2` | The per-project lock and the no-skip rule are unchanged, including for the first append. | **derived** — carried over; [evidence-model.md:190](evidence-model.md#L190) untouched. |

### Amendment 21 — append step 3 on an empty chain

**Target** [evidence-model.md:136](evidence-model.md#L136) (§3.2, step 3).

**Current frozen text**

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

### 2.21 Total typing of every record kind named in a `required_evidence` cell

Amendment 16 assigns a class by the kind of record cited. This is the complete mapping over
the frozen matrix, including the kinds revision 01 left unmapped.

| record kind as the frozen cells name it | citation kind | class | example rows |
|---|---|---|---|
| `SNAP`, `VR(pass)`, `VR(any)`, `WR`, `CR`, `RVW(v)`, "usage records", "terminal receipt per drained operation", `CommitReceipt` | evidence | `EVIDENCE` | [transition-matrix.md:84](transition-matrix.md#L84), [:126](transition-matrix.md#L126), [:130](transition-matrix.md#L130), [:159](transition-matrix.md#L159), [:163](transition-matrix.md#L163), [:353](transition-matrix.md#L353) |
| `ACT`, "successor `ContractActivationRecord`", the activation named at [:266](transition-matrix.md#L266) | prerequisite | `AUTHORITY` | [transition-matrix.md:123](transition-matrix.md#L123), [:189](transition-matrix.md#L189), [:266](transition-matrix.md#L266), [:269](transition-matrix.md#L269), [:305](transition-matrix.md#L305) |
| `DEC(K)` for every `K`, "`DEC` referenced by each resolution" | prerequisite | `DECISION` | [transition-matrix.md:141](transition-matrix.md#L141), [:156](transition-matrix.md#L156), [:171](transition-matrix.md#L171), [:172](transition-matrix.md#L172), [:336](transition-matrix.md#L336) |
| `ESC(s)`, with or without a named trigger | prerequisite | `CLAIM`, existence and provenance only (amendment 18) | [transition-matrix.md:128](transition-matrix.md#L128), [:132](transition-matrix.md#L132), [:158](transition-matrix.md#L158), [:210](transition-matrix.md#L210) |
| "policy evaluation record", "policy re-evaluation record" | prerequisite | `CLAIM` by the runtime (`R13.17`) | [transition-matrix.md:157](transition-matrix.md#L157), [:170](transition-matrix.md#L170) |
| "failing / passing chain verification record", "failing verification record" | prerequisite | `CLAIM` by the runtime (`R13.17`) | [transition-matrix.md:161](transition-matrix.md#L161), [:167](transition-matrix.md#L167), [:174](transition-matrix.md#L174), [:175](transition-matrix.md#L175), [:397](transition-matrix.md#L397) |
| "revocation record" | prerequisite | the `AuditEvent` of the `contract.revoke` transition that revoked the activation — envelope, any class; where the cell instead names `DEC(REVOKE_CAPABILITY)`, `DECISION` | [transition-matrix.md:191](transition-matrix.md#L191), [:270](transition-matrix.md#L270) |
| "the transition's own `AuditEvent`" | prerequisite | envelope, any class; `seq` lower than the consuming event | [transition-matrix.md:394](transition-matrix.md#L394) |
| "the `InvocationRequest` persisted as `request_ref` …", "`prompt_bundle_ref` persisted", "counter `ArtifactRef` set" | prerequisite | the event that persisted the artifact or durable identity — envelope, any class ([evidence-model.md:151](evidence-model.md#L151)) | [transition-matrix.md:305](transition-matrix.md#L305), [:307](transition-matrix.md#L307), [:337](transition-matrix.md#L337) |
| "the triggering record" | prerequisite | the class of whichever record the §9.B.1 trigger names, by this table | [transition-matrix.md:412](transition-matrix.md#L412) |
| "contract `contract_hash` verified", "or clock" | not a citation: a precondition | none; resolves to no event | [transition-matrix.md:121](transition-matrix.md#L121), [:340](transition-matrix.md#L340) |

One disclosed choice: `R13.17` types the policy and verification records `CLAIM` by the
runtime rather than adding a sixth `G-1` entity. Nothing else in this table is optional
once amendment 16 is adopted.

### 2.22 Verification against the review's 44-row inventory

Every row the review's §1.4 scan identified as naming `ACT`, `DEC`, `ESC`, an
activation/revocation record, or an `AuditEvent`. `M` marks a row the review flagged as
mixed, `U` as untyped, `C` as a `CLAIM`-gate conflict, `W` as a waiver route; each is the
review's code, followed by how the amended rules resolve it. Independent lifecycle and
authority defects are noted where they survive.

| row | citations, typed per citation | review code, resolved |
|---|---|---|
| [:123](transition-matrix.md#L123) | `ACT` → `AUTHORITY`; `SNAP` → `EVIDENCE` | **M** — two citations, two kinds; no cell-level class is assigned. |
| [:128](transition-matrix.md#L128) | `ESC(OPEN)` → `CLAIM`, existence only | **P, C** — `C` closed by amendment 18; `auto_resolvable = false` and the run binding stay preconditions. |
| [:132](transition-matrix.md#L132) | `ESC(OPEN)` with trigger → `CLAIM` | **P, C** — as above; the trigger stays a precondition on the cited escalation. |
| [:137](transition-matrix.md#L137) | `RVW` set → `EVIDENCE`; `ESC(OPEN)` → `CLAIM` | **M, C** — both resolved. |
| [:139](transition-matrix.md#L139) | `DEC(WAIVE)`/`DEC(ACCEPT_RISK)` per shortfall → `DECISION`, discharging that shortfall as `WAIVED`; `VR(pass)` and `RVW` set → `EVIDENCE`; `SNAP` → `EVIDENCE` | **M, W** — `W` closed by `G-1`'s waiver clause. |
| [:140](transition-matrix.md#L140) | `DEC(OVERRIDE)` or `DEC(EXTEND_BUDGET)` → `DECISION`, per alternative | **P** — rework and budget guards remain separate; `D01-F02-008` survives. |
| [:141](transition-matrix.md#L141) | `DEC(REJECT)` → `DECISION` | **P** — validity and `evidence_shown` survive ([transition-matrix.md:74](transition-matrix.md#L74)). |
| [:142](transition-matrix.md#L142) | `DEC(ABANDON)` → `DECISION` | **P** — recordable under amendment 12, since a project-subject `ABANDON` is not snapshot-bound. |
| [:144](transition-matrix.md#L144) | `DEC(OVERRIDE)` → `DECISION` | **P**. |
| [:156](transition-matrix.md#L156) | `DEC(SUSPEND)` → `DECISION` | **P**. |
| [:158](transition-matrix.md#L158) | `ESC(OPEN)` → `CLAIM` | **P, C** — resolved. |
| [:161](transition-matrix.md#L161) | failing chain verification record → `CLAIM` by the runtime, **or** `ESC(OPEN)` → `CLAIM`; one alternative cited | **U, C** — `U` closed by §2.21's verification-record row; per-alternative typing selects the branch. |
| [:162](transition-matrix.md#L162) | `DEC(SUSPEND)` → `DECISION`; terminal receipts → `EVIDENCE` | **M** — resolved. |
| [:164](transition-matrix.md#L164) | `ESC(OPEN)` → `CLAIM`; terminal receipts → `EVIDENCE` | **M, C** — resolved. |
| [:168](transition-matrix.md#L168) | `DEC(RESUME)` → `DECISION` | **P**. |
| [:169](transition-matrix.md#L169) | `DEC(RESUME)` → `DECISION` | **P**. |
| [:170](transition-matrix.md#L170) | policy re-evaluation record → `CLAIM` by the runtime, **or** `DEC(OVERRIDE)` → `DECISION` | **U** — closed by §2.21. |
| [:171](transition-matrix.md#L171) | the `DEC` each resolution referenced → `DECISION` | **P** — the citation is the decision each resolution actually referenced, live at that resolution, not mere historical existence; an `auto_resolvable` resolution cites no decision and the row's precondition governs. |
| [:172](transition-matrix.md#L172) | `DEC(EXTEND_BUDGET)` → `DECISION` | **P** — admissibility changes; `D01-F02-008`'s immutable allocation survives untouched. |
| [:173](transition-matrix.md#L173) | clean `SNAP` → `EVIDENCE`, **or** `DEC(ACCEPT_RISK)` → `DECISION` | **M** as a fixed cell type — resolved by per-alternative typing. |
| [:174](transition-matrix.md#L174) | passing chain verification record → `CLAIM` by the runtime; `DEC(OVERRIDE)` → `DECISION` | **U** — closed by §2.21; both conjuncts typed. |
| [:176](transition-matrix.md#L176) | `DEC(SUSPEND)` → `DECISION` | **P**. |
| [:189](transition-matrix.md#L189) | `ACT` → `AUTHORITY`; `SNAP` → `EVIDENCE` | **M** — one of `D01-F02-004`'s original examples, now typed per citation. |
| [:191](transition-matrix.md#L191) | revocation record → envelope of the `contract.revoke` transition, any class | **U** — closed by §2.21. |
| [:195](transition-matrix.md#L195) | `ESC(OPEN)` → `CLAIM` | **P, C** — resolved. |
| [:200](transition-matrix.md#L200) | `ESC(OPEN)` → `CLAIM` | **P, C** — resolved. |
| [:204](transition-matrix.md#L204) | `ESC(OPEN)` → `CLAIM` | **P, C** — resolved. |
| [:206](transition-matrix.md#L206) | `DEC(OVERRIDE)` → `DECISION` | **P** — `D01-F02-008`'s deadline immutability survives. |
| [:207](transition-matrix.md#L207) | `DEC(WAIVE)` per shortfall → `DECISION`, discharging it as `WAIVED`; remaining `VR(pass)`/`RVW` → `EVIDENCE` | **M, W** — both resolved. |
| [:208](transition-matrix.md#L208) | `DEC(REJECT)` → `DECISION` | **P**. |
| [:209](transition-matrix.md#L209) | `DEC(ABANDON)` → `DECISION` | **P**. |
| [:210](transition-matrix.md#L210) | `ESC(OPEN)` with `RECOVERY_AMBIGUITY` → `CLAIM` | **P, C** — resolved. |
| [:266](transition-matrix.md#L266) | the minted activation → `AUTHORITY` | **P** — `authority_chain` non-empty and a `capability_grant_basis` entry per granted capability remain mandatory (`A-INV-3`), and amendment 7 leaves that clause in force for run grants. |
| [:269](transition-matrix.md#L269) | successor activation → `AUTHORITY` | **P** — admissibility changes; `D01-F02-007`'s guard cycle survives untouched. |
| [:270](transition-matrix.md#L270) | `DEC(REVOKE_CAPABILITY)` → `DECISION`, **or** the triggering record → typed by §2.21 | **P / U** — closed by §2.21's triggering-record and revocation rows. |
| [:305](transition-matrix.md#L305) | `ACT` → `AUTHORITY`; the persisted `InvocationRequest` with its `idempotency_key` → the event that made that identity durable, envelope | **U** — closed by §2.21; `G-9`'s ordering ([evidence-model.md:151](evidence-model.md#L151)) is what makes that event exist and precede. |
| [:336](transition-matrix.md#L336) | `DEC(WAIVE)` → `DECISION`, discharging the waivable criterion as `WAIVED` | **P, W** — `justification` and `evidence_shown` still required; the waiver's normative effect is preserved by `G-1`. |
| [:338](transition-matrix.md#L338) | `RVW(PASS)` by an `INDEPENDENT` reviewer → `EVIDENCE`, **or** `DEC(OVERRIDE)` → `DECISION` | **M** as a fixed cell type — resolved by per-alternative typing; the independence predicate stays on the cited attestation. |
| [:340](transition-matrix.md#L340) | `DEC(REVOKE_CAPABILITY)` → `DECISION`, **or** clock → precondition, no citation | **P / U** — closed by §2.21's final row. |
| [:348](transition-matrix.md#L348) | the newly satisfied `VR(pass)` → `EVIDENCE`; `RVW` → `EVIDENCE`; `DEC` → `DECISION` | **M** — each cited requirement keeps its own kind. |
| [:353](transition-matrix.md#L353) | `CommitReceipt` with `verification = DIVERGED` → `EVIDENCE`; `ESC(OPEN)` → `CLAIM` | **M, C** — resolved. |
| [:358](transition-matrix.md#L358) | `CR` qualified `DIVERGED` → `EVIDENCE`; `ESC(OPEN)` → `CLAIM` | **M, C** — typing resolved; `D01-F02-010`'s `MATCHED`/`DIVERGED` contradiction survives untouched and is out of scope (§1.4). |
| [:394](transition-matrix.md#L394) | the discharged transition's own `AuditEvent` → envelope, any class, `seq` lower than the consuming event | **P** — under `R8.3`'s disclosed exemption. |
| [:414](transition-matrix.md#L414) | `DEC(K)` for `K ∈ required_decision_kinds` → `DECISION`, **or** `SNAP`/`VR(pass)` → `EVIDENCE` | **M** as a fixed cell type — resolved per alternative; the decision-kind set and the `auto_resolvable` condition stay preconditions. |

All 44 rows receive a total typing. Three rows carry independent findings that these
amendments do not touch and do not claim to close: [:172](transition-matrix.md#L172) and
[:206](transition-matrix.md#L206) (`D01-F02-008`), [:269](transition-matrix.md#L269)
(`D01-F02-007`), [:358](transition-matrix.md#L358) (`D01-F02-010`).

---

## 3. Frozen locations this document leaves untouched

Every location a reader might expect these corrections to touch. Nine locations listed as
untouched in revision 01 are now **amended** and appear in §2 instead:
[authority-matrix.md:12](authority-matrix.md#L12), [:15](authority-matrix.md#L15),
[:19](authority-matrix.md#L19), [:22](authority-matrix.md#L22),
[:292](authority-matrix.md#L292), [domain-model.md:380](domain-model.md#L380)–[:381](domain-model.md#L381),
[transition-matrix.md:49](transition-matrix.md#L49), [:393](transition-matrix.md#L393),
[evidence-model.md:62](evidence-model.md#L62).

| frozen location | current content, in brief | why untouched |
|---|---|---|
| [authority-matrix.md:13](authority-matrix.md#L13) `AX-2`, [domain-model.md:890](domain-model.md#L890) `G-4` | Exactly one capability per state-changing operation; absence ⇒ DENY. | Untouched and load-bearing: it is why the creation witness needs four events rather than a merged one (`R13.14`). |
| [authority-matrix.md:16](authority-matrix.md#L16) `AX-5` | No principal grants what it does not hold, except `HUMAN_PRINCIPAL` within the ceiling. | Compatible. A project grant is human-issued and ceiling-bounded (`R6.2`); a per-act exercise delegates nothing, now by the explicit predicate at §5.2 step 6 rather than by inference. |
| [authority-matrix.md:17](authority-matrix.md#L17) `AX-6`, [:18](authority-matrix.md#L18) `AX-7` | `NEVER` is never grantable; `KERNEL` is kernel-held, non-delegable, never in an invocation. | Untouched in substance. `AX-7` is the kernel form amendment 1 represents; it is **not** the rule `AX-15` excepts, which is `AX-1`. No amendment grants a `KERNEL` capability to a non-kernel actor or puts one in an invocation. |
| [authority-matrix.md:20](authority-matrix.md#L20) `AX-9` | A capability never substitutes for `required_evidence`. | Untouched, and its meaning is no longer overstated: it governs capabilities, not the effect of a waiver decision (`R7.3`). §5.2 step 8 invokes it only to keep a row's evidence unsubstituted. |
| [authority-matrix.md:30](authority-matrix.md#L30), [:34](authority-matrix.md#L34) | `HUMAN_PRINCIPAL`'s and `RUNTIME_KERNEL`'s grant powers. | Untouched. [:34](authority-matrix.md#L34) still forbids kernel self-granting a non-`KERNEL` capability; under `AX-16` the kernel never does, since the authority cited is the human's decision. It is not the basis of any actor-equality rule (`R3.11`). |
| [authority-matrix.md:41](authority-matrix.md#L41) | When a `HUMAN_DECISION` grant expires. | Untouched; `AX-20` adds when the nonce is spent, which this line does not state (`R6.5`). |
| [authority-matrix.md:51](authority-matrix.md#L51)–[:52](authority-matrix.md#L52) | The `HUMAN` class legend. | Untouched; §5.2 implements it, and `AX-14` is how it is satisfied on the `AUTO` rows. |
| [authority-matrix.md:56](authority-matrix.md#L56)–[:147](authority-matrix.md#L147) | The capability register. | No class, grantor, default or mode restriction changes. `AX-15` states a holding the register does not describe; [:143](authority-matrix.md#L143) keeps describing grantability and keeps `DENY` as the default for anyone but the authenticated principal recording their own decision. |
| [authority-matrix.md:155](authority-matrix.md#L155)–[:173](authority-matrix.md#L173) | The §3 mode gate. | Applied unchanged by §5.2 step 3 and §5.3 step 3. No capability becomes available in a mode that denied it; `project.create` stays `DENY` in `AUTONOMOUS`. |
| [authority-matrix.md:190](authority-matrix.md#L190)–[:222](authority-matrix.md#L222) | §4.1's per-invocation grant table, including [:221](authority-matrix.md#L221). | Untouched, and the reason no run grant can carry a `HUMAN`-class capability (`R3.2`). The `C`/`D` tension at [:203](authority-matrix.md#L203), [:206](authority-matrix.md#L206) against [:221](authority-matrix.md#L221) predates this document and is not one of the five findings; no amendment relies on resolving it. Amendment 6 is what stops the table's inapplicability to project grants from being a silent change. |
| [authority-matrix.md:239](authority-matrix.md#L239)–[:277](authority-matrix.md#L277) | §5 resolution and §5.1 admissible grantors. | Unchanged for run grants. §5.2 and §5.3 are additive sections after §5.1; step 5's `KERNEL` removal and [:266](authority-matrix.md#L266)'s "never for a run's grant" both stand. |
| [authority-matrix.md:285](authority-matrix.md#L285)–[:291](authority-matrix.md#L291), [:293](authority-matrix.md#L293) | §6's other enforcement points. | Untouched, and two are relied on: decision freshness at [:289](authority-matrix.md#L289) enforces the liveness §5.2 step 4 and `AX-19` require, and the denial `AuditEvent` at [:293](authority-matrix.md#L293) is the destination amendment 9 uses. |
| [domain-model.md:38](domain-model.md#L38), [:273](domain-model.md#L273), [:390](domain-model.md#L390), [:778](domain-model.md#L778), [:805](domain-model.md#L805), [:865](domain-model.md#L865) | Reference integrity and the activation/run cardinality. | Untouched. They are compatible with one transaction and deferred checks; `R3.12` applies that reading rather than weakening them. |
| [domain-model.md:141](domain-model.md#L141), [:153](domain-model.md#L153) | The ceiling and `P-INV-2`. | Untouched, and the basis for `R6.2`. Neither prescribes an empty initial ceiling; see §6.2. |
| [domain-model.md:145](domain-model.md#L145), [:146](domain-model.md#L146) | `event_head`, `event_seq`. | Untouched; initialization belongs to the append protocol. |
| [domain-model.md:284](domain-model.md#L284), [:285](domain-model.md#L285), [:287](domain-model.md#L287) | Run budget and deadline mutability. | Untouched: `D01-F02-008` is out of scope. Retyping `DEC(EXTEND_BUDGET)` does not extend them. |
| [domain-model.md:410](domain-model.md#L410) `A-INV-2` | Activation is the only entity conferring authority on a run. | Untouched and still literally true: `AX-18` keeps a project grant out of every run set, and amendment 8 scopes `C-INV-3` rather than repealing it (`R13.8`). |
| [domain-model.md:686](domain-model.md#L686)–[:712](domain-model.md#L712) | `HumanDecision` fields. | No field, type or enum changes. Two profiles are now written as explicit checks rather than assumed: `grants = revokes = ∅` for a per-act decision (§5.2 step 6), and `kind: GRANT_CAPABILITY, scope: PROJECT` for a project grant (§5.3 step 1). |
| [domain-model.md:714](domain-model.md#L714)–[:727](domain-model.md#L727) | `HD-INV-1` … `HD-INV-4`. | Untouched. `AX-20` states where a standing grant's single consumption falls, which is what `HD-INV-3` requires of it; `HD-INV-4` continues to stale a snapshot-bound decision, including those `R13.13` identifies. |
| [domain-model.md:789](domain-model.md#L789), [:797](domain-model.md#L797) | `capability_used` required for state-changing events; every transition emits an event first. | Untouched, and why the creation witness has four events. |
| [domain-model.md:888](domain-model.md#L888) `G-2`, [:889](domain-model.md#L889) `G-3` | The authority-citation allow-list; worker values are `CLAIM`. | Untouched. Every citation introduced is a `HumanDecision` or a `ContractActivationRecord`, or is absent; amendment 18 changes what a `CLAIM` may gate, not what a worker-authored value is. |
| [evidence-model.md:63](evidence-model.md#L63)–[:86](evidence-model.md#L86) | The `EVIDENCE`/`DECISION`/`AUTHORITY` rows and the classification table. | Untouched. Amendment 18 changes only the `CLAIM` row's gating cell; amendment 16 reads the classification table rather than reclassifying anything. `EVIDENCE` minting still requires one of five `KERNEL` capabilities, which is why `R13.17` types verification records `CLAIM`. |
| [evidence-model.md:127](evidence-model.md#L127) | The genesis hash formula. | Untouched; see `R10.3` on `schema_version`. |
| [evidence-model.md:132](evidence-model.md#L132) | The append table's three columns. | Untouched, and now respected by amendment 21. |
| [evidence-model.md:138](evidence-model.md#L138), [:139](evidence-model.md#L139), [:143](evidence-model.md#L143), [:173](evidence-model.md#L173)–[:175](evidence-model.md#L175), [:177](evidence-model.md#L177), [:187](evidence-model.md#L187), [:190](evidence-model.md#L190) | Atomicity, observability, the external-effect exclusion, the other chain checks, replay order, the lock. | Untouched. The four-event witness preserves all of them: one atomic write per append inside one transaction, no publication before persistence, chain order authoritative. |
| [evidence-model.md:167](evidence-model.md#L167) | Reconciliation closure. | Untouched: `D01-F02-009` is out of scope. |
| [evidence-model.md:194](evidence-model.md#L194)–[:214](evidence-model.md#L214) | `observed_satisfaction`, including `W` and the `WAIVED` disjunct. | Untouched — and this is the point of amendment 15's waiver clause: the derivation keeps reading waivers exactly as frozen. |
| [transition-matrix.md:45](transition-matrix.md#L45)–[:47](transition-matrix.md#L47), [:50](transition-matrix.md#L50)–[:52](transition-matrix.md#L52) | The other five semantic columns. | Untouched. No seventh column is added. |
| [transition-matrix.md:58](transition-matrix.md#L58)–[:62](transition-matrix.md#L62) | The policy verdict vocabulary. | Untouched. `AX-14` reads `AUTO` as the policy engine's contribution and [:60](transition-matrix.md#L60)'s `CONFIRM` as already fixing `APPROVE`. |
| [transition-matrix.md:64](transition-matrix.md#L64)–[:76](transition-matrix.md#L76) | The evidence shorthand. | No token is redefined; `CR` in particular is untouched. |
| [transition-matrix.md:84](transition-matrix.md#L84), [:85](transition-matrix.md#L85), [:117](transition-matrix.md#L117), [:265](transition-matrix.md#L265) | Creation, first import, first authoring. | No cell is amended. `AX-17` supplies creation's witness and authority; amendments 10–14 supply the import/authoring grant. |
| [transition-matrix.md:86](transition-matrix.md#L86)–[:97](transition-matrix.md#L97), [:119](transition-matrix.md#L119)–[:142](transition-matrix.md#L142), [:208](transition-matrix.md#L208), [:336](transition-matrix.md#L336) | The eighteen `HUMAN`-class rows. | No cell is amended. Fifteen are authorized by the decision their own verdict names; [:84](transition-matrix.md#L84) and [:97](transition-matrix.md#L97) need the chosen `APPROVE` (`R3.6`), which for [:97](transition-matrix.md#L97) adds a snapshot its evidence cell does not name (`R3.7`). Revision 01's claim that each row already names its decision is withdrawn. |
| [transition-matrix.md:108](transition-matrix.md#L108)–[:113](transition-matrix.md#L113), [:435](transition-matrix.md#L435) | The startup exception; no dispatch during `DRAFT`/`PLANNING`. | Untouched and not widened. No authority form adds a row to `PLANNING` or permits a dispatch there. |
| [transition-matrix.md:394](transition-matrix.md#L394)–[:397](transition-matrix.md#L397), [:399](transition-matrix.md#L399) | The rest of §7.5 and its prose. | Untouched. Only [:393](transition-matrix.md#L393)'s evidence cell is amended; [:399](transition-matrix.md#L399) is cited as support for `AX-15`'s `AUTO`, not for the holding. |
| [transition-matrix.md:485](transition-matrix.md#L485) | Creation by a non-human is `NONE_GRANTABLE`. | Untouched, and cited in §6.2: it connects human origination of a project with its ceiling. |
| `design/schema/**`, [roadmap_adapter.md](roadmap_adapter.md), [worker_provider.md](worker_provider.md) | Frozen schemas and adapter interfaces. | No JSON field or enum is added. The adapter's import requirement ([roadmap_adapter.md:56](roadmap_adapter.md#L56), [:57](roadmap_adapter.md#L57)) is satisfied by amendments 10–14 without an interface change, and its secret resolution ([:78](roadmap_adapter.md#L78), [:90](roadmap_adapter.md#L90)) is attributed by `AX-16`'s `on_behalf_of` rather than by requiring a `HUMAN` actor on a kernel-mediated event. |

---

## 4. Chosen and derived

Convention: every rule in §2 carries a `basis` cell. **Derived** means the rule follows
from frozen text cited in that same cell. **Chosen** means it does not — the frozen text is
silent, or says something the rule replaces. **Conditional** means it follows from frozen
text *given* a choice made elsewhere in this document, and is marked as such rather than as
derived. A rule with two marks says which half is which.

This section makes no claim about the set as a whole. Each label stands or falls on its own
cell, and revision 01's assurance that no choice was presented as a derivation is deleted:
the review found eight such labels, and they are corrected below.

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
| `R6.5` | derived | chosen | `AX-20`'s lifecycle is a choice, and now states the nonce boundary `HD-INV-3` requires. |
| `R7.2` | derived | chosen | Restricting the allow-list's reach to evidence citations changes its domain. |
| `R7.3` | derived | derived, and rewritten | The universal no-discharge rule was false; the waiver route is preserved and the `AX-9` attribution withdrawn. |
| `R8.3` | derived | chosen | An envelope exemption to the frozen `EVIDENCE` test is a choice, justified by the consuming row. |
| `R10.3` | derived | derived / chosen, split | The domain-vs-storage semantics are derived with [domain-model.md:134](domain-model.md#L134) added; binding either to a named implementation constant is a separate, chosen convention. |
| `R11.1` | chosen | chosen / derived, split | The branch is new; the value zero is forced. |

New rules in this revision: `R13.1` … `R13.20`. Chosen among them: `R13.2`, `R13.3`,
`R13.6`, `R13.8`, `R13.9`, `R13.17`, `R13.19`. Derived: `R13.1`, `R13.4` (possession half),
`R13.5`, `R13.7`, `R13.10`, `R13.11`, `R13.12`, `R13.13`, `R13.14`, `R13.15`, `R13.16`,
`R13.18`, `R13.20`.

---

## 5. What `DESIGN-03` must change once this freezes

`DESIGN-03` revision 02 specifies **direct exercise** for five project-holder capabilities
and amends [evidence-model.md:176](evidence-model.md#L176) itself. Amendments 1–5 and 13
generalize that mechanism and carry the enforcement-point changes it also needs. The two
documents cannot both freeze as written. Claims below are limited to what the amendments in
§2 deliver.

| `DESIGN-03` location | why it must change | required change |
|---|---|---|
| `PP-1` — the frozen design requires a non-delegated path and specifies none. | §5.2 specifies that path for the seven `HUMAN` capabilities with legal rows, with the `AX-1`/§6/`required_capability` exceptions `PP-1` does not name. `PP-1` cites three rows; the inventory has eighteen. | Restate as a reference to authority-matrix §5.2, keeping the claim that the four governance writes need **transition rows**, which §5.2 does not supply (§6.1). |
| `PP-2` — what is cited for `required_capability`. | The same reading as `R1.4`, now carried by amendment 1 plus amendments 3–5. | Cite the amended [evidence-model.md:176](evidence-model.md#L176), [authority-matrix.md:12](authority-matrix.md#L12), [:292](authority-matrix.md#L292) and [transition-matrix.md:49](transition-matrix.md#L49); drop the specification claim. |
| `PP-3` — a provisioning decision is `DECISION` class; disposition `-009`'s "only `:176` is amended". | The substance agrees with `R3.10` and `R5.2`, but the scope claim is false: this document amends twenty-one locations, including [evidence-model.md:62](evidence-model.md#L62), [:95](evidence-model.md#L95), [:178](evidence-model.md#L178) and six authority-matrix lines. | Re-verify `-009` against the amended baseline and restate its scope sentence. `PP-3`'s empty-delta premise must also become an explicit predicate, as §5.2 step 6 now is. |
| `PP-4`, `PP-5` — the ceiling does not bound direct exercise of the five. | `AX-13` states this generally and `R3.9` marks it chosen in whole, withdrawing the forced/chosen split `PP-4` relies on. | Delete the mechanism; keep the payload predicates and the `evidence_shown` content requirement. |
| `PP-4a` — `project.abandon` and `stage.abandon` "reachable by no specified path remains an open frozen gap". | Closed by amendments 3–5, 12 and 13: those rows name `DECIDE(ABANDON)`, and amendment 12 makes a project-subject `ABANDON` decision recordable. | Remove that entry from `DESIGN-03` §8 and point to §5.2. |
| `PP-6` — no self-authorization. | Superseded by `AX-16`: the performing actor may be `RUNTIME` with `on_behalf_of`, which `PP-6` treats as an integrity violation. This is the second substantive disagreement between the documents. | Adopt `AX-16`, or contest `R3.11` on the record. `PP-6`'s underlying rule — the kernel self-grants nothing — is preserved either way. |
| `PP-7` — one decision, one field, one write. | Consistent with §5.2 for per-act decisions, but `AX-20` gives a standing project grant a different consumption boundary. | Add the `AX-20` distinction so the unqualified rule is not read across §5.3. |
| `PP-8` — "This amendment adds no decision requirement to it." | Settled against `PP-8` by the review's §5 and by `AX-14`: `AUTO` states the policy engine's contribution and does not discharge [authority-matrix.md:51](authority-matrix.md#L51). Its transaction argument stands but its two-event values do not. | Adopt the decision requirement and `AX-17`'s four-event witness; the kind `APPROVE` keeps its chosen label. |
| §2.1 — ten-step admissibility. | Steps 1–4, 6 and 8 restate §5.2 steps 1, 3, 4, 5, 7 and 9. | Rewrite as a delta over §5.2, keeping the `evidence_shown` content requirement, the payload predicates and the atomicity rule. |
| §2.2 — `ProvisioningDecision` as a profile. | Unaffected: no field, enum or entity changes here. | No change. |
| §3 — `project.ceiling.set` and the mode-gate additions. | Unaffected. It is no longer a prerequisite of the first project grant (§6.2), but it is still the only specified way to change a ceiling after creation. | No change, beyond dropping any claim that §5.3 depends on it. |
| §6 — the initial `Project` state, `event_seq = 1`. | Superseded by `AX-17` and amendments 19–21: the witness ends at `event_seq = 3`. | Replace the asserted values with the amended [evidence-model.md:128](evidence-model.md#L128), [:135](evidence-model.md#L135), [:136](evidence-model.md#L136) and `AX-17`; if `DESIGN-03` keeps an empty initial ceiling, state it as its own choice (§6.2). |

Ordering: `DESIGN-04` should freeze first, since `DESIGN-03` stands on an authority path
that is not baseline text until these amendments land. Per the review method, the reviewer
of a revised `DESIGN-03` is the reviewer that raised `DESIGN-03-FINDINGS-01`, and this
document's author does not review it.

---

## 6. Delimitations

### 6.1 The ten `HUMAN` capabilities with no legal row

§5.2 supplies the authority form for all seventeen `HUMAN`-class capabilities. Its
procedure binds only the seven that a legal row names as `required_capability`, because
steps 2, 5 and 8 read that row. Revision 01 claimed the whole class; that claim is
withdrawn. Where the other ten close:

| capability | register row | where its exercise closes |
|---|---|---|
| `project.mode.set` | [authority-matrix.md:59](authority-matrix.md#L59) | `DESIGN-03` §5: a transition row per governance-field write. `P-INV-1` ([domain-model.md:152](domain-model.md#L152)) already requires `DEC(SET_MODE)`. |
| `policy.set` | [authority-matrix.md:63](authority-matrix.md#L63) | `DESIGN-03` §5, with its new decision kind. |
| `budget.grant` | [authority-matrix.md:65](authority-matrix.md#L65) | `DESIGN-03` §5, with its new decision kind. |
| `budget.extend` | [authority-matrix.md:66](authority-matrix.md#L66) | `DESIGN-03` §5 for the project holder. For a run holder the obstruction is `D01-F02-008`, which is out of scope here. |
| `policy.override` | [authority-matrix.md:64](authority-matrix.md#L64) | **Not closed anywhere yet.** No row names it, and no document proposes one. It is exercised wherever a policy verdict is overridden; the missing artefact is a row, not an authority form. |
| `commit.publish` | [authority-matrix.md:134](authority-matrix.md#L134) | **Not closed.** Only prose specifies it ([transition-matrix.md:381](transition-matrix.md#L381)–[:383](transition-matrix.md#L383)); it needs a row before §5.2's procedure can bind. |
| `audit.redact` | [authority-matrix.md:146](authority-matrix.md#L146) | **Not closed.** [evidence-model.md:270](evidence-model.md#L270) names the authority and a decision naming the artifact; there is no matrix row. |
| `secret.read` | [authority-matrix.md:110](authority-matrix.md#L110) | **Not closed.** The act happens inside execution, not at a transition. `AX-16` supplies the attribution for a kernel-mediated resolution ([roadmap_adapter.md:78](roadmap_adapter.md#L78), [:90](roadmap_adapter.md#L90)); what is missing is a specified point at which the exercise decision is presented and consumed. |
| `net.egress.any` | [authority-matrix.md:109](authority-matrix.md#L109) | **Not closed.** Same shape; `CLAUDE.md`'s `GR-17` note records exactly this gap in the implementation — an exercise-decision parameter at the execution boundary. |
| `proc.exec.arbitrary` | [authority-matrix.md:107](authority-matrix.md#L107) | **Not closed.** Same shape, with results never `EVIDENCE` by its own register row. |

`D01-F02-003` is nonetheless closed: the four capabilities it names — `project.abandon`,
`project.archive`, `stage.reject`, `stage.abandon` — are among the seven, as are
`decision.record` and `finding.waive`, the two further operations it names as stranded by
the same mechanism. The six capabilities marked "not closed" above are named by that
finding as further instances; each now has an authority form and lacks a row or an
execution-boundary point, which is a different gap and is stated here rather than claimed
closed.

### 6.2 The initial `capability_ceiling`

This document **chooses** the premise that the creating human supplies a non-empty
`capability_ceiling` in the creating act, containing at least the capabilities the project
will grant at project scope. The premise is permitted, not forced:
[domain-model.md:141](domain-model.md#L141) makes the ceiling required and human-sourced
without prescribing an initial value, and
[transition-matrix.md:485](transition-matrix.md#L485) connects human origination of a
project with its own ceiling. `DESIGN-03-015` already rejected a frozen derivation of an
empty ceiling.

Consequences, stated rather than assumed:

- Under this premise the first project grant of `roadmap.import` or `contract.author` needs
  no later setter, and `D01-F02-005`'s closure rests on amendments 6–8, 10, 11, 12 and 14.
- Revision 01's claim that the first grant necessarily depends on `DESIGN-03`'s
  `project.ceiling.set` is **withdrawn**.
- A non-empty initial ceiling grants nothing: bounding is not granting, and amendment 7
  keeps that sentence verbatim (`R13.7`).
- If a project is instead created with an empty ceiling — as `DESIGN-03` §6 proposes — then
  a ceiling-setting operation becomes a genuine prerequisite of the first project grant.
  That is a conditional dependency of that choice, not of this correction.

### 6.3 Two revision-01 claims withdrawn

| claim in revision 01 | disposition |
|---|---|
| An empty initial ceiling is forced, making the ceiling exemption forced for `project.create`. | **Withdrawn** (§6.2, `R3.9`). The review's counterexample is accepted. |
| The run-bound `escalation.raise` at [transition-matrix.md:128](transition-matrix.md#L128) has no authority form, and belongs in a later findings record. | **Withdrawn.** The review's refutation is accepted: `escalation.raise` has a `G` cell for every role ([authority-matrix.md:216](authority-matrix.md#L216)) with `ROLE_DEFAULT` as an admissible grantor ([:265](authority-matrix.md#L265)), so that run's activation can carry it ([domain-model.md:392](domain-model.md#L392), [:410](domain-model.md#L410)), and amendment 1's grant branch accepts a live activation containing the capability with no worker-actor predicate. No finding is promoted from it. |

### 6.4 What these amendments still do not do

| item | statement |
|---|---|
| Rows for the four governance writes | `project.mode.set`, `policy.set`, `budget.grant`, `budget.extend` have an authority form and no row. That is `DESIGN-03`'s subject, and `D01-F02-003`'s substance does not depend on it (§6.1). |
| The execution-boundary exercise point | `secret.read`, `net.egress.any` and `proc.exec.arbitrary` are exercised inside execution rather than at a transition, and no document specifies where their decision is presented and consumed (§6.1). |
| A sixth evidence entity | `R13.17` types verification and policy-evaluation records `CLAIM` by the runtime rather than widening `G-1`'s five-entity allow-list. If a later design prefers a `VerificationRecord` as `EVIDENCE`, that is a change to [domain-model.md:887](domain-model.md#L887) beyond these five findings. |
| The `C`/`D` tension in §4.1 | [authority-matrix.md:203](authority-matrix.md#L203) and [:206](authority-matrix.md#L206) give `C` cells to `HUMAN`-class capabilities that [:221](authority-matrix.md#L221) denies to every role. Pre-existing, not one of the five findings, and no amendment depends on resolving it. |
| Implementation | Nothing here is implemented. `src/` and `tests/` are untouched, and `CLAUDE.md`'s known gaps are unaffected by a design proposal. |

---

## 7. Verification of this document

| check | result |
|---|---|
| Citation resolution | Every `file:line` was resolved against the tag with `git show design-01-frozen:design/<file> \| sed -n '<line>p'` before it was written, and all citations were re-resolved afterwards. None is out of range; none lands on a blank line. Citations into `design/review/` were resolved against the working-tree records, which are committed evidence. |
| Quoted frozen text | All twenty-one amendment targets were compared byte-for-byte against their frozen lines, including the two-line `C-INV-3` block and the repeated §5.1 insertion anchor. |
| Inventory coverage | §2.22 covers all 44 rows of the review's inventory, and §2.21 types every record kind named in any `required_evidence` cell of the frozen matrix. Every `M`, `U`, `C` and `W` code in the review's table is answered in the row that carries it. |
| Exhaustive claims | `R3.5`'s `AUTO`-row claim and `R13.16`'s seven-of-seventeen claim were both re-derived by enumerating the frozen matrix's `required_capability` column against the seventeen `HUMAN`-class register rows. |
| Finding coverage | Each of the five `D01-F02` findings is named by at least one amendment, and each of the twenty-one amendments names at least one. All fourteen `DESIGN-04-FINDINGS-01` findings have a disposition in §0, each pointing at the amendment and frozen line that closes it. |
| Dispositions | Severity and blocking flags are reproduced as recorded. No disposition, blocking flag or review record was changed, and no file under `design/review/` was modified. |
| Frozen text | No frozen design file, schema or implementation file was edited. Revision 01 is unchanged. No commit, tag or branch operation was performed. |
| Version terms | `SCHEMA_VERSION` appears only as the domain-model version feeding the genesis hash, with the implementation binding labelled separately (`R10.3`). `STORAGE_VERSION` and `PRAGMA user_version` appear only to say they are a different thing. |
