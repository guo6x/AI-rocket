"""Generate deterministic evidence for the isolated JSON <-> R3 contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess

from rf_lab.json_r3_contract import OfflineJsonR3Receiver, encode_json_telemetry


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = [
    "engineering/json-r3-telemetry-contract.yaml",
    "docs/JSON_R3_TELEMETRY_CONTRACT.md",
    "docs/RECOVERY_LOGIC_SAFETY_CHANGE_PROPOSAL.md",
    "rf_lab/json_r3_contract.py",
    "rf_lab/telemetry_frame.py",
    "rf_lab/contract_evidence.py",
    "rf_lab/tests/test_json_r3_contract.py",
    "ground_station/core/telemetry_parser.py",
    "ground_station/tests/test_telemetry_parser.py",
]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_sha() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _sample() -> dict[str, object]:
    return {
        "time": 1001,
        "sample_time_ms": 1000,
        "sensor_valid": 1,
        "source_mode": "PHYSICAL",
        "pitch_raw": 2.0,
        "pitch_flt": 1.8,
        "roll_raw": -1.0,
        "roll_flt": -0.8,
        "yaw": 0.2,
        "alt": 12.3,
        "batt": 7.4,
        "auto": 0,
        "control_state": "IDLE",
        "chute": 0,
        "fstate": "IDLE",
    }


def _trace() -> dict[str, object]:
    receiver = OfflineJsonR3Receiver()
    first = encode_json_telemetry(_sample(), session_id=7, sequence=10)
    forward = encode_json_telemetry(
        {**_sample(), "time": 1002}, session_id=7, sequence=12
    )
    stale = encode_json_telemetry(
        {**_sample(), "time": 1003}, session_id=7, sequence=11
    )
    corrupt = bytearray(encode_json_telemetry(
        {**_sample(), "time": 1004}, session_id=7, sequence=13
    ))
    corrupt[-1] ^= 1
    changed = encode_json_telemetry(
        {**_sample(), "time": 1005}, session_id=8, sequence=0
    )
    offered = [
        ("first", first, 10),
        ("duplicate", first, 11),
        ("forward_gap", forward, 12),
        ("stale", stale, 13),
        ("crc_corruption", bytes(corrupt), 14),
        ("session_change", changed, 15),
    ]
    results = []
    for label, datagram, receive_time_ms in offered:
        result = receiver.ingest(datagram, receive_time_ms=receive_time_ms)
        results.append({
            "label": label,
            "status": result["status"],
            "authority": result["flight_control_authority"],
            "unobserved_sequence_count": (
                result.get("record", {}).get("unobserved_sequence_count", 0)
                if result.get("record") else 0
            ),
        })
    return {
        "offered_count": len(offered),
        "results": results,
        "bound_session_id": receiver.window.session_id,
        "last_sequence": receiver.window.last_sequence,
        "all_results_have_no_control_authority": all(
            not item["authority"] for item in results
        ),
    }


def build_evidence(command: str, artifact_path: str) -> dict[str, object]:
    trace = _trace()
    canonical_input = json.dumps(
        {"sample": _sample(), "trace_labels": [
            "first", "duplicate", "forward_gap", "stale", "crc_corruption", "session_change"
        ]}, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    canonical_result = json.dumps(trace, sort_keys=True, separators=(",", ":")).encode("ascii")
    source_sha256 = {
        path: _sha256((ROOT / path).read_bytes()) for path in SOURCE_PATHS
    }
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *SOURCE_PATHS],
        cwd=ROOT, capture_output=True, text=True,
    )
    changes = [line[3:] for line in status.stdout.splitlines() if line.strip()]
    return {
        "schema_version": 1,
        "contract": "AA-JSON-R3-TELEMETRY-001",
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
        "synthetic_only": True,
        "physical_hardware": False,
        "radio_transmissions": 0,
        "flight_commands": 0,
        "crc_is_authentication": False,
        "result": trace,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    path = args.write_evidence
    command = (
        "py -3 -m rf_lab.contract_evidence --write-evidence "
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
