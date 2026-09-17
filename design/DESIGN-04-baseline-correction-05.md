# DESIGN-04 — Baseline Correction (revision 05)

Revises [DESIGN-04-baseline-correction-04.md](DESIGN-04-baseline-correction-04.md) against
[DESIGN-04-FINDINGS-04.md](review/DESIGN-04-FINDINGS-04.md). Revisions 01, 02, 03 and 04 are
committed evidence and are unchanged — revision 04 is the SHA-256
`433869a3430937f2c150893bf672164b3ed6dfa3e2686d272d2c7cff49db2095` that `FINDINGS-04` froze —
and this document replaces them as the amendment. Where they differ, this one governs.

`FINDINGS-04` §8 records that **`design-04-frozen` does not stand as an accepted corrective
baseline** and that `design-01-frozen` remains the operative normative text. This revision
does not contest that verdict. It repairs the four proposal defects `FINDINGS-04` names —
the surviving halves of `DESIGN-04-025` and `-028`, and the new `-029`, `-030` and `-031` —
reassesses the partially closed `-020`, and synchronizes §0, §4, §6, §7 and §8 with that
review. It repairs no code: `DESIGN-04-032`…`-036` are implementation findings against
`GR-23` and this document neither fixes nor claims to fix them (§2.23).

Revision 05 was then reviewed within the open `GR-26` stage, with the verdict
**NOT_ACCEPTABLE**, and has been remediated in place against that review's three findings:
`GR26-R1` (blocking) — the repaired step 5a let an earlier revocation retire a later grant,
so `AX-19`(c)'s own restoration clause was unsatisfiable; `GR26-R2` — two already-disclosed
open debts were absent from §8's register; `GR26-R3` — this document wrongly said the owner
had not yet dispositioned `DESIGN-04-029`…`-036`. All three are repaired below, in §0, §5.3,
`AX-19`(a)/(c)/(f), `R13.26`, `R6.5`, §6.3, §6.5, §7 and §8. The `GR-26` review record is the
owner's and is not committed in this repository, so it is cited by finding identifier and
not by `file:line`; nothing in it is reproduced here as a disposition. That remediation is
the **only** change since revision 05 was reviewed, and no amendment target, no quoted frozen
text and no other proposed text moved with it.

