// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_moat_tile_v1.v — points.md #588: real, hand-built first test of
// Alan's own "moat" idea -- surround each real super-cell with real,
// small buffer cells (not just N/S/E/W, the corners too), each with
// its own LogicLock region, to see whether this fences the super-
// cell's own internal logic in and stops the real, repeated cross-
// die scattering seen in every prior real Chip Planner screenshot in
// this thread (#579-#585). Pattern A (Alan's own preferred first
// test) -- a constant, non-shared moat: this file has exactly ONE
// real super-cell, so the "do neighboring super-cells SHARE moat
// cells" question (pattern B, Alan's own "may prove a new type of
// beast altogether") doesn't arise yet -- that's a real, later,
// larger tiled test, not this one.
//
// THE REAL LAYOUT (row-major, matching project_assemble_v1.py's own
// real neighbor-wiring convention exactly -- dout_DIR of a cell feeds
// data_in_OPPOSITE(DIR) of its real neighbor in that direction):
//
//     NW ── N ── NE
//      │    │    │
//      W ── CTR ─ E
//      │    │    │
//     SW ── S ── SE
//
// CTR = unicell_super_v3 (#574's own real, proven, cheapest shell).
// N/S/E/W/NE/NW/SE/SW = ram_cell_v1 (the simplest real core already
// used as "moat" material elsewhere in this project).
//
// THE REAL POINT, confirmed against real port lists before wiring
// anything: there is no diagonal port anywhere in this project's own
// real RTL (only N/S/E/W exist on every core and shell). CTR
// therefore CANNOT reach NE/NW/SE/SW directly, by construction, not
// by omission here -- exactly Alan's own real confirmation. The
// corner cells CAN real form a ring AROUND the center, connected only
// to their own two adjacent EDGE moat cells (e.g. NE's own south port
// reaches E, NE's own west port reaches N) -- a real, genuine 2D
// analogue of a 3D via-layer bypass, using nothing but the existing
// cardinal ports.
//
// Real config convention: CTR and all 8 real moat cells share the
// SAME real cfg_valid_bcast/cfg_data_bcast construction the existing
// homogeneous array generator already uses (project_assemble_v1.py's
// own real `{13'b0, {20{ENTRY_DATA}}, {42{ENTRY_DATA}}, CFG_SELECT}`)
// -- deliberately, so this real ALM/Fmax number stays directly
// comparable to `#579`/`#580`'s own real N=10 array data (same real
// addon exposure, same genuinely-unconstrained config input, not the
// N=1 self-test's own cheaper, compile-time-known literal config).
`default_nettype none
`timescale 1ns / 1ps

module top_moat_tile_v1 (
    input  wire        CLK_100M,
    input  wire        ENTRY_DATA,     // real, unconstrained
    input  wire [4:0]  CFG_SELECT,     // real, unconstrained -- CTR's core_select
    output wire        LED0_N,
    output wire        LED1_N
);

reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

