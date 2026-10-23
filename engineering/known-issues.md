# R0/R1/R2.1 known issues

Initial findings used public comparison anchor `b6006c9`; later R0/R1 closures and the current R2.1 updates are labeled separately below. The R2.1 audit input is `e9510e61b6de518b272ea6fdb8433bbab4c501c5`, not the historical tested binary. Priorities reflect safety impact, dependency order, and the risk of misleading future work. An open item does not authorize a design change; it identifies work that needs a scoped decision and proof.

## P0 — safety or control authority

### R0-001 — WiFi command downlink is incomplete

- State: closed in R1 at `TESTED_SOFTWARE`; hardware remains `UNKNOWN`.
- Evidence: `engineering/command-safety-contract.yaml`; native command/relay tests; 27 ground-station tests including source-correlated simulated UDP ACK/NACK and telemetry return; STM32/ESP8266 target builds.
- R1 action: explicit unicast target, UDP-to-UART relay, canonical STM32 processor, ACK/NACK return, timeout/failed UI states.
- Remaining hardware gate: integrated physical ESP8266/STM32/UART/WiFi testing. The link is not `VERIFIED_HARDWARE` and is not approved for operational hardware use.

### R0-002 — Recovery FSM evidence was previously based on a different model

- State: open; classification: `TESTED_SOFTWARE`, not hardware verified.
- Evidence: `flight_computer/test_sil.py` defines STARTUP/APOGEE/MAIN_DEPLOY states absent from production `FlightStateMachine`.
- R0 action: production `flight_fsm.cpp` now has native tests. The historical Python script remains preserved and is explicitly classified as historical.
- Remaining gap: no sensor-in-loop, servo, or physical recovery test.

### R0-003 — E-stop release can retain prior automatic-control state

- State: closed in R1 at `TESTED_SOFTWARE`; physical neutralization remains `UNKNOWN`.
- Evidence: canonical processor native regression proves AUTO ON → ESTOP → RESET returns idle and cannot resume AUTO without new ARM/AUTO commands.
- R1 action: ESTOP latches, disables AUTO, resets PID history, and selects neutral TVC outputs; reset preserves disabled AUTO and neutral outputs.
- Remaining hardware gate: actual actuator neutral, timing, and repeated E-STOP/reset behavior on an accepted restrained control bench with propulsion isolated; this is a future evidence criterion, not authorization to wire or power hardware now.

### R0-004 — Serial and Serial2 share one command buffer

- State: closed in R1 at `TESTED_SOFTWARE`.
- Evidence: `CommandLineBuffer` instances are separate for Serial and Serial2; native interleaving and overlong-discard regression tests pass.
- R1 action: each transport has a fixed 128-byte boundary and independently discards an overlong line until newline without executing a prefix.
- Remaining hardware gate: simultaneous physical USB/UART traffic has not been measured.

### R0-005 — Sensor presence and read validity are not enforced

- State: R2.1 software closure; classification ceiling `TESTED_SOFTWARE`; current physical identity/validity remains `UNKNOWN`.
- Prior finding: identity, initialization and read lengths were unchecked; invalid data could enter estimation/FSM/control.
- Current boundary: `sensor_validity.*` + checked `wire_sensor_bus.h`; explicit supported WHO_AM_I IDs/addresses, checked configuration/readback, exact read lengths and BMP280 raw compensation; invalid values are omitted rather than fabricated zero. A sensor fault latches until reboot, neutralizes TVC, disables AUTO and prevents invalid data from entering Kalman/PID/FSM. ARM/AUTO_ON/SET_SERVO report `sensor_invalid`; ESTOP/RESET/emergency command semantics are retained.
- Software evidence: native fake-bus/production-main regressions and both controller source builds; final counts/resources are in `docs/R2_1_COMPATIBILITY_CLOSURE_REPORT.md`.
- Remaining closure: actual installed sensor identity/configuration, sample/fault behavior and bounded response on the accepted restrained bench; no calibration/noise/physical actuator result is inferred.

## P1 — engineering baseline blockers

### R0-006 — PID parameters conflict and none is hardware-qualified

