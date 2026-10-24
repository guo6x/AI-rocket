"""Minimal, deterministic read-only R3.2 quality-status demonstration."""
from __future__ import annotations

import argparse
import json

from rf_lab.telemetry_frame import TelemetryFrame, encode_telemetry
from rf_lab.telemetry_quality import TelemetryQualityMonitor


def run_demo() -> dict[str, object]:
    monitor = TelemetryQualityMonitor(stale_after_seconds=2.0)
    frames: list[dict[str, object]] = []

    def record(label: str, timestamp: float) -> None:
        frames.append({"label": label, "status": monitor.snapshot(now_seconds=timestamp)})

    record("before_data", 0)
    original = encode_telemetry(TelemetryFrame(101, 10, b"synthetic attitude bytes"))
    monitor.observe(original, now_seconds=0)
    record("first_decoded_untrusted", 0)

    damaged = bytearray(encode_telemetry(TelemetryFrame(101, 11, b"synthetic data")))
    damaged[-1] ^= 1
    monitor.observe(bytes(damaged), now_seconds=2.5)
    record("corrupt_does_not_make_old_sample_recent", 2.5)

    monitor.observe(original, now_seconds=3)
    record("duplicate_does_not_make_old_sample_recent", 3)

    changed = encode_telemetry(TelemetryFrame(202, 0, b"untrusted new session"))
    monitor.observe(changed, now_seconds=4)
    record("new_label_is_not_authenticated", 4)

    return {
        "mode": "SYNTHETIC_READ_ONLY",
        "radio_transmissions": 0,
        "command_dispatches": 0,
        "frames": frames,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    result = run_demo()
    by_label = {row["label"]: row["status"] for row in result["frames"]}
    expected = (
        by_label["before_data"]["freshness"] == "NO_DECODED_SAMPLE"
        and by_label["first_decoded_untrusted"]["freshness"] == "RECENT_UNAUTHENTICATED"
        and by_label["corrupt_does_not_make_old_sample_recent"]["freshness"] == "STALE_UNAUTHENTICATED"
        and by_label["duplicate_does_not_make_old_sample_recent"]["freshness"] == "STALE_UNAUTHENTICATED"
        and by_label["new_label_is_not_authenticated"]["session_change_seen_untrusted"] is True
        and by_label["new_label_is_not_authenticated"]["source_identity"] == "UNAUTHENTICATED"
        and all(not item["status"]["flight_control_authority"] for item in result["frames"])
    )
    print(json.dumps({"result": "PASS" if expected else "FAIL", **result},
                     indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
