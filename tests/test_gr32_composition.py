"""GR-32: the composition root — parameterization, provider choice, D6's gate.

Three claims are tested here.

**`D5`.** Pilot-specific values are inputs. `src/` compiles in no sandbox path,
no database path, no base revision, no objective and no target path, and two
different parameter sets drive two different compositions through the same
code. A runtime whose first pilot is baked into it is a script.

**`D6`.** The three legacy `main()` subcommands that perform a governed effect
— `invoke`, `validate`, `commit` — carry no confirmation plumbing and cannot
present rows 7.2-1 or 7.4-4. Under `SUPERVISED` they refuse structurally,
before the controller is built, before the epoch is bumped and before
`controller.started` is appended. Under `AUTONOMOUS` they behave exactly as
they always have, which is what keeps the historical crash, lease and
validation evidence passing without one of those files being edited.

**The provider.** `main()` no longer hardcodes `FakeProvider`; `--provider`
selects one and `driver.build_provider` is the single place adapters are named.

Every refusal is asserted with `match=` (`CLAUDE.md` Tooling).
"""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gruntime.controller import (
    CREATING_COMMANDS,
    DRIVER_COMMANDS,
    GATED_COMMANDS,
    LEGACY_COMMANDS,
    build_parser,
    legacy_command_admits,
    main as controller_main,
)
from gruntime.driver import build_provider
from gruntime.errors import PolicyDenied
from gruntime.models import GovernanceMode
from gruntime.store import StateStore

import gr32_support as S

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

#: The five files whose AUTONOMOUS crash and gate evidence GR-32 preserves by
#: not touching. `D6` exists so that none of them needs editing.
HISTORICAL_EVIDENCE = (
    "tests/test_r2_worker_crash_adoption.py",
    "tests/test_r3_commit_crash_adoption.py",
    "tests/test_gr09_validation.py",
    "tests/test_gr10_git_transaction.py",
    "tests/test_gr03_repository_lease.py",
)


# --- helpers ----------------------------------------------------------------


def store_of(parameters):
    return StateStore.open(Path(parameters.governance_root) / "state.db")


def legacy_argv(parameters, project_id, *command):
    root = Path(parameters.governance_root)
    return ["--db", str(root / "state.db"), "--artifacts", str(root / "artifacts"),
            "--journal", str(root / "workers"), "--repo", parameters.workspace_root,
            "--project", project_id, *command]


def epoch_and_events(parameters, project_id):
    store = store_of(parameters)
    try:
        project = store.get_project(project_id)
        started = [e for e in store.list_events(project_id)
                   if e.event_type == "controller.started"]
        return project.controller_epoch, len(started)
    finally:
        store.close()


BUDGET_A = ("1800000", "3", "25", "2", "1", "4")


def budget_flags(values=BUDGET_A):
    """`GR32-F-006`: every `Budget` field, supplied explicitly on the CLI."""
    names = ("wall-clock-ms", "worker-invocations", "cost-units",
             "validation-executions", "commits", "escalations")
    return [token for name, value in zip(names, values)
            for token in (f"--budget-{name}", value)]


def validation_flags():
    """A `network='NONE'` plan, supplied explicitly on the CLI (`GR32-F-005`)."""
    return ["--validation-argv", str(Path(sys.executable).resolve()),
            "--validation-argv=-c", "--validation-argv=print('observed')",
            "--validation-cwd", "src"]


def pilot_argv(root, governance, *, provider="fake", budget=BUDGET_A, validation=True):
    """The whole `pilot` command line; every value an argument."""
    return ["--provider", provider, "pilot",
            "--owner", S.OWNER.actor_id, "--owner-key", S.OWNER.principal_key_id,
            "--workspace", str(root), "--governance-root", str(governance),
            "--name", "CLI", "--slug", "cli",
            "--objective", "Write a file.", "--allow-path", "src/written.py",
            "--capability", "fs.read", "--capability", "fs.write",
            "--capability", "commit.propose", "--worker-role", "IMPLEMENTER",
            "--prompt", "Write it.", "--commit-message", "cli: write it",
            "--origin", S.ORIGIN, "--secret-name", S.SECRET_NAME,
            "--secret-env", S.CREDENTIAL_VARIABLE,
            *budget_flags(budget), *(validation_flags() if validation else ())]


def sources():
    """Every Python source file under `src/`."""
    return sorted(SRC.rglob("*.py"))


# --- D5: nothing about Pilot 1 is compiled into `src/` ----------------------


@pytest.mark.parametrize("literal", [
    "/tmp/pilot-sandbox",       # the throwaway target
    "/tmp/pilot-db",            # the throwaway store
    "27e6c88",                  # the pilot base revision
    "main.py",                  # the pilot's one target path
    "greet",                    # the pilot's objective
    "Add greet(name)",
])
def test_no_pilot_1_constant_is_compiled_into_src(literal):
    """`D5`. A value that belongs to one pilot is that pilot's input."""
    offenders = [path.relative_to(ROOT) for path in sources()
                 if literal in path.read_text()]
    assert offenders == [], f"{literal!r} is compiled into {offenders}"


def test_no_source_path_reads_claude_code_credential_storage():
    """`D2`. The credential is named, never discovered.

    No `~/.claude/.credentials.json`, no home-directory probe, no credential
    file of any kind: the only way a credential enters this runtime is by
    naming the environment variable that holds it.
    """
    forbidden = (".credentials.json", ".claude/", "Path.home(", "expanduser",
                 "CLAUDE_CODE_OAUTH", "ANTHROPIC_API_KEY")
    offenders = []
    for path in [*sources(), ROOT / "bin" / "pilot-run"]:
        text = path.read_text()
        for needle in forbidden:
            if needle in text:
                offenders.append((str(path.relative_to(ROOT)), needle))
    # `ClaudeCodeProvider.relay_environment` names `ANTHROPIC_API_KEY` as the
    # public placeholder it hands the sandboxed CLI, which is not a credential
    # and is stripped by the relay. Nothing else may appear at all.
    assert offenders == [("src/gruntime/adapters/claude_code.py", "ANTHROPIC_API_KEY")]


