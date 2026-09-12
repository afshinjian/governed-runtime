# DESIGN-01 — `RoadmapAdapter` Interface Specification

Interface only. No implementation, no transport, no concrete source format.
A roadmap source is an **input**, never an evidence source (`R-INV-1`).

---

## 1. Position

| property | value |
|---|---|
| direction | core calls adapter; adapter never calls core |
| trust | untrusted input; every returned value is `CLAIM` class until normalized and persisted by the kernel |
| purity | no workspace writes, no process execution, no capability held beyond those in §5 |
| identity | `adapter_id` plus `adapter_version`; both recorded on every `Roadmap` |
| statefulness | stateless between calls; all continuity carried in `cursor` and `source_digest` |

---

## 2. Types

| type | definition |
|---|---|
| `SourceLocator` | `{uri: Str(1..2048), credentials_ref: Str(1..128)?, options: {Str: Str}}` — `uri` opaque to core; `credentials_ref` names a secret, never carries one |
| `RawSource` | `{bytes_ref: ArtifactRef, fetched_at: Ts, source_digest: Hash, etag: Str?, cursor: Str?}` |
| `StageDescriptor` | `{key: Str(1..64), title: Str(1..256), intent: Str(1..8192), ordinal_hint: uint32, depends_on_keys: Set<Str(1..64)>, declared_status_hint: DeclaredStatus, labels: {Str: Str}, source_span: Str(1..256)?}` |
| `NormalizedRoadmap` | `{stages: [StageDescriptor], normalized_digest: Hash, source_digest: Hash, adapter_id: Str, adapter_version: SemVer, warnings: [Diagnostic]}` |
| `Diagnostic` | `{code: Str(1..64), severity: Enum<INFO,WARN,ERROR>, message: Str(1..1024), source_span: Str?}` |
| `DriftReport` | `{drift_state: Enum<IN_SYNC,SOURCE_AHEAD,RUNTIME_AHEAD,DIVERGED,UNREADABLE>, added_keys: Set<Str>, removed_keys: Set<Str>, changed_keys: Set<Str>, reordered: bool, source_digest: Hash, checked_at: Ts}` |
| `WritebackRequest` | `{stage_key: Str, observed_satisfaction: ObservedSatisfaction, observed_at: Ts, evidence_summary_ref: ArtifactRef, dry_run: bool}` |
| `WritebackResult` | `{applied: bool, new_source_digest: Hash?, diagnostics: [Diagnostic]}` |
| `AdapterError` | `{code: ErrorCode, message: Str(1..1024), retryable: bool, retry_after_ms: Ms?}` |

### 2.1 `ErrorCode`

| code | meaning | core response |
|---|---|---|
| `NOT_FOUND` | locator resolves to nothing | project stays `DRAFT` |
| `UNAUTHORIZED` | credentials rejected | `Escalation(CAPABILITY_DENIED)` |
| `UNPARSEABLE` | source fetched but not normalizable | `drift_state = UNREADABLE`, `Escalation(ROADMAP_DIVERGED)` |
| `CYCLIC_DEPENDENCIES` | `depends_on_keys` form a cycle | import rejected, `Escalation(CONTRACT_AMBIGUITY)` |
| `DUPLICATE_KEY` | two descriptors share a `key` | import rejected |
| `RATE_LIMITED` | upstream throttling | retry with `retry_after_ms` |
| `UNAVAILABLE` | transient upstream failure | retry with backoff |
| `WRITEBACK_REFUSED` | source is read-only or rejected the write | `writeback_mode` downgraded to `ADVISORY` |
| `VERSION_CONFLICT` | source changed under an in-flight writeback | re-`detect_drift`, then retry |

---

## 3. Operations

| operation | signature | required_capability | idempotent | may block | errors |
|---|---|---|---|---|---|
| `describe` | `() -> {adapter_id, adapter_version, capabilities: Set<Enum<READ,DRIFT,WRITEBACK,INCREMENTAL>>, schema_versions: [SemVer]}` | none | yes | no | none |
| `validate_locator` | `(SourceLocator) -> [Diagnostic]` | none | yes | no | `NOT_FOUND`, `UNAUTHORIZED` |
| `fetch` | `(SourceLocator, cursor: Str?) -> RawSource` | `roadmap.import` | yes for a fixed source state | yes | `NOT_FOUND`, `UNAUTHORIZED`, `RATE_LIMITED`, `UNAVAILABLE` |
| `normalize` | `(RawSource) -> NormalizedRoadmap` | `roadmap.import` | yes, deterministically | no | `UNPARSEABLE`, `CYCLIC_DEPENDENCIES`, `DUPLICATE_KEY` |
| `detect_drift` | `(SourceLocator, known_source_digest: Hash, known_keys: Set<Str>) -> DriftReport` | `roadmap.import` | yes | yes | `UNAVAILABLE`, `UNAUTHORIZED`, `UNPARSEABLE` |
| `writeback` | `(SourceLocator, [WritebackRequest]) -> WritebackResult` | `roadmap.writeback` | yes, keyed on `(stage_key, observed_at)` | yes | `WRITEBACK_REFUSED`, `VERSION_CONFLICT`, `UNAUTHORIZED` |

