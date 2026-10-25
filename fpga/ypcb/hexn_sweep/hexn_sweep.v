// hexn_sweep: clone of ../hexn_u2/hexn_u2.v (left untouched) whose core module is chosen at build time by the define CORE_MOD that prebuild.py writes (HEXN_VARIANT = base | A | B | AB). Everything else is as hexn_u2 (bridge on USER2).
// Hex-N on the YPCB-00338-1P1 (Kintex-7 XC7K480T): the detector bank, glue buffer, cells and the save/recall memory block (hexn_core_v2) behind a JTAG host link (hexn_jtag_bridge_v1, USER2: IR 0x03, so the DDR3 debug register of ypcb can keep USER1 in a joint design). The same command bytes as the Tang board's serial link, carried in 160-bit JTAG frames (see rtl/hexn_jtag_bridge_v1.v and tools/hexn_jtag_host_v1.py).
// Pins: SYS_CLK (50 MHz) and led[2:0] as designs/hello of the ypcb-00338-1p1 repo. led[0] = heartbeat (~1.5 Hz), led[1] = any core output bit high, led[2] = toggles with every byte the core sends.
// The RTL of the core, bank, cells and bridge is not in this folder: prebuild.py gathers it from the Imago-Unicell checkout (HEXN_REPO, default ~/Imago-Unicell) into the build directory as gen_00_hexn.v.
module hexn_sweep (input SYS_CLK, output [2:0] led);
    reg [31:0] count = 0; always @(posedge SYS_CLK) count <= count + 1;
    wire [7:0] rx_d, tx_d; wire rx_v, tx_s, tx_b; wire [5:0] cled;
    hexn_jtag_bridge_v1 #(.CHAIN(2), .FSPACING(128)) br (.clk(SYS_CLK), .rst(1'b0), .rx_d(rx_d), .rx_v(rx_v), .tx_d(tx_d), .tx_s(tx_s), .tx_b(tx_b));
    `CORE_MOD core (.clk(SYS_CLK), .rx_d(rx_d), .rx_v(rx_v), .tx_d(tx_d), .tx_s(tx_s), .tx_b(tx_b), .led(cled));
    reg txseen = 0; always @(posedge SYS_CLK) if (tx_s) txseen <= ~txseen;
    assign led = {txseen, |cled, count[25]};
endmodule
