"""Deterministic dual-period production-PID comparison tests."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from gnc_dual_period import (  # noqa: E402
    DURATION_MS,
    PERIODS_MS,
    all_input_rows,
    attitude_deg,
    compare_traces,
    manifest,
    metrics,
    python_trace,
    run_cpp_trace,
)


@pytest.fixture(scope="module")
def dual_results():
    rows = all_input_rows()
    expected = python_trace(rows)
    actual = run_cpp_trace(rows)
    assert not compare_traces(expected, actual)
    for row in actual:
        output = float(row["pid_output_deg"])
        row["quantization_error_deg"] = float(row["servo_command"]) - (90.0 + output)
    return rows, actual


def test_trace_uses_one_fixed_input_and_two_independent_periods():
    rows = all_input_rows()
    assert {int(row["period_ms"]) for row in rows} == set(PERIODS_MS)
    assert len(rows) == DURATION_MS // 10 + DURATION_MS // 50
    assert attitude_deg(0) == 0.0
    assert attitude_deg(250) > 0.0
    assert attitude_deg(720) == -6.0  # deterministic step
    assert attitude_deg(1300) < 0.0  # return ramp
    assert attitude_deg(DURATION_MS) == 0.0


def test_cpp_production_pid_matches_independent_reference(dual_results):
    rows, actual = dual_results
    expected = python_trace(rows)
    failures = compare_traces(expected, actual)
    assert not failures, "\n".join(failures)


def test_period_metrics_expose_call_rate_and_quantization(dual_results):
    _, actual = dual_results
    result = metrics(actual)
    by_period = result["per_period"]
    assert by_period["10"]["sample_count"] == 200
    assert by_period["50"]["sample_count"] == 40
    assert by_period["10"]["effective_rate_limit_deg_per_s"] == pytest.approx(30.0)
    assert by_period["50"]["effective_rate_limit_deg_per_s"] == pytest.approx(6.0)
    assert result["common_time_count"] == 40
    assert result["common_time_pid_max_abs_diff_deg"] > 1.0
    assert result["common_time_servo_max_abs_diff_count"] > 0
    for period in PERIODS_MS:
        period_rows = [row for row in actual if int(row["period_ms"]) == period]
        assert max(abs(float(row["pid_output_deg"])) for row in period_rows) <= 4.0 + 1.0e-6
        assert all(
            abs(float(current["pid_output_deg"]) - float(previous["pid_output_deg"]))
            <= 0.3 + 1.0e-6
            for previous, current in zip(period_rows, period_rows[1:])
        )
    assert by_period["10"]["quantization_error_max_abs_deg"] > 0.0
    assert by_period["50"]["quantization_error_max_abs_deg"] > 0.0


def test_servo_command_matches_main_cpp_integer_quantization(dual_results):
    _, actual = dual_results
    for row in actual:
        output = float(row["pid_output_deg"])
        expected = max(0, min(180, 90 + int(output)))
        assert int(row["servo_command"]) == expected
        assert math.isclose(
            float(row["quantization_error_deg"]),
            float(row["servo_command"]) - (90.0 + output),
            rel_tol=0.0,
            abs_tol=1.0e-7,
        )


def test_manifest_is_hardware_free_and_source_bound(dual_results):
    rows, actual = dual_results
    output = manifest(rows, actual, "python scripts/gnc_dual_period.py --write-json <output>")
    assert output["contract"] == "AA-GNC-OFFLINE-DUAL-PERIOD-001"
    assert output["source_git_sha"]
    assert output["source_sha256"]
    assert output["seed"] == "not_applicable_fixed_trace"
    assert output["comparison"] == "PASS"
    assert output["failures"] == []
    assert "platformio" in output["tool_versions"]
    assert output["period_50ms_is_measured"] is False
    assert output["physical_hardware"] is False
    assert output["plant_or_mounting_claim"] is False
    assert output["recovery_output_touched"] is False
