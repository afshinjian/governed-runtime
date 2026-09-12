# DESIGN-01 — Domain Model

Normative model for a project-agnostic governed AI development runtime.
No identifiers, vocabulary, or lifecycle rules from any specific host project,
model vendor, or agent implementation appear in this document. Vendor-specific
concerns are confined to adapters (`roadmap_adapter.md`) and providers
(`worker_provider.md`).

---

## 0. Notation

### 0.1 Scalar types

| Type | Definition |
|---|---|
| `Id` | ULID, 26 chars, Crockford base32, lexicographically time-sortable |
| `Hash` | `"<alg>:<lowerhex>"`, `alg` ∈ {`sha256`, `sha512`}; default `sha256` |
| `Ts` | RFC 3339 UTC instant, millisecond precision, `Z` suffix mandatory |
| `Ms` | `uint64` milliseconds |
| `Str(n..m)` | UTF-8 NFC string, length bounds in Unicode scalar values |
| `Path` | POSIX relative path, workspace-rooted, no `..`, no leading `/` |
| `Glob` | POSIX glob over `Path` |
| `SemVer` | `MAJOR.MINOR.PATCH` |
| `Unit` | `uint64` abstract cost unit, provider-normalized |
| `Ratio` | `float64` in `[0.0, 1.0]` |
| `Opaque` | provider-defined string, core MUST NOT parse or branch on it |

### 0.2 Type constructors

| Form | Meaning |
|---|---|
| `T?` | optional; absent ≠ null-valued |
| `[T]` | ordered list, duplicates significant |
| `Set<T>` | unordered, duplicate-free |
| `{K: V}` | map |
| `Enum<A,B>` | closed enumeration; unknown value = integrity violation |
| `Ref<E>` | `Id` constrained to entity `E`, referential integrity enforced |

### 0.3 Column legend for field tables

| Column | Meaning |
|---|---|
| `req` | `Y` required, `N` optional, `D` derived (computed, never accepted as input) |
| `mut` | `I` immutable after write, `A` append-only, `M` mutable |
| `src` | who may supply the value: `H` human, `W` worker, `R` runtime kernel, `X` external adapter |

---

## 1. Shared value types

### 1.1 `ActorRef`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `actor_kind` | `Enum<HUMAN,WORKER,RUNTIME,ADAPTER,EXTERNAL>` | Y | I | R | |
| `actor_id` | `Str(1..128)` | Y | I | R | stable principal identifier |
| `principal_key_id` | `Str(1..128)?` | N | I | R | required when `actor_kind = HUMAN` |
| `auth_method` | `Enum<NONE,SESSION,SIGNATURE,MTLS,DELEGATED>` | Y | I | R | `NONE` forbidden for `HUMAN` |
| `on_behalf_of` | `ActorRef?` | N | I | R | delegation depth ≤ 2 |

### 1.2 `ArtifactRef`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `digest` | `Hash` | Y | I | R | content address; store key |
| `media_type` | `Str(1..128)` | Y | I | R | IANA media type |
| `byte_len` | `uint64` | Y | I | R | |
| `encoding` | `Enum<IDENTITY,GZIP,ZSTD>` | Y | I | R | of stored octets |
| `retention_class` | `Enum<PERMANENT,STANDARD,EPHEMERAL>` | Y | I | R | see `evidence-model.md` §6 |
| `redacted` | `bool` | Y | M | R | payload removed, digest retained |

### 1.3 `Budget` / `BudgetUsage`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `wall_clock_ms` | `Ms` | Y | I | H/R | |
| `worker_invocations` | `uint32` | Y | I | H/R | |
| `cost_units` | `Unit` | Y | I | H/R | |
| `validation_executions` | `uint32` | Y | I | H/R | |
| `commits` | `uint32` | Y | I | H/R | |
| `escalations` | `uint32` | Y | I | H/R | ceiling before forced suspension |

`BudgetUsage` has the same field names with `uint64`/`Unit` counters, `mut = A`,
`src = R` only. Workers MUST NOT report their own usage as authoritative;
usage is derived from receipts.

### 1.4 `CommandSpec`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `argv` | `[Str(1..4096)]` | Y | I | W/H | non-empty; no shell interpolation |
| `cwd` | `Path` | Y | I | W/H | must lie inside contract scope |
| `env_allowlist` | `Set<Str(1..128)>` | Y | I | W/H | names only; values injected by runtime |
| `network` | `Enum<NONE,ALLOWLIST,ANY>` | Y | I | W/H | `ANY` requires `net.egress.any` |
| `timeout_ms` | `Ms` | Y | I | W/H | ≤ contract deadline remainder |
| `stdin_ref` | `ArtifactRef?` | N | I | W/H | |

### 1.5 `MutationProposal`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `op` | `Enum<CREATE,MODIFY,DELETE,RENAME,CHMOD>` | Y | I | W | |
| `path` | `Path` | Y | I | W | |
| `rename_to` | `Path?` | N | I | W | required iff `op = RENAME` |
| `before_digest` | `Hash?` | Y | I | R | absent iff `op = CREATE`; runtime-observed |
| `after_ref` | `ArtifactRef?` | N | I | W | absent iff `op = DELETE` |
| `mode` | `uint16?` | N | I | W | required iff `op = CHMOD` |
| `in_scope` | `bool` | D | I | R | `path` matches contract scope |

### 1.6 `Claim`

A structured, **non-authoritative** worker assertion. Never gates a transition.

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `claim_id` | `Id` | Y | I | R | |
| `subject` | `Enum<CRITERION,FILE,BEHAVIOR,DEPENDENCY,RISK,COMPLETION>` | Y | I | W | |
| `subject_ref` | `Str(1..256)?` | N | I | W | criterion id or path |
| `assertion` | `Str(1..4096)` | Y | I | W | |
| `confidence` | `Ratio` | Y | I | W | self-reported |
| `offered_evidence` | `[ArtifactRef]` | Y | I | W | may be empty |
| `corroboration` | `Enum<UNCHECKED,CORROBORATED,CONTRADICTED,UNVERIFIABLE>` | D | M | R | set only by runtime |

---

