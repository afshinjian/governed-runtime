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
| `CLAIM` | "what does someone say is true?" | any actor, typically a worker | no — only its provenance is verifiable | **never** | yes, trivially |
| `EVIDENCE` | "what was measured about reality?" | runtime kernel, or an attested external executor | yes — replay or re-observation | yes, as `required_evidence` | no — minting requires `validation.attest`, `commit.apply`, or `snapshot.take` |
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
| `EVIDENCE` → current | `EVIDENCE` bound to the newest `RealitySnapshot` covering its scope | a receipt goes stale, it does not become false |
| `DECISION` → `AUTHORITY` | a `HumanDecision` with non-empty `grants` | the grant is realized only through an activation record |
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
| 6 | `Project.event_head = event_hash` of the highest `seq`; updated in the same atomic write as the append |

### 3.2 Append protocol

| step | operation | failure handling |
|---|---|---|
| 1 | write payload to artifact store, obtain `payload_ref` | abort; nothing appended |
| 2 | reserve `seq = event_seq + 1` under a per-project lock | contention retries; `seq` is never skipped |
| 3 | read `prev_event_hash = event_head` | — |
| 4 | compute `event_hash` | — |
| 5 | atomically persist the event and advance `event_head`, `event_seq` | on partial failure the reservation is rolled back and the artifact becomes unreferenced (`refcount = 0`) |
| 6 | only now is the state change observable to any reader | `AE-INV-2` |

### 3.3 Verification

| check | procedure | failure |
|---|---|---|
| chain continuity | for each `seq` from 0 to head: recompute `event_hash`, compare to stored; compare `prev_event_hash` to predecessor's `event_hash` | `INTEGRITY_VIOLATION`, project → `SUSPENDED_BY_INTEGRITY` |
| gaplessness | `seq` values form `0..head` with no gaps or duplicates | same |
| payload binding | `payload_digest == payload_ref.digest`, and the stored bytes rehash to it unless `redacted` | same |
| authority binding | every event with `capability_used` has an `authority_ref` resolving to a live grant at `recorded_at` | same |
| monotonic time | `recorded_at` non-decreasing in `seq`, allowing for `clock_skew_ms` | `Escalation(INTEGRITY_VIOLATION)`, severity `MEDIUM` |
| evidence reachability | every `required_evidence` cited by a transition event resolves to an event of class `EVIDENCE` with `seq` lower than the transition's | `INTEGRITY_VIOLATION` |

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
| `R` | `Review` set with `input_snapshot_id = S.snapshot_id` meeting spec quorum and independence |
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
| authority trace | for one action: capability used, activation record, grant chain, mode, policy digest | answering "what allowed this?" |
| claim ledger | every `Claim` with its `corroboration` outcome | measuring how often self-reports held up |

Each export is itself written to the artifact store and appended as an
`AuditEvent`, so the act of exporting is part of the record.
