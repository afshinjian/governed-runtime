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

import secrets
import uuid
from datetime import datetime, timezone
from typing import Mapping, Optional, Sequence

from .canonical import canonical_json, digest_bytes
from .models import (
    ActorKind,
    ActorRef,
    ArtifactRef,
    AuthMethod,
    CommitIntent,
    CommitPreconditions,
    CommitReceipt,
    Hash,
    Id,
    MutationOp,
    MutationProposal,
    PathStr,
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

#: Trailer key carrying an evidence back-reference into the revision.
EVIDENCE_TRAILER = "Governed-Evidence"


def mint_operation_token() -> str:
    """Mint a globally unique, durable identity for one application attempt.

    Minted at `PROPOSED` and written into `trailers`, so the landed revision
    carries its own identity (`CM-INV-2`).
    """
    token = f"gr-{uuid.uuid4().hex}-{secrets.token_hex(8)}"
    if not TOKEN_MIN_LEN <= len(token) <= TOKEN_MAX_LEN:  # pragma: no cover
        raise ValueError(f"operation token out of bounds: {len(token)}")
    return token


def build_trailers(
    operation_token: str, evidence_refs: Sequence[Hash] = ()
) -> dict[str, str]:
    """Trailers for the revision: evidence back-references and the token."""
    trailers = {OPERATION_TOKEN_TRAILER: operation_token}
    if evidence_refs:
        trailers[EVIDENCE_TRAILER] = " ".join(evidence_refs)
    return trailers


def evaluate_preconditions(
    preconditions: CommitPreconditions,
    *,
    resolve_attestation,
    resolve_validation,
    resolve_decision,
) -> bool:
    """Decide `preconditions_met` for an intent.

    Every entry of `preconditions.reviews` is resolved through
    `resolve_attestation`, which raises `IntegrityViolation` for a raw id or a
    reference to a judgement record. Resolution happens here, on the consuming
    path, rather than being trusted because the value was already stored
    (`G-1`).
    """
    for digest in preconditions.validations:
        if not resolve_validation(digest):
            return False
    for ref in preconditions.reviews:
        # Raises rather than returning False: an unresolvable review
        # precondition is an integrity failure, not an unmet one.
        resolve_attestation(ref)
    for ref in preconditions.decisions:
        if not resolve_decision(ref):
            return False
    return True


def apply_to_index(
    base_index: Mapping[PathStr, Hash], mutations: Sequence[MutationProposal]
) -> dict[PathStr, Hash]:
    """The file index the mutations predict, applied to `base_index`."""
    index = dict(base_index)
    for mutation in mutations:
        if mutation.op is MutationOp.DELETE:
            index.pop(mutation.path, None)
        elif mutation.op is MutationOp.RENAME:
            digest = index.pop(mutation.path, None)
            if mutation.rename_to is not None and digest is not None:
                index[mutation.rename_to] = digest
        elif mutation.after_ref is not None:
            index[mutation.path] = mutation.after_ref.digest
    return index


def expected_tree_digest(
    base_index: Mapping[PathStr, Hash], mutations: Sequence[MutationProposal]
) -> Hash:
    """Predict the post-application tree digest (domain-model §8.3).

    The prediction is over the *file index* — path to content digest — rather
    than over the base digest alone, because a digest is not invertible and a
    prediction that cannot be compared to a re-observation is not a check.
    The adapter re-observes the same index after the mutation lands, so
    `MATCHED` means the workspace holds what was authorized and nothing else.
    """
    return digest_bytes(canonical_json(apply_to_index(base_index, mutations)))


def verify_application(
    intent: CommitIntent, actual_tree_digest: Hash
) -> Verification:
    """`MATCHED` iff `actual_tree_digest == intent.expected_tree_digest`.

    `DIVERGED` raises `Escalation(INTEGRITY_VIOLATION)` and suspends the run
    at the caller (`CM-INV-1`); the receipt still records what landed.
    """
    if actual_tree_digest == intent.expected_tree_digest:
        return Verification.MATCHED
    return Verification.DIVERGED


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
    revision found by `operation_token` after a restart (§8.4). The receipt
    carries the token either way, so the revision it describes stays matchable
    to the intent that authorized it.
    """
    applied_at = datetime.now(timezone.utc)
    applied_by = ActorRef(
        actor_kind=ActorKind.RUNTIME,
        actor_id="gruntime.commit",
        auth_method=AuthMethod.NONE,
    )
    verification = verify_application(intent, actual_tree_digest)
    preimage = {
        "intent_id": intent.intent_id,
        "revision_id": revision_id,
        "parent_revision_ids": list(parent_revision_ids),
        "actual_tree_digest": actual_tree_digest,
        "expected_tree_digest": intent.expected_tree_digest,
        "verification": verification.value,
        "diff_digest": diff_ref.digest,
        "applied_at": applied_at.isoformat(),
        "attribution": getattr(attribution, "value", attribution),
        "operation_token": intent.operation_token,
        "post_snapshot_id": post_snapshot_id,
    }
    return CommitReceipt(
        receipt_id=f"cr-{uuid.uuid4().hex}",
        intent_id=intent.intent_id,
        revision_id=revision_id,
        actual_tree_digest=actual_tree_digest,
        verification=verification,
        diff_ref=diff_ref,
        applied_at=applied_at,
        applied_by=applied_by,
        attribution=attribution,
        operation_token=intent.operation_token,
        post_snapshot_id=post_snapshot_id,
        receipt_hash=digest_bytes(canonical_json(preimage)),
        prev_event_hash=prev_event_hash,
        parent_revision_ids=tuple(parent_revision_ids),
        rollback_handle=rollback_handle,
    )