def test_two_different_parameter_sets_compose_two_different_projects(tmp_path):
    """The same code, twice, over two workspaces, two stores and two objectives."""
    first_root = S.workspace(tmp_path, name="alpha")
    second_root = S.workspace(tmp_path, name="beta")
    (second_root / "lib").mkdir()

    first = S.parameters(tmp_path, slug="alpha", root=first_root)
    second = S.parameters(
        tmp_path, slug="beta", root=second_root,
        objective="Add a farewell to lib/exit.py.",
        allowed_paths=("lib/exit.py",),
        capability_request=("fs.read", "fs.write", "commit.propose"),
        worker_role="INTEGRATOR",
        prompt="Add a farewell.", commit_message="beta: add farewell",
        validation=S.validation_plan(cwd="lib"))

    with S.session(first) as session:
        first_report = session.run()
    transport = S.ScriptedTransport(mutations=[
        dict(op="CREATE", path="lib/exit.py", content="def farewell():\n    return 'bye'\n",
             rename_to=None, before_digest=None, mode=None)])
    with S.session(second, transport=transport) as session:
        second_report = session.run()

    assert first_report.state == second_report.state == "MATERIALIZED"
    assert first_report.project_id != second_report.project_id
    assert first_report.materialized_revision != second_report.materialized_revision
    assert first.governance_root != second.governance_root

    # The second composition asked for a narrower ceiling, and got one.
    store = store_of(second)
    try:
        project = store.get_project(second_report.project_id)
        assert project.capability_ceiling == frozenset(
            {"fs.read", "fs.write", "commit.propose", "secret.read"})
        contract = store.get_contract(second_report.contract_id)
        assert contract.worker_role == "INTEGRATOR"
        assert contract.scope_include == ["lib/exit.py"]
    finally:
        store.close()


def test_the_driver_cli_names_every_pilot_value_as_a_flag():
    """`D5`'s minimum list, each one an option rather than a constant."""
    parser = build_parser()
    action = next(a for a in parser._actions if hasattr(a, "choices") and a.choices
                  and "pilot" in getattr(a, "choices", {}))
    options = {option for sub in action.choices.values()
               for act in sub._actions for option in act.option_strings}
    options |= {option for act in parser._actions for option in act.option_strings}
    for required in ("--objective", "--allow-path", "--workspace", "--governance-root",
                     "--provider", "--origin", "--secret-name", "--secret-env",
                     "--credential-header", "--credential-prefix", "--base-revision",
                     # `GR32-F-006`: one flag per `Budget` field.
                     "--budget-wall-clock-ms", "--budget-worker-invocations",
                     "--budget-cost-units", "--budget-validation-executions",
                     "--budget-commits", "--budget-escalations"):
        assert required in options, required


# --- the provider: named, never hardcoded -----------------------------------


def test_main_no_longer_hardcodes_a_provider():
    """`D4`: the claim `bin/pilot-run` used to make is no longer true."""
    module = (SRC / "gruntime" / "controller.py").read_text()
    tree = ast.parse(module)
    functions = {node.name: node for node in ast.walk(tree)
                 if isinstance(node, ast.FunctionDef)}
    for name in ("main", "build_parser"):
        source = ast.get_source_segment(module, functions[name])
        assert "FakeProvider" not in source, f"{name} names a concrete provider"
    assert "--provider" in ast.get_source_segment(module, functions["build_parser"])


def test_build_provider_names_the_adapters_and_refuses_the_rest(tmp_path, monkeypatch):
    from gruntime.adapters.claude_code import ClaudeCodeProvider
    from gruntime.adapters.codex import CodexProvider
    from gruntime.adapters.fake_provider import FakeProvider

    journal = tmp_path / "workers"
    read = lambda digest: b""
    assert isinstance(build_provider("fake", journal_dir=journal, read_artifact=read),
                      FakeProvider)
    transport = S.ScriptedTransport()
    assert isinstance(build_provider("claude-code", journal_dir=journal,
                                     read_artifact=read, transport=transport),
                      ClaudeCodeProvider)
    assert isinstance(build_provider("codex", journal_dir=journal,
                                     read_artifact=read, transport=transport),
                      CodexProvider)
    with pytest.raises(PolicyDenied, match=r"unknown provider 'nonesuch'"):
        build_provider("nonesuch", journal_dir=journal, read_artifact=read)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    with pytest.raises(PolicyDenied, match=r"needs its executable on PATH"):
        build_provider("codex", journal_dir=journal, read_artifact=read)


# --- D6: the legacy command gate --------------------------------------------


@pytest.fixture
def supervised(tmp_path):
    """A supervised project that reached a governed revision through the driver."""
    parameters, report, _ = S.applied(tmp_path, slug="d6")
    return parameters, report


@pytest.mark.parametrize("command", sorted(GATED_COMMANDS))
def test_every_gated_command_refuses_under_supervised(supervised, command):
    parameters, report = supervised
    extra = {
        "invoke": ["--run", report.run_id],
        "validate": ["--run", report.run_id, "--spec", "check"],
        "commit": ["--run", report.run_id, "--path", S.TARGET, "--content", "x"],
    }[command]
    with pytest.raises(PolicyDenied, match=rf"{command!r} is a legacy command"):
        controller_main(legacy_argv(parameters, report.project_id, command, *extra))


@pytest.mark.parametrize("command", sorted(GATED_COMMANDS))
def test_the_refusal_precedes_the_epoch_bump_and_the_started_event(supervised, command):
    """Structural, not incidental: nothing durable happens before it."""
    parameters, report = supervised
    before = epoch_and_events(parameters, report.project_id)
    extra = {
        "invoke": ["--run", report.run_id],
        "validate": ["--run", report.run_id, "--spec", "check"],
        "commit": ["--run", report.run_id, "--path", S.TARGET, "--content", "x"],
    }[command]
    with pytest.raises(PolicyDenied, match=r"refuses before the controller is built"):
        controller_main(legacy_argv(parameters, report.project_id, command, *extra))
    assert epoch_and_events(parameters, report.project_id) == before


@pytest.mark.parametrize("command", sorted(set(LEGACY_COMMANDS) - GATED_COMMANDS))
def test_start_recover_and_snapshot_are_unaffected(supervised, command):
    """The read and reconcile commands never needed a confirmation."""
    parameters, report = supervised
    epoch, started = epoch_and_events(parameters, report.project_id)
    assert controller_main(legacy_argv(parameters, report.project_id, command)) == 0
    after_epoch, after_started = epoch_and_events(parameters, report.project_id)
    assert after_epoch == epoch + 1 and after_started == started + 1


