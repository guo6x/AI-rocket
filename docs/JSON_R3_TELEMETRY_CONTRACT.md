# JSON ↔ R3 read-only telemetry contract

Status: **offline-only implementation on this branch**
Contract: `engineering/json-r3-telemetry-contract.yaml`
Converter: `rf_lab/json_r3_contract.py`
Evidence ceiling: `TESTED_SOFTWARE`; no RF, UART, flight command or actuator path is connected.

## 1. What exists today

The current software has two distinct formats:

1. The STM32 emits newline-delimited text JSON. `flight_computer/src/main.cpp`
   emits a `[FLIGHT] ` prefix on `Serial` and raw JSON on `Serial2`. The normal
   frame contains `time`, raw/filtered pitch and roll, `yaw`, `alt`, `batt`,
   validity/state fields and `sample_time_ms`. `yaw` is `gz` gyro rate in
   degrees/second, **not** a yaw heading. The invalid-sensor status frame has
   health/identity fields but deliberately omits fabricated attitude/altitude.
2. R3.0–R3.2 use `rf_lab/telemetry_frame.py`: an `AR` binary header, telemetry
   kind, unauthenticated `session_id`, `uint16` sequence, opaque payload, and
   CRC-32. R3.1/R3.2 add offline sequence and quality classification; they do
   not define an application JSON payload and do not authenticate a sender.

The ESP8266 relay forwards plaintext command lines to UART, unicasts `ACK` or
`NACK` to the most recent command client, and broadcasts all other UART lines
as telemetry. It does not translate JSON to R3 or add identity/timestamps.
The Ground Station parser extracts JSON objects without a source/authentication
contract; it now ignores valid JSON arrays/scalars at the object boundary so a
non-object cannot reach `MainWindow`'s mapping-only path. This is a minimal
input hardening change, not a UI rewrite.

`DataLogger` timestamps local host receipt time. `MainWindow` uses a local
monotonic receipt clock for live freshness and preserves `sample_time_ms` as
data; it does not claim that host receipt is sensor age. Offline replay adds a
separate `replay_time_ms` and `SIMULATION / OFFLINE REPLAY` display label.

## 2. Field mapping and semantics

The converter uses compact, deterministic application keys because the existing
R3 software budget is 160 payload bytes. The mapping is explicit; omitted
optional fields are reported by the decoder and never filled with zeroes.

| Flight JSON | R3 v1 key | Unit / meaning | Coordinate / precision | Availability and missing rule |
|---|---|---|---|---|
| `time` | `t` | sender/emission `millis`, ms | integer, no quantization | required non-negative integer |
| `sample_time_ms` | `s` | sensor read-start `millis`, ms | integer, no quantization | required when `sensor_valid=1`; may be null for an invalid frame |
| `sensor_valid` | `ok` | 0/1 health flag | integer flag | required; invalid is not converted to a fake sample |
| `source_mode` | `m` | `PHYSICAL`, `SIMULATION`, or `OFFLINE_REPLAY` declaration | enum text; Ground Station's `SIMULATION / OFFLINE REPLAY` is normalized to `OFFLINE_REPLAY` | required; declaration is not identity |
| `pitch_raw`, `pitch_flt` | `p`, `pf` | raw and Kalman-filtered pitch, degrees | `atan2(-ax,sqrt(ay²+az²))`; producer text has 2 decimals | both required for a valid sample |
| `roll_raw`, `roll_flt` | `r`, `rf` | raw and Kalman-filtered roll, degrees | `atan2(ay,az)`; producer text has 2 decimals | both required for a valid sample |
| `yaw` | `y` | `gz` gyro rate, degrees/second; not heading | producer text has 2 decimals; axis/mount transform unverified | required for a valid sample |
| `alt` | `h` | barometric altitude, metres | producer text has 2 decimals; calibration/accuracy unverified | required for a valid sample |
| `batt` | `b` | reported battery field; current firmware value is a placeholder | volts, producer text has 2 decimals | optional; never upgraded to a measured value |
| `auto`, `control_state`, `chute`, `fstate` | `u`, `cs`, `c`, `f` | software state flags/enums | integer flags / text enums | optional read-only state |
| `sensor_fault`, `sensor_fault_latched`, `sensor_io_budget_expired` | `e`, `l`, `q` | fault text/flags | text / integer flags | invalid sample requires `sensor_fault`; attitude fields must be omitted |
| `imu_address`, `imu_id`, `bmp_address`, `bmp_id` | `ia`, `ii`, `ba`, `bi` | diagnostic identity bytes | decimal uint8 | optional; not an authentication proof |