reg [3:0] cfg_pulse_sr = 4'hF;
always @(posedge clk) if (!rst) cfg_pulse_sr <= {cfg_pulse_sr[2:0], 1'b0};
wire cfg_valid_bcast = !rst && cfg_pulse_sr[3] && !cfg_pulse_sr[2];

// Real, matching project_assemble_v1.py's own exact construction --
// see this file's own header for why.
wire [79:0] cfg_data_bcast = {13'b0, {20{ENTRY_DATA}}, {42{ENTRY_DATA}}, CFG_SELECT};
wire [31:0] entry_data = {31'b0, ENTRY_DATA};

// ── Per-cell output wires, one set per real position ──
`define MOAT_WIRES(nm) \
    wire [31:0] nm``_dout_n, nm``_dout_s, nm``_dout_e, nm``_dout_w; \
    wire nm``_fire_n, nm``_fire_s, nm``_fire_e, nm``_fire_w; \
    wire nm``_ack_n, nm``_ack_s, nm``_ack_e, nm``_ack_w;

`MOAT_WIRES(CTR)
`MOAT_WIRES(N)
`MOAT_WIRES(S)
`MOAT_WIRES(E)
`MOAT_WIRES(W)
`MOAT_WIRES(NE)
`MOAT_WIRES(NW)
`MOAT_WIRES(SE)
`MOAT_WIRES(SW)

wire [4:0] status_core_select;

// ── CTR: the one real super-cell ──
unicell_super_v3 #(.CELL_ID(16'h1000)) CTR (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid_bcast), .cfg_data(cfg_data_bcast),
    .data_in_n(N_dout_s), .data_in_s(S_dout_n), .data_in_e(E_dout_w), .data_in_w(W_dout_e),
    .arrived_n(N_fire_s), .arrived_s(S_fire_n), .arrived_e(E_fire_w), .arrived_w(W_fire_e),
    .data_out_n(CTR_dout_n), .data_out_s(CTR_dout_s), .data_out_e(CTR_dout_e), .data_out_w(CTR_dout_w),
    .fire_n(CTR_fire_n), .fire_s(CTR_fire_s), .fire_e(CTR_fire_e), .fire_w(CTR_fire_w),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(CTR_ack_n), .ack_out_s(CTR_ack_s), .ack_out_e(CTR_ack_e), .ack_out_w(CTR_ack_w),
    .ack_in_n(N_ack_s), .ack_in_s(S_ack_n), .ack_in_e(E_ack_w), .ack_in_w(W_ack_e),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select(status_core_select)
);

// ── N: edge moat, real link to CTR (south) + NE/NW (east/west) ──
ram_cell_v1 #(.CELL_ID(16'h1001)) N (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid_bcast), .cfg_data({22'b0, cfg_data_bcast[46:5]}),
    .data_in_n(entry_data), .data_in_s(CTR_dout_n), .data_in_e(NE_dout_w), .data_in_w(NW_dout_e),
    .arrived_n(ENTRY_DATA), .arrived_s(CTR_fire_n), .arrived_e(NE_fire_w), .arrived_w(NW_fire_e),
    .data_out_n(N_dout_n), .data_out_s(N_dout_s), .data_out_e(N_dout_e), .data_out_w(N_dout_w),
    .fire_n(N_fire_n), .fire_s(N_fire_s), .fire_e(N_fire_e), .fire_w(N_fire_w),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(N_ack_n), .ack_out_s(N_ack_s), .ack_out_e(N_ack_e), .ack_out_w(N_ack_w),
    .ack_in_n(1'b0), .ack_in_s(CTR_ack_n), .ack_in_e(NE_ack_w), .ack_in_w(NW_ack_e),
    .freeze_in(1'b0), .status_data_valid()
);

// ── S: edge moat, real link to CTR (north) + SE/SW (east/west) ──
ram_cell_v1 #(.CELL_ID(16'h1002)) S (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid_bcast), .cfg_data({22'b0, cfg_data_bcast[46:5]}),
    .data_in_n(CTR_dout_s), .data_in_s(32'h0), .data_in_e(SE_dout_w), .data_in_w(SW_dout_e),
    .arrived_n(CTR_fire_s), .arrived_s(1'b0), .arrived_e(SE_fire_w), .arrived_w(SW_fire_e),
    .data_out_n(S_dout_n), .data_out_s(S_dout_s), .data_out_e(S_dout_e), .data_out_w(S_dout_w),
    .fire_n(S_fire_n), .fire_s(S_fire_s), .fire_e(S_fire_e), .fire_w(S_fire_w),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(S_ack_n), .ack_out_s(S_ack_s), .ack_out_e(S_ack_e), .ack_out_w(S_ack_w),
    .ack_in_n(CTR_ack_s), .ack_in_s(1'b0), .ack_in_e(SE_ack_w), .ack_in_w(SW_ack_e),
    .freeze_in(1'b0), .status_data_valid()
);

// ── E: edge moat, real link to CTR (west) + NE/SE (north/south) ──
ram_cell_v1 #(.CELL_ID(16'h1003)) E (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid_bcast), .cfg_data({22'b0, cfg_data_bcast[46:5]}),
    .data_in_n(NE_dout_s), .data_in_s(SE_dout_n), .data_in_e(32'h0), .data_in_w(CTR_dout_e),
    .arrived_n(NE_fire_s), .arrived_s(SE_fire_n), .arrived_e(1'b0), .arrived_w(CTR_fire_e),
    .data_out_n(E_dout_n), .data_out_s(E_dout_s), .data_out_e(E_dout_e), .data_out_w(E_dout_w),
    .fire_n(E_fire_n), .fire_s(E_fire_s), .fire_e(E_fire_e), .fire_w(E_fire_w),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(E_ack_n), .ack_out_s(E_ack_s), .ack_out_e(E_ack_e), .ack_out_w(E_ack_w),
    .ack_in_n(NE_ack_s), .ack_in_s(SE_ack_n), .ack_in_e(1'b0), .ack_in_w(CTR_ack_e),
    .freeze_in(1'b0), .status_data_valid()
);

// ── W: edge moat, real link to CTR (east) + NW/SW (north/south) ──
ram_cell_v1 #(.CELL_ID(16'h1004)) W (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid_bcast), .cfg_data({22'b0, cfg_data_bcast[46:5]}),
    .data_in_n(NW_dout_s), .data_in_s(SW_dout_n), .data_in_e(CTR_dout_w), .data_in_w(32'h0),
    .arrived_n(NW_fire_s), .arrived_s(SW_fire_n), .arrived_e(CTR_fire_w), .arrived_w(1'b0),
    .data_out_n(W_dout_n), .data_out_s(W_dout_s), .data_out_e(W_dout_e), .data_out_w(W_dout_w),
    .fire_n(W_fire_n), .fire_s(W_fire_s), .fire_e(W_fire_e), .fire_w(W_fire_w),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(W_ack_n), .ack_out_s(W_ack_s), .ack_out_e(W_ack_e), .ack_out_w(W_ack_w),
    .ack_in_n(NW_ack_s), .ack_in_s(SW_ack_n), .ack_in_e(CTR_ack_w), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

// ── NE: corner moat, real ring link to N (west) + E (south) only --
// no real path to CTR exists or is needed, confirmed in this file's
// own header. ──
ram_cell_v1 #(.CELL_ID(16'h1005)) NE (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid_bcast), .cfg_data({22'b0, cfg_data_bcast[46:5]}),
    .data_in_n(32'h0), .data_in_s(E_dout_n), .data_in_e(32'h0), .data_in_w(N_dout_e),
    .arrived_n(1'b0), .arrived_s(E_fire_n), .arrived_e(1'b0), .arrived_w(N_fire_e),
    .data_out_n(NE_dout_n), .data_out_s(NE_dout_s), .data_out_e(NE_dout_e), .data_out_w(NE_dout_w),
    .fire_n(NE_fire_n), .fire_s(NE_fire_s), .fire_e(NE_fire_e), .fire_w(NE_fire_w),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(NE_ack_n), .ack_out_s(NE_ack_s), .ack_out_e(NE_ack_e), .ack_out_w(NE_ack_w),
    .ack_in_n(1'b0), .ack_in_s(E_ack_n), .ack_in_e(1'b0), .ack_in_w(N_ack_e),
    .freeze_in(1'b0), .status_data_valid()
);

// ── NW: corner moat, real ring link to N (east) + W (south) only ──
ram_cell_v1 #(.CELL_ID(16'h1006)) NW (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid_bcast), .cfg_data({22'b0, cfg_data_bcast[46:5]}),
    .data_in_n(32'h0), .data_in_s(W_dout_n), .data_in_e(N_dout_w), .data_in_w(32'h0),
    .arrived_n(1'b0), .arrived_s(W_fire_n), .arrived_e(N_fire_w), .arrived_w(1'b0),
    .data_out_n(NW_dout_n), .data_out_s(NW_dout_s), .data_out_e(NW_dout_e), .data_out_w(NW_dout_w),
    .fire_n(NW_fire_n), .fire_s(NW_fire_s), .fire_e(NW_fire_e), .fire_w(NW_fire_w),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(NW_ack_n), .ack_out_s(NW_ack_s), .ack_out_e(NW_ack_e), .ack_out_w(NW_ack_w),
    .ack_in_n(1'b0), .ack_in_s(W_ack_n), .ack_in_e(N_ack_w), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

// ── SE: corner moat, real ring link to S (east) + E (north) only ──
ram_cell_v1 #(.CELL_ID(16'h1007)) SE (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid_bcast), .cfg_data({22'b0, cfg_data_bcast[46:5]}),
    .data_in_n(E_dout_s), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(S_dout_e),
    .arrived_n(E_fire_s), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(S_fire_e),
    .data_out_n(SE_dout_n), .data_out_s(SE_dout_s), .data_out_e(SE_dout_e), .data_out_w(SE_dout_w),
    .fire_n(SE_fire_n), .fire_s(SE_fire_s), .fire_e(SE_fire_e), .fire_w(SE_fire_w),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(SE_ack_n), .ack_out_s(SE_ack_s), .ack_out_e(SE_ack_e), .ack_out_w(SE_ack_w),
    .ack_in_n(E_ack_s), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(S_ack_e),
    .freeze_in(1'b0), .status_data_valid()
);

// ── SW: corner moat, real ring link to S (west) + W (north) only ──
ram_cell_v1 #(.CELL_ID(16'h1008)) SW (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid_bcast), .cfg_data({22'b0, cfg_data_bcast[46:5]}),
    .data_in_n(W_dout_s), .data_in_s(32'h0), .data_in_e(S_dout_w), .data_in_w(32'h0),
    .arrived_n(W_fire_s), .arrived_s(1'b0), .arrived_e(S_fire_w), .arrived_w(1'b0),
    .data_out_n(SW_dout_n), .data_out_s(SW_dout_s), .data_out_e(SW_dout_e), .data_out_w(SW_dout_w),
    .fire_n(SW_fire_n), .fire_s(SW_fire_s), .fire_e(SW_fire_e), .fire_w(SW_fire_w),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(SW_ack_n), .ack_out_s(SW_ack_s), .ack_out_e(SW_ack_e), .ack_out_w(SW_ack_w),
    .ack_in_n(W_ack_s), .ack_in_s(1'b0), .ack_in_e(S_ack_w), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

// ── Real anti-pruning guard: every one of the 9 real cells' own
// fire_*/dout_*[0] outputs XOR-reduced into one observable signal,
// same convention as project_assemble_v1.py's own array generator. ──
wire tile_alive =
    CTR_fire_n ^ CTR_fire_s ^ CTR_fire_e ^ CTR_fire_w ^ CTR_dout_n[0] ^ CTR_dout_s[0] ^ CTR_dout_e[0] ^ CTR_dout_w[0] ^
    N_fire_n   ^ N_fire_s   ^ N_fire_e   ^ N_fire_w   ^ N_dout_n[0]   ^ N_dout_s[0]   ^ N_dout_e[0]   ^ N_dout_w[0]   ^
    S_fire_n   ^ S_fire_s   ^ S_fire_e   ^ S_fire_w   ^ S_dout_n[0]   ^ S_dout_s[0]   ^ S_dout_e[0]   ^ S_dout_w[0]   ^
    E_fire_n   ^ E_fire_s   ^ E_fire_e   ^ E_fire_w   ^ E_dout_n[0]   ^ E_dout_s[0]   ^ E_dout_e[0]   ^ E_dout_w[0]   ^
    W_fire_n   ^ W_fire_s   ^ W_fire_e   ^ W_fire_w   ^ W_dout_n[0]   ^ W_dout_s[0]   ^ W_dout_e[0]   ^ W_dout_w[0]   ^
    NE_fire_n  ^ NE_fire_s  ^ NE_fire_e  ^ NE_fire_w  ^ NE_dout_n[0]  ^ NE_dout_s[0]  ^ NE_dout_e[0]  ^ NE_dout_w[0]  ^
    NW_fire_n  ^ NW_fire_s  ^ NW_fire_e  ^ NW_fire_w  ^ NW_dout_n[0]  ^ NW_dout_s[0]  ^ NW_dout_e[0]  ^ NW_dout_w[0]  ^
    SE_fire_n  ^ SE_fire_s  ^ SE_fire_e  ^ SE_fire_w  ^ SE_dout_n[0]  ^ SE_dout_s[0]  ^ SE_dout_e[0]  ^ SE_dout_w[0]  ^
    SW_fire_n  ^ SW_fire_s  ^ SW_fire_e  ^ SW_fire_w  ^ SW_dout_n[0]  ^ SW_dout_s[0]  ^ SW_dout_e[0]  ^ SW_dout_w[0];

reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;

assign LED0_N = ~hb_cnt[23];
assign LED1_N = ~tile_alive;

endmodule
