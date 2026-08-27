# R2 static mass and CG measurement guide

This how-to establishes low-risk, unpowered mass-property evidence for `AA-TVC-BENCH-001`. It does not use EDF thrust, powered servos, suspended operation, or dynamic testing.

## Before measuring

1. Disconnect and keep all power sources unpowered. Do not charge, discharge, open, or operate them.
2. Record the exact configuration revision and every included component. Remove loose tools, CH340, ST-Link, and temporary supports unless they are intentionally part of the measured configuration.
3. Confirm the physical datum labels from `M-P0-DATUM-01`. Longitudinal CG is reported as a Z coordinate from `DTM-AA-001` Z=0.
4. Use stable, level supports on a clear bench. Do not balance the article where a fall could damage a component.

## Total mass

1. Check that the scale reads zero with its empty tray or protective pad.
2. Place the complete unpowered configuration on the scale without cables touching the bench.
3. Record at least three raw readings after the display settles.
4. Report the representative value, scale resolution, observed variation, and included-component list in a measurement record.

Do not sum datasheet masses when an assembled mass can be measured. Component masses are still useful for CAD attribution and configuration changes.

## Preferred longitudinal CG: two-support reaction method

Use this when the article can rest stably on two narrow supports perpendicular to Z.

1. Place support A and support B at measured Z coordinates `z_A` and `z_B`, separated as far as practical while remaining stable.
2. Put one support on a scale and make the other a level support at the same height. Record the scale reaction. Swap the scale/support positions as a cross-check if practical.
3. Record total weight-equivalent mass `M` from the mass measurement and reaction-equivalent mass `R_B` at support B.
4. Compute:

   `z_CG = z_A + (R_B / M) × (z_B - z_A)`

5. Repeat after lifting and replacing the article. Record all raw `z_A`, `z_B`, `R_B`, and `M` inputs, not only the computed result.
6. Estimate uncertainty from ruler/scale resolution and repeat spread. If supports deform, slip, or contact different features between runs, mark the result unresolved.

The article must remain statically supported throughout. Do not use a powered fan, tensioned line, or hand-held reaction measurement.

## Balance-point cross-check

For a small, robust configuration, place it on a broad rounded support and move it slowly until it is neutrally balanced. Mark and measure that Z position from the datum. Use a second person or side stops to prevent a fall.

This is a cross-check, not a replacement for raw evidence. Do not use a sharp edge on wiring, batteries, PCBs, or printed parts. If the article cannot be safely balanced, skip this method.

## Transverse CG status

After longitudinal CG is known, rotate only if the unpowered article can be securely supported. Record whether X/Y balance was measured, approximately checked, or remains `UNKNOWN`. R2 does not require a fabricated transverse-CG value.

## Acceptance for the R2 intake

A mass or CG value becomes `MEASURED` only when the record identifies configuration, datum, method, tools, raw readings, units, uncertainty, photos, operator/date, and source commit. A plausible number without that record remains `UNKNOWN`.
