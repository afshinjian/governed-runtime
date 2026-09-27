# DESIGN-01 — Evidence Model

Two stores and one taxonomy:

| component | holds | addressing | mutability |
|---|---|---|---|
| Artifact store | bytes (outputs, diffs, prompts, indexes, payloads) | content address `Hash` | immutable; payload removable by tombstone |
| Event log | ordered facts about the project | `(project_id, seq)` with hash chain | append-only |
| Epistemic taxonomy | how much each record is allowed to prove | `AuditEvent.epistemic_class` | fixed at append |

---

## 1. Artifact store

### 1.1 Addressing

| property | rule |
|---|---|
| key | `"<alg>:<lowerhex(alg(octets))>"`, `alg = sha256` |
| octets hashed | the raw, pre-compression bytes |
| write | content-defined; writing existing content is a no-op returning the same key |
| collision | treated as `INTEGRITY_VIOLATION`, never as a hit |
| encoding | stored octets may be `GZIP`/`ZSTD`; the key always addresses the decoded form |
| size limit | per-class, enforced at write; oversize input is truncated into a new artifact with `truncated: true` recorded in its metadata, and the untruncated digest recorded alongside |

### 1.2 Artifact metadata (stored beside, not inside, the content)

| field | type | notes |
|---|---|---|
| `digest` | `Hash` | the key |
| `media_type` | `Str` | IANA type |
| `byte_len` | `uint64` | of decoded form |
| `encoding` | `Enum<IDENTITY,GZIP,ZSTD>` | of stored form |
| `first_seen_at` | `Ts` | |
| `producer` | `ActorRef` | who first wrote it |
| `retention_class` | `Enum<PERMANENT,STANDARD,EPHEMERAL>` | §6 |
| `refcount` | `uint32` | number of live event references |
| `truncated` | `bool` | |
| `untruncated_digest` | `Hash?` | present iff `truncated` |
| `redacted` | `bool` | payload replaced by tombstone |
| `tombstone` | `{redacted_at: Ts, decision_id: Ref<HumanDecision>, reason: Str}?` | |

### 1.3 Store invariants

| id | invariant |
|---|---|
| `AS-1` | Content is never overwritten. A changed byte is a different artifact. |
| `AS-2` | Deletion removes payload only. `digest`, metadata, and every referencing event survive. |
| `AS-3` | An artifact referenced by a `PERMANENT` event cannot be collected while the project is not `ARCHIVED`. |
| `AS-4` | Secrets never enter the store. Values resolved under `secret.read` are referenced by name and a salted digest, never by value. |
| `AS-5` | Reads are digest-verified on the way out; a mismatch is `INTEGRITY_VIOLATION`, not a cache miss. |

---

## 2. The CLAIM / EVIDENCE / DECISION / AUTHORITY distinction

The central rule of the runtime: **these four are different kinds of thing, and
only three of them can make a stage satisfied.**

| class | answers | produced by | verifiable by | can gate a transition | can be fabricated by a worker |
|---|---|---|---|---|---|
| `CLAIM` | "what does someone say is true?" | any actor, typically a worker | no — only its provenance is verifiable | **never on its asserted content**; a row may name it as a prerequisite (`G-1`) and gate on its existence, its provenance, and the control fields the runtime establishes — for an `Escalation`, `trigger`, `status`, `severity`, `auto_resolvable` and the holder bindings — which prove only what the runtime recorded. The asserted fields, `summary` and `evidence_refs` and any `Claim` they carry, gate nothing | yes, trivially |
| `EVIDENCE` | "what was measured about reality?" | runtime kernel, or an attested external executor | yes — replay or re-observation | yes, as `required_evidence` | no — minting requires `validation.attest`, `review.attest`, `commit.apply`, `recovery.reconcile`, or `snapshot.take`, all `KERNEL` |
| `DECISION` | "what did an authenticated human choose?" | `HUMAN` actor only | yes — signature and nonce | yes, as `DECIDE(K)`/`CONFIRM` | no — `HD-INV-1` |
| `AUTHORITY` | "what was someone permitted to attempt?" | `ContractActivationRecord`, `HumanDecision.grants` | yes — grant chain replay | yes, as `required_capability` | no — `AX-5`, `AX-7` |

