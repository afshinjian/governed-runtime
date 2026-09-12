"""Commit intent evaluation and application.

Design basis: transition-matrix §7.4, domain-model §8.3/§8.4, `CM-INV-1..3`,
evidence-model §3.2.1.

The ordering that makes a crash between the mutation and the receipt
recoverable: `operation_token` is durable and written into the revision's
trailers *before* the repository is touched, so a revision that landed while
the controller was down is always findable and is adopted rather than retried.

Preconditions are discharged by kernel-minted attestations only. This module
never resolves a reviewer's own judgement record (`G-1`).
"""

from __future__ import annotations

from typing import Optional, Sequence

from .models import (
    ArtifactRef,
    CommitIntent,
    CommitPreconditions,
    CommitReceipt,
    Hash,
    Id,
    MutationProposal,
    Verification,
)

#: Trailer key carrying the intent's `operation_token` into the revision.
OPERATION_TOKEN_TRAILER = "Operation-Token"

#: Capability that proposes an intent.
PROPOSE_CAPABILITY = "commit.propose"

#: Capability that authorizes one.
AUTHORIZE_CAPABILITY = "commit.authorize"

#: Capability that applies one. Never held by a worker (`AX-7`).
APPLY_CAPABILITY = "commit.apply"

#: Token length bounds (`CommitIntent.operation_token`, `Str(32..128)`).
TOKEN_MIN_LEN = 32
TOKEN_MAX_LEN = 128


def mint_operation_token() -> str:
    """Mint a globally unique, durable identity for one application attempt.

    Minted at `PROPOSED` and written into `trailers`, so the landed revision
    carries its own identity (`CM-INV-2`).
    """
    raise NotImplementedError


def build_trailers(
    operation_token: str, evidence_refs: Sequence[Hash] = ()
) -> dict[str, str]:
    """Trailers for the revision: evidence back-references and the token."""
    raise NotImplementedError


def evaluate_preconditions(
    preconditions: CommitPreconditions,
    *,
    resolve_attestation,
    resolve_validation,
    resolve_decision,
) -> bool:
    """Decide `preconditions_met` for an intent.

    Every entry of `preconditions.reviews` must resolve to a kernel-minted
    attestation. A raw id, or a reference to a judgement record, raises
    `IntegrityViolation` here rather than being trusted because it was already
    stored (`G-1`).
    """
    raise NotImplementedError


def expected_tree_digest(
    base_tree_digest: Hash, mutations: Sequence[MutationProposal]
) -> Hash:
    """Predict the post-application tree digest (domain-model §8.3)."""
    raise NotImplementedError


def verify_application(
    intent: CommitIntent, actual_tree_digest: Hash
) -> Verification:
    """`MATCHED` iff `actual_tree_digest == intent.expected_tree_digest`.

    `DIVERGED` raises `Escalation(INTEGRITY_VIOLATION)` and suspends the run
    at the caller (`CM-INV-1`); the receipt still records what landed.
    """
    raise NotImplementedError


def build_receipt(
    intent: CommitIntent,
    *,
    revision_id: str,
    parent_revision_ids: Sequence[str],
    actual_tree_digest: Hash,
    diff_ref: ArtifactRef,
    post_snapshot_id: Id,
    attribution,
    prev_event_hash: Hash,
    rollback_handle: Optional[str] = None,
) -> CommitReceipt:
    """Build the `CommitReceipt` for an application or an adoption.

    `attribution = RECONCILED` when minted under `recovery.reconcile` for a
    revision found by `operation_token` after a restart (§8.4).
    """
    raise NotImplementedError
