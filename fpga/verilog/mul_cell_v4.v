// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mul_cell_v4.v — points.md #724: a real, new "unified carrier" core,
// the 10th, built directly on adder_cell_v4.v's own proven shape
// (same two-stage A/B capture, same shell richness -- programming
// channel, addon chain, 6-way cardinality headroom, active/freeze).
// The one real, substantive difference: the core arithmetic itself is
// bitwise_multiplier_32bit.v (#724, promoted from a contributed,
// already-iverilog-verified combinational design in docs/stripped-
// cell/design-notes/future-core-candidates/), not adder_v1.v.
//
// Real, honest scope decisions, stated plainly:
//   - subtract_mode has no real equivalent for multiply and is
//     REMOVED entirely (not left as a dead field) -- this core always
//     computes A*B, nothing else. Its own old cfg_data bit [12] is
//     genuinely reserved now.
//   - LLVM's own `mul` on i32 truncates to the low 32 bits (standard
//     two's-complement wraparound, the same real semantic `add`/`sub`
//     already use here) -- this core offers Product[31:0] as its real
//     result. The high 32 bits (needed for a real, future `mulh`/
//     `umulh`) are computed by the real combinational multiplier but
//     not offered anywhere in THIS core; a future core could tap the
//     same real multiplier for that half without duplicating the
//     multiply itself.
//   - The real multiplier itself is purely combinational (zero clock
//     cycles of latency, confirmed directly in its own real
//     iverilog-verified form before this promotion) -- capturing B
//     and firing the real product happens on the exact same real
//     two-stage cycle count as add/sub/every other arithmetic core
//     here, no extra latency introduced.
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   downstream_mask  — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  upstream_mask    — one-hot(s), N/S/E/W real + 2 reserved
//   [12]    reserved         — subtract_mode's own old home, no real
//                              equivalent for multiply
//   [32:13] addon_config     — 20 bits, SAME real layout as every
//                              other _v4 core's own addon chain
//   [63:33] reserved
`default_nettype none
`timescale 1ns / 1ps

