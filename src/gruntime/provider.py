"""The `WorkerProvider` interface and the capability gate in front of it.

Design basis: worker_provider.md §2 (types), §3 (operations), §4 (`WP-6`,
`WP-15`, `WP-16`, `WP-17`), §5 (capability surface), authority-matrix §5.

Core calls the provider; the provider never calls core. `execution_binding`,
provider capability names and diagnostics are opaque and are never branched on.

`lookup` is a distinct operation, not a mode of `invoke`. It takes an
`idempotency_key` and nothing else — no request, no bridge, no bytes — so it
cannot start, resume, extend or bill an execution (`WP-16`). It is the only
provider operation reachable under `recovery.reconcile`, which is what makes
recovery incapable of executing an absent key rather than merely unwilling to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence, Union

from .models import (
    ArtifactRef,
    Budget,
    CapabilityId,
    Claim,
    Hash,
    Id,
    InvocationStatus,
    MutationProposal,
    OutcomeStatus,
    TerminationReason,
    Ts,
    Usage,
    WorkerRole,
)

# --- capability sets (worker_provider §5) ---------------------------------

#: Kernel-side capability for `preflight` and `invoke`.
INVOKE_CAPABILITY: CapabilityId = "worker.invoke"

#: Kernel-side capability for `lookup`.
RECONCILE_CAPABILITY: CapabilityId = "recovery.reconcile"

#: Kernel-side capability for `cancel`.
ABORT_CAPABILITY: CapabilityId = "run.abort"

#: Everything recovery holds. It reaches `lookup` and nothing else: no member
#: of this set can execute, mutate a repository, or create an operation
#: (`WP-16`, authority-matrix §5).
RECOVERY_CAPABILITIES: frozenset[CapabilityId] = frozenset({RECONCILE_CAPABILITY})

#: What the dispatch path holds.
DISPATCH_CAPABILITIES: frozenset[CapabilityId] = frozenset({INVOKE_CAPABILITY})


# --- types (worker_provider §2) -------------------------------------------


@dataclass(frozen=True)
class BindingDescriptor:
    binding_id: str
    label: str
    max_output_bytes: int
    relative_cost: float
    deterministic: bool


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    provider_version: str
    supported_roles: frozenset[WorkerRole]
    bindings: Sequence[BindingDescriptor]
    max_context_bytes: int
    supports_cancel: bool
    supports_streaming: bool
    cost_model: str


@dataclass(frozen=True)
class ScopeView:
    root: str
    file_index_ref: ArtifactRef
    snapshot_id: Id
    writable: bool
    include: Sequence[str] = ()
    exclude: Sequence[str] = ()


@dataclass(frozen=True)
class ToolDescriptor:
    tool_id: str
    required_capability: CapabilityId
    input_schema_ref: ArtifactRef
    output_schema_ref: ArtifactRef
    side_effecting: bool


@dataclass(frozen=True)
class ToolCall:
    call_id: Id
    tool_id: str
    arguments_ref: ArtifactRef
    requested_at: Ts


@dataclass(frozen=True)
class ToolResult:
    call_id: Id
    outcome: str
    latency_ms: int
    result_ref: Optional[ArtifactRef] = None
    denial_capability: Optional[CapabilityId] = None


@dataclass(frozen=True)
class InvocationRequest:
    """The exact bytes persisted as `WorkerInvocation.request_ref` before the
    first provider call (`WP-15`). Recovery reads them and never re-sends them."""

    invocation_id: Id
    worker_role: WorkerRole
    binding_id: str
    prompt_bundle_ref: ArtifactRef
    scope_view: ScopeView
    idempotency_key: Hash
    deadline_at: Ts
    context_refs: Sequence[ArtifactRef] = ()
    granted_capabilities: frozenset[CapabilityId] = frozenset()
    tool_surface: Sequence[ToolDescriptor] = ()
    budget: Budget = field(default_factory=Budget)


@dataclass(frozen=True)
class ValidationRequestDraft:
    validation_spec_id: str
    criterion_refs: frozenset[str] = frozenset()


@dataclass(frozen=True)
class InvocationOutcome:
    """Everything here other than `usage` is CLAIM class (`WP-1`)."""

    invocation_id: Id
    status: OutcomeStatus
    output_ref: ArtifactRef
    termination_reason: TerminationReason
    usage: Usage = field(default_factory=Usage)
    claims: Sequence[Claim] = ()
    proposed_mutations: Sequence[MutationProposal] = ()
    requested_validations: Sequence[ValidationRequestDraft] = ()
    diagnostics: Sequence[object] = ()


@dataclass(frozen=True)
class PreflightResult:
    accepted: bool
    estimated: Usage = field(default_factory=Usage)
    diagnostics: Sequence[object] = ()


@dataclass(frozen=True)
class ProviderHealth:
    status: str
    checked_at: Ts


@dataclass(frozen=True)
class CancelResult:
    acknowledged: bool


class ProviderError(Exception):
    """worker_provider §2 / §2.1. Carried, never interpreted by core."""

    def __init__(
        self,
        code: str,
        message: object = None,
        *,
        retryable: bool = False,
        retry_after_ms: Optional[int] = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.retry_after_ms = retry_after_ms


# --- LookupResult: exactly three answers (worker_provider §2, WP-16) -------


@dataclass(frozen=True)
class LookupLive:
    """An execution is still running under the key. `handle` is opaque and
    serves only to resume tracking it."""

    handle: object


@dataclass(frozen=True)
class LookupFinished:
    """The provider holds a terminal outcome for the key.

    The outcome is reported as it was, including `FAILED`, `TIMED_OUT`,
    `CANCELLED` and `REFUSED` (`CF-14`).
    """

    outcome: InvocationOutcome


@dataclass(frozen=True)
class LookupAbsent:
    """The provider holds nothing under the key and never did (`CF-12`).

    Returning this executes nothing; it is what lets recovery orphan an
    invocation safely instead of re-running the work.
    """


#: The only three answers `lookup` may give.
LookupResult = Union[LookupLive, LookupFinished, LookupAbsent]


# --- the interface --------------------------------------------------------


class ToolBridge:
    """The provider's only channel to the outside (worker_provider §3.1)."""

    def call(self, tool_call: ToolCall) -> ToolResult:
        """Kernel-mediated; an unknown `tool_id` returns `DENIED`, not raises."""
        raise NotImplementedError

    def progress(self, note: object) -> None:
        """Advisory. Recorded, never acted on."""
        raise NotImplementedError


