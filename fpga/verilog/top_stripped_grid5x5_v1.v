// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_stripped_grid5x5_v1.v — STEP 1 of the points.md #103 measurement
// campaign: scale-up baseline. Plain #88-#97 stripped cells, NO wrapper
// (#99), NO cardinal command channel (#100) — exactly the same cell as
// #97's 3-cell fit, just 25 of them (matching the real 25-cells-per-zone
// count used everywhere else in this project), wired as a genuine 5x5
// GRID with real N/S/E/W neighbors, not a straight chain — so interior
// cells carry real 4-neighbor fan-in/out for Quartus to actually route
// around, unlike #97's simple 3-cell chain.
//
// Data flows a boustrophedon (snake) path through all 25 cells so every
// cell is genuinely exercised: row 0 west->east, down to row 1, row 1
// east->west, down to row 2, etc., ending at (4,4). Purely for real
// switching activity/routing pressure — the exact path doesn't matter for
// an area/Fmax check, only that every cell does real work and nothing
// gets optimized away as dead logic.
//
// WHAT THIS ANSWERS: whether #97's ~10 ALM/cell and ~397.61 MHz Fmax hold
// at a size where routing/fan-out genuinely matters, per #97's own flagged
// open item and #99/#103's agreed sequencing (scale up BEFORE adding the
// wrapper or cardinal command channel, so their costs can be measured as
// clean deltas against a real, larger baseline — not against #97's
// minimal 3-cell number).
`default_nettype none
`timescale 1ns / 1ps

module top_stripped_grid5x5_v1 (
    input  wire CLK_100M,   // 100 MHz board ref, PIN_E23
    output wire LED0_N,     // lit (low) whenever ANY of the 25 cells is NOT ready
    output wire LED1_N      // heartbeat
);

// ── Clock/reset — same convention as every other project on this board ──
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz fabric clock

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

localparam [9:0] TOPO_NOR = 10'h004;

