"""Pure standard-library, telemetry-only **offline** datagram codec.

No radio driver, physical transmit, flight-command processing, or UART IO.
CRC-32 rejects accidental corruption; it does NOT authenticate a sender.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import struct
import zlib

MAGIC = b"AR"
VERSION = 1
KIND_TELEMETRY = 1
MAX_PAYLOAD_BYTES = 160  # experimental software budget, not a radio qualification
HEADER = struct.Struct(">2sBBIHH")
CRC = struct.Struct(">I")
OVERHEAD_BYTES = HEADER.size + CRC.size

class FrameError(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason

@dataclass(frozen=True)
class TelemetryFrame:
    session_id: int
    sequence: int
    payload: bytes


def encode_telemetry(frame: TelemetryFrame) -> bytes:
    if not isinstance(frame, TelemetryFrame):
        raise TypeError("expected TelemetryFrame")
    if not isinstance(frame.payload, bytes):
        raise TypeError("payload must be bytes")
    if not (1 <= len(frame.payload) <= MAX_PAYLOAD_BYTES):
        raise FrameError("payload_length_out_of_range")
    if type(frame.session_id) is not int or not (0 <= frame.session_id <= 0xFFFFFFFF):
        raise FrameError("session_id_out_of_range")
    if type(frame.sequence) is not int or not (0 <= frame.sequence <= 0xFFFF):
        raise FrameError("sequence_out_of_range")
    message = HEADER.pack(MAGIC, VERSION, KIND_TELEMETRY,
                          frame.session_id, frame.sequence, len(frame.payload)) + frame.payload
    return message + CRC.pack(zlib.crc32(message) & 0xFFFFFFFF)


def decode_telemetry(datagram: bytes) -> TelemetryFrame:
    if not isinstance(datagram, bytes):
        raise TypeError("datagram must be bytes")
    if len(datagram) < OVERHEAD_BYTES:
        raise FrameError("truncated_header_or_crc")
    if len(datagram) > OVERHEAD_BYTES + MAX_PAYLOAD_BYTES:
        raise FrameError("oversized_datagram")
    magic, version, kind, session, sequence, length = HEADER.unpack_from(datagram)
    if magic != MAGIC:
        raise FrameError("bad_magic")
    if version != VERSION:
        raise FrameError("unsupported_version")
    if kind != KIND_TELEMETRY:
        raise FrameError("non_telemetry_kind")
    if not (1 <= length <= MAX_PAYLOAD_BYTES):
        raise FrameError("payload_length_out_of_range")
    if len(datagram) != OVERHEAD_BYTES + length:
        raise FrameError("payload_size_mismatch")
    expected_crc = CRC.unpack_from(datagram, len(datagram)-CRC.size)[0]
    actual_crc = zlib.crc32(datagram[:-CRC.size]) & 0xFFFFFFFF
    if expected_crc != actual_crc:
        raise FrameError("crc_mismatch")
    return TelemetryFrame(session_id=session, sequence=sequence,
                          payload=datagram[HEADER.size:-CRC.size])


class ReceiptStatus(str, Enum):
    ACCEPT = "ACCEPT"
    DUPLICATE = "DUPLICATE"
    STALE_OR_OUT_OF_ORDER = "STALE_OR_OUT_OF_ORDER"
    SESSION_CHANGED = "SESSION_CHANGED"


@dataclass(frozen=True)
class Receipt:
    status: ReceiptStatus
    unobserved_sequence_count: int = 0


class TelemetrySequenceWindow:
    """Receive freshness gate, not security. No effects outside this object.

    Unobserved counters are gaps in sequence numbers, not proven RF losses.
    Session ID is unauthenticated; any valid-CRC datagram can change it.
    """
    def __init__(self) -> None:
        self.session_id: int | None = None
        self.last_sequence: int | None = None

    def ingest(self, frame: TelemetryFrame) -> Receipt:
        if not isinstance(frame, TelemetryFrame):
            raise TypeError("expected decoded telemetry frame")
        if self.session_id is None:
            self.session_id, self.last_sequence = frame.session_id, frame.sequence
            return Receipt(ReceiptStatus.ACCEPT)
        if self.session_id != frame.session_id:
            self.session_id, self.last_sequence = frame.session_id, frame.sequence
            return Receipt(ReceiptStatus.SESSION_CHANGED)
        assert self.last_sequence is not None
        delta = (frame.sequence - self.last_sequence) & 0xFFFF
        if delta == 0:
            return Receipt(ReceiptStatus.DUPLICATE)
        if delta >= 0x8000:
            return Receipt(ReceiptStatus.STALE_OR_OUT_OF_ORDER)
        self.last_sequence = frame.sequence
        return Receipt(ReceiptStatus.ACCEPT, unobserved_sequence_count=delta-1)
