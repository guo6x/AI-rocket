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
from urllib.parse import urlsplit

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

# These are the source-bound parameter IDs that make up each known conflict.
# Keeping the binding in the checker prevents a row from escaping the guard by
# simply clearing its mutable ``conflict`` and ``conflict_group`` fields.  A
# future resolution must be explicit and reviewable in the registry's
# ``conflict_resolutions`` section; it cannot be created by editing a row only.
KNOWN_CONFLICT_PARAMETER_IDS = {
    "SG92R-GEAR-MATERIAL-AND-WEIGHT": frozenset(
        {
            "MN-SG92R-LENGTH",
            "MN-SG92R-WIDTH",
            "MN-SG92R-HEIGHT",
            "MN-SG92R-SUPPLY",
            "MN-SG92R-STALL-TORQUE",
            "MN-SG92R-GEAR-MATERIAL-PAGE",
        }
    ),
    "ESP32S3-MEMORY-SUFFIX": frozenset(
        {
            "MN-ESP32S3-N16R8V-FLASH",
            "MN-ESP32S3-N16R8V-PSRAM",
        }
    ),
}
CONFLICT_BINDING_STATES = {"ACTIVE", "RESOLVED"}
PLACEHOLDER_SOURCE_HOSTS = {
    "example.com",
    "example.invalid",
    "example.net",
    "example.org",
}
RESOLUTION_REQUIRED_FIELDS = {
    "conflict_group",
    "parameter_ids",
    "asset_ids",
    "source_index",
    "source_refs",
    "status",
    "resolution_id",
    "review_reference",
    "source_url",
    "source_revision",
    "resolved_on",
    "decision",
}


def _repository_file(
    root: Path,
    reference: Any,
    field: str,
    errors: list[str],
) -> Path | None:
    """Resolve a repository-relative evidence path, fail closed.

    A resolution record is only useful when its review artifact and source
    index are present in the checkout being audited.  URL-shaped strings (or
    paths escaping the repository) therefore never satisfy this check.
    """

    if not _is_nonempty_string(reference):
        errors.append(f"{field} must be a nonempty repository-relative path")
        return None
    path = PurePosixPath(reference.strip().replace("\\", "/"))
    if (
        path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or any(":" in part for part in path.parts)
    ):
        errors.append(f"{field} must be repository-relative")
        return None
    candidate = root.joinpath(*path.parts)
    if not candidate.is_file():
        errors.append(f"{field} must reference an existing file")
        return None
    return candidate


