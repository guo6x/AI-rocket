"""R3.2 evidence integrity tests; no writes outside temporary directories."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from rf_lab.quality_demo import demo_input_trace
from rf_lab.quality_evidence import _canonical_sha256, evidence, main


class QualityEvidenceTests(unittest.TestCase):
    def test_demo_trace_and_result_hashes_are_reproducible(self):
        first_trace = demo_input_trace()
        second_trace = demo_input_trace()
        self.assertEqual(first_trace, second_trace)
        self.assertEqual(_canonical_sha256(first_trace), _canonical_sha256(second_trace))
        self.assertEqual(len(first_trace), 5)
        self.assertTrue(all(
            "datagram_hex" not in step or len(step["datagram_hex"]) >= 40
            for step in first_trace
        ))

    def test_evidence_binds_r31_artifact_and_offline_limits(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "evidence.json"
            record = evidence("test command", output.as_posix())
        self.assertEqual(record["input_trace_sha256"], _canonical_sha256(record["input_trace"]))
        self.assertEqual(record["deterministic_result_sha256"],
                         _canonical_sha256(record["deterministic_result"]))
        self.assertEqual(record["r3_1_replay"]["result"], "PASS")
        self.assertEqual(record["quality_demo_check_result"], "PASS")
        self.assertRegex(record["r3_1_replay"]["artifact_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(record["evidence_ceiling"], "TESTED_SOFTWARE")
        self.assertFalse(record["sensor_measurement_time_observed"])
        self.assertFalse(record["crc_is_authentication"])
        self.assertEqual(record["radio_transmissions"], 0)
        self.assertEqual(record["flight_commands"], 0)
        self.assertTrue(all(len(value) == 64 for value in record["source_sha256"].values()))

    def test_cli_writes_hash_bound_record_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "quality evidence.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["--write-evidence", str(output)]), 0)
            record = json.loads(output.read_text(encoding="utf-8"))
            summary = json.loads(stdout.getvalue())
            payload = output.read_bytes()
            self.assertEqual(summary["artifact_sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(record["artifact_path"], output.as_posix())
            with self.assertRaises(FileExistsError):
                main(["--write-evidence", str(output)])
            self.assertEqual(output.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