---

## 4. Contracts

| id | contract |
|---|---|
| `RA-1` | `normalize` is a pure function of `RawSource.bytes_ref`. Same bytes, same `normalized_digest`, on every adapter instance at the same `adapter_version`. |
| `RA-2` | `StageDescriptor.key` is stable across fetches for the same logical stage. Key instability presents as `removed + added` and destroys run history linkage. |
| `RA-3` | `declared_status_hint` populates `Stage.declared_status` only. It never touches `observed_satisfaction` and never gates a transition (`G-6`). |
| `RA-4` | `depends_on_keys` must resolve within the returned stage set and must be acyclic; the adapter reports the cycle rather than breaking it arbitrarily. |
| `RA-5` | `ordinal_hint` is advisory. The kernel owns `stage_order` and may reorder for dependency correctness. |
| `RA-6` | The adapter never learns capabilities, budgets, receipts, decisions, or run state. Its input is a locator; its output is descriptors. |
| `RA-7` | `writeback` is advisory by default. Failure never blocks a stage transition; it downgrades `writeback_mode` and emits a `Diagnostic`. |
| `RA-8` | `writeback` sends `observed_satisfaction` and an evidence summary reference. It never sends raw evidence, secrets, or prompt content. |
| `RA-9` | An adapter that cannot implement `detect_drift` declares so in `describe`; the kernel then treats every import as a full re-read and sets `drift_state = UNREADABLE` between reads. |
| `RA-10` | All adapter output is size-bounded: ≤ 4096 stages, ≤ 64 KiB per `intent`, ≤ 256 diagnostics. Exceeding a bound is `UNPARSEABLE`. |
| `RA-11` | Timeouts and retries are the kernel's: the adapter reports `retryable` and `retry_after_ms` and does not retry internally. |
| `RA-12` | Credentials are resolved by the kernel from `credentials_ref` under `secret.read` and injected into the adapter's environment; the adapter must not persist, log, or return them. |

---

## 5. Capability surface

| capability | held during | note |
|---|---|---|
| `roadmap.import` | `fetch`, `normalize`, `detect_drift` | |
| `roadmap.writeback` | `writeback` | `SUPERVISED` requires `CONFIRM` per call |
| `net.egress.allowlist` | `fetch`, `detect_drift`, `writeback` | hosts from policy allowlist |
| `fs.read` | `fetch` when the locator is workspace-local | scope-bounded |
| `secret.read` | credential resolution, performed by the kernel on the adapter's behalf | value never returned to core |

Everything else: DENY. In particular an adapter never holds `fs.write`,
`proc.exec.*`, `worker.invoke`, `snapshot.take`, `validation.attest`, or any
`stage.*`, `contract.*`, or `commit.*` capability.

---

## 6. Lifecycle mapping

| adapter result | kernel effect |
|---|---|
| `normalize` success on first import | stages materialized in `PENDING`; project `DRAFT` → `PLANNING` |
| `detect_drift` = `IN_SYNC` | no change |
| `detect_drift` = `SOURCE_AHEAD` | re-`fetch` and re-`normalize`; new keys become `PENDING` stages; project `SETTLING` → `ACTIVE` if applicable |
| `detect_drift` = `RUNTIME_AHEAD` | `writeback` attempted if `writeback_mode ≠ NONE`; otherwise recorded only |
| `detect_drift` = `DIVERGED` | `Escalation(ROADMAP_DIVERGED)`; roadmap frozen pending a decision |
| `detect_drift` = `UNREADABLE` | project `PLANNING` → `DRAFT`, or `Escalation(ROADMAP_DIVERGED)` if already `ACTIVE` |
| removed key whose stage has runs | stage is not deleted; it moves to `ABANDONED` only by `DEC(ABANDON)` |
| changed `intent` on a stage with an `ACTIVE` contract | contract is not mutated; `Escalation(CONTRACT_AMBIGUITY)` proposing a superseding contract |

---

## 7. Conformance checklist

| id | check |
|---|---|
| `CF-1` | `normalize` called twice on identical bytes yields byte-identical `NormalizedRoadmap` minus timestamps |
| `CF-2` | keys stable across two `fetch` calls with no source change |
| `CF-3` | cyclic input yields `CYCLIC_DEPENDENCIES`, never a silently broken edge |
| `CF-4` | duplicate keys yield `DUPLICATE_KEY`, never last-wins |
| `CF-5` | `writeback` with `dry_run = true` performs no source mutation and returns the same diagnostics as the real call |
| `CF-6` | no adapter output contains a credential, token, or secret value |
| `CF-7` | oversize source yields `UNPARSEABLE` rather than truncated output |
| `CF-8` | adapter performs no workspace write during any operation |
