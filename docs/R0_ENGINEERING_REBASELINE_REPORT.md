# R0 Engineering Re-baseline Report

Audit date: 2026-08-26

Audited input commit: `b6006c9429ae1a2950917a61b4d2e1cf511ab5ed`

Scope: repository-wide engineering audit, low-energy software corrections, status normalization, and repeatable software verification. No propulsion redesign, free-flight authorization, CAD redesign, history deletion, or physical qualification was performed.

## 1. Executive Summary

The repository contains substantial working software and exploratory engineering material, but it did not represent one controlled physical configuration. R0 establishes a conservative current baseline under `engineering/`, preserves old work as historical/prototype evidence, fixes two testable flight-core defects, restores reproducible builds, and adds one unified software check.

The verified result is limited: ground-station tests pass, production Kalman/FSM native tests pass, the STM32 and ESP8266 sources build, and deterministic simulation smoke checks pass. No item is classified `VERIFIED_HARDWARE`. WiFi command downlink is absent end to end, the physical EDF platform is not configuration-controlled, PID values conflict, and existing CAD is not a manufacturing release.

## 2. Current Real State

### Completed with current evidence

- A branch-isolated R0 audit and non-destructive asset inventory.
- A machine-readable authority layer: baseline, components, parameters, verification, known issues, and legacy classification.
- Ground-station software tests: 16 passed.
- Production flight-core native tests: 8 passed, including launch, burnout, rolling apogee, timer, manual deploy, and reset transitions.
- STM32F103C8 and ESP8266 source builds.
- Read-only simulation smoke checks that reproduce both a convergent prototype case and a divergent firmware-profile case.

### Partially established

- Flight software is `TESTED_SOFTWARE`: source and core tests exist, but peripherals, timing, command parsing, and hardware behavior are not exercised.
- Telemetry uplink segments are `IMPLEMENTED`: the firmware and ground-station paths exist, but integrated packet delivery is not repository-proven.
- Dynamics is `PROTOTYPE`: useful models exist, but plant parameters and polarity are not unified or correlated to hardware.
- Recovery is `PROTOTYPE`: production FSM behavior is tested in native software, while the physical mechanism is unknown.

### Not established

- Current as-built EDF diameter/thrust, total mass, CG, wiring, actuator direction/range, recovery assembly, and article identity.
- Bidirectional WiFi command transport.
- Hardware-qualified PID gains or control authority.
- CAD release, assembly validation, manufacturability, structural margin, or flight readiness.
- Any `VERIFIED_HARDWARE` or physical-flight result.

## 3. Source-of-Truth Conflicts

The old repository had several competing authorities. `aero_sim/rocket_config.py` defines a 75 mm fin-stabilized solid-motor vehicle, while EDF/TVC material cites 70, 74, and 90 mm ducts. Mass values include approximately 0.386, 1.0, and 1.15 kg; CG assumptions include 0.2, 0.4, and 0.5 m and broader prose ranges. None is tied to a measured current article.

PID sources also conflict: firmware FLIGHT is `1.0/0.1/0.3`, firmware TESTBENCH is `1.65/0/0.45`, the legacy optimizer uses `1.2/0.2/0.4`, and a dynamics TUNED case uses `2.0/0.0/0.5`; documents contain additional values. These values have different loop rates, output limits, plant assumptions, and signs, so they are not interchangeable.

R0 makes `engineering/current-baseline.yaml` the status router, production source the implementation authority, and executable checks the software-evidence authority. Full conflict records are in `engineering/parameter-registry.yaml`.

## 4. Software Findings

### Flight computer

- The production FSM and `flight_computer/test_sil.py` were different state models. Native tests now compile and exercise the production `flight_fsm.cpp`; the Python model is labeled historical.
- The rolling five-sample apogee test indexed the ring buffer as if it remained chronological after wrapping. R0 compares samples from the actual oldest index.
- Launch timing depended directly on Arduino `millis()`, preventing deterministic native tests. Time is now injected into arm/launch transitions by `main.cpp`.
- `FS_LANDED` has no production entry path; `launch_alt` and `arm_start_time` are not used for closure logic.
- E-stop reset can retain automatic-mode/controller state, serial interfaces share one command buffer, and sensor reads do not enforce identity/byte-count validity. These remain open rather than being changed without a safety contract.
- The STM32 build dependency was scoped to the native environment, so production could not find BMP280 headers. It is now declared in the STM32 environment.

