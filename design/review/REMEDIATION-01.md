# REMEDIATION-01

Remediation of the seven blocking findings in `design/review/FINDINGS-01.md`,
applied in one pass against baseline `c0cb238c97b54ffe47acb8a469659f518bc16794`.
Design artifacts only; no `src/` was written. Findings F01-002 and F01-003 share
a root cause and are closed by one change, recorded under **F01-002 + F01-003**.

---

## F01-001 — Activation can turn a worker request into authority without the required grantor

**Fix.** Grant provenance is checked for every capability, not only `HUMAN`-class
ones. A new axiom `AX-11` separates *bounding* from *granting*: the ceiling, the
mode gate, `capability_request` and the role table narrow the candidate set and
never create a grant. A capability is granted only when a principal named in its
§2 `grantable by` column produced an admissible grant record, and that record is
cited per capability in a new `ContractActivationRecord.capability_grant_basis`
field. `PROJECT_CEILING` is explicitly not an admissible grantor, and a `G`/`C`
role cell supplies a grant only where §2 names `ROLE_DEFAULT` as a grantor. The
worked case in the finding is stated in the text: `roadmap.writeback` is denied
`NO_GRANTOR` for a `PLANNER` in either mode without a live human grant, whatever
its `ORD` class, ceiling membership, `C` cell, and presence in the request say.

| file | section | change |
|---|---|---|
| `design/authority-matrix.md` | §0 Axioms | added `AX-11` |
| `design/authority-matrix.md` | §5 Resolution algorithm | rewrote step 6 (admissible grantor for every capability, not just `HUMAN`-class); extended step 8 to write `capability_grant_basis` |
| `design/authority-matrix.md` | §5.1 (new) Admissible grantors | grantor-by-grantor admissibility table, the `PROJECT_CEILING`/`ROLE_DEFAULT` rule, the `roadmap.writeback` case |
| `design/domain-model.md` | §6.2 `ContractActivationRecord` | added field `capability_grant_basis`; added `A-INV-3` |
| `design/domain-model.md` | §12 Global invariants | added `G-10` |
| `design/transition-matrix.md` | §6 `StageContract.status` | `DRAFT → ACTIVE` required_evidence now demands a `capability_grant_basis` entry per granted capability |
| `design/transition-matrix.md` | §9.3 Illegal authority and evidence operations | added rows for granting without an admissible grantor and for an activation record with incomplete `capability_grant_basis` |

---

## F01-002 + F01-003 — Worker dispatch has no controller recovery contract; a landed commit can remain permanently unreceipted

**Shared root cause, fixed once.** Both findings are the same defect at two call
sites: a side effect outside the kernel's store — a provider invocation, a
repository mutation — was performed without a durable identity recorded first,
and no restart procedure reconciled the outstanding operation before more work
was dispatched. The single change is an **identity-before-effect and
reconciliation protocol**, stated once as `G-9` and applied to both sites:

1. `Project.controller_epoch` increments once per controller start; every
   operation records the epoch it was created under.