### 2.1 Record classification

| record | class | why |
|---|---|---|
| `Stage.declared_status` | `CLAIM` | an assertion by whoever wrote it |
| `Claim` inside a `WorkerReceipt` | `CLAIM` | self-report, whatever its confidence value |
| `MutationProposal` | `CLAIM` | a proposed change, not an applied one |
| `Finding` | `CLAIM` about a defect | promoted only when its `evidence_refs` are themselves EVIDENCE |
| `Review` verdict | `CLAIM` when `reviewer_kind = AUTOMATED` or `PEER_WORKER`; `DECISION`-adjacent when `HUMAN` | a reviewer states a judgement; independence is what gives it weight |
| `ReviewAttestation` | `EVIDENCE` that a qualifying review **exists** | the runtime measured the review's spec, quorum, independence and bound snapshot — not the judgement inside it, exactly as `WorkerReceipt` measures the invocation and not the assertion |
| `WorkerReceipt` | `EVIDENCE` that a worker **said** something | the runtime measured the invocation, not the assertion |
| `ValidationReceipt` | `EVIDENCE` | runtime executed a pinned command and observed the result |
| `CommitReceipt` | `EVIDENCE` | runtime applied and re-observed the tree |
| `RealitySnapshot` | `EVIDENCE` | runtime observed the workspace directly |
| `Stage.observed_satisfaction` | derived `EVIDENCE` | a function of receipts over a snapshot |
| `HumanDecision` | `DECISION` | authenticated human choice, with `evidence_shown` |
| `ContractActivationRecord` | `AUTHORITY` | the grant that made a run's actions permissible |
| `HumanDecision.grants` / `revokes` | `AUTHORITY` | capability delta |
| `Escalation` | `CLAIM` by the runtime that it cannot proceed | resolves via `DECISION` |
| `AuditEvent` | the envelope; carries one of the four in `epistemic_class` | |

### 2.2 Promotion rules

| from | to | requires |
|---|---|---|
| `CLAIM` → `EVIDENCE` | never directly | a claim is corroborated by *separate* evidence; the claim itself stays a claim, and `Claim.corroboration` records the outcome |
| `Review` verdict → `EVIDENCE` | never; the kernel mints a `ReviewAttestation` | the attestation is EVIDENCE of a *different proposition* — that a review meeting the spec's quorum and independence was performed over a stated snapshot and returned verdict `v`. The verdict's substance stays CLAIM, which is why `RA-INV-3` forbids treating the reviewer's reasoning as fact and why an attestation over a `FAIL` is as much EVIDENCE as one over a `PASS`. This is the only route by which a judgmental criterion is discharged, and it requires `review.attest`, a `KERNEL` capability |
| `EVIDENCE` → current | `EVIDENCE` bound to the newest `RealitySnapshot` covering its scope | a receipt goes stale, it does not become false |
| `DECISION` → `AUTHORITY` | a `HumanDecision` with non-empty `grants` or `revokes` | a run grant is realized through an activation record; a project grant is realized by the decision itself and is never written into an activation (`AX-3`, authority-matrix §5.3). A decision with empty `grants` and empty `revokes` promotes to nothing: it authorizes its own act and delegates no capability (authority-matrix §5.2) |
| `AUTHORITY` → satisfaction | never | `AX-9`: permission to attempt is not proof of outcome |

### 2.3 Anti-patterns this taxonomy exists to prevent