| Property | Statement |
|---|---|
| Size | **1281 lines, 23 amendments.** Revision 04 was 1042 lines with 23 (its own front matter said 1043, which was wrong — [FINDINGS-04:62](review/DESIGN-04-FINDINGS-04.md#L62)); revision 03 was 952 with 23; revision 02 was 966 with 21. **No amendment is added, deleted or retargeted in revision 05** — the twenty-three targets and their quoted frozen text are byte-identical to revisions 03 and 04. Three **proposed** texts change, in two fenced blocks, all inside the project-grant repair: amendment 9's `AX-8` (the denial reason vocabulary, `-029`), and inside amendment 14's §5.3 insertion its ordering paragraph and step table (steps 1, 5a, 6 and 7) and `AX-19` clauses (a), (c), (e) and (f) (`-029`, `-030`, `GR26-R1`). Its `AX-18` and `AX-20` are unchanged, `AX-19`(b) and (d) are unchanged, and so are the other 44 fenced blocks (§7). Amendment 23's proposed `A-INV-2` is **unchanged**; only the `R13.22` rule cell that misdescribed it is corrected (`-028`). The growth is §2.23, the corrected `-020`/`-025`/`-028` dispositions, the three new finding rows, §6.5, `KD-14`/`KD-15`, and the `GR-26` remediation — `R13.26`'s ordering, the `-025` and owner-flag corrections in §0, two §6.3 rows, §6.5's alternatives, and `KD-16`/`KD-17`. |
| Baseline | `design-01-frozen`, peeled commit `8fd51193da0f29efb60ddf906fc845bb0dcbaeb3`. Every `file:line` citation resolves in that tag and was checked with `git show design-01-frozen:design/<file> \| sed -n '<line>p'`. |
| Kind | **Proposal, pending independent review and owner acceptance.** It is **not** frozen, is **not** the operative baseline, and nothing in it is in effect. No frozen file is edited, no schema is changed, no implementation is changed. `design-01-frozen` remains authoritative; `design-04-frozen` remains historical evidence of the tagged revision 04 and, per [FINDINGS-04:174](review/DESIGN-04-FINDINGS-04.md#L174), does not stand as an accepted corrective baseline. Every closure this document records is a **proposed** closure by its author; none is independently verified (§7). |
| Corrects | The same five findings as revisions 01–04: `D01-F02-001`, `-002` (retained half only), `-003` (partially — §6.1), `-004`, `-005`. |
| Changes in revision 04 | The five repairs of [DESIGN-04-FINDINGS-03](review/DESIGN-04-FINDINGS-03.md) §8: the project-grant lifetime completed and relabelled **chosen** at `AX-19`(a)–(f) with a new §5.3 step 5a; [transition-matrix.md:270](transition-matrix.md#L270) carried to §6.4 and the inventory count corrected to **thirty-nine of 44**; `R13.19` split into permitted worker-caused stop/require-human influence and what is actually asserted; the authority trace given `decision.record`'s self-held case (`R13.23`); dispositions, labels and counts synchronized; §8 added. |
| Changes in revision 05 | **1. `-029`, the revocation reason vocabulary.** Amendment 9 no longer pins the denial `AuditEvent`'s reason vocabulary to [domain-model.md:393](domain-model.md#L393)'s closed `denied_capabilities` enum. It states the vocabulary the denial event itself carries — that enum's seven values **plus `REVOKED`**, for the two formless denials only — as this amendment's own **choice**, with `denied_capabilities` and its frozen enum untouched (`R13.24`). **2. `-030`, the grant subject.** §5.3 step 1 now admits only `subject.kind ∈ {PROJECT, CAPABILITY}`, with the grant bound to the project by the decision's own `project_id` ([domain-model.md:691](domain-model.md#L691)), so [:702](domain-model.md#L702) makes the decision non-snapshot-bound and `AX-19`(e)'s exclusion of [transition-matrix.md:395](transition-matrix.md#L395) follows from the admission rule instead of being assumed (`R13.25`). Step 1 constrains `subject.id` only where the kind is `PROJECT`; the frozen model gives a `CAPABILITY` subject's `Id` no referent, and this document supplies none. Step 5a is rewritten so retirement is the **recorded historical fact**, not a filter on the revoking decision's current `decision_state` (`R13.26`, `AX-19`(c)). **3. `-028`.** `R13.22`'s rule cell no longer says the frozen wording "covers only the second"; it says the frozen wording draws no such distinction and is contradicted by [transition-matrix.md:208](transition-matrix.md#L208), which is why amendment 23 narrows it. **4. `-031`.** Every attribution of a *policy-evaluation record* to [transition-matrix.md:270](transition-matrix.md#L270) is withdrawn: that row says "the triggering record" and names no record kind, unlike [:157](transition-matrix.md#L157) and [:170](transition-matrix.md#L170). The row stays open for its actual unspecified record; the thirty-nine-of-44 count is unchanged. **5. `-020`** is recorded **PARTIALLY CLOSED**, as `FINDINGS-04` finds, with its residual mapping obligation named in `KD-3`/`KD-4` rather than absorbed into `-008`'s permitted delimitation. **6. Synchronization:** §0 gains rows for `-029`…`-031` and a statement that `-032`…`-036` are implementation findings; §2.23 states the creation witness's full predicate set for later `GR-23` conformance work; §6.5 records the alternatives the grant/lifetime repair chose among and the owner decision they present; §6.3 carries the newly withdrawn claims; §7 is restated as author verification only; §8 gains `KD-14` (inherited `CLAIM`-boundary tensions) and `KD-15` (`GR-23` conformance), and `KD-9` is rewritten. **7. The `GR-26` remediation**, made in place after this revision was reviewed NOT_ACCEPTABLE. `GR26-R1`: §5.3 gains a paragraph defining `pos`, the position of a decision's `∅ → VALID` `AuditEvent` on the project's per-project, gapless, totally ordered chain ([domain-model.md:778](domain-model.md#L778), [:779](domain-model.md#L779), [:797](domain-model.md#L797), [:877](domain-model.md#L877), [evidence-model.md:187](evidence-model.md#L187)), and step 5a retires `c` from a grant `G` only for a revocation `R` with `pos(R) > pos(G)`; `AX-19`(a), (c) and (f), `R13.26`, `R6.5`, §0's `-025` row, §6.3 and §6.5 follow it. No frozen field, entity, clock or ordering primitive is added. `GR26-R2`: §8 gains `KD-16` (the §5.2 denial-reason mapping) and `KD-17` (the `CAPABILITY`-subject referent), both already disclosed at `R13.24`/`R13.25`, both nonblocking here and neither solved here. `GR26-R3`: the false claim that `DESIGN-04-029`…`-036` have no owner disposition is withdrawn; the flags `DESIGN-04-FINDINGS-04` §6's table records are restated in §0 and §7. Owner blocking slots are untouched throughout, and no review record is edited. |
| Rule ids | Inherited from revisions 01–04 so the reviews' audits stay traceable: `R1.1` … `R12.1`, `R13.1` … `R13.20` less the withdrawn `R13.17`, plus `R13.21`, `R13.22`, `R13.23` and the new `R13.24`, `R13.25`, `R13.26`. |

## 0. Disposition of all thirty-six `DESIGN-04` findings

`DESIGN-04-FINDINGS-02` sustains nine of the first record's fourteen as closed and records
five as partially closed, then raises ten more; `DESIGN-04-FINDINGS-03` sustains sixteen of
those twenty-four as closed, records six as partially closed, two as closed by withdrawal,
and raises four more; `DESIGN-04-FINDINGS-04` sustains twenty-five of the twenty-eight as
closed, records `-020`, `-025` and `-028` as **partially closed**, and raises eight more —
`-029`…`-031` against the proposal and `-032`…`-036` against `GR-23`'s implementation.

**Every disposition in this section is a proposed closure by this document's author.** Under
the review method it is the reviewer of the revision who determines closure, and this
revision has not been reviewed. A row saying **CLOSED** here means only that this document
repairs or expressly withdraws the named finding against the frozen text it cites; it does
not mean the four normative files were amended, that an operation is executable, that a
deferred defect is solved, or that any reviewer has agreed. Where `FINDINGS-04` reached a
disposition that differs from revision 04's, **this revision adopts the review's**, not its
predecessor's. Judged against the frozen text each finding cites, not against whether the
reviewer's wording was engaged. The first twenty-four are below; `-025` to `-031` follow it,
and `-032` to `-036` follow them. Of those, the five this revision exists to repair are
`-025`, `-028`, `-029`, `-030` and `-031`: `-026` and `-027` were repaired in revision 04 and
`FINDINGS-04` sustains both as closed, so this revision sustains them and repairs nothing in
them. `-032` to `-036` are implementation findings this revision does not repair at all.

| id | disposition | what closes it |
|---|---|---|
| `-001` | **CLOSED** | Amendments 4 and 5 now admit `AX-1`'s `decision.record` exception at [authority-matrix.md:292](authority-matrix.md#L292) and [transition-matrix.md:49](transition-matrix.md#L49) (`-015`); `AX-15` is scoped (`-016`); the remaining possession consumers are amendments 22 and 23, both of which now carry that exception through — the trace's fifth case (`R13.23`) and `A-INV-2`'s amended scope (`R13.8`, `R13.22`) (`-017`, `-027`, `-028`). |
| `-002` | **CLOSED** | Amendment 7: [authority-matrix.md:22](authority-matrix.md#L22)'s admissibility clause is tested by §5.1 for a run grant and §5.3 for a project grant. Amendment 6's request/role wording is corrected against [domain-model.md:328](domain-model.md#L328)–[:329](domain-model.md#L329). |
| `-003` | **CLOSED** | Amendment 9: [authority-matrix.md:19](authority-matrix.md#L19) gains the denial `AuditEvent` destination already required at [:293](authority-matrix.md#L293). The worked case is `R13.10` (revision 02 misnamed it `R13.3`). |
| `-004` | **CLOSED** | `AX-17`'s four-event witness, with `R13.15` stating that `subject_snapshot_id` names the snapshot **recorded by** event 0, never an event id. |
| `-005` | **CLOSED** | Amendments 15–17: typing per citation and per alternative, verified row by row in §2.22. |
| `-006` | **CLOSED** | Amendment 15 preserves the `WAIVED` route ([evidence-model.md:204](evidence-model.md#L204), [:210](evidence-model.md#L210), [domain-model.md:246](domain-model.md#L246)). |
| `-007` | **CLOSED as the field boundary; the input derivation is NOT CLOSED** | Amendment 18 and `R13.19`: the `CLAIM` cell names the control fields that may gate — `trigger`, `status`, `severity`, `auto_resolvable`, holder bindings — and the asserted fields that may not. Revision 03's further assurance that no worker assertion becomes a gate is **withdrawn** (`DESIGN-04-026`): worker reports and worker actions do reach measured stop and require-human controls, which `R13.19`(i) now states and permits. What is asserted is only `R13.19`(ii). The missing severity/`auto_resolvable` derivation is carried (§6.4, §8 `KD-8`). |
| `-008` | **CLOSED on the delimitation branch** the finding itself offers ([FINDINGS-01:304](review/DESIGN-04-FINDINGS-01.md#L304)) | §2.21 maps every kind `G-1` admits, §2.22 resolves all 44 rows, and §6.4 lists the **five** rows and the record kinds that remain unclosed. No total mapping is claimed. Revision 03's residue — [transition-matrix.md:270](transition-matrix.md#L270) sent to §6.4 by §2.22 but absent from it, and counted inside the forty — was repaired in revision 04 and stands (`DESIGN-04-008` residue, §8 `KD-3`). Revision 05 removes the policy-evaluation-record attribution revision 04 attached to that carry-forward (`-031`) and changes no count. |
| `-009` | **CLOSED** | Amendment 13's closure line and §6.1 no longer say "in full"; `D01-F02-003` is partially closed in §0, §1.1, amendment 13 and §6.1. |
| `-010` | **CLOSED** | Amendment 12 (rev 02), with `R13.12` corrected so the stage rows are not covered by a project-subject argument (`-023`). |
| `-011` | **CLOSED** | §4 (rev 02), extended by this revision's label corrections (`-024`). |
| `-012` | **CLOSED** | Amendment 2's guarded biconditional (rev 02). |
| `-013` | **CLOSED** | Amendment 21 keeps the third cell (rev 02). |
| `-014` | **CLOSED** | §6.2's chosen premise (rev 02), now also naming the amendments `D01-F02-005` actually rests on. |
| `-015` | **CLOSED** | One clause each in amendments 4 and 5: possession may be held under `AX-1`'s named `decision.record` exception, so [transition-matrix.md:393](transition-matrix.md#L393) can record the first decision. |
| `-016` | **CLOSED** | `AX-15`'s final sentence is scoped to non-`KERNEL` capabilities; the kernel's own holding under [authority-matrix.md:18](authority-matrix.md#L18) and [:34](authority-matrix.md#L34) stands. |
| `-017` | **CLOSED** | Amendment 22 amends [evidence-model.md:282](evidence-model.md#L282) so the trace names whichever form was used, including `decision.record`'s self-held case (`R13.23`); amendment 23 scopes [domain-model.md:410](domain-model.md#L410) to a run's execution authority, with [transition-matrix.md:208](transition-matrix.md#L208) as the case that forces the distinction. `R13.8` and `AX-18` now reference that amended scope and no longer assert that the frozen wording is preserved. |
| `-018` | **CLOSED by withdrawal; replacement lifetime CHOSEN** | `AX-20`'s standing-grant lifecycle is deleted. `AX-19`(a)–(f) now supplies a complete replacement, **chosen and labelled as chosen** (`R6.5`, `DESIGN-04-025`): realization once with the nonce spent at realization, a per-act re-test, permanent retirement by `REVOKE_CAPABILITY` distinguished from re-testable ceiling/mode bounding, and a `PROJECT`-scope end at terminal project lifecycle. Revision 03's derivation of that lifetime from [authority-matrix.md:263](authority-matrix.md#L263) is **withdrawn**: that line is an activation-time predicate about a run grant's basis and derives no project lifetime. No row of §7.5 is amended and [:401](transition-matrix.md#L401)'s terminality is untouched, but only because (a) chose non-recording. |
| `-019` | **CLOSED** | Every `CLAIM` typing of policy and chain-verification records is deleted — amendment 16, `R13.17`, §2.21, §2.22, §3 and §6 — and those cells are stated unclosed for a later corrective record alongside `D01-F02-007`/`-008`/`-009`/`-010` (§6.4). |
| `-020` | **PARTIALLY CLOSED**, as [FINDINGS-04:44](review/DESIGN-04-FINDINGS-04.md#L44) finds; revision 04's own qualified wording is adopted as the review states it | **Closed:** the conflicting domains and the false coverage claim. `G-1`, amendment 16 and amendment 17 now admit one identical set — an evidence citation, an activation, a `HumanDecision`, an `Escalation`, or an `AuditEvent` the row names, the last covering the artifacts and identities at [transition-matrix.md:305](transition-matrix.md#L305), [:307](transition-matrix.md#L307), [:337](transition-matrix.md#L337), each cited as the event that persisted it, which is an **express conversion of the citation target** and not a property of the frozen envelope. **Not closed:** the finding's whole mapping obligation. Unlike `-008`, `-020` did **not** expressly offer delimitation as a complete repair, so carrying a row forward does not discharge it. [:270](transition-matrix.md#L270) and [:412](transition-matrix.md#L412) still lack any total triggering-record representation; both are carried at §6.4 and §8 `KD-3`/`KD-4`, which now name `-020`'s residue as well as `-008`'s ([FINDINGS-04:89](review/DESIGN-04-FINDINGS-04.md#L89), [:90](review/DESIGN-04-FINDINGS-04.md#L90)). Revision 05 adds no new mapping and claims none. |
| `-021` | **CLOSED as the literal field-boundary repair** | Amendment 18 names the gating fields; §2.22 stops calling [transition-matrix.md:132](transition-matrix.md#L132)'s trigger qualifier a precondition and treats it as the in-cell control field it is. Input trust and causal influence are a separate matter and are `-026`; see `R13.19`(i)/(ii) and §8 `KD-8`. |
| `-022` | **CLOSED by withdrawal, row retained unclosed in both cases** | The "live at that resolution" reading is deleted. [transition-matrix.md:171](transition-matrix.md#L171) needs a `DEC` that is `VALID` at the consuming transition ([:74](transition-matrix.md#L74), [authority-matrix.md:289](authority-matrix.md#L289), [transition-matrix.md:522](transition-matrix.md#L522)). **Case A:** a resolution that ran through a decision leaves it `CONSUMED` and terminal ([:394](transition-matrix.md#L394), [:401](transition-matrix.md#L401)), so no cited `DEC` can be `VALID` here. **Case B:** a resolution may have produced **no decision at all** — [:414](transition-matrix.md#L414) resolves on `auto_resolvable` with a `SNAP`/`VR(pass)`, and [:416](transition-matrix.md#L416) withdraws with no decision — while the row still prints a `DEC` cell. The row is **NOT CLOSED** in either case and both are carried to §6.4 and §8 (`KD-5`, `KD-6`). |
| `-023` | **CLOSED** | `R13.12` and §2.22 state that a `STAGE`-subject `ABANDON` is snapshot-bound ([domain-model.md:702](domain-model.md#L702)) and keeps its `SNAP`; the project-subject profile covers only [transition-matrix.md:86](transition-matrix.md#L86), [:89](transition-matrix.md#L89), [:91](transition-matrix.md#L91), [:94](transition-matrix.md#L94). |
| `-024` | **CLOSED** | §4 relabels `R13.5` (split), `R13.10`, `R13.14`, `R13.15` (conditional) and `R13.11` (chosen); `R13.17` is withdrawn; §2.21 drops the "nothing else optional" claim; the `ESC` count is twelve and the remaining semantic columns four. The new `R13.22` and `R13.21` label defects it could not have seen are `-028`. |

The findings `DESIGN-04-FINDINGS-03` raised against revision 03 and `DESIGN-04-FINDINGS-04`
raises against revision 04 are what this revision repairs. `-025` and `-028` are reopened as
the review leaves them: **partially closed**, with the remaining halves repaired here.

| id | disposition | what closes it |
|---|---|---|
| `-025` | **PROPOSED CLOSED, on the repaired rule; it was `PARTIALLY CLOSED` against revision 04** | Repair 1 of `FINDINGS-03` gave `AX-19` a complete, explicitly **chosen** lifetime at (a)–(f): realization once with the nonce spent there, a per-act re-test (§5.3 step 0), permanent retirement by a covering `REVOKE_CAPABILITY` under `AX-10` (§5.3 step 5a) held apart from re-testable ceiling/mode **bounding**, a `PROJECT`-scope end at terminal project lifecycle for the grant with no `expires_at`, `:396`/`:397` for the rest, and an exhaustiveness clause. `R6.5` is **chosen** with its "no §7.5 amendment" consequence marked conditional on clause (a); the derivation from [authority-matrix.md:263](authority-matrix.md#L263) is withdrawn in `R6.5`, §3, §4 and §6.3. [FINDINGS-04:49](review/DESIGN-04-FINDINGS-04.md#L49) sustained that as far as it went and held the finding **partially** closed for two reasons, both repaired here: the denial reason `REVOKED` had no conforming vocabulary (`-029`, `R13.24`) and the admission rule never imposed the subject profile the exhaustive end-set assumed (`-030`, `R13.25`). A third defect, inside the repaired step 5a itself, was found by the `GR-26` review of this revision and is repaired here as `GR26-R1`: the rule matched **any** recorded revocation, so on the history `G1 → R → G2` a revocation retired the capability from a grant recorded after it, and `AX-19`(c)'s own "only a new `GRANT_CAPABILITY` decision can [restore `c`]" was unsatisfiable rather than merely unproved. Retirement is now ordered on the project's audit chain — a revocation retires `c` only from grants realized at a lower `seq` (`R13.26`, §5.3 step 5a) — so (c) is true as written and (f)'s end-set is exhaustive over grants rather than over the project. With all three repaired the lifetime is internally consistent: every ending in (c)–(f) now follows from a predicate §5.3 actually tests, and each predicate is about records the project's own chain orders. The deferral alternative is still **not** taken (§6.5), so `D01-F02-005`'s closure rests on a chosen lifetime and is registered as such (§8 `KD-9`). |
| `-026` | **CLOSED by correcting the claim; the missing derivation is carried** | Repair 3. `R13.19` is split: (i) states and **permits** that a worker's reports and actions reach measured stop and require-human controls — `S-INV-3`, the denial/breach/failure/divergence triggers, and expiry's severity increase — and (ii) is the only thing asserted, namely that a worker cannot make an assertion evidence, author an authoritative `trigger`/`status`/`severity`/`auto_resolvable`, choose the mode, or author a decision. The input-independence assurance is withdrawn. The absent severity/`auto_resolvable` derivation and its field-update boundary go to §6.4 and §8 `KD-8`, with the `HIGH`/`SUPERVISED` false rule and the human-resolution requirement retained. No human-bypass or evidence-forgery claim is made in either direction. |
| `-027` | **CLOSED** | Repair 4. Amendment 22's proposed text gains the fifth case — `decision.record` held under `AX-1`'s named exception, the trace naming the authenticated principal and `auth_method` with no authority record and absent `authority_ref` — and `R13.23` states it. No prior authorizing decision is invented: under `AX-15` there is none, which is the point of the exception. |
| `-028` | **PROPOSED CLOSED, on the corrected rule cell; it was `PARTIALLY CLOSED` against revision 04** | Repairs 4 and 5 of `FINDINGS-03` split `R13.22` in §4's list, corrected `R13.14`'s four-event kind claim and `R13.21`'s export count, and made `R13.8` and `AX-18` reference `A-INV-2` **as amendment 23 amends it**. [FINDINGS-04:52](review/DESIGN-04-FINDINGS-04.md#L52) found the rule **cell** itself still saying "the frozen wording covers only the second" — which is exactly what [domain-model.md:410](domain-model.md#L410) does **not** say — while the basis cell beside it said the opposite, and found revision 04's own claim that both cells were repaired to be false. The cell is rewritten here: the frozen sentence is unqualified, draws no execution/governance distinction, and is already contradicted by [transition-matrix.md:208](transition-matrix.md#L208); that is why amendment 23 narrows it. The proposed `A-INV-2` text is unchanged. The false "both cells" claim is withdrawn (§6.3). |

The three findings `DESIGN-04-FINDINGS-04` raises against the **proposal** are repaired here.
Its five findings against the **implementation** are not, and are not this document's to
repair — see below the table.

| id | disposition | what closes it |
|---|---|---|
| `-029` | **PROPOSED CLOSED by stating the denial event's own vocabulary** | Amendment 9's proposed `AX-8` previously required a project-scope or per-act denial to be recorded "with the same reason vocabulary as `denied_capabilities`", whose frozen enum ([domain-model.md:393](domain-model.md#L393)) has no `REVOKED` — so §5.3 step 5a's mandated reason could not be recorded, and `AX-8` forbids silent denial either way. The pin is removed. The denial `AuditEvent` carries its reason in `payload_ref` ([domain-model.md:787](domain-model.md#L787)), which is **not** a frozen field table or enum, so amendment 9 states that vocabulary itself: [domain-model.md:393](domain-model.md#L393)'s seven values **plus `REVOKED`**, available only to the two formless denials. `denied_capabilities`, its enum and §5.1 are untouched, and a run grant can never produce `REVOKED` because §5.1 has no retirement step (`R13.24`). §5.3 step 7, §3's no-new-enum statement and §6.3 are synchronized. The alternatives — amending the frozen enum, or reusing `NO_GRANTOR`/`POLICY` — are recorded and rejected in §6.5. |
| `-030` | **PROPOSED CLOSED by restricting the admitted subject profile** | §5.3 step 1 previously tested `scope = PROJECT` only. `scope` and `subject` are independent frozen fields ([domain-model.md:692](domain-model.md#L692), [:700](domain-model.md#L700)), so a `GRANT_CAPABILITY` with `scope = PROJECT` and `subject.kind = STAGE` passed step 1, was snapshot-bound by [:702](domain-model.md#L702), and could take [transition-matrix.md:395](transition-matrix.md#L395)'s `STALE` — which `AX-19`(e) said could not happen and (f) declared the end-set exhaustive. Step 1 now admits only `subject.kind ∈ {PROJECT, CAPABILITY}`, which is precisely the profile [:702](domain-model.md#L702) exempts from snapshot binding, so (e) follows from the admission rule rather than being assumed of it, and `HD-INV-4`/[authority-matrix.md:289](authority-matrix.md#L289) cannot reach the grant (`R13.25`). The grant is bound to the project by the decision's `project_id` ([:691](domain-model.md#L691)), not by its `subject`: step 1 requires `subject.id = project_id` only where the kind is `PROJECT`, and leaves a `CAPABILITY` subject's `Id` unconstrained because the frozen model gives it no referent. A decision outside that profile realizes no project grant; this document says nothing further about it. Every lifetime and closure summary is corrected: `AX-19`(e), `R6.5`, §3's `HD-INV-4` and §7.5 rows, §4, §6.5 and `KD-9`. |
| `-031` | **PROPOSED CLOSED by withdrawing the attribution** | [transition-matrix.md:270](transition-matrix.md#L270) reads "human revocation, policy change, scope breach, or integrity violation" against "`DEC(REVOKE_CAPABILITY)` or the triggering record". It names **no** record kind, unlike [:157](transition-matrix.md#L157) ("policy evaluation record") and [:170](transition-matrix.md#L170) ("policy re-evaluation record"). Revision 04 said its policy-change branch names a policy-evaluation record and used that to route the row to `KD-1`. That attribution is **withdrawn** from §2.22, §6.4 and `KD-3` (§6.3). The row stays open for the unspecified record it actually prints; no representation is chosen for it here. The corrected **thirty-nine of 44** count is unchanged, because the row was already counted as unclosed. |

**Owner blocking flags for these eight.** They exist, and this document had wrongly said
they did not. `DESIGN-04-FINDINGS-04` §6's table records them: `-029` **true**, `-030`
**true**, `-031` **false**, `-032` **true**, `-033` **true**, `-034` **true**, `-035` **true**,
`-036` **true** ([FINDINGS-04:155](review/DESIGN-04-FINDINGS-04.md#L155)–[:162](review/DESIGN-04-FINDINGS-04.md#L162)).
That record's prose at [:17](review/DESIGN-04-FINDINGS-04.md#L17) and
[:151](review/DESIGN-04-FINDINGS-04.md#L151) says the new blocking cells are blank; they are
not, so the prose is stale and **the tables are authoritative** — the relation
[CLAUDE.md:99](../CLAUDE.md#L99)–[:102](../CLAUDE.md#L102) states for `DISPOSITION-01` and for
this record alike. This document reproduces those flags and sets none; they are the owner's,
the review record is unchanged, and nothing here is a new judgment about them (`GR26-R3`,
§6.3, §7).

`DESIGN-04-032`…`-036` are findings against **`GR-23`'s implementation** of `AX-17`, not
against this proposal: `-032` the mode installed at creation, `-033` the creator and
event-actor attribution, `-034` `chosen` against `options_offered`, `-035` the missing
`SIGNATURE` evidence, and `-036` the manufactured `evidence_shown` ([FINDINGS-04:158](review/DESIGN-04-FINDINGS-04.md#L158)–[:162](review/DESIGN-04-FINDINGS-04.md#L162)).
**This revision does not repair them and does not claim they are repaired.** No file under
`src/` or `tests/` is touched. What it does supply is §2.23: the full predicate set a
conforming creation witness must satisfy, stated once and explicitly, so that the later
conformance work has a specification to build against. They are registered at `KD-15` and
remain open.

**Five** rows and two record kinds are **NOT CLOSED** and are listed in §6.4 and §8 rather
than claimed: the policy-evaluation and verification-record cells, [transition-matrix.md:171](transition-matrix.md#L171)
in both its cases, [:270](transition-matrix.md#L270)'s triggering-record alternatives,
[:412](transition-matrix.md#L412) for comparison triggers, and the six `HUMAN` capabilities
with no legal row. `D01-F02-003` is partially closed for that last reason. Two further
boundaries are carried explicitly rather than treated as settled: the inherited `CLAIM`
tensions at `KD-14` — `declared_status`-caused escalation against `G-6`/[transition-matrix.md:505](transition-matrix.md#L505),
and [worker_provider.md:146](worker_provider.md#L146)–[:147](worker_provider.md#L147)'s
"only path" against the escalation control paths at [transition-matrix.md:128](transition-matrix.md#L128)
and [:158](transition-matrix.md#L158) — and `GR-23` conformance at `KD-15`. §8 is the
register of everything still open; it is a record of what is not closed, not a commitment to
close it.

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
named ones, and not for the six further operations it cites (§6.1, §6.4, §8 `KD-7`).
`D01-F02-005`'s closure rests throughout on chosen rules — the second grant form, its
admitted subject profile (`R13.25`), its lifetime (`R6.5`), its denial vocabulary (`R13.24`),
its chain-ordered retirement rule (`R13.26`) and §6.2's initial-ceiling premise — and is registered at §8 `KD-9` so the dependency is not
lost behind the word "closed". `FINDINGS-04` held that `KD-9` could not claim even
conditional closure while `-029` and `-030` stood, because a choice whose own premises
conflict is not a premise one can accept; with both repaired the conditional claim is
restated, still as a **proposed** closure resting on chosen premises and not as a verified
one. Whether those premises are accepted is the owner's disposition, not this document's
(§6.5).

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
| `R13.8` | The activation-only rule is scoped to a run's grants rather than repealed. | **chosen** — the frozen sentence is unqualified. Scoping it leaves `A-INV-2` **as amendment 23 amends it** ([domain-model.md:410](domain-model.md#L410)) intact: activation remains the only entity conferring a run's **execution** authority, because `AX-18` keeps project grants out of every run set. It does **not** leave the frozen unqualified wording literally true, and revision 03's conclusion that `A-INV-2` therefore needs no amendment is **withdrawn** (`DESIGN-04-017`, `-028`): [transition-matrix.md:208](transition-matrix.md#L208) is authority exercised over a run that no activation supplies, so the frozen wording is contradicted independently of anything this amendment does. Amendment 23 is what resolves it (`R13.22`). |

### Amendment 9 — `AX-8`

**Target** [authority-matrix.md:19](authority-matrix.md#L19) (§0 Axioms). **Current frozen text:**

```
| `AX-8` | Denial is recorded: every denied capability appears in `ContractActivationRecord.denied_capabilities` with a reason. Silent denial is a defect. |
```

**Proposed text**

```
| `AX-8` | Denial is recorded. For a run grant every denied capability appears in `ContractActivationRecord.denied_capabilities` with a reason from that field's own enum, unchanged. For a project grant (§5.3) or a per-act exercise (§5.2) there is no activation, and the record is the denial `AuditEvent` §6 already requires: `epistemic_class = AUTHORITY`, its payload carrying each denied `CapabilityId` with a reason drawn from `denied_capabilities`' seven values — `NOT_IN_CEILING`, `ROLE_FORBIDDEN`, `MODE_FORBIDDEN`, `NO_GRANTOR`, `BUDGET`, `POLICY`, `NEVER_GRANTABLE` — **together with `REVOKED`**, which records retirement under `AX-10`/`AX-19`(c) and arises only at §5.3 step 5a — never in §5, §5.1 or §5.2, none of which retires anything. That eight-value set is the denial event's vocabulary and is not written into `denied_capabilities`. Silent denial is a defect in either form. |
```

**Closes** `D01-F02-005`. Fixes `DESIGN-04-003` and `-029`.

| id | rule | basis |
|---|---|---|
| `R13.9` | A project-scope denial has a conforming destination. | **chosen** — the frozen axiom names one destination that cannot exist before a contract and run do ([domain-model.md:388](domain-model.md#L388), [:390](domain-model.md#L390)). The granting decision cannot hold it either: `grants` is immutable and there is no denied field ([domain-model.md:698](domain-model.md#L698), [:699](domain-model.md#L699)). The denial event is already mandatory ([authority-matrix.md:293](authority-matrix.md#L293)), so this reuses a frozen record rather than adding one. |
| `R13.10` | Worked failure case: a decision whose `grants` contains one capability outside `project.capability_ceiling`. | **conditional** — it needs amendment 6's project-grant intersection **and** this amendment's destination together. Step 2 of §5.3 drops the capability with `NOT_IN_CEILING`, and the reason and capability then appear in the denial `AuditEvent`. Frozen [domain-model.md:393](domain-model.md#L393) supplies the seven inherited reasons, not the destination; before these amendments the reason had nowhere conforming to go. |
| `R13.24` | The denial `AuditEvent`'s reason vocabulary is this amendment's own, and is the seven `denied_capabilities` values plus `REVOKED`. | **chosen.** Revision 04 pinned it to "the same reason vocabulary as `denied_capabilities`" and then required §5.3 step 5a to deny with `REVOKED`, which [domain-model.md:393](domain-model.md#L393)'s closed enum does not contain: after a live grant and a covering revocation, the mandated reason could not be recorded, while `AX-8` makes silent denial a defect either way (`DESIGN-04-029`). The pin is withdrawn (§6.3). What the denial event carries is its `payload_ref` body ([domain-model.md:787](domain-model.md#L787)), a content-addressed artifact with **no frozen field table and no frozen enum**, so stating its vocabulary changes no frozen type; the frozen obligation at [authority-matrix.md:293](authority-matrix.md#L293) fixes the event's `epistemic_class` and nothing about its payload. Reusing the seven inherited values is chosen for legibility, not derived. `denied_capabilities` and its enum are **untouched**, and no run grant can ever carry `REVOKED`: §5 and §5.1 have no retirement step, and a revoked basis decision fails §5.1 admissibility as `NO_GRANTOR` instead. The rejected alternatives — amending the frozen enum, or reusing `NO_GRANTOR` or `POLICY` — are recorded in §6.5. What this rule states is the **vocabulary** available to the denial event, not a mapping from each denial to a value. §5.3 supplies that mapping for its own steps 2–5a, and step 7 records it. §5.2 does **not**: its steps 1–9 are checks that pass or fail and name no reason, so which of the eight values a failed per-act exercise carries is unassigned, exactly as it was before this repair. `AX-8`'s prohibition on silent denial still binds a §5.2 denial to emit the event; this rule neither supplies the missing assignment nor claims to, and `REVOKED` is not the gap — it can arise in neither §5, §5.1 nor §5.2, only at §5.3 step 5a. |

### Amendment 10 — `AX-3`

**Target** [authority-matrix.md:14](authority-matrix.md#L14) (§0 Axioms). **Current frozen text:**

```
| `AX-3` | Grants are per `ContractActivationRecord`, scoped to one `StageRun`, and frozen for that run's life. |
```

**Proposed text**

```
| `AX-3` | A grant is realized in exactly one of two forms. A **run grant** is per `ContractActivationRecord`, scoped to one `StageRun`, and frozen for that run's life (§5). A **project grant** is realized directly by a live `HumanDecision{kind: GRANT_CAPABILITY}` with `scope = PROJECT`, is scoped to one `Project`, carries only `ORD` capabilities whose §2 `grantable by` column names `HUMAN_PRINCIPAL`, and authorizes exactly the acts §5.3 names — those an activation cannot authorize, because they supply the structure an activation would have to reference. Its lifetime is `AX-19`(a)–(f) and is **not** bounded by the first activation: a later stage's first `contract.author` is the same kind of act as the first project's (§5.3). No third form of grant exists; a `HUMAN`-class capability is granted by neither form and is exercised per act (§5.2). |
```

**Closes** `D01-F02-005`.

| id | rule | basis |
|---|---|---|
| `R4.1` | A second grant form exists, scoped to a project, and delimited by which acts it authorizes rather than by when they occur. | **chosen** — one form is what makes the first import and first contract authoring circular ([transition-matrix.md:85](transition-matrix.md#L85), [:117](transition-matrix.md#L117), [:265](transition-matrix.md#L265), [domain-model.md:316](domain-model.md#L316), [:388](domain-model.md#L388), [:390](domain-model.md#L390)). Amendments 6–8 carry the rest of the realization change this form requires. Revision 03's "exists for the acts that precede any activation" is **withdrawn** as a lifetime statement (`DESIGN-04-025`): it read as a temporal bound that would retire the grant at the first activation, contradicting both `AX-19`'s end-set and the second stage's own `contract.author`. The acts are delimited functionally by §5.3 instead; **which** acts those are is unchanged. |
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
| `R13.14` | Four events are required, not two. | **conditional** on `AX-14`/`R3.6`'s chosen approval and `AX-17`'s consumption, and then **derived**: every transition emits an event before the new state is observable ([domain-model.md:797](domain-model.md#L797)), each names exactly one capability ([domain-model.md:789](domain-model.md#L789), [:890](domain-model.md#L890)) so recording under `decision.record` cannot merge with creation under `project.create`, the decision is recorded by [transition-matrix.md:393](transition-matrix.md#L393) and consumed by [:394](transition-matrix.md#L394), and chain order is authoritative for replay ([evidence-model.md:187](evidence-model.md#L187)). Changing the approval's **kind** alone does not change the count, contrary to revision 03: [transition-matrix.md:84](transition-matrix.md#L84) still requires its `SNAP`, and the chosen recording/creation/consumption history still produces its three further events under [:393](transition-matrix.md#L393), [:394](transition-matrix.md#L394) and [domain-model.md:789](domain-model.md#L789), [:797](domain-model.md#L797). Only **removing** the approval or the consumption would change it, and that is a different premise, not a different kind. Revision 01's snapshot-0/creation-1 account is withdrawn. |
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
```

**Closes** `D01-F02-005`. Fixes the `R6.5` half of `DESIGN-04-011`, the remaining half of
`-025`, and `-030`.

| id | rule | basis |
|---|---|---|
| `R6.1` | The first import and first contract authoring can be authorized by a project grant with no activation. | **derived** that both are `ORD` with `HUMAN_PRINCIPAL` as a named grantor — [authority-matrix.md:74](authority-matrix.md#L74), [:86](authority-matrix.md#L86); **chosen** that a project grant authorizes them, with amendments 6–8 supplying the realization change. |
| `R6.2` | The grant is bounded by `project.capability_ceiling`. | **derived** — [domain-model.md:141](domain-model.md#L141), [:153](domain-model.md#L153) bound every grant in the project by the ceiling. |
| `R6.3` | The §3 mode gate is retained; the `KERNEL`/`NEVER` exclusion is not optional. | **chosen** for adopting the mode gate in a new resolution, mirroring §5 step 3 ([authority-matrix.md:243](authority-matrix.md#L243)); **derived** for the `KERNEL`/`NEVER` exclusion, which [authority-matrix.md:17](authority-matrix.md#L17) and [:18](authority-matrix.md#L18) require independently of this step. |
| `R6.4` | §4.1 is not applied. | **conditional** — see amendment 6, which performs the `AX-4` narrowing this depends on. |
| `R6.5` | A `GRANT_CAPABILITY` project decision is realized once, survives every exercise of its grant, and ends only by `AX-19`(c)–(f). | **chosen**, with a conditional half. Revision 03 called this derived; **it is not**, and that label is withdrawn. [authority-matrix.md:263](authority-matrix.md#L263) is an **activation-time** predicate about a **run** grant's basis decision: it requires that decision to be `VALID`, unexpired and nonce-unconsumed when the activation is resolved, and states nothing about that decision's state *after* the activation and nothing about a project-scoped grant. A predicate tested before an operation does not determine the decision's state after it. [transition-matrix.md:394](transition-matrix.md#L394) consumes a decision that "discharged the transition it was recorded for"; choosing that a project grant is recorded for **no** transition (`AX-19`(a)) is a **new premise**, not a reading of that row. The single-realization reading of `HD-INV-3` ([domain-model.md:718](domain-model.md#L718)) is likewise chosen: the frozen invariant fixes consumption to a `nonce` and forbids replay across runs, and does not say what counts as one use of a standing grant. What the frozen text **does** supply is the ending machinery this choice uses and does not amend: [authority-matrix.md:41](authority-matrix.md#L41)'s three boundaries, [:21](authority-matrix.md#L21)'s `AX-10` immediacy for future operations, [domain-model.md:141](domain-model.md#L141) and [:153](domain-model.md#L153)'s ceiling bound, [:699](domain-model.md#L699)'s immutable `revokes` delta, [:701](domain-model.md#L701)'s optional `expires_at` with `scope` as the fallback bound, [:702](domain-model.md#L702)'s exclusion of a `PROJECT`/`CAPABILITY`-subject `GRANT_CAPABILITY` from snapshot binding, [transition-matrix.md:99](transition-matrix.md#L99)'s terminal `ARCHIVED`, and [:396](transition-matrix.md#L396)/[:397](transition-matrix.md#L397). The **conditional** half is that, given (a), no new row and no amendment to §7.5 is needed: [:394](transition-matrix.md#L394)'s discharge predicate and [:401](transition-matrix.md#L401)'s terminality stay untouched *because* of the choice, not independently of it. Revision 02's `AX-20` lifecycle stays **withdrawn**: it invoked `VALID → CONSUMED` without a discharge, overlapped [:396](transition-matrix.md#L396), and was unreachable after [:401](transition-matrix.md#L401). Per-act decisions under §5.2 are unaffected and are consumed by the transition they discharge. Two operands of the end-set are supplied by this revision rather than assumed: [:702](domain-model.md#L702)'s snapshot-binding exclusion applies **because** §5.3 step 1 now admits only the subject profile it names (`R13.25`), and [:21](authority-matrix.md#L21)'s immediacy is read as a permanent historical effect, ordered against the grant it reaches by the project chain's own `seq` ([evidence-model.md:187](evidence-model.md#L187)), rather than as a filter on the revoking decision's current state or as an effect on every grant whatever its position (`R13.26`). Because the lifetime is chosen throughout, `D01-F02-005`'s closure rests on it: §8, `KD-9`. |
| `R13.25` | §5.3 admits a `GRANT_CAPABILITY` only over a `PROJECT` or `CAPABILITY` subject, on a decision whose `project_id` is this project, and that restriction is what makes `AX-19`(e) true. | **chosen** for the restriction; **derived** for its consequence. `scope` ([domain-model.md:700](domain-model.md#L700)) and `subject` ([:692](domain-model.md#L692)) are independent frozen fields, and nothing in the frozen text makes `scope = PROJECT` imply a `PROJECT` subject — which is why revision 04's step 1 admitted a `scope = PROJECT`, `subject.kind = STAGE` decision that [:702](domain-model.md#L702) makes snapshot-bound and [transition-matrix.md:395](transition-matrix.md#L395) can stale, contradicting `AX-19`(e) and (f) (`DESIGN-04-030`). Choosing the admitted profile to be exactly [:702](domain-model.md#L702)'s exempt one is this document's selection; **given** it, `snapshot_bound = false` and the `STALE` exclusion, `subject_snapshot_id`'s absence under [:703](domain-model.md#L703) and the unreachability of `HD-INV-4` and [authority-matrix.md:289](authority-matrix.md#L289) all follow from frozen text. The rejected alternative — admitting every subject profile and adding `STALE` to the end-set — is recorded in §6.5. No frozen field, enum or invariant is amended: step 1 is a predicate of the new §5.3, and a decision it rejects is left exactly as the frozen model has it. Two limits on what step 1 can test are stated rather than assumed. **The project binding is `project_id`, not `subject`.** [domain-model.md:691](domain-model.md#L691) types `project_id` as `Ref<Project>` and is the only field that names the project; `subject.id` is a bare `Id` ([:692](domain-model.md#L692)), so the `PROJECT` branch can require `subject.id = project_id` and that equality is a corroboration, not the binding. **A `CAPABILITY` subject's `id` is left unconstrained**, because the frozen model gives it no referent to constrain: `Id` is a ULID ([:17](domain-model.md#L17)) and `Ref<E>` is an `Id` constrained to an entity ([:38](domain-model.md#L38)), while a `CapabilityId` is a dotted name in the [authority-matrix.md:56](authority-matrix.md#L56) register and there is no `Capability` entity for a `Ref` to point at. Step 1 therefore does **not** require `subject.id` to name a capability in `grants`, and this document neither supplies a referent for that field nor claims one; nothing in `AX-19` depends on it, since [:702](domain-model.md#L702) exempts the profile by `subject.kind` alone. |
| `R13.26` | Retirement by revocation is a historical fact about **two** recorded decisions and their order on the project's audit chain: a revocation retires `c` from exactly those project grants realized before it, whatever its own later `decision_state`. | **chosen**, over frozen ordering. Two questions the frozen text leaves open are answered here, and both answers are choices. **(i) What happens when the revoking decision itself later expires, is consumed or goes stale.** [authority-matrix.md:21](authority-matrix.md#L21) says revocation "is immediate for future operations and never retroactive for recorded evidence" and says nothing about this. Revision 04's step 5a tested for a "later `VALID`" revocation, which would let the grant resurrect when that decision left `VALID` — a consequence the rule's own word "permanently" contradicts, and which [FINDINGS-04:164](review/DESIGN-04-FINDINGS-04.md#L164) declined to infer only because `AX-19`(c) says retirement is permanent. The predicate matches the rule instead: reached `VALID`, not `VOID`, retired thereafter. `VOID` is excluded because [transition-matrix.md:397](transition-matrix.md#L397) voids a decision whose own record fails verification or violates `HD-INV-1`, and such a record establishes nothing. **(ii) Which grants a revocation reaches.** Stating only (i) was not enough, and revision 05's first step 5a was defective for the reason the `GR-26` review gives: matching **any** recorded revocation retires `c` from a grant recorded *after* it, so on the history `G1 → R → G2` the capability `G2` grants is denied `REVOKED`, and `AX-19`(c)'s own "only a new `GRANT_CAPABILITY` decision can [restore `c`]" is not merely unproved but unsatisfiable. The relation chosen is the project's own: `pos(D)`, the `seq` of the `AuditEvent` `AE-INV-2` ([domain-model.md:797](domain-model.md#L797)) requires for `D`'s `∅ → VALID` transition ([transition-matrix.md:393](transition-matrix.md#L393)), least where that transition emits more than one. Amendment 12 amends that row's **evidence cell** only; the transition it prints, and `AE-INV-2`'s obligation over it, are the same in the frozen row and the amended one, so `pos` is well defined under either. **Nothing is invented for it.** The chain is per project ([domain-model.md:778](domain-model.md#L778)); `seq` is `uint64`, monotonic and gapless ([:779](domain-model.md#L779)); `Project → AuditEvent` is a total order ([:877](domain-model.md#L877)); and [evidence-model.md:187](evidence-model.md#L187) makes `seq` within a project **the** total order, authoritative for replay, with `causal_parent` explicitly advisory ([:188](evidence-model.md#L188), [domain-model.md:791](domain-model.md#L791)). `pos` is injective over a project's decisions on the reading that a decision-recording event's `subject` names the decision it records, an `AuditEvent` carrying exactly one ([:786](domain-model.md#L786)); nothing here rests on that reading, because step 5a's inequality is strict and a tie would retire nothing. This is the same ordering amendment 16 already uses for evidence reachability (`R8.1`), so the document acquires no second notion of "earlier": it is a position in the recorded history, **not** a commit time — `D01-F02-002`'s retained half and `R3.12` keep those apart, and this rule needs only the former. What is **chosen** is that retirement is ordered by `pos` at all, and that the boundary is the grant's realization under `AX-19`(a) rather than the act being resolved; [authority-matrix.md:21](authority-matrix.md#L21) fixes neither. The rejected alternatives — an unordered match, `decided_at`/`recorded_at`, and `HumanDecision.prev_event_hash` — are recorded in §6.5. No union rule over several grants is needed, because `AX-19`'s first sentence already makes an exercising event cite one granting `decision_id`, which §5.3 step 6 states. The revoking decision's own subject profile is **not** restricted, since nothing about it needs to stay fresh. |
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
| `R13.19` | The boundary is asserted content versus runtime-established control fields, not existence versus everything else. | **chosen** — the cell now names which fields may gate. It is available because the same row already says a claim's provenance *is* verifiable while its content is not; the named fields are the ones the frozen model sources to the runtime ([domain-model.md:737](domain-model.md#L737), [:738](domain-model.md#L738), [:743](domain-model.md#L743)–[:746](domain-model.md#L746), [:748](domain-model.md#L748)) and the trigger must have actually fired for the escalation to exist ([transition-matrix.md:412](transition-matrix.md#L412)), while `summary` and `evidence_refs` ([domain-model.md:739](domain-model.md#L739), [:740](domain-model.md#L740)) carry what the reporter said. `G-3` ([domain-model.md:889](domain-model.md#L889)) and the bare `Claim`'s own never-gates rule ([domain-model.md:113](domain-model.md#L113)) are untouched. Revision 03's assurance that **no worker assertion becomes a gate** is **withdrawn as too broad** (`DESIGN-04-026`). The accurate boundary has two halves, and this amendment asserts only the second. **(i) Worker reports and worker actions may reach a measured stop or a require-human control, and this is permitted.** A worker's own `declared_status` ([domain-model.md:203](domain-model.md#L203)) conflicting with `observed_satisfaction` **must** raise `Escalation(DECLARED_OBSERVED_CONFLICT)` under `S-INV-3` ([:254](domain-model.md#L254)–[:256](domain-model.md#L256)); a worker's denied action, scope attempt, repeated failure or usage divergence fires `CAPABILITY_DENIED`, `SCOPE_BREACH_ATTEMPT`, `REPEATED_FAILURE` or `POLICY_CONFLICT` ([:758](domain-model.md#L758), [:759](domain-model.md#L759), [:762](domain-model.md#L762), [worker_provider.md:92](worker_provider.md#L92)); and an escalation left unresolved for the configured window escalates severity one level and reopens ([transition-matrix.md:415](transition-matrix.md#L415), [:418](transition-matrix.md#L418)–[:419](transition-matrix.md#L419)), a specified route from worker-caused inaction to `HIGH`/`CRITICAL` and so to `auto_resolvable = false`. That is the fail-stop path and this document permits it. **(ii) What a worker cannot do** is what this cell now asserts: it cannot make an asserted field evidence or raise `observed_satisfaction` (`G-3`, [domain-model.md:113](domain-model.md#L113), [worker_provider.md:88](worker_provider.md#L88)), cannot author an authoritative `trigger`, `status`, `severity` or `auto_resolvable` — all sourced `R` at [:737](domain-model.md#L737), [:738](domain-model.md#L738), [:746](domain-model.md#L746), [:748](domain-model.md#L748) — cannot choose the project mode ([:138](domain-model.md#L138), [:152](domain-model.md#L152), [authority-matrix.md:59](authority-matrix.md#L59)), and cannot author a `HumanDecision` ([domain-model.md:714](domain-model.md#L714)). No claim of **input independence** for those runtime fields is made here: the derivation that would establish it does not exist in the frozen models and is carried unclosed (§6.4, §8 `KD-8`). Revision 02 called [transition-matrix.md:132](transition-matrix.md#L132)'s trigger qualifier an unchanged precondition; it is inside that row's `required_evidence` cell and is corrected in §2.22. |

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
| authority trace | for one action: capability used, mode, policy digest, and the authority the action was exercised under — the activation record and grant chain for a run grant; the granting `HumanDecision` for a project grant; the authorizing `HumanDecision` for a per-act exercise; the kernel's own holding for a `KERNEL` capability; and for `decision.record` the recording principal's own authenticated holding under `AX-1`'s named exception (`AX-15`), naming the authenticated principal and `auth_method` with no authority record and no `authority_ref` | answering "what allowed this?" |
```

**Closes** `D01-F02-001` and `D01-F02-005`.

| id | rule | basis |
|---|---|---|
| `R13.21` | The export that answers "what allowed this?" must name whichever authority form the action used. | **chosen** — the frozen row names an activation record unconditionally, so a pre-activation `project.create` or first `roadmap.import` has nothing to put in the field and the trace is unrealizable for exactly the acts amendments 3–5, 13 and 14 make legal. The alternative — stating that pre-activation acts have no exportable trace — is rejected: the authority exists and is already cited by `AuditEvent.authority_ref` ([domain-model.md:790](domain-model.md#L790)), so the trace can name it. The other **three** export artifacts ([evidence-model.md:280](evidence-model.md#L280), [:281](evidence-model.md#L281), [:283](evidence-model.md#L283)'s claim ledger) are untouched, and every export remains itself appended ([:285](evidence-model.md#L285)–[:286](evidence-model.md#L286)). Revision 03's "other two" is corrected: [:283](evidence-model.md#L283) is a fourth row of the same table. |
| `R13.23` | The trace has a fifth case, `decision.record` held under `AX-1`'s named exception. | **chosen**, and required by amendments 4 and 5. Those make possession under `AX-15` a legal way to hold `required_capability` at a transition, and amendments 1 and 2 require that act's event to carry **absent** `authority_ref` — so the frozen trace's "activation record, grant chain" has nothing to name for a case this document newly makes legal, exactly as for the other pre-activation acts. The export names the authenticated principal and `auth_method` instead. This invents **no prior authorizing decision**: `AX-15`'s whole point is that the human act *is* the decision, so there is none to cite, and [transition-matrix.md:393](transition-matrix.md#L393)'s own recording event is the first. Revision 03's `A22` omitted this case while amendments 4 and 5 created it (`DESIGN-04-027`). |

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

**Closes** `D01-F02-003`. Fixes `DESIGN-04-028` (the rule cell; the proposed text is unchanged).

| id | rule | basis |
|---|---|---|
| `R13.22` | Governing a run and executing within it are different authorities. The frozen wording draws **no** such distinction — it is unqualified, and as written it is already contradicted by frozen text — which is why amendment 23 narrows it to execution authority. | **split.** **Derived** that a distinction is *required*: [transition-matrix.md:208](transition-matrix.md#L208) is a run transition whose `required_capability` is the `HUMAN` capability `stage.reject`, which [authority-matrix.md:221](authority-matrix.md#L221) denies to every role, so no activation can supply it and §5.2 must — the frozen invariant as written is already contradicted by frozen text. **Chosen** that the resolution is *this* execution-only scope, and chosen in its boundary wording: the frozen line names no such scope and several other reconciliations exist. Revision 02's assertion that keeping the run's sets unchanged made the frozen wording equivalent is withdrawn, and so is revision 03's residual claim at `R13.8` that frozen `A-INV-2` needs no amendment. `AX-18` and amendment 8's `C-INV-3` keep every run set sourced from the activation, so nothing a worker holds changes, and no new worker capability or field is introduced. Revision 04's own rule cell said the frozen wording "covers only the second" while this basis said the opposite, and revision 04's §0 and §4 claimed both cells had been repaired; the cell is corrected above and the claim is withdrawn (`DESIGN-04-028`, §6.3). |

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
| [:270](transition-matrix.md#L270) | `DEC(REVOKE_CAPABILITY)` → `DECISION`, **or** the triggering record → typed only where it is already one of `G-1`'s kinds | **P / NOT CLOSED.** Only the decision branch is typed. The row's four triggering conditions are human revocation, policy change, scope breach and integrity violation; the first is the typed `DEC` branch. For the other three the row prints "the triggering record" and **names no record kind at all** — unlike [:157](transition-matrix.md#L157) and [:170](transition-matrix.md#L170), which do name a policy evaluation or re-evaluation record. Revision 04 attributed a policy-evaluation record to this row's policy-change branch; that attribution is **withdrawn** (`DESIGN-04-031`, §6.3), and no representation is chosen in its place. Whatever record the row means, it is typed here only if it is already one of `G-1`'s kinds, and the row does not say that it is. Carried to §6.4 as an unspecified operand, not as an instance of `KD-1`. |
| [:340](transition-matrix.md#L340) | `DEC(REVOKE_CAPABILITY)` → `DECISION`, **or** the clock → a precondition, no citation | **P** — a clock reading is not made into a record. |
| [:161](transition-matrix.md#L161), [:170](transition-matrix.md#L170), [:174](transition-matrix.md#L174) | the `ESC(OPEN)` alternative at [:161](transition-matrix.md#L161) → `CLAIM`; the `DEC(OVERRIDE)` alternative at [:170](transition-matrix.md#L170) and conjunct at [:174](transition-matrix.md#L174) → `DECISION`; the chain-verification and policy-re-evaluation records → **no admissible kind** | **NOT CLOSED.** `G-1` admits no kind for them and this document proposes none; revision 02's `CLAIM` typing is withdrawn. At [:161](transition-matrix.md#L161) and [:170](transition-matrix.md#L170) one alternative is typed and the other is not; at [:174](transition-matrix.md#L174) the unclosed record is a conjunct that `DEC(OVERRIDE)` cannot replace. Carried to §6.4. |
| [:171](transition-matrix.md#L171) | the `DEC` each resolution referenced → `DECISION` by kind | **NOT CLOSED, in two distinct cases.** Typing is not the obstruction in either. **(A) Consumed `DEC`:** a resolution's decision is `CONSUMED` by the resolution it discharged ([:394](transition-matrix.md#L394), terminal per [:401](transition-matrix.md#L401)), while a cited `DEC` must be `VALID` here ([:74](transition-matrix.md#L74), [authority-matrix.md:289](authority-matrix.md#L289), [transition-matrix.md:522](transition-matrix.md#L522)). **(B) Absent `DEC`:** the row's own precondition admits `status ∈ {RESOLVED, WITHDRAWN}`, and a resolution may have referenced **no** decision — [:414](transition-matrix.md#L414) resolves on `auto_resolvable = true` against a `SNAP`/`VR(pass)`, [:416](transition-matrix.md#L416) withdraws against the same — so there is no `DEC` for the cell to name. Revision 02's "live at that resolution" reading is withdrawn. Both cases carried to §6.4. |

**Thirty-nine** of the 44 rows are typed end to end. **Five** are not:
[:161](transition-matrix.md#L161) and [:170](transition-matrix.md#L170) have one typed
alternative and one unclosed, [:174](transition-matrix.md#L174) has an unclosed conjunct,
[:270](transition-matrix.md#L270) has one typed alternative and one unclosed, and
[:171](transition-matrix.md#L171) is unclosed outright (§6.4). Revision 02's claim that
all 44 receive a total typing is withdrawn, and so is revision 03's count of forty:
it counted [:270](transition-matrix.md#L270) as closed while the same section's own text
sent that row to §6.4, which did not carry it. Both are corrected here. The adjacent cells at
[:121](transition-matrix.md#L121), [:157](transition-matrix.md#L157),
[:159](transition-matrix.md#L159), [:163](transition-matrix.md#L163),
[:165](transition-matrix.md#L165), [:167](transition-matrix.md#L167),
[:175](transition-matrix.md#L175), [:307](transition-matrix.md#L307),
[:337](transition-matrix.md#L337), [:397](transition-matrix.md#L397) and
[:412](transition-matrix.md#L412) resolve by §2.21's table, which says which of them are
unclosed.

### 2.23 The creation witness's full predicate set

`AX-17` states an **ordering** witness: four transitions, four events, one transaction, no
event merging two capability identities. It was written with "unrelated defects held aside",
and that phrase has been read as though the ordering were the whole obligation. It is not.
`AX-17` is a conforming witness only when every other predicate of the four rows it names
also holds; §3's untouched-locations table keeps all of them in force, and `AX-14` adds the
approval. This section states them in one place, as **requirements of the design**, so that
later conformance work has something definite to build against.

Nothing here is new normative text and nothing here is implemented. `DESIGN-04-032`…`-036`
are `FINDINGS-04`'s findings that `GR-23`'s creation path does **not** satisfy rows 1, 2, 3,
5 and 6 below. This document does not repair them, does not assert they are repaired, and
records no conformance claim of any kind; the table's right-hand column names the finding so
the two records stay linked (`KD-15`).

| # | requirement | source | open implementation finding |
|---|---|---|---|
| 1 | **Mode.** The project's `governance_mode` at the moment of the creating act must be one the §3 mode gate permits for `project.create`. [authority-matrix.md:157](authority-matrix.md#L157) makes it `DENY` in `AUTONOMOUS` and [transition-matrix.md:84](transition-matrix.md#L84)'s `autonomous_policy` cell is `DENY`, so the initial mode must be `SUPERVISED`. `AX-14`'s `APPROVE` decision authorizes the act; it does **not** lift a `DENY` policy cell. §5.2 step 3 reads `governance_mode` "as it stands before the act", and creation is the one act with no prior project to read: what step 3 gates on there is the mode the creating act itself establishes, which [domain-model.md:138](domain-model.md#L138) makes a required, human-supplied field of the created `Project`. The gate is therefore evaluated against that supplied value, and `SUPERVISED` is the only value it passes. A project that is to run `AUTONOMOUS` reaches that mode only by a later `SET_MODE` decision under `project.mode.set` — which has no legal transition row in the frozen matrix and is `DESIGN-03`'s subject (§5, §6.1). Until that row exists, an `AUTONOMOUS` project has no legal history. | [authority-matrix.md:58](authority-matrix.md#L58), [:157](authority-matrix.md#L157), [transition-matrix.md:84](transition-matrix.md#L84); §5.2 step 3; `AX-14` | `-032` |
| 2 | **Creator.** `Project.created_by.actor_kind` must be `HUMAN`. It is the row's own precondition and a field requirement, and [transition-matrix.md:485](transition-matrix.md#L485) makes creation by a non-human `NONE_GRANTABLE`/`DENY` — a runtime cannot originate a project and thereby its own ceiling. | [domain-model.md:150](domain-model.md#L150), [transition-matrix.md:84](transition-matrix.md#L84), [:485](transition-matrix.md#L485) | `-033` |
| 3 | **Event attribution.** The two acts have **different** actors and both are constrained. The `decision.record` event is held under `AX-15`, which requires `actor.actor_kind = HUMAN` with `auth_method ∈ {SESSION, SIGNATURE, MTLS}` and **absent** `authority_ref` (amendments 1, 2); a `RUNTIME` actor with `auth_method = NONE` does not hold it and `AX-1` then denies the act. The `project.create` event may carry a `RUNTIME` actor, but only under `AX-16`: it must carry `on_behalf_of` naming the deciding principal, at delegation depth ≤ 2, and set `authority_ref` to the approval's `decision_id`. A `HUMAN` value in the decision's own `decided_by` satisfies neither of these: they are fields of the **events**. | `AX-15`, `AX-16`, amendments 1–2; [authority-matrix.md:143](authority-matrix.md#L143), [domain-model.md:60](domain-model.md#L60) | `-033` |
| 4 | **Authority citation and order.** Event 1 cites event 0's snapshot as `subject_snapshot_id` — the `RealitySnapshot` entity, never an `AuditEvent` id; event 2 sets `authority_ref` to the decision recorded at event 1 and cites event 0 as its `SNAP`; event 3 cites event 2. Each cited record has lower `seq` (`R13.15`). | `AX-17`, `R13.15`; [domain-model.md:703](domain-model.md#L703), [evidence-model.md:178](evidence-model.md#L178) | — (reported implemented at [FINDINGS-04:117](review/DESIGN-04-FINDINGS-04.md#L117)–[:119](review/DESIGN-04-FINDINGS-04.md#L119)) |
| 5 | **A valid choice.** The approval is a `HumanDecision` and every field predicate binds before it is cited as authority: `chosen` MUST be in `options_offered` ([domain-model.md:696](domain-model.md#L696)), and `options_offered` is a required field ([:695](domain-model.md#L695)). An approval recording `chosen` against an empty `options_offered` is malformed, and a malformed decision is not authority for anything. Where `auth_method = SIGNATURE`, `signature` is required ([:710](domain-model.md#L710)): the method label and a key id do not satisfy it, and an implementation that accepts the method without the evidence must either bind the signature or refuse the method. | [domain-model.md:695](domain-model.md#L695), [:696](domain-model.md#L696), [:710](domain-model.md#L710); `HD-INV-1` | `-034`, `-035` |
| 6 | **Informed approval.** `evidence_shown` is mandatory and is "what the human actually saw" ([domain-model.md:709](domain-model.md#L709)); `HD-INV-2` records an uninformed approval **as uninformed** and makes it satisfy no `required_evidence`; `subject_snapshot_id` is "the repository reality the human actually approved" ([:703](domain-model.md#L703)). The creating act therefore needs a presentation-and-response boundary bound to the exact observation of event 0, with freshness rechecked before the commit. A runtime-selected artifact index is a record of what the runtime chose to show, not evidence that a human saw and approved it, and labelling it `evidence_shown` asserts something the transaction has not established. | [domain-model.md:703](domain-model.md#L703), [:709](domain-model.md#L709), `HD-INV-2` at [:716](domain-model.md#L716) | `-036` |
| 7 | **Transaction shape.** One store transaction, four ordered appends, `Project.event_seq = 3` and `event_head` at event 3 on commit; no committed partial project; the snapshot complete before it is bound. | `AX-17`, `R3.12`, amendments 19–21 | — (reported implemented at [FINDINGS-04:115](review/DESIGN-04-FINDINGS-04.md#L115), [:120](review/DESIGN-04-FINDINGS-04.md#L120)) |

A correct four-event sequence alone is therefore **not** conformance to `AX-17`. Rows 1, 2,
3, 5 and 6 are independent obligations, each verifiable on its own field, and each is
currently reported unmet ([FINDINGS-04:122](review/DESIGN-04-FINDINGS-04.md#L122)–[:128](review/DESIGN-04-FINDINGS-04.md#L128)).
Row 1 also has a consequence for the roadmap that is not an implementation defect: while
`project.mode.set` has no legal row, this design offers no legal route from `SUPERVISED` to
`AUTONOMOUS` at all, so an `AUTONOMOUS` project cannot be reached by any conforming history
(§6.1, `KD-7` neighbours; the row itself is `DESIGN-03`'s, §5).

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
| [authority-matrix.md:41](authority-matrix.md#L41), [:263](authority-matrix.md#L263), [:21](authority-matrix.md#L21) | When a `HUMAN_DECISION` grant expires; a run grant's basis decision must be live with its nonce unconsumed at activation; `AX-10`'s immediate revocation. | Untouched, and used — but **not** as a derivation. [:41](authority-matrix.md#L41) supplies the three ending boundaries `AX-19`(d)/(e) route through and [:21](authority-matrix.md#L21) the immediacy `AX-19`(c) implements. [:263](authority-matrix.md#L263) is cited only for what it says: a predicate tested at activation time over a run grant's basis. It does **not** establish that a project grant's decision is never consumed, nor that a project grant exists at all; that is `R6.5`'s choice. |
| [authority-matrix.md:51](authority-matrix.md#L51)–[:52](authority-matrix.md#L52), [:56](authority-matrix.md#L56)–[:147](authority-matrix.md#L147) | The `HUMAN` class legend and the capability register. | Untouched; §5.2 implements the legend and `AX-14` satisfies it on the `AUTO` rows. No class, grantor, default or mode restriction changes. `AX-15` states a holding the register does not describe; [:143](authority-matrix.md#L143) keeps describing grantability and keeps `DENY` as the default for anyone but the authenticated principal recording their own decision. |
| [authority-matrix.md:155](authority-matrix.md#L155)–[:173](authority-matrix.md#L173) | The §3 mode gate. | Applied unchanged by §5.2 step 3 and §5.3 step 3. No capability becomes available in a mode that denied it; `project.create` stays `DENY` in `AUTONOMOUS` ([:157](authority-matrix.md#L157)), and `AX-14`'s approval does not lift that cell — a creating act must therefore happen under `SUPERVISED` (§2.23, row 1). |
| [authority-matrix.md:190](authority-matrix.md#L190)–[:222](authority-matrix.md#L222) | §4.1's per-invocation grant table, including [:221](authority-matrix.md#L221). | Untouched, and the reason no run grant can carry a `HUMAN`-class capability (`R3.2`). The `C`/`D` tension at [:203](authority-matrix.md#L203), [:206](authority-matrix.md#L206) against [:221](authority-matrix.md#L221) predates this document and is not one of the five findings; no amendment relies on resolving it. Amendment 6 is what stops the table's inapplicability to project grants from being a silent change. |
| [authority-matrix.md:239](authority-matrix.md#L239)–[:277](authority-matrix.md#L277) | §5 resolution and §5.1 admissible grantors. | Unchanged for run grants. §5.2 and §5.3 are additive sections after §5.1; step 5's `KERNEL` removal and [:266](authority-matrix.md#L266)'s "never for a run's grant" both stand. |
| [authority-matrix.md:285](authority-matrix.md#L285)–[:291](authority-matrix.md#L291), [:293](authority-matrix.md#L293) | §6's other enforcement points. | Untouched, and two are relied on: decision freshness at [:289](authority-matrix.md#L289) enforces the liveness §5.2 step 4 and `AX-19` require, and the denial `AuditEvent` at [:293](authority-matrix.md#L293) is the destination amendment 9 uses. |
| [domain-model.md:38](domain-model.md#L38), [:273](domain-model.md#L273), [:390](domain-model.md#L390), [:778](domain-model.md#L778), [:805](domain-model.md#L805), [:865](domain-model.md#L865) | Reference integrity and the activation/run cardinality. | Untouched. They are compatible with one transaction and deferred checks; `R3.12` applies that reading rather than weakening them. |
| [domain-model.md:141](domain-model.md#L141), [:153](domain-model.md#L153), [:145](domain-model.md#L145), [:146](domain-model.md#L146) | The ceiling and `P-INV-2`; `event_head` and `event_seq`. | Untouched. The ceiling is the basis for `R6.2` and prescribes no empty initial value (§6.2); chain-field initialization belongs to the append protocol. |
| [domain-model.md:284](domain-model.md#L284), [:285](domain-model.md#L285), [:287](domain-model.md#L287) | Run budget and deadline mutability. | Untouched: `D01-F02-008` is out of scope. Retyping `DEC(EXTEND_BUDGET)` does not extend them. |
| [domain-model.md:686](domain-model.md#L686)–[:712](domain-model.md#L712) | `HumanDecision` fields. | No field, type or enum changes. Two profiles are now written as explicit checks rather than assumed: `grants = revokes = ∅` for a per-act decision (§5.2 step 6), and `kind: GRANT_CAPABILITY`, `scope: PROJECT`, `project_id` = this project, `subject.kind ∈ {PROJECT, CAPABILITY}` for a project grant (§5.3 step 1). The subject conjunct is new in revision 05 and is a **selection among frozen values**, not a change to [:692](domain-model.md#L692) or [:700](domain-model.md#L700): the two fields stay independent, and a decision the step rejects keeps every frozen property it has, including snapshot binding under [:702](domain-model.md#L702) (`R13.25`). No field gains a new type or referent: the project binding is [:691](domain-model.md#L691)'s existing `Ref<Project>`, and `subject.id` is constrained only in the `PROJECT` case, where it is another `Id` of the same project. [:696](domain-model.md#L696)'s `chosen ∈ options_offered`, [:709](domain-model.md#L709)'s `evidence_shown` and [:710](domain-model.md#L710)'s conditional `signature` are untouched and are restated as conformance requirements in §2.23. |
| [domain-model.md:714](domain-model.md#L714)–[:727](domain-model.md#L727) | `HD-INV-1` … `HD-INV-4`. | Untouched in text. `HD-INV-3` ([:718](domain-model.md#L718)) is **read** by `AX-19`(a) as satisfied by one realization, the nonce spent there and the grant kept out of every run set so it is not replayed across runs — a **chosen** reading, since the invariant does not define one use of a standing grant (`R6.5`). `HD-INV-4` continues to stale a snapshot-bound decision, including those `R13.13` identifies; it cannot reach a project grant, because §5.3 step 1 admits only the subject profile [:702](domain-model.md#L702) excludes from snapshot binding, so `snapshot_bound = false` and the invariant's premise is unsatisfiable (`AX-19`(e), `R13.25`). Revision 04 asserted that conclusion from `scope` alone, which does not imply the subject (`DESIGN-04-030`, §6.3). |
| [domain-model.md:789](domain-model.md#L789), [:797](domain-model.md#L797), [:888](domain-model.md#L888) `G-2`, [:889](domain-model.md#L889) `G-3` | `capability_used` and event emission; the authority-citation allow-list; worker values are `CLAIM`. | Untouched. The first two are why the creation witness has four events. Every citation introduced is a `HumanDecision` or a `ContractActivationRecord`, or is absent; amendment 18 changes what a `CLAIM` may gate, not what a worker-authored value is, and the bare `Claim`'s own never-gates rule ([:113](domain-model.md#L113)) stands. |
| [domain-model.md:779](domain-model.md#L779), [:786](domain-model.md#L786), [:791](domain-model.md#L791), [:877](domain-model.md#L877), [evidence-model.md:187](evidence-model.md#L187)–[:188](evidence-model.md#L188) | `AuditEvent.seq` and `subject`; `causal_parent`; the `Project → AuditEvent` total order; §3.4's ordering rules. | Untouched, and **read** by §5.3's `pos` and `AX-19`(c) (`GR26-R1`, `R13.26`). `seq` is the frozen per-project total order and this document acquires no second notion of "earlier": amendment 16 already compares by it ([evidence-model.md:178](evidence-model.md#L178), `R8.1`). No field, entity or ordering is added, `causal_parent` stays advisory, and no verification check of [evidence-model.md:173](evidence-model.md#L173)–[:178](evidence-model.md#L178) is weakened. |
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
| [transition-matrix.md:394](transition-matrix.md#L394)–[:397](transition-matrix.md#L397), [:399](transition-matrix.md#L399)–[:401](transition-matrix.md#L401) | The rest of §7.5 and its prose, including terminality. | Untouched — **conditionally**, not independently. `AX-19`'s grant ends by [:396](transition-matrix.md#L396) or [:397](transition-matrix.md#L397) and takes no `VALID → CONSUMED`, so [:394](transition-matrix.md#L394)'s discharge predicate and [:401](transition-matrix.md#L401)'s terminal states need no change; that holds **because** `AX-19`(a) chose non-recording, and would not survive a different lifetime choice (`R6.5`). [:395](transition-matrix.md#L395) is unreachable for a grant §5.3 step 1 admits, because that step's subject conjunct puts the decision inside [domain-model.md:702](domain-model.md#L702)'s non-snapshot-bound set; it stays perfectly reachable for the decisions step 1 rejects, and this document claims nothing about those (`R13.25`). Only [:393](transition-matrix.md#L393)'s evidence cell is amended; [:399](transition-matrix.md#L399) supports `AX-15`'s `AUTO`, not the holding. |
| [transition-matrix.md:485](transition-matrix.md#L485) | Creation by a non-human is `NONE_GRANTABLE`. | Untouched, and cited in §6.2: it connects human origination of a project with its ceiling. |
| `design/schema/**`, [roadmap_adapter.md](roadmap_adapter.md), [worker_provider.md](worker_provider.md) | Frozen schemas and adapter interfaces. | No JSON field or enum is added, and no frozen enum is amended — including [domain-model.md:393](domain-model.md#L393)'s `denied_capabilities` reasons, whose seven values stand exactly as frozen. `AX-8`'s eight-value denial vocabulary is a property of the denial `AuditEvent`'s `payload_ref` body, which no frozen field table or schema constrains, and is stated by amendment 9 itself as a choice (`R13.24`). The adapter's import requirement ([roadmap_adapter.md:56](roadmap_adapter.md#L56), [:57](roadmap_adapter.md#L57)) is satisfied by amendments 10–14 without an interface change, and its secret resolution ([:78](roadmap_adapter.md#L78), [:90](roadmap_adapter.md#L90)) is attributed by `AX-16`'s `on_behalf_of` rather than by requiring a `HUMAN` actor on a kernel-mediated event. |

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
| `R6.5` | derived | **chosen**, conditional half marked | Revision 03's "derived, on a different basis" is withdrawn. [authority-matrix.md:263](authority-matrix.md#L263) is an activation-time run-grant predicate and derives no project lifetime; [transition-matrix.md:394](transition-matrix.md#L394)'s non-application rests on the new premise that a project grant is recorded for no transition. The lifetime is now stated in full at `AX-19`(a)–(f) and labelled chosen, with the §7.5 no-amendment consequence marked conditional on it. |
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

Labels revision 04 corrected, per `DESIGN-04-025` and `-028`: **`R6.5` from derived to
chosen**, with its §7.5 no-amendment consequence marked conditional on that choice; **`R13.22`
from derived to split**, in the list above; `R13.19` restated again so that only its part (ii)
is asserted; `R13.21` corrected on the export count; `R13.14` corrected on the four-event kind
assertion. `R13.23` is chosen.

Labels and rules revision 05 adds or corrects, per `DESIGN-04-028`, `-029`, `-030` and
`-031`: `R13.22`'s **rule cell** is rewritten to match its already-split basis — revision 04
changed the summary list and left the cell asserting the opposite, and its claim that both
were repaired is withdrawn (§6.3). `R13.24` (the denial event's reason vocabulary) is **new
and chosen**. `R13.25` (the admitted subject profile) is **new and split**: chosen for the
restriction, derived for the `STALE` exclusion that follows from it. `R13.26` (retirement as
a chain-ordered historical fact) is **new and chosen**. `R6.5` keeps its chosen label and its conditional
half, and now names `R13.25` and `R13.26` as the two operands its end-set rests on rather than
assuming them. No other label changes, and no basis cell elsewhere is reopened.

Rules here: `R13.1`–`R13.20` less the withdrawn `R13.17`, plus `R13.21`, `R13.22`, `R13.23`,
`R13.24`, `R13.25` and `R13.26`.
Chosen: `R13.2`, `R13.3`, `R13.6`, `R13.8`, `R13.9`, `R13.11`, `R13.19`, `R13.21`,
`R13.23`, `R13.24`, `R13.26`. Conditional: `R13.10`, `R13.14`, `R13.15`. Derived: `R13.1`,
`R13.4` (possession half), `R13.7`, `R13.12`, `R13.13`, `R13.16`, `R13.18`, `R13.20`.
Split: `R13.5`, `R13.22`, `R13.25`. `R13.22` moves out of the derived list: only the *need*
for a distinction is derived, and selecting this execution-only scope is chosen
(`DESIGN-04-028`).

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
| `PP-6`, `PP-7` — no self-authorization; one decision, one field, one write. | Adopt `AX-16` or contest `R3.11` on the record: the performing actor may be `RUNTIME` with `on_behalf_of`, which `PP-6` treats as an integrity violation. This is the one substantive disagreement left between the documents. `PP-7` is consistent with §5.2. Now that `AX-20` is withdrawn, the standing grant needs no carve-out **given** `AX-19`(a)'s chosen non-recording; if `DESIGN-03` declines that choice, `PP-7` needs one, so this is a dependency on a chosen rule rather than on frozen text (`R6.5`). |
| `PP-8` — "This amendment adds no decision requirement to it." | Settled against `PP-8` by `DESIGN-04-FINDINGS-01` §5 and by `AX-14`: `AUTO` states the policy engine's contribution and does not discharge [authority-matrix.md:51](authority-matrix.md#L51). Adopt the decision requirement and `AX-17`'s four-event witness; the kind `APPROVE` keeps its chosen label. |
| §2.1, §2.2, §3 — ten-step admissibility, the decision profile, `project.ceiling.set`. | Rewrite §2.1 as a delta over §5.2, whose steps 1, 3, 4, 5, 7 and 9 it restates, keeping the `evidence_shown` content requirement, the payload predicates and the atomicity rule. §2.2 is unaffected: no field, enum or entity changes here. §3 is unaffected and is no longer a prerequisite of the first project grant (§6.2), though it remains the only specified way to change a ceiling after creation. |
| §6 — the initial `Project` state, `event_seq = 1`. | Superseded by `AX-17` and amendments 19–21: the witness ends at `event_seq = 3`. Cite the amended [evidence-model.md:128](evidence-model.md#L128), [:135](evidence-model.md#L135), [:136](evidence-model.md#L136); if `DESIGN-03` keeps an empty initial ceiling, state it as its own choice (§6.2). |

Ordering: `DESIGN-04` should be accepted first, since `DESIGN-03` stands on an authority path
that is not baseline text until these amendments land. Nothing in this section is due yet:
`DESIGN-04` is not accepted, and the changes above become due only if and when it is. The
`PP-4`/`PP-5` and §6 entries in particular inherit the chosen grant lifetime, so they also
inherit whatever the owner disposes on `-025`, `-029` and `-030` (§6.5). Per the review
method, the reviewer of a revised `DESIGN-03` is the reviewer that raised
`DESIGN-03-FINDINGS-01`, and this document's author does not review it. The same rule binds
this document: its author does not review it, and `DESIGN-04-FINDINGS-01`…`-04`'s reviewer is
the reviewer of this revision.

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
| `AX-20`'s standing-grant consumption lifecycle. | 02 | **Withdrawn** (`R6.5`). It invoked `VALID → CONSUMED` with no discharge, overlapped [transition-matrix.md:396](transition-matrix.md#L396), and was unreachable once [:401](transition-matrix.md#L401) makes those states terminal. The replacement at `AX-19`(a)–(f) needs no amendment to §7.5, conditionally on its own chosen premise. |
| That the replacement project-grant lifetime is **derived** from [authority-matrix.md:263](authority-matrix.md#L263), [transition-matrix.md:394](transition-matrix.md#L394) and [:396](transition-matrix.md#L396). | 03 | **Withdrawn** (`DESIGN-04-025`). Those lines supply ending machinery and an activation-time run-grant predicate; they derive neither project scope, nor non-consumption after an act, nor a complete end-set. The lifetime is restated as chosen at `AX-19`(a)–(f) and its endings completed, including revocation and the `PROJECT`-scope boundary that revision 03 left unspecified. |
| Policy-evaluation and chain-verification records are `CLAIM` by the runtime (`R13.17`). | 02 | **Withdrawn** in full: from amendment 16, §2.21, the inventory, §3 and §6. Those cells are unclosed (§6.4). |
| `DEC` at [transition-matrix.md:171](transition-matrix.md#L171) is satisfied by a decision "live at that resolution". | 02 | **Withdrawn.** A cited decision must be `VALID` at the consuming transition ([:74](transition-matrix.md#L74), [authority-matrix.md:289](authority-matrix.md#L289), [transition-matrix.md:522](transition-matrix.md#L522)). The row is retained as unclosed (§6.4). |
| All fourteen `DESIGN-04-FINDINGS-01` findings are closed, and all 44 inventory rows are typed. | 02 | **Withdrawn.** The review sustains nine of fourteen as closed; §0 records this revision's own dispositions, and §2.22 separates typed rows from unclosed ones. |
| That a project-scope or per-act denial is recorded "with the same reason vocabulary as `denied_capabilities`". | 04 | **Withdrawn** (`DESIGN-04-029`, `R13.24`). The vocabulary it named is a closed enum without `REVOKED`, which §5.3 step 5a simultaneously mandated; amendment 9 now states the denial event's own eight-value vocabulary and leaves [domain-model.md:393](domain-model.md#L393) alone. |
| That `AX-19`(e)'s exclusion of [transition-matrix.md:395](transition-matrix.md#L395) follows from a project grant's `scope`. | 04 | **Withdrawn** (`DESIGN-04-030`, `R13.25`). [domain-model.md:702](domain-model.md#L702) exempts a `GRANT_CAPABILITY` by its **subject**, and `scope` ([:700](domain-model.md#L700)) and `subject` ([:692](domain-model.md#L692)) are independent. The exclusion now follows from §5.3 step 1's admitted subject profile; the claim that it followed from scope alone was false, and revision 04's exhaustive end-set was unsound for every other profile it admitted. |
| That a capability is retired only while the revoking decision is currently `VALID`. | 04 | **Withdrawn** (`R13.26`). §5.3 step 5a's "later `VALID`" filter contradicted `AX-19`(c)'s own word "permanently": a revocation that expired would have restored the grant. Retirement is now the recorded historical fact. |
| That a capability is retired by **any** recorded revocation covering the project, whatever its position relative to the grant. | 05 | **Withdrawn** (`GR26-R1`, `R13.26`). This revision's first step 5a matched every `REVOKE_CAPABILITY` that had reached `VALID` and was not `VOID`, with no relation to the grant being resolved, so on the history `G1 → R → G2` it denied `REVOKED` under `G2` as well — which made `AX-19`(c)'s "only a new `GRANT_CAPABILITY` decision can [restore `c`]" unsatisfiable and every later grant of a once-revoked capability a dead letter. Retirement is now ordered by the project's audit chain (`pos`, §5.3), and reaches only grants realized before the revocation. The historical-fact reading of the row above is retained and is unaffected. |
| That [transition-matrix.md:270](transition-matrix.md#L270)'s policy-change branch names a policy-evaluation record. | 04 | **Withdrawn** (`DESIGN-04-031`). The row prints "the triggering record" and names no kind; only [:157](transition-matrix.md#L157) and [:170](transition-matrix.md#L170) name a policy evaluation or re-evaluation record. The attribution is removed from §2.22, §6.4 and `KD-3`; the branch stays open for the record the row actually means, and none is chosen here. |
| That `R13.22`'s rule cell and summary label were both repaired, and that frozen `A-INV-2` "covers only the second" authority. | 04 | **Withdrawn** (`DESIGN-04-028`). The summary list was corrected and the rule cell was not; [domain-model.md:410](domain-model.md#L410) is unqualified and draws no execution/governance distinction, which is why amendment 23 narrows it rather than reading it. |
| Revision 04's own size and proposed-text accounting: "1043 lines", and a changed-proposed-text list that omitted `AX-18`. | 04 | **Withdrawn** as inaccurate ([FINDINGS-04:62](review/DESIGN-04-FINDINGS-04.md#L62)). Bookkeeping only; it determined no closure. Revision 05's own accounting is in the front matter and §7. |
| That "nothing here is implemented" describes the current state of the repository. | 04 | **Withdrawn as stated.** It was true when revision 04 was written and is not now: `GR-23` implements part of `AX-17`'s four-event sequence. *This document* changes no code, but the register must distinguish partial implementation from conformance, which is `KD-15` ([FINDINGS-04:105](review/DESIGN-04-FINDINGS-04.md#L105)). |
| That `DESIGN-04-029`…`-036` have no owner disposition yet. | 05 | **Withdrawn as false** (`GR26-R3`). `DESIGN-04-FINDINGS-04` §6's table carries an owner blocking flag for each of the eight — `-029` true, `-030` true, `-031` false, `-032`…`-036` true ([FINDINGS-04:155](review/DESIGN-04-FINDINGS-04.md#L155)–[:162](review/DESIGN-04-FINDINGS-04.md#L162)). That record's prose saying the new cells are blank ([:17](review/DESIGN-04-FINDINGS-04.md#L17), [:151](review/DESIGN-04-FINDINGS-04.md#L151)) is stale and does not govern its own tables, exactly as [CLAUDE.md:99](../CLAUDE.md#L99)–[:102](../CLAUDE.md#L102) records for `DISPOSITION-01`. The flags are reproduced in §0 and §7 and are set by no one but the owner; the immutable record is unchanged. |

### 6.4 Cells and acts these amendments do not close

Carried forward as work for a later corrective record, alongside `D01-F02-007`, `-008`,
`-009` and `-010` (§1.4), and alongside `D01-F02-005`, whose closure here rests entirely on
chosen rules (§6.2, `R6.5`, `R13.24`, `R13.25`). None is claimed closed anywhere in this
document. Every entry below appears in §8, which is the single register of what is open; §8
adds the five `D01-F02` identifiers and the two disclosed debts `KD-16` and `KD-17`, and
repeats nothing else.

| unclosed item | why, and what a later record must decide |
|---|---|
| The policy-evaluation cells at [transition-matrix.md:157](transition-matrix.md#L157) and [:170](transition-matrix.md#L170) | A policy evaluation is not one of `G-1`'s five evidence entities and is not an activation, decision, escalation or an `AuditEvent` the row names, so `G-1` admits no kind for it. Revision 02 typed it `CLAIM` by the runtime; that typing is **withdrawn** — [evidence-model.md:63](evidence-model.md#L63) and [:85](evidence-model.md#L85) do not supply it. Closing these cells means either a new admissible kind or a widened `G-1`, which is outside these five findings. |
| The verification-record cells at [transition-matrix.md:161](transition-matrix.md#L161), [:167](transition-matrix.md#L167), [:174](transition-matrix.md#L174), [:175](transition-matrix.md#L175) and [:397](transition-matrix.md#L397) | Same reason. At [:161](transition-matrix.md#L161) the `ESC(OPEN)` alternative is typed and usable, which does not close the verification alternative; at [:174](transition-matrix.md#L174) the verification record is a conjunct that `DEC(OVERRIDE)` cannot replace. |
| [transition-matrix.md:171](transition-matrix.md#L171), **case A — the consumed decision** | The cell requires the `DEC` each resolution referenced, and [:74](transition-matrix.md#L74), [authority-matrix.md:289](authority-matrix.md#L289) and [transition-matrix.md:522](transition-matrix.md#L522) require a cited decision to be `VALID` at *this* transition — while a resolution decision is `CONSUMED` by the resolution it discharged ([:394](transition-matrix.md#L394)), and `CONSUMED` is terminal ([:401](transition-matrix.md#L401)). Typing cannot close it, and revision 02's "live at that resolution" reading is withdrawn: it weakened decision currency. A later record must either relax the currency rule for a retrospective citation, change what this cell cites, or state that a consumed decision is citable as history and is not authority here. |
| [transition-matrix.md:171](transition-matrix.md#L171), **case B — the absent decision** | The row fires when every bound escalation has `status ∈ {RESOLVED, WITHDRAWN}`, and two of the ways to reach those states produce no decision at all: [:414](transition-matrix.md#L414) resolves on `auto_resolvable = true` against a `SNAP`/`VR(pass)` showing the condition cleared, and [:416](transition-matrix.md#L416) withdraws against the same. The cell still prints `DEC` referenced by each resolution, and there is none to name. This is **not** the same defect as case A and is not closed by fixing it: a later record must say what discharges the cell when a resolution referenced no decision. Revision 03 carried the row but explained only case A. |
| The triggering-record alternatives at [transition-matrix.md:270](transition-matrix.md#L270) | The cell reads `DEC(REVOKE_CAPABILITY)` **or** the triggering record, over four preconditions: human revocation, policy change, scope breach, integrity violation. Only the `DEC` branch is typed. For the other three conditions the row names **no record kind whatever**: it prints "the triggering record" and stops. That is the obstruction, and it is more basic than a typing question — there is no operand to type. Revision 04 said the policy-change branch names a policy-evaluation record; it does not, and that attribution is withdrawn (`DESIGN-04-031`, §6.3). [:157](transition-matrix.md#L157) and [:170](transition-matrix.md#L170) do name such a record and are `KD-1`; this row is **not** an instance of them. A **scope breach** or **integrity violation** may additionally fire from a comparison that persists no record, and a precondition cannot discharge a cell the row separately prints — the same obstruction as [:412](transition-matrix.md#L412) below. Where a condition does persist an admissible record, such as a denial `AuditEvent`, that instance is typed; the row as a whole is not. A later record must decide which record each of the three non-`DEC` conditions cites — choosing and justifying a representation rather than attributing one to the frozen text — or state that the `DEC` branch is mandatory whenever the others produce none. Revision 03 named this in §2.22 and pointed here, but did not carry it and counted it among the typed rows. This is also where `DESIGN-04-020`'s residual mapping obligation sits (§0). |
| The triggering-record cell at [transition-matrix.md:412](transition-matrix.md#L412) for comparison triggers | Where the fired trigger is a comparison over entity fields — `DEADLINE_EXCEEDED`, `REPEATED_FAILURE` ([domain-model.md:761](domain-model.md#L761), [:762](domain-model.md#L762)) — no record is persisted to cite, and a precondition cannot discharge a separately printed cell. Triggers that do name a record, such as `CAPABILITY_DENIED` ([domain-model.md:758](domain-model.md#L758)) citing the denial event, are typed. |
| `policy.override`, `commit.publish`, `audit.redact`, `secret.read`, `net.egress.any`, `proc.exec.arbitrary` | Each has an authority form and no legal row, so §5.2's procedure cannot bind it; the last three are exercised inside execution rather than at a transition (§6.1). |
| The `Escalation.severity` and `auto_resolvable` derivation | Amendment 18 gates on these fields; the frozen models do not fully specify them. `severity` ([domain-model.md:738](domain-model.md#L738)) is required, **mutable** and runtime-supplied, with no general assignment function, no trigger-to-severity table and no default: the only fixed assignment anywhere is `MEDIUM` for a monotonic-time `INTEGRITY_VIOLATION` ([evidence-model.md:177](evidence-model.md#L177)), and the only specified change is the one-level increase on expiry and reopen ([transition-matrix.md:415](transition-matrix.md#L415), [:418](transition-matrix.md#L418)–[:419](transition-matrix.md#L419)), which fixes no saturation at `CRITICAL` and no window. `auto_resolvable` ([:746](domain-model.md#L746)) is derived and **immutable**, and its rule is a false-condition only — false if `severity ≥ HIGH` or mode `SUPERVISED` — not an iff, so nothing determines its value in the remaining cases, and nothing reconciles an immutable derived field with a mutable input. Expiry sidesteps this by creating a new `Escalation` rather than mutating the old one; in-place severity change does not. A later record must supply the assignment function and the field-update boundary, or state that these fields gate only as far as the specified assignments reach. Until then the existing `HIGH`/`SUPERVISED` false rule and the prohibition on runtime resolution without a `HumanDecision` ([authority-matrix.md:142](authority-matrix.md#L142), [transition-matrix.md:414](transition-matrix.md#L414)) are retained and are the whole of what is claimed. |
| Rows for the four governance writes | `project.mode.set`, `policy.set`, `budget.grant`, `budget.extend` have an authority form and no row; that is `DESIGN-03`'s subject (§5). |
| The `C`/`D` tension in §4.1 | [authority-matrix.md:203](authority-matrix.md#L203) and [:206](authority-matrix.md#L206) give `C` cells to `HUMAN`-class capabilities that [:221](authority-matrix.md#L221) denies to every role. Pre-existing, not one of the five findings, and no amendment depends on resolving it. |
| The inherited `CLAIM`-boundary tensions | Two boundaries that predate this correction and that amendment 18 **does not repair**, now that `R13.19`(i) expressly permits worker-caused stop and require-human influence. (a) `S-INV-3` ([domain-model.md:254](domain-model.md#L254)–[:256](domain-model.md#L256)) makes a worker's own `declared_status` ([:203](domain-model.md#L203)), combined with measured dissatisfaction, **require** an `Escalation`, while `G-6` ([:892](domain-model.md#L892)) says `declared_status` never appears in any precondition of any transition and [transition-matrix.md:505](transition-matrix.md#L505) makes writing it to gate a transition `NONE_GRANTABLE`. (b) [worker_provider.md:146](worker_provider.md#L146)–[:147](worker_provider.md#L147) states that steps 8–12 — receipt, validation, review, recomputation — are the **only** path by which anything a worker produced can affect stage state, while [transition-matrix.md:128](transition-matrix.md#L128) and [:158](transition-matrix.md#L158) admit escalation control paths that this document types as admissible prerequisites. Raised at [FINDINGS-02:72](review/DESIGN-04-FINDINGS-02.md#L72) and [FINDINGS-03:69](review/DESIGN-04-FINDINGS-03.md#L69); neither is repaired here, neither is a claim that a worker can manufacture evidence or bypass a human, and `KD-8`'s missing field derivation is a different question. A later record must either reconcile the frozen sentences or state which yields. |
| Implementation conformance | This document changes no code. `GR-23` implements part of `AX-17`'s four-event sequence; `FINDINGS-04` §5 reports five independent departures on the successful creation path — mode, creator and event attribution, `chosen` against `options_offered`, missing `SIGNATURE` evidence, and manufactured `evidence_shown` (`DESIGN-04-032`…`-036`). §2.23 states the requirements; it repairs nothing and asserts no conformance. |

### 6.5 The grant/lifetime repair: what was chosen, and the decision it leaves open

[FINDINGS-04:176](review/DESIGN-04-FINDINGS-04.md#L176) offers the author two routes:
reconcile the revocation vocabulary and the subject/lifetime rules, **or** withdraw the
project-grant/lifetime repair and explicitly leave `D01-F02-005` open. This revision takes
the first route. The repair is **not** withdrawn, and the consequences of withdrawing it are
stated below so the alternative is a real option for the owner rather than an implied one.

Three choices carry the repair. Each had at least one available alternative, and the
alternative was rejected on the record, not overlooked.

| decision | chosen here | alternatives, and why not |
|---|---|---|
| The denial reason for a retired capability (`-029`, `R13.24`) | State the denial `AuditEvent`'s own vocabulary: [domain-model.md:393](domain-model.md#L393)'s seven values **plus `REVOKED`**, for §5.2/§5.3 denials only. The frozen enum and `denied_capabilities` are untouched, and the event's payload is unconstrained by any frozen field table. | **(i) Amend [domain-model.md:393](domain-model.md#L393) to add `REVOKED`.** Rejected: it would change a closed enum on a record a project-scope denial never writes, add a twenty-fourth amendment and a consumer audit, and widen the correction's surface for no gain. It remains available if the owner prefers one vocabulary everywhere. **(ii) Reuse an existing value — `NO_GRANTOR` or `POLICY`.** Rejected as false: the grantor existed and granted, and a human revocation is not a policy outcome. It would also make retirement indistinguishable from absence of a grantor in the record, which is what `AX-8` exists to prevent. |
| The admitted subject profile (`-030`, `R13.25`) | Admit only `subject.kind ∈ {PROJECT, CAPABILITY}`, on a decision whose `project_id` is this project, which is exactly [domain-model.md:702](domain-model.md#L702)'s non-snapshot-bound profile, so `AX-19`(e)'s `STALE` exclusion and (f)'s exhaustiveness follow from the admission rule. The project binding is `project_id` ([:691](domain-model.md#L691)); `subject.id` is constrained only in the `PROJECT` case, since the frozen model gives a `CAPABILITY` subject's `Id` no referent. | **Admit every subject profile and add `STALE` to the end-set.** Rejected: a snapshot-bound project grant would need a `subject_snapshot_id` ([domain-model.md:703](domain-model.md#L703)) and so a `COMPLETE` snapshot over a stage that the bootstrap acts exist to create, and `HD-INV-4` would then retire the project's authority whenever any later snapshot touched that stage — which is the opposite of a standing grant. It is coherent but a different and worse design; if the owner prefers it, `AX-19`(e)/(f), §5.3 step 0 and `R6.5` all change together. |
| The meaning of "retired", and which grants a revocation reaches (`R13.26`) | Retirement is the recorded historical fact, **ordered on the project's audit chain**: `c` is retired from grant `G` by revocation `R` exactly when `R` has reached `VALID`, is not `VOID`, and `pos(R) > pos(G)` — `pos(D)` being the `seq` of the `AuditEvent` `AE-INV-2` requires for `D`'s `∅ → VALID` transition. Retirement survives `R` leaving `VALID`; it does not reach a grant recorded after `R`. | **(i) Test the revoking decision's current state.** Rejected: it contradicts `AX-19`(c)'s "permanently", and an expiring revocation would silently restore a capability a human removed. It is what revision 04's step 5a literally said. **(ii) Match any recorded revocation, unordered.** Rejected as incoherent, and it is what this revision's own first step 5a said (§6.3, `GR26-R1`): on `G1 → R → G2` it retires `c` from `G2`, contradicting the same clause's statement that a new `GRANT_CAPABILITY` decision is what restores `c`. **(iii) Order by `decided_at` or `recorded_at`.** Rejected: these are clock readings, not the project's order of record — [domain-model.md:782](domain-model.md#L782) marks `recorded_at` "runtime clock only", [:792](domain-model.md#L792) records the skew against a reference clock, and [evidence-model.md:177](evidence-model.md#L177) only requires `recorded_at` to be non-decreasing in `seq` *within* that skew, which makes `seq` the primary and the timestamp the derivative. Choosing a clock would be inventing an ordering the frozen design declines to treat as authoritative ([:187](evidence-model.md#L187)). **(iv) Order by `HumanDecision.prev_event_hash` ([domain-model.md:712](domain-model.md#L712), `G-5`).** Rejected as underdetermined rather than wrong: the field links a decision to the chain, but the frozen text does not fix whether it names the head before or after the decision's own recording event, so two decisions can carry the same predecessor hash and the relation is not a total order. Where it is unambiguous it agrees with `pos`, and an implementation may use it to reconstruct `pos`. |

**If the owner instead directs withdrawal of the project-grant form and its lifetime**, then:
`D01-F02-005` — "initial import and first contract creation require activation authority
before the stage/contract/run structure supporting that authority has been established",
`CONFIRMED` by `VERIFY-01` and flagged **blocking: true** — **remains open**, and must be
recorded as open rather than deferred. It would remain open because the circularity is in
the frozen text and nothing else in this correction touches it: [transition-matrix.md:117](transition-matrix.md#L117)'s
first `roadmap.import` and [:265](transition-matrix.md#L265)'s first `contract.author` are
`ORD` capabilities needing a grant; `AX-3` as frozen realizes a grant only per
`ContractActivationRecord` scoped to one `StageRun`; [evidence-model.md:95](evidence-model.md#L95)
realizes a decision's grant only through an activation; and an activation must cite the
contract ([domain-model.md:388](domain-model.md#L388)) and run ([:390](domain-model.md#L390))
that those very acts create. Amendments 6–8, 10, 11 and 14 exist only to break that loop; §5
of this document and `DESIGN-03`'s provisioning path both stand on them. Withdrawal would
therefore also withdraw the `D01-F02-005` half of amendments 6, 7, 8, 10, 11, 14 and 22,
return `AX-4`, `AX-11`, `C-INV-3`, `AX-3` and the promotion rule to their frozen wording, and
leave `KD-9` recording an **open blocking finding** rather than a conditional closure.
`D01-F02-001`, `-002`, `-003` (partially) and `-004` would be unaffected: they rest on
amendments 1–5, 12, 13 and 15–21, none of which needs the project grant.

The decision is the owner's, and this document does not presume it. What it does not do is
withdraw the repair silently or leave `D01-F02-005` described as closed while its mechanism
is in doubt.

## 7. Author verification of this document

**This section is the author's own checking and is not a review.** `FINDINGS-04` records that
revision 04's equivalent section was read as though it were verification and was not
([FINDINGS-04:78](review/DESIGN-04-FINDINGS-04.md#L78)); the same limit applies here and is
stated rather than implied. Mechanical checks — citation resolution, byte-identity of quoted
frozen text, counts — reproduce and are reported below. **Closure claims do not.** Whether
`-025`, `-028`, `-029`, `-030` and `-031` are actually closed, and whether the repaired
lifetime is coherent, is for the reviewer of this revision to determine; §0 labels every such
claim **proposed**. Per `CLAUDE.md`'s review method a full independent pass, not a delta
review, is what precedes any acceptance, and the reviewer is the one that raised
`DESIGN-04-FINDINGS-01`…`-04`.

| check | result |
|---|---|
| Citation resolution | Every `file:line` was resolved against the tag with `git show design-01-frozen:design/<file> \| sed -n '<line>p'` before it was written, and all citations were re-resolved afterwards. None is out of range; none lands on a blank line. Citations into `design/review/` were resolved against the working-tree records, which are committed evidence. |
| Quoted frozen text | All twenty-three amendment targets were compared byte-for-byte against their frozen lines, including the two-line `C-INV-3` block and the repeated §5.1 insertion anchor, and all twenty-three quoted blocks are byte-identical to revisions 03 and 04. |
| Proposed-text delta | Revision 05 changes **three** proposed texts, carried in **two** fenced blocks, and no target. Block-by-block comparison of all 46 fenced blocks in revisions 04 and 05 reports exactly two differing: amendment 9's `AX-8` (the denial reason vocabulary), and amendment 14's §5.3 insertion, whose §5.3 body and `AX-19` both change while its `AX-18` and `AX-20` are byte-identical. Within that insertion the changed parts are the new ordering paragraph defining `pos` and steps 1, 5a, 6 and 7 of the step table, and `AX-19` clauses (a), (c), (e) and (f) — (a), (c) and (f) by the `GR-26` remediation (`GR26-R1`), the rest as revision 05 first stood. `AX-19`(b) and (d) are unchanged from revision 04. The other 44 blocks — all twenty-three frozen quotations and every other proposed text, amendments 10, 22 and 23 included — are byte-identical to revision 04. Amendment 23's proposed `A-INV-2` is unchanged in particular, since `-028` is a defect of the rule cell beside it and not of the proposed invariant. |
| Inventory coverage | §2.22 accounts for all 44 rows of the review's inventory and states which are typed and which remain unclosed: **thirty-nine typed end to end, five not** — [transition-matrix.md:161](transition-matrix.md#L161), [:170](transition-matrix.md#L170), [:174](transition-matrix.md#L174), [:270](transition-matrix.md#L270), [:171](transition-matrix.md#L171). Revision 05 changes no row's typing and no count: the `-031` repair removes an attribution from an already-unclosed row. §2.21 types every record kind `G-1` admits and names the kinds it does not. The count of `ESC` evidence rows is twelve. |
| Exhaustive claims | `R3.5`'s `AUTO`-row claim and `R13.16`'s seven-of-seventeen claim were re-derived from the frozen matrix's `required_capability` column against the seventeen `HUMAN`-class register rows. |
| Finding coverage | Each of the twenty-three amendments names at least one `D01-F02` finding. All **thirty-six** `DESIGN-04` findings have a disposition in §0. The thirty-one proposal findings are dispositioned with the `file:line` that closes them, as **proposed** closures; `-032`…`-036` are dispositioned as implementation findings this document does not repair. Four `D01-F02` findings are closed; `D01-F02-003` is partially closed and says so in §0, §1.1, amendment 13 and §6.1; `D01-F02-005`'s closure rests on chosen rules and is registered at §8 `KD-9`. |
| Register synchronization | Every row §2.22 sends to §6.4 has an entry there, and every §6.4 entry appears in §8; the two lists were compared entry by entry, including the entries added here (`KD-14`, `KD-15`, and `KD-16`/`KD-17` from the `GR-26` remediation) and the `-031` correction to `KD-3`. `KD-16` and `KD-17` are the two entries §8 carries that §6.4 does not, which §6.4's own sentence now states; §8 remains one contiguous table, `KD-1` through `KD-17`. Every finding `FINDINGS-04` records as open or partially closed appears in §0 and, where it survives, in §8. |
| Dispositions | Severity and blocking flags are reproduced as recorded. No disposition, blocking flag or review record was changed, and no file under `design/review/` was modified. **Every blocking slot in `DESIGN-04-FINDINGS-03` and `-04` remains as those records left it, and no flag is reproduced here as a new judgment. The owner's dispositions for `-001`…`-028` are [DISPOSITION-01.md](review/DISPOSITION-01.md)'s tables; those for `-029`…`-036` are `DESIGN-04-FINDINGS-04` §6's table — `-029` true, `-030` true, `-031` false, `-032`…`-036` true ([FINDINGS-04:155](review/DESIGN-04-FINDINGS-04.md#L155)–[:162](review/DESIGN-04-FINDINGS-04.md#L162)) — restated in §0. Revision 05 first said `-029`…`-036` had no owner disposition yet; that was false, it is withdrawn (§6.3, `GR26-R3`), and it is the reason the corrected statement cites the tables rather than either record's prose. In both records the tables govern and the prose saying the cells are blank is stale ([DISPOSITION-01:20](review/DISPOSITION-01.md#L20)–[:21](review/DISPOSITION-01.md#L21), [FINDINGS-04:17](review/DESIGN-04-FINDINGS-04.md#L17), [:151](review/DESIGN-04-FINDINGS-04.md#L151); [CLAUDE.md:99](../CLAUDE.md#L99)–[:102](../CLAUDE.md#L102)). No file under `design/review/` was modified.** |
| Frozen text | No frozen design file, schema or implementation file was edited. Revisions 01, 02, 03 and 04 are unchanged on disk; revision 04 still hashes to the SHA-256 `DESIGN-04-FINDINGS-04` recorded. No commit, tag or branch operation was performed, and no file under `src/` or `tests/` was read for edit or changed. |
| Version terms | `SCHEMA_VERSION` appears only as the domain-model version feeding the genesis hash, with the implementation binding labelled separately (`R10.3`). `STORAGE_VERSION` and `PRAGMA user_version` appear only to say they are a different thing. |

---

## 8. Known defects — the register

This is the **register**, not a promise. It records what is open in this correction, by
identifier, so that nothing on it can later be mistaken for closed. Nothing here is
scheduled, undertaken or assigned by this document. Each entry names the frozen text that
obstructs it and what a later record would have to decide; none of that constitutes a
commitment that a later record will exist. Revision 04 titled this "at freeze"; nothing is
frozen, so the register is simply of what is open now.

`FINDINGS-04` §4 made three requirements of this register, and all three are met here.
**(1)** It must carry the defects *inside* the chosen grant, not merely the dependence on a
choice. `-029` and `-030` were those defects; both are repaired in §2 rather than registered,
`KD-9` is rewritten accordingly, and `-031` and the `R13.22` cell are likewise repaired and
withdrawn in §6.3 rather than deferred. **(2)** The inherited `CLAIM`-boundary tensions must
be carried explicitly and not absorbed into `KD-8`'s missing field derivation: they are
`KD-14`. **(3)** A current record must distinguish `GR-23`'s partial implementation of
`AX-17` from conformance to it: that is `KD-15`, with the requirements themselves in §2.23.

`KD-16` and `KD-17` are added by the `GR-26` remediation (`GR26-R2`). Both are **documentary
synchronization only**: each is an open debt this document had already disclosed in a rule
cell — the §5.2 denial-reason mapping at `R13.24`, and the `CAPABILITY`-subject referent at
`R13.25` and §5.3 step 1 — and neither is solved, designed or narrowed here. Both are
**nonblocking for this bounded correction**: no closure claimed in §0 and no clause of
`AX-19` rests on either, which is why they are registered rather than repaired. Registering
them keeps the register, and not only a rule cell, the single place where an open debt can be
found.

Entries repeat material stated in §2.21, §2.22, §2.23, §6.1, §6.4, §1.4 and, for `KD-16` and
`KD-17`, the `R13.24`/`R13.25` rule cells. Where the register and those sections differ, they
are in conflict and the document is defective; they were compared entry by entry (§7).

| id | item | status |
|---|---|---|
| `KD-1` | **Policy-evaluation record cells:** [transition-matrix.md:157](transition-matrix.md#L157), [:170](transition-matrix.md#L170) | **NOT CLOSED.** A policy evaluation is none of `G-1`'s five evidence entities and none of its four prerequisite kinds, so `G-1` admits no kind for it. Revision 02's `CLAIM`-by-the-runtime typing is withdrawn and not replaced: [evidence-model.md:63](evidence-model.md#L63) restricts `EVIDENCE` minting without making a non-qualifying record a `CLAIM`, and [:85](evidence-model.md#L85) classifies only `Escalation`. At [:170](transition-matrix.md#L170) the `DEC(OVERRIDE)` alternative is typed and usable; that does not close the policy alternative. Closing needs a new admissible kind or a widened `G-1`, outside these five findings. |
| `KD-2` | **Chain-verification record cells:** [transition-matrix.md:161](transition-matrix.md#L161), [:167](transition-matrix.md#L167), [:174](transition-matrix.md#L174), [:175](transition-matrix.md#L175), [:397](transition-matrix.md#L397) | **NOT CLOSED**, for the same reason as `KD-1`. At [:161](transition-matrix.md#L161) the `ESC(OPEN)` alternative is typed; at [:174](transition-matrix.md#L174) the verification record is a **conjunct** that `DEC(OVERRIDE)` cannot replace. [:397](transition-matrix.md#L397) is also the `VOID` route `AX-19`(e) leaves available to a project grant, so this cell is load-bearing for repair 1's end-set. |
| `KD-3` | **The triggering-record alternatives at [transition-matrix.md:270](transition-matrix.md#L270)** | **NOT CLOSED.** Only the `DEC(REVOKE_CAPABILITY)` branch is typed. For the row's other three preconditions the cell prints "the triggering record" and names **no record kind at all**, so there is no operand to type — a more basic obstruction than `KD-1`'s, and **not** an instance of it: revision 04's attribution of a policy-evaluation record to the policy-change branch is withdrawn (`DESIGN-04-031`, §6.3), and [:157](transition-matrix.md#L157)/[:170](transition-matrix.md#L170) name such a record where this row does not. A **scope breach** or **integrity violation** may additionally fire from a comparison persisting no record, which cannot discharge a separately printed cell (`KD-4`). Where such a condition does persist an admissible record, that instance is typed; the row is not. Revision 03 sent this row to §6.4 and then omitted it, counting it among forty typed rows; the count is **thirty-nine of 44** and the row is carried. This entry also carries `DESIGN-04-020`'s residual mapping obligation, which `-008`'s permitted delimitation does not discharge (§0). |
| `KD-4` | **The triggering-record cell at [transition-matrix.md:412](transition-matrix.md#L412) for comparison triggers** | **NOT CLOSED.** Where the fired trigger is a comparison over entity fields — `DEADLINE_EXCEEDED`, `REPEATED_FAILURE` ([domain-model.md:761](domain-model.md#L761), [:762](domain-model.md#L762)) — no record is persisted to cite, and a precondition does not discharge a cell the row prints separately. Triggers that do name a record, such as `CAPABILITY_DENIED` ([:758](domain-model.md#L758)) citing the denial event, are typed; a typed example closes no comparison. Like `KD-3`, this entry carries `DESIGN-04-020`'s residue as well as `-008`'s (§0). |
| `KD-5` | **[transition-matrix.md:171](transition-matrix.md#L171), case A — the consumed decision** | **NOT CLOSED.** The cell requires the `DEC` each resolution referenced; [:74](transition-matrix.md#L74), [authority-matrix.md:289](authority-matrix.md#L289) and [transition-matrix.md:522](transition-matrix.md#L522) require a cited decision to be `VALID` at *this* transition; a resolution decision is `CONSUMED` by the resolution it discharged ([:394](transition-matrix.md#L394)) and `CONSUMED` is terminal ([:401](transition-matrix.md#L401)). Typing cannot close it. Revision 02's "live at that resolution" reading is withdrawn as a weakening of decision currency. |
| `KD-6` | **[transition-matrix.md:171](transition-matrix.md#L171), case B — the absent decision** | **NOT CLOSED, and distinct from `KD-5`.** The row fires when every bound escalation has `status ∈ {RESOLVED, WITHDRAWN}`, and two routes to those states reference no decision at all: [:414](transition-matrix.md#L414) resolves on `auto_resolvable = true` against a `SNAP`/`VR(pass)`, and [:416](transition-matrix.md#L416) withdraws against the same. The cell still prints a `DEC`. Fixing `KD-5` does not close this; revision 03 carried the row but explained only `KD-5`. |
| `KD-7` | **The six `HUMAN` operations with no legal row:** `policy.override`, `commit.publish`, `audit.redact`, `secret.read`, `net.egress.any`, `proc.exec.arbitrary` ([authority-matrix.md:64](authority-matrix.md#L64), [:134](authority-matrix.md#L134), [:146](authority-matrix.md#L146), [:110](authority-matrix.md#L110), [:109](authority-matrix.md#L109), [:107](authority-matrix.md#L107)) | **NOT CLOSED.** Each has an authority form under §5.2 and **no passing admission path**, and a form with no admission path authorizes nothing. No legal row names any of them as `required_capability` — publication has prose only ([transition-matrix.md:381](transition-matrix.md#L381)–[:383](transition-matrix.md#L383)), redaction names its authority at [evidence-model.md:270](evidence-model.md#L270), and the last three are exercised **inside execution** rather than at a transition, so §5.2's row-reading steps 2, 5 and 8 cannot bind them. `AX-16` supplies attribution, not admission. What is missing is a point at which the exercise decision is presented and consumed — the same shape as `CLAUDE.md`'s `GR-17` gap. `D01-F02-003` is **partially** closed for exactly this reason. |
| `KD-8` | **The `Escalation.severity` and `auto_resolvable` derivation** | **NOT CLOSED**, and newly registered by repair 3. Amendment 18 gates on these fields; the frozen models do not fully specify them. `severity` ([domain-model.md:738](domain-model.md#L738)) is required, **mutable** and runtime-supplied with no general assignment function, no trigger-to-severity table and no default — the only fixed assignment is `MEDIUM` for a monotonic-time `INTEGRITY_VIOLATION` ([evidence-model.md:177](evidence-model.md#L177)), and the only specified change is the one-level increase on expiry and reopen ([transition-matrix.md:415](transition-matrix.md#L415), [:418](transition-matrix.md#L418)–[:419](transition-matrix.md#L419)), which fixes neither the window nor saturation at `CRITICAL`. `auto_resolvable` ([domain-model.md:746](domain-model.md#L746)) is derived and **immutable** with a false-condition rule only, not an iff, and nothing reconciles an immutable derived field with a mutable input. What **is** claimed and retained: the `HIGH`/`SUPERVISED` false rule, and that non-auto-resolvability requires a `HumanDecision` ([authority-matrix.md:142](authority-matrix.md#L142), [transition-matrix.md:414](transition-matrix.md#L414)). What is **not** claimed: any input-independence of these fields from worker-caused conditions (`R13.19`(i)). |
| `KD-9` | **`D01-F02-005`** — activation authority required before the structure supporting it exists | **Proposed closed in this document only on chosen premises**, and registered here so the dependency is not lost. Its closure rests on: the second grant form itself (`R4.1`–`R4.3`, chosen), the `AX-4` narrowing and role-table non-application (`R6.4`, conditional), the basis-citation destination (`R13.6`, chosen), the denial destination and its vocabulary (`R13.9`, `R13.24`, chosen), the **whole of the `AX-19` lifetime** (`R6.5`, chosen), its admitted subject profile (`R13.25`, split), its chain-ordered historical reading of retirement (`R13.26`, chosen), and §6.2's chosen non-empty initial ceiling. Frozen text forces none of these. `FINDINGS-04` held that even the conditional claim was too strong while `-029` and `-030` stood, because those were defects **inside** the choice — a vocabulary the rule could not use and an end-set the admission rule did not support — rather than consequences of it. Both are repaired in §2, so the conditional claim is restated: **if** the premises above are accepted, `-005`'s circularity is broken; the premises are the owner's to accept (§6.5). This remains a **proposed** closure: no reviewer has verified it. If the owner declines the project-grant form or the lifetime, `-005` reopens intact and §6.5 states exactly what else goes with it; its `VERIFY-01` `CONFIRMED` status and **blocking: true** flag are unaffected by anything here, and nothing in this document makes the operation executable. |
| `KD-10` | **`D01-F02-007`** — contract supersession | **NOT CLOSED**, out of scope (§1.4). `CONFIRMED` by `VERIFY-01`; needs an `ACTIVE` contract and a second contract for the same stage ([transition-matrix.md:269](transition-matrix.md#L269), [:273](transition-matrix.md#L273)). Amendments 15–18 change the **admissibility** of records [:269](transition-matrix.md#L269) cites and nothing else; the underlying defect is untouched. Must be closed before the first contract replacement. |
| `KD-11` | **`D01-F02-008`** — immutable run budget and deadline | **NOT CLOSED**, out of scope (§1.4). `CONFIRMED`; needs a run that consumed its immutable allocation ([transition-matrix.md:172](transition-matrix.md#L172), [:206](transition-matrix.md#L206), [domain-model.md:284](domain-model.md#L284), [:287](domain-model.md#L287)). Retyping `DEC(EXTEND_BUDGET)` does not extend them (§3). It is also why `budget.extend` is only half-assigned to `DESIGN-03` (§6.1). Must be closed before the first exhausted budget or passed deadline. |
| `KD-12` | **`D01-F02-009`** — reconciliation closure after restart | **NOT CLOSED**, out of scope (§1.4). `CONFIRMED`; needs a controller restart with prior-epoch operations ([evidence-model.md:167](evidence-model.md#L167)). Must be closed before the first restart leaving a live operation. |
| `KD-13` | **`D01-F02-010`** — divergent apply | **NOT CLOSED**, out of scope (§1.4). `CONFIRMED`; needs an intent that reached `APPLYING` ([transition-matrix.md:358](transition-matrix.md#L358), [:73](transition-matrix.md#L73)). [:358](transition-matrix.md#L358) is typed by §2.22 and keeps the finding. Must be closed before the first divergent apply. |
| `KD-14` | **The inherited `CLAIM`-boundary tensions:** `declared_status` against `G-6`, and the provider's "only path" against the escalation control paths | **NOT CLOSED**, carried explicitly and newly registered. Amendment 18 does not repair either, and `R13.19`(i) now expressly invokes the influence they are about, so they cannot be left implicit. **(a)** `S-INV-3` ([domain-model.md:254](domain-model.md#L254)–[:256](domain-model.md#L256)) makes a worker's `declared_status` ([:203](domain-model.md#L203)) plus measured dissatisfaction **require** an `Escalation`, while `G-6` ([:892](domain-model.md#L892)) says `declared_status` never appears in any precondition of any transition and [transition-matrix.md:505](transition-matrix.md#L505) makes writing it to gate a transition `NONE_GRANTABLE`. **(b)** [worker_provider.md:146](worker_provider.md#L146)–[:147](worker_provider.md#L147) calls receipt/validation/review/recomputation the **only** path from worker output to stage state, while [transition-matrix.md:128](transition-matrix.md#L128) and [:158](transition-matrix.md#L158) admit escalation control paths this document types as admissible prerequisites. Raised at [FINDINGS-02:72](review/DESIGN-04-FINDINGS-02.md#L72) and [FINDINGS-03:69](review/DESIGN-04-FINDINGS-03.md#L69). These are **frozen-text tensions**, not claims that a worker can manufacture evidence or bypass a human; `R13.19`(ii) still denies that, and `G-3`, [domain-model.md:113](domain-model.md#L113) and [worker_provider.md:88](worker_provider.md#L88) are untouched. Distinct from `KD-8`, which is a missing field derivation. A later record must reconcile the sentences or state which yields. |
| `KD-15` | **`GR-23`'s conformance to `AX-17`** — `DESIGN-04-032`…`-036` | **NOT CLOSED, and not this document's to close.** `GR-23` implements the four-event transaction shape; [FINDINGS-04](review/DESIGN-04-FINDINGS-04.md) §5 reports that its successful creation path departs from five other obligations of the same witness: the mode it installs, the creator and event-actor attribution, `chosen` against an empty `options_offered`, a `SIGNATURE` method accepted without a signature, and an `evidence_shown` index the runtime selected rather than a human saw. §2.23 states all seven requirements so the conformance work has a specification; this revision writes no code, runs no conformance check, and asserts nothing about whether any of the five is met. A correct four-event sequence alone is not conformance. |
| `KD-16` | **The §5.2 denial-reason mapping** — which of `AX-8`'s eight values a failed per-act exercise carries | **NOT CLOSED, and not solved here. Nonblocking for this bounded correction.** Amendment 9's `AX-8` states the denial `AuditEvent`'s **vocabulary**; it does not assign a value to each denial. §5.3 supplies that mapping for its own steps 2–5a and records it at step 7. §5.2 does not: its steps 1–9 are checks that pass or fail and name no reason, so which value a failed per-act exercise carries is unassigned — exactly as it was before this correction, which neither widens nor narrows the gap. `AX-8`'s prohibition on silent denial still binds a §5.2 denial to emit the event. Disclosed at `R13.24` and registered here so the register, not only a rule cell, records it. `REVOKED` is **not** the gap: it can arise in neither §5, §5.1 nor §5.2, only at §5.3 step 5a. A later record must assign the reasons for §5.2's steps or state that the event carries a reason outside the eight. Nothing in this correction's five findings depends on the assignment, which is why it is documentary here and is not designed here. |
| `KD-17` | **The referent of a `CAPABILITY`-subject `HumanDecision.subject.id`** | **NOT CLOSED, and not defined here. Nonblocking for this bounded correction.** §5.3 step 1 admits `subject.kind ∈ {PROJECT, CAPABILITY}` and constrains `subject.id` only in the `PROJECT` case. The frozen model gives the `CAPABILITY` case no referent to constrain: `Id` is a ULID ([domain-model.md:17](domain-model.md#L17)), `Ref<E>` is an `Id` constrained to an entity ([:38](domain-model.md#L38)), and a `CapabilityId` is a dotted name in the [authority-matrix.md:56](authority-matrix.md#L56) register with no `Capability` entity for a `Ref` to point at. Step 1 therefore does not require `subject.id` to name a capability, and this document supplies no referent and claims none. Disclosed at `R13.25` and at §5.3 step 1, and registered here for the same reason as `KD-16`. Nothing in `AX-19` depends on it: [domain-model.md:702](domain-model.md#L702) exempts the profile by `subject.kind` alone, so the admission rule, the `STALE` exclusion and the end-set are unaffected either way. A later record must either give the field a referent for this `subject.kind` or state that it is uninterpreted. |

Three further items are carried in §6.4 and are **not** defects of this correction; they are
listed here only so the register is not read as exhaustive of §6.4. Transition rows for the
four governance writes `project.mode.set`, `policy.set`, `budget.grant` and `budget.extend`
are `DESIGN-03`'s subject (§5), and `budget.extend`'s run half is `KD-11`. The `C`/`D`
tension between [authority-matrix.md:203](authority-matrix.md#L203)/[:206](authority-matrix.md#L206)
and [:221](authority-matrix.md#L221) predates every revision, is none of the five findings,
and no amendment depends on resolving it. And `project.mode.set`'s missing row has the
consequence §2.23 row 1 names: while it is missing, no conforming history reaches
`AUTONOMOUS`.

**Nothing in this document is implemented and nothing in it is in effect.** This document
changes no file under `src/` or `tests/`; `GR-23`'s partial implementation of `AX-17`
predates it and is `KD-15`. Accepting this correction would not make any operation above
executable, and it is not accepted: revision 05 is a **proposal pending independent review
and owner acceptance**, `design-01-frozen` remains the operative baseline, and
`design-04-frozen` remains historical evidence of revision 04 rather than a corrective
baseline ([FINDINGS-04:174](review/DESIGN-04-FINDINGS-04.md#L174)).
