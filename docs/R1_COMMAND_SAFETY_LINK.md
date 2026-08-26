# R1 Command Safety Link

This document explains the governed command link that R1 will implement and test. It is both a design reference for maintainers and an operator-facing statement of what command status does—and does not—mean. The machine-readable authority is `engineering/command-safety-contract.yaml`.

## Scope and evidence boundary

R1 keeps the existing plaintext command vocabulary and adds deterministic parsing, fail-safe state transitions, ACK/NACK responses, isolated input boundaries, unicast WiFi routing, and visible command status. It covers software tests and simulated socket/serial paths only.

R1 does not energize an EDF, trigger physical recovery, tune a physical controller, redesign avionics/CAD, authorize free flight, or create `VERIFIED_HARDWARE` evidence. A green R1 gate can establish only `TESTED_SOFTWARE`.

## Architecture before R1

USB commands reach a parser embedded in STM32 `main.cpp`. Serial and Serial2 share one mutable command buffer. E-STOP centers TVC outputs but leaves automatic mode retained; reset merely clears the latch. The UDP ground-station sender lacks a configured target, and ESP8266 firmware forwards UART telemetry to UDP but has no UDP-to-UART path. There is no machine-readable command acknowledgement contract.

## Governed architecture

```text
CommandPanel plaintext command
              |
        +-----+------+
        |            |
 USB Serial      unicast UDP
        |            |
        |        ESP8266 relay
        |            |
        +-----+------+
              |
       isolated line buffer
              |
    canonical STM32 processor
              |
     state/action decision
              |
        ACK or NACK line
              |
      reverse transport path
              |
 Ground Station SENT / ACKNOWLEDGED /
         NACK / TIMEOUT / FAILED
```

USB and WiFi do not define separate command languages. Both terminate at one processor and one safety state.

## State model

The exclusive control states are `boot`, `idle`, `armed`, `auto_control_enabled`, and `estop_latched`. Link availability and degraded-input status are separate observations; they do not silently change actuator state.

After initialization, the control state is idle: automatic output is disabled and TVC is neutral. `arm` is a new explicit transition to armed. `auto_on` is accepted only from armed and only while recovery is not deployed. If recovery is deployed, `auto_on` returns `NACK invalid_state`, leaves command state armed, and leaves automatic output disabled. E-STOP is a fail-safe latch from any post-boot state. Reset is accepted only from E-STOP and returns to idle—not to the state that existed before E-STOP.

Recovery software state is separate. Resetting the command safety latch does not claim that a physical recovery mechanism was reloaded, repacked, or ready.

## Command boundaries and malformed input

Commands are newline-delimited plaintext with a maximum of 128 bytes. Serial and Serial2 own separate fixed-size line buffers. If a line is too long, that transport discards bytes until its next newline and reports `NACK overlong unknown`; no prefix is executed. Empty, truncated, malformed, missing, extra, non-finite, and out-of-range arguments similarly produce a NACK with no partial state or actuator mutation.

Manual servo values must both be integers in `[0, 180]`. R1 command-boundary ranges for controller gains are Kp `[0, 10]`, Ki `[0, 5]`, and Kd `[0, 10]`. These are input safety bounds, not new tuning recommendations or hardware-qualified values.

## E-STOP and reset

E-STOP performs all of the following as one accepted safety action:

- latch E-STOP;
- disable automatic control;
- reset retained PID history;
- command both TVC outputs to neutral.

Repeated E-STOP is safe and acknowledged. While latched, ordinary arm, auto, manual servo, gain, and profile commands are rejected. A recovery deployment request remains separately governed because it can be safety-relevant during an emergency; its ACK still means only that software accepted the request.

Reset keeps automatic control disabled, clears hidden controller history, keeps TVC neutral, and returns the control state to idle. New `arm` and `auto_on` commands are required. There is no “resume pre-E-STOP” path.

## ACK and NACK

Responses are intentionally small and readable:

```text
ACK <command_name>
NACK <reason> <command_name_or_unknown>
```

Reasons are `malformed`, `invalid_state`, `out_of_range`, `estop_latched`, `unknown_command`, and `overlong`.

ACK means only that the STM32 processor accepted the command. It does not prove that an actuator moved, recovery deployed, a sensor worked, the hardware is safe, or a vehicle is flight-ready.

The ESP relay may issue a NACK for an empty, overlong, or multiline UDP datagram that it refuses to place on UART. It never issues an ACK. Accepted-command ACK always originates from the STM32 canonical processor.

## WiFi target and link loss

The operator must enter an explicit unicast ESP8266 address and command port. Target validation rejects unspecified IPv4, multicast, and the limited-broadcast address `255.255.255.255`; without subnet-prefix or netmask context, it does not independently prove that every subnet-directed broadcast address has been classified. The software does not hard-code, broadcast to, or guess a command destination. A local UDP `sendto()` success becomes `SENT`; it never becomes `ACKNOWLEDGED` without a matching response returned from STM32 through ESP8266.

No usable socket or target is `FAILED`. A sent command with no response becomes `TIMEOUT`. In UDP mode, only an ACK/NACK whose source IP and port match the currently configured ESP command target can resolve the pending command; other response lines are logged as spurious and ignored. A received NACK from that configured source remains a rejection with its reason. Serial response handling is unchanged. Reconnect clears stale pending status and requires new commands. Loss of telemetry or UDP packets does not itself create a new actuator action in R1.

Source IP/port correlation is a transport check, not authentication. R1 does not authenticate or integrity-protect UDP commands and has no request IDs or replay protection. The ESP routes a response to the most recent command client, while one Ground Station permits only one outstanding command. These limitations keep R1-001 blocked, block any operational-hardware claim, and require a single controlled client during future restrained validation.

## Verification strategy

The implementation is accepted as software only when native tests exercise the real command processor and per-interface buffers, ground-station tests exercise target validation and status tracking, simulated UDP tests cover forward command and return telemetry/ACK paths, and both target firmware builds pass. Source-string assertions are not the primary R1 evidence.