// ── Snake routing_mask per grid position, boustrophedon path ────────────
// bit0=N(want_n) bit1=S(want_s) bit2=E(want_e) bit3=W(want_w) — matches
// unicell_stripped_v1.v's own field convention exactly.
function [5:0] snake_mask(input [2:0] r, input [2:0] c);
    begin
        if (r == 3'd4 && c == 3'd4)
            snake_mask = 6'b000000;              // chain end, last cell
        else if (r[0] == 1'b0) begin              // even row: moving EAST
            if (c < 3'd4) snake_mask = 6'b000100; // want_e
            else          snake_mask = 6'b000010; // c==4: want_s (drop to next row)
        end else begin                             // odd row: moving WEST
            if (c > 3'd0) snake_mask = 6'b001000; // want_w
            else          snake_mask = 6'b000010; // c==0: want_s
        end
    end
endfunction

// ── One-shot power-on autoconfig sweep — pulses each of the 25 cells'
// cfg_valid in turn (idx 0..24), then stops. Same stand-in convention as
// #95/#96 (loader_fsm_v3.v integration still deferred, per #88). ──
// ── One-hot walking shift register (fixed after the grid5x5 fit found
// the ORIGINAL magnitude-comparator scheme dominating the critical path
// -- points.md #105). Exactly one bit high at a time, shifting each
// cycle; each cell's cfg_valid wires DIRECTLY to its own bit, no
// comparison logic at all. Eliminates the 25-way equality-comparator
// fan-out entirely rather than relocating it. ──
reg [24:0] cfg_walk = 25'h1;   // bit 0 set at reset, walks up to bit 24 then stops
reg        cfg_active = 1'b1;
always @(posedge clk) begin
    if (rst) begin
        cfg_walk   <= 25'h1;
        cfg_active <= 1'b1;
    end else if (cfg_active) begin
        if (cfg_walk[24]) cfg_active <= 1'b0;
        else              cfg_walk   <= {cfg_walk[23:0], 1'b0};
    end
end

// ── Free-running stimulus into cell (0,0)'s north port — the grid's only
// external entry point, matching #95's convention. Every 256 cycles, a
// new counter-derived value. ──
reg [31:0] stim_cnt = 32'h0;
always @(posedge clk) if (!rst) stim_cnt <= stim_cnt + 32'h1;
wire        seed_pulse = (stim_cnt[7:0] == 8'h00);
wire [31:0] seed_data  = {stim_cnt[15:0], stim_cnt[31:16]};

// ── Per-cell signal arrays ────────────────────────────────────────────
wire [31:0] c_dout_n[0:4][0:4], c_dout_s[0:4][0:4], c_dout_e[0:4][0:4], c_dout_w[0:4][0:4];
wire        c_fire_n[0:4][0:4], c_fire_s[0:4][0:4], c_fire_e[0:4][0:4], c_fire_w[0:4][0:4];
wire        c_ready [0:4][0:4];
wire        c_ackn  [0:4][0:4], c_acks [0:4][0:4], c_acke [0:4][0:4], c_ackw [0:4][0:4];

genvar r, c;
generate
for (r = 0; r < 5; r = r + 1) begin : ROW
    for (c = 0; c < 5; c = c + 1) begin : COL

        wire        cell_cfg_valid = cfg_walk[r*5 + c];
        wire [127:0] cell_cfg_data;
        assign cell_cfg_data[127:70] = 58'h0;
        assign cell_cfg_data[69:64]  = snake_mask(r[2:0], c[2:0]);
        assign cell_cfg_data[63:10]  = 54'h0;
        assign cell_cfg_data[9:0]    = TOPO_NOR;

        unicell_stripped_v1 #(.CELL_ID({8'h0, r[3:0], c[3:0]})) CELL (
            .clk(clk), .rst(rst), .cfg_valid(cell_cfg_valid), .cfg_data(cell_cfg_data),

            .data_in_n((r==0) ? ((c==0) ? seed_data : 32'h0) : c_dout_s[r-1][c]),
            .arrived_n((r==0) ? ((c==0) ? seed_pulse : 1'b0) : c_fire_s[r-1][c]),
            .data_in_s((r==4) ? 32'h0 : c_dout_n[r+1][c]),
            .arrived_s((r==4) ? 1'b0  : c_fire_n[r+1][c]),
            .data_in_e((c==4) ? 32'h0 : c_dout_w[r][c+1]),
            .arrived_e((c==4) ? 1'b0  : c_fire_w[r][c+1]),
            .data_in_w((c==0) ? 32'h0 : c_dout_e[r][c-1]),
            .arrived_w((c==0) ? 1'b0  : c_fire_e[r][c-1]),

            .data_out_n(c_dout_n[r][c]), .fire_n(c_fire_n[r][c]),
            .data_out_s(c_dout_s[r][c]), .fire_s(c_fire_s[r][c]),
            .data_out_e(c_dout_e[r][c]), .fire_e(c_fire_e[r][c]),
            .data_out_w(c_dout_w[r][c]), .fire_w(c_fire_w[r][c]),

            .ready_out(c_ready[r][c]),
            .ready_in_n((r==0) ? 1'b1 : c_ready[r-1][c]),
            .ready_in_s((r==4) ? 1'b1 : c_ready[r+1][c]),
            .ready_in_e((c==4) ? 1'b1 : c_ready[r][c+1]),
            .ready_in_w((c==0) ? 1'b1 : c_ready[r][c-1]),

            .ack_out_n(c_ackn[r][c]), .ack_out_s(c_acks[r][c]),
            .ack_out_e(c_acke[r][c]), .ack_out_w(c_ackw[r][c]),
            .ack_in_n((r==0) ? 1'b0 : c_acks[r-1][c]),
            .ack_in_s((r==4) ? 1'b0 : c_ackn[r+1][c]),
            .ack_in_e((c==4) ? 1'b0 : c_ackw[r][c+1]),
            .ack_in_w((c==0) ? 1'b0 : c_acke[r][c-1]),

            .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
            .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),

            .freeze_in(1'b0),   // step 1 baseline — no freeze exercise, that's #92/#93's job


            .hold_in(1'b0),



            .fb_internal_in(1'b0),




            .a_reemit_in(1'b0),




            .a_update_in(1'b0),





            .a_self_update_in(1'b0),






            .program_in(1'b0),






            .program_done(),







            .prog_data_in(32'h0),







            .prog_arrived_in(1'b0),







            .prog_ack_out()
        );

    end
end
endgenerate

// ── All-ready reduction across all 25 cells ──────────────────────────
wire all_ready = c_ready[0][0] & c_ready[0][1] & c_ready[0][2] & c_ready[0][3] & c_ready[0][4]
                & c_ready[1][0] & c_ready[1][1] & c_ready[1][2] & c_ready[1][3] & c_ready[1][4]
                & c_ready[2][0] & c_ready[2][1] & c_ready[2][2] & c_ready[2][3] & c_ready[2][4]
                & c_ready[3][0] & c_ready[3][1] & c_ready[3][2] & c_ready[3][3] & c_ready[3][4]
                & c_ready[4][0] & c_ready[4][1] & c_ready[4][2] & c_ready[4][3] & c_ready[4][4];

assign LED0_N = all_ready;         // active-low: lit = something not ready
assign LED1_N = ~stim_cnt[23];     // slow heartbeat blink

endmodule
