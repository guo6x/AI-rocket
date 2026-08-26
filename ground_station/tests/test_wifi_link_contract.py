import socket
import threading
import time

import pytest
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
    responses = []
    reader = UdpReader(
        host="127.0.0.1",
        port=listen_port,
        target_addr=("127.0.0.1", command_port),
    )
    reader.data_received.connect(received.append)
    reader.command_response_received.connect(
        lambda data, source: responses.append((data, source))
    )
    reader.start()
    assert wait_for(lambda: reader.sock is not None)

    tracker = CommandTracker(timeout_seconds=1.0)
    assert reader.send("arm") is True
    tracker.mark_sent("arm")
    assert wait_for(lambda: len(received) == 1 and len(responses) == 1)

    ack, source = responses[0]
    assert reader.is_expected_response_source(source)
    telemetry = received[0]
    update = tracker.resolve(ack)
    assert update is not None
    assert update.status == "ACKNOWLEDGED"
    assert update.command == "arm"
    assert telemetry == '{"time":1,"alt":2.5}'
    assert bridge.received == ["arm"]

    reader.stop()
    bridge.close()


@pytest.mark.parametrize(
    ("response", "expected_status"),
    [("ACK arm", "ACKNOWLEDGED"), ("NACK invalid_state arm", "NACK")],
)
def test_udp_response_only_resolves_from_configured_esp_source(
    response, expected_status
):
    listen_port = free_udp_port()
    command_port = free_udp_port()
    reader = UdpReader(
        host="127.0.0.1",
        port=listen_port,
        target_addr=("127.0.0.1", command_port),
    )
    tracker = CommandTracker(timeout_seconds=1.0)
    seen_sources = []
    updates = []

    def resolve_if_expected(data, source):
        seen_sources.append(source)
        if reader.is_expected_response_source(source):
            updates.append(tracker.resolve(data))

    reader.command_response_received.connect(resolve_if_expected)
    reader.start()
    assert wait_for(lambda: reader.sock is not None)
    tracker.mark_sent("arm")

    wrong_source = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    expected_source = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    expected_source.bind(("127.0.0.1", command_port))
    wrong_source.sendto(response.encode("utf-8"), ("127.0.0.1", listen_port))
    assert wait_for(lambda: len(seen_sources) == 1)
    assert not reader.is_expected_response_source(seen_sources[0])
    assert tracker.pending

    expected_source.sendto(response.encode("utf-8"), ("127.0.0.1", listen_port))
    assert wait_for(lambda: len(seen_sources) == 2)
    assert reader.is_expected_response_source(seen_sources[1])
    assert not tracker.pending
    assert updates[0].status == expected_status

    reader.stop()
    wrong_source.close()
    expected_source.close()


def test_chute_command_is_not_a_confirmation_bypassing_quick_action():
    commands = {command for _, command in CommandPanel.DEFAULT_QUICK_BUTTONS}
    assert "deploy_chute" not in commands


def test_response_parser_does_not_treat_telemetry_as_ack():
    assert parse_command_response("ACK arm") is not None
    assert parse_command_response("NACK invalid_state auto_on") is not None
    assert parse_command_response('{"time":1}') is None
