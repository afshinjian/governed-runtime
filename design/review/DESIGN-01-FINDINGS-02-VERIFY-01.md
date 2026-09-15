# DESIGN-01-FINDINGS-02-VERIFY-01

Reviewed specification: `design-01-frozen`, peeled commit `8fd51193da0f29efb60ddf906fc845bb0dcbaeb3`, 2026-09-15.

Scope: independently verify all ten findings in [DESIGN-01-FINDINGS-02.md](DESIGN-01-FINDINGS-02.md), including a fresh verification of D01-F02-001. The reviewed findings were an untracked file at the start of this review; working-tree `HEAD` was `e2904aabf5a9692937d73cfe3e957f7f7ce221bd`. The specification was read from the frozen Git blobs, not inferred from implementation or subsequent amendments. All specification `file:line` references below identify those frozen blobs; relative links locate the documents.

**Result: 8 CONFIRMED, 1 PARTIALLY CONFIRMED, 1 REFUTED.** These are specification findings, not observed runtime failures. D01-F02-002 retains a bootstrap-description gap, but its claimed necessary exposure of dangling references is not established. D01-F02-006's independent reference-ordering impossibility is refuted by a transaction containing ordered appends. D01-F02-009 repeats an already-recorded F01-003 residue.

**Comparison baseline correction.** [FINDINGS-01.md:1](FINDINGS-01.md#L1) identifies its reviewed baseline as `c0cb238c97b54ffe47acb8a469659f518bc16794`, not `8fd5119`. The later tag contains that historical review unchanged, plus remediation and closure records. The comparison below distinguishes the original seven descriptions from their subsequent F01 closure history; it does not apply their old specification line numbers to the later tag.

| Finding | Disposition | Verified result |
|---|---|---|
| D01-F02-001 | **CONFIRMED** | The universal live-grant audit check cannot represent kernel self-holdings; project creation also has no admissible grant path. |
| D01-F02-002 | **PARTIALLY CONFIRMED** | First-append initialization is not specified by the ordinary append algorithm. However, lower event sequence does not require an earlier transaction commit; the claimed referential-integrity impossibility does not follow. |
| D01-F02-003 | **CONFIRMED** | None of the four lifecycle capabilities survives activation's role intersection. Later activation records can exist, but cannot supply those grants. |
| D01-F02-004 | **CONFIRMED** | Mandatory activation, decision, escalation and audit-envelope evidence conflicts with the closed entity allow-list and, for the first three, event classification. |
| D01-F02-005 | **CONFIRMED** | Initial import and first contract creation require activation authority before the stage/contract/run structure supporting that authority has been established. |
| D01-F02-006 | **REFUTED** | Mutually referencing activation/run records can be inserted with deferred reference checks, ordered events and one commit. The separate ACT admissibility failure remains D01-F02-004. |
| D01-F02-007 | **CONFIRMED** | Neither of the two transitions needed to supersede the active predecessor can go first. Revocation permits replacement activation but cannot produce predecessor status `SUPERSEDED`. |
| D01-F02-008 | **CONFIRMED** | The same exhausted run cannot acquire headroom or a later deadline through the permitted evolution of its immutable allocation/deadline and monotonic usage. |
| D01-F02-009 | **CONFIRMED** | Direct post-reconciliation dispatch/apply is admitted by the run gate and rejected by the closure predicate. This does not mean every possible recovery sequence is blocked. |
| D01-F02-010 | **CONFIRMED** | Literal expansion of `CR` requires `MATCHED`; the divergent recovery row additionally requires `DIVERGED` for the same receipt. |

**Verification method.**

For each claim, unrelated defects are held aside, as the findings themselves stipulate. Otherwise D01-F02-001 would make every later example vacuous. In particular, the persistence analysis of D01-F02-006 temporarily sets aside D01-F02-004's independently impossible evidence-class requirement. A counterexample here addresses the claimed independent obstruction, not the conformance of the entire unrepaired runtime.

The review distinguishes event order, logical transition preconditions and transaction visibility. A reference constraint does not by itself say that its target must have committed in an earlier transaction. Conversely, batching transitions does not authorize false lifecycle preconditions, retrospective capability grants, changes to immutable fields or replacement of an explicitly defined evidence token.

**D01-F02-001 — CONFIRMED: the audit rule excludes the kernel authority the design separately recognizes.**

The proof does not depend on DESIGN-03's proposed changes or its earlier review:

1. `AX-2` and `G-4` require a capability for each state-changing operation ([authority-matrix.md:13](../authority-matrix.md#L13), [domain-model.md:890](../domain-model.md#L890)). `AuditEvent.capability_used` is required for state-changing events, and every matrix transition must emit an event before becoming observable ([domain-model.md:789](../domain-model.md#L789), [domain-model.md:797](../domain-model.md#L797)).
2. The verifier requires each such event's `authority_ref` to resolve to a live grant ([evidence-model.md:176](../evidence-model.md#L176)). The permitted reference targets are an activation or a decision ([domain-model.md:790](../domain-model.md#L790), [domain-model.md:888](../domain-model.md#L888)).
3. The kernel holds `KERNEL` capabilities separately, non-delegably, but they are removed from activation grants and expressly never appear in `granted_capabilities` ([authority-matrix.md:18](../authority-matrix.md#L18), [authority-matrix.md:34](../authority-matrix.md#L34), [authority-matrix.md:245](../authority-matrix.md#L245), [authority-matrix.md:266](../authority-matrix.md#L266)). A decision cannot supply the missing alternative: its grant is realized only through activation ([evidence-model.md:95](../evidence-model.md#L95)).

Thus a state-changing `run.start`, `contract.activate` or `commit.apply` event has no conforming live-grant citation. Omitting the optional `authority_ref` does not evade a check conditioned on `capability_used`. Citing kernel self-holding would require an authority representation the allowed reference types do not provide.

Project creation independently needs `project.create` on the `∅ → DRAFT` row ([transition-matrix.md:84](../transition-matrix.md#L84)). It is HUMAN-class and has no admissible role grant ([authority-matrix.md:58](../authority-matrix.md#L58), [authority-matrix.md:221](../authority-matrix.md#L221)); neither `created_by = HUMAN` nor `AUTO` creates one. A different project's activation remains scoped to its own run. This argument survives the transactional qualification of D01-F02-002: preparing related records atomically cannot make `project.create` survive the grant algorithm.

The verifier therefore reports the stated integrity failure. The creation event need not be event zero; its required snapshot must have a lower sequence. This confirms the substance of DESIGN-03-021 independently, including the corrected event-order qualification in the reviewed finding.

**D01-F02-002 — PARTIALLY CONFIRMED: bootstrap is underspecified; a mandatory visibility conflict is not proved.**

The finding correctly identifies all three obligations: creation requires a complete `SNAP` ([transition-matrix.md:68](../transition-matrix.md#L68), [transition-matrix.md:84](../transition-matrix.md#L84)); its evidence event must have lower `seq` ([evidence-model.md:178](../evidence-model.md#L178)); and the snapshot/event reference the project ([domain-model.md:38](../domain-model.md#L38), [domain-model.md:778](../domain-model.md#L778), [domain-model.md:805](../domain-model.md#L805)).

The unsupported step is that appending the earlier event necessarily commits and exposes it separately. The protocol requires event/head atomicity and prohibits observation before persistence ([evidence-model.md:138](../evidence-model.md#L138), [evidence-model.md:139](../evidence-model.md#L139)). It does not require one independently committed transaction per event, prohibit reading a transaction's own writes, or require foreign keys to be checked after each individual insertion. Its explicit atomicity exclusion concerns effects outside the store ([evidence-model.md:143](../evidence-model.md#L143)). Serial appends under one project lock remain serial when committed together.

A countersequence to the claimed necessary exposure is:

1. Allocate the project identifier and prepare its prospective DRAFT record privately. Observe the existing workspace and prepare the complete snapshot and payload.
2. Under the project lock, begin a store transaction. Insert the prospective project and snapshot; append the snapshot event at `seq = 0` with the specified genesis predecessor ([evidence-model.md:127](../evidence-model.md#L127)). Initialize the transaction-local sequence/head from that event.
3. Append the creation event at `seq = 1`, citing the snapshot event. Read the previous head from the same transaction and advance it with the new event.
4. Validate the complete reference graph and commit the project, snapshot, both events and final head atomically. Readers see the new project only with its creation event already present; failure exposes none of the transaction.

There is no intermediate published project state or dangling committed reference. Evidence has the required earlier sequence even though both events become durable together. `AE-INV-2` is preserved: publication follows emission/persistence of the creation event. This is an implementation refinement of the stated store guarantees, not a claim that the frozen document spells out this recipe.

What remains unprovided is an explicit empty-chain initialization procedure. Ordinary append step 2 reads `event_seq + 1`, and step 3 reads `event_head`, although those derived fields have no prior event in a new project ([evidence-model.md:135](../evidence-model.md#L135), [evidence-model.md:136](../evidence-model.md#L136), [domain-model.md:145](../domain-model.md#L145)). The separate genesis rule specifies event zero but does not describe installing its initial project/head state. Retain that narrower specification gap; do not retain the stronger assertion that no transaction can satisfy reference integrity and ordered evidence. The same reasoning means the per-event-visibility premise from DESIGN-03-019 is not accepted here as an axiom.

**D01-F02-003 — CONFIRMED: a decision and a capability grant are separate requirements.**

The four capabilities are HUMAN-class, and activation intersects against the worker-role table before admitting grantors. Each is denied to every role; `D` cannot be overridden ([authority-matrix.md:61](../authority-matrix.md#L61), [authority-matrix.md:78](../authority-matrix.md#L78), [authority-matrix.md:194](../authority-matrix.md#L194), [authority-matrix.md:221](../authority-matrix.md#L221), [authority-matrix.md:244](../authority-matrix.md#L244)). Although that table is explicitly a worker table, the frozen design routes realized grants through this activation machinery: `AX-3` scopes them to a run, and decision-to-authority promotion is activation-only ([authority-matrix.md:14](../authority-matrix.md#L14), [evidence-model.md:95](../evidence-model.md#L95)).

A direct human decision is the strongest attempted escape. It is admissible as an authority-reference type, but no rule makes it an activation-independent grant. The HUMAN class requires a decision at exercise time as well as grant time, while the matrix separately requires capability possession ([authority-matrix.md:51](../authority-matrix.md#L51), [transition-matrix.md:49](../transition-matrix.md#L49)). `DECIDE(K)` therefore does not repair missing possession.

The full inventory was rechecked: four `project.abandon` rows, two `project.archive` rows, seven `stage.abandon` rows and two `stage.reject` rows, including run rejection at [transition-matrix.md:208](../transition-matrix.md#L208). The finding correctly rejects the universal timing premise: rejection after execution and archival after completion can have existing activation records. They simply cannot contain the needed grants. The same grant-path problem supports the additional cited HUMAN operations, including `decision.record`, `finding.waive`, unrestricted egress, publication and redaction. It does not depend on the audit failure in D01-F02-001.

**D01-F02-004 — CONFIRMED: literal required-evidence cells cannot be moved into other columns by interpretation.**

The decisive check is the intersection of the required record type with `G-1`'s closed allow-list, followed by the verifier's EVIDENCE-class requirement ([domain-model.md:887](../domain-model.md#L887), [evidence-model.md:178](../evidence-model.md#L178)):

| Mandatory record | Example frozen consumer | Obstruction |
|---|---|---|
| `ContractActivationRecord` / `ACT` | Run allocation and contract activation ([transition-matrix.md:189](../transition-matrix.md#L189), [transition-matrix.md:266](../transition-matrix.md#L266)) | Not in `G-1`; classified AUTHORITY ([evidence-model.md:83](../evidence-model.md#L83)). |
| `HumanDecision` / `DEC(REJECT)` | Stage rejection ([transition-matrix.md:141](../transition-matrix.md#L141)) | Not in `G-1`; decision/grant components are DECISION/AUTHORITY, neither EVIDENCE ([evidence-model.md:82](../evidence-model.md#L82), [evidence-model.md:84](../evidence-model.md#L84)). |
| `Escalation` / `ESC(OPEN)` | Entry to AWAITING_DECISION ([transition-matrix.md:128](../transition-matrix.md#L128)) | Not in `G-1`; classified CLAIM ([evidence-model.md:85](../evidence-model.md#L85)). |
| `AuditEvent` | Decision consumption ([transition-matrix.md:394](../transition-matrix.md#L394)) | The envelope entity itself is outside `G-1`, even if a particular envelope carries EVIDENCE. |

The taxonomy does allow decisions and authority to gate through their respective policy/capability mechanisms ([evidence-model.md:64](../evidence-model.md#L64), [evidence-model.md:65](../evidence-model.md#L65)). Those mechanisms do not remove a separate mandatory `required_evidence` cell. Nor does attaching a snapshot or wrapping a governance record in an event change the type/class of the required governance record. No generic governance attestation among the five allowed entities is specified. The contradiction remains after authority, reference integrity and ordering are granted.

**D01-F02-005 — CONFIRMED: the ordinary-capability bootstrap remains circular.**

Initial import requires `roadmap.import` both for project advancement and stage materialization; creating the first draft contract requires `contract.author` ([transition-matrix.md:85](../transition-matrix.md#L85), [transition-matrix.md:117](../transition-matrix.md#L117), [transition-matrix.md:265](../transition-matrix.md#L265)). Their named grantors are human or policy, not ROLE_DEFAULT ([authority-matrix.md:74](../authority-matrix.md#L74), [authority-matrix.md:86](../authority-matrix.md#L86)).

The grant algorithm starts from a contract's request and freezes its result into a run ([authority-matrix.md:241](../authority-matrix.md#L241), [authority-matrix.md:249](../authority-matrix.md#L249)). That machinery relies on the stage/contract/run structure whose first creation is being authorized: contracts reference stages; activations bind contracts and runs ([domain-model.md:316](../domain-model.md#L316), [domain-model.md:388](../domain-model.md#L388), [domain-model.md:390](../domain-model.md#L390)). A request or an authored payload is not already a realized grant.

The attempted startup routes do not close the loop:

- A human can supply contract content, but that does not waive `contract.author` or turn a decision into a grant outside activation.
- PLANNER's `G`/`C` cells only bound these two capabilities, because the register does not name ROLE_DEFAULT for them ([authority-matrix.md:271](../authority-matrix.md#L271)).
- An autonomous policy evaluation supplies grant provenance at activation; it is not a project-scope grant/exercise procedure.
- Adapter `fetch` and `normalize` already require `roadmap.import`; the first-import mapping provides no bootstrap exception ([roadmap_adapter.md:56](../roadmap_adapter.md#L56), [roadmap_adapter.md:57](../roadmap_adapter.md#L57), [roadmap_adapter.md:102](../roadmap_adapter.md#L102)).
- An invocation in another run does not confer authority on this initially unestablished project/run. Initial worker dispatch is also forbidden during DRAFT/PLANNING ([transition-matrix.md:435](../transition-matrix.md#L435)).

Grouping database writes cannot retroactively authorize the first protected import/authoring act. Unlike D01-F02-006's reference checks, this is a missing capability at the protected operation, not merely a choice of when to validate mutually referencing rows. The claim remains supported independently of project creation and the audit verifier.

**D01-F02-006 — REFUTED: earlier event order does not require separately committed mutually referencing entities.**

The required references and one-to-one relation are real ([domain-model.md:273](../domain-model.md#L273), [domain-model.md:390](../domain-model.md#L390), [domain-model.md:865](../domain-model.md#L865)). The allocation row also requires an already valid ACT ([transition-matrix.md:189](../transition-matrix.md#L189)). What the frozen text does not require is that an activation's foreign-key check complete in an earlier transaction than the run's insertion.

A sequence satisfying the claimed independent persistence constraints is:

1. Start with an existing project, current snapshot and the needed stage/contract prerequisites. Reserve distinct run and activation identifiers. Hold the project's append lock throughout one store transaction.
2. Insert the activation with `run_id = R`, deferring that reference check until transaction commit. Append its event at `n + 1` and update the transaction-local head.
3. Perform any required contract-activation transition before allocation. Insert R in ALLOCATED with `activation_id = A`; A now exists in the transaction and satisfies the allocation guard. Append the allocation event at a higher sequence, reading the transaction's updated head.
4. Check both references and the one-to-one relation, then commit the records, individually ordered events and final head together. Rollback publishes neither record.

The activation precedes allocation in event order; both references resolve when published. The run has only its legal ALLOCATED state, not an invented provisional lifecycle. No identifier is treated as a committed entity before commit. Deferred integrity checks still enforce integrity; the frozen `Ref<E>` definition does not prescribe immediate checking after each insert. Event/head writes remain atomic and appends remain serialized.

An in-memory transactional probe exercised this mutual-reference sequence and confirmed a valid committed graph and lower activation-event sequence. The probe intentionally did not claim to satisfy D01-F02-004: an AUTHORITY event is still inadmissible as ACT evidence under the unmodified global verifier. That is the separate defect the finding itself asks to set aside. Once it is set aside, the reference cycle does not establish another impossible operation. Unlike project genesis, this sequence starts with an existing sequence/head and needs no empty-chain initialization.

**D01-F02-007 — CONFIRMED: supersession has a logical guard cycle.**

Let P be ACTIVE and its same-stage successor S be DRAFT, with no live run and all unrelated requirements satisfied. The successor's stage/version relation is fixed by XC-11 ([stage_contract.schema.json:493](../schema/stage_contract.schema.json#L493)).

- S cannot become ACTIVE while P remains ACTIVE: the activation row requires no other ACTIVE contract ([transition-matrix.md:266](../transition-matrix.md#L266)).
- P cannot become SUPERSEDED while S remains DRAFT: its row requires that successor to have reached ACTIVE ([transition-matrix.md:269](../transition-matrix.md#L269)).
- P can first become REVOKED, EXPIRED or FULFILLED where the corresponding guard holds. S may then activate, but P is terminal and has no route to SUPERSEDED ([transition-matrix.md:273](../transition-matrix.md#L273)).

The last route is a conforming replacement sequence; it does **not** perform the specified supersession operation. This limits the finding to its stated target: reaching predecessor status SUPERSEDED through that successor, rather than all possible installation of replacement contracts.

A transaction does not fix the cycle: evaluating both guards before either transition leaves each false; evaluating them sequentially still has no first transition. This differs from deferred foreign-key validation, which does not assert that a lifecycle transition has already happened. A permissive two-contract state search, allowing every unrelated revocation/expiry/fulfillment prerequisite, reached 17 states and no predecessor SUPERSEDED state. It did reach REVOKED/ACTIVE, verifying the narrower replacement escape above.

**D01-F02-008 — CONFIRMED: extension is impossible for the same exhausted run.**

Suspension clearing is evaluated per holder and requires headroom in every budget dimension ([transition-matrix.md:151](../transition-matrix.md#L151), [transition-matrix.md:172](../transition-matrix.md#L172)). For a run, the relevant allocation is immutable and usage is append-only ([domain-model.md:284](../domain-model.md#L284), [domain-model.md:285](../domain-model.md#L285), [domain-model.md:84](../domain-model.md#L84)).

Take one dimension with allocation 10 and usage 10. Every allowed future allocation remains 10; every allowed future usage is at least 10. The required inequality, usage < allocation, therefore cannot become true. Replacing a Budget value is also a write to immutable `budget_allocated`; it does not evade the containing field's mutability rule.

Raising `Project.budget` changes a different field. Starting a new run gives a different holder. Neither clears this run's budget suspension. The mismatch is express, because `budget.extend` promises to raise a ceiling on a live run ([authority-matrix.md:66](../authority-matrix.md#L66)).

The deadline case is independent: the rework row asks for a deadline extension when needed, while `StageRun.deadline_at` is immutable ([transition-matrix.md:206](../transition-matrix.md#L206), [domain-model.md:287](../domain-model.md#L287)). No extension record or alternative effective-deadline formula is specified. Rework with existing headroom and an unexpired deadline can proceed; the finding correctly concerns exhausted/expired instances requiring an actual extension. Its stage-rework consequence is conditional on reusing that exhausted run, not proof that every stage retry is impossible.

**D01-F02-009 — CONFIRMED: the verifier rejects the directly permitted resumption; some other sequences can progress.**

Use an ACTIVE project, RUNNING stage and WORKING run with budget/deadline headroom, no suspension and one old PROPOSED intent. A scan finds no token and an unchanged base. The recovery row leaves `status = PROPOSED` and establishes `reconciliation_state = ORPHANED` ([transition-matrix.md:359](../transition-matrix.md#L359), [transition-matrix.md:371](../transition-matrix.md#L371)). Other old operations have already been reconciled.

The run gate now permits creating and dispatching an invocation ([transition-matrix.md:219](../transition-matrix.md#L219), [transition-matrix.md:305](../transition-matrix.md#L305), [transition-matrix.md:307](../transition-matrix.md#L307), [transition-matrix.md:427](../transition-matrix.md#L427)). The closure check still forbids an old nonterminal operation preceding that dispatch ([evidence-model.md:167](../evidence-model.md#L167)). PROPOSED remains explicitly nonterminal; ORPHANED is a terminal reconciliation result, not a terminal operation status ([transition-matrix.md:244](../transition-matrix.md#L244), [transition-matrix.md:246](../transition-matrix.md#L246)). The old epoch is immutable ([domain-model.md:638](../domain-model.md#L638)).

A genuine alternative was checked: if a policy prohibition applies to that PROPOSED intent, it may become DENIED under [transition-matrix.md:350](../transition-matrix.md#L350), after which a later dispatch no longer encounters that old nonterminal intent. This refutes any expansion of the finding into “no post-recovery execution can ever occur.” It does not reconcile the two rules for the specific directly permitted dispatch above.

The old AUTHORIZED case is stronger: no DENIED transition leaves AUTHORIZED, and its route toward a terminal operation status begins with APPLYING under `commit.apply` ([transition-matrix.md:351](../transition-matrix.md#L351)). That is itself the apply initiation rejected by the old-operation closure predicate. Changing the epoch or substituting another run is not resumption of the same operation/run.

This discrepancy was already demonstrated under **F01-003** in [MICRO-VERIFY-01.md:53](MICRO-VERIFY-01.md#L53), following the coverage concern in [CLOSURE-01.md:28](CLOSURE-01.md#L28). The claim is substantively confirmed and is not a new independent discovery.

**D01-F02-010 — CONFIRMED: the frozen shorthand produces an empty evidence predicate.**

The shorthand is an expansion, not a stated default: `CR = CommitReceipt with verification = MATCHED` ([transition-matrix.md:73](../transition-matrix.md#L73)). The divergent reconciliation row requires `CR with verification = DIVERGED` ([transition-matrix.md:358](../transition-matrix.md#L358)). Literal substitution requires one receipt satisfying both equalities. `verification` is one immutable derived value from the closed enum MATCHED/DIVERGED ([domain-model.md:657](../domain-model.md#L657)); the conjunction is empty.

The intended failure-preserving outcome is clear from the adjacent prose ([transition-matrix.md:366](../transition-matrix.md#L366)). Reading the explicit DIVERGED qualifier as overriding the shorthand would implement that intent, but the frozen token definition contains no override rule. It would relax one of the two printed predicates rather than exhibit a receipt satisfying both.

Two receipts do not solve a conjunction on one required receipt, and the intent-to-receipt relation is at most one ([domain-model.md:875](../domain-model.md#L875)). Falsifying MATCHED or changing the expected digest violates the derived comparison and immutable intent field. The ordinary failure row uses `CommitReceipt` directly, but it is under `commit.apply`; it cannot substitute for the recovery row while the unreconciled-operation gate applies ([transition-matrix.md:353](../transition-matrix.md#L353), [transition-matrix.md:516](../transition-matrix.md#L516)).

This verifies the literal defect, with ESC admissibility held aside. It also qualifies the earlier assertion that divergent adoption passes in [MICRO-VERIFY-01.md:49](MICRO-VERIFY-01.md#L49): that assertion followed the intended outcome without checking the CR expansion. This verification does not edit or silently revise the historical record.

**Comparison with FINDINGS-01 and its closure history.**

A shared subject area is not sufficient to call two findings duplicates. The relevant test is whether the same violated rule and counterexample were already recorded. All ten are accounted for below.

| D01-F02 finding | F01 relationship | Restatement or new substance? |
|---|---|---|
| 001 | Related to F01-001's authority topic. | **Not a restatement.** F01-001 concerned granting ORD authority without its required grantor. This concerns a verifier rejecting required kernel/human acts despite the separate kernel-holding model. The repaired all-capability grantor check does not fix it. |
| 002 | Shares startup consequences with F01-006. | **Not a restatement.** F01-006's startup cycle was READY requiring ACTIVE while ACTIVE required READY. Project genesis, event order and reference-check timing were not that finding. Only the narrower initialization gap is retained here. |
| 003 | Shares authority machinery with F01-001. | **Not a restatement.** The original described an excessive grant; this describes HUMAN capabilities with no realizable exercise grant. |
| 004 | **Structural overlap with F01-007:** required transition records excluded by G-1 and the epistemic taxonomy. | **New instances of the same defect pattern, not a restatement of the original Review-specific finding.** F01-007 identified judgmental Review consumers; 004 identifies activation, decision, escalation and AuditEvent consumers. Adding ReviewAttestation addressed different records. The overlap should be explicit; these consumers were not enumerated by F01-007. |
| 005 | Related to F01-006's startup liveness and F01-001's grant provenance. | **Not a restatement.** It identifies a capability bootstrap cycle, not the former project/stage or stage/dispatch guard cycles. The frozen startup exception and first-dispatch exception do not supply import/authoring authority ([transition-matrix.md:108](../transition-matrix.md#L108), [transition-matrix.md:432](../transition-matrix.md#L432)). |
| 006 | Shares run-start consequences with F01-006. | **Not a restatement, and independently refuted here.** The alleged mutually referencing creation cycle is different from the former CONTRACTED/dispatch composition cycle. No new persistence defect is established once batching is considered. |
| 007 | Related to F01-005's contract-transition topic. | **Not a restatement.** F01-005 was the status/hash preimage contradiction, repaired by excluding status. The mutually unsatisfied successor/predecessor guards remain even with a stable hash ([domain-model.md:373](../domain-model.md#L373)). |
| 008 | F01's bounded-loop answer mentions budgets, but no F01 finding identifies this extension contradiction. | **New substance.** Enforcing a finite budget and representing an authorized extension of a live run are different requirements. |
| 009 | **F01-003 residue**, also within the recovery work shared with F01-002. | **Restates an already-recorded F01-003 issue; do not count as a new defect.** The exact old-intent/ORPHANED/later-dispatch contradiction is in MICRO-VERIFY-01:53. It is a continuation of the original landed-commit recovery finding, not the original pre-remediation example verbatim. |
| 010 | Overlaps F01-003's failure-preserving commit recovery subject. | **New specific contradiction in that recovery machinery, not a restatement of the original missing-recovery protocol.** The CR/MATCHED/DIVERGED conflict was not stated in FINDINGS-01; MICRO-VERIFY-01 actually treated this branch as passing. It adds a missed predicate defect to that history. |

Thus **009 is the exact repeat within the maintained F01 review lineage**. **004 extends F01-007's forbidden/required-evidence pattern to additional record types**. The startup, authority and contract-status similarities elsewhere do not make those findings restatements. Strictly comparing only the seven original descriptions in FINDINGS-01, none states 009's later, remediation-era counterexample verbatim; attributing it to F01-003 requires the closure history preserved in the same frozen tag.

**Validation.**

Read all four frozen models in full: authority 293 lines, domain 896, transition 524 and evidence 286. Consulted the frozen adapter/provider capability provisions, contract schema constraints, and F01 remediation/closure history; independently rechecked DESIGN-03-021's substance against the frozen text. The four models, related interfaces/schemas, FINDINGS-01 and MICRO-VERIFY-01 in the working tree were byte-identical to the cited frozen versions.

Read-only Python probes parsed the contract schema and checked XC-11/12/13, confirmed the event schema is empty, enumerated all fifteen HUMAN lifecycle rows, exercised an in-memory transactional reference/order countermodel, searched the two-contract guard graph, and checked the CR predicate and the recovery gate/closure distinction. These are bounded checks of specification arguments, not runtime conformance tests. The transactional probe demonstrates reference/ordering feasibility; the interpretation of the append protocol is explained above and is not proved by a database accepting the transaction.

Only this verification Markdown file was created. The reviewed findings file and all existing repository files were left unchanged. No implementation tests, commits or tags were made. No owner blocking flags or historical dispositions were changed.

