"""Error taxonomy.

Each error names a governance failure class, never a vendor or transport
failure. Adapters translate their own failures into these.
"""

from __future__ import annotations


class GovernedRuntimeError(Exception):
    """Base class for every error the runtime raises."""


class IntegrityViolation(GovernedRuntimeError):
    """A record failed verification, or a rule that admits no exception broke.

    Raised by chain verification (evidence-model §3.3), by payload binding,
    by `G-1` (a `ReviewAttestation` is required where a review judgement was
    offered), and by `RA-INV-1` (attestation minting outside `review.attest`).
    """


class CapabilityDenied(GovernedRuntimeError):
    """An operation required a `CapabilityId` its caller does not hold.

    Design basis: authority-matrix `AX-2`; `WP-16` for the recovery case, where
    `recovery.reconcile` reaches `lookup` and nothing executable.
    """


class BarrierViolation(GovernedRuntimeError):
    """The `RUN-INV-3` barrier refused a new external effect.

    Raised while any `WorkerInvocation` or `CommitIntent` of the run is
    `PENDING` or `UNRESOLVABLE` (transition-matrix §5).
    """


class RecoveryAmbiguity(GovernedRuntimeError):
    """Recovery could not decide what already happened.

    `lookup` could not answer for a key, or a repository scan matched an
    `operation_token` to more than one revision, or to none while the base no
    longer matches (`CM-INV-3`, `WP-16`).
    """


class ProviderUnavailable(GovernedRuntimeError):
    """A provider operation failed transiently (worker_provider §2.1)."""


class PolicyDenied(GovernedRuntimeError):
    """A policy verdict forbade the transition (transition-matrix §2)."""
