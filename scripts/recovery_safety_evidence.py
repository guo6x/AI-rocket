"""Write a source-bound, software-only recovery detectability evidence record."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

from recovery_configuration_audit import audit


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = [
    "flight_computer/src/sensor_validity.cpp",
    "flight_computer/src/flight_fsm.cpp",
    "flight_computer/src/main.cpp",
    "scripts/recovery_configuration_audit.py",
    "scripts/recovery_safety_evidence.py",
    "scripts/tests/test_recovery_configuration_audit.py",
    "docs/RECOVERY_LOGIC_SAFETY_CHANGE_PROPOSAL.md",
]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_sha() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def build_evidence(command: str, artifact_path: str) -> dict[str, object]:
    sensor_path = ROOT / "flight_computer/src/sensor_validity.cpp"
    fsm_path = ROOT / "flight_computer/src/flight_fsm.cpp"
    result = audit(
        sensor_path.read_text(encoding="utf-8"),
        fsm_path.read_text(encoding="utf-8"),
    )
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *SOURCE_PATHS],
        cwd=ROOT, capture_output=True, text=True,
    )
    changes = [line[3:] for line in status.stdout.splitlines() if line.strip()]
    source_sha256 = {
        path: _sha256((ROOT / path).read_bytes()) for path in SOURCE_PATHS
    }
    canonical_input = json.dumps({
        "source_paths": SOURCE_PATHS,
        "audit_scope": result["scope"],
    }, sort_keys=True, separators=(",", ":")).encode("ascii")
    canonical_result = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("ascii")
    return {
        "schema_version": 1,
        "audit": "recovery_launch_detection_static_feasibility",
        "source_git_sha": _git_sha(),
        "source_worktree_clean": not changes,
        "source_worktree_changes": changes,
        "source_sha256": source_sha256,
        "input_sha256": _sha256(canonical_input),
        "result_sha256": _sha256(canonical_result),
        "command": command,
        "reproduction_command": command,
        "python": platform.python_version(),
        "dependencies": "Python standard library only",
        "artifact_path": artifact_path,
        "evidence_ceiling": "TESTED_SOFTWARE",
        "physical_hardware": False,
        "hardware_operation": "NONE",
        "thresholds_or_actuators_modified": False,
        "result": result,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-evidence",
        type=Path,
        default=ROOT / "engineering/offline-evidence/recovery/recovery_safety_audit_20261026.json",
    )
    args = parser.parse_args(argv)
    path = args.write_evidence
    command = (
        "py -3 scripts/recovery_safety_evidence.py --write-evidence "
        + "'" + path.as_posix().replace("'", "''") + "'"
    )
    evidence = build_evidence(command, path.as_posix())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8", newline="\n")
    print(json.dumps({
        "evidence": "WRITTEN",
        "source_git_sha": evidence["source_git_sha"],
        "input_sha256": evidence["input_sha256"],
        "result_sha256": evidence["result_sha256"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
