# Small unit bring-up guide: Tang Nano 20K + ESP32 (CORDIC unit)

Ledger #1036. The CORDIC unit, the SPI link and the SD round trip have all run on the real Tang Nano 20K (see the results below); the WiFi sketch has not. The order below goes from "does the link talk at all" to "does the card work", and each step has a clear pass/fail.

## What you need
- Tang Nano 20K with the 16 GB SanDisk Ultra (SDHC) in its microSD slot, USB-C cable.
- The ESP32 dev board on the breadboard, USB cable, 5 jumper wires plus a ground wire (table in `docs/playout_capture_v1.md`):
  CS_N IO5 -> pin 73, SCLK IO18 -> 74, MOSI IO23 -> 75, MISO IO19 <- 76 (right-hand header), READY IO34 <- 77, GND to GND.
- A PC with: Arduino IDE 2, and a way to load the FPGA bitstream (step 1).

## Step 1 -- load the FPGA (no ESP32 needed yet)
The ready-made bitstream is `fpga/build/unit_cordic_v1/unit_top.fs` (CORDIC unit: 2,556 LUT4 = 12%, 4 of 46 block RAMs, 155 MHz capable, 27 MHz used).
Use whichever loader you already used for the smoke test:
- command line: `openFPGALoader -b tangnano20k fpga/build/unit_cordic_v1/unit_top.fs` (SRAM: lost when the board loses power; add `-f` to write it to flash);
- or the Gowin Programmer program: device GW2AR-18, "SRAM Program", file `unit_top.fs`.
LEDs (lit = true): **LED0 (the first LED) blinks slowly (about once a second) = the FPGA is loaded and running. If LED0 is not blinking the bitstream did not load.** LED1 = the ESP32 has pulled chip-select low at least once (stays lit until the next load). LED2 = the ESP32 has clocked SCLK at least once. LED3 = the SD card is up and error-free. LED4 (the fifth LED) = a 1 has arrived on MOSI while chip-select was low: it proves the MOSI wire. (LED1, LED2 and LED4 stay lit until you press the Tang's **S1 button** or reload the FPGA; LED5 is unused.) **S1 (see the S1 label on the board) is the unit's reset:** hold it for a moment and the whole unit restarts as at power-up (SD card re-initialised, registers cleared, LED1/2/4 cleared) with no reload. If it does nothing, the bitstream predates 9 Oct 2026. So: after loading, LED0 should blink; after the first `id`, LED1 and LED2 should light; if they don't, the CS or SCLK wire isn't reaching the FPGA.

## Step 2 -- ESP32 side (one time)
1. Install Arduino IDE 2 (arduino.cc).
2. Boards: File > Preferences > "Additional boards manager URLs", add `https://espressif.github.io/arduino-esp32/package_esp32_index.json`. Tools > Board > Boards Manager > search "esp32" > install "esp32 by Espressif Systems".
3. Tools > Board > "ESP32 Dev Module" (or the exact board you have). Tools > Port > the ESP32's COM port.
4. File > Open `tools/esp32/unicell_unit_bridge/unicell_unit_bridge.ino` (the folder name and file name must match, as they do). Upload. If it says "Connecting......", hold the board's BOOT button until it starts.
5. Tools > Serial Monitor, set **115200 baud** and **Newline** at the bottom. You should see "UniCell unit bridge ready" and the ID check.
Pins are `#define`s at the top of the sketch if your wiring differs.
If the ESP32 is a camera module (ESP32-CAM) the camera uses several of IO18/19/23: tell me which board it is and I will re-pin.

## Step 3 -- the test ladder (type each into the Serial Monitor)
| command | pass looks like | if it fails |
|---|---|---|
| `id` | `ID = 0x57320001 OK` | `0x00000000` or `0xFFFFFFFF`: MISO/CS wiring or no common ground; check FPGA is loaded |
| `scratch` | `SCRATCH read-back OK` | wiring on MOSI/SCLK; lower `SPI_HZ` (500000) |
| `cordic` | six lines `ok`, `CORDIC OK` (z0=50000 -> -404) | wrong numbers: tell me which |
| `status` | `sd_ready=1 sd_error=0`, `READY pin=1` | sd_ready=0: card not found; sd_error=1 gives an err_code (send me the line) |
| `sdtest` | `SD ROUND TRIP OK` | send me the whole output |

`cordic` needs no SD card at all (the ESP32 pushes the angles in over SPI), so it proves the FPGA design and the link before the card is involved. `sdtest` uses raw card block 64 (change with `sdtest 200`); it overwrites that block. **The sketch refuses blocks below 16**: block 0 holds a FAT32 card's partition table. A raw-written block inside the card's file area will corrupt a file there, so use a spare card, or re-format afterwards.
`wires` drives CS and then SCLK by hand for 4 s each so you can watch Tang LED1 and LED2 light: it proves those two wires arrive before any SPI traffic is involved.
`miso` tells you whether the MISO wire is connected to something that drives it (it reads the pin with the ESP32's pull-down and pull-up in turn: a floating wire changes, a driven one doesn't).
**Counting holes on the Tang:** the Tang's header pins do not start at breadboard column 1; count from the Tang's own first pin (in our setup column 4; always count from the Tang's own first pin), and wire 'hole 1' there. A wire in a column with no Tang pin connects to nothing.
`status` also reports which SD command failed and the last byte the card sent (FF = the line sat idle high, i.e. the card said nothing; 00 = stuck low). `sdinit` re-runs the card start-up without reloading the FPGA: reseat the card, type `sdinit`, then `status`.
**First hardware result (8 Oct 2026):** `id`, `scratch` and `cordic` all passed on the real Tang Nano 20K + ESP32: the six CORDIC angles matched the simulator. The SD card then reported error 2 (no answer from the card); reseating the card fixed it (a contact problem), and `sdtest` then passed: SD ROUND TRIP OK. If it drops out again: reseat, `sdinit`, `status`.
Other commands: `z 100 200 300` (your own angles), `load 64 1` / `save 64 1`, `reg 8` (read a register), `reg 7 0x1234` (write), `words 0 8` (dump results RAM), `help`.

## Reading the unit by hand (for later designs)
Live sensors are now read on the ESP32's second core (`sampler.h`), so a slow sensor no longer holds up the page, and the Live sensors card draws a plot: a strip chart (one band per input plus the design's result) or an X-Y plot of input 1 against input 2. The page polls five times a second while the feed is on.

The page's "Design on the Tang" tile reads the bitstream's design ID (register 10) and warns if it differs from the Setup choice (one click fixes Setup). Bitstreams built before 9 Oct 2026 have no ID and show grey; reload the current `.fs` files to get it.

Registers, SPI protocol and the card layout are in `docs/playout_capture_v1.md` and `fpga/build/unit_cordic_v1/lanes.json`. A different design is wrapped the same way: `python3 tools/sd_unit_top_v1.py --icm <design.icm> --output <dir>` then `tools/gowin_sizing/build_unit_bitstream.sh <dir>`.

## WiFi remote control (ledger #1036 addendum 9)
`tools/esp32/unicell_unit_web/` is a second sketch (same wiring, same SPI layer in `unit_link.h`) that puts the unit on your WiFi. **It has been syntax-checked and its logic is covered by the simulation tests, but it has not yet been run on a real ESP32: treat the first run as a test.**

1. Nothing to edit in the sketch for the design any more. Upload it, then on the web page's **Setup** card choose the design that is loaded on the FPGA (CORDIC, Relay or Tree; it must match the bitstream on the Tang) and which sensor feeds each input; press Save setup. The choice is kept in the ESP32's flash, and `design cordic|relay|tree` in the Serial Monitor does the same for the design. This sets how many input words make one item and what the page says.
2. Upload it the same way as the serial sketch (Arduino IDE or `arduino-cli compile/upload`, board ESP32 Dev Module).
3. Serial Monitor (115200, Newline): the first boot prints a generated web password. Type `wifi <ssid> <password>`; it restarts, joins your WiFi and prints the address. Other commands: `ip` (address + password), `webpass <new, 8+ chars>`, `wificlear`, `id`, `reboot`.
4. Open `http://unicell.local/` (or the printed IP) in a browser on the same WiFi. Login: user `unicell`, the web password.
5. If WiFi cannot be joined, the ESP32 makes its own network **UniCell-Unit** (password = the web password); join it and open `http://192.168.4.1/`.

The page shows the unit status (ID, SD card, errors), a box to type input numbers (one item per line, or separated by anything that is not a digit), and a Run button that sends them over SPI, plays them through the design and shows the results. A second panel loads input from, or saves results to, raw SD blocks (blocks below 16 are refused).
Endpoints (for scripts): `GET /api/status`, `POST /api/run` (field `items`), `POST /api/sd` (`op`=load|save, `block`, `n`), `POST /api/sdinit`. Example: `curl -u unicell:PASSWORD -d "items=50000 -50000 0" http://unicell.local/api/run`.
**Limits, honestly:** plain HTTP with a password, for a trusted home or lab network only, never the internet; at most 512 words per run; one request at a time; it can overwrite raw SD blocks (16 and up).

## Loading a new design from the ESP32 (research from the Sipeed schematic Rev 1.3; NOT built, NOT tried)
What the schematic (Tang_Nano_20K_3923, 28 Aug 2025) shows:
- **JTAG test points** on the board: TP6 = TMS (FPGA pin 5), TP3 = TCK (pin 6), TP5 = TDI (pin 7), TP4 = TDO (pin 8), TP2 = GND. **TP1 = RECONFIG_N** (pin 9): pulling it low makes the FPGA reload from its flash.
- The BL616 USB chip drives the same four JTAG nets straight from its GPIO pins (no buffer, no series resistor). An ESP32 wired to the test points would share those nets, so: never run openFPGALoader and the ESP32 at the same time, and put about 1 k in series with each ESP32 line. Whether the BL616 leaves the pins released when idle is not known.
- The boot flash (XT25F64F, 64 Mbit) hangs only on the FPGA's dedicated MSPI pins (59-63, 57). The ESP32 cannot reach it; the FPGA reads it itself at power-up.
- MODE0/MODE1 are pins 88/87 = the two buttons S1/S2 (each pulled low by 1 k). The slave-SPI configuration pins (CS 55, SCLK 52, DIN 54, DOUT 53) are also on header J5, but which MODE setting selects that route has not been checked against Gowin's configuration guide.
- The FPGA's pins 75 and 76 (our MOSI/MISO) are also wired to the BL616's own SPI port. It has stayed quiet so far, which is why our link works.
Proposed route: (1) the ESP32 reads the new bitstream's blocks from the SD card through the running unit (needs a raw-block read register in the bridge), keeps the ~1 MB file in its own flash; (2) it bit-bangs it into the FPGA over JTAG through TP3-TP6 (SRAM load, volatile, like openFPGALoader now); (3) every generated design already contains the SD + SPI unit, so the link returns. TP1 would let the ESP32 reboot the FPGA from the board flash. Persistent install of a finished design stays `openFPGALoader -f` from a PC.

## The ESP32's own SD card (optional; ledger #1036 addendum 13)
A second card, on the ESP32 itself (NOT the one in the Tang's slot), to keep bitstreams, input files, results and the offline kit, and to upload or download them from the web page ("Files on the ESP32's own card"). It uses a separate SPI bus on four free pins, so it does not touch the link to the unit:

| SD module | ESP32 pin |
|---|---|
| CS | IO32 |
| CLK / SCK | IO33 |
| MOSI / DI | IO25 |
| MISO / DO | IO26 |
| VCC | 3V3 |
| GND | GND |

**Which module to buy:** a plain **3.3 V-only microSD breakout** (a bare socket on a small board, for example Adafruit's "MicroSD SPI or SDIO card breakout", product 4682, which is marked "3V ONLY"). Avoid the very cheap blue modules with a voltage regulator and level shifter: they are made for 5 V boards, and some keep the MISO line driven even when the card is not selected, which makes the card fail to start on an ESP32 (reported on the Arduino forum). If you already own one, power it from 5 V (VIN) only if it has the regulator, and if the card still does not start, that is the cause. Use a card of 32 GB or less (SDHC), formatted FAT32; a spare 8-16 GB card is plenty. A tiny 20x18 mm bare 3.3 V module sold in 10-packs with 6-way pin strips to solder (CS, MOSI, CLK, MISO, 3V3, GND; read the order off its silkscreen, it varies) is the right kind. If the card will not start, shorten the wires, add a 10 k pull-up from MISO and from CS to 3V3, and lower the 4000000 in `SD.begin` to 1000000. The card is read when the ESP32 starts, so insert it before power-up or press the ESP32's reset. Files: names of letters, digits, . - _ and space (at most 40, no folders), up to 32 MB each. **Not yet tried on hardware.**


## Live sensors (addendum 17, not run on hardware)
`tools/esp32/unicell_unit_web/sensors.h` lists the sensors you can choose from (the Setup card picks which one feeds each input); the web page's **Live sensors** panel (and `GET /api/live`) reads them, turns each into a SensorTrix word (amount in bits 31..16, location number in bits 15..0), runs one item through the design and shows the readings and the result. Defaults: three analog inputs on GPIO 35, 36, 39. Use **ADC1 pins only** (GPIO 32 to 39): ADC2 does not work while WiFi is on. To add a sensor from your pack, add one line to `SENSORS[]`: an ADC1 pin for an analog sensor, or pin -1 and a function returning 0..65535 for an I2C/digital one (include its Arduino library at the top of `sensors.h`). The number of sensors listed must be at least the design's input lanes (1 for CORDIC and relay, 4 for the tree). The CORDIC build receives the raw amount as its angle, so scale it in your function. Simulated end to end: `tests/vm/test_unit_live_feed_v1.py`.

### Parts from the SunFounder ESP32 Ultimate Starter Kit (readers written, nothing wired or run)
`sensors.h` has ready readers for: potentiometer, light sensor and soil moisture (plain analog, ADC1 pins 35/36/39 only), thermistor (assumed 10 k NTC, B 3950, 10 k divider; swap the resistances if your module is wired the other way), button / tilt switch / PIR motion / obstacle avoidance / line tracking (digital, 0 or 65535; many read LOW when active), ultrasonic (trigger + echo, distance in mm; its echo pin is 5 V, use a divider), and DHT11 (needs the Adafruit "DHT sensor library", off until `USE_DHT11` is defined). Free digital pins: 16, 17, 21, 22 (and 4, 13, 14, 27, which stay reserved for a later JTAG loader). Not covered: joystick (two analog axes need two ADC1 pins, only three are free), IR receiver (needs a decoding library), camera, displays and motors. Three sensors are active by default (potentiometer, light, thermistor), so the CORDIC and relay builds work as soon as they are wired; the 4-lane tree needs a fourth line enabled in the table.

## Other ready-made bitstreams (built 9 Oct 2026, timing met at 27 MHz, NOT yet run on a board)
- `fpga/build/unit_relay_v1/unit_top.fs` -- relay chain: one word in, the same word out. Test: load, LED0 blinks, `id` passes, then in the web sketch's Live sensors card one sensor's word should come back unchanged.
- `fpga/build/unit_tree_direct_v1/unit_top.fs` -- the same tree, but it powers up in DIRECT mode (see below), so the sensor pins feed it with no ESP32 involved at all.
- `fpga/build/unit_tree_v1/unit_top.fs` -- reduction tree: four words in, their sum out (amounts add, locations add). Test: Live sensors with four sensors active; the result's top 16 bits are the sum of the four amounts.
Load either with `openFPGALoader -b tangnano20k <file>`. The bridge sketch's `cordic` command only fits the CORDIC bitstream; for these two use the web sketch, or `reg` / `words` by hand. Simulation results for both: `tests/vm/test_unit_live_feed_v1.py`.


## Direct mode: a sensor wired straight to the Tang (no ESP32 in the path)

Every current bitstream can feed the design from sensor pins on the Tang itself. Wire a **digital** sensor (PIR, tilt switch, a button) with its signal on **Tang pin 72 (input 1)** and/or **pin 71 (input 2)**, power it from 3V3 (or what the module needs, but its signal must not exceed 3.3 V), and GND to GND. The pins are pulled low inside the FPGA, so an unwired pin reads 0. (Pins 72 and 71 are the next two on the same header as the ESP32 link pins 73 to 77; the build accepts them, but they have not been checked on the board: if your header differs, change `SENS` in `tools/sd_unit_top_v1.py`.)

In direct mode the FPGA itself builds a word per input about once a millisecond (8192 when the sensor is active, 0 when not; location = the input number), feeds it to the design, and latches the newest result. No SPI, no playout RAM, no host. **LED5** (the sixth) lights when the result carries at least one active sensor, **LED4** (the fifth) at two or more.

Two ways in: on the page, the **Direct sensors** card has a switch (register 11) and reads the result out (registers 12 to 14), so the ESP32 only reads; or load `fpga/build/unit_tree_direct_v1/unit_top.fs`, which powers up in direct mode, and unplug the ESP32 completely, then touch the sensor: the LEDs follow. In direct mode the ESP-fed Run and live feed refuse to run (switch direct off first). The tree design is the useful one for this: one active sensor gives amount 8192, two give 16384. CORDIC is not meaningful in direct mode.
