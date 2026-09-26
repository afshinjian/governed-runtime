"""The supervised stage driver: the composition root's orchestration half.

`B2`. Until GR-32 the runtime had every governed transition and no production
caller that walked them in order. `controller.main()` hardcoded `FakeProvider`
and offered `start`, `recover`, `snapshot`, `invoke`, `validate` and `commit` —
six commands that between them can neither create a project, provision its
ceiling or budget, record a decision, author or activate a contract, allocate a
run, nor configure the inference relay. Everything a supervised project needs
between creation and its first governed revision existed only inside tests,
which provisioned by writing rows (`tests/gr06_support.py`). This module is
that missing caller, and nothing else: it composes, it presents, it orders, and
it stops.

What it is not, deliberately (`D1`): not a second controller, not a transport,
not a provider architecture, not a registry, not a plugin layer and not a
state machine. Every transition below is the kernel's existing one, called with
the arguments the frozen matrix's row declares. The four concepts this module
adds are `PilotSession` (the ordering), `OwnerPresenter` (the human boundary),
`StepOutcome`/`DriverReport` (the record) and `ProposalMapping` (the one
worker mutation shape `propose_commit` can express).

**The human is never simulated.** Every `CONFIRM` cell and every grant below
is an `OwnerRequest` put to a presenter, and the presenter's answer is what is
recorded. `None` is a refusal, there is no default approval, no answer is
constructed that the presenter did not return, and no decision is reused for a
second act. A driver that filled in an answer would be manufacturing exactly
the authority `HD-INV-1` exists to forbid.

**Ordering is load-bearing.** The confirmations at run opening, contract
activation, first invocation and commit authorization are all `APPROVE`s, and
`APPROVE` is in `SNAPSHOT_BOUND_KINDS`: a snapshot landing between recording
one and consuming it makes it `STALE` (`HD-INV-4`). Each is therefore recorded
immediately before the act it discharges, with no observation in between. The
historical plan (`docs/gr31-plan.md`) orders contract construction before
`open_run`; the code cannot do that, because a contract binds the run's
`stage_id` and the run does not exist until `open_run` mints it. The corrected
order is recorded in `docs/gr32-validation.md` and implemented here
(`GR32-P-001`).

**The session stops after `apply_commit`.** No snapshot and no validation
follows materialization in the same invocation. Observing the workspace after a
governed commit is a separate entry (`PilotSession.observe`), taken after the
owner has advanced the throwaway workspace to the governed revision this one
reports, and what it produces is an observation — never a discharge of a commit
precondition, which `guard:gr31_preconditions_deferred` refuses outright.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import asdict, astuple, dataclass, field, fields
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

from jsonschema import Draft202012Validator

from .artifacts import ArtifactStore
from .authority import REGISTER, role_allows, ts
from .canonical import canonical_json, digest_bytes
from .contracts import SCHEMA as CONTRACT_SCHEMA, new_id, require
from .errors import CapabilityDenied, GovernedRuntimeError, PolicyDenied
from .models import (
    ActorRef,
    Attribution,
    Budget,
    DecisionKind,
    DecisionScope,
    DecisionSubjectKind,
    GovernanceMode,
    MutationOp,
    SnapshotTrigger,
    TerminationReason,
)
from .scope import in_scope
from .store import StateStore, now_ts
from .validation_catalog import ParameterSchema, ValidationOperation

# --- D2: the credential ------------------------------------------------------

#: The credential header and prefix the relay is configured with unless the
#: caller names others. `x-api-key` with an empty prefix is what a
#: key-authenticated Anthropic endpoint expects; `Authorization` with
#: `'Bearer '` remains selectable, and `InferenceRelay` admits exactly those
#: two header spellings (`guard:gr08_credential_header`).
DEFAULT_CREDENTIAL_HEADER = "x-api-key"
DEFAULT_CREDENTIAL_PREFIX = ""

#: The one network policy GR-32 registers a validation operation with. Egress
#: from validation is gated and unavailable in both of its forms (`CLAUDE.md`
#: Known gaps, `GR-09`/`GR-17`); registering anything else here would put a
#: catalog entry on disk whose execution cannot be reached, so the driver
#: refuses rather than registering one.
VALIDATION_NETWORK = "NONE"

#: The worker mutation ops `propose_commit` can express. Its signature takes
#: one `path` and one `content` and derives `CREATE` or `MODIFY` from the base
#: index itself, so these two are the whole supported surface and every other
#: op is refused rather than approximated.
SUPPORTED_OPS = (MutationOp.CREATE, MutationOp.MODIFY)

#: Every `Budget` field, in the model's own order. Read off the existing model
#: rather than listed, so the CLI flags `build_parser` derives from it and the
#: `Budget` `parameters_from` constructs cannot drift from `models.Budget`, and
#: no second budget shape exists (`GR32-F-006`).
BUDGET_FIELDS = tuple(item.name for item in fields(Budget))


def budget_is_supplied(budget) -> bool:
    """Whether `budget` is a `Budget` the owner actually supplied.

    `GR32-F-006`. A pilot's budget is a runtime input, and there is no default
    to fall back on: `None` is absent, a negative or non-numeric field is not a
    budget, and the all-zero `Budget()` is what an unprovisioned project already
    holds — granting it would record a human act that changes nothing, and
    `guard:gr31_budget_initial_only` would read the project as never granted.
    """
    return (isinstance(budget, Budget)
            and all(isinstance(value, (int, float)) and not isinstance(value, bool)
                    and value >= 0 for value in astuple(budget))
            and budget != Budget())


#: The contract's own `Budget` shape, as `stage_contract.schema.json` declares
#: it — the schema `StageContract` is validated against at step 7, not a copy.
CONTRACT_BUDGET = Draft202012Validator(CONTRACT_SCHEMA["$defs"]["Budget"])


def budget_fits_contract(budget) -> bool:
    """Whether `budget` is one step 7's `StageContract` can carry as its ceiling.

    `GR32-R-001`. `Budget.cost_units` is a float and the contract schema types
    every budget field `integer`, so a fractional `cost_units` passed step 1,
    was granted at step 5 and was refused only at step 7 — after a project, a
    ceiling, a budget and a run already existed. This asks the contract's own
    schema before step 2 instead. It changes neither model: the value is
    checked exactly as supplied, never rounded, truncated or normalized, and
    an integral one written as a float (`100.0`) is an integer to the schema
    and passes, as it always has at step 7.
    """
    return isinstance(budget, Budget) and CONTRACT_BUDGET.is_valid(_budget_document(budget))


class OwnerRefused(PolicyDenied):
    """The presenter gave no answer, or gave one that was not offered.

    A `PolicyDenied` rather than a new taxonomy: a step whose human act was
    declined is a step its caller has no authority for, which is what the rest
    of the runtime already says with this class.
    """


class ProposalUnsupported(PolicyDenied):
    """A worker receipt this bounded path cannot express, refused unchanged.

    `propose_commit` takes one path and one string of content. A receipt that
    says anything else — several mutations, a delete, a rename, a mode change,
    bytes that are not text, an outcome that is not a completed one — is
    refused here rather than being narrowed, reshaped or partially applied.
    The receipt is the proposal identity of record, and altering it to fit an
    interface would make the applied revision answer to something the worker
    never proposed.
    """


def credential_is_printable(value: str) -> bool:
    """Whether every character is printable ASCII, per `InferenceRelay`.

    The same predicate as `guard:gr08_credential_value`
    (`inference_relay.py`), asked earlier. Nothing here strips, trims,
    normalizes or repairs: a credential with a trailing newline is a
    misconfigured credential, and silently fixing it would make the runtime
    guess at a secret's real value.
    """
    return bool(value) and all(32 <= ord(c) < 127 for c in value)


def preflight_credential(variable: str, environ: Mapping[str, str]) -> None:
    """Refuse a missing, empty or malformed credential **before** step 12.

    `GR32-P-002`. `configure_inference_relay` consumes the secret grant and the
    single-action approval in one committed transaction and only then calls the
    resolver (`relay_controller.py`), so a resolver that fails leaves two spent
    human acts and nothing configured. GR-32 does not alter that kernel
    ordering; it keeps the ordinary reasons a resolver fails — an unset
    variable, an empty value, a value with a newline in it — from reaching it.
    The sharp edge remains for everything this cannot see, and is documented
    rather than claimed closed.

    Nothing about the value leaves this function: not its content, not its
    length, not a fragment of it. Only the variable's **name**, which the
    caller supplied, appears in a refusal.
    """
    require(variable in environ, f"the credential variable {variable!r} names nothing in this process environment; the pilot's credential is supplied by naming an environment variable, and no value is read from a file, a credential store or a default", PolicyDenied)  # guard:gr32_credential_declared
    value = environ.get(variable) or ""
    require(bool(value), f"the credential variable {variable!r} is set to an empty value; an empty credential is a misconfiguration, not a credential, and is refused before any secret decision is recorded", PolicyDenied)  # guard:gr32_credential_nonempty
    require(credential_is_printable(value), f"the credential in {variable!r} contains a character the relay's credential guard refuses (printable ASCII only, inference_relay.py guard:gr08_credential_value); it is refused unchanged rather than stripped, trimmed or normalized", PolicyDenied)  # guard:gr32_credential_printable


# --- the presentation boundary ----------------------------------------------


#: The two answers every governed act below offers. A decision must choose an
#: offered option (`guard:decision_option_membership`), so the options are
#: named once here rather than at each of the fourteen call sites.
APPROVE_OPTION = "APPROVE"
REFUSE_OPTION = "REFUSE"
OPTIONS = (APPROVE_OPTION, REFUSE_OPTION)


@dataclass(frozen=True)
class OwnerRequest:
    """Exactly what is being put to the human, for one act.

    `options` is the closed set of answers; `detail` is what the act would do,
    in full, so the answer is an answer to this act and not to a category of
    acts. Carries no credential and no environment value: what a human needs
    to decide whether to open a relay is the origin and the secret's logical
    name, never the secret.
    """

    step: int
    act: str
    question: str
    options: tuple
    subject_kind: str
    subject_id: str
    #: The one option that authorizes. Every other offered option, and no
    #: answer at all, refuses: there is no option that means "proceed anyway".
    approving: str = APPROVE_OPTION
    detail: Mapping[str, object] = field(default_factory=dict)

    def document(self) -> dict:
        return {
            "step": self.step,
            "act": self.act,
            "question": self.question,
            "options": list(self.options),
            "approving": self.approving,
            "subject_kind": self.subject_kind,
            "subject_id": self.subject_id,
            "detail": dict(self.detail),
        }


@dataclass(frozen=True)
class OwnerAnswer:
    """One human's answer to one `OwnerRequest`.

    `decided_by` is the principal the answer is attributed to. It comes back
    from the presenter rather than being filled in by the driver: the driver
    knows which principal it *asked*, which is not evidence of who answered.
    """

    chosen: str
    justification: str
    decided_by: ActorRef
    signature: Optional[str] = None


#: A presenter is shown one request and returns one answer, or `None`. `None`
#: is a refusal — of this act, now — and is never read as "no opinion", never
#: retried and never defaulted.
OwnerPresenter = Callable[[OwnerRequest], Optional[OwnerAnswer]]

class ConsoleOwnerPresenter:
    """A presenter that asks the person at the terminal, and nothing else.

    Prints the request as JSON — the whole of it, so what is authorized is what
    is shown — and reads one line. Anything but the approving option, including
    end of input, is a refusal. It fabricates nothing: a closed stdin answers
    `None`, which stops the session, rather than defaulting to approval.
    """

    def __init__(self, decided_by: ActorRef, *, stream=None, output=None):
        self.decided_by = decided_by
        self._stream = stream
        self._output = output

    def __call__(self, request: OwnerRequest) -> Optional[OwnerAnswer]:
        import sys

        stream = self._stream or sys.stdin
        output = self._output or sys.stdout
        print(canonical_json(request.document()).decode(), file=output, flush=True)
        print(f"{request.act}: type {APPROVE_OPTION} to authorize, anything else to refuse.",
              file=output, flush=True)
        line = stream.readline()
        if line.strip() != APPROVE_OPTION:
            return None
        return OwnerAnswer(chosen=APPROVE_OPTION, decided_by=self.decided_by,
                           justification=f"owner authorized {request.act} at the console")


# --- the report -------------------------------------------------------------


@dataclass
class StepOutcome:
    """One step: what was asked, what happened, and what identifies it."""

    step: int
    act: str
    result: str
    decision_id: Optional[str] = None
    identity: Mapping[str, str] = field(default_factory=dict)
    refusal_type: Optional[str] = None
    refusal_text: Optional[str] = None
    detail: Mapping[str, object] = field(default_factory=dict)

    def document(self) -> dict:
        return {
            "step": self.step,
            "act": self.act,
            "result": self.result,
            "decision_id": self.decision_id,
            "identity": dict(sorted(self.identity.items())),
            "refusal_type": self.refusal_type,
            "refusal_text": self.refusal_text,
            "detail": dict(sorted(self.detail.items())),
        }


@dataclass
class DriverReport:
    """The deterministic record of one driver invocation.

    Deterministic in shape, not in content: the same sequence produces the same
    keys in the same order, and every value is JSON-capable. No credential, no
    environment value and no file content taken from outside the workspace ever
    reaches it — `parameters` carries the credential variable's *name* because
    the name is configuration the owner supplied, and carries no value read
    from it.
    """

    entry: str
    parameters: Mapping[str, object]
    steps: list = field(default_factory=list)
    state: str = "NOT_STARTED"
    project_id: Optional[str] = None
    run_id: Optional[str] = None
    contract_id: Optional[str] = None
    materialized_revision: Optional[str] = None
    stopped_at: Optional[int] = None
    stopped_because: Optional[str] = None
    observational: bool = False

    def document(self) -> dict:
        return {
            "entry": self.entry,
            "state": self.state,
            "observational": self.observational,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "contract_id": self.contract_id,
            "materialized_revision": self.materialized_revision,
            "stopped_at": self.stopped_at,
            "stopped_because": self.stopped_because,
            "parameters": dict(sorted(self.parameters.items())),
            "steps": [step.document() for step in self.steps],
        }


# --- D5: every pilot-specific value is an input ------------------------------


@dataclass(frozen=True)
class ValidationPlan:
    """A catalog operation to register and bind, supplied by the caller.

    `network` is a field so the refusal below has something to refuse. It
    defaults to the only value GR-32 registers and there is no parameter,
    flag or combination that makes an egress-bearing validation reachable.
    """

    spec_id: str
    operation_id: str
    version: str
    argv: tuple
    cwd: str
    timeout_ms: int = 60000
    parameters: Mapping[str, ParameterSchema] = field(default_factory=dict)
    values: Mapping[str, object] = field(default_factory=dict)
    network: str = VALIDATION_NETWORK

    def document(self) -> dict:
        return {
            "spec_id": self.spec_id,
            "operation": f"{self.operation_id}@{self.version}",
            "network": self.network,
            "cwd": self.cwd,
            "timeout_ms": self.timeout_ms,
        }


@dataclass(frozen=True)
class PilotParameters:
    """Everything about *this* pilot, and nothing compiled in.

    `src/` holds no pilot sandbox path, no pilot database path, no pilot base
    revision, no objective and no target path. Two different parameter sets
    drive two different compositions through the same code, which is what
    makes this a runtime rather than one pilot with a configuration file
    (`D5`).
    """

    workspace_root: str
    governance_root: str
    provider: str
    # Everything below is the pilot half. `observe` and `resume` compose a
    # runtime and observe it; they need none of it, so a parameter set built
    # for them leaves these empty and `run()` refuses it (`PILOT_FIELDS`).
    project_name: str = ""
    project_slug: str = ""
    objective: str = ""
    allowed_paths: tuple = ()
    inference_origin: str = ""
    secret_name: str = ""
    secret_env_var: str = ""
    worker_role: str = ""
    capability_request: tuple = ()
    prompt: str = ""
    commit_message: str = ""
    credential_header: str = DEFAULT_CREDENTIAL_HEADER
    credential_prefix: str = DEFAULT_CREDENTIAL_PREFIX
    base_revision: Optional[str] = None
    excluded_paths: tuple = ()
    # `GR32-F-006`: no compiled budget. `None` is "not supplied", and `run()`
    # refuses it at step 1 (`guard:gr32_budget_supplied`).
    budget: Optional[Budget] = None
    deadline_ms: int = 3600000
    # `GR32-F-005`: mandatory for the pilot entry. `None` is refused at step 1
    # (`guard:gr32_validation_plan_required`); `observe` and `resume` need none.
    validation: Optional[ValidationPlan] = None

    @property
    def ceiling(self) -> frozenset:
        """Exactly what this pilot needs: its request, plus `secret.read`.

        Derived rather than listed, so a narrower request narrows the ceiling
        with it. `secret.read` is the one addition: the inference relay is
        opened under it (`guard:gr08_secret_grant` reads the project ceiling),
        and it is never a worker capability — `capability_request` is refused
        if it names it.
        """
        return frozenset(self.capability_request) | {"secret.read"}

    @property
    def activation_grants(self) -> frozenset:
        """The requested capabilities no role default can confer.

        Read off the register rather than listed: a capability whose admissible
        grantors include `ROLE_DEFAULT` is granted by the role, and asking a
        human to grant it as well would spend an act on nothing. What is left
        is what the activation grant decision must actually cover.
        """
        return frozenset(
            capability for capability in self.capability_request
            if "ROLE_DEFAULT" not in REGISTER.get(capability, ("NEVER", ()))[1])

    def document(self) -> dict:
        """The parameters, for the report. Names only, never values read."""
        return {
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            "objective": self.objective,
            "allowed_paths": list(self.allowed_paths),
            "excluded_paths": list(self.excluded_paths),
            "workspace_root": self.workspace_root,
            "governance_root": self.governance_root,
            "provider": self.provider,
            "inference_origin": self.inference_origin,
            "secret_name": self.secret_name,
            # The variable's NAME. Its value is read once, in step 12's
            # resolver closure, and reaches no report, event or artifact.
            "secret_env_var": self.secret_env_var,
            "credential_header": self.credential_header,
            "credential_prefix": self.credential_prefix,
            "worker_role": self.worker_role,
            "capability_request": sorted(self.capability_request),
            "ceiling": sorted(self.ceiling),
            "activation_grants": sorted(self.activation_grants),
            "base_revision": self.base_revision,
            # The budget the owner asked for, as supplied. A request, not a
            # grant: step 5 records the owner's decision on it.
            "budget": _budget_document(self.budget) if isinstance(self.budget, Budget) else None,
            "validation": self.validation.document() if self.validation else None,
        }


# --- D1: the composition root's concrete names -------------------------------


#: The fields the pilot entry needs and the observation entries do not. A
#: parameter set built for `observe` or `resume` carries the composition half
#: and leaves these empty; `run()` refuses such a set rather than walking the
#: sequence with a blank objective and an empty scope.
PILOT_FIELDS = ("project_name", "project_slug", "objective", "allowed_paths",
                "capability_request", "worker_role", "prompt", "commit_message",
                "inference_origin", "secret_name", "secret_env_var")


def parameters_are_complete(parameters: "PilotParameters") -> bool:
    """Whether this parameter set can drive the whole sequence."""
    return all(getattr(parameters, field) for field in PILOT_FIELDS)


def build_provider(name, *, journal_dir, read_artifact, transport=None):
    """Construct the selected provider. The one place adapters are named.

    A transport may be supplied by the caller; where it is not, the CLI
    adapters take the kernel's sandboxed process transport. Nothing here is a
    registry or a plugin layer: it is three names and a mapping, which is what
    "the composition root may name concrete adapters" means (`D1`).
    """
    from .adapters.claude_code import ClaudeCodeProvider
    from .adapters.codex import CodexProvider
    from .adapters.fake_provider import FakeProvider

    journal_dir = Path(journal_dir)
    if name == "fake":
        return FakeProvider(journal_dir)
    kinds = {"claude-code": ClaudeCodeProvider, "codex": CodexProvider}
    require(name in kinds, f"unknown provider {name!r}: the composition root builds one of {sorted(('fake', *kinds))}", PolicyDenied)  # guard:gr32_known_provider
    if transport is None:
        from .adapters.relay_process import WorkerRelayTransport
        import shutil

        executable = shutil.which(name.removesuffix("-code"))
        require(executable is not None, f"provider {name!r} needs its executable on PATH; none was found", PolicyDenied)  # guard:gr32_provider_executable
        transport = WorkerRelayTransport(executable)
    return kinds[name](journal_dir, transport=transport, read_artifact=read_artifact)


# --- D-proposal: the worker receipt is the proposal identity of record -------


@dataclass(frozen=True)
class ProposalMapping:
    """One worker mutation, expressed in `propose_commit`'s own terms.

    `path` and `content` are the two arguments that interface takes. `digest`
    is the artifact identity the receipt named, carried through so the report
    can say which proposed artifact became which revision. `op` and
    `before_digest` are the worker's own claims about the base, preserved
    rather than dropped (`GR32-F-003`): `map_proposal` has already proved them
    against the governed base, so the operation `propose_commit` derives is the
    one the worker proposed. `propose_commit` is not widened to accept anything
    else.
    """

    path: str
    content: str
    digest: str
    op: str
    before_digest: Optional[str]

    def document(self) -> dict:
        return {"path": self.path, "op": self.op, "before_digest": self.before_digest,
                "content_digest": self.digest,
                "content_bytes": len(self.content.encode("utf-8"))}


def is_utf8(payload: bytes) -> bool:
    """Whether `payload` is UTF-8 text.

    A predicate, not a raiser, so the refusal above is one deletable line
    (`CLAUDE.md` Tooling): a `try`/`except` at the guard site would orphan its
    body under `bin/mutate` and report ERROR, which proves nothing about
    whether the guard is tested.
    """
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def map_proposal(receipt, read_artifact, *, scope_include, scope_exclude,
                 base_index) -> ProposalMapping:
    """The receipt's single supported mutation, or a refusal naming why.

    The receipt is the proposal identity of record: the path comes from it and
    the content comes from the artifact its `after_ref` names, verified to
    re-digest to that identity rather than trusted to. Everything the bounded
    path cannot express is refused as itself — never narrowed to the first
    mutation, never a delete turned into an empty file, never bytes coerced
    past a decoder. `read_artifact` is a parameter so the verification is a
    verification: a store that answered with different bytes is caught here.

    `base_index` is the governed base `propose_commit` will commit onto — path
    to content digest, as `Repository.file_index` reports it (`GR32-F-003`).
    `propose_commit` derives `CREATE` or `MODIFY` from that index and ignores
    the worker's claim, so a worker that said `CREATE` over an existing file,
    or `MODIFY` against content it never saw, would otherwise be committed as
    a `MODIFY` it did not propose. The worker's `op` and `before_digest` are
    checked against the base here instead and refused on any disagreement;
    nothing is translated between `CREATE` and `MODIFY`.
    """
    require(receipt.attribution is Attribution.DIRECT, f"receipt {receipt.receipt_id} carries attribution {receipt.attribution.value}: a reconciled outcome is what recovery observed, not a proposal this session may act on, and it stops for the owner", ProposalUnsupported)  # guard:gr32_proposal_direct
    require(receipt.termination_reason is TerminationReason.COMPLETED, f"receipt {receipt.receipt_id} terminated {receipt.termination_reason.value}: only a COMPLETED worker outcome carries a proposal, and a refused, failed, timed-out or cancelled one is reported rather than mined for mutations", ProposalUnsupported)  # guard:gr32_proposal_completed
    require(not receipt.capability_violations_attempted and not receipt.scope_breaches_attempted, f"receipt {receipt.receipt_id} records {len(receipt.capability_violations_attempted)} attempted capability violation(s) and {len(receipt.scope_breaches_attempted)} scope breach(es); a proposal from a worker that reached for what it was not granted stops for the owner", ProposalUnsupported)  # guard:gr32_proposal_clean
    require(len(receipt.proposed_mutations) == 1, f"receipt {receipt.receipt_id} proposes {len(receipt.proposed_mutations)} mutations; propose_commit expresses exactly one path and one content, and GR-32 refuses the rest rather than widening it or applying a prefix of them", ProposalUnsupported)  # guard:gr32_proposal_single
    mutation = receipt.proposed_mutations[0]
    require(mutation.op in SUPPORTED_OPS, f"mutation op {mutation.op.value} is outside the bounded GR-32 path; propose_commit derives CREATE or MODIFY from the base index and expresses no delete, rename or mode change", ProposalUnsupported)  # guard:gr32_proposal_op
    require(mutation.rename_to is None, f"mutation on {mutation.path!r} carries rename_to={mutation.rename_to!r}; a rename is two paths and propose_commit takes one, so it is refused rather than half-applied", ProposalUnsupported)  # guard:gr32_proposal_rename
    require(mutation.mode is None, f"mutation on {mutation.path!r} carries mode={mutation.mode!r}; propose_commit writes content and never a file mode, so a mode change is refused rather than dropped", ProposalUnsupported)  # guard:gr32_proposal_mode
    require(mutation.after_ref is not None, f"mutation on {mutation.path!r} has no after_ref; the content of a proposal is the artifact the receipt names, and a mutation naming none proposes nothing this path can apply", ProposalUnsupported)  # guard:gr32_proposal_after_ref
    require(in_scope(mutation.path, tuple(scope_include), tuple(scope_exclude)), f"mutation path {mutation.path!r} is outside the activated contract scope {list(scope_include)!r} minus {list(scope_exclude)!r}; a proposal that left its scope stops for the owner", ProposalUnsupported)  # guard:gr32_proposal_scope
    require(mutation.op is not MutationOp.CREATE or mutation.path not in base_index, f"the worker proposed CREATE for {mutation.path!r}, which already exists at the governed base; propose_commit would commit it as a MODIFY the worker never proposed, so the operation mismatch is refused rather than translated", ProposalUnsupported)  # guard:gr32_proposal_create_absent
    require(mutation.op is not MutationOp.CREATE or mutation.before_digest is None, f"the worker proposed CREATE for {mutation.path!r} while claiming a prior content identity {mutation.before_digest!r}; a CREATE has no before state, and a proposal that contradicts itself is refused", ProposalUnsupported)  # guard:gr32_proposal_create_before
    require(mutation.op is not MutationOp.MODIFY or mutation.path in base_index, f"the worker proposed MODIFY for {mutation.path!r}, which is absent at the governed base; propose_commit would commit it as a CREATE the worker never proposed, so the operation mismatch is refused rather than translated", ProposalUnsupported)  # guard:gr32_proposal_modify_present
    require(mutation.op is not MutationOp.MODIFY or mutation.before_digest == base_index.get(mutation.path), f"the worker's before_digest {mutation.before_digest!r} for {mutation.path!r} is not the governed base content {base_index.get(mutation.path)!r}; a MODIFY written against content that is missing, stale or wrong is refused rather than applied over what the worker never saw", ProposalUnsupported)  # guard:gr32_proposal_modify_before
    payload = read_artifact(mutation.after_ref.digest)
    require(digest_bytes(payload) == mutation.after_ref.digest, f"the artifact read for {mutation.path!r} does not re-digest to the identity the receipt named ({mutation.after_ref.digest}); the proposal is the receipt, so content that does not match it is refused rather than committed", ProposalUnsupported)  # guard:gr32_proposal_digest
    require(is_utf8(payload), f"the artifact proposed for {mutation.path!r} is not UTF-8 text; propose_commit takes str content, and GR-32 refuses rather than decoding with a replacement character and committing something the worker did not propose", ProposalUnsupported)  # guard:gr32_proposal_utf8
    return ProposalMapping(path=mutation.path, content=payload.decode("utf-8"),
                           digest=mutation.after_ref.digest, op=mutation.op.value,
                           before_digest=mutation.before_digest)


# --- the session -------------------------------------------------------------


class PilotSession:
    """One process, one controller epoch, one relay, one ordered sequence.

    The relay is configured in memory and the controller epoch fences worker
    effects, so steps 12–16 are one uninterrupted session by construction: two
    CLI processes are two epochs and two relays, never one session continued.
    A restart is `resume()` — a new epoch, `recover(project_id)`, a report, and
    a stop for the owner — and never an automatic continuation of a sequence
    whose relay died with the process that held it.

    Every step refuses, reports and stops. Nothing here retries, substitutes,
    resets, rolls back a repository effect that already landed, or continues
    past a typed refusal; `run()` records the step and re-raises the kernel's
    own error, so the caller sees the refusal that happened rather than a
    driver's paraphrase of it, and `report` holds the record either way.
    """

    def __init__(self, controller, parameters, present, *, owner,
                 environ=None, commit_preconditions=None, entry="pilot"):
        self.controller = controller
        self.parameters = parameters
        self.owner = owner
        self._present = present
        self._environ = os.environ if environ is None else environ
        self._commit_preconditions = commit_preconditions
        self.report = DriverReport(entry=entry, parameters=parameters.document())
        self.project_id = None
        self.run_id = None
        self.contract = None
        self.receipt = None
        self.intent = None
        self._activation_grant = None
        self._activation_approval = None

    # -- the human boundary -------------------------------------------------

    def _ask(self, request: OwnerRequest) -> OwnerAnswer:
        """Put one act to the presenter and take its answer, or stop.

        Three separable refusals, because they are three different things
        going wrong: nothing came back, something came back that was never
        offered, and the owner declined. None of them is recoverable here and
        none of them has a default.
        """
        answer = self._present(request)
        require(isinstance(answer, OwnerAnswer), f"step {request.step}: the owner was asked to authorize {request.act} and returned no answer; None is a refusal and this session stops rather than proceeding on a default", OwnerRefused)  # guard:gr32_owner_answer
        require(answer.chosen in request.options, f"step {request.step}: the owner's answer to {request.act} is {answer.chosen!r}, which was not among the options offered {list(request.options)!r}; an answer that was never offered is not an answer the owner gave", OwnerRefused)  # guard:gr32_owner_option
        require(answer.chosen == request.approving, f"step {request.step}: the owner chose {answer.chosen!r} over {request.approving!r} for {request.act}; the act is refused and the session stops for the owner", OwnerRefused)  # guard:gr32_owner_approves
        return answer

    def _evidence(self, request: OwnerRequest):
        """What the presentation carried, stored as the artifact it is.

        `HD-INV-2`: an uninformed approval discharges nothing, and
        `_record_decision` refuses an empty `evidence_shown`. The evidence is
        the request document — the act, its subject and its detail, exactly as
        shown — rather than a label naming something the human never saw.
        """
        return self.controller.store.store_artifact(
            canonical_json(request.document()), media_type="application/json")

    def _decide(self, step, act, *, kind, subject_kind, subject_id, scope, question,
                detail, grants=(), options=OPTIONS, approving=APPROVE_OPTION):
        """Ask, then record one `HumanDecision`. One decision, one act.

        The recorded decision carries the presenter's own `chosen`,
        `justification`, principal and signature. Nothing is substituted, and
        the caller consumes this decision on the single act it was asked for:
        a decision is never presented twice.
        """
        request = OwnerRequest(step=step, act=act, question=question, options=options,
                               approving=approving, subject_kind=subject_kind.value,
                               subject_id=subject_id, detail=detail)
        answer = self._ask(request)
        return self.controller.record_decision(
            self.project_id, decision_kind=kind, subject_kind=subject_kind,
            subject_id=subject_id, scope=scope, question=question,
            options_offered=request.options, chosen=answer.chosen,
            justification=answer.justification, decided_by=answer.decided_by,
            signature=answer.signature, evidence_shown=(self._evidence(request),),
            grants=frozenset(grants))

    # -- the record ---------------------------------------------------------

    def _step(self, step, act, body, **detail):
        """Run one step, record it, and stop the session if it refuses."""
        outcome = StepOutcome(step=step, act=act, result="NOT_ATTEMPTED", detail=detail)
        self.report.steps.append(outcome)
        try:
            value = body(outcome)
        except GovernedRuntimeError as exc:
            record_refusal(self.report, outcome, exc)
            raise
        outcome.result = "OK"
        return value

    def documented_report(self) -> dict:
        """The report as JSON-capable data, proven free of the credential.

        The guard is the runtime's own `SecretGuard`, which holds a salted
        fingerprint of whatever the relay resolved. Asking it here means the
        claim "no credential reaches the report" is checked against the actual
        secret rather than asserted in a docstring.
        """
        document = self.report.document()
        self.controller.secret_guard.check(document)  # guard:gr32_report_secret_free
        return document

    # -- D2: the credential, read once and held only in the closure ---------

    def _resolver(self):
        """The resolver `configure_inference_relay` requires, and nothing more.

        The value is read inside this closure, at the moment the kernel asks
        for it, and is never stored on the session, the report or the
        parameters. The name is bound too: a resolver that answered for any
        name would hand the credential to a second, unapproved secret.
        """
        variable = self.parameters.secret_env_var
        expected = self.parameters.secret_name
        environ = self._environ

        def resolve(name):
            require(name == expected, f"the relay asked to resolve {name!r}; the approved secret for this session is {expected!r}", CapabilityDenied)  # guard:gr32_secret_name_binding
            return environ[variable]

        return resolve

    # -- the contract this pilot asks for -----------------------------------

    def _contract_document(self, stage_id):
        """The `StageContract` for this run, built from the parameters.

        `required_validations` is empty and no commit review or validation
        precondition is bound: `B6` and `B7` are open, and
        `guard:gr31_preconditions_deferred` refuses a non-empty precondition
        rather than discharging one hollowly. GR-32 neither works around that
        nor weakens it.
        """
        parameters = self.parameters
        require("secret.read" not in parameters.capability_request, "secret.read is a HUMAN-class capability the kernel holds to open the relay; a worker never receives it, and a contract that requested it would be asking for the credential itself", PolicyDenied)  # guard:gr32_secret_not_worker_capability
        require(all(role_allows(c, parameters.worker_role) for c in parameters.capability_request), f"worker role {parameters.worker_role!r} does not admit every requested capability {sorted(parameters.capability_request)!r} (authority.ROLE_TABLE); the role is named rather than defaulted, and a role that cannot hold the request is refused here instead of silently losing capabilities at activation", PolicyDenied)  # guard:gr32_role_admits_request
        return dict(
            schema_version="0.1.0", contract_id=new_id(), project_id=self.project_id,
            stage_id=stage_id, contract_version=1, status="DRAFT",
            objective=parameters.objective,
            scope_include=list(parameters.allowed_paths),
            scope_exclude=list(parameters.excluded_paths),
            acceptance_criteria=[dict(criterion_id="review", text=parameters.objective,
                                      kind="JUDGMENTAL", verifier_ref="review",
                                      mandatory=True, waivable=False)],
            required_validations=[],
            required_reviews=[dict(spec_id="review", reviewer_kind="HUMAN",
                                   independence_required="INDEPENDENT",
                                   blocking_severity="BLOCKER", quorum=1)],
            prohibited_actions=[],
            capability_request=list(parameters.capability_request),
            worker_role=parameters.worker_role,
            budget_ceiling=_budget_document(parameters.budget),
            deadline_ms=parameters.deadline_ms, escalation_triggers=[],
            rollback_policy="REVERT_COMMITS", evidence_retention_class="STANDARD",
            authored_by=dict(actor_kind="RUNTIME", actor_id="gruntime.driver",
                             auth_method="NONE"),
            authored_at=ts(now_ts()),
        )

    # -- entry: the supervised sequence, steps 1-16 --------------------------

    def run(self) -> DriverReport:
        """Walk steps 1–16 and stop.

        Step 1 is the caller's composition (`open_runtime`); what `run()`
        records as step 1 is the rest of it, the refusal of a parameter set that
        cannot drive the sequence — incomplete, without a supplied budget, or
        without a validation plan — before any transition.

        The sequence is the frozen one, in the one order the code admits:
        create, start, provision the ceiling, provision the budget, confirm and
        open the run, author the contract against *that run's* `stage_id`,
        grant, approve, activate, bind the validations, open the relay,
        confirm and invoke, map the proposal, confirm and authorize, apply.

        And then stop. Nothing observes the workspace after materialization
        here: the revision this returns is the boundary, and the owner advances
        the throwaway workspace to it before `observe()` is a truthful thing to
        do.
        """
        self.report.state = "RUNNING"
        parameters = self.parameters
        controller = self.controller

        def compose(outcome):
            # Step 1's remainder: the runtime is composed, and what is left is
            # to refuse a parameter set that cannot drive the sequence — as a
            # recorded, stopped step (`GR32-F-001`), before any transition.
            require(parameters_are_complete(parameters), "this parameter set carries only the composition half — the workspace, the governance root and the provider — and an observation or a restart is all it can drive; running the sequence needs the objective, the scope, the request, the role, the prompt, the commit message, the origin and the credential variable the owner chose", PolicyDenied)  # guard:gr32_pilot_parameters_complete
            require(budget_is_supplied(parameters.budget), f"the pilot's budget is a runtime input and none admissible was supplied ({parameters.budget!r}); every Budget field {list(BUDGET_FIELDS)} must be given explicitly, non-negative and not all zero, and the driver chooses no default for it", PolicyDenied)  # guard:gr32_budget_supplied
            require(budget_fits_contract(parameters.budget), f"the pilot's budget {_budget_document(parameters.budget)!r} does not fit the StageContract budget shape (stage_contract.schema.json $defs/Budget: every field a non-negative integer); step 7 would refuse it after a project, a ceiling, a budget and a run already existed, so it is refused here, before any transition, and is not rounded, truncated or normalized", PolicyDenied)  # guard:gr32_budget_contract_shape
            require(isinstance(parameters.validation, ValidationPlan), "the pilot sequence registers and binds a network='NONE' validation operation at step 11, and no validation plan was supplied; a governed revision is not materialized without one", PolicyDenied)  # guard:gr32_validation_plan_required
            outcome.detail = {"provider": parameters.provider,
                              "budget": _budget_document(parameters.budget),
                              "validation": parameters.validation.document()}

        self._step(1, "runtime.compose", compose)

        def create(outcome):
            self.project_id = controller.create_project(
                name=parameters.project_name, slug=parameters.project_slug,
                workspace_root=parameters.workspace_root, approved_by=self.owner,
                present=self._creation_presenter(), initial_mode=GovernanceMode.SUPERVISED,
                justification="the owner approved taking this workspace under governance")
            self.report.project_id = self.project_id
            outcome.identity = {"project_id": self.project_id}
            return self.project_id

        self._step(2, "project.create", create, workspace_root=parameters.workspace_root)

        self._step(3, "controller.start",
                   lambda outcome: outcome.identity.update(
                       controller_epoch=str(controller.start(self.project_id))))

        def ceiling(outcome):
            decision = self._decide(
                4, "project.ceiling.set", kind=DecisionKind.GRANT_CAPABILITY,
                subject_kind=DecisionSubjectKind.PROJECT, subject_id=self.project_id,
                scope=DecisionScope.PROJECT, grants=parameters.ceiling,
                question=f"Bound project {self.project_id} to the capability ceiling {sorted(parameters.ceiling)}?",
                detail={"ceiling": sorted(parameters.ceiling)})
            outcome.decision_id = decision.decision_id
            controller.set_capability_ceiling(self.project_id, ceiling=parameters.ceiling,
                                              decision_id=decision.decision_id)

        self._step(4, "project.ceiling.set", ceiling, ceiling=sorted(parameters.ceiling))

        def budget(outcome):
            decision = self._decide(
                5, "budget.grant", kind=DecisionKind.EXTEND_BUDGET,
                subject_kind=DecisionSubjectKind.PROJECT, subject_id=self.project_id,
                scope=DecisionScope.PROJECT,
                question=f"Grant project {self.project_id} its initial budget?",
                detail={"budget": _budget_document(parameters.budget)})
            outcome.decision_id = decision.decision_id
            controller.grant_project_budget(self.project_id, budget=parameters.budget,
                                            decision_id=decision.decision_id)

        self._step(5, "budget.grant", budget, budget=_budget_document(parameters.budget))

        def open_run(outcome):
            # Row 5-1's subject is the PROJECT: the run does not exist yet, so
            # there is nothing else the owner could have been shown. Recorded
            # immediately before the allocation it discharges, with no
            # observation between the two (`HD-INV-4`).
            decision = self._decide(
                6, "run.start", kind=DecisionKind.APPROVE,
                subject_kind=DecisionSubjectKind.PROJECT, subject_id=self.project_id,
                scope=DecisionScope.PROJECT,
                question=f"Open a governed run on project {self.project_id} for: {parameters.objective}?",
                detail={"row": "5-1", "objective": parameters.objective})
            outcome.decision_id = decision.decision_id
            self.run_id = controller.open_run(self.project_id,
                                              confirmation_id=decision.decision_id)
            self.report.run_id = self.run_id
            outcome.identity = {"run_id": self.run_id}

        self._step(6, "run.start", open_run, row="5-1")

        def author(outcome):
            stage_id = controller.store.get_run(self.run_id).stage_id
            # `GR32-P-001`: the historical plan authors the contract before the
            # run. It cannot: `guard:gr06_run_identity` binds the contract to
            # `run.stage_id`, which `open_run` mints. The plan is not edited;
            # the corrected order is recorded in `docs/gr32-validation.md`.
            self.contract = controller.author_contract(self._contract_document(stage_id))
            self.report.contract_id = self.contract.contract_id
            outcome.identity = {"contract_id": self.contract.contract_id,
                                "stage_id": stage_id}

        self._step(7, "contract.author", author, capability_request=sorted(parameters.capability_request))

        def grant(outcome):
            # A *separate* decision from the ceiling's, and not the same act:
            # the ceiling bounds what may ever be conferred and this confers.
            # The ceiling decision was consumed by step 4 precisely so it
            # cannot also stand here (`human_covers`' VALID conjunct).
            self._activation_grant = self._decide(
                8, "capability.grant", kind=DecisionKind.GRANT_CAPABILITY,
                subject_kind=DecisionSubjectKind.PROJECT, subject_id=self.project_id,
                scope=DecisionScope.PROJECT, grants=parameters.activation_grants,
                question=f"Grant this run the capabilities no role default confers: {sorted(parameters.activation_grants)}?",
                detail={"grants": sorted(parameters.activation_grants)})
            outcome.decision_id = self._activation_grant.decision_id

        self._step(8, "capability.grant", grant, grants=sorted(parameters.activation_grants))

        def approve(outcome):
            self._activation_approval = self._decide(
                9, "contract.approve", kind=DecisionKind.APPROVE,
                subject_kind=DecisionSubjectKind.CONTRACT,
                subject_id=self.contract.contract_id, scope=DecisionScope.SINGLE_ACTION,
                question=f"Activate contract {self.contract.contract_id} on run {self.run_id}?",
                detail={"row": "6-2", "objective": parameters.objective,
                        "scope_include": list(parameters.allowed_paths)})
            outcome.decision_id = self._activation_approval.decision_id

        self._step(9, "contract.approve", approve, row="6-2")

        def activate(outcome):
            record = controller.activate_contract(
                self.contract.contract_id, self.run_id,
                decision_ids=(self._activation_grant.decision_id,),
                approval_id=self._activation_approval.decision_id)
            outcome.identity = {"activation_id": record.activation_id}
            outcome.detail = {"granted": sorted(record.granted_capabilities),
                              "denied": dict(sorted(record.denied_capabilities.items()))}

        self._step(10, "contract.activate", activate)

        self._step(11, "validation.bind", self._bind_validations)
        self._step(12, "secret.read", self._configure_relay,
                   origin=parameters.inference_origin, secret_name=parameters.secret_name,
                   credential_header=parameters.credential_header)
        self._step(13, "worker.invoke", self._invoke, row="7.2-1")
        self._step(14, "commit.propose", self._propose)
        self._step(15, "commit.authorize", self._authorize, row="7.4-4")
        self._step(16, "commit.apply", self._apply)

        # Step 17: stop. No snapshot, no validation, no further transition.
        self.report.state = "MATERIALIZED"
        self.report.stopped_at = 16
        self.report.stopped_because = (
            "the governed revision is materialized; observation and validation are a "
            "separate driver entry, taken after the owner advances the workspace to it")
        return self.report

    def _creation_presenter(self):
        """Adapt the genesis presentation boundary to the owner presenter.

        The observation is shown whole and the choice comes back from the
        presenter. The `snapshot_id` the response names is the one that was
        presented — a binding, not an answer — and the principal is checked
        against the one whose approval `create_project` will record, because
        `_genesis` attributes the approval to `approved_by` and an answer given
        by somebody else would be recorded under the wrong name.
        """
        from .controller import CREATE_CHOICE, CreationResponse

        def present(observation):
            request = OwnerRequest(
                step=2, act="project.create", question=observation.question,
                options=tuple(observation.options_offered),
                # The kernel's own name for the approving choice, not the
                # first option positionally: `guard:creation_response_approves`
                # compares against `CREATE_CHOICE`, and a driver that decided
                # which option approves by its position would be a second
                # opinion about the same question.
                approving=CREATE_CHOICE,
                subject_kind="PROJECT", subject_id=observation.project_id,
                detail={"workspace_root": observation.workspace_root,
                        "initial_mode": observation.initial_mode.value,
                        "snapshot_id": observation.snapshot_id,
                        "evidence_shown": [ref.digest for ref in observation.evidence_shown]})
            answer = self._ask(request)
            require(answer.decided_by == self.owner, f"the creation answer is attributed to {answer.decided_by.actor_id!r}, and {self.owner.actor_id!r} is the principal this creation records as approver (AX-14); an approval recorded under a name that did not give it is unattributable", OwnerRefused)  # guard:gr32_creation_principal
            return CreationResponse(snapshot_id=observation.snapshot_id,
                                    chosen=answer.chosen, signature=answer.signature)

        return present

    def _bind_validations(self, outcome):
        """Register the operation and pin it to the run. `network='NONE'`.

        Binding is not requesting: `contract.required_validations` is empty,
        and what is pinned here is the run's immutable validation slice, which
        `observe()` may later execute as an observation. Nothing makes an
        `ALLOWLIST` or `ANY` operation reachable — egress from validation is
        gated and has no enforcing adapter in either form.

        `GR32-F-005`: the plan is mandatory, and step 1 has already refused a
        pilot without one, so there is no path on which this step reports `OK`
        with nothing bound.
        """
        plan = self.parameters.validation
        require(plan.network == VALIDATION_NETWORK, f"GR-32 registers validation operations with network={VALIDATION_NETWORK!r} only; {plan.network!r} would need an egress capability at execution, and validation egress is gated with no enforcing adapter in either of its forms (CLAUDE.md Known gaps)", PolicyDenied)  # guard:gr32_validation_network_none
        operation = ValidationOperation(
            operation_id=plan.operation_id, version=plan.version, argv=tuple(plan.argv),
            parameters=dict(plan.parameters), cwd=plan.cwd, env_allowlist=(),
            network=plan.network, timeout_ms=plan.timeout_ms, write_policy="READ_ONLY",
            side_effect_class="READ_ONLY", safe_to_rerun=True)
        self.controller.validation_catalog.register(operation)
        digest = self.controller.bind_validations(
            self.run_id, {plan.spec_id: {"operation": operation.reference,
                                         "parameters": dict(plan.values)}})
        outcome.identity = {"validation_contract_digest": digest}
        outcome.detail = {"bound": [plan.spec_id], "network": plan.network}
        return digest

    def _configure_relay(self, outcome):
        """Step 12. Preflight, then the two secret decisions, then the relay.

        The preflight runs **before** either decision is recorded, and records
        none of its own: `configure_inference_relay` consumes both in a
        committed transaction and only then calls the resolver, so an unset or
        malformed credential reaching that point would spend two human acts on
        a relay that was never opened (`GR32-P-002`).
        """
        parameters = self.parameters
        preflight_credential(parameters.secret_env_var, self._environ)
        grant = self._decide(
            12, "secret.grant", kind=DecisionKind.GRANT_CAPABILITY,
            subject_kind=DecisionSubjectKind.CAPABILITY, subject_id="secret.read",
            scope=DecisionScope.PROJECT, grants=("secret.read",),
            question=f"Grant the kernel secret.read so it can open one inference relay to {parameters.inference_origin}?",
            detail={"origin": parameters.inference_origin,
                    "secret_name": parameters.secret_name,
                    "credential_variable": parameters.secret_env_var,
                    "credential_header": parameters.credential_header})
        approval = self._decide(
            12, "secret.approve", kind=DecisionKind.APPROVE,
            subject_kind=DecisionSubjectKind.CAPABILITY, subject_id="secret.read",
            scope=DecisionScope.SINGLE_ACTION,
            options=(parameters.secret_name, REFUSE_OPTION), approving=parameters.secret_name,
            question=f"Resolve the secret {parameters.secret_name!r} once, for this run only?",
            detail={"origin": parameters.inference_origin,
                    "secret_name": parameters.secret_name,
                    "credential_variable": parameters.secret_env_var})
        outcome.decision_id = approval.decision_id
        outcome.identity = {"secret_grant_id": grant.decision_id,
                            "secret_approval_id": approval.decision_id}
        self.controller.configure_inference_relay(
            self.run_id, origin=parameters.inference_origin,
            secret_name=parameters.secret_name, resolve_secret=self._resolver(),
            grant_decision_id=grant.decision_id, approval_id=approval.decision_id,
            credential_header=parameters.credential_header,
            credential_prefix=parameters.credential_prefix,
            protocol_headers=getattr(type(self.controller.provider), "relay_headers", ()))
        outcome.detail = {"origin": parameters.inference_origin,
                          "credential_header": parameters.credential_header,
                          "credential_prefix": parameters.credential_prefix}

    def _invoke(self, outcome):
        """Step 13. Row 7.2-1's confirmation, then the existing dispatch path.

        The row is `WHEN(FIRST_INVOCATION_OF_RUN, CONFIRM, AUTO)`: the
        confirmation is asked once per run, and this session makes one
        invocation. Recorded immediately before `create_invocation`, which
        consumes it in the same transaction that mints the invocation.
        """
        controller = self.controller
        decision = self._decide(
            13, "worker.invoke", kind=DecisionKind.APPROVE,
            subject_kind=DecisionSubjectKind.RUN, subject_id=self.run_id,
            scope=DecisionScope.RUN,
            question=f"Put a worker to work on run {self.run_id} for: {self.parameters.objective}?",
            detail={"row": "7.2-1", "provider": self.parameters.provider,
                    "objective": self.parameters.objective})
        outcome.decision_id = decision.decision_id
        invocation = controller.create_invocation(
            self.run_id, prompt=self.parameters.prompt.encode("utf-8"),
            provider_id=controller.provider.describe().provider_id,
            confirmation_id=decision.decision_id)
        controller.mark_dispatched(invocation.invocation_id)
        self.receipt = controller.invoke(invocation.invocation_id)
        outcome.identity = {"invocation_id": invocation.invocation_id,
                            "receipt_id": self.receipt.receipt_id}
        outcome.detail = {"termination_reason": self.receipt.termination_reason.value,
                          "attribution": self.receipt.attribution.value,
                          "proposed_mutations": len(self.receipt.proposed_mutations)}

    def _propose(self, outcome):
        """Step 14. The receipt's one mutation, in `propose_commit`'s terms.

        The worker's operation and `before_digest` are checked against the base
        `propose_commit` will commit onto before it is called (`GR32-F-003`),
        so a refusal leaves no `CommitIntent`. The base is read through the
        existing `governed_repo` handle with `create=False`: that is the
        governed worktree once it exists and, before it does, the workspace
        repository whose `HEAD` `ensure_worktree` would create it at — read
        only, with no worktree created and no lease taken on the driver's
        account. `propose_commit` itself is unchanged and not widened.
        """
        governed = self.controller.governed_repo(self.project_id, create=False)
        base_revision = governed.head_revision()
        mapping = map_proposal(
            self.receipt, self.controller.store.artifact_bytes,
            scope_include=self.contract.scope_include,
            scope_exclude=self.contract.scope_exclude,
            base_index=governed.file_index(base_revision))
        self.intent = self.controller.propose_commit(
            self.run_id, path=mapping.path, content=mapping.content,
            message=self.parameters.commit_message,
            preconditions=self._commit_preconditions)
        outcome.identity = {"intent_id": self.intent.intent_id,
                            "operation_token": self.intent.operation_token}
        outcome.detail = dict(mapping.document(),
                              base_revision_id=self.intent.base_revision_id,
                              validated_against=base_revision)

    def _authorize(self, outcome):
        """Step 15. Row 7.4-4, recorded immediately before it is discharged.

        `COMMIT_INTENT` is a snapshot-bound subject and `APPROVE` a
        snapshot-bound kind, so an observation between this decision and
        `authorize_commit` would make it `STALE`. There is none.
        """
        decision = self._decide(
            15, "commit.authorize", kind=DecisionKind.APPROVE,
            subject_kind=DecisionSubjectKind.COMMIT_INTENT, subject_id=self.intent.intent_id,
            scope=DecisionScope.SINGLE_ACTION,
            question=f"Commit intent {self.intent.intent_id} onto {self.intent.target_ref}?",
            detail={"row": "7.4-4", "paths": [m.path for m in self.intent.mutations],
                    "base_revision_id": self.intent.base_revision_id,
                    "message": self.intent.message})
        outcome.decision_id = decision.decision_id
        self.controller.authorize_commit(self.intent.intent_id,
                                         confirmation_id=decision.decision_id)
        outcome.identity = {"intent_id": self.intent.intent_id}

    def _apply(self, outcome):
        """Step 16. The materialization boundary this session reports."""
        receipt = self.controller.apply_commit(self.intent.intent_id)
        self.report.materialized_revision = receipt.revision_id
        outcome.identity = {"receipt_id": receipt.receipt_id,
                            "revision_id": receipt.revision_id}
        outcome.detail = {"verification": receipt.verification.value,
                          "attribution": receipt.attribution.value}
        return receipt

    # -- entry: observation after materialization ---------------------------

    def observe(self, project_id, run_id=None, *, spec_id=None) -> DriverReport:
        """Observe the workspace, and optionally run one bound validation.

        A separate invocation, and explicitly observational: the owner has
        advanced the throwaway workspace to the governed revision the pilot
        entry reported, and what happens here describes that reality. It
        discharges nothing. A commit precondition naming a validation is
        refused by `guard:gr31_preconditions_deferred` whatever this produces,
        because a validation precondition is currently discharged by artifact
        existence rather than by a passing receipt (`B7`) — so a receipt from
        here could "meet" a precondition it never tested. GR-32 does not work
        around that; it keeps the two apart.
        """
        self.project_id, self.run_id = project_id, run_id
        self.report.observational = True
        self.report.project_id = project_id
        self.report.run_id = run_id
        self.report.state = "RUNNING"

        def snapshot(outcome):
            snapshot_id = self.controller.take_snapshot(
                project_id, trigger=SnapshotTrigger.ON_DEMAND)
            record = self.controller.store.get_snapshot(snapshot_id)
            outcome.identity = {"snapshot_id": snapshot_id,
                                "snapshot_hash": record.snapshot_hash}
            outcome.detail = {
                "suspension": self.controller.store.get_project(project_id).suspension.value,
                "discharges": "nothing"}

        self._step(1, "snapshot.take", snapshot)
        if spec_id is not None:
            def validate(outcome):
                receipt = self.controller.execute_validation(run_id, spec_id)
                outcome.identity = {"op_id": receipt.op_id, "receipt_hash": receipt.receipt_hash}
                outcome.detail = {"verdict": receipt.verdict, "exit_code": receipt.exit_code,
                                  "discharges": "nothing"}

            self._step(2, "validation.execute", validate, spec_id=spec_id)
        self.report.state = "OBSERVED"
        self.report.stopped_because = (
            "observation only: no receipt produced here discharges a commit precondition")
        return self.report

    # -- entry: restart -----------------------------------------------------

    def resume(self, project_id) -> DriverReport:
        """A new epoch, `recover`, a report, and a stop for the owner.

        A restart is not a continuation. The relay lived in the memory of the
        process that died and the epoch it invoked under is now fenced, so
        steps 12–16 are never resumed automatically: what this does is find out
        what the previous process left behind and hand that to the owner.
        """
        self.project_id = project_id
        self.report.project_id = project_id
        self.report.state = "RUNNING"

        self._step(1, "controller.start",
                   lambda outcome: outcome.identity.update(
                       controller_epoch=str(self.controller.start(project_id))))

        def recover(outcome):
            result = self.controller.recover(project_id)
            outcome.detail = {
                "invocations_reconciled": sorted(result.invocations_reconciled),
                "intents_reconciled": sorted(result.intents_reconciled),
                "validations_reconciled": sorted(result.validations_reconciled),
                "escalations_raised": sorted(result.escalations_raised),
                "unresolved": sorted(result.unresolved),
                "suspension": self.controller.store.get_project(project_id).suspension.value}

        self._step(2, "recovery.reconcile", recover)
        self.report.state = "RECOVERED"
        self.report.stopped_because = (
            "a restart reports and stops: the relay and the epoch it ran under are gone, "
            "and the owner decides what happens next")
        return self.report


def _budget_document(budget: Budget) -> dict:
    """`Budget` as the contract schema spells it, in a stable key order."""
    return {key: value for key, value in sorted(asdict(budget).items())}


def record_refusal(report: DriverReport, outcome: StepOutcome, exc: GovernedRuntimeError) -> None:
    """Mark `outcome` refused and stop `report` there. The one refusal record.

    Shared by every step and by a composition that refused before a session
    existed (`GR32-F-001`), so a terminated invocation never leaves its report
    `RUNNING` and every refusal reads the same way: which step, which type, in
    the kernel's own words.
    """
    outcome.result = "REFUSED"
    outcome.refusal_type = type(exc).__name__
    outcome.refusal_text = str(exc)
    report.state = "STOPPED"
    report.stopped_at = outcome.step
    report.stopped_because = f"{type(exc).__name__}: {exc}"


# --- step 1: the composition itself ------------------------------------------


def compose_runtime(parameters: PilotParameters, *, transport=None):
    """Open the store, artifacts and repository, and build the provider.

    Step 1 of the sequence, and the whole of what "composition root" means
    here: concrete adapters named in one place, handed to one `Controller`.
    The governance root holds the store, the artifacts, the provider journal,
    the governed worktree and the repository lease — never the workspace, or
    the runtime's own files would read as workspace drift.

    A composition that refuses — an unknown provider, a missing executable, a
    store that will not open — closes what it opened and raises the typed
    refusal, which `drive()` reports as a stopped step 1 (`GR32-F-001`). The
    caller owns the returned controller's store and closes it.
    """
    from .adapters.git_repo import GitRepository
    from .controller import Controller

    root = Path(parameters.governance_root)
    root.mkdir(parents=True, exist_ok=True)
    store = StateStore.open(root / "state.db")
    try:
        artifacts = ArtifactStore(root / "artifacts")
        built = build_provider(
            parameters.provider, journal_dir=root / "workers",
            read_artifact=store.artifact_bytes, transport=transport)
        return Controller(
            store=store, artifacts=artifacts, provider=built,
            repo=GitRepository(Path(parameters.workspace_root)), governance_dir=root)
    except BaseException:
        store.close()
        raise


@contextmanager
def open_runtime(parameters: PilotParameters, *, transport=None):
    """`compose_runtime`, closed on the way out."""
    controller = compose_runtime(parameters, transport=transport)
    try:
        yield controller
    finally:
        controller.store.close()


def owner_from(actor_id: str, principal_key_id: str, auth_method: str = "SESSION") -> ActorRef:
    """The human principal a CLI invocation names. Named, keyed, not delegated.

    `record_decision` refuses a `HUMAN` actor with no `principal_key_id`
    (`guard:decision_principal_key_record`, `F04-001`), so the key is required
    here rather than defaulted to something the runtime invented.
    """
    from .models import ActorKind, AuthMethod

    return ActorRef(actor_kind=ActorKind.HUMAN, actor_id=actor_id,
                    auth_method=AuthMethod(auth_method), principal_key_id=principal_key_id)


def parameters_from(args) -> PilotParameters:
    """Build `PilotParameters` from a parsed command line.

    Every value below arrives from the command line. `src/` holds no pilot
    sandbox path, no pilot database path, no pilot base revision, no objective
    and no target path (`D5`).
    """
    def given(name, default=""):
        # `observe` and `resume` do not carry the pilot half at all, so a
        # missing option is an absent value rather than a defaulted one.
        return getattr(args, name, None) or default

    validation = None
    if given("validation_argv", ()):
        validation = ValidationPlan(
            spec_id=args.validation_spec, operation_id=args.validation_operation,
            version=args.validation_version, argv=tuple(args.validation_argv),
            cwd=args.validation_cwd, timeout_ms=args.validation_timeout_ms)
    # `GR32-F-006`: the budget is constructed from the owner's flags, one per
    # `Budget` field, and from nothing else. `observe` and `resume` carry none,
    # so for them it is absent rather than defaulted.
    supplied = [getattr(args, f"budget_{name}", None) for name in BUDGET_FIELDS]
    budget = Budget(*supplied) if all(value is not None for value in supplied) else None
    return PilotParameters(
        workspace_root=str(Path(args.workspace).resolve()),
        governance_root=str(Path(args.governance_root).resolve()),
        provider=args.provider,
        project_name=given("name"), project_slug=given("slug"),
        objective=given("objective"),
        allowed_paths=tuple(given("allow_path", ())),
        excluded_paths=tuple(given("exclude_path", ())),
        inference_origin=given("origin"), secret_name=given("secret_name"),
        secret_env_var=given("secret_env"),
        credential_header=given("credential_header", DEFAULT_CREDENTIAL_HEADER),
        credential_prefix=getattr(args, "credential_prefix", DEFAULT_CREDENTIAL_PREFIX),
        worker_role=given("worker_role"),
        capability_request=tuple(given("capability", ())),
        prompt=given("prompt"), commit_message=given("commit_message"),
        base_revision=getattr(args, "base_revision", None),
        deadline_ms=getattr(args, "deadline_ms", None) or 3600000,
        budget=budget, validation=validation)


def drive(args) -> tuple:
    """Run one driver entry and return its report document and exit status.

    `0` is a completed entry; `1` is a refusal that stopped it. A refusal is a
    result, not a crash: the report says which step, what was asked, what
    refused and in what words, which is what the owner needs in order to
    decide what happens next. Nothing is retried here, ever.

    That holds for composition too (`GR32-F-001`): a typed refusal while the
    runtime is being composed — an unknown provider, an absent executable, a
    store that will not open — is step 1 of a `STOPPED` report, not a
    traceback. Only `GovernedRuntimeError` is a refusal; anything else is a
    defect and propagates as one. No credential has been resolved at that
    point, so the composition report carries only the parameters' names.
    """
    parameters = parameters_from(args)
    owner = owner_from(args.owner, args.owner_key, args.owner_auth)
    try:
        controller = compose_runtime(parameters)
    except GovernedRuntimeError as exc:
        report = DriverReport(entry=args.command, parameters=parameters.document())
        outcome = StepOutcome(step=1, act="runtime.compose", result="NOT_ATTEMPTED",
                              detail={"provider": parameters.provider})
        report.steps.append(outcome)
        record_refusal(report, outcome, exc)
        return report.document(), 1
    try:
        session = PilotSession(controller, parameters,
                               ConsoleOwnerPresenter(owner), owner=owner,
                               entry=args.command)
        try:
            if args.command == "pilot":
                session.run()
            elif args.command == "observe":
                session.observe(args.project, args.run, spec_id=args.validation_spec_id)
            else:
                session.resume(args.project)
        except GovernedRuntimeError:
            return session.documented_report(), 1
        return session.documented_report(), 0
    finally:
        controller.store.close()
