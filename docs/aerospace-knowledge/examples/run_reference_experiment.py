"""Offline, pinned-source numerical reference experiment for the legacy 1-D model.

DOES NOT operate hardware, tune a controller, or certify a physical rocket.
Run from the repository with a new output directory, never an existing one.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import platform
from pathlib import Path

from simulation_manifest import sha256_file, validate_manifest

# GitHub-verified historical model blob, not a physical configuration authority.
MODEL_GIT_BLOB_SHA = "f804ab126d13781928036ee4a22b99cf0ea59be6"
MODEL_SOURCE_COMMIT = "25b0f6c31f01ab9178cf6dd96d7e0ca8eff7cc99"

CASE = {
    "mass_kg": 1.0, "length_cg_m": 0.2, "length_thrust_m": 0.5,
    "nominal_max_thrust_N": 15.0, "actual_thrust_N": 0.0,
    "initial_angle_deg": 0.1, "dt_s": 0.002, "steps": 200,
    "record_every_steps": 20, "damping_Nm_s_rad": 0.5,
    "gravity_m_s2": 9.81, "max_analytic_error_rad": 1e-7,
    "max_equilibrium_error_rad": 1e-14, "max_symmetry_error_rad": 1e-13,
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _model_class(source_path: Path):
    spec = importlib.util.spec_from_file_location("adastra_pinned_legacy_physics_model", source_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot import local source model")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.InvertedPendulum1D


def linearized_angle(t: float, theta0: float, model, damping: float) -> float:
    """Linearization of the zero-thrust inverted-pendulum equation at theta=0.

    I θ'' + c θ' - m g L θ = 0, theta(0)=theta0, theta'(0)=0.
    This is an APPROXIMATION to nonlinear sin(theta), not an exact orbit model.
    """
    a = damping / model.I
    b = model.m * model.g * model.L_cg / model.I
    discr = math.sqrt(a * a + 4.0 * b)
    r_pos, r_neg = (-a + discr) / 2.0, (-a - discr) / 2.0
    coeff_pos = (-r_neg * theta0) / (r_pos - r_neg)
    coeff_neg = (r_pos * theta0) / (r_pos - r_neg)
    return coeff_pos * math.exp(r_pos * t) + coeff_neg * math.exp(r_neg * t)


def simulate(Model, angle_deg: float, settings: dict) -> list[tuple[float, float, float]]:
    engine = Model(
        mass=settings["mass_kg"], length_cg=settings["length_cg_m"],
        length_thrust=settings["length_thrust_m"], max_thrust=settings["nominal_max_thrust_N"],
    )
    engine.reset(initial_pitch_deg=angle_deg)
    rows = [(0.0, engine.state[0], engine.state[1])]
    for i in range(1, settings["steps"] + 1):
        # Zero thrust, no actuator commands; experimental numerical verification only.
        engine.step(settings["dt_s"], servo_angle_deg=0.0, thrust=0.0)
        if i % settings["record_every_steps"] == 0:
            rows.append((i * settings["dt_s"], engine.state[0], engine.state[1]))
    return rows


def _csv_bytes(rows: list[tuple[float, float, float]], predictions: list[float]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["time_s", "sim_angle_rad", "linearized_angle_rad", "sim_angular_rate_rad_s", "abs_error_rad"])
    for (t, theta, omega), reference in zip(rows, predictions):
        writer.writerow([f"{t:.6f}", f"{theta:.15e}", f"{reference:.15e}", f"{omega:.15e}", f"{abs(theta-reference):.15e}"])
    return stream.getvalue().encode("utf-8")


def run_experiment(repo_root: Path, output_dir: Path, *, require_exact_source: bool = True) -> dict:
    """Create a new immutable-by-convention archive; never overwrite existing results.

    require_exact_source=False is solely for testing the runner on a reconstructed
    local file and MUST NOT be used to claim that official source was verified.
    """
    repo_root = repo_root.resolve()
    source = repo_root / "dynamics_sim" / "physics_engine.py"
    source_bytes = source.read_bytes()
    actual_blob = git_blob_sha(source_bytes)
    if require_exact_source and actual_blob != MODEL_GIT_BLOB_SHA:
        raise RuntimeError(f"MODEL_SOURCE_MISMATCH: expected {MODEL_GIT_BLOB_SHA}, actual {actual_blob}")
    Model = _model_class(source)
    settings = dict(CASE)
    pos = simulate(Model, settings["initial_angle_deg"], settings)
    neg = simulate(Model, -settings["initial_angle_deg"], settings)
    equilibrium = simulate(Model, 0.0, settings)
    model_for_reference = Model(mass=settings["mass_kg"], length_cg=settings["length_cg_m"], length_thrust=settings["length_thrust_m"], max_thrust=settings["nominal_max_thrust_N"])
    theta0 = math.radians(settings["initial_angle_deg"])
    predictions = [linearized_angle(t, theta0, model_for_reference, settings["damping_Nm_s_rad"]) for t, _, _ in pos]
    max_err = max(abs(theta - reference) for (_, theta, _), reference in zip(pos, predictions))
    max_eq_angle = max(abs(theta) for _, theta, _ in equilibrium)
    max_eq_rate = max(abs(omega) for _, _, omega in equilibrium)
    max_sym_angle = max(abs(p[1] + n[1]) for p, n in zip(pos, neg))
    max_sym_rate = max(abs(p[2] + n[2]) for p, n in zip(pos, neg))
    if not all(map(math.isfinite, (max_err, max_eq_angle, max_eq_rate, max_sym_angle, max_sym_rate))):
        raise RuntimeError("NONFINITE_DIAGNOSTICS")
    passed = (max_err <= settings["max_analytic_error_rad"] and
              max_eq_angle <= settings["max_equilibrium_error_rad"] and
              max_eq_rate <= settings["max_equilibrium_error_rad"] and
              max_sym_angle <= settings["max_symmetry_error_rad"] and
              max_sym_rate <= settings["max_symmetry_error_rad"])
    if not passed:
        raise RuntimeError(f"BENCHMARK_FAILED: analytic={max_err}, eq_angle={max_eq_angle}, eq_rate={max_eq_rate}, symmetry_angle={max_sym_angle}, symmetry_rate={max_sym_rate}")
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "inputs").mkdir()
    (output_dir / "outputs").mkdir()
    (output_dir / "inputs" / "physics_engine.py").write_bytes(source_bytes)
    (output_dir / "inputs" / "reference_case.json").write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "outputs" / "samples.csv").write_bytes(_csv_bytes(pos, predictions))
    result = {
        "status": "PASS_NUMERICAL_REFERENCE_ONLY",
        "archive_source_matches_pinned_git_blob": actual_blob == MODEL_GIT_BLOB_SHA,
        "source_git_blob_sha1": actual_blob,
        "model_name": "legacy_unpowered_inverted_pendulum_1d",
        "reference": "small-angle linearization of original nonlinear zero-thrust ODE",
        "points_recorded": len(pos),
        "max_abs_analytic_error_rad": max_err,
        "max_abs_equilibrium_angle_rad": max_eq_angle,
        "max_abs_equilibrium_rate_rad_s": max_eq_rate,
        "max_pos_neg_symmetry_angle_rad": max_sym_angle,
        "max_pos_neg_symmetry_rate_rad_s": max_sym_rate,
        "thresholds": {"analytic_error_rad": settings["max_analytic_error_rad"], "equilibrium_angle_rad": settings["max_equilibrium_error_rad"], "equilibrium_rate_rad_s": settings["max_equilibrium_error_rad"], "symmetry_angle_rad": settings["max_symmetry_error_rad"], "symmetry_rate_rad_s": settings["max_symmetry_error_rad"]},
        "limitations": ["No external force/thrust", "Very small initial pitch angle", "Linearized reference approximates sin(theta)", "Historical prototype parameters, not measurements", "No controls, electronics, physical hardware, or flight qualification"],
    }
    (output_dir / "outputs" / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "run_id": "KB3-ZERO-THRUST-REFERENCE-001",
        "classification": "SOFTWARE_SIMULATION_ONLY",
        "intended_use": "Check archived prototype model zero-thrust numerical integration against an independent small-angle analytic approximation",
        "unsupported_uses": ["powered thrust tests", "real control tuning", "hardware verification", "free flight readiness", "manufacturing release"],
        "model": {
            "name": "legacy-InvertedPendulum1D", "version": "Ad Astra 2026-10-19 main model snapshot",
            "coordinate_system": "theta=0 at upward vertical, clockwise positive; angle in rad for archived state",
            "units": {"mass": "kg", "length": "m", "force": "N", "time": "s", "angle": "rad", "angular_rate": "rad/s"},
            "assumptions": ["no thrust", "fixed I=(1/3)m(2Lcg)^2", "linearized analytic reference sin(theta)≈theta", "damping coefficient 0.5 Nm s/rad", "historical prototype, not current device"],
            "physical_correlation_status": "NOT_MEASURED_OR_CORRELATED"
        },
        "source": {"repository": "guo6x/AI-rocket", "commit": MODEL_SOURCE_COMMIT},
        "runtime": {"python_version": platform.python_version(), "dependencies": {}, "command": "python docs/aerospace-knowledge/examples/run_reference_experiment.py --output-dir <new-empty-dir>", "random_seed": None},
        "inputs": [{"path": f"inputs/{n}", "sha256": sha256_file(output_dir / "inputs" / n)} for n in ("physics_engine.py", "reference_case.json")],
        "outputs": [{"path": f"outputs/{n}", "sha256": sha256_file(output_dir / "outputs" / n)} for n in ("samples.csv", "summary.json")],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_manifest(manifest_path)
    if errors:
        raise RuntimeError(f"LOCAL_MANIFEST_FAILED: {errors}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = run_experiment(args.repo_root, args.output_dir)
    print(json.dumps({"status": summary["status"], "max_analytic_error_rad": summary["max_abs_analytic_error_rad"], "archived_at": str(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