The attitude formulas are the current mathematical coordinate convention. They
do not establish the installed board's body-axis orientation, sign relative to
the airframe, or actuator direction; those remain unverified physical facts.
The STM32 uses `String(..., 2)` for displayed numeric JSON values, while the
underlying calculations remain floating point. The converter preserves parsed
numbers without claiming extra precision or accuracy. Missing values are
omitted or rejected according to the table; no zero is synthesized.

The application object has `v:1` and is canonical ASCII JSON (sorted keys,
compact separators). Oversize payloads are rejected explicitly rather than
truncated. A full diagnostic record may therefore exceed the R3.0 budget; the
caller must choose the contract's optional fields deliberately.

## 3. Four clocks and provenance

| Clock / declaration | Where it comes from | What it does **not** prove |
|---|---|---|
| `sample_time_ms` | STM32 `SensorSample.time_ms`, captured at read start | sensor completion time, transport delay, freshness at Ground Station |
| `send_time_ms` (`time`) | STM32 loop's JSON emission/mission `millis` | radio egress time or receiver arrival |
| `receive_time_ms` | explicit offline observer argument | sensor measurement time or RF latency; never synthesized by converter |
| `replay_time_ms` | explicit offline replay argument | physical time or live sensor time |
| `source_mode` | producer declaration | sender identity, hardware presence, authorization |
| `source_identity` / `authentication` | converter policy | always `UNAUTHENTICATED` / `NONE` |

CRC-32 detects accidental corruption only. A valid CRC, session label, sequence
number, recent receipt or declared `PHYSICAL` mode never authenticates a sender
and never grants flight-control authority.

## 4. Receiver rules

`OfflineJsonR3Receiver` first decodes with the existing R3 codec and validates
the application schema before changing sequence state. It then reuses the
existing `TelemetrySequenceWindow` for the initially bound session:

* malformed header, length, CRC, schema, JSON, missing required field or
  oversized payload → `REJECT_*`; no window or freshness mutation;
* duplicate → `REJECT_DUPLICATE`; no refresh;
* stale/out-of-order → `REJECT_STALE_OR_OUT_OF_ORDER`; no refresh;
* a different session label, whether claimed new or old →
  `REJECT_SESSION_CHANGED_UNTRUSTED`; the bound session remains unchanged;
* an accepted frame → `ACCEPT_UNAUTHENTICATED` with an unobserved sequence-gap
  count. That count is not a measured packet-loss count;
* command-like fields (`arm`, `estop`, `servo_pitch`, `deploy_chute`, etc.) are
  forbidden. Every result carries `flight_control_authority: false`.

This strict session policy intentionally adds a safety boundary around the raw
R3 exploratory behavior, which reports `SESSION_CHANGED` and resets its window.
It does not modify R3.0–R3.2 production research code.

## 5. Reproduction

```powershell
py -3 -m unittest rf_lab.tests.test_json_r3_contract -v
py -3 -m pytest ground_station/tests/test_telemetry_parser.py -q
py -3 -m unittest discover -s rf_lab/tests
py -3 -m rf_lab.contract_evidence --write-evidence engineering/offline-evidence/r3/json_r3_contract_evidence.json
```

The evidence artifact binds source SHA, source-file SHA-256 values, canonical
input/result hashes, commands and Python version. It is software evidence only.

## 6. Explicit non-goals and remaining gaps

This contract does not translate the ESP plaintext command/ACK channel, change
Ground Station live transport, add authentication, add a LoRa/SX1278 driver,
measure latency/range/throughput, or connect any R3 frame to STM32 command
processing. The existing R3 binary format remains a separate offline telemetry
research format until a future compatibility and security review authorizes an
adapter.
