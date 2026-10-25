# SYSTEM-V1 — existing software capability matrix

**Document type:** reference for the project owner and software-integration engineers.

**Inventory date:** 2026-10-25.

**Fixed inventory source:** `50006f8fd6830a34f16b5e9d2f4e84269c403007` (PR #24 source).
**Purpose:** identify reusable software, missing integration and evidence ceilings before claiming a whole-product loop. This is not a test report, hardware acceptance or release authorization.

## 1. Baseline and evidence rules

This matrix inventories the fixed source above. Concurrent SYSTEM-V1 work may add code after that source; its completion must be established by a separate exact-source report, not inferred from this inventory. Source links below are pinned to the inventory commit so later line movement does not change the inspected behavior.

For current engineering status, use [engineering/current-baseline.yaml](../engineering/current-baseline.yaml), [engineering/component-status.yaml](../engineering/component-status.yaml) and [engineering/known-issues.md](../engineering/known-issues.md). For implementation behavior, production code takes precedence over reports. [Engineering authority rules](../engineering/README.md) keep ownership, configuration, software evidence and hardware verification separate.

Three evidence layers must not be merged:

1. **Existing code at the inventory source:** directly inspected functionality and interfaces.
2. **Prior software evidence:** committed traces, native/fixture tests and earlier build reports for their named source revisions. These are reusable evidence, not a new run at `50006f8...` or at the final SYSTEM-V1 source.
3. **Current SYSTEM-V1 acceptance:** **PENDING** in this document. The root task must bind its actual gate results to the tested source, logs, commands and remaining limitations. An implemented workflow or successful Git merge is not CI PASS.

The [R3.2 mainline evidence note](R3_2_MAINLINE_EVIDENCE_AND_BLOCKERS.md) explicitly separates the prior `889cbfb5...` feature-head handoff from a new merge-head run. Its reported 379 executions include repeated standalone groups; they are not 379 unique tests. Older entries such as Ground Station 49 in `verification-status.yaml` also remain historical records, not current totals.

## 2. Status vocabulary

| Status | Meaning in this matrix |
| --- | --- |
| `IMPLEMENTED` | Source-path code exists. No new test or hardware claim is implied. |
| `TESTED_SOFTWARE` | A repeatable software test/build or committed software evidence exists for a stated prior source and contract. Exact-current-source acceptance still requires the current gate. |
| `NEEDS_INTEGRATION` | Useful components exist, but the required producer/adapter/UI or end-to-end software contract is absent or unverified. |
| `BLOCKED` | A named missing dependency or known mismatch prevents the stated use. |
| `HISTORICAL` | Preserved prior route, configuration, output or result; not current plant or product authority. |
| `UNKNOWN` | Evidence is absent or insufficient. Do not substitute a default, filename, purchase record or simulation assumption. |

Where engineering authority uses `PROTOTYPE`, that classification is retained explicitly in the notes; implementation or narrow numerical tests do not upgrade the model to physical validation. No matrix row establishes `VERIFIED_HARDWARE`.

## 3. Reusable capability inventory

| Domain / capability | Status | Existing implementation and prior evidence | Missing integration or evidence ceiling |
| --- | --- | --- | --- |
| Ground Station: Serial and explicit-unicast WiFi transport | `TESTED_SOFTWARE` | [SerialReader][gs-serial], [UdpReader][gs-udp], existing simulated WiFi return-path and transport tests in [ground_station/tests][gs-tests]. | No physical serial/WiFi reconnect, range, operator-workflow or current board evidence. IP/port response correlation is not cryptographic authentication. |
| Ground Station: canonical command receipts | `TESTED_SOFTWARE` | [CommandTracker][gs-command] tracks one pending plaintext command and distinguishes `SENT`, `ACKNOWLEDGED`, `NACK`, `TIMEOUT` and `FAILED`; [MainWindow][gs-main] connects transport/UI status. Tests cover `sensor_invalid` and `recovery_disabled` reasons. | `SENT` is local transport success. ACK is a software command response, not measured actuator motion or physical safety. No authenticated request identity, replay protection or multi-client arbitration. |
| Ground Station: parsing, raw/structured logs, curves and attitude view | `IMPLEMENTED` / prior `TESTED_SOFTWARE` | [TelemetryParser][gs-parser] handles fragmented/concatenated JSON; [DataLogger][gs-logger] records RAW and DICT lines; [MainWindow][gs-main] connects plots, indicators and 3D. Existing parser/logging/sensor-validity UI tests are retained. | This baseline has no dedicated controlled offline fixture/replay producer. A parser or stored CSV is not an implemented, isolated replay product loop. Baseline yaw/battery display semantics need correction; see section 4. |
| Ground Station: honest source/freshness and offline/live separation | `NEEDS_INTEGRATION` | Sensor-validity display/freezing exists in [MainWindow][gs-main]. R3 quality dimensions exist independently. | Baseline has no shared source/clock/freshness envelope, offline command-exclusion loop or session-isolated replay adapter. SYSTEM-V1 additions require their own negative/UI tests; do not count them as pre-existing baseline behavior. |
| Flight Computer: checked sensor identity/configuration/read validity | `TESTED_SOFTWARE` | [sensor_validity.cpp][fc-sensors], [wire_sensor_bus.h][fc-bus], production-main fake-boundary/native tests and prior target builds. Supported IMU IDs are MPU6500 `0x70` / MPU9250 `0x71`; BMP280 ID is `0x58`. | Readback and exact read-length checks are software behavior. Actual populated silicon, mounting, calibration, accuracy, bus timing and current physical fault response remain `UNKNOWN`. Faults latch until reboot; RESET does not clear the sensor latch. |
| Flight Computer: PID/Kalman and dual-axis output intent | `TESTED_SOFTWARE` | Production [pid.cpp][fc-pid], [kalman.cpp][fc-kalman] and [main.cpp][fc-main]; R2.3 production C++/independent oracle and dual-cadence traces under [engineering/offline-evidence/r2_3](../engineering/offline-evidence/r2_3). | Oracle parity proves tested numerical/source behavior, not correct mounting, linkage sign, loaded servo response, measured loop timing or physical stabilization. |
| Flight Computer: command state, E-STOP/reset and independent line buffers | `TESTED_SOFTWARE` | [command_processor.cpp][fc-command], [main.cpp][fc-main], [command_line_buffer.h][fc-buffer] and native command/production-main tests. | Neutral writes are software intent, not measured neutralization. E-STOP has the narrower semantics in section 4; it is not a physical power cut and does not reject the default profile's explicit `deploy_chute`. |
| Flight Computer: GNC-only recovery-output isolation | `TESTED_SOFTWARE` | Opt-in `gnc_only_bench` / `native_gnc_only_bench`; production compile guards omit recovery PB0 attach/write and automatic FSM updates; `deploy_chute` returns `NACK recovery_disabled`. | Default firmware remains distinct and unchanged. Fake Servo/bus tests and source builds are not proof of the actual installed target, wiring or absence of physical actuation. |
| Recovery: production FSM logic | `TESTED_SOFTWARE` for synthetic logic; qualification `BLOCKED` | Production FSM/native cases and [recovery_configuration_audit.py][recovery-audit] exist. | Configured accelerometer range is ±2 g, but automatic launch detection requires strictly greater than 2.5 g for three samples. `BLOCKED_UNREACHABLE_THRESHOLD` remains open; no silent range/threshold retuning. Sensor-invalid/E-STOP early returns also suspend automatic FSM/backup-timer evaluation. |
| ESP8266: UDP command → UART → ACK/NACK return and telemetry broadcast | `TESTED_SOFTWARE` | [main.cpp][esp-main], [relay_router.cpp][esp-router], native relay tests and prior NodeMCU/ESP-01S source builds. Explicit unicast commands are line-validated; UART ACK/NACK routes to the most recent command client's IP/port. | Plaintext, unauthenticated, no request IDs/replay protection; last-client routing is not multi-client arbitration. ESP-01S build success does not prove its actual flash, boot, power, UART or radio operation. |
| RF R3.0: telemetry-only binary codec and sequence classifier | `TESTED_SOFTWARE` | [telemetry_frame.py][rf-frame] provides strict framing, CRC32 and a uint16 forward window; [test_telemetry_frame.py][rf-frame-tests] covers malformed bounds, CRC, duplicates, half-range, wrap and command-looking opaque payloads. | CRC detects accidental corruption only. `session_id` is an unauthenticated label; a changed label can reset the window. No command/actuator authority exists. |
| RF R3.0/R3.1: deterministic synthetic fault experiments | `TESTED_SOFTWARE` | [offline_link_replay.py][rf-replay], [reliability_experiment.py][rf-reliability], tests and committed [R3 evidence](../engineering/offline-evidence/r3). Prior R3.1 evidence records 10 scenarios, 591 generated frames, 39 generator-known drops and 589 offered datagrams. | Generator-known drops and receiver-inferred sequence gaps are different counters. Delays use abstract ordering slots. Host resource checks are not embedded memory, RF loss/latency/throughput/range or reliability measurements. |
| RF R3.2: read-only quality/freshness dimensions and clock guards | `TESTED_SOFTWARE` | [TelemetryQualityMonitor][rf-quality], deterministic demo/tests and immutable clock-guard v2 evidence. Checks cover both offered and accepted clock anchors, invalid/replayed non-refresh, session warning and no command API. | Injected timestamps are synthetic receive observations. `RECENT_UNAUTHENTICATED` is neither sensor sample freshness, payload truth nor trusted identity. `source_identity` stays `UNAUTHENTICATED`; real RF metrics stay `NOT_MEASURED`. |
| RF ↔ ESP/Flight Computer/Ground Station integration | `NEEDS_INTEGRATION` | Both the R3 binary experiment and the current ESP text path exist separately. | R3 uses `AR` + big-endian header + 1–160 byte opaque payload + CRC32. Existing ESP uses newline-delimited text and `strlen`; arbitrary binary NUL/newline/CRC bytes cannot pass unchanged. No versioned text/binary adapter, payload-budget mapping or production RF-quality binding exists at the inventory source. Do not replace the WiFi route or attach command authority. |
| RF hardware/region compatibility | `BLOCKED` / `UNKNOWN` | [rf-offline-contract.yaml](../engineering/rf-offline-contract.yaml) preserves a limited official RA-02 document review and owned-asset references. | Radio driver `NOT_IMPLEMENTED`; module revision, SPI/FIFO/timing, connector/antenna match and relevant operating-region authorization are unresolved. 176 bytes < a vendor's 256-byte feature description is not demonstrated packet/FIFO interoperability. No transmission or hardware operation is authorized. |
| Research: 1D/2D inverted pendulum, delayed sensor and limited actuator models | `IMPLEMENTED`; narrow cases `TESTED_SOFTWARE` | [physics_engine.py][model-1d], [physics_engine_2d.py][model-2d], [components.py][model-components] and [simulation_smoke.py][sim-smoke]. Engineering authority classifies these as `PROTOTYPE`. | Unmeasured mass, CG, inertia, thrust, damping, delay and actuator assumptions; script sign/cadence disagreements persist. Smoke explicitly expects TUNED small-angle convergence **and TESTBENCH non-ideal 5° non-convergence**. No physical stability proof. |
| Research: Barrowman CG/CP, RocketPy, custom quaternion 6DOF, PID comparison and Monte Carlo | `HISTORICAL` | Executable source exists under [aero_sim][aero-source]; [rocket_config.py][legacy-config] explicitly labels the old 75 mm solid-flight baseline. Existing output files are preserved. | Not the current EDF bench. Motor text/constants and assumptions conflict; outputs lack full run provenance. Smoke checks only selected kernels, not full trajectory validity. Old reported flight/PID improvements do not qualify current hardware. |
| Research: numerical reference and evidence-manifest method | `TESTED_SOFTWARE` for recorded narrow research; broader adoption `NEEDS_INTEGRATION` | [KR-2026-002](aerospace-knowledge/records/KR-2026-002-simulation-provenance.md), [KR-2026-004](aerospace-knowledge/records/KR-2026-004-authentic-model-analytic-benchmark.md), associated examples and immutable KB3 artifacts. | Historical 1D reference covers only zero thrust, 0.1°, 0.4 s and the same assumed model; hashes establish file identity, not physical truth. Other models, step convergence and independent-solver/measurement correlation remain open. |
| CI/local gate: complete software runner | `IMPLEMENTED`; prior constituent gates `TESTED_SOFTWARE` | [scripts/check.py][full-check] contains existing GS/native/ESP, simulation, engineering/recovery audits, R2.3, RF/research tests and five source builds. Failure affects the exit code. | Current SYSTEM-V1 exact-source run is `PENDING` here. Repeated standalone groups must not inflate unique test totals. Hardware gates are deliberately outside this software exit code; advisory recovery audit does not mean recovery-qualified. |
| CI: hosted SYSTEM-V1 workflow and attributable logs | `IMPLEMENTED`; current hosted result `UNKNOWN` | [system-v1-software.yml][ci-workflow] runs the full runner on pull requests/main or manual dispatch and retains logs, including failures, with read-only repository permission. | Workflow presence is not an executed PASS. Root must record the actual run URL, tested checkout SHA, conclusion and failed/skipped steps; local PASS must not be relabeled hosted CI PASS. |

## 4. Firmware and display meanings that must remain explicit

### Attitude, timing and battery

At the inventory source, production `main.cpp` computes `pitch = atan2(-ax, sqrt(ay*ay + az*az))` and `roll = atan2(ay, az)` in degrees. Pitch Kalman uses `gy`, roll Kalman uses `gx`. These formulas do not establish the installed sensor-to-vehicle transform.

- **`yaw` is assigned `gz`: angular rate in deg/s, not yaw heading in degrees.** Do not use that field as an absolute heading in a 3D view or silently integrate it into a claimed navigation solution.
- **`batt` is the hardcoded value `7.4`.** It is a source placeholder, not a battery/ADC measurement. Missing battery information is unavailable, not zero or a retained prior-session value.
- **`source_mode=PHYSICAL` is a producer declaration, not authenticated provenance.** `sample_time_ms` is source-provided timing, distinct from receiver arrival, replay time and wall-clock time; neither field alone proves a real sensor or trustworthy sample age.
- The actual code uses a `micros()` delta and `delay(50)`, with fallback `dt=0.01` for zero/nonpositive or >0.5 s intervals. The 50 ms comparison in R2.3 is an assumption, not measured target scheduling. Legacy 2D simulation uses 1 ms integration and 10 ms PID updates despite older 1 kHz controller prose.
- Production PID is `error = target - current`; FLIGHT limits output to ±4 with ±0.3 per `compute`, TESTBENCH to ±15 with ±1 per `compute`. Automatic writes are `90 + int(PID)` constrained to 0–180 on PA6/PA7. These are command units/call-count limits, not measured nozzle angle, servo slew or restoring-torque direction.

### E-STOP, fault latch and recovery are separate contracts

The baseline accepts `estop` in every command state, latches E-STOP, disables AUTO, resets both PID histories and writes TVC neutral. `reset` is accepted only from E-STOP and returns to idle; AUTO does not resume without new commands. A sensor fault remains latched until reboot; RESET is not a sensor-recovery action.

**The default profile still accepts explicit `deploy_chute` while armed, AUTO-enabled or E-STOP-latched, including invalid-sensor conditions.** The command branch precedes sensor-validity rejection for ARM/AUTO/manual TVC. Do not document E-STOP as forbidding every output or as a recovery power isolation. Separately, invalid-sensor and E-STOP early returns prevent automatic `fsm.update`, including automatic backup-timer evaluation. These facts coexist; neither should be hidden by the phrase “E-STOP safe.”

The opt-in GNC-only profile rejects deployment and omits PB0 recovery attachment/writes and automatic FSM updates. It is not the default profile. The configured ±2 g / strict >2.5 g detection mismatch remains `BLOCKED_UNREACHABLE_THRESHOLD`; this documentation does not authorize changing ranges, thresholds, recovery actions or default profiles.

## 5. Highest-value software integration checkpoints

1. **A transport-independent, receive-only telemetry contract and demonstrable first-use loop.** Explicitly map existing FC/ESP text to any offline/R3 adapter; keep source declaration, authentication, sample validity, sample time, arrival age, replay clock and per-field availability separate. Include old-session callbacks, missing axes/battery, stale/duplicate/corrupt input and offline command rejection in acceptance. No command authority follows from CRC or a recent status.
2. **One signed model/cadence contract anchored to production algorithms.** Reuse the existing PID/Kalman oracle and dual-period work, document axes/units/signs/call timing, preserve the non-ideal failure and test positive/negative disturbances. Do not optimize a “best PID” or infer physical polarity before the plant/configuration is known.
3. **Versioned software evidence for one declared model and the completed product loop.** Reuse manifest/hash practices, retain failure cases and historical artifacts, and add step-convergence/independent-reference checks. The exact-source full gate and actual hosted run must be attributable; software evidence must not promote hardware, RF, CAD, recovery or physical-stability status.

## 6. Current SYSTEM-V1 gate handoff

| Evidence field | State at this inventory-writing step |
| --- | --- |
| Fixed pre-change inventory | `50006f8fd6830a34f16b5e9d2f4e84269c403007` |
| Final tested SYSTEM-V1 source / working-tree binding | `PENDING` — root task records actual source and changed-file binding |
| Current complete local software gate | `PENDING` — this writing task did not run tests/builds |
| Current hosted SYSTEM-V1 workflow | `UNKNOWN` — require actual run URL, checkout SHA and conclusion |
| Offline/UI/adapter acceptance | `PENDING` — do not infer from this capability matrix |
| Current physical board/wiring/sensor/actuator proof | `UNKNOWN` / `NOT_EVALUATED` |
| RF driver/link/region gate | `BLOCKED` / `UNKNOWN`; no transmissions authorized |
| Recovery qualification | `BLOCKED_UNREACHABLE_THRESHOLD` / `NOT_EVALUATED` |
| Physical TVC stability / free-flight qualification | `UNKNOWN` / not authorized |

This document adds no new test execution, measured value, hardware procedure, manufacturing release, transmitter authorization or operational control authority.

[gs-serial]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/ground_station/core/serial_reader.py
[gs-udp]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/ground_station/core/udp_reader.py
[gs-command]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/ground_station/core/command_link.py
[gs-main]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/ground_station/ui/main_window.py
[gs-tests]: https://github.com/guo6x/AI-rocket/tree/50006f8fd6830a34f16b5e9d2f4e84269c403007/ground_station/tests
[gs-parser]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/ground_station/core/telemetry_parser.py
[gs-logger]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/ground_station/core/data_logger.py
[fc-main]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/flight_computer/src/main.cpp
[fc-sensors]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/flight_computer/src/sensor_validity.cpp
[fc-bus]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/flight_computer/src/wire_sensor_bus.h
[fc-pid]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/flight_computer/src/algorithms/pid.cpp
[fc-kalman]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/flight_computer/src/algorithms/kalman.cpp
[fc-command]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/flight_computer/src/command_processor.cpp
[fc-buffer]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/flight_computer/src/command_line_buffer.h
[recovery-audit]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/scripts/recovery_configuration_audit.py
[esp-main]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/esp8266_firmware/src/main.cpp
[esp-router]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/esp8266_firmware/src/relay_router.cpp
[rf-frame]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/rf_lab/telemetry_frame.py
[rf-frame-tests]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/rf_lab/tests/test_telemetry_frame.py
[rf-replay]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/rf_lab/offline_link_replay.py
[rf-reliability]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/rf_lab/reliability_experiment.py
[rf-quality]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/rf_lab/telemetry_quality.py
[model-1d]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/dynamics_sim/physics_engine.py
[model-2d]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/dynamics_sim/physics_engine_2d.py
[model-components]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/dynamics_sim/components.py
[sim-smoke]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/scripts/simulation_smoke.py
[aero-source]: https://github.com/guo6x/AI-rocket/tree/50006f8fd6830a34f16b5e9d2f4e84269c403007/aero_sim
[legacy-config]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/aero_sim/rocket_config.py
[full-check]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/scripts/check.py
[ci-workflow]: https://github.com/guo6x/AI-rocket/blob/50006f8fd6830a34f16b5e9d2f4e84269c403007/.github/workflows/system-v1-software.yml
