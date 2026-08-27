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

## 5. Required measurements

The measurement plan contains 35 P0 items required before CAD: 12 EDF, 9 TVC-servo, 4 electronics, 4 power, 3 existing-structure, 2 mass/CG, and 1 datum-confirmation item. All are currently `MISSING`. P1 items cover harness detail, service access, transverse CG status, and candidate hardware access; one P2 item defers accessory masses.

## 6. Datum definition

R2 defines a right-handed `DTM-AA-001`: Z follows the nominal EDF/body axis in the intended thrust-vector direction; X is the first transverse TVC axis; Y completes the frame. The origin is the center of a physical EDF reference plane selected during measurement. Every physical direction and feature remains `TBD_MEASURED` or `TBD_CONFIRMED_ON_ARTICLE`, so no alignment with historical CAD is assumed.

## 7. Mass and CG status

All component masses, assembled mass, longitudinal CG, transverse CG status, date, evidence, and uncertainty remain `UNKNOWN`. The guide defines electronic-scale mass, a two-support static reaction method, and a balance-point cross-check. No powered or thrust-derived method is allowed.

## 8. Interface register

Eight interfaces cover EDF-to-gimbal, gimbal-to-frame, servo-to-frame, horn/linkage, gimbal/pivot, electronics/frame, moving wiring, and power/frame. All are `BLOCKED_BY_MEASUREMENT`; attachment types and fit dimensions are not selected.

## 9. TVC requirement baseline

The baseline requires EDF retention, two-axis motion, a defined neutral geometry, protected wiring, inspectability, removable EDF, replaceable servos, accessible fasteners, and a feasible assembly sequence. Pitch/roll range, hard stops, linkage clearance, material, wall thickness, infill, fastener size, and structural strength are deliberately unresolved. Historical ±15-degree, M3-like, 74 mm, and SG92R geometry is not adopted.

## 10. Historical CAD conflicts

The early, pro, v3, NX, full-vehicle, and printed-output generations are classified as historical reference. They assume conflicting EDF naming/sizes and hard-coded servo, wall, pivot, exit, and clearance geometry. Some may become topology reuse candidates after measurement-driven re-parameterization, but none is released for manufacture.

## 11. AeroForge intake readiness

The `TVC_ASSEMBLY_V1` intake connects requirements, component envelopes, interfaces, datum, motion constraints, manufacturing unknowns, verification requirements, and evidence sources. Its status is `BLOCKED_BY_MEASUREMENT`. It becomes eligible for design ingestion only when the R2 physical measurement gate is `READY` and the requirements are reviewed.

## 12. Blocking human inputs

All 35 P0 measurement IDs are listed explicitly in the AeroForge intake and user checklist. The principal blockers are actual EDF identity/envelope, actual servo geometry, electronics/power/structure envelopes, physical datum, assembled mass/CG, and a governed numeric motion/load basis.

## 13. Tests and checks

`scripts/r2_physical_baseline_check.py` recursively parses the new YAML, validates article/component/measurement/interface references, rejects unsupported `MEASURED` states, rejects manufacture-release statuses, checks that current requirements do not obtain numeric authority only from historical CAD, verifies complete AeroForge P0 handoff, and checks the human checklist. Missing measurements make the physical gate `BLOCKED` without failing the structure gate.

## 14. Changed files

R2 adds the as-built authority, evidence templates, TVC requirements, AeroForge intake, user worksheet/checklist, mass/CG guide, this report, and the R2 gate. Historical CAD and physical-design assets are not modified.

## 15. Next action after measurements

The user should complete the observation records and 35 P0 measurements, attach stable photo references, and update the inventory/mass/interface records through review. Once the physical gate becomes `READY`, AeroForge can ingest the requirements, measured envelopes, datum, interfaces, and mass properties to begin a parametric TVC assembly and motion/interference verification. That later step is not authorized by R2 intake completion.
