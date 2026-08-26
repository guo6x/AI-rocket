# R0 known issues

The list is evidence-based as of audited input commit `b6006c9`. Priorities reflect safety impact, dependency order, and the risk of misleading future work. An open item does not authorize a design change; it identifies work that needs a scoped decision and proof.

## P0 — safety or control authority

### R0-001 — WiFi command downlink is incomplete

- Status: `BLOCKED`
- Evidence: `esp8266_firmware/src/main.cpp` only reads `Serial` and broadcasts UDP. `ground_station/ui/main_window.py` calls `UdpReader.send(...)` without `target_addr`.
- Impact: WiFi arm, E-stop, PID, servo, or recovery commands are not delivered end to end, despite historical claims.
- Required closure: define a command transport and acknowledgement/safety contract, implement both routing segments, then perform software and restrained hardware tests. No architecture rewrite was attempted in R0.

### R0-002 — Recovery FSM evidence was previously based on a different model

- State: open; classification: `TESTED_SOFTWARE`, not hardware verified.
- Evidence: `flight_computer/test_sil.py` defines STARTUP/APOGEE/MAIN_DEPLOY states absent from production `FlightStateMachine`.
- R0 action: production `flight_fsm.cpp` now has native tests. The historical Python script remains preserved and is explicitly classified as historical.
- Remaining gap: no sensor-in-loop, command-parser, servo, or physical recovery test.

### R0-003 — E-stop release can retain prior automatic-control state

- State: open; classification: `UNKNOWN`
- Evidence: `processCommand("estop")` centers servos but does not clear `auto_mode`; `reset` only clears `estop_active`.
- Impact: a reset can resume automatic outputs using retained mode/controller state.
- Required closure: specify the intended fail-safe state, extract command handling for tests, then change behavior with a regression test and restrained bench verification.

### R0-004 — Serial and Serial2 share one command buffer

- State: open; classification: `UNKNOWN`
- Evidence: both input loops in `flight_computer/src/main.cpp` append to global `cmdBuffer`.
- Impact: simultaneous partial commands can interleave or corrupt each other.
- Required closure: use per-interface buffers and test interleaved input without changing the external protocol.

### R0-005 — Sensor presence and read validity are not enforced

- State: open; classification: `UNKNOWN`
- Evidence: MPU6500 initialization prints `OK` without checking the I2C transaction; the loop does not verify that 14 bytes are available. BMP280 reads continue after `bmp.begin()` failure.
- Impact: invalid sensor data can enter estimation, FSM, telemetry, and control as if valid.
- Required closure: define degraded/fault behavior, add testable sensor-adapter boundaries, and validate on restrained hardware.

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
- Evidence: R0 source build uses approximately 58,724 of 65,536 bytes (89.6%).
- Impact: future diagnostics or safety checks may exceed the selected board flash budget.
- Required closure: track size in CI/check output and avoid unbounded feature additions before hardware target confirmation.