def test_every_gated_command_still_works_under_autonomous(h):
    """The historical path, in-process, on a project in the mode it assumes."""
    from genesis_support import AUTONOMOUS, OWNER, create_project

    h.init_repo()
    with h.controller(with_repo=True) as controller:
        project = create_project(controller, then_mode=AUTONOMOUS, name="D6",
                                 slug="d6-autonomous", workspace_root=str(h.repo_dir),
                                 approved_by=OWNER)
        controller.start(project)
        run = controller.open_run(project)
        controller.take_snapshot(project)

    argv = ["--db", str(h.db_path), "--artifacts", str(h.artifacts_dir),
            "--journal", str(h.journal_dir), "--repo", str(h.repo_dir),
            "--project", project]
    assert controller_main(argv + ["invoke", "--run", run]) == 0
    assert controller_main(argv + ["commit", "--run", run, "--path", "feature.txt",
                                   "--content", "governed\n"]) == 0


def test_the_predicate_answers_for_the_mode_the_project_is_in(supervised, monkeypatch):
    """One predicate, both directions, read off the project row."""
    parameters, report = supervised
    store = store_of(parameters)
    try:
        for command in sorted(GATED_COMMANDS):
            assert not legacy_command_admits(store, command, report.project_id)
        for command in sorted(set(LEGACY_COMMANDS) - GATED_COMMANDS):
            assert legacy_command_admits(store, command, report.project_id)
        project = store.get_project(report.project_id)
        project.governance_mode = GovernanceMode.AUTONOMOUS
        store.put_project(project)
        for command in LEGACY_COMMANDS:
            assert legacy_command_admits(store, command, report.project_id)
    finally:
        store.close()


def test_the_gated_set_cannot_drift_from_the_parser_surface():
    """The parser *is* the mappings, so a command cannot exist ungated.

    `D6`: "parser and predicate must not silently drift". `build_parser` builds
    its subparsers from `LEGACY_COMMANDS` and `DRIVER_COMMANDS`, so the two can
    only disagree if someone changes the mappings — which changes the parser in
    the same edit.
    """
    import argparse

    parser = build_parser()
    action = next(a for a in parser._actions
                  if isinstance(a, argparse._SubParsersAction))
    assert set(action.choices) == set(LEGACY_COMMANDS) | set(DRIVER_COMMANDS)
    assert GATED_COMMANDS <= set(LEGACY_COMMANDS)
    assert not GATED_COMMANDS & set(DRIVER_COMMANDS)
    # The intended gated set, stated once so a silent widening or narrowing of
    # the mapping is a failing test rather than a quiet policy change.
    assert GATED_COMMANDS == frozenset({"invoke", "validate", "commit"})
    assert set(LEGACY_COMMANDS) == {"start", "recover", "snapshot",
                                    "invoke", "validate", "commit"}
    assert set(DRIVER_COMMANDS) == {"pilot", "observe", "resume"}
    assert CREATING_COMMANDS == frozenset({"pilot"})


def test_the_driver_commands_are_the_supervised_path(supervised):
    """`resume` runs against the supervised project the gate refuses `invoke` on."""
    parameters, report = supervised
    argv = ["--project", report.project_id, "--provider", "fake", "resume",
            "--owner", S.OWNER.actor_id, "--owner-key", S.OWNER.principal_key_id,
            "--workspace", parameters.workspace_root,
            "--governance-root", parameters.governance_root]
    assert controller_main(argv) == 0


# --- the historical evidence is untouched -----------------------------------


@pytest.mark.parametrize("relpath", HISTORICAL_EVIDENCE)
def test_the_historical_evidence_files_are_unmodified(relpath):
    """`GR32-P-003`. `D6` exists so none of these needs an edit.

    Compared against the committed bytes rather than asserted in prose: the
    claim GR-32 makes is that its gate preserves this evidence *without*
    touching it, and a test that only ran them would not notice an edit that
    made them pass.
    """
    committed = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{relpath}"],
                               capture_output=True)
    if committed.returncode != 0:  # pragma: no cover - not a git checkout
        pytest.skip("not a git checkout")
    assert (ROOT / relpath).read_bytes() == committed.stdout


def test_the_historical_evidence_runs_autonomous_projects():
    """And that is why the gate cannot reach it: it gates `SUPERVISED` only."""
    for relpath in HISTORICAL_EVIDENCE:
        text = (ROOT / relpath).read_text()
        if "create_project" in text:
            assert "AUTONOMOUS" in text, relpath


# --- the composition half, on its own ---------------------------------------


def test_running_a_pilot_on_an_observation_parameter_set_is_refused(tmp_path):
    """`observe` and `resume` need the composition half; `run()` needs both.

    A parameter set built for a restart carries a workspace, a governance root
    and a provider and nothing else. Walking the sequence with it would author
    a contract with a blank objective and an empty scope, so it is refused.
    """
    from gruntime.driver import PilotParameters, PilotSession, parameters_are_complete

    complete = S.parameters(tmp_path, slug="halves")
    partial_set = PilotParameters(
        workspace_root=complete.workspace_root,
        governance_root=complete.governance_root, provider="fake")
    assert parameters_are_complete(complete)
    assert not parameters_are_complete(partial_set)

    from gruntime.driver import open_runtime

    with open_runtime(partial_set) as controller:
        session = PilotSession(controller, partial_set, S.ScriptedPresenter(),
                               owner=S.OWNER, environ=S.environ())
        with pytest.raises(PolicyDenied, match=r"carries only the composition half"):
            session.run()
        # `GR32-F-001`: a refused pre-step check is a stopped step 1, never a
        # report left `RUNNING` with nothing recorded.
        assert session.report.state == "STOPPED"
        assert session.report.stopped_at == 1
        assert [s.act for s in session.report.steps] == ["runtime.compose"]


def test_the_pilot_cli_presents_each_act_and_a_closed_stdin_refuses(tmp_path, capsys):
    """`ConsoleOwnerPresenter` fabricates nothing: no input is a refusal.

    The whole CLI path — parser, `parameters_from`, `drive`, the presenter and
    the report — with the one answer a closed stdin can give.
    """
    import io
    import json as _json

    root = S.workspace(tmp_path, name="cli")
    argv = pilot_argv(root, tmp_path / "governance-cli")

    class ClosedStdin(io.StringIO):
        pass

    import gruntime.driver as driver_module

    original = driver_module.ConsoleOwnerPresenter.__call__

    def present(self, request):
        self._stream = ClosedStdin("")
        return original(self, request)

    driver_module.ConsoleOwnerPresenter.__call__ = present
    try:
        status = controller_main(argv)
    finally:
        driver_module.ConsoleOwnerPresenter.__call__ = original

    assert status == 1
    printed = capsys.readouterr().out.strip().splitlines()
    report = _json.loads(printed[-1])
    assert report["state"] == "STOPPED"
    assert report["stopped_at"] == 2
    assert report["steps"][-1]["refusal_type"] == "OwnerRefused"
    assert report["materialized_revision"] is None
    # What the presenter was shown is on stdout ahead of the report.
    assert any("project.create" in line for line in printed[:-1])


