from PySide6.QtWidgets import QApplication

from core.udp_reader import UdpReader
from ui.main_window import MainWindow


class FakeConnectedTransport:
    is_running = True

    def __init__(self):
        self.sent = []

    def send(self, command):
        self.sent.append(command)
        return True


def test_main_window_never_promotes_sent_to_ack_without_response():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    transport = FakeConnectedTransport()
    window.data_thread = transport

    window.on_send_command("arm")
    assert transport.sent == ["arm"]
    assert window.command_tracker.pending
    assert "COMMAND: SENT arm" in window.command_panel.command_status_label.text()

    window.on_data_received("ACK arm")
    assert not window.command_tracker.pending
    assert "COMMAND: ACKNOWLEDGED arm" in window.command_panel.command_status_label.text()

    window.data_thread = None
    window.close()
    app.processEvents()


def test_main_window_ignores_udp_response_from_wrong_source():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    transport = UdpReader(target_addr=("192.0.2.10", 9876))
    transport.is_running = True
    window.data_thread = transport

    window.command_tracker.mark_sent("arm")
    window.on_udp_command_response("ACK arm", ("192.0.2.11", 9876))
    assert window.command_tracker.pending
    assert "Spurious UDP response" in window.log_display.toPlainText()

    window.on_udp_command_response("ACK arm", ("192.0.2.10", 9876))
    assert not window.command_tracker.pending
    assert "COMMAND: ACKNOWLEDGED arm" in window.command_panel.command_status_label.text()

    transport.is_running = False
    window.data_thread = None
    window.close()
    app.processEvents()