## 2. `Project`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `project_id` | `Id` | Y | I | R | |
| `name` | `Str(1..128)` | Y | M | H | |
| `slug` | `Str(1..64)` | Y | I | H | `^[a-z0-9][a-z0-9-]*$` |
| `schema_version` | `SemVer` | Y | M | R | domain model version |
| `lifecycle` | `ProjectLifecycle` | Y | M | R | axis 1, §9.1 |
| `suspension` | `SuspensionState` | Y | M | R | axis 3, §9.3 — orthogonal |
| `suspension_ref` | `Ref<Escalation>?` | Y | M | R | required iff `suspension ≠ NONE` |
| `governance_mode` | `Enum<SUPERVISED,AUTONOMOUS>` | Y | M | H | changeable only by `HumanDecision` |
| `workspace_root` | `Path` | Y | I | H | |
| `roadmap_id` | `Ref<Roadmap>?` | N | M | R | absent while `DRAFT` |
| `capability_ceiling` | `Set<CapabilityId>` | Y | M | H | upper bound on all grants |
| `policy_digest` | `Hash` | Y | M | R | digest of active policy document |
| `budget` | `Budget` | Y | M | H | |
| `budget_used` | `BudgetUsage` | D | A | R | |
| `event_head` | `Hash` | D | M | R | head of hash-chained log |
| `event_seq` | `uint64` | D | M | R | monotonic, gapless |
| `snapshot_current` | `Ref<RealitySnapshot>?` | D | M | R | |
| `created_at` / `updated_at` | `Ts` | Y | M | R | |
| `created_by` | `ActorRef` | Y | I | R | `actor_kind` MUST be `HUMAN` |

**P-INV-1** `governance_mode` transitions require a `HumanDecision` of kind `SET_MODE`.
**P-INV-2** No grant anywhere in the project may exceed `capability_ceiling`.
**P-INV-3** `lifecycle`, `suspension` are independent; neither encodes the other.

---

## 3. `Roadmap`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `roadmap_id` | `Id` | Y | I | R | |
| `project_id` | `Ref<Project>` | Y | I | R | |
| `adapter_id` | `Str(1..64)` | Y | I | X | see `roadmap_adapter.md` |
| `adapter_version` | `SemVer` | Y | I | X | |
| `source_uri` | `Str(1..2048)` | Y | I | X | opaque to core |
| `source_digest` | `Hash` | Y | M | R | digest of raw source as fetched |
| `normalized_digest` | `Hash` | Y | M | R | digest of canonical normalized form |
| `revision` | `uint32` | Y | M | R | increments on re-import |
| `stage_order` | `[Ref<Stage>]` | Y | M | R | total order, duplicate-free |
| `dependency_edges` | `Set<{from: Ref<Stage>, to: Ref<Stage>}>` | Y | M | R | MUST be acyclic |
| `drift_state` | `Enum<IN_SYNC,SOURCE_AHEAD,RUNTIME_AHEAD,DIVERGED,UNREADABLE>` | D | M | R | |
| `drift_detected_at` | `Ts?` | D | M | R | |
| `writeback_mode` | `Enum<NONE,ADVISORY,AUTHORITATIVE>` | Y | M | H | `AUTHORITATIVE` needs `roadmap.writeback` |
| `frozen` | `bool` | Y | M | R | true while any run is active |
| `imported_at` | `Ts` | Y | M | R | |
| `imported_by` | `ActorRef` | Y | M | R | `ADAPTER` or `HUMAN` |

**R-INV-1** The roadmap is an **input**, never an evidence source. A stage's
`declared_status` may be sourced from it; `observed_satisfaction` never may.

---

## 4. `Stage`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `stage_id` | `Id` | Y | I | R | |
| `roadmap_id` | `Ref<Roadmap>` | Y | I | R | |
| `project_id` | `Ref<Project>` | Y | I | R | |
| `ordinal` | `uint32` | Y | M | R | position in `stage_order` |
| `key` | `Str(1..64)` | Y | I | X | adapter-stable natural key |
| `title` | `Str(1..256)` | Y | M | X | |
| `intent` | `Str(1..8192)` | Y | M | X | human-authored goal text |
| `depends_on` | `Set<Ref<Stage>>` | Y | M | R | |
| `lifecycle` | `StageLifecycle` | Y | M | R | axis 2, §9.2 |
| `suspension` | `SuspensionState` | Y | M | R | axis 3, §9.3 — orthogonal |
| `suspension_ref` | `Ref<Escalation>?` | Y | M | R | required iff `suspension ≠ NONE` |
| **`declared_status`** | `DeclaredStatus` | Y | M | W/X/H | §4.1 — assertion, never authority |
| `declared_status_source` | `ActorRef` | Y | M | R | who asserted it |
| `declared_status_at` | `Ts` | Y | M | R | |
| `declared_status_basis` | `[ArtifactRef]` | Y | M | W | evidence *offered* with the claim |
| **`observed_satisfaction`** | `ObservedSatisfaction` | D | M | R | §4.2 — computed only |
| `observed_satisfaction_at` | `Ts?` | D | M | R | |
| `observed_basis` | `[Hash]` | D | M | R | receipt hashes that produced it |
| `observed_evaluator_version` | `SemVer?` | D | M | R | evaluator that computed it |
| `criteria_state` | `{Str: CriterionState}` | D | M | R | per acceptance criterion |
| `active_contract_id` | `Ref<StageContract>?` | N | M | R | at most one `ACTIVE` |
| `runs` | `[Ref<StageRun>]` | D | A | R | |
| `attempt_count` | `uint32` | D | M | R | |
| `max_attempts` | `uint32` | Y | M | H | exceeding forces escalation |
| `terminal_reason` | `Enum<SATISFIED,REJECTED,ABANDONED,SUPERSEDED>?` | N | I | R | set once on terminal entry |
| `created_at` / `updated_at` | `Ts` | Y | M | R | |

### 4.1 `DeclaredStatus` — what someone *says*

| value | meaning | epistemic class |
|---|---|---|
| `NOT_STARTED` | no actor claims work has begun | CLAIM |
| `IN_PROGRESS` | an actor claims work is underway | CLAIM |
| `CLAIMED_COMPLETE` | an actor claims the stage is done | CLAIM |
| `CLAIMED_BLOCKED` | an actor claims it cannot proceed | CLAIM |
| `WITHDRAWN` | a prior claim was retracted by its source | CLAIM |

