# Small unit bring-up guide: Tang Nano 20K + ESP32 (CORDIC unit)

Ledger #1036. Nothing here has run on real hardware yet, so the order below goes from "does the link talk at all" to "does the card work", and each step has a clear pass/fail.

## What you need
- Tang Nano 20K with the 16 GB SanDisk Ultra (SDHC) in its microSD slot, USB-C cable.
- The ESP32 dev board on the breadboard, USB cable, 5 jumper wires plus a ground wire (table in `docs/playout_capture_v1.md`):
  CS_N IO5 -> pin 73, SCLK IO18 -> 74, MOSI IO23 -> 75, MISO IO19 <- 76 (right-hand header), READY IO34 <- 77, GND to GND.
- A PC with: Arduino IDE 2, and a way to load the FPGA bitstream (step 1).

## Step 1 -- load the FPGA (no ESP32 needed yet)
The ready-made bitstream is `fpga/build/unit_cordic_v1/unit_top.fs` (CORDIC unit: 2,454 LUT4 = 12%, 4 of 46 block RAMs, 165 MHz capable, 27 MHz used).
Use whichever loader you already used for the smoke test:
- command line: `openFPGALoader -b tangnano20k fpga/build/unit_cordic_v1/unit_top.fs` (SRAM: lost when the board loses power; add `-f` to write it to flash);
- or the Gowin Programmer program: device GW2AR-18, "SRAM Program", file `unit_top.fs`.
LEDs (lit = true): **LED0 blinks slowly (about once a second) = the FPGA is loaded and running. If LED0 is not blinking the bitstream did not load.** LED1 = the ESP32 has pulled chip-select low at least once (stays lit until the next load). LED2 = the ESP32 has clocked SCLK at least once. LED3 = the SD card is up and error-free. LED4 (the fifth LED) = a 1 has arrived on MOSI while chip-select was low: it proves the MOSI wire. (LED1, LED2 and LED4 stay lit until the FPGA is reloaded; LED5 is unused.) So: after loading, LED0 should blink; after the first `id`, LED1 and LED2 should light; if they don't, the CS or SCLK wire isn't reaching the FPGA.

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
Registers, SPI protocol and the card layout are in `docs/playout_capture_v1.md` and `fpga/build/unit_cordic_v1/lanes.json`. A different design is wrapped the same way: `python3 tools/sd_unit_top_v1.py --icm <design.icm> --output <dir>` then `tools/gowin_sizing/build_unit_bitstream.sh <dir>`.

## WiFi remote control (ledger #1036 addendum 9)
`tools/esp32/unicell_unit_web/` is a second sketch (same wiring, same SPI layer in `unit_link.h`) that puts the unit on your WiFi. **It has been syntax-checked and its logic is covered by the simulation tests, but it has not yet been run on a real ESP32: treat the first run as a test.**

1. Choose the design that is loaded on the FPGA: near the top of `unicell_unit_web.ino` leave exactly one of `DESIGN_CORDIC` (default), `DESIGN_TREE4`, `DESIGN_RELAY` defined. This sets how many input words make one item and what the page says.
2. Upload it the same way as the serial sketch (Arduino IDE or `arduino-cli compile/upload`, board ESP32 Dev Module).
3. Serial Monitor (115200, Newline): the first boot prints a generated web password. Type `wifi <ssid> <password>`; it restarts, joins your WiFi and prints the address. Other commands: `ip` (address + password), `webpass <new, 8+ chars>`, `wificlear`, `id`, `reboot`.
4. Open `http://unicell.local/` (or the printed IP) in a browser on the same WiFi. Login: user `unicell`, the web password.
5. If WiFi cannot be joined, the ESP32 makes its own network **UniCell-Unit** (password = the web password); join it and open `http://192.168.4.1/`.

The page shows the unit status (ID, SD card, errors), a box to type input numbers (one item per line, or separated by anything that is not a digit), and a Run button that sends them over SPI, plays them through the design and shows the results. A second panel loads input from, or saves results to, raw SD blocks (blocks below 16 are refused).
Endpoints (for scripts): `GET /api/status`, `POST /api/run` (field `items`), `POST /api/sd` (`op`=load|save, `block`, `n`), `POST /api/sdinit`. Example: `curl -u unicell:PASSWORD -d "items=50000 -50000 0" http://unicell.local/api/run`.
**Limits, honestly:** plain HTTP with a password, for a trusted home or lab network only, never the internet; at most 512 words per run; one request at a time; it can overwrite raw SD blocks (16 and up).
