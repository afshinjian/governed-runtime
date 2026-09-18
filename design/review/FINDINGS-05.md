# FINDINGS-05 — GR-27 final independent implementation review

Baseline: `7c34dc2cddfb969caa81165534a829cb6e126aad` plus the reviewed, uncommitted
GR-27 implementation and tests in the working tree.

| Property | Value |
|---|---|
| Record identifier | `FINDINGS-05` |
| Stage | `GR-27`: GR-23 conformance to AX-17 |
| Date | 2026-09-18 |
| Record status | Final independent review recorded; uncommitted for fresh verification |
| Reviewer | Codex, independent GR-27 implementation reviewer |
| Final independent verdict | **PASS** |
| Owner closeout readiness | **READY_FOR_OWNER_CLOSEOUT** |
| Inherited finding dispositions | **11 CLOSED**: `DESIGN-04-032` through `DESIGN-04-036`, and `GR27-R1` through `GR27-R6` |
| Residual finding set | **1 NONBLOCKING**, `F05-001` (nested `create_project`); **0 blocking** |
| Final baseline | **1270 collected / 1270 passed** |
| Final targeted suite | **485 passed** |
| Scope disposition | No unauthorized scope widening; no SET_MODE implementation; no storage migration; no unrelated F03/F04 remediation |

## 1. Provenance, baseline and scope

The OWNER directed this record after the completed final independent PASS review
and subsequent owner verification. The eleven CLOSED dispositions, the nested
`create_project` NONBLOCKING disposition, and the final verification counts are
the final reviewed state supplied by the OWNER. `GR27-R1` through `GR27-R6` retain
their prior review identifiers; no earlier committed record contains those IDs.
This recording pass rechecked the current implementation and test anchors,
verified the local owner baseline evidence, repeated the targeted suite, and
reproduced the nested-creation disposition. It changes no implementation.