### 4.2 `ObservedSatisfaction` — what the runtime *verified*

| value | meaning | epistemic class |
|---|---|---|
| `UNKNOWN` | no evaluation has run against current reality | EVIDENCE-absent |
| `UNSATISFIED` | evaluated; ≥1 mandatory criterion demonstrably unmet | EVIDENCE |
| `PARTIAL` | evaluated; some mandatory criteria met, none failed, ≥1 unevaluated | EVIDENCE |
| `SATISFIED` | every mandatory criterion has a passing receipt over the current snapshot | EVIDENCE |
| `CONTRADICTED` | `declared_status = CLAIMED_COMPLETE` while evidence shows `UNSATISFIED` | EVIDENCE |
| `STALE` | prior `SATISFIED` invalidated by a newer `RealitySnapshot` | EVIDENCE |
| `INDETERMINATE` | evaluation attempted but required validators unavailable or nondeterministic | EVIDENCE-failure |

### 4.3 `CriterionState`

| field | type | req | mut | src |
|---|---|---|---|---|
| `criterion_id` | `Str(1..64)` | Y | I | R |
| `outcome` | `Enum<UNEVALUATED,MET,UNMET,WAIVED,INDETERMINATE>` | D | M | R |
| `basis_refs` | `[Hash]` | D | M | R |
| `evaluated_against_snapshot` | `Ref<RealitySnapshot>?` | D | M | R |
| `waiver_decision_id` | `Ref<HumanDecision>?` | N | M | R |

**S-INV-1** `declared_status` and `observed_satisfaction` are separate fields with
separate writers. No code path derives one from the other.
**S-INV-2** Only `observed_satisfaction` gates `lifecycle` transitions to `SATISFIED`.
**S-INV-3** `declared_status = CLAIMED_COMPLETE` with `observed_satisfaction ∈
{UNSATISFIED, CONTRADICTED}` MUST raise an `Escalation` with trigger
`DECLARED_OBSERVED_CONFLICT`.
**S-INV-4** Any new `RealitySnapshot` touching a stage's scope demotes
`SATISFIED` → `STALE` until re-evaluated.

---

## 5. `StageRun`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `run_id` | `Id` | Y | I | R | |
| `stage_id` | `Ref<Stage>` | Y | I | R | |
| `project_id` | `Ref<Project>` | Y | I | R | |
| `attempt_ordinal` | `uint32` | Y | I | R | 1-based |
| `contract_id` | `Ref<StageContract>` | Y | I | R | |
| `contract_hash` | `Hash` | Y | I | R | pinned; drift = integrity violation |
| `activation_id` | `Ref<ContractActivationRecord>` | Y | I | R | |
| `lifecycle` | `RunLifecycle` | Y | M | R | §9.4 |
| `suspension` | `SuspensionState` | Y | M | R | orthogonal |
| `effective_capabilities` | `Set<CapabilityId>` | Y | I | R | frozen at activation |
| `input_snapshot_id` | `Ref<RealitySnapshot>` | Y | I | R | pre-run ground truth |
| `output_snapshot_id` | `Ref<RealitySnapshot>?` | N | M | R | post-run ground truth |
| `worker_invocations` | `[Ref<WorkerInvocation>]` | D | A | R | |
| `validation_ops` | `[Ref<ValidationOperation>]` | D | A | R | |
| `reviews` | `[Ref<Review>]` | D | A | R | |
| `commit_intents` | `[Ref<CommitIntent>]` | D | A | R | |
| `escalations` | `[Ref<Escalation>]` | D | A | R | |
| `budget_allocated` | `Budget` | Y | I | R | ≤ contract ceiling |
| `budget_used` | `BudgetUsage` | D | A | R | |
| `started_at` | `Ts` | Y | I | R | |
| `deadline_at` | `Ts` | Y | I | R | |
| `ended_at` | `Ts?` | N | I | R | |
| `outcome` | `Enum<SATISFIED,REJECTED,ABORTED,EXPIRED>?` | N | I | R | |
| `outcome_receipt_hash` | `Hash?` | D | I | R | |

**RUN-INV-1** Exactly one `StageRun` per stage may be non-terminal.
**RUN-INV-2** `effective_capabilities` is immutable for the run's life; widening
requires abort + new activation.

---

## 6. Contract entities

### 6.1 `StageContract`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `contract_id` | `Id` | Y | I | R | |
| `stage_id` | `Ref<Stage>` | Y | I | R | |
| `project_id` | `Ref<Project>` | Y | I | R | |
| `contract_version` | `uint32` | Y | I | R | |
| `supersedes` | `Ref<StageContract>?` | N | I | R | |
| `status` | `Enum<DRAFT,ACTIVE,SUPERSEDED,REVOKED,EXPIRED,FULFILLED>` | Y | M | R | §9.5 |
| `objective` | `Str(1..8192)` | Y | I | H/W | |
| `scope_include` | `[Glob]` | Y | I | H/W | non-empty |
| `scope_exclude` | `[Glob]` | Y | I | H/W | evaluated after include |
| `acceptance_criteria` | `[AcceptanceCriterion]` | Y | I | H/W | non-empty |
| `required_validations` | `[ValidationSpec]` | Y | I | H/W | |
| `required_reviews` | `[ReviewSpec]` | Y | I | H/W | |
| `prohibited_actions` | `Set<Str(1..256)>` | Y | I | H/W | |
| `capability_request` | `Set<CapabilityId>` | Y | I | H/W | request, not grant |
| `worker_role` | `WorkerRole` | Y | I | H/W | |
| `budget_ceiling` | `Budget` | Y | I | H | |
| `deadline_ms` | `Ms` | Y | I | H | relative to activation |
| `escalation_triggers` | `Set<EscalationTrigger>` | Y | I | H/W | in addition to mandatory set |
| `rollback_policy` | `Enum<NONE,REVERT_COMMITS,RESTORE_SNAPSHOT>` | Y | I | H | |
| `evidence_retention_class` | `Enum<PERMANENT,STANDARD,EPHEMERAL>` | Y | I | H | |
| `authored_by` | `ActorRef` | Y | I | R | |
| `authored_at` | `Ts` | Y | I | R | |
| `contract_hash` | `Hash` | D | I | R | over all fields except itself; see schema |

