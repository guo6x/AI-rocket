# R2.1 historical-to-current delta audit

Audit date: 2026-10-23. Input branch: `feat/r2-1-real-assets-multi-bench`.
Input exact HEAD: `e9510e61b6de518b272ea6fdb8433bbab4c501c5`.
This table was written before changing production code for this task.

## Evidence and comparison boundary

This is recovery of a previously demonstrated bench, **not first-time bring-up**.
The initial public snapshot is `b6006c9429ae1a2950917a61b4d2e1cf511ab5ed`.
It is a source comparison anchor, NOT a proven identity of the historically
tested binary. The exact old physical-run firmware/configuration is not known.
Historical source references below mean those files at the input exact HEAD;
their R0 stale/current-proof warnings remain valid.

`HISTORICALLY_REPORTED_HARDWARE` preserves historical reports and the owner's
correction. `CURRENT_CODE_CONTINUITY` means a source path survives, not that it
has been exercised on today's board. Software changes/tests can earn only
`TESTED_SOFTWARE`. A bounded physical regression can earn at most
`RESTRAINED_BENCH_VERIFIED_ONLY` for its exact configuration and behavior, after
an immutable procedure/configuration/result/date evidence record is reviewed.
None of these is PID qualification, vehicle integration or flight release.

## Capability-by-capability delta

| Capability: historical achievement | Historical evidence location | Current code retained at input HEAD | Recoverable public-source/configuration delta | Must physically repeat? | Smallest justified regression (later, gated; not a current instruction) | Maximum evidence afterwards |
|---|---|---|---|---|---|---|
| Controller flashed and running; ST-LINK used | `project-overview.md` hardware/toolchain tables; `hardware-wiring-STM32.md` | `flight_computer/platformio.ini`; `src/main.cpp` setup/loop | `b6006c9` already has `CPUTAPID 0x2ba01477` and domestic-compatible comment. R0 `879167a` scopes BMP280 dependencies; R1 `5aa00cf` / `4d4bf7f` replaces command handling. Purchased APM32 naming is a historical recovery question, not proof of a new board. Current STM32 Arduino startup/linker is not a native APM32 qualification. | No repeat to prove historical flashing. Current target identity/clock and changed firmware need bounded mapping before current qualification. | First unpowered board-marking observation; only if still needed, current-target detect/boot record without actuators. No blind programmer/flash exercise. | Marking alone: `CONFIGURATION_OBSERVED`, not runtime proof. Subsequent boot: restrained logic/debug baseline only. |
| GY-91 I2C and attitude acquisition worked | `project-overview.md` hardware table; `verification-protocol.md` completed sensor row; `hardware-wiring-STM32.md` PB6/PB7 | `main.cpp` IMU read, attitude/Kalman, BMP280 | Order says MPU9250 + BMP280; source says MPU6500, assumes 0x68/0x76 and reset scales, ignores transaction/length failures. Public snapshot to input HEAD retains this deficiency. New identity/validity behavior is required, not reconstruction of basic I2C success. | No repeat of generic I2C discovery. Yes, actual identity and validity of the present configuration before current closed-loop use. | Exact sensor IDs/addresses and a valid stationary sample with checked transactions, plus fail-closed fault behavior on the accepted restrained bench. | Exact sensor/read/fault behavior only: `RESTRAINED_BENCH_VERIFIED_ONLY`; no calibration/noise or attitude-accuracy qualification. |
| Two SG92R units physically driven by PWM | `project-overview.md` SG92R x2 / PA6/PA7; `verification-protocol.md` physical servo row; historical wiring | `main.cpp` PA6/PA7 attach, center and write | Pins and Servo API survive. R1 adds governed arm/state, ESTOP latch, reset/neutral, independent line buffers; R2.1 will add sensor-fault inhibition. Missing raw old logs alone is not a retest reason. | No generic dual-servo/PWM demonstration. Yes, changed safety semantics before present hardware qualification. | Once sensor/power/identity prerequisites pass, only a restrained bounded two-axis command and changed ESTOP/reset/fault neutral/inhibit behavior. | Exact units/configuration/safety response only; not loaded range/rate/torque or flight authority. |
| `auto_on` attitude-driven self-stabilization was exercised | Owner's project-history correction; `project-overview.md` auto_on entry. `verification-protocol.md` desktop-tilt section is a plan, not by itself a completed run. | `main.cpp`: attitude -> Kalman -> `PID.compute()` -> two `servo.write()` calls | Public PID/Kalman implementation and source profile values are unchanged from `b6006c9`; historical prose gives conflicting gains. R1 changes entry/safety/transport behavior; current identity/read guards are missing. Do not claim PID tuning occurred in this task. | No repeat to recover the old self-stabilization fact. A current closed-loop regression is deferred until identity, valid reads, actuator sign/range, plant and restraint evidence exist. | Only after those gates: a separately reviewed bounded response observation using a frozen configuration, not gain tuning or a vehicle test. Not authorized/executed here. | At most configuration-specific restrained response; no stability envelope or hardware-qualified PID profile. |
| ESP8266-01S flashed; WiFi telemetry used; prose claims WiFi uplink moved servo | `project-overview.md`; completed bidirectional row of `verification-protocol.md`; ESP/UART2 section in `hardware-wiring-STM32.md` | `esp8266_firmware/src/main.cpp`, `relay_router.*`; FC `command_processor.*` | **Historical implementation/configuration gap:** public `b6006c9` ESP source is UART -> UDP only and has no UDP receive path. Working missing code/path must not be guessed. R1 supplies current UDP -> UART validation and ACK/NACK return. Historical/current target names NodeMCU (4 MB), purchased ESP-01S class 1 MB. | No repeat of the historical telemetry claim. Yes, current R1 bidirectional route on the actual ESP-01S. | After accepted target/power prerequisites: one governed GS -> UDP -> ESP-01S -> UART -> FC exchange with FC ACK/NACK returning to the sending client and telemetry return; actuator movement is not needed to prove transport. | Current end-to-end transport on that exact bench only; not authentication, RF range, packet-loss, multi-client arbitration or servo dynamics. |
| Ground station WiFi/serial telemetry and command interaction | `project-overview.md` ground-station row; `verification-protocol.md` command/servo claim, subject to the WiFi gap above | `ground_station/core/{udp_reader,serial_reader,command_link}.py`; UI command-status path | R1 adds SENT/ACK/NACK/TIMEOUT/FAILED handling, UDP source correlation and one-in-flight semantics. Historical missing ESP uplink remains unresolved. | No repeat of generic UI/telemetry reception. Current end-to-end confirmation is shared with the single ESP-01S regression, not another full experiment. | Same exact command/return-path record as preceding row, proving FC ACK rather than treating SENT as execution. | Current transport/status behavior only, not operator usability or physical actuator success. |
| LoRa RA-02/SX1278 purchased, no demonstrated link recovered | `project-memory.md` reserve; `verification-protocol.md` future LoRa stage; asset registry `AST-RF-RA02-001` | No production LoRa link path | Ownership is new evidence of assets, not a WiFi-equivalent implementation or physical link. | Not a regression: no historical link to repeat. No LoRa physical action needed for this GNC/avionics closure. | None in this task; independent interface/regulatory/firmware work precedes any later link experiment. | `PURCHASE_CONFIRMED` only; never inherit WiFi verification. |

