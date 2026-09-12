# MICRO-01

Micro-resolution pass over the three findings left `UNRESOLVED` by
[CLOSURE-01.md](CLOSURE-01.md). Baseline `d44b5d6` (`HEAD`, clean), 2026-09-12.

The owner decided the four open mechanisms (D1–D5 below). This record applies
those decisions and says, per decision, exactly which file and section changed.
No mechanism was redesigned and no alternative was proposed. `F01-001`,
`F01-004`, `F01-005` and `F01-006` were not touched; their files were read only
to confirm the edits below do not intersect them.

Findings addressed: `F01-002` (D1, D3, D4), `F01-003` (D2, D3, D4),
`F01-007` (D5).

---

## D1 — `lookup` as an operation distinct from `invoke` (`F01-002`)

| file | section | change |
|---|---|---|
| `worker_provider.md` | §2 Types, line 34 | Added `LookupResult`: exactly one of `LIVE{handle: Opaque}`, `FINISHED{outcome: InvocationOutcome}`, `ABSENT`. `handle` is `Opaque` to core and only resumes tracking under the same key. |
| `worker_provider.md` | §3 Operations, line 61 | Added the `lookup` row: `(idempotency_key: Hash) -> LookupResult`, required_capability **`recovery.reconcile`** (not `worker.invoke`), idempotent, non-blocking, errors `UNAVAILABLE`. |
| `worker_provider.md` | §3, prose after the operations table (lines 65–69) | States that `lookup` is a distinct operation, not a mode of `invoke`: it takes a key and nothing else — no `InvocationRequest`, no `ToolBridge`, no request bytes — so it cannot start, resume, extend or bill an execution, and it is the only provider operation reachable under `recovery.reconcile`. |
| `worker_provider.md` | §4, `WP-15` (line 102) | Reworded. The persisted `request_ref` is now the durable, auditable record of what was sent and the reason the key survives a restart. Removed "Recovery replays those stored bytes"; recovery reads them and never re-sends them. The no-rebuilt-context rule is unchanged. |
| `worker_provider.md` | §4, `WP-16` (line 103) | Rewritten. `lookup` is an operation in its own right, gated by `recovery.reconcile` rather than `worker.invoke`; it returns `FINISHED`/`LIVE`/`ABSENT` and executes nothing in all three cases; recovery resolves by `lookup` alone and never resubmits `request_ref` to `invoke`, because an `ABSENT` key would execute the work instead of reporting that nothing happened. An implemented `lookup` that cannot answer a given key still yields `UNRESOLVABLE` + `Escalation(RECOVERY_AMBIGUITY)`. |
| `worker_provider.md` | §4, `WP-17` (line 104) | **New contract — inadmissibility.** A provider that cannot implement `lookup` is inadmissible for governed mutation: not registrable for, or dispatchable under, any run whose contract can reach a `CommitIntent` or any capability mutating state outside the kernel's store. Without `lookup` the `G-9` ordering has no reader. |
| `worker_provider.md` | §5 kernel-side capability table (line 123) | Added `recovery.reconcile` → `lookup`, "never `invoke`". `worker.invoke` still covers `preflight` and `invoke` only. |
| `worker_provider.md` | §6.1 Recovery sequence, step 2 (line 157) | Replaced "re-submit the stored `request_ref` bytes" with `lookup(idempotency_key)` under `recovery.reconcile`; stored bytes are never re-sent, context never rebuilt. |
| `worker_provider.md` | §6.1 closing prose (line 170) | Now states `lookup` is the only provider call the sequence makes and it executes nothing. |
| `worker_provider.md` | §7 Conformance, `CF-11`–`CF-15` (lines 189–193) | `CF-11` reworded off "replayed" (it still tests `WP-6` on `invoke`). `CF-12` restated in terms of `lookup` returning `ABSENT`. New `CF-13` (`FINISHED`/`LIVE` answered with no usage delta), `CF-14` (a failed/timed-out/cancelled/refused execution is reported as such), `CF-15` (a provider without `lookup` is refused registration). |
| `transition-matrix.md` | §7.2, reconciliation rows (lines 313–314) and following note | Preconditions now read `lookup(idempotency_key)` returned `FINISHED(outcome)` / `ABSENT`, not "replaying the persisted `request_ref`". Note adds resubmitting `request_ref` to the illegal list. |
| `transition-matrix.md` | §9.3 (line 518) | **New illegal row:** resubmit a persisted `request_ref` to `invoke` as a means of reconciling an invocation. |
| `transition-matrix.md` | §9.3 (line 519) | **New illegal row:** dispatch a governed mutation to a provider that does not implement `lookup` (`WP-17`). |
| `domain-model.md` | §8.1 `WorkerInvocation.request_ref` (line 580) | Note rewritten: persisted for durable key + auditability; recovery reads it and never re-sends it; resolution is by `lookup` alone. |
| `domain-model.md` | §8.2 `WorkerReceipt.attribution` (line 605) | Note now defines `DIRECT` explicitly (minted under `worker.invoke` from an invocation this controller ran) and `RECONCILED` as minted from what `lookup` reported, including the `ABSENT` case where the receipt records that nothing ran. |
| `domain-model.md` | §8.2 `W-INV-3` (line 613) | "Replay under the original `idempotency_key`" → `lookup` on the original key reports the prior outcome without executing; resubmitting `request_ref` is named illegal. |
| `domain-model.md` | §5 `RUN-INV-3` (line 295) | Reconciliation means "by `lookup` on its persisted `idempotency_key` or by matching the repository against `operation_token`" (also carries D2, below). |
| `authority-matrix.md` | §2.3 `recovery.reconcile` (line 94) | Permission text now names `WorkerProvider.lookup(idempotency_key)` instead of replaying an `InvocationRequest`, and states the capability authorizes **observation only**: no `invoke`, no repository mutation, no operation creation (also carries D2). |
| `authority-matrix.md` | §6 enforcement points, "controller recovery" (line 291) | Resolution is by `lookup(idempotency_key)` or an `operation_token` scan, both under `recovery.reconcile` (also carries D2 and D4). |

