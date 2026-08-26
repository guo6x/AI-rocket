from PySide6.QtWidgets import QApplication

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
