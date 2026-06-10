// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// top_kintex7_zones.v — Kintex-7 2×8 zone grid
// Protocol v2.3
//
// 16 zones × 28 cells = 448 cells total
// 597,200 LUTs available, 575,232 used (96.3%)
//
// Grid layout:
//   [Z00]─[Z01]─[Z02]─[Z03]─[Z04]─[Z05]─[Z06]─[Z07]  ← row 0
//     |     |     |     |     |     |     |     |
//   [Z08]─[Z09]─[Z10]─[Z11]─[Z12]─[Z13]─[Z14]─[Z15]  ← row 1
//
// Bridge connections (2 per active direction):
//   Row 0 zones: east + west + south (no north)
//   Row 1 zones: east + west + north (no south)
//   Leftmost (Z00,Z08): no west
//   Rightmost (Z07,Z15): no east
//   Corner zones: 2 directions = 4 bridges
//   Edge zones:   3 directions = 6 bridges
//
// Each zone is a Pblock — CONTAIN_ROUTING true.
// Bridge signals registered — 1 tick latency per crossing.
// Timing: 125MHz throughout, each zone independently verified.

`default_nettype none
`timescale 1ns / 1ps

module top (
    input  wire        clk,
    input  wire        rst,

    // Command bus (from AXI bridge / XDMA)
    input  wire [31:0] cmd_bus,
    input  wire [31:0] cmd_data,
    input  wire        cmd_valid,
    input  wire [15:0] cpu_addr,
    input  wire [31:0] cpu_data,
    input  wire        cpu_valid,

    // Fired output (collected from all zones, priority mux)
    output wire [15:0] out_addr,
    output wire [31:0] out_data,
    output wire        out_valid,

    output wire [15:0] armed_count,
    output wire [31:0] cycle_count,

    output wire [2:0]  led
);

localparam NZ = 16;
localparam NB = 2;   // bridges per direction

// ── Per-zone outputs ──────────────────────────────────────────────────────
wire [15:0] zo_addr  [0:NZ-1];
wire [31:0] zo_data  [0:NZ-1];
wire        zo_valid [0:NZ-1];
wire [15:0] zo_armed [0:NZ-1];
wire [31:0] zo_cycle [0:NZ-1];

// ── Bridge wires (horizontal E/W between zones in same row) ───────────────
// Naming: bh_ew[col][bridge] = east output of col → west input of col+1
wire [NB-1:0]    bh_ev [0:6];   // east-valid  col 0-6 (row 0)
wire [NB*16-1:0] bh_ea [0:6];   // east-addr
wire [NB*32-1:0] bh_ed [0:6];   // east-data

wire [NB-1:0]    bh_wv [0:6];   // west-valid  col 1-7 back to col 0-6
wire [NB*16-1:0] bh_wa [0:6];
wire [NB*32-1:0] bh_wd [0:6];

wire [NB-1:0]    bh_ev1 [0:6];  // row 1 horizontal
wire [NB*16-1:0] bh_ea1 [0:6];
wire [NB*32-1:0] bh_ed1 [0:6];

wire [NB-1:0]    bh_wv1 [0:6];
wire [NB*16-1:0] bh_wa1 [0:6];
wire [NB*32-1:0] bh_wd1 [0:6];

// ── Bridge wires (vertical N/S between rows) ──────────────────────────────
wire [NB-1:0]    bv_sv [0:7];   // south output of row 0 → north input of row 1
wire [NB*16-1:0] bv_sa [0:7];
wire [NB*32-1:0] bv_sd [0:7];

wire [NB-1:0]    bv_nv [0:7];   // north output of row 1 → south input of row 0
wire [NB*16-1:0] bv_na [0:7];
wire [NB*32-1:0] bv_nd [0:7];

