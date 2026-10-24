"""Read-only recovery detectability audit for the existing production firmware.

This is not a flight-readiness test. It checks only whether the launch detection
threshold is mathematically reachable with the *currently configured* IMU
full-scale register and the current raw-count-to-g conversion.

Exit status 0 means the audit itself ran (including if the design is BLOCKED).
Use --strict to exit 1 on a detected contradiction. Unknown source format fails
closed with exit 2. No hardware is contacted, and no thresholds are changed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
RANGES = {0x00: (2, 16384), 0x08: (4, 8192), 0x10: (8, 4096), 0x18: (16, 2048)}
REGISTER_PATTERN = re.compile(
    r"configure\s*\(\s*bus\s*,\s*imu_address_\s*,\s*0x1[cC]\s*,\s*(0x[0-9a-fA-F]+|\d+)\s*\)"
)
CONVERSION_PATTERN = re.compile(
    r"sample\.az\s*=\s*raw_az\s*/\s*([0-9]+(?:\.[0-9]+)?)f?\s*;"
)
THRESHOLD_PATTERN = re.compile(
    r"FlightStateMachine::LAUNCH_ACCEL_THRESHOLD\s*=\s*([0-9]+(?:\.[0-9]+)?)f?\s*;"
)
LAUNCH_COMPARE_PATTERN = re.compile(
    r"(?:std::)?fabs\s*\(\s*az\s*\)\s*>\s*LAUNCH_ACCEL_THRESHOLD"
)


class CannotAudit(ValueError):
    pass


def unique(pattern: re.Pattern[str], source: str, description: str) -> str:
    hits = pattern.findall(source)
    if len(hits) != 1:
        raise CannotAudit(f"{description}: expected one exact production match; found {len(hits)}")
    return hits[0]


def audit(sensor_source: str, fsm_source: str) -> dict[str, object]:
    register_value = int(unique(REGISTER_PATTERN, sensor_source, "IMU ACCEL_CONFIG"), 0)
    if register_value not in RANGES:
        raise CannotAudit(f"unsupported ACCEL_CONFIG value 0x{register_value:02x}")
    scale_g, expected_counts_per_g = RANGES[register_value]
    divisor = float(unique(CONVERSION_PATTERN, sensor_source, "az conversion"))
    threshold = float(unique(THRESHOLD_PATTERN, fsm_source, "launch threshold"))
    unique(LAUNCH_COMPARE_PATTERN, fsm_source, "launch comparator")
    if not (divisor > 0 and threshold >= 0):
        raise CannotAudit("nonpositive conversion divisor or negative launch threshold")

    # int16 can reach -32768 counts; the condition is a strict '>' comparison.
    max_abs_output_g = 32768.0 / divisor
    scaling_consistent = divisor == float(expected_counts_per_g)
    reachable_by_numeric_representation = threshold < max_abs_output_g

    if not scaling_consistent:
        status = "BLOCKED_SCALE_MISMATCH"
    elif not reachable_by_numeric_representation:
        status = "BLOCKED_UNREACHABLE_THRESHOLD"
    else:
        status = "NUMERICALLY_REACHABLE_NOT_QUALIFIED"

    return {
        "audit": "recovery_launch_detection_static_feasibility",
        "scope": "single-axis az; configuration and numeric representability only",
        "imu_accel_config_hex": f"0x{register_value:02x}",
        "configured_full_scale_g": scale_g,
        "configured_expected_counts_per_g": expected_counts_per_g,
        "production_az_counts_per_g": divisor,
        "strict_launch_threshold_g": threshold,
        "max_abs_numeric_az_g": round(max_abs_output_g, 6),
        "scale_matches_configuration": scaling_consistent,
        "threshold_numerically_reachable": reachable_by_numeric_representation,
        "status": status,
        "recovery_qualified": False,
        "caveat": "A numerically reachable threshold is only necessary, not sufficient: axis mounting, dynamics, sample timing, filtering, calibration and physical tests remain unproven.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="return nonzero if current configuration is blocked")
    args = parser.parse_args(argv)
    try:
        sensor = (args.root / "flight_computer/src/sensor_validity.cpp").read_text(encoding="utf-8")
        fsm = (args.root / "flight_computer/src/flight_fsm.cpp").read_text(encoding="utf-8")
        result = audit(sensor, fsm)
    except (OSError, CannotAudit) as exc:
        result = {"audit": "recovery_launch_detection_static_feasibility",
                  "status": "UNKNOWN_SOURCE_OR_CONFIG", "error": str(exc),
                  "recovery_qualified": False}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Recovery detectability: {result['status']}")
        print(f"  IMU: +/-{result['configured_full_scale_g']} g; az divisor: {result['production_az_counts_per_g']} counts/g")
        print(f"  strict launch threshold: {result['strict_launch_threshold_g']} g; max encoded |az|: {result['max_abs_numeric_az_g']} g")
        print("  Recovery qualification: NOT EVALUATED; do not infer readiness.")
    if args.strict and str(result["status"]).startswith("BLOCKED_"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