class WorkerProvider:
    """Interface every provider adapter implements (worker_provider §3).

    A provider that cannot implement `lookup` is inadmissible for governed
    mutation (`WP-17`): an operation the kernel can start and can never learn
    the outcome of is not governable.
    """

    def describe(self) -> ProviderDescriptor:
        raise NotImplementedError

    def preflight(self, request: InvocationRequest) -> PreflightResult:
        """Requires `worker.invoke`."""
        raise NotImplementedError

    def invoke(self, request: InvocationRequest, bridge: ToolBridge) -> InvocationOutcome:
        """Requires `worker.invoke`. Idempotent on `idempotency_key` (`WP-6`)."""
        raise NotImplementedError

    def lookup(self, idempotency_key: Hash) -> LookupResult:
        """Report what happened under `idempotency_key`, executing nothing.

        Requires `recovery.reconcile`. Takes a key and nothing else: no
        `InvocationRequest`, no `ToolBridge`, no request bytes (`WP-16`).
        """
        raise NotImplementedError

    def cancel(self, invocation_id: Id, reason: str) -> CancelResult:
        """Requires `run.abort`."""
        raise NotImplementedError

    def health(self) -> ProviderHealth:
        raise NotImplementedError


class GovernedProvider:
    """Capability gate around a `WorkerProvider`.

    Each operation is admitted only if its kernel-side capability is in the
    set this gate was constructed with. Held with `RECOVERY_CAPABILITIES`, the
    gate exposes `lookup` alone: `invoke` and `preflight` raise
    `CapabilityDenied` rather than reaching the provider at all, so recovery
    holds no capability that can execute (`WP-16`, `AX-2`).
    """

    def __init__(
        self,
        provider: WorkerProvider,
        capabilities: Iterable[CapabilityId],
    ) -> None:
        self.provider = provider
        self.capabilities: frozenset[CapabilityId] = frozenset(capabilities)

    def _require(self, capability: CapabilityId) -> None:
        """Raise `CapabilityDenied` unless `capability` is held."""
        raise NotImplementedError

    def describe(self) -> ProviderDescriptor:
        raise NotImplementedError

    def preflight(self, request: InvocationRequest) -> PreflightResult:
        raise NotImplementedError

    def invoke(self, request: InvocationRequest, bridge: Optional[ToolBridge] = None) -> InvocationOutcome:
        raise NotImplementedError

    def lookup(self, idempotency_key: Hash) -> LookupResult:
        raise NotImplementedError

    def cancel(self, invocation_id: Id, reason: str) -> CancelResult:
        raise NotImplementedError

    def health(self) -> ProviderHealth:
        raise NotImplementedError


def status_for_outcome(status: OutcomeStatus) -> InvocationStatus:
    """Map a provider outcome onto the invocation status it is adopted as.

    `REFUSED` maps to `FAILED`; no non-`COMPLETED` outcome ever becomes
    `COMPLETED` (`W-INV-4`, worker_provider §6.1 step 3).
    """
    raise NotImplementedError
