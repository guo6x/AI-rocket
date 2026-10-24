# R2.3 dual-period cadence supplement

**Contract:** `AA-GNC-OFFLINE-DUAL-PERIOD-001`

**Branch:** `feat/r2-3-offline-gnc-contract`

**Scope:** one deterministic software-only comparison of the production
`PIDController` at two offline control cadences.
**Evidence ceiling:** `TESTED_SOFTWARE`; this is not a measured board period,
plant model, mounting result, stability result, or flight result.

## Fixed input and processing

The same piecewise-linear synthetic attitude function is sampled on one
physical time axis from 0 through 2000 ms.  It contains a positive ramp to
`+6 deg`, a hold, a step to `-6 deg` at 720 ms, a negative hold, a ramp back
to zero, and a zero tail.  It has no mass, inertia, thrust, linkage, sensor,
or other physical parameter.

Each cadence owns a fresh production `PIDController::FLIGHT` state.  The
production C++ translation unit performs the integral update, integral cap,
derivative calculation, `±4 deg` output limit, and `±0.3 deg` per-call rate
limit.  The probe then applies the exact `main.cpp` conversion:

```text
constrain(90 + (int)PID_output, 0, 180)
```

The 10 ms and 50 ms schedules are both offline assumptions.  The 50 ms value
is not a measurement of the flight computer scheduler.

## Results

| quantity | 10 ms | 50 ms |
| --- | ---: | ---: |
| control calls | 200 | 40 |
| theoretical per-call rate limit | 30 deg/s | 6 deg/s |
| float PID minimum / maximum | -4 / 4 deg | -3 / 0.084 deg |
| integer servo-command transitions | 22 | 6 |
| maximum absolute float-to-command quantization error | 0.999999762 deg | 0.999999762 deg |

At the 40 common physical timestamps (50–2000 ms), the 10 ms versus 50 ms
float PID difference is maximum `5.200000048 deg`, RMS `2.254336377 deg`.
The integer command difference is maximum `5` counts, RMS `2.1213203436`
counts.  These are cadence and quantization effects of the production
controller path, not a claim that either schedule is stable on hardware.

## Reproducibility and boundary

The paired trace and manifest are stored at
`engineering/offline-evidence/r2_3/gnc_dual_period_trace.json`.  The manifest
records the fixed input hash, source-file SHA-256 values, source Git SHA,
compiler/Python/pytest/PyYAML/PlatformIO versions, command, sample counts,
metrics, `seed: not_applicable_fixed_trace`, and `physical_hardware: false`.

The existing 49-input/34-output C++/Python oracle evidence remains unchanged.
No production gains, signs, defaults, E-STOP behavior, recovery behavior, or
physical actuator constraints were modified.  Physical sensor mounting,
servo/linkage direction, actual board period, plant dynamics, and recovery
qualification remain unresolved.
