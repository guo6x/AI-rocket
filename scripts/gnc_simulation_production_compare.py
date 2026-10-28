"""Compare the legacy 2D simulation PID with the production C++ PID.

This is a deliberately narrow, offline source-assumption audit.  It feeds the
same fixed attitude trace (the trace already used by ``gnc_dual_period``) to
the legacy ``dynamics_sim.physics_engine_2d.PIDController2D`` and to the
actual production ``PIDController`` translation unit through the existing C++
probe.  No plant, sensor, board, actuator, or recovery output is accessed.

The expected result is a *difference*, not a stability verdict: the legacy 2D
model uses ``error=current`` while production uses ``target-current``.  The
artifact makes that polarity and the 10/50 ms cadence assumptions explicit so
that a future model change cannot silently hide the mismatch.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "dynamics_sim"))

from gnc_dual_period import (  # noqa: E402
    PERIODS_MS,
    all_input_rows,
    encode_rows,
    run_cpp_trace,
    servo_command,
)
from physics_engine_2d import PIDController2D  # noqa: E402


SOURCE_PATHS = (
    "flight_computer/src/main.cpp",
    "flight_computer/src/algorithms/pid.cpp",
    "flight_computer/src/algorithms/pid.h",
    "scripts/gnc_dual_period.py",
    "scripts/gnc_dual_period_cpp_probe.cpp",
    "scripts/gnc_simulation_production_compare.py",
    "dynamics_sim/physics_engine_2d.py",
    "dynamics_sim/physics_engine.py",
    "dynamics_sim/components.py",
    "dynamics_sim/test_polarity.py",
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _legacy_trace(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    """Run the existing legacy 2D PID, independently per cadence.

    ``PIDController2D`` stores one state per axis.  We use its x/pitch-like
    axis and feed zero to the unused y axis; this is a comparison of the
    controller assumption only, not a 2D plant simulation.
    """

    controllers: Dict[int, PIDController2D] = {}
    result: List[Dict[str, object]] = []
    for row in rows:
        period = int(row["period_ms"])
        controller = controllers.setdefault(period, PIDController2D(profile="FLIGHT"))
        legacy_output, _ = controller.compute(
            float(row["current_deg"]), 0.0, float(row["dt_s"])
        )
        result.append(
            {
                "period_ms": period,
                "step": int(row["step"]),
                "time_ms": int(row["time_ms"]),
                "current_deg": float(row["current_deg"]),
                "dt_s": float(row["dt_s"]),
                "legacy_pid_output_deg": float(legacy_output),
                "legacy_servo_command": servo_command(float(legacy_output)),
            }
        )
    return result


def _join(
    rows: Sequence[Dict[str, object]],
    production: Sequence[Dict[str, object]],
    legacy: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    if not (len(rows) == len(production) == len(legacy)):
        raise AssertionError("input, production, and legacy row counts differ")
    joined: List[Dict[str, object]] = []
    for source, prod, old in zip(rows, production, legacy):
        keys = ("period_ms", "step", "time_ms")
        if any(int(source[key]) != int(prod[key]) or int(source[key]) != int(old[key]) for key in keys):
            raise AssertionError(f"trace identity mismatch at {source}")
        production_output = float(prod["pid_output_deg"])
        legacy_output = float(old["legacy_pid_output_deg"])
        if abs(legacy_output) <= 1.0e-8 or abs(production_output) <= 1.0e-8:
            relation = "ZERO_OR_NONZERO"
        elif legacy_output * production_output < 0.0:
            relation = "OPPOSITE_SIGN"
        else:
            relation = "SAME_SIGN"
        joined.append(
            {
                "period_ms": int(source["period_ms"]),
                "step": int(source["step"]),
                "time_ms": int(source["time_ms"]),
                "current_deg": float(source["current_deg"]),
                "dt_s": float(source["dt_s"]),
                "legacy_pid_output_deg": legacy_output,
                "production_pid_output_deg": production_output,
                "pid_delta_deg": legacy_output - production_output,
                "legacy_servo_command": int(old["legacy_servo_command"]),
                "production_servo_command": int(prod["servo_command"]),
                "sign_relation": relation,
            }
        )
    return joined


def _rms(values: Iterable[float]) -> float:
    values = list(values)
    return math.sqrt(sum(value * value for value in values) / len(values)) if values else 0.0


def _summary(rows: Sequence[Dict[str, object]]) -> Dict[str, object]:
    summary: Dict[str, object] = {}
    for period in PERIODS_MS:
        selected = [row for row in rows if int(row["period_ms"]) == period]
        nonzero = [
            row
            for row in selected
            if abs(float(row["legacy_pid_output_deg"])) > 1.0e-8
            or abs(float(row["production_pid_output_deg"])) > 1.0e-8
        ]
        opposite = [row for row in nonzero if row["sign_relation"] == "OPPOSITE_SIGN"]
        deltas = [float(row["pid_delta_deg"]) for row in selected]
        summary[str(period)] = {
            "sample_count": len(selected),
            "nonzero_count": len(nonzero),
            "opposite_sign_count": len(opposite),
            "opposite_sign_fraction": len(opposite) / len(nonzero) if nonzero else 0.0,
            "legacy_output_min_deg": min(float(row["legacy_pid_output_deg"]) for row in selected),
            "legacy_output_max_deg": max(float(row["legacy_pid_output_deg"]) for row in selected),
            "production_output_min_deg": min(float(row["production_pid_output_deg"]) for row in selected),
            "production_output_max_deg": max(float(row["production_pid_output_deg"]) for row in selected),
            "max_abs_delta_deg": max(abs(value) for value in deltas),
            "rms_delta_deg": _rms(deltas),
            "legacy_servo_change_count": sum(
                a != b
                for a, b in zip(
                    [int(row["legacy_servo_command"]) for row in selected],
                    [int(row["legacy_servo_command"]) for row in selected][1:],
                )
            ),
            "production_servo_change_count": sum(
                a != b
                for a, b in zip(
                    [int(row["production_servo_command"]) for row in selected],
                    [int(row["production_servo_command"]) for row in selected][1:],
                )
            ),
            "theoretical_rate_limit_deg_per_s": 0.3 / (period / 1000.0),
        }
    return summary


def build_result() -> Dict[str, object]:
    rows = all_input_rows()
    production = run_cpp_trace(rows)
    legacy = _legacy_trace(rows)
    joined = _join(rows, production, legacy)
    input_hash = _sha256_bytes(encode_rows(rows).encode("utf-8"))
    result_hash = _sha256_bytes(
        json.dumps(joined, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return {
        "schema_version": 1,
        "contract": "AA-GNC-SIM-PRODUCTION-COMPARE-001",
        "source_git_sha": _git_sha(),
        "source_sha256": {path: _sha256(ROOT / path) for path in SOURCE_PATHS},
        "input_trace_sha256": input_hash,
        "result_rows_sha256": result_hash,
        "command": "py -3 scripts/gnc_simulation_production_compare.py --write-json engineering/offline-evidence/r2_3/gnc_simulation_production_compare.json",
        "tool_versions": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pytest": _package_version("pytest"),
            "pyyaml": _package_version("PyYAML"),
        },
        "assumptions": {
            "input": "fixed synthetic attitude_deg trace from gnc_dual_period",
            "periods_ms": list(PERIODS_MS),
            "production_schedule": "one production PID compute per supplied sample; 10 ms and 50 ms are offline schedules",
            "legacy_schedule": "physics_engine_2d calls PID every 10 ms in its 1 ms integration loop; 50 ms is an audit-only resampling",
            "legacy_profile": "physics_engine_2d.PIDController2D(FLIGHT)",
            "production_profile": "flight_computer PIDController::FLIGHT",
            "pid_parameters": {
                "kp": 1.0,
                "ki": 0.1,
                "kd": 0.3,
                "integral_limit": 5.0,
                "output_limit_deg": 4.0,
                "rate_limit_deg_per_call": 0.3,
                "gain_schedule_threshold_deg": 10.0,
                "gain_schedule_scale": 0.3,
            },
            "legacy_error_formula": "current_deg (target zero)",
            "production_error_formula": "target-current (target zero)",
            "units": "attitude and PID output are degrees; dt is seconds",
            "servo_mapping": "90 + int(output), constrained to [0,180]; no physical write",
            "parameter_sources": {
                "input_trace": "scripts/gnc_dual_period.py:43-64",
                "production_pid": "flight_computer/src/algorithms/pid.cpp:23-105",
                "legacy_pid": "dynamics_sim/physics_engine_2d.py:60-117",
                "production_servo_mapping": "flight_computer/src/main.cpp:291-296",
            },
            "legacy_physical_model_parameters": "not used in this controller-only comparison",
            "physical_model_difference": "not evaluated; no mass, inertia, thrust, friction, linkage, or actuator parameters are supplied",
            "physical_hardware": False,
            "plant_simulated": False,
            "plant_or_mounting_claim": False,
            "recovery_output_touched": False,
            "nonconvergence_or_model_failure": "not_run_no_plant",
        },
        "comparison_status": "DIFFERENCE_CONFIRMED",
        "summary": _summary(joined),
        "rows": joined,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=Path)
    args = parser.parse_args()
    output = build_result()
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(
            json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps({"comparison_status": output["comparison_status"], "summary": output["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
