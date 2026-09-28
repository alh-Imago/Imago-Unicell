// unicell_tang_nano_20k_smoke_v2.v -- points.md #896: v2 of the on-board smoke test, real-hardware-fixed.
//
// WHAT THIS PROVES: one real UniCell `sequencer_shell_v1c` core, genuinely configured and running on real
// Gowin silicon, its own internal 2-bit `seq_index` state machine visibly counting 0->1->2->3->0... on two
// LEDs at roughly 1 Hz. This is not the measurement harness from `#889` (that generator exists purely to
// close a cell into a synthesisable, pin-bound system for sizing/timing; its LEDs show an LFSR-driven "is
// this alive" signal, not a real, deliberate operation). This file is a SEPARATE, hand-designed, real
// working demonstration: a specific, deliberate config word is loaded (not random), and the core's own real
// downstream-offer/ack handshake (adder_cell_v4c and friends all share this shape) is genuinely exercised,
// gated by a real ~1 Hz tick so the advance is watchable, not a blur.
//
// v2 vs v1 (`#892`): `BTN_RST_N` removed entirely. Real, physical testing (`#894`/`#895`) proved the whole
// chain (config load, arming, handshake) genuinely works on real silicon once the reset button is taken out
// of the picture -- with it, v1 stayed permanently reset on the physical board despite passing simulation,
// a pull-up fix, and holding the button down. Root cause not yet confirmed; not required to ship a working
// demo tonight, so v2 uses a pure power-on reset instead. See `#896` for the honest, undiagnosed gap this
// leaves: WHY `BTN_RST_N` failed is still an open, real question.
//
// Per `#890`/`#891`: `sequencer` is one of the cheap types (80 LUT4 standalone, `#889`), chosen because
// this is a testbed/proof-of-concept deliverable, not an attempt at a capable accelerator.
//
// Pins: all verified against the real chip database in docs/man/tang-nano-20k.man.json (`#887`).
//   BOARD_CLK  = pin 4  (27 MHz crystal)
//   LED0_N     = pin 15 (heartbeat -- proves the design is genuinely clocking)
//   LED1_N     = pin 16 (seq_index bit 0)
//   LED2_N     = pin 17 (seq_index bit 1)
//   LED3_N     = pin 18 (advance-tick pulse stretched to be visible -- one blink per advance)
//
// TICK_DIV is a real parameter: the default (27_000_000) gives ~1 Hz on real 27 MHz hardware. The testbench
// overrides it to a small value so simulation finishes in a reasonable number of cycles while exercising the
// exact same RTL path.
`default_nettype none
`timescale 1ns / 1ps

module unicell_tang_nano_20k_smoke_v2 #(
    parameter integer TICK_DIV = 27_000_000   // cycles per advance at 27 MHz => ~1.0 Hz
) (
    input  wire BOARD_CLK,
    output wire LED0_N,
    output wire LED1_N,
    output wire LED2_N,
    output wire LED3_N
);

// points.md #895/#896: BTN_RST_N removed entirely. #894/#895's real-hardware diagnostics proved the whole
// sequencer/config/handshake chain works correctly on real silicon once BTN_RST_N is taken out of the reset
// path -- with it, the design stayed permanently reset on the physical board despite passing simulation, a
// pull-up fix (#893), and holding the button down. Root cause not yet confirmed; not required to ship a
// working demo. Pure power-on reset instead: no button, no external pin, nothing but the clock.
wire clk = BOARD_CLK;
reg [7:0] por_cnt = 8'h00;
wire rst = (por_cnt != 8'hFF);
always @(posedge clk) if (rst) por_cnt <= por_cnt + 8'd1;

// One-shot config-load pulse, same proven shape as #889's harness and project_assemble_v1.generate_top
// (#554): fires exactly once, a few cycles after reset.
reg [3:0] cfg_pulse_sr = 4'hF;
always @(posedge clk) if (!rst) cfg_pulse_sr <= {cfg_pulse_sr[2:0], 1'b0};
wire cfg_valid = !rst && cfg_pulse_sr[3] && !cfg_pulse_sr[2];

// Real, DELIBERATE (not random) config word -- sequencer_cell_v4c's own field map:
//   [7:0]=value_0 [15:8]=value_1 [23:16]=value_2 [31:24]=value_3
//   [33:32]=sequence_len_m1 (3 => cycle through all 4 values)
//   [39:34]=downstream_mask (bit0=north; only north routed, matching this file's own loopback wiring)
localparam [63:0] CFG_DATA = {24'h0, 6'b00_0001, 2'd3, 8'h04, 8'h03, 8'h02, 8'h01};

wire [31:0] dout_n;
wire fire_n;
wire ack_out_n;   // unused: this core never asserts ack_out (it doesn't consume upstream data)
wire [1:0] seq_index;

// Real advance tick: fires for exactly one cycle every TICK_DIV cycles.
reg [31:0] tick_cnt = 0;
wire tick = (tick_cnt == TICK_DIV - 1);
always @(posedge clk) tick_cnt <= tick ? 32'd0 : (tick_cnt + 32'd1);

// The real ack loopback: this is a closed, standalone cell (no real neighbour), so its own downstream
// offer is acknowledged by THIS SAME tick, not by another cell -- fire_n stays high (offer held) until the
// tick happens to catch it, giving a clean, watchable ~1 TICK_DIV-cycle advance rate.
wire ack_in_n = fire_n && tick;

sequencer_shell_v1c #(.CELL_ID(16'h0001)) SEQ (
    .clk(clk), .rst(rst),
    .active_in_n(1'b1), .active_in_s(1'b0), .active_in_e(1'b0), .active_in_w(1'b0),
    .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),
    .cfg_valid(cfg_valid), .cfg_data(CFG_DATA),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(fire_n), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(ack_in_n), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
    .status_seq_index(seq_index)
);

// Stretch the tick pulse so it's a visible blink, not a single 37ns flash.
reg [23:0] tick_stretch = 0;
always @(posedge clk) tick_stretch <= tick ? 24'hFFFFFF : (tick_stretch != 0 ? tick_stretch - 24'd1 : 24'd0);

reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;

assign LED0_N = ~hb_cnt[23];          // heartbeat: proves the design is genuinely clocking
assign LED1_N = ~seq_index[0];        // real sequencer state, bit 0
assign LED2_N = ~seq_index[1];        // real sequencer state, bit 1
assign LED3_N = ~(tick_stretch != 0); // one visible blink per real advance

endmodule
