// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// latch_cell_v3.v — points.md #587: the same real change as compare_
// cell_v3.v (#584), applied to the next-smallest real core (8.5 real
// ALM at N=1, #574 -- the smallest of all 8). Config fields (set_dir/
// clear_dir/downstream_mask/toggle_dir) no longer re-latched into a
// private local copy on cfg_valid -- read straight off a continuously-
// valid cfg_data input instead (the shell's own core_config, stable
// for as long as this core stays selected). Genuine runtime state
// (latched/out_buffer/data_valid/pending_ack) UNCHANGED from v1 --
// still real per-core registers, same real semantics, including v1's
// own real quirk that data_valid goes live immediately on cfg_valid
// (unlike compare, which starts empty) -- preserved exactly.
//
// Same real safety reasoning as compare_cell_v3.v's own header:
// arrived_n/s/e/w are gated by the shell's own sel_active_latch at
// the instantiation site (unchanged), so a misread config value from
// another core's own bit pattern (shared budget, reused positions)
// can never trigger a genuine set/clear/toggle while this core is
// deselected.
//
// cfg_data[63:0] field map — UNCHANGED from v1:
//   [3:0]   set_dir           — one-hot direction, arrivals here latch to 1
//   [7:4]   clear_dir         — one-hot direction, arrivals here clear to 0
//   [11:8]  downstream_mask   — where the current latched value is offered
//   [15:12] toggle_dir        — one-hot direction, arrivals here flip the
//                                current state
//   [63:16] reserved
`default_nettype none
`timescale 1ns / 1ps

module latch_cell_v3 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,   // points.md #587: must be CONTINUOUSLY
                                    // valid (wired to the shell's own
                                    // core_config), matching compare_
                                    // cell_v3.v's own real precondition.

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    output wire         ready_out,
    output wire         status_latched
);

    // ── points.md #587: THE real change -- config fields read straight
    // off the continuously-valid cfg_data input, no local register. ──
    wire [3:0] set_dir         = cfg_data[3:0];
    wire [3:0] clear_dir       = cfg_data[7:4];
    wire [3:0] downstream_mask = cfg_data[11:8];
    wire [3:0] toggle_dir      = cfg_data[15:12];

    // ── UNCHANGED from v1: genuine runtime state ──
    reg latched    = 1'b0;
    reg out_buffer = 1'b0;
    reg data_valid = 1'b0;
    reg [3:0] pending_ack = 4'h0;

    wire effective_freeze = freeze_in;

    wire sel_set_n = arrived_n && set_dir[0];
    wire sel_set_s = arrived_s && set_dir[1];
    wire sel_set_e = arrived_e && set_dir[2];
    wire sel_set_w = arrived_w && set_dir[3];
    wire set_arrived_value = (sel_set_n ? data_in_n[0] : 1'b0) |
                             (sel_set_s ? data_in_s[0] : 1'b0) |
                             (sel_set_e ? data_in_e[0] : 1'b0) |
                             (sel_set_w ? data_in_w[0] : 1'b0);
    wire capture_set = (sel_set_n | sel_set_s | sel_set_e | sel_set_w) && !effective_freeze && set_arrived_value;

    wire sel_clr_n = arrived_n && clear_dir[0];
    wire sel_clr_s = arrived_s && clear_dir[1];
    wire sel_clr_e = arrived_e && clear_dir[2];
    wire sel_clr_w = arrived_w && clear_dir[3];
    wire capture_clr = (sel_clr_n | sel_clr_s | sel_clr_e | sel_clr_w) && !effective_freeze;

    wire sel_tog_n = arrived_n && toggle_dir[0];
    wire sel_tog_s = arrived_s && toggle_dir[1];
    wire sel_tog_e = arrived_e && toggle_dir[2];
    wire sel_tog_w = arrived_w && toggle_dir[3];
    wire capture_tog = (sel_tog_n | sel_tog_s | sel_tog_e | sel_tog_w) && !effective_freeze;

    assign ack_out_n = (sel_set_n || sel_clr_n || sel_tog_n) && !effective_freeze;
    assign ack_out_s = (sel_set_s || sel_clr_s || sel_tog_s) && !effective_freeze;
    assign ack_out_e = (sel_set_e || sel_clr_e || sel_tog_e) && !effective_freeze;
    assign ack_out_w = (sel_set_w || sel_clr_w || sel_tog_w) && !effective_freeze;

    // CLEAR takes priority over SET, TOGGLE lowest — unchanged.
    wire next_latched = capture_clr ? 1'b0 : capture_set ? 1'b1 : capture_tog ? ~latched : latched;

    wire want_to_offer = data_valid && !effective_freeze;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = {31'h0, out_buffer};
    assign data_out_s = {31'h0, out_buffer};
    assign data_out_e = {31'h0, out_buffer};
    assign data_out_w = {31'h0, out_buffer};

    assign status_latched = latched;
    assign ready_out = !effective_freeze;

    // ── points.md #587: the reset/reload block is now ONLY about
    // genuine runtime state -- no config fields left to latch here. ──
    always @(posedge clk) begin
        if (rst) begin
            latched         <= 1'b0;
            out_buffer      <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            latched         <= 1'b0;
            out_buffer      <= 1'b0;
            data_valid      <= 1'b1;   // UNCHANGED from v1 — live from the
                                        // first cycle after config.
            pending_ack     <= 4'h0;
        end else begin
            if (capture_set || capture_clr || capture_tog) begin
                latched <= next_latched;
            end

            if (pending_ack == 4'h0) begin
                out_buffer <= next_latched;
            end

            pending_ack <= next_pending_ack;
        end
    end

endmodule
