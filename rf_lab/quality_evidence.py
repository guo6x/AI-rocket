"""Reproducible R3.2 telemetry-quality and preserved R3.1 evidence record."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from rf_lab.quality_demo import check_demo_result, demo_input_trace, run_demo
from rf_lab.reliability_experiment import (
    _input_trace as r31_input_trace,
    check_invariants as r31_check_invariants,
    run_deterministic_experiment as run_r31_experiment,
)

ROOT = Path(__file__).resolve().parents[1]
R31_ARTIFACT = "engineering/offline-evidence/r3/r3_1_telemetry_reliability.json"
SOURCE_PATHS = (
    "engineering/rf-telemetry-quality-contract.yaml",
    "engineering/rf-reliability-contract.yaml",
    "docs/R3_1_RF_RELIABILITY_EXPERIMENT.md",
    "docs/R3_2_TELEMETRY_QUALITY.md",
    "rf_lab/telemetry_frame.py",
    "rf_lab/telemetry_quality.py",
    "rf_lab/quality_demo.py",
    "rf_lab/quality_evidence.py",
    "rf_lab/reliability_experiment.py",
    "rf_lab/tests/test_reliability_experiment.py",
    "rf_lab/tests/test_telemetry_frame.py",
    "rf_lab/tests/test_telemetry_quality.py",
    "rf_lab/tests/test_quality_demo.py",
    "rf_lab/tests/test_quality_evidence.py",
    "scripts/check.py",
)


def _canonical_sha256(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
        text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _source_worktree_changes() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *SOURCE_PATHS],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("unable to inspect R3.2 evidence source worktree")
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


def evidence(command: str, artifact_path: str) -> dict[str, Any]:
    trace = demo_input_trace()
    demo_result = run_demo()
    if not check_demo_result(demo_result):
        raise AssertionError("R3.2 telemetry-quality demo invariants did not pass")
    r31_result = run_r31_experiment()
    r31_check_invariants(r31_result)
    r31_trace = r31_input_trace()

    r31_artifact_path = ROOT / R31_ARTIFACT
    r31_artifact = json.loads(r31_artifact_path.read_text(encoding="utf-8"))
    r31_trace_hash = _canonical_sha256(r31_trace)
    stable_r31_result_hash = _canonical_sha256(r31_result)
    if r31_trace_hash != r31_artifact["input_trace_sha256"]:
        raise AssertionError("preserved R3.1 trace differs from its committed evidence")
    if stable_r31_result_hash != r31_artifact["deterministic_result_sha256"]:
        raise AssertionError("preserved R3.1 result differs from its committed evidence")

    source_changes = _source_worktree_changes()
    source_hashes = {path: _file_sha256(ROOT / path) for path in SOURCE_PATHS}
    return {
        "schema_version": 1,
        "experiment": "r3_2_synthetic_telemetry_quality_v1",
        "source_git_sha": _git_sha(),
        "source_worktree_clean": not source_changes,
        "source_worktree_changes": source_changes,
        "source_sha256": source_hashes,
        "input_trace": trace,
        "input_trace_sha256": _canonical_sha256(trace),
        "deterministic_result": demo_result,
        "deterministic_result_sha256": _canonical_sha256(demo_result),
        "quality_demo_check_result": "PASS",
        "r3_1_replay": {
            "command": "py -3 -m rf_lab.reliability_experiment --check",
            "result": "PASS",
            "input_trace_sha256": r31_trace_hash,
            "deterministic_result_sha256": stable_r31_result_hash,
            "artifact_path": R31_ARTIFACT,
            "artifact_sha256": _file_sha256(r31_artifact_path),
            "summary": r31_result["summary"],
        },
        "command": command,
        "reproduction_commands": [
            "py -3 -m rf_lab.quality_demo --check",
            "py -3 -m rf_lab.reliability_experiment --check",
            command,
        ],
        "tool_versions": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "dependencies": "Python standard library only",
        "artifact_path": artifact_path,
        "evidence_ceiling": "TESTED_SOFTWARE",
        "synthetic_only": True,
        "physical_hardware": False,
        "radio_transmissions": 0,
        "flight_commands": 0,
        "crc_is_authentication": False,
        "sensor_measurement_time_observed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-evidence", type=Path, required=True,
                        help="write a new evidence JSON without overwriting")
    args = parser.parse_args(argv)
    output = args.write_evidence
    artifact_path = output.as_posix()
    command = (
        "py -3 -m rf_lab.quality_evidence --write-evidence "
        + "'" + artifact_path.replace("'", "''") + "'"
    )
    record = evidence(command, artifact_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
    print(json.dumps({
        "evidence": "WRITTEN",
        "artifact_path": artifact_path,
        "artifact_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "source_git_sha": record["source_git_sha"],
        "source_worktree_clean": record["source_worktree_clean"],
        "input_trace_sha256": record["input_trace_sha256"],
        "deterministic_result_sha256": record["deterministic_result_sha256"],
        "quality_demo_check_result": record["quality_demo_check_result"],
        "r3_1_result": record["r3_1_replay"]["result"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
