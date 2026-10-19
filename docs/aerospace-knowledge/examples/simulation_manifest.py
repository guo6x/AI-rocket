"""Research-only, offline simulation artifact manifest checker.

Validates metadata and SHA256 of files in the run's directory. Does not execute
simulation code, operate hardware, edit engineering baselines, or certify a model.
Python 3.10+, standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_TOP = {"schema_version", "run_id", "classification", "intended_use", "unsupported_uses", "model", "source", "runtime", "inputs", "outputs"}


def _nonempty(x: object) -> bool:
    return isinstance(x, str) and bool(x.strip())


def _require_text(value: object, field: str, errors: list[str]) -> None:
    if not _nonempty(value):
        errors.append(f"{field}: nonempty string required")


def _nested_object(obj: dict, key: str, required: set[str], errors: list[str]) -> dict:
    v = obj.get(key)
    if not isinstance(v, dict):
        errors.append(f"{key}: object required")
        return {}
    for field in sorted(required - set(v)):
        errors.append(f"{key}.{field}: missing")
    return v


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_artifacts(manifest: dict, key: str, base: Path, manifest_path: Path, errors: list[str]) -> None:
    artifacts = manifest.get(key)
    if not isinstance(artifacts, list) or not artifacts:
        errors.append(f"{key}: nonempty list required")
        return
    seen: set[str] = set()
    for i, item in enumerate(artifacts):
        prefix = f"{key}[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: object required")
            continue
        p, digest = item.get("path"), item.get("sha256")
        if not _nonempty(p):
            errors.append(f"{prefix}.path: nonempty relative POSIX path required")
            continue
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            errors.append(f"{prefix}.sha256: lowercase 64-hex digest required")
            continue
        if "\\" in p or ":" in p or p.startswith("/"):
            errors.append(f"{prefix}.path: absolute/Windows/backslash path rejected")
            continue
        parts = PurePosixPath(p).parts
        if any(segment in ("", ".", "..") for segment in p.split("/")) or not parts:
            errors.append(f"{prefix}.path: dot segments or empty segments rejected")
            continue
        normalized = "/".join(parts)
        if normalized in seen:
            errors.append(f"{prefix}.path: duplicate {normalized}")
            continue
        seen.add(normalized)
        candidate = base.joinpath(*parts)
        try:
            resolved = candidate.resolve(strict=True)
            if not resolved.is_relative_to(base):
                errors.append(f"{prefix}.path: escapes manifest directory")
                continue
            if resolved == manifest_path:
                errors.append(f"{prefix}.path: manifest cannot hash itself")
                continue
            if not resolved.is_file():
                errors.append(f"{prefix}.path: not a regular file")
                continue
            if sha256_file(resolved) != digest:
                errors.append(f"{prefix}.sha256: content mismatch for {normalized}")
        except (OSError, ValueError) as exc:
            errors.append(f"{prefix}.path: inaccessible ({type(exc).__name__})")


def validate_manifest(manifest_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        manifest_path = manifest_path.resolve(strict=True)
        root = manifest_path.parent
        raw = manifest_path.read_text(encoding="utf-8")
        doc = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"manifest: unreadable or invalid JSON ({type(exc).__name__})"]
    if not isinstance(doc, dict):
        return ["manifest: JSON object required"]
    for key in sorted(REQUIRED_TOP - set(doc)):
        errors.append(f"{key}: missing")
    if type(doc.get("schema_version")) is not int or doc.get("schema_version") != 1:
        errors.append("schema_version: expected integer 1")
    for k in ("run_id", "intended_use"):
        _require_text(doc.get(k), k, errors)
    if doc.get("classification") != "SOFTWARE_SIMULATION_ONLY":
        errors.append("classification: expected SOFTWARE_SIMULATION_ONLY")
    unsupported = doc.get("unsupported_uses")
    if not isinstance(unsupported, list) or not unsupported or not all(_nonempty(s) for s in unsupported):
        errors.append("unsupported_uses: nonempty list of nonempty strings required")
    model = _nested_object(doc, "model", {"name", "version", "coordinate_system", "units", "assumptions", "physical_correlation_status"}, errors)
    for k in ("name", "version", "coordinate_system", "physical_correlation_status"):
        _require_text(model.get(k), "model." + k, errors)
    if not isinstance(model.get("units"), dict) or not model["units"] or not all(_nonempty(k) and _nonempty(v) for k,v in model["units"].items()):
        errors.append("model.units: nonempty mapping of unit labels required")
    if not isinstance(model.get("assumptions"), list) or not all(_nonempty(x) for x in model["assumptions"]):
        errors.append("model.assumptions: list of strings required")
    src = _nested_object(doc, "source", {"repository", "commit"}, errors)
    _require_text(src.get("repository"), "source.repository", errors)
    if not isinstance(src.get("commit"), str) or not HEX40.fullmatch(src["commit"]):
        errors.append("source.commit: lowercase 40-hex git commit required")
    runtime = _nested_object(doc, "runtime", {"python_version", "dependencies", "command", "random_seed"}, errors)
    for k in ("python_version", "command"):
        _require_text(runtime.get(k), "runtime." + k, errors)
    if not isinstance(runtime.get("dependencies"), dict) or not all(_nonempty(k) and _nonempty(v) for k,v in runtime["dependencies"].items()):
        errors.append("runtime.dependencies: mapping of name to pinned version required")
    seed = runtime.get("random_seed", "__MISSING__")
    if seed != "__MISSING__" and seed is not None and type(seed) is not int:
        errors.append("runtime.random_seed: integer or null required")
    _verify_artifacts(doc, "inputs", root, manifest_path, errors)
    _verify_artifacts(doc, "outputs", root, manifest_path, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON manifest next to its archived inputs/outputs")
    args = parser.parse_args()
    errors = validate_manifest(args.manifest)
    if errors:
        for message in errors:
            print("FAIL: " + message, file=sys.stderr)
        return 1
    print("PASS: archive structure and file hashes match; NOT a simulation validity certification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
