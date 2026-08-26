# R1 Governed Command & Safety Link Report

Date: 2026-08-26

R1 base: `d40585f77e1b73d270dd9972823a5939cbfcd81a`

Evidence ceiling: `TESTED_SOFTWARE`. No hardware was energized, flashed, connected, moved, or physically verified in R1.

## 1. Before state

At the R1 base, plaintext USB commands reached parsing code embedded in STM32 `main.cpp`; Serial and Serial2 shared one `String` buffer. E-STOP centered TVC servos but retained `auto_mode`, and reset only cleared the latch, so automatic output could resume without a new explicit command. The Ground Station UDP sender required a target that `MainWindow` did not provide. ESP8266 relayed STM32 UART telemetry to UDP but did not receive UDP commands. There was no ACK/NACK contract, timeout distinction, or end-to-end software path.

The R0 base firmware sizes were:

| Target | Flash | RAM |
| --- | ---: | ---: |
| STM32F103C8 | 58,724 / 65,536 bytes (89.6%) | 2,904 / 20,480 bytes (14.2%) |
| ESP8266 NodeMCU v2 | 272,903 / 1,044,464 bytes (26.1%) | 28,404 / 81,920 bytes (34.7%) |

## 2. Command safety contract

`engineering/command-safety-contract.yaml` is the machine-readable authority. It defines boot, idle, armed, automatic-control, E-STOP-latched, link, and degraded-input states. For every retained plaintext command it defines allowed and rejected states, state and actuator effects, ACK behavior, idempotency, safety relevance, UI versus firmware enforcement, malformed handling, and duplicate handling.

The external vocabulary remains `arm`, `auto_on`, `auto_off`, `set_servo:...`, `set_pid:...`, `estop`, `reset`, `deploy_chute`, and the two existing profile commands. R1 does not introduce a parallel WiFi command language.

## 3. Architecture after R1

USB Serial and WiFi UDP converge at one `CommandProcessor`. WiFi uses an explicit unicast Ground Station target, ESP UDP datagram validation, UART forwarding, the STM32 Serial2-specific line buffer, canonical state/action decision, and a plaintext ACK/NACK returned through ESP to the command source. STM32 telemetry continues UART-to-ESP-to-UDP broadcast.

Production command parsing no longer depends on Arduino `String` or a physical Serial object. The processor and fixed input buffer compile under the native test environment.

## 4. ESTOP/reset semantics

An accepted E-STOP transitions the command state to a latch, disables automatic output, resets both PID histories, and selects neutral TVC outputs. Repeated E-STOP repeats the same safe actions. While latched, arm, AUTO, servo, PID, and profile commands are rejected; malformed lines remain malformed and cannot mutate state.

Reset is accepted only from the E-STOP latch. It returns command control to idle, keeps AUTO disabled, resets PID histories, keeps TVC neutral, and disarms only an unlaunched recovery FSM. A new `arm` followed by a new `auto_on` is required. If the recovery FSM is no longer idle or software reports deployment, a new arm is rejected. Reset never clears the recovery-deployed flag or claims physical reloading.

Native regression proves `arm → auto_on → estop → reset → auto_on` ends with `NACK invalid_state`, idle command state, and automatic control disabled.

## 5. Parser design

`flight_computer/src/command_processor.*` performs strict exact-command parsing with atomic decisions. Manual servo arguments are two integers in `[0, 180]`. PID input safety bounds are Kp `[0, 10]`, Ki `[0, 5]`, and Kd `[0, 10]`; these are parser limits, not tuning recommendations. Missing, extra, non-numeric, non-finite, empty, unknown, and out-of-range input returns a typed NACK action with no partial mutation.

The output is a `CommandDecision`: result, action, before/after control state, canonical name, and validated numeric payload. Hardware-dependent application remains in `main.cpp`, after acceptance.

## 6. Serial/Serial2 isolation

`CommandLineBuffer` is a fixed 129-byte object with a 128-byte command limit. STM32 owns one instance for USB Serial and one for Serial2. Interleaving `set_ser` on Serial with `estop\n` on Serial2 and then finishing `vo:90,90\n` on Serial produces two independent lines; it cannot form a mixed command.

When an interface receives byte 129, it discards that interface until newline and emits one `NACK overlong unknown`. It never executes the first 128-byte prefix. The other interface remains unaffected.

## 7. ACK/NACK semantics

STM32 responses are:

```text
ACK <command_name>
NACK <reason> <command_name_or_unknown>
```

Reasons are `malformed`, `invalid_state`, `out_of_range`, `estop_latched`, `unknown_command`, and `overlong`. ESP may issue only a malformed/overlong NACK when a UDP datagram cannot safely become one UART line; ESP never issues an ACK.

ACK means the canonical STM32 software accepted a command. It does not prove physical actuator completion, recovery deployment, sensor health, radio quality, safety, or flight readiness.

## 8. WiFi downlink implementation

Ground Station requires an explicit unicast IPv4 target and command port. Empty, multicast, unspecified, and global-broadcast targets are rejected; no private address is hard-coded or silently guessed. `UdpReader.send()` rejects empty, multiline, or overlong commands and returns a boolean transport result.

