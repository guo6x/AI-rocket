# R2.1 GNC / avionics compatibility closure

Date: 2026-10-23 (Asia/Shanghai).
Branch: `feat/r2-1-real-assets-multi-bench`.
Fetched and verified input exact HEAD:
`e9510e61b6de518b272ea6fdb8433bbab4c501c5`.

## Outcome and evidence ceiling

This is a historical-capability recovery and software-delta closure, not a first
hardware bring-up. No hardware upload, wiring, power-on, actuator movement, RF
transmission or device configuration was performed. Target builds and controlled
native/Qt/socket tests earn `TESTED_SOFTWARE` only; current hardware qualification
remains pending. The historical claims have not been erased or promoted to
current `VERIFIED_HARDWARE`.

The final delivered commit and remote/local SHA parity are reported in the
delivery response. This document cannot embed its own final commit SHA without
changing that SHA. The unified gate is also rerun on the committed exact HEAD
before push; that result is part of the delivery response.

## Historical recovery and current deltas

The seven-field, per-capability audit was saved **before production changes**:
`R2_1_HISTORICAL_TO_CURRENT_DELTA_AUDIT.md`.

Recovered reports include controller flash/boot, GY-91 I2C/attitude, two physical
SG92R outputs, ESP8266-01S telemetry, ground-station interaction and owner-reported
`auto_on` self-stabilization. The source still preserves attitude -> Kalman ->
PID -> pitch/roll servo writes. PID algorithms, profile gains and plant models
were not tuned or changed.

The comparison anchor `b6006c9429ae1a2950917a61b4d2e1cf511ab5ed` is the initial
public source, not a known identity of the old tested binary. It already has the
domestic-compatible `CPUTAPID 0x2ba01477` override. Therefore APM32 compatibility
is configuration recovery, not evidence that the board has never been flashed.

Historical WiFi command-to-physical-servo prose conflicts with that snapshot's
UART-to-UDP-only ESP implementation. This remains a **historical
implementation/configuration gap**; no missing code or working transport is
invented. The current R1 bidirectional command/ACK/NACK path is the subject of
future bounded regression. RA-02/SX1278 ownership has no recovered physical link
evidence and inherits none of WiFi's status.

## APM32 conclusion

See `R2_1_APM32_COMPATIBILITY_MATRIX.md` for the exact official sources, hashes,
installed-toolchain audit and four-way classification of the used interfaces.
The explicit opt-in `apm32f103c8_compat` environment retains the historical
STM32 Arduino core, 72 MHz startup, 64 KiB flash and 20 KiB RAM assumptions. It
is deliberately **not** a native APM32 port or a declaration of drop-in runtime
compatibility. The historical `bluepill_f103c8` target remains the default.

The actually used subset is PA6/PA7/PB0 GPIO with Servo's TIM2 scheduler,
USART2 PA2/PA3, debug USART1 PA9/PA10, I2C1 PB6/PB7, SysTick/millis, startup,
linker and ST-LINK/OpenOCD. Historical TIM3 pin alternate-function labels are
not the actual Servo backend. Exact board markings, oscillator/startup, silicon
revision/errata, debug/flash-driver behavior and current physical timing remain
configuration-specific uncertainties.

## GY-91 identity and validity conclusion

`SensorValidity` is independent of Arduino and uses a small exact-register-IO
boundary shared by native fakes and the production Wire adapter. It accepts
only checked MPU6500 `WHO_AM_I=0x70` or MPU9250 `0x71` at `0x68/0x69`, and
BMP280 `0x58` at `0x76/0x77`. A GY-91 purchase label does not identify the
populated silicon. MPU9250 magnetometer support is not claimed.

Wake/axis/full-scale registers and BMP configuration are written and read back;
the existing +/-2 g and +/-250 deg/s conversion assumptions are explicit. IMU
14-byte and BMP raw/calibration transactions must return the exact length.
BMP280 compensation now uses checked raw inputs rather than library getters
that hide I2C failures; native reference-sample tests cover the conversion.
Unknown identities, short reads, NACKs, invalid calibration, disabled/invalid raw
samples and nonfinite/out-of-range barometer results fail closed.