def test_bin_pilot_run_is_a_preflight_and_performs_no_transition(tmp_path, monkeypatch):
    """`D4`. It observes; it neither refuses on stale claims nor runs GR-33."""
    import json as _json

    target = S.workspace(tmp_path, name="preflight")
    head = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    monkeypatch.setenv(S.CREDENTIAL_VARIABLE, S.CREDENTIAL)
    # Invoked as a program, through its own shebang — the way an operator
    # runs it. Going through `sys.executable` would hand it this suite's
    # interpreter and hide whether the script can find the runtime's
    # dependencies on its own.
    argv = [str(ROOT / "bin" / "pilot-run"),
            "--target", str(target),
            "--governance-root", str(tmp_path / "governance-preflight"),
            "--base-revision", head, "--objective", "Add greet.",
            "--allow-path", "src/main.py", "--provider", "fake",
            "--origin", S.ORIGIN, "--secret-name", S.SECRET_NAME,
            "--secret-env", S.CREDENTIAL_VARIABLE]
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    report = _json.loads(result.stdout)
    assert result.returncode == 0, result.stderr
    assert report["state"] == "READY"
    assert report["runtime_transitions_performed"] == 0
    assert all(step["state"] == "NOT_ATTEMPTED" for step in report["steps"])
    assert report["credential_observation"]["accepted"] is True
    assert S.CREDENTIAL not in result.stdout
    # It made no store and no transition.
    assert not (tmp_path / "governance-preflight").exists()

    # And it refuses, rather than proceeding, when a precondition does not hold.
    monkeypatch.delenv(S.CREDENTIAL_VARIABLE)
    refused = subprocess.run(argv, capture_output=True, text=True, check=False)
    assert refused.returncode == 1
    assert "names nothing in this process environment" in refused.stdout


def test_bin_pilot_run_finds_the_runtime_without_being_handed_an_interpreter(tmp_path, monkeypatch):
    """It imports `gruntime.driver`, so it must locate the project interpreter.

    The credential check is `driver.preflight_credential` itself rather than a
    second implementation, which means the script needs the runtime's
    dependencies. A bare `python3` on `PATH` does not have them, so the script
    re-execs under the project interpreter it locates relative to itself. Run
    here with a scrubbed environment — no `PYTHONPATH`, no inherited venv — so
    the test fails if that stops working.
    """
    import json as _json

    target = S.workspace(tmp_path, name="standalone")
    head = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    environment = {k: v for k, v in os.environ.items()
                   if k not in ("PYTHONPATH", "VIRTUAL_ENV", "GRUNTIME_PILOT_REEXEC")}
    environment[S.CREDENTIAL_VARIABLE] = S.CREDENTIAL
    result = subprocess.run(
        [str(ROOT / "bin" / "pilot-run"), "--target", str(target),
         "--governance-root", str(tmp_path / "governance-standalone"),
         "--base-revision", head, "--objective", "Add greet.",
         "--allow-path", "src/main.py", "--provider", "fake", "--origin", S.ORIGIN,
         "--secret-name", S.SECRET_NAME, "--secret-env", S.CREDENTIAL_VARIABLE],
        capture_output=True, text=True, check=False, env=environment)
    assert result.returncode == 0, result.stderr
    assert _json.loads(result.stdout)["credential_observation"]["accepted"] is True


def test_bin_pilot_run_no_longer_asserts_what_gr_32_made_untrue(tmp_path, monkeypatch):
    """`D4`. The two stale assertions are gone from what it *reports*.

    Checked against the report rather than the prose: the docstring still says
    what the script used to claim and why that is no longer true, which is the
    record a reader needs. What matters is that nothing it emits asserts a
    missing composition root or a hardcoded provider any more, and that it no
    longer answers `BLOCKED` on those grounds.
    """
    import json as _json

    target = S.workspace(tmp_path, name="stale-claims")
    head = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    monkeypatch.setenv(S.CREDENTIAL_VARIABLE, S.CREDENTIAL)
    result = subprocess.run(
        [str(ROOT / "bin" / "pilot-run"), "--target", str(target),
         "--governance-root", str(tmp_path / "governance-stale"),
         "--base-revision", head, "--objective", "Add greet.",
         "--allow-path", "src/main.py", "--provider", "fake", "--origin", S.ORIGIN,
         "--secret-name", S.SECRET_NAME, "--secret-env", S.CREDENTIAL_VARIABLE],
        capture_output=True, text=True, check=False)
    report = _json.loads(result.stdout)
    assert "missing" not in report and "shipped_already" not in report
    assert "implementation_evidence" not in report
    assert report["blocked_before"] is None
    assert "FakeProvider" not in result.stdout
    assert report["driver_entry"] == "python -m gruntime.controller pilot"
    # And it still says the live run is not its job.
    assert "GR-33" in report["stage"]


# --- GR32-F-001: composition refusals are reports, not tracebacks -----------


def last_report(capsys):
    import json as _json

    return _json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_an_unknown_provider_is_a_stopped_json_report_not_a_traceback(tmp_path):
    """The reviewer's reproduction, through the real module entry point."""
    import json as _json

    root = S.workspace(tmp_path, name="unknown-provider")
    result = subprocess.run(
        [sys.executable, "-m", "gruntime.controller",
         *pilot_argv(root, tmp_path / "governance-unknown", provider="nonesuch")],
        capture_output=True, text=True, cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(SRC)})
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    report = _json.loads(result.stdout)
    assert report["state"] == "STOPPED" and report["stopped_at"] == 1
    step, = report["steps"]
    assert (step["act"], step["result"], step["refusal_type"]) == (
        "runtime.compose", "REFUSED", "PolicyDenied")
    assert "unknown provider 'nonesuch'" in step["refusal_text"]


