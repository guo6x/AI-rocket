# R3.1 — deterministic offline telemetry reliability experiment

**Contract:** `engineering/rf-reliability-contract.yaml` (`AA-RF-OFFLINE-RELIABILITY-001`)
**Protocol compatibility:** unchanged R3.0 telemetry frame version 1
**Evidence ceiling:** `TESTED_SOFTWARE`; no real radio, device, command, or actuator acceptance.

## Experiment boundary

`rf_lab/reliability_experiment.py` is a standalone synthetic generator/receiver experiment over the existing R3.0 `encode_telemetry`, `decode_telemetry`, and `TelemetrySequenceWindow`. It adds no radio driver, socket, UART, flight-command, or actuator path. CRC-32 still detects accidental corruption only; `session_id` remains an unauthenticated label whose change can reset the freshness window.

The experiment records the generator's known synthetic drops separately from receiver-inferred unobserved sequence gaps. A corrupt, truncated, delayed, or duplicated datagram can make those counts differ. Neither count is a measured RF packet-loss rate. Delays are represented only by delivery order and abstract generator slots; no milliseconds or hardware timing are assigned.

## Fixed scenarios and bounded stress trace

The executable experiment covers normal ordered delivery, independently selected synthetic drops, contiguous burst drops, duplicate delivery, delayed/out-of-order delivery, CRC corruption, truncated header/payload, malformed declared length, 16-bit large-gap/half-range/wrap behavior, and untrusted session-label churn. A further bounded 512-frame fault mix uses Python `random.Random(0x5231)` to shuffle a fixed event population: 32 each of drop, duplicate, CRC corruption, truncation, and delay, plus 352 normal frame selections. These are fixture counts, not a link-probability model.

For each scenario, the output separates unique frames generated, known synthetic drops, datagrams offered to the receiver, receiver status/rejection counts, unobserved sequence gaps, maximum accepted forward gap, pending synthetic delayed frames, and permission-boundary counters. The receiver records zero freshness-window mutation for invalid datagrams, duplicates, and stale frames. Valid frames with a changed session label may reset the window, explicitly untrusted; no outcome can dispatch a command or grant control authority in this harness.

The seeded scenario is capped at 512 generated frames and 1,024 deliveries. Its pending-delay peak uses an explicit same-slot order: new synthetic delays enter the queue before frames released in that slot leave it. The check bounds the queue by 512 frames and applies deliberately generous host-only guardrails of 10 seconds and 8 MiB of Python `tracemalloc` peak. Each run reports observed host elapsed time and Python allocation. These are checks on this bounded Python process only, not embedded memory, RF performance, throughput, latency, or timing claims.

## Reproduction

```powershell
py -3 -m unittest discover -s rf_lab/tests -v
py -3 -m rf_lab.reliability_experiment --check
py -3 -m rf_lab.reliability_experiment --write-evidence engineering/offline-evidence/r3/r3_1_telemetry_reliability.json
py -3 scripts/check.py
```

The R3.1 JSON evidence is a new artifact; the prior R3.0 `rf_offline_replay.json` remains unchanged. It includes the full generated/delivery trace, fixed seed, input-trace SHA-256, deterministic-result SHA-256, source file SHA-256 values, source Git SHA/worktree state, exact command, Python/platform/available compiler tool versions, runtime/memory observation, and `TESTED_SOFTWARE` ceiling. Runtime and allocation observations may vary by host; trace and deterministic result hashes bind the reproducible inputs and software classifications.

## Actual run results

The deterministic scenario counters, trace/result hashes, source hashes, tool versions, and host resource observation are recorded in the committed evidence artifact at `engineering/offline-evidence/r3/r3_1_telemetry_reliability.json`. The final delivery report gives the full repository regression/build counts. No hardware operation is required or authorized.

## Remaining limits

- No physical LoRa/SX1278/RA-02 behavior, RF loss, range, link timing, throughput, packet/FIFO compatibility, region legality, pinout, or antenna has been measured.
- A valid-CRC forged `session_id` can still trigger `SESSION_CHANGED` and reset freshness. Authentication and replay protection across session labels remain unresolved protocol/security work.
- CRC-32 is not identity authentication or protection against deliberate modification.
- The harness proves only bounded software behavior for the recorded synthetic traces, not operational telemetry reliability or any flight/control suitability.
