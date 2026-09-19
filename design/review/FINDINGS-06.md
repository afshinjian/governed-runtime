# FINDINGS-06 — GR-28 final independent implementation review

Baseline: `85fdffd18890128cee041ca02bb9a382ef8c7e0d` plus the reviewed,
uncommitted GR-28 implementation, tests, mutation runner and evidence record in
the working tree.

| Property | Value |
|---|---|
| Record identifier | `FINDINGS-06` |
| Stage | `GR-28`: `COMMIT_INTENT` §7.4 transition authority only |
| Date | 2026-09-19 |
| Record status | Final independent implementation review recorded; uncommitted for fresh verification |
| Reviewer | Codex, independent GR-28 implementation reviewer |
| Final independent verdict | **PASS** |
| Owner closeout readiness | **READY_FOR_OWNER_CLOSEOUT** |
| Closed | `F03-002`, `F03-003`, the §7.4 instance of `F03-001`, `GR28-R01` |
| Still open | `F03-001` overall (**OPEN/PARTIAL**); `F04-004` (**OPEN**) |
| Final baseline | **1289 collected / 1289 passed** |
| Targeted review suite | **132 passed** |
| Mutation evidence | **PASS — 20/20 KILLED**: 4 GR-28 guards and 16 adjacent historical guards |
| Tests added | **19** |

## 1. Provenance, numbering and reviewed bytes

