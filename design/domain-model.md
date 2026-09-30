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
| `roadmap_id` | `Ref<Roadmap>?` | N | M | R | absent until the project's first `DRAFT → PLANNING` transaction, which binds `roadmap_id` atomically with that transition (transition-matrix §11 `RI-1`); no other act writes it |
| `capability_ceiling` | `Set<CapabilityId>` | Y | M | H | upper bound on all grants |
| `policy_digest` | `Hash` | Y | M | R | digest of active policy document |
| `budget` | `Budget` | Y | M | H | |
| `budget_used` | `BudgetUsage` | D | A | R | |
| `event_head` | `Hash` | D | M | R | head of hash-chained log |
| `event_seq` | `uint64` | D | M | R | monotonic, gapless |
| `controller_epoch` | `uint64` | D | M | R | incremented once per controller start, before any dispatch or apply; operations carry the epoch they were created under |
| `snapshot_current` | `Ref<RealitySnapshot>?` | D | M | R | |
| `created_at` / `updated_at` | `Ts` | Y | M | R | |
| `created_by` | `ActorRef` | Y | I | R | `actor_kind` MUST be `HUMAN` |

**P-INV-1** `governance_mode` transitions require a `HumanDecision` of kind `SET_MODE`.
**P-INV-2** No grant anywhere in the project may exceed `capability_ceiling`.
**P-INV-3** `lifecycle`, `suspension` are independent; neither encodes the other.
**P-INV-4** `controller_epoch` increments before the controller performs any
work. An operation whose `controller_epoch` is lower than the project's and whose
status is non-terminal outlived a controller and MUST be reconciled before the
run it belongs to does anything further (`RUN-INV-3`).

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
| `attempt_count` | `uint32` | D | M | R | number of distinct `StageRun`s of this stage that have entered `RUNNING`; a run is counted once, in the store transaction that commits its §3 `CONTRACTED → RUNNING` (transition-matrix §13 `WD-4`); re-entry into `RUNNING` by the same run does not count; every `attempt_count < max_attempts` precondition reads the value before its transition |
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
| `controller_epoch` | `uint64` | Y | I | R | `project.controller_epoch` at allocation |
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
**RUN-INV-3** A run initiates no new external effect — it may create no new
`WorkerInvocation`, and may advance no `CommitIntent` past `AUTHORIZED` under
`commit.apply` — while any of its `WorkerInvocation` or `CommitIntent` records has
`reconciliation_state ∈ {PENDING, UNRESOLVABLE}`. Every such record is reconciled
first, by `lookup` on its persisted `idempotency_key` or by matching the
repository against `operation_token`. Transitions taken under
`recovery.reconcile` are exempt from the bar: they initiate nothing and are the
only way a record leaves `PENDING` (transition-matrix §5, §5.1). This is the
guarantee that a controller restart cannot produce a duplicate worker or a
duplicate commit: the effect is adopted, or proven not to have happened, never
repeated.

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
| `contract_hash` | `Hash` | D | I | R | over all fields except itself **and except `status`**; see schema HASHING comment |

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
except `contract_hash` and except `status`. `status` is lifecycle, not content:
excluding it is what lets the legal transitions `DRAFT → ACTIVE` and
`ACTIVE → FULFILLED`/`REVOKED`/`EXPIRED`/`SUPERSEDED` preserve the hash pinned
into `StageRun.contract_hash`, while `XC-13` keeps `status` the only member that
may differ between persisted documents sharing a `contract_id`. Mutation of any
field inside the preimage after `ACTIVE` is an integrity violation.
**C-INV-3** `capability_request` is a request. A run's grants come only from
`ContractActivationRecord`; a project grant comes only from a live
`HumanDecision{kind: GRANT_CAPABILITY, scope: PROJECT}` (authority-matrix §5.3) and never
reaches a run.

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
| `capability_grant_basis` | `{CapabilityId: {grantor: ActorRef, grant_kind: Enum<HUMAN_DECISION,POLICY,ROLE_DEFAULT>, ref: Id?, at: Ts}}` | Y | I | R | one entry per granted capability, naming the admissible grantor that supplied it (authority-matrix §5.1) |
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
**A-INV-2** Activation is the **only** entity that confers a run's **execution authority**:
its `granted_capabilities`, and the `StageRun.effective_capabilities` frozen from them.
Authority to govern a run from outside it — a human decision authorizing `stage.reject` on
the run's own row — is not execution authority, confers no capability on the run, and adds
nothing to either set (authority-matrix §5.2, `AX-18`).
**A-INV-3** `capability_grant_basis` has exactly one entry per member of
`granted_capabilities`, and each entry names a grantor listed in that
capability's `grantable by` column in authority-matrix §2. A granted capability
with no basis entry, or one whose basis names a principal the register does not
list for it, is an integrity violation, not a grant. `CEILING` is not an
admissible `grant_kind` here: the ceiling bounds grants and issues none
(`AX-11`).

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