| pattern | which rule stops it |
|---|---|
| a worker writing "tests pass" and the stage advancing | `G-6`, illegal-section row on `declared_status`; only `ValidationReceipt` counts |
| a worker emitting a document shaped like a receipt | `V-INV-1`; minting requires `validation.attest`, a `KERNEL` capability |
| a reviewer reviewing its own output | `RV-INV-1`, `RC-2`; independence is computed from provenance, not declared |
| a stale green build carrying a later change | `S-INV-4`; a new snapshot demotes `SATISFIED` to `STALE` |
| a human clicking approve on an empty screen | `HD-INV-2`; `evidence_shown` is mandatory |
| one approval authorizing an unbounded series of actions | `HD-INV-3`; single-use nonce plus `scope` |
| a runtime resolving its own escalation | illegal-section row; `auto_resolvable = false` requires a `DECISION` |
| grant creep across attempts | `AX-3`, `RUN-INV-2`; capabilities freeze at activation |
| a peer worker's review verdict counting as measurement | `G-1`, `RA-INV-1`; `RVW(v)` resolves to a kernel-minted `ReviewAttestation`, never to the `Review` |
| a capability appearing because it was in the ceiling and the role table | `AX-11`, `A-INV-3`; the register names who may grant it, and the grant record is cited per capability |
| an approval from before the workspace changed still discharging `CONFIRM` | `HD-INV-4`; a snapshot-bound decision goes `STALE` with its snapshot |
| a restart re-running a worker or re-landing a commit | `G-9`, `RUN-INV-3`, `CM-INV-2`; identity is durable before the effect and the effect is adopted, not repeated |

---

## 3. Hash-chained event log

### 3.1 Chain construction

| step | rule |
|---|---|
| 1 | `body = AuditEvent` minus `event_hash` and minus `signature` |
| 2 | `canonical = JCS(body)` per RFC 8785 |
| 3 | `event_hash = "sha256:" + lowerhex(sha256(canonical))` |
| 4 | `body.prev_event_hash` is the `event_hash` of the event at `seq - 1` in the same project |
| 5 | genesis: `seq = 0`, `prev_event_hash = "sha256:" + lowerhex(sha256(project_id ‖ 0x00 ‖ schema_version))` |
| 6 | `Project.event_head = event_hash` of the highest `seq`; updated in the same atomic write as the append. At `seq = 0` that write also installs the `Project` record and initializes `event_seq = 0`: a project and its first event become durable together, and no reader ever observes a project whose chain state is uninitialized |

### 3.2 Append protocol

| step | operation | failure handling |
|---|---|---|
| 1 | write payload to artifact store, obtain `payload_ref` | abort; nothing appended |
| 2 | reserve `seq = event_seq + 1` under a per-project lock; for a project with no prior event, `event_seq` is unset and the reserved value is `seq = 0` | contention retries; `seq` is never skipped |
| 3 | read `prev_event_hash = event_head`; at `seq = 0`, `event_head` is unset and `prev_event_hash` is the §3.1 genesis constant instead | — |
| 4 | compute `event_hash` | — |
| 5 | atomically persist the event and advance `event_head`, `event_seq` | on partial failure the reservation is rolled back and the artifact becomes unreferenced (`refcount = 0`) |
| 6 | only now is the state change observable to any reader | `AE-INV-2` |

### 3.2.1 External side effects

The §3.2 transaction is atomic over the event and the log head. It is not atomic
with anything outside the store — a provider invocation and a repository
mutation both happen outside it, and a controller can die between the effect and
the receipt. The ordering rule that makes such a gap recoverable rather than
permanent:

| step | rule |
|---|---|
| 1 | before any external effect, its durable identity is appended: `idempotency_key` with `request_ref` for an invocation, `operation_token` for a commit intent, each carrying the `controller_epoch` |
| 2 | the effect carries that identity outward — the key on the provider call, the token in the revision's trailers — so the external world holds the same identifier the log does |
| 3 | the effect is performed |
| 4 | the receipt is appended per §3.2 |

A crash between 1 and 4 leaves an operation whose identity is durable and whose
outcome is not. Recovery reads those operations, queries the outside world by
that identity, and appends either an adopting receipt
(`attribution = RECONCILED`) or a record that nothing happened — under
`recovery.reconcile`, never by repeating the effect. An effect performed before
its identity is durable is unrecoverable by construction and is illegal
(transition-matrix §9.3); `G-9` states the rule.

| verification check added by this ordering | procedure | failure |
|---|---|---|
| effect attribution | every `WorkerReceipt` and `CommitReceipt` resolves to an earlier event carrying its `idempotency_key` or `operation_token` | `INTEGRITY_VIOLATION` |
| reconciliation closure | no non-terminal operation with `controller_epoch < project.controller_epoch` precedes a later dispatch or apply on the same run | `INTEGRITY_VIOLATION`; `RUN-INV-3` |

### 3.3 Verification

