"""Shared setup for the GR-32 driver and composition tests.

Nothing here provisions by writing a row. Every project below is created,
started, provisioned, run, contracted, activated, invoked, proposed,
authorized and applied through `PilotSession`, which is the point: `B1` was
"the harness bypasses governance" and `B2` is "nothing in production walks the
sequence", so a support module that wrote `Project.capability_ceiling` would be
testing the bypass again.

The worker is offline. `ClaudeCodeProvider` is the real adapter, with a
scripted transport standing in for the vendor CLI — the same shape
`tests/test_gr07_workers.py` has used since GR-07. The relay is configured for
real against a syntactically valid origin and is never dialled: GR-32 proves
the composition, and the first live provider invocation is still unproven
territory (`CLAUDE.md` Known gaps, GR-07).
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:  # pragma: no cover - import side effect
    sys.path.insert(0, str(SRC))

from gruntime.adapters.claude_code import ClaudeCodeProvider  # noqa: E402
from gruntime.adapters.worker_process import ProcessResult  # noqa: E402
from gruntime.canonical import canonical_json  # noqa: E402
from gruntime.driver import (  # noqa: E402
    OwnerAnswer,
    PilotParameters,
    PilotSession,
    ValidationPlan,
    open_runtime,
)
from gruntime.models import ActorKind, ActorRef, AuthMethod, Budget  # noqa: E402
from gruntime.worker_protocol import request_from_bytes, strict_json  # noqa: E402

#: A credential that satisfies the relay's printable-ASCII guard, supplied the
#: way `D2` requires: by naming an environment variable, never by a path.
CREDENTIAL = "sk-gr32-offline-4f21a8c07bd94e3f"
CREDENTIAL_VARIABLE = "GR32_PILOT_CREDENTIAL"

#: A syntactically valid origin that is never dialled. `InferenceRelay`
#: verifies TLS against the real trust store, so an offline test that reached
#: it would fail on the network rather than on governance.
ORIGIN = "https://inference.invalid"

SECRET_NAME = "pilot-inference-key"

#: The path this pilot's worker is allowed to touch, and the file it proposes.
TARGET = "src/main.py"
PROPOSED = "def greet(name):\n    return f'Hello, {name}!'\n"

OWNER = ActorRef(actor_kind=ActorKind.HUMAN, actor_id="owner@example.invalid",
                 auth_method=AuthMethod.SESSION, principal_key_id="key-owner")

#: A second, differently-named human. Used where a test needs an answer that
#: came back attributed to somebody other than the approving principal.
OTHER = ActorRef(actor_kind=ActorKind.HUMAN, actor_id="other@example.invalid",
                 auth_method=AuthMethod.SESSION, principal_key_id="key-other")

#: What Pilot 1 asks a worker for. `secret.read` is deliberately absent: the
#: kernel holds it to open the relay and a worker never receives it.
CAPABILITIES = ("fs.read", "fs.write", "commit.propose", "validation.request",
                "proc.exec.validation", "net.egress.allowlist")


class ScriptedPresenter:
    """A presenter with a script, never a default.

    Answers the approving option for every act, except where `refuse_at` names
    an act (or a `step:act` pair), which answers `None` — a refusal. It
    fabricates nothing the driver could not have been told: every answer it
    returns is one the request offered.
    """

    def __init__(self, *, decided_by=OWNER, refuse_at=(), answer_with=None,
                 attribute_to=None):
        self.decided_by = decided_by
        self.refuse_at = frozenset([refuse_at] if isinstance(refuse_at, str) else refuse_at)
        #: {act: chosen} for tests about an answer that was never offered.
        self.answer_with = dict(answer_with or {})
        #: {act: ActorRef} for tests about who answered.
        self.attribute_to = dict(attribute_to or {})
        self.seen = []

    def __call__(self, request):
        self.seen.append(request)
        keys = (request.act, f"{request.step}:{request.act}")
        if any(key in self.refuse_at for key in keys):
            return None
        chosen = next((self.answer_with[key] for key in keys if key in self.answer_with),
                      request.approving)
        decided_by = next((self.attribute_to[key] for key in keys if key in self.attribute_to),
                          self.decided_by)
        return OwnerAnswer(chosen=chosen, decided_by=decided_by,
                           justification=f"owner authorized {request.act}")


class ScriptedTransport:
    """The vendor CLI, scripted. `ClaudeCodeProvider` is the real adapter.

    `run` is `ProcessTransport`'s signature, so `JournaledWorkerProvider` takes
    this path and no relay bridge is involved: the relay is configured by step
    12 and this worker never dials it, which is what makes the sequence offline
    without weakening any gate it traverses.
    """

    def __init__(self, mutations=None, **envelope_changes):
        self.mutations = mutations
        self.changes = envelope_changes
        self.calls = []

    def run(self, argv, payload, **kwargs):
        data = strict_json(payload)
        request = request_from_bytes(canonical_json(data["request"]))
        self.calls.append((argv, kwargs))
        mutations = self.mutations
        if mutations is None:
            mutations = [dict(op="CREATE", path=TARGET, content=PROPOSED,
                              rename_to=None, before_digest=None, mode=None)]
        document = dict(
            version=1, invocation_id=request.invocation_id, status="COMPLETED",
            termination_reason="COMPLETED", output="proposed one change", claims=[],
            session=dict(id=request.session_id, fresh=True, continued_from=None),
            review=None, proposed_mutations=list(mutations),
            requested_validations=[], tool_calls=[])
        document.update(self.changes)
        return ProcessResult(canonical_json(dict(
            type="result", subtype="success", is_error=False,
            structured_output=document)))


def workspace(tmp_path, *, name="workspace"):
    """A real git repository, with the pilot's target directory in it."""
    import subprocess

    root = tmp_path / name
    if (root / ".git").exists():
        return root
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("pilot\n", encoding="utf-8")

    def git(*args):
        subprocess.run(["git", *args], cwd=str(root), check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "gr32@example.invalid")
    git("config", "user.name", "GR-32")
    git("config", "commit.gpgsign", "false")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    return root


