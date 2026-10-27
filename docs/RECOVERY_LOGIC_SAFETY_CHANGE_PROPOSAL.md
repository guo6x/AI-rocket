# Recovery launch-detection safety change proposal

Status: **REVIEW REQUIRED — NO PRODUCTION CHANGE MADE**
Review baseline (historical static-audit snapshot): `origin/main` `10a47d5e1e95b1b1b261e4c2eb7790f0601f713a`
Current provenance authority: `main` `7af811392189f25d7219778d1154f9b738ba968f`, hosted software CI run `40455461657`
Audit command: `py -3 scripts/recovery_configuration_audit.py --json`
Evidence ceiling: `TESTED_SOFTWARE` for the static/offline result; recovery qualification remains `BLOCKED`.

This document is an independent safety review of the existing recovery
configuration. It is not an authorization to change a threshold, enable a
deployment output, or operate hardware.

## 1. Production path and provenance

| Element | Current implementation | Units and path |
|---|---|---|
| IMU configuration | `flight_computer/src/sensor_validity.cpp:95-100` writes MPU register `0x1C = 0x00` | MPU full scale `+/-2 g`; the same value is read back on every sample at `:159` |
| Raw decode | `sensor_validity.cpp:172-175` decodes signed big-endian `int16_t raw_az` | ADC counts, signed range `-32768..32767` |
| Conversion | `sensor_validity.cpp:206-211` assigns `sample.az = raw_az / 16384.0f` | `g`, `16384 counts/g`; `SensorSample` documents this in `sensor_validity.h:36` |
| Launch threshold | `flight_computer/src/flight_fsm.cpp:5` | `2.5 g`, compile-time `float` |
| Comparator and persistence | `flight_fsm.cpp:57-69` | `std::fabs(az) > 2.5f` for three consecutive calls, only from `FS_ARMED` |
| Caller | `flight_computer/src/main.cpp:241-255,278-289` | A valid sensor cycle calls `fsm.update(az, altitude, millis())`; a failed cycle disables automatic control and returns before the FSM |
| Cadence | `main.cpp:317` plus sensor/I/O/printing work | `delay(50)` is a nominal ~20 Hz loop, not a measured period |

The threshold/persistence logic is historical (the launch detector is present
in the `b6006c9` lineage); the explicit current sensor configuration and scaling
were added later. This is an integration/configuration contradiction, not a
new R3 change.

## 2. Static boundary result

For the configured scale, the exact representable output is:

```text
raw_az ∈ [-32768, 32767]
sample.az = raw_az / 16384.0
therefore sample.az ∈ [-2.000000000, +1.999938965] g
max |sample.az| = 2.0 g
```

The launch predicate requires `|sample.az| > 2.5 g`. It would require an
absolute raw count greater than `40960`, outside the signed 16-bit source. No
finite sequence of valid samples can satisfy the predicate, so the three-sample
counter can never reach `FS_POWERED` through this automatic path. This proves
the **numeric contradiction**, not physical launch behavior or recovery safety.

The repository audit independently reproduces the result:

```json
{
  "imu_accel_config_hex": "0x00",
  "configured_full_scale_g": 2,
  "production_az_counts_per_g": 16384.0,
  "strict_launch_threshold_g": 2.5,
  "max_abs_numeric_az_g": 2.0,
  "scale_matches_configuration": true,
  "threshold_numerically_reachable": false,
  "status": "BLOCKED_UNREACHABLE_THRESHOLD",
  "recovery_qualified": false
}
```

The `--strict` form intentionally exits `1` for this known blocker. The normal
audit exits `0` because the audit ran successfully; neither mode changes code.

## 3. Saturation, invalid data, delay and safe-state implications

* Under the MPU full-scale configuration, an acceleration beyond the selected
  `+/-2 g` range is expected to saturate before conversion; this clipping
  behavior is a sensor/configuration assumption, not a physical measurement in
  this repository. The current code has no explicit saturation bit or
  stuck-at-limit detector. A clipped value would remain a finite, apparently
  valid sample and still could not cross `2.5 g`.
* The existing all-zero/all-`0xff` IMU-frame checks reject obvious bus faults,
  but do not prove plausibility, vibration tolerance, calibration, or absence
  of a saturated/stuck sensor. Identity and scale registers are checked on each
  sample; short/NACK/nonfinite barometer paths latch a fault.
