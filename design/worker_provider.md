# DESIGN-01 — `WorkerProvider` Interface Specification

Interface only. No implementation, no vendor, no model identifiers. Core treats
`execution_binding`, provider capability names, and provider diagnostics as
`Opaque` and never branches on their content.

---

## 1. Position

| property | value |
|---|---|
| direction | core calls provider; provider never calls core, and never calls another provider |
| trust | provider output is `CLAIM` class in full; only the kernel's measurement of the invocation is `EVIDENCE` |
| authority | the provider receives a capability set; it cannot request, widen, or discover capabilities |
| role | assigned by `StageContract.worker_role`; the provider cannot select or change it |
| workspace | the provider never touches the live workspace; it reads a materialized scope view and returns proposals |
| identity | `provider_id` plus `provider_version`; recorded on every `WorkerInvocation` |

---

## 2. Types

| type | definition |
|---|---|
| `ProviderDescriptor` | `{provider_id: Str(1..64), provider_version: SemVer, supported_roles: Set<WorkerRole>, bindings: [BindingDescriptor], max_context_bytes: uint64, supports_cancel: bool, supports_streaming: bool, cost_model: Enum<UNIT_METERED,WALL_CLOCK,FLAT,UNKNOWN>}` |
| `BindingDescriptor` | `{binding_id: Opaque, label: Str(1..128), max_output_bytes: uint64, relative_cost: Unit, deterministic: bool}` |
| `InvocationRequest` | `{invocation_id: Id, worker_role: WorkerRole, binding_id: Opaque, prompt_bundle_ref: ArtifactRef, context_refs: [ArtifactRef], scope_view: ScopeView, granted_capabilities: Set<CapabilityId>, tool_surface: [ToolDescriptor], budget: Budget, deadline_at: Ts, idempotency_key: Hash}` |
| `ScopeView` | `{root: Path, include: [Glob], exclude: [Glob], file_index_ref: ArtifactRef, snapshot_id: Ref<RealitySnapshot>, writable: bool}` |
| `ToolDescriptor` | `{tool_id: Str(1..64), required_capability: CapabilityId, input_schema_ref: ArtifactRef, output_schema_ref: ArtifactRef, side_effecting: bool}` |
| `ToolCall` | `{call_id: Id, tool_id: Str, arguments_ref: ArtifactRef, requested_at: Ts}` |
| `ToolResult` | `{call_id: Id, outcome: Enum<OK,DENIED,ERROR,TIMEOUT>, result_ref: ArtifactRef?, denial_capability: CapabilityId?, latency_ms: Ms}` |
| `InvocationOutcome` | `{invocation_id: Id, status: Enum<COMPLETED,FAILED,TIMED_OUT,CANCELLED,REFUSED>, output_ref: ArtifactRef, claims: [Claim], proposed_mutations: [MutationProposal], requested_validations: [ValidationRequestDraft], usage: Usage, termination_reason: Enum<COMPLETED,DEADLINE,BUDGET,POLICY_STOP,PROVIDER_ERROR,HUMAN_STOP,REFUSAL>, diagnostics: [Opaque]}` |
| `ValidationRequestDraft` | `{validation_spec_id: Str(1..64), criterion_refs: Set<Str(1..64)>}` |
| `Usage` | `{input_units: Unit, output_units: Unit, tool_calls: uint32, cost_units: Unit, wall_clock_ms: Ms}` |
| `ProviderError` | `{code: ErrorCode, message: Opaque, retryable: bool, retry_after_ms: Ms?}` |

### 2.1 `ErrorCode`