#### `AcceptanceCriterion`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `criterion_id` | `Str(1..64)` | Y | I | H/W | unique within contract |
| `text` | `Str(1..2048)` | Y | I | H/W | |
| `kind` | `Enum<MECHANICAL,JUDGMENTAL>` | Y | I | H/W | |
| `verifier_ref` | `Str(1..64)` | Y | I | H/W | `ValidationSpec.spec_id` if `MECHANICAL`, else `ReviewSpec.spec_id` |
| `mandatory` | `bool` | Y | I | H/W | |
| `waivable` | `bool` | Y | I | H | if false, no `HumanDecision` can waive it |

#### `ValidationSpec`

| field | type | req | mut | src |
|---|---|---|---|---|
| `spec_id` | `Str(1..64)` | Y | I | H/W |
| `command` | `CommandSpec` | Y | I | H/W |
| `expected_exit_codes` | `Set<int32>` | Y | I | H/W |
| `determinism_class` | `Enum<DETERMINISTIC,FLAKY_TOLERANT,NONDETERMINISTIC>` | Y | I | H/W |
| `max_retries` | `uint8` | Y | I | H/W |
| `result_parser` | `Enum<EXIT_CODE,JSON_REPORT,JUNIT_XML,NONE>` | Y | I | H/W |

#### `ReviewSpec`

| field | type | req | mut | src |
|---|---|---|---|---|
| `spec_id` | `Str(1..64)` | Y | I | H/W |
| `reviewer_kind` | `Enum<AUTOMATED,PEER_WORKER,HUMAN>` | Y | I | H |
| `independence_required` | `Enum<INDEPENDENT,SHARED_CONTEXT_ALLOWED>` | Y | I | H |
| `blocking_severity` | `Enum<BLOCKER,MAJOR,MINOR>` | Y | I | H |
| `quorum` | `uint8` | Y | I | H | ≥ 1 |

**C-INV-1** Every `mandatory` criterion MUST resolve `verifier_ref` to a spec of
the matching kind. Unbound mandatory criteria make the contract unactivatable.
**C-INV-2** `contract_hash` is computed over the canonical JSON of every field
except `contract_hash`. Any mutation after `ACTIVE` is an integrity violation.
**C-INV-3** `capability_request` is a request. Grants come only from
`ContractActivationRecord`.

### 6.2 `ContractActivationRecord`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `activation_id` | `Id` | Y | I | R | |
| `contract_id` | `Ref<StageContract>` | Y | I | R | |
| `contract_hash` | `Hash` | Y | I | R | must equal contract's |
| `run_id` | `Ref<StageRun>` | Y | I | R | |
| `project_id` | `Ref<Project>` | Y | I | R | |
| `granted_capabilities` | `Set<CapabilityId>` | Y | I | R | AUTHORITY record |
| `denied_capabilities` | `{CapabilityId: Enum<NOT_IN_CEILING,ROLE_FORBIDDEN,MODE_FORBIDDEN,NO_GRANTOR,BUDGET,POLICY,NEVER_GRANTABLE>}` | Y | I | R | |
| `authority_chain` | `[{grantor: ActorRef, grant_kind: Enum<HUMAN_DECISION,POLICY,CEILING,ROLE_DEFAULT>, ref: Id?, at: Ts}]` | Y | I | R | non-empty |
| `governance_mode_at_activation` | `Enum<SUPERVISED,AUTONOMOUS>` | Y | I | R | |
| `policy_digest` | `Hash` | Y | I | R | |
| `input_snapshot_id` | `Ref<RealitySnapshot>` | Y | I | R | |
| `activated_by` | `ActorRef` | Y | I | R | `RUNTIME` only |
| `activated_at` | `Ts` | Y | I | R | |
| `expires_at` | `Ts` | Y | I | R | `activated_at + deadline_ms` |
| `revoked_at` | `Ts?` | N | I | R | |
| `revoked_by` | `ActorRef?` | N | I | R | |
| `revocation_reason` | `Enum<HUMAN_REVOKE,POLICY_CHANGE,SCOPE_BREACH,BUDGET,INTEGRITY,SUPERSEDED,EXPIRED>?` | N | I | R | |
| `record_hash` | `Hash` | D | I | R | |
| `prev_event_hash` | `Hash` | D | I | R | |

**A-INV-1** `granted_capabilities ⊆ capability_request ∩ role_defaults ∩
project.capability_ceiling ∩ mode_allowed`. Anything not granted is DENIED.
**A-INV-2** Activation is the **only** entity that confers authority on a run.

---

## 7. Evidence-producing entities

### 7.1 `ValidationOperation` — the *request* (CLAIM-adjacent, not evidence)

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `op_id` | `Id` | Y | I | R | |
| `run_id` | `Ref<StageRun>` | Y | I | R | |
| `stage_id` | `Ref<Stage>` | Y | I | R | |
| `validation_spec_id` | `Str(1..64)` | Y | I | W | must exist in pinned contract |
| `criterion_refs` | `Set<Str(1..64)>` | Y | I | W | criteria this op addresses |
| `command` | `CommandSpec` | Y | I | R | materialized from spec; worker may not alter argv |
| `requested_by` | `ActorRef` | Y | I | R | |
| `requested_at` | `Ts` | Y | I | R | |
| `required_capability` | `CapabilityId` | D | I | R | `proc.exec.validation` |
| `executor` | `Enum<RUNTIME_SANDBOX,EXTERNAL_ATTESTED>` | Y | I | R | |
| `attempt` | `uint8` | Y | I | R | |
| `status` | `Enum<REQUESTED,AUTHORIZED,DENIED,EXECUTING,COMPLETED,EXEC_FAILED,TIMED_OUT,CANCELLED>` | Y | M | R | |
| `denial_reason` | `Str(1..512)?` | N | I | R | |
| `receipt_id` | `Ref<ValidationReceipt>?` | N | I | R | |

