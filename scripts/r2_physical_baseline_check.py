"""Validate the R2 as-built structure without requiring physical measurements."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
ENGINEERING = ROOT / "engineering"
COMPONENT_RE = re.compile(r"CMP-[A-Z0-9-]+")


def load_yaml(relative: str) -> Any:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def evaluate() -> tuple[list[str], int, int, str]:
    errors: list[str] = []

    # Parse every engineering YAML, including templates and nested authorities.
    parsed_files: dict[Path, Any] = {}
    for path in sorted(ENGINEERING.rglob("*.yaml")):
        try:
            parsed_files[path] = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - reported as gate evidence
            errors.append(f"YAML parse failed: {path.relative_to(ROOT)}: {exc}")

    required_paths = [
        "engineering/as-built/article.yaml",
        "engineering/as-built/component-inventory.yaml",
        "engineering/as-built/measurement-plan.yaml",
        "engineering/as-built/interface-register.yaml",
        "engineering/as-built/mass-properties.yaml",
        "engineering/as-built/evidence-index.yaml",
        "engineering/as-built/datum-definition.yaml",
        "engineering/tvc-mechanical-requirements.yaml",
        "engineering/aeroforge-intake/tvc-assembly-intake.yaml",
    ]
    for relative in required_paths:
        if not (ROOT / relative).is_file():
            errors.append(f"Missing required R2 authority: {relative}")

    if errors:
        return errors, 0, 0, "BLOCKED"

    article = load_yaml(required_paths[0])
    inventory = load_yaml(required_paths[1])
    plan = load_yaml(required_paths[2])
    interfaces = load_yaml(required_paths[3])
    mass = load_yaml(required_paths[4])
    evidence_index = load_yaml(required_paths[5])
    datum = load_yaml(required_paths[6])
    requirements = load_yaml(required_paths[7])
    intake = load_yaml(required_paths[8])

    article_id = article.get("article_id")
    if article_id != "AA-TVC-BENCH-001":
        errors.append("article_id must be AA-TVC-BENCH-001")
    for name, document in (
        ("inventory", inventory),
        ("measurement plan", plan),
        ("interface register", interfaces),
        ("mass properties", mass),
        ("evidence index", evidence_index),
        ("datum", datum),
        ("TVC requirements", requirements),
        ("AeroForge intake", intake),
    ):
        if document.get("article_id") != article_id:
            errors.append(f"{name} article_id does not match article.yaml")

    components = inventory.get("components") or []
    component_ids = [item.get("component_id") for item in components]
    component_set = set(component_ids)
    if len(component_ids) != len(component_set) or None in component_set:
        errors.append("Component IDs must be present and unique")

    required_component_fields = {
        "component_id", "category", "claimed_model", "actual_model", "quantity",
        "ownership_status", "installed_status", "evidence_class", "evidence_source",
        "dimensions", "mass", "interface", "notes", "confidence",
    }
    allowed_classes = set(inventory.get("allowed_evidence_classes") or [])
    for item in components:
        missing_fields = sorted(required_component_fields - set(item))
        if missing_fields:
            errors.append(f"{item.get('component_id')} missing fields: {missing_fields}")
        if item.get("evidence_class") not in allowed_classes:
            errors.append(f"{item.get('component_id')} has invalid evidence_class")

    interface_items = interfaces.get("interfaces") or []
    interface_ids = [item.get("interface_id") for item in interface_items]
    interface_set = set(interface_ids)
    if len(interface_ids) != len(interface_set) or None in interface_set:
        errors.append("Interface IDs must be present and unique")
    for item in components:
        for interface_id in item.get("interface") or []:
            if interface_id not in interface_set:
                errors.append(f"{item['component_id']} references unknown {interface_id}")
    for interface in interface_items:
        for field in ("side_a", "side_b"):
            for component_id in COMPONENT_RE.findall(str(interface.get(field, ""))):
                if component_id not in component_set:
                    errors.append(f"{interface['interface_id']} references unknown {component_id}")

    measurements = plan.get("measurements") or []
    measurement_ids = [item.get("measurement_id") for item in measurements]
    measurement_set = set(measurement_ids)
    if len(measurement_ids) != len(measurement_set) or None in measurement_set:
        errors.append("Measurement IDs must be present and unique")
    for measurement in measurements:
        for component_id in measurement.get("component_ids") or []:
            if component_id not in component_set:
                errors.append(f"{measurement['measurement_id']} references unknown {component_id}")

    evidence_ids = {
        record.get("record_id")
        for record in evidence_index.get("evidence_records") or []
    }
    for path, document in parsed_files.items():
        for node in walk(document):
            if not isinstance(node, dict):
                continue
            if node.get("status") == "RELEASED_FOR_MANUFACTURE":
                errors.append(f"Forbidden release status in {path.relative_to(ROOT)}")
            if node.get("status") == "MEASURED":
                refs = node.get("evidence") or node.get("evidence_refs") or []
                if not refs:
                    errors.append(f"MEASURED item lacks evidence in {path.relative_to(ROOT)}")
                for ref in refs:
                    if ref not in evidence_ids:
                        errors.append(f"MEASURED item references unknown evidence {ref}")

    for section in requirements.get("requirements", {}).values():
        for requirement in section if isinstance(section, list) else []:
            value = requirement.get("value")
            source = str(requirement.get("source", "")).lower()
            if isinstance(value, (int, float)) and "historical" in source:
                errors.append(
                    f"{requirement.get('requirement_id')} takes a current numeric value only from historical CAD"
                )

    if datum.get("datum_id") != intake.get("datum", {}).get("datum_id"):
        errors.append("AeroForge datum does not match datum-definition.yaml")
    if requirements.get("design_item") != intake.get("design_item"):
        errors.append("AeroForge design_item does not match TVC requirements")
    if not intake.get("known_unknowns"):
        errors.append("AeroForge known_unknowns must not be empty")

    p0_required = {
        item["measurement_id"]
        for item in measurements
        if item.get("priority") == "P0" and item.get("required_for_cad") is True
    }
    handoff = set(intake.get("required_human_inputs") or [])
    if handoff != p0_required:
        errors.append(
            "AeroForge required_human_inputs must exactly match P0 required-for-CAD measurements"
        )
    checklist_path = ROOT / "docs/R2_USER_MEASUREMENT_CHECKLIST.md"
    if not checklist_path.is_file():
        errors.append("Human measurement checklist is missing")
    else:
        checklist = checklist_path.read_text(encoding="utf-8")
        absent = sorted(item for item in p0_required if item not in checklist)
        if absent:
            errors.append(f"Checklist omits P0 measurements: {absent}")

    mass_component_ids = set((mass.get("component_masses") or {}).keys())
    if not mass_component_ids.issubset(component_set):
        errors.append("Mass properties references unknown component IDs")

    missing = [
        item for item in measurements
        if item.get("priority") == "P0"
        and item.get("required_for_cad") is True
        and (item.get("status") != "RECORDED" or not item.get("evidence_refs"))
    ]
    physical_gate = "BLOCKED" if missing else "READY"
    intake_expected = "BLOCKED_BY_MEASUREMENT" if missing else "READY"
    if intake.get("status") != intake_expected:
        errors.append(
            f"AeroForge status must be {intake_expected} for current measurement state"
        )

    return errors, len(components), len(missing), physical_gate


def main() -> int:
    errors, component_count, missing_count, physical_gate = evaluate()
    if errors:
        for error in errors:
            print(f"R2 ERROR: {error}")
        print("R2 PHYSICAL BASELINE STRUCTURE CHECK: FAIL")
        print("R2 PHYSICAL MEASUREMENT GATE: BLOCKED")
        print("AEROFORGE INTAKE: BLOCKED")
        return 1

    print(f"R2 components inventoried: {component_count}")
    print(f"R2 MUST-HAVE measurements missing: {missing_count}")
    print("R2 PHYSICAL BASELINE STRUCTURE CHECK: PASS")
    print(f"R2 PHYSICAL MEASUREMENT GATE: {physical_gate}")
    print(f"AEROFORGE INTAKE: {'READY' if physical_gate == 'READY' else 'BLOCKED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
