"""Run the real Ground Station event loop and save attributable offline evidence.

No desktop impersonation or image generation: PNGs come from QWidget.grab()
and the application's actual OpenGL framebuffer. Device/socket creation is
denied. The optional finite soak measures this host only, not flight fitness.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import tracemalloc
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ground_station"))
import main as launcher  # noqa: E402
from core.data_logger import DataLogger  # noqa: E402
from core.offline_replay import FIXTURE, SOURCE  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def current_rss():
    if sys.platform != "win32":
        return None
    # Process-local memory observation, not Windows UI automation.
    import ctypes
    from ctypes import wintypes

    class MemoryCounters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in (
                "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage",
            )
        ]
    counters = MemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return None
    return counters.WorkingSetSize


class RuntimeAcceptance:
    def __init__(self, app, output, soak_samples):
        self.app, self.output, self.soak_samples = app, output, soak_samples
        self.window = MainWindow()
        self.window.data_logger = DataLogger(str(output / "telemetry"))
        self.window.resize(1360, 980)
        self.window.show()
        self.started = time.monotonic()
        self.stage = "BOOT"
        self.flags = set()
        self.pause_at = None
        self.soak_index = 0
        self.soak_input_hash = hashlib.sha256()
        self.result = {
            "status": "RUNNING", "assertions": [], "snapshots": [], "memory": [],
            "boundary": {"synthetic_only": True, "hardware_verified": False,
                         "source_authenticated": False, "hardware_connections": 0,
                         "radio_transmissions": 0, "control_sends": 0},
        }
        self.timer = QTimer()
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def check(self, condition, name):
        if not condition:
            raise AssertionError(name)
        self.result["assertions"].append(name)

    def screenshot(self, name):
        path = self.output / (name + ".png")
        self.check(self.window.grab().save(str(path)), "save " + name)
        self.result["snapshots"].append({"path": path.name, "sha256": digest(path)})

    def tick(self):
        try:
            self._tick()
        except Exception as error:
            self.result["status"] = "FAIL"
            self.result["error"] = repr(error)
            import traceback
            self.result["traceback"] = traceback.format_exc()
            self.finish()

    def _tick(self):
        window = self.window
        if time.monotonic() - self.started > max(60, self.soak_samples * 0.1 + 60):
            raise TimeoutError("runtime acceptance watchdog")
        if self.stage == "BOOT":
            if time.monotonic() - self.started < 0.6:
                return
            self.check(window.isVisible() and window.data_thread is None, "actual window starts with no device")
            self.screenshot("01_no_device")
            window.mode_combo.setCurrentIndex(1)
            self.screenshot("02_udp_settings_no_connection")
            window.mode_combo.setCurrentIndex(2)
            window.start_replay()
            self.stage = "DEMO"
        if self.stage == "DEMO":
            replay = window.replay
            elapsed = replay.elapsed_ms
            if elapsed >= 1100 and "plots" not in self.flags:
                self.check(len(window.plot_panel.history_time) >= 3, "real parser to dashboard and curves")
                self.screenshot("03_replay_curves")
                window.tab_widget.setCurrentIndex(1)
                self.flags.add("plots")
            if elapsed >= 1550 and "pause" not in self.flags:
                window.pause_replay()
                self.pause_at = time.monotonic()
                self.pause_position = replay.position
                self.screenshot("04_paused")
                self.flags.add("pause")
            if replay.state == "PAUSED" and time.monotonic() - self.pause_at > 0.4:
                self.check(replay.position == self.pause_position, "pause retains cursor without receiving")
                window.start_replay()
            if elapsed >= 2600 and "fault" not in self.flags:
                self.check("SENSOR FAULT" in window.sensor_status_label.text(), "sensor fault visibly freezes last sample")
                self.check(window.dashboard.indicators["pitch_flt"].value_label.text() == "9.00", "fault creates no zero attitude")
                self.screenshot("05_sensor_fault")
                self.flags.add("fault")
            if elapsed >= 3650 and "compare" not in self.flags:
                self.screenshot("06_raw_filtered_recovered")
                self.flags.add("compare")
            if elapsed >= 4500 and "gap" not in self.flags:
                self.check("INTERRUPTION" in window.sensor_status_label.text(), "data interruption visibly freezes")
                self.screenshot("07_interruption")
                self.flags.add("gap")
            if elapsed >= 7400 and "3d_selected" not in self.flags:
                if window.view3d_panel is not None:
                    window.tab_widget.setCurrentWidget(window.view3d_panel)
                self.flags.add("3d_selected")
            if elapsed >= 8100 and "3d" not in self.flags:
                window.poll_link_and_command_state()
                gl_view = getattr(window.view3d_panel, "gl_view", None)
                valid = gl_view is not None and gl_view.isValid() and gl_view.render_ok and not gl_view.render_error
                self.result["opengl"] = {"status": "PASS" if valid else "NOT_VERIFIED",
                                         "context_valid": gl_view is not None and gl_view.isValid(),
                                         "successful_paint": gl_view is not None and gl_view.render_ok,
                                         "ui_status": window.view3d_status_label.text(),
                                         "model": "existing arbitrary-unit box, NOT engineering CAD; yaw unavailable"}
                if valid:
                    try:
                        framebuffer = gl_view.grabFramebuffer()
                        if gl_view.render_error or framebuffer.isNull():
                            raise RuntimeError(gl_view.render_error or "empty GL framebuffer")
                        path = self.output / "08_gl_framebuffer.png"
                        self.check(framebuffer.save(str(path)), "save actual GL framebuffer")
                        self.result["snapshots"].append({"path": path.name, "sha256": digest(path)})
                        self.result["opengl"]["size"] = [framebuffer.width(), framebuffer.height()]
                    except Exception as error:
                        window.on_3d_failed(str(error))
                        self.result["opengl"].update(status="NOT_VERIFIED", error=repr(error))
                self.result["opengl"]["ui_status"] = window.view3d_status_label.text()
                self.screenshot("08_3d_or_explicit_degradation")
                self.flags.add("3d")
            if replay.state == "FINISHED":
                self.check(len(window.plot_panel.history_time) == 15, "15 valid samples, 2 faults and one gap, no fake zeros")
                self.check(len(window.comparison_panel.time_q) == 15, "original four comparison curves updated")
                self.check(window.data_logger.file_handle is None, "natural completion closes log")
                log_path = Path(window.data_logger.current_log_file)
                text = log_path.read_text(encoding="utf-8")
                self.check(all(part in text for part in (SOURCE, "fixture_sha256", ",RAW,", ",DICT,", "FINISHED")), "raw and parsed replay log saved with provenance")
                self.result["demo_log"] = {"path": str(log_path.relative_to(self.output)), "sha256": digest(log_path)}
                self.screenshot("09_finished")
                window.restart_replay()
                self.check(list(window.plot_panel.history_time) == [0], "restart resets time axis and old session")
                window.stop_replay()
                self.check(not window.replay.timer.isActive(), "stop terminates replay input timer")
                for command in ("arm", "auto_on", "set_servo:90,90", "deploy_chute", "estop", "reset"):
                    window.on_send_command(command)
                    self.check("read-only offline" in window.command_panel.command_status_label.text(), "sender rejects " + command)
                window.disconnect_data()
                window.connection_mode = "offline"
                window.replay_status_label.setText("SOAK — synthetic harness input, no transport or commands")
                window.tab_widget.setCurrentIndex(0)
                window.data_logger.start_logging()
                window.data_logger.log({"source_mode": SOURCE, "experiment": "finite deterministic UI soak", "samples": self.soak_samples})
                self.soak_started = time.monotonic()
                tracemalloc.start()
                self.stage = "SOAK"
        elif self.stage == "SOAK":
            index = self.soak_index
            sample = {"source_mode": SOURCE, "replay_time_ms": index * 20, "time": index * 20,
                      "sensor_valid": 1, "alt": (index % 101) / 10,
                      "pitch_raw": (index % 21) - 10, "pitch_flt": (index % 21) - 10.25,
                      "roll_raw": (index % 11) - 5, "roll_flt": (index % 11) - 5.25,
                      "yaw": 0, "auto": 0, "fstate": "IDLE"}
            raw = json.dumps(sample, sort_keys=True, separators=(",", ":"))
            self.soak_input_hash.update((raw + "\n").encode())
            window.on_data_received(raw)
            self.soak_index += 1
            if self.soak_index % 500 == 0:
                current, peak = tracemalloc.get_traced_memory()
                observation = {"samples": self.soak_index, "wall_seconds": round(time.monotonic() - self.soak_started, 3),
                               "python_current_bytes": current, "python_peak_bytes": peak, "rss_bytes": current_rss(),
                               "plot_points": len(window.plot_panel.history_time), "comparison_points": len(window.comparison_panel.time_q),
                               "text_blocks": window.log_display.document().blockCount(), "parser_chars": len(window.parser.buffer)}
                self.result["memory"].append(observation)
                print(json.dumps(observation), flush=True)
            if self.soak_index >= self.soak_samples:
                self.check(len(window.plot_panel.history_time) <= 1000 and len(window.comparison_panel.time_q) <= 1000, "plot buffers bounded after finite soak")
                self.check(window.log_display.document().blockCount() <= 2000, "UI log bounded after finite soak")
                self.result["soak"] = {"samples": self.soak_index, "synthetic_sample_spacing_ms": 20,
                                       "wall_seconds": round(time.monotonic() - self.soak_started, 3),
                                       "input_sha256": self.soak_input_hash.hexdigest(),
                                       "long_duration_claim": "PARTIALLY_VERIFIED: finite host observation, not multi-hour endurance or leak-freedom proof"}
                self.screenshot("10_finite_soak")
                self.result["status"] = "PASS" if self.result["opengl"]["status"] == "PASS" else "PARTIALLY_VERIFIED"
                self.finish()

    def finish(self):
        self.timer.stop()
        self.window.close()
        self.app.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--soak-samples", type=int, default=4500)
    args = parser.parse_args()
    if args.soak_samples < 1500:
        parser.error("soak must exceed the existing plot/text buffer ceilings")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)  # preserve historical runs
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    source_status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).splitlines()

    def deny_io(*_args, **_kwargs):
        raise AssertionError("runtime acceptance prohibits all device/socket connections")

    # This is the real app with its original widgets and event loop, not a fake
    # screenshot. Only external I/O boundaries are replaced with deny-all stubs.
    with patch("serial.Serial", deny_io), patch("socket.socket", deny_io), patch("ui.main_window.get_available_ports", lambda: []):
        app = launcher.create_application(["SYSTEM-V1 runtime acceptance"])
        acceptance = RuntimeAcceptance(app, output, args.soak_samples)
        qt_exit = app.exec()
    result = acceptance.result
    result["qt_exit_code"] = qt_exit
    result["source_git_sha"] = source_sha
    result["source_git_status_at_start"] = source_status
    result["source_hashes"] = {
        str(path.relative_to(ROOT)): digest(path)
        for path in sorted((ROOT / "ground_station").rglob("*.py"))
        if "__pycache__" not in path.parts
    }
    result["source_hashes"]["scripts/system_v1_runtime.py"] = digest(__file__)
    result["fixture_sha256"] = digest(FIXTURE)
    result["environment"] = {"python": sys.version, "platform": platform.platform(), "qt_platform": os.environ.get("QT_QPA_PLATFORM", "desktop-default"),
                             "dependencies": {name: importlib.metadata.version(name) for name in ("PySide6", "shiboken6", "pyqtgraph", "numpy", "pyserial", "PyOpenGL")}}
    result["command"] = subprocess.list2cmdline([sys.executable, *sys.argv])
    result["result_sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    (output / "runtime_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "qt_exit_code": qt_exit, "assertions": len(result["assertions"]), "output": str(output)}, ensure_ascii=False), flush=True)
    # All application widgets are closed while the QApplication is still live.
    app.processEvents()
    return 0 if result["status"] in {"PASS", "PARTIALLY_VERIFIED"} and qt_exit == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