def test_a_missing_provider_executable_is_a_stopped_report(tmp_path, capsys, monkeypatch):
    root = S.workspace(tmp_path, name="no-executable")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert controller_main(pilot_argv(root, tmp_path / "gov-noexec", provider="codex")) == 1
    report = last_report(capsys)
    assert report["state"] == "STOPPED" and report["stopped_at"] == 1
    assert "needs its executable on PATH" in report["steps"][0]["refusal_text"]


def test_a_cli_pilot_without_a_validation_plan_is_a_stopped_report(tmp_path, capsys):
    """`GR32-F-005` through the CLI: refused at step 1, no project, no revision."""
    root = S.workspace(tmp_path, name="no-plan")
    assert controller_main(pilot_argv(root, tmp_path / "gov-noplan", validation=False)) == 1
    report = last_report(capsys)
    assert report["state"] == "STOPPED" and report["stopped_at"] == 1
    assert "no validation plan was supplied" in report["steps"][0]["refusal_text"]
    assert report["project_id"] is None and report["materialized_revision"] is None
    assert S.revisions(root) == "1"


# --- GR32-F-006: the CLI budget ---------------------------------------------


@pytest.mark.parametrize("values", [
    ("1800000", "3", "25", "2", "1", "4"),
    ("7200000", "9", "400.5", "11", "5", "7"),
])
def test_the_cli_budget_is_constructed_from_the_flags(tmp_path, values):
    from gruntime.driver import parameters_from
    from gruntime.models import Budget

    args = build_parser().parse_args(pilot_argv(tmp_path, tmp_path / "g", budget=values))
    wall, invocations, cost, validations, commits, escalations = values
    assert parameters_from(args).budget == Budget(
        int(wall), int(invocations), float(cost), int(validations), int(commits),
        int(escalations))


def test_the_cli_refuses_a_pilot_with_no_budget_flags(tmp_path):
    argv = pilot_argv(tmp_path, tmp_path / "g")
    without = [token for index, token in enumerate(argv)
               if not token.startswith("--budget-")
               and not (index and argv[index - 1].startswith("--budget-"))]
    with pytest.raises(SystemExit) as raised:
        build_parser().parse_args(without)
    assert raised.value.code == 2


# --- GR32-F-002: the preflight never sees or repeats the credential ---------


def preflight(tmp_path, bindir, *, provider="claude-code", extra_env=None,
              objective="Add greet.", secret_name=S.SECRET_NAME, label=None):
    label = label or bindir.name
    target = S.workspace(tmp_path, name=f"preflight-{label}")
    head = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    environment = {**os.environ, "PATH": f"{bindir}:{os.environ.get('PATH', '')}",
                   S.CREDENTIAL_VARIABLE: S.CREDENTIAL, **(extra_env or {})}
    return subprocess.run(
        [str(ROOT / "bin" / "pilot-run"), "--target", str(target),
         "--governance-root", str(tmp_path / f"governance-{label}"),
         "--base-revision", head, "--objective", objective,
         "--allow-path", "src/main.py", "--provider", provider, "--origin", S.ORIGIN,
         "--secret-name", secret_name, "--secret-env", S.CREDENTIAL_VARIABLE],
        capture_output=True, text=True, check=False, env=environment)


def hostile(tmp_path, name, body):
    bindir = tmp_path / name
    bindir.mkdir()
    script = bindir / "claude"
    script.write_text("#!/bin/sh\n" + body)
    script.chmod(0o755)
    return bindir


def baked(tmp_path, name, line):
    """A `claude` whose `--version` prints `line` verbatim, quotes and all.

    A quoted heredoc: the shell expands nothing in it, so a `"` or a `\\` in
    the line reaches stdout exactly as written.
    """
    return hostile(tmp_path, name, f"cat <<'EOF'\n{line}\nEOF\n")


def parsed_strings(value):
    """Every key and value string of a parsed report — what a reader receives."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from parsed_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from parsed_strings(item)


def assert_withheld(result, secret, reason):
    """BLOCKED, deterministic, and the secret in no stream and no parsed string."""
    import json as _json

    assert secret not in result.stdout and secret not in result.stderr
    report = _json.loads(result.stdout)
    assert not any(secret in text for text in parsed_strings(report))
    assert result.returncode == 1 and report["state"] == "BLOCKED"
    assert reason in report["reason"]
    assert "provider_observation" not in report
    return report


def test_a_hostile_provider_probe_cannot_see_or_echo_the_credential(tmp_path):
    """The reviewer's reproduction: `--version` echoing the named variable."""
    import json as _json

    spy = tmp_path / "probe-environment"
    bindir = hostile(tmp_path, "hostile", (
        f"env > {spy}\n"
        f"echo \"claude 9.9 ${S.CREDENTIAL_VARIABLE}\"\n"
        f"echo \"${S.CREDENTIAL_VARIABLE}\" >&2\n"))
    result = preflight(tmp_path, bindir)
    seen = spy.read_text()
    assert S.CREDENTIAL not in seen, "the credential reached the probe's environment"
    assert S.CREDENTIAL_VARIABLE not in seen, "the credential variable reached the probe"
    assert set(line.split("=", 1)[0] for line in seen.splitlines()) <= {
        "PATH", "LC_ALL", "PWD", "SHLVL", "_", "OLDPWD"}
    assert S.CREDENTIAL not in result.stdout and S.CREDENTIAL not in result.stderr
    report = _json.loads(result.stdout)
    assert result.returncode == 0 and report["state"] == "READY"
    assert report["provider_observation"]["version"] == "claude 9.9"


def test_a_provider_that_prints_the_credential_anyway_blocks_the_whole_report(tmp_path):
    """Output is checked against the configured value, not a known fixture.

    This provider knows the value without the environment — it is written into
    it — so sanitizing the probe cannot stop it printing it. The report that
    would have carried it is withheld whole.
    """
    import json as _json

    other = "sk-another-offline-value-9c3e1b"
    bindir = hostile(tmp_path, "baked", f"echo 'claude 1.0 {other}'\n")
    result = preflight(tmp_path, bindir, extra_env={S.CREDENTIAL_VARIABLE: other})
    assert other not in result.stdout and other not in result.stderr
    report = _json.loads(result.stdout)
    assert result.returncode == 1 and report["state"] == "BLOCKED"
    assert "--version output contained the value" in report["reason"]


# --- GR32-F-002 (remediation 002): raw values, not serialized JSON ----------


