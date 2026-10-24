"""R3.2: source-quality and synthetic-age tests; no actual radio."""
import unittest

from rf_lab.telemetry_frame import TelemetryFrame, encode_telemetry
from rf_lab.telemetry_quality import TelemetryQualityMonitor


def packet(session: int, sequence: int, body: bytes = b"synthetic-telemetry") -> bytes:
    return encode_telemetry(TelemetryFrame(session, sequence, body))


class TelemetryQualityTests(unittest.TestCase):
    def test_empty_monitor_never_claims_data_or_source(self):
        result = TelemetryQualityMonitor().snapshot(now_seconds=10)
        self.assertEqual(result["freshness"], "NO_DECODED_SAMPLE")
        self.assertIsNone(result["synthetic_age_seconds"])
        self.assertEqual(result["source_identity"], "UNAUTHENTICATED")
        self.assertEqual(result["actual_rf_loss_latency_range_throughput"], "NOT_MEASURED")
        self.assertFalse(result["flight_control_authority"])

    def test_age_boundary_is_explicit_synthetic_not_hardware(self):
        m = TelemetryQualityMonitor(stale_after_seconds=2)
        outcome = m.observe(packet(7, 0), now_seconds=1)
        self.assertEqual(outcome["event"], "ACCEPT")
        self.assertTrue(outcome["sample_refreshed"])
        self.assertEqual(m.snapshot(now_seconds=3)["freshness"], "RECENT_UNAUTHENTICATED")
        aged = m.snapshot(now_seconds=3.001)
        self.assertEqual(aged["freshness"], "STALE_UNAUTHENTICATED")
        self.assertAlmostEqual(aged["synthetic_age_seconds"], 2.001)

    def test_crc_rejection_does_not_refresh_last_decoded_sample(self):
        m = TelemetryQualityMonitor(stale_after_seconds=1)
        m.observe(packet(1, 10), now_seconds=0)
        broken = bytearray(packet(1, 11))
        broken[-1] ^= 1
        event = m.observe(bytes(broken), now_seconds=2)
        self.assertEqual(event["event"], "REJECT_crc_mismatch")
        self.assertFalse(event["sample_refreshed"])
        state = m.snapshot(now_seconds=2)
        self.assertEqual(state["last_packet_outcome"], "REJECT_crc_mismatch")
        self.assertEqual(state["freshness"], "STALE_UNAUTHENTICATED")
        self.assertEqual(state["synthetic_age_seconds"], 2)
        self.assertEqual(m.window.last_sequence, 10)

    def test_duplicate_never_refreshes_sample_age(self):
        m = TelemetryQualityMonitor(stale_after_seconds=1)
        m.observe(packet(1, 10), now_seconds=0)
        event = m.observe(packet(1, 10), now_seconds=5)
        self.assertEqual(event["event"], "DUPLICATE")
        self.assertFalse(event["sample_refreshed"])
        self.assertEqual(m.snapshot(now_seconds=5)["synthetic_age_seconds"], 5)

    def test_out_of_order_never_refreshes_sample_age(self):
        m = TelemetryQualityMonitor(stale_after_seconds=1)
        m.observe(packet(1, 10), now_seconds=0)
        event = m.observe(packet(1, 9), now_seconds=5)
        self.assertEqual(event["event"], "STALE_OR_OUT_OF_ORDER")
        self.assertFalse(event["sample_refreshed"])
        self.assertEqual(m.snapshot(now_seconds=5)["freshness"], "STALE_UNAUTHENTICATED")
        self.assertEqual(m.window.last_sequence, 10)

    def test_gap_count_is_not_measured_rf_loss(self):
        m = TelemetryQualityMonitor()
        m.observe(packet(1, 10), now_seconds=0)
        self.assertEqual(m.observe(packet(1, 15), now_seconds=1)["forward_unobserved_sequences"], 4)
        state = m.snapshot(now_seconds=1)
        self.assertEqual(state["receiver_sequence_gaps_unobserved"], 4)
        self.assertEqual(state["actual_rf_loss_latency_range_throughput"], "NOT_MEASURED")

    def test_untrusted_session_change_is_persistent_warning(self):
        m = TelemetryQualityMonitor()
        m.observe(packet(1, 10), now_seconds=0)
        result = m.observe(packet(2, 0), now_seconds=1)
        self.assertEqual(result["event"], "SESSION_CHANGED")
        state = m.snapshot(now_seconds=1)
        self.assertTrue(state["session_change_seen_untrusted"])
        self.assertFalse(state["last_sample_was_authenticated"])
        self.assertEqual(state["source_identity"], "UNAUTHENTICATED")
        self.assertEqual(state["freshness"], "RECENT_UNAUTHENTICATED")
        # A return to the original unauthenticated label does not prove identity.
        m.observe(packet(1, 11), now_seconds=2)
        self.assertTrue(m.snapshot(now_seconds=2)["session_change_seen_untrusted"])

    def test_command_looking_payload_stays_opaque(self):
        m = TelemetryQualityMonitor()
        result = m.observe(packet(1, 0, b"arm"), now_seconds=0)
        self.assertEqual(result["event"], "ACCEPT")
        self.assertFalse(result["flight_control_authority"])
        self.assertFalse(m.snapshot(now_seconds=0)["control_or_actuator_channel_connected"])
        self.assertFalse(hasattr(m, "dispatch_command"))
        self.assertFalse(hasattr(m, "write_actuator"))

    def test_non_byte_datagram_is_rejected_without_window_change(self):
        m = TelemetryQualityMonitor()
        m.observe(packet(1, 10), now_seconds=1)
        result = m.observe("not bytes", now_seconds=2)
        self.assertEqual(result["event"], "REJECT_datagram_must_be_bytes")
        self.assertFalse(result["sample_refreshed"])
        self.assertEqual(m.window.last_sequence, 10)
        self.assertEqual(m.snapshot(now_seconds=2)["synthetic_age_seconds"], 1)

    def test_truncation_rejected_without_freshness_refresh(self):
        m = TelemetryQualityMonitor()
        m.observe(packet(1, 10), now_seconds=1)
        result = m.observe(packet(1, 11)[:5], now_seconds=3)
        self.assertEqual(result["event"], "REJECT_truncated_header_or_crc")
        self.assertFalse(result["sample_refreshed"])
        self.assertEqual(m.window.last_sequence, 10)

    def test_bad_clock_atomic_no_offer_or_window_mutation(self):
        m = TelemetryQualityMonitor()
        m.observe(packet(1, 5), now_seconds=10)
        before = m.snapshot(now_seconds=10)
        for clock in (-1, float("nan"), float("inf"), 9, True, "11"):
            with self.subTest(clock=clock):
                with self.assertRaises((TypeError, ValueError)):
                    m.observe(packet(1, 6), now_seconds=clock)
                self.assertEqual(m.snapshot(now_seconds=10), before)
                self.assertEqual(m.window.last_sequence, 5)
        self.assertEqual(m.observe(packet(1, 6), now_seconds=11)["event"], "ACCEPT")

    def test_large_integer_clock_remains_exact_without_float_overflow(self):
        base = 2**53
        m = TelemetryQualityMonitor(stale_after_seconds=1)
        m.observe(packet(1, 5), now_seconds=base)
        at_one_second = m.snapshot(now_seconds=base + 1)
        self.assertEqual(at_one_second["synthetic_age_seconds"], 1)
        self.assertEqual(at_one_second["freshness"], "RECENT_UNAUTHENTICATED")

        huge = 10**400
        m.observe(packet(1, 6), now_seconds=huge)
        self.assertEqual(m.snapshot(now_seconds=huge + 1)["synthetic_age_seconds"], 1)

    def test_bad_stale_threshold_rejected(self):
        for value in (0, -0.1, float("nan"), float("inf"), True, "2"):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    TelemetryQualityMonitor(value)

    def test_snapshot_does_not_advance_state(self):
        m = TelemetryQualityMonitor(stale_after_seconds=2)
        m.observe(packet(1, 10), now_seconds=0)
        future = m.snapshot(now_seconds=100)
        self.assertEqual(future["freshness"], "STALE_UNAUTHENTICATED")
        self.assertEqual(m.snapshot(now_seconds=1)["freshness"], "RECENT_UNAUTHENTICATED")
        self.assertEqual(m.observe(packet(1, 11), now_seconds=1)["event"], "ACCEPT")

    def test_no_unbounded_packet_storage(self):
        m = TelemetryQualityMonitor()
        for i in range(1000):
            m.observe(packet(1, i), now_seconds=i)
        self.assertEqual(m.snapshot(now_seconds=999)["event_counts"], {"ACCEPT": 1000})
        self.assertFalse(any(name in vars(m) for name in ("packets", "payloads", "datagrams", "history")))
        self.assertEqual(m.window.last_sequence, 999)


if __name__ == "__main__":
    unittest.main()
