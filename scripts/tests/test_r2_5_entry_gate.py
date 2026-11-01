"""No-hardware mutation tests for R2.5 GNC/avionics handoff."""
from copy import deepcopy
import pytest
from scripts.r2_5_entry_gate import FIRST_BOUNDARY, evaluate, build_report, ROOT

@pytest.fixture
def authority():
    return {
        "assets": {"assets": [
            {"asset_id": "AST-MCU-APM32-001", "ownership": "OWNED"},
            {"asset_id": "AST-SENSOR-GY91-001", "ownership": "OWNED"},
            {"asset_id": "AST-SERVO-SG92R-001", "ownership": "OWNED",
             "quantity": 2, "unit_ids": ["U1", "U2"]},
        ]},
        "lines": {"lines": [
            {"line_id": "GNC", "current_assets": [
                "AST-MCU-APM32-001", "AST-SENSOR-GY91-001", "AST-SERVO-SG92R-001"]},
            {"line_id": "AVIONICS", "current_assets": []},
        ]},
        "plan": {"stages": [
            *({"stage_id": s, "status": "COMPLETE_SOFTWARE", "physical_action": False}
              for s in ("S0-HISTORICAL-EVIDENCE-RECOVERY", "S1-ASSET-AND-TARGET-RECONCILIATION",
                        "S2-MINIMUM-REGRESSION-PLAN", "S2B-GNC-ONLY-BENCH-SOFTWARE-ISOLATION")),
            {"stage_id": FIRST_BOUNDARY, "status": "PENDING_HARDWARE", "physical_action": True,
             "energy_scope": "unpowered observation only",
             "depends_on": ["S2-MINIMUM-REGRESSION-PLAN"],
             "owner": "HUMAN_EXECUTION_WITH_CODEX_GUIDANCE",
             "required_evidence": ["one clear unpowered photo"], "evidence_records": []},
            {"stage_id": "S3-PROGRAMMER-DETECTION-IF_REQUIRED",
             "status": "PENDING_HARDWARE", "physical_action": True,
             "depends_on": [FIRST_BOUNDARY], "evidence_records": []},
        ]},
        "baseline": {"current_blockers": [{"id": "R2_1-005"}]},
        "cad": {"status": "NOT_STARTED", "cad_start_status": "BLOCKED_BY_MEASUREMENT",
                "manufacturing_release": False},
        "measurements": {"measurements": [
            {"measurement_id": "M-P0-EDF-01", "required_for": ["CAD_START"], "status": "MISSING"},
            {"measurement_id": "M-P0-SERVO-01", "required_for": ["CAD_START"], "status": "MISSING"},
            {"measurement_id": "M-NON-CAD-01", "required_for": ["ARTICLE_INTEGRATION"], "status": "MISSING"},
        ]},
    }

def test_nominal_registry_earns_only_unpowered_human_handoff(authority):
    result = evaluate(authority)
    assert result["result"] == "PASS_PREPARATION_ONLY"
    assert result["first_human_boundary"]["stage_id"] == FIRST_BOUNDARY
    assert result["first_human_boundary"]["energy_scope"] == "unpowered observation only"
    assert not result["powered_bench_authorized"]
    assert not result["hardware_verified"]
    assert not result["physical_actions_performed"]
    assert result["external_gate"] == "BLOCKED_BY_EXTERNAL_EVIDENCE"
    assert result["cad"]["missing_cad_start_count"] == 2
    assert result["cad"]["manufacturing_release"] is False

def test_missing_recovery_blocker_is_rejected(authority):
    authority["baseline"]["current_blockers"] = []
    result = evaluate(authority)
    assert result["result"] == "FAIL_AUTHORITY_CHECK"
    assert result["recovery"] == "NOT_ESTABLISHED"
    assert result["first_human_boundary"] is None

def test_purchase_record_cannot_be_upgraded_into_hardware_evidence(authority):
    authority["plan"]["stages"][-2]["status"] = "COMPLETED"
    result = evaluate(authority)
    assert "Unpowered observation cannot be completed without physical evidence records" in result["errors"]
    assert not result["hardware_verified"]

def test_promoting_powered_hardware_stage_without_evidence_fails(authority):
    authority["plan"]["stages"][-1]["status"] = "READY"
    result = evaluate(authority)
    assert any("hardware promotion lacks evidence records" in e for e in result["errors"])
    assert not result["powered_bench_authorized"]

@pytest.mark.parametrize("missing", ["AST-MCU-APM32-001", "AST-SENSOR-GY91-001", "AST-SERVO-SG92R-001"])
def test_missing_owned_candidate_fail_closed(authority, missing):
    for asset in authority["assets"]["assets"]:
        if asset["asset_id"] == missing:
            asset["ownership"] = "EXCLUDED_CLOSED_TRANSACTION"
    result = evaluate(authority)
    assert result["result"] == "FAIL_AUTHORITY_CHECK"
    assert result["first_human_boundary"] is None

@pytest.mark.parametrize("bad_units", [["U1", "U1"], ["U1"], []])
def test_servo_unit_identity_must_be_distinct(authority, bad_units):
    authority["assets"]["assets"][-1]["unit_ids"] = bad_units
    assert any("two-servo" in e for e in evaluate(authority)["errors"])

def test_cad_promotion_while_missing_measurements_fails(authority):
    authority["cad"]["status"] = "READY"
    authority["cad"]["cad_start_status"] = "READY"
    assert any("CAD authority promoted" in e for e in evaluate(authority)["errors"])

def test_authority_validation_errors_surface_and_block_handoff(authority):
    result = evaluate(authority, authority_errors=["r2_1_check found unbound evidence"])
    assert result["result"] == "FAIL_AUTHORITY_CHECK"
    assert result["first_human_boundary"] is None

def test_software_preparation_not_completed_blocks_handoff(authority):
    authority["plan"]["stages"][0]["status"] = "PENDING_SOFTWARE"
    result = evaluate(authority)
    assert result["software_preparation"] == "INCOMPLETE"
    assert result["first_human_boundary"] is None

def test_first_physical_gate_must_remain_unpowered(authority):
    authority["plan"]["stages"][-2]["energy_scope"] = "servo power allowed"
    result = evaluate(authority)
    assert result["result"] == "FAIL_AUTHORITY_CHECK"
    assert result["first_human_boundary"] is None

def test_evaluation_is_deterministic_and_does_not_mutate(authority):
    before = deepcopy(authority)
    assert evaluate(authority) == evaluate(authority)
    assert authority == before

def test_conditional_cad_measurement_is_not_an_unconditional_blocker(authority):
    authority["measurements"]["measurements"].append({
        "measurement_id": "M-P0-STRUCT-02",
        "required_for": ["CAD_START"], "status": "MISSING",
        "condition": {"type": "ANY_COMPONENT_PRESENT_AND_REUSED"},
    })
    result = evaluate(authority)
    assert result["cad"]["missing_cad_start_count"] == 2
    assert result["cad"]["conditional_cad_start_not_evaluated_ids"] == ["M-P0-STRUCT-02"]


def test_repository_authorities_generate_only_preparation_report():
    report = build_report(ROOT)
    assert report["result"] == "PASS_PREPARATION_ONLY", report["errors"]
    assert report["first_human_boundary"]["stage_id"] == FIRST_BOUNDARY
    assert report["cad"]["missing_cad_start_count"] == 19
    assert report["recovery"] == "BLOCKED_UNREACHABLE_THRESHOLD"
    assert not report["powered_bench_authorized"]
    assert not report["hardware_verified"]
    assert len(report["input_sha256"]) == 6
