# Historical CAD crosswalk

All listed assets are currently preserved for provenance only. **The owner has rejected prior AI-generated CAD as unfit for the current project (2026-10-25).** Nothing in this crosswalk is an approved design, a valid dimension source, a candidate automatically eligible for reuse, or a manufacturing release. See `engineering/cad-authority.yaml`.

| Asset | Classification | Embedded assumption or conflict | R2 disposition |
| --- | --- | --- | --- |
| `tvc_design/generate_tvc.py` and `outputs/**` | `HISTORICAL`, `REFERENCE_ONLY`, `REJECTED_FOR_CURRENT_DESIGN` | EDF OD 74 mm; 0.2 mm clearance; 3 mm wall; servo envelope 23.5 × 12.5 × 27 mm; simplified M3-like pivots; no measured article. | Reuse only as a topology reference after EDF, servo, frame, motion, load, and process inputs are approved. |
| `tvc_design/generate_pro_tvc.py` and `pro_outputs/**` | `HISTORICAL`, `REFERENCE_ONLY`, `REJECTED_FOR_CURRENT_DESIGN` | EDF OD 74 mm; SG92R 23 × 12.2 × 27 mm; 2.5 mm wall; 62 mm exit; assumed mounting and pivot geometry. | Values conflict with unresolved 70/90 mm EDF claim and unknown servos. |
| `tvc_design/generate_pro_tvc_v3.py` and `pro_outputs_v3/**` | `HISTORICAL`, `REFERENCE_ONLY`, `REJECTED_FOR_CURRENT_DESIGN` | EDF OD 74 mm; pivot hole 3.2 mm; pivot height 15 mm; SG92R envelope; hard-coded clearances and structure. | V3 naming does not establish fit, load capacity, motion clearance, or manufacturability. |
| `cad_automation/generate_tvc_nx.py` and related NX asset | `HISTORICAL`, `REFERENCE_ONLY`, `REJECTED_FOR_CURRENT_DESIGN` | Default 74 mm EDF but described as 70 mm; 60 mm exit; 3 mm wall; SG92R envelope; simplified single lug. | NX automation feasibility only; not an assembly definition. |
| `3d_print_files/**` TVC and full-rocket assets | `HISTORICAL`, `REFERENCE_ONLY` | Mixed full-vehicle generations, body tubes, bolts, recovery parts, and TVC meshes with incomplete source mapping. | Do not use for current frame interface or printing. |
| `generate_rocket*.py` and full-vehicle outputs | `HISTORICAL`, `REFERENCE_ONLY` | Multiple body diameters/coordinates and legacy flight geometry. | Excluded from current EDF bench envelope unless a physical structure is measured. |
| `cad_automation/generative_sleeve*.py` and fairing assets | `HISTORICAL`, `REFERENCE_ONLY` | Legacy sleeve/fairing dimensions and process experiments. | Outside TVC Assembly V1; no current frame authority. |

## Reuse decision rule

No historical candidate is approved for direct re-parameterization or inclusion in the new assembly. A new design starts from independently evidenced measurements and a separately selected CAD source. Historical model geometry may only inform archival questions; similarity or a previous positive script result is not evidence of fit.
