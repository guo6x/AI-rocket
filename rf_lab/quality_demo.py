"""Minimal, deterministic read-only R3.2 quality-status demonstration."""
from __future__ import annotations

import argparse
import json

from rf_lab.telemetry_frame import TelemetryFrame, encode_telemetry
from rf_lab.telemetry_quality import TelemetryQualityMonitor


def demo_input_trace() -> list[dict[str, object]]:
    """Return the exact fixed timeline inputs, including the encoded frames."""
    original = encode_telemetry(TelemetryFrame(101, 10, b"synthetic attitude bytes"))
    damaged = bytearray(encode_telemetry(TelemetryFrame(101, 11, b"synthetic data")))
    damaged[-1] ^= 1
    changed = encode_telemetry(TelemetryFrame(202, 0, b"untrusted new session"))
    return [
        {"label": "before_data", "operation": "snapshot", "now_seconds": 0},
        {"label": "first_decoded_untrusted", "operation": "observe_then_snapshot",
         "now_seconds": 0, "datagram_hex": original.hex()},
        {"label": "corrupt_does_not_make_old_sample_recent", "operation": "observe_then_snapshot",
         "now_seconds": 2.5, "datagram_hex": bytes(damaged).hex()},
        {"label": "duplicate_does_not_make_old_sample_recent", "operation": "observe_then_snapshot",
         "now_seconds": 3, "datagram_hex": original.hex()},
        {"label": "new_label_is_not_authenticated", "operation": "observe_then_snapshot",
         "now_seconds": 4, "datagram_hex": changed.hex()},
    ]


def run_demo() -> dict[str, object]:
    monitor = TelemetryQualityMonitor(stale_after_seconds=2.0)
    frames: list[dict[str, object]] = []
    for step in demo_input_trace():
        if step["operation"] == "observe_then_snapshot":
            monitor.observe(bytes.fromhex(str(step["datagram_hex"])),
                            now_seconds=step["now_seconds"])
        frames.append({
            "label": step["label"],
            "status": monitor.snapshot(now_seconds=step["now_seconds"]),
        })

    return {
        "mode": "SYNTHETIC_READ_ONLY",
        "radio_transmissions": 0,
        "command_dispatches": 0,
        "frames": frames,
    }


def check_demo_result(result: dict[str, object]) -> bool:
    by_label = {row["label"]: row["status"] for row in result["frames"]}
    return (
        by_label["before_data"]["freshness"] == "NO_DECODED_SAMPLE"
        and by_label["first_decoded_untrusted"]["freshness"] == "RECENT_UNAUTHENTICATED"
        and by_label["corrupt_does_not_make_old_sample_recent"]["freshness"] == "STALE_UNAUTHENTICATED"
        and by_label["duplicate_does_not_make_old_sample_recent"]["freshness"] == "STALE_UNAUTHENTICATED"
        and by_label["new_label_is_not_authenticated"]["session_change_seen_untrusted"] is True
        and by_label["new_label_is_not_authenticated"]["source_identity"] == "UNAUTHENTICATED"
        and all(not item["status"]["flight_control_authority"] for item in result["frames"])
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    result = run_demo()
    expected = check_demo_result(result)
    print(json.dumps({"result": "PASS" if expected else "FAIL", **result},
                     indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
