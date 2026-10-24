"""R3.2 read-only telemetry-quality view for OFFLINE evidence.

A syntactically valid datagram is not an authenticated sender or a real RF link.
All timestamps are explicitly supplied synthetic monotonic seconds, never read
from a radio, clock, UART, socket, or actuator interface.

The monitor does NOT decode the opaque application payload into commands.
It does NOT trust session_id. It does NOT retain arbitrary packet bodies.
"""
from __future__ import annotations

from collections import Counter
import math

from rf_lab.telemetry_frame import (
    FrameError,
    ReceiptStatus,
    TelemetrySequenceWindow,
    decode_telemetry,
)


class TelemetryQualityMonitor:
    """Bounded-state, read-only classifier; no device or control channel."""

    def __init__(self, stale_after_seconds: float = 2.0) -> None:
        self.stale_after_seconds = self._number(stale_after_seconds)
        if self.stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        self.window = TelemetrySequenceWindow()
        self._last_offer_at: int | float | None = None
        self._last_accepted_at: int | float | None = None
        self._last_event = "NO_DATA"
        self._session_change_seen = False
        self._counts: Counter[str] = Counter()
        self._forward_gaps = 0

    @staticmethod
    def _number(value: int | float) -> int | float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("synthetic timestamp must be a real number")
        # Keep integer clocks exact (including values outside float's range).
        # Converting first would round large seconds values or raise OverflowError.
        if isinstance(value, int):
            if value < 0:
                raise ValueError("synthetic timestamp must be finite and nonnegative")
            return value
        if not math.isfinite(value) or value < 0:
            raise ValueError("synthetic timestamp must be finite and nonnegative")
        return value

    def _check_now(self, now_seconds: int | float) -> int | float:
        now = self._number(now_seconds)
        if self._last_offer_at is not None and now < self._last_offer_at:
            raise ValueError("synthetic offer timestamps must be monotonic")
        return now

    def observe(self, datagram: bytes, *, now_seconds: float) -> dict[str, object]:
        """Classify one offered simulated frame. No payload is retained/used.

        A bad clock is rejected before any counters or sequence state changes.
        Invalid data and duplicates never refresh the last decoded sample age.
        """
        now = self._check_now(now_seconds)
        self._last_offer_at = now
        try:
            frame = decode_telemetry(datagram)
        except (FrameError, TypeError) as error:
            reason = error.reason if isinstance(error, FrameError) else "datagram_must_be_bytes"
            self._last_event = "REJECT_" + reason
            self._counts[self._last_event] += 1
            return {
                "event": self._last_event,
                "sample_refreshed": False,
                "forward_unobserved_sequences": 0,
                "flight_control_authority": False,
            }

        receipt = self.window.ingest(frame)
        self._last_event = receipt.status.value
        self._counts[self._last_event] += 1
        self._forward_gaps += receipt.unobserved_sequence_count
        refreshed = receipt.status in (
            ReceiptStatus.ACCEPT,
            ReceiptStatus.SESSION_CHANGED,
        )
        if refreshed:
            self._last_accepted_at = now
        if receipt.status == ReceiptStatus.SESSION_CHANGED:
            # This flag must never be treated as a trusted handover or reboot.
            self._session_change_seen = True
        return {
            "event": self._last_event,
            "sample_refreshed": refreshed,
            "forward_unobserved_sequences": receipt.unobserved_sequence_count,
            "flight_control_authority": False,
        }

    def snapshot(self, *, now_seconds: float) -> dict[str, object]:
        """Separate message syntax, recency, source trust, and control authority.

        An externally provided monotonic-clock example is NOT measured latency.
        Snapshot is read-only; observing a later instant does not mutate state.
        """
        now = self._check_now(now_seconds)
        if self._last_accepted_at is None:
            freshness = "NO_DECODED_SAMPLE"
            age = None
        else:
            age = now - self._last_accepted_at
            freshness = ("RECENT_UNAUTHENTICATED"
                         if age <= self.stale_after_seconds
                         else "STALE_UNAUTHENTICATED")
        return {
            "freshness": freshness,
            "synthetic_age_seconds": age,
            "last_packet_outcome": self._last_event,
            "packet_acceptance_is_sender_authentication": False,
            "source_identity": "UNAUTHENTICATED",
            "session_change_seen_untrusted": self._session_change_seen,
            "last_sample_was_authenticated": False,
            "receiver_sequence_gaps_unobserved": self._forward_gaps,
            "event_counts": dict(sorted(self._counts.items())),
            "actual_rf_loss_latency_range_throughput": "NOT_MEASURED",
            "control_or_actuator_channel_connected": False,
            "flight_control_authority": False,
        }
