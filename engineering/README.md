# Ad Astra engineering baseline

This directory is the current engineering-status entry point for Project Ad Astra. It records what the repository proves, what the project owns, what is assigned to a specific experimental article, and what remains unknown. It does not certify a flight vehicle or any physical assembly.

## Read this first

1. `current-baseline.yaml` — current objective, blockers, authority order, and R2.1 direction.
2. `assets/project-asset-registry.yaml` — project-level owned hardware/tools; ownership is separate from article assignment and hardware verification.
3. `experimental-lines.yaml` — GNC, avionics, RF, TVC, recovery, propulsion-science, and system-integration benches.
4. `component-status.yaml` — implementation, software-test, and hardware-evidence status by subsystem.
5. `parameter-registry.yaml` — parameter values with provenance and conflicts; `UNKNOWN` is intentional.
6. `verification-status.yaml` — repeatable software checks separated from hardware-gated work.
7. `known-issues.md` — open engineering and safety-relevant gaps.
8. `legacy-assets.md` — historical sources and generated assets that remain preserved but are not authoritative.
9. `as-built/` — R2 TVC article, inventory, datum, measurement, interface, mass, and evidence authority.
10. `tvc-mechanical-requirements.yaml` — requirement baseline for a future measured TVC assembly; not CAD.
11. `aeroforge-intake/` — staged TVC concept/design-review handoff.
12. `command-safety-contract.yaml` — R1 canonical command states, actions, ACK/NACK, and link-loss rules.
13. `../docs/R2_1_REAL_ASSET_MULTI_BENCH_ARCHITECTURE.md` — current project-level development model.

## Status vocabulary

| Status | Meaning |
| --- | --- |
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

The repository contains an implemented flight-control code path, governed plaintext command processor, software-tested ESP command relay, staged R2 mechanical intake, and substantial simulation/research assets. R2.1 now records the project's real owned hardware/tool base and treats Ad Astra as multiple experimental lines that mature independently before system integration. The strongest near-term physical opportunity is GNC/avionics bench bring-up because the project already owns a controller board, GY-91, two SG92R servos, programmers/debuggers, and prototyping tools. Two critical compatibility gaps remain before hardware work: the purchased flight-controller board is APM32F103C8T6 rather than the repository's nominal STM32F103C8T6 target, and the purchased ESP8266 is ESP-01S rather than the current NodeMCU-v2-style build target. These are not hardware-proven until bench evidence exists.

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