| code | meaning | core response |
|---|---|---|
| `UNSUPPORTED_ROLE` | provider cannot serve the contract's role | invocation `REJECTED_BY_POLICY`; try next provider in the registry |
| `UNKNOWN_BINDING` | `binding_id` not offered by `describe` | `REJECTED_BY_POLICY` |
| `CONTEXT_TOO_LARGE` | bundle exceeds `max_context_bytes` | kernel re-bundles or escalates `CONTRACT_AMBIGUITY` |
| `UNAVAILABLE` | transient provider failure | retry with backoff, within budget |
| `RATE_LIMITED` | provider throttling | retry after `retry_after_ms` |
| `REFUSED` | provider declined the task | `WorkerReceipt` with `termination_reason = REFUSAL`; not retried against the same binding |
| `PROVIDER_ERROR` | non-transient failure | run → `CLOSED_ABORTED` |
| `CANCELLED` | cancellation acknowledged | `WorkerInvocation` → `CANCELLED` |

---

## 3. Operations

| operation | signature | required_capability (kernel-side) | idempotent | may block | errors |
|---|---|---|---|---|---|
| `describe` | `() -> ProviderDescriptor` | none | yes | no | `UNAVAILABLE` |
| `preflight` | `(InvocationRequest) -> {accepted: bool, estimated: Usage, diagnostics: [Opaque]}` | `worker.invoke` | yes | no | `UNSUPPORTED_ROLE`, `UNKNOWN_BINDING`, `CONTEXT_TOO_LARGE` |
| `invoke` | `(InvocationRequest, ToolBridge) -> InvocationOutcome` | `worker.invoke` | yes, keyed on `idempotency_key` | yes | all of §2.1 |
| `cancel` | `(invocation_id: Id, reason: Enum<SUSPENSION,BUDGET,DEADLINE,HUMAN_STOP>) -> {acknowledged: bool}` | `run.abort` | yes | no | `UNAVAILABLE` |
| `health` | `() -> {status: Enum<UP,DEGRADED,DOWN>, checked_at: Ts}` | none | yes | no | none |

### 3.1 `ToolBridge` — the only channel to the outside

| operation | signature | direction | note |
|---|---|---|---|
| `call` | `(ToolCall) -> ToolResult` | provider → kernel | kernel mediates every call; unknown `tool_id` returns `DENIED` |
| `progress` | `(Opaque) -> ()` | provider → kernel | advisory; recorded, never acted on |

There is no other egress. A provider that reaches the network, filesystem, or a
process other than through `ToolBridge` is out of contract and its receipts are
recorded with `capability_violations_attempted`.

---

## 4. Contracts

| id | contract |
|---|---|
| `WP-1` | Everything in `InvocationOutcome` other than `usage` is `CLAIM` class. No field can raise `observed_satisfaction`. |
| `WP-2` | `proposed_mutations` are proposals against `scope_view.snapshot_id`. The provider never writes the live workspace; application is `commit.apply`, a `KERNEL` capability. |
| `WP-3` | `requested_validations` may only name a `validation_spec_id` already present in the pinned contract. The provider cannot author a validator or alter a command. |
| `WP-4` | Every side-effecting action goes through `ToolBridge.call` and is denied unless `tool.required_capability ∈ granted_capabilities`. Denial is returned, not raised, and is recorded. |
| `WP-5` | `usage` reported by the provider is advisory; the authoritative `Usage` in the `WorkerReceipt` is the kernel's own measurement. Divergence beyond tolerance raises `Escalation(POLICY_CONFLICT)`. |
| `WP-6` | `invoke` is idempotent on `idempotency_key`: a repeat returns the prior outcome rather than re-executing, so retries cannot double-spend budget. |
| `WP-7` | The provider receives no secrets. Secret-bearing values are injected by the kernel into tool execution environments and never appear in `prompt_bundle_ref` or `context_refs`. |
| `WP-8` | The provider is not told the governance mode, the capability ceiling, the budget of other runs, or the contents of the audit log. It receives exactly `InvocationRequest`. |
| `WP-9` | A provider may not invoke another provider or spawn a sub-worker; `worker.delegate` is `NEVER` grantable. Fan-out is a kernel decision. |
| `WP-10` | Deadline and budget are enforced by the kernel. `deadline_at` passing terminates the invocation regardless of provider state; a provider that ignores it is recorded as `TIMED_OUT`. |
| `WP-11` | Output size is bounded by `BindingDescriptor.max_output_bytes`. Overflow is truncated into an artifact with `truncated = true`, and the invocation ends `FAILED`. |
| `WP-12` | Provenance for independence (`RC-2`) is the tuple `(provider_id, binding_id, context_digest, session continuity)`. The provider must report session continuity truthfully in `diagnostics`; the kernel additionally computes it from `context_digest` overlap and takes the stricter result. |
| `WP-13` | `REFUSED` is a legitimate terminal outcome, recorded as such. It is never retried against the same binding within the same run, and never converted into a validation failure. |
| `WP-14` | The provider is stateless across invocations from core's perspective. Any provider-side session is invisible to core and must not change the meaning of `idempotency_key`. |

