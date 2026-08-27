# R2 user measurement checklist

Article: `AA-TVC-BENCH-001`

Use a phone camera, ruler or caliper, removable labels, and an electronic scale. Keep every item unpowered. Put a ruler in dimensional photos, take straight-on and side views, and assign a visible item ID so photos cannot be confused later. Enter results in `R2_PHYSICAL_MEASUREMENT_WORKSHEET.md`, then create evidence records from `engineering/evidence/templates/`.

## MUST HAVE BEFORE CAD — 35 missing

### EDF

- [ ] `M-P0-EDF-01` Label/model plus front and rear photos.
- [ ] `M-P0-EDF-02` Maximum rigid outer diameter: ___ mm.
- [ ] `M-P0-EDF-03` Intended retention/body diameter and axial location: ___ mm / ___.
- [ ] `M-P0-EDF-04` Overall and rigid-body lengths: ___ / ___ mm.
- [ ] `M-P0-EDF-05` Inlet diameter and photographed reference plane: ___ mm.
- [ ] `M-P0-EDF-06` Outlet diameter and photographed reference plane: ___ mm.
- [ ] `M-P0-EDF-07` Mounting-feature type/count/thickness: ___ / ___ / ___ mm.
- [ ] `M-P0-EDF-08` Mounting-hole center pattern from a named datum: ___.
- [ ] `M-P0-EDF-09` Mounting-hole diameter(s): ___ mm.
- [ ] `M-P0-EDF-10` Usable unobstructed clamping-zone start/end and obstructions: ___.
- [ ] `M-P0-EDF-11` Cable exit position/direction, connector envelope, relaxed keepout: ___.
- [ ] `M-P0-EDF-12` EDF mass with normal attached leads: ___ g.

For photos, include the full EDF, both axial ends, every label, every mounting feature, and a ruler in the same plane as the feature being measured.

### Two TVC servos

- [ ] `M-P0-SERVO-01` Label each unit PITCH/ROLL; photograph labels and all sides.
- [ ] `M-P0-SERVO-02` Body L × W × H for each unit: P ___ × ___ × ___; R ___ × ___ × ___ mm.
- [ ] `M-P0-SERVO-03` Tab length/width/thickness/location for each unit: ___.
- [ ] `M-P0-SERVO-04` Hole diameters and center coordinates from two body faces: ___.
- [ ] `M-P0-SERVO-05` Shaft-center coordinates, shaft diameter, protrusion: ___.
- [ ] `M-P0-SERVO-06` Horn type, attachment, retained screw, linkage-hole positions: ___.
- [ ] `M-P0-SERVO-07` Label/datasheet or gentle unpowered usable-range evidence: ___. Do not force or energize.
- [ ] `M-P0-SERVO-08` Cable exit, cable diameter, connector dimensions: ___.
- [ ] `M-P0-SERVO-09` Mass with selected horn and normal lead: P ___ g; R ___ g.

### Flight electronics

- [ ] `M-P0-ELEC-01` STM32 board label, PCB L/W, maximum heights, mounting holes.
- [ ] `M-P0-ELEC-02` ESP label and board form factor, PCB L/W, heights, mounting holes.
- [ ] `M-P0-ELEC-03` GY-91/sensor board both faces, L/W/heights, holes, axis markings.
- [ ] `M-P0-ELEC-04` Each connector type, mating direction, keepout length, wire exit.

Photograph boards unpowered from directly above and from each connector side. Include the ruler at PCB height.

### Power items — mechanical data only

- [ ] `M-P0-POWER-01` Photograph actual power source and regulator/BEC labels, or record that no item is present.
- [ ] `M-P0-POWER-02` Each present item's rigid L × W × H: ___.
- [ ] `M-P0-POWER-03` Each present item's intact unpowered mass: ___ g.
- [ ] `M-P0-POWER-04` Connector type/dimensions, wire exit, relaxed lead keepout: ___.

Do not open, charge, discharge, connect, or energize a power item for R2 measurement.

### Existing structure and article properties

- [ ] `M-P0-STRUCT-01` Lay out and photograph every tube, frame, plate, bracket, printed part, and existing TVC part; record absent categories.
- [ ] `M-P0-STRUCT-02` Measure each present envelope, wall/plate thickness, and hole pattern.
- [ ] `M-P0-STRUCT-03` Record markings, known material evidence, fastener/pivot types and quantities; leave unknown material blank.
- [ ] `M-P0-MASS-01` List the exact assembled configuration and measure total unpowered mass: ___ g.
- [ ] `M-P0-MASS-02` Measure longitudinal CG from the selected datum using the static guide: ___ mm.
- [ ] `M-P0-DATUM-01` Apply removable X/Y/Z and origin labels; photograph the EDF reference plane and article orientation.

## SHOULD HAVE BEFORE DETAIL DESIGN

- [ ] `M-P1-WIRE-01` Relaxed harness lengths, connectors, bend zones, and strain-relief candidates.
- [ ] `M-P1-SERVICE-01` Connector mating directions and required tool/service access.
- [ ] `M-P1-CG-01` Transverse CG balance status after the longitudinal measurement.
- [ ] `M-P1-FASTENER-01` Actual candidate fastener/pivot head, tool, and retention envelopes.

## CAN DEFER

- [ ] `M-P2-MASS-01` Accessory masses for CH340, ST-Link, or recovery servo only if a later configuration installs them.

## Evidence handoff

For each completed line, record the measurement ID, component ID, date, operator, method, tool, raw value, unit, uncertainty, and photo references. A blank or uncertain result should remain `UNKNOWN`; do not substitute an internet dimension or an old CAD value.
