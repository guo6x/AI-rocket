"""Real existing widgets, fake clock, and deny-all transports; no hardware I/O."""

import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import QObject, Signal, QThread

from core.data_logger import DataLogger
from core.offline_replay import OfflineReplay, SOURCE, load_timeline
from core.telemetry_parser import TelemetryParser
from ui import main_window


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


class View(QWidget):
    def __init__(self):
        super().__init__()
        self.update_attitude = Mock()


@pytest.fixture
def replay_window(monkeypatch, tmp_path):
    monkeypatch.setattr(main_window, "get_available_ports", lambda: [])
    monkeypatch.setattr(main_window, "DataLogger", lambda **_: DataLogger(str(tmp_path)))
    monkeypatch.setitem(sys.modules, "ui.view3d_widget", SimpleNamespace(Rocket3DWidget=View))
    clock = Clock()
    monkeypatch.setattr(main_window, "OfflineReplay", lambda parent: OfflineReplay(parent, clock=clock))
    transports = [Mock(side_effect=AssertionError("no offline transport construction")) for _ in range(2)]
    monkeypatch.setattr(main_window, "SerialReader", transports[0])
    monkeypatch.setattr(main_window, "UdpReader", transports[1])
    window = main_window.MainWindow()
    window.command_timer.stop()
    window.mode_combo.setCurrentIndex(2)
    yield window, clock, transports
    window.data_thread = None
    window.close()


def advance(window, clock, milliseconds):
    clock.now = milliseconds / 1000
    window.replay._tick()


def test_fixture_is_fixed_synthetic_telemetry_not_a_controller_or_command_log():
    document, digest = load_timeline()
    assert len(digest) == 64
    assert len(document["events"]) == 18
    assert sum(event["kind"] == "gap" for event in document["events"]) == 1
    assert all(isinstance(event.get("telemetry", {}), dict) for event in document["events"])
    assert document["source"] == SOURCE


def test_replay_real_parser_widgets_fault_gap_recovery_log_and_stop(replay_window):
    window, clock, transports = replay_window
    # Direct connection entry must route to replay BEFORE either transport.
    window.connect_data()
    log_path = window.data_logger.current_log_file
    assert window.connection_mode == "offline"
    assert window.data_thread is None
    advance(window, clock, 1500)
    assert len(window.plot_panel.history_time) == 4
    assert list(window.plot_panel.history_time) == [0, 0.5, 1, 1.5]
    assert window.dashboard.indicators["pitch_flt"].value_label.text() == "9.00"
    assert len(window.comparison_panel.time_q) == 4
    window.view3d_panel.update_attitude.assert_called_with(-6.0, 9.0, 0.0)
    advance(window, clock, 2500)
    assert len(window.plot_panel.history_time) == 4
    assert "SENSOR FAULT" in window.sensor_status_label.text()
    assert window.dashboard.indicators["pitch_flt"].value_label.text() == "9.00"
    advance(window, clock, 3500)
    assert len(window.plot_panel.history_time) == 6
    advance(window, clock, 6500)
    assert "INTERRUPTION" in window.sensor_status_label.text()
    assert len(window.plot_panel.history_time) == 6
    advance(window, clock, 7000)
    assert window.dashboard.isEnabled()
    assert window.plot_panel.history_time[-1] == 7.0
    assert window.dashboard.indicators["pitch_flt"].value_label.text() == "-12.00"
    advance(window, clock, 11000)
    assert window.replay.state == "FINISHED"
    assert len(window.plot_panel.history_time) == 15
    assert len(window.comparison_panel.time_q) == 15
    assert window.view3d_panel.update_attitude.call_count == 15
    assert window.data_logger.file_handle is None
    from pathlib import Path
    log = Path(log_path).read_text(encoding="utf-8")
    assert SOURCE in log and "fixture_sha256" in log
    assert "synthetic_imu_read" in log and "interruption" in log
    assert "FINISHED" in log and ",RAW," in log and ",DICT," in log
    window.stop_replay()
    advance(window, clock, 20000)
    assert len(window.plot_panel.history_time) == 15
    assert all(not transport.called for transport in transports)


def test_pause_resume_restart_and_stop_do_not_advance_or_append_old_session(replay_window):
    window, clock, _ = replay_window
    window.start_replay()
    advance(window, clock, 1000)
    first_log = window.data_logger.current_log_file
    window.pause_replay()
    count = len(window.plot_panel.history_time)
    advance(window, clock, 6000)
    assert len(window.plot_panel.history_time) == count
    assert window.replay.state == "PAUSED"
    window.start_replay()
    advance(window, clock, 6500)
    assert window.plot_panel.history_time[-1] == 1.5
    window.restart_replay()
    assert list(window.plot_panel.history_time) == [0]
    assert first_log != window.data_logger.current_log_file
    window.stop_replay()
    advance(window, clock, 20000)
    assert list(window.plot_panel.history_time) == [0]


@pytest.mark.parametrize("command", ["arm", "auto_on", "set_servo:90,90", "deploy_chute", "estop", "reset", "anything"])
def test_offline_rejects_commands_in_actual_sender_even_with_injected_live_transport(replay_window, command):
    window, _, _ = replay_window
    transport = SimpleNamespace(is_running=True, send=Mock(return_value=True))
    window.data_thread = transport
    window.on_send_command(command)
    transport.send.assert_not_called()
    assert not window.command_tracker.pending
    assert "read-only offline" in window.command_panel.command_status_label.text()


