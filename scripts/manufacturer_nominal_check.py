"""Validate the source-bound manufacturer nominal parameter layer.

This check is intentionally narrower than the R2 physical-evidence gates.  It
validates provenance and schema for manufacturer reference values while
refusing to promote them to OBSERVED, MEASURED, CONFIRMED_PRESENT or
VERIFIED_HARDWARE evidence.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "engineering" / "parameter-registry.yaml"
ASSET_PATH = ROOT / "engineering" / "assets" / "project-asset-registry.yaml"


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys instead of silently overriding them."""


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep=False):
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                None, None, "YAML mapping keys must be strings", key_node.start_mark,
            )
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate YAML key {key!r}", key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


REQUIRED_FIELDS = {
    "id",
    "asset_id",
    "model_claim",
    "manufacturer",
    "property",
    "value",
    "unit",
    "applicability",
    "source_url",
    "source_revision",
    "evidence_level",
    "model_status",
    "conflict",
    "conflict_group",
    "conflict_note",
    "design_use",
    "design_scope",
}
MODEL_STATUSES = {"CONFIRMED_SERIES", "UNRESOLVED_VARIANT", "VERSION_CONFLICT"}
DESIGN_USES = {"OFFLINE_CONCEPT_REFERENCE", "REFERENCE_ONLY_NO_FIT"}
NOMINAL_EVIDENCE = "MANUFACTURER_NOMINAL_REFERENCE"
FORBIDDEN_EVIDENCE = {"MEASURED", "OBSERVED", "VERIFIED_HARDWARE", "CONFIRMED_PRESENT"}

# A property has one canonical unit in this layer.  Keeping this table small
# makes a typo such as cm, m, or V for a dimension fail closed.
PROPERTY_UNITS = {
    "core_architecture": "text",
    "maximum_clock_frequency": "MHz",
    "supply_voltage_min": "V",
    "supply_voltage_max": "V",
    "flash_capacity": "MB",
    "psram_capacity": "MB",
    "module_length": "mm",
    "module_width": "mm",
    "module_height": "mm",
    "header_pitch": "mm",
    "wifi_frequency": "GHz",
    "axis_count": "count",
    "package_length": "mm",
    "package_width": "mm",
    "package_height": "mm",
    "digital_interfaces": "text",
    "pressure_range_min": "hPa",
    "pressure_range_max": "hPa",
    "body_length": "mm",
    "body_width": "mm",
    "body_height": "mm",
    "nominal_supply_voltage": "V",
    "stall_torque": "kgf·cm",
    "gear_material": "text",
    "ic_input_voltage_min": "V",
    "ic_input_voltage_max": "V",
    "ic_nominal_output_current_max": "A",
    "switching_frequency": "kHz",
    "radio_frequency_min": "MHz",
    "radio_frequency_max": "MHz",
    "host_interface": "text",
    "antenna_connector": "text",
    "reference_mass": "g",
    "chip_supply_voltage_min": "V",
    "chip_supply_voltage_max": "V",
}
NUMERIC_UNITS = {unit for unit in PROPERTY_UNITS.values() if unit != "text"}
CONFLICT_GROUPS = {
    "SG92R-GEAR-MATERIAL-AND-WEIGHT",
    "ESP32S3-MEMORY-SUFFIX",
}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.load(handle, Loader=UniqueKeyLoader)
    return data if isinstance(data, dict) else {}


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _asset_ids(assets_doc: dict[str, Any], errors: list[str]) -> set[str]:
    assets = assets_doc.get("assets")
    if not isinstance(assets, list):
        errors.append("assets must be a list")
        return set()
    result: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict) or not _is_nonempty_string(asset.get("asset_id")):
            errors.append(f"assets[{index}].asset_id must be a nonempty string")
            continue
        asset_id = asset["asset_id"]
        if asset_id in result:
            errors.append(f"duplicate asset_id {asset_id}")
        result.add(asset_id)
    return result


