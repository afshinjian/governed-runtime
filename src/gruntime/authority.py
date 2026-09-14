"""AX-1..11: bounds narrow; only recorded, admissible grantors grant.

The tables transcribe design-01-frozen authority-matrix §§2, 4.1. Resolution
is pure; the controller persists its inputs and the resulting activation.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

import rfc8785

from .canonical import digest_bytes
from .contracts import require
from .decision import derive_decision_state
from .errors import CapabilityDenied
from .models import ActorKind, AuthMethod, DecisionKind, DecisionState
from .scope import authorize_path

# Capability: (class, admissible grant kinds). Ceiling is deliberately absent.
REGISTER = {}
for kind, grantors, names in (
    ("ORD", ("ROLE_DEFAULT", "POLICY"), "fs.read"),
    ("ORD", ("ROLE_DEFAULT",), "stage.declare fs.write proc.exec.validation validation.request review.submit finding.raise finding.resolve commit.propose escalation.raise"),
    ("ORD", ("HUMAN_DECISION", "POLICY"), "roadmap.import contract.author fs.delete net.egress.allowlist audit.read"),
    ("ORD", ("HUMAN_DECISION",), "roadmap.writeback contract.supersede fs.read.outside_scope"),
    ("HUMAN", ("HUMAN_DECISION",), "project.create project.mode.set project.abandon project.archive policy.set policy.override budget.grant budget.extend stage.reject stage.abandon proc.exec.arbitrary net.egress.any secret.read finding.waive commit.publish decision.record audit.redact"),
    ("KERNEL", (), "project.lifecycle.advance suspension.set suspension.clear stage.lifecycle.advance stage.satisfy contract.activate contract.revoke run.start run.abort worker.invoke recovery.reconcile snapshot.take validation.execute validation.attest review.attest review.attest.independent commit.authorize commit.apply escalation.resolve audit.append"),
    ("NEVER", (), "worker.delegate fs.read.outside_workspace fs.write.outside_scope commit.rewrite_history audit.rewrite"),
):
    for name in names.split():
        REGISTER[name] = (kind, grantors)

ROLES = ("PLANNER", "IMPLEMENTER", "REVIEWER", "INTEGRATOR", "ANALYST")
ROLE_TABLE = dict(
    zip(("fs.read", "fs.read.outside_scope", "fs.write", "fs.delete",
         "proc.exec.validation", "proc.exec.arbitrary", "net.egress.allowlist",
         "net.egress.any", "secret.read", "validation.request", "review.submit",
         "finding.raise", "finding.resolve", "finding.waive", "commit.propose",
         "contract.author", "contract.supersede", "stage.declare", "escalation.raise",
         "audit.read", "roadmap.import", "roadmap.writeback"),
        ("GGGGG", "CDCDC", "DGDGD", "DCDCD", "DGGGG", "DDDDC", "CCDCC",
         "DDDDD", "DCDCD", "DGGGG", "DDGDD", "GGGGG", "DCGCD", "DDDDD", "DGDGD",
         "GDDDD", "CDDDD", "GGGGG", "GGGGG", "CCGCG", "CDDDD", "CDDDD")))
AUTONOMOUS_DENY = frozenset(("project.create", "fs.read.outside_scope", "proc.exec.arbitrary", "net.egress.any"))
# Attempts that can execute, mutate, or reach an external service cost budget.
COST_CAPABILITIES = frozenset(("fs.write", "fs.delete", "proc.exec.validation", "proc.exec.arbitrary",
    "net.egress.allowlist", "net.egress.any", "secret.read", "validation.request", "commit.propose",
    "commit.publish", "roadmap.import", "roadmap.writeback", "contract.author", "contract.supersede"))


def runtime_actor(name):
    return dict(actor_kind="RUNTIME", actor_id=name, auth_method="NONE")


def ts(value):
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def role_allows(capability, role):
    return role in ROLES and ROLE_TABLE.get(capability, "DDDDD")[ROLES.index(role)] != "D"  # guard:gr06_role_table


def human_covers(decision, contract, run_id, capability, now, snapshot_id):
    actor = decision.decided_by
    authenticated = (actor.actor_kind is ActorKind.HUMAN and bool(actor.principal_key_id)
        and actor.auth_method in (AuthMethod.SESSION, AuthMethod.SIGNATURE, AuthMethod.MTLS)
        and decision.auth_method == actor.auth_method
        and (actor.auth_method is not AuthMethod.SIGNATURE or bool(decision.signature)))
    subjects = {"PROJECT": contract.project_id, "STAGE": contract.stage_id,
                "RUN": run_id, "CONTRACT": contract.contract_id, "CAPABILITY": capability}
    subject_matches = subjects.get(decision.subject_kind.value) == decision.subject_id
    scope_matches = (decision.scope.value == "PROJECT" and decision.subject_kind.value in ("PROJECT", "CAPABILITY")
        or decision.scope.value == "STAGE" and decision.subject_kind.value == "STAGE"
        or decision.scope.value == "RUN" and decision.subject_kind.value == "RUN"
        or decision.scope.value == "SINGLE_ACTION" and decision.subject_kind.value == "CONTRACT")
    return (authenticated and decision.project_id == contract.project_id  # guard:gr06_human_admissible
        and decision.decision_kind is DecisionKind.GRANT_CAPABILITY
        and capability in decision.grants and capability not in decision.revokes
        and bool(decision.evidence_shown) and 16 <= len(decision.nonce) <= 64
        and decision.decided_at <= now and subject_matches and scope_matches
        # Snapshot observation persists STALE through the single decision-state
        # derivation. An unchanged re-observation does not supersede a decision.
        and (not decision.snapshot_bound or bool(decision.subject_snapshot_id))
        and derive_decision_state(decision, now=now) is DecisionState.VALID)


def resolve_grants(contract, *, ceiling, mode, remaining_budget, now, run_id,
                   snapshot_id, decisions=(), policy_evaluations=(), policy_digest=None):
    granted, denied, basis = set(), {}, {}
    require(mode in ("AUTONOMOUS", "SUPERVISED"), "unknown governance mode")  # guard:gr06_mode
    for capability in contract.capability_request:
        reason = None
        entry = None
        kind, grantors = REGISTER.get(capability, ("NEVER", ()))
        if capability not in ceiling:  # guard:gr06_resolve_ceiling
            reason = "NOT_IN_CEILING"
        elif kind in ("KERNEL", "NEVER"):  # guard:gr06_resolve_nondelegable
            reason = "NEVER_GRANTABLE"
        elif mode == "AUTONOMOUS" and capability in AUTONOMOUS_DENY:  # guard:gr06_resolve_mode
            reason = "MODE_FORBIDDEN"
        elif not role_allows(capability, contract.worker_role):  # guard:gr06_resolve_role
            reason = "ROLE_FORBIDDEN"
        else:
            for decision in decisions:
                if "HUMAN_DECISION" in grantors and human_covers(decision, contract, run_id, capability, now, snapshot_id):  # guard:gr06_human_grantor
                    actor = decision.decided_by
                    entry = dict(grant_kind="HUMAN_DECISION", ref=decision.decision_id, at=ts(now),
                        grantor=dict(actor_kind=actor.actor_kind.value, actor_id=actor.actor_id,
                                     auth_method=actor.auth_method.value, principal_key_id=actor.principal_key_id))
                    break
            for evaluation in policy_evaluations:
                if entry is None and "POLICY" in grantors and mode == "AUTONOMOUS" and (  # guard:gr06_policy_grantor
                    evaluation["policy_digest"] == policy_digest
                    and evaluation["project_id"] == contract.project_id
                    and capability in evaluation["policy_grantable"]):
                    entry = dict(grant_kind="POLICY", ref=evaluation["evaluation_id"], at=ts(now), grantor=runtime_actor("POLICY_ENGINE"))
            if entry is None and "ROLE_DEFAULT" in grantors:  # guard:gr06_role_grantor
                entry = dict(grant_kind="ROLE_DEFAULT", at=ts(now), grantor=runtime_actor("ROLE_DEFAULT"))
            if entry is None:  # guard:gr06_no_grantor
                reason = "NO_GRANTOR"
            elif capability in COST_CAPABILITIES and any(v <= 0 for v in remaining_budget.values()):  # guard:gr06_budget_exhausted
                reason = "BUDGET"
        if reason:
            denied[capability] = reason
        else:
            granted.add(capability)
            basis[capability] = entry
    return frozenset(granted), denied, basis


@dataclass(frozen=True, init=False)
class ContractActivationRecord:
    _encoded: bytes

    def __init__(self, document):
        object.__setattr__(self, "_encoded", rfc8785.dumps(document))
        self.verify()

    @classmethod
    def mint(cls, **document):
        document["record_hash"] = digest_bytes(rfc8785.dumps(document))
        return cls(document)

    def document(self):
        return json.loads(self._encoded)

    def __getattr__(self, name):
        try:
            return self.document()[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def verify(self):
        doc = self.document()
        require(doc["record_hash"] == digest_bytes(rfc8785.dumps({k: v for k, v in doc.items() if k != "record_hash"})), "activation record hash mismatch")  # guard:gr06_activation_hash
        require(doc["activated_by"]["actor_kind"] == "RUNTIME", "only runtime may mint activation")  # guard:gr06_activation_actor
        require(bool(doc["authority_chain"]), "activation authority chain is empty")  # guard:gr06_authority_chain
        granted = doc["granted_capabilities"]
        require(len(set(granted)) == len(granted) and set(doc["capability_grant_basis"]) == set(granted) and not set(granted) & set(doc["denied_capabilities"]), "A-INV-3: grant basis must exactly cover grants")  # guard:gr06_basis_coverage
        for c, entry in doc["capability_grant_basis"].items():
            kind, grantors = REGISTER.get(c, ("NEVER", ()))
            grant_kind = entry["grant_kind"]
            actor = entry["grantor"]
            admissible = (grant_kind in grantors and kind not in ("KERNEL", "NEVER")
                and entry in doc["authority_chain"] and parse_ts(entry["at"]) <= parse_ts(doc["activated_at"]))
            if grant_kind == "HUMAN_DECISION":
                admissible = admissible and bool(entry.get("ref")) and actor["actor_kind"] == "HUMAN" and bool(actor.get("principal_key_id")) and actor["auth_method"] in ("SESSION", "SIGNATURE", "MTLS")
            else:
                admissible = admissible and actor == runtime_actor("ROLE_DEFAULT" if grant_kind == "ROLE_DEFAULT" else "POLICY_ENGINE") and ("ref" not in entry if grant_kind == "ROLE_DEFAULT" else bool(entry.get("ref")))
            require(admissible, "A-INV-3: inadmissible grantor")  # guard:gr06_basis_grantor


def evaluate_authority(contract, activation, capability, *, run_id, project_id, now,
                       root=None, path=None, submodules=(), exercise_decision=None, grant_only=False):
    """Evaluate a verified activation. The controller also replays source records.

    No activation means no authority, including for a document labelled ACTIVE.
    This permission to attempt never discharges transition evidence (AX-9).
    """
    require(activation is not None, "unactivated contract grants nothing", CapabilityDenied)  # guard:gr06_activation_required
    activation.verify()
    # Reparse to verify the document even if an in-memory value was tampered with.
    from .contracts import StageContract
    contract = StageContract(contract.document())
    require(activation.contract_id == contract.contract_id and activation.contract_hash == contract.contract_hash and activation.run_id == run_id and activation.project_id == project_id == contract.project_id, "activation contract/run binding mismatch")  # guard:gr06_activation_binding
    require(contract.status == "ACTIVE" and not activation.document().get("revoked_at") and parse_ts(activation.activated_at) <= now <= parse_ts(activation.expires_at), "activation is inactive, revoked or expired", CapabilityDenied)  # guard:gr06_activation_live
    require(type(capability) is str and capability in activation.granted_capabilities, "capability not granted", CapabilityDenied)  # guard:gr06_capability_required
    require(capability in contract.capability_request and role_allows(capability, contract.worker_role), "grant exceeds contract or role")  # guard:gr06_grant_bounds
    require(set(activation.granted_capabilities) | set(activation.denied_capabilities) == set(contract.capability_request), "AX-8: activation must account for every request")  # guard:gr06_denial_coverage
    require(parse_ts(activation.expires_at) == parse_ts(activation.activated_at) + timedelta(milliseconds=contract.deadline_ms), "activation deadline differs from frozen contract")  # guard:gr06_activation_deadline
    require(capability not in contract.prohibited_actions, "contract prohibits action", CapabilityDenied)  # guard:gr06_prohibited_action
    if grant_only:  # guard:gr07_grant_only_boundary
        return True
    needs_decision = REGISTER[capability][0] == "HUMAN" or (
        activation.governance_mode_at_activation == "SUPERVISED" and capability in ("roadmap.writeback", "fs.delete"))
    if needs_decision:
        d = exercise_decision
        valid = (d is not None and d.project_id == project_id and d.decision_kind is DecisionKind.APPROVE
            and d.subject_kind.value == "CAPABILITY" and d.subject_id == capability
            and d.scope.value == "SINGLE_ACTION" and bool(d.evidence_shown)
            and d.decided_by.actor_kind is ActorKind.HUMAN and bool(d.decided_by.principal_key_id)
            and d.auth_method in (AuthMethod.SESSION, AuthMethod.SIGNATURE, AuthMethod.MTLS)
            and d.auth_method == d.decided_by.auth_method and d.decided_at <= now
            and derive_decision_state(d, now=now) is DecisionState.VALID)
        # This checks the exercise precondition; the effect's transition must
        # consume the decision atomically. Grant-time permission is insufficient.
        require(valid, "capability requires a live human decision at exercise time", CapabilityDenied)  # guard:gr06_exercise_decision
    if capability.startswith("fs."):
        require(path is not None and root is not None, "filesystem authority requires target", CapabilityDenied)  # guard:gr06_target_required
    if path is not None:
        return authorize_path(contract, root, path, submodules=submodules,
            outside_scope=capability == "fs.read.outside_scope",
            write=capability in ("fs.write", "fs.delete", "commit.propose"))
    return True