def test_mode_switch_stops_replay_closes_log_and_clears_partial_parser(replay_window):
    window, clock, _ = replay_window
    window.start_replay()
    replay = window.replay
    window.parser.parse('{"incomplete":')
    window.mode_combo.setCurrentIndex(1)
    assert replay.state == "STOPPED"
    assert not replay.timer.isActive()
    assert window.replay is None and window.data_thread is None
    assert window.data_logger.file_handle is None
    assert window.command_panel.isEnabled()
    assert window.parser.buffer == ""


def test_old_input_callbacks_cannot_mutate_new_session_and_no_live_value_leaks(replay_window):
    window, _, _ = replay_window

    class OldInput(QObject):
        data = Signal(str)
        error = Signal(str)
        state = Signal(str)

    old = OldInput()
    window.bind_session_signal(old.data, window.on_data_received)
    window.bind_session_signal(old.error, window.on_error)
    window.bind_session_signal(old.state, window.on_link_state_changed)
    window.dashboard.update_indicators({"batt": 7.4})
    window.start_replay()
    assert window.dashboard.indicators["batt"].value_label.text() == "unavailable"
    before = list(window.plot_panel.history_time)
    old.data.emit('{"sensor_valid":1,"alt":99,"pitch_flt":99}')
    old.error.emit("stale error")
    old.state.emit("DISCONNECTED")
    assert window.connection_mode == "offline"
    assert window.replay.state == "RUNNING"
    assert list(window.plot_panel.history_time) == before
    assert "OFFLINE RUNNING" in window.command_panel.link_status_label.text()


def test_worker_callbacks_remain_on_gui_thread_without_transport_io(replay_window):
    import time
    window, _, _ = replay_window

    class Worker(QThread):
        text = Signal(str)
        response = Signal(str, object)
        notification = Signal()

        def run(self):
            self.text.emit("sample")
            self.response.emit("ACK estop", ("192.0.2.1", 9876))
            self.notification.emit()

    worker = Worker()
    calls = []

    def record(*args):
        calls.append((QThread.currentThread(), args))

    window.bind_session_signal(worker.text, record)
    window.bind_session_signal(worker.response, record, response=True)
    window.bind_session_signal(worker.notification, record, notification=True)
    worker.start()
    assert worker.wait(2000)
    app = QApplication.instance()
    deadline = time.monotonic() + 2
    while len(calls) < 3 and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.001)
    assert len(calls) == 3
    assert all(thread == app.thread() for thread, _ in calls)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "bad", None, 10**400])
def test_invalid_numeric_data_freezes_widgets_without_fabricated_zero(replay_window, bad):
    window, _, _ = replay_window
    window.on_data_received(json.dumps({"sensor_valid": 1, "alt": bad, "pitch_flt": 1.0}))
    assert not window.plot_panel.history_time
    assert "invalid/missing numeric" in window.sensor_status_label.text()


def test_missing_numeric_data_is_not_a_zero_sample_and_gyro_is_not_heading(replay_window):
    window, _, _ = replay_window
    window.on_data_received('{"sensor_valid":1}')
    assert not window.plot_panel.history_time
    window.on_data_received('{"sensor_valid":1,"alt":2,"pitch_flt":3,"roll_flt":4,"yaw":100}')
    window.view3d_panel.update_attitude.assert_called_with(4, 3, 0.0)


def test_parser_incomplete_buffer_and_ui_text_are_bounded_and_recover(replay_window):
    window, _, _ = replay_window
    parser = TelemetryParser()
    parser.parse('{"partial":' + " " * parser.MAX_BUFFER_CHARS)
    assert parser.buffer == "" and parser.overlong_buffers_rejected == 1
    assert parser.parse('{"alt":1}') == [{"alt": 1}]
    for index in range(2300):
        window.log_message(f"<b>raw data {index}</b>")
    assert window.log_display.document().blockCount() <= 2000
    assert "<b>raw data 2299</b>" in window.log_display.toPlainText()


def test_3d_update_failure_is_visible_not_silently_ignored(replay_window):
    window, _, _ = replay_window
    window.view3d_panel.update_attitude.side_effect = RuntimeError("synthetic GL failure")
    window.on_data_received('{"sensor_valid":1,"alt":2,"pitch_flt":3,"roll_flt":4}')
    assert "DEGRADED" in window.view3d_status_label.text()
    assert "synthetic GL failure" in window.view3d_status_label.text()


def test_partial_axis_or_comparison_data_never_generates_missing_zero_values(replay_window):
    window, _, _ = replay_window
    window.on_data_received('{"sensor_valid":1,"alt":2,"pitch_flt":3}')
    assert not window.plot_panel.history_time
    window.view3d_panel.update_attitude.assert_not_called()
    window.on_data_received('{"sensor_valid":1,"alt":2,"pitch_flt":3,"roll_flt":4,"pitch_raw":5}')
    assert len(window.plot_panel.history_time) == 1
    assert not window.comparison_panel.time_q
    window.view3d_panel.update_attitude.assert_called_once_with(4, 3, 0.0)


def test_claimed_valid_but_incomplete_sample_cannot_clear_prior_fault_for_legacy_data(replay_window):
    window, _, _ = replay_window
    window.on_data_received('{"sensor_valid":0,"sensor_fault":"imu_read"}')
    window.on_data_received('{"sensor_valid":1}')
    assert window.sensor_fault_active
    window.on_data_received('{"alt":2,"pitch_flt":3,"roll_flt":4}')
    assert window.sensor_fault_active
    assert not window.plot_panel.history_time
    window.on_data_received('{"sensor_valid":1,"alt":2,"pitch_flt":3,"roll_flt":4}')
    assert not window.sensor_fault_active
    assert len(window.plot_panel.history_time) == 1
