"""Read-only smoke checks for the currently executable simulation kernels.

This script intentionally does not run generators that overwrite files under
``aero_sim/results`` or ``dynamics_sim``.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aero_sim"))
sys.path.insert(0, str(ROOT / "dynamics_sim"))

import rocket_config  # noqa: E402
from components import SensorModel, ServoModel  # noqa: E402
from physics_engine import InvertedPendulum1D  # noqa: E402
from physics_engine_2d import run_2d_test  # noqa: E402
from sixdof_simulation import quat_normalize, quat_to_rotmat  # noqa: E402


def check_legacy_flight_config_consistency() -> None:
    expected = rocket_config.MASS_DRY + rocket_config.MOTOR_TOTAL_MASS
    assert math.isclose(rocket_config.MASS_TOTAL, expected, rel_tol=0.0, abs_tol=1e-12)
    assert rocket_config.BODY_OUTER_RADIUS > rocket_config.BODY_INNER_RADIUS > 0


def check_component_models_are_finite() -> None:
    sensor = SensorModel(update_rate_hz=20.0, delay_ms=50.0)
    servo = ServoModel(update_rate_hz=50.0, max_angle_deg=15.0, speed_deg_per_s=600.0)
    pendulum = InvertedPendulum1D()
    pendulum.reset(initial_pitch_deg=1.0)
    sensor.reset()
    servo.reset()

    measured = sensor.update(0.001, 0.0, 1.0)
    servo.command(10.0)
    servo_angle = servo.step(0.001)
    pitch, pitch_rate = pendulum.step(0.001, servo_angle)
    assert all(math.isfinite(value) for value in (measured, servo_angle, pitch, pitch_rate))
    assert abs(servo_angle) <= 0.6 + 1e-9


def check_quaternion_rotation() -> None:
    q = quat_normalize([2.0, 0.0, 0.0, 0.0])
    rotation = quat_to_rotmat(q)
    assert rotation.shape == (3, 3)
    assert abs(float(rotation[0, 0]) - 1.0) < 1e-12


def check_current_tvc_simulation_baseline() -> None:
    tuned = run_2d_test(
        profile="TUNED",
        initial_perturbation=1.0,
        duration=10.0,
        thrust=15.0,
        with_sensors=True,
        with_disturbance=True,
    )
    testbench = run_2d_test(
        profile="TESTBENCH",
        initial_perturbation=5.0,
        duration=10.0,
        thrust=15.0,
        with_sensors=True,
        with_disturbance=True,
    )

    assert tuned["stable"] is True
    assert testbench["stable"] is False
    print(
        "Simulation baseline: TUNED small-angle case converges; "
        "firmware TESTBENCH profile does not converge in the non-ideal 5-degree case."
    )


def main() -> int:
    check_legacy_flight_config_consistency()
    check_component_models_are_finite()
    check_quaternion_rotation()
    check_current_tvc_simulation_baseline()
    print("Simulation smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