### 7.2 `ValidationReceipt` — EVIDENCE

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `receipt_id` | `Id` | Y | I | R | |
| `op_id` | `Ref<ValidationOperation>` | Y | I | R | |
| `run_id` | `Ref<StageRun>` | Y | I | R | |
| `executed_at` | `Ts` | Y | I | R | |
| `duration_ms` | `Ms` | Y | I | R | |
| `executor_identity` | `ActorRef` | Y | I | R | `RUNTIME` or attested `EXTERNAL` |
| `executor_version` | `SemVer` | Y | I | R | |
| `exit_code` | `int32` | Y | I | R | |
| `outcome` | `Enum<PASS,FAIL,ERROR,TIMEOUT,SKIPPED>` | Y | I | R | derived from parser + expected codes |
| `stdout_ref` / `stderr_ref` | `ArtifactRef` | Y | I | R | truncation recorded in artifact meta |
| `report_refs` | `[ArtifactRef]` | Y | I | R | parsed structured results |
| `satisfies_criteria` | `Set<Str(1..64)>` | Y | I | R | ⊆ `op.criterion_refs`; empty if `outcome ≠ PASS` |
| `input_snapshot_id` | `Ref<RealitySnapshot>` | Y | I | R | what was measured |
| `env_digest` | `Hash` | Y | I | R | |
| `toolchain_digest` | `Hash` | Y | I | R | |
| `determinism_class` | `Enum<DETERMINISTIC,FLAKY_TOLERANT,NONDETERMINISTIC>` | Y | I | R | copied from spec |
| `replay_key` | `Hash?` | D | I | R | present iff `DETERMINISTIC` |
| `attestation` | `Hash` | D | I | R | signature over receipt body |
| `receipt_hash` | `Hash` | D | I | R | |
| `prev_event_hash` | `Hash` | D | I | R | |

**V-INV-1** Only `actor_kind = RUNTIME` (or an `EXTERNAL` executor holding
`validation.attest`) may mint a `ValidationReceipt`. A worker-authored receipt is
an integrity violation, not a validation result.
**V-INV-2** A receipt is bound to `input_snapshot_id`. It stops being current
evidence when the snapshot it measured is superseded within the stage's scope.

### 7.3 `Review`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `review_id` | `Id` | Y | I | R | |
| `run_id` | `Ref<StageRun>` | Y | I | R | |
| `stage_id` | `Ref<Stage>` | Y | I | R | |
| `review_spec_id` | `Str(1..64)` | Y | I | R | |
| `criteria_addressed` | `Set<Str(1..64)>` | Y | I | R | |
| `reviewer` | `ActorRef` | Y | I | R | |
| `reviewer_kind` | `Enum<AUTOMATED,PEER_WORKER,HUMAN>` | Y | I | R | must match spec |
| `independence` | `Enum<INDEPENDENT,SHARED_CONTEXT,SELF_REVIEW>` | D | I | R | computed from provenance |
| `inputs_digest` | `Hash` | Y | I | R | digest of the diff/snapshot reviewed |
| `input_snapshot_id` | `Ref<RealitySnapshot>` | Y | I | R | |
| `verdict` | `Enum<PASS,PASS_WITH_FINDINGS,FAIL,INCONCLUSIVE,ABSTAIN>` | Y | I | R | |
| `findings` | `[Ref<Finding>]` | D | A | R | |
| `evidence_refs` | `[ArtifactRef]` | Y | I | R | |
| `started_at` / `completed_at` | `Ts` | Y | I | R | |
| `review_hash` | `Hash` | D | I | R | |

**RV-INV-1** `independence = SELF_REVIEW` never satisfies a `ReviewSpec` with
`independence_required = INDEPENDENT`; it is recorded, and counted as `ABSTAIN`.

### 7.4 `Finding`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `finding_id` | `Id` | Y | I | R | |
| `review_id` | `Ref<Review>` | Y | I | R | |
| `run_id` | `Ref<StageRun>` | Y | I | R | |
| `severity` | `Enum<BLOCKER,MAJOR,MINOR,INFO>` | Y | M | R | downgrade requires decision |
| `category` | `Enum<CORRECTNESS,SCOPE_BREACH,EVIDENCE_GAP,SECURITY,REGRESSION,MAINTAINABILITY,PROCESS,PERFORMANCE>` | Y | I | R | |
| `claim` | `Str(1..4096)` | Y | I | R | the asserted defect |
| `location` | `{path: Path, line_start: uint32?, line_end: uint32?}?` | N | I | R | |
| `evidence_refs` | `[ArtifactRef]` | Y | I | R | empty ⇒ `confidence` capped at 0.5 |
| `confidence` | `Ratio` | Y | I | R | |
| `status` | `Enum<OPEN,ACKNOWLEDGED,FIXED,WAIVED,DISPUTED,INVALID>` | Y | M | R | §9.6 |
| `blocks_satisfaction` | `bool` | D | M | R | `severity ≥ spec.blocking_severity ∧ status ∈ {OPEN,ACKNOWLEDGED,DISPUTED}` |
| `waiver` | `{decision_id: Ref<HumanDecision>, justification: Str(1..2048), expires_at: Ts?}?` | N | I | R | |
| `resolved_by_run_id` | `Ref<StageRun>?` | N | M | R | |
| `resolution_receipt_hash` | `Hash?` | N | M | R | |

---

## 8. Action entities

### 8.1 `WorkerInvocation`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `invocation_id` | `Id` | Y | I | R | |
| `run_id` | `Ref<StageRun>` | Y | I | R | |
| `stage_id` | `Ref<Stage>` | Y | I | R | |
| `provider_id` | `Str(1..64)` | Y | I | R | registry key; core does not interpret |
| `provider_version` | `SemVer` | Y | I | R | |
| `worker_role` | `WorkerRole` | Y | I | R | |
| `execution_binding` | `Opaque` | Y | I | X | provider-defined target selector |
| `prompt_bundle_ref` | `ArtifactRef` | Y | I | R | exact bytes sent |
| `context_refs` | `[ArtifactRef]` | Y | I | R | |
| `context_digest` | `Hash` | D | I | R | over bundle + context, ordered |
| `granted_capabilities` | `Set<CapabilityId>` | Y | I | R | ⊆ run's effective set |
| `sandbox_profile_id` | `Str(1..64)` | Y | I | R | |
| `budget_allocated` | `Budget` | Y | I | R | |
| `idempotency_key` | `Hash` | Y | I | R | `H(context_digest ‖ role ‖ attempt)` |
| `dispatched_at` | `Ts` | Y | I | R | |
| `deadline_at` | `Ts` | Y | I | R | |
| `status` | `Enum<PENDING,DISPATCHED,RUNNING,COMPLETED,FAILED,TIMED_OUT,CANCELLED,REJECTED_BY_POLICY>` | Y | M | R | |
| `receipt_id` | `Ref<WorkerReceipt>?` | N | I | R | |

