"""Deterministic telemetry-only datagram replay with simulated faults.

No RF device, socket, UART or flight-command channel is used. Results describe
synthetic frames, not measured link reliability or flight suitability.
"""
from __future__ import annotations
from collections import Counter
import json
from rf_lab.telemetry_frame import (
    TelemetryFrame, FrameError, TelemetrySequenceWindow,
    decode_telemetry, encode_telemetry,
)

SCENARIO = "r3_readonly_replay_v1"


def replay() -> dict[str, object]:
    packets = [encode_telemetry(TelemetryFrame(17, i, f'{{"sample":{i}}}'.encode('ascii')))
               for i in range(100, 121)]
    events: list[tuple[str, bytes]] = []
    for i, p in enumerate(packets, start=100):
        if i in (103, 104):
            continue
        if i == 111:
            continue  # deliver after 112
        if i == 115:
            broken = bytearray(p)
            broken[12] ^= 0x80
            events.append(("corrupted", bytes(broken)))
        else:
            events.append(("normal", p))
        if i == 107:
            events.append(("duplicate", p))
        if i == 112:
            events.append(("out_of_order", packets[111 - 100]))
    events.append(("new_session", encode_telemetry(TelemetryFrame(18, 0, b'{"start":true}'))))

    window = TelemetrySequenceWindow()
    counts: Counter[str] = Counter()
    unobserved = 0
    results: list[dict[str, object]] = []
    for label, packet in events:
        try:
            frame = decode_telemetry(packet)
        except FrameError as exc:
            counts["REJECT_" + exc.reason] += 1
            results.append({"label": label, "status": "REJECT_" + exc.reason})
            continue
        receipt = window.ingest(frame)
        counts[receipt.status.value] += 1
        unobserved += receipt.unobserved_sequence_count
        results.append({
            "label": label, "session_id": frame.session_id,
            "sequence": frame.sequence, "status": receipt.status.value,
            "unobserved_sequence_count": receipt.unobserved_sequence_count,
        })
    return {
        "scenario": SCENARIO,
        "synthetic_only": True,
        "radio_transmissions": 0,
        "flight_commands": 0,
        "events": results,
        "event_count": len(events),
        "counts": dict(sorted(counts.items())),
        "unobserved_sequence_total": unobserved,
        "warning": "Gaps are unobserved sequence numbers, not measured packet-loss statistics; CRC is not authentication.",
    }


def main() -> int:
    print(json.dumps(replay(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