@pytest.mark.parametrize("credential", [
    'sk-gr32"quoted"-fixture-7a1',
    'sk-gr32\\back\\slash-fixture-3c9',
    'sk-gr32"both\\kinds-fixture-e40',
], ids=["quote", "backslash", "both"])
def test_provider_output_holding_a_json_sensitive_credential_is_blocked(tmp_path, credential):
    """The closure reviewer's reproduction: `json.dumps` escaped the secret.

    Checked as the raw provider string, before it enters the report, so the
    parsed report — not only the printed text — holds none of it.
    """
    assert json_escapes(credential)
    bindir = baked(tmp_path, "json-sensitive", f"claude 1.0 {credential}")
    result = preflight(tmp_path, bindir, extra_env={S.CREDENTIAL_VARIABLE: credential})
    assert_withheld(result, credential, "--version output contained the value")


def json_escapes(value):
    import json as _json

    return _json.dumps(value)[1:-1] != value


def test_provider_stderr_holding_the_credential_is_blocked(tmp_path):
    credential = 'sk-gr32"stderr\\fixture-9d2'
    bindir = hostile(tmp_path, "stderr", f"echo 'claude 1.0'\ncat >&2 <<'EOF'\n{credential}\nEOF\n")
    result = preflight(tmp_path, bindir, extra_env={S.CREDENTIAL_VARIABLE: credential})
    assert_withheld(result, credential, "--version output contained the value")


def test_a_json_sensitive_credential_never_reaches_a_hostile_probe(tmp_path):
    """The sanitized probe environment holds for a quoted, backslashed secret."""
    import json as _json

    credential = 'sk-gr32"env\\fixture-55'
    spy = tmp_path / "probe-environment"
    bindir = hostile(tmp_path, "hostile-json", (
        f"env > {spy}\n"
        f"echo \"claude 9.9 ${S.CREDENTIAL_VARIABLE}\"\n"))
    result = preflight(tmp_path, bindir, extra_env={S.CREDENTIAL_VARIABLE: credential})
    seen = spy.read_text()
    assert credential not in seen and S.CREDENTIAL_VARIABLE not in seen
    report = _json.loads(result.stdout)
    assert credential not in result.stdout and credential not in result.stderr
    assert not any(credential in text for text in parsed_strings(report))
    assert result.returncode == 0 and report["state"] == "READY"


@pytest.mark.parametrize("field", ["objective", "secret_name"])
def test_a_credential_reaching_the_report_by_any_other_field_withholds_it(tmp_path, field):
    """The final check covers every report string, not only the provider's.

    The owner pasting the value itself where a name or an objective belongs is
    the case a provider check cannot see. `"` makes it one `json.dumps` escapes.
    """
    credential = 'sk-gr32"pasted\\fixture-a07'
    bindir = baked(tmp_path, f"clean-{field}", "claude 1.0")
    result = preflight(tmp_path, bindir, extra_env={S.CREDENTIAL_VARIABLE: credential},
                       **{field: f"x {credential} y"})
    assert_withheld(result, credential, "withheld whole")


def test_a_credential_spelled_only_by_an_escape_in_the_output_is_withheld(tmp_path):
    """No one string holds it, but the printed text would.

    The credential is `\\"`-bearing; the objective holds the bare `"` form,
    which `json.dumps` writes as exactly the credential's characters.
    """
    credential = 'sk-gr32\\"esc-fixture-b18'
    objective = credential.replace('\\"', '"')
    bindir = baked(tmp_path, "escape-only", "claude 1.0")
    result = preflight(tmp_path, bindir, extra_env={S.CREDENTIAL_VARIABLE: credential},
                       objective=objective)
    assert_withheld(result, credential, "withheld whole")


def test_ordinary_provider_version_output_is_still_reported(tmp_path):
    import json as _json

    credential = 'sk-gr32"ordinary\\fixture-c3f'
    bindir = baked(tmp_path, "ordinary", 'claude 2.0.1 (Claude Code) "stable" \\ build')
    result = preflight(tmp_path, bindir, extra_env={S.CREDENTIAL_VARIABLE: credential})
    report = _json.loads(result.stdout)
    assert result.returncode == 0 and report["state"] == "READY", result.stdout
    assert report["provider_observation"]["version"] == 'claude 2.0.1 (Claude Code) "stable" \\ build'
    assert credential not in result.stdout


# --- GR32-F-002 (remediation 003): the whole launch surface, before launch --


def spying(tmp_path, name, *, directory=None):
    """A `claude` that records that it ran and dumps its whole launch surface.

    `ran` exists only if the provider executed; `seen` holds every environment
    key and value, its own `$0` and its arguments — everything a process can
    learn about how it was launched.
    """
    bindir = tmp_path / (directory or name)
    bindir.mkdir()
    ran, seen = tmp_path / f"{name}-ran", tmp_path / f"{name}-seen"
    script = bindir / "claude"
    script.write_text("#!/bin/sh\n"
                      f": > '{ran}'\n"
                      f"env > '{seen}'\n"
                      f"echo \"argv0=$0 argv=$*\" >> '{seen}'\n"
                      "echo 'claude 3.1'\n")
    script.chmod(0o755)
    return bindir, ran, seen


def test_a_credential_in_the_caller_path_never_reaches_the_probe(tmp_path):
    """The closure-review-002 reproduction: the value is a `PATH` entry.

    The provider is resolved in the preflight; the child's `PATH` is built,
    not forwarded, so the entry that holds the value never reaches it and the
    preflight proceeds.
    """
    import json as _json

    bindir, ran, seen = spying(tmp_path, "path-entry")
    poisoned = f"{tmp_path / S.CREDENTIAL}:{bindir}:{os.environ.get('PATH', '')}"
    result = preflight(tmp_path, bindir, extra_env={"PATH": poisoned})
    assert ran.exists(), result.stdout
    assert S.CREDENTIAL not in seen.read_text(), "the credential reached the probe via PATH"
    assert S.CREDENTIAL not in result.stdout and S.CREDENTIAL not in result.stderr
    report = _json.loads(result.stdout)
    assert result.returncode == 0 and report["state"] == "READY", result.stdout
    assert report["provider_observation"]["version"] == "claude 3.1"