2. Before the effect, its identity is durable — `request_ref` with
   `idempotency_key` for an invocation, `operation_token` for a commit intent —
   and the effect carries that identity outward (the key on the provider call,
   the token in the revision's trailers).
3. On restart, every non-terminal operation with a stale epoch is `PENDING`
   reconciliation. The kernel asks the outside world by that identity and
   *adopts* the result (mint the receipt with `attribution = RECONCILED`,
   state `ADOPTED`) or proves nothing happened (state `ORPHANED`). It never
   repeats the effect, rebuilds context, or mints a new key or attempt.
4. `RUN-INV-3` bars a run from creating a `WorkerInvocation` or advancing a
   `CommitIntent` past `AUTHORIZED` while any of its operations is `PENDING` or
   `UNRESOLVABLE`. An `UNRESOLVABLE` one raises
   `Escalation(RECOVERY_AMBIGUITY)`; for a commit intent it also suspends under
   `SUSPENDED_BY_INTEGRITY`, so tree equality is never used to guess which
   revision fulfilled which intent.

This closes F01-002 (duplicate worker), F01-003 (unreceipted landed commit), and
with them review questions 4 and 8.

| file | section | change |
|---|---|---|
| `design/authority-matrix.md` | §2.3 Contract and run | added `KERNEL` capability `recovery.reconcile` |
| `design/authority-matrix.md` | §6 Enforcement points | added `operation identity` and `controller recovery` rows; `receipt minting` row now covers `recovery.reconcile` and `attribution` |
| `design/domain-model.md` | §2 `Project` | added `controller_epoch`; added `P-INV-4` |
| `design/domain-model.md` | §5 `StageRun` | added `controller_epoch`; added `RUN-INV-3` |
| `design/domain-model.md` | §8.1 `WorkerInvocation` | added `request_ref`, `controller_epoch`, `reconciliation_state`; `idempotency_key` note now requires stability across restarts |
| `design/domain-model.md` | §8.2 `WorkerReceipt` | added `attribution`; added `W-INV-3` |
| `design/domain-model.md` | §8.3 `CommitIntent` | added `operation_token`, `controller_epoch`, `reconciliation_state`; `trailers` now carries `operation_token` |
| `design/domain-model.md` | §8.4 `CommitReceipt` | added `attribution` and `operation_token`; added `CM-INV-2`, `CM-INV-3` |
| `design/domain-model.md` | §9.B.1 `EscalationTrigger` | added `RECOVERY_AMBIGUITY` |
| `design/domain-model.md` | §10.4, §12 | listed `reconciliation_state` among subordinate state fields; added `G-9` |
| `design/transition-matrix.md` | §4 Axis 3 | `NONE → SUSPENDED_BY_INTEGRITY` precondition now covers an `UNRESOLVABLE` commit intent |
| `design/transition-matrix.md` | §5 `StageRun.lifecycle` | added the reconciliation row to `AWAITING_DECISION`; added the `RUN-INV-3` gate note |
| `design/transition-matrix.md` | §7.2 `WorkerInvocation.status` | `∅ → PENDING` now requires the persisted request and a reconciled run; added two reconciliation rows and the state-assignment note |
| `design/transition-matrix.md` | §7.4 `CommitIntent.status` | `∅ → PROPOSED` mints `operation_token`; `AUTHORIZED → APPLYING` requires it durable first; added three `APPLYING` reconciliation rows and the ambiguity rule |
| `design/transition-matrix.md` | §9.3 | added rows for dispatching under an unreconciled operation, replacing an unreconciled invocation with a new key, mutating before the token is durable, and re-applying an `APPLYING` intent unreconciled |
| `design/evidence-model.md` | §3.2.1 (new) External side effects | the four-step ordering rule, the recovery reading of it, and two added chain-verification checks |
| `design/evidence-model.md` | §2.3 Anti-patterns | added the restart-duplication row |
| `design/worker_provider.md` | §4 Contracts | extended `WP-6` (outcome retention window); added `WP-15` request-before-call and `WP-16` answerable-by-key |
| `design/worker_provider.md` | §6 Invocation sequence | inserted the persist-request step before dispatch; renumbered steps; added §6.1 Recovery sequence |
| `design/worker_provider.md` | §7 Conformance checklist | added `CF-11`, `CF-12` |

---

## F01-004 — Approvals are not bound to the repository reality the human approved

**Fix.** Decisions now have currency on the same terms as evidence. A decision
that speaks about the workspace is `snapshot_bound` and records
`subject_snapshot_id`, the snapshot its `evidence_shown` artifacts were measured
against. A derived `decision_state` makes the binding operative: when a newer
`COMPLETE` snapshot whose drift touches the subject's scope supersedes that
snapshot, the decision becomes `STALE` and satisfies no `CONFIRM` or `DECIDE(K)`,
whether or not it was ever used and whatever its `expires_at` says. `STALE` is
terminal — fresh validations over the new reality do not revive an approval of
the old one; the subject is re-decided. `HD-INV-3` still prevents reuse after
consumption; `HD-INV-4` now prevents stale first use. Decisions that are not
about workspace state (`SET_MODE`, `SUSPEND`, `RESUME`, `ABANDON`,
`EXTEND_BUDGET`, capability grants over a `PROJECT`/`CAPABILITY` subject) are not
snapshot-bound.

| file | section | change |
|---|---|---|
| `design/domain-model.md` | §9.A `HumanDecision` | added `snapshot_bound`, `subject_snapshot_id`, `decision_state`; added `HD-INV-4` |
| `design/domain-model.md` | §10.4, §11, §12 | listed `decision_state`; added the `HumanDecision → RealitySnapshot` cardinality; added `G-10` (shared with F01-001) |
| `design/transition-matrix.md` | §1.2 Evidence shorthand | `DEC(K)` now requires `decision_state = VALID` |
| `design/transition-matrix.md` | §7.5 (new) `HumanDecision.decision_state` | full state machine: `VALID`, `CONSUMED`, `STALE`, `EXPIRED`, `VOID`, with the terminality note (former §7.5 `Escalation.status` is now §7.6) |
| `design/transition-matrix.md` | §9.3 | added the row forbidding citation of a decision with `decision_state ≠ VALID` |
| `design/authority-matrix.md` | §1.1 Grant kinds | `HUMAN_DECISION` expiry now includes `decision_state` leaving `VALID` |
| `design/authority-matrix.md` | §6 Enforcement points | added the `decision freshness` row |
| `design/evidence-model.md` | §5.1 (new) Decision currency | the bound/current/stale/renewal table and why evidence invalidation alone was insufficient |
| `design/evidence-model.md` | §2.3 Anti-patterns | added the stale-approval row |

---

## F01-005 — Legal contract status transitions cannot preserve the required contract hash

**Fix.** `status` is removed from the `contract_hash` preimage, alongside
`contract_hash` itself. Status is lifecycle, not content: the hash pins what the
contract authorizes. With it excluded, `DRAFT → ACTIVE` and the later
`ACTIVE → FULFILLED`/`REVOKED`/`EXPIRED`/`SUPERSEDED` transitions all preserve
the hash pinned into `StageRun.contract_hash`, recomputation still succeeds, and
`XC-13` holds unchanged — `status` remains the only member that may differ
between persisted documents sharing a `contract_id`. Mutation of any member
inside the preimage after `ACTIVE` is an integrity violation as before.

| file | section | change |
|---|---|---|
| `design/schema/stage_contract.schema.json` | top-level `$comment` (HASHING) | preimage is now the document minus `contract_hash` **and** `status`, with the reason stated |
| `design/schema/stage_contract.schema.json` | cross-constraint `XC-12` | rule text updated; notes the hash is invariant across status transitions |
| `design/schema/stage_contract.schema.json` | cross-constraint `XC-13` | notes that `contract_hash` is identical across documents sharing a `contract_id` |
| `design/domain-model.md` | §6.1 `StageContract` | `contract_hash` field note; rewrote `C-INV-2` |
| `design/transition-matrix.md` | §6 `StageContract.status` | added the "Status is outside the hash preimage" note |

---

## F01-006 — Cross-axis guards deadlock startup and initial dispatch

**Fix, two cycles.**

*Startup.* §3 gains a startup exception: `∅ → PENDING` and `PENDING → READY` are
additionally legal while `project.lifecycle = PLANNING`. A first stage can
therefore reach `READY`, which is what `PLANNING → ACTIVE` requires. No other
axis-2 row is legal during `PLANNING`.

*Initial dispatch.* The composition table denied worker dispatch in
`CONTRACTED`, while `CONTRACTED → RUNNING` needs a `DISPATCHED` run, which needs
an accepted `WorkerInvocation`. The `CONTRACTED` row now permits exactly the
first invocation of the run allocated under the active contract; every later
invocation still requires `RUNNING`. `READY → RUNNING` stays illegal, so the
activation record and `effective_capabilities` still exist before anything is
dispatched. Both fixes are mode-independent.

| file | section | change |
|---|---|---|
| `design/transition-matrix.md` | §3 preamble | added the **Startup exception** paragraph |
| `design/transition-matrix.md` | §3 rows | `∅ → PENDING` and `PENDING → READY` preconditions now name the permitted project lifecycles |
| `design/transition-matrix.md` | §8 Composition table | split `ACTIVE / PENDING, READY, CONTRACTED` into a `CONTRACTED` row permitting the run's first invocation and a `PENDING, READY` row; added the cycle-breaking note and the note limiting the table to hot-path operations |

---

## F01-007 — Judgmental reviews are simultaneously forbidden and required as transition evidence

**Fix.** A new kernel-minted EVIDENCE record, `ReviewAttestation`, separates the
judgement from the measurement of it — the same shape as `WorkerReceipt`, which
is EVIDENCE that a worker said something without making what it said true. The
attestation asserts a different proposition from the review: that a review
meeting its `ReviewSpec`'s quorum and computed independence was performed over a
stated snapshot and returned verdict `v`. The `Review` verdict stays CLAIM, no
CLAIM is promoted to EVIDENCE, and the `RVW(v)` token throughout the transition
matrix now resolves to the attestation, so judgmental completion is possible
without letting a worker's own verdict gate satisfaction. Minting requires a new
`KERNEL` capability, `review.attest`.

| file | section | change |
|---|---|---|
| `design/domain-model.md` | §7.3.1 (new) `ReviewAttestation` | entity table plus `RA-INV-1`…`RA-INV-4` |
| `design/domain-model.md` | §11 Cardinality | added `ReviewSpec → ReviewAttestation` and `ReviewAttestation → Review` |
| `design/domain-model.md` | §12 `G-1` | added `ReviewAttestation` to the permitted `required_evidence` set; stated that a `Review` is never cited directly |
| `design/authority-matrix.md` | §2.5 Evidence and review | added `KERNEL` capability `review.attest` |
| `design/authority-matrix.md` | §6 Enforcement points | `receipt minting` row now covers `review.attest` |
| `design/transition-matrix.md` | §1.2 Evidence shorthand | `RVW(v)` redefined as the kernel-minted `ReviewAttestation` |
| `design/transition-matrix.md` | §9.3 | added rows forbidding a non-kernel `ReviewAttestation` and direct citation of a `Review` as evidence |
| `design/evidence-model.md` | §2 class table, §2.1 | added `ReviewAttestation` as EVIDENCE; listed `review.attest` among minting capabilities |
| `design/evidence-model.md` | §2.2 Promotion rules | added the `Review` verdict → `ReviewAttestation` row |
| `design/evidence-model.md` | §2.3 Anti-patterns | added the peer-verdict-as-measurement row |
| `design/evidence-model.md` | §4 Deriving `observed_satisfaction` | input `R` is now the `ReviewAttestation` set; the evaluator no longer reads `Review` records directly |
| `design/worker_provider.md` | §6 Invocation sequence | added the attestation-minting step |
