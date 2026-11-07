# Sensor-package reference verification, 2026-11-06

Continuation of Draft PR #52 at `8b7e4bbf88275d0f1d5819db5d00239e3341890c`.
This record covers source-bound numerical geometry only.

## Passed locally

- Original MPU-9250 and BMP280 PDFs downloaded; byte digests and drawing-page
  pixels checked. Independent review confirmed every nominal/min/max dimension,
  BMP explicit-tolerance precedence and whole-height interpretation.
- `python -m unittest discover -s cad_reference/tests -v`: **34/34 passed**,
  comprising 18 existing Ra-02 tests and 16 new sensor-reference tests.
  These include real CadQuery/OpenCascade STEP export and import, six independent
  package boxes, file digests, source/claim/dimension/unit/scope mutations,
  unknown-to-zero/identity upgrades, wrong datum/geometry, protected output
  directories, and export/import failures retaining INCOMPLETE receipts.
- `python -m pytest scripts/tests/test_manufacturer_nominal.py
  scripts/tests/test_cad_baseline_gate.py -q`: **28/28 passed**.
- `python scripts/manufacturer_nominal_check.py --json`: PASS; 44 existing rows,
  two existing conflict groups and 15 unresolved assets remain unchanged.
- `python scripts/cad_baseline_gate.py --check`: bookkeeping PASS; accepted
  current models **0**, CAD `NOT_STARTED`, CAD_START `BLOCKED`, all **19** blockers
  unchanged, manufacturing `NOT_AUTHORIZED`.
- Fresh generated example contains six STEP files, six CAD-derived SVGs,
  validation.json and README.txt. Each STEP is reimported during generation.
- `python -m compileall -q cad_reference` and `git diff --check`: passed.
- Independent code review found that unchecked model metadata could previously
  enter a PASS receipt. Exact allowed keys and fixed claim/basis validation were
  added, with a regression test. Review reran all 34 tests and found no further
  blocking issue within this reference-only scope.

## Not a complete project acceptance

`python scripts/check.py` was attempted but exited before running aggregate
checks because **PlatformIO is missing** locally. The above tests do not replace
the whole software gate. The existing CI workflow is extended to generate the
new sensor references with the real CAD kernel. Its result is separate from this
local record and must be checked for the exact published commit.

The initial authority-test invocation encountered a missing pytest dependency;
pytest was installed into an isolated workspace directory and the final 28-test
run passed. A harmless pytest-plugin deprecation warning remained.

## Unchanged boundaries

No production control/telemetry/firmware change, hardware connection, physical
measurement, powered test, RF emission, manufacturing, supplier contact or
purchase. Purchase identity and GY-91 board geometry remain unknown. This package
does not claim sensor axes, detailed pad/lid/vent geometry, installed clearance,
material volume, mass, structural integrity or flight suitability.
