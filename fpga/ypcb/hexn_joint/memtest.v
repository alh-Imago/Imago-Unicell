// JOINT DESIGN (hexn_joint): everything the hexn_ram memtest.v does (DDR3 latency probe on the ypcb USER1 register), PLUS the Hex-N core and its JTAG bridge on USER2, inside the same module so the generated uberddr3 top level is used unchanged. The Hex-N RTL arrives from prebuild.py as gen_01_hexn.v. The Hex-N core runs on this module's clk (the DDR3 controller clock, 83.33 MHz) and has no other connection to the probe.
// Drop-in replacement for ypcb designs/uberddr3/memtest.v: SAME module name and ports, but it runs memlat.v (the latency probe)
// instead of the memory test, so the uberddr3 prebuild's top level, JTAG register layout and host plumbing are used unchanged.
// Control (the bits designs/uberddr3 passes as mode/len/seed):
//   mode 1 = single random reads, one at a time      mode 2 = pipelined random reads      mode 3 = pipelined sequential reads
//   len  = the number of reads is 2^len (len 0..15; larger values are clamped to 2^15)      seed = random address seed
// Results are put in the fields the old memory test used (the register words stay where they were):
//   errors         <- lat_min        first_err_addr <- lat_max         write_cycles <- total_cycles       read_cycles <- n_done
//   err_mask[31:0] <- lat_sum        err_mask[63:32] <- stall_sum      err_mask[71:64] <- read data fold (low byte)
// so register words 23, 24, 25, 26, 27 (low byte), 28 and 29 carry them.
module memtest #(
    parameter integer ADDR_BITS = 25,
    parameter integer DATA_BITS = 576
) (
    input wire clk,
    input wire ready,
    input wire start,
    input wire [1:0] mode,
    input wire [4:0] len,
    input wire [7:0] seed,
    output wire busy,
    output wire [31:0] errors,
    output wire [31:0] first_err_addr,
    output wire [DATA_BITS / 8 - 1:0] err_mask,
    output wire [31:0] write_cycles,
    output wire [31:0] read_cycles,
    output wire wb_stb,
    output wire wb_we,
    output wire [ADDR_BITS - 1:0] wb_addr,
    output wire [DATA_BITS - 1:0] wb_data,
    input wire wb_stall,
    input wire wb_ack,
    input wire [DATA_BITS - 1:0] wb_rdata
);
    wire [15:0] n_done;
    wire [31:0] lat_sum, stall_sum, rd_fold;
    wire [1:0] lmode = (mode == 2'd0) ? 2'd0 : mode - 2'd1;
    wire [15:0] count = (len > 5'd15) ? 16'h8000 : (16'd1 << len);
    memlat #(.ADDR_BITS(ADDR_BITS), .DATA_BITS(DATA_BITS)) lat (
        .clk(clk), .ready(ready), .start(start), .mode(lmode), .count(count), .seed(seed), .busy(busy), .n_done(n_done),
        .lat_min(errors), .lat_max(first_err_addr), .lat_sum(lat_sum), .stall_sum(stall_sum), .total_cycles(write_cycles),
        .rd_fold(rd_fold), .wb_stb(wb_stb), .wb_we(wb_we), .wb_addr(wb_addr), .wb_data(wb_data),
        .wb_stall(wb_stall), .wb_ack(wb_ack), .wb_rdata(wb_rdata));
    // ---- Hex-N on USER2 (the ypcb DDR3 debug register keeps USER1) ----
    wire [7:0] hx_rx_d, hx_tx_d; wire hx_rx_v, hx_tx_s, hx_tx_b; wire [5:0] hx_led;
    hexn_jtag_bridge_v1 #(.CHAIN(2), .FSPACING(128)) hx_br (.clk(clk), .rst(1'b0), .rx_d(hx_rx_d), .rx_v(hx_rx_v), .tx_d(hx_tx_d), .tx_s(hx_tx_s), .tx_b(hx_tx_b));
    hexn_core_v2 hx_core (.clk(clk), .rx_d(hx_rx_d), .rx_v(hx_rx_v), .tx_d(hx_tx_d), .tx_s(hx_tx_s), .tx_b(hx_tx_b), .led(hx_led));
    assign read_cycles = {16'd0, n_done};
    assign err_mask = {rd_fold[7:0], stall_sum, lat_sum};
endmodule