module mul_cell_v4 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         active,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,

    output wire         status_data_valid,
    output wire         status_a_arrived
);

    reg [31:0] a_reg           = 32'h0;
    reg        a_arrived       = 1'b0;
    reg [31:0] out_buffer      = 32'h0;
    reg        data_valid      = 1'b0;
    reg [5:0]  downstream_mask = 6'h0;
    reg [5:0]  upstream_mask   = 6'h0;
    reg [19:0] addon_config    = 20'h0;
    reg [3:0]  pending_ack     = 4'h0;
    reg        armed           = 1'b0;

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    wire capture_now = any_upstream_arrived && !a_arrived && !effective_freeze &&
                       effective_armed && !program_in;
    wire can_fire = any_upstream_arrived && a_arrived && !data_valid && !effective_freeze &&
                    effective_armed && !program_in;

    assign ack_out_n = (capture_now || can_fire) && sel_n;
    assign ack_out_s = (capture_now || can_fire) && sel_s;
    assign ack_out_e = (capture_now || can_fire) && sel_e;
    assign ack_out_w = (capture_now || can_fire) && sel_w;

    // ── The real arithmetic — the one real, substantive difference
    // from adder_cell_v4.v. Purely combinational, zero clock cycles
    // of latency (confirmed directly before this promotion). Only the
    // low 32 bits are offered here, matching LLVM's own real `mul`
    // truncation semantics. ──
    wire [63:0] mul_product;
    bitwise_multiplier_32bit MUL (
        .A(a_reg), .B(upstream_val), .Product(mul_product)
    );
    wire [31:0] mul_result = mul_product[31:0];

    wire want_to_offer = data_valid && !effective_freeze && effective_armed;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask[3:0] & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    // ── points.md #617's own real, three-addon chain, wired exactly
    // as every other _v4 core's own -- same order, same 20-bit
    // addon_config layout, reused verbatim. ──
    wire [31:0] after_mask, after_shiftlane, addon_out;
    nibble_mask_addon_v1 ADDON_NM (
        .mask_en(addon_config[8]), .nibble_mask(addon_config[7:0]),
        .data_in(out_buffer), .data_out(after_mask)
    );
    shift_lane_addon_v1 ADDON_SL (
        .direction(addon_config[15]), .shift_en(addon_config[14]),
        .shift_amt(addon_config[13:9]), .lane_cut(addon_config[18:16]),
        .data_in(after_mask), .data_out(after_shiftlane)
    );
    invert_addon_v1 ADDON_INV (
        .invert_en(addon_config[19]),
        .data_in(after_shiftlane), .data_out(addon_out)
    );

    assign data_out_n = addon_out;
    assign data_out_s = addon_out;
    assign data_out_e = addon_out;
    assign data_out_w = addon_out;

    assign ready_out = effective_armed && !effective_freeze && !(a_arrived && data_valid);
    assign status_data_valid = data_valid;
    assign status_a_arrived  = a_arrived;

    // points.md #724: subtract_mode's own old PROG_ID slot (3'd2)
    // removed entirely (no real equivalent for multiply); addon_
    // config keeps its own old ID (3'd3) rather than renumbering.
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd0;
    localparam [2:0] PROG_ID_UPSTREAM_MASK   = 3'd1;
    localparam [2:0] PROG_ID_ADDON_CONFIG    = 3'd3;
    localparam [2:0] PROG_ID_COMPLETE        = 3'd7;

    wire prog_any_arrived = prog_arrived_in_n | prog_arrived_in_s | prog_arrived_in_e | prog_arrived_in_w;
    wire prog_sel_n = prog_arrived_in_n;
    wire prog_sel_s = prog_arrived_in_s && !prog_arrived_in_n;
    wire prog_sel_e = prog_arrived_in_e && !prog_arrived_in_n && !prog_arrived_in_s;
    wire prog_sel_w = prog_arrived_in_w && !prog_arrived_in_n && !prog_arrived_in_s && !prog_arrived_in_e;
    wire [31:0] prog_data_val = prog_sel_n ? prog_data_in_n :
                                prog_sel_s ? prog_data_in_s :
                                prog_sel_e ? prog_data_in_e :
                                             prog_data_in_w;
    wire [2:0]  prog_id   = prog_data_val[22:20];
    wire [19:0] prog_word = prog_data_val[19:0];

    wire programming_active = program_in && active && prog_any_arrived;
    assign program_done = program_done_r;
    reg   program_done_r = 1'b0;

    assign prog_ack_out_n = programming_active && prog_sel_n;
    assign prog_ack_out_s = programming_active && prog_sel_s;
    assign prog_ack_out_e = programming_active && prog_sel_e;
    assign prog_ack_out_w = programming_active && prog_sel_w;

    always @(posedge clk) begin
        if (rst) begin
            a_reg           <= 32'h0;
            a_arrived       <= 1'b0;
            out_buffer      <= 32'h0;
            data_valid      <= 1'b0;
            downstream_mask <= 6'h0;
            upstream_mask   <= 6'h0;
            addon_config    <= 20'h0;
            pending_ack     <= 4'h0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[5:0];
            upstream_mask   <= cfg_data[11:6];
            addon_config    <= cfg_data[32:13];
            a_arrived       <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_UPSTREAM_MASK:   upstream_mask   <= prog_word[5:0];
                PROG_ID_ADDON_CONFIG:    addon_config    <= prog_word[19:0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (can_fire) begin
                out_buffer <= mul_result;
                data_valid <= 1'b1;
                a_arrived  <= 1'b0;
            end else if (capture_now) begin
                a_reg     <= upstream_val;
                a_arrived <= 1'b1;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end
            pending_ack <= next_pending_ack;

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