---

## D2 — Scoping the universal recovery gate (`F01-003`)

The gate forbids **initiating** new external effects while any operation is
unreconciled. It does not forbid the reconciliation transition itself.

| file | section | change |
|---|---|---|
| `transition-matrix.md` | §5, `RUN-INV-3` gate (line 214) | Restated as "initiates no new external effect — no provider `invoke`, no repository mutation, and therefore no `WorkerInvocation` dispatch and no `CommitIntent` transition past `AUTHORIZED` **under `commit.apply`**". Membership condition `{NOT_REQUIRED, ADOPTED, ORPHANED}` unchanged. |
| `transition-matrix.md` | §5, scope table (lines 225–228) | **The exemption row added here.** Row 1: dispatching, calling `invoke`, mutating the repository, or advancing past `AUTHORIZED` under `commit.apply` — forbidden while any record is `PENDING`/`UNRESOLVABLE`. Row 2 (**exemption**): any transition whose `required_capability` is `recovery.reconcile` — `lookup`, the `operation_token` scan, and the state change recording the result, **including `APPLYING → APPLIED` and `APPLYING → FAILED` in §7.4** — permitted, and only for the operation being reconciled. |
| `transition-matrix.md` | §5, line 230 | Adds why: without the exemption the gate is unsatisfiable, since the only transitions that move a record out of `PENDING` are the ones it would block. |
| `transition-matrix.md` | §9.3 (line 516) | **Contradiction with §7.4 removed.** The illegal row is narrowed to advancing past `AUTHORIZED` **under `commit.apply`**, and its rationale now says the bar is on *initiating* an effect, with the §7.4 reconciliation rows out of `APPLYING` exempt by the §5 gate and the only way the barrier is ever cleared. |
| `transition-matrix.md` | §7.4, note after the reconciliation rows (line 362) | States these rows are the only transitions permitted under the barrier, by the §5 exemption; each initiates nothing. |
| `domain-model.md` | §5 `RUN-INV-3` (line 295) | Matched to the scoped gate: "initiates no new external effect", advance past `AUTHORIZED` qualified by `commit.apply`, and an explicit sentence exempting transitions taken under `recovery.reconcile`. |
| `authority-matrix.md` | §2.3 (line 94), §6 (line 291) | `recovery.reconcile` is named the sole capability exempt from the `RUN-INV-3` barrier; the enforcement row gates only the *initiation* of an effect and says the check does not gate the reconciling transitions themselves. |

`transition-matrix.md:461` and `:312` in the CLOSURE-01 baseline are now
`:516` and `:356`; they no longer contradict.

---

