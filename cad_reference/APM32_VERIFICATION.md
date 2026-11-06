# APM32 reference verification, 2026-11-06

Continuation of PR #52 from head
`f6691fd853b1c86d240022d4fc26f910785c28b7`, base
`94afa857890ee80ab78f99b9f9241e998aa338d4`.

## Performed locally

- Geehy V1.5 PDF retrieved from the official product-page link. Mechanical,
  land-pattern and exact order-code pages reviewed as both text and pixels.
  Source URL, digest and page mapping are in `APM32_REFERENCE.md`.
- Three actual STEP exports produced using CadQuery 2.7.0 / OCP 7.8.1.1:
  nominal chip body, separate maximum-dimension box and 48 planar land faces.
- The delivered package was reimported and independently checked, including
  every land's topology, position, straight boundaries, corners and area.
- Coordinate JSON and source-figure pin numbering checked independently.
  SVG rendered to PNG and visually inspected for content and clipping.
- **89 CAD tests passed**, including 18 new APM32 tests. Negative tests include
  changed source/model/unknowns, wrong origin or size, missing/duplicate/rotated
  pads, invented pad thickness, loose edges, forged hashes/labels/claims,
  duplicate JSON keys, extra files, symlinks, and export/import failure.
- **28 existing manufacturer-nominal/CAD-authority tests passed.** Nominal
  registry check passed with 44 reference parameters and unchanged conflicts.
- CAD bookkeeping audit passed while honestly retaining `NOT_STARTED`, zero
  accepted current models, all 19 missing CAD_START items and no release.
- Python compileall and Git whitespace checks passed.
- Independent code/source review found no remaining reference-scope blockers.
  It confirmed that STEP's symmetric unlabeled land geometry cannot establish
  electrical pin identity: coordinate JSON and SVG must accompany it.

## Verification limits

The full local `scripts/check.py` was attempted but could not run its software
gates because PlatformIO is missing. Its FAIL labels are a prerequisite
failure, not evidence of a newly failing firmware test. Focused local checks
above are not whole-project acceptance. The remote CI result for the published
commit must be checked separately; this note does not claim it has passed.

This is computational/source verification only. No actual board measurements,
chip identification, hardware operation, radio, flashing, power-up, actuation,
propulsion, structural validation, PCB release or manufacturing took place.
There was no purchase, supplier contact, merge or deployment.

The original Ra-02 and sensor files and three-page PDF remain byte-unchanged.
The new APM32 reference is shown in its own SVG, not silently inserted into the
older review PDF. Main physical/parameter authority files are unchanged.