### Ground station and ESP8266

- The serial-mode plaintext command path exists: `CommandPanel` emits commands such as `arm`, `auto_on`, `set_servo:...`, and `set_pid:...`; `SerialReader.send()` appends only a newline before transmission.
- WiFi-mode command downlink is incomplete because `UdpReader.send()` requires a target address while `MainWindow.on_send_command()` provides none.
- The ESP8266 firmware does not receive UDP command packets or forward them to STM32 serial; it only reads serial telemetry and broadcasts UDP.
- No end-to-end WiFi command acknowledgement or safety contract exists.
- The duplicate quick recovery-deploy action bypassed the dedicated confirmation path and was removed. The dedicated confirmed control remains.
- A queued Qt signal test previously asserted without pumping the event loop. The test now waits through `QCoreApplication.processEvents()`.

## 5. Simulation Findings

The tracked two-dimensional dynamics baseline is reproducible without rewriting results. Under its own prototype assumptions, the TUNED small-angle case converges, while the firmware TESTBENCH profile with a non-ideal 5-degree/15 N case diverges. This is evidence about the model, not the hardware.

Dynamics scripts use inconsistent controller polarity and vary mass, CG, thrust, damping, limits, rates, and delay. The legacy PID optimizer assumes 100 Hz while production firmware nominally loops near 20 Hz. Existing CSV/JSON/PNG outputs do not consistently embed commit, dependency, input hash, and exact command provenance.

The aerodynamic model is reclassified `LEGACY_FLIGHT_BASELINE`. It includes fins, launch rail/location, and solid-motor assumptions and must not be used as the current EDF bench truth.

## 6. Hardware Findings

The repository names STM32F103C8T6, ESP8266, SG92R, GY-91/MPU6500, BMP280, and EDF concepts, but it does not contain one dated as-built manifest tying component identity, wiring, firmware commit, mass properties, photos, test procedure, raw observations, operator/date, and acceptance criteria together.

Historical Markdown statements about power-on, flashing, sensors, servo movement, and bidirectional communication are not accepted as current physical evidence. All hardware verification therefore remains `UNKNOWN` or `BLOCKED`. Safe closure requires restrained, low-authority bench work after the physical configuration is measured and documented.

## 7. CAD Findings

CAD generators, NX journals, TVC variants, output directories, and mesh generations use conflicting dimensions, coordinate conventions, names, and hard-coded paths. No manifest links a generated output hash to a generator, input configuration, dependency version, and source commit.

The existing verifier scripts can inspect presence, bounds, faces, selected radii, watertightness, volume, duplicate vertices, and degenerate triangles. However, some detected failures still return exit code zero, and mixed positive/negative coordinate generations are compared. These scripts do not prove joints, motion envelopes, interference, fastener access, wiring routes, actual component envelopes, tolerances, materials/processes, mass linkage, loads, structural margin, assembly sequence, maintainability, or manufacture.

Consequently every existing CAD/mesh asset defaults to `HISTORICAL` or `PROTOTYPE`; none is released for manufacture or flight.

## 8. Verification Gaps

- No hardware-in-loop, sensor-in-loop, or restrained integrated bench record.
- No sensor identity, calibration, read-validity, noise, drift, or failure-response evidence.
- No actuator neutral/sign/travel/rate/current/load/jam/repeatability record.
- No end-to-end command acknowledgement, loss, reconnect, timeout, or E-stop behavior proof.
- No measured physical plant for simulation correlation or controller qualification.
- No current CAD configuration, release manifest, or mechanical acceptance criteria.
- No structural, thermal, electrical-power, vibration, EMC, recovery-load, or flight-readiness evidence.

## 9. Legacy Assets Classification

No user history or asset was deleted. Detailed per-path classification is in `engineering/legacy-assets.md`. In summary:

