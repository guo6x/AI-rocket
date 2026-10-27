import hashlib
import shutil

import pytest
import yaml

from scripts.r2_evidence import validate_evidence_files
from scripts.r2_physical_baseline_check import load_documents
from scripts import r2_physical_baseline_check as checker


@pytest.fixture
def evidence_case(tmp_path):
    documents = load_documents()
    path = tmp_path / "engineering/evidence/records/example.yaml"
    path.parent.mkdir(parents=True)
    record = {
        "schema_version": 1, "record_id": "OBS-TEST-001",
        "record_type": "hardware_observation", "article_id": "AA-TVC-BENCH-001",
        "component_id": "CMP-EDF-001", "date": "2026-10-18",
        "operator": "Synthetic test fixture", "method": "Test only", "tool": "Test camera",
        "observations": ["Synthetic fixture, not physical evidence"],
        "source_commit": "a" * 40,
        "photo_refs": [{"location": "external:test-only/photo.jpg", "sha256": "b" * 64}],
    }
    entry = {key: record[key] for key in ("record_id", "record_type", "article_id")}
    entry["path"] = path.relative_to(tmp_path).as_posix()
    documents["evidence"]["evidence_records"] = [entry]

    def save():
        path.write_text(yaml.safe_dump(record), encoding="utf-8")
        entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

    save()
    return documents, record, entry, path, save, tmp_path


def test_valid_observation_and_measurement(evidence_case):
    documents, record, entry, _, save, root = evidence_case
    assert validate_evidence_files(documents, root) == []
    record.update(record_type="measurement", measurement_id="M-P0-EDF-02",
                  raw_measurement=0, unit="mm", uncertainty=0.1)
    entry["record_type"] = "measurement"
    save()
    assert validate_evidence_files(documents, root) == []


@pytest.mark.parametrize("field,value,expected", [
    ("record_id", "OTHER", "record_id"),
    ("article_id", "OTHER", "article_id"),
    ("component_id", "OTHER", "component_id"),
    ("operator", "REPLACE_ME", "operator"),
    ("method", "", "method"),
    ("date", "2026-02-30", "date"),
    ("source_commit", "abc123", "source_commit"),
    ("observations", [], "observations"),
    ("photo_refs", [], "photo_refs"),
    ("photo_refs", ["unhashed.jpg"], "photo"),
    ("record_type", "test_observation", "unsupported"),
])
def test_invalid_records_fail(evidence_case, field, value, expected):
    documents, record, _, _, save, root = evidence_case
    record[field] = value
    save()
    assert any(expected in error for error in validate_evidence_files(documents, root))


def test_missing_file_and_hash_mismatch(evidence_case):
    documents, _, entry, path, _, root = evidence_case
    entry["sha256"] = "0" * 64
    assert any("sha256" in error for error in validate_evidence_files(documents, root))
    path.unlink()
    assert any("cannot read" in error for error in validate_evidence_files(documents, root))


@pytest.mark.parametrize("path", ["../escape.yaml", "engineering/evidence/templates/record.yaml", ""])
def test_record_path_is_confined(evidence_case, path):
    documents, _, entry, _, _, root = evidence_case
    entry["path"] = path
    assert validate_evidence_files(documents, root)


def test_malformed_record_is_diagnostic(evidence_case):
    documents, _, _, path, _, root = evidence_case
    path.write_text("- not a mapping", encoding="utf-8")
    assert any("mapping" in error for error in validate_evidence_files(documents, root))


def test_measured_component_cannot_use_observation(evidence_case):
    documents, _, entry, _, _, root = evidence_case
    component = documents["inventory"]["components"][0]
    component.update(evidence_class="MEASURED", evidence_source=[entry["record_id"]])
    assert any("MEASURED requires" in error for error in validate_evidence_files(documents, root))


def test_measurement_cannot_borrow_another_component_record(evidence_case):
    documents, _, entry, _, _, root = evidence_case
    measurement = next(item for item in documents["plan"]["measurements"]
                       if item["measurement_id"] == "M-P0-SERVO-02")
    measurement.update(status="RECORDED", evidence_refs=[entry["record_id"]])
    assert any("another component" in error for error in validate_evidence_files(documents, root))


def test_measurement_requires_raw_values_units_and_uncertainty(evidence_case):
    documents, record, entry, _, save, root = evidence_case
    record.update(record_type="measurement", measurement_id="M-P0-EDF-02")
    entry["record_type"] = "measurement"
    save()
    errors = validate_evidence_files(documents, root)
    assert any("raw_measurement" in error for error in errors)
    assert any("unit" in error for error in errors)
    assert any("uncertainty" in error for error in errors)


def test_nested_measured_value_cannot_use_observation(evidence_case):
    documents, _, entry, _, _, root = evidence_case
    documents["inventory"]["components"][0]["dimensions"] = {
        "status": "MEASURED", "values": {"diameter": 12}, "evidence": [entry["record_id"]],
    }
    assert any("MEASURED value" in error for error in validate_evidence_files(documents, root))


