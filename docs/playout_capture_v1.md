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