## D3 — `ADOPTED` means established, not succeeded

| file | section | change |
|---|---|---|
| `transition-matrix.md` | §7.2, reconciliation row (line 313, formerly `:275`) | Was `→ COMPLETED` for any prior outcome. Now `→ COMPLETED, FAILED, TIMED_OUT, CANCELLED`, with an explicit mapping from `outcome.status`: `COMPLETED → COMPLETED`, `FAILED → FAILED`, `TIMED_OUT → TIMED_OUT`, `CANCELLED → CANCELLED`, `REFUSED → FAILED`, "and never `COMPLETED` for a non-`COMPLETED` outcome". Evidence is a `WR` carrying `outcome.termination_reason` with `attribution = RECONCILED`. (`REFUSED` maps to `FAILED` because `WorkerInvocation.status` has no `REFUSED` member; the refusal is preserved in the receipt's `termination_reason`, per `WP-13`.) |
| `transition-matrix.md` | §7.2, note (line 316 ff.) | `ADOPTED` is set on the `FINISHED(outcome)` row **for every outcome status**, and the note states adoption establishes the outcome rather than asserting success — "exactly as the commit side preserves a `DIVERGED` receipt (§7.4)". |
| `worker_provider.md` | §6.1, step 3 (line 158, formerly `:148`) | Was "prior outcome returned ⇒ invocation → `COMPLETED`". Now mints the receipt with `outcome.termination_reason` and takes the status `outcome.status` maps to, with the same five-way mapping; state `ADOPTED`. |
| `worker_provider.md` | §6.1, note after the sequence | New paragraph: `ADOPTED` means the outcome was established, not that it succeeded; collapsing a failure into `COMPLETED` would manufacture a success no provider reported; this is the commit side's rule for a `DIVERGED` receipt. |
| `transition-matrix.md` | §7.4, note (line 366 ff.) | The `DIVERGED` row's `ADOPTED` is now stated in the same words — "the outcome was established, and it was a failure" — so both sites read identically. |
| `domain-model.md` | §8.2 `W-INV-4` (line 618) | **New invariant:** a `RECONCILED` receipt carries the outcome that was found, not a better one; a prior `FAILED`/`TIMED_OUT`/`CANCELLED`/`REFUSED` is preserved and never recorded as `COMPLETED`. |
| `worker_provider.md` | §7, `CF-14` (line 192) | Conformance check for the same rule. |

---

## D4 — One reconciliation-state derivation table

| file | section | change |
|---|---|---|
| `transition-matrix.md` | **new §5.1 "Reconciliation-state derivation" (line 234)** | The single derivation for both `WorkerInvocation.reconciliation_state` and `CommitIntent.reconciliation_state`. Rows: current epoch → `NOT_REQUIRED`; old epoch **and** non-terminal status → `PENDING`, spelled out for **every** non-terminal status of either entity (`PENDING`/`DISPATCHED`/`RUNNING`; `PROPOSED`/`BLOCKED`/`AUTHORIZED`/`APPLYING`), "with no exception"; old epoch **and** terminal status → `NOT_REQUIRED`; recovery executed under `recovery.reconcile` → `ADOPTED`/`ORPHANED`/`UNRESOLVABLE`, **terminal**, taking precedence over `NOT_REQUIRED`, and never reverting. |
| `transition-matrix.md` | §5.1, consequences table | Two shared consequences. (a) An old-epoch record that never initiated its effect — a `WorkerInvocation` still `PENDING`, a `CommitIntent` in `PROPOSED`/`BLOCKED`/`AUTHORIZED` — reconciles to `ORPHANED` once recovery confirms no effect token exists outside the kernel; `ORPHANED` is the positive finding that nothing landed. (b) A `LIVE` answer keeps the record `PENDING` until the outcome arrives, then `ADOPTED` — it does **not** fall back to `NOT_REQUIRED`. Closes with the `ADOPTED`-means-established rule shared with D3. |
| `transition-matrix.md` | §5.1 header prose | Names the four referring sites — §7.2, §7.4, `worker_provider.md` §6.1, `authority-matrix.md` §6 — and states they refer here rather than restating the derivation. |
| `transition-matrix.md` | §7.4, new row (line 359) | **New reconciliation row** giving old-epoch `PROPOSED`/`BLOCKED`/`AUTHORIZED` intents the path the general rule requires: status unchanged, `recovery.reconcile`, precondition "never reached `APPLYING`, so no repository mutation was ever initiated under its `operation_token`; a scan finds no revision carrying the token and a fresh `SNAP` still matches `base_revision_id`", evidence `SNAP` matching `base_revision_id`. Resolves `ORPHANED`. |
| `transition-matrix.md` | §7.4, note (line 366 ff.) | Says reconciliation states are set "per §5.1" and explains the fourth row: these intents are `PENDING` like every other non-terminal old-epoch record, carry no effect token in the repository, and resolve `ORPHANED` without touching `status`. |
| `transition-matrix.md` | §7.2, note (line 316 ff.) | Says reconciliation states are set "per §5.1"; the `LIVE` case is deferred to §5.1 rather than restated. |
| `worker_provider.md` | §6.1, steps 1 and 5 (lines 156, 160) | Step 1 derives the state "per the single derivation table (transition-matrix §5.1)" rather than stating its own rule. Step 5 (`LIVE`) now keeps the state `PENDING` and adopts on the terminal outcome; the previous "state returns to `NOT_REQUIRED` on its terminal receipt" is removed. |
| `domain-model.md` | §8.1 `WorkerInvocation.reconciliation_state` (line 582) | Note replaced by a pointer to §5.1 as the sole derivation, plus the `ADOPTED`-means-established clause. |
| `domain-model.md` | §8.3 `CommitIntent.reconciliation_state` (line 639) | Note replaced by the same pointer, and explicitly: `PENDING` covers every non-terminal old-epoch status, `PROPOSED`/`BLOCKED`/`AUTHORIZED` included, not only `APPLYING`. |
| `authority-matrix.md` | §6, "controller recovery" (line 291) | Cites §5.1 as the derivation and names `PENDING` as the unresolved state, which the previous wording only implied. |

---

## D5 — Attestation-typed review preconditions (`F01-007`)

| file | section | change |
|---|---|---|
| `domain-model.md` | §8.3 `CommitIntent.preconditions` (line 640) | `reviews: Set<Ref<Review>>` → **`reviews: Set<Ref<ReviewAttestation>>`**, with a note that it holds kernel-minted attestations, never `Review` records (`G-1`). |
| `transition-matrix.md` | §7.3 `Finding.status`, `∅ → OPEN` (line 333, formerly `:289`) | Precondition now "raised within a `Review` that a `ReviewAttestation` counts in its `review_ids`"; `required_evidence` changed from "`Review` record" to `RVW(v)` — the attestation covering that `Review` — with an explicit note that the `Review` itself is never cited (`G-1`, §9.3). |
| `schema/stage_contract.schema.json` | `$defs.EscalationTrigger.enum` (line 269) | Added `"RECOVERY_AMBIGUITY"` after `"INTEGRITY_VIOLATION"`. The enum now matches `domain-model.md` §9.B, so a contract can name the trigger in `escalation_triggers`. |

Not changed, and deliberately: `domain-model.md:512`
(`ReviewAttestation.review_ids: Set<Ref<Review>>`) — an attestation *cites* the
reviews it measures; that reference is the mechanism `G-1` relies on, not a
consumer of `Review` as evidence. `domain-model.md:281` (`StageRun.reviews`) is a
run's inventory of review records, not `required_evidence`.

---

## Files touched

| file | decisions |
|---|---|
| `design/worker_provider.md` | D1, D3, D4 |
| `design/transition-matrix.md` | D1, D2, D3, D4, D5 |
| `design/domain-model.md` | D1, D2, D3, D4, D5 |
| `design/authority-matrix.md` | D1, D2, D4 |
| `design/schema/stage_contract.schema.json` | D5 |

`design/evidence-model.md` needed no edit: §3.2.1 already describes recovery as
querying the outside world by the persisted identity (D1-compatible), and its
reconciliation-closure check already gates "a later dispatch or apply", which is
the D2 scoping. Under D4 the old-epoch `PROPOSED`/`BLOCKED`/`AUTHORIZED` intents
are `PENDING` rather than `NOT_REQUIRED`, which removes the conflict CLOSURE-01
raised against that check. `design/roadmap_adapter.md` and
`design/schema/events.schema.json` were unaffected.

No `src/` code was written (phase DESIGN-01). No implementation tests were run;
the schema enum edit was verified by inspection, not by a validator.

NEW_ESCALATION: None.
