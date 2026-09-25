# ESP32 ⟷ BL616 Link Protocol — v0.1 (draft)

Status: draft, pre-hardware. Written before the Tang Nano 20K board arrives, to give
BL616 firmware work a fixed contract to build against rather than an ad-hoc one
discovered later.

## 1. Relationship model

ESP32 and BL616 are two separate tools, each owning its own state and its own SD
card. This is a peer data-sharing link, not a load/bus relationship — neither side
reaches into the other's internals, memory, or storage directly. All exchange happens
through this protocol.

- **BL616 side**: owns the Tang Nano's SD card (reference data, programming images),
  the 64Mbit flash (stable bitstream images), and the FPGA fabric (JTAG/SPI/UART to
  the Gowin chip — its existing built-in role, unchanged).
- **ESP32 side**: owns its own SD card (web assets, session data, results held for
  or served to the web front end), and the wifi/web-facing UI.

## 2. Physical link

- Direct GPIO wiring between ESP32 and BL616 — no USB involved on this link (BL616's
  USB stays dedicated to its existing PC-facing JTAG/UART/SPI role).
- **Data lines**: UART or SPI, TBD based on §6 below.
- **Attention line**: one extra GPIO, BL616 → ESP32, toggled when BL616 has something
  ready (a result, a status change) — avoids constant polling from the ESP32 side.
- Pin assignments: TBD once board is in hand and available GPIOs are confirmed.

## 3. Framing

Every message is a packet, not a raw byte stream, so a dropped byte doesn't desync
the link with no recovery path.

| Field | Size | Notes |
|---|---|---|
| SYNC | 1 byte | Fixed marker (e.g. `0xA5`) so a receiver can resync after noise/loss |
| VERSION | 1 byte | Protocol version this packet was built against (§5) |
| TYPE | 1 byte | Message type (§4) |
| LENGTH | 2 bytes | Payload length in bytes |
| PAYLOAD | 0–N bytes | Type-specific content |
| CHECKSUM | 1 byte | Simple sum or XOR checksum over TYPE+LENGTH+PAYLOAD |

If checksum fails, receiver drops the packet and waits for the next SYNC byte —
no automatic retry at this layer yet (see §7 open items).

## 4. Message types (initial set)

| Type | Direction | Purpose |
|---|---|---|
| `HELLO` | either | Handshake: announce protocol version, request/confirm compatibility |
| `BITSTREAM_SELECT` | ESP32 → BL616 | Request a specific bitstream image (from 64Mbit flash) be loaded — slow, full fabric reconfigure |
| `PATTERN_PUSH` | ESP32 → BL616 | Push a trained pattern (ICM-style config data) into the already-running substrate — fast, no reconfigure |
| `REF_DATA_REQUEST` | ESP32 → BL616 | Ask for a block of reference data held on the Tang's SD card |
| `REF_DATA_RESPONSE` | BL616 → ESP32 | Requested reference data block |
| `RESULT_READY` | BL616 → ESP32 | Signals new result data is available (paired with the attention line) |
| `RESULT_DATA` | BL616 → ESP32 | The actual result payload |
| `STATUS_REQUEST` | ESP32 → BL616 | Ask current state (which bitstream loaded, fabric busy/idle, last error) |
| `STATUS_RESPONSE` | BL616 → ESP32 | Current state payload |
| `ERROR` | either | Malformed request, unknown type, checksum failure report, etc. |

This set will grow — treat it as a starting vocabulary, not final.

## 5. Versioning

- VERSION byte in every packet header (§3).
- On `HELLO`, both sides declare their protocol version. If they don't match, the
  side detecting the mismatch responds with `ERROR` rather than guessing at
  compatibility — since BL616 firmware and ESP32 firmware will be iterated on
  independently, silent misinterpretation after a one-sided update is the failure
  mode this guards against.

## 6. Initiation model

- ESP32 is generally the initiator for requests (bitstream select, pattern push,
  reference data, status).
- BL616 uses the attention line to signal `RESULT_READY` proactively rather than
  waiting to be polled — assumes BL616 can toggle a GPIO independently of servicing
  a UART/SPI transaction, which should hold true given it's a real MCU with its own
  firmware loop.
- **Open question feeding into UART vs SPI choice**: does the ESP32 ever need bulk
  reads from the Tang SD card (large reference datasets), or is traffic realistically
  small structured request/response? Bulk favors SPI; small/simple favors UART's
  lower complexity. Revisit once real data sizes are known.

## 7. Open items

- Pin assignments (depends on board GPIO availability once in hand).
- UART vs SPI decision (§6).
- Retry/resend behavior on checksum failure — none defined yet, currently just drop.
- Whether `PATTERN_PUSH` payload format tracks the existing UniCell ICM v3 format,
  or needs its own variant for the neural substrate's discrete lane/gate/threshold
  config.
- Real GPIO pin count/timer budget check once BL616 firmware work starts, alongside
  its existing JTAG/UART/SPI/MS5351 duties.
