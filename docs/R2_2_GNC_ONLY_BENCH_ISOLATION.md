# R2.2 GNC-only bench isolation

Issue: [#8](https://github.com/guo6x/AI-rocket/issues/8)

This change is software-only and remains on the feature branch. It does not
flash, power, wire, transmit RF, connect a servo, or claim recovery or flight
qualification.

## Baseline before implementation

At input HEAD `99e2458603f0d5dcf24208d5b2b1062b15312973`, the new read-only
`recovery_configuration_audit.py` extracted the current production values rather
than assuming them:

- `ACCEL_CONFIG=0x00`, configured +/-2 g, `16384 counts/g`;
- `sample.az = raw_az / 16384.0f`;
- strict comparator `fabs(az) > 2.5f`, three consecutive samples;
- signed-int16 ceiling `|az| = 2.0 g`, therefore `BLOCKED_UNREACHABLE_THRESHOLD`;
- recovery qualification remains `NOT_EVALUATED`.

The audit's 9 scenarios passed. The unchanged full gate also passed before this
profile work: Ground Station 49, flight native 43, ESP relay 3, deterministic
script tests 134, research 22, and the historical/APM32/ESP source builds all
passed; hardware remained `NOT_EVALUATED`. Its recovery contradiction was
reported as an advisory blocker, not converted to a green recovery result.

## Explicit opt-in profile

`flight_computer/platformio.ini` adds:

- `gnc_only_bench`: STM32 source build with `AI_ROCKET_GNC_ONLY_BENCH=1`;
- `native_gnc_only_bench`: the same native test translation unit under the bench
  macro, with four fake-boundary isolation cases in
  `flight_computer/test/gnc_only_bench_cases.h`.

The default `bluepill_f103c8`, `apm32f103c8_compat` and `native` profiles retain
their historical/R1 recovery behavior. The profile gate is compile-time:

- recovery servo PB0 is not attached or written, including startup neutral;
- ARM does not arm the recovery FSM, and the loop does not run automatic recovery
  transitions or timer/apogee deployment;
- `deploy_chute` returns `NACK recovery_disabled` before recovery state changes;
- TVC PA6/PA7 manual and automatic attitude output remains available after a
  valid sensor sample;
- sensor-invalid handling still latches, disables AUTO and neutralizes TVC;
- ESTOP/RESET semantics remain available and cannot enable recovery output.

No runtime command can turn the profile back into a recovery-output profile.

## Evidence ceiling

Native tests use fake sensors, serial streams and Servo objects to verify software
write intent only. They cover valid sensor manual/automatic TVC control, invalid
sensor rejection and neutralization, ESTOP/RESET/re-arm, command-path
interaction, and attempted recovery deployment. They do not prove physical
servo motion, sensor accuracy, timing, wiring, power, recovery detectability or
flight readiness. Recovery remains `BLOCKED` under `R2_1-005`.

Final test/build counts and exact commit SHA are reported in the delivery
response after the post-commit exact-HEAD gate and push.