- State: open; classification: `UNKNOWN`
- Evidence: firmware FLIGHT `1.0/0.1/0.3`; firmware TESTBENCH `1.65/0/0.45`; legacy optimizer `1.2/0.2/0.4`; dynamics TUNED `2.0/0/0.5`; documents also cite `0.58/0/0.15` and ranges.
- Impact: selecting a value by filename or prose can create unstable behavior.
- Required closure: freeze measured plant parameters first, then define a versioned testbench profile and validate from low authority under physical restraints.

### R0-007 — Current physical configuration is unknown

- Status: `BLOCKED`
- Evidence: documents alternate among 70 mm, 74 mm, and 90 mm EDF assumptions; masses range from 0.386 kg to 1.15 kg; CG assumptions range from 0.2 m to 0.8 m.
- Impact: simulation, controller, CAD, load, and verification results cannot be tied to one physical article.
- Required closure: create a measured configuration manifest with datum definitions, mass, CG, component model/serial, geometry, and photos before control claims.

### R0-008 — Dynamics scripts use inconsistent control polarity and plant assumptions

- State: open; classification: `PROTOTYPE`
- Evidence: `param_sweep.py` and `fine_tune.py` feed the PID sign differently from `cg_impact_study.py` and `test_polarity.py`; damping, thrust, mass, CG, and controller timing vary.
- Impact: `sweep_results.csv`, recommendations, and report conclusions are not interchangeable.
- Required closure: choose one signed coordinate convention, add model-level tests, and regenerate results into versioned outputs without overwriting historical artifacts.

### R0-009 — Simulation results lack full provenance

- State: open; classification: `PROTOTYPE`
- Evidence: tracked JSON/PNG/CSV artifacts do not consistently embed source commit, exact input file hash, model version, dependency versions, and command.
- Impact: results cannot be reliably reproduced or mapped to code revisions.
- Required closure: add an output manifest/versioned run directory for future runs; preserve all existing results as historical.

### R0-010 — `rocket_config.py` is a legacy solid-flight baseline, not project truth

- State: open; classification: `STALE`.
- Evidence: it defines a 75 mm body, fins, launch rail, geographical launch site, and Estes motor while the current safe objective is an EDF bench.
- R0 action: label it `LEGACY_FLIGHT_BASELINE` and route current status to `engineering/`.
- Remaining gap: legacy generator/viewer text still needs a future provenance-aware archival pass if those assets are republished.

### R0-011 — CAD generations are mixed and not configuration-controlled

- Status: `BLOCKED`
- Evidence: root generators, `tvc_design`, NX scripts, and multiple output directories use different coordinates, dimensions, names, and absolute paths. No manifest links an output hash to a generator and input set.
- Impact: no asset can be assumed to be the current manufacturing design.
- Required closure: inventory the intended physical article first; then select or create a controlled assembly in a separate scoped task. R0 does not redesign CAD.

### R0-012 — CAD verification scripts overstate results

- State: open; classification: `HISTORICAL`
- Evidence: `verify_v10.py` reports failed joints/sections but exits 0. `verify_rocket.py` mixes positive- and negative-X generations and exits 0. `verify_viewer.py` proves file presence and displayed mesh statistics only.
- Impact: automation can report success without engineering acceptance.
- Required closure: separate asset/version checks, return nonzero on failed assertions, and define the exact geometry contract before using these scripts as gates.

### R0-013 — Many historical tools contain absolute Windows paths

- State: open; classification: `HISTORICAL`
- Evidence: generators and NX journals reference `D:\AI_rocket` or `d:\AI_rocket` directly.
- Impact: workflows are not portable and can write to unintended locations.
- Required closure: clean paths only when a generator is selected for continued use; do not mechanically revive every historical version.

### R0-014 — Hardware claims have no repeatable repository evidence

- Status: `BLOCKED`
- Evidence: Markdown claims sensors, wiring, servo motion, flashing, and bidirectional communication, but no dated procedure/result/configuration bundle is tracked.
- Impact: `VERIFIED_HARDWARE` cannot be assigned.
- Required closure: use a hardware test-record template that captures article ID, wiring, firmware commit, procedure, raw result, operator/date, and pass criteria.

