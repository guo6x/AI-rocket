import pytest
from PySide6.QtWidgets import QApplication

from core.command_link import CommandTracker, command_name, parse_command_response
from core.serial_reader import SerialReader
from ui.command_panel import CommandPanel


def test_plaintext_command_names_and_response_vocabulary():
    assert command_name("arm") == "arm"
    assert command_name("set_servo:90,90") == "set_servo"
    assert parse_command_response("ACK set_servo").status == "ACKNOWLEDGED"
    nack = parse_command_response("NACK out_of_range set_servo")
    assert nack.status == "NACK"
    assert nack.detail == "out_of_range"
    assert parse_command_response("ACK set_servo extra") is None


def test_tracker_distinguishes_sent_acknowledged_nack_and_timeout():
    tracker = CommandTracker(timeout_seconds=1.0)
    sent = tracker.mark_sent("arm", now=10.0)
    assert sent.status == "SENT"
    assert tracker.expire(now=10.9) is None
    acknowledged = tracker.resolve("ACK arm")
    assert acknowledged.status == "ACKNOWLEDGED"
    assert not tracker.pending

    tracker.mark_sent("auto_on", now=20.0)
    nack = tracker.resolve("NACK invalid_state auto_on")
    assert nack.status == "NACK"
    assert nack.detail == "invalid_state"

    tracker.mark_sent("set_servo:90,90", now=30.0)
    timeout = tracker.expire(now=31.0)
    assert timeout.status == "TIMEOUT"
    assert not tracker.pending


def test_tracker_rejects_ambiguous_parallel_ack_waits():
    tracker = CommandTracker()
    tracker.mark_sent("arm", now=0.0)
    with pytest.raises(RuntimeError):
        tracker.mark_sent("auto_on", now=0.1)
    assert tracker.resolve("ACK unrelated") is None
    assert tracker.pending
    cancelled = tracker.cancel_pending("superseded by ESTOP")
    assert cancelled.command == "arm"
    assert not tracker.pending


class FakeSerialPort:
    is_open = True

    def __init__(self):
        self.writes = []

    def write(self, payload):
        self.writes.append(payload)


def test_serial_mode_uses_plaintext_line_protocol():
    reader = SerialReader("TEST")
    reader.serial_port = FakeSerialPort()
    assert reader.send("set_pid:1.0,0.1,0.3") is True
    assert reader.serial_port.writes == [b"set_pid:1.0,0.1,0.3\n"]


def test_command_and_link_status_are_visible_and_estop_stays_available():
    app = QApplication.instance() or QApplication([])
    panel = CommandPanel()
    panel.set_link_state("TELEMETRY LOST")
    panel.set_command_status("TIMEOUT", "arm", "no ACK/NACK received")
    assert panel.link_status_label.text() == "LINK: TELEMETRY LOST"
    assert "COMMAND: TIMEOUT arm" in panel.command_status_label.text()
    assert panel.estop_btn.isEnabled()
    panel.close()
    app.processEvents()



@pytest.mark.parametrize(
    ("response", "expected_command", "expected_reason"),
    [
        ("NACK sensor_invalid arm", "arm", "sensor_invalid"),
        ("NACK sensor_invalid auto_on", "auto_on", "sensor_invalid"),
        ("NACK sensor_invalid set_servo", "set_servo", "sensor_invalid"),
        ("NACK recovery_disabled deploy_chute", "deploy_chute", "recovery_disabled"),
    ],
)
def test_current_firmware_rejection_reasons_parse_as_nack(
    response, expected_command, expected_reason
):
    result = parse_command_response(response)
    assert result is not None
    assert result.status == "NACK"
    assert result.command == expected_command
    assert result.detail == expected_reason


@pytest.mark.parametrize(
    "malformed",
    [
        "NACK unrecognized_reason arm",
        "NACK recovery_disabled",
        "NACK sensor_invalid arm extra",
        "NACK sensor_invalid arm\nauto_on",
        "NACK sensor_invalid  arm",
        "ACKNOWLEDGED arm",
        '{"time":1}',
    ],
)
def test_invalid_or_unknown_responses_do_not_resolve_pending_command(malformed):
    tracker = CommandTracker(timeout_seconds=1.0)
    tracker.mark_sent("arm", now=10.0)
    assert parse_command_response(malformed) is None
    assert tracker.resolve(malformed) is None
    assert tracker.pending
    assert tracker.expire(now=11.0).status == "TIMEOUT"


def test_matching_firmware_rejection_is_terminal_nack_not_timeout():
    tracker = CommandTracker(timeout_seconds=1.0)
    tracker.mark_sent("arm", now=10.0)
    result = tracker.resolve("NACK sensor_invalid arm")
    assert result is not None
    assert result.status == "NACK"
    assert result.detail == "sensor_invalid"
    assert result.command == "arm"
    assert tracker.expire(now=12.0) is None


def test_nack_for_other_command_does_not_resolve_pending_command():
    tracker = CommandTracker(timeout_seconds=1.0)
    tracker.mark_sent("arm", now=10.0)
    assert tracker.resolve("NACK recovery_disabled deploy_chute") is None
    assert tracker.pending
    result = tracker.resolve("NACK sensor_invalid arm")
    assert result is not None
    assert result.status == "NACK"
    assert not tracker.pending
