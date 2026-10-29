"""KB4: independent numerical convergence of the pinned historical zero-thrust ODE.

Offline study only. No hardware, thrust, control commands or flight qualification.
Requires scipy, numpy. Run on the *unaltered* pinned source model.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import platform
from pathlib import Path

import numpy
import scipy
from scipy.integrate import solve_ivp

from run_reference_experiment import MODEL_GIT_BLOB_SHA, MODEL_SOURCE_COMMIT, _model_class, git_blob_sha
from simulation_manifest import sha256_file, validate_manifest

CASE = {
    "initial_angle_deg": 0.5,
    "mass_kg": 1.0,
    "length_cg_m": 0.2,
    "length_thrust_m": 0.5,
    "nominal_max_thrust_N": 15.0,
    "actual_thrust_N": 0.0,
    "gravity_m_s2": 9.81,
    "damping_N_m_s_per_rad": 0.5,
    "duration_s": 1.2,
    "step_sizes_s": [0.08, 0.04, 0.02, 0.01],
    "reference_rtol": 1e-12,
    "reference_atol": 1e-14,
    "max_solver_disagreement_rad": 1e-10,
    "minimum_error_improvement_per_halving": 10.0,
    "maximum_finest_error_rad": 1e-7,
}


def independent_rhs(t: float, state: list[float], case: dict) -> list[float]:
    """Derived from the conceptual zero-thrust ODE, not from model._derivatives()."""
    theta, omega = state
    mass = case["mass_kg"]
    length = case["length_cg_m"]
    inertia = mass * (2.0 * length)**2 / 3.0
    return [omega, (mass * case["gravity_m_s2"] * length * math.sin(theta)
                    - case["damping_N_m_s_per_rad"] * omega) / inertia]


def integrate_original(Model, step_size: float, case: dict) -> tuple[float, float]:
    duration = case["duration_s"]
    count = round(duration / step_size)
    if not math.isclose(count * step_size, duration, rel_tol=0.0, abs_tol=1e-13):
        raise ValueError("Each step size must exactly partition the observation window")
    model = Model(mass=case["mass_kg"], length_cg=case["length_cg_m"],
                  length_thrust=case["length_thrust_m"], max_thrust=case["nominal_max_thrust_N"])
    model.reset(initial_pitch_deg=case["initial_angle_deg"])
    for _ in range(count):
        model.step(dt=step_size, servo_angle_deg=0.0, thrust=0.0)
    return model.state[0], model.state[1]


def reference_solvers(case: dict) -> dict[str, tuple[float, float]]:
    y0 = [math.radians(case["initial_angle_deg"]), 0.0]
    solution: dict[str, tuple[float, float]] = {}
    for method in ("DOP853", "Radau"):
        result = solve_ivp(lambda t, y: independent_rhs(t, y, case),
                           (0.0, case["duration_s"]), y0, method=method,
                           rtol=case["reference_rtol"], atol=case["reference_atol"],
                           t_eval=[case["duration_s"]])
        if not result.success:
            raise RuntimeError(f"{method}: {result.message}")
        values = tuple(float(x) for x in result.y[:, -1])
        if not all(math.isfinite(x) for x in values):
            raise RuntimeError(f"{method}: nonfinite result")
        solution[method] = values
    return solution


def evaluate(repo_root: Path, case: dict | None = None) -> tuple[dict, bytes, bytes]:
    case = dict(CASE if case is None else case)
    source_file = repo_root / "dynamics_sim" / "physics_engine.py"
    source = source_file.read_bytes()
    actual_blob = git_blob_sha(source)
    if actual_blob != MODEL_GIT_BLOB_SHA:
        raise RuntimeError(f"MODEL_SOURCE_MISMATCH expected={MODEL_GIT_BLOB_SHA} actual={actual_blob}")
    if case["actual_thrust_N"] != 0.0:
        raise ValueError("Reference is strictly unpowered: actual thrust must equal 0")
    Model = _model_class(source_file)
    references = reference_solvers(case)
    independent_difference = max(abs(x-y) for x, y in zip(references["DOP853"], references["Radau"]))
    table = []
    for step in case["step_sizes_s"]:
        theta, omega = integrate_original(Model, step, case)
        err = abs(theta-references["DOP853"][0])
        table.append({"dt_s": step, "angle_rad": theta, "angular_rate_rad_s": omega,
                      "angle_error_to_DOP853_rad": err})
    ratios = [a["angle_error_to_DOP853_rad"] / b["angle_error_to_DOP853_rad"]
              for a, b in zip(table, table[1:])]
    passed = (independent_difference <= case["max_solver_disagreement_rad"]
              and all(r >= case["minimum_error_improvement_per_halving"] for r in ratios)
              and table[-1]["angle_error_to_DOP853_rad"] <= case["maximum_finest_error_rad"])
    summary = {
        "status": "PASS_NUMERICAL_CONVERGENCE_ONLY" if passed else "FAIL_NUMERICAL_CONVERGENCE",
        "research_case": "KB4 nonlinear zero-thrust numerical convergence",
        "source_git_blob_sha1": actual_blob,
        "actual_thrust_N": 0.0,
        "reference_results": {key: {"angle_rad": value[0], "angular_rate_rad_s": value[1]}
                              for key, value in references.items()},
        "independent_solver_max_state_disagreement": independent_difference,
        "rk4_step_halving_angle_error_ratios": ratios,
        "rk4_results": table,
        "limitations": ["Prototype dynamics only; physical parameters not measured",
                        "Independent solvers share the same stated nonlinear ODE",
                        "No independent physics validation, actuator, controls, or real hardware",
                        "Step-order check limited to four chosen step sizes and one initial state"],
    }
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("dt_s", "angle_rad", "angular_rate_rad_s", "error_to_DOP853_angle_rad"))
    for row in table:
        writer.writerow((f'{row["dt_s"]:.5f}', f'{row["angle_rad"]:.16e}',
                         f'{row["angular_rate_rad_s"]:.16e}', f'{row["angle_error_to_DOP853_rad"]:.16e}'))
    data = stream.getvalue().encode("utf-8")
    report = (json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False)+"\n").encode("utf-8")
    if not passed:
        raise RuntimeError(f"NUMERICAL_CONVERGENCE_FAILED: {summary}")
    return summary, data, report


def archive(repo_root: Path, target: Path) -> dict:
    repo_root = repo_root.resolve()
    target = target.resolve()
    if target.exists():
        raise FileExistsError("Refusing to overwrite an existing experiment archive")
    summary, csv_data, report = evaluate(repo_root)
    source = (repo_root / "dynamics_sim" / "physics_engine.py").read_bytes()
    target.mkdir(parents=True, exist_ok=False)
    for sub in ("inputs", "outputs"):
        (target / sub).mkdir()
    (target / "inputs" / "physics_engine.py").write_bytes(source)
    (target / "inputs" / "case.json").write_text(json.dumps(CASE, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    (target / "outputs" / "convergence.csv").write_bytes(csv_data)
    (target / "outputs" / "summary.json").write_bytes(report)
    doc = {
        "schema_version": 1,
        "run_id": "KB4-NONLINEAR-STEP-CONVERGENCE-001",
        "classification": "SOFTWARE_SIMULATION_ONLY",
        "intended_use": "Compare the real pinned historical unpowered 1D RK4 model to DOP853 and Radau nonlinear ODE integration",
        "unsupported_uses": ["physical model calibration", "controller tuning", "powered experiments", "flight readiness", "manufacturing approval"],
        "model": {"name": "historical-InvertedPendulum1D-zero-thrust", "version": "pinned Git blob",
                  "coordinate_system": "theta zero is vertical, positive clockwise, angles in rad",
                  "units": {"angle": "rad", "time": "s", "mass": "kg", "force": "N", "length": "m"},
                  "assumptions": ["zero thrust", "historical default 1D inertia and damping", "nonlinear sin(theta) retained"],
                  "physical_correlation_status": "NOT_MEASURED_OR_VALIDATED"},
        "source": {"repository": "guo6x/AI-rocket", "commit": MODEL_SOURCE_COMMIT},
        "runtime": {"python_version": platform.python_version(),
                    "dependencies": {"scipy": scipy.__version__, "numpy": numpy.__version__},
                    "command": "python docs/aerospace-knowledge/examples/nonlinear_convergence.py --output-dir NEW_DIRECTORY",
                    "random_seed": None},
        "inputs": [{"path": f"inputs/{p}", "sha256": sha256_file(target / "inputs" / p)}
                   for p in ("physics_engine.py", "case.json")],
        "outputs": [{"path": f"outputs/{p}", "sha256": sha256_file(target / "outputs" / p)}
                    for p in ("convergence.csv", "summary.json")]
    }
    (target / "manifest.json").write_text(json.dumps(doc, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    failures = validate_manifest(target / "manifest.json")
    if failures:
        raise RuntimeError(f"MANIFEST_FAILED: {failures}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = archive(args.repo_root, args.output_dir)
    print(json.dumps({"status": result["status"], "error_ratios": result["rk4_step_halving_angle_error_ratios"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
