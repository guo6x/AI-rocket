# R2.1 Real Asset Registry & Multi-Bench Architecture

## Why this exists

Project Ad Astra is not being developed as one monolithic vehicle BOM. The intended development model is to mature major technical capabilities on separate, traceable benches and integrate them only after each line has earned its own evidence.

The repository previously centered physical intake around `AA-TVC-BENCH-001`. That remains valid for TVC mechanical work, but it is not the project-wide hardware inventory.

R2.1 introduces two additional authority layers:

- `engineering/assets/project-asset-registry.yaml`: project-level owned assets and bench tools.
- `engineering/experimental-lines.yaml`: technical-line/article assignments, readiness, blockers, and next gates.

## Evidence semantics

A completed purchase record supplied by the project owner is accepted as ownership evidence for the project asset registry. This proves ownership of the purchased item class/order variant; it does not by itself prove current wiring, exact as-used geometry, pinout, calibration, or hardware functionality.

Those later claims still require the appropriate bench evidence.

This distinction is deliberate:

- ownership can be confirmed at project level;
- article assignment is configuration control;
- physical wiring/geometry is bench evidence;
- hardware behavior is verification evidence.

## Current owned capability

The current asset base is already sufficient to plan a useful low-energy GNC/avionics bench without new procurement.

Core owned assets include:

- APM32F103C8T6 core board;
- GY-91 order variant specified as MPU9250 + BMP280;
- two SG92R metal-gear 9 g servos;
- ESP8266 ESP-01S;
- ESP32-S3 DevKitC-1 N16R8;
- ST-LINK V2;
- CH340G USB-TTL;
- USB logic analyzer;
- digital multimeter;
- 830-hole breadboard and jumper wires;
- LM2596S adjustable buck module;
- 10 kg / 0.1 g electronic scale;
- two SX1278 RA-02 LoRa modules and associated 433 MHz RF assets.

The closed LoRa-cable transaction is explicitly excluded.

## Technical lines

### AA-GNC-BENCH-001

Purpose: state estimation, stabilization logic, controller behavior, and actuator-command verification.

This is the strongest near-term physical line because the project already owns the MCU, sensor, two servos, programmer, serial adapter, logic analyzer, multimeter, and prototyping hardware.

Historical flash, sensing, dual-servo and stabilization reports are recovered,
not first-time bring-up. R2.1 closes current software compatibility/validity
deltas first; the next physical observation is selected from that audit rather
than asking for the whole historical bench again.

### AA-AVIONICS-BENCH-001

Purpose: sensing, power, command, logging, communications, and fault/interface work.

Two runtime compatibility questions remain hardware-gated after software audit:

1. APM32 uses an explicit experimental compatibility environment that retains the historical STM32 core/72 MHz/64 KiB/20 KiB assumptions; it is not a native APM32 port.
2. ESP-01S now has a separate 1 MB `esp01_1m` environment while NodeMCU-v2 remains the historical development target; boot/power/current R1 transport are not hardware-proven.

A source build is not hardware evidence for either mismatch.

ESP32-S3 is preserved as a separate candidate node; it does not automatically replace the existing flight-control path.

### AA-RF-BENCH-001

Purpose: independent telemetry-link experimentation using the owned RA-02 pair and 433 MHz RF assets.

This line stays independent from the primary flight-control path until interfaces, regional operating constraints, and bench configuration are explicit.

### AA-TVC-BENCH-001

Purpose: mechanical two-axis actuation, gimbal geometry, motion/interference, and serviceability.

The project owns two SG92R servos, but the current asset registry contains no purchased EDF and no confirmed frame/gimbal hardware. Therefore TVC CAD remains downstream of real mechanical inputs.

### AA-RECOVERY-BENCH-001

Purpose: recovery-state logic and later low-risk actuator/mechanism verification.

Current status is software foundation only. The R1 state-machine work remains reusable, but there is no dedicated physical recovery mechanism assigned.

### AA-PROPULSION-SCIENCE-001

Purpose: foundational chemistry, materials, instrumentation, thermofluid analysis, cold-flow architecture, and propulsion-system learning.

Near-term useful work is deliberately focused on safe lab fundamentals, public literature, measurement, modeling, instrumentation, materials compatibility, and inert-fluid experiments.

The project asset registry does not authorize energetic propellant preparation, mixing/casting instructions, ignition development, or unsupervised motor/combustion testing.

### AA-SYSTEM-INTEGRATION-001

Purpose: integrate matured technical lines only after configuration, interfaces, evidence, and blockers are explicit.

System integration does not upgrade a subsystem's evidence level merely because it is connected to other hardware.

## Recommended execution order

1. GNC compatibility and hardware bring-up planning.
2. Avionics target/power/interface audit.
3. Human flashing/wiring/bench execution only where software cannot cross the physical boundary.
4. Capture repeatable evidence and update hardware status.
5. Resume TVC concept intake when EDF/frame geometry exists.
6. Run RF and recovery as independent capability tracks.
7. Keep propulsion science foundational until appropriate facilities and supervision exist.
8. Integrate only mature lines.

## Work allocation

### Assistant can do directly

- maintain the project asset registry;
- maintain technical-line architecture and requirements;
- review repository state and compatibility evidence;
- specify test gates and evidence format;
- independently review Codex changes;
- sequence the project and prevent cross-line scope creep.

### Codex should do next

- audit APM32F103C8T6 compatibility with the current STM32 firmware/toolchain;
- audit ESP-01S compatibility with the current ESP8266 NodeMCU-v2 target;
- add project-asset/multi-bench schema checks to the unified software gate;
- prepare a safe, exact GNC/avionics bench bring-up worksheet;
- do not claim hardware success and do not require new procurement.

### Human-only boundary

When the software/document work has exhausted what can be proven remotely, the project owner performs only the physical boundary steps, such as:

- confirm markings/pin labels;
- connect specified low-energy bench wiring;
- plug in ST-LINK/USB-TTL;
- flash firmware;
- report exact tool output;
- move/observe a servo when explicitly instructed by the approved bench procedure;
- capture photos or logic-analyzer traces.

The repository should then convert those observations into repeatable evidence rather than relying on memory.
