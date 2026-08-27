from scripts.r2_physical_baseline_check import (
    clone_documents,
    evaluate_documents,
    load_documents,
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