## P2 — maintainability and clarity

### R0-015 — `CODE_WIKI.md` is empty

- State: open; classification: `STALE`
- Impact: the filename suggests an information source but contains no content.
- Required closure: either populate it from an approved documentation need or mark it historical; it was not deleted in R0.

### R0-016 — Historical completion language remains inside preserved assets

- State: open; classification: `STALE`.
- Evidence: reports and HTML use terms such as “final”, “industrial-grade”, “completed”, and “verified”.
- R0 action: add authority routing and legacy classification rather than rewriting historical records.
- Remaining gap: downstream viewers that bypass README/engineering may still show stale claims.

### R0-017 — STM32 flash headroom is limited

- State: open; classification: `TESTED_SOFTWARE`
- Evidence: historical R0 exact-main used 58,724/65,536 flash bytes; review-corrected R1 used 58,764 bytes. The final R2.1 frozen source uses 55,136/65,536 bytes (84.1%) and 3,060/20,480 RAM (14.9%) for the BluePill/APM32 compatibility builds; sizes are tracked by the unified gate.
- Impact: future diagnostics or safety checks may exceed the selected board flash budget.
- Required closure: track size in CI/check output and avoid unbounded feature additions before hardware target confirmation.

## R1 remaining command-link limitations

### R1-001 — UDP commands are unauthenticated and lack integrity/replay identity

- Status: `BLOCKED` for operational hardware use.
- Evidence: R1 intentionally retains a minimal plaintext UDP protocol with no authentication, integrity tag, sequence/request ID, or replay protection. Ground Station source IP/port correlation is only a transport check and does not close this issue.
- Impact: another host on the same reachable network could inject commands; responses cannot be cryptographically attributed or uniquely correlated across clients.
- Required closure: select a scoped threat model and authenticated/request-identified protocol before treating WiFi control as operational hardware authority.

### R1-002 — Command-link closure has no physical integration evidence

- Status: `BLOCKED`; classification remains `UNKNOWN` for hardware.
- Evidence: R1 uses native logic tests, simulated sockets, and source builds only.
- Impact: UART wiring, voltage levels, baud integrity, ESP association, packet loss, RF range, real actuator neutralization, and operator timing remain unverified.
- Required closure: execute a versioned, restrained, low-energy hardware procedure with EDF and recovery actuation disabled.

### R1-003 — Relay response routing supports one most-recent command client

- State: open; classification: `PROTOTYPE`.
- Evidence: ESP8266 stores one last command source IP/port, and Ground Station permits only one outstanding command.
- Impact: concurrent clients can supersede response routing; R1 does not provide multi-client arbitration.
- Required closure: keep a single authorized operator/client during any future bench validation or add request/client identity in a separately scoped protocol hardening task.

### R1-004 — Directed-broadcast classification requires network context

- State: open; classification: `PROTOTYPE`.
- Evidence: Ground Station target validation rejects unspecified IPv4, multicast, and limited broadcast `255.255.255.255`, but has no subnet prefix or netmask input.
- Impact: software alone does not independently prove that every subnet-directed broadcast address is classified and rejected.
- Required closure: provide explicit network context in a separately scoped link-hardening task if directed-broadcast classification must become a software proof. This is not an authentication control.


## R2.1 real-asset / multi-bench blockers

### R2_1-001 — Purchased controller is APM32F103C8T6, not the nominal STM32F103C8T6 target

- Status: `BLOCKED` for hardware bring-up claims.
- Evidence: project asset registry records APM32F103C8T6; `b6006c9` already carries a domestic-compatible TAP-ID override. R2.1 audits the used subset and adds an opt-in `apm32f103c8_compat` build retaining the STM32 core/72 MHz/64 KiB/20 KiB assumptions. See the compatibility matrix for official device/errata and installed-core evidence.
- Impact: source compatibility is plausible but not sufficient to claim successful flashing, clock/peripheral equivalence, boot behavior, or hardware execution.
- Remaining closure: observe exact board markings/pin labels first; only unresolved startup/clock/debug/peripheral deltas justify conditional current detect/boot work. Historical flash success does not need blind repetition. No native APM32 port/drop-in claim is made.

