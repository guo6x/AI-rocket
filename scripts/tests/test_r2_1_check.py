"""Isolated, software-only mutation tests for the R2.1 authority gate."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from scripts.r2_1_check import (
    PROHIBITED_PROPULSION_WORK,
    evaluate_documents,
    load_documents,
    main,
    validate,
)


@pytest.fixture
def documents():
    return {
        "assets": {
            "schema_version": 1,
            "source_basis": [{"id": "SRC-PURCHASE-TEST", "type": "USER_PURCHASE_RECORD"}],
            "assets": [
                {
                    "asset_id": "AST-CONTROLLER-001", "item": "controller", "quantity": 1,
                    "ownership": "OWNED", "ownership_evidence": "SRC-PURCHASE-TEST",
                    "verification": "PURCHASE_CONFIRMED", "assignment": "CANDIDATE",
                    "candidate_lines": ["GNC"],
                },
                {
                    "asset_id": "AST-SERVO-001", "item": "servo", "quantity": 2,
                    "unit_ids": ["AST-SERVO-U1", "AST-SERVO-U2"],
                    "ownership": "OWNED", "ownership_evidence": "SRC-PURCHASE-TEST",
                    "verification": "CONFIGURATION_UNVERIFIED", "assignment": "CANDIDATE",
                    "candidate_lines": ["GNC"],
                },
            ],
            "excluded_transactions": [
                {"record_id": "TX-CLOSED-001", "item": "closed cable", "reason": "closed"},
            ],
        },
        "lines": {
            "schema_version": 1,
            "lines": [
                {"line_id": "GNC", "article_id": "AA-GNC-001", "current_assets": ["AST-CONTROLLER-001", "AST-SERVO-001"], "status": "REBASELINE_REQUIRED"},
                {"line_id": "MATERIALS_PROPULSION_SCIENCE", "article_id": "AA-SCIENCE-001", "current_assets": [], "status": "FOUNDATIONAL_ONLY", "prohibited_work": list(PROHIBITED_PROPULSION_WORK)},
            ],
            "priority_order": ["GNC", "MATERIALS_PROPULSION_SCIENCE"],
        },
        "baseline": {
            "schema_version": 2,
            "project_development_model": {"technical_lines": [
                {"line_id": "GNC", "article_id": "AA-GNC-001"},
                {"line_id": "MATERIALS_PROPULSION_SCIENCE", "article_id": "AA-SCIENCE-001"},
            ]},
        },
        "plan": {
            "schema_version": 1,
            "applies_to": ["AA-GNC-001"],
            "stages": [
                {"stage_id": "S0-AUDIT", "physical_action": False, "status": "COMPLETE_SOFTWARE", "depends_on": []},
                {"stage_id": "S1-COMPATIBILITY", "physical_action": False, "status": "COMPLETE_SOFTWARE", "depends_on": ["S0-AUDIT"]},
                {"stage_id": "S2-OBSERVATION", "physical_action": True, "status": "PENDING_HARDWARE", "depends_on": ["S1-COMPATIBILITY"]},
                {"stage_id": "S3-REGRESSION", "physical_action": True, "status": "PENDING_HARDWARE", "depends_on": ["S2-OBSERVATION"]},
            ],
        },
        "historical": {
            "schema_version": 1,
            "capabilities": [
                {"capability_id": "HWCAP-FLASH-001", "historical_level": "HISTORICALLY_REPORTED_HARDWARE", "historical_sources": ["historical report"], "current_code_continuity": True, "current_sources": ["flight_computer/src/main.cpp"]},
                {"capability_id": "HWCAP-LORA-001", "historical_level": "NOT_FOUND", "historical_sources": ["future-plan reference"], "current_code_continuity": False, "current_sources": []},
            ],
        },
    }


def errors(documents, tmp_path):
    return evaluate_documents(documents, tmp_path)


def test_pending_hardware_without_any_physical_records_passes(documents, tmp_path):
    assert errors(documents, tmp_path) == []


@pytest.mark.parametrize("section, field, expected", [
    ("assets", "assets", "asset_id"),
    ("assets", "source_basis", "source id"),
    ("assets", "excluded_transactions", "record_id"),
    ("lines", "lines", "line_id"),
    ("plan", "stages", "stage_id"),
    ("historical", "capabilities", "capability_id"),
])
def test_duplicate_ids_are_rejected(documents, tmp_path, section, field, expected):
    documents[section][field].append(deepcopy(documents[section][field][0]))
    assert any(expected in item and "duplicate" in item for item in errors(documents, tmp_path))


def test_duplicate_article_ids_are_rejected(documents, tmp_path):
    documents["lines"]["lines"][1]["article_id"] = "AA-GNC-001"
    assert any("duplicate article_id" in item for item in errors(documents, tmp_path))


def test_unit_ids_are_unique_across_assets(documents, tmp_path):
    documents["assets"]["assets"][0]["unit_ids"] = ["AST-SERVO-U1"]
    assert any("duplicate asset/unit id" in item for item in errors(documents, tmp_path))


@pytest.mark.parametrize("quantity", [True, False, 0, -1, "2", 1.5, None, []])
def test_quantity_requires_positive_integer_not_bool(documents, tmp_path, quantity):
    documents["assets"]["assets"][0]["quantity"] = quantity
    assert any("quantity must be a positive integer" in item for item in errors(documents, tmp_path))


def test_unit_count_matches_quantity(documents, tmp_path):
    documents["assets"]["assets"][1]["quantity"] = 1
    assert any("unit_ids count" in item for item in errors(documents, tmp_path))


def test_closed_transaction_cannot_be_ownership_source(documents, tmp_path):
    documents["assets"]["assets"][0]["ownership_evidence"] = "TX-CLOSED-001"
    assert any("excluded/closed transaction" in item for item in errors(documents, tmp_path))


def test_source_marked_closed_cannot_prove_ownership(documents, tmp_path):
    documents["assets"]["source_basis"][0]["transaction_status"] = "CANCELLED"
    assert any("excluded/closed transaction" in item for item in errors(documents, tmp_path))


def test_closed_source_record_reference_cannot_be_laundered(documents, tmp_path):
    documents["assets"]["source_basis"][0]["record_id"] = "TX-CLOSED-001"
    assert any("excluded/closed transaction" in item for item in errors(documents, tmp_path))


def test_excluded_item_cannot_be_owned_by_renaming_asset_id(documents, tmp_path):
    documents["assets"]["assets"][0]["item"] = "closed cable"
    assert any("excluded/closed transaction" in item for item in errors(documents, tmp_path))


def test_ownership_evidence_must_resolve_declared_source(documents, tmp_path):
    documents["assets"]["assets"][0]["ownership_evidence"] = "SRC-NOT-FOUND"
    assert any("unknown ownership_evidence" in item for item in errors(documents, tmp_path))


@pytest.mark.parametrize("field", ["verification", "status", "evidence_class"])
def test_owned_or_purchased_asset_does_not_imply_verified_hardware(documents, tmp_path, field):
    documents["assets"]["assets"][0][field] = "VERIFIED_HARDWARE"
    assert any("purchase/ownership cannot establish VERIFIED_HARDWARE" in item for item in errors(documents, tmp_path))


def test_every_line_asset_reference_resolves(documents, tmp_path):
    documents["lines"]["lines"][0]["current_assets"].append("AST-UNKNOWN")
    assert any("unknown asset AST-UNKNOWN" in item for item in errors(documents, tmp_path))


def test_excluded_asset_cannot_be_assigned_to_line(documents, tmp_path):
    documents["assets"]["assets"][0]["ownership"] = "EXCLUDED_CLOSED_TRANSACTION"
    assert any("excluded asset" in item for item in errors(documents, tmp_path))


def test_baseline_article_mapping_must_match_line_authority(documents, tmp_path):
    documents["baseline"]["project_development_model"]["technical_lines"][0]["article_id"] = "AA-WRONG-001"
    assert any("baseline technical_lines must match" in item for item in errors(documents, tmp_path))


@pytest.mark.parametrize("index", range(4))
def test_each_propulsion_safety_boundary_is_mandatory(documents, tmp_path, index):
    del documents["lines"]["lines"][1]["prohibited_work"][index]
    assert any("prohibited_work missing" in item for item in errors(documents, tmp_path))


def test_propulsion_line_itself_cannot_disappear(documents, tmp_path):
    del documents["lines"]["lines"][1]
    assert any("MATERIALS_PROPULSION_SCIENCE line is required" in item for item in errors(documents, tmp_path))


def test_prohibited_work_cannot_be_reintroduced_as_allowed_work(documents, tmp_path):
    documents["lines"]["lines"][1]["allowed_next_work"] = [PROHIBITED_PROPULSION_WORK[0]]
    assert any("conflicts with prohibited_work" in item for item in errors(documents, tmp_path))


@pytest.mark.parametrize("value", [None, {}, "S0-AUDIT", True])
def test_dependencies_require_explicit_list(documents, tmp_path, value):
    documents["plan"]["stages"][1]["depends_on"] = value
    assert any("depends_on must be a list" in item for item in errors(documents, tmp_path))


def test_missing_dependency_list_is_rejected(documents, tmp_path):
    del documents["plan"]["stages"][1]["depends_on"]
    assert any("depends_on must be a list" in item for item in errors(documents, tmp_path))


def test_unknown_dependency_is_rejected(documents, tmp_path):
    documents["plan"]["stages"][1]["depends_on"] = ["S-NOT-FOUND"]
    assert any("unknown prerequisite" in item for item in errors(documents, tmp_path))


def test_future_dependency_and_cycle_are_rejected(documents, tmp_path):
    documents["plan"]["stages"][0]["depends_on"] = ["S1-COMPATIBILITY"]
    result = errors(documents, tmp_path)
    assert any("must precede" in item for item in result)
    assert any("dependency cycle" in item for item in result)


def test_software_cannot_complete_before_physical_prerequisite(documents, tmp_path):
    documents["plan"]["stages"].append({
        "stage_id": "S4-SOFTWARE", "physical_action": False,
        "status": "COMPLETE_SOFTWARE", "depends_on": ["S3-REGRESSION"],
    })
    assert any("unsatisfied prerequisite S3-REGRESSION" in item for item in errors(documents, tmp_path))


def test_physical_action_flag_must_be_boolean(documents, tmp_path):
    documents["plan"]["stages"][2]["physical_action"] = "false"
    assert any("physical_action must be boolean" in item for item in errors(documents, tmp_path))


def test_physical_stage_cannot_use_software_complete_status(documents, tmp_path):
    documents["plan"]["stages"][2]["status"] = "COMPLETE_SOFTWARE"
    assert any("physical stage has invalid status" in item for item in errors(documents, tmp_path))


@pytest.mark.parametrize("status", ["READY", "COMPLETED"])
def test_physical_ready_or_complete_needs_evidence(documents, tmp_path, status):
    documents["plan"]["stages"][2]["status"] = status
    assert any("requires current evidence_records" in item for item in errors(documents, tmp_path))


def test_pending_physical_stage_still_requires_explicit_prerequisite(documents, tmp_path):
    documents["plan"]["stages"][2]["depends_on"] = []
    assert any("physical stage requires at least one explicit earlier prerequisite" in item for item in errors(documents, tmp_path))


def attach_record(documents, tmp_path, stage_index=2, outcome="PRECONDITIONS_SATISFIED"):
    stage = documents["plan"]["stages"][stage_index]
    records = tmp_path / "engineering/evidence/records"
    records.mkdir(parents=True, exist_ok=True)
    raw_path = records / f"{stage['stage_id']}.log"
    raw_path.write_text("controlled synthetic test fixture, not hardware evidence\n", encoding="utf-8")
    record = {
        "schema_version": 1, "record_id": f"OBS-{stage['stage_id']}",
        "record_type": "hardware_observation", "stage_id": stage["stage_id"],
        "article_id": "AA-GNC-001", "date": "2026-10-23", "operator": "test fixture",
        "method": "synthetic unit test", "tool": "pytest", "source_commit": "a" * 40,
        "outcome": outcome, "observations": ["synthetic fixture only"],
        "artifact_refs": [{"path": raw_path.relative_to(tmp_path).as_posix(), "sha256": sha256(raw_path.read_bytes()).hexdigest()}],
    }
    record_path = records / f"{stage['stage_id']}.yaml"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
    stage["evidence_records"] = [{"path": record_path.relative_to(tmp_path).as_posix(), "sha256": sha256(record_path.read_bytes()).hexdigest()}]
    return record, record_path


def save_record(stage, record, record_path):
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
    stage["evidence_records"][0]["sha256"] = sha256(record_path.read_bytes()).hexdigest()


def test_ready_accepts_hashed_stage_bound_precondition_record(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    attach_record(documents, tmp_path)
    assert errors(documents, tmp_path) == []


def test_completed_accepts_hashed_stage_bound_pass_record(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "COMPLETED"
    attach_record(documents, tmp_path, outcome="PASS")
    assert errors(documents, tmp_path) == []


def test_ready_physical_cannot_omit_all_software_prerequisites(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    stage["depends_on"] = []
    attach_record(documents, tmp_path)
    assert any("active physical path requires a completed software ancestor" in item for item in errors(documents, tmp_path))


def test_skipped_software_ancestor_cannot_authorize_physical_ready(documents, tmp_path):
    documents["plan"]["stages"][0].update(status="NOT_REQUIRED", optional=True, not_required_reason="synthetic skipped software")
    documents["plan"]["stages"][1].update(status="NOT_REQUIRED", optional=True, not_required_reason="synthetic skipped software")
    documents["plan"]["stages"][2]["status"] = "READY"
    attach_record(documents, tmp_path)
    assert any("active physical path requires a completed software ancestor" in item for item in errors(documents, tmp_path))


def test_evidence_does_not_override_unsatisfied_prerequisites(documents, tmp_path):
    documents["plan"]["stages"][3]["status"] = "READY"
    attach_record(documents, tmp_path, stage_index=3)
    assert any("unsatisfied prerequisite S2-OBSERVATION" in item for item in errors(documents, tmp_path))


@pytest.mark.parametrize("path", ["../outside.yaml", "C:/outside.yaml", "/outside.yaml", "engineering/evidence/templates/fake.yaml", "engineering/evidence/records/../../outside.yaml", "engineering\\evidence\\records\\fake.yaml"])
def test_record_path_must_be_confined_repository_relative(documents, tmp_path, path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    stage["evidence_records"] = [{"path": path, "sha256": "a" * 64}]
    assert any("confined" in item for item in errors(documents, tmp_path))


def test_missing_record_is_rejected_even_if_hash_looks_valid(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    stage["evidence_records"] = [{"path": "engineering/evidence/records/missing.yaml", "sha256": "a" * 64}]
    assert any("file does not exist" in item for item in errors(documents, tmp_path))


def test_record_content_hash_must_match(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    attach_record(documents, tmp_path)
    stage["evidence_records"][0]["sha256"] = "0" * 64
    assert any("SHA-256 mismatch" in item for item in errors(documents, tmp_path))


@pytest.mark.parametrize("field, value, expected", [
    ("source_commit", "main", "source_commit must be an exact 40"),
    ("source_commit", True, "source_commit must be an exact 40"),
    ("stage_id", "S-WRONG", "stage_id must match"),
    ("article_id", "AA-WRONG", "article_id must be in applies_to"),
    ("date", "2026-02-30", "date must be an ISO"),
    ("operator", "", "operator must be a nonempty string"),
    ("record_type", "USER_PURCHASE_RECORD", "record_type must be current"),
    ("observations", [], "observations must not be empty"),
    ("artifact_refs", [], "artifact_refs must not be empty"),
    ("schema_version", True, "schema_version must be integer 1"),
])
def test_invalid_evidence_metadata_fails_closed(documents, tmp_path, field, value, expected):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    record, path = attach_record(documents, tmp_path)
    record[field] = value
    save_record(stage, record, path)
    assert any(expected in item for item in errors(documents, tmp_path))


def test_completed_needs_actual_pass_not_only_preconditions(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "COMPLETED"
    attach_record(documents, tmp_path)
    assert any("COMPLETED requires outcome PASS" in item for item in errors(documents, tmp_path))


def test_raw_artifact_content_hash_must_match(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    record, path = attach_record(documents, tmp_path)
    record["artifact_refs"][0]["sha256"] = "0" * 64
    save_record(stage, record, path)
    assert any("SHA-256 mismatch" in item for item in errors(documents, tmp_path))


def test_lora_cannot_inherit_wifi_historical_verification(documents, tmp_path):
    documents["historical"]["capabilities"][1]["historical_level"] = "HISTORICALLY_REPORTED_HARDWARE"
    assert any("LoRa has no historical physical-link evidence" in item for item in errors(documents, tmp_path))


@pytest.mark.parametrize("section, field, value", [
    ("assets", "assets", {}), ("assets", "assets", [True]),
    ("lines", "lines", "GNC"), ("plan", "stages", [None]),
    ("historical", "capabilities", [42]),
])
def test_malformed_containers_return_actionable_errors_not_exceptions(documents, tmp_path, section, field, value):
    documents[section][field] = value
    assert errors(documents, tmp_path)


@pytest.mark.parametrize("section, field, index, key", [
    ("assets", "source_basis", 0, "record_id"),
    ("assets", "source_basis", 0, "transaction_status"),
    ("assets", "assets", 0, "ownership"),
    ("assets", "assets", 0, "verification"),
    ("assets", "assets", 0, "assignment"),
    ("lines", "lines", 0, "status"),
    ("plan", "stages", 0, "status"),
    ("historical", "capabilities", 0, "historical_level"),
])
@pytest.mark.parametrize("malformed", [{"not": "a scalar"}, []])
def test_unhashable_statuses_and_ids_fail_closed(documents, tmp_path, section, field, index, key, malformed):
    documents[section][field][index][key] = malformed
    assert errors(documents, tmp_path)


def test_unhashable_evidence_record_type_fails_closed(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    record, path = attach_record(documents, tmp_path)
    record["record_type"] = ["hardware_observation"]
    save_record(stage, record, path)
    assert any("record_type must be current" in item for item in errors(documents, tmp_path))


def test_not_required_needs_explicit_historical_delta_justification(documents, tmp_path):
    documents["plan"]["stages"][2]["status"] = "NOT_REQUIRED"
    assert any("not_required_reason" in item for item in errors(documents, tmp_path))


def test_documented_optional_detection_does_not_fabricate_current_evidence(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["stage_id"] = "S3-PROGRAMMER-DETECTION-IF_REQUIRED"
    documents["plan"]["stages"][3]["depends_on"] = [stage["stage_id"]]
    stage["status"] = "NOT_REQUIRED"
    stage["optional"] = True
    stage["not_required_reason"] = "Historical unchanged behavior; no present decision requires repeat."
    assert errors(documents, tmp_path) == []


def test_mandatory_sensor_regression_cannot_be_bypassed_as_not_required(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "NOT_REQUIRED"
    stage["optional"] = True
    stage["not_required_reason"] = "A label cannot waive current sensor-validity evidence."
    assert any("mandatory physical" in item for item in errors(documents, tmp_path))


def test_unhashable_evidence_record_id_fails_closed(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    record, path = attach_record(documents, tmp_path)
    record["record_id"] = []
    save_record(stage, record, path)
    assert any("record_id must be a nonempty string" in item for item in errors(documents, tmp_path))


def test_pending_software_evidence_files_are_checked_when_declared(documents, tmp_path):
    documents["plan"]["stages"][0]["software_evidence"] = ["docs/missing.md"]
    assert any("software evidence file does not exist" in item for item in errors(documents, tmp_path))


def test_existing_confined_software_evidence_is_accepted(documents, tmp_path):
    software_path = tmp_path / "audit.md"
    software_path.write_text("controlled synthetic software artifact", encoding="utf-8")
    documents["plan"]["stages"][0]["software_evidence"] = ["audit.md"]
    assert errors(documents, tmp_path) == []


def test_software_evidence_cannot_escape_repository(documents, tmp_path):
    documents["plan"]["stages"][0]["software_evidence"] = ["../outside.md"]
    assert any("confined repository-relative" in item for item in errors(documents, tmp_path))


def test_evidence_symlink_cannot_escape_records(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    _, path = attach_record(documents, tmp_path)
    outside = tmp_path / "outside.yaml"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("Creating symlinks requires Windows Developer Mode or symlink privilege")
    assert any("confined" in item for item in errors(documents, tmp_path))


def test_evidence_resolve_errors_fail_closed(documents, tmp_path, monkeypatch):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    _, path = attach_record(documents, tmp_path)
    original_resolve = Path.resolve

    def failing_resolve(self, *args, **kwargs):
        if self.name == path.name:
            raise OSError("synthetic resolve failure")
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", failing_resolve)
    assert any("cannot be resolved safely" in item for item in errors(documents, tmp_path))


def test_raw_artifact_path_cannot_escape_records(documents, tmp_path):
    stage = documents["plan"]["stages"][2]
    stage["status"] = "READY"
    record, path = attach_record(documents, tmp_path)
    record["artifact_refs"][0]["path"] = "../outside.log"
    save_record(stage, record, path)
    assert any("confined" in item for item in errors(documents, tmp_path))


def test_stage_cannot_reuse_another_stages_evidence_record(documents, tmp_path):
    first = documents["plan"]["stages"][2]
    first["status"] = "COMPLETED"
    attach_record(documents, tmp_path, outcome="PASS")
    second = documents["plan"]["stages"][3]
    second["status"] = "READY"
    second["evidence_records"] = deepcopy(first["evidence_records"])
    result = errors(documents, tmp_path)
    assert any("stage_id must match S3-REGRESSION" in item for item in result)
    assert any("duplicate physical evidence record_id" in item for item in result)


def test_errors_are_deterministic_sorted_and_unique(documents, tmp_path):
    documents["assets"]["assets"][0]["quantity"] = True
    documents["plan"]["stages"][2]["status"] = "COMPLETED"
    result = errors(documents, tmp_path)
    assert result == sorted(set(result))
    assert result == errors(deepcopy(documents), tmp_path)


PATHS = {
    "assets": "engineering/assets/project-asset-registry.yaml",
    "lines": "engineering/experimental-lines.yaml",
    "baseline": "engineering/current-baseline.yaml",
    "plan": "engineering/bringup/gnc-avionics-bringup.yaml",
    "historical": "engineering/historical-hardware-capabilities.yaml",
}


def write_documents(documents, tmp_path):
    for name, relative in PATHS.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(documents[name]), encoding="utf-8")


def test_duplicate_yaml_keys_fail_closed(documents, tmp_path):
    write_documents(documents, tmp_path)
    path = tmp_path / PATHS["assets"]
    path.write_text(path.read_text(encoding="utf-8") + "\nschema_version: 1\n", encoding="utf-8")
    assert any("duplicate YAML key" in item for item in validate(tmp_path))


def test_non_string_yaml_key_fails_closed(documents, tmp_path):
    write_documents(documents, tmp_path)
    path = tmp_path / PATHS["assets"]
    path.write_text(path.read_text(encoding="utf-8") + "\ntrue: wrong\n", encoding="utf-8")
    assert any("YAML mapping keys must be strings" in item for item in validate(tmp_path))


def test_recursive_yaml_alias_fails_closed(documents, tmp_path):
    write_documents(documents, tmp_path)
    path = tmp_path / PATHS["assets"]
    path.write_text(path.read_text(encoding="utf-8") + "\ncycle: &cycle [*cycle]\n", encoding="utf-8")
    assert any("recursive YAML alias" in item for item in validate(tmp_path))


def test_missing_authority_file_is_actionable(tmp_path):
    assert any("missing required R2.1 authority" in item for item in validate(tmp_path))


def test_documents_load_independently_from_working_directory(documents, tmp_path):
    write_documents(documents, tmp_path)
    assert load_documents(tmp_path) == documents
    assert validate(tmp_path) == []


def test_json_cli_is_deterministic_and_does_not_claim_hardware_success(documents, tmp_path, capsys):
    write_documents(documents, tmp_path)
    assert main(["--root", str(tmp_path), "--json"]) == 0
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["structure_status"] == "PASS"
    assert result["hardware_status"] == "NOT_EVALUATED"
    assert result["errors"] == []
    assert main(["--root", str(tmp_path), "--json"]) == 0
    assert capsys.readouterr().out == output


def test_text_cli_distinguishes_structure_from_physical_readiness(documents, tmp_path, capsys):
    write_documents(documents, tmp_path)
    assert main(["--root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "R2.1 STRUCTURE CHECK: PASS" in output
    assert "Hardware verification: NOT_EVALUATED" in output


def test_cli_invalid_data_returns_nonzero_and_not_evaluated(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--json"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["structure_status"] == "FAIL"
    assert result["hardware_status"] == "NOT_EVALUATED"
    assert result["errors"]
