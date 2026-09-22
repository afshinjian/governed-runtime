"""Contract tests for the governed skill layer (GR-30).

The six check groups are the enforcement column of
`.agents/governance/rules.md`. Every negative case asserts the exact
finding or validation error it produces, per the match= convention.
"""
from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
AUTH_SCHEMA_PATH = ROOT / ".agents/governance/authorization.schema.json"
REPORT_SCHEMA_PATH = ROOT / ".agents/governance/report.schema.json"
AUTH_SCHEMA = json.loads(AUTH_SCHEMA_PATH.read_text())
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text())


def _load_check():
    path = ROOT / "bin" / "check-governed-skills"
    loader = SourceFileLoader("check_governed_skills", str(path))
    spec = importlib.util.spec_from_loader("check_governed_skills", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


check = _load_check()
CHECK_NAMES = [name for name, _ in check.CHECKS]


def governed_copy(tmp_path):
    root = tmp_path / "tree"
    root.mkdir()
    shutil.copytree(ROOT / ".agents", root / ".agents")
    shutil.copytree(ROOT / ".claude", root / ".claude")
    shutil.copy2(ROOT / "AGENTS.md", root / "AGENTS.md")
    shutil.copy2(ROOT / "CLAUDE.md", root / "CLAUDE.md")
    (root / "bin").mkdir()
    shutil.copy2(ROOT / "bin" / "check-governed-skills", root / "bin" / "check-governed-skills")
    (root / "tests").mkdir()
    shutil.copy2(ROOT / "tests" / "test_governed_skills.py", root / "tests" / "test_governed_skills.py")
    return root


def findings_for(root):
    return {name: items for name, items in check.run_checks(root)}


def catalog_of(root):
    return json.loads((root / ".agents/governance/catalog.json").read_text())


# -- the contract holds on the real tree --------------------------------------


def test_contract_holds_on_the_tree():
    results = check.run_checks(ROOT)
    assert [name for name, _ in results] == CHECK_NAMES
    for name, items in results:
        assert items == [], f"{name}: {items}"


def test_contract_holds_on_a_full_copy(tmp_path):
    assert findings_for(governed_copy(tmp_path)) == {name: [] for name in CHECK_NAMES}


def test_check_script_passes_on_the_tree():
    proc = subprocess.run(
        [sys.executable, "-B", str(ROOT / "bin" / "check-governed-skills")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "governed skill contract: OK" in proc.stdout


def test_every_catalog_skill_requires_authorization():
    catalog = catalog_of(ROOT)
    for entry in catalog["skills"]:
        assert entry["authorization_required"] is True
        assert entry["path"] == f".agents/skills/{entry['id']}/SKILL.md"


# -- authorization schema refusals (SK-03..SK-11) ----------------------------


def authorization(**overrides):
    doc = {
        "authorization_id": "gr30-auth-001",
        "skill": "governed-stage-implementer",
        "mode": "implementation",
        "stage": "GR-30",
        "scope": [".agents/**", ".claude/skills/**"],
        "authorized_by": {"actor_kind": "HUMAN", "principal": "owner"},
        "created_at": "2026-09-20T00:00:00Z",
        "governance_mode": "SUPERVISED",
        "may_commit_tag_push": False,
    }
    doc.update(overrides)
    return doc


def test_template_example_validates():
    text = (ROOT / ".agents/governance/authorization-template.md").read_text()
    example = json.loads(re.search(r"```json\n(.*?)```", text, re.S).group(1))
    jsonschema.validate(example, AUTH_SCHEMA)


def test_each_catalog_mode_is_open_to_its_skill():
    for entry in catalog_of(ROOT)["skills"]:
        for mode in entry["modes"]:
            doc = authorization(skill=entry["id"], mode=mode)
            if mode == "remediation":
                doc["original_findings"] = ["GR30-F-001"]
            if mode == "closure-review":
                doc["candidate"] = {"candidate_ref": "d2a8e31"}
            jsonschema.validate(doc, AUTH_SCHEMA)


def test_remediation_requires_its_original_findings():
    jsonschema.validate(
        authorization(mode="remediation", original_findings=["GR30-F-001"]), AUTH_SCHEMA
    )
    with pytest.raises(jsonschema.ValidationError, match="original_findings"):
        jsonschema.validate(authorization(mode="remediation"), AUTH_SCHEMA)


def test_closure_review_requires_the_candidate_identity():
    jsonschema.validate(
        authorization(
            skill="governed-independent-reviewer",
            mode="closure-review",
            candidate={"candidate_ref": "d2a8e31", "review_record": "design/review/RECORD.md"},
        ),
        AUTH_SCHEMA,
    )
    with pytest.raises(jsonschema.ValidationError, match="candidate"):
        jsonschema.validate(
            authorization(skill="governed-independent-reviewer", mode="closure-review"),
            AUTH_SCHEMA,
        )


def test_agent_signed_authorization_is_refused():
    doc = authorization(authorized_by={"actor_kind": "AGENT", "principal": "agent-1"})
    with pytest.raises(jsonschema.ValidationError, match="HUMAN"):
        jsonschema.validate(doc, AUTH_SCHEMA)


def test_autonomous_governance_is_refused():
    with pytest.raises(jsonschema.ValidationError, match="SUPERVISED"):
        jsonschema.validate(authorization(governance_mode="AUTONOMOUS"), AUTH_SCHEMA)


def test_git_authority_in_an_authorization_is_refused():
    with pytest.raises(jsonschema.ValidationError, match="may_commit_tag_push"):
        jsonschema.validate(authorization(may_commit_tag_push=True), AUTH_SCHEMA)


def test_unknown_authorization_field_is_refused():
    with pytest.raises(jsonschema.ValidationError, match="Additional properties"):
        jsonschema.validate(authorization(may_widen_scope=True), AUTH_SCHEMA)


def test_mode_outside_the_skills_modes_is_refused():
    with pytest.raises(jsonschema.ValidationError, match="is not one of"):
        jsonschema.validate(
            authorization(skill="governed-stage-planner", mode="implementation"), AUTH_SCHEMA
        )


def test_empty_scope_is_refused():
    with pytest.raises(jsonschema.ValidationError, match="non-empty"):
        jsonschema.validate(authorization(scope=[]), AUTH_SCHEMA)


# -- report schema refusals (SK-12) ------------------------------------------


def report(**overrides):
    doc = {
        "report_id": "gr30-report-001",
        "authorization_id": "gr30-auth-001",
        "skill": "governed-stage-implementer",
        "mode": "implementation",
        "stage": "GR-30",
        "outcome": "COMPLETE",
        "scope_observed": [".agents/**"],
    }
    doc.update(overrides)
    return doc


def test_report_without_authorization_is_refused():
    doc = report()
    del doc["authorization_id"]
    with pytest.raises(jsonschema.ValidationError, match="authorization_id"):
        jsonschema.validate(doc, REPORT_SCHEMA)


def test_report_outside_the_outcomes_is_refused():
    with pytest.raises(jsonschema.ValidationError, match="is not one of"):
        jsonschema.validate(report(outcome="MAYBE"), REPORT_SCHEMA)


def test_finding_without_a_claim_is_refused():
    doc = report(findings=[{"id": "GR30-F-001", "severity": "BLOCKER"}])
    with pytest.raises(jsonschema.ValidationError, match="claim"):
        jsonschema.validate(doc, REPORT_SCHEMA)


def test_report_with_unknown_field_is_refused():
    with pytest.raises(jsonschema.ValidationError, match="Additional properties"):
        jsonschema.validate(report(attached_patch={"file": "x"}), REPORT_SCHEMA)


def test_report_of_an_uncataloged_skill_is_refused():
    with pytest.raises(jsonschema.ValidationError, match="is not one of"):
        jsonschema.validate(report(skill="rogue-skill"), REPORT_SCHEMA)


# -- structural refusals of the contract check --------------------------------


def test_missing_wrapper_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    shutil.rmtree(root / ".claude/skills/governed-stage-planner")
    assert any("wrapper missing" in f for f in findings_for(root)["wrappers"])


def test_wrapper_without_a_catalog_entry_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".claude/skills/rogue-skill/SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\nname: rogue-skill\ndescription: Rogue.\n---\n\nPoints nowhere.\n")
    assert any("wrapper without a catalog entry" in f for f in findings_for(root)["wrappers"])


def test_wrapper_that_drops_the_pointer_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".claude/skills/governed-stage-planner/SKILL.md"
    path.write_text(
        path.read_text().replace(
            ".agents/skills/governed-stage-planner/SKILL.md", ".agents/governance/rules.md"
        )
    )
    assert any("does not point" in f for f in findings_for(root)["wrappers"])


def test_wrapper_description_drift_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".claude/skills/governed-owner-closeout/SKILL.md"
    path.write_text(path.read_text().replace("Walks the checklist", "Runs the checklist"))
    assert any("description diverges" in f for f in findings_for(root)["wrappers"])


def test_wrapper_that_restates_procedure_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    canonical = root / ".agents/skills/governed-repo-reality-check/SKILL.md"
    _, body = check.split_frontmatter(canonical.read_text())
    stolen = next(line.strip() for line in body.splitlines() if len(line.strip()) >= 40)
    wrapper = root / ".claude/skills/governed-repo-reality-check/SKILL.md"
    wrapper.write_text(wrapper.read_text().rstrip("\n") + "\n" + stolen + "\n")
    assert any("restates a canonical line" in f for f in findings_for(root)["wrapper-dedup"])


def test_missing_codex_surface_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    (root / "AGENTS.md").unlink()
    assert any("codex discovery surface missing" in f for f in findings_for(root)["wrappers"])


def test_catalog_entry_that_self_authorizes_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/governance/catalog.json"
    catalog = json.loads(path.read_text())
    catalog["skills"][0]["authorization_required"] = False
    path.write_text(json.dumps(catalog, indent=2) + "\n")
    assert any(
        "does not require a stage authorization" in f for f in findings_for(root)["authority"]
    )


def test_schema_that_grants_git_authority_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/governance/authorization.schema.json"
    schema = json.loads(path.read_text())
    schema["properties"]["may_commit_tag_push"]["const"] = True
    path.write_text(json.dumps(schema, indent=2) + "\n")
    assert any("does not pin may_commit_tag_push" in f for f in findings_for(root)["authority"])


def test_template_example_drift_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/governance/authorization-template.md"
    path.write_text(
        path.read_text().replace('"may_commit_tag_push": false', '"may_commit_tag_push": true')
    )
    assert any("does not validate" in f for f in findings_for(root)["authorization-schema"])


def test_mode_enum_drift_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/governance/catalog.json"
    catalog = json.loads(path.read_text())
    implementer = next(e for e in catalog["skills"] if e["id"] == "governed-stage-implementer")
    implementer["modes"].remove("remediation")
    path.write_text(json.dumps(catalog, indent=2) + "\n")
    assert any(
        "mode enum does not match the catalog for governed-stage-implementer" in f
        for f in findings_for(root)["authorization-schema"]
    )


def test_unbound_stage_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/skills/governed-repo-reality-check/SKILL.md"
    path.write_text(path.read_text().replace("`stage`", "`phase`"))
    assert any("binds no stage" in f for f in findings_for(root)["authorization-gate"])


def test_first_step_without_refusal_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/skills/governed-stage-implementer/SKILL.md"
    path.write_text(path.read_text().replace("REFUSED", "NOTED"))
    assert any("does not refuse before any effect" in f for f in findings_for(root)["authorization-gate"])


def test_reviewer_without_independence_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/skills/governed-independent-reviewer/SKILL.md"
    path.write_text(path.read_text().replace("SK-07", "SK-02"))
    assert any("cites no SK-07" in f for f in findings_for(root)["authorization-gate"])


def test_output_without_the_report_schema_citation_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/skills/governed-pilot-readiness/SKILL.md"
    path.write_text(
        path.read_text().replace(
            ".agents/governance/report.schema.json", ".agents/governance/rules.md"
        )
    )
    assert any("does not cite the report schema" in f for f in findings_for(root)["report-schema"])


def test_ungoverned_tree_fails_every_check(tmp_path):
    results = check.run_checks(tmp_path)
    assert [name for name, _ in results] == CHECK_NAMES
    assert all(items for _, items in results)


def test_check_script_reports_findings(tmp_path):
    root = governed_copy(tmp_path)
    shutil.rmtree(root / ".claude/skills/governed-pilot-readiness")
    proc = subprocess.run(
        [sys.executable, "-B", str(ROOT / "bin" / "check-governed-skills"), str(root)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "wrappers: wrapper missing" in proc.stdout


# -- GR30-R01: the check enumerates the layers it governs ----------------------


def test_uncataloged_canonical_skill_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/skills/rogue-skill/SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "---\nname: rogue-skill\ndescription: Commits on the owner's behalf.\n---\n\nProcedure.\n"
    )
    assert any(
        "canonical skill without a catalog entry" in f for f in findings_for(root)["wrappers"]
    )


def test_stray_file_under_the_canonical_skill_root_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    (root / ".agents/skills/NOTES.md").write_text("notes\n")
    assert any(
        "stray file under the canonical skill root" in f for f in findings_for(root)["wrappers"]
    )


def test_file_beside_a_canonical_procedure_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    (root / ".agents/skills/governed-stage-planner/EXTRA.md").write_text("extra\n")
    assert any(
        "canonical skill directory carries a file beside its procedure" in f
        for f in findings_for(root)["wrappers"]
    )


def test_governance_file_outside_the_governed_contract_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    (root / ".agents/governance/extra-rules.md").write_text("# Extra rules\n")
    assert any(
        "governance file outside the governed contract" in f
        for f in findings_for(root)["wrappers"]
    )


def test_stray_directory_under_governance_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    (root / ".agents/governance/extra").mkdir()
    assert any(
        "stray directory under .agents/governance" in f for f in findings_for(root)["wrappers"]
    )


def test_file_beside_a_wrapper_pointer_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    (root / ".claude/skills/governed-stage-planner/EXTRA.md").write_text("extra\n")
    assert any(
        "wrapper directory carries a file beside its pointer" in f
        for f in findings_for(root)["wrappers"]
    )


# -- GR30-R02: the catalog role and kind vocabularies are pinned ----------------


def mutate_catalog_entry(tmp_path, skill_id, mutate):
    root = governed_copy(tmp_path)
    path = root / ".agents/governance/catalog.json"
    catalog = json.loads(path.read_text())
    entry = next(e for e in catalog["skills"] if e["id"] == skill_id)
    mutate(entry)
    path.write_text(json.dumps(catalog, indent=2) + "\n")
    return root


def test_kind_drift_that_sheds_rule_citations_is_a_finding(tmp_path):
    root = mutate_catalog_entry(
        tmp_path, "governed-stage-implementer", lambda entry: entry.update(kind="read-only")
    )
    assert any(
        "diverges from the governed skill registry" in f for f in findings_for(root)["authority"]
    )


def test_kind_outside_the_vocabulary_is_a_finding(tmp_path):
    root = mutate_catalog_entry(
        tmp_path, "governed-stage-implementer", lambda entry: entry.update(kind="banana")
    )
    assert any(
        "kind outside the governed vocabulary" in f for f in findings_for(root)["authority"]
    )


def test_role_outside_the_vocabulary_is_a_finding(tmp_path):
    root = mutate_catalog_entry(
        tmp_path, "governed-stage-implementer", lambda entry: entry.update(role="ROOT")
    )
    assert any(
        "role outside the governed vocabulary" in f for f in findings_for(root)["authority"]
    )


def test_registry_role_drift_is_a_finding(tmp_path):
    root = mutate_catalog_entry(
        tmp_path, "governed-pilot-readiness", lambda entry: entry.update(role="REVIEWER")
    )
    assert any(
        "diverges from the governed skill registry" in f for f in findings_for(root)["authority"]
    )


# -- GR30-R03: the report schema is pinned, not just sampled ---------------------


def test_report_schema_that_drops_report_id_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/governance/report.schema.json"
    schema = json.loads(path.read_text())
    schema["required"].remove("report_id")
    path.write_text(json.dumps(schema, indent=2) + "\n")
    assert any(
        "report schema does not require report_id" in f
        for f in findings_for(root)["report-schema"]
    )


def test_report_outcome_vocabulary_widened_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/governance/report.schema.json"
    schema = json.loads(path.read_text())
    schema["properties"]["outcome"]["enum"].append("SHIPPED")
    path.write_text(json.dumps(schema, indent=2) + "\n")
    assert any(
        "does not pin outcome" in f for f in findings_for(root)["report-schema"]
    )


# -- GR30-R04: warrant fields bind to the modes that exercise them --------------


def test_warrant_field_on_a_mode_that_does_not_exercise_it_is_refused():
    with pytest.raises(jsonschema.ValidationError, match="original_findings"):
        jsonschema.validate(authorization(original_findings=["GR30-R01"]), AUTH_SCHEMA)
    with pytest.raises(jsonschema.ValidationError, match="candidate"):
        jsonschema.validate(authorization(candidate={"candidate_ref": "d2a8e31"}), AUTH_SCHEMA)
    with pytest.raises(jsonschema.ValidationError, match="candidate"):
        jsonschema.validate(
            authorization(
                mode="remediation",
                original_findings=["GR30-R01"],
                candidate={"candidate_ref": "d2a8e31"},
            ),
            AUTH_SCHEMA,
        )
    with pytest.raises(jsonschema.ValidationError, match="original_findings"):
        jsonschema.validate(
            authorization(
                skill="governed-independent-reviewer",
                mode="implementation-review",
                original_findings=["GR30-R01"],
            ),
            AUTH_SCHEMA,
        )
    with pytest.raises(jsonschema.ValidationError, match="original_findings"):
        jsonschema.validate(
            authorization(
                skill="governed-independent-reviewer",
                mode="closure-review",
                candidate={"candidate_ref": "d2a8e31"},
                original_findings=["GR30-R01"],
            ),
            AUTH_SCHEMA,
        )


def test_schema_that_drops_a_warrant_requirement_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/governance/authorization.schema.json"
    schema = json.loads(path.read_text())
    schema["allOf"] = [
        block for block in schema["allOf"] if block.get("then", {}) != {"required": ["original_findings"]}
    ]
    path.write_text(json.dumps(schema, indent=2) + "\n")
    assert any(
        "opens remediation mode without its required original_findings" in f
        for f in findings_for(root)["authorization-schema"]
    )


def test_schema_that_unbinds_warrant_fields_is_a_finding(tmp_path):
    root = governed_copy(tmp_path)
    path = root / ".agents/governance/authorization.schema.json"
    schema = json.loads(path.read_text())
    schema["allOf"] = [
        block for block in schema["allOf"] if "not" not in block.get("then", {})
    ]
    path.write_text(json.dumps(schema, indent=2) + "\n")
    assert any(
        "accepts candidate on remediation mode" in f
        for f in findings_for(root)["authorization-schema"]
    )