def validation_plan(*, spec_id="check", cwd="src"):
    """A `network='NONE'` catalog operation, parameterized like every other."""
    return ValidationPlan(
        spec_id=spec_id, operation_id="pilot.check", version="1.0.0",
        argv=(str(Path(sys.executable).resolve()), "-c", "print('observed')"),
        cwd=cwd, timeout_ms=30000)


def parameters(tmp_path, *, slug="gr-32", root=None, governance=None, **changes):
    """Every pilot-specific value, supplied from here rather than from `src/`."""
    root = root or workspace(tmp_path)
    fields = dict(
        project_name="GR-32 Pilot", project_slug=slug,
        objective="Add greet(name) to src/main.py, returning a greeting.",
        allowed_paths=(TARGET,), excluded_paths=(),
        workspace_root=str(root),
        governance_root=str(governance or (tmp_path / f"governance-{slug}")),
        provider="claude-code", inference_origin=ORIGIN, secret_name=SECRET_NAME,
        secret_env_var=CREDENTIAL_VARIABLE, worker_role="IMPLEMENTER",
        capability_request=CAPABILITIES,
        prompt="Add greet(name) to src/main.py.",
        commit_message="pilot: add greet(name)",
        budget=Budget(3600000, 100, 100.0, 100, 100, 100),
        validation=validation_plan())
    fields.update(changes)
    return PilotParameters(**fields)


def environ(value=CREDENTIAL, *, variable=CREDENTIAL_VARIABLE):
    """A process environment holding exactly the credential under test.

    A mapping rather than `os.environ`: the driver takes the environment as a
    parameter, so a test never has to mutate the real one to say what a
    credential is.
    """
    return {} if value is None else {variable: value}


@contextmanager
def session(parameters, *, present=None, transport=None, credential=CREDENTIAL,
            commit_preconditions=None, owner=OWNER, entry="pilot"):
    """An open runtime and a `PilotSession` over it, torn down on the way out."""
    with open_runtime(parameters, transport=transport or ScriptedTransport()) as controller:
        yield PilotSession(controller, parameters, present or ScriptedPresenter(),
                           owner=owner, environ=environ(credential),
                           commit_preconditions=commit_preconditions, entry=entry)


def applied(tmp_path, **changes):
    """Run the whole supervised sequence once and return what it produced.

    Returns `(parameters, report)`. The runtime is closed: a caller that wants
    to look at the store opens its own, which is also what a second CLI process
    would do.
    """
    pilot = parameters(tmp_path, **changes)
    with session(pilot) as live:
        report = live.run()
        document = live.documented_report()
    return pilot, report, document


def revisions(root):
    """Every revision in the repository, on every line."""
    import subprocess

    return subprocess.run(["git", "-C", str(root), "rev-list", "--count", "--all"],
                          check=True, capture_output=True, text=True).stdout.strip()


def provider_kind():
    """The adapter the scripted transport is wired into. Named once."""
    return ClaudeCodeProvider
