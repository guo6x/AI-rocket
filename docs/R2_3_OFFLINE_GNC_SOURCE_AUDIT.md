# R2.3 Offline GNC Source–Simulation Reconciliation

**Status:** pre-execution source audit completed; deterministic Codex-run software tests pending.

**Branch:** `feat/r2-3-offline-gnc-contract`, branched from R2.2 `f2af1326db5ea627c20d5b3c2045b707ecf72d5e`.

**Issue:** [#9](https://github.com/guo6x/AI-rocket/issues/9). **PR #7 is not merged**.

This is a source audit and independent offline verification stage. It is **not** a new PID tuner, hardware bring-up, rocket flight simulator qualification, or recovery qualification.

## Concrete discrepancies confirmed from existing source

| Property | Production GNC-only firmware | Existing Python models | Audit result |
|---|---|---|---|
| Pitch/roll accelerometer formulas | Pitch: `atan2(-ax, sqrt(ay²+az²))`; roll: `atan2(ay,az)` | `physics_engine_2d.py` state uses `theta_x/theta_y`, calls second axis *yaw* | Sensor-to-physical frame transform **unknown**; do not relabel yaw as roll |
| Gyro channels | Pitch uses `gy`, roll uses `gx` in Kalman update | Historic models generate synthetic angle channels and do not prove gyro mounting orientation | Orientation and sign remain **unknown** |
| PID input convention | `error = target - current`; target defaults zero; `servo = 90 + PID(output)` | `PIDController2D.compute` uses `error = current`; `physics_engine.py` assumes positive servo yields negative plant torque | **Algebraic polarity inconsistency.** Only physical mounting can establish restoring direction |
| Legacy 1D scripts | Same production PID math is **not** called | `param_sweep.py` uses `pid.compute(0, measured)`; `test_polarity.py` and `cg_impact_study.py` add an outer minus | Opposite sign conventions require explicit model/source mapping |
| Controller update cadence | One compute per valid `loop()`; `delay(50)` plus sensor, serial, telemetry work; actual period is unmeasured | 2D engine integrates at 1 ms, calls its own PID every 10 ms | Simulation 100 Hz vs firmware **at most nominal ~20 Hz**, not direct evidence equivalence |
| Rate limiting | `FLIGHT` 0.3 degrees/**compute**; `TESTBENCH` 1 degree/**compute** | Models sometimes describe rate limit as fixed per step while using 100 Hz | A 0.3°/call cap implies a theoretical 30°/s at 100 Hz versus at most ~6°/s at 20 Hz. These are software command limits, not measured servo speed |
| dt treatment | `dt = (micros-lastTime)/1e6`; invalid/`>0.5s` reset to 0.01 s | Simulated sensors and control use fixed separate scheduling | Need boundary-case and irregular-dt tests, not silent normalization |
| Physical plant | No currently measured article geometry, mass, inertia, thrust or linkage sign | Models use varied 1 kg / 1.15 kg, 0.2/0.5 m and hypothetical thrust | Physical stabilization quality **UNKNOWN** |

## Why R2.3 matters

The historical hardware demonstration (GY-91 → dual SG92R movement responding to tilt) is preserved. But output movement is not itself proof that the **physical feedback sign** stabilizes an independently identified plant. Python models that achieve a stable inverted pendulum may be using the opposite error convention, different sample rate and different fictitious geometry from production firmware.

The correct next step is to test whether the **same source control law** generates the same output for the same synthetic measurement and timing trace; then separately show which plant/mounting assumptions are needed to call that output physically corrective. Avoid changing gains, signs or saturation solely to force synthetic convergence.

## Deliverables for Codex

1. `docs/R2_3_GNC_SOURCE_SIM_DELTA_REPORT.md`: trace table with source-line paths and exact status per discrepancy.
2. An independent **Python oracle** of production PID/estimator step semantics with fixed input vectors and expected JSON/CSV outputs.
3. A native test runner exercising the actual C++ `PIDController`, `KalmanFilter` and, where needed, the real `gnc_only_bench` orchestration under fakes; do not test a copied “equivalent” C++ implementation instead.
4. An offline comparison using exactly the same inputs/dt across Python/C++, with sign tests in both directions, zero neutral, drift-free static vectors, large input, saturation/rate-limit, jitter and fault transitions.
5. Optional **synthetic** plant sign matrix with both polarities deliberately modeled; never pick the “working” polarity as the actual hardware mounting.
6. Reproducible output manifest: project SHA, input hashes, script command, dependencies, random seed and limitations. Use a new versioned location. Do not overwrite legacy CSV/JSON/PNGs.
7. If adding `scripts/check.py` steps, keep existing historical software gates and make classifications explicit.
8. A final report that separates `SOURCE_EQUIVALENCE_PASS/FAIL`, `SIM_ASSUMPTION_ONLY`, `UNKNOWN_PHYSICAL`, and `BLOCKED`, with a clear STOP rather than an artificial “stable” claim.

## Non-negotiable scope boundaries

- No hardware, board photograph, cabling, flash, sensors, WiFi/LoRa transmission, servo movement or EDF operation.
- No gains/limits/sign correction in production, no trajectory guidance or navigation-target tracking.
- No changes to E-STOP/RESET, sensor faults, the recovery-disabled profile, or original firmware defaults.
- `R2_1-005` recovery `±2g` versus strict `>2.5g` stays blocked.
- If a real-control-law correction is justified, record an engineering change proposal with acceptance prerequisites. Do **not** silently apply it in R2.3.
- No merge. Codex must test and push a clean, exact-HEAD branch; independent review follows.

## Who does what

**Assistant:** repo history/source review, signed contract, cross-check of results, independent PR review.

**Codex:** local executable oracle, native code/test harness, offline simulations, full regression and tracked evidence.

**Owner:** no current action; physical mounting/servo direction only needs a later observation if the project resumes restrained hardware work.
