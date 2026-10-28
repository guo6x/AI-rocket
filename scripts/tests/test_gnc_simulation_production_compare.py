"""Regression tests for the simulation/production GNC assumption audit."""

from __future__ import annotations

import sys
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_PATH = ROOT / "engineering" / "offline-evidence" / "r2_3" / "gnc_simulation_production_compare.json"
sys.path.insert(0, str(ROOT / "scripts"))

from gnc_simulation_production_compare import (  # noqa: E402
    SOURCE_PATHS,
    _sha256,
    build_result,
)


@pytest.fixture(scope="module")
def result():
    return build_result()


def test_same_trace_has_confirmed_legacy_polarity_difference(result):
    assert result["comparison_status"] == "DIFFERENCE_CONFIRMED"
    assert result["assumptions"]["physical_hardware"] is False
    assert result["assumptions"]["plant_simulated"] is False
    for period in ("10", "50"):
        summary = result["summary"][period]
        assert summary["opposite_sign_count"] == summary["nonzero_count"]
        assert summary["opposite_sign_fraction"] == pytest.approx(1.0)
        assert summary["max_abs_delta_deg"] > 0.0


def test_rows_bind_cadence_and_integer_mapping(result):
    rows = result["rows"]
    assert {int(row["period_ms"]) for row in rows} == {10, 50}
    assert len([row for row in rows if int(row["period_ms"]) == 10]) == 200
    assert len([row for row in rows if int(row["period_ms"]) == 50]) == 40
    for row in rows:
        assert int(row["legacy_servo_command"]) == max(
            0, min(180, 90 + int(float(row["legacy_pid_output_deg"])))
        )
        assert int(row["production_servo_command"]) == max(
            0, min(180, 90 + int(float(row["production_pid_output_deg"])))
        )


def test_result_is_source_and_input_bound(result):
    assert len(result["source_git_sha"]) == 40
    assert len(result["input_trace_sha256"]) == 64
    assert len(result["result_rows_sha256"]) == 64
    assert result["assumptions"]["nonconvergence_or_model_failure"] == "not_run_no_plant"
    assert result["source_sha256"] == {
        path: _sha256(ROOT / path) for path in SOURCE_PATHS
    }


def test_checked_in_evidence_replays_same_trace_and_source_hashes(result):
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    assert evidence["contract"] == result["contract"]
    assert evidence["input_trace_sha256"] == result["input_trace_sha256"]
    assert evidence["result_rows_sha256"] == result["result_rows_sha256"]
    assert evidence["source_sha256"] == result["source_sha256"]
    assert evidence["comparison_status"] == "DIFFERENCE_CONFIRMED"