### 8.2 `WorkerReceipt`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `receipt_id` | `Id` | Y | I | R | |
| `invocation_id` | `Ref<WorkerInvocation>` | Y | I | R | |
| `ended_at` | `Ts` | Y | I | R | |
| `duration_ms` | `Ms` | Y | I | R | |
| `usage` | `{input_units: Unit, output_units: Unit, tool_calls: uint32, cost_units: Unit}` | Y | I | R | measured by runtime |
| `output_ref` | `ArtifactRef` | Y | I | R | raw provider output |
| `claims` | `[Claim]` | Y | I | W | non-authoritative |
| `proposed_mutations` | `[MutationProposal]` | Y | I | W | not yet applied |
| `requested_validations` | `[Ref<ValidationOperation>]` | D | A | R | |
| `capability_violations_attempted` | `[{capability: CapabilityId, at: Ts, detail: Str(1..1024)}]` | Y | I | R | |
| `scope_breaches_attempted` | `[{path: Path, at: Ts}]` | Y | I | R | |
| `termination_reason` | `Enum<COMPLETED,DEADLINE,BUDGET,POLICY_STOP,PROVIDER_ERROR,HUMAN_STOP,INTEGRITY>` | Y | I | R | |
| `attested_by` | `ActorRef` | Y | I | R | `RUNTIME` only |
| `receipt_hash` | `Hash` | D | I | R | |
| `prev_event_hash` | `Hash` | D | I | R | |

**W-INV-1** A `WorkerReceipt` is EVIDENCE that a worker *said* something; its
`claims` remain CLAIMs. It never raises `observed_satisfaction`.
**W-INV-2** `proposed_mutations` do not touch the workspace. Only an applied
`CommitIntent` does.

### 8.3 `CommitIntent`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `intent_id` | `Id` | Y | I | R | |
| `run_id` | `Ref<StageRun>` | Y | I | R | |
| `stage_id` | `Ref<Stage>` | Y | I | R | |
| `vcs_kind` | `Enum<DVCS,CVCS,NONE>` | Y | I | R | vendor-neutral |
| `base_revision_id` | `Str(1..128)` | Y | I | R | |
| `target_ref` | `Str(1..256)` | Y | I | R | branch/line identifier |
| `mutations` | `[MutationProposal]` | Y | I | R | all must be `in_scope` |
| `expected_tree_digest` | `Hash` | Y | I | R | post-application prediction |
| `message` | `Str(1..8192)` | Y | I | W | |
| `trailers` | `{Str: Str}` | Y | I | R | includes evidence back-references |
| `preconditions` | `{validations: Set<Hash>, reviews: Set<Ref<Review>>, decisions: Set<Ref<HumanDecision>>}` | Y | I | R | |
| `preconditions_met` | `bool` | D | M | R | |
| `status` | `Enum<PROPOSED,BLOCKED,AUTHORIZED,DENIED,APPLYING,APPLIED,FAILED,ROLLED_BACK>` | Y | M | R | §9.7 |
| `authorized_by` | `ActorRef?` | N | I | R | |
| `authorized_at` | `Ts?` | N | I | R | |
| `denial_reason` | `Str(1..512)?` | N | I | R | |
| `receipt_id` | `Ref<CommitReceipt>?` | N | I | R | |

### 8.4 `CommitReceipt`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `receipt_id` | `Id` | Y | I | R | |
| `intent_id` | `Ref<CommitIntent>` | Y | I | R | |
| `revision_id` | `Str(1..128)` | Y | I | R | resulting revision |
| `parent_revision_ids` | `[Str(1..128)]` | Y | I | R | |
| `actual_tree_digest` | `Hash` | Y | I | R | |
| `verification` | `Enum<MATCHED,DIVERGED>` | D | I | R | vs `expected_tree_digest` |
| `files_changed` | `[{path: Path, op: Enum<CREATE,MODIFY,DELETE,RENAME,CHMOD>, before_digest: Hash?, after_digest: Hash?}]` | Y | I | R | |
| `diff_ref` | `ArtifactRef` | Y | I | R | |
| `applied_at` | `Ts` | Y | I | R | |
| `applied_by` | `ActorRef` | Y | I | R | `RUNTIME` only |
| `post_snapshot_id` | `Ref<RealitySnapshot>` | Y | I | R | |
| `rollback_handle` | `Str(1..256)?` | N | I | R | |
| `receipt_hash` | `Hash` | D | I | R | |
| `prev_event_hash` | `Hash` | D | I | R | |

**CM-INV-1** `verification = DIVERGED` MUST raise `Escalation(INTEGRITY_VIOLATION)`
and suspend the run.

---

## 9. Governance entities

