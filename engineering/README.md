# Ad Astra engineering baseline

This directory is the current engineering-status entry point for Project Ad Astra. It records what the repository proves, what the project owns, what is assigned to a specific experimental article, and what remains unknown. It does not certify a flight vehicle or any physical assembly.

## Read this first

1. `current-baseline.yaml` — current objective, blockers, authority order, and R2.1 direction.
2. **`cad-authority.yaml` — owner-corrected fact: current mechanical CAD is NOT_STARTED; legacy AI models are rejected, not a design baseline.**
3. `assets/project-asset-registry.yaml` — project-level owned hardware/tools; ownership is separate from article assignment and hardware verification.
4. `experimental-lines.yaml` — GNC, avionics, RF, TVC, recovery, propulsion-science, and system-integration benches.
5. `component-status.yaml` — implementation, software-test, and hardware-evidence status by subsystem.
6. `parameter-registry.yaml` — parameter values with provenance and conflicts; `UNKNOWN` is intentional.
7. `verification-status.yaml` — repeatable software checks separated from hardware-gated work.
8. `known-issues.md` — open engineering and safety-relevant gaps.
9. `legacy-assets.md` — historical sources and generated assets that remain preserved but are not authoritative.
10. `as-built/` — R2 TVC article, inventory, datum, measurement, interface, mass, and evidence authority.
11. `tvc-mechanical-requirements.yaml` — requirement baseline for a future measured TVC assembly; not CAD.
12. `aeroforge-intake/` — staged TVC concept/design-review handoff.
13. `command-safety-contract.yaml` — R1 canonical command states, actions, ACK/NACK, and link-loss rules.
14. `../docs/R2_1_REAL_ASSET_MULTI_BENCH_ARCHITECTURE.md` — current project-level development model.
15. `historical-hardware-capabilities.yaml` and `../docs/R2_1_HISTORICAL_TO_CURRENT_DELTA_AUDIT.md` — preserved historical capability and the seven-field current delta audit, not a request to repeat every experiment.
16. `../docs/R2_1_COMPATIBILITY_CLOSURE_REPORT.md` — current software/target closure, remaining hardware boundaries and the single-action handoff.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `NOT_STARTED` | Current accepted design work does not exist; retained historical files do not count. |
| `IMPLEMENTED` | Production-path code exists. No test or hardware claim is implied. |
| `TESTED_SOFTWARE` | A repeatable software test or source build passes. |
| `VERIFIED_HARDWARE` | Repeatable repository evidence links a procedure, configuration, result, and date to real hardware. |
| `PROTOTYPE` | Exploratory implementation, model, or geometry; not an accepted engineering design. |
| `HISTORICAL` | Preserved prior route, snapshot, or result. |
| `STALE` | Known to disagree with current code or current project direction. |
| `BLOCKED` | A named dependency or missing capability prevents completion. |
| `UNKNOWN` | Evidence is absent or insufficient; no value is inferred. |

Project ownership is tracked separately in the asset registry. A purchase record can establish that the project owns an item without proving current wiring, exact geometry, calibration, or successful hardware behavior.

## Authority order

For current project status, use this directory first. For implementation behavior, production code is authoritative over reports. A passing source build proves only that the source compiles. A software test proves only its tested contract. Historical Markdown, filenames such as `final` or `v11`, mesh quality, and generated reports do not prove hardware validation or manufacturability.

## Current answer in one paragraph

The repository preserves historical reports of controller flash/boot, GY-91
sensing, two physical TVC servos, telemetry, ground-station interaction and
attitude-driven stabilization. R2.1 is recovery and current re-baselining, not
first-time bring-up. Current software adds checked sensor identity/read validity,
an explicit experimental APM32 compatibility environment, an ESP-01S 1 MB target
and deterministic ownership/stage checks. Historical WiFi command-to-servo prose
conflicts with the initial telemetry-only ESP source: that remains an
implementation/configuration gap, not invented missing code. Software gates do
not establish current target runtime, sensor accuracy, servo response or R1
end-to-end physical transport. Only changed/uncertain behavior needs bounded
regression; absent old raw logs alone is not a reason to repeat the old bench.

## Software check

Install the runtime dependencies needed by the modules under test, then the development tools:

```powershell
pip install -r ground_station\requirements.txt
pip install -r aero_sim\requirements.txt
pip install -r requirements-dev.txt
```

On Windows, native C++ tests require a compiler. If no `gcc`/`g++` is installed, PlatformIO can provide the tested toolchain:

```powershell
platformio pkg install --global --tool platformio/toolchain-gccmingw32
```

Run the unified, hardware-independent check:

```powershell
python scripts\check.py
```

The existing R0/R1/R2 checks retain their original evidence ceilings. R2.1 adds a project-level ownership and multi-bench configuration layer; it must not silently upgrade any subsystem to `VERIFIED_HARDWARE`.

Read-only R2.1 structure diagnostics are also available independently:

```powershell
python scripts\r2_1_check.py --json
```

`structure_status: PASS` is compatible with `hardware_status: NOT_EVALUATED`.
Pending physical stages do not need invented evidence to pass software checks.
READY/COMPLETED physical stages require satisfied dependencies and stage-bound,
hash-checked records/raw artifacts confined to `engineering/evidence/records/`.
Conditional stages may be omitted only with an explicit rationale; this does not
create a hardware-verification claim.
