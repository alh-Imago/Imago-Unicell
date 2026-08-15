// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_stripped_zone50_addons_v1.v — points.md #312 continuation: a
// direct clone of the proven top_stripped_zone50_v1.v baseline
// (points.md #148), with ONE change: every cell's shared output
// (data_out_n/s/e/w, confirmed identical -- unicell_stripped_v1.v
// broadcasts a single out_buffer to all four cardinal ports) is
// routed through the three real ADDONs (points.md #311:
// shift_lane_addon_v1.v, nibble_mask_addon_v1.v, invert_addon_v1.v)
// before reaching neighboring cells, instead of going straight
// through. The unicell_stripped_v1 cell instance itself is completely
// UNTOUCHED -- same ports, same connections, same proven core --
// matching the ADDON definition exactly (#253: wraps the shell from
// OUTSIDE, the cell still participates in the fabric mesh unchanged
// underneath).
//
// Addon config is driven from each cell's own free-running local
// counter (not a fixed literal), so Quartus cannot constant-propagate
// the addon logic away (the #283/#286 lesson, applied here).
//
// Purpose: a real Quartus ALM/Fmax comparison against the unmodified
// baseline, at the same 50-cell scale (avoiding #228's own lesson --
// too few cells lets Quartus prune logic that never gets meaningfully
// exercised, producing a false "per-cell" cost).
`default_nettype none
`timescale 1ns / 1ps

module top_stripped_zone50_addons_v1 (
    input  wire CLK_100M,
    output wire LED0_N,
    output wire LED1_N
);

localparam ROWS = 5;
localparam COLS = 10;
localparam CELLS = ROWS*COLS;   // 50

reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

localparam [9:0] TOPO_NOR = 10'h004;
localparam [2:0] OP_PROGRAM  = 3'b000;
localparam [2:0] OP_COLLECT  = 3'b001;
localparam [2:0] OP_SET_CTRL = 3'b010;
localparam [2:0] OP_CLR_CTRL = 3'b011;
localparam [2:0] OP_DIAG     = 3'b100;
localparam [2:0] PID_TOPOLOGY = 3'd0, PID_ROUTING_MASK = 3'd1, PID_COMPLETE = 3'd7;

