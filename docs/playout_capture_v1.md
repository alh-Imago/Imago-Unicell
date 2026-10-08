# playout_v1 / capture_v1 -- feeding and reading a design from block RAM (ledger #1036)

`fpga/verilog/playout_v1.v`: a RAM that plays preloaded words into a design's entry ports by itself. `capture_v1.v`: a RAM that takes the design's result words. Neither uses vendor IP: the memory is a plain synchronous-read array, so Quartus maps it to M10K/M20K, Gowin to BSRAM (yosys `synth_gowin` shows 2 BSRAM blocks for 1,024 x 32), and iverilog simulates it.

**Playout.** Host loads words through the write port (`wr_en/wr_addr/wr_data`), pulses `start` with `count` = items x LANES. Layout: address = item*LANES + lane. Each lane is a flex entry port (`lane_data`, `lane_valid` held until `lane_ack`). Lanes run independently; one RAM read per two cycles; `done` pulses when the last word has been taken. LANES, WIDTH, AW are parameters.

**Capture.** Flex exit ports in (`out_data/valid/ack`), round-robin between exits, one word per cycle, stored as {exit tag, data} in arrival order; `count` says how many; host reads through `rd_addr/rd_data` (valid one cycle later). When full it stops acking, so the design stalls and nothing is lost.

