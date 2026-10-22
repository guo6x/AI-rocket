# R2.1 Target Compatibility Pre-Audit

## Scope

This is a pre-audit only. It uses the current repository configuration plus current vendor/platform documentation to identify what is already plausible, what is definitely mismatched, and what must be proven locally before human wiring/flashing.

It does not claim successful hardware operation.

## 1. Flight controller: purchased APM32F103C8T6 vs repository BluePill STM32F103C8 target

### Repository state

`flight_computer/platformio.ini` currently uses:

- `platform = ststm32`
- `board = bluepill_f103c8`
- Arduino framework
- ST-LINK upload
- 115200 monitor
- an explicit OpenOCD `CPUTAPID 0x2ba01477` override described in the file as support for a domestic-compatible chip.

PlatformIO's BluePill target describes an STM32F103C8T6 at 72 MHz with 64 KB flash and 20 KB RAM.

The flight code currently uses, among other interfaces:

- USART2;
- I2C / Wire;
- PA6 and PA7 for the two TVC servo outputs;
- PB0 for the recovery-servo output.

### Purchased-controller evidence

The project asset registry records an APM32F103C8T6 core board.

Geehy's current APM32F103 family documentation describes:

- Arm Cortex-M3;
- up to 96 MHz family operation;
- 2.0-3.6 V supply;
- SWD and JTAG debug;
- multiple USART, I2C, SPI and timer peripherals;
- an APM32F103x4/x6/x8 device family with current datasheet/user manual support.

### Pre-audit conclusion

The hardware is close enough in class that a controlled compatibility audit is justified, and the repository already contains a TAP-ID workaround suggesting prior awareness of a non-ST-compatible target.

However, a BluePill source build is still not proof that the purchased APM32 board is a drop-in runtime target.

Codex/local validation must explicitly check:

1. exact purchased board schematic/pin labels;
2. APM32F103C8T6 package/pin compatibility for PA6, PA7, PB0, USART2 and I2C;
3. clock/startup assumptions made by the Arduino STM32 core;
4. ST-LINK/OpenOCD detection with the configured TAP ID;
5. flash size/linker assumptions;
6. peripheral behavior used by Servo, Wire and HardwareSerial;
7. whether a dedicated APM32 environment should be added rather than silently relying on a BluePill identity.

Until that is done:

- `source build PASS` stays `TESTED_SOFTWARE`;
- APM32 flashing/boot stays `UNKNOWN`;
- no controller is hardware-qualified.

## 2. Sensor: purchased GY-91 order variant vs current firmware assumptions

The project asset registry records a GY-91 order variant specified as MPU9250 + BMP280.

Current firmware:

- addresses the inertial device at `0x68`;
- labels it as MPU6500;
- writes `PWR_MGMT_1`;
- uses fixed scale factors;
- does not verify the IMU identity before printing an OK message;
- addresses BMP280 at `0x76`.

This makes R0-005 more important, not less.

Before any closed-loop servo experiment, local work should introduce a sensor-identity/read-validity boundary that can distinguish:

- actual device identity;
- initialization success;
- sufficient bytes/read success;
- fault/degraded behavior.

No PID tuning should start before this gate.

## 3. WiFi relay: purchased ESP-01S vs repository NodeMCU-v2 target

### Repository state

`esp8266_firmware/platformio.ini` currently uses:

- `board = nodemcuv2`
- Arduino framework
- 80 MHz ESP8266 class
- 921600 upload speed.

PlatformIO documents NodeMCU-v2 as a 4 MB flash development-board target.

### Purchased-module evidence

The project asset registry records an ESP8266 ESP-01S.

Ai-Thinker documentation for ESP-01S specifies:

- DIP-8 module form factor;
- default 8 Mbit / 1 MB SPI flash;
- UART/GPIO interface;
- two exposed general-purpose IO ports;
- 3.0-3.6 V supply;
- supply capability above 300 mA for reliable operation.

PlatformIO provides a dedicated `esp01_1m` board target for a 1 MB ESP-01-class module.

### Pre-audit conclusion

The current `nodemcuv2` environment is not an appropriate final hardware target for the purchased ESP-01S because the board form factor, flash size and programming/reset assumptions differ.

The relay source itself primarily uses WiFi, UDP and the default UART, so an ESP-01S-specific build is technically plausible; that must be proven by a separate target build.

Codex/local work should:

1. add or prototype a non-default `esp01_1m` environment without deleting the historical NodeMCU environment;
2. build the relay under that target;
3. report flash/RAM usage;
4. confirm there are no dependencies on unavailable NodeMCU GPIO;
5. document manual boot/program/reset requirements for ESP-01S;
6. keep upload/physical flashing human-gated.

Do not use NodeMCU build success as evidence for the ESP-01S hardware.

## 4. Immediate priority

The next best engineering task is a software-only/local compatibility pass:

1. APM32 target and pin/peripheral audit;
2. GY-91 identity/validity adapter design;
3. ESP-01S PlatformIO target build;
4. unified check updates;
5. only then produce the exact human wiring/flashing worksheet.

This ordering minimizes the chance that the user is asked to wire hardware around a software assumption that can be resolved first.
