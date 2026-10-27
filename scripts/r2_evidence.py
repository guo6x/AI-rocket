"""Read-only integrity checks for indexed physical evidence (not certification)."""

from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path
import re
from typing import Any

import yaml


def filled(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not any(
        marker in value.upper() for marker in ("REPLACE", "YYYY", "UNKNOWN", "TBD")
    )


def walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def validate_evidence_files(documents: dict[str, Any], root: Path) -> list[str]:
    """Require local YAML records and hashes; never fetch external photo references."""
    try:
        return _validate_evidence_files(documents, root)
    except (KeyError, TypeError, ValueError, AttributeError, OSError) as exc:
        return [f"Invalid evidence structure: {type(exc).__name__}: {exc}"]


def _validate_evidence_files(documents: dict[str, Any], root: Path) -> list[str]:
    errors = []
    loaded = {}
    article_id = documents["article"]["article_id"]
    components = {item["component_id"] for item in documents["inventory"]["components"]}
    measurements = {item["measurement_id"] for item in documents["plan"]["measurements"]}
    coverage_vocabulary = set(documents["plan"].get("coverage_vocabulary") or {"single_component"})
    allowed = (root / "engineering/evidence/records").resolve()
    for entry in documents["evidence"].get("evidence_records") or []:
        record_id = entry.get("record_id", "<missing>")
        prefix = f"Evidence {record_id}"
        relative = entry.get("path")
        if not isinstance(relative, str) or not relative:
            errors.append(f"{prefix}: path is required")
            continue
        path = (root / relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(allowed):
            errors.append(f"{prefix}: path must stay under engineering/evidence/records/")
            continue
        if path.suffix.lower() not in {".yaml", ".yml"}:
            errors.append(f"{prefix}: record must be a YAML file")
            continue
        try:
            raw = path.read_bytes()
            record = yaml.safe_load(raw.decode("utf-8-sig"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            errors.append(f"{prefix}: cannot read record: {exc}")
            continue
        digest = hashlib.sha256(raw).hexdigest()
        if entry.get("sha256") != digest:
            errors.append(f"{prefix}: sha256 does not match record bytes")
        if not isinstance(record, dict):
            errors.append(f"{prefix}: record must be a mapping")
            continue
        loaded[record_id] = record
        for field, expected in (
            ("schema_version", 1), ("record_id", record_id),
            ("article_id", article_id), ("record_type", entry.get("record_type")),
        ):
            if record.get(field) != expected:
                errors.append(f"{prefix}: {field} does not match index/article/schema")
        if record.get("component_id") not in components:
            errors.append(f"{prefix}: unknown component_id")
        for field in ("operator", "method", "tool"):
            if not filled(record.get(field)):
                errors.append(f"{prefix}: {field} must be filled")
        try:
            date.fromisoformat(str(record.get("date")))
        except ValueError:
            errors.append(f"{prefix}: date must be a real ISO date")
        if not re.fullmatch(r"[0-9a-fA-F]{40}", str(record.get("source_commit", ""))):
            errors.append(f"{prefix}: source_commit must be a full Git SHA")
        photos = record.get("photo_refs")
        if not isinstance(photos, list) or not photos:
            errors.append(f"{prefix}: photo_refs must be a non-empty list")
        else:
            for photo in photos:
                if not isinstance(photo, dict) or not filled(photo.get("location")) or not re.fullmatch(
                    r"[0-9a-f]{64}", str(photo.get("sha256", ""))
                ):
                    errors.append(f"{prefix}: each photo needs a location and lowercase sha256")
        record_type = record.get("record_type")
        if record_type == "measurement":
            if record.get("measurement_id") not in measurements:
                errors.append(f"{prefix}: unknown measurement_id")
            if record.get("raw_measurement") is None or record.get("raw_measurement") in ([], {}, ""):
                errors.append(f"{prefix}: raw_measurement is required")
            if not filled(record.get("unit")):
                errors.append(f"{prefix}: unit is required")
            if record.get("uncertainty") is None:
                errors.append(f"{prefix}: uncertainty is required (use an explicit limitation if unknown)")
        elif record_type == "hardware_observation":
            observations = record.get("observations")
            if not isinstance(observations, list) or not observations or not all(filled(x) for x in observations):
                errors.append(f"{prefix}: observations must be non-empty text entries")
        else:
            errors.append(f"{prefix}: unsupported record_type")

    for component in documents["inventory"]["components"]:
        if component.get("evidence_class") not in {"OBSERVED", "MEASURED"}:
            continue
        for ref in component.get("evidence_source") or []:
            record = loaded.get(ref, {})
            if record.get("component_id") != component["component_id"]:
                errors.append(f"{component['component_id']}: evidence {ref} belongs to another component")
            if component.get("evidence_class") == "MEASURED" and record.get("record_type") != "measurement":
                errors.append(f"{component['component_id']}: MEASURED requires measurement records")
    for measurement in documents["plan"]["measurements"]:
        coverage = measurement.get("coverage", "single_component")
        if coverage not in coverage_vocabulary:
            errors.append(f"{measurement['measurement_id']}: unsupported coverage policy {coverage}")
        if coverage == "each_component_and_unit" and "unit_id" not in (measurement.get("fields") or []):
            errors.append(f"{measurement['measurement_id']}: each_component_and_unit requires a unit_id field")
        covered_components: dict[str, set[str]] = {}
        unit_components: dict[str, set[str]] = {}
        for ref in measurement.get("evidence_refs") or []:
            record = loaded.get(ref, {})
            if record.get("component_id") not in measurement.get("component_ids", []):
                errors.append(f"{measurement['measurement_id']}: evidence {ref} belongs to another component")
            if record.get("record_type") == "measurement" and record.get("measurement_id") != measurement["measurement_id"]:
                errors.append(f"{measurement['measurement_id']}: evidence {ref} belongs to another measurement")
            if measurement.get("status") == "NOT_APPLICABLE" and record.get("record_type") != "hardware_observation":
                errors.append(f"{measurement['measurement_id']}: NOT_APPLICABLE requires observation evidence")
            component_id = record.get("component_id")
            if coverage == "each_component_and_unit" and component_id in measurement.get("component_ids", []):
                physical_unit_id = record.get("physical_unit_id")
                if not filled(physical_unit_id):
                    errors.append(
                        f"{measurement['measurement_id']}: evidence {ref} requires physical_unit_id"
                    )
                else:
                    covered_components.setdefault(component_id, set()).add(physical_unit_id)
                    unit_components.setdefault(physical_unit_id, set()).add(component_id)
        if coverage == "each_component_and_unit" and measurement.get("status") in {"RECORDED", "NOT_APPLICABLE"}:
            expected_components = set(measurement.get("component_ids") or [])
            missing_components = expected_components - set(covered_components)
            if missing_components:
                errors.append(
                    f"{measurement['measurement_id']}: evidence must cover each component: "
                    f"{sorted(missing_components)}"
                )
            shared_units = {
                unit_id: sorted(component_ids)
                for unit_id, component_ids in unit_components.items()
                if len(component_ids) > 1
            }
            if shared_units:
                errors.append(
                    f"{measurement['measurement_id']}: physical_unit_id cannot be shared across components: "
                    f"{shared_units}"
                )
    for name, document in documents.items():
        for node in walk(document):
            if not isinstance(node, dict) or node.get("status") != "MEASURED":
                continue
            for ref in node.get("evidence") or node.get("evidence_refs") or []:
                if loaded.get(ref, {}).get("record_type") != "measurement":
                    errors.append(f"{name}: MEASURED value requires measurement evidence, not {ref}")
    return errors
