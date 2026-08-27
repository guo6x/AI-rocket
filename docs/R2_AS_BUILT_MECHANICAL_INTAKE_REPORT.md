# R2 As-Built Physical Baseline & Mechanical Design Intake Report

Date: 2026-08-27

R2 base: `38c662d42db68823da8946c4d7f16e247cc79691`

Article: `AA-TVC-BENCH-001`

## 1. R1 to R2 transition

R1 closed the governed plaintext command path at `TESTED_SOFTWARE`. R2 does not extend control logic or start TVC CAD. It creates the physical-input boundary needed before a credible mechanical design can begin.

## 2. Current physical evidence state

The repository contains historical hardware claims, current firmware targets, wiring prose, simulation assumptions, and several CAD generations. It contains no dated physical observation or measurement record that identifies the current article. Therefore the article physical state is `UNKNOWN`, not verified.

## 3. Claimed versus confirmed components

Nineteen inventory entries cover the EDF, controller, WiFi board, sensor module/devices, three servos, power components, bench tools, fasteners, pivots, structure, printed parts, wiring, and any existing TVC hardware. Some electronics and tools are `REPORTED_PRESENT` only because historical prose says they were used. None is `CONFIRMED_PRESENT` or `MEASURED`. The EDF and battery were historically described as pending purchase, and R2 does not infer that they were later obtained.

## 4. Current article definition

`AA-TVC-BENCH-001` is a configuration placeholder for a restrained, low-energy EDF TVC bench. Its assembly status is unknown. Allowed R2 work is static observation, photography, unpowered dimensional measurement, unpowered mass/static balance measurement, and software-only intake preparation. Manufacture, powered EDF work, structural qualification, free flight, and hardware verification claims are prohibited.

## 5. Staged measurement dependencies

The plan contains 40 total measurements. Priority remains an execution-order hint; each item now separately declares the engineering gates that actually depend on it.

At the initial no-evidence state, the deterministic blockers are:

- inventory observation: 1 grouped photo/presence/reuse record;
- CAD start: 19 active blockers;
- motion verification: 5 blockers, including two unresolved governed system-range requirements;
- detail design: 3 active blockers;
- article integration: 10 active blockers.

CAD start is limited to actual EDF retention/outlet/cable geometry, both TVC servo identities and body/mount/shaft/horn/cable geometry, a confirmed datum, and the photo inventory. Existing-frame dimensions are conditional: they activate only when observation evidence shows a frame/printed/TVC part is present and selected for reuse. Missing STM32, ESP, sensor-board, power, assembled-mass, and CG measurements do not block the first parametric CAD skeleton. EDF and servo masses are deferred to detail/load sizing and article integration.

## 6. Datum definition

R2 defines a right-handed `DTM-AA-001`: Z follows the nominal EDF/body axis in the intended thrust-vector direction; X is the first transverse TVC axis; Y completes the frame. The origin is the center of a physical EDF reference plane selected during measurement. Every physical direction and feature remains `TBD_MEASURED` or `TBD_CONFIRMED_ON_ARTICLE`, so no alignment with historical CAD is assumed.

## 7. Mass and CG status

All component masses, assembled mass, longitudinal CG, transverse CG status, date, evidence, and uncertainty remain `UNKNOWN`. The guide defines electronic-scale mass, a two-support static reaction method, and a balance-point cross-check. No powered or thrust-derived method is allowed.

## 8. Interface register

Eight interfaces cover EDF-to-gimbal, gimbal-to-frame, servo-to-frame, horn/linkage, gimbal/pivot, electronics/frame, moving wiring, and power/frame. All are `BLOCKED_BY_MEASUREMENT`; attachment types and fit dimensions are not selected.

## 9. TVC requirement baseline

The baseline requires EDF retention, two-axis motion, a defined neutral geometry, protected wiring, inspectability, removable EDF, replaceable servos, accessible fasteners, and a feasible assembly sequence. Required pitch/roll range and hard-stop intent are `TBD_SYSTEM_REQUIREMENT`; they cannot be obtained by measuring a servo. Available servo range may come from measurement or a model-specific datasheet, while available mechanism range comes from later CAD verification. Acceptance must prove `available mechanical motion >= required TVC motion envelope`. Linkage clearance, material, wall thickness, infill, fastener size, and structural strength remain unresolved. Historical ±15-degree, M3-like, 74 mm, and SG92R geometry is not adopted.

## 10. Historical CAD conflicts

The early, pro, v3, NX, full-vehicle, and printed-output generations are classified as historical reference. They assume conflicting EDF naming/sizes and hard-coded servo, wall, pivot, exit, and clearance geometry. Some may become topology reuse candidates after measurement-driven re-parameterization, but none is released for manufacture.

## 11. AeroForge intake readiness

The `TVC_ASSEMBLY_V1` intake now has two readiness levels. Concept intake depends on inventory plus CAD_START and is currently `BLOCKED`; when ready, it permits only parametric CAD/design exploration. Design-review intake additionally depends on motion, detail, and article-integration evidence and is also `BLOCKED`. Neither state authorizes manufacture, accepts a design, verifies structure/hardware, or supports flight.

## 12. Blocking human inputs

The user workflow is split into four phases. Phase A is one grouped photo inventory that resolves presence, identity, article inclusion, and reuse intent. Phase B contains the minimum CAD-start geometry—18 fixed measurement items after the photo inventory, plus existing-structure dimensions only if reuse is selected. Phase C covers available motion, moving wires, masses, materials, and hardware detail. Phase D covers electronics, optional included power items, full service envelopes, assembled mass, and CG.

## 13. Tests and checks

`scripts/r2_physical_baseline_check.py` recursively parses the YAML, validates article/component/measurement/interface references, evaluates evidence-backed conditional dependencies, rejects unsupported `MEASURED` states and manufacture-release statuses, prevents historical CAD from supplying current numeric requirements, verifies every AeroForge input group against the measurement dependency map, and checks the staged human checklist. Eight behavioral tests cover power and STM32 non-blocking behavior, EDF and servo CAD blockers, evidence-backed absent-frame handling, evidence rigor, release prohibition, and historical-CAD isolation.

## 14. Changed files

R2 adds the as-built authority, evidence templates, TVC requirements, AeroForge intake, user worksheet/checklist, mass/CG guide, this report, and the R2 gate. Historical CAD and physical-design assets are not modified.

## 15. Next action after measurements

The user should complete Phase A photo inventory first, then only the active Phase B CAD-start items. Once inventory and CAD_START are ready, AeroForge concept intake can begin a parametric TVC design exploration. Motion verification, detail design, article integration, and formal design review remain separately blocked until their own evidence and governed system requirements are complete.
