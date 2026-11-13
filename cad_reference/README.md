# Electronics reference CAD, 2026-11-06

先看[中文交付导航](DELIVERY_MAP.md)：13 份参考文件分别能做什么、如何核验、下一步真正缺什么。

## Ra-02 source-version warning, reviewed 2026-11-13

The existing Ra-02 STEP cases remain pinned to the **2017 English source**
linked below, including its 3.2 +/- 0.1 mm height band. They are not a claim
about the current manufacturer's complete tolerance envelope or the purchased unit.

The [current manufacturer index](https://docs.ai-thinker.com/Ra-02/index.html)
now links a [Chinese V1.1 PDF dated 2026-06-29](https://aithinker-static.oss-cn-shenzhen.aliyuncs.com/docs/Public%20Document%20Center/LoRa/lora/Specification/Ra-02_V1.1%E8%A7%84%E6%A0%BC%E4%B9%A6-20260629.pdf).
The downloaded PDF's page 6 lists 17 x 16 x 3.2 (+/- 0.2) mm without separately
defining every axis in that table. Its actual page-9 drawing explicitly labels
17 +/- 0.2 and 16 +/- 0.2 mm; the pictured underside is marked Ra-02_V1.4.
Both pages were rendered and visually inspected. PDF SHA-256:
`770895e55b47598b6dccc5ebb190d4b9a98721135f0762803b7abae1dfb42d80`.

A document revision named V1.1 is not a PCB revision identity. **The newer
document has not been bound to the user's purchased modules or their blue
carrier boards.** Do not silently combine its dimensions with the old source,
treat 3.3 mm as a current worst-case height, or infer carrier/header/cable
dimensions from either bare-module document. This notice changes no geometry,
manifest, parameter registry, as-built record, acceptance state or firmware.
The existing files remain historical-source numeric references, not fit approval.

## New: per-unit measurement-to-envelope CAD input

The [measurement envelope tool](BOARD_MEASUREMENT_ENVELOPE.md) converts one reviewed
private real-board record into two independently reimported reference boxes. It
retains below-board heights, rigid protrusions and supplied uncertainty bounds.
All five shipped JSON templates are blank and refuse generation. No actual board
dimensions, new physical-board STEP or assembly acceptance are claimed. Existing
13 STEP references and all 19 CAD_START blockers remain unchanged.

## Next real-board input: five-unit measurement workbook

The [Chinese board measurement guide](BOARD_MEASUREMENT_WORKBOOK.md) and
[six-page fillable PDF](examples/board-measurement-workbook.pdf) turn the unresolved
board geometry into a concrete collection task: APM32, ESP32-S3, two separate
Ra-02 carriers and GY-91. Start with APM32 and one Ra-02. No new purchases or
repeat purchase proof are needed. A matching supplier board drawing/CAD is also
an acceptable starting point for a nominal model; current searches did not bind
one to these purchased PCB revisions.

The sheets distinguish PCB thickness, above/below-board heights, all rigid
protrusions, hole/header coordinates and mated connector/service space. All
80 form fields are blank. They do not add measured values, assumed board
geometry or a new assembly. The 13 existing STEP references remain unchanged.
Regenerate with `python cad_reference/make_board_measurement_workbook.py --output
/tmp/board-measurement-workbook-new.pdf` (ReportLab dependency already listed).

## New: board-level source review and seller numeric spans

[Board-level review](BOARD_SPANS_REFERENCE.md) follows the actual purchased
carrier/header variants. The new ESP32 surface records only the seller's
**57 x 28 mm printed dimensions**, not a true PCB contour or complete envelope.
The pictured antenna protrudes beyond the 57 mm label boundary. No height,
headers, mounting holes or USB geometry is guessed. Ra-02 carrier DXF and other
sellers' dimensions were located but not substituted for the purchased blue
carrier. See the [source decisions](../engineering/references/board-source-review-20261107.md).

## Purchase-variant recovery, 2026-11-07

The [original-image review](../engineering/references/purchase-variant-recovery-20261107.md)
recovered the 24 previously supplied purchase screenshots. The selected Ra-02
product is **with a carrier board**, so the 17 x 16 mm bare-module references
below do not represent the purchased assembly's complete outline. The APM32
selection says downward-soldered headers; GY-91 says purple board with refurbished
chips. These are product-option statements, not measurements or functional
verdicts. The current official Espressif table now includes DevKitC-1-N16R8;
the seller's Type-C board has not been matched to its Micro-USB board drawing.
No geometry, fit status or authority gate is upgraded by these recovered facts.

## New: APM32 chip body and 48-land reference

[APM32F103C8T6 / LQFP48](APM32_REFERENCE.md) adds a source-reviewed nominal
body STEP, separate maximum-dimension STEP and **48 planar recommended lands**
with pin labels, coordinate JSON and an SVG review. The official order-code
table explicitly identifies this chip package. It does not establish the
purchased core board's shape, headers, connector or physical identity.
The earlier three-page PDF below covers Ra-02 and the two sensor packages only;
open the new APM32 SVG for this addition.

## Inspect and independently check the delivery

Open the [three-page reference review](examples/electronics-reference-review.pdf)
for real STEP-derived nominal views and all nine reference-size cases. These are
not manufacturing drawings, and the views are not to scale.

The [read-only package checker](verify_package.py) now independently reimports
every delivered STEP instead of trusting a stored PASS receipt. It checks the
reviewed source dimensions, file inventory, digests, labels and reference-only
state. See [delivery verification and limits](DELIVERY_REVIEW.md).
The PDF tool also supports `--check` for read-only reproduction of the actual
delivered PDF. PDF outputs inside either verified package are rejected so that
creating a review cannot invalidate the reference files it just checked.

## Continuation: sensor chip packages

[MPU-9250 and BMP280 reference CAD](SENSOR_REFERENCE.md) now adds six real
STEP files: independent minimum, nominal and maximum chip-package boxes from
newly inspected manufacturer drawings. These are **not the purchased GY-91
board**, not a placement layout and not a physical-identity claim. The original
Ra-02 package below remains unchanged. All TVC/CAD_START blockers remain.

**REFERENCE ONLY. Not a current physical assembly, fit drawing, printable design,
manufacturing release, or flight article.** Current TVC CAD remains
`NOT_STARTED`, with 19 unmet CAD_START entries. No old rejected geometry is used.

## What is actually built

A source-bound, editable CadQuery script produces independent rectangular
**Ra-02 V1.1 reference boxes**, with nominal length 17 mm and width 16 mm,
and three height cases: 3.1 / 3.2 / 3.3 mm. These represent the source's
3.2 +/- 0.1 mm thickness band. They are not detailed component replicas, a
placement layout, a mounting design, or a complete worst-case fit envelope.
Length/width tolerances, connector/cable clearance and antenna clearance are
unknown. The box volume is not the physical module's material volume or mass.

The practical advance is a reproducible path from reviewed source records to
real STEP files, native topology checks and STEP import verification, without
inventing the missing mechanical interfaces. The accepted assembly is still absent.

- [Generator](generate_reference.py): Python parametric source.
- [Input/provenance manifest](reference-inputs.json): exact registry row hashes,
  reviewed primary-source PDF digest, explicit unknowns and blocked ESP-01S.
- [Generated example](examples/ra02-20261106/): three STEP files, three SVG views,
  machine-readable validation and warnings. Keep the receipt with the STEP files.
- Actual purchase identity remains unverified. A procurement record is not a
  measurement or proof that the purchased module matches this source revision.

## Sources checked this time

**Ra-02:** [Ai-Thinker V1.1 specification, page 2](https://aithinker-static.oss-cn-shenzhen.aliyuncs.com/docs/Public%20Document%20Center/LoRa/lora/Specification/Ra-02_V1.1%20Specification-20171219.pdf).
The original PDF was retrieved and its page pixels inspected. It agrees with
`MN-RA02-LENGTH/WIDTH/HEIGHT` in `engineering/parameter-registry.yaml`, including
the existing 0.1 mm height tolerance. Source bytes SHA-256:
`b4d1fa7502007b18a06620681eece42985f8eb8bf62279fdaea4f00cd977b59d`.

**ESP-01S: do not build a fitting enclosure from the current registry.**
The old shared-series reference is 24.7 x 14.4 x 11.0 mm. On this review the old
PDF URL returned the documentation home page rather than a PDF. The live
[manufacturer index](https://docs.ai-thinker.com/esp8266/) links an
[ESP-01S-specific V1.1 PDF](https://aithinker-static.oss-cn-shenzhen.aliyuncs.com/docs/Public%20Document%20Center/WiFi/esp8266/Specification/ESP-01S%20Specification-20250802.pdf):

- Page 3 records a 2025-08-02 dimension-description correction.
- Page 7 lists 24.6 x 14.4 x 11.2 mm, with a 0.2 mm tolerance notation and a note
  that 11.2 mm is the pin-header height. Do not assume this unqualified notation
  establishes all-axis envelope tolerances or a complete installed height.
- Page 11's dimension drawing still labels the length **24.7 mm**. The original
  drawing pixels were inspected, not inferred from search snippets.

Thus both a series-versus-specific-document difference and an internal PDF
length inconsistency remain. The generator refuses ESP-01S and does not choose
a number, reinterpret the pin-header height, or alter the old authority layer.
PDF SHA-256: `83ba3c69b403b3b4ba48ea1367bcfef8262e4bd55d1373f0d206ddd8fa84fb80`.
The minimal future evidence is a model/revision-specific manufacturer or seller
clarification and, before fit approval, the actual unpowered part measurements.
No supplier was contacted and no purchase was made.

## Other unresolved parts

The existing 23-category purchase registry remains the ownership source. It
records APM32, ESP32-S3, ESP-01S, GY-91, SG92R x2, LM2596 and Ra-02 x2, among
other tools/accessories. It does not establish board dimensions or installation.
The old SG92R metal-gear/POM question came from a stronger-than-visible
transcription: the original says metal servo, which does not establish gear
material. Exact seller model/material remains unresolved. The historical ESP32-S3 N16R8/N16R8V
source snapshot is retained, but the newer review above updates that question:
current official naming exists, while exact board/USB applicability remains open.
No current EDF, ESC, main battery or frame purchase is recorded. Such parts need
selection before interface design; the task is not to ask for measurements of
unbought parts. Historic purchase screenshots are now recovered privately as
described above. They are deliberately not placed in `engineering/evidence/records/`
because they contain personal order fields. No dimensions were inferred from
image scale.

## Reproduce

Use an isolated Python 3.12 environment, then:

```sh
python -m pip install -r cad_reference/requirements.txt
python -m unittest discover -s cad_reference/tests -v
python cad_reference/generate_reference.py --output /tmp/ra02-reference-new
python scripts/cad_baseline_gate.py --check
```

Choose a new output directory. Existing directories are rejected. Invalid inputs
are rejected before CAD generation. STEP import/export failures write an
`INCOMPLETE` receipt, not a PASS. Input row changes require explicit source
review and a manifest update; do not just recalculate hashes to bypass review.
PDF hashes identify the retrieved bytes but are not signatures, proof of
manufacturer authenticity, or proof of applicability to the purchased unit.

## Verification and limits

The tests exercise real CadQuery/OpenCascade export and import, valid closed
solid topology, bounding dimensions, reference origin and analytic box volume.
They also inject wrong dimensions, datum, topology, missing/conflicting sources,
unknown-to-zero changes and import failure. SVGs are generated from the actual
CAD and were visually inspected. No STL is supplied to avoid implying a
fabrication deliverable. This is computational geometry validation only.

The isolated local reference tests and existing authority tests are recorded in
`VERIFICATION.md`. The complete project gate needs PlatformIO and is distinct
from these results. No physical test, power-up, actuation, radio transmission,
structural calculation, TVC/propulsion design or hardware acceptance occurred.
