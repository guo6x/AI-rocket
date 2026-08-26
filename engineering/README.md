# Ad Astra R0 engineering baseline

This directory is the current engineering-status entry point for Project Ad Astra. It is a reference layer: it records what the repository proves, what it merely implements, and what remains unknown. It does not certify a flight vehicle or any physical assembly.

## Read this first

1. `current-baseline.yaml` — current objective, intended platform, blockers, and authority order.
2. `component-status.yaml` — implementation, software-test, and hardware-evidence status by subsystem.
3. `parameter-registry.yaml` — parameter values with provenance and conflicts; `UNKNOWN` is intentional.
4. `verification-status.yaml` — repeatable software checks separated from hardware-gated work.
5. `known-issues.md` — open engineering and safety-relevant gaps.
6. `legacy-assets.md` — historical sources and generated assets that remain preserved but are not authoritative.
7. `../docs/R0_ENGINEERING_REBASELINE_REPORT.md` — audit narrative and evidence.

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

## Authority order

For current project status, use this directory first. For implementation behavior, production code is authoritative over reports. A passing source build proves only that the source compiles. A software test proves only its tested contract. Historical Markdown, filenames such as `final` or `v11`, mesh quality, and generated reports do not prove hardware validation or manufacturability.

The audited input commit is `b6006c9429ae1a2950917a61b4d2e1cf511ab5ed`. Future baseline changes must update provenance and verification records in the same change.

## Current answer in one paragraph

The repository contains an implemented STM32 flight-control code path, an implemented ESP8266 telemetry uplink, a working Python ground-station codebase, exploratory flight and EDF-TVC simulations, and many preserved CAD/model generations. The current safe development objective is an EDF TVC bench platform, but the actual assembled physical configuration and its dimensions, mass, CG, actuator envelopes, and integrated behavior are not proven by repository evidence. WiFi command downlink is incomplete, controller parameters are not hardware-qualified, recovery hardware is not verified, and existing CAD is historical/prototype rather than manufacturing-ready.

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

The terminal line `R0 SOFTWARE CHECK: PASS` covers syntax, YAML parsing, ground-station tests, read-only simulation smoke checks, native flight-core tests, and STM32/ESP8266 source builds. Hardware procedures remain `MANUAL / HARDWARE-GATED` and are not converted into software failures.
