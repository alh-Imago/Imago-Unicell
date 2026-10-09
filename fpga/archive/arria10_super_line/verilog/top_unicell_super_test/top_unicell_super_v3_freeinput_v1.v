// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_unicell_super_v3_freeinput_v1.v — points.md #581: a real, single-
// variable isolation experiment, built specifically because #579/#580's
// own real N=1-vs-N=10 comparison conflated TWO real, different
// candidate causes and couldn't tell them apart:
//
//   (a) genuine cardinal connectivity -- real neighbor cells wired in,
//       instead of the self-test's own tied-off boundary constants.
//   (b) genuinely UNCONSTRAINED config input -- top_unicell_super_
//       test_v3.v's own FSM only ever presents core_select/core_config
//       as one of 8 real, compile-time-KNOWN literal words (each a
//       Verilog constant assigned at a specific FSM state). Quartus's
//       own synthesis-time optimizer can trace an FSM with literal
//       per-state outputs and specialize/prune logic around the exact,
//       finite, small set of values that will ever actually reach a
//       core -- something it structurally CANNOT do when core_select/
//       core_config are driven straight from real top-level primary
//       inputs (as project_assemble_v1.py's own array generator does),
//       since a primary input could genuinely be ANY value a real host
//       might load over JTAG.
//
// THIS FILE changes ONLY (b), holding (a) fixed at N=1/no-neighbors
// (identical boundary tie-off to top_unicell_super_test_v3.v) and
// addon_config still tied to a constant 0 (identical to every self-
// test so far, #579's own real finding) -- so any real ALM delta
// against the real N=1 self-test baseline (#574: 479 total / 301.9
// DUT ALM) is attributable to config-input freedom ALONE, not
// connectivity, not addons.
//
// ONE real unicell_super_v3 cell. core_select comes from a genuine,
// unconstrained CFG_SELECT[4:0] top-level input; core_config from a
// genuine, unconstrained CFG_CONFIG[41:0] top-level input (NOT the
// array generator's own cruder single-bit-repeated broadcast -- a
// full, independently-unconstrained 42-bit field, the most general
// real case Quartus could ever be asked to handle). addon_config
// stays a literal constant 0, matching every prior self-test exactly.
// One real, genuinely free ENTRY_DATA drives the N-side data path,
// matching the self-test's own real single active input convention.
// No FSM, no self-check (there's no fixed core to check against) --
// a real, non-prunable XOR-reduce anti-pruning guard instead, same
// convention the array generator itself already uses.
`default_nettype none
`timescale 1ns / 1ps

module top_unicell_super_v3_freeinput_v1 (
    input  wire        CLK_100M,
    input  wire        ENTRY_DATA,       // real, unconstrained -- N-side data/arrival
    input  wire [4:0]  CFG_SELECT,       // real, unconstrained -- core_select
    input  wire [41:0] CFG_CONFIG,       // real, unconstrained -- core_config
    output wire        LED0_N,
    output wire        LED1_N
);

reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

// Real, one-shot, broadcast config-load pulse -- fires exactly once,
// a few cycles after reset. Identical timing convention to the array
// generator's own cfg_valid_bcast (#554).
reg [3:0] cfg_pulse_sr = 4'hF;
always @(posedge clk) if (!rst) cfg_pulse_sr <= {cfg_pulse_sr[2:0], 1'b0};
wire cfg_valid = !rst && cfg_pulse_sr[3] && !cfg_pulse_sr[2];   // one real cycle

// addon_config: literal constant 0, matching top_unicell_super_test_
// v3.v's own real pack() function exactly -- addons stay disabled
// here, deliberately, so this experiment isolates config-input
// freedom ALONE, not addon exposure (#579 already covers that
// separately).
wire [79:0] cfg_data = {13'b0, 20'h0, CFG_CONFIG, CFG_SELECT};

wire [31:0] entry_data = {31'b0, ENTRY_DATA};

wire [31:0] data_out_n, data_out_s, data_out_e, data_out_w;
wire        fire_n, fire_s, fire_e, fire_w;
wire        ack_n, ack_s, ack_e, ack_w;
wire [4:0]  status_core_select;

unicell_super_v3 DUT (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(entry_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(ENTRY_DATA), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(data_out_n), .data_out_s(data_out_s), .data_out_e(data_out_e), .data_out_w(data_out_w),
    .fire_n(fire_n), .fire_s(fire_s), .fire_e(fire_e), .fire_w(fire_w),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(ack_n), .ack_out_s(ack_s), .ack_out_e(ack_e), .ack_out_w(ack_w),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select(status_core_select)
);

// Real, non-prunable anti-pruning guard -- same convention as
// project_assemble_v1.py's own array generator (#554): Quartus cannot
// prove this constant, since it structurally depends on ENTRY_DATA's
// own real fanout through the cell, so it cannot prune the cell away.
wire cell_alive = fire_n ^ fire_s ^ fire_e ^ fire_w ^
                  data_out_n[0] ^ data_out_s[0] ^ data_out_e[0] ^ data_out_w[0] ^
                  ack_n ^ ack_s ^ ack_e ^ ack_w;

reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;

assign LED0_N = ~hb_cnt[23];
assign LED1_N = ~cell_alive;

endmodule
