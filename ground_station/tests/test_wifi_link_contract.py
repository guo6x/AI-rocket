from pathlib import Path

from core.udp_reader import UdpReader
from ui.command_panel import CommandPanel


ROOT = Path(__file__).resolve().parents[2]


class FakeSocket:
    def __init__(self):
        self.sent = []

    def sendto(self, payload, target):
        self.sent.append((payload, target))


def test_udp_send_requires_an_explicit_target():
    reader = UdpReader()
    reader.sock = FakeSocket()

    reader.send("arm")
    assert reader.sock.sent == []

    reader.send("arm", ("192.0.2.1", 9876))
    assert reader.sock.sent == [(b"arm", ("192.0.2.1", 9876))]


def test_current_wifi_downlink_is_explicitly_incomplete():
    esp_source = (ROOT / "esp8266_firmware" / "src" / "main.cpp").read_text(encoding="utf-8")
    ui_source = (ROOT / "ground_station" / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert "udp.parsePacket" not in esp_source
    assert "self.data_thread.send(cmd_json)" in ui_source


def test_chute_command_is_not_a_confirmation_bypassing_quick_action():
    commands = {command for _, command in CommandPanel.DEFAULT_QUICK_BUTTONS}
    assert "deploy_chute" not in commands