// Tie-off for unused bridge directions
wire [NB-1:0]    tie_v = {NB{1'b0}};
wire [NB*16-1:0] tie_a = {NB*16{1'b0}};
wire [NB*32-1:0] tie_d = {NB*32{1'b0}};

// ── Zone instantiation macro (via generate) ───────────────────────────────
// Row 0: Z00-Z07  (col 0-7, no north)
// Row 1: Z08-Z15  (col 0-7, no south)

genvar c;
generate

// ── Row 0 ─────────────────────────────────────────────────────────────────
for (c = 0; c < 8; c = c + 1) begin : row0
    unicell_zone #(.NUM_CELLS(28), .NUM_BRIDGES(NB), .ZONE_ID(c)) z (
        .clk (clk), .rst (rst),
        .cmd_bus (cmd_bus), .cmd_data (cmd_data), .cmd_valid (cmd_valid),
        .cpu_addr (cpu_addr), .cpu_data (cpu_data), .cpu_valid (cpu_valid),
        .out_addr (zo_addr[c]), .out_data (zo_data[c]), .out_valid (zo_valid[c]),
        .armed_count (zo_armed[c]), .cycle_count (zo_cycle[c]),
        // North — unused (row 0 top)
        .bridge_n_in_valid (tie_v), .bridge_n_in_addr (tie_a), .bridge_n_in_data (tie_d),
        .bridge_n_out_valid (), .bridge_n_out_addr (), .bridge_n_out_data (),
        // South → row 1 north
        .bridge_s_in_valid  (bv_nv[c]), .bridge_s_in_addr  (bv_na[c]), .bridge_s_in_data  (bv_nd[c]),
        .bridge_s_out_valid (bv_sv[c]), .bridge_s_out_addr (bv_sa[c]), .bridge_s_out_data (bv_sd[c]),
        // East (col 0-6 only; col 7 ties off)
        .bridge_e_in_valid  (c<7 ? bh_wv[c]  : tie_v),
        .bridge_e_in_addr   (c<7 ? bh_wa[c]  : tie_a),
        .bridge_e_in_data   (c<7 ? bh_wd[c]  : tie_d),
        .bridge_e_out_valid (c<7 ? bh_ev[c]  : /* open */),
        .bridge_e_out_addr  (c<7 ? bh_ea[c]  : /* open */),
        .bridge_e_out_data  (c<7 ? bh_ed[c]  : /* open */),
        // West (col 1-7 only; col 0 ties off)
        .bridge_w_in_valid  (c>0 ? bh_ev[c-1] : tie_v),
        .bridge_w_in_addr   (c>0 ? bh_ea[c-1] : tie_a),
        .bridge_w_in_data   (c>0 ? bh_ed[c-1] : tie_d),
        .bridge_w_out_valid (c>0 ? bh_wv[c-1] : /* open */),
        .bridge_w_out_addr  (c>0 ? bh_wa[c-1] : /* open */),
        .bridge_w_out_data  (c>0 ? bh_wd[c-1] : /* open */)
    );
end

// ── Row 1 ─────────────────────────────────────────────────────────────────
for (c = 0; c < 8; c = c + 1) begin : row1
    unicell_zone #(.NUM_CELLS(28), .NUM_BRIDGES(NB), .ZONE_ID(c+8)) z (
        .clk (clk), .rst (rst),
        .cmd_bus (cmd_bus), .cmd_data (cmd_data), .cmd_valid (cmd_valid),
        .cpu_addr (cpu_addr), .cpu_data (cpu_data), .cpu_valid (cpu_valid),
        .out_addr (zo_addr[c+8]), .out_data (zo_data[c+8]), .out_valid (zo_valid[c+8]),
        .armed_count (zo_armed[c+8]), .cycle_count (zo_cycle[c+8]),
        // North ← row 0 south
        .bridge_n_in_valid  (bv_sv[c]), .bridge_n_in_addr  (bv_sa[c]), .bridge_n_in_data  (bv_sd[c]),
        .bridge_n_out_valid (bv_nv[c]), .bridge_n_out_addr (bv_na[c]), .bridge_n_out_data (bv_nd[c]),
        // South — unused (row 1 bottom)
        .bridge_s_in_valid (tie_v), .bridge_s_in_addr (tie_a), .bridge_s_in_data (tie_d),
        .bridge_s_out_valid (), .bridge_s_out_addr (), .bridge_s_out_data (),
        // East
        .bridge_e_in_valid  (c<7 ? bh_wv1[c]  : tie_v),
        .bridge_e_in_addr   (c<7 ? bh_wa1[c]  : tie_a),
        .bridge_e_in_data   (c<7 ? bh_wd1[c]  : tie_d),
        .bridge_e_out_valid (c<7 ? bh_ev1[c]  : /* open */),
        .bridge_e_out_addr  (c<7 ? bh_ea1[c]  : /* open */),
        .bridge_e_out_data  (c<7 ? bh_ed1[c]  : /* open */),
        // West
        .bridge_w_in_valid  (c>0 ? bh_ev1[c-1] : tie_v),
        .bridge_w_in_addr   (c>0 ? bh_ea1[c-1] : tie_a),
        .bridge_w_in_data   (c>0 ? bh_ed1[c-1] : tie_d),
        .bridge_w_out_valid (c>0 ? bh_wv1[c-1] : /* open */),
        .bridge_w_out_addr  (c>0 ? bh_wa1[c-1] : /* open */),
        .bridge_w_out_data  (c>0 ? bh_wd1[c-1] : /* open */)
    );
end

endgenerate

// ── Output collection — priority mux across all 16 zones ─────────────────
// First valid zone wins each cycle. Zones fire rarely relative to clock rate
// so contention is low. Upgrade to round-robin if needed.
wire any_valid = |{zo_valid[15],zo_valid[14],zo_valid[13],zo_valid[12],
                   zo_valid[11],zo_valid[10],zo_valid[9], zo_valid[8],
                   zo_valid[7], zo_valid[6], zo_valid[5], zo_valid[4],
                   zo_valid[3], zo_valid[2], zo_valid[1], zo_valid[0]};

reg [3:0] win_zone = 4'h0;
integer z;
always @(*) begin
    win_zone = 4'h0;
    for (z = 15; z >= 0; z = z - 1)
        if (zo_valid[z]) win_zone = z[3:0];
end

assign out_valid = any_valid;
assign out_addr  = zo_addr[win_zone];
assign out_data  = zo_data[win_zone];

// Sum armed counts across all zones
assign armed_count = zo_armed[0]  + zo_armed[1]  + zo_armed[2]  + zo_armed[3]  +
                     zo_armed[4]  + zo_armed[5]  + zo_armed[6]  + zo_armed[7]  +
                     zo_armed[8]  + zo_armed[9]  + zo_armed[10] + zo_armed[11] +
                     zo_armed[12] + zo_armed[13] + zo_armed[14] + zo_armed[15];
assign cycle_count = zo_cycle[0]; // all zones share clock, count from zone 0

// LEDs
assign led[0] = any_valid;
assign led[1] = armed_count[0];
assign led[2] = ~rst;

endmodule