def validate_documents(
    registry_doc: dict[str, Any],
    assets_doc: dict[str, Any],
    root: Path = ROOT,
) -> list[str]:
    """Return deterministic validation errors for supplied YAML documents."""

    errors: list[str] = []
    asset_ids = _asset_ids(assets_doc, errors)
    layer = registry_doc.get("manufacturer_nominal")
    if not isinstance(layer, dict):
        return ["manufacturer_nominal must be a mapping"]
    if layer.get("schema_version") != 1:
        errors.append("manufacturer_nominal.schema_version must be 1")
    source_index = layer.get("source_index")
    if not _is_nonempty_string(source_index):
        errors.append("manufacturer_nominal.source_index must be a nonempty string")
    else:
        source_path = PurePosixPath(source_index.replace("\\", "/"))
        if source_path.is_absolute() or ".." in source_path.parts:
            errors.append("manufacturer_nominal.source_index must be repository-relative")
        elif not (root / Path(*source_path.parts)).is_file():
            errors.append("manufacturer_nominal.source_index must reference an existing file")

    parameters = layer.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        errors.append("manufacturer_nominal.parameters must be a nonempty list")
        parameters = []
    seen_ids: set[str] = set()
    nominal_assets: set[str] = set()
    groups: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(parameters):
        prefix = f"manufacturer_nominal.parameters[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        missing = sorted(REQUIRED_FIELDS - row.keys())
        errors.extend(f"{prefix} missing {field}" for field in missing)
        parameter_id = row.get("id")
        if not _is_nonempty_string(parameter_id):
            errors.append(f"{prefix}.id must be a nonempty string")
        elif parameter_id in seen_ids:
            errors.append(f"duplicate manufacturer nominal id {parameter_id}")
        else:
            seen_ids.add(parameter_id)

        asset_id = row.get("asset_id")
        if not _is_nonempty_string(asset_id) or asset_id not in asset_ids:
            errors.append(f"{prefix}.asset_id must resolve to project-asset-registry.yaml")
        else:
            nominal_assets.add(asset_id)
        for field in ("model_claim", "manufacturer", "applicability", "design_scope"):
            if not _is_nonempty_string(row.get(field)):
                errors.append(f"{prefix}.{field} must be a nonempty string")
        prop = row.get("property")
        expected_unit = PROPERTY_UNITS.get(prop)
        if expected_unit is None:
            errors.append(f"{prefix}.property is not in the nominal property vocabulary")
        unit = row.get("unit")
        if not _is_nonempty_string(unit):
            errors.append(f"{prefix}.unit is required")
        elif expected_unit is not None and unit != expected_unit:
            errors.append(f"{prefix}.unit {unit!r} does not match {prop!r} ({expected_unit})")

        value = row.get("value")
        if value is None:
            errors.append(f"{prefix}.value must not be null")
        elif unit in NUMERIC_UNITS and (isinstance(value, bool) or not isinstance(value, (int, float))):
            errors.append(f"{prefix}.value must be numeric for unit {unit}")
        elif unit in NUMERIC_UNITS and not math.isfinite(float(value)):
            errors.append(f"{prefix}.value must be finite")
        elif unit == "text" and not _is_nonempty_string(value):
            errors.append(f"{prefix}.value must be a nonempty string for text properties")
        if "tolerance" in row:
            tolerance = row.get("tolerance")
            if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(float(tolerance)) or tolerance < 0:
                errors.append(f"{prefix}.tolerance must be a finite nonnegative number")
            if row.get("tolerance_unit") != unit:
                errors.append(f"{prefix}.tolerance_unit must match unit")

        source_url = row.get("source_url")
        if not _is_nonempty_string(source_url) or not source_url.startswith("https://"):
            errors.append(f"{prefix}.source_url must be a nonempty https URL")
        source_revision = row.get("source_revision")
        if not _is_nonempty_string(source_revision) or source_revision.strip().upper() in {"UNKNOWN", "N/A"}:
            errors.append(f"{prefix}.source_revision must identify a document/page revision or retrieval")
        if row.get("evidence_level") != NOMINAL_EVIDENCE:
            errors.append(f"{prefix}.evidence_level must be {NOMINAL_EVIDENCE}")
        if row.get("evidence_level") in FORBIDDEN_EVIDENCE or row.get("status") in FORBIDDEN_EVIDENCE:
            errors.append(f"{prefix} must not present manufacturer nominal data as measured/observed evidence")

        model_status = row.get("model_status")
        if model_status not in MODEL_STATUSES:
            errors.append(f"{prefix}.model_status is invalid")
        design_use = row.get("design_use")
        if design_use not in DESIGN_USES:
            errors.append(f"{prefix}.design_use is invalid")
        conflict = row.get("conflict")
        if not isinstance(conflict, bool):
            errors.append(f"{prefix}.conflict must be boolean")
        group = row.get("conflict_group")
        if group is not None and not _is_nonempty_string(group):
            errors.append(f"{prefix}.conflict_group must be null or a nonempty string")
        note = row.get("conflict_note")
        if note is not None and not isinstance(note, str):
            errors.append(f"{prefix}.conflict_note must be null or a string")
        if model_status == "VERSION_CONFLICT" and (conflict is not True or not _is_nonempty_string(group)):
            errors.append(f"{prefix} version conflict must carry conflict=true and conflict_group")
        if conflict is True and model_status != "VERSION_CONFLICT":
            errors.append(f"{prefix} conflict=true requires model_status VERSION_CONFLICT")
        if group in CONFLICT_GROUPS and (conflict is not True or model_status != "VERSION_CONFLICT"):
            errors.append(f"{prefix} known conflict group cannot be silently confirmed")
        if group in CONFLICT_GROUPS:
            groups.setdefault(group, []).append(row)

    for group, rows in sorted(groups.items()):
        if len(rows) < 2:
            errors.append(f"conflict group {group} must retain at least two source-bound rows")

    unresolved = layer.get("unresolved_assets")
    unresolved_ids: set[str] = set()
    if not isinstance(unresolved, list):
        errors.append("manufacturer_nominal.unresolved_assets must be a list")
        unresolved = []
    for index, entry in enumerate(unresolved):
        prefix = f"manufacturer_nominal.unresolved_assets[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        asset_id = entry.get("asset_id")
        if not _is_nonempty_string(asset_id) or asset_id not in asset_ids:
            errors.append(f"{prefix}.asset_id must resolve to project-asset-registry.yaml")
        elif asset_id in unresolved_ids:
            errors.append(f"duplicate unresolved asset_id {asset_id}")
        else:
            unresolved_ids.add(asset_id)
        if entry.get("status") != "UNKNOWN":
            errors.append(f"{prefix}.status must remain UNKNOWN")
        if not _is_nonempty_string(entry.get("reason")):
            errors.append(f"{prefix}.reason must be a nonempty string")

    if nominal_assets & unresolved_ids:
        errors.append("an asset cannot be both manufacturer nominal and unresolved")
    if nominal_assets | unresolved_ids != asset_ids:
        missing = sorted(asset_ids - nominal_assets - unresolved_ids)
        extra = sorted(nominal_assets | unresolved_ids - asset_ids)
        if missing:
            errors.append(f"assets missing nominal-or-UNKNOWN disposition: {', '.join(missing)}")
        if extra:
            errors.append(f"nominal disposition has unknown assets: {', '.join(extra)}")

    concept = layer.get("offline_concept_design")
    if not isinstance(concept, list) or not concept:
        errors.append("manufacturer_nominal.offline_concept_design must be a nonempty list")
    else:
        for index, entry in enumerate(concept):
            prefix = f"manufacturer_nominal.offline_concept_design[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{prefix} must be a mapping")
                continue
            if entry.get("asset_id") not in asset_ids:
                errors.append(f"{prefix}.asset_id must resolve to project-asset-registry.yaml")
            scopes = entry.get("allowed_scopes")
            if not isinstance(scopes, list) or not scopes or not all(_is_nonempty_string(s) for s in scopes):
                errors.append(f"{prefix}.allowed_scopes must be a nonempty string list")
            if not _is_nonempty_string(entry.get("limitation")):
                errors.append(f"{prefix}.limitation must be a nonempty string")

    return sorted(set(errors))


