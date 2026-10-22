# R2.1 Historical Hardware Recovery Findings

## Executive finding

The project should not be treated as first-time hardware bring-up.

Cloud repository records describe a prior real-hardware phase in which controller firmware, GY-91 sensing, two TVC servos, ESP8266 telemetry, ground-station interaction, and attitude-driven stabilization had already been exercised.

At the same time, the public repository snapshot does not contain a modern immutable evidence bundle for those runs, and one important WiFi claim conflicts with the source that was published later. The correct engineering action is therefore:

**recover -> reconcile -> minimally regress changed paths -> re-baseline**

not:

**erase history -> repeat everything from zero**.

## What the cloud history explicitly reports

Historical sources report:

- flight-controller firmware was flashed and running;
- GY-91 I2C communication and sensor data were working;
- two SG92R TVC servos had PWM drive verified;
- ESP8266-01S UDP relay firmware had been flashed;
- ground station supported WiFi/serial operation;
- historical verification prose says WiFi command uplink produced physical servo deflection;
- `auto_on` enabled attitude stabilization.

These claims are now indexed machine-readably in:

`engineering/historical-hardware-capabilities.yaml`

## What current source still preserves

The current flight-control path still contains the same basic stabilization architecture:

1. read inertial data;
2. derive raw pitch/roll;
3. update the Kalman filters;
4. when AUTO is enabled, compute PID outputs;
5. write corrected commands to the pitch/roll servos.

So the historical self-stabilization capability was not conceptually removed by R0/R1.

R1 changed the command-safety and transport-governance layer around it, especially ESTOP/reset, parser/dispatcher behavior, ACK/NACK, and WiFi relay semantics.

## Important controller-target clue

The initial published `flight_computer/platformio.ini` at `b6006c9` already contained:

`upload_flags = -c set CPUTAPID 0x2ba01477`

with a comment explicitly describing support for a domestic-compatible MCU.

That means the APM32-vs-STM32 naming mismatch was likely already part of the historical hardware reality, rather than a new 2026-10 discovery.

The repository still needs a formal APM32 compatibility baseline, but it should not pretend nobody has ever flashed the board.

## Important WiFi contradiction

Historical prose says:

- ESP8266-01S firmware was flashed;
- WiFi telemetry worked;
- WiFi command uplink could drive a physical servo.

However, the initial public ESP8266 source at `b6006c9` only implements:

STM32 UART -> ESP8266 -> UDP broadcast telemetry

It has no UDP command receive path back toward STM32.

Therefore at least one of the following must be true:

1. the hardware demonstration used an earlier/local ESP firmware not preserved in the public snapshot;
2. the command-to-servo test used a different path than the later prose implies;
3. the prose overstated which transport had been exercised.

Do not guess which one.

R1 has since implemented a governed bidirectional UDP/UART path in current code, so the engineering problem is now to reconcile historical hardware with the current implementation rather than reconstruct the historical missing source blindly.

## LoRa / 433 MHz status

The project owns SX1278 / RA-02 and 433 MHz RF hardware.

Current cloud search found:

- hardware-reserve references;
- future-plan references to replacing WiFi with LoRa;

but no equivalent production RA-02 firmware or real-link verification record.

Therefore:

- WiFi historical capability: reported;
- LoRa historical capability: not established.

Do not inherit WiFi's status onto LoRa.

## Minimum regression philosophy

A physical step should be repeated only if it closes a present engineering uncertainty, for example:

- current firmware materially changed;
- actual board/target assumptions differ;
- a safety-critical path changed;
- the next engineering decision depends on a fresh measurement;
- the historical working configuration cannot be mapped to the current one.

Examples:

- repeating every basic servo command just because old logs are missing: not automatically required;
- verifying present sensor identity/read validity before current closed-loop work: required;
- verifying R1 ESTOP/reset behavior on the physical servos because that behavior changed after the historical run: required before current hardware qualification;
- re-checking ESP-01S under the current R1 bidirectional relay because the command path changed materially: required for current WiFi hardware status.

## Recommended next action

Codex should perform a historical-to-current delta audit before asking the user to touch hardware.

The output should be a table with:

- historical capability;
- historical source;
- current source continuity;
- changed code/configuration since the hardware run;
- whether physical regression is needed;
- smallest regression that would close the current gap.

The first human action should be selected from that delta table, not predetermined.
