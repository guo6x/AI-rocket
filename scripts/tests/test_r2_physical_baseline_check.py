import json

import pytest

from scripts import r2_physical_baseline_check as checker
from scripts.r2_physical_baseline_check import (
    GATES,
    GateResult,
    build_report,
    clone_documents,
    evaluate_documents,
    load_documents,
    main,
)


OBSERVATION_ID = "OBS-TEST-001"


def add_evidence(documents, record_id=OBSERVATION_ID):
    documents["evidence"]["evidence_records"].append(
        {
            "record_id": record_id,
            "record_type": "test_observation",
            "article_id": "AA-TVC-BENCH-001",
        }
    )


def measurement(documents, measurement_id):
    return next(
        item
        for item in documents["plan"]["measurements"]
        if item["measurement_id"] == measurement_id
    )


def component(documents, component_id):
    return next(
        item
        for item in documents["inventory"]["components"]
        if item["component_id"] == component_id
    )


def complete(documents, measurement_id, evidence_id=OBSERVATION_ID):
    item = measurement(documents, measurement_id)
    item["status"] = "RECORDED"
    item["evidence_refs"] = [evidence_id]


def observe_photo_inventory(documents, frame_status="NOT_PRESENT", frame_reuse="NOT_REUSE"):
    add_evidence(documents)
    inventory_measurement = measurement(documents, "M-P0-STRUCT-01")
    for component_id in inventory_measurement["component_ids"]:
        item = component(documents, component_id)
        item["ownership_status"] = (
            "CONFIRMED_PRESENT"
            if component_id in {
                "CMP-EDF-001",
                "CMP-TVC-SERVO-PITCH-001",
                "CMP-TVC-SERVO-ROLL-001",
            }
            else "NOT_PRESENT"
        )
        item["evidence_class"] = "OBSERVED"
        item["evidence_source"] = [OBSERVATION_ID]
        item["reuse_intent"] = "NOT_REUSE"
    frame = component(documents, "CMP-FRAME-TUBE-001")
    frame["ownership_status"] = frame_status
    frame["reuse_intent"] = frame_reuse
    complete(documents, "M-P0-STRUCT-01")


def complete_cad_start(documents, except_ids=()):
    except_ids = set(except_ids)
    for item in documents["plan"]["measurements"]:
        if "CAD_START" in item["required_for"] and not item.get("condition"):
            if item["measurement_id"] not in except_ids:
                complete(documents, item["measurement_id"])


def fresh_documents():
    return clone_documents(load_documents())


def synchronize_intake(documents):
    _, gates = evaluate_documents(documents)
    concept = documents["intake"]["concept_intake"]
    concept_blockers = gates.union(concept["required_gates"])
    concept["blockers"] = list(concept_blockers)
    concept["status"] = "BLOCKED" if concept_blockers else "READY"
    review = documents["intake"]["design_review_intake"]
    review_blockers = gates.union(review["required_gates"])
    review["status"] = "BLOCKED" if review_blockers else "READY"


def test_missing_power_envelope_does_not_block_cad_start():
    documents = fresh_documents()
    observe_photo_inventory(documents)
    complete_cad_start(documents)
    synchronize_intake(documents)
    errors, gates = evaluate_documents(documents)
    assert errors == []
    assert "M-P0-POWER-02" not in gates.blockers["CAD_START"]
    assert gates.status("CAD_START") == "READY"


def test_missing_stm32_envelope_does_not_block_cad_start():
    documents = fresh_documents()
    observe_photo_inventory(documents)
    complete_cad_start(documents)
    synchronize_intake(documents)
    errors, gates = evaluate_documents(documents)
    assert errors == []
    assert "M-P0-ELEC-01" not in gates.blockers["CAD_START"]
    assert gates.status("CAD_START") == "READY"


def test_missing_actual_edf_geometry_blocks_cad_start():
    documents = fresh_documents()
    observe_photo_inventory(documents)
    complete_cad_start(documents, except_ids={"M-P0-EDF-02"})
    synchronize_intake(documents)
    errors, gates = evaluate_documents(documents)
    assert errors == []
    assert "M-P0-EDF-02" in gates.blockers["CAD_START"]


def test_missing_servo_mount_shaft_and_horn_geometry_blocks_cad_start():
    documents = fresh_documents()
    observe_photo_inventory(documents)
    missing = {"M-P0-SERVO-04", "M-P0-SERVO-05", "M-P0-SERVO-06"}
    complete_cad_start(documents, except_ids=missing)
    synchronize_intake(documents)
    errors, gates = evaluate_documents(documents)
    assert errors == []
    assert missing.issubset(set(gates.blockers["CAD_START"]))


def test_not_present_existing_frame_does_not_require_frame_dimensions():
    documents = fresh_documents()
    observe_photo_inventory(documents, frame_status="NOT_PRESENT", frame_reuse="NOT_REUSE")
    complete_cad_start(documents)
    synchronize_intake(documents)
    errors, gates = evaluate_documents(documents)
    assert errors == []
    assert "M-P0-STRUCT-02" not in gates.blockers["CAD_START"]
    assert gates.status("CAD_START") == "READY"


