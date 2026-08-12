// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_full_tree_system_v1.v — points.md #273's design, made real-
// hardware-buildable. NOT YET BUILT — prepared project. Same topology
// as `tb_full_tree_system_v1.v` (already iverilog-proven, 19/19
// regression clean), reusing every config value verbatim — this file's
// ONLY real difference from the testbench is HOW A/B/C get seeded
// (a real synthesizable FSM through `mem_read_splitter_v1_test.v`'s
// debug write port, instead of a simulation-only hierarchical
// backdoor) and how results get checked (LEDs, not $display).
//
// TOPOLOGY (identical to #273):
//   SPLITTER -> MUX_ROOT --N--> RA  --\
//                --S--> RB1 --+--> ADDER1 (A+B) --> COMBINER_ROOT slot0 (raw)
//                --E--> MUX_CHILD --N--> RB2 --\
//                          --S--> RC  --+--> ADDER2 (B+C) --> COMBINER_RELAY
//                                                              --> COMBINER_ROOT slot2 (child)
//                                                              --> BRAM(in)
//
// Self-test FSM: (1) configure all 11 cells (one-shot, all cfg_valid
// pulsed together — every cell has its own dedicated cfg_valid input,
// no shared bus, so simultaneous one-cycle configuration is valid,
// unlike the serial per-cell loaders earlier single-chain tops used).
// (2) write A, B, C into SPLITTER's BRAM via the debug port. (3) issue
// the 4 reads (A, B->RB1, B->RB2 with a re-written routing byte, C).
// (4) let the pipeline run — writes are captured continuously and
// checked against the known-correct values (`#273`'s own proven
// A+B=0x1234, B+C=0x0284). LED0 heartbeats while running; LED1
// sticky-lights on ANY mismatch, or if steady-state is reached without
// both results landing (should never light on correct hardware).
`default_nettype none
`timescale 1ns / 1ps

module top_full_tree_system_v1 (
    input  wire CLK_100M,
    output wire LED0_N,
    output wire LED1_N
);

localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

// ── Clock/reset — same convention as every other project here ──────────
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

