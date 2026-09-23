"""GR-31 `G4`: `proc.exec.validation`, the declaration nothing consumed.

Rows 7.1-2 and 7.1-3 — `REQUESTED → AUTHORIZED` and `REQUESTED → DENIED` —
declare `proc.exec.validation` as their `required_capability`
(`transitions.py:1153`, `:1158`). No `require_authority` call consumed that
declaration, so the table said one thing and the code asked nothing. It is the
same shape as `F03-001`, on the one validation path the supervised pilot
executes, and `CLAUDE.md` recorded it as an open gap deferred from GR-17.

This closes it for those two rows **only**. `F03-001` stays open for the other
131 rows that consume no declaration, and `F04-004` — which closes only when
all of `F03-001`..`003` close — is unaffected.

The check sits immediately before `_require_egress_authority` and therefore
ahead of the `validation.executing` append, for the reason that check already
gives: a denial must leave no attempt for recovery to reconcile, and must
never build an executor.
"""

from __future__ import annotations

import json

import pytest

from gruntime.errors import CapabilityDenied
from gruntime.models import DecisionSubjectKind

from test_gr31_supervision_gates import granted_run, provisioned
from test_gr09_validation import bind, operation


def denials(c, project):
    return [json.loads(c.store.artifact_bytes(event.payload_digest))
            for event in c.store.list_events(project)
            if event.event_type == "authority.denied"]


def run_with(c, project, capabilities):
    """A run whose activation grants exactly `capabilities`.

    Provisioned through `set_capability_ceiling` and `grant_project_budget`
    (`provisioned` above), never through `store.put_project`: a test that
    wrote the project row itself would be asserting against the bypass `B1`
    names rather than against the runtime.
    """
    return granted_run(c, project, capabilities=tuple(capabilities))


def test_validation_requires_proc_exec(h):
    """`execute_validation` refuses without the capability its rows declare.

    And it refuses *before* anything is written: no `validation.executing`
    event, no attempt for recovery to find, no executor built. A refusal that
    left an attempt behind would turn a denial into an unresolvable one.
    """
    project = provisioned(h, "gr31-g4a")
    with h.controller(with_repo=True) as c:
        (h.repo_dir / "src").mkdir(exist_ok=True)
        run = run_with(c, project, ["fs.read", "fs.write", "commit.propose"])
        bind(c, run, operation())
        activation = c.store.activation_for_run(run)
        assert "proc.exec.validation" not in activation.granted_capabilities

        with pytest.raises(CapabilityDenied, match="grant source expired, revoked, exhausted or inadmissible"):
            c.execute_validation(run, "check")

        assert not c._validation_attempts(project)
        assert not [e for e in c.store.list_events(project)
                    if e.event_type == "validation.executing"]
        assert [d["capability"] for d in denials(c, project)] == ["proc.exec.validation"]
        c.store.verify_chain(project)


def test_granted_proc_exec_admits_the_validation(h):
    """A real grant passes the gate: this is an authority check, not a ban."""
    project = provisioned(h, "gr31-g4b")
    with h.controller(with_repo=True) as c:
        (h.repo_dir / "src").mkdir(exist_ok=True)
        run = run_with(c, project,
                       ["fs.read", "fs.write", "commit.propose", "proc.exec.validation"])
        bind(c, run, operation())
        assert "proc.exec.validation" in c.store.activation_for_run(run).granted_capabilities

        receipt = c.execute_validation(run, "check")
        assert receipt.verdict == "PASS"
        assert not denials(c, project)
        c.store.verify_chain(project)


def test_the_capability_is_the_one_the_rows_declare(h):
    """Read the requirement off the frozen table, not out of this test.

    A test that hard-coded the string would pass over a channel that consulted
    nothing, which is the defect `F03-001` names.
    """
    from gruntime.transitions import Axis, rules_for
    from gruntime.models import ValidationStatus as _V

    for to_state in (_V.AUTHORIZED, _V.DENIED):
        rules = rules_for(Axis.VALIDATION, _V.REQUESTED, to_state)
        assert rules, f"§7.1 carries no row REQUESTED -> {to_state}"
        assert {rule.required_capability for rule in rules} == {"proc.exec.validation"}
