# Link test v1: ESP32 to Tang Nano 20K (SPI) and ESP32 search speed

Status: written and compile-checked only (sketch stub-built on a PC, search header run natively). NOT run on the boards. Every number it prints is a first measurement.

## Wiring (ESP32 pin to Tang Nano 20K package pin)

| Signal | ESP32 | Direction | Tang Nano 20K pin |
|---|---|---|---|
| CS_N | IO5 | ESP32 to Tang | 73 |
| SCLK | IO18 | ESP32 to Tang | 74 |
| MOSI | IO23 | ESP32 to Tang | 75 |
| MISO | IO19 | Tang to ESP32 | 76 |
| READY | IO34 | Tang to ESP32 | 77 |
| GND | GND | | GND |

Notes
- Pins 75 and 76 are also the BL616's SPI port; it has been quiet so far.
- Tang pins are the package pin numbers on the right-hand header; count holes from the Tang's own first pin (column 4 in Alan's setup).
- Keep wires short. The sketch runs SCLK at 0.5, 1 and 1.5 MHz; the bridge limit is below 27 MHz / 16 = about 1.69 MHz.
- Do not run the loader and the ESP32 JTAG at the same time.
- Source of the pin list: `docs/unit_bringup_guide.md` and `tools/esp32/unicell_unit_bridge/unicell_unit_bridge.ino` in the main repo.

## Steps
1. Load the unit on the Tang: `openFPGALoader -b tangnano20k fpga/build/unit_cordic_v1/unit_top.fs` (file is tracked in the main repo). LED0 blinking = loaded. S1 = reset.
2. Open `hexn_link_speed/hexn_link_speed.ino` in the Arduino IDE (the folder includes `c4search.h`), board ESP32 Dev Module, upload.
3. Serial Monitor 115200 baud, line ending Newline.
4. `id` should print `0x57320001 ... LINK OK`. LED1 = CS seen, LED2 = SCLK seen, LED4 = MOSI 1 seen. If NO LINK, check wiring first.
5. `link` times register loopback, register reads and 64-word and 1-word transfers at three clock speeds.
6. `search` times Connect Four alpha-beta at depth 3 to 6 on the ESP32 (nodes per second).
7. Paste the printed lines back; they get logged as measurements.

## What the numbers decide
- 1-word row against 64-word row: whether positions are sent one per transaction or in batches.
- Search nodes per second: whether the ESP32 can hold the board and rules, with the Tang doing the judging.
- Arithmetic only (not a measurement): at 1 MHz a 64-word write is 3 + 256 bytes = 2072 bits, so about 2.1 ms of clock time, before the few microseconds of chip-select gaps.
