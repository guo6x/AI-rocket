# AI-rocket — R3.2 integration evidence and engineering blockers

**Snapshot date:** 2026-10-25  
**Main commit recorded:** `9e0d335523c7072c6846cb4522ae6009c7ad5179`  
**Document purpose:** current navigation/decision record, not a new test result or physical readiness declaration.  
**Qualification ceiling:** `TESTED_SOFTWARE`; **hardware qualification remains `NOT_EVALUATED`**.

## 1. Integrated stages and precise evidence

| Stage | Integrated PR | What has software evidence | What has **not** been established |
|---|---|---|---|
| R1–R2.2 command, sensor & recovery-isolated GNC | [#7](https://github.com/guo6x/AI-rocket/pull/7) plus earlier R0/R1 closures | Native command/sensor guards, ESTOP/RESET, GNC-only recovery exclusion, five source-target builds | Real hardware safety, actual sensor identity, servo motion, flash/boot or recovery deployment |
| R2.3 GNC source/cadence consistency | [#10](https://github.com/guo6x/AI-rocket/pull/10) | Production C++ PID/Kalman vs independent oracle (49 instructions, 34 numeric rows); two assumed 10 ms/50 ms controller schedules, same synthetic signal; 40 aligned points show different command output | Measured controller loop period, mounting/polarity, plant parameters, physical stabilization |
| R3.0 telemetry-only framing | [#12](https://github.com/guo6x/AI-rocket/pull/12) | Pure offline codec, CRC32, sequence window, duplicate/corrupt/out-of-order replay | RA-02 transceiver behavior; interoperability, authenticated peer, actual RF packets |
| Ground Station rejection reasons | [#14](https://github.com/guo6x/AI-rocket/pull/14) | `sensor_invalid` and `recovery_disabled` NACK display/timeout distinction and IP/port source correlation in simulated transports | Live ESP/STM32 transport or end-to-end hardware confirmation |
| R3.1 reliability observability | [#16](https://github.com/guo6x/AI-rocket/pull/16) | 10 deterministic fault scenarios; 591 generated synthetic frames; 39 generator-side drops; 589 offered datagrams; all 589 independently checked against committed CRC/sequence classifications | Real packet-loss rate, range, airtime, latency, RF reliability |
| R3.2 telemetry quality & precision | [#18](https://github.com/guo6x/AI-rocket/pull/18) | Read-only freshness/status classifier, explicit unauthenticated source, correct invalid/duplicate/stale non-refresh, extreme integer/mixed-clock guards, immutable v2 evidence | True sensor sample time, authenticated origin, truth of telemetry payload, hardware operation |

**Source records:** `engineering/offline-evidence/r2_3/`, `engineering/offline-evidence/r3/`, `engineering/command-safety-contract.yaml`, `engineering/rf-offline-contract.yaml`, `engineering/rf-reliability-contract.yaml`, `engineering/rf-telemetry-quality-contract.yaml`, and corresponding `docs/R2_3_*.md`, `docs/R3_*.md`.

### Latest reported software runs (not re-executed at merge main SHA)

The R3.2 local Codex handoff states that **at feature HEAD `889cbfb5fa43d408c80a694d0d2b3d060b94c51e`**, single-process `py -3 scripts/check.py` exited 0: **379 test executions, 0 failures**, including Ground Station 64, flight native 47, GNC-only native 4, ESP relay native 3, scripts 144, two extra standalone GNC groups 5+5, RF 85, and preserved research regression 22. The two standalone GNC groups also run inside the 144 scripts suite, so the log represents **369 unique test cases at most by that accounting**, not 379 separate cases. Simulation and five source builds (BluePill, APM32-compat, GNC-only, ESP8266 NodeMCU, ESP-01S) passed in that handoff.

The reviewer independently inspected source and replayed committed data, but **did not rerun the complete PlatformIO/PySide build suite at the new merge HEAD**. GitHub commit/merge success alone is not CI PASS. `engineering/verification-status.yaml` contains historical per-test evidence (including an older 49-count Ground Station test entry); do **not** reclassify it as an exact R3.2 merge-HEAD run.

## 2. Open engineering blockers — separated from software acceptance

| ID | Impact / present conclusion | Minimum new evidence for closure |
|---|---|---|
| GNC-P0 physical mapping | Sensor mounting coordinate transform and physical servo/linkage torque sign `UNKNOWN`; legacy dynamics models disagree in sign/axis naming | Configuration-specific mounting/axis documentation and independently reviewed matching physical evidence; no polarity inference from software oracle |
| GNC-P1 actual loop timing | `delay(50)` in production source versus old simulation 10 ms controller step; `50 ms` in R2.3 is a comparison assumption, **not** measured firmware scheduling | Exact target and timed telemetry/control trace, with source version; do not convert assumed period into a hardware fact |
| GNC-P1 plant parameters | Mass, CG, moments, thrust, servo linkage, damping, actuator speed not measured for one controlled article; TESTBENCH 5° non-ideal simulation does not converge | Versioned article-specific measured geometry/parameters and independently reviewed simulation correlation; no claims of physical stability |
| RECOVERY-P0 reachability | Firmware accelerometer range ±2g vs detection condition strictly greater than 2.5g for three samples; `BLOCKED_UNREACHABLE_THRESHOLD / NOT_EVALUATED` | Separately authorized, traceable design review with physical sensing range and failure-mode study. **Do not silently retune** threshold to get a pass |
| RF-P0 sender identity | `session_id` is an unauthenticated label and can change freshness window; CRC is corruption detection, **not** cryptographic authenticity | Threat model, reviewed authenticated receive-only design and negative security tests; no command authority |
| RF-P1 device/region | RA-02 SPI/module revision, connector/antenna match, packet vs 176-byte software framing, relevant radio compliance `UNKNOWN` | Exact module/specification and lawful configuration review, distinct from any approval to transmit |
| TELEMETRY-P0 meaning | `RECENT_UNAUTHENTICATED` means recent syntactically accepted **synthetic receive** only; real sensor sampling time and content truth unknown | Defined capture timestamp semantics and trusted measurement provenance, separate from reception age |
| CMD-P0 operational UDP | Existing WiFi/plaintext command transport has no authenticated sender/replay identity; source IP/port correlation does not provide cryptographic trust | Security design and reviewed software negative tests before considering hardware control authority |
| INTEGRATION-P0 hardware basis | Historic demonstrations exist, but this sequence has no fresh, verifiable board/wiring/power/actuation evidence | Configuration/identity and accepted evidence process; **no automatic hardware operation** |

## 3. Decision rules

1. `TESTED_SOFTWARE` is evidence for the *specific tested source and synthetic/native interfaces only*. Build success is not flash/boot/communications/actuator verification.
2. `UNKNOWN` and `NOT_EVALUATED` stay distinct; a passing build never upgrades a physical gate.
3. `BLOCKED_UNREACHABLE_THRESHOLD` stays blocking; do not quietly tune recovery/sensor range/actuation.
4. Every future artifact identifies exact generator commit, file hashes, inputs, invocation, tests and evidence ceiling. Keep old artifacts immutable. For R3.2, `r3_2_telemetry_quality_clock_guard_v2.json` records source SHA `7947e4a08e7fe9a8f1fb645221892a41cac48424` and is distinct from its later artifact commit `889cbfb5...`.
5. Existing independent RF code is telemetry-only and **must not** be promoted to WiFi/LoRa command authority because the receiver has a `CRC PASS` or `RECENT` status.
6. Hardware, RF transmissions, launch, propulsion and recovery mechanisms are **not authorized** by this document; physical qualification needs separate planning, governance and explicit owner approval.
7. No need to repeat unchanged simulation runs without a substantive new hypothesis, signal, measurement or acceptance criterion.

## 4. Safe, actionable next engineering checkpoint

**R4.0 proposal: evidence consolidation and software-only reproducibility.** Before any physical operations:
- Review and reconcile historical `engineering/verification-status.yaml` and `engineering/known-issues.md` against this current integration snapshot **without rewriting historical test results**.
- Define a machine-readable live `main` software gate report sourced from real current run logs, distinguishing latest verified source SHA, date, and unknown values.
- Add an automated assertion that documentation cannot upgrade `TESTED_SOFTWARE` to `VERIFIED_HARDWARE` without new hardware source evidence.
- Keep control-state changes, flight firmware modifications, RF driver integration and target hardware operations **outside** this documentation task.

**Do not label R4.0 `PASS` merely because this checklist exists.**