### 9.A `HumanDecision` — AUTHORITY

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `decision_id` | `Id` | Y | I | R | |
| `project_id` | `Ref<Project>` | Y | I | R | |
| `subject` | `{kind: Enum<PROJECT,STAGE,RUN,CONTRACT,FINDING,ESCALATION,COMMIT_INTENT,CAPABILITY>, id: Id}` | Y | I | R | |
| `decision_kind` | `Enum<APPROVE,REJECT,WAIVE,OVERRIDE,GRANT_CAPABILITY,REVOKE_CAPABILITY,SET_MODE,SUSPEND,RESUME,ABANDON,EXTEND_BUDGET,ACCEPT_RISK>` | Y | I | H | |
| `question` | `Str(1..4096)` | Y | I | R | posed by runtime, verbatim |
| `options_offered` | `[Str(1..512)]` | Y | I | R | |
| `chosen` | `Str(1..512)` | Y | I | H | MUST be in `options_offered` |
| `justification` | `Str(1..4096)` | Y | I | H | non-empty for `OVERRIDE`, `WAIVE`, `ACCEPT_RISK` |
| `grants` | `Set<CapabilityId>` | Y | I | H | possibly empty |
| `revokes` | `Set<CapabilityId>` | Y | I | H | possibly empty |
| `scope` | `Enum<PROJECT,STAGE,RUN,SINGLE_ACTION>` | Y | I | H | |
| `expires_at` | `Ts?` | N | I | H | absent ⇒ `scope` bounds it |
| `decided_by` | `ActorRef` | Y | I | R | `actor_kind` MUST be `HUMAN` |
| `auth_method` | `Enum<SESSION,SIGNATURE,MTLS>` | Y | I | R | `NONE`/`DELEGATED` invalid |
| `decided_at` | `Ts` | Y | I | R | |
| `nonce` | `Str(16..64)` | Y | I | R | replay protection, single use |
| `evidence_shown` | `[ArtifactRef]` | Y | I | R | what the human actually saw |
| `signature` | `Hash?` | N | I | R | required iff `auth_method = SIGNATURE` |
| `decision_hash` | `Hash` | D | I | R | |
| `prev_event_hash` | `Hash` | D | I | R | |

**HD-INV-1** A `HumanDecision` with `actor_kind ≠ HUMAN` is void and is itself an
integrity violation. Runtimes and workers cannot manufacture authority.
**HD-INV-2** `evidence_shown` is mandatory: an uninformed approval is recorded as
such and does not satisfy `required_evidence` in the transition matrix.
**HD-INV-3** A decision is consumed once (`nonce`); it cannot be replayed across runs.

### 9.B `Escalation`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `escalation_id` | `Id` | Y | I | R | |
| `project_id` | `Ref<Project>` | Y | I | R | |
| `stage_id` | `Ref<Stage>?` | N | I | R | |
| `run_id` | `Ref<StageRun>?` | N | I | R | |
| `trigger` | `EscalationTrigger` | Y | I | R | §9.B.1 |
| `severity` | `Enum<LOW,MEDIUM,HIGH,CRITICAL>` | Y | M | R | |
| `summary` | `Str(1..4096)` | Y | I | R | |
| `evidence_refs` | `[ArtifactRef]` | Y | I | R | |
| `raised_by` | `ActorRef` | Y | I | R | |
| `raised_at` | `Ts` | Y | I | R | |
| `suspension_applied` | `SuspensionState` | Y | I | R | which axis-3 value was set |
| `suspension_target` | `Enum<PROJECT,STAGE,RUN,NONE>` | Y | I | R | |
| `required_decision_kinds` | `Set<Enum<...>>` | Y | I | R | acceptable resolutions |
| `auto_resolvable` | `bool` | D | I | R | false if `severity ≥ HIGH` or mode `SUPERVISED` |
| `assigned_to` | `ActorRef?` | N | M | R | |
| `status` | `Enum<OPEN,ACKNOWLEDGED,RESOLVED,EXPIRED,WITHDRAWN>` | Y | M | R | §9.8 |
| `resolution_decision_id` | `Ref<HumanDecision>?` | N | I | R | |
| `resolved_at` | `Ts?` | N | I | R | |
| `escalation_hash` | `Hash` | D | I | R | |

#### 9.B.1 `EscalationTrigger`

| value | raised when |
|---|---|
| `CONTRACT_AMBIGUITY` | a mandatory criterion has no resolvable verifier |
| `CAPABILITY_DENIED` | an action required a capability not granted |
| `SCOPE_BREACH_ATTEMPT` | a mutation or read targeted a path outside contract scope |
| `BUDGET_EXHAUSTED` | any `budget_used` field reached its ceiling |
| `DEADLINE_EXCEEDED` | `now > deadline_at` with run non-terminal |
| `REPEATED_FAILURE` | `attempt_count > max_attempts` |
| `VALIDATION_UNAVAILABLE` | a required validator could not execute |
| `NONDETERMINISM` | a `DETERMINISTIC` spec produced differing receipts on replay |
| `BLOCKER_FINDING` | an unresolved finding has `blocks_satisfaction = true` |
| `DECLARED_OBSERVED_CONFLICT` | `CLAIMED_COMPLETE` vs `UNSATISFIED`/`CONTRADICTED` |
| `REALITY_DRIFT` | workspace changed outside runtime-mediated mutations |
| `ROADMAP_DIVERGED` | adapter reports `DIVERGED` or `UNREADABLE` |
| `POLICY_CONFLICT` | two applicable policy rules give opposite verdicts |
| `INTEGRITY_VIOLATION` | hash-chain break, contract mutation, forged receipt or decision |

### 9.C `AuditEvent`

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `event_id` | `Id` | Y | I | R | |
| `project_id` | `Ref<Project>` | Y | I | R | chain is per project |
| `seq` | `uint64` | Y | I | R | monotonic, gapless from 0 |
| `prev_event_hash` | `Hash` | Y | I | R | `seq = 0` ⇒ genesis constant |
| `event_hash` | `Hash` | D | I | R | over canonical body incl. `prev_event_hash` |
| `recorded_at` | `Ts` | Y | I | R | runtime clock only |
| `epistemic_class` | `Enum<CLAIM,EVIDENCE,DECISION,AUTHORITY>` | Y | I | R | see `evidence-model.md` §2 |
| `event_type` | `Str(1..64)` | Y | I | R | `<entity>.<verb>` |
| `actor` | `ActorRef` | Y | I | R | |
| `subject` | `{kind: Str(1..32), id: Id}` | Y | I | R | |
| `payload_ref` | `ArtifactRef` | Y | I | R | content-addressed body |
| `payload_digest` | `Hash` | Y | I | R | equals `payload_ref.digest` |
| `capability_used` | `CapabilityId?` | N | I | R | required for state-changing events |
| `authority_ref` | `Id?` | N | I | R | activation or decision that permitted it |
| `causal_parent` | `Ref<AuditEvent>?` | N | I | R | logical causality, not chain order |
| `clock_skew_ms` | `int64` | Y | I | R | runtime vs reference clock |
| `signature` | `Hash?` | N | I | R | |