#### 7.3.1 `ReviewAttestation` — EVIDENCE

A `Review` is a judgement, and a judgement by an `AUTOMATED` or `PEER_WORKER`
reviewer is CLAIM class. A `ReviewAttestation` is the kernel's measurement *of*
that judgement: it does not assert the defect-freedom the review asserts, it
attests that a review meeting a named `ReviewSpec`'s quorum and independence
exists, was computed over a stated snapshot, and carries a stated verdict. This
is the same shape as `WorkerReceipt`, which is EVIDENCE that a worker said
something without making what it said true.

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `attestation_id` | `Id` | Y | I | R | |
| `run_id` | `Ref<StageRun>` | Y | I | R | |
| `stage_id` | `Ref<Stage>` | Y | I | R | |
| `review_spec_id` | `Str(1..64)` | Y | I | R | the spec this attestation discharges |
| `review_ids` | `Set<Ref<Review>>` | Y | I | R | the reviews counted toward quorum; size ≥ `spec.quorum` |
| `verdict` | `Enum<PASS,PASS_WITH_FINDINGS,FAIL,INCONCLUSIVE,ABSTAIN>` | D | I | R | aggregated over `review_ids` per spec; the value `RVW(v)` matches |
| `criteria_addressed` | `Set<Str(1..64)>` | D | I | R | union over `review_ids`, ⊆ contract criteria |
| `quorum_met` | `bool` | D | I | R | |
| `independence_satisfied` | `bool` | D | I | R | computed from provenance (`RC-2`, `WP-12`), never asserted |
| `blocking_findings` | `Set<Ref<Finding>>` | D | I | R | findings with `blocks_satisfaction = true` |
| `input_snapshot_id` | `Ref<RealitySnapshot>` | Y | I | R | every counted review measured this snapshot |
| `contract_hash` | `Hash` | Y | I | R | the pinned contract the spec came from |
| `attested_by` | `ActorRef` | Y | I | R | `RUNTIME` only |
| `attested_at` | `Ts` | Y | I | R | |
| `attestation_hash` | `Hash` | D | I | R | |
| `prev_event_hash` | `Hash` | D | I | R | |

