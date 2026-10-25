"""Socket lifecycle boundary tests use fakes only, not a radio/device."""

from unittest.mock import Mock

from core import udp_reader


def test_socket_is_not_sendable_until_bind_and_configuration_complete(monkeypatch):
    reader = udp_reader.UdpReader(target_addr=("192.0.2.1", 9876))
    fake = Mock()

    def bind(_address):
        assert reader.sock is None
        assert not reader.send("arm")

    def receive(_length):
        assert reader.sock is fake
        reader.is_running = False
        raise OSError("synthetic end of receive loop")

    fake.bind.side_effect = bind
    fake.recvfrom.side_effect = receive
    monkeypatch.setattr(udp_reader.socket, "socket", lambda *_: fake)
    reader.run()
    fake.close.assert_called_once()
    fake.sendto.assert_not_called()
    assert reader.sock is None


def test_bind_failure_closes_private_socket_without_publishing_it(monkeypatch):
    reader = udp_reader.UdpReader()
    fake = Mock()
    fake.bind.side_effect = OSError("synthetic bind failure")
    monkeypatch.setattr(udp_reader.socket, "socket", lambda *_: fake)
    reader.run()
    fake.close.assert_called_once()
    assert reader.sock is None
    assert not reader.is_running
