"""Negative contracts recovered from the unmerged R2 tail, without hardware I/O."""

import pytest
import yaml

from scripts import r2_physical_baseline_check as checker


def fresh_documents():
    return checker.clone_documents(checker.load_documents())


def assert_not_evaluated(errors, gates):
    assert errors
    assert all(gates.status(gate) == "NOT_EVALUATED" for gate in checker.GATES)


@pytest.mark.parametrize("stage", ["concept_intake", "design_review_intake"])
@pytest.mark.parametrize("required_gates", [
    [], ["CAD_START"], ["CAD_START", "CAD_START"], ["UNKNOWN_GATE"],
])
def test_intake_cannot_weaken_required_gate_contract(stage, required_gates):
    documents = fresh_documents()
    documents["intake"][stage].update(
        required_gates=required_gates, status="READY", blockers=[],
    )

    errors, gates = checker.evaluate_documents(documents)

    assert any(f"{stage} required_gates" in error for error in errors)
    assert_not_evaluated(errors, gates)


@pytest.mark.parametrize("stage", ["concept_intake", "design_review_intake"])
def test_repository_rejects_empty_gates_even_when_intake_claims_ready(stage, monkeypatch):
    documents = fresh_documents()
    documents["intake"][stage].update(required_gates=[], status="READY", blockers=[])
    monkeypatch.setattr(checker, "load_documents", lambda: documents)

    errors, gates, count = checker.evaluate_repository()

    assert_not_evaluated(errors, gates)
    assert count == 0


@pytest.mark.parametrize("case", ["duplicate", "cross_article", "blank_id"])
def test_index_identity_is_not_ambiguous(case):
    documents = fresh_documents()
    record = {"record_id": "OBS-SYNTHETIC-001", "article_id": "AA-TVC-BENCH-001"}
    records = documents["evidence"]["evidence_records"]
    records.append(record)
    if case == "duplicate":
        records.append(dict(record))
    elif case == "cross_article":
        record["article_id"] = "OTHER-ARTICLE"
    else:
        record["record_id"] = " "

    errors, gates = checker.evaluate_documents(documents)

    expected = "article_id" if case == "cross_article" else "non-empty and unique"
    assert any(expected in error for error in errors)
    assert_not_evaluated(errors, gates)


@pytest.mark.parametrize("case", [
    "plan_not_mapping", "measurements_not_list", "invalid_record_entry",
    "unknown_component_condition", "missing_inventory_measurement",
])
def test_malformed_schema_fails_closed_at_both_entry_points(case, monkeypatch):
    documents = fresh_documents()
    if case == "plan_not_mapping":
        documents["plan"] = []
    elif case == "measurements_not_list":
        documents["plan"]["measurements"] = None
    elif case == "invalid_record_entry":
        documents["evidence"]["evidence_records"] = [None]
    elif case == "unknown_component_condition":
        documents["plan"]["measurements"][0]["condition"] = {
            "type": "ANY_COMPONENT_INCLUDED", "component_ids": ["CMP-NOT-FOUND"],
        }
    else:
        documents["plan"]["measurements"] = [
            item for item in documents["plan"]["measurements"]
            if item["measurement_id"] != "M-P0-STRUCT-01"
        ]

    errors, gates = checker.evaluate_documents(documents)
    assert_not_evaluated(errors, gates)
    monkeypatch.setattr(checker, "load_documents", lambda: documents)
    errors, gates, count = checker.evaluate_repository()
    assert_not_evaluated(errors, gates)
    assert count == 0


def test_regular_validation_error_also_invalidates_gate_status():
    documents = fresh_documents()
    documents["article"]["status"] = "RELEASED_FOR_MANUFACTURE"

    errors, gates = checker.evaluate_documents(documents)

    assert any("Forbidden release status" in error for error in errors)
    assert_not_evaluated(errors, gates)


@pytest.mark.parametrize("status", ["RECORDED", "NOT_APPLICABLE", "UNKNOWN_STATUS"])
def test_measurement_status_requires_its_evidence_contract(status):
    documents = fresh_documents()
    documents["plan"]["measurements"][0].update(status=status, evidence_refs=[])

    errors, gates = checker.evaluate_documents(documents)

    assert any("status" in error for error in errors)
    assert_not_evaluated(errors, gates)


@pytest.mark.parametrize("field,value", [
    ("installed_status", "INSTALLED"),
    ("ownership_status", "NOT_PART_OF_CURRENT_ARTICLE"),
    ("evidence_class", "OBSERVED"),
])
def test_observation_claims_require_referenced_evidence(field, value):
    documents = fresh_documents()
    documents["inventory"]["components"][0][field] = value

    errors, gates = checker.evaluate_documents(documents)

    assert any("evidence" in error for error in errors)
    assert_not_evaluated(errors, gates)


@pytest.mark.parametrize("error", [OSError("unreadable"), yaml.YAMLError("invalid YAML")])
def test_repository_load_failure_is_a_closed_diagnostic(error, monkeypatch):
    def fail_loading():
        raise error

    monkeypatch.setattr(checker, "load_documents", fail_loading)

    errors, gates, count = checker.evaluate_repository()

    assert any("Cannot load R2 documents" in item for item in errors)
    assert_not_evaluated(errors, gates)
    assert count == 0


def test_unchanged_baseline_remains_blocked_not_hardware_qualified():
    errors, gates = checker.evaluate_documents(fresh_documents())

    assert errors == []
    assert all(gates.status(gate) == "BLOCKED" for gate in checker.GATES)
