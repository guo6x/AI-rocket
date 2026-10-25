"""Deterministic R3.2 offline status presentation regression."""
import unittest

from rf_lab.quality_demo import main, run_demo


class QualityDemoTests(unittest.TestCase):
    def setUp(self):
        self.d = {r["label"]: r["status"] for r in run_demo()["frames"]}

    def test_bad_packets_cannot_resurrect_old_telemetry(self):
        self.assertEqual(self.d["before_data"]["freshness"], "NO_DECODED_SAMPLE")
        self.assertEqual(self.d["first_decoded_untrusted"]["freshness"], "RECENT_UNAUTHENTICATED")
        for key in ("corrupt_does_not_make_old_sample_recent",
                    "duplicate_does_not_make_old_sample_recent"):
            self.assertEqual(self.d[key]["freshness"], "STALE_UNAUTHENTICATED")

    def test_new_session_never_authenticates_peer(self):
        last = self.d["new_label_is_not_authenticated"]
        self.assertTrue(last["session_change_seen_untrusted"])
        self.assertEqual(last["source_identity"], "UNAUTHENTICATED")
        self.assertFalse(last["packet_acceptance_is_sender_authentication"])
        self.assertFalse(last["flight_control_authority"])

    def test_no_radio_or_commands_and_deterministic(self):
        first = run_demo()
        self.assertEqual(first, run_demo())
        self.assertEqual(first["radio_transmissions"], 0)
        self.assertEqual(first["command_dispatches"], 0)

    def test_cli_check_uses_same_invariants(self):
        import contextlib
        import io
        import json
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--check"]), 0)
        self.assertEqual(json.loads(output.getvalue())["result"], "PASS")


if __name__ == "__main__":
    unittest.main()
