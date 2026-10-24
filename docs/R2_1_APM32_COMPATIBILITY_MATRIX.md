# R2.1 APM32F103C8T6 compatibility reference

Audit date: 2026-10-23. Input branch HEAD: `e9510e61b6de518b272ea6fdb8433bbab4c501c5`.

## Conclusion and historical boundary

This is an existing, historically flashed controller path, not first-time hardware bring-up. `b6006c9:flight_computer/platformio.ini` already specifies `upload_flags = -c set CPUTAPID 0x2ba01477` and explicitly describes a domestic-compatible chip. The historical flash/boot report remains `HISTORICALLY_REPORTED_HARDWARE`; it is not erased by the STM32/APM32 naming mismatch.

The used APM32 interfaces, pin assignments, memory sizes and Cortex-M3 class match documented interfaces closely enough to retain the existing implementation and add the explicit opt-in `apm32f103c8_compat` build. This is an **experimental STM32-core compatibility alias**, not a native Geehy board port, and not proof of current flash/boot, timing or peripheral operation. The historical `bluepill_f103c8` target remains the default. No clock, memory limit or debug-ID value is increased or guessed.

## Current vendor sources

The live [Geehy APM32F103 product page](https://global.geehy.com/product/fifth/APM32F103) was inspected on the audit date. It currently lists the exact low/medium-density family documents below; the generic family's 96 MHz headline is not permission to change the current 72 MHz configuration.

| Source | What was actually inspected | SHA-256 of retrieved PDF |
| --- | --- | --- |
| [APM32F103x4x6x8 Datasheet V1.5](https://global.geehy.com/uploads/tool/APM32F103x4x6x8%20datasheet%20V1.5.pdf) | 61-page PDF; relevant complete pages: product table (printed p.5), pin table (p.8-11), memory/map (p.15-16), interfaces (p.19), HSE (p.28), ordering (p.54). C8T6 specifically: LQFP48, 64 KB flash, 20 KB SRAM. | `b3d0b480d8840eecca7119fde3a122a662e44fd68fd20453d2eddb686408ea56` |
| [APM32F103x8 Errata Sheet V2.2](https://global.geehy.com/uploads/tool/APM32F103x8%20Errata%20Sheet%20V2.2.pdf) | Entire 12-page PDF, including revision applicability and April 2026 history. | `0f16299bc92decd0f98a03ab1f8d2ad88c7fbae65de5ec810c2241f5f61993aa` |
| [APM32F103x4x6x8xB User Manual V1.9](https://global.geehy.com/uploads/tool/APM32F103x4x6x8xB%20User%20Manual%C2%A0V1.9.pdf) | Link/title verified in the live product page. PDF transfer failed with timeout/proxy closure; its unread contents are **not** asserted as evidence. | Not obtained |

The [GeehySemi SDK V2.0.0 x8 device header](https://github.com/GeehySemi/APM32F10x_SDK/blob/cb084dd9ce994cc6fc449f692cdc78f34d7e2edb/Libraries/Device/Geehy/APM32F10x/Include/apm32f103x8.h) was also inspected read-only at the pinned SDK commit `cb084dd9ce994cc6fc449f692cdc78f34d7e2edb`: `TMR2_IRQn=28`, `I2C1_EV_IRQn=31`, `USART2_IRQn=38`; the used GPIO, USART2, I2C1 and TMR2 base addresses agree with the STM32 mapping. Matching addresses/IRQs do not prove all register semantics. No SDK code was imported.

## Installed toolchain actually audited

PlatformIO Core 6.1.19; `ststm32` 19.4.0; `framework-arduinoststm32` 4.21100.0 (Arduino STM32 core 2.11.0); CMSIS 2.50900.0 (5.9.0); ARM GCC 1.120301.0 (12.3.1); OpenOCD package 3.1200.0. These are observed installed versions, not a permanent dependency lock.

In the paths below, `CORE` means the installed `framework-arduinoststm32` package and `VARIANT` means `CORE/variants/STM32F1xx/F103C8T_F103CB(T-U)`.

| Actual dependency | Installed source evidence | APM32 classification / remaining boundary |
| --- | --- | --- |
| PA6 pitch, PA7 roll, PB0 recovery GPIO | `main.cpp`; `Servo.cpp` calls `pinMode(OUTPUT)` and `digitalWrite`; datasheet pin table: LQFP48 pins 16/17/18 | **Compatible by documented pin/interface**. These ADC-shared pins are 3.3 V-tolerance GPIO, not an assumed 5 V interface. Board header routing and actual actuator pulse levels remain hardware-only. No recovery hardware connection or exercise was performed by this audit. |
| Servo timer | `VARIANT/variant_PILL_F103Cx.h:129-130` defines `TIMER_SERVO=TIM2`; `CORE/libraries/Servo/src/stm32/Servo.cpp:30` creates one timer; callback toggles GPIO; initialization derives a 1 us timer tick | **Likely compatible but unproven** with APM32 TMR2. This implementation does **not** use PA6/PA7/PB0 TIM3 alternate-function PWM. Do not require a TIM3-channel remap or add an invented per-servo timer conflict. Clock-derived period/jitter still needs a present restrained-bench record before timing qualification. |
| USART2 relay UART | `HardwareSerial Serial2(USART2)`; `VARIANT/PeripheralPins.c:138,148`: PA2 TX / PA3 RX; `HardwareSerial.cpp:296-297` selects the matching first pin map; 115200 baud | **Compatible by documented interface/pins**, **likely compatible but unproven** at STM32 HAL runtime. LQFP48 pins 12/13. Physical bidirectional exchange is shared with the R1 WiFi regression, not a separate rediscovery experiment. |
| Debug/ground-station serial | `VARIANT/variant_PILL_F103Cx.h:135-144`: USART1, PA9 TX / PA10 RX | **Compatible by documented interface/pins** (LQFP48 pins 30/31); actual baud/return path unproven today. The default `Serial` path is USART1, not proof of a working native USB device. |
| Wire / I2C1 | `VARIANT/variant_PILL_F103Cx.h:117-121`: PB7 SDA / PB6 SCL; `PeripheralPins.c:66,75`; `Wire.begin()`, 100 kHz | **Compatible by documented interface/pins** (LQFP48 pins 43/42); STM32 HAL behavior, physical pull-ups, sensor identity and read validity remain distinct. `I2C_TIMEOUT_TICK=10` bounds backend waits; `Stream::setTimeout()` does not configure this bus. See timeout caveat below. |
| millis / micros / SysTick | `CORE/cores/arduino/wiring_time.c:25-34`; `CORE/libraries/SrcWrapper/src/stm32/clock.c:29-69`: HAL tick and SysTick counter/handler | Cortex-M3/SysTick are **compatible by documented interface**; absolute rate and interrupt latency are **hardware-only proof required** under the real oscillator/clock tree. |
| Flash / SRAM / linker | BluePill board JSON: 65536 / 20480 bytes; `VARIANT/ldscript.ld:39-40`: SRAM `0x20000000`, flash `0x08000000`, lengths from board limits; minimum heap 0x200 / stack 0x400 | **Compatible by documented C8T6 capacity/map**. Keep 64 KiB / 20 KiB; no undocumented 128 KiB enlargement. Link success is not stack/heap exhaustion or device flash-programming proof. |
| Startup / clock / flash wait states | `VARIANT/variant_PILL_F103Cx.cpp:95-133`: HSE on, HSE x9 PLL, AHB /1, APB1 /2, APB2 /1, flash latency 2; default HSE 8 MHz in `CORE/system/STM32F1xx/stm32f1xx_hal_conf_default.h:82-87` | **Likely compatible but unproven**. Vendor allows a 4-16 MHz HSE and 96 MHz maximum, but neither proves this board has an 8 MHz crystal or identical RCM/flash behavior. Keep 72 MHz assumptions; no automatic fallback/overclock was added. |
| ST-LINK / SWD / OpenOCD | Historical and current TAPID `0x2ba01477`; installed `target/stm32f1x.cfg` consumes `CPUTAPID`, then instantiates the `stm32f1x` flash driver | SWD is **compatible by documented interface**; exact detect/erase/program/verify behavior is **hardware-only proof required**. The ID override changes the expected debug-port ID; it does not identify a unique chip, certify the flash driver, or prove a current upload. No debugger/upload command was executed. |
| Native APM32 identity/support claim | Installed PlatformIO STM32 boards and OpenOCD scripts contain no dedicated APM32 target used here; compatibility env still names BluePill | **Incompatible as a native-support claim**. A new native BSP/startup/flash-driver port is not justified by this audit alone. The opt-in alias exposes the actual assumption without inventing such support. |

### Timeout and errata caveats

`CORE/libraries/Wire/src/utility/twi.c:47-50` defaults to a 100-tick wait. Both firmware environments now compile it with `I2C_TIMEOUT_TICK=10`; the same core's SysTick units are milliseconds. The busy retry and transfer-completion phases use separate start times (`twi.c:984-1023`, `1069-1112`), and a register read includes a write phase plus read phase. Therefore this is **not** a claim that an entire sample or command response is bounded to 10 ms. Adapter/sample budgets and native fault tests are software evidence only; actual stuck-bus/ESTOP latency requires a later current hardware trace.

Current x8 errata must not be silently inherited away:

- Section 3.2 applies GPIO alternate-function push-pull/floating-input interference cautions to A1/A2/B1 revisions. The vendor recommends external pull-up treatment for AF push-pull outputs; USART TX is relevant. Existing board circuitry and exact chip revision are unknown. This audit does not instruct unverified rewiring. Servo GPIO output is not the AF-PWM mode described in that erratum.
- Section 5.1 warns about HSE startup timeout. Its `0x3200` recommendation describes an older library's wait-count configuration. The installed STM32 HAL uses `HAL_GetTick()` and a 100 ms `HSE_STARTUP_TIMEOUT`; copying the numeric loop count into a millisecond macro would be unjustified. Actual HSE startup remains unproven.
- Section 5.2 addresses a PLL-to-24-MHz/MCO condition; current source uses 72 MHz and no PA8 MCO output. PA8/PC8 at 2 V, low-power wake and power-consumption errata are not evidence that the present used path fails, nor evidence that it has passed.

## Target/build result and evidence ceiling

`apm32f103c8_compat` extends `env:bluepill_f103c8`, inherits the bounded I2C flag and historical TAPID, and adds only `AI_ROCKET_APM32_COMPAT_EXPERIMENTAL=1`. `native` explicitly enables GNU C++11 and uses `-Itest/fakes` for the real-main host harness; the fake headers are not firmware build flags.

Final frozen-source build results: `bluepill_f103c8` and `apm32f103c8_compat` both PASS with 55136 / 65536 flash bytes (84.1%) and 3060 / 20480 RAM bytes (14.9%). The generated `.bin` SHA-256 is `58b830790b16c51303a984de30b9636fafbfe07cbb3aac6c73831641f84c65d4` for both environments. Identical output is expected because the compatibility marker is compile-time metadata only; it does not mean APM32 hardware was flashed or run. The final closure report should bind the repository commit and this software-only evidence.

Maximum evidence earned remotely: `TESTED_SOFTWARE` plus documented compatibility. Historically demonstrated flash/boot, GPIO servo movement and sensing do not need blanket repetition. Only present uncertainties (actual marking/revision/oscillator/header mapping, changed sensor safety, changed command safety, current UART/UDP return path) justify a targeted regression. Consult the single-action human handoff; this reference is not a physical execution procedure or a hardware/flight release.

## Installed-source fingerprints

SHA-256 values recorded to make the non-repository toolchain audit reproducible:

| Installed file | SHA-256 |
| --- | --- |
| `ststm32/boards/bluepill_f103c8.json` | `921a06085e8d3cafc36ae2878cc06a673cc2eae84e2431a3fee06b3b90fc68f1` |
| `VARIANT/variant_PILL_F103Cx.h` | `5feafd9d60691af36f9085442241c6623cfba75b5144b8730587dbefd771bb85` |
| `VARIANT/variant_PILL_F103Cx.cpp` | `8a803d7ef1146d3b6ab2625bef538c58f7ec66bc5f70e1e2edf289120fd2b7bd` |
| `VARIANT/PeripheralPins.c` | `1dcac20abe64e20bbef6bf6f9a6685ff2f701cedb9f02b62ca3aaf04a7a54b14` |
| `CORE/libraries/Servo/src/stm32/Servo.cpp` | `40b17a311db2b46302ecf3e268b362182c67e5a3d7d9a5d3a8857d461a125d6a` |
| `CORE/libraries/Wire/src/utility/twi.c` | `8b3933ab56b85b48d0bd3fb14ea0789281f7eab101fc4a238426f168a91bb0fb` |
| `tool-openocd/openocd/scripts/target/stm32f1x.cfg` | `fe44c3ade7395db34a751c57401ebc2a176ed1ca793c47081cc9f06a8618125e` |