def audit_repository(root: Path = ROOT) -> list[str]:
    registry_path = root / "engineering" / "parameter-registry.yaml"
    asset_path = root / "engineering" / "assets" / "project-asset-registry.yaml"
    try:
        registry_doc = load_yaml(registry_path)
        assets_doc = load_yaml(asset_path)
    except (OSError, yaml.YAMLError) as exc:
        return [f"unable to load manufacturer nominal inputs: {exc}"]
    return validate_documents(registry_doc, assets_doc, root=root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit a machine-readable result")
    args = parser.parse_args()
    errors = audit_repository()
    layer = load_yaml(REGISTRY_PATH).get("manufacturer_nominal", {}) if not errors else {}
    parameters = layer.get("parameters", []) if isinstance(layer, dict) else []
    conflicts = sorted({row.get("conflict_group") for row in parameters if isinstance(row, dict) and row.get("conflict_group")})
    result = {
        "status": "PASS" if not errors else "FAIL",
        "manufacturer_nominal_parameters": len(parameters),
        "conflict_groups": conflicts,
        "unresolved_assets": len(layer.get("unresolved_assets", [])) if isinstance(layer, dict) else 0,
        "errors": errors,
    }
    if args.json:
        import json

        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(f"manufacturer_nominal: {result['status']}")
        print(f"parameters={result['manufacturer_nominal_parameters']} conflicts={len(conflicts)} unresolved_assets={result['unresolved_assets']}")
        for error in errors:
            print(f"ERROR: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