def test_measured_without_evidence_still_fails_structure_validation():
    documents = fresh_documents()
    component(documents, "CMP-EDF-001")["dimensions"] = {
        "status": "MEASURED",
        "values": {"outer_diameter": 70},
        "evidence": [],
    }
    errors, _ = evaluate_documents(documents)
    assert any("MEASURED item lacks valid evidence" in error for error in errors)


def test_released_for_manufacture_is_rejected():
    documents = fresh_documents()
    documents["article"]["status"] = "RELEASED_FOR_MANUFACTURE"
    errors, _ = evaluate_documents(documents)
    assert any("Forbidden release status" in error for error in errors)


def test_historical_cad_cannot_supply_current_numeric_requirement():
    documents = fresh_documents()
    pitch = next(
        item
        for item in documents["requirements"]["requirements"]["motion"]
        if item["parameter"] == "pitch_required_range"
    )
    pitch["value"] = 15
    pitch["source"] = "historical CAD +/-15 deg"
    errors, _ = evaluate_documents(documents)
    assert any("only from historical CAD" in error for error in errors)


def test_cli_reports_detail_design_gate(capsys):
    assert main([]) == 0
    output = capsys.readouterr().out
    assert "R2 DETAIL_DESIGN blockers:" in output
    assert "R2 DETAIL DESIGN GATE:" in output


@pytest.mark.parametrize("status", ["RECORDED", "NOT_APPLICABLE"])
def test_completed_status_without_evidence_fails(status):
    documents = fresh_documents()
    measurement(documents, "M-P0-EDF-02")["status"] = status
    errors, gates = evaluate_documents(documents)
    assert any("completed status lacks valid evidence" in error for error in errors)
    assert gates.status("CAD_START") == "NOT_EVALUATED"


@pytest.mark.parametrize("mutation", [
    lambda d: d["plan"].update(measurements=None),
    lambda d: d.update(plan=[]),
    lambda d: measurement(d, "M-P0-EDF-02").update(required_for=["TYPO"]),
    lambda d: measurement(d, "M-P0-EDF-02").update(condition={"type": "TYPO"}),
    lambda d: measurement(d, "M-P0-EDF-02").update(condition={
        "type": "ANY_COMPONENT_INCLUDED", "component_ids": ["CMP-NOT-FOUND"]}),
    lambda d: d["intake"]["concept_intake"].update(required_gates=[]),
    lambda d: d["intake"]["concept_intake"].update(required_gates=["CAD_START"]),
    lambda d: d["intake"]["design_review_intake"].update(required_gates=["TYPO"]),
    lambda d: measurement(d, "M-P0-EDF-02").update(status="TYPO"),
])
def test_malformed_dependencies_fail_closed(mutation):
    documents = fresh_documents()
    mutation(documents)
    errors, gates = evaluate_documents(documents)
    assert errors
    assert all(gates.status(gate) == "NOT_EVALUATED" for gate in GATES)


def test_duplicate_and_cross_article_evidence_rejected():
    documents = fresh_documents()
    add_evidence(documents)
    add_evidence(documents)
    documents["evidence"]["evidence_records"][0]["article_id"] = "OTHER"
    errors, _ = evaluate_documents(documents)
    assert any("unique" in error for error in errors)
    assert any("article_id" in error for error in errors)


def test_json_report_is_actionable_and_gate_filter_does_not_change_validation(capsys):
    assert main(["--format", "json", "--gate", "CAD_START"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["structure_status"] == "PASS"
    assert list(report["gates"]) == ["CAD_START"]
    assert report["gates"]["CAD_START"]["status"] == "BLOCKED"
    assert len(report["gates"]["CAD_START"]["blockers"]) == 19
    item = next(x for x in report["gates"]["CAD_START"]["blockers"] if x["id"] == "M-P0-EDF-02")
    assert item["method"] and item["tool"] and item["fields"]
    assert report["hardware_verified"] is False
    assert report["manufacture_authorized"] is False


def test_failed_report_never_advertises_ready():
    report = build_report(["Bad YAML"], GateResult({gate: () for gate in GATES}), 0)
    assert report["structure_status"] == "FAIL"
    assert all(item["status"] == "NOT_EVALUATED" for item in report["gates"].values())


def test_text_details_list_methods(capsys):
    assert main(["--details", "--gate", "INVENTORY_BASELINE"]) == 0
    output = capsys.readouterr().out
    assert "M-P0-STRUCT-01" in output
    assert "Method:" in output
    assert "[CAD_START]" not in output


@pytest.mark.parametrize("field,value", [
    ("installed_status", "INSTALLED"),
    ("ownership_status", "NOT_PART_OF_CURRENT_ARTICLE"),
])
def test_presence_decisions_cannot_bypass_observation(field, value):
    documents = fresh_documents()
    component(documents, "CMP-EDF-001")[field] = value
    errors, _ = evaluate_documents(documents)
    assert any("observation evidence" in error for error in errors)


def test_json_failure_is_valid_json_and_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(checker, "evaluate_repository", lambda: (
        ["Broken unrelated gate"], GateResult({gate: () for gate in GATES}), 0))
    assert main(["--format", "json", "--gate", "CAD_START"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["errors"] == ["Broken unrelated gate"]
    assert report["gates"]["CAD_START"]["status"] == "NOT_EVALUATED"