### R2_1-002 — Purchased ESP8266 is ESP-01S while the firmware build target is NodeMCU-v2 style

- Status: `BLOCKED` for physical WiFi-link claims.
- Evidence: ESP-01S purchase plus separate `esp01_1m` software build (1 MiB class, conservative DOUT, 115200 upload). NodeMCU development target is preserved. Exact memory use is in `docs/R2_1_ESP01S_TARGET.md`.
- Impact: flash layout, GPIO availability, reset/boot wiring, power interface, and serial pins cannot be assumed equivalent from a successful source build.
- Remaining closure: actual flash population/boot/power and R1 GS -> UDP -> ESP-01S -> UART -> FC -> ACK/NACK return plus telemetry on the accepted bench. Historical command-to-servo prose conflicts with the initial telemetry-only ESP source: this is a historical implementation/configuration gap, not permission to guess missing code.

### R2_1-003 — No repeatable GNC bench hardware evidence bundle exists

- Status: `BLOCKED`.
- Evidence: the project owns the controller, GY-91, two SG92R servos, programmer, USB-TTL, logic analyzer, multimeter, breadboard, and jumpers, but no repository record yet links a physical configuration to flash/boot/sensor/servo results.
- Impact: R0/R1 software cannot be promoted to hardware proof.
- Required closure: freeze a low-energy bench configuration and capture exact board markings, wiring revision, firmware commit, tool output, sensor reads, actuator command behavior, and pass/fail criteria.

### R2_1-004 — Avionics bench power/interface architecture is not yet accepted

- Status: `BLOCKED`.
- Evidence: LM2596S and prototyping assets are owned, but no accepted voltage-domain, current-budget, grounding, connector, or protection configuration exists.
- Impact: hardware should not be wired from historical prose or guessed pinouts.
- Required closure: define and review the bench-only power/interface plan before human wiring.

### R2_1-005 — Existing IMU range and automatic recovery launch threshold do not match

- Status: `BLOCKED` for recovery qualification; pre-existing configuration mismatch, not introduced by R2.1.
- Evidence: production IMU scaling/configuration uses +/-2 g (`16384 LSB/g`), while `flight_fsm.cpp` requires `az > 2.5 g` for launch detection. A valid signed 16-bit sample in this range cannot cross that threshold. Native FSM tests with synthetic higher acceleration exercise logic only, not the configured physical sensor path.
- R2.1 decision: preserve existing scale and FSM thresholds; do not silently retune or broaden this GNC/avionics compatibility task into recovery control redesign. Sensor invalidity is prevented from triggering the FSM.
- Remaining closure: a separate configuration/control-contract decision and corresponding tests before any future recovery qualification. No physical recovery action is requested.
- R2.1 offline follow-up: `scripts/recovery_configuration_audit.py` now reads the production ACCEL_CONFIG register, `az` count-to-g divisor, strict launch threshold, and comparator. It prints an explicit known-blocker status and never grants recovery qualification. Use `--json` to inspect; `--strict` exits nonzero when mathematically blocked. Test coverage: `scripts/tests/test_recovery_configuration_audit.py`. This is read-only static analysis, not a hardware test.

### R2_2-001 — GNC-only bench isolation is software-only

- Status: `TESTED_SOFTWARE`; recovery qualification remains `BLOCKED`.
- Evidence: opt-in `gnc_only_bench` and `native_gnc_only_bench` targets; profile omits recovery-servo attach/write, leaves the recovery FSM unarmed/unupdated, and returns `NACK recovery_disabled` for `deploy_chute`. Native fake-sensor/fake-servo tests preserve TVC manual/automatic control while covering invalid sensors, E-STOP/RESET and attempted deployment.
- Boundary: this profile cannot produce recovery-output intent, but it does not prove physical TVC direction, load, neutral timing, sensor accuracy, or recovery behavior. The default historical firmware profile remains unchanged.