def test_repository_integration_rejects_index_without_record(evidence_case, monkeypatch):
    documents, _, entry, _, _, root = evidence_case
    shutil.copytree(checker.ROOT / "engineering", root / "engineering", dirs_exist_ok=True)
    shutil.copytree(checker.ROOT / "docs", root / "docs")
    evidence_path = root / "engineering/as-built/evidence-index.yaml"
    evidence_path.write_text(yaml.safe_dump(documents["evidence"]), encoding="utf-8")
    monkeypatch.setattr(checker, "ROOT", root)
    monkeypatch.setattr(checker, "ENGINEERING", root / "engineering")
    errors, gates, count = checker.evaluate_repository()
    assert errors == []
    assert count == 40
    assert gates.status("CAD_START") == "BLOCKED"
    entry.pop("path")
    evidence_path.write_text(yaml.safe_dump(documents["evidence"]), encoding="utf-8")
    errors, gates, _ = checker.evaluate_repository()
    assert any("path is required" in error for error in errors)
    assert all(gates.status(gate) == "NOT_EVALUATED" for gate in checker.GATES)
    plan_path = root / "engineering/as-built/measurement-plan.yaml"
    documents["plan"]["measurements"] = 7
    plan_path.write_text(yaml.safe_dump(documents["plan"]), encoding="utf-8")
    errors, gates, count = checker.evaluate_repository()
    assert errors and count == 0
    assert gates.status("CAD_START") == "NOT_EVALUATED"


def test_not_applicable_cannot_use_measurement_record(evidence_case):
    documents, record, entry, _, save, root = evidence_case
    record.update(record_type="measurement", measurement_id="M-P0-EDF-02",
                  raw_measurement=12, unit="mm", uncertainty="Not quantified; pending review")
    entry["record_type"] = "measurement"
    save()
    measurement = next(item for item in documents["plan"]["measurements"]
                       if item["measurement_id"] == "M-P0-EDF-02")
    measurement.update(status="NOT_APPLICABLE", evidence_refs=[entry["record_id"]])
    assert any("NOT_APPLICABLE" in error for error in validate_evidence_files(documents, root))


def _add_servo_measurement(documents, root, record_id, component_id, unit_id):
    measurement_id = "M-P0-SERVO-02"
    path = root / f"engineering/evidence/records/{record_id}.yaml"
    record = {
        "schema_version": 1,
        "record_id": record_id,
        "record_type": "measurement",
        "article_id": "AA-TVC-BENCH-001",
        "component_id": component_id,
        "physical_unit_id": unit_id,
        "measurement_id": measurement_id,
        "date": "2026-10-27",
        "operator": "Synthetic unit-coverage fixture",
        "method": "Test only",
        "tool": "Test caliper",
        "raw_measurement": {"body_length": 23.0},
        "unit": "mm",
        "uncertainty": 0.1,
        "photo_refs": [{"location": f"external:test-only/{record_id}.jpg", "sha256": "c" * 64}],
        "source_commit": "d" * 40,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record), encoding="utf-8")
    entry = {
        "record_id": record_id,
        "record_type": "measurement",
        "article_id": "AA-TVC-BENCH-001",
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    documents["evidence"]["evidence_records"].append(entry)
    return entry


def test_multi_component_measurement_requires_each_servo_unit(evidence_case):
    documents, _, _, _, _, root = evidence_case
    measurement = next(item for item in documents["plan"]["measurements"]
                       if item["measurement_id"] == "M-P0-SERVO-02")
    pitch = _add_servo_measurement(
        documents, root, "MEAS-SERVO-PITCH-001", "CMP-TVC-SERVO-PITCH-001", "SERVO-U1"
    )
    roll = _add_servo_measurement(
        documents, root, "MEAS-SERVO-ROLL-001", "CMP-TVC-SERVO-ROLL-001", "SERVO-U2"
    )
    measurement.update(status="RECORDED", evidence_refs=[pitch["record_id"], roll["record_id"]])
    assert validate_evidence_files(documents, root) == []


def test_multi_component_measurement_rejects_partial_servo_coverage(evidence_case):
    documents, _, _, _, _, root = evidence_case
    measurement = next(item for item in documents["plan"]["measurements"]
                       if item["measurement_id"] == "M-P0-SERVO-02")
    pitch = _add_servo_measurement(
        documents, root, "MEAS-SERVO-PITCH-ONLY-001", "CMP-TVC-SERVO-PITCH-001", "SERVO-U1"
    )
    measurement.update(status="RECORDED", evidence_refs=[pitch["record_id"]])
    errors = validate_evidence_files(documents, root)
    assert any("must cover each component" in error for error in errors)


def test_multi_component_measurement_rejects_shared_physical_unit(evidence_case):
    documents, _, _, _, _, root = evidence_case
    measurement = next(item for item in documents["plan"]["measurements"]
                       if item["measurement_id"] == "M-P0-SERVO-02")
    pitch = _add_servo_measurement(
        documents, root, "MEAS-SERVO-SHARED-PITCH-001", "CMP-TVC-SERVO-PITCH-001", "SERVO-SHARED"
    )
    roll = _add_servo_measurement(
        documents, root, "MEAS-SERVO-SHARED-ROLL-001", "CMP-TVC-SERVO-ROLL-001", "SERVO-SHARED"
    )
    measurement.update(status="RECORDED", evidence_refs=[pitch["record_id"], roll["record_id"]])
    errors = validate_evidence_files(documents, root)
    assert any("cannot be shared across components" in error for error in errors)
