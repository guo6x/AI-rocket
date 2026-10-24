# R3.2 — read-only telemetry-quality status

**Status:** implemented candidate; full local exact-HEAD build/regression pending.  
**Upstream:** R3.1 [PR #16](https://github.com/guo6x/AI-rocket/pull/16), exact upstream `50a96183fdf1a0bd2bdadd90316359e73be170cc`.  
**Contract:** `engineering/rf-telemetry-quality-contract.yaml` (`AA-RF-TELEMETRY-QUALITY-001`).  
**Evidence ceiling:** offline software only; no verified transmitter, receiver or control authority.

## Engineering question

A ground display must not conflate **receiving a datagram**, **decoding a frame**, **receiving a newer measurement**, **having a recent syntactically acceptable frame** and **verifying the sender's identity**. These are distinct events with very different safety implications.

The R3.2 class `TelemetryQualityMonitor` keeps them distinct. It consumes only the R3.0 `decode_telemetry` result plus an explicit synthetic observation timestamp. It never parses application payloads, connects to any GUI/flight command path, contacts hardware or retains packet bodies.

## Independent output dimensions

| Field | Semantics |
|---|---|
| `freshness` | `NO_DECODED_SAMPLE`, `RECENT_UNAUTHENTICATED`, or `STALE_UNAUTHENTICATED`, based **only** on the last accepted synthetic observation and an injected synthetic clock |
| `last_packet_outcome` | Last offered synthetic frame: `ACCEPT`, `DUPLICATE`, `STALE_OR_OUT_OF_ORDER`, `SESSION_CHANGED` or strict `REJECT_...`; independent of freshness |
| `source_identity` | Always `UNAUTHENTICATED`. Neither CRC, session label nor sequence counts verify remote identity |
| `session_change_seen_untrusted` | Sticky warning when a syntactically valid but unauthenticated frame changes session label |
| `receiver_sequence_gaps_unobserved` | Cumulative skipped sequence indices; **not** packet loss |
| `actual_rf_loss_latency_range_throughput` | Always `NOT_MEASURED` |
| `flight_control_authority` | Always `false`; there is no command/actuator API |

A valid new session changes the observed sequence window (R3.0 behavior). R3.2 deliberately **does not claim** this is an authorized reset or reboot. Since a valid-CRC frame can be forged, a real deployment needs an independently designed and reviewed authentication/handover policy before treating a new session as trustworthy.

A malformed frame, duplicate, or stale/out-of-order sequence never refreshes `last_accepted_at`. Thus an incoming CRC error can coexist with a prior accepted sample that has aged out; the monitor reports both facts, rather than labeling the stream healthy. A future-looking/invalid clock sample is rejected before counters/window change. The threshold defaults to **2 synthetic seconds** for illustration, not an actual radio timeout or flight-time requirement.

## Reproduction

From repository root:

```powershell
py -3 -m unittest discover -s rf_lab/tests -v
py -3 -m rf_lab.quality_demo --check
py -3 -m rf_lab.reliability_experiment --check
py -3 scripts/check.py
```

The self-contained demo `rf_lab/quality_demo.py` shows a timeline: no data → accepted-but-unauthenticated → corrupt frame while previously accepted sample is stale → duplicate while stale → session-change warning. It uses synthetic observation times and prints JSON; no socket or radio is initialized. `scripts/check.py` additionally runs the demo and existing RF unit test discovery.

Added tests reside in `rf_lab/tests/test_telemetry_quality.py` and `rf_lab/tests/test_quality_demo.py`. They verify age boundaries, CRC rejections, duplicate/stale behavior, session changes, no command API, invalid clocks with state invariance, snapshot purity and fixed-memory-shape counters.

**The remote candidate code and tests are committed but full project regression has not been independently executed at its latest SHA.** Do not merge based solely on source inspection. A fresh, exact-HEAD Codex test/build report and independent review are required.

## Remaining unknowns

Real-world sample age requires independently established sender timestamps, clock assumptions and capture semantics. This module uses **synthetic receive-observation timestamps**; a CRC-valid datagram received now can carry *old, replayed or false sensor data*. Even `RECENT_UNAUTHENTICATED` is **not** sensor freshness or measurement integrity.

Other unresolved work includes RF/SX1278 driver compatibility, sender authentication, cross-session replay protection, actual antenna/radio performance, and any physical hardware integration. Those are separate gates; R3.2 does not implement them.

No hardware, RF transmission, GPS, flight navigation/commands, actuation, propulsion or recovery operation is authorized or part of this stage.