**RA-INV-1** Minting requires `review.attest`, a `KERNEL` capability. A
worker-authored or human-authored attestation is an integrity violation, not a
review result.
**RA-INV-2** An attestation is minted only when `quorum_met = true` and
`independence_satisfied = true` for its spec. A spec that cannot be satisfied
produces no attestation; the stage takes the `AWAITING_REVIEW → AWAITING_DECISION`
row instead.
**RA-INV-3** The attestation carries a verdict; it never carries the reviewer's
reasoning as fact. The `Review` records it cites stay CLAIM class, and a finding
raised inside one is promoted only by its own `evidence_refs`.
**RA-INV-4** Like every receipt, an attestation is bound to
`input_snapshot_id` and stops being current evidence when that snapshot is
superseded within the stage's scope.

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
| `idempotency_key` | `Hash` | Y | I | R | `H(context_digest ‖ role ‖ attempt)`, where `attempt` is the tuple `⟨run_id, invocation_ordinal_within_run⟩` and the ordinal is 1 + the number of `WorkerInvocation` records of the same `run_id` admitted before this one, of any status, counted inside its §7.2 `∅ → PENDING` transaction. `‖` is the canonical length-prefixed `KEY_PREIMAGE` encoding and `H` is `"sha256:" + lowerhex(sha256(KEY_PREIMAGE))` (transition-matrix §13 `WD-2`, which also defines collision refusal). No field is added. Stable for the life of the invocation, including across controller restarts |
| `request_ref` | `ArtifactRef` | Y | I | R | the exact `InvocationRequest`, persisted **before** the first provider call; it makes the `idempotency_key` durable and the request auditable. Recovery reads it and never re-sends it — resolution is by `lookup(idempotency_key)` alone (`WP-16`) |
| `controller_epoch` | `uint64` | Y | I | R | `project.controller_epoch` at creation |
| `reconciliation_state` | `Enum<NOT_REQUIRED,PENDING,ADOPTED,ORPHANED,UNRESOLVABLE>` | D | M | R | derived solely by the reconciliation-state derivation table, transition-matrix §5.1 — the one derivation shared with `CommitIntent`. `ADOPTED` there means the outcome was established, not that it succeeded |
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
| `termination_reason` | `Enum<COMPLETED,DEADLINE,BUDGET,POLICY_STOP,PROVIDER_ERROR,HUMAN_STOP,INTEGRITY,REFUSAL>` | Y | I | R | always the recorded outcome's own `termination_reason`, never rewritten or substituted. The outcome's `status` and `termination_reason` form one evidence pair, and a receipt is minted directly only for a pair a legal row admits (transition-matrix §13 `WD-6`); reconciliation (7.2-9) records the same true pair. `REFUSAL` is recorded exactly when the outcome carried `REFUSAL`; a direct refusal requires the pair `REFUSED + REFUSAL` (worker_provider §2.1, `WP-13`, `WP-18`). An enum value, not a lifecycle state |
| `attested_by` | `ActorRef` | Y | I | R | `RUNTIME` only |
| `attribution` | `Enum<DIRECT,RECONCILED>` | Y | I | R | `DIRECT` iff minted under `worker.invoke` from an invocation this controller ran; `RECONCILED` iff minted under `recovery.reconcile` from what `lookup` reported, including a reported `FAILED`, `TIMED_OUT`, `CANCELLED` or `REFUSED` outcome, and including the `ABSENT` case where the receipt records that nothing ran |
| `receipt_hash` | `Hash` | D | I | R | |
| `prev_event_hash` | `Hash` | D | I | R | |

**W-INV-1** A `WorkerReceipt` is EVIDENCE that a worker *said* something; its
`claims` remain CLAIMs. It never raises `observed_satisfaction`.
**W-INV-2** `proposed_mutations` do not touch the workspace. Only an applied
`CommitIntent` does.
**W-INV-3** A receipt with `attribution = RECONCILED` is the same EVIDENCE class
as a direct one and is never re-executed for. `lookup` on the original
`idempotency_key` reports the provider's prior outcome without executing
(`WP-16`); a second execution would be a duplicate worker and is illegal, as is
resubmitting `request_ref` to obtain the outcome (transition-matrix §9.3).
**W-INV-4** A `RECONCILED` receipt carries the outcome that was found, not a
better one. `ADOPTED` records that the outcome is now established; a prior
`FAILED`, `TIMED_OUT`, `CANCELLED` or `REFUSED` outcome is preserved as such and
is never recorded as `COMPLETED` (transition-matrix §5.1, §7.2).

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
| `trailers` | `{Str: Str}` | Y | I | R | includes evidence back-references **and `operation_token`**, so the landed revision carries its own identity |
| `operation_token` | `Str(32..128)` | Y | I | R | durable, globally unique identity of this application attempt, minted at `PROPOSED` and written into `trailers`; the key a restart scans the repository by |
| `controller_epoch` | `uint64` | Y | I | R | `project.controller_epoch` at creation |
| `reconciliation_state` | `Enum<NOT_REQUIRED,PENDING,ADOPTED,ORPHANED,UNRESOLVABLE>` | D | M | R | derived solely by the reconciliation-state derivation table, transition-matrix §5.1 — the one derivation shared with `WorkerInvocation`. `PENDING` covers **every** non-terminal old-epoch status, `PROPOSED`, `BLOCKED` and `AUTHORIZED` included, not only `APPLYING` |
| `preconditions` | `{validations: Set<Hash>, reviews: Set<Ref<ReviewAttestation>>, decisions: Set<Ref<HumanDecision>>}` | Y | I | R | `reviews` holds kernel-minted attestations, never `Review` records: a precondition is discharged by the kernel's measurement of a review, not by the reviewer's own verdict (`G-1`) |
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
| `attribution` | `Enum<DIRECT,RECONCILED>` | Y | I | R | `RECONCILED` iff minted under `recovery.reconcile` for a revision found by `operation_token` after a restart |
| `operation_token` | `Str(32..128)` | Y | I | R | copied from the intent; equals the token carried by `revision_id`'s trailers |
| `post_snapshot_id` | `Ref<RealitySnapshot>` | Y | I | R | |
| `rollback_handle` | `Str(1..256)?` | N | I | R | |
| `receipt_hash` | `Hash` | D | I | R | |
| `prev_event_hash` | `Hash` | D | I | R | |

