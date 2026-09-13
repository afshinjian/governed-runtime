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
from .errors import IntegrityViolation
from .repository import assert_unprotected
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
                index[mutation.rename_to] = (mutation.after_ref.digest if mutation.after_ref else digest)
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


def exact_paths(intent: CommitIntent) -> tuple[str, ...]:
    """All source and destination paths, with no pathspec or scope expansion."""
    paths = []
    for mutation in intent.mutations:
        if not mutation.in_scope:  # guard:commit_scope
            raise IntegrityViolation("commit mutation is outside contract scope")
        assert_unprotected(mutation.path)  # guard:commit_source_protected
        paths.append(mutation.path)
        if mutation.rename_to is not None:
            assert_unprotected(mutation.rename_to)  # guard:commit_rename_protected
            paths.append(mutation.rename_to)
    if not paths or len(set(paths)) != len(paths):  # guard:commit_paths_unique
        raise IntegrityViolation("commit paths must be nonempty and unique")
    return tuple(sorted(paths))


def commit_message(intent: CommitIntent) -> bytes:
    """Canonical UTF-8 message; body hash includes the evidence/token trailers."""
    if (not intent.message.strip() or "\0" in intent.message  # guard:commit_message_shape
            or "\r" in intent.message or len(intent.message) > 8192
            or not intent.message.split("\n", 1)[0].strip()):
        raise IntegrityViolation("invalid commit message")
    if (not TOKEN_MIN_LEN <= len(intent.operation_token) <= TOKEN_MAX_LEN  # guard:commit_token_carried
            or intent.trailers.get(OPERATION_TOKEN_TRAILER) != intent.operation_token
            or any(not key or any(c in key for c in ":\n\r\0")
                   or any(c in value for c in "\n\r\0")
                   for key, value in intent.trailers.items())):
        raise IntegrityViolation("invalid commit trailers or missing operation token")
    return (intent.message.rstrip("\n") + "\n\n" + "\n".join(
        f"{key}: {value}" for key, value in sorted(intent.trailers.items())
    ) + "\n").encode("utf-8")


def message_fields(message: bytes) -> tuple[str, Hash]:
    subject, _, body = message.partition(b"\n")
    return subject.decode("utf-8"), digest_bytes(body)


def expected_entries(intent: CommitIntent, base: Mapping[str, tuple[str, Hash]]):
    """Predict content AND modes, retaining every untouched entry."""
    exact_paths(intent)
    entries = dict(base)
    for mutation in intent.mutations:
        old = base.get(mutation.path)
        if ((mutation.op is MutationOp.CREATE and old is not None)
                or (mutation.op is not MutationOp.CREATE and old is None)
                or mutation.before_digest != (old[1] if old else None)):
            raise IntegrityViolation("mutation preimage differs from the base")  # guard:commit_preimage
        if ((mutation.op in (MutationOp.CREATE, MutationOp.MODIFY) and mutation.after_ref is None)
                or (mutation.op is MutationOp.DELETE and mutation.after_ref is not None)
                or (mutation.op is MutationOp.RENAME and
                    (not mutation.rename_to or mutation.rename_to in base))
                or (mutation.op is not MutationOp.RENAME and mutation.rename_to is not None)
                or (mutation.op is MutationOp.CHMOD and mutation.mode not in (0o644, 0o755))):
            raise IntegrityViolation("invalid mutation shape")  # guard:commit_mutation_shape
        if mutation.op in (MutationOp.DELETE, MutationOp.RENAME):
            entries.pop(mutation.path)
        if mutation.op is not MutationOp.DELETE:
            path = mutation.rename_to if mutation.op is MutationOp.RENAME else mutation.path
            mode = ("100755" if mutation.mode == 0o755 else "100644") if mutation.op is MutationOp.CHMOD else (old[0] if old else "100644")
            entries[path] = (mode, mutation.after_ref.digest if mutation.after_ref else old[1])
    return entries


def verify_application(intent: CommitIntent, actual_tree_digest: Hash) -> Verification:
    return (Verification.MATCHED if actual_tree_digest == intent.expected_tree_digest
            else Verification.DIVERGED)


def verification_errors(intent: CommitIntent, observation: Mapping) -> tuple[str, ...]:
    """Used for precommit checks, direct receipts and reconciled receipts."""
    subject, body_hash = message_fields(commit_message(intent))
    expected = {
        "parent_revision_ids": (intent.base_revision_id,),
        "actual_tree_digest": intent.expected_tree_digest,
        "subject": subject,
        "body_hash": body_hash,
        "committed_paths": exact_paths(intent),
        "operation_tokens": (intent.operation_token,),
        "matching_revisions": (observation["revision_id"],),
        "entries": expected_entries(intent, observation["base_entries"]),
    }
    errors = []
    for key, value in expected.items():
        matches = observation.get(key) == value
        if not matches:  # guard:commit_observation_matches
            errors.append(key)
    return tuple(errors)


def verify_receipt(intent: CommitIntent, receipt: CommitReceipt, observation: Mapping) -> Verification:
    errors = list(verification_errors(intent, observation))
    recorded = {
        "revision_id": receipt.revision_id,
        "parent_revision_ids": tuple(receipt.parent_revision_ids),
        "actual_tree_digest": receipt.actual_tree_digest,
        "tree_id": receipt.tree_id,
        "subject": receipt.subject,
        "body_hash": receipt.body_hash,
        "committed_paths": tuple(receipt.committed_paths),
        "files_changed": tuple(receipt.files_changed),
        "operation_tokens": (receipt.operation_token,),
    }
    if receipt.intent_id != intent.intent_id or any(  # guard:commit_receipt_matches
        observation.get(key) != value for key, value in recorded.items()
    ):
        errors.append("receipt")
    return Verification.DIVERGED if errors else Verification.MATCHED


def build_receipt(
    intent: CommitIntent, *, observation: Mapping, diff_ref: ArtifactRef,
    post_snapshot_id: Id, attribution, prev_event_hash: Hash,
) -> CommitReceipt:
    """Record the observed revision, including all fields in its hash."""
    applied_at = datetime.now(timezone.utc)
    preimage = dict(observation, intent_id=intent.intent_id,
                    diff_digest=diff_ref.digest, applied_at=applied_at.isoformat(),
                    attribution=attribution.value, post_snapshot_id=post_snapshot_id,
                    prev_event_hash=prev_event_hash)
    receipt = CommitReceipt(
        receipt_id=f"cr-{uuid.uuid4().hex}", intent_id=intent.intent_id,
        revision_id=observation["revision_id"],
        parent_revision_ids=observation["parent_revision_ids"],
        actual_tree_digest=observation["actual_tree_digest"],
        tree_id=observation["tree_id"], subject=observation["subject"],
        body_hash=observation["body_hash"],
        committed_paths=observation["committed_paths"],
        files_changed=observation["files_changed"],
        verification=Verification.DIVERGED, diff_ref=diff_ref, applied_at=applied_at,
        applied_by=ActorRef(actor_kind=ActorKind.RUNTIME,
                            actor_id="gruntime.commit", auth_method=AuthMethod.NONE),
        attribution=attribution, operation_token=intent.operation_token,
        post_snapshot_id=post_snapshot_id, receipt_hash="", prev_event_hash=prev_event_hash,
    )
    receipt.verification = verify_receipt(intent, receipt, observation)
    preimage["verification"] = receipt.verification.value
    receipt.receipt_hash = digest_bytes(canonical_json(preimage))
    return receipt
