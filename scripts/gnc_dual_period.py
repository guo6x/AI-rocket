"""Deterministic dual-period comparison for the production GNC PID.

The comparison is deliberately a software-only control-law experiment.  A
fixed, piecewise-linear attitude trace is sampled at 10 ms and 50 ms.  Each
period owns an independent production ``PIDController`` state.  The C++ side
of the comparison includes ``flight_computer/src/algorithms/pid.cpp``; the
Python side is an independent float32 reference implementation.

The 50 ms period is an offline comparison assumption.  It is not a measured
flight-computer period and this artifact makes no stability, plant, mounting,
or hardware claim.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import platform
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
PROBE_SOURCE = ROOT / "scripts" / "gnc_dual_period_cpp_probe.cpp"
DURATION_MS = 2000
PERIODS_MS = (10, 50)
OUTPUT_LIMIT_DEG = 4.0
RATE_LIMIT_DEG_PER_CALL = 0.3


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def attitude_deg(time_ms: int) -> float:
    """Fixed synthetic attitude trace shared by both control periods.

    Segment boundaries intentionally do not all coincide with 50 ms sample
    boundaries.  This exposes the timing effect without introducing a plant
    or any physical parameter.  The abrupt transition at 720 ms is the step;
    the other transitions are ramps or holds.
    """

    t = int(time_ms)
    if t < 200:
        return 0.0
    if t < 350:
        return 6.0 * (t - 200) / 150.0
    if t < 720:
        return 6.0
    if t < 1190:
        return -6.0
    if t < 1440:
        return -6.0 * (1.0 - (t - 1190) / 250.0)
    return 0.0


def sample_rows(period_ms: int) -> List[Dict[str, object]]:
    """Sample the same fixed physical-time function at one control period."""

    if period_ms <= 0 or DURATION_MS % period_ms:
        raise ValueError("period must be a positive divisor of DURATION_MS")
    rows: List[Dict[str, object]] = []
    # The first control call occurs after one period, matching an elapsed dt
    # rather than inventing an initial zero-duration call.
    for step, time_ms in enumerate(range(period_ms, DURATION_MS + 1, period_ms)):
        rows.append(
            {
                "period_ms": period_ms,
                "step": step,
                "time_ms": time_ms,
                "current_deg": attitude_deg(time_ms),
                "dt_s": period_ms / 1000.0,
            }
        )
    return rows


class PidReference:
    """Independent float32 reference of production PIDController::compute."""

    def __init__(self) -> None:
        # Production default is PIDController::FLIGHT.
        self.kp = _f32(1.0)
        self.ki = _f32(0.1)
        self.kd = _f32(0.3)
        self.output_limit = _f32(4.0)
        self.rate_limit = _f32(0.3)
        self.gs_threshold = _f32(10.0)
        self.gs_scale = _f32(0.3)
        self.target = _f32(0.0)
        self.integral = _f32(0.0)
        self.last_error = _f32(0.0)
        self.last_output = _f32(0.0)

    def step(self, current: float, dt: float) -> float:
        error = _f32(self.target - _f32(current))
        self.integral = _f32(self.integral + _f32(error * _f32(dt)))
        self.integral = _f32(max(-5.0, min(5.0, self.integral)))
        derivative = _f32((error - self.last_error) / _f32(dt))
        self.last_error = error
        kp_eff = self.kp
        if abs(error) > self.gs_threshold:
            kp_eff = _f32(self.kp * self.gs_scale)
        output = _f32(
            kp_eff * error + self.ki * self.integral + self.kd * derivative
        )
        output = _f32(max(-self.output_limit, min(self.output_limit, output)))
        if output > self.last_output + self.rate_limit:
            output = _f32(self.last_output + self.rate_limit)
        if output < self.last_output - self.rate_limit:
            output = _f32(self.last_output - self.rate_limit)
        self.last_output = output
        return output


def servo_command(pid_output: float) -> int:
    """Match main.cpp: ``constrain(90 + (int)PID, 0, 180)``."""

    # int(float) in C++ truncates toward zero for these finite values.
    return max(0, min(180, 90 + int(pid_output)))


def python_trace(rows: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    controllers: Dict[int, PidReference] = {}
    output: List[Dict[str, object]] = []
    for row in rows:
        period = int(row["period_ms"])
        controller = controllers.setdefault(period, PidReference())
        pid_output = controller.step(float(row["current_deg"]), float(row["dt_s"]))
        servo = servo_command(pid_output)
        unquantized = 90.0 + pid_output
        output.append(
            {
                "period_ms": period,
                "step": int(row["step"]),
                "time_ms": int(row["time_ms"]),
                "current_deg": float(row["current_deg"]),
                "dt_s": float(row["dt_s"]),
                "pid_output_deg": pid_output,
                "servo_command": servo,
                "quantization_error_deg": float(servo) - unquantized,
            }
        )
    return output


def all_input_rows() -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for period in PERIODS_MS:
        rows.extend(sample_rows(period))
    return rows


def _compiler() -> Tuple[str, Dict[str, str]]:
    env = os.environ.copy()
    compiler = shutil.which("g++", path=env.get("PATH")) or shutil.which(
        "c++", path=env.get("PATH")
    )
    if compiler:
        return compiler, env
    core = Path(env.get("PLATFORMIO_CORE_DIR", ""))
    candidates = [core / "packages" / "toolchain-gccmingw32" / "bin"]
    for directory in candidates:
        for name in ("g++.exe", "g++", "c++.exe", "c++"):
            candidate = directory / name
            if candidate.exists():
                env["PATH"] = str(directory) + os.pathsep + env.get("PATH", "")
                return str(candidate), env
    raise RuntimeError("No C++ compiler found (set PATH or PLATFORMIO_CORE_DIR)")


def encode_rows(rows: Iterable[Dict[str, object]]) -> str:
    lines: List[str] = []
    active_period = None
    for row in rows:
        period = int(row["period_ms"])
        if active_period != period:
            lines.append(f"RESET,{period}")
            active_period = period
        lines.append(
            "PID,{period},{step},{time},{current:.9g},{dt:.9g}".format(
                period=period,
                step=int(row["step"]),
                time=int(row["time_ms"]),
                current=float(row["current_deg"]),
                dt=float(row["dt_s"]),
            )
        )
    return "\n".join(lines) + "\n"


def run_cpp_trace(rows: Sequence[Dict[str, object]], build_dir: Path | None = None) -> List[Dict[str, object]]:
    compiler, env = _compiler()
    if build_dir is None:
        build_dir = Path(tempfile.mkdtemp(prefix="ai_rocket_gnc_dual_period_"))
    else:
        build_dir.mkdir(parents=True, exist_ok=True)
    exe = build_dir / ("gnc_dual_period.exe" if os.name == "nt" else "gnc_dual_period")
    command = [
        compiler,
        "-std=c++11",
        "-O0",
        "-I",
        str(ROOT / "flight_computer" / "test" / "fakes"),
        "-I",
        str(ROOT / "flight_computer" / "src"),
        str(PROBE_SOURCE),
        "-o",
        str(exe),
    ]
    compiled = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    if compiled.returncode:
        raise RuntimeError(f"dual-period C++ probe compile failed:\n{compiled.stdout}\n{compiled.stderr}")
    ran = subprocess.run(
        [str(exe)], cwd=ROOT, env=env, input=encode_rows(rows), text=True, capture_output=True
    )
    if ran.returncode:
        raise RuntimeError(f"dual-period C++ probe failed:\n{ran.stdout}\n{ran.stderr}")
    decoded: List[Dict[str, object]] = []
    for line in ran.stdout.splitlines():
        if not line.strip():
            continue
        fields = line.split(",")
        if len(fields) != 8 or fields[0] != "PID":
            raise RuntimeError(f"invalid dual-period C++ row: {line!r}")
        decoded.append(
            {
                "period_ms": int(fields[1]),
                "step": int(fields[2]),
                "time_ms": int(fields[3]),
                "current_deg": float(fields[4]),
                "dt_s": float(fields[5]),
                "pid_output_deg": float(fields[6]),
                "servo_command": int(fields[7]),
            }
        )
    return decoded


def compare_traces(expected: Sequence[Dict[str, object]], actual: Sequence[Dict[str, object]], tolerance: float = 2.0e-5) -> List[str]:
    failures: List[str] = []
    if len(expected) != len(actual):
        failures.append(f"row count mismatch: expected={len(expected)} actual={len(actual)}")
    for index, (want, got) in enumerate(zip(expected, actual)):
        for key in ("period_ms", "step", "time_ms", "servo_command"):
            if want[key] != got[key]:
                failures.append(f"row {index} {key}: expected={want[key]!r} actual={got[key]!r}")
        for key in ("current_deg", "dt_s"):
            if not math.isclose(
                float(want[key]), float(got[key]), rel_tol=0.0, abs_tol=tolerance
            ):
                failures.append(
                    f"row {index} {key}: expected={want[key]:.9g} actual={got[key]:.9g}"
                )
        if not math.isclose(
            float(want["pid_output_deg"]), float(got["pid_output_deg"]), rel_tol=tolerance, abs_tol=tolerance
        ):
            failures.append(
                f"row {index} pid output: expected={want['pid_output_deg']:.9g} actual={got['pid_output_deg']:.9g}"
            )
    return failures


def _common_rows(rows: Sequence[Dict[str, object]]) -> Dict[int, Dict[int, Dict[str, object]]]:
    by_period: Dict[int, Dict[int, Dict[str, object]]] = {period: {} for period in PERIODS_MS}
    for row in rows:
        by_period[int(row["period_ms"])][int(row["time_ms"])] = row
    return by_period


def metrics(trace: Sequence[Dict[str, object]]) -> Dict[str, object]:
    by_period = _common_rows(trace)
    p10 = by_period[10]
    p50 = by_period[50]
    common_times = sorted(set(p10) & set(p50))
    pid_diff = [float(p10[t]["pid_output_deg"]) - float(p50[t]["pid_output_deg"]) for t in common_times]
    cmd_diff = [int(p10[t]["servo_command"]) - int(p50[t]["servo_command"]) for t in common_times]
    def rms(values: Sequence[float]) -> float:
        return math.sqrt(sum(value * value for value in values) / len(values)) if values else 0.0

    per_period: Dict[str, object] = {}
    for period, period_rows in by_period.items():
        outputs = [float(row["pid_output_deg"]) for row in period_rows.values()]
        commands = [int(row["servo_command"]) for row in period_rows.values()]
        quant = [float(row["quantization_error_deg"]) for row in trace if int(row["period_ms"]) == period]
        per_period[str(period)] = {
            "sample_count": len(period_rows),
            "effective_rate_limit_deg_per_s": RATE_LIMIT_DEG_PER_CALL / (period / 1000.0),
            "pid_min_deg": min(outputs),
            "pid_max_deg": max(outputs),
            "servo_change_count": sum(a != b for a, b in zip(commands, commands[1:])),
            "quantization_error_max_abs_deg": max(abs(value) for value in quant),
            "quantization_error_rms_deg": rms(quant),
        }
    return {
        "common_time_count": len(common_times),
        "common_time_start_ms": common_times[0] if common_times else None,
        "common_time_end_ms": common_times[-1] if common_times else None,
        "common_time_pid_max_abs_diff_deg": max((abs(value) for value in pid_diff), default=0.0),
        "common_time_pid_rms_diff_deg": rms(pid_diff),
        "common_time_servo_max_abs_diff_count": max((abs(value) for value in cmd_diff), default=0),
        "common_time_servo_rms_diff_count": rms([float(value) for value in cmd_diff]),
        "per_period": per_period,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_sha() -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def _compiler_version() -> str | None:
    try:
        compiler, env = _compiler()
    except RuntimeError:
        return None
    result = subprocess.run([compiler, "--version"], cwd=ROOT, env=env, capture_output=True, text=True)
    return result.stdout.splitlines()[0].strip() if result.returncode == 0 and result.stdout else None


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _platformio_version() -> str | None:
    candidates = [shutil.which("platformio"), shutil.which("pio")]
    sibling = Path(sys.executable).with_name(
        "platformio.exe" if os.name == "nt" else "platformio"
    )
    if sibling.exists():
        candidates.append(str(sibling))
    for candidate in candidates:
        if not candidate:
            continue
        result = subprocess.run(
            [candidate, "--version"], cwd=ROOT, capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.splitlines()[0].strip()
    return None


def _source_hashes() -> Dict[str, str]:
    paths = [
        "engineering/gnc-offline-contract.yaml",
        "docs/R2_3_OFFLINE_GNC_SOURCE_AUDIT.md",
        "docs/R2_2_GNC_ONLY_BENCH_ISOLATION.md",
        "docs/R2_3_DUAL_PERIOD_CADENCE_SUPPLEMENT.md",
        "flight_computer/src/algorithms/pid.cpp",
        "flight_computer/src/algorithms/pid.h",
        "flight_computer/src/main.cpp",
        "flight_computer/test/fakes/Arduino.h",
        "scripts/gnc_dual_period.py",
        "scripts/gnc_dual_period_cpp_probe.cpp",
        "scripts/tests/test_gnc_dual_period.py",
        "scripts/check.py",
    ]
    return {path: _sha256(ROOT / path) for path in paths}


def manifest(rows: Sequence[Dict[str, object]], trace: Sequence[Dict[str, object]], command: str) -> Dict[str, object]:
    input_bytes = encode_rows(rows).encode("utf-8")
    return {
        "schema_version": 1,
        "contract": "AA-GNC-OFFLINE-DUAL-PERIOD-001",
        "source_git_sha": _git_sha(),
        "source_sha256": _source_hashes(),
        "input_trace_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "command": command,
        "tool_versions": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "compiler": _compiler_version(),
            "platformio": _platformio_version(),
        },
        "dependencies": {
            "pytest": _package_version("pytest"),
            "pyyaml": _package_version("PyYAML"),
        },
        "periods_ms": list(PERIODS_MS),
        "duration_ms": DURATION_MS,
        "sequence": "fixed_piecewise_attitude_v1",
        "input_rows": len(rows),
        "output_rows": len(trace),
        "seed": "not_applicable_fixed_trace",
        "physical_hardware": False,
        "period_50ms_is_measured": False,
        "plant_or_mounting_claim": False,
        "recovery_output_touched": False,
        "comparison": "PASS",
        "failures": [],
        "metrics": metrics(trace),
        "results": trace,
    }


def run(write_json: Path | None = None) -> Dict[str, object]:
    rows = all_input_rows()
    expected = python_trace(rows)
    actual = run_cpp_trace(rows)
    failures = compare_traces(expected, actual)
    if failures:
        raise AssertionError("\n".join(failures))
    # Add quantization fields to C++ rows only after parity comparison, so the
    # production command value remains the directly observed C++ result.
    for row in actual:
        output = float(row["pid_output_deg"])
        row["quantization_error_deg"] = float(row["servo_command"]) - (90.0 + output)
    result = manifest(rows, actual, "py -3 scripts/gnc_dual_period.py --write-json engineering/offline-evidence/r2_3/gnc_dual_period_trace.json")
    if write_json:
        write_json.parent.mkdir(parents=True, exist_ok=True)
        write_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=Path)
    args = parser.parse_args()
    result = run(args.write_json)
    summary = {
        "comparison": "PASS",
        "input_rows": result["input_rows"],
        "output_rows": result["output_rows"],
        "metrics": result["metrics"],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
