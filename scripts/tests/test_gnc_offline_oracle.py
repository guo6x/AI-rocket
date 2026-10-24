"""Deterministic R2.3 source/oracle parity tests (software only)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from gnc_offline_oracle import (  # noqa: E402
    compare_traces,
    manifest,
    oracle_trace,
    run_cpp_trace,
    trace_rows,
)


def _result(results, case, step):
    return next(row["value"] for row in results if row["case"] == case and row["step"] == step)


@pytest.fixture(scope="module")
def cpp_results():
    rows = trace_rows()
    return run_cpp_trace(rows)


def test_trace_has_required_signed_and_timing_cases():
    rows = trace_rows()
    cases = {str(row["case"]) for row in rows}
    assert {
        "positive_perturbation",
        "negative_perturbation",
        "zero_and_step",
        "flight_limit_and_rate",
        "irregular_dt",
        "testbench_profile",
        "kalman_static_zero",
        "kalman_positive_step",
        "kalman_negative_step",
    } <= cases
    assert any(float(row.get("dt", 0.0)) == 0.073 for row in rows)
    assert any(float(row.get("current", 0.0)) == 45.0 for row in rows)
    assert any(float(row.get("current", 0.0)) == -45.0 for row in rows)


def test_cpp_production_trace_matches_independent_python_oracle(cpp_results):
    expected = oracle_trace(trace_rows())
    failures = compare_traces(expected, cpp_results)
    assert not failures, "\n".join(failures)


def test_pid_sign_zero_limit_and_rate_semantics_are_explicit():
    results = oracle_trace(trace_rows())
    positive = _result(results, "positive_perturbation", 0)
    negative = _result(results, "negative_perturbation", 0)
    zero = _result(results, "zero_and_step", 0)
    assert positive < 0.0
    assert negative > 0.0
    assert zero == 0.0

    limited = [
        _result(results, "flight_limit_and_rate", step) for step in range(4)
    ]
    assert all(abs(value) <= 4.0 + 1.0e-6 for value in limited)
    assert all(abs(limited[index] - limited[index - 1]) <= 0.3 + 1.0e-6 for index in range(1, len(limited)))

    testbench = [_result(results, "testbench_profile", step) for step in range(3)]
    assert all(abs(value) <= 15.0 + 1.0e-6 for value in testbench)
    assert all(abs(testbench[index] - testbench[index - 1]) <= 1.0 + 1.0e-6 for index in range(1, len(testbench)))


def test_kalman_signed_steps_and_static_zero_are_deterministic():
    results = oracle_trace(trace_rows())
    static = [_result(results, "kalman_static_zero", step) for step in range(4)]
    assert all(abs(value) <= 1.0e-7 for value in static)
    positive = _result(results, "kalman_positive_step", 0)
    negative = _result(results, "kalman_negative_step", 0)
    assert positive > 0.0
    assert negative < 0.0
    assert math.isclose(abs(positive), abs(negative), rel_tol=1.0e-5, abs_tol=1.0e-5)


def test_manifest_is_source_bound_and_hardware_free():
    rows = trace_rows()
    output = manifest(rows, oracle_trace(rows), "python scripts/gnc_offline_oracle.py --write-json <output>")
    assert output["contract"] == "AA-GNC-OFFLINE-CONTRACT-001"
    assert output["source_git_sha"]
    assert output["input_trace_sha256"]
    assert output["source_sha256"]
    assert output["seed"] == "not_applicable_fixed_trace"
    assert output["physical_hardware"] is False
    assert output["plant_or_mounting_claim"] is False
    assert output["recovery_output_touched"] is False
