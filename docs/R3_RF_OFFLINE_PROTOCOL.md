# R3.0 — RF/LoRa offline telemetry protocol prototype

**Technical line:** `AA-RF-BENCH-001`  
**Authority:** `engineering/rf-offline-contract.yaml`  
**Evidence level:** software-only experiment; **not hardware or radio verification**.

## Why a separate protocol?

The project owns **two SX1278 RA-02** modules, adapter cables and nominal 433 MHz antenna accessories, but the existing repository does not contain equivalent verified LoRa transmission or reception records. The historically exercised ESP8266/UDP telemetry and command path is a *different physical transport* and must not be used as proof of LoRa operation.

R3.0 deliberately isolates RF software from the flight computer, recovery controller and Ground Station command operations. There is **no radio driver, serial connection, frequency/power configuration, command transmission or hardware actuation**.

## Proposed software-only datagram

One simulated datagram carries exactly one frame. Big-endian wire format:

| Field | Bytes | Contract |
|---|---:|---|
| magic | 2 | ASCII `AR` |
| version | 1 | `1` |
| kind | 1 | `1` = telemetry only; other values rejected |
| session_id | 4 | unsigned; unauthenticated epoch label |
| sequence | 2 | unsigned 16-bit, wraps modulo 65536 |
| payload_length | 2 | unsigned |
| payload | 1–160 | **opaque telemetry bytes**, not flight commands |
| CRC32 | 4 | IEEE CRC-32 of header plus payload, big-endian |

Overhead is **16 bytes** and the experimental frame ceiling is **176 bytes**. The 160-byte application-payload budget is **not** a claim that any specific modem configuration or hardware will support this traffic or timing.

The parser fails closed on malformed length, wrong magic/version/kind, truncation, excess length and CRC mismatch. CRC detects accidental corruption; **it is not authentication, integrity against an active adversary, replay defense, encryption or any kind of authority**.

The receiver classifies accepted, duplicate, stale/out-of-order and new-session frames. It estimates the count of *unobserved sequence numbers*, not measured RF packet losses. Session changes are unauthenticated and not automatically trusted for a real operational system. A valid-CRC payload such as `arm` remains uninterpreted bytes; it is never passed to the flight-controller command processor.

## Repository files

- `rf_lab/telemetry_frame.py`: standard-library encode/decode and freshness classifier.
- `rf_lab/offline_link_replay.py`: deterministic synthetic replay with deliberate dropped, damaged, repeated, out-of-order and session-changed packets.
- `rf_lab/tests/test_telemetry_frame.py`: framing/sequence boundary tests.
- `rf_lab/tests/test_offline_link_replay.py`: fault behavior/determinism tests.
- `scripts/check.py`: runs isolated RF tests as an additional software gate.
- `engineering/rf-offline-contract.yaml`: formal scope and evidence ceiling.

## Offline check

From the repository root:

```powershell
py -3 -m unittest discover -s rf_lab/tests -v
py -3 -m rf_lab.offline_link_replay
py -3 -m rf_lab.offline_link_replay --write-evidence engineering/offline-evidence/r3/rf_offline_replay.json
```

The original 31-test candidate result above is historical evidence and is retained as such; it is not the result for later branch heads. The current replay evidence records the exact delivered synthetic datagrams, explicit fault schedule, input-trace SHA-256, source-file SHA-256 values, source Git HEAD, whether provenance inputs were dirty, Python/platform versions, command and evidence ceiling. It is reproducible software evidence only.

## Official RA-02 / SX1278 document review

I reviewed Ai-Thinker's official **Ra-02 LoRa Product Specification V1.1** (two pages; PDF metadata date 2017-12-19): [official PDF](https://aithinker-static.oss-cn-shenzhen.aliyuncs.com/docs/Public%20Document%20Center/LoRa/lora/Specification/Ra-02_V1.1%20Specification-20171219.pdf) and [RA-02 documentation page](https://docs.ai-thinker.com/en/Ra-02/). The document identifies the RA-02/SX1278, SPI half-duplex, 410–525 MHz, typical 3.3 V supply, and describes a packet-CRC engine “up to 256 bytes.” This is vendor-document evidence, not identification or testing of the owned boards.

The proposed maximum software frame is 176 bytes. Although 176 is numerically below 256, this comparison does **not** establish that 176 application bytes plus this protocol's four-byte IEEE CRC are supported by the module's packet/FIFO path: the short product specification does not define what is counted in the 256-byte statement or how that feature maps to this software frame. The packet engine's CRC and the software CRC are not assumed to be the same or interchangeable.

The following chip/module adapter assumptions remain `UNKNOWN / NOT VERIFIED`: exact SMD-16 pin mapping and module revision; SPI register/FIFO addresses and transfer sequence, mode, clock and chip-select timing; DIO/RESET mapping and interrupt behavior; radio packet/header and CRC configuration; whether the software frame maps one-to-one to a radio packet or needs length adaptation/fragmentation; receive scheduling; and antenna/connector identity. Operating-region frequency and transmit authorization also remain unevaluated. Semtech's official [SX1276 product page](https://www.semtech.com/products/wireless-rf/lora-connect/sx1276) lists the `SX1276-7-8-9 Datasheet`, but its PDF body was not reviewed in this pass, so no register-level claims are attributed to it.

## Next-step acceptance

1. Confirm exact committed SHA and run all RF unit tests directly from the branch.
2. Perform negative/mutation testing on strict length checks, CRC handling, new-session freshness and sequence wrap.
3. Run complete `python scripts/check.py` without resource-contention parallelism; report each pre-existing GNC/ESP/native/ground-station gate.
4. Treat the vendor-document comparison above as a limited desk review only; resolve the listed adapter assumptions from the exact vendor/module documentation before implementing a driver, without setting transmitter power/frequency or touching hardware.
5. Identify operational risks separately: missing authenticated source identity, unauthenticated session resets, radio regulatory constraints, and physical antenna/module connector uncertainty.
6. Preserve the existing WiFi transport and all historical source and evidence files. Do not connect RF telemetry to the flight-command path.

## Explicit exclusions

No radio transmission, no GPIO/SPI wiring, no programming any RA-02, no frequency or output power advice, no recovery/servo command channel, no free flight and no hardware acceptance. This is a standalone software experiment that informs a future radio qualification plan, not the qualification itself.
