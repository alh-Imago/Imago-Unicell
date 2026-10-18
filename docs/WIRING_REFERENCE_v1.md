# Wiring reference: Tang Nano 20K, ESP32 and the sensors (ledger #1173, 15 Oct 2026)

Every wiring arrangement used or planned in this project, gathered from `docs/unit_bringup_guide.md`, `docs/playout_capture_v1.md`, `tools/esp32/*`, `tools/sd_unit_top_v1.py` and `tools/board_tests_v1.py`. Each section says what was actually checked on the board and what was not. All logic is 3.3 V. Pin numbers for the Tang are FPGA package pins (the numbers printed beside the Tang's headers); for the ESP32 they are GPIO numbers.

| # | Arrangement | Status |
|---|---|---|
| 1 | Tang alone: USB serial to the PC (test results), LEDs, buttons | **Run on the card** (all board tests) |
| 2 | ESP32 <-> Tang SPI link (the "small unit") | **Run on the card**, 8 Oct 2026 (ledger #1036 add. 7) |
| 3 | The Tang's own SD slot (inside the unit) | **Run on the card**, 8 Oct 2026 (SD round trip) |
| 4 | Analog sensors on the ESP32 (potentiometer, light, thermistor) | Wired and read on 10 Oct 2026 (potentiometer, light); thermistor not recorded as run |
| 5 | Digital sensors on the ESP32 (PIR, tilt, ultrasonic) | Tilt and ultrasonic reported working by Alan 17 Oct 2026 (ledger #1201, no values seen); PIR not reported |
| 6 | Direct mode: a sensor wired straight to the Tang, no ESP32 | Pins 72/71 **not checked on the board** |
| 7 | HW-262 shield on the Tang (buttons, 4-digit display, buzzer) | Build exists, **not wired** |
| 8 | The ESP32's own SD card | **Not tried** |
| 9 | ESP32 loading a design through the JTAG test points | **Research only, not built** |

---

## 1. Tang alone: the lines every board test uses

```
 PC  --USB-C--> [ Tang Nano 20K ]
                  |  BL616 USB chip -> two serial ports (ttyUSB0 = JTAG/loader, ttyUSB1 = the FPGA's serial line)
                  |  FPGA pin 69  = UART_TX  (115200 baud, the result line "UCT <name> res=P ...")
                  |  FPGA pin 4   = BOARD_CLK (27 MHz)
                  |  FPGA pins 15-18 = LED0..LED3 (active low): LED0 heartbeat, LED1 pass, LED2 fail, LED3 finished
                  |  FPGA pins 19, 20 = LED4, LED5 (used by the unit builds)
                  |  FPGA pin 88  = button S1 (active high, 1k pull-down): restarts the small unit
```
Loader: `openFPGALoader -b tangnano20k <file>.fs` (SRAM load, lost at power-off). The serial line is read with `watch_serial.py` on ttyUSB1 (opened before the load). Rule found by experiment: power the board off between sessions, and give it one load per power-up.

## 2. ESP32 <-> Tang SPI link (the small unit)

ESP32 is the SPI master, the FPGA the slave. Bare ESP32 dev board on a breadboard, the Tang on the same breadboard, each board on its own USB power, **common ground**.

```
   ESP32 dev board                              Tang Nano 20K
   ----------------                             -------------------------------
   IO5   (CS_N)   --------------------------->  pin 73  left header, hole 1  (IOT40A)
   IO18  (SCLK)   --------------------------->  pin 74  left header, hole 2  (IOT34B)
   IO23  (MOSI)   --------------------------->  pin 75  left header, hole 3  (IOT34A)
   IO34  (READY)  <---------------------------  pin 77  left header, hole 5  (IOT30A, silkscreen LCD_CLK)
   IO19  (MISO)   <---------------------------  pin 76  RIGHT header, hole 3, below 5V and GND (IOT30B)
   GND            ------------------------------ any GND (either header)
                                                (left hole 4 = pin 85, SD data 1: leave unconnected)
```
- MISO is on the opposite header from the other four, so it needs one jumper across the board.
- Count holes from the Tang's own first pin (breadboard column 4 in our setup, not column 8 as first misread from a photo).
- IO5 is an ESP32 strapping pin: safe as chip-select (it idles high) but the FPGA must not drive it during ESP32 boot (the FPGA drives only MISO and READY).
- IO34 is input-only on the ESP32, which is why READY goes there. SPI clock 1 MHz or less on a breadboard (the FPGA needs SCLK below 27 MHz / 16).
- Result on the card: `id` = 0x57320001, scratch register round-trip, CORDIC unit returned all six reference answers, SD round trip passed (8 Oct 2026).
- A diagnostic found while wiring: the sketch's `wires` command drives CS and SCLK by hand so Tang LED1 and LED2 light, proving those two wires before any SPI traffic; `miso` shows whether the MISO wire is driven or floating.
- If the ESP32 is a camera module (ESP32-CAM), the camera uses IO18/19/23: the pins would need to be moved.

## 3. The Tang's own SD slot (inside the unit)

Wired on the board, nothing to connect. Used in SPI mode by the unit (`sd_spi_v1.v`): CLK pin 83, CMD (= MOSI) pin 82, DAT0 (= MISO) pin 84, DAT3 (= CS) pin 81. The board file lists no pull-ups on them. Card used: 16 GB SanDisk Ultra (SDHC), raw 512-byte blocks, no filesystem: a FAT32 card keeps its partition table in block 0, so the tests use blocks 16 and up (input 16, results 17, the round trip used block 64). A first start-up failure (err_code 2) was a contact problem: reseat the card.

## 4. Analog sensors on the ESP32

Use **ADC1 pins only** (GPIO 32-39): ADC2 does not work while WiFi is on, and the web sketch always has WiFi on.

```
   potentiometer:  wiper -> GPIO 35,  ends -> 3V3 and GND
   light sensor:   A0 (signal) -> GPIO 36,  VCC -> 3V3 (never 5 V), GND -> GND
   thermistor:     10k NTC / 10k divider -> GPIO 39  (assumed circuit; swap the resistances if your module is wired the other way)
```
Notes from the 10 Oct 2026 board run: an untouched potentiometer wobbled by about 90 counts, and the light trace swung 0 to about 1200 (likely 100 Hz room-light flicker); the sketch has a `scan` command to tell flicker from wiring faults and an averaging-window slider (default 20 ms). SunFounder's own example reads the light sensor on GPIO 35; ours uses 36 (the table is in `tools/esp32/unicell_unit_web/sensors.h`). The ESP32 ADC is flat near 0 and 4095; readings below about 100 are not trustworthy.

## 5. Digital sensors on the ESP32 (readers written, nothing wired or run)

```
   PIR motion:     signal -> GPIO 16          tilt switch:  signal -> GPIO 17 (internal pull-up, reads LOW when active)
   ultrasonic:     trigger -> GPIO 22,  echo -> GPIO 21 THROUGH A VOLTAGE DIVIDER (the echo pin is 5 V)
   DHT11:          needs the Adafruit "DHT sensor library", off until USE_DHT11 is defined
```
Free digital pins: 16, 17, 21, 22 (and 4, 13, 14, 27, kept free for a later JTAG loader). Pins already taken: 5/18/19/23/34 (link), 25/26/32/33 (the ESP32's own SD card).

## 6. Direct mode: a sensor straight onto the Tang, no ESP32 in the path

This is the arrangement for experiments that show the architecture needs no interrupts and no host: the FPGA samples the pins about once a millisecond, builds a word per input (8192 when active, 0 when not; location = the input number), feeds the design, and latches the newest result. No SPI, no playout RAM, no host program.

```
   digital sensor (PIR, tilt switch, button)            Tang Nano 20K
   signal  --------------------------------------->   pin 72  (input 1)
   signal  --------------------------------------->   pin 71  (input 2)
   VCC     -> 3V3 (signal must never exceed 3.3 V)
   GND     -> GND
```
- The pins are pulled low inside the FPGA, so an unwired pin reads 0.
- **LED5** lights when the result carries at least one active sensor, **LED4** at two or more.
- Bitstream `fpga/build/unit_tree_direct_v1/unit_top.fs` powers up in direct mode: unplug the ESP32 completely and touch the sensor, the LEDs follow. With the tree design, one active sensor gives amount 8192 and two give 16384.
- **CORRECTION (ledger #1202, 18 Oct 2026): pins 72 and 71 are on the RIGHT header at the far end from the USB socket (from that end: 52, 53, 71, 72, 3V3, GND), not beside the link pins.** The text below is the original and is wrong about the location. Pins 72 and 71 are the next two on the same header as the link pins 73-77, but **have not been checked on the board**: if your header differs, change `SENS` in `tools/sd_unit_top_v1.py`.

## 7. HW-262 multi-function shield (buttons, display, buzzer) on the Tang

Bitstream `fpga/build/unit_tree_shield_v1/unit_top.fs` (the tree design in direct mode, sensor pins active low). Power the shield from the Tang's **3V3** into the shield's 5V pin so every signal is 3.3 V; check with a meter first that the shield's 5V pin is the rail the buttons and chips hang off (the shield's own "3.3V" pin goes nowhere). The LM35 temperature sensor does not work at 3.3 V and is unused.

```
   shield (Uno header)                Tang Nano 20K
   S1 button (A1)  ------------------>  pin 72      S2 button (A2)  ------------------>  pin 71
   display latch (pin 4) ------------->  pin 25     display clock (pin 7) ------------>  pin 26
   display data  (pin 8) ------------->  pin 27     buzzer (pin 3) ------------------->  pin 28
   5V pin <- Tang 3V3                    GND <-> GND
```
From the schematic (`docs/hardware/hw262_schematic.png`, a picture only): the display is two 74HC595 chips in a chain, common-anode (a 0 lights a segment); the buzzer is on a PNP transistor, so low = sound; the buttons pull low with 10k pull-ups to the 5V rail through jumper J2. The display shows the result amount as four hex digits (0000 nothing pressed, 2000 one button, 4000 two buttons); the buzzer sounds at two buttons. **Still to confirm on the board:** the clock (7) and latch (4) pin numbers (7 is visible on the schematic, 4 is inferred), that Tang pins 25-28 and 71/72 are on your header, and that the display is bright enough at 3.3 V.

## 8. The ESP32's own SD card (optional)  [run on the card 17 Oct 2026, ledger #1199: card detected after reformat, a 363-byte file uploaded and survived a reset; download content check and delete not reported]

A second card on the ESP32 for bitstreams, input files and results, on a separate SPI bus so the link to the unit is untouched.

```
   SD module        ESP32
   CS        --->   IO32          SCK/CLK  --->  IO33
   MOSI/DI   --->   IO25          MISO/DO  <---  IO26
   VCC       --->   3V3           GND      --->  GND
```
Use a plain 3.3 V-only microSD breakout (for example Adafruit 4682). Avoid the cheap blue modules with a regulator and level shifter (some keep MISO driven when the card is not selected, which stops the card starting on an ESP32). Card 32 GB or less, FAT32. If it will not start: shorter wires, 10 k pull-ups from MISO and CS to 3V3, lower the `SD.begin` clock from 4000000 to 1000000. Insert the card before power-up or press reset.

## 9. ESP32 loading a design through the JTAG test points (research from the Sipeed schematic Rev 1.3, not built)

```
   Tang test points:  TP6 = TMS (pin 5)   TP3 = TCK (pin 6)   TP5 = TDI (pin 7)   TP4 = TDO (pin 8)   TP2 = GND
                      TP1 = RECONFIG_N (pin 9): pulling it low makes the FPGA reload from its flash
```
- The BL616 drives the same four JTAG nets straight from its GPIO pins (no buffer, no series resistor). An ESP32 on the test points would share them: never run openFPGALoader and the ESP32 at the same time, and put about 1 k in series with each ESP32 line. Whether the BL616 releases the pins when idle is unknown.
- The boot flash hangs only on the FPGA's dedicated MSPI pins (59-63, 57), out of the ESP32's reach.
- MODE0/MODE1 = pins 88/87 = the buttons S1/S2. The slave-SPI configuration pins (CS 55, SCLK 52, DIN 54, DOUT 53) are on header J5, but which MODE setting selects that route has not been checked against Gowin's configuration guide.
- Pins 75 and 76 (our MOSI/MISO) are also wired to the BL616's own SPI port. It has stayed quiet so far, which is why the link works.
- Proposed route: the ESP32 reads the new bitstream's blocks from the Tang's SD through the running unit, keeps the ~1 MB file in its own flash, bit-bangs it in over JTAG (SRAM load, volatile, like openFPGALoader), and every generated design keeps the SD + SPI unit so the link returns. The ESP32 pins kept free for this: IO4, IO13, IO14, IO27.

---

## Pin summary

| Tang pin | Use | Section |
|---|---|---|
| 4 | BOARD_CLK 27 MHz | 1 |
| 15-20 | LED0..LED5 (active low) | 1 |
| 69 | UART_TX to the BL616 serial | 1 |
| 71, 72 | direct sensor inputs 2, 1 | 6, 7 |
| 73, 74, 75, 76, 77 | SPI CS_N, SCLK, MOSI, MISO, READY | 2 |
| 81, 82, 83, 84 | SD slot DAT3(CS), CMD(MOSI), CLK, DAT0(MISO) | 3 |
| 25, 26, 27, 28 | shield display latch, clock, data; buzzer | 7 |
| 88 | button S1 (restart the unit) | 1 |
| 5-9 | JTAG TMS, TCK, TDI, TDO, RECONFIG_N (test points) | 9 |

| ESP32 GPIO | Use | Section |
|---|---|---|
| 5, 18, 23, 19, 34 | CS_N, SCLK, MOSI, MISO, READY | 2 |
| 35, 36, 39 | potentiometer, light, thermistor (ADC1) | 4 |
| 16, 17, 21, 22 | PIR, tilt, ultrasonic echo/trigger | 5 |
| 32, 33, 25, 26 | own SD card CS, SCK, MOSI, MISO | 8 |
| 4, 13, 14, 27 | kept free for a later JTAG loader | 9 |

Sources: `docs/unit_bringup_guide.md`, `docs/playout_capture_v1.md`, `tools/sd_unit_top_v1.py` (the `PINS` and `SHIELD_PINS` tables), `tools/board_tests_v1.py`, `tools/esp32/unicell_unit_bridge/unicell_unit_bridge.ino`, `tools/esp32/unicell_unit_web/sensors.h`, `docs/man/tang-nano-20k.man.json`.
