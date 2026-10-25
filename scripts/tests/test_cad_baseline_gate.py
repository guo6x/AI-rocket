"""CAD current-authority gate: success does not mean CAD has been designed."""
from copy import deepcopy

import pytest

from scripts.cad_baseline_gate import CadAuthorityError, audit, run


def fixture_records():
    authority = {
        "status": "NOT_STARTED",
        "cad_start_status": "BLOCKED_BY_MEASUREMENT",
        "accepted_geometry": None,
        "accepted_assembly": None,
        "accepted_drawings": [],
        "manufacturing_release": False,
        "flight_qualification": False,
        "legacy_policy": {
            "classification": "REJECTED_FOR_CURRENT_DESIGN",
            "current_design_sources": [],
            "may_supply_actual_dimensions_or_manufacturing_authority": False,
        },
        "current_article": "AA-TVC-BENCH-001",
    }
    plan = {
        "article_id": "AA-TVC-BENCH-001",
        "measurements": [
            {"measurement_id": "M-EDF", "status": "MISSING", "evidence_refs": []},
            {"measurement_id": "M-SERVO", "status": "MISSING", "evidence_refs": []},
        ],
    }
    intake = {
        "article_id": "AA-TVC-BENCH-001",
        "concept_intake": {"status": "BLOCKED", "blockers": ["M-EDF", "M-SERVO"]},
    }
    return authority, plan, intake


def test_missing_cad_is_honest_success_without_a_cad_pass():
    result = audit(*fixture_records())
    assert result["audit"] == "PASS"
    assert result["cad_status"] == "NOT_STARTED"
    assert result["cad_start"] == "BLOCKED"
    assert result["missing_count"] == 2
    assert result["manufacturing_release"] == "NOT_AUTHORIZED"


@pytest.mark.parametrize("field,value", [
    ("status", "TESTED_SOFTWARE"),
    ("cad_start_status", "READY"),
    ("accepted_geometry", "old-rocket.step"),
    ("accepted_assembly", "pro_outputs/full_assembly.step"),
    ("manufacturing_release", True),
    ("flight_qualification", True),
    ("accepted_drawings", ["old.dxf"]),
])
def test_fabricated_cad_authority_fails(field, value):
    authority, plan, intake = fixture_records()
    authority[field] = value
    with pytest.raises(CadAuthorityError):
        audit(authority, plan, intake)


def test_legacy_promoted_to_design_is_rejected():
    authority, plan, intake = fixture_records()
    authority["legacy_policy"]["current_design_sources"] = ["outputs/full_assembly.step"]
    with pytest.raises(CadAuthorityError):
        audit(authority, plan, intake)


def test_missing_measurement_identifier_is_fatal():
    authority, plan, intake = fixture_records()
    intake["concept_intake"]["blockers"].append("NOT-IN-PLAN")
    with pytest.raises(CadAuthorityError):
        audit(authority, plan, intake)


def test_recorded_measurement_without_evidence_is_rejected():
    authority, plan, intake = fixture_records()
    plan["measurements"][0]["status"] = "RECORDED"
    with pytest.raises(CadAuthorityError):
        audit(authority, plan, intake)


def test_inconsistent_ready_evidence_requires_rebaseline():
    authority, plan, intake = fixture_records()
    for row in plan["measurements"]:
        row["status"] = "RECORDED"
        row["evidence_refs"] = ["evidence/measurement.jpg"]
    with pytest.raises(CadAuthorityError):
        audit(authority, plan, intake)


def test_real_repo_remains_truthfully_blocked():
    result = run()
    assert result["cad_status"] == "NOT_STARTED"
    assert result["cad_start"] == "BLOCKED"
    assert result["missing_count"] > 0