def test_a_credential_in_an_unrelated_variable_never_reaches_the_probe(tmp_path):
    import json as _json

    bindir, ran, seen = spying(tmp_path, "unrelated")
    result = preflight(tmp_path, bindir, extra_env={
        "GR32_UNRELATED_SETTING": f"prefix-{S.CREDENTIAL}-suffix",
        f"GR32_KEY_{S.CREDENTIAL.replace('-', '_')}": "value"})
    assert ran.exists(), result.stdout
    assert S.CREDENTIAL not in seen.read_text()
    assert S.CREDENTIAL.replace("-", "_") not in seen.read_text()
    assert "GR32_UNRELATED_SETTING" not in seen.read_text()
    assert _json.loads(result.stdout)["state"] == "READY"


def test_a_credential_in_the_executable_path_is_refused_before_launch(tmp_path):
    """The resolved executable's own path holds the value: nothing is launched."""
    bindir, ran, seen = spying(tmp_path, "exec-path", directory=f"bin-{S.CREDENTIAL}")
    result = preflight(tmp_path, bindir, label="exec-path")
    assert not ran.exists(), "the provider executed despite a secret-bearing launch path"
    assert not seen.exists()
    assert_withheld(result, S.CREDENTIAL, "launch surface")


def test_a_credential_in_the_executable_filename_is_refused_before_launch(tmp_path):
    """Via a symlink named `claude` whose target's filename holds the value."""
    bindir, ran, seen = spying(tmp_path, "exec-name")
    (bindir / "claude").rename(bindir / f"claude-{S.CREDENTIAL}")
    (bindir / "claude").symlink_to(bindir / f"claude-{S.CREDENTIAL}")
    result = preflight(tmp_path, bindir)
    assert not ran.exists(), "the provider executed despite a secret-bearing target"
    assert_withheld(result, S.CREDENTIAL, "launch surface")


@pytest.mark.parametrize("surface", ["argv", "executable", "env-key", "env-value", "cwd"])
def test_the_launch_surface_invariant_refuses_each_element(surface):
    """`refuse_secret_bearing_launch` in isolation, one element at a time."""
    module = pilot_run_module()
    secret = 'sk-gr32"launch\\fixture-e71'
    argv, environment, cwd = ["/usr/bin/claude", "--version"], {"PATH": "/usr/bin", "LC_ALL": "C"}, "/tmp"
    if surface == "argv":
        argv = [*argv, f"--x={secret}"]
    elif surface == "executable":
        argv = [f"/opt/{secret}/claude", "--version"]
    elif surface == "env-key":
        environment = {**environment, f"K{secret}": "v"}
    elif surface == "env-value":
        environment = {**environment, "PATH": f"/usr/bin:/{secret}"}
    else:
        cwd = f"/tmp/{secret}"
    module.refuse_secret_bearing_launch("", argv, environment, cwd)
    module.refuse_secret_bearing_launch(secret, ["/usr/bin/claude", "--version"],
                                        {"PATH": "/usr/bin", "LC_ALL": "C"}, "/tmp")
    with pytest.raises(ValueError, match="launch surface") as raised:
        module.refuse_secret_bearing_launch(secret, argv, environment, cwd)
    assert secret not in str(raised.value)


def test_the_probe_environment_is_built_not_inherited(monkeypatch):
    """Built from the resolved executable alone: no caller `PATH`, no other key."""
    module = pilot_run_module()
    monkeypatch.setenv("PATH", f"/caller/{S.CREDENTIAL}:/usr/bin")
    monkeypatch.setenv("GR32_UNRELATED_SETTING", S.CREDENTIAL)
    environment = module.probe_environment("/opt/provider/bin/claude")
    assert set(environment) == {"PATH", "LC_ALL"}
    assert environment["PATH"].split(":")[0] == "/opt/provider/bin"
    assert not any(S.CREDENTIAL in value for value in environment.values())


# --- GR32-F-004: the re-exec marker is not trusted because a caller set it ---


def test_a_caller_supplied_reexec_marker_does_not_skip_the_reexec(tmp_path):
    """The reviewer's reproduction: a bare interpreter, a scrubbed path, `=1`."""
    import json as _json
    import shutil

    bare = shutil.which("python3", path="/usr/bin:/bin")
    if bare is None or Path(bare).parent == Path(sys.executable).parent:  # pragma: no cover
        pytest.skip("no system interpreter distinct from the project's")
    target = S.workspace(tmp_path, name="forged-marker")
    head = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    environment = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "VIRTUAL_ENV")}
    environment.update(PATH="/usr/bin:/bin", GRUNTIME_PILOT_REEXEC="1")
    environment[S.CREDENTIAL_VARIABLE] = S.CREDENTIAL
    result = subprocess.run(
        [bare, str(ROOT / "bin" / "pilot-run"), "--target", str(target),
         "--governance-root", str(tmp_path / "governance-forged"),
         "--base-revision", head, "--objective", "Add greet.",
         "--allow-path", "src/main.py", "--provider", "fake", "--origin", S.ORIGIN,
         "--secret-name", S.SECRET_NAME, "--secret-env", S.CREDENTIAL_VARIABLE],
        capture_output=True, text=True, check=False, env=environment)
    assert "Traceback" not in result.stderr
    assert result.returncode == 0, result.stderr
    assert _json.loads(result.stdout)["credential_observation"]["accepted"] is True


def bare_interpreter():
    bare = shutil.which("python3", path="/usr/bin:/bin")
    if bare is None or Path(bare).parent == Path(sys.executable).parent:  # pragma: no cover
        pytest.skip("no system interpreter distinct from the project's")
    return bare


def standalone_preflight(tmp_path, name, launcher, *, marker=None):
    """`bin/pilot-run` launched by `launcher`, with no inherited venv or path.

    `marker`, when given, is exported as `GRUNTIME_PILOT_REEXEC` by the shell
    that then execs the launcher, so `$$` is the pid the script will run as —
    the closure reviewer's forgery (`GR32-F-004`).
    """
    target = S.workspace(tmp_path, name=name)
    head = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    environment = {k: v for k, v in os.environ.items()
                   if k not in ("PYTHONPATH", "VIRTUAL_ENV", "GRUNTIME_PILOT_REEXEC")}
    environment.update({"PATH": "/usr/bin:/bin", S.CREDENTIAL_VARIABLE: S.CREDENTIAL})
    argv = [*launcher, "--target", str(target),
            "--governance-root", str(tmp_path / f"governance-{name}"),
            "--base-revision", head, "--objective", "Add greet.",
            "--allow-path", "src/main.py", "--provider", "fake", "--origin", S.ORIGIN,
            "--secret-name", S.SECRET_NAME, "--secret-env", S.CREDENTIAL_VARIABLE]
    if marker is not None:
        argv = ["/bin/sh", "-c", f'GRUNTIME_PILOT_REEXEC="{marker}"; '
                'export GRUNTIME_PILOT_REEXEC; exec "$@"', "sh", *argv]
    return subprocess.run(argv, capture_output=True, text=True, check=False, env=environment)


