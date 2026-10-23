"""Unit tests for the read-only recovery configuration feasibility audit."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recovery_configuration_audit import CannotAudit, audit


def sensor(config: str = "0x00", divisor: str = "16384.0f") -> str:
    return (
        f"if (!configure(bus, imu_address_, 0x1C, {config})) return false;\n"
        f"sample.az = raw_az / {divisor};\n"
    )


def fsm(threshold: str = "2.5f", comparison: str = "std::fabs(az)") -> str:
    return (
        f"const float FlightStateMachine::LAUNCH_ACCEL_THRESHOLD = {threshold};\n"
        f"if ({comparison} > LAUNCH_ACCEL_THRESHOLD) {{ count++; }}\n"
    )


class RecoveryDetectabilityTests(unittest.TestCase):
    def test_current_two_g_configuration_cannot_cross_two_point_five_g(self):
        result = audit(sensor(), fsm())
        self.assertEqual(result["status"], "BLOCKED_UNREACHABLE_THRESHOLD")
        self.assertEqual(result["configured_full_scale_g"], 2)
        self.assertFalse(result["threshold_numerically_reachable"])
        self.assertFalse(result["recovery_qualified"])

    def test_consistent_four_g_configuration_only_clears_numeric_contradiction(self):
        result = audit(sensor("0x08", "8192.0f"), fsm())
        self.assertEqual(result["status"], "NUMERICALLY_REACHABLE_NOT_QUALIFIED")
        self.assertTrue(result["scale_matches_configuration"])
        self.assertFalse(result["recovery_qualified"])

    def test_range_change_without_conversion_change_is_blocked(self):
        result = audit(sensor("0x08", "16384.0f"), fsm())
        self.assertEqual(result["status"], "BLOCKED_SCALE_MISMATCH")
        self.assertFalse(result["scale_matches_configuration"])

    def test_strict_greater_than_equal_to_encoding_ceiling_is_unreachable(self):
        result = audit(sensor(), fsm("2.0f"))
        self.assertEqual(result["status"], "BLOCKED_UNREACHABLE_THRESHOLD")

    def test_low_threshold_is_still_not_qualified(self):
        result = audit(sensor(), fsm("1.5f"))
        self.assertEqual(result["status"], "NUMERICALLY_REACHABLE_NOT_QUALIFIED")
        self.assertFalse(result["recovery_qualified"])

    def test_unsupported_sensor_range_is_unknown_not_green(self):
        with self.assertRaises(CannotAudit):
            audit(sensor("0x40"), fsm())

    def test_unknown_source_shape_fails_closed(self):
        with self.assertRaises(CannotAudit):
            audit(sensor().replace("0x1C", "ACCEL_CONFIG"), fsm())

    def test_changed_comparator_cannot_be_silently_approved(self):
        with self.assertRaises(CannotAudit):
            audit(sensor(), fsm().replace(">", "<"))

    def test_multiple_ranges_fail_closed(self):
        with self.assertRaises(CannotAudit):
            audit(sensor() + sensor("0x08", "8192.0f"), fsm())


if __name__ == "__main__":
    unittest.main()
