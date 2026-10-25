"""Deterministic R3.1 synthetic reliability experiment tests."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from rf_lab.reliability_experiment import (
    SCENARIO_SEED,
    SEEDED_FRAME_COUNT,
    ReadOnlyTelemetryReceiver,
    _canonical_sha256,
    _input_trace,
    check_invariants,
    evidence,
    main,
    run_deterministic_experiment,
    run_experiment,
)


class ReliabilityExperimentTests(unittest.TestCase):
    def setUp(self):
        self.report = run_deterministic_experiment()
        self.rows = {row["scenario"]: row for row in self.report["scenarios"]}

    def test_r3_0_protocol_and_evidence_ceiling_remain_unchanged(self):
        self.assertEqual(self.report["contract_id"], "AA-RF-OFFLINE-RELIABILITY-001")
        self.assertEqual(self.report["evidence_ceiling"], "TESTED_SOFTWARE")
        self.assertTrue(self.report["synthetic_only"])
        self.assertEqual(self.report["real_radio_metrics"], "NOT_MEASURED")
        self.assertFalse(self.report["crc_authentication"])

    def test_all_requested_fault_families_have_explicit_scenarios(self):
        self.assertEqual(set(self.rows), {
            "normal_ordered",
            "independent_synthetic_drops",
            "contiguous_synthetic_burst",
            "duplicate_delivery",
            "delayed_out_of_order",
            "crc_corruption",
            "truncation_and_length_anomalies",
            "uint16_large_gap_half_range_and_wrap",
            "untrusted_session_churn",
            "seeded_bounded_fault_mix",
        })

    def test_normal_stream_is_ordered_and_gap_free(self):
        row = self.rows["normal_ordered"]
        self.assertEqual(row["generator"]["unique_frames_generated"], 8)
        self.assertEqual(row["receiver"]["status_counts"]["ACCEPT"], 8)
        self.assertEqual(row["receiver"]["unobserved_forward_sequence_gap_count"], 0)

    def test_independent_and_bursty_generator_drops_are_reported_separately(self):
        independent = self.rows["independent_synthetic_drops"]
        burst = self.rows["contiguous_synthetic_burst"]
        self.assertEqual(independent["generator"]["known_synthetic_drop_count"], 3)
        self.assertEqual(independent["receiver"]["unobserved_forward_sequence_gap_count"], 3)
        self.assertEqual(burst["generator"]["known_synthetic_drop_count"], 4)
        self.assertEqual(burst["receiver"]["unobserved_forward_sequence_gap_count"], 4)
        self.assertNotIn("packet_loss_rate", independent["receiver"])

    def test_duplicate_is_reported_but_does_not_advance_freshness(self):
        row = self.rows["duplicate_delivery"]
        self.assertEqual(row["receiver"]["status_counts"]["DUPLICATE"], 1)
        self.assertEqual(row["receiver"]["duplicate_or_stale_window_mutations"], 0)
        duplicate = next(item for item in row["observations"]
                         if item["generator_label"] == "duplicate_copy")
        self.assertEqual(duplicate["status"], "DUPLICATE")
        self.assertTrue(duplicate["window_unchanged"])
        self.assertFalse(duplicate["flight_control_authority_granted"])

    def test_delayed_out_of_order_data_is_receiver_stale_not_a_known_drop(self):
        row = self.rows["delayed_out_of_order"]
        self.assertEqual(row["generator"]["known_synthetic_drop_count"], 0)
        self.assertEqual(row["generator"]["synthetic_fault_injection_counts"]["delayed"], 2)
        self.assertEqual(row["receiver"]["status_counts"]["STALE_OR_OUT_OF_ORDER"], 2)
        self.assertEqual(row["receiver"]["unobserved_forward_sequence_gap_count"], 2)
        self.assertEqual(row["receiver"]["maximum_unobserved_forward_gap_in_one_accept"], 2)
        self.assertEqual(row["receiver"]["duplicate_or_stale_window_mutations"], 0)
        self.assertEqual([item["sequence"] for item in row["observations"]],
                         [0, 1, 4, 5, 2, 3, 6, 7])
        self.assertEqual([item["status"] for item in row["observations"]], [
            "ACCEPT", "ACCEPT", "ACCEPT", "ACCEPT",
            "STALE_OR_OUT_OF_ORDER", "STALE_OR_OUT_OF_ORDER", "ACCEPT", "ACCEPT",
        ])
        for item in row["observations"]:
            self.assertGreaterEqual(item["release_slot"], item["source_generation_ordinal"])
        self.assertEqual([item["release_slot"] for item in row["observations"]],
                         [0, 1, 4, 5, 6, 6, 6, 7])

    def test_crc_rejection_creates_gap_without_known_simulator_drop(self):
        row = self.rows["crc_corruption"]
        self.assertEqual(row["generator"]["known_synthetic_drop_count"], 0)
        self.assertEqual(row["receiver"]["rejected_by_reason"], {"crc_mismatch": 1})
        self.assertEqual(row["receiver"]["unobserved_forward_sequence_gap_count"], 1)
        rejected = next(item for item in row["observations"] if item["status"] == "REJECT_crc_mismatch")
        self.assertTrue(rejected["window_unchanged"])

    def test_truncated_and_invalid_length_datagrams_do_not_poison_window(self):
        row = self.rows["truncation_and_length_anomalies"]
        self.assertEqual(row["receiver"]["rejected_by_reason"], {
            "payload_length_out_of_range": 1,
            "payload_size_mismatch": 1,
            "truncated_header_or_crc": 1,
        })
        self.assertEqual(row["receiver"]["invalid_datagram_window_mutations"], 0)
        self.assertEqual(row["receiver"]["unobserved_forward_sequence_gap_count"], 0)
        self.assertEqual(row["receiver"]["status_counts"]["ACCEPT"], 2)
        self.assertTrue(all(item["window_unchanged"] for item in row["observations"][1:4]))

    def test_large_uint16_gaps_half_range_and_wrap(self):
        row = self.rows["uint16_large_gap_half_range_and_wrap"]
        receiver = row["receiver"]
        self.assertEqual(receiver["unobserved_forward_sequence_gap_count"], 65532)
        self.assertEqual(receiver["maximum_unobserved_forward_gap_in_one_accept"], 32766)
        self.assertEqual(receiver["status_counts"]["STALE_OR_OUT_OF_ORDER"], 2)
        self.assertEqual([item["status"] for item in row["observations"][-3:]], [
            "ACCEPT", "ACCEPT", "STALE_OR_OUT_OF_ORDER"
        ])

    def test_spoofable_session_changes_are_untrusted_and_control_free(self):
        row = self.rows["untrusted_session_churn"]
        receiver = row["receiver"]
        self.assertFalse(receiver["session_identity_authenticated"])
        self.assertEqual(receiver["status_counts"]["SESSION_CHANGED"], 2)
        self.assertEqual(receiver["status_counts"]["DUPLICATE"], 1)
        self.assertEqual(receiver["status_counts"]["STALE_OR_OUT_OF_ORDER"], 1)
        self.assertEqual(receiver["flight_command_dispatches"], 0)
        self.assertEqual(receiver["flight_control_authority_grants"], 0)
        self.assertFalse(row["permission_boundary"]["flight_command_channel_connected"])
        self.assertTrue(all(not item["flight_control_authority_granted"]
                            for item in row["observations"]))

    def test_receiver_has_no_dispatch_or_actuator_api(self):
        receiver = ReadOnlyTelemetryReceiver()
        self.assertFalse(hasattr(receiver, "dispatch_command"))
        self.assertFalse(hasattr(receiver, "write_actuator"))
        self.assertEqual(receiver.summary()["flight_control_authority_grants"], 0)

    def test_non_bytes_input_is_rejected_without_mutating_freshness(self):
        receiver = ReadOnlyTelemetryReceiver()
        before = (receiver.window.session_id, receiver.window.last_sequence)
        outcome = receiver.offer("not-a-datagram")
        self.assertEqual(outcome["status"], "REJECT_datagram_must_be_bytes")
        self.assertTrue(outcome["window_unchanged"])
        self.assertEqual((receiver.window.session_id, receiver.window.last_sequence), before)

    def test_seeded_stream_has_exact_fixed_fault_population_and_bounds(self):
        row = self.rows["seeded_bounded_fault_mix"]
        generator = row["generator"]
        self.assertEqual(SEEDED_FRAME_COUNT, 512)
        self.assertEqual(SCENARIO_SEED, 0x5231)
        self.assertEqual(generator["unique_frames_generated"], 512)
        self.assertEqual(generator["synthetic_fault_injection_counts"], {
            "crc_corruption": 32,
            "delay": 32,
            "drop": 32,
            "duplicate": 32,
            "normal": 352,
            "truncation": 32,
        })
        self.assertEqual(generator["known_synthetic_drop_count"], 32)
        self.assertEqual(generator["datagrams_offered_to_receiver"], 512)
        self.assertEqual(generator["maximum_pending_synthetic_delayed_datagrams"], 2)
        self.assertEqual(row["receiver"]["invalid_datagram_window_mutations"], 0)

    def test_known_synthetic_drops_are_not_aliased_to_inferred_gaps(self):
        crc = self.rows["crc_corruption"]
        delayed = self.rows["delayed_out_of_order"]
        self.assertNotEqual(
            crc["generator"]["known_synthetic_drop_count"],
            crc["receiver"]["unobserved_forward_sequence_gap_count"],
        )
        self.assertNotEqual(
            delayed["generator"]["known_synthetic_drop_count"],
            delayed["receiver"]["unobserved_forward_sequence_gap_count"],
        )

    def test_trace_and_deterministic_result_hashes_reproduce(self):
        self.assertEqual(_canonical_sha256(_input_trace()), _canonical_sha256(_input_trace()))
        first = run_deterministic_experiment()
        second = run_deterministic_experiment()
        self.assertEqual(_canonical_sha256(first), _canonical_sha256(second))
        self.assertEqual(check_invariants(first), check_invariants(second))

    def test_resource_observation_is_host_software_only(self):
        report = run_experiment()
        resource = report["software_resource_observation"]
        self.assertIn("not an RF", resource["scope"])
        self.assertGreaterEqual(resource["host_elapsed_seconds"], 0)
        self.assertGreater(resource["python_tracemalloc_peak_bytes"], 0)
        self.assertLessEqual(resource["host_elapsed_seconds"], resource["host_runtime_guard_seconds"])
        self.assertLessEqual(resource["python_tracemalloc_peak_bytes"],
                             resource["python_tracemalloc_guard_bytes"])
        self.assertLessEqual(resource["maximum_pending_delay_queue_observed"],
                             resource["delay_queue_bound_frames"])
        self.assertEqual(resource["maximum_generated_frames_per_scenario"], 512)

    def test_evidence_write_binds_trace_sources_versions_and_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "r3_1 evidence.json"
            command = "py -3 -m rf_lab.reliability_experiment --write-evidence 'r3_1 evidence.json'"
            record = evidence(command, output.as_posix())
            output.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
            loaded = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(loaded["artifact_path"], output.as_posix())
        self.assertEqual(loaded["reproduction_command"], command)
        self.assertEqual(loaded["input_trace_sha256"], _canonical_sha256(loaded["input_trace"]))
        self.assertRegex(loaded["deterministic_result_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(loaded["input_seed"], SCENARIO_SEED)
        self.assertEqual(loaded["evidence_ceiling"], "TESTED_SOFTWARE")
        self.assertFalse(loaded["physical_hardware"])
        self.assertEqual(loaded["radio_transmissions"], 0)
        self.assertEqual(loaded["flight_commands"], 0)
        self.assertFalse(loaded["crc_is_authentication"])
        self.assertIn("python", loaded["tool_versions"])
        self.assertIn("platformio_cli", loaded["tool_versions"])
        self.assertIn("platformio_compiler_versions", loaded["tool_versions"])
        self.assertIn("rf_lab/reliability_experiment.py", loaded["source_sha256"])
        self.assertTrue(all(len(value) == 64 for value in loaded["source_sha256"].values()))

    def test_evidence_cli_writes_new_artifact_and_reports_exact_file_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "evidence.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["--write-evidence", str(output)]), 0)
            summary = json.loads(stdout.getvalue())
            serialized = output.read_bytes()
            record = json.loads(serialized)
        self.assertEqual(summary["evidence"], "WRITTEN")
        self.assertEqual(summary["artifact_sha256"], hashlib.sha256(serialized).hexdigest())
        self.assertEqual(record["artifact_path"], output.as_posix())
        self.assertEqual(record["input_trace_sha256"], _canonical_sha256(record["input_trace"]))

    def test_cli_check_executes_the_experiment(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(["--check"]), 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(len(result["scenario_names"]), 10)
        self.assertIn("generator drops and receiver sequence gaps are independently counted",
                      result["invariants"])

    def test_evidence_cli_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "existing.json"
            output.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                main(["--write-evidence", str(output)])
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
