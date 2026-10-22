# Codex Task — R2.1 GNC/Avionics Compatibility Closure

Work from branch:

`feat/r2-1-real-assets-multi-bench`

Branch base was latest main at task creation:

`f59dc2c5791ee88f3d853112930de55d0c31f4d3`

Do not merge.

## Objective

Important correction from the project owner and cloud-history audit:

This is NOT a first-time hardware bring-up.

Historical repository records explicitly report that the project previously achieved:
- controller firmware flashed/running;
- GY-91 sensor communication and attitude data;
- two SG92R TVC servos physically driven;
- Ground Station / ESP8266 telemetry and command path;
- command uplink producing physical servo deflection;
- `auto_on` attitude stabilization behavior in which filtered pitch/roll feeds PID outputs and the servos move in response.

Current `flight_computer/src/main.cpp` still contains that closed-loop path:
filtered pitch/roll -> PID.compute() -> servo writes.

Therefore the task is to RECOVER, RECONCILE, and RE-BASELINE an already demonstrated hardware capability against current code and purchased hardware, not to assume the hardware has never worked.

Close as much of the historical-evidence recovery and current-target reconciliation as possible without requiring unnecessary repeated physical work.

Do not start TVC CAD, propulsion work, PID tuning, free-flight preparation, or recovery actuation.

## 1. Read the new R2.1 authorities first

- `engineering/assets/project-asset-registry.yaml`
- `engineering/experimental-lines.yaml`
- `engineering/current-baseline.yaml`
- `engineering/bringup/gnc-avionics-bringup.yaml`
- `docs/R2_1_REAL_ASSET_MULTI_BENCH_ARCHITECTURE.md`
- `docs/R2_1_TARGET_COMPATIBILITY_PREAUDIT.md`

Also inspect the latest main research commits so nothing is overwritten.

## 2. APM32F103C8T6 compatibility audit

Current flight target:

`flight_computer/platformio.ini -> bluepill_f103c8`

Purchased controller:

`APM32F103C8T6`

The existing config already includes an OpenOCD CPUTAPID override.

Perform a precise source/toolchain audit for the subset actually used by production firmware:

- PA6
- PA7
- PB0
- USART2
- I2C/Wire
- Servo/timer usage
- millis/SysTick
- flash/RAM/linker limits
- startup/clock assumptions
- ST-LINK/OpenOCD behavior

Use current Geehy APM32F103x4/x6/x8 documentation where needed.

Do not simply declare drop-in compatibility.

Deliver a compatibility matrix with:

- compatible by documented interface
- likely compatible but unproven
- incompatible
- hardware-only proof required

If a dedicated PlatformIO environment or build flag is needed, implement it without deleting the historical STM32 target.

Run the build.

## 3. GY-91 / MPU9250 + BMP280 mismatch

Purchased sensor order specifies:

GY-91 / MPU9250 + BMP280

Current firmware calls the inertial path MPU6500, hard-codes address/scales, and currently lacks robust identity/read-validity enforcement.

Fix this in a testable, scoped way before any physical PID work.

Requirements:

- extract or introduce a small sensor identity/read-validity boundary;
- do not fake a model identity;
- check WHO_AM_I or equivalent supported identity evidence;
- make initialization/read failure observable;
- prevent an invalid read from silently entering control as valid data;
- preserve software-only testability;
- update R0-005 status only to the evidence actually earned.

Do not tune PID.

## 4. ESP-01S target

Current ESP environment:

`board = nodemcuv2`

Purchased module:

`ESP8266 ESP-01S`, default order/spec class is 1 MB flash.

PlatformIO provides `esp01_1m`.

Add a separate ESP-01S target, preserving NodeMCU historical/development target if useful.

Requirements:

- build relay under `esp01_1m`;
- report Flash/RAM;
- confirm source does not depend on NodeMCU-only GPIO;
- use a conservative upload speed suitable for a manually programmed ESP-01S unless there is evidence for higher;
- document boot/program/reset pin requirements;
- do not attempt physical flashing.

## 5. Project-level schema/checks

Extend software checks so R2.1 files cannot silently rot.

At minimum validate:

- project asset IDs unique;
- excluded/closed transaction not treated as owned;
- every asset referenced by `experimental-lines.yaml` exists;
- every article ID unique;
- owned asset does not imply VERIFIED_HARDWARE;
- propulsion-science line retains its prohibited-work boundary;
- bring-up stages remain ordered and human physical actions cannot become READY before their prerequisites.

Integrate into `scripts/check.py` with deterministic tests.

Do not make missing physical evidence fail the software structure gate.

## 6. Produce the exact human handoff, but do not execute it

First determine whether a new physical action is actually needed.

If historical evidence plus current code is sufficient for a given fact, do NOT ask the user to repeat it just to recreate history.

Only request a physical regression where:
- the hardware target has changed or is mismatched;
- current firmware materially changed the behavior;
- the old claim cannot be mapped to the current configuration;
- or a present evidence gap blocks the next engineering decision.

Then create:

`docs/R2_1_GNC_AVIONICS_HUMAN_HANDOFF.md`

It must contain only the next smallest physical action.

The next physical gate is NOT predetermined to be ST-LINK detection.

Choose the smallest regression that closes the highest-value CURRENT uncertainty after historical evidence recovery.

If the exact purchased-board/module form factor still cannot be proven from repository/purchase evidence, the next human action should be only the minimum observation needed (for example, one close-up photo of the relevant board front/back and labels).

Do not give a multi-page sequence of physical actions all at once.

## 7. Verification

Run the full existing gate plus new R2.1 checks.

Report:

- exact HEAD
- changed files
- APM32 compatibility conclusion
- GY-91 identity/validity changes
- ESP-01S build result and size
- R2.1 test counts
- all prior R0/R1/R2 regressions
- exact next human action
- blockers that remain

Commit and push to the same branch.

Do not merge.