The committed general review sequence ends at
[FINDINGS-04:1](FINDINGS-04.md#L1), making this `FINDINGS-05`. The separate
`DESIGN-04-FINDINGS-*` sequence records design reviews; its latest record carries
[Revision 05's independent PASS and owner acceptance:14](DESIGN-04-FINDINGS-05.md#L14).
All nineteen pre-existing committed review records were checked against HEAD
and remain unchanged.

The normative comparison is `design-01-frozen`, peeled commit
`8fd51193da0f29efb60ddf906fc845bb0dcbaeb3`, together with the accepted DESIGN-04
Revision 05 correction: [AX-17:529](../DESIGN-04-baseline-correction-05.md#L529)
and the [seven creation obligations:898](../DESIGN-04-baseline-correction-05.md#L898).
The four frozen model files remain byte-identical to `design-01-frozen`.
The older nonconformance statements in
[CLAUDE.md:93](../../CLAUDE.md#L93) and
[Revision 05:892](../DESIGN-04-baseline-correction-05.md#L892) describe their prior
baseline; the implementation dispositions below are recorded here without
editing those documents.

HEAD alone does not contain the reviewed implementation. These SHA-256 values
bind the three changed production files and the new conformance test file to
the bytes whose anchors were checked:

| File | SHA-256 |
|---|---|
| `src/gruntime/controller.py` | `41688094ae03b7c2dc5423eb68282f53ca1ad8d1a2e029c6a3f3b7600befcd4d` |
| `src/gruntime/contract_controller.py` | `01e5e1193114cc59229fab426025e9a45cb7f2b87434271ef780179ac898af31` |
| `src/gruntime/store.py` | `91973c07109af5735f7293a4cdf53ea1f71e9db815b4b4da625a726828516bd7` |
| `tests/test_gr23_conformance.py` | `98d1540a6857f1024209dfac69042634f0528cd0050314854a806359a524cc75` |

## 2. Final finding status

These are eleven inherited closures, not eleven new findings. Every anchor
below refers to the current working-tree file and was rechecked when recording.

| Identifier | Final status | Closure evidence and regression coverage |
|---|---|---|
| `DESIGN-04-032` | **CLOSED** | The supplied initial mode is required at [controller.py:794](../../src/gruntime/controller.py#L794). Creation reads the actual matrix policy at [controller.py:302](../../src/gruntime/controller.py#L302), enforces both the policy gate and explicit SUPERVISED contract at [controller.py:868](../../src/gruntime/controller.py#L868) and [controller.py:869](../../src/gruntime/controller.py#L869), and installs that mode at [controller.py:937](../../src/gruntime/controller.py#L937). The retained frozen cell is [transition-matrix.md:84](../transition-matrix.md#L84). Success and AUTONOMOUS refusal are covered at [test_gr23_conformance.py:357](../../tests/test_gr23_conformance.py#L357) and [test_gr23_conformance.py:371](../../tests/test_gr23_conformance.py#L371). |
| `DESIGN-04-033` | **CLOSED** | The project preserves the approving HUMAN as creator at [controller.py:945](../../src/gruntime/controller.py#L945); `decision.record` attributes the event to that human at [controller.py:1624](../../src/gruntime/controller.py#L1624). Creation uses the delegated runtime actor at [controller.py:1015](../../src/gruntime/controller.py#L1015) and cites the approval at [controller.py:1017](../../src/gruntime/controller.py#L1017); delegation depth is checked at [controller.py:512](../../src/gruntime/controller.py#L512). Separate field checks are at [test_gr23_conformance.py:203](../../tests/test_gr23_conformance.py#L203), [test_gr23_conformance.py:226](../../tests/test_gr23_conformance.py#L226), [test_gr23_conformance.py:279](../../tests/test_gr23_conformance.py#L279) and [test_gr23_conformance.py:309](../../tests/test_gr23_conformance.py#L309). |
| `DESIGN-04-034` | **CLOSED** | Creation presents CREATE and DECLINE at [controller.py:311](../../src/gruntime/controller.py#L311) and [controller.py:966](../../src/gruntime/controller.py#L966), then records the offered choices and selected response at [controller.py:986](../../src/gruntime/controller.py#L986). Decision recording enforces membership at [controller.py:1558](../../src/gruntime/controller.py#L1558). Empty/unoffered choices and the persisted real choices are checked at [test_gr23_conformance.py:73](../../tests/test_gr23_conformance.py#L73), [test_gr23_conformance.py:97](../../tests/test_gr23_conformance.py#L97) and [test_gr23_conformance.py:120](../../tests/test_gr23_conformance.py#L120). |
| `DESIGN-04-035` | **CLOSED** | The response signature is passed at [controller.py:990](../../src/gruntime/controller.py#L990), required for SIGNATURE authentication at [controller.py:1559](../../src/gruntime/controller.py#L1559), stored at [controller.py:1610](../../src/gruntime/controller.py#L1610), and included in the decision content hash computed at [controller.py:1613](../../src/gruntime/controller.py#L1613). Missing evidence rolls back; supplied evidence survives readback and changing it changes the hash ([test_gr23_conformance.py:147](../../tests/test_gr23_conformance.py#L147), [test_gr23_conformance.py:165](../../tests/test_gr23_conformance.py#L165)). This is evidence presence and binding, not cryptographic signature verification; that limit is explicit at [controller.py:1522](../../src/gruntime/controller.py#L1522). |
| `DESIGN-04-036` | **CLOSED** | The mandatory presenter receives the exact observation at [controller.py:955](../../src/gruntime/controller.py#L955) and [controller.py:974](../../src/gruntime/controller.py#L974). The response must conform, name that observation, approve CREATE and pass the freshness recheck ([controller.py:975](../../src/gruntime/controller.py#L975), [controller.py:977](../../src/gruntime/controller.py#L977), [controller.py:978](../../src/gruntime/controller.py#L978), [controller.py:979](../../src/gruntime/controller.py#L979)). The decision explicitly binds the presented snapshot and evidence at [controller.py:995](../../src/gruntime/controller.py#L995). Refusal and exact-binding coverage begins at [test_gr23_conformance.py:401](../../tests/test_gr23_conformance.py#L401) and [test_gr23_conformance.py:543](../../tests/test_gr23_conformance.py#L543). |
| `GR27-R1` | **CLOSED** | The initial mode has no production default, the matrix gate and SUPERVISED requirement are independent, and the presentation carries the installed mode ([controller.py:794](../../src/gruntime/controller.py#L794), [controller.py:868](../../src/gruntime/controller.py#L868), [controller.py:869](../../src/gruntime/controller.py#L869), [controller.py:960](../../src/gruntime/controller.py#L960)). Tests separately exercise omission, a denying SUPERVISED cell, a hypothetically permissive AUTONOMOUS cell, and presentation consistency ([test_gr23_conformance.py:584](../../tests/test_gr23_conformance.py#L584), [test_gr23_conformance.py:612](../../tests/test_gr23_conformance.py#L612), [test_gr23_conformance.py:627](../../tests/test_gr23_conformance.py#L627), [test_gr23_conformance.py:649](../../tests/test_gr23_conformance.py#L649)). |
| `GR27-R2` | **CLOSED** | Pending-project mutation admission uses the transaction's private token at [controller.py:558](../../src/gruntime/controller.py#L558); appends enforce it at [controller.py:510](../../src/gruntime/controller.py#L510). A reentrant presenter cannot insert another event into genesis. Tests verify the exact four-event witness, refusal/rollback, unrelated-project operability and hold cleanup ([test_gr23_conformance.py:684](../../tests/test_gr23_conformance.py#L684), [test_gr23_conformance.py:701](../../tests/test_gr23_conformance.py#L701), [test_gr23_conformance.py:732](../../tests/test_gr23_conformance.py#L732), [test_gr23_conformance.py:763](../../tests/test_gr23_conformance.py#L763)). |
| `GR27-R3` | **CLOSED** | Response fields are materialized as inert built-ins at [controller.py:265](../../src/gruntime/controller.py#L265) and [controller.py:271](../../src/gruntime/controller.py#L271), before freshness is checked. The exact approved snapshot is passed at [controller.py:995](../../src/gruntime/controller.py#L995), validated as this project's COMPLETE observation at [controller.py:1563](../../src/gruntime/controller.py#L1563), and retained at [controller.py:1564](../../src/gruntime/controller.py#L1564). Hostile values remain unevaluated; exact, foreign and nonbinding snapshot cases are covered at [test_gr23_conformance.py:835](../../tests/test_gr23_conformance.py#L835), [test_gr23_conformance.py:872](../../tests/test_gr23_conformance.py#L872), [test_gr23_conformance.py:899](../../tests/test_gr23_conformance.py#L899), [test_gr23_conformance.py:929](../../tests/test_gr23_conformance.py#L929) and [test_gr23_conformance.py:962](../../tests/test_gr23_conformance.py#L962). |
| `GR27-R4` | **CLOSED** | Admission precedes the durable epoch bump ([controller.py:1098](../../src/gruntime/controller.py#L1098)), contract persistence ([contract_controller.py:29](../../src/gruntime/contract_controller.py#L29)), observation/artifact work ([controller.py:1230](../../src/gruntime/controller.py#L1230)) and repository lease/worktree mutation ([controller.py:467](../../src/gruntime/controller.py#L467)). Catching a refusal cannot leave an unattested mutation behind. Tests check epoch, contracts, artifacts and worktree absence at [test_gr23_conformance.py:1065](../../tests/test_gr23_conformance.py#L1065), [test_gr23_conformance.py:1106](../../tests/test_gr23_conformance.py#L1106), [test_gr23_conformance.py:1145](../../tests/test_gr23_conformance.py#L1145) and [test_gr23_conformance.py:1404](../../tests/test_gr23_conformance.py#L1404). |
| `GR27-R5` | **CLOSED** | The hold surrounds BEGIN through COMMIT/ROLLBACK at [controller.py:876](../../src/gruntime/controller.py#L876) and is released in `finally` at [controller.py:590](../../src/gruntime/controller.py#L590). Public decision recording passes no genesis token ([controller.py:1465](../../src/gruntime/controller.py#L1465)); only genesis's private calls carry it. A response finalizer remains refused inside the open transaction, preserving one snapshot and four events ([test_gr23_conformance.py:1262](../../tests/test_gr23_conformance.py#L1262)); public approval injection and subsequent hold release are checked at [test_gr23_conformance.py:1188](../../tests/test_gr23_conformance.py#L1188) and [test_gr23_conformance.py:1311](../../tests/test_gr23_conformance.py#L1311). |
| `GR27-R6` | **CLOSED** | The inert-value refusal at [controller.py:271](../../src/gruntime/controller.py#L271) uses constant diagnostic text; it does not inspect an attacker-controlled type name or format the rejected value. The hostile metaclass/value regression asserts no diagnostic evaluation and no published state at [test_gr23_conformance.py:1372](../../tests/test_gr23_conformance.py#L1372). |

## 3. AX-17 witness retained

| seq | Capability | Final implementation evidence |
|---|---|---|
| 0 | `snapshot.take` | Observe and append at [controller.py:917](../../src/gruntime/controller.py#L917) and [controller.py:924](../../src/gruntime/controller.py#L924); initialize the project/head at [controller.py:929](../../src/gruntime/controller.py#L929). |
| 1 | `decision.record` | Record the informed APPROVE at [controller.py:980](../../src/gruntime/controller.py#L980), binding the snapshot entity at [controller.py:995](../../src/gruntime/controller.py#L995); reach VALID at [controller.py:1603](../../src/gruntime/controller.py#L1603). |
| 2 | `project.create` | Append creation at [controller.py:999](../../src/gruntime/controller.py#L999), citing the snapshot at [controller.py:1010](../../src/gruntime/controller.py#L1010) and approval at [controller.py:1017](../../src/gruntime/controller.py#L1017). |
| 3 | `audit.append` | Consume the decision at [controller.py:1019](../../src/gruntime/controller.py#L1019); cite the discharged creation as causal parent at [controller.py:1078](../../src/gruntime/controller.py#L1078), then persist CONSUMED at [controller.py:1082](../../src/gruntime/controller.py#L1082). |

One store transaction encloses all four events
([controller.py:877](../../src/gruntime/controller.py#L877),
[controller.py:890](../../src/gruntime/controller.py#L890),
[controller.py:892](../../src/gruntime/controller.py#L892)). The tests verify
capability order and chain integrity, final `event_seq = 3` and event-3 head,
authority/snapshot references, consumption, and failed-creation rollback at
[test_gr23_creation_path.py:96](../../tests/test_gr23_creation_path.py#L96),
[test_gr23_creation_path.py:124](../../tests/test_gr23_creation_path.py#L124),
[test_gr23_creation_path.py:136](../../tests/test_gr23_creation_path.py#L136),
[test_gr23_creation_path.py:152](../../tests/test_gr23_creation_path.py#L152) and
[test_gr23_creation_path.py:174](../../tests/test_gr23_creation_path.py#L174).

## 4. Residual finding

Frozen residual finding set: **one finding, zero blocking**. `F05-001` assigns
this record's conventional identifier to the already identified nested
`create_project` issue; it does not renumber any closed finding. Provenance uses
the general FINDINGS records' supplied/confirmed convention.

| id | severity | blocking | provenance | file | description |
|---|---|---|---|---|---|
| F05-001 | MINOR | false | supplied (owner), confirmed by current-tree probe | [src/gruntime/controller.py:877](../../src/gruntime/controller.py#L877) | **Nested `create_project` on the same controller/store connection exposes SQLite's transaction error. NONBLOCKING.** A presenter invoking creation again reaches `BEGIN IMMEDIATE` while the outer transaction is open and receives `sqlite3.OperationalError: cannot start a transaction within a transaction`, rather than a controller-level refusal. BEGIN precedes the inner `try` ([controller.py:878](../../src/gruntime/controller.py#L878)), so the inner call does not roll back the outer transaction. The nested hold is removed by [controller.py:591](../../src/gruntime/controller.py#L591). If the presenter catches the error and approves, the outer project commits the conforming four-event witness; if the error escapes, the outer handler rolls back at [controller.py:892](../../src/gruntime/controller.py#L892). No inner project is published and no hold remains. This is an error-reporting/API limitation, not a demonstrated authority, atomicity or witness breach; it does not block GR-27 owner closeout. |

The recording probe used fresh temporary stores and the public creation API,
without changing repository code or tests. Its observed durable counts were:

| Nested error handling | Projects | Audit events | Snapshots | Decisions | Pending holds after return | Open transaction after return |
|---|---|---|---|---|---|---|
| Caught by presenter; outer approval returned | 1 | 4 | 1 | 1 | 0 | false |
| Propagated from presenter; outer creation refused | 0 | 0 | 0 | 0 | 0 | false |

## 5. OWNER blocking and disposition

The [review method:105](../../CLAUDE.md#L105) reserves blocking dispositions to
the owner. The OWNER's instruction for this record supplies the final closures,
NONBLOCKING residual disposition and READY_FOR_OWNER_CLOSEOUT state. The flags
below mean **blocking GR-27 closeout in this final state**, not a retrospective
change to the original severity or owner flags. In particular the historical
`true` flags for the five design findings remain in
[DESIGN-04-FINDINGS-04:158](DESIGN-04-FINDINGS-04.md#L158) through its row at
[DESIGN-04-FINDINGS-04:162](DESIGN-04-FINDINGS-04.md#L162).

| id | owner blocking (GR-27 closeout) | owner disposition | owner note |
|---|---|---|---|
| DESIGN-04-032 | false | CLOSED | Mode conformance verified; §2. |
| DESIGN-04-033 | false | CLOSED | Creator and both event actors verified; §2. |
| DESIGN-04-034 | false | CLOSED | Offered-choice membership verified; §2. |
| DESIGN-04-035 | false | CLOSED | Signature evidence presence and binding verified; §2. |
| DESIGN-04-036 | false | CLOSED | Informed, observation-bound approval verified; §2. |
| GR27-R1 | false | CLOSED | Explicit SUPERVISED contract verified; §2. |
| GR27-R2 | false | CLOSED | Pending-project reentrancy boundary verified; §2. |
| GR27-R3 | false | CLOSED | Inert response and exact snapshot binding verified; §2. |
| GR27-R4 | false | CLOSED | Admission before durable mutation verified; §2. |
| GR27-R5 | false | CLOSED | Hold through transaction completion verified; §2. |
| GR27-R6 | false | CLOSED | Constant refusal diagnostic verified; §2. |
| F05-001 | false | NONBLOCKING | Nested creation remains a bounded API/error-reporting limitation; §4. |

| Count check | Rows |
|---|---|
| Inherited design closures in §2 | 5 |
| GR-27 remediation closures in §2 | 6 |
| Residual findings in §4 | 1 |
| Owner dispositions in §5 | 12 |
| Final blocking findings in this GR-27 record | 0 |

## 6. Verification and scope boundary

| Verification | Result and provenance |
|---|---|
| Final owner baseline | **1270 collected / 1270 passed**. Rechecked in the existing local log at [.evidence/20260918T171102.768134604Z-baseline.log:1274](../../.evidence/20260918T171102.768134604Z-baseline.log#L1274) and [its final result:1296](../../.evidence/20260918T171102.768134604Z-baseline.log#L1296). The full baseline was not rerun for this recording action. |
| Fresh collection check | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest --collect-only -q -p no:cacheprovider`: **1270 collected**, exit 0. |
| Final targeted suite | Owner-reported **485 passed**, independently reproduced during recording with the command below: **485 passed in 18.24s**, exit 0. |
| Nested creation | Both caught and propagated paths reproduced with the §4 results. |
| Record integrity | Current citation targets and line numbers checked; eleven unique closure rows, one residual finding, twelve owner dispositions; no blank owner flag or note. |
| Repository boundary | Prior review records, production code, tests, design documents and `CLAUDE.md` preserved; only this new review record added by the recording action. |

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_gr23_creation_path.py tests/test_gr23_conformance.py \
  tests/test_gr03_approval_staleness.py tests/test_gr06_contract_authority.py \
  tests/test_gr09_validation.py
```

The baseline log is local, gitignored evidence, not a committed artifact. Its
summary is preserved above; this record does not claim to repair mutation-log
durability or to re-run mutations.

| Scope check | Final disposition and evidence |
|---|---|
| Authorized GR-27 implementation | Creation conformance and its direct mutation/response boundaries only, including the actor serializer and necessary test fixture/caller adaptations. No unauthorized scope widening. |
| SET_MODE | **No implementation.** Production creation remains SUPERVISED. The direct post-creation mode writes used by older tests are explicitly test-only construction ([genesis_support.py:68](../../tests/genesis_support.py#L68), [genesis_support.py:90](../../tests/genesis_support.py#L90)); they establish no production mode transition. |
| Storage migration | **None.** [store.py:116](../../src/gruntime/store.py#L116) remains `STORAGE_VERSION = 5`. Delegation is serialized only when present ([store.py:434](../../src/gruntime/store.py#L434)), preserving the previous undelegated actor representation; [test_gr23_conformance.py:325](../../tests/test_gr23_conformance.py#L325) checks its unchanged event preimage. |
| Unrelated F03/F04 remediation | **None claimed or included.** The F03 paths `_require_commit_authority`, `_transition_intent` and `evaluate_transition` retain their HEAD implementations at [contract_controller.py:192](../../src/gruntime/contract_controller.py#L192), [controller.py:1818](../../src/gruntime/controller.py#L1818) and [controller.py:2209](../../src/gruntime/controller.py#L2209). GR-27's decision/fixture changes serve the closures above; they do not close the separate [FINDINGS-03:10](FINDINGS-03.md#L10) or [FINDINGS-04:10](FINDINGS-04.md#L10) finding sets. |

**Final independent verdict: PASS. Owner closeout readiness:
READY_FOR_OWNER_CLOSEOUT.** This is readiness for the owner's closeout, not a
stage transition or a claim that unrelated project debt is closed. The record
is left uncommitted for fresh verification. No previous record is modified;
no staging, commit, tag or push is performed.
