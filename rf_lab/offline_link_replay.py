"""Deterministic telemetry-only datagram replay with simulated faults.

No RF device, socket, UART or flight-command channel is used. Results describe
synthetic frames, not measured link reliability or flight suitability.
"""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
from rf_lab.telemetry_frame import (
    TelemetryFrame, FrameError, TelemetrySequenceWindow,
    decode_telemetry, encode_telemetry,
)

SCENARIO = "r3_readonly_replay_v1"
ROOT = Path(__file__).resolve().parents[1]
FAULT_SCHEDULE = {
    "synthetic_drops": [
        {"session_id": 17, "sequence": 103},
        {"session_id": 17, "sequence": 104},
    ],
    "duplicate_deliveries": [{"session_id": 17, "sequence": 107}],
    "delayed_deliveries": [
        {"session_id": 17, "sequence": 111, "delivered_after_sequence": 112},
    ],
    "corruptions": [
        {"session_id": 17, "sequence": 115, "byte_offset": 12, "xor_mask": "0x80"},
    ],
    "session_transitions": [
        {"from": 17, "to": 18, "first_sequence": 0},
        {"from": 18, "to": 19, "first_sequence": 65534},
    ],
    "wraparound": [{"session_id": 19, "from_sequence": 65535, "to_sequence": 0}],
}


def scenario_packets() -> list[tuple[str, bytes]]:
    packets = [encode_telemetry(TelemetryFrame(17, i, f'{{"sample":{i}}}'.encode('ascii')))
               for i in range(100, 121)]
    events: list[tuple[str, bytes]] = []
    for i, p in enumerate(packets, start=100):
        if i in (103, 104):
            continue
        if i == 111:
            continue  # deliver after 112
        if i == 115:
            broken = bytearray(p)
            broken[12] ^= 0x80
            events.append(("corrupted", bytes(broken)))
        else:
            events.append(("normal", p))
        if i == 107:
            events.append(("duplicate", p))
        if i == 112:
            events.append(("out_of_order", packets[111 - 100]))
    events.append(("new_session", encode_telemetry(TelemetryFrame(18, 0, b'{"start":true}'))))
    # Exercise sequence wrap through the same encode -> decode -> window path
    # as the other replay events, after starting a separate unauthenticated
    # session at the end of the uint16 range.
    events.extend([
        ("wrap_session", encode_telemetry(TelemetryFrame(19, 65534, b'{"start":true}'))),
        ("wrap_before_zero", encode_telemetry(TelemetryFrame(19, 65535, b'{"sample":65535}'))),
        ("wrap_to_zero", encode_telemetry(TelemetryFrame(19, 0, b'{"sample":0}'))),
    ])
    return events


def replay() -> dict[str, object]:
    events = scenario_packets()

    window = TelemetrySequenceWindow()
    counts: Counter[str] = Counter()
    unobserved = 0
    results: list[dict[str, object]] = []
    for label, packet in events:
        try:
            frame = decode_telemetry(packet)
        except FrameError as exc:
            counts["REJECT_" + exc.reason] += 1
            results.append({"label": label, "status": "REJECT_" + exc.reason})
            continue
        receipt = window.ingest(frame)
        counts[receipt.status.value] += 1
        unobserved += receipt.unobserved_sequence_count
        results.append({
            "label": label, "session_id": frame.session_id,
            "sequence": frame.sequence, "status": receipt.status.value,
            "unobserved_sequence_count": receipt.unobserved_sequence_count,
        })
    return {
        "scenario": SCENARIO,
        "fault_schedule": FAULT_SCHEDULE,
        "synthetic_only": True,
        "radio_transmissions": 0,
        "flight_commands": 0,
        "events": results,
        "event_count": len(events),
        "counts": dict(sorted(counts.items())),
        "unobserved_sequence_total": unobserved,
        "warning": "Gaps are unobserved sequence numbers, not measured packet-loss statistics; CRC is not authentication.",
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_sha256() -> dict[str, str]:
    paths = [
        "engineering/rf-offline-contract.yaml",
        "docs/R3_RF_OFFLINE_PROTOCOL.md",
        "rf_lab/telemetry_frame.py",
        "rf_lab/offline_link_replay.py",
        "rf_lab/tests/test_telemetry_frame.py",
        "rf_lab/tests/test_offline_link_replay.py",
        "scripts/check.py",
    ]
    return {
        path: _sha256((ROOT / path).read_bytes())
        for path in paths
    }


def _source_worktree_changes() -> list[str]:
    """Return modified/untracked provenance inputs relative to HEAD."""
    paths = [
        "engineering/rf-offline-contract.yaml",
        "docs/R3_RF_OFFLINE_PROTOCOL.md",
        "rf_lab/telemetry_frame.py",
        "rf_lab/offline_link_replay.py",
        "rf_lab/tests/test_telemetry_frame.py",
        "rf_lab/tests/test_offline_link_replay.py",
        "scripts/check.py",
    ]
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("unable to inspect source worktree state")
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


def _git_sha() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def evidence(command: str, artifact_path: str) -> dict[str, object]:
    """Build a reproducibility record for the fixed synthetic replay."""
    packets = scenario_packets()
    input_trace = [
        {"label": label, "datagram_hex": packet.hex()}
        for label, packet in packets
    ]
    canonical_inputs = json.dumps(
        {"fault_schedule": FAULT_SCHEDULE, "input_trace": input_trace},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    source_changes = _source_worktree_changes()
    return {
        "schema_version": 1,
        "contract": "AA-RF-OFFLINE-001",
        "scenario": SCENARIO,
        "source_git_sha": _git_sha(),
        "source_worktree_clean": not source_changes,
        "source_worktree_changes": source_changes,
        "source_sha256": _source_sha256(),
        "input_trace_sha256": _sha256(canonical_inputs),
        "fault_schedule": FAULT_SCHEDULE,
        "input_trace": input_trace,
        "command": command,
        "tool_versions": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "dependencies": "Python standard library only",
        "artifact_path": artifact_path,
        "reproduction_command": command,
        "seed": "not_applicable_fixed_trace",
        "evidence_ceiling": "TESTED_SOFTWARE",
        "synthetic_only": True,
        "physical_hardware": False,
        "radio_transmissions": 0,
        "flight_commands": 0,
        "crc_is_authentication": False,
        "result": replay(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-evidence", type=Path)
    args = parser.parse_args(argv)
    if args.write_evidence:
        artifact_path = args.write_evidence.as_posix()
        command = (
            "py -3 -m rf_lab.offline_link_replay --write-evidence "
            + "'" + artifact_path.replace("'", "''") + "'"
        )
        result = evidence(command, artifact_path)
        args.write_evidence.parent.mkdir(parents=True, exist_ok=True)
        args.write_evidence.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(json.dumps({
            "evidence": "WRITTEN",
            "event_count": result["result"]["event_count"],
            "counts": result["result"]["counts"],
            "input_trace_sha256": result["input_trace_sha256"],
            "source_git_sha": result["source_git_sha"],
        }, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(replay(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
