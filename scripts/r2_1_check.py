"""Deterministic R2.1 authority validation, not a hardware-readiness grant.

Pending physical stages require no fabricated records. Promoting a physical stage
to READY/COMPLETED instead requires completed prerequisites and confined,
hash-bound current precondition/outcome evidence. Purchase and historical reports
never provide that promotion by themselves.
"""

from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_PATHS = {
    "assets": "engineering/assets/project-asset-registry.yaml",
    "lines": "engineering/experimental-lines.yaml",
    "baseline": "engineering/current-baseline.yaml",
    "plan": "engineering/bringup/gnc-avionics-bringup.yaml",
    "historical": "engineering/historical-hardware-capabilities.yaml",
}
PROHIBITED_PROPULSION_WORK = (
    "Unsupervised energetic propellant preparation",
    "Energetic-material mixing/casting/processing instructions",
    "Ignition-system development for energetic propellant tests",
    "Motor or combustion testing outside an appropriate qualified facility",
)
OWNERSHIP = {"OWNED", "EXCLUDED_CLOSED_TRANSACTION"}
ASSIGNMENT = {"UNASSIGNED", "BENCH_TOOL", "CANDIDATE", "ASSIGNED"}
PURCHASE_VERIFICATION = {
    "PURCHASE_CONFIRMED", "CONFIGURATION_UNVERIFIED", "MODEL_TO_BE_PHOTO_CONFIRMED",
}
PHYSICAL_STATUSES = {"PENDING_HARDWARE", "READY", "COMPLETED", "NOT_REQUIRED"}
SOFTWARE_STATUSES = {"PENDING_SOFTWARE", "COMPLETE_SOFTWARE", "NOT_REQUIRED"}
SATISFIED_STATUSES = {"COMPLETE_SOFTWARE", "COMPLETED", "NOT_REQUIRED"}
OPTIONAL_PHYSICAL_STAGE_IDS = {
    "S3-PROGRAMMER-DETECTION-IF_REQUIRED",
    "S4-FLASH-AND-BOOT-IF_REQUIRED",
}
CLOSED_STATUSES = {
    "CLOSED", "CANCELLED", "CANCELED", "TIMEOUT_CLOSED", "TRANSACTION_CLOSED",
    "EXCLUDED_CLOSED_TRANSACTION", "REFUNDED",
}
COMPLETED_TRANSACTION_STATUSES = {"COMPLETED", "PAID", "DELIVERED", "SUCCESS"}
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}\Z")
COMMIT_RE = re.compile(r"[0-9a-fA-F]{40}\Z")


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate/non-string mapping keys instead of silently overriding."""


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep=False):
    mapping = {}
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
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping,
)
# Retain ISO date scalars as strings so quoted/unquoted dates share one contract.
UniqueKeyLoader.add_constructor(
    "tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node),
)


def _validate_tree(value: Any, path: str, ancestors: set[int] | None = None):
    """Validate all keys and reject recursive aliases before recursive audits."""
    ancestors = set() if ancestors is None else ancestors
    if not isinstance(value, (dict, list)):
        return
    identity = id(value)
    if identity in ancestors:
        raise ValueError(f"{path}: recursive YAML alias is forbidden")
    next_ancestors = ancestors | {identity}
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: YAML mapping keys must be strings")
            _validate_tree(child, f"{path}.{key}", next_ancestors)
    else:
        for index, child in enumerate(value):
            _validate_tree(child, f"{path}[{index}]", next_ancestors)


def _load_yaml(path: Path):
    document = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    _validate_tree(document, path.name)
    return document


def load_documents(root: Path = ROOT) -> dict[str, Any]:
    """Load all R2.1 authorities strictly; callers may catch parse/IO failures."""
    return {name: _load_yaml(Path(root) / relative) for name, relative in DOCUMENT_PATHS.items()}


def _mapping(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path} must be a mapping")
        return {}
    return value


def _string(value: Any, path: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a nonempty string")
        return None
    return value


def _strings(value: Any, path: str, errors: list[str], *, nonempty=False) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{path} must be a list of strings")
        return []
    if nonempty and not value:
        errors.append(f"{path} must not be empty")
    strings = []
    for index, item in enumerate(value):
        text = _string(item, f"{path}[{index}]", errors)
        if text is not None:
            strings.append(text)
    if len(strings) != len(set(strings)):
        errors.append(f"{path} must not contain duplicate references")
    return strings


def _rows(value: Any, path: str, errors: list[str], *, nonempty=True) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append(f"{path} must be a list of mappings")
        return []
    if nonempty and not value:
        errors.append(f"{path} must not be empty")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{path}[{index}] must be a mapping")
        else:
            result.append(item)
    return result


def _indexed(rows: list[dict[str, Any]], field: str, path: str, errors: list[str], *, label=None):
    result = {}
    for index, row in enumerate(rows):
        value = _string(row.get(field), f"{path}[{index}].{field}", errors)
        if value is None:
            continue
        if value in result:
            errors.append(f"{path}: duplicate {label or field} {value}")
        else:
            result[value] = row
    return result


def _enum(value: Any, allowed: set[str], path: str, errors: list[str]):
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{path} must be one of {', '.join(sorted(allowed))}")


def _version(document: dict[str, Any], expected: int, path: str, errors: list[str]):
    value = document.get("schema_version")
    if type(value) is not int or value != expected:
        errors.append(f"{path}.schema_version must be integer {expected}")


def _forbid_purchase_hardware_promotion(value: Any, path: str, errors: list[str]):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"verification", "status", "evidence_class", "evidence_level"} and child == "VERIFIED_HARDWARE":
                errors.append(f"{path}.{key}: purchase/ownership cannot establish VERIFIED_HARDWARE")
            _forbid_purchase_hardware_promotion(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _forbid_purchase_hardware_promotion(child, f"{path}[{index}]", errors)


def _validate_assets(document: dict[str, Any], errors: list[str]):
    sources = _indexed(_rows(document.get("source_basis"), "assets.source_basis", errors), "id", "assets.source_basis", errors, label="source id")
    excluded_rows = _rows(document.get("excluded_transactions"), "assets.excluded_transactions", errors, nonempty=False)
    excluded = _indexed(excluded_rows, "record_id", "assets.excluded_transactions", errors)
    excluded_items = set()
    for record_id, row in excluded.items():
        item = _string(row.get("item"), f"excluded transaction {record_id}.item", errors)
        _string(row.get("reason"), f"excluded transaction {record_id}.reason", errors)
        if item:
            excluded_items.add(item.strip().casefold())

    closed_sources = set(excluded)
    for source_id, source in sources.items():
        _string(source.get("type"), f"source {source_id}.type", errors)
        source_record = source.get("record_id")
        if "record_id" in source:
            source_record = _string(source_record, f"source {source_id}.record_id", errors)
        transaction_status = source.get("transaction_status")
        status = transaction_status.upper() if isinstance(transaction_status, str) else None
        if "transaction_status" in source and status not in CLOSED_STATUSES | COMPLETED_TRANSACTION_STATUSES:
            errors.append(f"source {source_id}.transaction_status must be a recognized completed or closed status")
        if status in CLOSED_STATUSES or source_id in excluded or source_record in excluded:
            closed_sources.add(source_id)

    rows = _rows(document.get("assets"), "assets.assets", errors)
    assets = _indexed(rows, "asset_id", "assets.assets", errors)
    asset_unit_ids = set(assets)
    _forbid_purchase_hardware_promotion(document.get("assets"), "assets.assets", errors)
    for asset_id, asset in assets.items():
        prefix = f"asset {asset_id}"
        item = _string(asset.get("item"), f"{prefix}.item", errors)
        quantity = asset.get("quantity")
        if type(quantity) is not int or quantity <= 0:
            errors.append(f"{prefix}.quantity must be a positive integer (not boolean)")
        if "unit_ids" in asset:
            units = _strings(asset["unit_ids"], f"{prefix}.unit_ids", errors, nonempty=True)
            if type(quantity) is int and len(units) != quantity:
                errors.append(f"{prefix}.unit_ids count must match quantity")
            for unit in units:
                if unit in asset_unit_ids:
                    errors.append(f"{prefix}: duplicate asset/unit id {unit}")
                asset_unit_ids.add(unit)
        _enum(asset.get("ownership"), OWNERSHIP, f"{prefix}.ownership", errors)
        _enum(asset.get("assignment"), ASSIGNMENT, f"{prefix}.assignment", errors)
        _enum(asset.get("verification"), PURCHASE_VERIFICATION, f"{prefix}.verification", errors)
        if "candidate_lines" in asset:
            _strings(asset["candidate_lines"], f"{prefix}.candidate_lines", errors)
        evidence = _string(asset.get("ownership_evidence"), f"{prefix}.ownership_evidence", errors)
        if asset.get("ownership") == "OWNED":
            if asset_id in excluded or evidence in closed_sources or (item and item.strip().casefold() in excluded_items):
                errors.append(f"{prefix}: excluded/closed transaction cannot establish OWNED")
            if evidence and evidence not in sources:
                errors.append(f"{prefix}: unknown ownership_evidence {evidence}")
        if asset.get("ownership") == "EXCLUDED_CLOSED_TRANSACTION" and asset.get("assignment") != "UNASSIGNED":
            errors.append(f"{prefix}: excluded asset must remain UNASSIGNED")
    return assets


def _validate_lines(document, baseline, assets, errors):
    rows = _rows(document.get("lines"), "lines.lines", errors)
    lines = _indexed(rows, "line_id", "lines.lines", errors)
    articles = _indexed(rows, "article_id", "lines.lines", errors)
    for line_id, line in lines.items():
        _string(line.get("status"), f"line {line_id}.status", errors)
        refs = _strings(line.get("current_assets", []), f"line {line_id}.current_assets", errors)
        for ref in refs:
            if ref not in assets:
                errors.append(f"line {line_id}: unknown asset {ref}")
            elif assets[ref].get("ownership") != "OWNED":
                errors.append(f"line {line_id}: excluded asset {ref} cannot be assigned")
        if line.get("status") == "VERIFIED_HARDWARE":
            errors.append(f"line {line_id}: purchase/ownership cannot establish VERIFIED_HARDWARE; use a separate current hardware evidence gate")
    priority = _strings(document.get("priority_order"), "lines.priority_order", errors, nonempty=True)
    if set(priority) != set(lines):
        errors.append("lines.priority_order must reference each declared line exactly once")

    science = lines.get("MATERIALS_PROPULSION_SCIENCE")
    if science is None:
        errors.append("MATERIALS_PROPULSION_SCIENCE line is required")
    else:
        prohibited = _strings(science.get("prohibited_work"), "MATERIALS_PROPULSION_SCIENCE.prohibited_work", errors, nonempty=True)
        missing = sorted(set(PROHIBITED_PROPULSION_WORK) - set(prohibited))
        if missing:
            errors.append(f"MATERIALS_PROPULSION_SCIENCE.prohibited_work missing: {', '.join(missing)}")
        allowed = _strings(science.get("allowed_next_work", []), "MATERIALS_PROPULSION_SCIENCE.allowed_next_work", errors)
        if set(allowed) & set(prohibited):
            errors.append("MATERIALS_PROPULSION_SCIENCE.allowed_next_work conflicts with prohibited_work")
    model = _mapping(baseline.get("project_development_model"), "baseline.project_development_model", errors)
    baseline_rows = _rows(model.get("technical_lines"), "baseline.technical_lines", errors)
    baseline_lines = _indexed(baseline_rows, "line_id", "baseline.technical_lines", errors)
    _indexed(baseline_rows, "article_id", "baseline.technical_lines", errors)
    for index, row in enumerate(baseline_rows):
        _string(row.get("article_id"), f"baseline.technical_lines[{index}].article_id", errors)
    if {key: row.get("article_id") for key, row in baseline_lines.items()} != {key: row.get("article_id") for key, row in lines.items()}:
        errors.append("baseline technical_lines must match experimental-lines line/article mapping exactly")
    return articles


def _confined_file(reference, root, path, errors):
    row = _mapping(reference, path, errors)
    name = _string(row.get("path"), f"{path}.path", errors)
    digest = row.get("sha256")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        errors.append(f"{path}.sha256 must be an exact 64-hex SHA-256")
    if not name:
        return None
    relative = PurePosixPath(name)
    if "\\" in name or ":" in name or relative.is_absolute() or ".." in relative.parts or relative.parts[:3] != ("engineering", "evidence", "records"):
        errors.append(f"{path}.path must be confined under engineering/evidence/records/ as a repository-relative POSIX path")
        return None
    try:
        target = (root / name).resolve()
        approved = (root / "engineering/evidence/records").resolve()
        target.relative_to(approved)
        approved.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{path}.path must be confined under engineering/evidence/records/ (symlink/escape rejected)")
        return None
    except (OSError, RuntimeError):
        errors.append(f"{path}.path cannot be resolved safely as a confined evidence file")
        return None
    if not target.is_file():
        errors.append(f"{path}: evidence file does not exist: {name}")
        return None
    try:
        actual_digest = sha256(target.read_bytes()).hexdigest()
    except OSError as exc:
        errors.append(f"{path}: cannot read evidence file {name}: {type(exc).__name__}")
        return None
    if isinstance(digest, str) and actual_digest != digest.lower():
        errors.append(f"{path}: SHA-256 mismatch for {name}")
        return None
    return target


def _validate_software_evidence(stage, root, errors):
    if "software_evidence" not in stage:
        return
    prefix = f"stage {stage.get('stage_id')}.software_evidence"
    refs = _strings(stage["software_evidence"], prefix, errors, nonempty=True)
    for name in refs:
        relative = PurePosixPath(name)
        if "\\" in name or ":" in name or relative.is_absolute() or ".." in relative.parts:
            errors.append(f"{prefix}: software evidence must be a confined repository-relative POSIX path: {name}")
            continue
        try:
            resolved = (root / name).resolve()
            resolved.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{prefix}: software evidence must be confined to the repository: {name}")
            continue
        except (OSError, RuntimeError):
            errors.append(f"{prefix}: software evidence path cannot be resolved safely: {name}")
            continue
        if not resolved.is_file():
            errors.append(f"{prefix}: software evidence file does not exist: {name}")


def _validate_stage_evidence(stage, applies_to, root, record_ids, errors):
    stage_id = stage.get("stage_id")
    prefix = f"stage {stage_id}"
    refs = stage.get("evidence_records", [])
    needs_evidence = isinstance(stage.get("status"), str) and stage["status"] in {"READY", "COMPLETED"}
    if needs_evidence and not refs:
        errors.append(f"{prefix} {stage.get('status')} requires current evidence_records")
    rows = _rows(refs, f"{prefix}.evidence_records", errors, nonempty=False)
    seen_paths = set()
    valid_outcomes = set()
    for index, ref in enumerate(rows):
        ref_prefix = f"{prefix}.evidence_records[{index}]"
        record_path = _confined_file(ref, root, ref_prefix, errors)
        if record_path is None:
            continue
        if record_path in seen_paths:
            errors.append(f"{prefix}: duplicate evidence record path {ref.get('path')}")
        seen_paths.add(record_path)
        if record_path.suffix.lower() not in {".yaml", ".yml"}:
            errors.append(f"{ref_prefix}: evidence record must be a YAML document")
            continue
        try:
            loaded = _load_yaml(record_path)
        except (OSError, ValueError, yaml.YAMLError, RecursionError) as exc:
            errors.append(f"{ref_prefix}: invalid evidence YAML: {exc}")
            continue
        record = _mapping(loaded, ref_prefix, errors)
        before = len(errors)
        _version(record, 1, ref_prefix, errors)
        record_id = _string(record.get("record_id"), f"{ref_prefix}.record_id", errors)
        if record_id in record_ids:
            errors.append(f"{ref_prefix}: duplicate physical evidence record_id {record_id}")
        elif record_id:
            record_ids.add(record_id)
        record_type = record.get("record_type")
        if not isinstance(record_type, str) or record_type not in {"hardware_observation", "hardware_regression"}:
            errors.append(f"{ref_prefix}.record_type must be current hardware_observation or hardware_regression, not purchase/history evidence")
        if record.get("stage_id") != stage_id:
            errors.append(f"{ref_prefix}.stage_id must match {stage_id}")
        if record.get("article_id") not in applies_to:
            errors.append(f"{ref_prefix}.article_id must be in applies_to")
        for field in ("operator", "method", "tool"):
            _string(record.get(field), f"{ref_prefix}.{field}", errors)
        source_commit = record.get("source_commit")
        if not isinstance(source_commit, str) or not COMMIT_RE.fullmatch(source_commit):
            errors.append(f"{ref_prefix}.source_commit must be an exact 40-hex Git SHA")
        raw_date = record.get("date")
        try:
            if not isinstance(raw_date, str) or date.fromisoformat(raw_date).isoformat() != raw_date:
                raise ValueError
        except ValueError:
            errors.append(f"{ref_prefix}.date must be an ISO calendar date YYYY-MM-DD")
        _strings(record.get("observations"), f"{ref_prefix}.observations", errors, nonempty=True)
        artifact_refs = _rows(record.get("artifact_refs"), f"{ref_prefix}.artifact_refs", errors)
        for artifact_index, artifact in enumerate(artifact_refs):
            raw_path = _confined_file(artifact, root, f"{ref_prefix}.artifact_refs[{artifact_index}]", errors)
            if raw_path == record_path:
                errors.append(f"{ref_prefix}: raw artifact must not reference its own metadata record")
        outcome = record.get("outcome")
        _enum(outcome, {"PRECONDITIONS_SATISFIED", "PASS"}, f"{ref_prefix}.outcome", errors)
        if len(errors) == before:
            valid_outcomes.add(outcome)
    if stage.get("status") == "COMPLETED" and "PASS" not in valid_outcomes:
        errors.append(f"{prefix}: COMPLETED requires outcome PASS in a valid current record")
    if stage.get("status") == "READY" and not valid_outcomes:
        errors.append(f"{prefix}: READY requires outcome PRECONDITIONS_SATISFIED or PASS in a valid current record")


def _validate_stages(document, articles, root, errors):
    applies_to = _strings(document.get("applies_to"), "plan.applies_to", errors, nonempty=True)
    for article_id in applies_to:
        if article_id not in articles:
            errors.append(f"plan.applies_to references unknown article {article_id}")
    rows = _rows(document.get("stages"), "plan.stages", errors)
    stages = _indexed(rows, "stage_id", "plan.stages", errors)
    order = {stage_id: index for index, stage_id in enumerate(stages)}
    dependencies = {}
    record_ids = set()
    for stage_id, stage in stages.items():
        prefix = f"stage {stage_id}"
        physical = stage.get("physical_action")
        if type(physical) is not bool:
            errors.append(f"{prefix}.physical_action must be boolean")
        allowed = PHYSICAL_STATUSES if physical is True else SOFTWARE_STATUSES
        status = stage.get("status")
        if not isinstance(status, str) or status not in allowed:
            kind = "physical" if physical is True else "software"
            errors.append(f"{prefix}: {kind} stage has invalid status; expected {', '.join(sorted(allowed))}")
        if status == "NOT_REQUIRED":
            _string(stage.get("not_required_reason"), f"{prefix}.not_required_reason", errors)
            if stage.get("optional") is not True:
                errors.append(f"{prefix}: NOT_REQUIRED is allowed only for an explicitly optional stage")
            if physical is True and stage_id not in OPTIONAL_PHYSICAL_STAGE_IDS:
                errors.append(f"{prefix}: mandatory physical observation/sensor/regression stages cannot be NOT_REQUIRED")
        if "optional" in stage and type(stage["optional"]) is not bool:
            errors.append(f"{prefix}.optional must be boolean")
        if physical is True and stage.get("optional") is True and stage_id not in OPTIONAL_PHYSICAL_STAGE_IDS:
            errors.append(f"{prefix}: only conditional programmer-detection/flash stages may be optional")
        deps = _strings(stage.get("depends_on"), f"{prefix}.depends_on", errors)
        if physical is True and not deps:
            errors.append(f"{prefix}: physical stage requires at least one explicit earlier prerequisite")
        dependencies[stage_id] = deps
        for dependency in deps:
            if dependency not in stages:
                errors.append(f"{prefix}: unknown prerequisite {dependency}")
            elif order[dependency] >= order[stage_id]:
                errors.append(f"{prefix}: prerequisite {dependency} must precede {stage_id} in stages")
            if isinstance(status, str) and status in {"READY", "COMPLETED", "COMPLETE_SOFTWARE", "NOT_REQUIRED"}:
                prerequisite = stages.get(dependency, {})
                if not isinstance(prerequisite.get("status"), str) or prerequisite["status"] not in SATISFIED_STATUSES:
                    errors.append(f"{prefix}: unsatisfied prerequisite {dependency} ({prerequisite.get('status', 'UNKNOWN')})")
        _validate_stage_evidence(stage, applies_to, root, record_ids, errors)
        _validate_software_evidence(stage, root, errors)

    visiting, visited = set(), set()

    def visit(stage_id):
        if stage_id in visiting:
            errors.append(f"plan: dependency cycle includes {stage_id}")
            return
        if stage_id in visited:
            return
        visiting.add(stage_id)
        for dependency in dependencies.get(stage_id, []):
            if dependency in stages:
                visit(dependency)
        visiting.remove(stage_id)
        visited.add(stage_id)

    for stage_id in stages:
        visit(stage_id)

    def has_completed_software_ancestor(stage_id, seen):
        if stage_id in seen:
            return False
        for dependency in dependencies.get(stage_id, []):
            prerequisite = stages.get(dependency, {})
            if prerequisite.get("physical_action") is False and prerequisite.get("status") == "COMPLETE_SOFTWARE":
                return True
            if has_completed_software_ancestor(dependency, seen | {stage_id}):
                return True
        return False

    for stage_id, stage in stages.items():
        if stage.get("physical_action") is True and stage.get("status") in ("READY", "COMPLETED"):
            if not has_completed_software_ancestor(stage_id, set()):
                errors.append(f"stage {stage_id}: active physical path requires a completed software ancestor")


def _validate_historical(document, errors):
    rows = _rows(document.get("capabilities"), "historical.capabilities", errors)
    capabilities = _indexed(rows, "capability_id", "historical.capabilities", errors)
    for capability_id, capability in capabilities.items():
        prefix = f"capability {capability_id}"
        _enum(capability.get("historical_level"), {"HISTORICALLY_REPORTED_HARDWARE", "NOT_FOUND"}, f"{prefix}.historical_level", errors)
        _strings(capability.get("historical_sources"), f"{prefix}.historical_sources", errors, nonempty=True)
        continuity = capability.get("current_code_continuity")
        if type(continuity) is not bool:
            errors.append(f"{prefix}.current_code_continuity must be boolean")
        _strings(capability.get("current_sources"), f"{prefix}.current_sources", errors, nonempty=continuity is True)
        if capability_id == "HWCAP-LORA-001" and capability.get("historical_level") != "NOT_FOUND":
            errors.append("LoRa has no historical physical-link evidence and must not inherit WiFi verification")


def evaluate_documents(documents: dict[str, Any], root: Path = ROOT) -> list[str]:
    """Return sorted actionable errors; pending physical work is not an error."""
    errors: list[str] = []
    try:
        _validate_tree(documents, "documents")
    except (ValueError, RecursionError) as exc:
        return [str(exc)]
    if not isinstance(documents, dict):
        return ["documents must be a mapping"]
    docs = {name: _mapping(documents.get(name), name, errors) for name in DOCUMENT_PATHS}
    for name, document in docs.items():
        _version(document, 2 if name == "baseline" else 1, name, errors)
    assets = _validate_assets(docs["assets"], errors)
    articles = _validate_lines(docs["lines"], docs["baseline"], assets, errors)
    _validate_stages(docs["plan"], articles, Path(root), errors)
    _validate_historical(docs["historical"], errors)
    return sorted(set(errors))


def validate(root: Path = ROOT) -> list[str]:
    """Load/validate without mutating the repository or executing physical steps."""
    root = Path(root)
    documents = {}
    errors = []
    for name, relative in DOCUMENT_PATHS.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing required R2.1 authority: {relative}")
            continue
        try:
            documents[name] = _load_yaml(path)
        except (OSError, ValueError, yaml.YAMLError, RecursionError) as exc:
            errors.append(f"{relative}: YAML load failed: {exc}")
    if errors:
        return sorted(set(errors))
    return evaluate_documents(documents, root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root (read-only)")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON")
    arguments = parser.parse_args(argv)
    errors = validate(arguments.root)
    result = {
        "errors": errors,
        "hardware_status": "NOT_EVALUATED",
        "structure_status": "FAIL" if errors else "PASS",
    }
    if arguments.json:
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        for error in errors:
            print(f"R2.1 ERROR: {error}")
        print("Hardware verification: NOT_EVALUATED (historical/purchase evidence is not current hardware acceptance)")
        print(f"R2.1 STRUCTURE CHECK: {result['structure_status']}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
