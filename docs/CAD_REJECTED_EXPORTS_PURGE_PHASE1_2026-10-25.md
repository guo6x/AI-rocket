# Historical AI CAD export cleanup — phase 1

**Correction by project owner:** CAD for the current article is **NOT_STARTED**. These deleted files were rejected generated examples, not approved manufacturing designs.

## This change

From clean `main@3a38e74e6afa3139c010924aec91c4b66b21edc8`, remove **22** old exported file blobs only: `outputs/` (7), `pro_outputs/` (6), `pro_outputs_v3/` (5), and `cad_automation/AI_Avionics_Sleeve.stl`, `AI_Avionics_Sleeve_V3.glb`, `AI_Avionics_Sleeve_V3.stl`, `sleeve_preview.glb` (4). They total approximately 55.9 MiB of file data, **not** 55.9 MiB removed from Git history.

The content can be recovered at original prior-to-delete tree `03fbd826031f24055bf5de79c7aa4aa72810b451` or in closed [PR #21](https://github.com/guo6x/AI-rocket/pull/21) and old commits. There is **no history rewrite**. All `3d_print_files/`, source generators, NX source files, Ground Station, GNC, ESP firmware, RF scripts, measured-baseline records and contracts are preserved.

## Acceptance and consequences

- This is a **repository-hygiene change**, not new CAD, geometry verification, hardware qualification or mechanical release.
- Historical viewers/macros *may* still reference removed obsolete exports. Those consumers are not current product authority; any genuinely active caller revealed by CI must be addressed without restoring invalid geometry to current-design status.
- Review the changed file list and run the current complete `scripts/check.py` via GitHub Actions **at this branch head** before merging.
- The authoritative `engineering/cad-authority.yaml` stays `NOT_STARTED / CAD_START BLOCKED`; do not replace unavailable EDF/servo dimensions with guesses from legacy CAD.