**CM-INV-1** `verification = DIVERGED` MUST raise `Escalation(INTEGRITY_VIOLATION)`
and suspend the run.
**CM-INV-2** The `operation_token` is durable before the repository is touched,
and the repository operation carries it. A revision that landed while the
controller was down is therefore always findable, so an `APPLYING` intent is
resolved by adoption (mint the `CommitReceipt` with `attribution = RECONCILED`)
or by proof that nothing landed — never by a blind retry, which is not
idempotent.
**CM-INV-3** A token matching more than one revision, or matching none while the
workspace no longer matches `base_revision_id`, is `UNRESOLVABLE`: raise
`Escalation(RECOVERY_AMBIGUITY)` and suspend. Tree equality alone never
establishes which revision fulfilled which intent.

---

## 9. Governance entities

### 9.A `HumanDecision` — AUTHORITY

| field | type | req | mut | src | notes |
|---|---|---|---|---|---|
| `decision_id` | `Id` | Y | I | R | |
| `project_id` | `Ref<Project>` | Y | I | R | |
| `subject` | `{kind: Enum<PROJECT,STAGE,RUN,CONTRACT,FINDING,ESCALATION,COMMIT_INTENT,CAPABILITY>, id: Id}` | Y | I | R | |
| `decision_kind` | `Enum<APPROVE,REJECT,WAIVE,OVERRIDE,GRANT_CAPABILITY,REVOKE_CAPABILITY,SET_MODE,SUSPEND,RESUME,ABANDON,EXTEND_BUDGET,ACCEPT_RISK,SET_CEILING,GRANT_BUDGET>` | Y | I | H | |
| `question` | `Str(1..4096)` | Y | I | R | posed by runtime, verbatim |
| `options_offered` | `[Str(1..512)]` | Y | I | R | |
| `chosen` | `Str(1..512)` | Y | I | H | MUST be in `options_offered` |
| `justification` | `Str(1..4096)` | Y | I | H | non-empty for `OVERRIDE`, `WAIVE`, `ACCEPT_RISK` |
| `grants` | `Set<CapabilityId>` | Y | I | H | possibly empty |
| `revokes` | `Set<CapabilityId>` | Y | I | H | possibly empty |
| `scope` | `Enum<PROJECT,STAGE,RUN,SINGLE_ACTION>` | Y | I | H | |
| `expires_at` | `Ts?` | N | I | H | absent ⇒ `scope` bounds it |
| `snapshot_bound` | `bool` | D | I | R | true iff the decision speaks about the state of the workspace: `subject.kind ∈ {STAGE, RUN, COMMIT_INTENT, FINDING}`, or `decision_kind ∈ {APPROVE, WAIVE, ACCEPT_RISK, OVERRIDE, REJECT}`. `SET_MODE`, `SUSPEND`, `RESUME`, `ABANDON`, `EXTEND_BUDGET`, `GRANT_CAPABILITY` and `REVOKE_CAPABILITY` over a `PROJECT` or `CAPABILITY` subject are not snapshot-bound |
| `subject_snapshot_id` | `Ref<RealitySnapshot>?` | Y | I | R | required iff `snapshot_bound`; the `COMPLETE` snapshot the `evidence_shown` artifacts were measured against — the repository reality the human actually approved |
| `decision_state` | `Enum<VALID,CONSUMED,STALE,EXPIRED,VOID>` | D | M | R | transition-matrix §7.5; only `VALID` is authority |
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
**HD-INV-4** A snapshot-bound decision is authority only while its
`subject_snapshot_id` is still the newest `COMPLETE` snapshot covering the
subject's scope. When a newer snapshot whose `drift_summary` touches that scope
supersedes it, `decision_state` becomes `STALE` and the decision satisfies no
`CONFIRM` or `DECIDE(K)`, whatever its `expires_at` says and whether or not it
was ever used. Fresh validations and reviews over the new reality do not revive
it: the human approved artifacts that no longer describe the workspace, so the
subject must be re-decided. `HD-INV-3` prevents reuse after consumption;
`HD-INV-4` prevents stale first use.

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
| `RECOVERY_AMBIGUITY` | after a controller restart an operation cannot be reconciled: the provider cannot say whether an invocation ran, or a repository scan matches an `operation_token` to zero revisions with a changed base, or to more than one |

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
| `authority_ref` | `Id?` | N | I | R | activation or decision that permitted it; on an event carrying `capability_used`, absent exactly when that capability is `KERNEL`-class or is `decision.record` (evidence-model §3.3), and otherwise required. An event carrying no `capability_used` is unconstrained by this note |
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
`Escalation.status`, `ValidationOperation.status`, `WorkerInvocation.status`,
`HumanDecision.decision_state`, and the `reconciliation_state` carried by
`WorkerInvocation` and `CommitIntent` — each defined in its entity table and
transitioned in `transition-matrix.md`. None of them is a lifecycle axis: they
qualify one entity, never the project or the stage.

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
| ReviewSpec → ReviewAttestation | 1 : 0..n (≤ 1 current per `input_snapshot_id`) |
| ReviewAttestation → Review | 1 : 1..n (quorum members) |
| StageRun → CommitIntent | 1 : 0..n |
| CommitIntent → CommitReceipt | 1 : 0..1 |
| HumanDecision → RealitySnapshot | 1 : 0..1 (`subject_snapshot_id`, present iff `snapshot_bound`) |
| Project → AuditEvent | 1 : 1..n (total order) |
| Project → RealitySnapshot | 1 : 1..n |
| Escalation → HumanDecision | 1 : 0..1 (resolution) |

