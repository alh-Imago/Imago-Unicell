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
- Tang pins are the package pin numbers printed on the board's pinout (Alan's picture, 31 Oct 2026). With the USB-C socket at the top, they sit on BOTH headers, not one:
  - left header, top to bottom: **73, 74, 75**, 85, **77**, 15, 16, 27, 28, 25, 26, 29, 30, 31, 17, 20, 19, 18, 3V3, GND
  - right header, top to bottom: 5V, GND, **76**, 80, 42, 41, 56, 54, 51, 48, 55, 49, 86, 79, GND, 3V3, 72, 71, 53, 52
  - so CS_N (73), SCLK (74), MOSI (75) are the top three on the left; READY (77) is the fifth on the left (pin 85 sits between 75 and 77); MISO (76) is the third on the right. (The first version of this sheet said "right-hand header" for all five; that was wrong. The wiring that worked on the boards is whatever Alan actually connected; this table is what the pin numbers mean.)
  - pins 15 to 20 drive the six on-board LEDs.
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
