# CAD ground-truth reset — 2026-10-25

## Owner correction: no usable CAD has been completed

The project owner explicitly rejected the older AI-created rocket, TVC, fairing and sleeve models as poor-quality historical products. **There is no approved current CAD assembly, no accepted component drawing and no manufacturing release.** A STEP/STL/GLB/PRT file being in Git is not a completed design; neither an automated mesh export nor a zero-exit legacy verification script is an engineering acceptance.

The current authority is `engineering/cad-authority.yaml`: `NOT_STARTED / BLOCKED_BY_MEASUREMENT`.

## Inventory of the misleading surfaces

Repository at reset base `main@3c38a188d039c794f8e0cea6d499960f79921be5` has 326 tracked blobs, including:

| Old location | Count in tree (all files, not necessarily geometry) | Disposition |
|---|---:|---|
| `3d_print_files/` | 44 | Unqualified old STL/GLB assemblies and preview pages; not print-ready |
| `cad_automation/` | 19 | Mixed NX .prt, generated sleeves, macros and scripts; old claims not authoritative |
| `outputs/` | 7 | Early TVC STEP/STL exports, rejected for current design |
| `pro_outputs/` | 6 | TVC v2 exports; “pro” is a filename, not validation |
| `pro_outputs_v3/` | 5 | TVC v3 exports, no current interface/motion proof |
| `tvc_design/` | 3 | Prototype generators with assumed 74 mm EDF and servo dimensions |
| `generate_rocket*.py` and `generate_all_3d_models.py` | several root scripts | Conflicting historical generations; no CAD input authority |
| `verify_v10.py`, `verify_rocket.py`, `verify_viewer.py` | 3 | Historical heuristics, **not** engineering validators; old scripts may exit 0 despite failure |

The old generated files are **quarantined by classification**, not deleted in this initial reset. This preserves reproducibility and avoids breaking viewer links, archived evidence, NX journals, or reference crosswalks before a dependency audit. Their directory names and preview links must no longer be surfaced as recommended models. A later *separate* cleanup PR may delete old binaries after identifying hardcoded users; Git history will remain available.

## The real starting point (reuse work already done)

- `engineering/as-built/measurement-plan.yaml` already defines the required EDF, two servo, datum, harness, and existing-frame evidence. Do not create a second conflicting questionnaire.
- `engineering/as-built/component-inventory.yaml` distinguishes project purchase records from actually observed article geometry.
- `engineering/aeroforge-intake/tvc-assembly-intake.yaml` already defines the CAD_START blocker set; it remains blocked while measurements are missing.
- `engineering/tvc-mechanical-requirements.yaml` specifies nonnumeric interface, motion, interference, and maintainability goals. It is **requirements only**, not geometry.
- `engineering/as-built/historical-cad-crosswalk.md` is a historical discrepancy index, *not* a list of parts cleared for reuse.

No 70/74/90 mm EDF diameter, servo size, pivot spacing, range, material, shell thickness, or fastener from an old file is accepted as current physical truth.

## CAD start gate / actual work definition

1. Confirm one **actual article** and included components (physical observations, not copied filenames).
2. Record model/scale photos and critical physical EDF envelope/retention/hole pattern, two servo envelopes, shaft/horn locations, cable keepouts, and local datum using the existing `CAD_START` measurement IDs. Absent EDF or no current article must remain recorded as UNKNOWN/NOT_PRESENT, not fabricated.
3. Review pitch/roll axis and required range; only then create a **new editable parametric CAD source** in a new controlled folder. Do **not** use old `generate_rocket*`, `outputs`, or NX model generations as the nominal baseline.
4. Validate with actual CAD-kernel geometry, export/reimport, static interference, full envelope motion, service access and traceable measurements. Exit nonzero on geometry test failures. Passing tests cannot substitute for structural and manufacturing review.
5. No print, assembly, physical RF, motor, propulsion or flight test is authorized by this CAD reset.

The safe, executable current gate is `python scripts/cad_baseline_gate.py --check`. **A PASS from that command means that the project's CAD evidence has been honestly classified, not that CAD is ready or manufactured.** It separately prints `CAD_START=BLOCKED` and the required missing IDs.

## Correct next deliverable

A project-specific **CAD input freeze**, followed by a first parametric **new** TVC mechanical design candidate. This will use the actual EDF and servo measurements when available, preserve parameter provenance and perform negative CAD validation. Until then, the valid output is the current `NOT_STARTED` state and a concrete list of missing inputs—not another attractive but unsupported STL model.