---

## 12. Global invariants

| id | invariant |
|---|---|
| `G-1` | A `required_evidence` cell is a conjunction of **citations**, each of which may itself be a disjunction of alternatives; a cell is not typed as a whole, and each citation carries its own kind. An **evidence citation** names a record that measures reality, and no entity outside `{ValidationReceipt, WorkerReceipt, CommitReceipt, ReviewAttestation, RealitySnapshot}` may be cited as one; a `Review` is never cited directly, the kernel-minted `ReviewAttestation` being what the `RVW(v)` token in `transition-matrix.md` resolves to, so a judgmental criterion is discharged by the kernel's measurement of the review, not by the reviewer's own verdict. A **prerequisite citation** names a record of one of exactly four kinds: an activation, a `HumanDecision`, an `Escalation`, or an `AuditEvent` the row names — the last including a persisted artifact or durable identity, cited as the event that persisted it. These four and the evidence citation are the **only** admissible kinds; a cell naming a record of any other kind is outside this rule and is not closed by it. A prerequisite citation is never a measurement and never makes a criterion `MET`. It has exactly the effect another rule of this design gives it: a `HumanDecision{kind ∈ {WAIVE, ACCEPT_RISK}}` discharges the shortfall it names by producing the `WAIVED` outcome `evidence-model.md` §4 reads, and an `Escalation` gates only as §2's `CLAIM` row permits. Where a cell element names no record at all — a clock reading, a recomputation — it is a precondition, not a citation. |
| `G-2` | No entity outside `{HumanDecision, ContractActivationRecord}` may be cited as `required_capability` authority. |
| `G-3` | A worker-authored value is `CLAIM` class regardless of its confidence, formatting, or self-declared certainty. |
| `G-4` | Every state-changing operation names exactly one `CapabilityId`; absence ⇒ DENY. |
| `G-5` | Every receipt carries `prev_event_hash`; the chain is verifiable without the artifact store. |
| `G-6` | `declared_status` never appears in any precondition of any transition. |
| `G-7` | Terminal states (`SATISFIED`, `REJECTED`, `ABANDONED`, `COMPLETED`, `ARCHIVED`) are re-enterable only via a new entity revision, never by mutation. |
| `G-8` | Suspension never overwrites a lifecycle value; it is read alongside it. |
| `G-9` | Every side effect outside the kernel's own store — a provider invocation, a repository mutation — has a durable identity persisted **before** the effect (`idempotency_key` with `request_ref`, or `operation_token`), and a non-terminal one that outlives its controller is reconciled before any further work on its run (`RUN-INV-3`, `CM-INV-2`). |
| `G-10` | An authority record cites the grantor that produced it. A grant with no admissible grantor in the capability register is not a grant (`A-INV-3`, `AX-11`); a decision whose `decision_state ≠ VALID` is not authority (`HD-INV-4`). |