- Old milestone/status documents and team reports: `HISTORICAL` and often `STALE`.
- Solid-motor aero configuration/results: `LEGACY_FLIGHT_BASELINE` / `HISTORICAL_RESULT`.
- Dynamics scripts/results: `PROTOTYPE` / `PROTOTYPE_RESULT` unless tied only to superseded assumptions.
- Old SIL state machine: `HISTORICAL_TEST_MODEL`.
- CAD generators, viewers, STL/STEP outputs, and NX journals: `HISTORICAL` or `PROTOTYPE`, not manufacturing authority.
- Empty `CODE_WIKI.md`: `STALE_EMPTY`, preserved.

## 10. Top 10 Engineering Risks

1. WiFi control is described historically but is not implemented end to end.
2. E-stop release semantics can restore retained automatic-control state.
3. The current physical article and its mass properties are unknown.
4. Competing PID profiles could be selected without matching sign, rate, limit, or plant.
5. Sensor failures and short reads can enter control/state estimation without a defined fault response.
6. Shared serial command buffering can interleave partial commands.
7. Simulation polarity and plant assumptions differ across scripts.
8. CAD filenames/version labels can be mistaken for a released design despite missing assembly/manufacturing proof.
9. Historical “complete/verified/final” language can be mistaken for current evidence.
10. STM32 flash use is 89.6%, limiting room for safety diagnostics and future code.

## 11. Recommended Next 5 Actions

1. **Freeze a safe as-built bench manifest:** assign article ID and datum; measure mass, CG, EDF/component identity and geometry; record wiring and photos. This unlocks every downstream model and test.
2. **Define the fail-safe command contract:** specify power-up, arm, E-stop, reset, timeout, acknowledgement, link-loss, and recovery-command behavior before changing transport code.
3. **Make sensor/command boundaries testable:** add checked sensor adapters, per-interface command buffers, parser tests, and explicit degraded states without energizing propulsion.
4. **Unify and version one signed dynamics baseline:** bind measured plant inputs, firmware loop timing, actuator mapping, limits, and one controller profile; add provenance manifests to outputs.
5. **Run restrained low-authority hardware gates:** first sensors and servos without EDF, then guarded EDF/TVC tests with current limits and independent E-stop; store raw records. CAD release work follows measured envelopes and loads.

## 12. Changed Files

R0 changes are grouped as follows:

- Engineering authority: `engineering/README.md`, four YAML registries, `known-issues.md`, and `legacy-assets.md`.
- Unified verification: `scripts/check.py`, `scripts/simulation_smoke.py`, and `requirements-dev.txt`.
- Flight core/build: `flight_computer/platformio.ini`, production FSM header/source/call site, and native tests.
- Ground station: event-loop-safe tests, WiFi contract tests, and removal of the confirmation-bypassing quick deploy action.
- Authority warnings: repository README, old project/status/wiring/verification reports, historical aero/CAD publishers, viewer, and old SIL script.
- This report.

No tracked historical file was deleted and no generated physical design was overwritten.

## 13. Tests Run

Initial audit failures were retained as findings: ground-station tests had 12 passes and one queued-signal failure; native tests lacked an available native compiler; the STM32 build failed because the BMP280 dependency was scoped incorrectly.

Final unified command: `.\.venv\Scripts\python.exe scripts\check.py`

| Gate | Final result |
| --- | --- |
| Python compileall | PASS |
| Engineering YAML parse | PASS |
| Ground station | PASS — 16 tests |
| Deterministic simulation smoke | PASS |
| Production flight core native | PASS — 8 tests |
| STM32F103C8 source build | PASS — RAM 14.2%, flash 89.6% |
| ESP8266 source build | PASS — RAM 34.7%, flash 26.1% |
| Hardware gates | MANUAL / not executed / not part of software exit code |

The unified software check exits zero only when all software steps run and pass; it does not short-circuit after a failure and cannot promote hardware status.

## 14. Remaining Unknowns

The actual article configuration, measured parameters, installed component identities, wiring, power budget, sensor health, actuator mapping, recovery mechanism, structural state, restraints, and safe operating envelope remain unknown. The correct current conclusion is therefore: software baseline `TESTED_SOFTWARE`; simulations `PROTOTYPE` or `HISTORICAL`; hardware `UNKNOWN`/`BLOCKED`; free-flight readiness not established and outside R0 scope.
