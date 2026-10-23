# R2.1 ESP-01S target reference

Audit date: 2026-10-23. Input branch HEAD: `e9510e61b6de518b272ea6fdb8433bbab4c501c5`.

## Conclusion and historical gap

The current governed relay builds successfully for a dedicated `esp01_1m` environment without removing the historical/default `nodemcuv2` environment. This closes a **software target/build** gap, not the current physical WiFi regression.

The historical reports of ESP8266-01S telemetry and WiFi-to-servo interaction remain recorded. However, `b6006c9:esp8266_firmware/src/main.cpp` implements only UART -> UDP telemetry, with no UDP receive/command path. This remains a **historical implementation/configuration gap**. No missing historical source or test transport is guessed.

Today's R1 source implements Ground Station -> UDP -> ESP UART -> flight controller command processing -> ACK/NACK -> UDP return to the latest command sender, while telemetry uses broadcast return. The actual installed ESP-01S has not been flashed or tested in this audit. LoRa inherits none of this status.

## Target choices

| Setting | Historical development target | New opt-in module target |
| --- | --- | --- |
| Environment/board | `nodemcuv2` | `esp01_1m` |
| CPU / SDK | 80 MHz ESP8266 / Arduino | Same, no CPU change |
| Nominal physical flash | 4 MiB | 1 MiB (1048576 bytes), matching the order/spec class, not a measured flash ID |
| Arduino linker layout | `eagle.flash.4m1m.ld` | `eagle.flash.1m256.ld`: program region 761840 bytes, reserved 256 KiB filesystem plus EEPROM/RF/WiFi areas |
| Flash mode | Board default DIO | Explicit DOUT; the ESP8266 core describes DOUT as most compatible/slowest, reducing dependence on unverified flash-chip wiring |
| UART upload speed | Existing 921600 | Conservative 115200 |
| Reset arrangement | Development board assumption | Board metadata has `ck`; this does not create USB/DTR/RTS circuitry on a bare ESP-01S. Manual boot/reset remains human-gated. |

Source definitions inspected locally: `platform-espressif8266/boards/{esp01_1m,nodemcuv2}.json` and `framework-arduinoespressif8266/tools/sdk/ld/eagle.flash.1m256.ld`. The default generic `esp01_1m` board uses QIO; the project deliberately overrides it to DOUT. This is a conservative build choice, not proof that the physical module booted.

