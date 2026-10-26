"""Focused tests for the isolated JSON <-> R3 telemetry contract."""
from __future__ import annotations

import unittest
import json

from rf_lab.json_r3_contract import (
    ContractError,
    OfflineJsonR3Receiver,
    decode_json_telemetry,
    encode_json_telemetry,
)


def valid_sample(**overrides):
    record = {
        "time": 1001,
        "sample_time_ms": 1000,
        "sensor_valid": 1,
        "source_mode": "PHYSICAL",
        "pitch_raw": 2.0,
        "pitch_flt": 1.8,
        "roll_raw": -1.0,
        "roll_flt": -0.8,
        "yaw": 0.2,
        "alt": 12.3,
        "batt": 7.4,
        "auto": 0,
        "control_state": "IDLE",
        "chute": 0,
        "fstate": "IDLE",
    }
    record.update(overrides)
    return record


class JsonR3ContractTests(unittest.TestCase):
    def test_round_trip_preserves_units_and_distinct_times(self):
        datagram = encode_json_telemetry(valid_sample(), session_id=7, sequence=3)
        result = decode_json_telemetry(datagram, receive_time_ms=1200, replay_time_ms=50)
        self.assertEqual(result["timing"], {
            "sample_time_ms": 1000,
            "send_time_ms": 1001,
            "receive_time_ms": 1200,
            "replay_time_ms": 50,
        })
        self.assertEqual(result["yaw"], 0.2)  # gyro yaw rate, not heading
        self.assertEqual(result["source_identity"], "UNAUTHENTICATED")
        self.assertFalse(result["flight_control_authority"])

    def test_ground_station_replay_label_is_explicitly_normalized(self):
        datagram = encode_json_telemetry(
            valid_sample(source_mode="SIMULATION / OFFLINE REPLAY"),
            session_id=7,
            sequence=4,
        )
        result = decode_json_telemetry(datagram)
        self.assertEqual(result["source_mode"], "OFFLINE_REPLAY")

    def test_invalid_sensor_frame_has_no_fabricated_zeroes(self):
        source = valid_sample(
            sensor_valid=0,
            sensor_fault="imu_read",
            sample_time_ms=None,
        )
        for field in ("pitch_raw", "pitch_flt", "roll_raw", "roll_flt", "yaw", "alt"):
            source.pop(field)
        datagram = encode_json_telemetry(source, session_id=1, sequence=0)
        result = decode_json_telemetry(datagram)
        self.assertFalse(result["sensor_valid"])
        self.assertIsNone(result["sample_time_ms"])
        self.assertNotIn("pitch_raw", result)

    def test_invalid_sensor_frame_cannot_carry_attitude_values(self):
        source = valid_sample(sensor_valid=0, sensor_fault="imu_read")
        with self.assertRaises(ContractError) as ctx:
            encode_json_telemetry(source, session_id=1, sequence=0)
        self.assertEqual(ctx.exception.reason, "invalid_sample_must_omit:pitch_raw")

    def test_missing_valid_field_rejected(self):
        source = valid_sample()
        source.pop("roll_flt")
        with self.assertRaises(ContractError) as ctx:
            encode_json_telemetry(source, session_id=1, sequence=0)
        self.assertEqual(ctx.exception.reason, "missing_valid_sample_field:roll_flt")

    def test_control_fields_are_never_carried(self):
        source = valid_sample(command="arm")
        with self.assertRaises(ContractError) as ctx:
            encode_json_telemetry(source, session_id=1, sequence=0)
        self.assertTrue(ctx.exception.reason.startswith("control_field_forbidden:"))

    def test_oversized_application_payload_is_explicitly_rejected(self):
        source = valid_sample(control_state="X" * 32, fstate="Y" * 32)
        # Diagnostic fields are bounded, but the R3 payload budget remains a
        # contract boundary rather than an implicit truncation permission.
        source.update({
            "sensor_fault": "Z" * 32,
            "sensor_fault_latched": 1,
            "sensor_io_budget_expired": 1,
            "imu_address": 255,
            "imu_id": 255,
            "bmp_address": 255,
            "bmp_id": 255,
        })
        with self.assertRaises(ContractError) as ctx:
            encode_json_telemetry(source, session_id=1, sequence=0)
        self.assertEqual(ctx.exception.reason, "application_payload_exceeds_r3_budget")

    def test_receiver_rejects_duplicate_stale_and_session_change_without_mutation(self):
        receiver = OfflineJsonR3Receiver()
        first = encode_json_telemetry(valid_sample(), session_id=4, sequence=10)
        self.assertEqual(receiver.ingest(first, receive_time_ms=10)["status"],
                         "ACCEPT_UNAUTHENTICATED")
        duplicate = receiver.ingest(first, receive_time_ms=11)
        self.assertEqual(duplicate["status"], "REJECT_DUPLICATE")
        stale = receiver.ingest(
            encode_json_telemetry(valid_sample(time=999), session_id=4, sequence=9),
            receive_time_ms=12,
        )
        self.assertEqual(stale["status"], "REJECT_STALE_OR_OUT_OF_ORDER")
        session = receiver.ingest(
            encode_json_telemetry(valid_sample(time=1002), session_id=5, sequence=0),
            receive_time_ms=13,
        )
        self.assertEqual(session["status"], "REJECT_SESSION_CHANGED_UNTRUSTED")
        self.assertEqual((receiver.window.session_id, receiver.window.last_sequence), (4, 10))

    def test_receiver_rejects_corruption_and_missing_payload_before_window_change(self):
        receiver = OfflineJsonR3Receiver()
        valid = encode_json_telemetry(valid_sample(), session_id=3, sequence=1)
        broken = bytearray(valid)
        broken[-1] ^= 1
        self.assertTrue(receiver.ingest(bytes(broken))["status"].startswith("REJECT_crc_mismatch"))
        self.assertEqual((receiver.window.session_id, receiver.window.last_sequence), (None, None))
        malformed = encode_json_telemetry(valid_sample(), session_id=3, sequence=1)
        # The frame is valid R3, but its application schema is deliberately
        # invalid and must not bind a sequence window.
        from rf_lab.telemetry_frame import TelemetryFrame, encode_telemetry
        malformed = encode_telemetry(
            TelemetryFrame(3, 1, b'{"m":"PHYSICAL","ok":1,"t":1,"v":1}')
        )
        self.assertEqual(receiver.ingest(malformed)["status"],
                         "REJECT_missing_valid_sample_field:sample_time_ms")
        self.assertEqual((receiver.window.session_id, receiver.window.last_sequence), (None, None))

    def test_invalid_observation_clock_is_rejected_without_window_change(self):
        receiver = OfflineJsonR3Receiver()
        frame = encode_json_telemetry(valid_sample(), session_id=2, sequence=4)
        result = receiver.ingest(frame, receive_time_ms=-1)
        self.assertEqual(result["status"], "REJECT_receive_time_ms_must_be_nonnegative_integer")
        self.assertEqual((receiver.window.session_id, receiver.window.last_sequence), (None, None))

    def test_invalid_sample_timestamp_and_diagnostic_id_are_rejected(self):
        from rf_lab.telemetry_frame import TelemetryFrame, encode_telemetry

        bad_time_payload = json.dumps(
            {"e": "imu_read", "m": "PHYSICAL", "ok": 0, "s": "old", "t": 1, "v": 1},
            sort_keys=True, separators=(",", ":")
        ).encode("ascii")
        with self.assertRaises(ContractError) as time_error:
            decode_json_telemetry(encode_telemetry(TelemetryFrame(1, 0, bad_time_payload)))
        self.assertEqual(time_error.exception.reason, "sample_time_ms_must_be_nonnegative_integer")

        bad_id_payload = json.dumps(
            {"ba": 256, "e": "imu_read", "m": "PHYSICAL", "ok": 0, "t": 1, "v": 1},
            sort_keys=True, separators=(",", ":")
        ).encode("ascii")
        with self.assertRaises(ContractError) as id_error:
            decode_json_telemetry(encode_telemetry(TelemetryFrame(1, 1, bad_id_payload)))
        self.assertEqual(id_error.exception.reason, "bmp_address_out_of_range")


if __name__ == "__main__":
    unittest.main()
