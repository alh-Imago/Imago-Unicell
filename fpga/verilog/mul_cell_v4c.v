// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mul_cell_v4c.v — points.md #724: the "c" (carrier) variant of
// mul_cell_v4.v, built alongside it from the start (unlike the other
// 9 cores, whose _v4c variants were a later correction, #720) --
// Alan's own direct instruction to build both together this time.
// Same real reasoning as every other _v4c file's own header -- the
// carrier's whole design concept is to hold common functionality
// centrally, and this core's own internal 3-addon chain duplicates
// exactly what the carrier itself now provides once, shared.
// mul_cell_v4.v itself is UNCHANGED, still the real, proven,
// standalone core.
//
// Real, honest scope of this file's own changes from v4:
//   1. The internal addon chain is REMOVED entirely -- data_out_n/s/
//      e/w now come directly from out_buffer, the real computed
//      product's own low 32 bits.
//   2. addon_config (20 bits) is removed from cfg_data's own field
//      map, the register, and PROG_ID_ADDON_CONFIG. cfg_data KEEPS
//      its original 64-bit width; PROG_ID_COMPLETE stays at 3'd7,
//      addon_config's own old slot (3'd3) is simply unused now.
//   3. Same real config-off-shell reasoning as every other _v4c file
//      (confirmed correct the hard way in #723): this core's own
//      real config fields STAY registers, fed from the carrier's own
//      combinational incoming_config (the value about to be
//      committed), NOT the registered core_config -- a core that
//      latches once on its own cfg_valid needs the value that's about
//      to land, not the one that already did.
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   downstream_mask  — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  upstream_mask    — one-hot(s), N/S/E/W real + 2 reserved
//   [12]    reserved         — subtract_mode's own old home in
//                              adder_cell_v4c.v; never existed here at
//                              all (multiply has no equivalent)
//   [63:13] reserved         — 51 bits (addon_config's own old home,
//                              now genuinely free, plus the original
//                              31 bits of headroom)

`default_nettype none
`timescale 1ns / 1ps

module mul_cell_v4c #(
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

    // ── points.md #724: NO addon chain here at all — the carrier
    // already provides one, shared across whichever core is active. ──
    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    assign ready_out = effective_armed && !effective_freeze && !(a_arrived && data_valid);
    assign status_data_valid = data_valid;
    assign status_a_arrived  = a_arrived;

    // points.md #724: subtract_mode's own old PROG_ID slot (3'd2)
    // removed entirely (no real equivalent for multiply); addon_
    // config keeps its own old ID (3'd3) rather than renumbering.
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd0;
    localparam [2:0] PROG_ID_UPSTREAM_MASK   = 3'd1;
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
            pending_ack     <= 4'h0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[5:0];
            upstream_mask   <= cfg_data[11:6];
            a_arrived       <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_UPSTREAM_MASK:   upstream_mask   <= prog_word[5:0];
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
