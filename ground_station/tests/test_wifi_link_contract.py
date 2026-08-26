import socket
import threading
import time

from PySide6.QtCore import QCoreApplication

from core.command_link import CommandTracker, parse_command_response
from core.udp_reader import UdpReader
from ui.command_panel import CommandPanel


class FakeSocket:
    def __init__(self):
        self.sent = []

    def sendto(self, payload, target):
        self.sent.append((payload, target))


def free_udp_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def wait_for(predicate, timeout=3.0):
    app = QCoreApplication.instance() or QCoreApplication([])
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    return predicate()


def test_udp_send_requires_explicit_valid_unicast_target():
    reader = UdpReader()
    reader.sock = FakeSocket()
    assert reader.send("arm") is False

    reader.target_addr = ("255.255.255.255", 9876)
    assert reader.send("arm") is False

    reader.target_addr = ("192.0.2.1", 9876)
    assert reader.send("arm") is True
    assert reader.sock.sent == [(b"arm", ("192.0.2.1", 9876))]


def test_udp_send_rejects_ambiguous_command_boundaries():
    reader = UdpReader(target_addr=("192.0.2.1", 9876))
    reader.sock = FakeSocket()
    assert reader.send("") is False
    assert reader.send("arm\nestop") is False
    assert reader.send("x" * 129) is False
    assert reader.sock.sent == []


class SimulatedEspStmBridge:
    """Behavioral socket bridge for command ACK and telemetry return paths."""

    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", port))
        self.received = []
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.thread.start()

    def run(self):
        payload, source = self.sock.recvfrom(512)
        command = payload.decode("utf-8")
        self.received.append(command)
        response = b"ACK arm" if command == "arm" else b"NACK unknown_command unknown"
        self.sock.sendto(response, source)
        self.sock.sendto(b'{"time":1,"alt":2.5}', source)

    def close(self):
        self.thread.join(timeout=2.0)
        self.sock.close()


def test_simulated_ground_to_esp_to_stm_ack_and_telemetry_return():
    listen_port = free_udp_port()
    command_port = free_udp_port()
    bridge = SimulatedEspStmBridge(command_port)
    bridge.start()

    received = []
    reader = UdpReader(
        host="127.0.0.1",
        port=listen_port,
        target_addr=("127.0.0.1", command_port),
    )
    reader.data_received.connect(received.append)
    reader.start()
    assert wait_for(lambda: reader.sock is not None)

    tracker = CommandTracker(timeout_seconds=1.0)
    assert reader.send("arm") is True
    tracker.mark_sent("arm")
    assert wait_for(lambda: len(received) == 2)

    ack = next(line for line in received if line.startswith("ACK "))
    telemetry = next(line for line in received if line.startswith("{"))
    update = tracker.resolve(ack)
    assert update is not None
    assert update.status == "ACKNOWLEDGED"
    assert update.command == "arm"
    assert telemetry == '{"time":1,"alt":2.5}'
    assert bridge.received == ["arm"]

    reader.stop()
    bridge.close()


def test_chute_command_is_not_a_confirmation_bypassing_quick_action():
    commands = {command for _, command in CommandPanel.DEFAULT_QUICK_BUTTONS}
    assert "deploy_chute" not in commands


def test_response_parser_does_not_treat_telemetry_as_ack():
    assert parse_command_response("ACK arm") is not None
    assert parse_command_response("NACK invalid_state auto_on") is not None
    assert parse_command_response('{"time":1}') is None