ESP8266 validates one command per datagram, forwards it with one UART newline, remembers the most recent command source, and unicasts UART ACK/NACK back to that source. Non-response UART lines continue on the established telemetry broadcast path. ESP setup logging was removed from the shared command UART so relay diagnostics cannot become STM32 commands.

## 9. Link-loss behavior

The UI distinguishes `SENT`, `ACKNOWLEDGED`, `NACK`, `TIMEOUT`, and `FAILED`. A local serial write or UDP `sendto()` establishes only SENT. One outstanding command is permitted per Ground Station so an ACK is not ambiguously correlated. E-STOP can supersede an outstanding command; ordinary commands cannot.

No ACK/NACK within 1.5 seconds becomes TIMEOUT. Invalid target, unavailable socket, disconnected transport, or failed write becomes FAILED. Telemetry inactivity is displayed separately as `TELEMETRY LOST`; it neither proves command failure nor triggers an actuator action. Reconnect clears stale pending state.

## 10. Ground-station changes

The existing UI structure is preserved. The UDP row now asks for listen port, explicit ESP IPv4, and command port. The command panel adds compact link and command-status labels. E-STOP remains a separate always-enabled control. The former local “Armed” checkbox is labeled as a controls lock so it cannot be mistaken for firmware acknowledgement; firmware state remains authoritative.

Serial and UDP responses are parsed by the same `CommandTracker`. ACK/NACK lines are not fed into the telemetry JSON parser.

## 11. Tests

The unified command is `python scripts/check.py`. The first complete R1 run passed:

| Gate | Result |
| --- | --- |
| Python compileall | PASS |
| Engineering YAML | PASS |
| Ground Station and simulated link | PASS — 24 tests |
| Simulation smoke / R0 regression | PASS |
| STM32 Kalman/FSM/command native | PASS — 19 tests |
| ESP relay native | PASS — 3 tests |
| STM32 target build | PASS |
| ESP8266 target build | PASS |
| Hardware | MANUAL / HARDWARE-GATED; not executed |

Behavioral tests cover valid and invalid command parsing, E-STOP/reset regression, duplicate E-STOP, state gates, ranges, malformed/extra/non-finite inputs, overlong discard, interface interleaving, response vocabulary, explicit target validation, sent/ACK/NACK/timeout tracking, a real localhost UDP socket forward/ACK/telemetry-return simulation, visible UI status, and serial newline framing.

## 12. Remaining hardware gates

- Physical STM32 USB and Serial2 command input with simultaneous traffic.
- UART voltage, wiring, baud integrity, framing, restart, and sustained-load checks.
- ESP8266 association/AP fallback, unicast receipt, ACK return, loss, reconnect, range, and interference.
- Measured E-STOP TVC neutral, AUTO inhibition, reset behavior, and timing with EDF disabled.
- Physical sensor validity, servo mapping/load, and recovery mechanism remain outside R1 and unverified.

## 13. Known limitations

UDP commands are plaintext and unauthenticated, with no integrity tag, request ID, replay protection, or multi-client arbitration. ESP sends responses to the most recent command source, and another client could supersede it. These limitations are recorded as blockers for operational hardware use.

The 1.5-second timeout is a Ground Station software observation, not an autonomous flight failsafe. R1 does not add automatic actuator behavior on network loss. The sensor-degraded state is documented but not implemented because sensor-health redesign is outside R1. No hardware result is inferred from source builds or socket simulation.

## 14. Changed files

- Contract and reports: `engineering/command-safety-contract.yaml`, `docs/R1_COMMAND_SAFETY_LINK.md`, this report.
- STM32: `command_processor.*`, `command_line_buffer.h`, `main.cpp`, `flight_fsm.*`, native tests.
- ESP8266: `relay_router.*`, bidirectional `main.cpp`, native test and PlatformIO environment.
- Ground Station: `command_link.py`, serial/UDP return values and target validation, compact status UI, behavioral tests.
- Gate/status: `scripts/check.py`, engineering baseline/component/verification/known-issue files, and engineering README.

No CAD, aero model, PID algorithm/profile value, physical EDF parameter, board target, or recovery mechanical design was changed.

## 15. Exact-head validation

R1 was created from exact `origin/main` `d40585f77e1b73d270dd9972823a5939cbfcd81a`, after verifying it contains R0 head `22edc4f31f932ebc1323698f502e6eb1b95981bc`. Final validation must run `python scripts/check.py`, `git diff --check`, and a clean Git status on the committed R1 head. The delivery response reports the final exact local/remote SHA; a commit cannot embed its own final SHA without changing that SHA.

### Firmware size comparison

| Target | R0 before | R1 after | Delta |
| --- | ---: | ---: | ---: |
| STM32 flash | 58,724 | 58,724 | 0 bytes; 0.00 percentage points of 64 KiB |
| STM32 RAM | 2,904 | 3,172 | +268 bytes; +1.31 percentage points of 20 KiB |
| ESP8266 flash | 272,903 | 273,147 | +244 bytes; +0.02 percentage points of available flash |
| ESP8266 RAM | 28,404 | 28,296 | −108 bytes; −0.13 percentage points of 80 KiB |

STM32 flash remains approximately 89.6%, so limited headroom remains an open engineering risk; R1 adds no net flash bytes but does consume 268 additional RAM bytes for isolated fixed buffers.
