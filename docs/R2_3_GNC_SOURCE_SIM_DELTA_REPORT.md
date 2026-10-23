# R2.3 GNC source–simulation delta report

**Contract:** `AA-GNC-OFFLINE-CONTRACT-001`
**Issue:** [#9](https://github.com/guo6x/AI-rocket/issues/9)
**Branch:** `feat/r2-3-offline-gnc-contract`
**Scope:** deterministic, software-only source/oracle reconciliation.
**Evidence ceiling:** `TESTED_SOFTWARE`; no physical mounting, linkage, plant,
or flight conclusion is made here.

This report is deliberately separate from the historical simulation outputs in
`dynamics_sim/`. Those files are evidence of what the old models did; they are
not overwritten or promoted to current firmware evidence.

## Source-to-model trace

| Signal or operation | Current firmware source | Existing model/source | Units and algebra | R2.3 result |
| --- | --- | --- | --- | --- |
| Pitch accelerometer angle | `flight_computer/src/main.cpp:263` | Model states are `theta_x`/`theta_y`; no accepted sensor-frame transform | `atan2(-ax, sqrt(ay²+az²))`, degrees; `ax,ay,az` are g | Software formula is traceable; physical axis/sign remains unknown |
| Roll accelerometer angle | `flight_computer/src/main.cpp:264` | `dynamics_sim/physics_engine_2d.py:4-7, 202-214` calls the second state yaw | `atan2(ay, az)`, degrees | Do not relabel model yaw as firmware roll |
| Gyro feedback channels | `flight_computer/src/main.cpp:260-267` | Legacy models synthesize angle channels; no mounting proof | Firmware pitch uses `gy`, roll uses `gx`; degrees/s | Source channel selection is confirmed; sensor-to-bench transform is unknown |
| Kalman state update | `flight_computer/src/algorithms/kalman.cpp:20-47` | `scripts/gnc_offline_oracle.py` independent float32 implementation | angle/rate in degrees and degrees/s; `dt` in seconds | C++ and oracle are compared row-by-row; no NaN/dt guard is invented |
| PID error | `flight_computer/src/algorithms/pid.cpp:79-80` | `physics_engine_2d.py:83-98` uses `error=current`; `param_sweep.py:19-40` uses target−current | Firmware `error=target-current`, target defaults 0 | Algebraic convention conflict is confirmed |
| TVC command | `flight_computer/src/main.cpp:283-289` | `physics_engine_2d.py:140-145` uses a synthetic negative thrust torque | PID output is degrees; firmware converts to integer and writes `90 + output`, constrained 0–180 | Mathematical command direction is known; physical restoring sign is unknown |
| Rate/absolute limits | `pid.cpp:29-40,99-105` | Legacy models have different profiles and update cadence | FLIGHT ±4° and 0.3°/compute; TESTBENCH ±15° and 1°/compute | Software limits are tested; these are not measured servo speed or plant limits |
| Flight-model controller | `pid.cpp:29-40,79-105` | `aero_sim/control_simulation.py:31-90,105-113` | The flight model uses body-velocity/quaternion terms, different TVC signs and a 2 ms six-DOF callback; its integral cap and actuator mapping are not the firmware PID/Kalman path | Historical trajectory results remain simulation-only and are not a source-equivalence result |
| Control timing | `main.cpp:254-257,309` | `physics_engine_2d.py:195,211-215` | Firmware `micros()` delta, fallback 0.01 s, then `delay(50)`; model integrates 1 ms and computes at 10 ms | Timing mismatch is confirmed; actual hardware period is unmeasured |
| Sensor validity boundary | `sensor_validity.cpp:77-138,148-215` | No equivalent physical claim in legacy models | Explicit identity/configuration/read-length/sample checks; invalid state latches | Fault gating is software-tested; sensor accuracy is not established |

The integer conversion in `main.cpp:284,287` is significant: a small positive
or negative floating PID output can both truncate to a neutral integer command.
The oracle therefore compares the production PID float separately from any
future orchestration/PWM integer trace.

## Five contract conflicts

| ID | Required question | Status | Evidence and boundary |
| --- | --- | --- | --- |
| `R2_3-001` | Polarity convention | `CONFIRMED` software contradiction; `UNKNOWN_MOUNTING` physical sign | Firmware uses target−current and `90+PID` (`pid.cpp:79-80`, `main.cpp:283-288`). The 2D model uses current as error and models negative thrust torque for positive servo (`physics_engine_2d.py:83-98,140-145`); legacy polarity scripts add an outer minus (`test_polarity.py:37-40`). Positive/negative synthetic inputs are compared, but no result is called physically restoring. |
| `R2_3-002` | Control sample rate | `CONFIRMED` mismatch | Firmware performs one update per valid loop and ends with `delay(50)` (`main.cpp:233-309`) plus I/O/reporting work. The model integrates at 1 ms and computes PID every 10 ms (`physics_engine_2d.py:195,211-215`). A per-call rate limit therefore has a different theoretical degrees/second effect. No measured board loop period is claimed. |
| `R2_3-003` | Axis naming/mapping | `CONFIRMED` naming gap; `UNKNOWN_MOUNTING` transform | Firmware names pitch/roll and selects gy/gx (`main.cpp:263-267`); the model calls its second angle yaw (`physics_engine_2d.py:4-7,131-138`). No sign/permutation matrix is accepted without sensor mounting and linkage evidence. |
| `R2_3-004` | Physical plant | `BLOCKED` / `UNKNOWN_PLANT` | Production code has no article-specific mass, CG, inertia, thrust, or servo-linkage data. Legacy values are hypothetical (`physics_engine_2d.py:121-127,177-193`; related studies). Numeric model convergence is therefore simulation-assumption-only and cannot qualify tuning or flight. |
| `R2_3-005` | `dt` path | `CONFIRMED` software behavior; `NEEDS_LATER_HARDWARE_OBSERVATION` for scheduler timing | Firmware replaces `dt<=0` or `dt>0.5` with 0.01 s (`main.cpp:254-257`); PID/Kalman themselves do not normalize `dt` (`pid.cpp:79-87`; `kalman.cpp:20-37`). The offline trace uses positive nominal and irregular intervals. A real loop-period claim remains unmeasured. |

## Deterministic evidence mapping

The offline oracle is independent Python arithmetic in
`scripts/gnc_offline_oracle.py`; the C++ probe includes the production
`pid.cpp` and `kalman.cpp` translation units in
`scripts/gnc_offline_cpp_probe.cpp`. Both consume the same fixed CSV trace.
The trace includes:

- positive and negative signed perturbations, zero/return-to-zero, and a step;
- FLIGHT and TESTBENCH profile limits and per-call rate limits;
- irregular positive `dt` values, including `0.073 s`;
- native production-loop checks for the firmware `dt<=0` and `dt>0.5 s` → `0.01 s` fallback;
- static-zero and positive/negative Kalman angle/rate sequences;
- source-equivalence comparison for every emitted row.

The legacy 1-D sweep/polarity scripts are retained as historical references:
`dynamics_sim/param_sweep.py` uses a direct target-minus-measured input while
`dynamics_sim/test_polarity.py` and `cg_impact_study.py` add an outer negation.
They are therefore not silently selected as the physical sign convention.

The native `gnc_only_bench` cases remain the boundary tests for the actual
production loop and fake peripherals (`flight_computer/test/gnc_only_bench_cases.h`):

- valid sensor → ARM/manual/`auto_on` keeps PA6/PA7 TVC intent and leaves PB0
  recovery unattached/unwritten;
- `deploy_chute` is rejected as `recovery_disabled` without changing recovery
  state or output;
- a sensor fault latches, neutralizes TVC, rejects unsafe commands, and never
  writes recovery;
- E-STOP/RESET neutralizes and then permits re-arming TVC while the recovery
  FSM remains idle.

The existing default native suite and the R0/R1/R2/R2.1/R2.2 checks remain
required. Their counts and the exact post-commit SHA belong in the final
delivery record, not in this pre-commit source report.

## Reproducibility manifest contract

Every committed generated trace under a new versioned R2.3 evidence directory
must carry a manifest with at least:

```json
{
  "schema_version": 1,
  "contract": "AA-GNC-OFFLINE-CONTRACT-001",
  "source_git_sha": "<40-hex exact HEAD>",
  "command": "<exact command line>",
  "input_trace_sha256": "<sha256>",
  "source_sha256": {"<repo-relative source>": "<sha256>"},
  "tool_versions": {"python": "<version>", "compiler": "<version>", "platformio": "<version>"},
  "dependencies": {"pytest": "<version>", "pyyaml": "<version>"},
  "seed": "not_applicable_fixed_trace",
  "physical_hardware": false,
  "plant_or_mounting_claim": false,
  "recovery_output_touched": false,
  "comparison": "PASS",
  "failures": []
}
```

The output must be deterministic for the same source SHA and command. A failed
comparison must remain a failure; no gains, signs, limits, profile defaults,
E-STOP semantics, or historical results may be changed to make it pass.

`source_git_sha` identifies the exact checkout used to generate the trace. If
the generated JSON is committed in a later commit, the delivery record must
also report that artifact commit SHA; do not silently present the later commit
as the source SHA captured by the run.

The generated trace is committed at
`engineering/offline-evidence/r2_3/gnc_offline_trace.json`. It was generated
from source SHA `e8a2f271c7ac647c216130814f307afeb9f77e2d`; the pre-commit
artifact SHA-256 is
`d027dd49c2b2170582af63908f419736306dae9ffee3675962f0b60a8868b182`.

## Physical and release boundary

This report does not establish physical polarity, sensor mounting, servo
neutral/travel/load/rate, plant stability, or flight readiness. It does not
authorize wiring, powering, flashing, RF transmission, servo movement, EDF or
propulsion operation, recovery deployment, or free flight. The `gnc_only_bench`
compile-time isolation remains required for loop-level tests, and recovery
qualification remains blocked under the R2.1 threshold contradiction.

If an implementation-level control-law correction is later justified, record
an engineering change proposal first. The proposal must identify the affected
source contract, signed axis/mounting evidence, acceptance vectors, and a
reviewed regression plan. R2.3 itself makes no such correction.