Every control cycle refreshes validity before ARM/AUTO/manual-servo command
dispatch. A failure is latched until reboot, disables AUTO, resets PID history
and selects neutral TVC; invalid data never enters Kalman/PID/recovery FSM.
`NACK sensor_invalid` makes blocked control requests observable on both command
transports. ESTOP/RESET and explicit emergency deployment semantics are retained;
RESET cannot clear the sensor latch. Fault telemetry omits invalid numerical
attitude/altitude rather than fabricating zero. Native production-main fakes
verify software write intent, not physical neutralization or recovery movement.

BMP busy/NVM status and sensor-IO scheduling have explicit bounded software
handling. The STM32 Wire HAL timeout is compiled as `I2C_TIMEOUT_TICK=10`;
`Stream::setTimeout()` would not configure that backend. A sample budget is not
a measured physical E-STOP latency guarantee. Exact timing, sensor accuracy,
orientation, calibration, noise, plausibility under motion and physical fault
response remain unverified; no PID or flight qualification is earned.

The audit also makes a pre-existing configuration mismatch explicit: the
unchanged +/-2 g IMU scale cannot reach the recovery FSM's `az > 2.5 g` launch
threshold. `R2_1-005` records this as a blocker for future recovery qualification.
Native synthetic high-acceleration FSM tests prove logic, not feasibility of
that configured physical path. Neither sensor scale nor FSM threshold is
silently retuned; recovery work remains out of scope.

The Ground Station must honor explicit invalid sensor frames without inserting
default zero attitude into plots/3D. Its small R2.1 guard retains raw/structured
logging and command ACK semantics while visibly marking invalid sensor data.
Legacy telemetry without the new validity field remains supported, not silently
reclassified as newly checked sensor evidence.

## ESP-01S conclusion

See `R2_1_ESP01S_TARGET.md`. NodeMCU-v2 is preserved; `esp01_1m` is a separate
1 MiB-class, 115200-upload, conservative DOUT target. Source uses WiFi/UDP and
UART0, not NodeMCU-only GPIO or Serial remapping. Boot/reset pin requirements
are reference constraints, not an instruction to flash now.

Verified ESP-01S size: Flash **273,147 / 761,840 bytes (35.9% program region)**;
RAM **28,296 / 81,920 bytes (34.5%)**. Nominal physical flash is 1,048,576 bytes;
the linker reserves space, so it is not the same denominator as the application
region. Build success does not prove actual flash population, power, boot,
association, UART or current bidirectional physical link operation.

Both ESP builds selected a pre-existing ignored local `wifi_config.h` via
`__has_include`. Its contents were neither read nor changed, and neither it nor
the binaries are committed or shared. The listed resources/hashes describe that
local-config build, not a guaranteed identical clean-checkout artifact. No WiFi
association or hardware operation was performed.

## Deterministic R2.1 authority gate

`scripts/r2_1_check.py` and isolated mutation tests validate unique asset/unit,
article, line and stage IDs; closed-transaction exclusion; declared ownership
sources; line/asset and baseline/article references; purchase-vs-hardware evidence
boundaries; and the propulsion-science prohibited-work boundary.

Bring-up dependencies are explicit, ordered and acyclic. Physical stages cannot
be marked READY/COMPLETED before prerequisites; mandatory sensor/observation
gates cannot be waived with `NOT_REQUIRED`. Only explicitly optional conditional
programmer/flash stages may be omitted with a rationale. Active physical chains
must contain a completed software prerequisite.

Current physical records/raw artifacts are confined, SHA-256-bound, stage/article
matched and carry date/operator/method/tool/exact source commit. READY requires
precondition evidence; COMPLETED requires a valid PASS outcome. Pending physical
work requires no invented record. JSON output keeps `structure_status` separate
from `hardware_status: NOT_EVALUATED`. A software validator is not human review
or proof that a record's asserted physical event really happened.

## Verification

The final unified command was run against the reviewed working tree and passed:

