"""Validate staged R2 readiness without requiring every measurement at CAD start."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
ENGINEERING = ROOT / "engineering"
COMPONENT_RE = re.compile(r"CMP-[A-Z0-9-]+")
GATES = (
    "INVENTORY_BASELINE",
    "CAD_START",
    "MOTION_VERIFICATION",
    "DETAIL_DESIGN",
    "ARTICLE_INTEGRATION",
)
INPUT_GROUPS = {
    "INVENTORY_BASELINE": "inventory_inputs",
    "CAD_START": "cad_start_inputs",
    "MOTION_VERIFICATION": "motion_verification_inputs",
    "DETAIL_DESIGN": "detail_design_inputs",
    "ARTICLE_INTEGRATION": "article_integration_inputs",
}


@dataclass(frozen=True)
class GateResult:
    blockers: dict[str, tuple[str, ...]]

    def status(self, gate: str) -> str:
        return "BLOCKED" if self.blockers[gate] else "READY"

    def union(self, gates: list[str]) -> tuple[str, ...]:
        return tuple(sorted({item for gate in gates for item in self.blockers[gate]}))


def load_yaml(relative: str) -> Any:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def load_documents() -> dict[str, Any]:
    return {
        "article": load_yaml("engineering/as-built/article.yaml"),
        "inventory": load_yaml("engineering/as-built/component-inventory.yaml"),
        "plan": load_yaml("engineering/as-built/measurement-plan.yaml"),
        "interfaces": load_yaml("engineering/as-built/interface-register.yaml"),
        "mass": load_yaml("engineering/as-built/mass-properties.yaml"),
        "evidence": load_yaml("engineering/as-built/evidence-index.yaml"),
        "datum": load_yaml("engineering/as-built/datum-definition.yaml"),
        "requirements": load_yaml("engineering/tvc-mechanical-requirements.yaml"),
        "intake": load_yaml("engineering/aeroforge-intake/tvc-assembly-intake.yaml"),
        "checklist": (ROOT / "docs/R2_USER_MEASUREMENT_CHECKLIST.md").read_text(encoding="utf-8"),
    }


def clone_documents(documents: dict[str, Any]) -> dict[str, Any]:
    """Public test helper for deterministic scenario evaluation."""
    return deepcopy(documents)


def walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def evidence_ids(documents: dict[str, Any]) -> set[str]:
    return {
        record.get("record_id")
        for record in documents["evidence"].get("evidence_records") or []
        if record.get("record_id")
    }


def refs_are_valid(refs: list[str], known_evidence: set[str]) -> bool:
    return bool(refs) and set(refs).issubset(known_evidence)


def component_has_observation(component: dict[str, Any], known_evidence: set[str]) -> bool:
    return (
        component.get("evidence_class") in {"OBSERVED", "MEASURED"}
        and refs_are_valid(component.get("evidence_source") or [], known_evidence)
    )


def condition_is_active(
    condition: dict[str, Any] | None,
    components: dict[str, dict[str, Any]],
    known_evidence: set[str],
) -> bool:
    if not condition:
        return True
    selected = [components[item] for item in condition.get("component_ids") or []]
    condition_type = condition.get("type")
    if condition_type == "ANY_COMPONENT_INCLUDED":
        return any(
            item.get("article_inclusion") == "INCLUDED"
            or item.get("installed_status") == "INSTALLED"
            for item in selected
        )
    if condition_type == "ANY_COMPONENT_PRESENT_AND_REUSED":
        return any(
            item.get("ownership_status") == "CONFIRMED_PRESENT"
            and item.get("reuse_intent") == "REUSE"
            and component_has_observation(item, known_evidence)
            for item in selected
        )
    raise ValueError(f"Unknown measurement condition: {condition_type}")


def measurement_is_complete(measurement: dict[str, Any], known_evidence: set[str]) -> bool:
    return (
        measurement.get("status") in {"RECORDED", "NOT_APPLICABLE"}
        and refs_are_valid(measurement.get("evidence_refs") or [], known_evidence)
    )


def evaluate_documents(documents: dict[str, Any]) -> tuple[list[str], GateResult]:
    errors: list[str] = []
    article = documents["article"]
    inventory = documents["inventory"]
    plan = documents["plan"]
    interfaces = documents["interfaces"]
    mass = documents["mass"]
    evidence = documents["evidence"]
    datum = documents["datum"]
    requirements = documents["requirements"]
    intake = documents["intake"]

    article_id = article.get("article_id")
    if article_id != "AA-TVC-BENCH-001":
        errors.append("article_id must be AA-TVC-BENCH-001")
    for name, document in (
        ("inventory", inventory), ("measurement plan", plan),
        ("interface register", interfaces), ("mass properties", mass),
        ("evidence index", evidence), ("datum", datum),
        ("TVC requirements", requirements), ("AeroForge intake", intake),
    ):
        if document.get("article_id") != article_id:
            errors.append(f"{name} article_id does not match article.yaml")

    component_items = inventory.get("components") or []
    component_ids = [item.get("component_id") for item in component_items]
    components = {item.get("component_id"): item for item in component_items}
    component_set = set(component_ids)
    if len(component_ids) != len(component_set) or None in component_set:
        errors.append("Component IDs must be present and unique")

    required_component_fields = {
        "component_id", "category", "claimed_model", "actual_model", "quantity",
        "ownership_status", "installed_status", "evidence_class", "evidence_source",
        "dimensions", "mass", "interface", "notes", "confidence",
    }
    allowed_classes = set(inventory.get("allowed_evidence_classes") or [])
    allowed_ownership = set(inventory.get("ownership_status_vocabulary") or [])
    known_evidence = evidence_ids(documents)
    for item in component_items:
        missing_fields = sorted(required_component_fields - set(item))
        if missing_fields:
            errors.append(f"{item.get('component_id')} missing fields: {missing_fields}")
        if item.get("evidence_class") not in allowed_classes:
            errors.append(f"{item.get('component_id')} has invalid evidence_class")
        if item.get("ownership_status") not in allowed_ownership:
            errors.append(f"{item.get('component_id')} has invalid ownership_status")
        if item.get("ownership_status") in {"CONFIRMED_PRESENT", "NOT_PRESENT"}:
            if not component_has_observation(item, known_evidence):
                errors.append(
                    f"{item.get('component_id')} {item.get('ownership_status')} lacks observation evidence"
                )
        if item.get("article_inclusion") == "INCLUDED" or item.get("reuse_intent") in {
            "REUSE", "NOT_REUSE"
        }:
            if not component_has_observation(item, known_evidence):
                errors.append(
                    f"{item.get('component_id')} inclusion/reuse decision lacks observation evidence"
                )

    interface_items = interfaces.get("interfaces") or []
    interface_ids = [item.get("interface_id") for item in interface_items]
    interface_set = set(interface_ids)
    if len(interface_ids) != len(interface_set) or None in interface_set:
        errors.append("Interface IDs must be present and unique")
    for item in component_items:
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
    dependency_vocabulary = set(plan.get("dependency_gate_vocabulary") or [])
    if dependency_vocabulary != set(GATES):
        errors.append("Measurement dependency gate vocabulary is incomplete")
    for measurement in measurements:
        required_for = set(measurement.get("required_for") or [])
        if not required_for or not required_for.issubset(set(GATES)):
            errors.append(f"{measurement.get('measurement_id')} has invalid required_for")
        for component_id in measurement.get("component_ids") or []:
            if component_id not in component_set:
                errors.append(f"{measurement['measurement_id']} references unknown {component_id}")
        try:
            condition_is_active(measurement.get("condition"), components, known_evidence)
        except ValueError as exc:
            errors.append(str(exc))

    # Evidence rigor remains global, independent of readiness staging.
    for key, document in documents.items():
        if key == "checklist":
            continue
        for node in walk(document):
            if not isinstance(node, dict):
                continue
            if node.get("status") == "RELEASED_FOR_MANUFACTURE":
                errors.append(f"Forbidden release status in {key}")
            if node.get("status") == "MEASURED":
                refs = node.get("evidence") or node.get("evidence_refs") or []
                if not refs_are_valid(refs, known_evidence):
                    errors.append(f"MEASURED item lacks valid evidence in {key}")
    if intake.get("manufacture_authorized") is not False:
        errors.append("AeroForge manufacture_authorized must remain false")

    # Current requirement values may not silently come only from historical CAD.
    for section in requirements.get("requirements", {}).values():
        for requirement in section if isinstance(section, list) else []:
            value = requirement.get("value")
            source = str(requirement.get("source", "")).lower()
            if isinstance(value, (int, float)) and "historical" in source:
                errors.append(
                    f"{requirement.get('requirement_id')} takes a current numeric value only from historical CAD"
                )
    motion_requirements = {
        item.get("parameter"): item
        for item in requirements.get("requirements", {}).get("motion", [])
    }
    for parameter in ("pitch_required_range", "roll_required_range"):
        if motion_requirements.get(parameter, {}).get("status") not in {
            "TBD_SYSTEM_REQUIREMENT",
            "DEFINED_SYSTEM_REQUIREMENT",
            "APPROVED_SYSTEM_REQUIREMENT",
        }:
            errors.append(f"{parameter} must remain a system/control requirement")
    if "available_servo_range" not in motion_requirements:
        errors.append("available_servo_range must be represented separately")

    blockers: dict[str, list[str]] = {gate: [] for gate in GATES}
    for measurement in measurements:
        active = condition_is_active(
            measurement.get("condition"), components, known_evidence
        )
        if not active or measurement_is_complete(measurement, known_evidence):
            continue
        for gate in measurement.get("required_for") or []:
            blockers[gate].append(measurement["measurement_id"])

    photo_inventory = next(
        item for item in measurements if item["measurement_id"] == "M-P0-STRUCT-01"
    )
    if measurement_is_complete(photo_inventory, known_evidence):
        resolved_presence = {
            "CONFIRMED_PRESENT", "NOT_PRESENT", "NOT_PART_OF_CURRENT_ARTICLE"
        }
        unresolved = [
            component_id
            for component_id in photo_inventory["component_ids"]
            if components[component_id].get("ownership_status") not in resolved_presence
        ]
        for component_id in unresolved:
            blockers["INVENTORY_BASELINE"].append(
                f"INVENTORY-PRESENCE-{component_id}"
            )
            blockers["CAD_START"].append(f"INVENTORY-PRESENCE-{component_id}")

    # Motion verification also requires a governed required range, not only measured availability.
    for parameter in ("pitch_required_range", "roll_required_range"):
        requirement = motion_requirements.get(parameter, {})
        if (
            requirement.get("value") is None
            or requirement.get("status") == "TBD_SYSTEM_REQUIREMENT"
        ):
            blockers["MOTION_VERIFICATION"].append(requirement.get("requirement_id", parameter))

    gate_result = GateResult(
        {gate: tuple(sorted(set(items))) for gate, items in blockers.items()}
    )

    if datum.get("datum_id") != intake.get("datum", {}).get("datum_id"):
        errors.append("AeroForge datum does not match datum-definition.yaml")
    if requirements.get("design_item") != intake.get("design_item"):
        errors.append("AeroForge design_item does not match TVC requirements")
    if not intake.get("known_unknowns"):
        errors.append("AeroForge known_unknowns must not be empty")

    input_groups = intake.get("input_groups") or {}
    for gate, group_name in INPUT_GROUPS.items():
        planned = {
            item["measurement_id"]
            for item in measurements
            if gate in (item.get("required_for") or [])
        }
        if set(input_groups.get(group_name) or []) != planned:
            errors.append(f"AeroForge {group_name} does not match measurement dependencies")

    concept = intake.get("concept_intake") or {}
    concept_gates = concept.get("required_gates") or []
    concept_blockers = gate_result.union(concept_gates)
    concept_status = "BLOCKED" if concept_blockers else "READY"
    if concept.get("status") != concept_status:
        errors.append(f"AeroForge concept_intake status must be {concept_status}")
    if set(concept.get("blockers") or []) != set(concept_blockers):
        errors.append("AeroForge concept_intake blockers do not match active gate blockers")

    design_review = intake.get("design_review_intake") or {}
    review_blockers = gate_result.union(design_review.get("required_gates") or [])
    review_status = "BLOCKED" if review_blockers else "READY"
    if design_review.get("status") != review_status:
        errors.append(f"AeroForge design_review_intake status must be {review_status}")

    checklist = documents.get("checklist", "")
    absent = sorted(item for item in measurement_set if item not in checklist)
    if absent:
        errors.append(f"Checklist omits planned measurements: {absent}")
    mass_component_ids = set((mass.get("component_masses") or {}).keys())
    if not mass_component_ids.issubset(component_set):
        errors.append("Mass properties references unknown component IDs")

    return errors, gate_result


def evaluate_repository() -> tuple[list[str], GateResult, int]:
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
        "docs/R2_USER_MEASUREMENT_CHECKLIST.md",
    ]
    missing_paths = [item for item in required_paths if not (ROOT / item).is_file()]
    errors = [f"Missing required R2 authority: {item}" for item in missing_paths]
    for path in sorted(ENGINEERING.rglob("*.yaml")):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - output is the evidence
            errors.append(f"YAML parse failed: {path.relative_to(ROOT)}: {exc}")
    if errors:
        return errors, GateResult({gate: () for gate in GATES}), 0
    documents = load_documents()
    validation_errors, gate_result = evaluate_documents(documents)
    return validation_errors, gate_result, len(documents["plan"].get("measurements") or [])


def main() -> int:
    errors, gates, measurement_count = evaluate_repository()
    if errors:
        for error in errors:
            print(f"R2 ERROR: {error}")
        print("R2 PHYSICAL BASELINE STRUCTURE CHECK: FAIL")
        return 1

    documents = load_documents()
    concept = documents["intake"]["concept_intake"]["status"]
    review = documents["intake"]["design_review_intake"]["status"]
    print(f"R2 total planned measurements: {measurement_count}")
    display_names = {
        "INVENTORY_BASELINE": ("PHOTO INVENTORY", "INVENTORY OBSERVATION"),
        "CAD_START": ("CAD_START", "CAD START"),
        "MOTION_VERIFICATION": ("MOTION_VERIFICATION", "MOTION VERIFICATION"),
        "DETAIL_DESIGN": ("DETAIL_DESIGN", "DETAIL DESIGN"),
        "ARTICLE_INTEGRATION": ("ARTICLE_INTEGRATION", "ARTICLE INTEGRATION"),
    }
    for gate, (count_name, gate_name) in display_names.items():
        print(f"R2 {count_name} blockers: {len(gates.blockers[gate])}")
        print(f"R2 {gate_name} GATE: {gates.status(gate)}")
    print(f"AEROFORGE TVC CONCEPT INTAKE: {concept}")
    print(f"AEROFORGE TVC DESIGN-REVIEW INTAKE: {review}")
    print("R2 PHYSICAL BASELINE STRUCTURE CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
