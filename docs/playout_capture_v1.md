# playout_v1 / capture_v1 -- feeding and reading a design from block RAM (ledger #1036)

`fpga/verilog/playout_v1.v`: a RAM that plays preloaded words into a design's entry ports by itself. `capture_v1.v`: a RAM that takes the design's result words. Neither uses vendor IP: the memory is a plain synchronous-read array, so Quartus maps it to M10K/M20K, Gowin to BSRAM (yosys `synth_gowin` shows 2 BSRAM blocks for 1,024 x 32), and iverilog simulates it.

**Playout.** Host loads words through the write port (`wr_en/wr_addr/wr_data`), pulses `start` with `count` = items x LANES. Layout: address = item*LANES + lane. Each lane is a flex entry port (`lane_data`, `lane_valid` held until `lane_ack`). Lanes run independently; one RAM read per two cycles; `done` pulses when the last word has been taken. LANES, WIDTH, AW are parameters.

**Capture.** Flex exit ports in (`out_data/valid/ack`), round-robin between exits, one word per cycle, stored as {exit tag, data} in arrival order; `count` says how many; host reads through `rd_addr/rd_data` (valid one cycle later). When full it stops acking, so the design stalls and nothing is lost.

**Host side.** The only host-facing signals are the write port, `start/count/done` and the read port, so JTAG, a UART/USB-serial link (Tang Nano's BL616), or an SD card can fill and read them. The old Intel ISSP bridge (`fpga/host_bridge_bram_icm.tcl`) is not usable on Gowin.

**Measured.** Test `tests/vm/test_playout_v1.py`: playout alone gives every lane its own words in order under random consumer stalls; the 4-point Wasserstein-2 engine (#1034) fed only by playout and read only from capture gives the reference squared distances (cfg_valid pulse needed after reset, as for any flex design). Gowin synthesis (yosys, pre place-and-route): playout with 14 lanes ~ 370 LUT + ~570 FF + 2 BSRAM; capture, 1 exit ~ 75 LUT + 87 FF + 2 BSRAM. (ALU cells not counted.)

**Not done.** The host link (UART/SD/ESP) and a top-level that wires playout -> design -> capture on the Tang Nano.