def test_a_pid_forged_reexec_marker_does_not_skip_the_reexec(tmp_path):
    """The closure reviewer's reproduction: `<caller pid>:<interpreter>`.

    The shell exports the marker naming its own pid and execs a bare
    `python3`, which keeps that pid. The marker the first remediation trusted
    is now read by nothing, so the script still re-execs, imports the runtime
    and reports READY rather than an import failure.
    """
    import json as _json

    interpreter = ROOT / ".venv" / "bin" / "python"
    result = standalone_preflight(tmp_path, "pid-forged", [bare_interpreter(),
                                  str(ROOT / "bin" / "pilot-run")],
                                  marker=f"$$:{interpreter}")
    assert "Traceback" not in result.stderr
    report = _json.loads(result.stdout)
    assert result.returncode == 0 and report["state"] == "READY", report.get("reason")
    assert report["credential_observation"]["accepted"] is True


def test_the_script_no_longer_reads_a_reexec_marker():
    """No code names the marker; only the docstring says why it is gone."""
    tree = ast.parse((ROOT / "bin" / "pilot-run").read_text())
    docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                  if isinstance(node, (ast.Module, ast.FunctionDef)) and node.body
                  and isinstance(node.body[0], ast.Expr)
                  and isinstance(node.body[0].value, ast.Constant)}
    named = [node.value for node in ast.walk(tree)
             if isinstance(node, ast.Constant) and isinstance(node.value, str)
             and id(node) not in docstrings and "GRUNTIME_PILOT_REEXEC" in node.value]
    assert named == []


def test_a_symlinked_pilot_run_reaches_the_project_interpreter(tmp_path):
    import json as _json

    link = tmp_path / "pilot-run-link"
    link.symlink_to(ROOT / "bin" / "pilot-run")
    result = standalone_preflight(tmp_path, "symlinked", [str(link)])
    assert result.returncode == 0, result.stderr
    assert _json.loads(result.stdout)["state"] == "READY"


def pilot_run_module():
    import importlib.machinery
    import importlib.util

    loader = importlib.machinery.SourceFileLoader("pilot_run_reexec_under_test",
                                                  str(ROOT / "bin" / "pilot-run"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class Execed(Exception):
    pass


@pytest.fixture
def reexec(monkeypatch):
    """The re-exec decision in isolation: `os.execv` records instead of execing."""
    module = pilot_run_module()
    calls = []

    def execv(path, argv):
        calls.append((path, argv))
        raise Execed

    monkeypatch.setattr(module.os, "execv", execv)

    def decide(*, prefix, executable, marker=None):
        monkeypatch.setattr(module.sys, "prefix", str(prefix))
        monkeypatch.setattr(module.sys, "executable", str(executable))
        if marker is None:
            monkeypatch.delenv("GRUNTIME_PILOT_REEXEC", raising=False)
        else:
            monkeypatch.setenv("GRUNTIME_PILOT_REEXEC", marker)
        del calls[:]
        try:
            module.reexec_under_project_interpreter()
        except Execed:
            pass
        return list(calls)

    return module, decide


def test_an_interpreter_in_the_project_venv_is_not_reexeced(reexec):
    """Identity is `sys.prefix`, however the interpreter was launched."""
    module, decide = reexec
    assert decide(prefix=module.VENV, executable="/usr/bin/python3") == []
    assert decide(prefix=module.VENV, executable=module.INTERPRETER) == []


@pytest.mark.parametrize("marker", [None, "1", "{pid}:{interpreter}"])
def test_an_interpreter_outside_the_venv_is_reexeced_whatever_the_marker(reexec, marker):
    module, decide = reexec
    if marker is not None:
        marker = marker.format(pid=os.getpid(), interpreter=module.INTERPRETER)
    calls = decide(prefix="/usr", executable="/usr/bin/python3", marker=marker)
    assert [path for path, _ in calls] == [str(module.INTERPRETER)]
    assert calls[0][1][:2] == [str(module.INTERPRETER),
                               str((ROOT / "bin" / "pilot-run").resolve())]


def test_the_reexeced_child_never_execs_again(reexec):
    """No infinite re-exec: the child is launched by `INTERPRETER`'s own path.

    Even an `INTERPRETER` that failed to activate the venv (prefix `/usr`)
    runs on rather than execing itself again; the import failure that follows
    is a BLOCKED preflight.
    """
    module, decide = reexec
    assert decide(prefix="/usr", executable=module.INTERPRETER) == []


def test_no_project_interpreter_means_no_reexec(reexec, monkeypatch, tmp_path):
    module, decide = reexec
    monkeypatch.setattr(module, "INTERPRETER", tmp_path / "absent" / "python")
    assert decide(prefix="/usr", executable="/usr/bin/python3") == []


def test_an_unimportable_runtime_is_a_blocked_preflight_not_a_traceback(tmp_path, monkeypatch, capsys):
    """Where the runtime cannot be imported, the report says so as JSON."""
    import importlib.machinery
    import importlib.util
    import json as _json

    loader = importlib.machinery.SourceFileLoader("pilot_run_under_test",
                                                  str(ROOT / "bin" / "pilot-run"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    monkeypatch.setitem(sys.modules, "gruntime.driver", None)
    monkeypatch.setenv(S.CREDENTIAL_VARIABLE, S.CREDENTIAL)
    target = S.workspace(tmp_path, name="unimportable")
    head = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    status = module.main([
        "--target", str(target), "--governance-root", str(tmp_path / "governance-unimportable"),
        "--base-revision", head, "--objective", "Add greet.", "--allow-path", "src/main.py",
        "--provider", "fake", "--origin", S.ORIGIN, "--secret-name", S.SECRET_NAME,
        "--secret-env", S.CREDENTIAL_VARIABLE])
    report = _json.loads(capsys.readouterr().out)
    assert status == 1 and report["state"] == "BLOCKED"
    assert "The runtime is not importable" in report["reason"]
