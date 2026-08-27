# R2 staged user measurement checklist

Article: `AA-TVC-BENCH-001`

Keep every item unpowered. Use a phone camera, ruler or caliper, removable labels, and an electronic scale only in the later phases that need them. A ruler should be visible in dimensional photos. Record `PRESENT`, `NOT_PRESENT`, or `UNKNOWN`; absence is a valid evidence-backed result.

Priority (`P0/P1/P2`) describes execution urgency. The phase and `required_for` dependency determine which engineering gate a result blocks.

## Phase A — photo inventory first

Complete this before deciding what must be measured.

- [ ] `M-P0-STRUCT-01` Put every part intended or considered for `AA-TVC-BENCH-001` on a clear surface. Take an overall photo, then front/side/label photos with a ruler for each major item. Record presence, actual label/model where visible, intended article inclusion, and reuse intent.

Include at least:

- EDF, if present;
- two TVC servos;
- existing frame, tube, printed parts, pivot hardware, or TVC mechanical parts, if present;
- STM32, ESP, and sensor board;
- power source, regulator/BEC, wiring, and connectors, if present;
- recovery servo or other optional article parts, if intended for inclusion.

If a frame or old TVC part is `NOT_PRESENT` or `NOT_REUSED`, its conditional dimensions are not required. The observation record and photos are still required to justify that result.

## Phase B — minimum CAD-start measurements

These establish only enough geometry for initial parametric TVC CAD exploration. They do not establish motion acceptance, loads, manufacturing readiness, or full article integration.

### EDF retention geometry

- [ ] `M-P0-EDF-01` Exact model/label and front/rear identity photos.
- [ ] `M-P0-EDF-02` Maximum rigid external diameter: ___ mm.
- [ ] `M-P0-EDF-03` Intended retention/body diameter and axial location: ___ mm / ___.
- [ ] `M-P0-EDF-04` Overall and rigid-body lengths: ___ / ___ mm.
- [ ] `M-P0-EDF-06` Outlet diameter and photographed reference plane: ___ mm.
- [ ] `M-P0-EDF-07` Mounting-feature type/count/thickness: ___ / ___ / ___ mm.
- [ ] `M-P0-EDF-08` Mounting-hole center pattern from the selected datum: ___.
- [ ] `M-P0-EDF-09` Mounting-hole diameter(s): ___ mm.
- [ ] `M-P0-EDF-10` Usable retention/clamping-zone start/end and obstructions: ___.
- [ ] `M-P0-EDF-11` Cable exit position/direction, connector envelope, relaxed keepout: ___.

### Two TVC servos

- [ ] `M-P0-SERVO-01` Label each unit PITCH/ROLL and photograph its identity.
- [ ] `M-P0-SERVO-02` Body L × W × H for each unit.
- [ ] `M-P0-SERVO-03` Mounting-tab length, width, thickness, and case location.
- [ ] `M-P0-SERVO-04` Mounting-hole diameters and center coordinates.
- [ ] `M-P0-SERVO-05` Shaft-center datum, shaft diameter, and protrusion.
- [ ] `M-P0-SERVO-06` Horn type/attachment and linkage-hole coordinates.
- [ ] `M-P0-SERVO-08` Cable exit, cable diameter, connector dimensions, and keepout.

### Datum and conditional existing structure

- [ ] `M-P0-DATUM-01` Apply removable X/Y/Z/origin labels and photograph the EDF reference plane.
- [ ] `M-P0-STRUCT-02` Only if Phase A proves an existing frame/printed/TVC part is present and selected for reuse: measure its envelope, thickness, interface datum, and hole pattern.

STM32, ESP, sensor-board, power, assembled-mass, and CG measurements are not CAD_START blockers.

## Phase C — motion verification and detail design

Required TVC range comes from a governed system/control requirement. Servo or mechanism measurement establishes available range; it does not define the required angle.

- [ ] `M-P0-SERVO-07` Available servo range from model-specific datasheet or gentle unpowered evidence. Do not force or energize.
- [ ] `M-P1-WIRE-01` Relaxed moving-wire lengths, bend zones, connectors, and strain-relief candidates, if wiring is included.
- [ ] `M-P0-EDF-05` EDF inlet diameter/reference plane for detailed flow/interface geometry.
- [ ] `M-P0-EDF-12` EDF mass for load/pivot sizing and article integration: ___ g.
- [ ] `M-P0-SERVO-09` Each TVC servo mass with intended horn/lead: ___ / ___ g.
- [ ] `M-P0-STRUCT-03` Material markings and hardware identity only for observed reuse candidates.
- [ ] `M-P1-FASTENER-01` Fastener/pivot head, retention, and tool-access envelopes only for selected hardware.

Motion verification must later prove:

`available mechanical motion >= approved required TVC motion envelope`

The required pitch/roll range remains `TBD_SYSTEM_REQUIREMENT`; historical ±15° is not accepted.

## Phase D — article integration

- [ ] `M-P0-ELEC-01` STM32 identity, board envelope, heights, and mounting features.
- [ ] `M-P0-ELEC-02` ESP identity/form factor, envelope, heights, and mounting features.
- [ ] `M-P0-ELEC-03` Sensor-board identity, envelope, mounting features, and axis markings.
- [ ] `M-P0-ELEC-04` Electronics connector, mating, wire-exit, and service keepouts.
- [ ] `M-P0-POWER-01` Included power-component identities; evidence-backed `NOT_PRESENT` is valid for optional items.
- [ ] `M-P0-POWER-02` Included power-component external envelopes.
- [ ] `M-P0-POWER-03` Included power-component masses.
- [ ] `M-P0-POWER-04` Included power connector/wire-exit envelopes.
- [ ] `M-P0-MASS-01` Exact assembled configuration and total unpowered mass.
- [ ] `M-P0-MASS-02` Longitudinal CG from `DTM-AA-001` using the static guide.
- [ ] `M-P1-SERVICE-01` Connector mating and tool/service access paths.
- [ ] `M-P1-CG-01` Transverse CG status after longitudinal CG is established.
- [ ] `M-P2-MASS-01` CH340, ST-Link, or recovery-servo mass only if installed in the reviewed article configuration.

Do not open, charge, discharge, connect, or energize power items for these measurements.

## Evidence handoff

For each completed or not-applicable measurement, record the measurement ID, component ID, date, operator, method, tool, raw result, unit, uncertainty, and photo/evidence references. `NOT_PRESENT` and `NOT_APPLICABLE` require observation evidence. Never substitute an internet dimension or historical CAD value.