| check | procedure | failure |
|---|---|---|
| chain continuity | for each `seq` from 0 to head: recompute `event_hash`, compare to stored; compare `prev_event_hash` to predecessor's `event_hash` | `INTEGRITY_VIOLATION`, project → `SUSPENDED_BY_INTEGRITY` |
| gaplessness | `seq` values form `0..head` with no gaps or duplicates | same |
| payload binding | `payload_digest == payload_ref.digest`, and the stored bytes rehash to it unless `redacted` | same |
| authority binding | every event with `capability_used` resolves it at `recorded_at` by exactly one authority form (`AX-1`): a `KERNEL`-class capability by the kernel's own holding, requiring `actor.actor_kind = RUNTIME` and absent `authority_ref` (`AX-7`); `decision.record` by the principal's own holding, requiring `actor.actor_kind = HUMAN` with `auth_method ∈ {SESSION, SIGNATURE, MTLS}` and absent `authority_ref` (`AX-15`); any other `HUMAN`-class capability by `authority_ref` naming the live `HumanDecision` that authorized this act (authority-matrix §5.2); every other capability by `authority_ref` naming a live grant carrying it — a `ContractActivationRecord` whose `granted_capabilities` contains it, or a project grant per authority-matrix §5.3 | same |
| monotonic time | `recorded_at` non-decreasing in `seq`, allowing for `clock_skew_ms` | `Escalation(INTEGRITY_VIOLATION)`, severity `MEDIUM` |
| evidence reachability | for each citation in the row's `required_evidence` (`G-1`), and for a disjunctive citation the one alternative the transition event names, that citation resolves to an earlier event of the same project with `seq` lower than the transition's, of the class its record carries: `EVIDENCE` for an evidence citation; `AUTHORITY` for an activation; `DECISION` for a `HumanDecision`; `CLAIM` for an `Escalation`; and any class for an `AuditEvent` the row names, including one that persisted a cited artifact or durable identity. A cell element naming no record is a precondition and resolves to no event. A citation of any other kind is not resolved by this check and its row is not closed (`G-1`) | `INTEGRITY_VIOLATION` |

Verification requires only the event records; the artifact store is needed for
payload binding but not for chain continuity.

### 3.4 Ordering

| property | rule |
|---|---|
| total order | `seq` within a project; chain order is authoritative for replay |
| causal order | `causal_parent` is advisory and may point to any lower `seq`, including in another subtree |
| cross-project | no global chain; projects are independent roots |
| concurrency | appends serialize on the per-project lock; concurrent producers observe a single total order |

---

## 4. Deriving `observed_satisfaction`

Pure function, runtime-only, recomputed rather than stored as opinion.

| input | source |
|---|---|
| `S` | newest `RealitySnapshot` with `completeness = COMPLETE` covering `contract.scope_include` |
| `C` | `contract.acceptance_criteria` from the pinned `contract_hash` |
| `V` | `ValidationReceipt` set with `input_snapshot_id = S.snapshot_id` |
| `R` | `ReviewAttestation` set with `input_snapshot_id = S.snapshot_id`, one per mandatory judgmental criterion's spec; each attests quorum and independence were met (`RA-INV-2`). The evaluator reads attestations, never `Review` records directly — `G-1` |
| `W` | waivers: `HumanDecision{kind ∈ {WAIVE, ACCEPT_RISK}}`, unexpired |

| condition, evaluated in order | result |
|---|---|
| `S` does not exist | `UNKNOWN` |
| some required validator could not execute, or a `DETERMINISTIC` spec produced divergent receipts | `INDETERMINATE` |
| every mandatory `c ∈ C` is `MET` (by `V`/`R`) or `WAIVED` (by `W`) | `SATISFIED` |
| some mandatory `c` is `UNMET` and `declared_status = CLAIMED_COMPLETE` | `CONTRADICTED` |
| some mandatory `c` is `UNMET` | `UNSATISFIED` |
| no mandatory `c` is `UNMET` and some mandatory `c` is `UNEVALUATED` | `PARTIAL` |
| a previous result was `SATISFIED` and `S` is newer than the receipts that produced it | `STALE` |

`declared_status` appears exactly once above, and only to distinguish
`CONTRADICTED` from `UNSATISFIED` — it never turns an `UNSATISFIED` into
anything better.

---

