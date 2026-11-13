# APM32F103C8T6 LQFP48 reference CAD

This adds **three real STEP files and a 48-land coordinate model**, rather than
another whole-board guess. It is a chip-package and manufacturer-recommended
land-pattern reference. It is **not the purchased APM32 core board**, a populated
PCB, a fabrication footprint release or an accepted mechanical assembly.

The reference can be imported into a CAD tool to inspect the chip dimensions,
compare body and lead-span limits, and review the 48 recommended land positions.
Board-specific geometry and installation clearance are still unknown.

## Open the outputs

- [Labeled drawing](examples/apm32-20261106/APM32F103C8T6_REFERENCE_ONLY.svg).
- [Nominal body STEP](examples/apm32-20261106/APM32F103C8T6_BODY_NOMINAL_REFERENCE_ONLY.step):
  a 7 × 7 × 1.4 mm rectangular body at nominal stand-off Z=0.1 mm.
- [Maximum-dimension STEP](examples/apm32-20261106/APM32F103C8T6_MAX_DIMENSIONS_REFERENCE_ONLY.step):
  a separate 9.2 × 9.2 × 1.6 mm reference box. This includes the maximum
  lead-tip spans and overall-height limit, not installation clearance.
- [Recommended lands STEP](examples/apm32-20261106/APM32F103C8T6_RECOMMENDED_LANDS_REFERENCE_ONLY.step):
  48 separate planar faces, deliberately **not solids**. No unprovided copper
  or solder thickness has been invented. A CAD importer should preserve surfaces.
- [Land-coordinate JSON](examples/apm32-20261106/land-coordinates-reference-only.json):
  all pin labels, centers and rectangle dimensions, in millimeters.
- [Editable CadQuery source](generate_apm32_reference.py) and
  [reviewed input manifest](apm32-reference-inputs.json).

These STEP files are independent references. Loading all of them together is
not a physical assembly. The body box omits molding/chamfer details and bent
leads. The large box is a numeric limit reference, not component material.
The review image is not to scale and is not a manufacturing drawing.

## Evidence and dimension derivation

Primary source: [Geehy APM32F103x4x6x8 datasheet V1.5](https://global.geehy.com/uploads/tool/APM32F103x4x6x8%20datasheet%20V1.5.pdf),
linked from the [official product page](https://global.geehy.com/product/fifth/APM32F103).
Retrieved 2026-11-06. Original PDF text and page pixels were inspected, including
the exact order-code row, mechanical drawing, dimension table and land pattern.
Downloaded PDF: 2,139,361 bytes, 61 pages, SHA-256
`b3d0b480d8840eecca7119fde3a122a662e44fd68fd20453d2eddb686408ea56`.
The digest identifies reviewed bytes; it is not a manufacturer signature or
proof of which chip is physically fitted to the purchased board.

Printed p54 / PDF55 explicitly maps **APM32F103C8T6 to LQFP48**. Printed
pp45–46 / PDF46–47, Figure 18 and Table 41, specify:

- Body X/Y: 7.00 ± 0.10 mm; nominal body thickness: 1.40 ± 0.05 mm.
- Stand-off: 0.10 ± 0.05 mm. Nominal body top is therefore Z=1.50 mm.
- Lead-tip X/Y span: 9.00 ± 0.20 mm; **overall height is maximum 1.60 mm**.
  That maximum is not nominal body thickness.

Printed p47 / PDF48, Figure 19, specifies 48 recommended rectangular lands:
12 per side, 0.50 mm pitch, 0.30 mm width, 1.20 mm radial length, 7.30 mm
opposing inner span and 9.70 mm outer span. The 5.80 mm row span independently
checks as 11 × 0.50 + 0.30. These dimensions describe recommended lands,
not the metal lead width or PCB outline.

The generator derives radial centers as (7.30 + 9.70) / 4 = 4.25 mm. Tangential
centers run from −2.75 to +2.75 mm in 0.50 mm steps. The center datum is at the
seating plane Z=0. In the drawing's top view, X is right and Y is up. Labels
follow **Figure 19**: bottom left-to-right 1–12, right bottom-to-top 13–24,
top right-to-left 25–36, left top-to-bottom 37–48. Figure 18 uses a rotated
view; its orientation is not silently mixed into the land-coordinate model.
Pin labels are not an electrical net assignment or a verified board pin map.

## Source and physical authority remain separate

The purchase binding is the existing `AST-MCU-APM32-001` record for the
APM32F103C8T6 core board. The new manifest records a separately reviewed
chip-package reference source. It does not rewrite the older family-level
electrical parameters or broaden their evidence claims. The main parameter
registry, as-built data and CAD authority files are unchanged.

Unknown: purchased chip identity, board dimensions/thickness, USB connector,
header positions, mounting holes, chip orientation on board, solder-mask/paste
rules, copper thickness, materials, mass and installation clearance. A source
recommended land pattern alone is insufficient for PCB manufacture: the actual
package, electrical mapping, PCB stackup, mask/paste rules and fabrication checks
need separate confirmation. No user photographs were treated as measurements.

## Reproduce and check actual delivered geometry

Use the existing Python 3.12 CAD environment and dependencies:

```sh
python -m pip install -r cad_reference/requirements.txt
python -m unittest discover -s cad_reference/tests -v
python cad_reference/generate_apm32_reference.py --output /tmp/apm32-reference-new
python cad_reference/generate_apm32_reference.py --check /tmp/apm32-reference-new
python cad_reference/generate_apm32_reference.py --check cad_reference/examples/apm32-20261106
python scripts/cad_baseline_gate.py --check
```

Generation refuses an existing output directory. Invalid or altered source
records fail before output creation; export/import failure leaves an INCOMPLETE
receipt. Source changes require a new review, not merely recalculating a hash.

The read-only checker reimports all three STEP files. It checks actual box
dimensions, origin, topology and analytic volume; every land's planar topology,
four straight boundaries, corners, center, dimensions and area; the pin-label
coordinate artifact; exact file inventory/digests; and the SVG against the
verified land coordinates. Rewriting a receipt to say PASS cannot hide wrong
geometry or a changed drawing. The coordinate labels are essential because a
square 48-land array is rotationally symmetric and its unlabeled geometry
alone cannot prove pin numbering.

No hardware, power, flashing, radio transmission, propulsion, TVC, actuation,
PCB fabrication or manufacturing action occurred. All **19 CAD_START blockers**
and zero accepted current mechanical models remain unchanged.
