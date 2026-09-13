"""StageContract: frozen design-01 schema, XC-1..14 and F01-005 hashing.

The encoded document is the immutable value. Accessors return copies; absent
optional members stay absent. A contract is a request and carries no authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files
import json
import secrets
import time
import unicodedata

from jsonschema import Draft202012Validator, FormatChecker
import rfc8785

from .canonical import digest_bytes
from .errors import IntegrityViolation, PolicyDenied

SCHEMA_BYTES = files("gruntime").joinpath("schemas/stage_contract.schema.json").read_bytes()
SCHEMA = json.loads(SCHEMA_BYTES)
FORMATS = FormatChecker()


@FORMATS.checks("date-time", raises=ValueError)
def _timestamp(value):
    # Keep date validation available without jsonschema's optional format extras.
    return not isinstance(value, str) or datetime.fromisoformat(value.replace("Z", "+00:00")) is not None


VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FORMATS)


def require(condition, reason, error=IntegrityViolation):
    if not condition:  # guard:gr06_refusal
        raise error(reason)


def new_id():
    """Domain Id: millisecond timestamp and 80 random bits, Crockford ULID."""
    value = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    return "".join(alphabet[(value >> shift) & 31] for shift in range(125, -1, -5))


def contract_hash(document):
    preimage = {key: value for key, value in document.items()
                if key not in ("contract_hash", "status")}
    return digest_bytes(rfc8785.dumps(preimage))


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def validate_contract(document):
    errors = list(VALIDATOR.iter_errors(document))
    require(not errors, "StageContract schema: " + "; ".join(e.message for e in errors), PolicyDenied)  # guard:gr06_schema
    require(all(not any(ord(c) < 32 or ord(c) == 127 for c in s) for s in _strings(document)), "XC-14: control character", PolicyDenied)  # guard:gr06_controls
    require(all(unicodedata.normalize("NFC", s) == s for s in _strings(document)), "strings must be NFC", PolicyDenied)  # guard:gr06_nfc
    criteria = document["acceptance_criteria"]
    validations = [s["spec_id"] for s in document["required_validations"]]
    reviews = [s["spec_id"] for s in document["required_reviews"]]
    require(len({c["criterion_id"] for c in criteria}) == len(criteria), "XC-1: duplicate criterion", PolicyDenied)  # guard:gr06_criterion_ids
    require(len(set(validations + reviews)) == len(validations + reviews), "XC-2: duplicate or overlapping spec ids", PolicyDenied)  # guard:gr06_spec_ids
    require(all(c["verifier_ref"] in (validations if c["kind"] == "MECHANICAL" else reviews) for c in criteria), "XC-3/4: unbound verifier", PolicyDenied)  # guard:gr06_verifiers
    require(any(c["mandatory"] for c in criteria), "XC-5: mandatory criterion required", PolicyDenied)  # guard:gr06_mandatory
    # Reject ambiguous spellings instead of normalizing after the hash is pinned.
    from .scope import canonical_pattern
    for pattern in document["scope_include"] + document["scope_exclude"]:
        canonical_pattern(pattern)
    require(contract_hash(document) == document["contract_hash"], "XC-12: contract hash mismatch")  # guard:gr06_contract_hash


@dataclass(frozen=True, init=False)
class StageContract:
    _encoded: bytes

    def __init__(self, document):
        validate_contract(document)  # guard:gr06_validate_document
        object.__setattr__(self, "_encoded", rfc8785.dumps(document))

    @classmethod
    def author(cls, document):
        doc = dict(document)
        require(doc.get("status") == "DRAFT", "authoring requires DRAFT", PolicyDenied)  # guard:gr06_author_draft
        doc["contract_hash"] = contract_hash(doc)
        return cls(doc)

    def document(self):
        return json.loads(self._encoded)

    def __getattr__(self, name):
        try:
            return self.document()[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def with_status(self, status):
        return StageContract(dict(self.document(), status=status))