## 5. Evidence currency

| term | definition |
|---|---|
| bound | a receipt names the `RealitySnapshot` it measured |
| current | its bound snapshot is the newest `COMPLETE` snapshot covering the relevant scope |
| stale | bound snapshot superseded by a newer one whose `drift_summary` touches the scope |
| replayable | `determinism_class = DETERMINISTIC`; `replay_key = H(contract_hash ‖ spec_id ‖ input tree_digest ‖ toolchain_digest ‖ env_digest)` |
| replay hit | a current receipt with the same `replay_key` exists; re-execution may be skipped and the existing receipt cited |
| replay mismatch | re-execution under an identical `replay_key` produced a different `outcome` ⇒ `Escalation(NONDETERMINISM)` and both receipts retained |

Only *current* evidence satisfies `required_evidence`. Stale evidence is never
deleted; it remains a true statement about an earlier state of the world.

### 5.1 Decision currency

Currency applies to decisions on the same terms, because an approval is a
statement about what the human was shown.

| term | definition |
|---|---|
| snapshot-bound | `HumanDecision.snapshot_bound = true`: the decision speaks about the state of the workspace |
| bound | such a decision names `subject_snapshot_id`, the `COMPLETE` snapshot its `evidence_shown` artifacts were measured against |
| current | `subject_snapshot_id` is still the newest `COMPLETE` snapshot covering the subject's scope; `decision_state = VALID` |
| stale | superseded by a newer snapshot whose `drift_summary` touches that scope ⇒ `decision_state = STALE` |
| renewal | a stale decision is never revived. The subject is re-decided, producing a new `HumanDecision` with a new nonce over the new snapshot |

An unconsumed approval therefore cannot outlive the reality it was granted
against. Re-running validations and reviews over the new workspace produces
current EVIDENCE but no current DECISION, so `CONFIRM` and `DECIDE(K)` are
unmet until the human sees the changed artifacts and decides again
(`HD-INV-4`). Evidence invalidation alone was never enough: the two classes go
stale independently and both are checked.

---

## 6. Retention and redaction

| retention_class | collected when | examples |
|---|---|---|
| `PERMANENT` | never before project `ARCHIVED`; then only by explicit decision | receipts, decisions, activation records, snapshots' file indexes, diffs |
| `STANDARD` | on project `ARCHIVED`, or after the configured window once `refcount = 0` | worker outputs, prompt bundles, review bodies |
| `EPHEMERAL` | once the owning run is terminal | stdout/stderr tails, intermediate tool logs |

| redaction rule | detail |
|---|---|
| what changes | artifact payload only, replaced by a tombstone record |
| what never changes | `digest`, `payload_digest`, `event_hash`, `prev_event_hash`, chain continuity |
| authority | `audit.redact`, a `HUMAN`-class capability, plus a `HumanDecision` naming the artifact |
| effect on verification | payload-binding check reports `REDACTED` rather than failing; continuity check is unaffected |
| effect on transitions | an event whose evidence artifact is redacted can no longer be re-verified; a transition that depended on it is flagged `EVIDENCE_UNRECOVERABLE` on audit, never retroactively reversed |

---

## 7. Export

| artifact | contents | use |
|---|---|---|
| chain manifest | `(seq, event_hash, prev_event_hash, event_type, epistemic_class, actor, payload_digest)` per event | offline verification without payloads |
| evidence bundle | for one stage: pinned contract, activation record, all receipts, snapshots, reviews, findings, decisions, plus the chain manifest slice | answering "why is this stage satisfied?" |
| authority trace | for one action: capability used, mode, policy digest, and the authority the action was exercised under — the activation record and grant chain for a run grant; the granting `HumanDecision` for a project grant; the authorizing `HumanDecision` for a per-act exercise; the kernel's own holding for a `KERNEL` capability; and for `decision.record` the recording principal's own authenticated holding under `AX-1`'s named exception (`AX-15`), naming the authenticated principal and `auth_method` with no authority record and no `authority_ref` | answering "what allowed this?" |
| claim ledger | every `Claim` with its `corroboration` outcome | measuring how often self-reports held up |

Each export is itself written to the artifact store and appended as an
`AuditEvent`, so the act of exporting is part of the record.