| Gate | Result and evidence |
| --- | --- |
| Python syntax / engineering YAML | PASS; compileall and recursive YAML parse |
| Ground Station | PASS; 49 tests |
| Simulation smoke | PASS; deterministic TUNED/TESTBENCH checks |
| Flight native | PASS; 43 tests, including the production `main.cpp` fake-bus harness |
| ESP relay native | PASS; 3 tests |
| BluePill source build | PASS; 55,136/65,536 Flash (84.1%), 3,060/20,480 RAM (14.9%); SHA-256 `58b830790b16c51303a984de30b9636fafbfe07cbb3aac6c73831641f84c65d4` |
| APM32 compatibility build | PASS; same size and SHA as the marker-only compatibility alias; no board execution |
| NodeMCU source build | PASS; 273,147/1,044,464 Flash (26.2%), 28,296/81,920 RAM (34.5%); SHA-256 `0b4e0a22405f2cfc4004ce8efd3a0d05845b0c4258a3f721060149003d8cae2a` |
| ESP-01S `esp01_1m` build | PASS; 273,147/761,840 Flash (35.9%), 28,296/81,920 RAM (34.5%); SHA-256 `e6a37fb554ef1420495cf9aa96a42c2bae0db307002237650f9a5a163ef9a209` |
| R2 physical structure | PASS; hardware remains manual/evidence-gated: 40 planned measurements, blockers inventory 1, CAD_START 19, motion 5, detail 3, article integration 10 |
| R2.1 deterministic structure | PASS; reports `hardware_status: NOT_EVALUATED` |
| R2/R2.1 script tests | PASS; 125 tests (9 retained R2 + 116 R2.1) |
| Preserved research regressions | PASS; 22 offline tests; research files unchanged |

The unified command's final lines were `R0 SOFTWARE CHECK: PASS`, `R1 COMMAND
SAFETY CHECK: PASS`, and `R2.1 SOFTWARE REGRESSION CHECK: PASS`. These are
software/static/controlled-test results only; no upload, power, RF, UART runtime,
actuator movement or current hardware acceptance occurred. The ESP images were
built with the pre-existing ignored local `wifi_config.h` described above.

## Physical decisions

Do **not** repeat generic historical flash/boot, I2C discovery, basic two-servo
PWM, telemetry reception or the fact that self-stabilization had been exercised
merely because old raw logs are missing. Their recovered historical status is
preserved.

Current qualification eventually needs only the relevant changed/uncertain
subsets: actual sensor identity/validity; current R1 ESTOP/reset and new sensor
fault inhibit on the accepted restrained actuator bench; and the current
GS -> UDP -> ESP-01S -> UART -> FC -> ACK/NACK return plus telemetry route.
Transport can be proven without servo motion. Current closed-loop regression is
deferred until sensor, actuator sign/range, plant and restraint evidence exists.
There is no EDF, propulsion, recovery actuation, PID tuning or free-flight task.

The sole next human action is in `R2_1_GNC_AVIONICS_HUMAN_HANDOFF.md`: one clear
unpowered controller-board front photo showing the MCU marking and pin labels.
It does not request detection, rewiring, flashing, power-on or servo movement.

## Changed files

Exact repository changed-file list relative to the fetched input HEAD (ignored
`.pio` outputs and the untracked local WiFi configuration are excluded):

```text
docs/R2_1_APM32_COMPATIBILITY_MATRIX.md
docs/R2_1_COMPATIBILITY_CLOSURE_REPORT.md
docs/R2_1_ESP01S_TARGET.md
docs/R2_1_GNC_AVIONICS_HUMAN_HANDOFF.md
docs/R2_1_HISTORICAL_HARDWARE_RECOVERY.md
docs/R2_1_HISTORICAL_TO_CURRENT_DELTA_AUDIT.md
docs/R2_1_REAL_ASSET_MULTI_BENCH_ARCHITECTURE.md
docs/R2_1_TARGET_COMPATIBILITY_PREAUDIT.md
engineering/README.md
engineering/assets/project-asset-registry.yaml
engineering/bringup/gnc-avionics-bringup.yaml
engineering/command-safety-contract.yaml
engineering/component-status.yaml
engineering/current-baseline.yaml
engineering/experimental-lines.yaml
engineering/historical-hardware-capabilities.yaml
engineering/known-issues.md
engineering/verification-status.yaml
esp8266_firmware/platformio.ini
flight_computer/platformio.ini
flight_computer/src/command_processor.cpp
flight_computer/src/command_processor.h
flight_computer/src/main.cpp
flight_computer/src/sensor_validity.cpp
flight_computer/src/sensor_validity.h
flight_computer/src/wire_sensor_bus.h
flight_computer/test/fakes/Arduino.h
flight_computer/test/fakes/Servo.h
flight_computer/test/fakes/Wire.h
flight_computer/test/main_loop_cases.h
flight_computer/test/sensor_validity_cases.h
flight_computer/test/test_kalman.cpp
ground_station/tests/test_sensor_validity_ui.py
ground_station/ui/main_window.py
scripts/check.py
scripts/r2_1_check.py
scripts/tests/test_r2_1_check.py
```