**Host side.** The only host-facing signals are the write port, `start/count/done` and the read port, so JTAG, a UART/USB-serial link (Tang Nano's BL616), or an SD card can fill and read them. The old Intel ISSP bridge (`fpga/host_bridge_bram_icm.tcl`) is not usable on Gowin.

**Measured.** Test `tests/vm/test_playout_v1.py`: playout alone gives every lane its own words in order under random consumer stalls; the 4-point Wasserstein-2 engine (#1034) fed only by playout and read only from capture gives the reference squared distances (cfg_valid pulse needed after reset, as for any flex design). Gowin synthesis (yosys, pre place-and-route): playout with 14 lanes ~ 370 LUT + ~570 FF + 2 BSRAM; capture, 1 exit ~ 75 LUT + 87 FF + 2 BSRAM. (ALU cells not counted.)

**Not done.** The host link (UART/SD/ESP) and a top-level that wires playout -> design -> capture on the Tang Nano.

## SD card (FPGA's own microSD slot) -- raw blocks, SPI mode (ledger #1036)
`fpga/verilog/sd_spi_v1.v`: an SD card in SPI mode, raw 512-byte blocks, no filesystem (bring-up CMD0/8/55+41/58, CMD17 read, CMD24 write; block- and byte-addressed cards). `sd_stream_v1.v`: moves runs of blocks between the card and the playout / capture RAMs (`cmd_load` / `cmd_save`, word w of block i at address i*128 + w, little-endian). `sd_card_model_v1.v`: a behavioural card for simulation only.
Pins (SPI use of the SDIO pins, from docs/man/tang-nano-20k.man.json): CLK=83, CMD(MOSI)=82, DAT0(MISO)=84, DAT3(CS)=81. The board file lists no pull-ups on them: check before relying on the slot.
Tests: `tests/vm/test_sd_spi_v1.py` -- bring-up + read + write for SDHC and byte-addressed cards; and the whole small unit card -> sd_stream -> playout -> 4-point W2 engine -> capture -> sd_stream -> card: the two squared distances read back from the card block equal the reference. Simulation only: nothing here has touched a real card or the board yet.
How to use: a PC writes the input words to the card as plain blocks (item-major, lane-minor, little-endian 32-bit words); the unit loads block 0.., plays it through, saves the results to a chosen block; the PC reads that block back.

## ESP32 side: the camera extension board (owner's photographs, 8 Oct 2026)
Terminal labels read from the photographs (the kit's pin-table images are still unread): left block I36 I39 I34 I35 IO32 IO33 IO25 IO26 IO27 IO14 IO12 IO13 GND 5V; right block IO23 IO22 TXD RXD IO21 IO19 IO18 IO5 IO4 IO0 IO2 IO15 GND 3V3. IO1/IO3 are TXD/RXD (the USB serial); IO6-IO11 are the module's flash and not brought out.
Proposed SPI link, ESP32 master, FPGA slave: SCLK IO18, MOSI IO23, MISO IO19, CS_N IO5, READY IO34 (the ESP32's default VSPI pins, so full-speed hardware SPI). The FPGA drives only MISO and READY, neither a strapping pin (IO5 is a strapping pin but the ESP32 drives it). On the FPGA side the edge connector pins 73-77 from the board file. Not wired. Unverified: whether a fitted camera, or anything else on the board, also uses IO18/19/23/5/34 (expected free with no camera fitted) -- check with a continuity test. The ESP32's own SD slot (IO14/15/2/4/12/13) is left alone.

## The SPI bridge and the whole unit (ledger #1036)
`spi_bridge_v1.v` is an SPI slave (mode 0, MSB first, everything in the system clock domain): SCLK must be slower than clk/16 (27 MHz -> at most ~1.6 MHz; 1 MHz or less on a breadboard). `sd_unit_v1.v` ties it to `sd_stream_v1`, `playout_v1` and `capture_v1` around any flex design. `tools/sd_unit_top_v1.py --icm design.icm --output dir` wraps any flex design and writes `unit_top.v`, `unit_top.cst`, `lanes.json` (which entry is which lane), `FILES.txt`, `README_UNIT.md`.

SPI transaction (CS low ... CS high, big-endian): `0x01 WR_REG addr d3..d0` | `0x02 RD_REG addr pad` then four more clocks return d3..d0 | `0x03 WR_WORDS hi lo` then 4-byte words (auto-increment) into the playout RAM | `0x04 RD_WORDS hi lo pad` then 4-byte words out of the capture RAM.
Registers: 0 ID (0x57320001) | 1 STATUS [0] sd_ready [1] sd_error [2] sd_busy [3] play_busy [4] sd_done (sticky) [5] play_done (sticky) [6] capture non-empty [12:8] sd err_code | 2 CONTROL (write): [0] sd_load [1] sd_save [2] play_start [3] capture_clear [4] clear the done bits | 3 START_BLOCK | 4 NBLOCKS | 5 PLAY_COUNT (items x lanes) | 6 CAP_COUNT | 7 SCRATCH | 8 MAX_OUT (pacing: at most this many results outstanding, 0 = unlimited) | 9 RPI (results per item, default 1).
Typical run: read ID -> wait STATUS bit0 -> START_BLOCK=16, NBLOCKS=n, CONTROL=1 -> wait bit4 -> PLAY_COUNT=items*lanes, CONTROL=4 -> poll CAP_COUNT -> RD_WORDS 0 ... (and/or CONTROL=0x10, START_BLOCK=17, CONTROL=2 to save the results to the card).

**The card (16 GB SanDisk Ultra, Class 10 = SDHC, block-addressed).** Raw blocks overwrite whatever is there: a FAT32 card keeps its partition table in block 0, so use blocks well away from it (the tests and README use 16 for input and 17 for results; such cards normally start their partition much later, but check yours). A standard-capacity (byte-addressed, SD 1.x) card is also handled (CMD8 "illegal command", no HCS, CMD16 = 512) and tested against a simulated one.

**Breadboard wiring (ESP32 camera-board terminals <-> Tang Nano edge connector; proposed, not wired, check with a continuity test).** 3.3 V logic both sides, each board on its own USB power:
| signal | ESP32 terminal | Tang Nano package pin | direction |
|---|---|---|---|
| SCLK | IO18 | 74 | ESP32 -> FPGA |
| MOSI | IO23 | 75 | ESP32 -> FPGA |
| MISO | IO19 | 76 | FPGA -> ESP32 |
| CS_N | IO5 | 73 | ESP32 -> FPGA |
| READY | IO34 | 77 | FPGA -> ESP32 |
| GND | GND | any GND | shared |
The Tang Nano's package pin numbers are not its labelled header holes: read the hole for pins 73-77 off the board's own pinout sheet. Start with SCLK at 1 MHz or less.

**Measured (simulation, ledger #1036).** `tests/vm/test_spi_bridge_v1.py`: registers (ID, scratch), words written to the playout RAM over SPI and results read back over SPI, the SD load/play/save sequence over SPI, and the 4-point Wasserstein-2 engine driven only by a simulated ESP32 (results equal the reference over SPI and on the card, ~5.5 min). `tests/vm/test_sd_unit_top_v1.py`: the generated top for a small adder design -- the generated unit_top.v in simulation with a simulated card and ESP32, the pin file, and Gowin synthesis. Size (yosys, pre place-and-route): the whole unit around a 2-lane adder design = about 1,900 LUT4 + 330 ALU + 1,030 FF + 4 BSRAM, about 9% of a Nano 20K.

**HONEST LIMIT -- the W2 engine does not fit the Nano 20K.** Using the board file's per-cell costs, the 4-point W2 engine (5,440 cells, 4,660 of them ram relays and 614 crosses) needs roughly 300k LUT4 and 190k FF (about 200k LUT4 even with the multipliers in DSP blocks, and 78 multipliers against 48 DSP multipliers) against 20,736 LUT4 / 15,552 FF; even the 2-point engine (1,845 cells) is about 100k LUT4. It was validated in the VM and in simulated RTL, and it is the right workload for a bigger part (the Arria 10 tile plan), but the Nano needs a much smaller design for a real board run. Nothing here has run on hardware.

## First design for the Nano: the CORDIC example (ledger #1036)
`nano/examples/cordic_z_convergence.icm-hier.json` (36 cells, one entry `z_input`, one exit `z_output`; z0 = 50000 -> -404) wrapped by `tools/sd_unit_top_v1.py`: about 2,200 LUT4 + 670 ALU + 1,800 FF + 4 BSRAM with the whole unit, roughly 11% of a Nano 20K. It holds ONE item at a time (checked in RTL: with overlapping items and random stalls two results swap, -821 / 821), so the unit paces it: before the run CONTROL=8 (clear capture), MAX_OUT=1, RPI=1; then the next angle is issued only after the previous result is captured (`tests/vm/test_playout_v1.py::test_pacing_keeps_the_items_in_flight_at_the_limit` proves the gate on a stand-in design; `tests/vm/test_sd_unit_top_v1.py::test_the_cordic_example_...` runs the CORDIC through the generated top from a simulated card, results over SPI equal FlexGrid's). Not on a board yet.
