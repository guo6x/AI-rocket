# R2 as-built authority

This directory is the current mechanical-input authority for article `AA-TVC-BENCH-001`. It records what the repository can and cannot establish about the physical article. It does not release a design for manufacture.

Evidence precedence is: user measurement record, model-specific datasheet, current code reference, historical prose, then historical CAD. A stronger source may supersede a weaker source only through a reviewed Git change.

## Evidence classes

| Class | Meaning in R2 |
| --- | --- |
| `OBSERVED` | A dated observation record identifies the physical item, but does not establish a numerical measurement. |
| `MEASURED` | A dated measurement record contains method, tool, value, unit, uncertainty, and evidence references. |
| `DATASHEET` | A model-specific manufacturer source is linked, but fit-critical values still require an as-built check. |
| `INFERRED` | Derived from current code or another explicit source; not directly observed. |
| `HISTORICAL` | Preserved prior claim or CAD assumption; reference only. |
| `UNKNOWN` | No acceptable evidence is present. |

## Claim source audit

| Claimed item | Repository sources | R2 treatment |
| --- | --- | --- |
| STM32F103C8T6 / Blue Pill | `project-overview.md`, `flight_computer/platformio.ini`, `flight_computer/src/main.cpp` | Model is claimed and code-targeted; physical identity is `UNKNOWN`, ownership is `REPORTED_PRESENT`. |
| ESP8266-01S | `project-overview.md`, `hardware-wiring-STM32.md`; firmware targets NodeMCU v2 | Conflicting module/board context; actual model and envelope are `UNKNOWN`. |
| GY-91 / MPU6500 / BMP280 | `project-overview.md`, `hardware-wiring-STM32.md`, `flight_computer/src/main.cpp` | Historical module claim plus code addresses; no current identity or measurement evidence. |
| Three SG92R servos | `project-overview.md`; firmware defines pitch, roll, and recovery channels | SG92R is a historical/intended model, not a confirmed installed model. |
| EDF | `project-overview.md` says 70/90 mm and pending purchase; TVC generators assume 74 mm | No EDF is established as part of the current article. All actual dimensions are `UNKNOWN`. |
| Battery / supply / regulator or BEC | Historical wiring and project plan | No current item/model, connector, mass, or envelope is established. |
| CH340 and ST-Link V2 | `project-overview.md`, `hardware-wiring-STM32.md`, PlatformIO comments | `REPORTED_PRESENT`; physical identity and current use lack evidence records. |
| Fasteners, bearings, pivots, frame, tube, printed parts, wiring, TVC hardware | CAD generators and historical output assets | No installed current-article hardware is established. Historical geometry is not an as-built measurement. |

The machine-readable files in this directory govern the article, inventory, measurements, datums, interfaces, mass properties, and evidence references. Historical files remain preserved in place.