def _is_placeholder_source_url(value: Any) -> bool:
    """Reject reserved documentation hosts used only as test placeholders."""

    if not _is_nonempty_string(value):
        return False
    parsed = urlsplit(value.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    return host in PLACEHOLDER_SOURCE_HOSTS or host.endswith(".invalid")


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
    _repository_file(root, source_index, "manufacturer_nominal.source_index", errors)

    parameters = layer.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        errors.append("manufacturer_nominal.parameters must be a nonempty list")
        parameters = []
    seen_ids: set[str] = set()
    rows_by_id: dict[str, dict[str, Any]] = {}
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
            rows_by_id[parameter_id] = row

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
        elif _is_nonempty_string(group) and group not in CONFLICT_GROUPS:
            errors.append(f"{prefix}.conflict_group is not a declared conflict group")
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
            expected_ids = KNOWN_CONFLICT_PARAMETER_IDS.get(group, frozenset())
            if parameter_id not in expected_ids:
                errors.append(f"{prefix}.id is not part of immutable conflict binding {group}")

    for group, rows in sorted(groups.items()):
        if len(rows) < 2:
            errors.append(f"conflict group {group} must retain at least two source-bound rows")

    # Validate immutable parameter-to-conflict bindings before accepting the
    # mutable row flags.  A row that clears ``conflict`` and ``conflict_group``
    # is still rejected while its known binding is ACTIVE.  The only supported
    # escape hatch is a complete, source-bound resolution record reviewed in a
    # separate registry section.
    bindings = layer.get("conflict_bindings")
    binding_by_group: dict[str, dict[str, Any]] = {}
    if not isinstance(bindings, list) or not bindings:
        errors.append("manufacturer_nominal.conflict_bindings must be a nonempty list")
        bindings = []
    for index, binding in enumerate(bindings):
        prefix = f"manufacturer_nominal.conflict_bindings[{index}]"
        if not isinstance(binding, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        for field in ("conflict_group", "parameter_ids", "status", "note"):
            if field not in binding:
                errors.append(f"{prefix} missing {field}")
        group = binding.get("conflict_group")
        if not _is_nonempty_string(group) or group not in CONFLICT_GROUPS:
            errors.append(f"{prefix}.conflict_group must identify a known conflict group")
            continue
        if group in binding_by_group:
            errors.append(f"duplicate conflict binding {group}")
        else:
            binding_by_group[group] = binding
        parameter_ids = binding.get("parameter_ids")
        if not isinstance(parameter_ids, list) or not parameter_ids or not all(
            _is_nonempty_string(parameter_id) for parameter_id in parameter_ids
        ):
            errors.append(f"{prefix}.parameter_ids must be a nonempty string list")
        else:
            if len(set(parameter_ids)) != len(parameter_ids):
                errors.append(f"{prefix}.parameter_ids must not contain duplicates")
            expected_ids = KNOWN_CONFLICT_PARAMETER_IDS.get(group, frozenset())
            if set(parameter_ids) != expected_ids:
                errors.append(f"{prefix}.parameter_ids must match the immutable known binding for {group}")
            unknown_ids = sorted(set(parameter_ids) - seen_ids)
            errors.extend(f"{prefix}.parameter_ids references unknown parameter {parameter_id}" for parameter_id in unknown_ids)
        status = binding.get("status")
        if status not in CONFLICT_BINDING_STATES:
            errors.append(f"{prefix}.status must be ACTIVE or RESOLVED")
        if not _is_nonempty_string(binding.get("note")):
            errors.append(f"{prefix}.note must be a nonempty string")

    resolutions = layer.get("conflict_resolutions")
    resolution_by_group: dict[str, dict[str, Any]] = {}
    if resolutions is None:
        resolutions = []
    if not isinstance(resolutions, list):
        errors.append("manufacturer_nominal.conflict_resolutions must be a list")
        resolutions = []
    for index, resolution in enumerate(resolutions):
        prefix = f"manufacturer_nominal.conflict_resolutions[{index}]"
        if not isinstance(resolution, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        missing = sorted(RESOLUTION_REQUIRED_FIELDS - resolution.keys())
        errors.extend(f"{prefix} missing {field}" for field in missing)
        group = resolution.get("conflict_group")
        if not _is_nonempty_string(group) or group not in CONFLICT_GROUPS:
            errors.append(f"{prefix}.conflict_group must identify a known conflict group")
            continue
        if group in resolution_by_group:
            errors.append(f"duplicate conflict resolution {group}")
        else:
            resolution_by_group[group] = resolution
        if resolution.get("status") != "RESOLVED":
            errors.append(f"{prefix}.status must be RESOLVED")
        parameter_ids = resolution.get("parameter_ids")
        expected_ids = KNOWN_CONFLICT_PARAMETER_IDS.get(group, frozenset())
        if (
            not isinstance(parameter_ids, list)
            or not all(_is_nonempty_string(parameter_id) for parameter_id in parameter_ids)
            or set(parameter_ids) != expected_ids
        ):
            errors.append(f"{prefix}.parameter_ids must match the immutable known binding for {group}")
        elif len(parameter_ids) != len(set(parameter_ids)):
            errors.append(f"{prefix}.parameter_ids must not contain duplicates")

        # A resolution must identify the affected assets explicitly.  Deriving
        # this only from a free-form review note would allow a resolution for
        # one received unit to be applied to another asset with the same
        # nominal model name.
        resolution_asset_ids = resolution.get("asset_ids")
        expected_asset_ids = {
            rows_by_id[parameter_id].get("asset_id")
            for parameter_id in expected_ids
            if parameter_id in rows_by_id
        }
        if (
            not isinstance(resolution_asset_ids, list)
            or not resolution_asset_ids
            or not all(_is_nonempty_string(asset_id) for asset_id in resolution_asset_ids)
            or len(resolution_asset_ids) != len(set(resolution_asset_ids))
            or set(resolution_asset_ids) != expected_asset_ids
        ):
            errors.append(f"{prefix}.asset_ids must match the affected conflict parameters")

        # Bind the record to the same checked-in source index as the nominal
        # layer.  This is deliberately a local path check; it does not claim
        # that an external URL has been independently authenticated.
        resolution_source_index = resolution.get("source_index")
        if resolution_source_index != source_index:
            errors.append(f"{prefix}.source_index must match manufacturer_nominal.source_index")
        _repository_file(root, resolution_source_index, f"{prefix}.source_index", errors)

        # Every parameter in the immutable binding must carry the exact
        # source URL/revision currently present in the registry.  A source ref
        # for a different model, or a hand-edited revision string, cannot
        # silently clear the conflict.
        source_refs = resolution.get("source_refs")
        source_ref_ids: list[str] = []
        if not isinstance(source_refs, list) or not source_refs:
            errors.append(f"{prefix}.source_refs must be a nonempty list")
        else:
            for ref_index, source_ref in enumerate(source_refs):
                ref_prefix = f"{prefix}.source_refs[{ref_index}]"
                if not isinstance(source_ref, dict):
                    errors.append(f"{ref_prefix} must be a mapping")
                    continue
                for field in ("parameter_id", "source_url", "source_revision"):
                    if field not in source_ref:
                        errors.append(f"{ref_prefix} missing {field}")
                parameter_id = source_ref.get("parameter_id")
                if not _is_nonempty_string(parameter_id):
                    errors.append(f"{ref_prefix}.parameter_id must be a nonempty string")
                    continue
                source_ref_ids.append(parameter_id)
                if parameter_id not in expected_ids:
                    errors.append(f"{ref_prefix}.parameter_id is not part of conflict group {group}")
                    continue
                if parameter_id in source_ref_ids[:-1]:
                    errors.append(f"{ref_prefix}.parameter_id must not be duplicated")
                row = rows_by_id.get(parameter_id)
                if row is None:
                    errors.append(f"{ref_prefix}.parameter_id references unknown parameter {parameter_id}")
                    continue
                if source_ref.get("source_url") != row.get("source_url"):
                    errors.append(f"{ref_prefix}.source_url must match parameter {parameter_id}")
                if source_ref.get("source_revision") != row.get("source_revision"):
                    errors.append(f"{ref_prefix}.source_revision must match parameter {parameter_id}")
            if set(source_ref_ids) != expected_ids:
                errors.append(f"{prefix}.source_refs must cover the immutable conflict parameters")

        if not _is_nonempty_string(resolution.get("resolution_id")):
            errors.append(f"{prefix}.resolution_id must be a nonempty string")
        review_file = _repository_file(root, resolution.get("review_reference"), f"{prefix}.review_reference", errors)
        if review_file is not None:
            if review_file.stat().st_size == 0:
                errors.append(f"{prefix}.review_reference must reference a nonempty file")
            else:
                try:
                    review_text = review_file.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    errors.append(f"{prefix}.review_reference must be readable UTF-8: {exc}")
                else:
                    review_tokens = [group, *sorted(expected_asset_ids), *sorted(expected_ids)]
                    if isinstance(source_refs, list):
                        review_tokens.extend(
                            source_ref.get("source_url")
                            for source_ref in source_refs
                            if isinstance(source_ref, dict) and _is_nonempty_string(source_ref.get("source_url"))
                        )
                        review_tokens.extend(
                            source_ref.get("source_revision")
                            for source_ref in source_refs
                            if isinstance(source_ref, dict) and _is_nonempty_string(source_ref.get("source_revision"))
                        )
                    for token in review_tokens:
                        if token not in review_text:
                            errors.append(f"{prefix}.review_reference must contain binding token {token}")
        source_url = resolution.get("source_url")
        if not _is_nonempty_string(source_url) or not source_url.startswith("https://"):
            errors.append(f"{prefix}.source_url must be a nonempty https URL")
        elif _is_placeholder_source_url(source_url):
            errors.append(f"{prefix}.source_url must not use a reserved placeholder host")
        source_revision = resolution.get("source_revision")
        if not _is_nonempty_string(source_revision) or source_revision.strip().upper() in {"UNKNOWN", "N/A"}:
            errors.append(f"{prefix}.source_revision must be a nonempty string")
        if not _is_nonempty_string(resolution.get("resolved_on")):
            errors.append(f"{prefix}.resolved_on must be a nonempty string")
        if not _is_nonempty_string(resolution.get("decision")):
            errors.append(f"{prefix}.decision must be a nonempty string")

    for group, expected_ids in sorted(KNOWN_CONFLICT_PARAMETER_IDS.items()):
        binding = binding_by_group.get(group)
        if binding is None:
            errors.append(f"known conflict group {group} is missing its binding record")
            continue
        status = binding.get("status")
        resolution = resolution_by_group.get(group)
        if status == "ACTIVE":
            if resolution is not None:
                errors.append(f"active conflict group {group} cannot carry a resolution record")
            for parameter_id in sorted(expected_ids):
                row = rows_by_id.get(parameter_id)
                if row is None:
                    errors.append(f"known conflict parameter {parameter_id} is missing from the registry")
                    continue
                if (
                    row.get("conflict_group") != group
                    or row.get("conflict") is not True
                    or row.get("model_status") != "VERSION_CONFLICT"
                ):
                    errors.append(
                        f"known conflict parameter {parameter_id} must retain conflict=true, "
                        f"model_status VERSION_CONFLICT and conflict_group {group}"
                    )
        elif status == "RESOLVED":
            if resolution is None:
                errors.append(f"resolved conflict group {group} requires an auditable resolution record")
            for parameter_id in sorted(expected_ids):
                row = rows_by_id.get(parameter_id)
                if row is None:
                    errors.append(f"resolved conflict parameter {parameter_id} is missing from the registry")
                    continue
                if row.get("conflict") is True or row.get("conflict_group") is not None or row.get("model_status") == "VERSION_CONFLICT":
                    errors.append(f"resolved conflict parameter {parameter_id} still carries conflict metadata")

    for group in sorted(resolution_by_group):
        binding = binding_by_group.get(group)
        if binding is None or binding.get("status") != "RESOLVED":
            errors.append(f"conflict resolution {group} requires binding status RESOLVED")

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
