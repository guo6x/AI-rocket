"""Deterministic offline comparison for the production GNC primitives.

This module intentionally keeps the reference implementation independent from
the production C++ sources.  ``run_cpp_trace`` compiles a tiny probe which
includes the production PID/Kalman translation units and feeds it the same
CSV trace used by :class:`GncOracle`.  No board, sensor, actuator, or plant is
accessed by this module.

The trace is deliberately a control-law trace, not a stability simulation:
``current`` is the measured attitude in degrees and ``angle``/``rate`` are the
accelerometer/gyro inputs to one Kalman update.  Physical mounting and plant
sign are therefore outside the result's evidence boundary.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import platform
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
PROBE_SOURCE = ROOT / "scripts" / "gnc_offline_cpp_probe.cpp"


def _f32(value: float) -> float:
    """Round one operation to the precision used by a C++ ``float``."""

    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _pid_profile(profile: str) -> Dict[str, float]:
    if profile == "flight":
        return {
            "kp": 1.0,
            "ki": 0.1,
            "kd": 0.3,
            "limit": 4.0,
            "rate": 0.3,
            "threshold": 10.0,
            "scale": 0.3,
        }
    if profile == "testbench":
        return {
            "kp": 1.65,
            "ki": 0.0,
            "kd": 0.45,
            "limit": 15.0,
            "rate": 1.0,
            "threshold": 1.0e6,
            "scale": 1.0,
        }
    raise ValueError(f"unknown PID profile: {profile}")


class GncOracle:
    """Independent float32 model of one production PID and one Kalman filter."""

    def __init__(self) -> None:
        self.pid_profile = "flight"
        self.pid = _pid_profile(self.pid_profile)
        self.pid_target = _f32(0.0)
        self.pid_integral = _f32(0.0)
        self.pid_last_error = _f32(0.0)
        self.pid_last_output = _f32(0.0)
        self.k_angle = _f32(0.0)
        self.k_bias = _f32(0.0)
        self.k_p00 = _f32(0.0)
        self.k_p01 = _f32(0.0)
        self.k_p10 = _f32(0.0)
        self.k_p11 = _f32(0.0)
        self.k_q_angle = _f32(0.001)
        self.k_q_bias = _f32(0.003)
        self.k_r_measure = _f32(0.03)

    def reset_pid(self) -> None:
        self.pid_integral = _f32(0.0)
        self.pid_last_error = _f32(0.0)
        self.pid_last_output = _f32(0.0)

    def set_pid_profile(self, profile: str) -> None:
        self.pid_profile = profile
        self.pid = _pid_profile(profile)
        # PIDController::setProfile applies the profile then resets state.
        self.reset_pid()

    def pid_step(self, current: float, dt: float) -> float:
        p = self.pid
        error = _f32(self.pid_target - _f32(current))
        self.pid_integral = _f32(self.pid_integral + _f32(error * _f32(dt)))
        self.pid_integral = _f32(max(-5.0, min(5.0, self.pid_integral)))
        derivative = _f32((error - self.pid_last_error) / _f32(dt))
        self.pid_last_error = error
        kp_eff = p["kp"] * p["scale"] if abs(error) > p["threshold"] else p["kp"]
        output = _f32(kp_eff * error + p["ki"] * self.pid_integral + p["kd"] * derivative)
        output = _f32(max(-p["limit"], min(p["limit"], output)))
        if output > self.pid_last_output + p["rate"]:
            output = _f32(self.pid_last_output + p["rate"])
        if output < self.pid_last_output - p["rate"]:
            output = _f32(self.pid_last_output - p["rate"])
        self.pid_last_output = output
        return output

    def reset_kalman(self) -> None:
        self.k_angle = _f32(0.0)
        self.k_bias = _f32(0.0)
        self.k_p00 = _f32(0.0)
        self.k_p01 = _f32(0.0)
        self.k_p10 = _f32(0.0)
        self.k_p11 = _f32(0.0)

    def kalman_step(self, new_angle: float, new_rate: float, dt: float) -> float:
        dt = _f32(dt)
        rate = _f32(new_rate - self.k_bias)
        self.k_angle = _f32(self.k_angle + _f32(dt * rate))
        self.k_p00 = _f32(
            self.k_p00
            + _f32(dt * (_f32(dt * self.k_p11) - self.k_p01 - self.k_p10 + self.k_q_angle))
        )
        self.k_p01 = _f32(self.k_p01 - _f32(dt * self.k_p11))
        self.k_p10 = _f32(self.k_p10 - _f32(dt * self.k_p11))
        self.k_p11 = _f32(self.k_p11 + _f32(self.k_q_bias * dt))
        innovation_cov = _f32(self.k_p00 + self.k_r_measure)
        gain_angle = _f32(self.k_p00 / innovation_cov)
        gain_bias = _f32(self.k_p10 / innovation_cov)
        innovation = _f32(new_angle - self.k_angle)
        self.k_angle = _f32(self.k_angle + _f32(gain_angle * innovation))
        self.k_bias = _f32(self.k_bias + _f32(gain_bias * innovation))
        p00_temp = self.k_p00
        p01_temp = self.k_p01
        self.k_p00 = _f32(self.k_p00 - _f32(gain_angle * p00_temp))
        self.k_p01 = _f32(self.k_p01 - _f32(gain_angle * p01_temp))
        self.k_p10 = _f32(self.k_p10 - _f32(gain_bias * p00_temp))
        self.k_p11 = _f32(self.k_p11 - _f32(gain_bias * p01_temp))
        return self.k_angle


def trace_rows() -> List[Dict[str, object]]:
    """Return fixed, named cases used by both the Python and C++ traces."""

    rows: List[Dict[str, object]] = []

    def pid_case(name: str, values: Sequence[Tuple[float, float]], profile: str = "flight") -> None:
        rows.append({"kind": "PID_PROFILE", "case": name, "profile": profile})
        rows.append({"kind": "PID_RESET", "case": name})
        for step, (current, dt) in enumerate(values):
            rows.append({
                "kind": "PID",
                "case": name,
                "step": step,
                "current": current,
                "dt": dt,
                "profile": profile,
            })

    # Two signs, zero, and a return-to-zero sequence expose error polarity and
    # integral/derivative history without asserting a physical corrective sign.
    pid_case("positive_perturbation", [(5.0, 0.05), (5.0, 0.05), (0.0, 0.05)])
    pid_case("negative_perturbation", [(-5.0, 0.05), (-5.0, 0.05), (0.0, 0.05)])
    pid_case("zero_and_step", [(0.0, 0.05), (0.0, 0.05), (2.0, 0.05), (2.0, 0.05), (0.0, 0.05)])
    pid_case("flight_limit_and_rate", [(45.0, 0.05), (-45.0, 0.05), (45.0, 0.05), (0.0, 0.05)])
    pid_case("irregular_dt", [(2.0, 0.01), (2.0, 0.073), (2.0, 0.2), (-2.0, 0.011)])
    pid_case("testbench_profile", [(12.0, 0.05), (-12.0, 0.05), (0.0, 0.05)], "testbench")

    rows.append({"kind": "KALMAN_RESET", "case": "kalman_static_zero"})
    for step in range(4):
        rows.append({"kind": "KALMAN", "case": "kalman_static_zero", "step": step, "angle": 0.0, "rate": 0.0, "dt": 0.01})
    rows.append({"kind": "KALMAN_RESET", "case": "kalman_positive_step"})
    for step, (angle, rate, dt) in enumerate([(10.0, 0.0, 0.01), (10.0, 5.0, 0.01), (10.0, 0.0, 0.05), (0.0, -5.0, 0.02)]):
        rows.append({"kind": "KALMAN", "case": "kalman_positive_step", "step": step, "angle": angle, "rate": rate, "dt": dt})
    rows.append({"kind": "KALMAN_RESET", "case": "kalman_negative_step"})
    for step, (angle, rate, dt) in enumerate([(-10.0, 0.0, 0.01), (-10.0, -5.0, 0.01), (-10.0, 0.0, 0.05), (0.0, 5.0, 0.02)]):
        rows.append({"kind": "KALMAN", "case": "kalman_negative_step", "step": step, "angle": angle, "rate": rate, "dt": dt})
    return rows


def oracle_trace(rows: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    oracle = GncOracle()
    output: List[Dict[str, object]] = []
    for row in rows:
        kind = row["kind"]
        if kind == "PID_PROFILE":
            oracle.set_pid_profile(str(row["profile"]))
        elif kind == "PID_RESET":
            oracle.reset_pid()
        elif kind == "PID":
            output.append({
                "kind": "PID",
                "case": row["case"],
                "step": int(row["step"]),
                "value": oracle.pid_step(float(row["current"]), float(row["dt"])),
            })
        elif kind == "KALMAN_RESET":
            oracle.reset_kalman()
        elif kind == "KALMAN":
            output.append({
                "kind": "KALMAN",
                "case": row["case"],
                "step": int(row["step"]),
                "value": oracle.kalman_step(float(row["angle"]), float(row["rate"]), float(row["dt"])),
            })
        else:
            raise ValueError(f"unknown trace row kind: {kind}")
    return output


def _compiler() -> Tuple[str, Dict[str, str]]:
    env = os.environ.copy()
    compiler = shutil.which("g++", path=env.get("PATH")) or shutil.which("c++", path=env.get("PATH"))
    if compiler:
        return compiler, env
    # PlatformIO's native package is not necessarily on PATH on Windows.
    core = Path(env.get("PLATFORMIO_CORE_DIR", ""))
    candidates = [core / "packages" / "toolchain-gccmingw32" / "bin"]
    for directory in candidates:
        for name in ("g++.exe", "g++", "c++.exe", "c++"):
            candidate = directory / name
            if candidate.exists():
                env["PATH"] = str(directory) + os.pathsep + env.get("PATH", "")
                return str(candidate), env
    raise RuntimeError("No C++ compiler found (set PATH or PLATFORMIO_CORE_DIR)")


def run_cpp_trace(rows: Sequence[Dict[str, object]], build_dir: Path | None = None) -> List[Dict[str, object]]:
    """Compile/run the production C++ probe and decode its deterministic trace."""

    compiler, env = _compiler()
    if build_dir is None:
        build_dir = Path(tempfile.mkdtemp(prefix="ai_rocket_gnc_trace_"))
    else:
        build_dir.mkdir(parents=True, exist_ok=True)
    exe = build_dir / ("gnc_trace.exe" if os.name == "nt" else "gnc_trace")
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
        raise RuntimeError(f"C++ probe compile failed:\n{compiled.stdout}\n{compiled.stderr}")
    payload = io_trace(rows)
    ran = subprocess.run([str(exe)], cwd=ROOT, env=env, input=payload, text=True, capture_output=True)
    if ran.returncode:
        raise RuntimeError(f"C++ probe failed:\n{ran.stdout}\n{ran.stderr}")
    decoded: List[Dict[str, object]] = []
    for line in ran.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) != 4:
            raise RuntimeError(f"invalid C++ trace row: {line!r}")
        decoded.append({"kind": parts[0], "case": parts[1], "step": int(parts[2]), "value": float(parts[3])})
    return decoded


def io_trace(rows: Iterable[Dict[str, object]]) -> str:
    """Encode trace rows as a small dependency-free CSV protocol."""

    lines: List[str] = []
    for row in rows:
        kind = row["kind"]
        if kind == "PID_PROFILE":
            lines.append(f"PID_PROFILE,{row['case']},{row['profile']}")
        elif kind == "PID_RESET":
            lines.append(f"PID_RESET,{row['case']}")
        elif kind == "PID":
            lines.append(f"PID,{row['case']},{row['step']},{row['current']:.9g},{row['dt']:.9g}")
        elif kind == "KALMAN_RESET":
            lines.append(f"KALMAN_RESET,{row['case']}")
        elif kind == "KALMAN":
            lines.append(f"KALMAN,{row['case']},{row['step']},{row['angle']:.9g},{row['rate']:.9g},{row['dt']:.9g}")
        else:
            raise ValueError(f"unknown trace row kind: {kind}")
    return "\n".join(lines) + "\n"


def compare_traces(reference: Sequence[Dict[str, object]], actual: Sequence[Dict[str, object]], tolerance: float = 2.0e-5) -> List[str]:
    failures: List[str] = []
    if len(reference) != len(actual):
        failures.append(f"row count mismatch: reference={len(reference)} actual={len(actual)}")
    for index, (expected, observed) in enumerate(zip(reference, actual)):
        for key in ("kind", "case", "step"):
            if expected[key] != observed[key]:
                failures.append(f"row {index} {key}: expected={expected[key]!r} actual={observed[key]!r}")
        if not math.isclose(float(expected["value"]), float(observed["value"]), rel_tol=tolerance, abs_tol=tolerance):
            failures.append(
                f"row {index} value: expected={expected['value']:.9g} actual={observed['value']:.9g}"
            )
    return failures


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_sha() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _compiler_version() -> str | None:
    try:
        compiler, env = _compiler()
    except RuntimeError:
        return None
    result = subprocess.run(
        [compiler, "--version"], cwd=ROOT, env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout.splitlines()[0].strip() if result.stdout else None


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
    candidates.append(str(sibling) if sibling.exists() else None)
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
        "flight_computer/src/main.cpp",
        "flight_computer/src/algorithms/pid.cpp",
        "flight_computer/src/algorithms/pid.h",
        "flight_computer/src/algorithms/kalman.cpp",
        "flight_computer/src/algorithms/kalman.h",
        "flight_computer/src/sensor_validity.cpp",
        "flight_computer/src/sensor_validity.h",
        "flight_computer/test/gnc_offline_cases.h",
        "flight_computer/test/test_kalman.cpp",
        "dynamics_sim/physics_engine_2d.py",
        "dynamics_sim/param_sweep.py",
        "dynamics_sim/test_polarity.py",
        "dynamics_sim/cg_impact_study.py",
        "scripts/gnc_offline_oracle.py",
        "scripts/gnc_offline_cpp_probe.cpp",
        "scripts/tests/test_gnc_offline_oracle.py",
        "scripts/check.py",
        "docs/R2_3_GNC_SOURCE_SIM_DELTA_REPORT.md",
        "engineering/verification-status.yaml",
    ]
    return {path: _sha256(ROOT / path) for path in paths}


def manifest(
    rows: Sequence[Dict[str, object]], reference: Sequence[Dict[str, object]], command: str
) -> Dict[str, object]:
    """Build a reproducible, source-bound output object for evidence."""

    trace_bytes = io_trace(rows).encode("utf-8")
    source_hashes = _source_hashes()
    compiler = _compiler_version()

    return {
        "schema_version": 1,
        "contract": "AA-GNC-OFFLINE-CONTRACT-001",
        "source_git_sha": _git_sha(),
        "source": sorted(source_hashes),
        "source_sha256": source_hashes,
        "input_trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
        "command": command,
        "tool_versions": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "compiler": compiler,
            "platformio": _platformio_version(),
        },
        "dependencies": {
            "pytest": _package_version("pytest"),
            "pyyaml": _package_version("PyYAML"),
        },
        "input_rows": len(rows),
        "output_rows": len(reference),
        "seed": "not_applicable_fixed_trace",
        "physical_hardware": False,
        "plant_or_mounting_claim": False,
        "recovery_output_touched": False,
        "results": reference,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=Path, help="write deterministic comparison output")
    parser.add_argument("--skip-cpp", action="store_true", help="only emit the Python oracle")
    args = parser.parse_args()

    rows = trace_rows()
    reference = oracle_trace(rows)
    actual = [] if args.skip_cpp else run_cpp_trace(rows)
    failures = [] if args.skip_cpp else compare_traces(reference, actual)
    command = " ".join(["python", "scripts/gnc_offline_oracle.py", *sys.argv[1:]])
    result = manifest(rows, reference, command)
    result["cpp_rows"] = actual
    result["comparison"] = "SKIPPED" if args.skip_cpp else ("PASS" if not failures else "FAIL")
    result["failures"] = failures
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"comparison": result["comparison"], "input_rows": len(rows), "output_rows": len(reference), "failures": failures}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