Upstream references: [PlatformIO ESP-01 1M target](https://docs.platformio.org/en/latest/boards/espressif8266/esp01_1m.html), [ESP8266 Arduino 3.1.2 flash-mode options](https://arduino-esp8266.readthedocs.io/en/3.1.2/ideoptions.html#flash-mode), and [Ai-Thinker ESP8266 document index](https://docs.ai-thinker.com/esp8266). The vendor index currently links an [ESP-01S specification dated 2025-08-02](https://aithinker-static.oss-cn-shenzhen.aliyuncs.com/docs/Public%20Document%20Center/WiFi/esp8266/Specification/ESP-01S%20Specification-20250802.pdf), internally titled V1.1. Relevant complete pages were read: p.7 specifies DIP-8, default 8 Mbit flash and supply current above 500 mA; p.12-13 define pins/boot modes; p.15 recommends 3.3 V with at least 500 mA peak capacity. PDF SHA-256: `83ba3c69b403b3b4ba48ea1367bcfef8262e4bd55d1373f0d206ddd8fa84fb80`. This current vendor requirement supersedes the pre-audit's weaker >300 mA planning statement; it does not measure the installed supply. Exact installed markings/flash identity remain physical observations.

## Source pin/peripheral audit

`esp8266_firmware/src/main.cpp` and `relay_router.*` use WiFi, UDP and default `Serial` at 115200. They contain no `D0`/`D1` NodeMCU aliases, GPIO writes, `Serial.swap()`, alternate UART, I2C or SPI peripheral dependency. Default ESP8266 UART0 is TX GPIO1 / RX GPIO3, exposed by the ESP-01S. No ESP-01 GPIO0/GPIO2 actuator or status-LED dependency is introduced.

This establishes source portability, not actual UART voltage levels, baud stability, WiFi reachability, antenna performance, command authorization or RF range. The current relay is governed plaintext, not an authenticated communications system; ACK/NACK routing still selects the latest command client and does not prove concurrent-client arbitration.

## Build evidence

Command executed, build-only: `pio run -d esp8266_firmware -e esp01_1m -e nodemcuv2`.

Observed packages: PlatformIO Core 6.1.19, `espressif8266` 4.2.1, Arduino core 3.1.2 (`framework-arduinoespressif8266` 3.30102.0), Xtensa GCC 10.3.0 (`toolchain-xtensa` 2.100300.220621), `tool-esptoolpy` 1.30000.201119 (3.0.0).

An existing gitignored `esp8266_firmware/src/wifi_config.h` is present, so the source's `__has_include` branch selects local configuration rather than `wifi_config.example.h`. Its contents were not read, changed or committed by this audit. These sizes/hashes describe that local build; a clean checkout using the example configuration may differ. The build did not connect to WiFi or exercise runtime configuration.

| Build | Result | Static RAM | Program flash |
| --- | --- | --- | --- |
| `esp01_1m` | PASS | 28296 / 81920 bytes (34.5%) | 273147 / 761840 bytes (35.9%) |
| `nodemcuv2` | PASS | 28296 / 81920 bytes (34.5%) | 273147 / 1044464 bytes (26.2%) |

ESP-01S flash headroom in the linked program region: 488693 bytes. Static RAM headroom: 53624 bytes, **not** a measurement of runtime heap, WiFi buffers or stack peaks. The program-region denominator is not the 1 MiB physical-chip capacity. No OTA or filesystem upload was attempted or qualified.

SHA-256 of this run's `.pio/build/esp01_1m/firmware.bin`: `e6a37fb554ef1420495cf9aa96a42c2bae0db307002237650f9a5a163ef9a209`.

SHA-256 of this run's `.pio/build/nodemcuv2/firmware.bin`: `0b4e0a22405f2cfc4004ce8efd3a0d05845b0c4258a3f721060149003d8cae2a`.

Upstream `elf2bin.py` emitted Python `SyntaxWarning` messages for `\s` escape literals; both images were produced successfully. Hashes identify these local outputs, not a reproducible-build guarantee or a physical upload receipt. The final closure report binds final source and artifact evidence if later changes require a rebuild.

## Future boot/program/reset requirements (reference only)

This table defines mode requirements; it is **not** the next human action, an instruction to rewire, or permission to energize/flash hardware.

| Signal/resource | Required interpretation before a later approved physical gate |
| --- | --- |
| VCC / GND | Regulated 3.3 V-class supply, vendor-recommended at least 500 mA peak capacity, and common logic reference; a bare ESP-01S is not a 5 V NodeMCU power input. Current installed supply arrangement is not accepted from old wiring prose. |
| EN / RST | EN asserted high; reset is active-low. The board's actual biasing/reset circuitry must be known; host upload-speed settings cannot supply it. |
| GPIO0 | Sampled low at reset for UART download, high for normal flash boot. No runtime command function is assigned here. |
| GPIO2 / GPIO15 | Boot strap requires GPIO2 high and GPIO15 low. ESP-01S GPIO15 is not a user header pin; do not invent an exposed connection or modify it. Exact module biasing remains an observation. |
| UART0 | GPIO1 TX / GPIO3 RX, 3.3 V logic, crossed with the peer UART. Boot-ROM serial traffic can precede the 115200 application protocol; do not mistake it for FC command acceptance. |
| Reset method | A manual module lacks the NodeMCU USB auto-reset circuit unless separately established. Module markings, straps and accepted power configuration precede any human flash/boot action. |

Maximum evidence earned: `TESTED_SOFTWARE` for both target builds. A later current end-to-end regression must prove the R1 GS/UDP/ESP/UART/FC ACK or NACK return plus telemetry on the accepted exact bench. It does not need servo motion merely to prove transport, and it must not be duplicated as separate ESP and ground-station experiments. Consult `R2_1_GNC_AVIONICS_HUMAN_HANDOFF.md` for the one selected next physical action only.