---

## 5. Capability surface

Capabilities reach the provider only as `InvocationRequest.granted_capabilities`,
computed by `authority-matrix.md` §5 and frozen for the run.

| class | present in `granted_capabilities` | note |
|---|---|---|
| `ORD` | possibly, per role table §4.1 | each gates one or more `ToolDescriptor` entries |
| `HUMAN` | never | exercise requires a `HumanDecision` the provider cannot produce |
| `KERNEL` | never | `AX-7` |
| `NEVER` | never | `AX-6` |

| kernel-side capability | used when |
|---|---|
| `worker.invoke` | `preflight`, `invoke` |
| `run.abort` | `cancel` |
| `audit.append` | recording invocation, tool calls, and receipt |

---

## 6. Invocation sequence

| step | actor | action | record |
|---|---|---|---|
| 1 | kernel | resolve capabilities, freeze `effective_capabilities` | `ContractActivationRecord` (AUTHORITY) |
| 2 | kernel | take `RealitySnapshot`, build `ScopeView` | `RealitySnapshot` (EVIDENCE) |
| 3 | kernel | assemble prompt bundle and context, store content-addressed, compute `context_digest` | artifacts |
| 4 | provider | `preflight` | `AuditEvent` |
| 5 | kernel | `WorkerInvocation` → `DISPATCHED` | `AuditEvent` |
| 6 | provider | `invoke`; each side effect via `ToolBridge.call` | one `AuditEvent` per call, with `capability_used` |
| 7 | kernel | measure usage, bound output, mint `WorkerReceipt` | `WorkerReceipt` (EVIDENCE of what was said) |
| 8 | kernel | convert `requested_validations` into `ValidationOperation` records | CLAIM → request |
| 9 | kernel | execute validations, mint `ValidationReceipt` | EVIDENCE |
| 10 | kernel | recompute `observed_satisfaction` | derived EVIDENCE |

Steps 7 through 10 are the only path by which anything a worker produced can
affect stage state.

---

## 7. Conformance checklist

| id | check |
|---|---|
| `CF-1` | `invoke` twice with the same `idempotency_key` performs one execution and returns one outcome |
| `CF-2` | a tool call whose `required_capability` is absent returns `DENIED` and performs no side effect |
| `CF-3` | no filesystem access outside `ScopeView`, verified by the post-run snapshot showing zero unattributed drift |
| `CF-4` | no network egress except through `ToolBridge` |
| `CF-5` | `cancel` during `invoke` terminates within the configured grace window, or the kernel force-terminates and records `HUMAN_STOP` |
| `CF-6` | `proposed_mutations` reference only paths inside `ScopeView.include` minus `exclude` |
| `CF-7` | `requested_validations` name only `validation_spec_id` values present in the pinned contract |
| `CF-8` | outputs contain no secret values, verified against the salted digests of resolved secrets |
| `CF-9` | provider-reported `usage` is within tolerance of kernel measurement |
| `CF-10` | a `REFUSED` outcome produces a receipt and does not advance any stage state |
