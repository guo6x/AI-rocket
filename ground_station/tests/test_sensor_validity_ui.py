"""Offscreen sensor-state propagation; no device, socket or actuator is opened."""

import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt

from ui import main_window


class FakeLogger:
    def __init__(self, **_kwargs):
        self.entries = []

    def log(self, value):
        self.entries.append(value)

    def start_logging(self):
        pass

    def stop_logging(self):
        pass


class FakeView3D(QWidget):
    def __init__(self):
        super().__init__()
        self.update_attitude = Mock()


@pytest.fixture
def window(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(main_window, "get_available_ports", lambda: [])
    monkeypatch.setattr(main_window, "DataLogger", FakeLogger)
    monkeypatch.setitem(sys.modules, "ui.view3d_widget", SimpleNamespace(Rocket3DWidget=FakeView3D))
    instance = main_window.MainWindow()
    instance.command_timer.stop()
    instance.dashboard.update_indicators = Mock()
    instance.plot_panel.update_plot = Mock()
    instance.comparison_panel.update_plot = Mock()
    yield instance
    instance.data_thread = None
    instance.close()
    app.processEvents()


def valid_frame(**overrides):
    frame = {
        "time": 1000, "sensor_valid": 1, "sensor_fault": "valid",
        "alt": 12.3, "pitch_raw": 2.0, "pitch_flt": 1.5,
        "roll_raw": 3.0, "roll_flt": 2.5, "yaw": 0.1,
    }
    frame.update(overrides)
    return frame


@pytest.mark.parametrize("flag", [False, 0])
def test_explicit_sensor_fault_never_sends_default_zero_values_to_visuals(window, flag):
    frame = {"time": 1100, "sensor_valid": flag, "sensor_fault": "imu_read"}
    raw = json.dumps(frame)
    window.on_data_received(raw)

    window.dashboard.update_indicators.assert_not_called()
    window.plot_panel.update_plot.assert_not_called()
    window.comparison_panel.update_plot.assert_not_called()
    window.view3d_panel.update_attitude.assert_not_called()
    assert "SENSOR FAULT" in window.sensor_status_label.text()
    assert "imu_read" in window.sensor_status_label.text()
    assert "frozen" in window.sensor_status_label.text().lower()
    assert not window.dashboard.isEnabled()
    assert not window.tab_widget.isEnabled()
    assert frame in window.data_logger.entries
    assert raw in window.data_logger.entries


@pytest.mark.parametrize("flag", [None, "0", "1", "false", "true", 0.0, 1.0, 2, -1, [], {}])
def test_malformed_sensor_valid_flag_fails_closed_without_traceback(window, flag):
    frame = valid_frame(sensor_valid=flag)
    window.on_data_received(json.dumps(frame))

    assert "SENSOR FAULT" in window.sensor_status_label.text()
    assert "invalid sensor_valid flag" in window.sensor_status_label.text()
    window.dashboard.update_indicators.assert_not_called()
    window.plot_panel.update_plot.assert_not_called()
    window.view3d_panel.update_attitude.assert_not_called()
    assert frame in window.data_logger.entries


def test_fault_after_valid_sample_freezes_last_visuals_not_a_false_zero_sample(window):
    window.on_data_received(json.dumps(valid_frame()))
    window.on_data_received(json.dumps({"sensor_valid": 0, "sensor_fault": "bmp_read", "time": 2000}))

    assert window.dashboard.update_indicators.call_count == 1
    assert window.plot_panel.update_plot.call_count == 1
    assert window.comparison_panel.update_plot.call_count == 1
    assert window.view3d_panel.update_attitude.call_count == 1
    assert "bmp_read" in window.sensor_status_label.text()
    assert not window.dashboard.isEnabled()
    assert not window.tab_widget.isEnabled()


@pytest.mark.parametrize("flag", [True, 1])
def test_explicit_valid_sample_restores_display_without_sending_any_command(window, flag):
    transport = SimpleNamespace(is_running=True, send=Mock(return_value=True))
    window.data_thread = transport
    window.on_data_received(json.dumps({"sensor_valid": 0, "sensor_fault": "imu_identity"}))
    frame = valid_frame(sensor_valid=flag)
    window.on_data_received(json.dumps(frame))

    assert "SENSOR: valid sample reported" in window.sensor_status_label.text()
    assert window.dashboard.isEnabled()
    assert window.tab_widget.isEnabled()
    window.dashboard.update_indicators.assert_called_once_with(frame)
    window.plot_panel.update_plot.assert_called_once()
    window.view3d_panel.update_attitude.assert_called_once()
    transport.send.assert_not_called()
    assert not window.command_tracker.pending


def test_legacy_frames_without_validity_flag_remain_supported_as_unverified(window):
    frame = valid_frame()
    del frame["sensor_valid"]
    window.on_data_received(json.dumps(frame))

    assert "legacy" in window.sensor_status_label.text().lower()
    assert "unverified" in window.sensor_status_label.text().lower()
    window.dashboard.update_indicators.assert_called_once_with(frame)
    window.plot_panel.update_plot.assert_called_once()


def test_missing_legacy_flag_cannot_clear_an_explicit_current_sensor_fault(window):
    window.on_data_received(json.dumps({"sensor_valid": 0, "sensor_fault": "config_readback"}))
    legacy = valid_frame()
    del legacy["sensor_valid"]
    window.on_data_received(json.dumps(legacy))

    assert "SENSOR FAULT" in window.sensor_status_label.text()
    assert "config_readback" in window.sensor_status_label.text()
    window.plot_panel.update_plot.assert_not_called()
    window.dashboard.update_indicators.assert_not_called()
    assert legacy in window.data_logger.entries


def test_udp_activity_cannot_overwrite_independent_sensor_fault_indicator(window):
    window.connection_mode = "udp"
    window.on_data_received(json.dumps({"sensor_valid": 0, "sensor_fault": "bmp_identity"}))
    window.on_data_received("[ESP] still receiving")

    assert "SENSOR FAULT" in window.sensor_status_label.text()
    assert "bmp_identity" in window.sensor_status_label.text()
    assert "UDP ACTIVE" in window.command_panel.link_status_label.text()


def test_fault_status_is_plain_text_not_html_and_preserves_original_log(window):
    reason = "<b>imu_read</b>"
    raw = json.dumps({"sensor_valid": 0, "sensor_fault": reason})
    window.on_data_received(raw)

    assert reason in window.sensor_status_label.text()
    assert window.sensor_status_label.textFormat() == Qt.PlainText
    assert raw in window.data_logger.entries
    assert "SENSOR FAULT" in window.sensor_status_label.text()


def test_fault_does_not_resolve_pending_command_or_manufacture_ack(window):
    window.command_tracker.mark_sent("arm")
    window.on_data_received(json.dumps({"sensor_valid": 0, "sensor_fault": "imu_sample"}))
    assert window.command_tracker.pending


def test_disconnect_marks_sensor_visuals_unavailable(window):
    window.on_data_received(json.dumps(valid_frame()))
    window.disconnect_data()

    assert "unavailable" in window.sensor_status_label.text().lower()
    assert not window.dashboard.isEnabled()
    assert not window.tab_widget.isEnabled()
