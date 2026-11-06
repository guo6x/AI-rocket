# Local validation, 2026-11-06

Base source: `94afa857890ee80ab78f99b9f9241e998aa338d4`.
Environment: Python 3.12.14, CadQuery 2.7.0, OpenCascade binding version in the
example receipt. All checks were software-only in the cloud.

| Check | Actual result |
| --- | --- |
| `python -m unittest discover -s cad_reference/tests -v` | 18 tests passed, including real CAD and negative tests |
| Existing `test_cad_baseline_gate.py` and `test_manufacturer_nominal.py` | 28 passed |
| `python scripts/cad_baseline_gate.py --check` | Truthfulness audit PASS; accepted models 0; 19 CAD_START blockers remain |
| `python scripts/manufacturer_nominal_check.py --json` | PASS, existing 44 nominal parameters and 15 unresolved assets unchanged |
| Three generated STEP files | Reimported; valid single closed solid, source dimensions, origin and analytic volume matched |
| `python -m compileall -q cad_reference` | PASS |
| `git diff --check` | PASS |
| SVG nominal view | Rendered on white background and visually inspected; simple reference box only |
| `python scripts/check.py` | BLOCKED/exit 1: PlatformIO missing, full gate did not execute |
| Remote CI | Separate PR workflow result; not substituted with local focused checks |

Independent review found a provenance guard gap: a changed PDF digest/revision
could pass. The generator now checks the reviewed digest and revision explicitly,
and an added negative test covers this. Final reference tests passed after the fix.

Earlier failed development runs were not shipped: an OCC solid closure flag was
replaced with closed-shell checks, and the thickness comparison uses a numeric
tolerance rather than exact floating-point equality. These were software issues,
not physical evidence.

The 18 + 28 tests are distinct focused suites; they are not whole-project acceptance.
No thermal, structural, EMI/RF, mounting-fit, material, manufacturing, electrical
power, hardware or flight validation has been completed by this package.
