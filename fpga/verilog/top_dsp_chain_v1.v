// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_dsp_chain_v1.v — points.md #466/#467's own queue: the FIRST real
// DSP hardware bring-up build. Real host bridge (`host_bridge_dsp_v1.v`)
// driving one real DSP ADD wrapper (`dsp_arith_wrapper_v1.v`, OP="ADD"
// -- the first, most-proven mode this session) directly, per this
// project's own "smallest reproducible case first" discipline -- no
// RAM-cell fabric staging yet, that's real, separate, later
// integration work once the DSP hard IP itself is confirmed working on
// real silicon.
//
// CRITICAL — GENERATE THE REAL IP BEFORE BUILDING (same discipline as
// every other ISSP bridge in this project): IP Catalog -> In-System
// Sources and Probes, name the instance `issp_dsp` (matching this
// file's own instantiation and `tb_stub_issp_dsp_v1.v`'s own
// simulation-only stand-in), Source width = 37, Probe width = 114,
// ENABLE "Source Clock" (wire to the real 25MHz fabric clock below),
// ENABLE the source synchronization registers. `issp_dsp.qsys` is
// deliberately NOT committed to git, per this project's own standing
// `docs/HARDWARE_SETUP.md`/`TOOLCHAIN_SETUP.md` convention.
//
// ALSO CRITICAL — generate the real `alterafpf_add_single` megafunction
// via IP Catalog (Floating-Point IP Cores, real confirmed name per
// #462) before building. Its exact real port names were NOT
// independently confirmed (#462's own stated gap) -- this file assumes
// the standard Altera convention (`dataa`/`datab`/`clock`/`result`);
// if the real generated IP differs, `dsp_arith_wrapper_v1.v`'s own
// instantiation is the one place that needs adjusting.
`default_nettype none
`timescale 1ns / 1ps

module top_dsp_chain_v1 (
    input  wire CLK_100M,
    output wire LED0_N,
    output wire LED1_N
);

// ── Clock/reset — same convention as every other project here ──────
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

// ── Real bridge <-> real DSP wrapper signals ────────────────────────
wire [31:0] dsp_data_in_a, dsp_data_in_b, dsp_data_out;
wire        dsp_arrived_a, dsp_arrived_b;
wire        dsp_ack_out_a, dsp_ack_out_b;
wire        dsp_fire, dsp_ack_in;
wire        dsp_wd_cfg_valid;
wire [15:0] dsp_wd_cfg_threshold;
wire        dsp_wd_timeout_err;
wire [15:0] dsp_wd_count_out;

host_bridge_dsp_v1 BRIDGE (
    .clk(clk), .rst(rst),
    .dsp_data_in_a(dsp_data_in_a), .dsp_arrived_a(dsp_arrived_a), .dsp_ack_out_a(dsp_ack_out_a),
    .dsp_data_in_b(dsp_data_in_b), .dsp_arrived_b(dsp_arrived_b), .dsp_ack_out_b(dsp_ack_out_b),
    .dsp_data_out(dsp_data_out), .dsp_fire(dsp_fire), .dsp_ack_in(dsp_ack_in),
    .dsp_wd_cfg_valid(dsp_wd_cfg_valid), .dsp_wd_cfg_threshold(dsp_wd_cfg_threshold),
    .dsp_wd_timeout_err(dsp_wd_timeout_err), .dsp_wd_count_out(dsp_wd_count_out)
);

dsp_arith_wrapper_v1 #(.OP("ADD")) DSP_ADD (
    .clk(clk), .rst(rst),
    .data_in_a(dsp_data_in_a), .arrived_a(dsp_arrived_a), .ack_out_a(dsp_ack_out_a),
    .data_in_b(dsp_data_in_b), .arrived_b(dsp_arrived_b), .ack_out_b(dsp_ack_out_b),
    .data_out(dsp_data_out), .fire(dsp_fire), .ready_in(1'b1), .ack_in(dsp_ack_in),
    .wd_cfg_valid(dsp_wd_cfg_valid), .wd_cfg_threshold(dsp_wd_cfg_threshold),
    .wd_timeout_err(dsp_wd_timeout_err), .wd_count_out(dsp_wd_count_out)
);

// ── Heartbeat + basic alive indication ──
reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;
assign LED0_N = ~hb_cnt[23];
assign LED1_N = ~dsp_wd_timeout_err;

endmodule
