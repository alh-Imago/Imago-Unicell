// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_bram_icm_hostbridge_v1.v — points.md #430's own queue item 2,
// first real slice: a self-contained top-level proving the real
// JTAG-to-BRAM and JTAG-to-ICM channels work on real silicon, driven
// directly by `host_bridge_bram_icm_v1.v` -- the FIRST real host-driven
// (not self-test-FSM-driven) hardware anywhere in this project's own
// history. Deliberately scoped to ONE shared BRAM and ONE super carrier
// cell (`unicell_super_v1.v`), per this project's own "smallest
// reproducible case first" discipline -- wiring a host bridge into the
// full 3-chain v2 sentinel+gather mechanism is separate, later,
// not-yet-scoped work.
//
// REAL, HONEST SCOPE: the driven cell's own data-path ports (data_in_*/
// arrived_*/ack_in_*) are tied inert (0/1 as appropriate) -- this build
// proves CONFIG loading and BRAM read/write over real JTAG, not a full
// data-flow round trip through the cell itself. That's real, separate,
// later work once these two raw channels are confirmed on silicon.
//
// CRITICAL — GENERATE THE REAL IP BEFORE BUILDING (same discipline as
// every other ISSP bridge in this project): IP Catalog -> In-System
// Sources and Probes, name the instance `issp_bram_icm` (matching this
// file's own instantiation below and `tb_stub_issp_bram_icm_v1.v`'s own
// simulation-only stand-in), Source width = 91, Probe width = 112,
// ENABLE "Source Clock" (wire to the real 25MHz fabric clock below),
// ENABLE the source synchronization registers. `issp_bram_icm.qsys` is
// deliberately NOT committed to git, per this project's own standing
// `docs/HARDWARE_SETUP.md`/`TOOLCHAIN_SETUP.md` convention -- regenerate
// locally before any real Quartus build.
`default_nettype none
`timescale 1ns / 1ps

module top_bram_icm_hostbridge_v1 (
    input  wire CLK_100M,
    output wire LED0_N,
    output wire LED1_N
);

// ── Clock/reset — same convention as every other project here ──────────
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

// ── Real ISSP bridge signals ────────────────────────────────────────
wire                bram_cmd_valid;
wire                bram_cmd_op;
wire [3:0]          bram_cmd_addr;
wire [39:0]         bram_cmd_wdata;
wire                bram_rdata_valid;
wire [39:0]         bram_rdata;
wire                bram_write_done;

wire                icm_cfg_valid;
wire [79:0]         icm_cfg_data;
wire [4:0]          icm_status_core_select;

host_bridge_bram_icm_v1 BRIDGE (
    .clk(clk), .rst(rst),
    .bram_cmd_valid(bram_cmd_valid), .bram_cmd_op(bram_cmd_op),
    .bram_cmd_addr(bram_cmd_addr), .bram_cmd_wdata(bram_cmd_wdata),
    .bram_rdata_valid(bram_rdata_valid), .bram_rdata(bram_rdata),
    .bram_write_done(bram_write_done),
    .icm_cfg_valid(icm_cfg_valid), .icm_cfg_data(icm_cfg_data),
    .icm_status_core_select(icm_status_core_select)
);

// ── The real shared BRAM, same ADDR_WIDTH/DATA_WIDTH convention as v2 ──
bram_controller_v1 #(.ADDR_WIDTH(4), .DATA_WIDTH(40)) BRAM (
    .clk(clk), .rst(rst),
    .cmd_valid(bram_cmd_valid), .cmd_op(bram_cmd_op),
    .cmd_addr(bram_cmd_addr), .cmd_wdata(bram_cmd_wdata),
    .rdata_valid(bram_rdata_valid), .rdata(bram_rdata), .write_done(bram_write_done)
);

// ── The one driven super carrier cell -- data-path ports tied inert,
// per this file's own stated scope (config + BRAM channels only). ──
unicell_super_v1 #(.CELL_ID(16'h0030)) CELL (
    .clk(clk), .rst(rst),
    .cfg_valid(icm_cfg_valid), .cfg_data(icm_cfg_data),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select(icm_status_core_select)
);

// ── Heartbeat + basic alive indication ──
reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;
assign LED0_N = ~hb_cnt[23];
assign LED1_N = 1'b1;   // reserved, no error condition tracked at this level

endmodule
