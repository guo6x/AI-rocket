# GY-91 order: independent chip-package references

**REFERENCE ONLY. Not a GY-91 PCB, current assembly, measured part, mounting
design, fabrication file or flight release.** All 19 CAD_START blockers and the
current TVC `NOT_STARTED` state remain unchanged.

## Actual continuation

The purchase registry records `AST-SENSOR-GY91-001`, a GY-91 module whose order
description names MPU9250 + BMP280. That justifies investigating those named
chips. It does not prove which chips populate the received board, their location,
orientation, or the board dimensions. The raw historical purchase/photo images
were not retrieved in this continuation; a conversation search for GY-91 returned
no matches. Their absence here is not evidence that the user never supplied them.
The existing [purchase registry](../engineering/assets/project-asset-registry.yaml)
is unchanged. No dimensions are inferred from photographs.

The editable [generator](generate_sensor_reference.py) and
[input manifest](sensor-reference-inputs.json) produce **six independent STEP
reference boxes**, each with a real CAD-derived SVG and a read-back receipt:

| Chip package | Minimum XYZ (mm) | Nominal XYZ (mm) | Maximum XYZ (mm) |
| --- | --- | --- | --- |
| MPU-9250 | 2.90 × 2.90 × 0.95 | 3.00 × 3.00 × 1.00 | 3.10 × 3.10 × 1.05 |
| BMP280 | 1.90 × 2.40 × 0.90 | 2.00 × 2.50 × 0.95 | 2.10 × 2.60 × 1.00 |

[Generated examples](examples/sensors-20261106/) are new geometry, not reused
historical rocket models. XYZ follows the legacy registry length/width/height
ordering. Each file starts at its own arbitrary box corner `(0, 0, 0)`. This is
**not** a sensor-axis convention, pin-1 orientation, GY-91 board coordinate system
or assembly placement. All-min/all-max cases describe numeric dimensional corners,
not correlated manufacturing distributions or complete installed-fit envelopes.

## Primary evidence actually reviewed

Original PDF bytes were retrieved on 2026-11-06 and the dimension-page pixels
were inspected. A separate review verified the dimension interpretation.

- **MPU-9250:** [TDK official PDF, PS-MPU-9250A-01, revision 1.1,
  2016-06-20, printed page 39](https://product.tdk.com/system/files/dam/doc/product/sensor/mortion-inertial/imu/data_sheet/ps-mpu-9250a-01-v1.1.pdf).
  Table D/E/A supplies the three whole-package limits. SHA-256:
  `fb38e76cd5f3b223d5c93046d690bd843c34a9c77f70c04f0052c12436855db9`.
  A1 is a separate pad seating-height dimension; it is **not added** to total A.
- **BMP280:** [Bosch official PDF, BST-BMP280-DS001-26, revision 1.26,
  October 2021, printed page 38, Figure 18](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf).
  SHA-256: `473ff27d9df698b4757e36b36209f83b9f637b592c999d5fabe2a9453a488da6`.
  The drawing explicitly gives 2.00 ±0.10 and 2.50 ±0.10 mm and total height
  0.95 ±0.05 mm. Its general ±50 µm note does **not override or add to** those
  explicit limits. The 0.13 ±0.025 mm substrate dimension is not total height.

The old BMP280 product-page URL returned 404 during this review; the original
Bosch PDF remains available. The old InvenSense PDF URL redirected to an HTML
download page; the TDK-hosted PDF above supplied the actual drawing. The legacy
registry records are preserved and hashed rather than silently rewritten. Nominal
values agree; tolerance limits are explicitly bound to the new PDF review.
Source hashes identify retrieved bytes, not manufacturer authentication or
applicability to the purchased unit. PDFs are not redistributed in this package.

## What this does not model

No PCB, mounting holes, pin pads, pin-1 mark, lid curvature, vent passage,
solder stack, connector, wire, material, mass or chip placement is invented.
A rectangular package reference is not a detailed package replica. In particular,
the BMP280 reference box does not validate a pressure vent or sensor housing.
The datasheet separately calls for ventilation and lid clearance, which would
need a real installation design and review. No such clearance is generated here.

ESP-01S length/source conflict, SG92R gear/version conflict and ESP32-S3 board
variant mismatch remain open. EDF, ESC, main battery and frame are not treated
as purchased or dimensioned. There is no physical test or supplier outreach.

## Reproduce and verify

```sh
python -m pip install -r cad_reference/requirements.txt
python -m unittest discover -s cad_reference/tests -v
python cad_reference/generate_sensor_reference.py --output /tmp/sensor-reference-new
python scripts/cad_baseline_gate.py --check
```

Output directories must be new. The generator rejects changed source digests,
revisions, dimensional limits, registry provenance, units, conflicts, scope,
physical-identity upgrades and unknown-to-zero substitutions. Rehashing a registry
row does not bypass the critical provenance/scope guards. Export or import failure
leaves an `INCOMPLETE` receipt, never a geometry PASS. Generated STEP solids are
actually reimported and checked for one valid closed solid, dimension, datum and
analytic box volume. Box volume is not material volume or mass.

The generator makes no network calls at generation time: reviewed values are
pinned, while the receipt preserves source provenance for human review. Source
refresh is a separate review task, not an assertion that online PDFs never change.
The shared geometry validator is also hashed in each receipt.

See [verification details](SENSOR_VERIFICATION.md). Computational geometry and
software CI are not physical fit, structural, RF, flight or manufacturing approval.
