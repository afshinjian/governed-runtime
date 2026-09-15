# DESIGN-04 — Findings 03

Review of [DESIGN-04-baseline-correction-03.md](../DESIGN-04-baseline-correction-03.md), **952 lines, 23 amendments**, against `design-01-frozen`, peeled commit `8fd51193da0f29efb60ddf906fc845bb0dcbaeb3`. Reviewed draft SHA-256: `fef49bcf19a463f8529f54a36d0bd4786566236fefdfd6998d96bda78a04e46f`.

`D04:` means a line in revision 03. `A:`, `D:`, `E:` and `T:` mean frozen `authority-matrix.md`, `domain-model.md`, `evidence-model.md` and `transition-matrix.md`; `WP:` means frozen `worker_provider.md`. Model/interface/schema citations identify the tagged blobs. Review citations identify the existing review records. Relative links are navigation aids. Severity below is a technical assessment; **every blocking slot is reserved for the owner and left blank**.

Read order: the entire revision 03, the entire Findings 02 record, then all four frozen models. The review also checks rewritten material that previously passed, including the compressed inventory and delimitations. It does not treat either an author's CLOSED label or an earlier review's disposition as a substitute for the frozen predicates.

## 1. Four requested file:line resolutions

### 1.1 AX-19: the run-basis rule does not derive a project-grant lifetime