---

## 13. Repository bootstrap authority (GR-33 N8)

`RepositoryBootstrapAuthority` (RBA) and `RepositoryBootstrapSuccession` (RBS) are §8
action entities, placed here at the end of the document so that no existing line moves.
Their transitions are transition-matrix §16; their evidence is evidence-model §8; their
one capability, `repository.bootstrap.record`, is registered in authority-matrix §7.

In this section B is a project's RBA, R₀ is the run named by its row 16-1 act, S is the
snapshot named by `B.input_snapshot_id`, `ACT(R₀)` is the `ContractActivationRecord` of
`R₀.activation_id`, Rs is a successor run, and `GL(p)` is the repository adapter's fixed
governed-line name for project p.

### 13.1 `RepositoryBootstrapAuthority`

| field | type | req | mut | src | rule |
|---|---|---|---|---|---|
| `bootstrap_id` | `Id` | Y | I | R | identity; unique |
| `project_id` | `Ref<Project>` | Y | I | R | **binding**; unique, so at most one record per project for the project's life |
| `stage_run_id` | `Ref<StageRun>` | Y | I | R | **binding**. The original bound run R₀, named in the 16-1 act; `R₀.project_id = project_id`. It is never changed; succession does not rewrite it. |
| `input_snapshot_id` | `Ref<RealitySnapshot>` | Y | I | R | **binding**. It equals `R₀.input_snapshot_id` **and** `ContractActivationRecord.input_snapshot_id` of `R₀.activation_id`. The snapshot has `project_id = project_id`, `completeness = COMPLETE` and a present `vcs_state`. |
| `expected_ref_target` | `Str(1..128)` | Y | I | R | **binding**. It is exactly the `vcs_state.revision_id` string of `input_snapshot_id`, copied with no normalization, abbreviation expansion, ref resolution or object lookup. |
| `project_ref` | `Str(1..256)` | Y | I | R | **binding**. It is `GL(project_id)`: the repository adapter's fixed governed-line name. That is a pure, injective function of `project_id` alone, not configurable per project, and never a path prefix of another project's name. For the one adapter (Git) it is `refs/heads/gruntime/<project_id>/governed` (D-PC-08). |
| `controller_epoch` | `uint64` | Y | I | R | provenance only: `project.controller_epoch` at establishment. The record is not an operation, and transition-matrix §5.1 never reads this field. |
| `recorded_by` | `ActorRef` | Y | I | R | `RUNTIME` only |
| `recorded_at` | `Ts` | Y | I | R | |
| `consumed` | `bool` | D | M | R | true iff the project's chain holds the row 16-3 event for `bootstrap_id`; derived, never asserted |
| `record_hash` | `Hash` | D | I | R | canonical record, excluding itself, `prev_event_hash` and `consumed` |
| `prev_event_hash` | `Hash` | D | I | R | |

