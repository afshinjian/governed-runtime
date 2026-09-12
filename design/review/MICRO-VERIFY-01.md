# MICRO-VERIFY-01

Reviewed baseline: `cb9eb8a89ca7f0d69ec04fdd614cd67e774a6b7f` (`HEAD`, initially clean), 2026-09-12.

Scope: verify application of the owner decisions D1–D5 in [MICRO-01.md](MICRO-01.md) and the closure criteria already stated for F01-002, F01-003 and F01-007 in [CLOSURE-01.md](CLOSURE-01.md). The decisions are accepted as requirements; their merits are not evaluated. Design-file line references identify this baseline. Other findings are not reassessed, and no new finding is raised.

**Result: 0 RESOLVED, 3 UNRESOLVED.** Several specific repairs pass, but the three findings do not yet satisfy their complete CLOSURE-01 criteria. These are specification-verification results, not observations of runtime behavior.

| Finding | Disposition | Remaining closure gap |
|---|---|---|
| F01-002 | **UNRESOLVED** | The required preserved refusal cannot be represented by `WorkerReceipt.termination_reason` ([domain-model.md:603](../domain-model.md#L603)); recovery step 1 still restates a status-only derivation that omits terminal reconciliation precedence ([worker_provider.md:156](../worker_provider.md#L156)). These concern the outcome-preservation and completed-reconciliation cases in [CLOSURE-01.md:29](CLOSURE-01.md#L29) and [CLOSURE-01.md:31](CLOSURE-01.md#L31). |
| F01-003 | **UNRESOLVED** | Old `PROPOSED`/`BLOCKED`/`AUTHORIZED` intents now become `ORPHANED` without changing status ([transition-matrix.md:359](../transition-matrix.md#L359), [transition-matrix.md:371](../transition-matrix.md#L371)), but the unchanged audit check still rejects a later dispatch/apply while such an old nonterminal operation exists ([evidence-model.md:167](../evidence-model.md#L167)). This is the pre-`APPLYING` coverage/audit consistency criterion in [CLOSURE-01.md:28](CLOSURE-01.md#L28). |
| F01-007 | **UNRESOLVED** | Direct evidence consumers were switched to attestations, but `RVW(v)` still binds `v` to a `Review` verdict ([transition-matrix.md:71](../transition-matrix.md#L71)), while the domain binds it to the attestation's aggregate verdict ([domain-model.md:513](../domain-model.md#L513)). This is the incomplete propagation already recorded at [CLOSURE-01.md:51](CLOSURE-01.md#L51). |

**Owner-decision application.**

| Decision | Verification | Evidence |
|---|---|---|
| D1 — separate, non-executing `lookup` | **APPLIED** | `LookupResult` has `LIVE`, `FINISHED`, `ABSENT`; `lookup(Hash)` requires `recovery.reconcile` and takes no executable request ([worker_provider.md:34](../worker_provider.md#L34), [worker_provider.md:61](../worker_provider.md#L61), [worker_provider.md:65](../worker_provider.md#L65)). `WP-16` forbids recovery resubmission, and `WP-17` excludes providers without lookup from governed mutation ([worker_provider.md:103](../worker_provider.md#L103), [worker_provider.md:104](../worker_provider.md#L104)). Authority and illegal operations agree ([authority-matrix.md:94](../authority-matrix.md#L94), [transition-matrix.md:518](../transition-matrix.md#L518), [transition-matrix.md:519](../transition-matrix.md#L519)). |
| D2 — gate initiation, exempt reconciliation | **APPLIED** | The exemption expressly includes recovery `APPLYING → APPLIED`/`FAILED` ([transition-matrix.md:228](../transition-matrix.md#L228)); the illegal row is restricted to advancing under `commit.apply` and repeats the exemption ([transition-matrix.md:516](../transition-matrix.md#L516)). Domain and authority use the same scope ([domain-model.md:295](../domain-model.md#L295), [authority-matrix.md:291](../authority-matrix.md#L291)). |
| D3 — adoption establishes the actual outcome | **INCOMPLETE** | Both recovery sequences preserve the five outcome statuses, including `REFUSED → FAILED`, and require the original termination reason ([transition-matrix.md:313](../transition-matrix.md#L313), [worker_provider.md:158](../worker_provider.md#L158)). However, the receipt enum cannot store `REFUSAL` ([worker_provider.md:33](../worker_provider.md#L33), [domain-model.md:603](../domain-model.md#L603)). |
| D4 — one reconciliation-state derivation | **INCOMPLETE** | §5.1 covers all old nonterminal statuses, terminal-result precedence, orphaning and live tracking ([transition-matrix.md:234](../transition-matrix.md#L234), [transition-matrix.md:244](../transition-matrix.md#L244), [transition-matrix.md:246](../transition-matrix.md#L246), [transition-matrix.md:252](../transition-matrix.md#L252), [transition-matrix.md:253](../transition-matrix.md#L253)). The provider's local derivation and the old-intent audit check still disagree with its consequences ([worker_provider.md:156](../worker_provider.md#L156), [evidence-model.md:167](../evidence-model.md#L167)). |
| D5 — attestation-typed review preconditions | **APPLIED to the specified consumers** | `CommitIntent.preconditions.reviews` is `Set<Ref<ReviewAttestation>>`; finding creation requires the covering attestation ([domain-model.md:640](../domain-model.md#L640), [transition-matrix.md:333](../transition-matrix.md#L333)). The accompanying `RECOVERY_AMBIGUITY` schema addition is present ([stage_contract.schema.json:270](../schema/stage_contract.schema.json#L270)). The pre-existing `RVW(v)` aggregate mismatch remains outside those two type replacements. |

**F01-002 — unknown-key recovery passes; outcome and state consistency remain incomplete.**

There is no legal recovery path that executes an unknown `idempotency_key`. The persisted request is read for identity/audit and never re-sent ([domain-model.md:580](../domain-model.md#L580), [worker_provider.md:102](../worker_provider.md#L102)). The only provider operation reachable under `recovery.reconcile` is `lookup`, which cannot start, resume, extend or bill execution ([worker_provider.md:65](../worker_provider.md#L65), [worker_provider.md:123](../worker_provider.md#L123)). An unknown key returns `ABSENT` and produces `FAILED`/`ORPHANED`; an unanswerable key produces `UNRESOLVABLE` and escalation ([worker_provider.md:159](../worker_provider.md#L159), [worker_provider.md:161](../worker_provider.md#L161)). Request resubmission and replacement keys/attempts are explicitly illegal ([transition-matrix.md:517](../transition-matrix.md#L517), [transition-matrix.md:518](../transition-matrix.md#L518)). `WP-6` and `CF-11` still describe `invoke` deduplication; they do not authorize recovery to bypass these restrictions ([worker_provider.md:93](../worker_provider.md#L93), [worker_provider.md:189](../worker_provider.md#L189)).

D3's status mapping agrees at both recovery sites: `COMPLETED → COMPLETED`, `FAILED → FAILED`, `TIMED_OUT → TIMED_OUT`, `CANCELLED → CANCELLED`, `REFUSED → FAILED` ([transition-matrix.md:313](../transition-matrix.md#L313), [worker_provider.md:158](../worker_provider.md#L158)). Adoption also preserves a divergent commit as a failure ([transition-matrix.md:358](../transition-matrix.md#L358), [transition-matrix.md:365](../transition-matrix.md#L365)). The remaining representational failure is concrete: a legitimate `FINISHED` outcome with `status = REFUSED` and `termination_reason = REFUSAL` requires a reconciled receipt carrying `REFUSAL` ([worker_provider.md:33](../worker_provider.md#L33), [worker_provider.md:48](../worker_provider.md#L48), [worker_provider.md:158](../worker_provider.md#L158)). That value is absent from the closed receipt enum ([domain-model.md:603](../domain-model.md#L603)); unknown enum values are integrity violations ([domain-model.md:37](../domain-model.md#L37)). Mapping the invocation to `FAILED` therefore does not yet make the owner-required refusal-preserving receipt valid. This fails the existing outcome-preservation criterion, without questioning the chosen mapping.

The requested §5.1 deferral check has the following result:

| Consumer | Verification |
|---|---|
| transition-matrix §7.2 | Refers to §5.1 for `ADOPTED`/`ORPHANED` and `LIVE` remaining `PENDING`; no return to `NOT_REQUIRED` is specified here ([transition-matrix.md:316](../transition-matrix.md#L316), [transition-matrix.md:322](../transition-matrix.md#L322)). |
| transition-matrix §7.4 | Refers to §5.1 and supplies the observation-to-outcome rows, including old pre-`APPLYING` intents ([transition-matrix.md:359](../transition-matrix.md#L359), [transition-matrix.md:365](../transition-matrix.md#L365)). |
| worker_provider §6.1 | Step 5 correctly retains `PENDING` until `ADOPTED` ([worker_provider.md:160](../worker_provider.md#L160)). **Step 1 is not a consistent deferral:** after citing §5.1 it still says “non-terminal `status` ⇒ `PENDING`, terminal `status` ⇒ `NOT_REQUIRED`” for every selected old invocation ([worker_provider.md:156](../worker_provider.md#L156)). That summary omits §5.1's terminal reconciliation-result precedence. |
| authority-matrix §6 | Explicitly derives the state by §5.1 and checks the allowed barrier values without supplying another status-to-state derivation ([authority-matrix.md:291](../authority-matrix.md#L291)). |

For the remaining provider contradiction, take an invocation recovered to `FAILED`/`ADOPTED`, then restart the controller again. §5.1 requires its reconciliation result to remain `ADOPTED`, whatever its later epoch/status ([transition-matrix.md:246](../transition-matrix.md#L246)); the literal terminal-status rule still printed in provider step 1 yields `NOT_REQUIRED`. The citation to §5.1 is present, but the conflicting local restatement has not been removed. Both domain fields already identify §5.1 as their sole derivation ([domain-model.md:582](../domain-model.md#L582), [domain-model.md:639](../domain-model.md#L639)).

**F01-003 — landed-commit adoption passes; pre-`APPLYING` audit consistency does not.**

The gate at [transition-matrix.md:228](../transition-matrix.md#L228) and the illegal row at [transition-matrix.md:516](../transition-matrix.md#L516) no longer contradict. Under the recovery barrier, each determinate landed-commit observation has exactly one applicable recovery row:

| Observation for the persisted `operation_token` | Legal adoption under `recovery.reconcile` |
|---|---|
| Exactly one revision; tree equals `expected_tree_digest` | `APPLYING → APPLIED`, `MATCHED` receipt with `attribution = RECONCILED` and `post_snapshot_id`, reconciliation `ADOPTED` ([transition-matrix.md:356](../transition-matrix.md#L356), [transition-matrix.md:365](../transition-matrix.md#L365)). |
| Exactly one revision; tree differs | `APPLYING → FAILED`, `DIVERGED` reconciled receipt plus escalation, reconciliation `ADOPTED`; failure is retained ([transition-matrix.md:358](../transition-matrix.md#L358), [transition-matrix.md:366](../transition-matrix.md#L366), [domain-model.md:669](../domain-model.md#L669)). |

The predicates are mutually exclusive. The ordinary `commit.apply` rows cannot supply a second adoption path while the operation is unreconciled ([transition-matrix.md:352](../transition-matrix.md#L352), [transition-matrix.md:353](../transition-matrix.md#L353), [transition-matrix.md:516](../transition-matrix.md#L516)). No-token orphaning is a different observation, and multiple matches remain `UNRESOLVABLE` ([transition-matrix.md:357](../transition-matrix.md#L357), [transition-matrix.md:374](../transition-matrix.md#L374)). The receipt binds the found revision to the intent's token ([domain-model.md:663](../domain-model.md#L663)); recovery appends the adopting receipt under the common append protocol, whose state becomes observable only after durable event/head persistence ([evidence-model.md:158](../evidence-model.md#L158), [evidence-model.md:138](../evidence-model.md#L138), [domain-model.md:797](../domain-model.md#L797)). Thus the observation-to-durable-adoption path identified by CLOSURE-01 is repaired.

The remaining failure is the other commit case CLOSURE-01 explicitly required: recovery before `APPLYING`. Consider an old `AUTHORIZED` intent with no matching repository token and an unchanged base. The new row resolves it to `ORPHANED` while retaining `status = AUTHORIZED` ([transition-matrix.md:359](../transition-matrix.md#L359), [transition-matrix.md:371](../transition-matrix.md#L371)); its creation epoch is immutable ([domain-model.md:638](../domain-model.md#L638)). Once the run's other records are reconciled, the barrier permits a subsequent dispatch ([transition-matrix.md:219](../transition-matrix.md#L219), [transition-matrix.md:305](../transition-matrix.md#L305)). Yet the unchanged audit check forbids an old nonterminal operation preceding that dispatch and declares it an integrity violation ([evidence-model.md:167](../evidence-model.md#L167)). `AUTHORIZED` remains one of the explicitly nonterminal statuses ([transition-matrix.md:244](../transition-matrix.md#L244)); terminal reconciliation `ORPHANED` has not made its operation status terminal. The audit check does not consult that reconciliation result. This contradicts the new row's stated barrier-clearing consequence and leaves the existing shared-protocol criterion unresolved.

**F01-007 — direct consumer types pass; aggregate-verdict binding remains inconsistent.**

| Review-evidence consumer | Current required record |
|---|---|
| Commit preconditions and authorization | `Set<Ref<ReviewAttestation>>`, consumed as the cited `RVW` set ([domain-model.md:640](../domain-model.md#L640), [transition-matrix.md:349](../transition-matrix.md#L349)). |
| Finding creation and review-based resolution | Creation requires the attestation whose `review_ids` covers the originating review; resolution uses `RVW` ([transition-matrix.md:333](../transition-matrix.md#L333), [transition-matrix.md:335](../transition-matrix.md#L335), [transition-matrix.md:338](../transition-matrix.md#L338), [transition-matrix.md:339](../transition-matrix.md#L339)). |
| Satisfaction evaluator | `ReviewAttestation` set bound to the current snapshot; explicitly never reads `Review` records directly ([evidence-model.md:203](../evidence-model.md#L203)). |
| Project, stage, run and contract review-evidence gates | `RVW`, whose record type is `ReviewAttestation` ([transition-matrix.md:71](../transition-matrix.md#L71), [transition-matrix.md:93](../transition-matrix.md#L93), [transition-matrix.md:134](../transition-matrix.md#L134), [transition-matrix.md:202](../transition-matrix.md#L202), [transition-matrix.md:268](../transition-matrix.md#L268)). |

No remaining field or legal `required_evidence` cell takes a `Review` record in place of an attestation. The remaining `Ref<Review>` fields are the run's inventory, an attestation's quorum members, and a finding's originating review ([domain-model.md:281](../domain-model.md#L281), [domain-model.md:512](../domain-model.md#L512), [domain-model.md:544](../domain-model.md#L544)). They are record relationships, not evidence substitutions. Kernel-only minting and the CLAIM/EVIDENCE boundary remain explicit ([domain-model.md:525](../domain-model.md#L525), [domain-model.md:532](../domain-model.md#L532), [domain-model.md:887](../domain-model.md#L887), [transition-matrix.md:524](../transition-matrix.md#L524)).

However, [CLOSURE-01.md:51](CLOSURE-01.md#L51) also recorded that the attestation's aggregate verdict was not consistently propagated. That exact discrepancy remains: the domain says `ReviewAttestation.verdict` is aggregated over `review_ids` and is the value `RVW(v)` matches ([domain-model.md:512](../domain-model.md#L512), [domain-model.md:513](../domain-model.md#L513)); the shorthand still says an attestation over “a `Review` with `verdict = v`” ([transition-matrix.md:71](../transition-matrix.md#L71)), and authority still describes attesting an individual review ([authority-matrix.md:121](../authority-matrix.md#L121)). Quorum can exceed one ([stage_contract.schema.json:427](../schema/stage_contract.schema.json#L427)). Matching a member review's verdict and matching the aggregate are different predicates; the consumer definition has not been aligned. D5's two record-type changes therefore pass without establishing complete F01-007 closure.

Validation: inspected MICRO-01, CLOSURE-01 and the current design specifications/schema references within this scope; traced the permitted recovery branches and searched recovery/state and review-evidence consumers. A read-only enum comparison confirmed `REFUSAL` is the provider termination reason missing from `WorkerReceipt`; parsed the contract schema and confirmed `RECOVERY_AMBIGUITY` occurs once in its trigger enum. No implementation tests were run. Only this verification record was added.

NEW_ESCALATION: None.

## OWNER DISPOSITION (post-budget)

Convergence budget exhausted: FINDINGS-01 → REMEDIATION-01 → CLOSURE-01 →
MICRO-01 → MICRO-VERIFY-01. No further review pass is authorized.

F01-002, F01-003, F01-007 are DEFERRED_TO_GR-01 as DESIGN-01-RESIDUE. The
recovery protocol (D1–D4) and attestation propagation (D5) are decided; what
remains unverified is cross-document restatement consistency, which the owner
judges unresolvable by further specification review.

Binding acceptance criteria for GR-01 (these findings close there, not here):
- R-1  lookup() never executes an unknown idempotency_key. Test: unknown key
       returns ABSENT with zero provider-side side effects.
- R-2  kill -9 between a FINISHED lookup and a durable receipt; on restart the
       operation is adopted exactly once, outcome preserved.
- R-3  kill -9 between commit and receipt; restart adopts the landed commit
       exactly once, never commits twice, never exempts the gate.
- R-4  reconciliation_state is computed by one function derived from §5.1; no
       second implementation exists. Test: every old-epoch status maps as
       specified, PROPOSED/BLOCKED/AUTHORIZED → ORPHANED.
- R-5  no code path accepts a Review where a ReviewAttestation is required.

GR-01 does not pass until R-1..R-5 pass.