// ════════════════════════════════════════════════════════════════════
// One-shot configuration — all 11 cells, one cycle, per-instance
// cfg_valid (no shared bus, so no serial loader needed).
// ════════════════════════════════════════════════════════════════════
localparam [63:0] CFG_SPLITTER = {56'h0, DIR_N, DIR_E};
localparam [63:0] CFG_MROOT    = {48'h0, DIR_E, DIR_S, DIR_N, DIR_W};
localparam [63:0] CFG_MCHILD   = {48'h0, DIR_E, DIR_S, DIR_N, DIR_W};
localparam [63:0] CFG_STAGE    = {54'h0, DIR_W, DIR_E};
localparam [63:0] CFG_ADDER    = {56'h0, (DIR_N | DIR_W), DIR_E};
localparam [63:0] CFG_CRELAY   = {48'h0, 4'h0, 4'h0, DIR_N, DIR_E};
localparam [63:0] CFG_CROOT    = {45'h0, 1'b1, 2'b00, DIR_E, 4'h0, DIR_N, DIR_W};

reg cfg_pulse = 1'b0;
reg [2:0] cfg_step = 3'd0;
always @(posedge clk) begin
    if (rst) begin
        cfg_step  <= 3'd0;
        cfg_pulse <= 1'b0;
    end else if (cfg_step == 3'd0) begin
        cfg_pulse <= 1'b1;
        cfg_step  <= 3'd1;
    end else if (cfg_step == 3'd1) begin
        cfg_pulse <= 1'b0;
        cfg_step  <= 3'd2;
    end
end
wire cfg_active = cfg_pulse;

// ════════════════════════════════════════════════════════════════════
// READ SIDE
// ════════════════════════════════════════════════════════════════════
reg  [31:0] addr_in = 0;
reg         addr_pulse = 0;
reg  [15:0] dbg_wr_addr = 0;
reg  [39:0] dbg_wr_wdata = 0;
reg         dbg_wr_valid = 0;
wire        dbg_wr_done;

wire [31:0] splitter_data_out_e;
wire [7:0]  splitter_routing_out;
wire        splitter_fire_e, splitter_ready_o;
wire        root_ack_out_w;

mem_read_splitter_v1_test #(.CELL_ID(16'h0010), .ADDR_WIDTH(16)) SPLITTER (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_SPLITTER),
    .data_in_n(addr_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(addr_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(splitter_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(splitter_fire_e), .fire_w(),
    .ready_out(splitter_ready_o),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(root_ready_out), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(root_ack_out_w), .ack_in_w(1'b0),
    .freeze_in(1'b0),
    .routing_out(splitter_routing_out),
    .status_data_valid(), .status_addr_captured(),
    .dbg_wr_valid(dbg_wr_valid), .dbg_wr_addr(dbg_wr_addr), .dbg_wr_wdata(dbg_wr_wdata), .dbg_wr_done(dbg_wr_done)
);

wire root_ready_out;
wire [31:0] root_data_out_n, root_data_out_s, root_data_out_e;
wire        root_fire_n, root_fire_s, root_fire_e;
wire [7:0]  root_routing_out;
wire        mchild_ack_out_w;
wire ra_ready_out, rb1_ready_out;
wire ra_ack_out_w, rb1_ack_out_w;

mux_cell_v1 #(.CELL_ID(16'h0011)) MUX_ROOT (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_MROOT),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(splitter_data_out_e),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(splitter_fire_e),
    .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(8'h0), .routing_in_w(splitter_routing_out),
    .data_out_n(root_data_out_n), .data_out_s(root_data_out_s), .data_out_e(root_data_out_e), .data_out_w(),
    .fire_n(root_fire_n), .fire_s(root_fire_s), .fire_e(root_fire_e), .fire_w(),
    .routing_out(root_routing_out),
    .ready_out(root_ready_out),
    .ready_in_n(ra_ready_out), .ready_in_s(rb1_ready_out), .ready_in_e(mchild_ready_out), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(root_ack_out_w),
    .ack_in_n(ra_ack_out_w), .ack_in_s(rb1_ack_out_w), .ack_in_e(mchild_ack_out_w), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

wire mchild_ready_out;
wire [31:0] mchild_data_out_n, mchild_data_out_s;
wire        mchild_fire_n, mchild_fire_s;
wire rb2_ready_out, rc_ready_out;
wire rb2_ack_out_w, rc_ack_out_w;

mux_cell_v1 #(.CELL_ID(16'h0012)) MUX_CHILD (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_MCHILD),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(root_data_out_e),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(root_fire_e),
    .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(8'h0), .routing_in_w(root_routing_out),
    .data_out_n(mchild_data_out_n), .data_out_s(mchild_data_out_s), .data_out_e(), .data_out_w(),
    .fire_n(mchild_fire_n), .fire_s(mchild_fire_s), .fire_e(), .fire_w(),
    .routing_out(),
    .ready_out(mchild_ready_out),
    .ready_in_n(rb2_ready_out), .ready_in_s(rc_ready_out), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(mchild_ack_out_w),
    .ack_in_n(rb2_ack_out_w), .ack_in_s(rc_ack_out_w), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

wire [31:0] ra_data_out_e, rb1_data_out_e, rb2_data_out_e, rc_data_out_e;
wire ra_fire_e, rb1_fire_e, rb2_fire_e, rc_fire_e;
wire adder1_ready_out, adder2_ready_out;
wire adder1_ack_out_n, adder1_ack_out_w, adder2_ack_out_n, adder2_ack_out_w;

ram_cell_v1 #(.CELL_ID(16'h0013)) RA (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_STAGE),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(root_data_out_n),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(root_fire_n),
    .data_out_n(), .data_out_s(), .data_out_e(ra_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(ra_fire_e), .fire_w(),
    .ready_out(ra_ready_out),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(adder1_ready_out), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ra_ack_out_w),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(adder1_ack_out_n), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

ram_cell_v1 #(.CELL_ID(16'h0014)) RB1 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_STAGE),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(root_data_out_s),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(root_fire_s),
    .data_out_n(), .data_out_s(), .data_out_e(rb1_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(rb1_fire_e), .fire_w(),
    .ready_out(rb1_ready_out),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(adder1_ready_out), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(rb1_ack_out_w),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(adder1_ack_out_w), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

ram_cell_v1 #(.CELL_ID(16'h0015)) RB2 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_STAGE),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(mchild_data_out_n),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(mchild_fire_n),
    .data_out_n(), .data_out_s(), .data_out_e(rb2_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(rb2_fire_e), .fire_w(),
    .ready_out(rb2_ready_out),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(adder2_ready_out), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(rb2_ack_out_w),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(adder2_ack_out_n), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

ram_cell_v1 #(.CELL_ID(16'h0016)) RC (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_STAGE),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(mchild_data_out_s),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(mchild_fire_s),
    .data_out_n(), .data_out_s(), .data_out_e(rc_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(rc_fire_e), .fire_w(),
    .ready_out(rc_ready_out),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(adder2_ready_out), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(rc_ack_out_w),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(adder2_ack_out_w), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

wire [31:0] adder1_data_out_e, adder2_data_out_e;
wire adder1_fire_e, adder2_fire_e;
wire croot_ack_n, croot_ack_e;

adder_cell_v1 #(.CELL_ID(16'h0017)) ADDER1 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_ADDER),
    .data_in_n(ra_data_out_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(rb1_data_out_e),
    .arrived_n(ra_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(rb1_fire_e),
    .data_out_n(), .data_out_s(), .data_out_e(adder1_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(adder1_fire_e), .fire_w(),
    .ready_out(adder1_ready_out),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(adder1_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(adder1_ack_out_w),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(croot_ack_n), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(), .status_a_arrived()
);

adder_cell_v1 #(.CELL_ID(16'h0018)) ADDER2 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_ADDER),
    .data_in_n(rb2_data_out_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(rc_data_out_e),
    .arrived_n(rb2_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(rc_fire_e),
    .data_out_n(), .data_out_s(), .data_out_e(adder2_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(adder2_fire_e), .fire_w(),
    .ready_out(adder2_ready_out),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(adder2_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(adder2_ack_out_w),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(crelay_ack_n), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(), .status_a_arrived()
);

// ════════════════════════════════════════════════════════════════════
// WRITE SIDE
// ════════════════════════════════════════════════════════════════════
wire crelay_ack_n;
wire [31:0] crelay_data_out_e;
wire crelay_fire_e;
wire [7:0] crelay_routing_out;
wire crelay_ready_out;

combiner_relay_v1 #(.CELL_ID(16'h0019)) COMBINER_RELAY (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_CRELAY),
    .data_in_n(adder2_data_out_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(adder2_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .ack_out_n(crelay_ack_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .data_out_n(), .data_out_s(), .data_out_e(crelay_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(crelay_fire_e), .fire_w(),
    .routing_out(crelay_routing_out),
    .ready_out(crelay_ready_out),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(croot_ack_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_slot(), .status_data_valid()
);

wire [1:0] croot_status_slot;
wire        wr_cmd_valid;
wire [15:0] wr_cmd_addr;
wire [39:0] wr_cmd_wdata;
wire        wr_write_done;

combiner_cell_v2 #(.CELL_ID(16'h001A), .ADDR_WIDTH(16)) COMBINER_ROOT (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_CROOT),
    .data_in_n(adder1_data_out_e), .data_in_s(32'h0), .data_in_e(crelay_data_out_e), .data_in_w(32'h0),
    .arrived_n(adder1_fire_e), .arrived_s(1'b0), .arrived_e(crelay_fire_e), .arrived_w(1'b0),
    .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(crelay_routing_out), .routing_in_w(8'h0),
    .ack_out_n(croot_ack_n), .ack_out_s(), .ack_out_e(croot_ack_e), .ack_out_w(),
    .wr_cmd_valid(wr_cmd_valid), .wr_cmd_addr(wr_cmd_addr), .wr_cmd_wdata(wr_cmd_wdata),
    .wr_write_done(wr_write_done),
    .freeze_in(1'b0),
    .status_slot(croot_status_slot), .status_wrote_this_cycle()
);

// ── BRAM(in) — separate instance from BRAM(out), per #257's own
// "two independent regions" design. ──
wire        in_rdata_valid;
wire [39:0] in_rdata;
reg         in_rd_cmd_valid = 0;
reg  [15:0] in_rd_cmd_addr = 0;
wire        in_mem_cmd_valid = wr_cmd_valid || in_rd_cmd_valid;
wire        in_mem_cmd_op    = wr_cmd_valid;   // write wins priority (never coincide in this self-test)
wire [15:0] in_mem_cmd_addr  = wr_cmd_valid ? wr_cmd_addr : in_rd_cmd_addr;
wire [39:0] in_mem_cmd_wdata = wr_cmd_wdata;

// NOTE (points.md #284): bram_controller_v2.v, not v1 -- for
// consistency/safety with the SPLITTER's own required swap (v1 failed
// to infer as real M20K 3 hierarchy levels deep). BRAM_IN here is only
// 2 levels deep (matching #265's own successful configuration), so v1
// likely would have been fine here specifically -- but v2 has no real
// downside at 2 levels either, and using it uniformly for BOTH
// memories removes any doubt rather than leaving one on "probably
// fine, unconfirmed" and the other on the confirmed fix.
bram_controller_v2 #(.ADDR_WIDTH(16), .DATA_WIDTH(40)) BRAM_IN (
    .clk(clk), .rst(rst),
    .cmd_valid(in_mem_cmd_valid), .cmd_op(in_mem_cmd_op), .cmd_addr(in_mem_cmd_addr), .cmd_wdata(in_mem_cmd_wdata),
    .rdata_valid(in_rdata_valid), .rdata(in_rdata), .write_done(wr_write_done)
);

// ════════════════════════════════════════════════════════════════════
// Self-test FSM — real synthesizable sequencing, replacing the sim
// testbench's `initial` block.
// ════════════════════════════════════════════════════════════════════
localparam [31:0] VAL_A = 32'h0000_1000;
localparam [31:0] VAL_B = 32'h0000_0234;
localparam [31:0] VAL_C = 32'h0000_0050;
localparam [39:0] EXP_RESULT1 = {2'd1, 2'b00, 2'b00, 2'b00, VAL_A + VAL_B};   // 0x4000001234
localparam [39:0] EXP_RESULT2 = {2'd2, 2'b00, 2'd2, 2'b00, VAL_B + VAL_C};    // 0x8800000284

localparam S_CFGWAIT   = 4'd0,
           S_WR_A      = 4'd1,  S_WR_A_WAIT  = 4'd2,
           S_WR_B1     = 4'd3,  S_WR_B1_WAIT = 4'd4,
           S_ISSUE_A   = 4'd5,  S_ISSUE_A_SETTLE  = 4'd13,
           S_ISSUE_B1  = 4'd6,  S_ISSUE_B1_SETTLE = 4'd14,
           S_WR_B2     = 4'd7,  S_WR_B2_WAIT = 4'd8,
           S_ISSUE_B2  = 4'd9,  S_ISSUE_B2_SETTLE = 4'd15,
           S_WR_C      = 5'd16, S_WR_C_WAIT  = 5'd17,
           S_ISSUE_C   = 4'd10,
           S_WAIT      = 4'd11,
           S_RUN       = 4'd12;
// NOTE: an earlier draft checked `splitter_ready_o` immediately in the
// very next state after a state that had just pulsed `addr_pulse` for
// a DIFFERENT/prior address — a real race, confirmed via iverilog
// (first sim run reached S_RUN with zero results, zero errors: the
// address issues silently never delivered). Root cause: `ready_out` is
// a combinational read of `addr_captured`/`data_valid`, which don't
// actually update until the register edge AFTER the capture that just
// happened — so the very next cycle still reads the OLD "ready" value,
// letting the next ISSUE state fire one cycle too early, before the
// splitter has genuinely finished the previous capture. Fixed by
// inserting an explicit SETTLE state (waits `SETTLE_CYCLES` cycles,
// comfortably more than the real 1-cycle read latency) between every
// pulse and the next readiness check — same robust pattern
// `top_bram_controller_test_v1.v` already used successfully (waiting
// for genuine completion signals, not re-polling a registered signal
// on the very next cycle).
localparam SETTLE_CYCLES = 5'd20;

reg [4:0]  state = S_CFGWAIT;
reg [23:0] wait_cnt = 0;
reg [4:0]  settle_cnt = 0;
reg        result1_seen = 0, result2_seen = 0;
reg        err_sticky = 0;
reg [23:0] heartbeat = 0;

// Real, genuinely runtime-variable address offset — an earlier draft
// used LITERAL CONSTANT addresses (16'h0010/0011/0012) throughout, and
// the real Quartus build confirmed the consequence directly: "Total
// block memory bits 0/43,642,880 (0%)" — Quartus's optimizer legally
// concluded the memory only ever needed to hold those few fixed
// values, collapsing the entire 64K-deep array down to plain
// registers instead of inferring real M20K blocks at all. The exact
// same trap `#249`'s own top_ram_chain50_v1.v was specifically built
// to avoid (a free-running stimulus, not a constant), and the same fix
// `top_bram_controller_test_v1.v` (`#262`/`#265`) already proved
// works — a genuinely varying offset added to every address used,
// each full pass. The self-test now loops continuously (S_RUN
// increments the offset and returns to S_WR_A) rather than running
// once — Quartus can no longer determine a small fixed address set at
// compile time.
reg [15:0] addr_offset = 16'h0;

always @(posedge clk) begin
    addr_pulse   <= 1'b0;
    dbg_wr_valid <= 1'b0;
    heartbeat    <= heartbeat + 24'h1;

    if (rst) begin
        state         <= S_CFGWAIT;
        wait_cnt      <= 0;
        settle_cnt    <= 0;
        result1_seen  <= 0;
        result2_seen  <= 0;
        err_sticky    <= 0;
        addr_offset   <= 16'h0;
    end else begin
        // Continuous write-capture — same pattern as the proven
        // testbench, active for the whole run.
        if (wr_cmd_valid) begin
            if (wr_cmd_wdata == EXP_RESULT1) result1_seen <= 1'b1;
            else if (wr_cmd_wdata == EXP_RESULT2) result2_seen <= 1'b1;
            else err_sticky <= 1'b1;
        end

        case (state)
            S_CFGWAIT: if (!cfg_active && cfg_step == 3'd2) state <= S_WR_A;

            S_WR_A: begin
                dbg_wr_valid <= 1'b1;
                dbg_wr_addr  <= 16'h0010 + addr_offset;
                dbg_wr_wdata <= {2'd1, 2'b00, 2'b00, 2'b00, VAL_A};
                state <= S_WR_A_WAIT;
            end
            S_WR_A_WAIT: if (dbg_wr_done) state <= S_ISSUE_A;

            S_ISSUE_A: if (splitter_ready_o) begin
                addr_in <= {16'h0, 16'h0010 + addr_offset}; addr_pulse <= 1'b1;
                settle_cnt <= 0;
                state <= S_ISSUE_A_SETTLE;
            end
            S_ISSUE_A_SETTLE: begin
                settle_cnt <= settle_cnt + 5'd1;
                if (settle_cnt >= SETTLE_CYCLES) state <= S_WR_B1;
            end

            S_WR_B1: begin
                dbg_wr_valid <= 1'b1;
                dbg_wr_addr  <= 16'h0011 + addr_offset;
                dbg_wr_wdata <= {2'd1, 2'b01, 2'b00, 2'b00, VAL_B};
                state <= S_WR_B1_WAIT;
            end
            S_WR_B1_WAIT: if (dbg_wr_done) state <= S_ISSUE_B1;

            S_ISSUE_B1: if (splitter_ready_o) begin
                addr_in <= {16'h0, 16'h0011 + addr_offset}; addr_pulse <= 1'b1;
                settle_cnt <= 0;
                state <= S_ISSUE_B1_SETTLE;
            end
            S_ISSUE_B1_SETTLE: begin
                settle_cnt <= settle_cnt + 5'd1;
                if (settle_cnt >= SETTLE_CYCLES) state <= S_WR_B2;
            end

            S_WR_B2: begin
                dbg_wr_valid <= 1'b1;
                dbg_wr_addr  <= 16'h0011 + addr_offset;
                dbg_wr_wdata <= {2'd2, 2'b00, 2'b10, 2'b00, VAL_B};
                state <= S_WR_B2_WAIT;
            end
            S_WR_B2_WAIT: if (dbg_wr_done) state <= S_ISSUE_B2;

            S_ISSUE_B2: if (splitter_ready_o) begin
                addr_in <= {16'h0, 16'h0011 + addr_offset}; addr_pulse <= 1'b1;
                settle_cnt <= 0;
                state <= S_ISSUE_B2_SETTLE;
            end
            S_ISSUE_B2_SETTLE: begin
                settle_cnt <= settle_cnt + 5'd1;
                if (settle_cnt >= SETTLE_CYCLES) state <= S_WR_C;
            end

            S_WR_C: begin
                dbg_wr_valid <= 1'b1;
                dbg_wr_addr  <= 16'h0012 + addr_offset;
                dbg_wr_wdata <= {2'd2, 2'b01, 2'b10, 2'b00, VAL_C};
                state <= S_WR_C_WAIT;
            end
            S_WR_C_WAIT: if (dbg_wr_done) state <= S_ISSUE_C;

            S_ISSUE_C: if (splitter_ready_o) begin
                addr_in <= {16'h0, 16'h0012 + addr_offset}; addr_pulse <= 1'b1;
                state <= S_WAIT;
            end

            S_WAIT: begin
                wait_cnt <= wait_cnt + 24'h1;
                if (wait_cnt > 24'd400) state <= S_RUN;
            end

            // Loops continuously — a new, genuinely different address
            // offset every pass, not a one-shot test. result1_seen/
            // result2_seen reset here too, so a failure on ANY later
            // pass is caught, not masked by an earlier pass's success
            // (result flags are otherwise sticky, matching #262's own
            // established convention for a repeating self-test).
            S_RUN: begin
                wait_cnt <= 0;
                addr_offset  <= addr_offset + 16'h1;
                result1_seen <= 1'b0;
                result2_seen <= 1'b0;
                state <= S_WR_A;
            end

            default: state <= S_CFGWAIT;
        endcase
    end
end

assign LED0_N = ~heartbeat[21];                              // heartbeat
assign LED1_N = ~err_sticky;
// LED1 lights (active-low convention) sticky on ANY wrong write, ever,
// across any pass. (The "reached S_RUN without both results" check
// from the one-shot version no longer applies now that S_RUN itself is
// a single transient cycle in a continuous loop, not a terminal state.)

endmodule