The **binding tuple** is exactly D-PC-08's five fields: `project_id`, `stage_run_id`,
`input_snapshot_id`, `expected_ref_target` and `project_ref`. Every other column is
identity, provenance or chain, and is never a source of authority or of a CAS operand. No
intent participates in establishment.

### 13.2 `RepositoryBootstrapSuccession`

The record hands off one unconsumed RBA's run binding from the currently bound run to
exactly one successor run. It is not a general delegation mechanism. It applies to no other
entity, capability or record, and it cannot exist for a consumed RBA.

| field | type | req | mut | src | rule |
|---|---|---|---|---|---|
| `succession_id` | `Id` | Y | I | R | identity |
| `bootstrap_id` | `Ref<RepositoryBootstrapAuthority>` | Y | I | R | the one RBA handed off; unconsumed at the act |
| `ordinal` | `uint32` | Y | I | R | 1-based position in this RBA's succession chain; unique per `bootstrap_id` |
| `predecessor_succession_id` | `Ref<RepositoryBootstrapSuccession>?` | N | I | R | absent iff `ordinal = 1`; otherwise the record with `ordinal − 1` |
| `predecessor_run_id` | `Ref<StageRun>` | Y | I | R | the bound run at the act: `RBA.stage_run_id` if `ordinal = 1`, else the predecessor record's `successor_run_id`; unique per `bootstrap_id` |
| `successor_run_id` | `Ref<StageRun>` | Y | I | R | a run of `project_id`, distinct from every run already in the chain (R₀ included) |
| `project_id` | `Ref<Project>` | Y | I | R | **preserved**: copied from the RBA; equality-checked |
| `input_snapshot_id` | `Ref<RealitySnapshot>` | Y | I | R | **preserved**: copied from the RBA; equality-checked. The successor's own `input_snapshot_id` is never read for this field. |
| `expected_ref_target` | `Str(1..128)` | Y | I | R | **preserved**: copied byte for byte from the RBA; equality-checked |
| `project_ref` | `Str(1..256)` | Y | I | R | **preserved**: copied from the RBA; equality-checked |
| `confirmation_id` | `Ref<HumanDecision>?` | N | I | R | Present iff `governance_mode = SUPERVISED` at the act (D-N8-03 = A). It names the one `APPROVE` that satisfies transition-matrix `RB-18` and is consumed by this act alone (`RB-21`). It is absent under AUTONOMOUS. |
| `controller_epoch` | `uint64` | Y | I | R | provenance only |
| `recorded_by` | `ActorRef` | Y | I | R | `RUNTIME` only |
| `recorded_at` | `Ts` | Y | I | R | |
| `record_hash` | `Hash` | D | I | R | |
| `prev_event_hash` | `Hash` | D | I | R | |

The RBA is never mutated by a succession. Its `stage_run_id` remains R₀ for ever. The chain
is append-only and linear, with no branching, cycle, skip, reorder or deletion.

**Bound run.** `bound(B)` is `B.stage_run_id` if B has no succession. Otherwise it is the
`successor_run_id` of B's highest-`ordinal` succession. It is a pure function of governed
store records and is never taken from any repository state.

### 13.3 Binding rules