The OWNER directed this immutable recording action after the final independent
review state was established. The committed general implementation-review
sequence ends at [FINDINGS-05:1](FINDINGS-05.md#L1), so the next record under the
existing convention is `FINDINGS-06.md`. The separate
`DESIGN-*-FINDINGS-*` files remain the design-review sequence and were not used
to invent a new implementation-review name.

The authorized scope is exactly the fourteen §7.4 rows at
[transitions.py:1314](../../src/gruntime/transitions.py#L1314), not a general
transition-engine rollout. The implementation evidence independently records
that boundary, the two complete finding closures, and the 14-of-145 partial
closure at [gr28-mutations.json:2](../../docs/evidence/gr28-mutations.json#L2)
through [gr28-mutations.json:10](../../docs/evidence/gr28-mutations.json#L10).

HEAD alone does not contain the reviewed implementation. These SHA-256 values
bind the changed and added implementation artifacts to the bytes whose anchors
were checked:

| File | SHA-256 |
|---|---|
| `src/gruntime/authority.py` | `4df32dc564af775a3361d290dca8782ebf229d4e73a10a006a533a78199ced43` |
| `src/gruntime/contract_controller.py` | `1a7d54e016782c9fe25209584639789bbe980edda6463c35664713de317adb7f` |
| `src/gruntime/controller.py` | `458403b5573fb801847b07392de8484e24c8f7b22e42f737bb180cf78f8a75a0` |
| `src/gruntime/policy.py` | `fc8fc8f7e7c11f5d57fe82e93c86bb9df6b90f2e9a1cab3bc996e62d1c5e0d50` |
| `tests/test_gr02_transition_engine.py` | `4a2754bdf493f63af4a30ad8ee9cc16749992e479a445abcc3fea817a1c5f57c` |
| `tests/test_gr10_git_transaction.py` | `ffea753a6f48ff1362188e3672dd3e7dea2eda472c64d0fa9cadb1d6fa3b0657` |
| `tests/test_gr28_transition_authority.py` | `336cfdeb74b7aae83de03c5c46e5aa1b8f75c5b684d9c1733ad76f9a11529e25` |
| `bin/check-gr28-mutations` | `9fffade83d65fa247075927d037671dc08073e29908a1581fb279a42965d1cfe` |
| `docs/evidence/gr28-mutations.json` | `7ec15ac80dfd7d3f98cae82f41a547f8781479c3ca0d5d6d8a4dbe5abd37c2ee` |

## 2. Final finding status

| Identifier | Final status | Independent disposition and current evidence |
|---|---|---|
| `F03-002` | **CLOSED** | Contract mutation authority remains a distinct syscall/tool-mediation check: `_require_commit_authority` still re-proves `commit.propose` and per-path mutation grants at [contract_controller.py:192](../../src/gruntime/contract_controller.py#L192) and [contract_controller.py:211](../../src/gruntime/contract_controller.py#L211). It no longer stands in for transition authority. Kernel capabilities are derived from the register at [authority.py:38](../../src/gruntime/authority.py#L38); the transition channel selects `KERNEL` authority only from the acting runtime holder and `ORD` authority only from the live activation at [controller.py:1863](../../src/gruntime/controller.py#L1863) through [controller.py:1916](../../src/gruntime/controller.py#L1916). Authorize/deny and apply therefore enforce the capabilities their §7.4 rows declare. The withheld-capability regressions are at [test_gr28_transition_authority.py:72](../../tests/test_gr28_transition_authority.py#L72), [test_gr28_transition_authority.py:94](../../tests/test_gr28_transition_authority.py#L94), [test_gr28_transition_authority.py:109](../../tests/test_gr28_transition_authority.py#L109) and [test_gr28_transition_authority.py:125](../../tests/test_gr28_transition_authority.py#L125). |
| `F03-003` | **CLOSED** | `_transition_intent` no longer accepts a caller-supplied capability. It resolves the row and proves its declared capability before assigning status, labels the event with `rule.required_capability`, and only then persists at [controller.py:1962](../../src/gruntime/controller.py#L1962) through [controller.py:1998](../../src/gruntime/controller.py#L1998). Proposal uses the same channel and returned label at [controller.py:1816](../../src/gruntime/controller.py#L1816) and [controller.py:1836](../../src/gruntime/controller.py#L1836). Tests cover the exercised §7.4 lifecycle labels, the formerly mislabelled blocked exit, and the `_transition_intent` helper signature at [test_gr28_transition_authority.py:143](../../tests/test_gr28_transition_authority.py#L143), [test_gr28_transition_authority.py:178](../../tests/test_gr28_transition_authority.py#L178) and [test_gr28_transition_authority.py:206](../../tests/test_gr28_transition_authority.py#L206). |
| `F03-001` — §7.4 instance | **CLOSED** | Production §7.4 paths now read their row through `rules_for`, select among duplicate edges using the actually held capability, and call the same `capability_missing` predicate used by the resolver at [controller.py:1918](../../src/gruntime/controller.py#L1918) through [controller.py:1960](../../src/gruntime/controller.py#L1960). That shared predicate is defined at [policy.py:201](../../src/gruntime/policy.py#L201) and remains resolver step 7 at [policy.py:353](../../src/gruntime/policy.py#L353). The shared-predicate regression covers all 145 legal rows in both held and absent directions at [test_gr02_transition_engine.py:256](../../tests/test_gr02_transition_engine.py#L256). All fourteen §7.4 declarations now have this production consumer. |
| `F03-001` — overall | **OPEN/PARTIAL** | The closure above is intentionally only 14 of 145 legal rows. No non-§7.4 state-writing path was routed through the channel. The original overall finding therefore remains open for the other 131 rows; this record does not reinterpret a scoped implementation as complete remediation of [FINDINGS-03:12](FINDINGS-03.md#L12). |
| `F04-004` | **OPEN** | The historical finding requires all three owner-blocking `F03-001` through `F03-003` findings to be closed ([FINDINGS-04:15](FINDINGS-04.md#L15)). `F03-002` and `F03-003` are closed here, but `F03-001` remains open overall. GR-28 therefore improves the finding's underlying state without satisfying its closure predicate. |
| `GR28-R01` | **CLOSED** | The direct apply path now re-reads the intent after `mark_applying` persists `APPLYING`, before repository mutation and settlement, at [controller.py:2214](../../src/gruntime/controller.py#L2214) through [controller.py:2224](../../src/gruntime/controller.py#L2224). The normal granted lifecycle reaches one revision, `APPLIED`, a receipt, and a valid audit chain at [test_gr28_transition_authority.py:371](../../tests/test_gr28_transition_authority.py#L371). |

## 3. `GR28-R01`: stale-intent correction

The correction was **NECESSARY_AND_BOUNDED**.

It was necessary because `apply_commit` re-read an `AUTHORIZED` object under
the repository lease, then `mark_applying` independently loaded another object
and persisted it as `APPLYING`. Without a second read, the first object remained
`AUTHORIZED` in memory and was passed to settlement. Once GR-28 correctly
enforced the matrix edge, settlement attempted the nonexistent
`AUTHORIZED → APPLIED` edge instead of §7.4-7's `APPLYING → APPLIED` edge. The
new read at [controller.py:2217](../../src/gruntime/controller.py#L2217) obtains
the status that `mark_applying` already persisted; settlement still occurs
through `_transition_intent` at [controller.py:2177](../../src/gruntime/controller.py#L2177).

It was bounded because it adds one store read and changes no status, capability,
evidence rule, transaction boundary, repository operation, schema or design.
It neither creates a transition nor weakens a guard; it makes the object passed
to the new §7.4 checker describe the transition the existing code has already
performed. This is direct enabling correctness for the authorized GR-28 path,
not Tier-2 or non-§7.4 remediation.

## 4. Mutation evidence and test accounting

The implementation evidence record declares 20 guards killed, lists the four GR-28
guards and the sixteen adjacent historical guards at
[gr28-mutations.json:13](../../docs/evidence/gr28-mutations.json#L13) through
[gr28-mutations.json:38](../../docs/evidence/gr28-mutations.json#L38), and
inlines each guard's mutant/restored summaries. Independent parsing confirmed
exactly 20 guard objects, exactly 4 with `kind = gr28`, exactly 16 with
`kind = adjacent`, and all 20 with `passed = true`; the first result begins at
[gr28-mutations.json:54](../../docs/evidence/gr28-mutations.json#L54), the four
GR-28 results are anchored at [gr28-mutations.json:113](../../docs/evidence/gr28-mutations.json#L113),
[gr28-mutations.json:262](../../docs/evidence/gr28-mutations.json#L262),
[gr28-mutations.json:405](../../docs/evidence/gr28-mutations.json#L405) and
[gr28-mutations.json:423](../../docs/evidence/gr28-mutations.json#L423), and the
final KILLED summary is at [gr28-mutations.json:681](../../docs/evidence/gr28-mutations.json#L681).

| Mutation accounting | Final count |
|---|---:|
| GR-28 guards | 4 |
| Adjacent historical guards rechecked | 16 |
| Total guards | 20 |
| KILLED | 20 |
| SURVIVED in final evidence | 0 |

The temporary `commit_mark_status` survivor is preserved rather than erased.
Deleting that guard initially left 1289 tests green because the new
`transition_row_declared` guard raised the same exception type for the same
illegal case. The evidence records the mutant, restored suite and
`SURVIVED` result at [gr28-mutations.json:40](../../docs/evidence/gr28-mutations.json#L40)
through [gr28-mutations.json:50](../../docs/evidence/gr28-mutations.json#L50).
The existing parametrized test was repaired narrowly with a per-case refusal
message and `match=` at [test_gr10_git_transaction.py:311](../../tests/test_gr10_git_transaction.py#L311)
through [test_gr10_git_transaction.py:333](../../tests/test_gr10_git_transaction.py#L333).
The rerun then killed `commit_mark_status`, recorded at
[gr28-mutations.json:540](../../docs/evidence/gr28-mutations.json#L540). This is
an honest mutation-history correction and one targeted guard assertion, not a
historical `F04-002` backfill.

`tests_added = 19` is also exact: seventeen tests are in the new GR-28 file
([test_gr28_transition_authority.py:72](../../tests/test_gr28_transition_authority.py#L72)
through [test_gr28_transition_authority.py:371](../../tests/test_gr28_transition_authority.py#L371))
and two shared-predicate tests were added at
[test_gr02_transition_engine.py:256](../../tests/test_gr02_transition_engine.py#L256)
and [test_gr02_transition_engine.py:273](../../tests/test_gr02_transition_engine.py#L273).
The `test_gr10_git_transaction.py` change modifies an existing parametrized
test and is not counted as a test addition.

## 5. OWNER blocking and disposition

The [review method:105](../../CLAUDE.md#L105) reserves blocking dispositions to
the OWNER. The OWNER supplied the final dispositions and
`READY_FOR_OWNER_CLOSEOUT` state recorded below. The blocking column means
**blocking the scoped GR-28 closeout**, not rewriting the historical `true`
flags in [FINDINGS-03:12](FINDINGS-03.md#L12) through
[FINDINGS-03:14](FINDINGS-03.md#L14) or the historical `F04-004` flag.

| id | owner blocking (GR-28 closeout) | owner disposition | owner note |
|---|---|---|---|
| F03-002 | false | CLOSED | §7.4 authorize/deny/apply enforce their declared transition capabilities; §2. |
| F03-003 | false | CLOSED | §7.4 status writers prove the row capability and derive the event label from that row; §2. |
| F03-001 (§7.4 instance) | false | CLOSED | All fourteen §7.4 rows have a production consumer of the shared capability predicate; §2. |
| F03-001 (overall) | false | OPEN/PARTIAL | The other 131 legal rows remain outside GR-28; open project debt does not block this deliberately scoped closeout; §2. |
| F04-004 | false | OPEN | Its all-three closure predicate is unsatisfied while F03-001 remains open overall; no GR-28 scope expansion; §2. |
| GR28-R01 | false | CLOSED | Necessary and bounded stale-object re-read verified on the direct apply lifecycle; §3. |

| Count check | Rows |
|---|---:|
| Complete F03 closures | 2 |
| Scoped F03 instance closures | 1 |
| GR-28 review-item closures | 1 |
| Open/partial inherited dispositions | 2 |
| Owner disposition rows | 6 |
| Blank owner blocking/disposition/note cells | 0 |
| Final findings blocking scoped GR-28 closeout | 0 |

## 6. Verification and scope boundary

| Verification | Result |
|---|---|
| Final baseline | Fresh run: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — **1289 collected / 1289 passed in 145.87s**, exit 0. |
| Targeted review suite | Fresh run of `tests/test_gr28_transition_authority.py`, `tests/test_gr02_transition_engine.py`, and `tests/test_gr10_git_transaction.py` — **132 passed in 26.94s**, exit 0. Fresh collection confirmed the same 132 cases. |
| Mutation evidence | Structured count and every `passed` field checked; **20/20 KILLED**, split 4 GR-28 / 16 adjacent; temporary survivor and final kill both retained. |
| Citation integrity | Every source, test, evidence and prior-review anchor in this record was resolved against the current working tree. |
| Record integrity | Six owner rows and their count table checked; no owner blocking, disposition or note cell is blank. |
| Repository boundary | Prior review records, source, tests, evidence, `CLAUDE.md` and design-model files were not edited by this recording action. Only this new review record was added. |

The scoped transition channel deliberately enforces only the row's declared
capability. Its own current contract says preconditions and
`required_evidence` are not enforced there at
[controller.py:1937](../../src/gruntime/controller.py#L1937) through
[controller.py:1941](../../src/gruntime/controller.py#L1941). The following
non-closures are therefore explicit:

| Excluded work | Final disposition |
|---|---|
| Tier-2 or non-§7.4 transition remediation | **None.** `F03-001` remains OPEN/PARTIAL overall. |
| Design changes | **None.** No design model, frozen tag or accepted correction was changed. |
| `required_evidence` enforcement | **None.** Capability-only enforcement is explicit in the implementation anchor above. |
| `F02-002` supervised `CONFIRM` | **Not implemented.** Row 7.4-4 still declares `CONFIRM` at [transitions.py:1334](../../src/gruntime/transitions.py#L1334); GR-28 adds no confirmation decision path. |
| `F03-004` / `F03-005` | **No remediation or closure claimed.** Their historical records remain at [FINDINGS-03:15](FINDINGS-03.md#L15) and [FINDINGS-03:16](FINDINGS-03.md#L16). |
| `F04-001` / `F04-002` / `F04-003` historical backfill | **None.** The single `match=` repair is limited to the adjacent guard exposed during GR-28 mutation review and does not close or backfill the historical test estate. |
| SET_MODE | **No implementation.** GR-28 changes no project-mode transition. |
| Storage migration | **None.** [store.py:116](../../src/gruntime/store.py#L116) remains `STORAGE_VERSION = 5`. |

**Final independent verdict: PASS. Owner closeout readiness:
READY_FOR_OWNER_CLOSEOUT.** This is readiness for the scoped GR-28 owner
closeout, not closure of `F03-001` overall, `F04-004`, or any excluded debt.
The record is left untracked and uncommitted. No staging, commit, tag or push is
performed.
