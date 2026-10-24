"""Deterministic offline telemetry framing tests."""
import struct
import unittest
from rf_lab.telemetry_frame import (
    TelemetryFrame, FrameError, TelemetrySequenceWindow, ReceiptStatus,
    HEADER, OVERHEAD_BYTES, MAX_PAYLOAD_BYTES, decode_telemetry, encode_telemetry,
)

class TelemetryProtocolTests(unittest.TestCase):
    def setUp(self):
        self.frame = TelemetryFrame(1, 7, b'{"t":100}')
        self.valid = encode_telemetry(self.frame)

    def assertReject(self, datagram, reason):
        with self.assertRaises(FrameError) as ctx:
            decode_telemetry(datagram)
        self.assertEqual(ctx.exception.reason, reason)

    def test_round_trip(self): self.assertEqual(decode_telemetry(self.valid), self.frame)
    def test_boundary_exact_payload(self):
        self.assertEqual(len(encode_telemetry(TelemetryFrame(0,65535,b'x'*MAX_PAYLOAD_BYTES))),OVERHEAD_BYTES+MAX_PAYLOAD_BYTES)
    def test_empty_payload(self):
        with self.assertRaises(FrameError): encode_telemetry(TelemetryFrame(1,2,b''))
    def test_too_long_payload(self):
        with self.assertRaises(FrameError): encode_telemetry(TelemetryFrame(1,2,b'x'*(MAX_PAYLOAD_BYTES+1)))
    def test_payload_must_be_bytes(self):
        with self.assertRaises(TypeError): encode_telemetry(TelemetryFrame(1,2,'text'))
    def test_session_out_of_range(self):
        with self.assertRaises(FrameError): encode_telemetry(TelemetryFrame(2**32,2,b'a'))
    def test_seq_out_of_range(self):
        with self.assertRaises(FrameError): encode_telemetry(TelemetryFrame(1,-1,b'a'))
    def test_truncated_header(self): self.assertReject(self.valid[:10],"truncated_header_or_crc")
    def test_truncated_payload(self): self.assertReject(self.valid[:-2],"payload_size_mismatch")
    def test_oversized_datagram(self): self.assertReject(self.valid+b'x'*MAX_PAYLOAD_BYTES,"oversized_datagram")
    def test_bad_magic(self): self.assertReject(b'ZZ'+self.valid[2:],"bad_magic")
    def test_bad_version(self): self.assertReject(self.valid[:2]+b'\x02'+self.valid[3:],"unsupported_version")
    def test_command_like_kind_rejected_before_crc(self):
        self.assertReject(self.valid[:3]+b'\x02'+self.valid[4:],"non_telemetry_kind")
    def test_declared_oversize_rejected(self):
        a=bytearray(self.valid); a[10:12]=struct.pack('>H',MAX_PAYLOAD_BYTES+1)
        self.assertReject(bytes(a),"payload_length_out_of_range")
    def test_declared_short_rejected(self):
        a=bytearray(self.valid); a[10:12]=struct.pack('>H',3)
        self.assertReject(bytes(a),"payload_size_mismatch")
    def test_corrupt_payload_crc(self):
        a=bytearray(self.valid); a[HEADER.size]^=0x01
        self.assertReject(bytes(a),"crc_mismatch")
    def test_corrupt_crc(self):
        a=bytearray(self.valid); a[-1]^=1
        self.assertReject(bytes(a),"crc_mismatch")
    def test_first_accept(self):
        w=TelemetrySequenceWindow()
        self.assertEqual(w.ingest(self.frame).status,ReceiptStatus.ACCEPT)
    def test_duplicate(self):
        w=TelemetrySequenceWindow(); w.ingest(self.frame)
        self.assertEqual(w.ingest(self.frame).status,ReceiptStatus.DUPLICATE)
    def test_gap_is_unobserved_not_proven_loss(self):
        w=TelemetrySequenceWindow(); w.ingest(self.frame)
        self.assertEqual(w.ingest(TelemetryFrame(1,10,b'a')).unobserved_sequence_count,2)
    def test_stale(self):
        w=TelemetrySequenceWindow(); w.ingest(self.frame)
        self.assertEqual(w.ingest(TelemetryFrame(1,6,b'a')).status,ReceiptStatus.STALE_OR_OUT_OF_ORDER)
    def test_ambiguous_half_range_stale(self):
        w=TelemetrySequenceWindow(); w.ingest(self.frame)
        self.assertEqual(w.ingest(TelemetryFrame(1,(7+32768)%65536,b'a')).status,ReceiptStatus.STALE_OR_OUT_OF_ORDER)
    def test_wrap_around(self):
        w=TelemetrySequenceWindow(); w.ingest(TelemetryFrame(1,65535,b'a'))
        self.assertEqual(w.ingest(TelemetryFrame(1,0,b'a')).status,ReceiptStatus.ACCEPT)
    def test_session_change_not_authentic(self):
        w=TelemetrySequenceWindow(); w.ingest(self.frame)
        self.assertEqual(w.ingest(TelemetryFrame(2,0,b'a')).status,ReceiptStatus.SESSION_CHANGED)
    def test_endianness(self):
        self.assertEqual(self.valid[4:10], b'\x00\x00\x00\x01\x00\x07')
    def test_no_command_decoding(self):
        f=decode_telemetry(encode_telemetry(TelemetryFrame(1,0,b'arm')))
        self.assertEqual(f.payload,b'arm')  # opaque bytes; never dispatched to command processor

if __name__ == '__main__':
    unittest.main()