## Wiring continuity and current uncertainty

Historical PB6/PB7 I2C, PA2/PA3 UART2, PA9/PA10 UART1, PA6/PA7
TVC signals and PB0 recovery signal remain the source comparison basis. The
historical document's TIM3 channel labels are pin alternate-function labels,
not proof of the Arduino Servo library's actual timer allocation. Audit that
library and the installed variant before claiming timer compatibility.

Historical 5 V GY-91 VIN and USB-powered servo wiring are **not** approved
current power instructions. Exact board regulator/level-shifting, oscillator,
pin labels and accepted power arrangement still require configuration evidence.
Recovery hardware, EDF, propulsion, PID tuning and free flight are excluded.

## No-repeat decision and first physical boundary

Preserve historical flash/boot, basic I2C, dual PWM, telemetry and stabilization
as recovered reports; do not repeat them solely to manufacture missing old logs.
Current software work must finish first. The smallest unresolved observation is
the exact purchased controller board/markings, not mandatory ST-LINK detection.
The final handoff will contain only that one action, not the future regressions
listed as audit criteria above.

## Research preservation

Fetched `origin/main` is `f59dc2c5791ee88f3d853112930de55d0c31f4d3`.
Reviewed research commits `44edda1`, `25b0f6c`, `f59dc2c`: the aerospace
knowledge base, source/provenance PoCs and immutable numerical-reference
evidence remain untouched. This task continues the existing R2.1 lineage;
it does not restart from main, cherry-pick research, or merge.