| binding | exact rule | checked (transition-matrix §16) |
|---|---|---|
| `project_id` | `= R₀.project_id = S.project_id`, and for every RBS equal to `B.project_id` | 16-1; 16-4; read at 16-2, 16-3 and bootstrapping 7.4-6 |
| `stage_run_id` | R₀, named by the 16-1 act; a `StageRun` of `project_id`, non-terminal, with `AC-1` committed | 16-1 (immutable thereafter) |
| `input_snapshot_id` | `= R₀.input_snapshot_id = ACT(R₀).input_snapshot_id`; S is `COMPLETE` with `vcs_state ≠ ∅`; each RBS copy is equal | 16-1; 16-4 |
| `expected_ref_target` (E) | `= S.vcs_state.revision_id`, byte for byte, in the adapter's canonical full object-name form, or 16-1 refuses (no expansion); each RBS copy is equal | 16-1; 16-4 |
| `project_ref` | `= GL(project_id)`; each RBS copy is equal | 16-1; 16-4 |
| bootstrapping intent I (7.4-6 while `consumed = false`) | `I.run_id = bound(B)`; `I.project = project_id`; `I.target_ref = project_ref`; `I.base_revision_id = E`; `I.vcs_kind = DVCS` | bootstrapping 7.4-6; 16-2 |

### 13.4 Cardinality

| relation | cardinality |
|---|---|
| Project → RepositoryBootstrapAuthority | 1 : 0..1 |
| RepositoryBootstrapAuthority → RepositoryBootstrapSuccession | 1 : 0..n (linear chain) |
| StageRun → RepositoryBootstrapSuccession (as predecessor) | 1 : 0..1 per RBA |

### 13.5 Invariants

| id | invariant |
|---|---|
| `RBA-INV-1` | `project_ref` is created only by transition-matrix row 16-2, by an intent of `bound(B)`, against a durable, unconsumed RBA established earlier by row 16-1, whose E is the `vcs_state.revision_id` of the snapshot named by `input_snapshot_id`. It is adopted only as GR-33 N9 defines. Bootstrap never resets or rewinds it, and later advances happen only under `commit.apply`. |
| `RBA-INV-2` | At most one RBA per project; immutable; never deleted, superseded or rebound; `stage_run_id` fixed for ever (transition-matrix `RB-5`). |
| `RBA-INV-3` | Provenance closure and monotone refusal (transition-matrix `RB-4`, `RB-6`). RBA fields come only from R₀, `R₀.input_snapshot_id`'s snapshot record, `ACT(R₀)` and `GL`. RBS fields come only from B, its existing chain, Rs's `StageRun` record (identity, project and status only) and, under SUPERVISED, the confirmation's value artifact. `bound(B)` is computed from those records alone. Any ref value, reflog, packed-refs, `HEAD` or symbolic ref, marker or lock file, the live workspace, index or working tree, Git config, a private or exported view, another StageRun's snapshot, activation or record beyond those named, an implicit choice of successor, repository contents or objects (including resolving an abbreviated E), directory existence, and driver or CLI arguments as field values are inadmissible sources (transition-matrix §16.4); observing one is permitted only as a refusal input. |
| `RBA-INV-4` | Neither record is authority: they confer no capability, are never `required_capability` authority (`G-2`), and enter no grant set. They create no retry, attempt, budget or human authority. They are not snapshot-bound and not transition-matrix §5.1 operations. |
| `RBA-INV-5` | Under `G-9`, the RBA (with its succession chain) is the durable identity of the project-ref creation effect, persisted in an earlier transaction than the effect. It sits alongside `idempotency_key`/`request_ref` and `operation_token`, and `G-9` is otherwise unchanged. |
| `RBA-INV-6` | Consumed exactly once, by row 16-3. After that, an absent ref is an integrity violation and is never re-created, and no succession may follow. |
| `RBA-INV-7` | No `APPLIED` `CommitReceipt` of an intent targeting `project_ref` precedes consumption. |
| `RBA-INV-8` | Both records exist only for `vcs_kind = DVCS`. |
| `RBS-INV-1` | Succession is explicit and narrow: exactly one RBS per handoff, recorded by row 16-4, which preserves the four fields `project_id`, `input_snapshot_id`, `expected_ref_target` and `project_ref` unchanged. It is linear and append-only, and allowed only from a terminal bound run with no `APPLYING` intent, before consumption. No run acts under another run's binding without it (transition-matrix `RB-8`, `RB-17`..`RB-19`, `RB-21`). |