* `WireSensorBus` enforces a 25 ms sample I/O budget. A budget overrun or other
  sensor failure calls `disableUnsafeControl()` and returns before Kalman, PID,
  or the recovery FSM. This neutralizes TVC and disables AUTO, but it also
  suspends the automatic apogee/timer path for that cycle. Existing command
  handling still services E-STOP, RESET and the separately governed emergency
  deploy request; this review does not alter those semantics.
* `SensorSample.time_ms` is captured when the read begins, while the FSM uses a
  later `millis()` value. `delay(50)`, I2C work and serial output make the actual
  period unmeasured. The three-sample requirement therefore has no qualified
  physical time meaning.
* The GNC-only build omits recovery attachment and FSM updates, but it is an
  opt-in isolation profile. The default firmware recovery behavior is unchanged.

## 4. Engineering change candidates (not selected)

### Candidate A — widen the IMU full-scale range

Change the MPU accelerometer configuration and matching conversion to `0x08`
(`+/-4 g`, `8192 counts/g`) or another explicitly reviewed range, while keeping
the existing strict `2.5 g` and three-sample predicate.

*Condition:* the populated IMU identity, register semantics and expected launch
acceleration must be confirmed for the actual article; the safety review must
accept the resulting resolution/noise trade-off.

*Benefits:* preserves the existing threshold and supplies numeric headroom for
values above `2.5 g`; the static audit can then move to
`NUMERICALLY_REACHABLE_NOT_QUALIFIED`.

*Risks/side effects:* lower counts-per-g, changed attitude/noise behavior,
possible saturation still below the real event, and changed calibration and
fault-injection assumptions. Any other code that relies on the `+/-2 g` scale
must be audited.

*Required verification:* exact register readback and identity tests; signed
conversion boundary tests; saturation and bias/noise analysis; timing and
three-sample persistence analysis; a separately approved restrained physical
test with a frozen configuration. Numeric reachability alone never qualifies
deployment.

### Candidate B — redesign launch detection within a proven reachable envelope

Keep the `+/-2 g` configuration but replace the unreachable feature with a
reviewed, calibrated detector that is strictly inside the proven envelope (for
example, a multi-axis/temporal feature with a threshold at or below the measured
range and explicit anti-vibration bounds). Do not select a new threshold from
this document.

*Condition:* measured sensor bias/noise, mounting orientation, expected launch
acceleration and false-positive consequences must be supplied and reviewed.

*Benefits:* avoids changing the sensor scale and may use multiple independent
signals rather than a single saturated axis.

*Risks/side effects:* less margin to the sensor ceiling, increased false
positive/false negative risk, more state and timing behavior, and a direct
change to a safety-critical deployment predicate.

*Required verification:* formal state-transition review, deterministic boundary
and fault-injection tests, measured restrained acceleration data, timeout and
sensor-loss analysis, and independent approval of deployment behavior.

### Candidate C — fail-closed automatic recovery until a qualified trigger exists

Leave the current values unchanged but explicitly keep automatic launch/recovery
qualification blocked and require a separately authorized, reviewed trigger for
any future recovery experiment.

*Condition:* project safety review accepts that automatic recovery is not
available in the current configuration.

*Benefits:* no unreviewed threshold or actuator change; preserves the current
software safety boundary.

*Risks/side effects:* no automatic launch-to-recovery path is available, so this
is not a flight-ready solution.

*Required verification:* ensure status/telemetry clearly reports the blocked
qualification state and that no test or operator interface treats synthetic FSM
tests as physical readiness.

## 5. Decision and evidence boundary

No candidate is implemented in this branch. Production thresholds, sensor
registers, control polarity, E-STOP, actuator logic, default mode and recovery
deployment behavior remain byte-for-byte unchanged relative to `origin/main`.
The current conclusion is:

* **Confirmed software/static defect:** automatic launch detection is
  numerically unreachable with the configured `+/-2 g` conversion and strict
  `>2.5 g` comparator.
* **Confirmed software behavior:** sensor faults neutralize TVC/disable AUTO and
  skip the FSM for that cycle; emergency command paths remain separately
  governed.
* **Unverified risks:** actual IMU clipping/noise, mounting, acceleration,
  timing, recovery hardware and deployment outcome.
* **No physical evidence:** no board was powered, flashed, wired or actuated.

The only safe next step is an independent safety decision selecting a candidate
and its verification gates. This document does not authorize a human or an
automated system to perform that change.