**AE-INV-1** Append-only. Redaction replaces `payload_ref` content with a tombstone;
`payload_digest` and `event_hash` are never rewritten.
**AE-INV-2** Every state transition in `transition-matrix.md` emits ≥ 1 `AuditEvent`
before the new state is observable.

### 9.D `RealitySnapshot` — OBSERVATION-grade EVIDENCE

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `snapshot_id` | `Id` | Y | I | R | |
| `project_id` | `Ref<Project>` | Y | I | R | |
| `taken_at` | `Ts` | Y | I | R | |
| `taken_by` | `ActorRef` | Y | I | R | `RUNTIME` only |
| `trigger` | `Enum<SCHEDULED,PRE_RUN,POST_RUN,PRE_COMMIT,POST_COMMIT,DRIFT_CHECK,ON_DEMAND>` | Y | I | R | |
| `scope` | `[Glob]` | Y | I | R | what was actually walked |
| `completeness` | `Enum<COMPLETE,PARTIAL,TRUNCATED,FAILED>` | Y | I | R | |
| `tree_digest` | `Hash` | Y | I | R | Merkle root over scope |
| `file_index_ref` | `ArtifactRef` | Y | I | R | path → digest, size, mode |
| `file_count` | `uint64` | Y | I | R | |
| `byte_count` | `uint64` | Y | I | R | |
| `vcs_state` | `{revision_id: Str, target_ref: Str, dirty: bool, untracked: uint32, ahead: uint32, behind: uint32}?` | N | I | R | absent iff `vcs_kind = NONE` |
| `toolchain_digest` | `Hash` | Y | I | R | resolved tool versions |
| `env_digest` | `Hash` | Y | I | R | allowlisted env only |
| `probe_results` | `[{probe_id: Str, kind: Enum<EXISTS,BUILDS,RUNS,MATCHES>, outcome: Enum<TRUE,FALSE,ERROR>, digest: Hash}]` | Y | I | R | cheap ground-truth probes |
| `derived_observations` | `[{stage_id: Ref<Stage>, criterion_id: Str, observation: Enum<MET,UNMET,INDETERMINATE>, basis_refs: [Hash]}]` | D | I | R | feeds `observed_satisfaction` |
| `drift_vs` | `Ref<RealitySnapshot>?` | N | I | R | |
| `drift_summary` | `{added: uint32, removed: uint32, modified: uint32, unattributed: uint32}?` | D | I | R | `unattributed > 0` ⇒ `REALITY_DRIFT` |
| `snapshot_hash` | `Hash` | D | I | R | |

**RS-INV-1** `RealitySnapshot` is the only source of truth about the workspace.
No stage may be marked `SATISFIED` on the basis of a snapshot with
`completeness ≠ COMPLETE` over that stage's scope.

---

## 10. Enumerations used as state axes

These are defined here and consumed by `transition-matrix.md`. They are **three
orthogonal fields**, never collapsed into one.

### 10.1 `ProjectLifecycle` (axis 1)
`DRAFT`, `PLANNING`, `ACTIVE`, `SETTLING`, `COMPLETED`, `ARCHIVED`, `ABANDONED`

### 10.2 `StageLifecycle` (axis 2)
`PENDING`, `READY`, `CONTRACTED`, `RUNNING`, `AWAITING_VALIDATION`,
`AWAITING_REVIEW`, `AWAITING_DECISION`, `SATISFIED`, `REJECTED`, `ABANDONED`

### 10.3 `SuspensionState` (axis 3 — applies independently to Project, Stage, Run)
`NONE`, `SUSPENDED_BY_HUMAN`, `SUSPENDED_BY_POLICY`, `SUSPENDED_BY_ESCALATION`,
`SUSPENDED_BY_BUDGET`, `SUSPENDED_BY_INTEGRITY`, `SUSPENDED_BY_DRIFT`, `QUIESCING`

### 10.4 Subordinate state fields
`RunLifecycle`, `StageContract.status`, `Finding.status`, `CommitIntent.status`,
`Escalation.status`, `ValidationOperation.status`, `WorkerInvocation.status` —
each defined in its entity table and transitioned in `transition-matrix.md`.

---

## 11. Cardinality

| relation | cardinality |
|---|---|
| Project → Roadmap | 1 : 0..1 |
| Roadmap → Stage | 1 : 1..n |
| Stage → StageContract | 1 : 0..n (≤ 1 `ACTIVE`) |
| Stage → StageRun | 1 : 0..n (≤ 1 non-terminal) |
| StageContract → ContractActivationRecord | 1 : 0..n (≤ 1 un-revoked) |
| StageRun → ContractActivationRecord | 1 : 1 |
| StageRun → WorkerInvocation | 1 : 0..n |
| WorkerInvocation → WorkerReceipt | 1 : 0..1 |
| StageRun → ValidationOperation | 1 : 0..n |
| ValidationOperation → ValidationReceipt | 1 : 0..1 |
| StageRun → Review | 1 : 0..n |
| Review → Finding | 1 : 0..n |
| StageRun → CommitIntent | 1 : 0..n |
| CommitIntent → CommitReceipt | 1 : 0..1 |
| Project → AuditEvent | 1 : 1..n (total order) |
| Project → RealitySnapshot | 1 : 1..n |
| Escalation → HumanDecision | 1 : 0..1 (resolution) |

---

## 12. Global invariants

| id | invariant |
|---|---|
| `G-1` | No entity outside `{ValidationReceipt, WorkerReceipt, CommitReceipt, RealitySnapshot}` may be cited as `required_evidence`. |
| `G-2` | No entity outside `{HumanDecision, ContractActivationRecord}` may be cited as `required_capability` authority. |
| `G-3` | A worker-authored value is `CLAIM` class regardless of its confidence, formatting, or self-declared certainty. |
| `G-4` | Every state-changing operation names exactly one `CapabilityId`; absence ⇒ DENY. |
| `G-5` | Every receipt carries `prev_event_hash`; the chain is verifiable without the artifact store. |
| `G-6` | `declared_status` never appears in any precondition of any transition. |
| `G-7` | Terminal states (`SATISFIED`, `REJECTED`, `ABANDONED`, `COMPLETED`, `ARCHIVED`) are re-enterable only via a new entity revision, never by mutation. |
| `G-8` | Suspension never overwrites a lifecycle value; it is read alongside it. |