// ── Snake routing, generalized to ROWS x COLS (was hardcoded to 5x5) ──
function [5:0] snake_mask(input [3:0] r, input [3:0] c);
    begin
        if (r == ROWS-1 && c == COLS-1)
            snake_mask = 6'b000000;   // chain end
        else if (r[0] == 1'b0) begin
            if (c < COLS-1) snake_mask = 6'b000100;   // East
            else            snake_mask = 6'b000010;   // South (wrap)
        end else begin
            if (c > 0)      snake_mask = 6'b001000;   // West
            else            snake_mask = 6'b000010;   // South (wrap)
        end
    end
endfunction

reg [31:0] stim_cnt = 32'h0;
always @(posedge clk) if (!rst) stim_cnt <= stim_cnt + 32'h1;
wire        seed_pulse = (stim_cnt[7:0] == 8'h00);
wire [31:0] seed_data  = {stim_cnt[15:0], stim_cnt[31:16]};

// ── Wrapper program driver — CELLS addresses now, not fixed 25 ──
reg [6:0] prog_addr = 7'h0;
reg [3:0] prog_row  = 4'h0;
reg [3:0] prog_col  = 4'h0;
reg [1:0] prog_word = 2'h0;
reg       prog_active = 1'b1;

wire [5:0]  prog_snake  = snake_mask(prog_row, prog_col);
wire [31:0] prog_word0 = {13'h0, PID_TOPOLOGY,     6'h0, TOPO_NOR};
wire [31:0] prog_word1 = {13'h0, PID_ROUTING_MASK, 12'h0, prog_snake[3:0]};
wire [31:0] prog_word2 = {13'h0, PID_COMPLETE,     16'h1};
wire [31:0] prog_data  = (prog_word == 2'd0) ? prog_word0 :
                          (prog_word == 2'd1) ? prog_word1 : prog_word2;

always @(posedge clk) begin
    if (rst) begin
        prog_addr   <= 7'h0;
        prog_row    <= 4'h0;
        prog_col    <= 4'h0;
        prog_word   <= 2'h0;
        prog_active <= 1'b1;
    end else if (prog_active) begin
        if (prog_word == 2'd2) begin
            prog_word <= 2'h0;
            if (prog_addr == CELLS-1) begin
                prog_active <= 1'b0;
            end else begin
                prog_addr <= prog_addr + 7'd1;
                if (prog_col == COLS-1) begin
                    prog_col <= 4'h0;
                    prog_row <= prog_row + 4'd1;
                end else begin
                    prog_col <= prog_col + 4'd1;
                end
            end
        end else begin
            prog_word <= prog_word + 2'd1;
        end
    end
end

// ── Freeze-cascade exercise (same pattern as top_stripped_grid5x5_both_v2.v,
// sim-confirmed there first): freeze one interior cell via the wrapper's
// real SET_CTRL path after programming completes, hold it, confirm the
// already-wired ready/ack backpressure cascades upstream at this larger
// scale too, then release. Reuses the SAME wbus chain as programming. ──
localparam [6:0] FREEZE_TARGET = 7'd25;   // r=2,c=5 -- interior, on the snake path
localparam [2:0] PH_PROGRAM = 3'd0, PH_SETTLE = 3'd1, PH_HOLD = 3'd2, PH_DONE = 3'd3;
reg [1:0]  fz_phase = PH_PROGRAM;
reg [15:0] fz_wait  = 16'h0;
reg        fz_bus_valid = 1'b0;
reg [2:0]  fz_bus_op    = 3'h0;
reg        freeze_cascade_seen = 1'b0;

always @(posedge clk) begin
    if (rst) begin
        fz_phase <= PH_PROGRAM;
        fz_wait  <= 16'h0;
        fz_bus_valid <= 1'b0;
        fz_bus_op    <= 3'h0;
        freeze_cascade_seen <= 1'b0;
    end else begin
        fz_bus_valid <= 1'b0;   // one-shot pulse by default
        case (fz_phase)
            PH_PROGRAM: if (!prog_active) begin
                fz_phase <= PH_SETTLE; fz_wait <= 16'h0;
            end
            PH_SETTLE: begin
                fz_wait <= fz_wait + 16'h1;
                if (fz_wait == 16'd200) begin
                    fz_bus_valid <= 1'b1; fz_bus_op <= OP_SET_CTRL;  // index 0 = freeze
                    fz_phase <= PH_HOLD; fz_wait <= 16'h0;
                end
            end
            PH_HOLD: begin
                fz_wait <= fz_wait + 16'h1;
                if (!all_ready) freeze_cascade_seen <= 1'b1;
                if (fz_wait == 16'd2000) begin
                    fz_bus_valid <= 1'b1; fz_bus_op <= OP_CLR_CTRL;
                    fz_phase <= PH_DONE;
                end
            end
            default: ;
        endcase
    end
end

wire        w0_bus_in_valid = prog_active ? 1'b1 : fz_bus_valid;
wire [6:0]  w0_bus_in_addr  = prog_active ? prog_addr : FREEZE_TARGET;
wire [2:0]  w0_bus_in_op    = prog_active ? OP_PROGRAM : fz_bus_op;
wire [31:0] w0_bus_in_data  = prog_active ? prog_data : 32'h0;   // ctrl index 0 = freeze

// ── Command-cell mechanism driver (identical to step 3/#146) ──
reg [1:0]  cmd_word = 2'h0;
reg        cmd_trigger = 1'b0;
reg        cmd_arrived = 1'b0;
wire [31:0] cmd_data = (cmd_word == 2'd0) ? {13'h0, PID_TOPOLOGY, 6'h0, TOPO_NOR} :
                       (cmd_word == 2'd1) ? {13'h0, PID_ROUTING_MASK, 16'h0} :
                                            {13'h0, PID_COMPLETE, 16'h1};
always @(posedge clk) begin
    if (rst) begin
        cmd_word    <= 2'h0;
        cmd_trigger <= 1'b0;
        cmd_arrived <= 1'b0;
    end else begin
        cmd_trigger <= stim_cnt[13];
        cmd_arrived <= stim_cnt[13] && (stim_cnt[6:0] != 7'h7F);
        if (cmd_arrived) cmd_word <= (cmd_word == 2'd2) ? 2'd0 : (cmd_word + 2'd1);
    end
end

// ── Per-cell signal arrays — 2D, sized to ROWS x COLS ──
// c_dout_* now carries the ADDON-PROCESSED value (post-shift/lane/
// mask/invert) -- this is what neighboring cells and the LED
// aggregation actually read, identical to the baseline's own naming
// so the rest of this file (unchanged from top_stripped_zone50_v1.v)
// needs no further edits below. raw_dout_* is the cell's own genuine,
// untouched output, captured separately so the addon chain has
// something real to process.
wire [31:0] c_dout_n[0:ROWS-1][0:COLS-1], c_dout_s[0:ROWS-1][0:COLS-1];
wire [31:0] c_dout_e[0:ROWS-1][0:COLS-1], c_dout_w[0:ROWS-1][0:COLS-1];
wire [31:0] raw_dout_n[0:ROWS-1][0:COLS-1];   // only N needed -- all 4 are
                                                // identical (confirmed:
                                                // unicell_stripped_v1.v
                                                // broadcasts one shared
                                                // out_buffer to all four)
wire [31:0] addon_dout[0:ROWS-1][0:COLS-1];    // after nibble_mask -> shift/lane -> invert
wire        c_fire_n[0:ROWS-1][0:COLS-1], c_fire_s[0:ROWS-1][0:COLS-1];
wire        c_fire_e[0:ROWS-1][0:COLS-1], c_fire_w[0:ROWS-1][0:COLS-1];
wire        c_ready [0:ROWS-1][0:COLS-1];
wire        c_ackn  [0:ROWS-1][0:COLS-1], c_acks [0:ROWS-1][0:COLS-1];
wire        c_acke  [0:ROWS-1][0:COLS-1], c_ackw [0:ROWS-1][0:COLS-1];

// ── Per-cell free-running local addon-config counter -- NOT a fixed
// literal, so Quartus cannot constant-propagate the addon logic away
// (#283/#286's own lesson). Each cell gets its own independent
// counter (seeded by FLAT) so the config genuinely varies cell to
// cell as well as cycle to cycle. ──
reg [15:0] addon_cnt[0:ROWS-1][0:COLS-1];

wire        wbus_valid[0:CELLS];
wire [6:0]  wbus_addr [0:CELLS];
wire [2:0]  wbus_op   [0:CELLS];
wire [31:0] wbus_data [0:CELLS];

assign wbus_valid[0] = w0_bus_in_valid;
assign wbus_addr[0]  = w0_bus_in_addr;
assign wbus_op[0]    = w0_bus_in_op;
assign wbus_data[0]  = w0_bus_in_data;

wire [31:0] w_prog_data [0:ROWS-1][0:COLS-1];
wire        w_prog_valid[0:ROWS-1][0:COLS-1];
wire        w_program_out[0:ROWS-1][0:COLS-1];
wire        w_freeze[0:ROWS-1][0:COLS-1], w_hold[0:ROWS-1][0:COLS-1], w_fbint[0:ROWS-1][0:COLS-1];
wire        w_reemit[0:ROWS-1][0:COLS-1], w_update[0:ROWS-1][0:COLS-1], w_selfupd[0:ROWS-1][0:COLS-1];
wire        c_program_done[0:ROWS-1][0:COLS-1];
wire        cmd_program_out[0:ROWS-1][0:COLS-1];

genvar r, c;
generate
for (r = 0; r < ROWS; r = r + 1) begin : ROW
    for (c = 0; c < COLS; c = c + 1) begin : COL

        localparam integer FLAT = r*COLS + c;

        wire [31:0] diag_word = {30'h0, c_program_done[r][c], c_ready[r][c]};

        cell_wrapper_v2 #(.ADDR(FLAT[6:0])) WRAP (
            .clk(clk), .rst(rst),
            .bus_in_valid(wbus_valid[FLAT]), .bus_in_addr(wbus_addr[FLAT]),
            .bus_in_op(wbus_op[FLAT]),       .bus_in_data(wbus_data[FLAT]),
            .bus_out_valid(wbus_valid[FLAT+1]), .bus_out_addr(wbus_addr[FLAT+1]),
            .bus_out_op(wbus_op[FLAT+1]),       .bus_out_data(wbus_data[FLAT+1]),
            .cell_prog_data_out(w_prog_data[r][c]), .cell_prog_arrived_out(w_prog_valid[r][c]),
            .cell_program_out(w_program_out[r][c]), .cell_program_done_in(c_program_done[r][c]),
            .cell_freeze_out(w_freeze[r][c]), .cell_hold_out(w_hold[r][c]),
            .cell_fb_internal_out(w_fbint[r][c]), .cell_a_reemit_out(w_reemit[r][c]),
            .cell_a_update_out(w_update[r][c]), .cell_a_self_update_out(w_selfupd[r][c]),
            .cell_out_buffer(c_dout_n[r][c]), .cell_diag_in(diag_word)
        );

        cell_command_v1 CMD (
            .clk(clk), .rst(rst),
            .trigger_in(cmd_trigger),
            .program_done_in(c_program_done[r][c]),
            .program_out(cmd_program_out[r][c])
        );

        unicell_stripped_v1 #(.CELL_ID({6'h0, r[4:0], c[4:0]})) CELL (
            .clk(clk), .rst(rst), .cfg_valid(1'b0), .cfg_data(128'h0),

            .data_in_n((r==0) ? ((c==0) ? seed_data : 32'h0) : c_dout_s[r-1][c]),
            .arrived_n((r==0) ? ((c==0) ? seed_pulse : 1'b0) : c_fire_s[r-1][c]),
            .data_in_s((r==ROWS-1) ? 32'h0 : c_dout_n[r+1][c]),
            .arrived_s((r==ROWS-1) ? 1'b0  : c_fire_n[r+1][c]),
            .data_in_e((c==COLS-1) ? 32'h0 : c_dout_w[r][c+1]),
            .arrived_e((c==COLS-1) ? 1'b0  : c_fire_w[r][c+1]),
            .data_in_w((c==0) ? 32'h0 : c_dout_e[r][c-1]),
            .arrived_w((c==0) ? 1'b0  : c_fire_e[r][c-1]),

            .data_out_n(raw_dout_n[r][c]), .fire_n(c_fire_n[r][c]),
            .data_out_s(), .fire_s(c_fire_s[r][c]),
            .data_out_e(), .fire_e(c_fire_e[r][c]),
            .data_out_w(), .fire_w(c_fire_w[r][c]),

            .ready_out(c_ready[r][c]),
            .ready_in_n((r==0) ? 1'b1 : c_ready[r-1][c]),
            .ready_in_s((r==ROWS-1) ? 1'b1 : c_ready[r+1][c]),
            .ready_in_e((c==COLS-1) ? 1'b1 : c_ready[r][c+1]),
            .ready_in_w((c==0) ? 1'b1 : c_ready[r][c-1]),

            .ack_out_n(c_ackn[r][c]), .ack_out_s(c_acks[r][c]),
            .ack_out_e(c_acke[r][c]), .ack_out_w(c_ackw[r][c]),
            .ack_in_n((r==0) ? 1'b0 : c_acks[r-1][c]),
            .ack_in_s((r==ROWS-1) ? 1'b0 : c_ackn[r+1][c]),
            .ack_in_e((c==COLS-1) ? 1'b0 : c_ackw[r][c+1]),
            .ack_in_w((c==0) ? 1'b0 : c_acke[r][c-1]),

            .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
            .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),

            .freeze_in(w_freeze[r][c]),
            .hold_in(w_hold[r][c]),
            .fb_internal_in(w_fbint[r][c]),
            .a_reemit_in(w_reemit[r][c]),
            .a_update_in(w_update[r][c]),
            .a_self_update_in(w_selfupd[r][c]),

            .program_in(w_program_out[r][c] | cmd_program_out[r][c]),
            .program_done(c_program_done[r][c]),

            .prog_data_in_n(w_prog_data[r][c]), .prog_data_in_s(32'h0),
            .prog_data_in_e(32'h0), .prog_data_in_w(cmd_data),
            .prog_arrived_in_n(w_prog_valid[r][c]), .prog_arrived_in_s(1'b0),
            .prog_arrived_in_e(1'b0), .prog_arrived_in_w(cmd_arrived),
            .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
        );

        // ── The three real ADDONs (#311), wired OUTSIDE the untouched
        // cell instance above -- exactly the ADDON definition (#253):
        // wraps the shell from outside, the cell itself unaffected.
        // Order: nibble_mask (pre) -> shift/lane (SHIFT_OUT direction)
        // -> invert. Config driven from this cell's own free-running
        // local counter, not a fixed literal (#283/#286's lesson).
        always @(posedge clk) begin
            if (rst) addon_cnt[r][c] <= FLAT[15:0];
            else     addon_cnt[r][c] <= addon_cnt[r][c] + 16'h1;
        end

        wire [31:0] after_mask, after_shiftlane;

        nibble_mask_addon_v1 NM (
            .mask_en(addon_cnt[r][c][0]),
            .nibble_mask(addon_cnt[r][c][15:8]),
            .data_in(raw_dout_n[r][c]),
            .data_out(after_mask)
        );

        shift_lane_addon_v1 SL (
            .direction(1'b1),                      // SHIFT_OUT (out-shift + lane, matching real coupling)
            .shift_en(addon_cnt[r][c][1]),
            .shift_amt({addon_cnt[r][c][4:2], 2'b00}), // constrained to the real sparse-supported set
            .lane_cut(addon_cnt[r][c][7:5]),
            .data_in(after_mask),
            .data_out(after_shiftlane)
        );

        invert_addon_v1 INV (
            .invert_en(addon_cnt[r][c][2]),
            .data_in(after_shiftlane),
            .data_out(addon_dout[r][c])
        );

        // All four cardinal-facing outputs carry the SAME addon-
        // processed value -- matching the core's own original
        // all-four-identical broadcast exactly.
        assign c_dout_n[r][c] = addon_dout[r][c];
        assign c_dout_s[r][c] = addon_dout[r][c];
        assign c_dout_e[r][c] = addon_dout[r][c];
        assign c_dout_w[r][c] = addon_dout[r][c];

    end
end
endgenerate

wire chain_tail_bit = wbus_data[CELLS][0] ^ wbus_valid[CELLS];
wire cmd_activity = cmd_program_out[0][0] ^ cmd_program_out[2][5] ^ cmd_program_out[4][9];

wire all_ready;
genvar rr, cc;
wire [ROWS*COLS-1:0] ready_flat;
generate
for (rr = 0; rr < ROWS; rr = rr + 1) begin : RRDY
    for (cc = 0; cc < COLS; cc = cc + 1) begin : CRDY
        assign ready_flat[rr*COLS+cc] = c_ready[rr][cc];
    end
end
endgenerate
assign all_ready = &ready_flat;

assign LED0_N = all_ready;
assign LED1_N = ~(stim_cnt[23] ^ chain_tail_bit ^ cmd_activity ^ freeze_cascade_seen);

endmodule
