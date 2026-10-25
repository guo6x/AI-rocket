# Phase 1: remove rejected AI-generated CAD exports from active tree

**Date:** 2026-10-25  
**Source baseline:** `main@03fbd826031f24055bf5de79c7aa4aa72810b451`  
**Phase-1 deletion commit:** `9b7f2df427df6cc03cd3401c4c2164a2f2af3153`  
**Scope:** 22 unapproved exported binary artifacts, totaling about **55.86 MiB of tracked blob contents** (not a promise to shrink Git history or remote repository storage).

## Files removed from branch tip

- All 7 tracked binary exports in `outputs/`.
- All 6 tracked binary exports in `pro_outputs/`.
- All 5 tracked binary exports in `pro_outputs_v3/`.
- `cad_automation/AI_Avionics_Sleeve.stl`, `AI_Avionics_Sleeve_V3.glb`, `AI_Avionics_Sleeve_V3.stl`, and `sleeve_preview.glb`.

The original content is recoverable using the full Git history at the pre-cleanup main SHA above. No `git filter-repo`, force push, history rewrite or file-format conversion was attempted.

## Dependency-boundary audit

Before the deletion, 12 core runtime entry points spanning `flight_computer/src/`, `esp8266_firmware/src/`, `ground_station/core/`, `ground_station/ui/`, and `scripts/` were scanned for direct references to the removed names or prefixes. No direct consumers were found in that selected active group. This is a **focused source check**, not a comprehensive proof that no old preview or historical script refers to the artifacts.

The old `3d_print_files/` binaries, `viewer.html`, legacy generator scripts, NX `.prt` files, `reports/`, `engineering/as-built/`, and the current Ground Station code are **not removed in phase 1**. Historical pages may contain broken references to the removed exports; such pages are non-authoritative and should remain clearly marked `STALE`.

## Acceptance conditions before merging

1. Verify this branch diff only removes the listed 22 old binary blobs and updates documentation. Do not delete a genuine current source or evidence record.
2. Run `py -3 scripts/cad_baseline_gate.py --check`: expect baseline truthfulness PASS and CAD_START BLOCKED.
3. Run `py -3 scripts/check.py` on branch exact HEAD or obtain equivalent explicit integration evidence. No hardware operation is needed.
4. Verify CAD remains `NOT_STARTED`; do not reuse historical 74 mm EDF or previous servo/hole dimensions as manufacturing inputs.
5. Only then merge; do not mark current CAD READY.

## Subsequent historical cleanup

Other old 3D mesh/demo directories and root generators remain for separate impact analysis. Do not repeat a blind bulk purge when old website demo entry points may still depend on them. The objective is a clean active engineering baseline, **not** erasing all historical research.