**The derivation does not reach.** [A:257–263](../authority-matrix.md#L257) requires the human basis record to be VALID, unexpired, nonce-unconsumed and scoped over **this run, at activation time**. It neither says that activation never consumes that basis decision nor defines the lifetime of a different, activation-independent project grant. A predicate tested before an operation does not determine the decision's state after that operation. Revision 03 now correctly limits AX-11's §5.1 admission test to run grants ([D04:260](../DESIGN-04-baseline-correction-03.md#L260)); it cannot simultaneously use that run-only test as a universal project-lifetime rule at [484/496](../DESIGN-04-baseline-correction-03.md#L484).

[T:394](../transition-matrix.md#L394) consumes a decision that discharged the transition it was recorded for. Choosing that a project grant is never recorded for any transition is a **new premise**, not something this row establishes. [A:41](../authority-matrix.md#L41) does supply generic human-grant expiry boundaries, and [T:396](../transition-matrix.md#L396) supplies VALID→EXPIRED for time/scope exit. Neither establishes the proposed one-grant, repeatedly exercised, never-consumed nonce interpretation of [D:708/718](../domain-model.md#L718) and [E:107](../evidence-model.md#L107). `R6.5` at D04:496 and its “derived, on a different basis” summary at [827](../DESIGN-04-baseline-correction-03.md#L827) repeat the run-to-project substitution previously rejected under -002, now in a lifetime argument. **New finding DESIGN-04-025.** The old AX-11 cross-reference defect itself is repaired.

Deleting the old AX-20 consumption rule removes its illegal transition, but **does not establish a complete replacement lifetime**:

| Ending condition | Frozen rule and revision-03 consumer | Resolution |
|---|---|---|
| Explicit expiry | D:701 permits an absent `expires_at`; A:41 and T:396 expire a grant/decision when its actual time or scope boundary is crossed. D04:473 checks unexpired at every act. | A grant with a time limit has a specified time end. This does not cover every allowed grant: the timestamp is optional. No consumption is needed to take EXPIRED. |
| Decision becomes STALE or VOID | D:702/719–727 and T:395/397; only VALID is authority, D:704/896. | Usability ends if the decision actually leaves VALID. A PROJECT/CAPABILITY-subject GRANT_CAPABILITY is not snapshot-bound, so ordinary snapshot change does not end that profile. The VOID row's verification-record admission is expressly deferred by §6.4. |
| Human revocation | [A:21](../authority-matrix.md#L21) requires immediate removal of permission for future operations; [D:699](../domain-model.md#L699) supplies an immutable `revokes` delta. | §5.3 steps 1–6 at D04:473–478 never subtract a later revocation. AX-19's exhaustive end list supplies no revocation condition. T:394–397 has no human-revocation transition for the original grant decision; T:270 revokes a **contract**, not this project grant. AX-10 still prohibits post-revocation use, but the new realization/liveness algorithm does not represent how it stops accepting the original VALID decision. Classification of `revokes` as AUTHORITY at E:84/A11 does not implement that operation. |
| Ceiling narrowing | D:141/153 and [D04:474](../DESIGN-04-baseline-correction-03.md#L474). | Re-intersection with the current ceiling immediately removes an excluded capability from the usable set. That part works. It does not retire the original immutable `decision.grants`, spend its nonce or change its state. The draft must distinguish temporary bounding from grant termination; otherwise later ceiling widening can make the old capability eligible again. Frozen ceiling bounds alone do not choose permanent retirement. |
| Project lifecycle termination / end of bootstrap | D:700 says only `scope = PROJECT`; A:43's explicit “project lifetime” belongs to **CEILING**, not HUMAN_DECISION. [T:99](../transition-matrix.md#L99) makes ARCHIVED terminal; [T:436/446](../transition-matrix.md#L436) denies the listed hot-path operations in terminal project states. | None defines when this decision leaves its PROJECT scope, ties its state to ABANDONED/ARCHIVED, or makes first activation the boundary for a grant described as existing for pre-activation acts (D04:326/466–469). Barring a hot-path action is not retiring authority; T:265's contract-authoring row has no corresponding project-lifetime predicate. An optional-expiry project grant therefore has no fully specified lifecycle end. |

The required repair is a **chosen** project-grant/nonce rule with explicit scope and revocation semantics, reconciled with HD-INV-3 and §7.5. Relabeling R6.5 alone is insufficient. Do not reintroduce VALID→CONSUMED without T:394's discharge, or a transition out of T:401's terminal states. Revision 02's lifecycle axiom is indeed gone; the identifier `AX-20` at [D04:485](../DESIGN-04-baseline-correction-03.md#L485) now names the former policy-grantor exclusion, not the withdrawn lifecycle.

### 1.2 Artifact envelopes contain the record; the amendment must supply admission

**An envelope does not confer admissibility on the artifact it contains. The three artifact/identity kinds remain inadmissible as direct citations. Revision 03, however, expressly chooses their persistence events as the citation targets, and that proposed rule closes this part of -020.** The question's “Amendment 20” is read as the repair of **DESIGN-04-020** in amendments 15–17 and R8.3. Actual amendment 20 at [D04:609–620](../DESIGN-04-baseline-correction-03.md#L609) is the genesis sequence reservation and has no artifact-admission rule.

The decisive addition is in [G-1, D04:511](../DESIGN-04-baseline-correction-03.md#L511): “including a persisted artifact or durable identity, cited as the event that persisted it.” [Reachability, 534](../DESIGN-04-baseline-correction-03.md#L534), and [column semantics, 556](../DESIGN-04-baseline-correction-03.md#L556) adopt the same representation. This is an explicit **chosen conversion of the citation target**, beyond a class-check exemption. The phrase “AuditEvent the row names” must be read with that express inclusion, rather than as silently excluding the case the same sentence adds.

| Frozen consumer | Record actually required | Resolution under the express proposed conversion |
|---|---|---|
| [T:305](../transition-matrix.md#L305) | ACT plus the persisted InvocationRequest as `request_ref`, with its idempotency key and controller epoch | ACT is admitted independently. The other citation names the event that persisted **that request and identity**, retaining the required bytes/key/epoch and before-call ordering. D:580 and WP:28/102/137 distinguish stored bytes from their persistence event. An unrelated event would not meet “persisted it.” |
| [T:307](../transition-matrix.md#L307) | Persisted `prompt_bundle_ref` | D:573's exact prompt bytes remain required. The proposed citation is their persisting event; it establishes durability, without changing the prompt's type or truth. |
| [T:337](../transition-matrix.md#L337) | A counter-ArtifactRef set | The persisting event(s) must cover the named counter-artifact set. The contest precondition remains, and neither the artifact nor its envelope becomes proof that the counter-assertion is true. This transition records a dispute; it does not itself establish INVALID or satisfaction. |

[E:7–9](../evidence-model.md#L7) distinguishes the byte store, event log and epistemic taxonomy; [D:787–788](../domain-model.md#L787) distinguishes the event's payload reference from the event; [E:86](../evidence-model.md#L86) calls AuditEvent an envelope. [VERIFY-01:71–80](DESIGN-01-FINDINGS-02-VERIFY-01.md#L71) and [Findings 02:76](DESIGN-04-FINDINGS-02.md#L76) remain correct: wrapping never changes the original record's type/class. Here admission comes from the **new G-1 clause and amended column semantics**, not from the frozen envelope definition. The artifacts stay outside the direct-citation set; the selected events fall inside its expressly amended prerequisite set. Frozen rules cannot derive that conversion, but they do not prevent an amendment from choosing it.

The stronger lower-seq ordering is also openly **chosen** at [D04:543/716–718](../DESIGN-04-baseline-correction-03.md#L543): E:151 alone only orders identity before the external effect. A row actually requiring an AuditEvent, such as [T:394](../transition-matrix.md#L394), and the chosen revocation/denial event representations also fit all three amended rules. No unmet persistence predicate is demonstrated for T:305/307/337 under this explicit conversion, so this review does **not** require deferring them. The conversion is limited to the named artifact/identity persistence cases; it does not readmit the expressly excluded policy/verification records. **DESIGN-04-020 remains PARTIALLY CLOSED for T:270's carry-forward/mapping residue (§3.1), not for these three converted citations.**

### 1.3 Severity and auto-resolvability: runtime ownership does not prove absence of worker influence

**A worker cannot authoritatively set either field directly, but worker-supplied values and worker-caused triggers can influence whether a human is required. A complete severity-input derivation is absent.** Thus [R13.19's D04:585](../DESIGN-04-baseline-correction-03.md#L585) “no worker assertion becomes a gate” is too broad. Its narrower statement that a worker cannot assert an authoritative `auto_resolvable` is supported.

The complete set of **specified** inputs and assignments found in the four models is:

| Destination | Specified inputs / producer | Resolution |
|---|---|---|
| Initial `Escalation.severity` | [D:738](../domain-model.md#L738): required, mutable, runtime-supplied enum. | This is **not a derived field** and has no general assignment function, trigger-to-severity table, default, or rule excluding copied reporter values from its calculation. D:44/46 distinguishes computed fields from their permitted supplier. Source R alone identifies the writer, not all upstream inputs. No direct W assignment is permitted; no general claim of input independence is proved. |
| A particular initial severity | [E:177](../evidence-model.md#L177): a monotonic-time verification failure produces INTEGRITY_VIOLATION, severity MEDIUM. | This is the one explicit fixed severity assignment. Runtime `recorded_at`/clock-skew values, D:782/792, drive it; it is not a general severity rule for every INTEGRITY_VIOLATION trigger. |
| Severity on escalation expiry/reopening | [T:415/418–419](../transition-matrix.md#L415): unresolved for the configured window; increase the preceding severity one level and reopen a new Escalation with the same trigger. | Inputs are the prior severity, lack of resolution, configured window/timer and retained trigger. Window configuration, saturation at CRITICAL, and general in-place severity changes are not defined here. This creates a specified indirect route from a worker-caused unresolved escalation to HIGH/CRITICAL. |
| `auto_resolvable` | [D:746](../domain-model.md#L746): derived, immutable, runtime-only; false if severity ≥ HIGH **or** mode SUPERVISED. | The named inputs are severity and project mode. “False if” is not an iff definition of true in all other cases. No complete additional-input/default rule is supplied. Severity is mutable while this derived field is immutable; the draft supplies no general rule reconciling later severity changes with it. Expiry creates a new entity, so that particular path can derive a new value without mutating the old one. |
| Project mode | [D:138/152](../domain-model.md#L138), [A:59](../authority-matrix.md#L59), [T:511](../transition-matrix.md#L511) | Human-supplied, with SET_MODE required for a change. Workers cannot directly choose it. SUPERVISED forces false regardless of worker behavior. |
| Human-resolution consumers | [A:142](../authority-matrix.md#L142), [T:128/158/195](../transition-matrix.md#L128), [T:414/510](../transition-matrix.md#L414), [E:108](../evidence-model.md#L108) | Non-auto-resolvability routes work to decision/suspension and forbids runtime resolution without a HumanDecision. T:171 has its separate unclosed DEC-currency problem. Holder bindings/status select the relevant escalation; `required_decision_kinds` at D:745 selects acceptable human resolutions, not a missing severity formula. |

All fifteen trigger definitions at D:757–771 were traced, including upstream inputs rather than just the `src` column:

| Trigger(s) | Worker-value or worker-action path, and limit |
|---|---|
| CONTRACT_AMBIGUITY | Contract criteria/verifier references and extra escalation triggers admit H/W input, D:324/332/343–347. C-INV-1, D:371–372, independently prevents activation with an unbound mandatory criterion. Worker input is possible; it does not waive that gate or specify the resulting severity. |
| CAPABILITY_DENIED; SCOPE_BREACH_ATTEMPT | Worker ToolCall arguments or mutation/read targets can attempt a missing capability or out-of-scope path (WP:31/75/91; D:103–109/601–602). Runtime enforcement creates the denial/attempt record; the worker need not be allowed to perform the forbidden effect. D:758–759 requires an actual failed condition, not a claimed one. |
| BUDGET_EXHAUSTED; DEADLINE_EXCEEDED; REPEATED_FAILURE | Worker activity can consume measured usage, fail attempts, or leave a run nonterminal until its deadline (D:84–86/214–215/284–287/596; D:760–762). The usage, attempt count and clock are runtime measurements, not accepted self-reported counters. T:412's comparison-trigger record gap remains separately unclosed. |
| VALIDATION_UNAVAILABLE; NONDETERMINISM | Required specs/commands and determinism declarations can originate in H/W contract content (D:325/354–359). At execution the runtime materializes the pinned command (D:432); WP:90 forbids the provider altering it. Actual execution failure/divergent receipts, not an asserted failure, fire D:763–764. |
| BLOCKER_FINDING | Worker review/finding proposals are permitted by A:120/123/208–210. Runtime Finding severity/status and the human-sourced blocking threshold feed `blocks_satisfaction` (D:368/546/552–553), which fires D:765. There is no formula equating Finding.severity to Escalation.severity; the enums even differ. Do not invent one. |
| DECLARED_OBSERVED_CONFLICT | A direct W/X/H `declared_status` value (D:203) combined with measured dissatisfaction requires an escalation (D:254–256/766; E:211/216–218). This is an explicit worker-assertion-to-trigger path even though the resulting trigger field is R-owned. Its tension with G-6/T:505 predates this revision; the amendment cannot cite unchanged G-3 or the bare Claim rule as a proof that this indirect influence is absent. |
| REALITY_DRIFT; INTEGRITY_VIOLATION | Actual unattributed workspace changes, changed contract bytes, or attempted forged records can be caused by a misbehaving worker and detected by the runtime (D:767/770; D:821; T:492–499). Such effects are prohibited, not authorized worker powers. The E:177 clock case has a different, runtime-only input. |
| ROADMAP_DIVERGED | D:768 reads adapter reports. No direct worker-supplied value is specified for that report; adapter input is a distinct external source. Calling the adapter or causing a fetch is not proof that the worker supplies its returned drift value. |
| POLICY_CONFLICT | D:769 requires conflicting applicable policy verdicts. The policy is human-authored/digest-pinned (A:32). Worker attempts can select the situation being evaluated; WP:92 also explicitly raises POLICY_CONFLICT for divergence between **provider-reported usage** and the kernel measurement. No general severity assignment follows from either path. |
| RECOVERY_AMBIGUITY | D:771 reads provider/repository reconciliation results. A provider that cannot answer lookup can cause this path (WP:103/161); a plain worker Claim is not a lookup result or repository observation. The runtime must actually fail to establish the outcome. |

Workers can also request escalation through the resolved `escalation.raise` capability ([A:141/216](../authority-matrix.md#L141)); the role default is still bounded by A:241–248 and T:412 still requires a fired trigger. This does not grant them `escalation.resolve` or a way to forge a human decision.

One concrete indirect path is **worker-caused denial → recorded CAPABILITY_DENIED escalation → no resolution within the configured window → reopened escalation with increased severity → severity ≥ HIGH → auto_resolvable false → human required** (A:293; D:758; T:412/415/418–419; D:746; T:510). The missing general initial-severity rule does not erase the specified severity-increase rule. Whether any particular instance expires rather than resolving depends on those guards; this is not a claim that every worker request forces a human immediately.

**What is and is not established:** runtime ownership blocks direct field forgery; it does not block causal worker influence through legitimate triggers, and no complete proof excludes worker reports from the unspecified severity calculation. This can be an intentional stop/require-human route. It is not proof that a worker can set auto_resolvable true, bypass T:510, or make a criterion MET. Amendment 18 must state that limited boundary honestly, and either specify the missing trusted derivation or carry it as unclosed instead of using R13.19 as a complete safety proof. **New finding DESIGN-04-026.** The literal control-field omission in old -021 is repaired.

### 1.4 The two new amendments and all their authority consumers

#### Amendment 22 — authority trace, E:282

**It introduces a chosen export representation, but omits the decision.record exception.** [D04:662](../DESIGN-04-baseline-correction-03.md#L662) enumerates run grant, project grant, per-act decision and kernel holding. [D04:178/426](../DESIGN-04-baseline-correction-03.md#L178) expressly makes `decision.record` an exception to requiring any of those four forms, and [D04:132/158](../DESIGN-04-baseline-correction-03.md#L132) requires its `authority_ref` to be absent. It therefore has neither an authorizing decision to export nor an activation nor a KERNEL holding. The newly legal first decision at T:393 still has no case in this export. **New finding DESIGN-04-027; old -017 is only partially closed.**

| Consumer or constraint checked | Result |
|---|---|
| E:282's “for one action”; D:789–790; E:176 as amended by A1; AX-1/A15 at D04:178/426 | Four ordinary cases agree with the authority audit. The authenticated-human self-held decision.record case is missing. Add its principal/authentication provenance and explicit absence of a prior authority reference; do not substitute the decision being created as its own authorization. |
| Run grant-chain consumers: A:22/248/263–265; D:394–395/411–417; [T:515](../transition-matrix.md#L515) | A22 retains activation plus grant chain for this form. Per-capability basis coverage and admissible grantor checks remain; a form-specific export does not excuse an unattributed run grant. |
| Project/per-act consumers: A7/A13/A14; D:888/896; A:289 | Exporting a HumanDecision is representable under G-2, but cannot cure the project lifetime defect or make a non-VALID decision present authority. Audit must resolve authority at the action's recorded time (A1), not require historical grants to remain live at export time. |
| Kernel cases: A:18/34; mode/policy cells T:50–61 | Kernel holding is a valid representation. It does not replace an independently required CONFIRM/DECIDE policy check merely because the capability is KERNEL. Common mode/policy-digest fields remain. |
| Other export artifacts and integrity: E:280–286, D:795–798, E:173–175/187–190 | The chain manifest, stage evidence bundle **and claim ledger** remain; export persistence and AuditEvent emission remain required. R13.21 at D04:669 incorrectly says “other two” exports: E:283 is a third. There is no authority-trace schema in the frozen empty events.schema.json supplying the omitted exception. |

This is new material, not a derivation from optional `authority_ref`: it replaces a universally required activation/grant-chain export with different content according to the authority used. Its **chosen** label is correct.

#### Amendment 23 — A-INV-2, D:410

**The proposed execution/governance distinction is sound, and is new normative scope. Its propagation is incomplete inside the draft.** [D04:682–686](../DESIGN-04-baseline-correction-03.md#L682) preserves activation as the source of the run's execution sets and permits separately authorized governance of the run. [T:208](../transition-matrix.md#L208) requires HUMAN `stage.reject` for a run transition; [A:221](../authority-matrix.md#L221) excludes it from every worker role. That is the concrete consumer motivating the distinction.

| Consumer family checked | Resolution under A23 |
|---|---|
| Grant realization/resolution: A:14–15/22/239–277; D:380–381/392–395/408–417; E:83/95/109/111 | Run execution still comes only from activation and its per-capability basis. Project grants/per-act holdings do not satisfy a run-set membership test. A:251's empty-set “run can do nothing” is an execution statement, consistent with separately authorized governance and kernel operations. |
| Immutable propagation: D:273/276/293–294/576; A:249/285–287; T:190/266/305–306/500 | Invocation grants must remain subsets of the frozen effective set; A23 adds no capability and permits no in-place widening. Scope/tool checks remain independently required. |
| Governance of an existing run: T:195/206–210 and A13 steps 1–9 | T:208 obtains its HUMAN holding per act. Neighboring KERNEL run transitions keep kernel holdings and their own DEC/evidence/policy checks. Neither “outside governance” nor an export creates a new legal transition. |
| Execution/composition and illegal consumers: T:25–39/427–448/464–467/492–524 | Axis gates, startup restrictions, recovery barriers and illegal execution remain. T:465's “every action illegal” is scoped by its READY→RUNNING execution example, not a prohibition on recording decisions or governing that run. |
| Provider/adapter and schema consumers: WP:15/28/30/91/110–125/133/180; roadmap_adapter:84–94; stage_contract.schema.json:145–174/247/477–484 | Actual request/invocation membership and worker exclusions remain. A per-act decision supplies no worker grant and does not satisfy a schema request predicate. The separate HUMAN secret/egress/arbitrary-command admission gaps remain §6.4 work. |
| Internal uses of A-INV-2 | **Not reconciled.** [R13.8, D04:292](../DESIGN-04-baseline-correction-03.md#L292) still says the frozen invariant is “literally true” and “needs no amendment.” More seriously, [AX-18, D04:483](../DESIGN-04-baseline-correction-03.md#L483) is proposed normative text saying it “holds unchanged” and repeating the unqualified authority-on-a-run wording. Both conflict with A23 and must refer to its new execution scope. |

The distinction does **not** introduce HUMAN execution grants, new fields or a new event/capability type. It does introduce a chosen narrowing of the former unqualified invariant. [R13.22, D04:693](../DESIGN-04-baseline-correction-03.md#L693) correctly marks that selection chosen in its basis, but its rule cell says the *frozen* wording already covers only execution, and [§4:845](../DESIGN-04-baseline-correction-03.md#L845) lists all of R13.22 as derived. Those statements need the same split. **Old -017 retains the scope-propagation residue; new label defect DESIGN-04-028.**

## 2. Requested edits: exact landing checks

| Requested repair | Location checked | Result |
|---|---|---|
| -015 in amendment 4 | [D04:199](../DESIGN-04-baseline-correction-03.md#L199), replacing A:292 | **Lands:** explicitly admits possession under AX-1's named decision.record exception. |
| -015 in amendment 5 | [D04:219](../DESIGN-04-baseline-correction-03.md#L219), replacing T:49 | **Lands independently:** same named exception is present. The first recording at T:393 passes both possession definitions under the chosen AX-15 holding. A22's later export omission is a separate defect. |
| -016 non-KERNEL scope | [D04:426](../DESIGN-04-baseline-correction-03.md#L426) | **Lands:** “No other non-KERNEL capability” preserves A:18/34's kernel self-holdings. D04:771 agrees. |
| -019, amendment 16 | [D04:534/542](../DESIGN-04-baseline-correction-03.md#L534) | **Deleted:** CLAIM is assigned to Escalation only; no policy/verification assignment survives. |
| -019, R13.17 | [D04:15/839–842](../DESIGN-04-baseline-correction-03.md#L839) | **Withdrawn:** no operative R13.17 rule or basis row remains. References identify its withdrawal. |
| -019, §2.21 | [D04:710](../DESIGN-04-baseline-correction-03.md#L710) | **Deleted and excluded:** both record kinds are inadmissible/unclosed. Mention of the old CLAIM assignment is expressly negative/history. |
| -019, §2.22 | [D04:740](../DESIGN-04-baseline-correction-03.md#L740) | **Deleted:** verification/policy operands have “no admissible kind”; valid alternative branches do not close them. |
| -019, §3 | [D04:786](../DESIGN-04-baseline-correction-03.md#L786) | **Deleted:** no such record is typed; cells remain unclosed. |
| -019, §6 | [D04:921/932–933](../DESIGN-04-baseline-correction-03.md#L921) | **Deleted:** withdrawal is explicit and exact policy/verification cells are carried. No affirmative normative CLAIM typing remains in any of the six locations. |
| AX-11 form-scoped admission | [D04:239/260](../DESIGN-04-baseline-correction-03.md#L239) | **Lands:** §5.1 for run grants, §5.3 for project grants; StageContract ownership of request/role is accurately stated against D:328–329. |

## 3. Carry-forward audit and compression regressions

### 3.1 Are all NOT CLOSED items actually in §6.4?

**No: the acknowledged T:270 operand is missing, and the forty-of-44 claim closes it by counting it.** [D04:738](../DESIGN-04-baseline-correction-03.md#L738) says its triggering record is typed only when already a G-1 kind and otherwise is not closed, pointing to §6.4. Yet [743–747](../DESIGN-04-baseline-correction-03.md#L743) lists only T:161/170/174/171 as exceptions, and [§6.4:932–938](../DESIGN-04-baseline-correction-03.md#L932) has no T:270 entry. [Findings 02:128](DESIGN-04-FINDINGS-02.md#L128) had already identified that alternative. A policy change, scope breach or integrity trigger at [T:270](../transition-matrix.md#L270) is not necessarily an admitted record, and calling the condition a precondition does not erase its record cell. This is a surviving -008/-020 mapping residue with a contradictory compressed summary.

| Unclosed item | Carry-forward and cross-document closure check |
|---|---|
| Policy records, T:157/170 | D04:710/740/932 consistently exclude them. T:170's DEC alternative is explicitly only an alternative. No affirmative CLAIM assignment or individual row-closure assertion survives. |
| Verification records, T:161/167/174/175/397 | D04:710/740/933 retain all five. T:161's ESC alternative is distinguished; T:174's DEC conjunct cannot replace verification. No individual closure elsewhere. |
| T:171 resolution decisions | D04:741/792/922/934 consistently withdraw historical validity and retain present VALID. The **auto-resolved/withdrawn case with no resolution DEC** also needs explicit retention: T:414/416 may supply no decision, while T:171 still prints the DEC cell. The whole row is carried, so this omission does not silently close that case, but §6.4 currently explains only consumed decisions. |
| T:412 comparison triggers | D04:711/935 retain the distinct triggering-record obligation for D:761/762 comparisons. A denial-event example does not close those comparisons. |
| T:270 triggering-record alternatives | **Not carried**, despite D04:738's explicit §6.4 reference. The four-row exception count contradicts it. Add the unresolved alternatives, including recordless conditions that cannot discharge a printed record operand. |
| T:305/307/337 artifact/identity operands | Their admissibility is **closed by the explicit chosen persistence-event conversion**, D04:511/534/556/716–717/736/753, subject to preserving the exact operands as §1.2 explains. They need not be carried merely because the underlying artifacts remain inadmissible as direct citations. |
| Six HUMAN operations without rows | D04:888/890–895/936 carry policy.override, commit.publish, audit.redact, secret.read, net.egress.any and proc.exec.arbitrary. D04:427/798's actor attribution supplies no admission/consumption procedure. No full closure of those six is asserted. |
| Four project governance writes | D04:859/864/885–887/937 assign rows to DESIGN-03. D04:881's “close in DESIGN-03” is prospective, subject to §5's required revision; it is not a claim that this proposal has implemented them. Run budget.extend still has D01-F02-008. |
| Role-table C/D tension | D04:437/777/938 retain A:203/206 versus A:221 without using it as a grant escape. |
| D01-F02-007/008/009/010 | §6.4:927–928 carries all four by identifier; §1.4:99–113 states their remaining work. D04:731/733/734/782/789/792 preserve the specific immutable-budget, supersession, recovery-closure and CR-expansion obstructions. None is declared repaired by typing. |
| Implementation | D04:939/951 explicitly says unimplemented/untouched. No implementation closure is claimed. |

The global D01-F02-004 closure language at D04:67/70/949 must be read as the targeted activation/decision/escalation/event repair, not total admission of every matrix operand: §0:32 expressly chooses the delimitation branch. That delimitation is legitimate only when its inventory and §6.4 are accurate. They currently omit T:270. Even before resolving the CLAIM-provenance question, **39 of the 44 rows have end-to-end typing without the identified operand qualifications**, rather than forty: T:270 joins the four named exceptions. This count accepts the express persistence-event conversion for T:305.

### 3.2 Previously correct material that was rewritten or compressed

All inherited amendment quotations were compared across revisions, and all 23 quotations were checked against the tag. The proposed blocks for amendments **1–3, 8–12 and 19–21 are byte-identical to revision 02**. The following checks cover the revised explanations and compressed sections as well as changed operative blocks:

| Area / old correct result | Revision-03 check |
|---|---|
| A1/A2 audit/reference guard; -012 | D04:132/158/165 preserve capability-conditioned authority checking and optionality for events carrying no capability. A4/A5's added root exception is consistent. |
| A9 denial destination; -003 | D04:305/312–313/479 retains the explicit AUTHORITY denial event and per-capability reason vocabulary. The denial is not itself a successful exercise of the denied capability. D04:27 corrects the worked-case name to R13.10. |
| Four-event witness; -004 | D04:428/447–449 retains snapshot 0, recorded approval 1, creation 2, consumption 3, one transaction, final head 3, and the D01-F02-006 refutation. R13.15 explicitly says the snapshot **entity**, not event ID, is subject_snapshot_id. The shorthand inside AX-17 is resolved by that qualifier. No qualifier was compressed out here. |
| Per-citation and per-alternative typing; -005 | D04:511/534/556/730–741 preserves ACT+SNAP, RVW+ESC, and heterogeneous alternatives. T:173/338/414 remain alternatives, not whole-cell class assignments. The new persistence-event conversion is an additional chosen representation, not an evidence-class promotion. |
| Waivers; -006 | D04:511/520/733 preserves WAIVED versus MET against D:246/E:204/210. Shortfalls require their own waivers; remaining receipts and T:139's SNAP remain. T:209's unconditional DEC cell is not erased by its precondition alternative. |
| Conditional recording SNAP; -010 | D04:369/376–378 and 731 preserve the iff field rule, informed-decision requirements, and independent consumer SNAPs. PROJECT ABANDON/GRANT_CAPABILITY are distinguished from STAGE ABANDON and kind-bound APPROVE. -023 is repaired. |
| Prior chosen/derived repairs; -011/-024 | D04:247/313/376/448–449/834–840 retain the split/conditional corrections. R6.5 introduces a new unsupported derivation; R13.22 introduces a new summary mismatch (§5 below). |
| Append shape/genesis; -013 | D04:598/620/641/649 retains all three append cells, zero reservation and genesis predecessor, with transaction-local initialization and no external-effect atomicity claim. |
| Initial ceiling; -014 | D04:899–912 retains an expressly chosen nonempty initial ceiling, bounding-not-granting, and a later setter only conditional on an empty initial ceiling. The premise itself remains sound; the project-grant lifetime is separate. |
| §2.21/§2.22 compressed mapping | Exactly 44 distinct original inventory rows are still listed. Twelve ESC evidence consumers are correctly counted. Policy/verification and T:171 withdrawals are preserved. T:270 is lost from the exception summary. The artifact/event distinction now has an express chosen conversion in all three rules. |
| §3 untouched list | D04:769–798 retains reference integrity, worker/run sets, minting restrictions, current decisions, waiver semantics, axis gates, immutable-budget and recovery limits. It correctly removes E:282/D:410 from “untouched,” but the obsolete A-INV-2 assertions survive elsewhere at D04:292/483. |
| §5 DESIGN-03 consequences | D04:859–865 retains required governance transition rows, explicit empty deltas, performer/on_behalf_of attribution, evidence_shown/payload predicates/atomicity, AUTO's separate decision requirement and final event_seq 3. D04:862's claim that the replacement standing-grant rule needs no carve-out inherits §1.1's unsupported lifetime argument. |
| §6 HUMAN closure | D04:431/878–895 consistently limits claimed coverage to seven capabilities/eighteen rows, with decision.record admitted by its separate AX-15 exception, and keeps the other ten without a passing procedure. The six nongovernance gaps are not closed by naming an authority form. |

## 4. Disposition of the twenty-four earlier findings

These are dispositions of the **named defects**, not a claim that every combined operation is executable. A withdrawn faulty transition can be closed as that defect while its replacement creates a new finding. All blocking slots remain blank.

| id | disposition | file:line resolution / remaining boundary | blocking (owner reserved) |
|---|---|---|---|
| DESIGN-04-001 | PARTIALLY CLOSED | D04:199/219/426 repair both root holding checks and kernel scope. New A22 omits the root trace case; A23 still conflicts with D04:292/483. -017 residue remains. | |
| DESIGN-04-002 | CLOSED | D04:239/260 explicitly fixes project-specific role/request and form-specific admissibility against A:15/22/263 and D:328–329. The new lifetime substitution is -025. | |
| DESIGN-04-003 | CLOSED | D04:305/479 supplies A:293's denial destination. Admission of a later citation is a different check. | |
| DESIGN-04-004 | CLOSED | D04:428/449 preserves the four events and correct snapshot entity reference, conditional on the chosen authority recipe. | |
| DESIGN-04-005 | CLOSED | D04:511/534/556 retains conjunct/alternative typing; no whole-cell class equality returns. | |
| DESIGN-04-006 | CLOSED | D04:511/520 retains E:204/210's WAIVED route without calling it measured MET. | |
| DESIGN-04-007 | PARTIALLY CLOSED | D04:577 names the actual control fields, but D04:585's assurance about worker assertions is unsupported by upstream/derived-input analysis; -026. | |
| DESIGN-04-008 | PARTIALLY CLOSED | Delimitation is an acceptable branch, but D04:738/743 and §6.4 disagree on T:270. T:305/307/337 now have an express chosen persistence-event conversion. | |
| DESIGN-04-009 | CLOSED | D04:431/890–895 limits D01-F02-003 closure and retains the six operations with no procedure. | |
| DESIGN-04-010 | CLOSED | D04:369/377 conditions only decision recording's SNAP and preserves stage-subject binding. | |
| DESIGN-04-011 | CLOSED for its original enumerated defects | Original actor/profile/ceiling/representation choices stay disclosed; successor R6.5 and new R13.22 defects are -025/-028. | |
| DESIGN-04-012 | CLOSED | D04:158 explicitly guards the biconditional by capability_used. | |
| DESIGN-04-013 | CLOSED | D04:641 keeps E:136's third cell. | |
| DESIGN-04-014 | CLOSED | D04:899–912 keeps the nonempty ceiling chosen and the setter dependency conditional. | |
| DESIGN-04-015 | CLOSED | Both D04:199 and 219 admit AX-1's decision.record exception. The new export omission is -027. | |
| DESIGN-04-016 | CLOSED | D04:426's non-KERNEL qualification preserves A:18/34. | |
| DESIGN-04-017 | PARTIALLY CLOSED | A22 updates four forms but omits the named root exception; A23 states execution scope while D04:292/483 retain the unqualified old interpretation. | |
| DESIGN-04-018 | CLOSED by withdrawal of the offending rule | Old end-of-grant VALID→CONSUMED is removed. D04:484/496's replacement lifetime still needs -025; withdrawal is not proof of that replacement. | |
| DESIGN-04-019 | CLOSED | All six locations remove affirmative policy/verification CLAIM typing; D04:932–933 carries the exact cells. | |
| DESIGN-04-020 | PARTIALLY CLOSED | D04:511/534/556 expressly supply the chosen persistence-event conversion and common event kind. T:412 comparisons are carried, but T:270's residual branch is omitted from §6.4 and contradicted by the count. | |
| DESIGN-04-021 | CLOSED as the literal field-boundary repair | D04:577/732 names trigger, status, severity, auto_resolvable and bindings; T:132's trigger is correctly in-cell. Input trust/causal influence is the new -026. | |
| DESIGN-04-022 | CLOSED by withdrawal; underlying row NOT CLOSED | D04:741/792/922/934 withdraw historical DEC validity and carry T:171. Include the no-DEC auto/withdrawal branch in the later record as well. | |
| DESIGN-04-023 | CLOSED | D04:377/731 correctly distinguishes STAGE from PROJECT ABANDON, D:702. | |
| DESIGN-04-024 | CLOSED for its enumerated repairs | D04:247/313/376/448–449/834–840 correct the old labels, and counts are twelve ESC/four remaining columns. New R13.22 summary defect is -028. | |

## 5. Chosen/derived audit — new and rewritten rules only

The draft's own convention at D04:804–808 is applied: frozen consequence is derived; an amendment choice is chosen; a consequence depending on a choice is conditional. Unchanged old labels are not reopened.

| New/rewritten rule | Ruling |
|---|---|
| A4/A5 root-exception additions; A13 AX-15 scope | Chosen propagation of the existing selected holding, consistent with R13.3/R3.8. The non-KERNEL qualification preserves an independently frozen holding. Neither adds another authority form. |
| A6/R6.4 and A7's admission clause | Project-specific non-application of the role table depends on the chosen project-grant form; conditional is appropriate. A:190 does not by itself narrow AX-4. A7's destination/admission split remains chosen under R13.6. |
| R13.5, D04:247 | Correct split: ceiling derived from D:141/153; applying this mode gate in the new resolution chosen. |
| R13.10, D04:313 | Correct conditional: needs the selected intersection and denial destination; D:393 gives only the vocabulary. |
| R13.11–13, D04:376–378 | Correct: choosing the row to repair is chosen; the PROJECT/STAGE/kind profiles themselves follow D:702. Consumer SNAPs remain separate. |
| R13.14–15, D04:448–449 | Conditional label and lower-seq versus authority_ref qualification are correct. One residual support error: **changing the approval kind alone does not change the four-event count**, contrary to D04:448. T:84 still requires SNAP, and the chosen recording/creation/consumption history still has its three further events under T:393/394 and D:789/797. Removing approval/consumption would be a different premise. |
| R6.5/AX-19, D04:484/496/827 | **Not derived.** A:263 is an activation-time run-basis test, not a project lifetime or a post-activation no-consumption theorem. The new project nonce/scope lifetime must be chosen and completed; -025. |
| A15–17/R8.3/§2.21, D04:511/534/543/556/713–718 | Correctly labels representation and stronger ordering choices as chosen. E:151 derives before-effect durability, not a separate earlier event before PENDING. G-1 now expressly supplies the citation-target conversion; it must not be described as the frozen envelope carrying the artifact's admissibility (§1.2). |
| R13.18, D04:584 | Derived need to amend the CLAIM gate remains supported by E:62/85 and the twelve ESC evidence rows. Corrected count is twelve. |
| R13.19, D04:585 | Chosen permission is labeled correctly. Its argument from R ownership to no worker-assertion gate is not derived or proved; -026. |
| R13.21/A22, D04:662/669 | Chosen export representation is correctly labeled; omitted exception is -027. E:283 also disproves “other two export artifacts.” |
| R13.22/A23, D04:682–693/845 | The frozen conflict motivates a distinction, but selecting this execution-only scope is chosen. §4 must list the split, and the rule cell must not say frozen D:410 already has that scope. **-028.** |
| R13.17 | Withdrawn, with no replacement classification for excluded policy/verification records. Historical mentions do not constitute normative typing. |

## 6. Independent citation re-verification

The draft contains **597 Markdown file:line link occurrences, 250 distinct frozen file:line targets, and seven distinct review-record targets**. Frozen targets split as **authority 58, domain 60, evidence 38, transition 90, adapter 4**. All targets are in range and nonblank. All **23** current-frozen-text blocks match their tagged text byte for byte, including the two-line invariant and both repeated insertion anchors. These mechanical checks establish location/quotation accuracy, not the truth of the claim citing them.

The following sample contains **68 distinct members of those 250 frozen targets**. Each was read with its surrounding rules and checked semantically against the identified revision-03 occurrence. The full trigger, consumer and inventory reviews above are additional coverage.

| # | Draft occurrence | Frozen citation | Independent resolution |
|---|---|---|---|
| 1 | D04:169 | A:12 | Default DENY requires the explicit new forms/exception; optional citations alone do not authorize. |
| 2 | D04:230 | A:15 | Frozen intersection is unqualified; A6 deliberately splits its run/project domains. |
| 3 | D04:770 | A:16 | Human grantor exception is ceiling-bounded; a per-act empty-delta exercise grants nothing. |
| 4 | D04:40 | A:18 | Kernel-only holding survives the corrected non-KERNEL prohibition. |
| 5 | D04:27 | A:19 | Frozen denial destination is activation-only; A9 supplies the explicit project/per-act event destination. |
| 6 | D04:26 | A:22 | Admissibility and basis destination are separate requirements; revised A7 now changes both for project grants. |
| 7 | D04:40 | A:34 | Kernel is a principal and can self-hold KERNEL only; human-authorized runtime performance is different. |
| 8 | D04:496 | A:41 | Generic time/scope/state expiry does not specify revocation representation or PROJECT lifecycle boundary. |
| 9 | D04:436 | A:51 | HUMAN needs an exercise-time decision; selecting grantless possession remains a choice. |
| 10 | D04:492 | A:74 | roadmap.import is ORD with human/policy grantors; it does not itself define project realization. |
| 11 | D04:492 | A:86 | contract.author is ORD with human/policy grantors; initial realization is chosen by A14. |
| 12 | D04:246 | A:190 | Table is per WorkerInvocation; StageContract still owns the request/role fields. |
| 13 | D04:919 | A:216 | escalation.raise has a G cell for every role, still subject to resolution. |
| 14 | D04:437 | A:221 | HUMAN denied to all roles; A23 cannot turn outside governance into a worker grant. |
| 15 | D04:42 | A:263 | Requires live unconsumed human basis **at activation for this run**; no project/post-use lifetime follows. |
| 16 | D04:25 | A:292 | Possession is a separate enforcement point; amendment 4 now includes the root exception. |
| 17 | D04:447 | D:38 | Reference integrity does not force earlier independent commits; deferred transaction checks remain compatible. |
| 18 | D04:446 | D:60 | on_behalf_of exists with depth ≤2; using it for the performer is an explicit choice. |
| 19 | D04:607 | D:134 | schema_version means domain-model version; no implementation constant is specified. |
| 20 | D04:247 | D:141 | Ceiling is required, human-supplied, and bounds grants; there is no empty default. |
| 21 | D04:247 | D:153 | All project grants are bounded, including new project grants; re-intersection does not retire a nonce. |
| 22 | D04:26 | D:328 | capability_request is a StageContract field and a request, not a grant. |
| 23 | D04:26 | D:329 | worker_role also exists on StageContract; the revised project-specific explanation is accurate. |
| 24 | D04:41 | D:410 | Frozen exclusivity is unqualified; A23 narrows it, contradicting retained D04:292/483 assurances. |
| 25 | D04:312 | D:698 | grants is immutable and can be nonempty; bounding/use must not silently mutate it. |
| 26 | D04:312 | D:699 | revokes is an independent immutable delta; classification does not implement a project-revocation consumer. |
| 27 | D04:47 | D:702 | Snapshot binding is by subject OR kind; STAGE ABANDON remains bound. |
| 28 | D04:376 | D:703 | subject_snapshot_id refers to a RealitySnapshot iff bound, not an event ID. |
| 29 | D04:585 | D:738 | Escalation.severity is mutable and R-supplied, with no general derivation in its note. |
| 30 | D04:585 | D:746 | HIGH/CRITICAL or SUPERVISED forces false; no iff/true branch or full input policy is stated. |
| 31 | D04:141 | D:790 | authority_ref admits activation/decision or absence; A1 supplies when those representations suffice. |
| 32 | D04:502 | D:887 | Original allow-list is over entities; the narrowed rule must explicitly admit each prerequisite kind. |
| 33 | D04:568 | E:62 | CLAIM originally never gates; the control-field exception is a substantive choice. |
| 34 | D04:710 | E:63 | EVIDENCE has producer/minting restrictions; failing them does not derive CLAIM for an unnamed record. |
| 35 | D04:445 | E:82 | HumanDecision is DECISION; empty deltas do not make it an activation grant. |
| 36 | D04:542 | E:83 | Activation is AUTHORITY; per-kind reachability fixes its old class conflict. |
| 37 | D04:356 | E:84 | Both grants and revokes are AUTHORITY deltas; no lifetime/operation is defined by classification. |
| 38 | D04:542 | E:85 | Escalation is runtime CLAIM; that does not classify policy/verification records. |
| 39 | D04:518 | E:86 | AuditEvent contains a class; it does not change a payload's entity type or inherit its admissibility. |
| 40 | D04:142 | E:95 | Baseline realizes grants through activation; A11 changes that source rule. |
| 41 | D04:79 | E:127 | Genesis fixes zero and predecessor formula, not installation of initial project/head state. |
| 42 | D04:589 | E:128 | Atomic head update exists; A19 adds project installation and initialization. |
| 43 | D04:77 | E:135 | Ordinary reservation reads prior event_seq; A20 supplies the missing empty-chain branch. |
| 44 | D04:78 | E:136 | Ordinary predecessor reads event_head; A21 adds genesis fallback and keeps failure handling. |
| 45 | D04:543 | E:151 | Durable identity precedes external effect; a distinct earlier-than-PENDING event is an extra choice. |
| 46 | D04:449 | E:178 | Lower seq applies to required_evidence, not every authority_ref; original class test was EVIDENCE. |
| 47 | D04:30 | E:204 | Unexpired WAIVE/ACCEPT_RISK decisions are the satisfaction function's waiver input. |
| 48 | D04:41 | E:282 | Original action trace requires activation/grant chain; A22's new four cases omit decision.record. |
| 49 | D04:547 | T:48 | Original column is current receipts/snapshots; A17 explicitly changes its domain. |
| 50 | D04:25 | T:49 | Actor must hold the capability independently of evidence/policy; A5 now includes the exception. |
| 51 | D04:46 | T:74 | DEC is informed and VALID at the current transition; past validity cannot discharge it. |
| 52 | D04:440 | T:84 | Creation requires SNAP independently of the chosen approval kind; AUTO does not remove HUMAN-class requirements. |
| 53 | D04:440 | T:97 | Abandoned-project archive is AUTO with no evidence cell; chosen APPROVE still imposes decision snapshot binding. |
| 54 | D04:45 | T:132 | Trigger selection is inside required_evidence; A18 now names that field explicitly. |
| 55 | D04:731 | T:142 | This is STAGE abandonment; the PROJECT-subject exception does not apply. |
| 56 | D04:740 | T:161 | Verification or RECOVERY_AMBIGUITY ESC; admitting the alternative does not close verification. |
| 57 | D04:740 | T:170 | Policy re-evaluation or OVERRIDE; the policy-record branch remains excluded. |
| 58 | D04:741 | T:171 | Required resolution DEC is separate from AUTO policy; consumed and absent resolution-decision cases remain. |
| 59 | D04:740 | T:174 | Verification plus OVERRIDE is conjunctive; the decision cannot replace verification. |
| 60 | D04:41 | T:208 | HUMAN stage.reject governs a run transition; no worker activation grant can supply it. |
| 61 | D04:738 | T:270 | A triggering record is an independent disjunct; unresolved kinds/recordless triggers need explicit carry-forward. |
| 62 | D04:44 | T:305 | ACT plus persisted request/identity; A15–17 expressly choose the exact identity's persistence event, not a direct artifact citation. |
| 63 | D04:44 | T:307 | Operand is persisted prompt_bundle_ref; amended column semantics selects its persisting event without changing the prompt's type. |
| 64 | D04:44 | T:337 | Operand is a counter-ArtifactRef set; selected persistence events establish durability, not the counter-assertion's truth. |
| 65 | D04:39 | T:393 | Recording is its own capability-bearing transition; A12 repairs only its unconditional SNAP cell. |
| 66 | D04:42 | T:394 | Consumption requires an actual discharged transition and its event; it does not derive project non-consumption. |
| 67 | D04:42 | T:396 | Time/scope exit admits VALID→EXPIRED; it does not define the chosen project's scope boundary. |
| 68 | D04:42 | T:401 | Terminal decisions cannot be revived or subsequently consumed; the removed AX-20 violated this. |

## 7. New findings in revision 03

Four new entries continue the existing sequence. The surviving T:270 mapping/carry-forward and A-INV-2 propagation defects remain under -008/-017/-020 above; they are not counted again as new discoveries.

| id | severity | blocking (owner reserved) | draft location | finding and required correction |
|---|---|---|---|---|
| DESIGN-04-025 | MAJOR | | D04:484/496/774/784/796/827/862/920 | **Replacement project-grant lifetime is claimed derived from a run-only, activation-time predicate and leaves endings incomplete.** A:263 proves neither lifetime non-consumption nor project scope. A:21 requires immediate revocation, D:701 permits no time limit, and T:394–397 supplies no project-revocation or explicit project-lifetime boundary. Specify a chosen coherent nonce/lifetime rule with per-act revocation and scope checks, distinguishing ceiling bounding from retirement; reconcile HD-INV-3 and §7.5. |
| DESIGN-04-026 | MAJOR | | D04:577/585/732/785 | **The CLAIM control-field safety argument stops at the runtime writer and misses upstream worker influence.** D:738 has no general severity derivation; D:746 has a partial false-condition rule. D:203/254–256/758–766, WP:92 and T:415/418–419 give direct worker-value or worker-caused trigger paths to a human-required escalation. Explicitly permit and delimit that stop/require-human influence; do not assert no worker assertion gates. Specify or defer the missing severity/auto-resolvability derivation without claiming it proved. No human-bypass or evidence-forgery exploit is established here. |
| DESIGN-04-027 | MAJOR | | D04:662/669 | **The new authority trace omits AX-1's non-form decision.record exception.** A22 covers the four forms; D04:178/426 exempts recording from them and A1/A2 require absent authority_ref. Add the authenticated-human self-held trace case, without inventing a prior authorizing decision. |
| DESIGN-04-028 | MINOR | | D04:693/845; supporting errors at448/669 | **The new A-INV-2 scope choice is again summarized as a frozen derivation.** Keep R13.22's motivated distinction separate from the chosen narrowing in both rule and summary. Also remove the unsupported claim that a different decision kind alone changes the four-event count, and count E:283's claim ledger among the other export artifacts. |

## 8. Is revision 03 freezable with NOT CLOSED items carried to a later corrective record?

**No, as written.** Deferring the identified frozen gaps is compatible with freezing a bounded corrective record. Revision 03 still introduces an unsupported project lifetime, omits a newly legal authority case from its new export, retains contradictory normative A-INV-2 wording, overstates its CLAIM input boundary, and claims coverage its own inventory contradicts. Carry-forward cannot make those current assertions correct.

The smallest coherent repair set is:

1. **Complete and label the chosen project-grant lifetime** in AX-19/R6.5 and its summaries. Define what consumes/realizes the one grant, how future use checks revocation, how PROJECT/bootstrap scope ends without an expires_at, and whether ceiling removal merely bounds or retires a capability. Preserve legal decision-state transitions and single-use/no-replay semantics, amending the relevant rule explicitly if the choice changes it. Merely renaming the current derivation “chosen” leaves the ending gaps. An alternative deferral must withdraw this new lifetime and the associated D01-F02-005 closure claim, not freeze “never consumed” as proved.
2. **Complete the existing delimitation branch.** Carry **T:270's unresolved triggering-record alternatives** into §6.4 and correct the forty-of-44 count/claims to reflect that fifth qualified row. Retain both consumed-DEC and absent-DEC cases at T:171. Preserve A15–17's explicit chosen artifact-to-persistence-event conversion and its exact-operand requirement; no general artifact allowance or policy/verification widening is needed.
3. **Correct the CLAIM boundary claim.** State that worker reports/actions may trigger measured stop/require-human controls, while asserted success cannot become evidence and workers cannot author authoritative control values or human decisions. Remove the unsupported input-independence assurance. Specify the trusted severity/auto-resolvability inputs if claiming them closed; otherwise carry the incomplete derivation and its field-update boundary to §6.4, with the existing HIGH/SUPERVISED false rule and human-resolution prohibition retained. Do not silently declare the inherited G-6/provider-stage-path tensions repaired.
4. **Finish both new authority consumers.** Add decision.record's authenticated-human trace case to A22. Rewrite R13.8 and normative AX-18 to reference **A23's amended execution scope**, removing the statements that frozen A-INV-2 is already literally preserved or needs no amendment. This requires no new worker capability or field.
5. **Synchronize dispositions, labels and supporting counts** with those repairs: R6.5 chosen/conditional as warranted; R13.22 split in both locations; T:270 mapping closure qualified; the four-event kind assertion and export count corrected. Keep all owner blocking slots untouched.

The existing policy/verification-record cells, comparison-trigger records, six HUMAN procedures, four DESIGN-03 governance rows, role-table tension and D01-F02-007/008/009/010 can remain later-record work when they are consistently described as such. Freezing this reviewable correction would not make those operations executable or make the proposal implemented.

## 9. Validation and workspace boundary

Read all four frozen models in full: A 293 lines, D 896, E 286, T 524; read both frozen interfaces and relevant schema constraints. Rechecked all 44 inventory rows and adjacent operands; independently enumerated **143 legal transition rows, seventeen HUMAN register entries, eighteen HUMAN transition consumers across seven capabilities, three HUMAN rows with an AUTO verdict, and twelve ESC evidence consumers**. Checked all 250 frozen citation targets, semantically re-verified the 68-item sample, and compared all 23 quotations to the tag. A separate read-only review checked compression, carry-forward and rewritten labels; its conclusions were checked against the cited text.

These are specification checks, not runtime conformance tests. Only this new findings record was written. No draft, frozen model, previous review, implementation or other pre-existing workspace file was edited. No commit, tag, branch or index mutation was made. All blocking slots remain blank for the owner.
