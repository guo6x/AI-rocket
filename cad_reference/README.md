# Electronics reference CAD, 2026-11-06

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
The existing SG92R metal-gear/POM and ESP32-S3 N16R8/N16R8V conflicts are unchanged.
No current EDF, ESC, main battery or frame purchase is recorded. Such parts need
selection before interface design; the task is not to ask for measurements of
unbought parts. Historic purchase/photos were previously supplied, but no raw
image files are linked in `engineering/evidence/records/`; this review did not
remeasure from photos or treat their absence in Git as the user's omission.

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
