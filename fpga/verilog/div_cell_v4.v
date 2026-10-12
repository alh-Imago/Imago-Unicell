// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// div_cell_v4.v — ledger #1073: the division core for the CARDINAL (v4) family, cloned from the shape of
// adder_cell_v4.v (two-stage A/B capture, pending_ack offering, programming channel, addon chain, active/freeze)
// with ONLY the arithmetic swapped: unsigned restoring long division, STEPS quotient bits per clock, run as a
// loop. The same arithmetic as sub/verilog/div_cell_v4sa.v (flex) and div_cell_v4s.v (sub).
//
// OPERAND ROLES BY ARRIVAL ORDER, like subtract: the FIRST operand to arrive is the DIVIDEND (a_reg), the
// SECOND is the DIVISOR. The compiler must make the dividend arrive first (exactly as for adder_cell_v4's
// subtract mode). Not commutative.
//
// TIMING IS DATA-DRIVEN. After the divisor arrives the cell is BUSY for ceil(32 / STEPS) clocks, offers nothing and
// takes no divisor meanwhile (ready_out is low while an operand is held and the cell is busy); then it offers the
// result like any other core. Nothing outside needs to know the count: a longer cell only delays what waits on it.
// freeze_in holds the loop (nothing steps while frozen).
//
// RESULTS (unsigned): quotient = A / B, remainder = A % B. Division by zero needs no special case: the quotient
// comes out all ones and the remainder equals the dividend (the rule the LaTeX front end uses).
//
// ONE OUTPUT PORT SET, TWO PHASES (this family has no second port; this is the #1036 framework, as the adder's
// carry word and mul's high word):
//   - second_output = 0: only the first word is offered (by default the quotient).
//   - second_output = 1: after the first word has been fully acknowledged, the second word is offered; by
//     second_downstream_mask if non-zero (a different edge may carry it), otherwise by downstream_mask. No new
//     operand is taken until both words have left.
//   - rem_primary = 1: the REMAINDER is the first word and the QUOTIENT the second (so x mod y alone is a
//     single-word result with second_output = 0).
//
// cfg_data[63:0] field map (the adder's layout, bit [12] re-purposed):
//   [5:0]   downstream_mask
//   [11:6]  upstream_mask
//   [12]    rem_primary      — 0 = quotient first, 1 = remainder first (the adder's subtract_mode slot)
//   [32:13] addon_config     — 20 bits, same layout as every _v4 core
//   [33]    second_output
//   [39:34] second_downstream_mask (0 = same faces as downstream_mask)
//   [63:40] reserved
// PROG_IDs (the adder's numbering): 0 down, 1 up, 2 rem_primary, 3 addon, 4 second_output, 5 second_downstream_mask, 7 COMPLETE.
`default_nettype none
`timescale 1ns / 1ps

module div_cell_v4 #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        STEPS   = 1        // quotient bits per clock, 1..32
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

    output wire         status_data_valid,   // a result is held (not counting the busy loop)
    output wire         status_a_arrived     // the dividend is captured, awaiting the divisor
);

    reg [31:0] a_reg           = 32'h0;
    reg        a_arrived       = 1'b0;
    reg [31:0] out_buffer      = 32'h0;
    reg        data_valid      = 1'b0;
    reg [5:0]  downstream_mask = 6'h0;
    reg [5:0]  upstream_mask   = 6'h0;
    reg        rem_primary     = 1'b0;
    reg        second_output   = 1'b0;
    reg [5:0]  second_downstream_mask = 6'h0;
    reg [31:0] captured_second = 32'h0;
    reg        delivering_second = 1'b0;
    reg        phase1_offered  = 1'b0;
    reg [19:0] addon_config    = 20'h0;
    reg [3:0]  pending_ack     = 4'h0;
    reg        armed           = 1'b0;

    // the division loop's own state
    reg        busy            = 1'b0;
    reg [31:0] d_reg           = 32'h0;
    reg [31:0] r_reg           = 32'h0;
    reg [31:0] q_reg           = 32'h0;     // starts as the dividend; its bits shift out at the top as quotient bits shift in
    reg [5:0]  remaining       = 6'd0;

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

    // while the loop runs (or a two-word result is still leaving) no new operand is taken
    wire block_for_second = second_output && (data_valid || busy);
    wire capture_now = any_upstream_arrived && !a_arrived && !effective_freeze && !block_for_second &&
                       effective_armed && !program_in;
    wire can_fire = any_upstream_arrived && a_arrived && !data_valid && !busy && !effective_freeze &&
                    effective_armed && !program_in;

    assign ack_out_n = (capture_now || can_fire) && sel_n;
    assign ack_out_s = (capture_now || can_fire) && sel_s;
    assign ack_out_e = (capture_now || can_fire) && sel_e;
    assign ack_out_w = (capture_now || can_fire) && sel_w;

    // ── the arithmetic: STEPS restoring-division steps in one clock; a step is skipped once the bits are used up ──
    reg [31:0] nR, nQ;
    reg [32:0] diff;
    integer    i;
    always @* begin
        nR = r_reg;
        nQ = q_reg;
        diff = 33'h0;
        for (i = 0; i < STEPS; i = i + 1) begin
            if (i < remaining) begin
                nR   = {nR[30:0], nQ[31]};
                nQ   = {nQ[30:0], 1'b0};
                diff = {1'b0, nR} - {1'b0, d_reg};
                if (!diff[32]) begin
                    nR    = diff[31:0];
                    nQ[0] = 1'b1;
                end
            end
        end
    end
    wire last_clock = (remaining <= STEPS);
    wire step_now   = busy && !effective_freeze && effective_armed && !program_in;

    // ── downstream offering — the adder's, unchanged ──
    wire want_to_offer = data_valid && !effective_freeze && effective_armed;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && !phase1_offered && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask[3:0] & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);
    wire start_second_phase = offer_draining && second_output && !delivering_second;
    wire genuinely_done     = offer_draining && !start_second_phase;

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

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

    assign ready_out = effective_armed && !effective_freeze && !(a_arrived && (data_valid || busy)) && !block_for_second;
    assign status_data_valid = data_valid;
    assign status_a_arrived  = a_arrived;

    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd0;
    localparam [2:0] PROG_ID_UPSTREAM_MASK   = 3'd1;
    localparam [2:0] PROG_ID_REM_PRIMARY     = 3'd2;   // the adder's subtract_mode slot
    localparam [2:0] PROG_ID_ADDON_CONFIG    = 3'd3;
    localparam [2:0] PROG_ID_SECOND_OUTPUT   = 3'd4;
    localparam [2:0] PROG_ID_SECOND_DOWNSTREAM_MASK = 3'd5;
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
            rem_primary     <= 1'b0;
            second_output   <= 1'b0;
            second_downstream_mask <= 6'h0;
            captured_second <= 32'h0;
            delivering_second <= 1'b0;
            phase1_offered  <= 1'b0;
            addon_config    <= 20'h0;
            pending_ack     <= 4'h0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
            busy            <= 1'b0;
            remaining       <= 6'd0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[5:0];
            upstream_mask   <= cfg_data[11:6];
            rem_primary     <= cfg_data[12];
            second_output   <= cfg_data[33];
            second_downstream_mask <= cfg_data[39:34];
            delivering_second <= 1'b0;
            phase1_offered  <= 1'b0;
            addon_config    <= cfg_data[32:13];
            a_arrived       <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            busy            <= 1'b0;                  // a reconfigure discards an operation in flight
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_UPSTREAM_MASK:   upstream_mask   <= prog_word[5:0];
                PROG_ID_REM_PRIMARY:     rem_primary     <= prog_word[0];
                PROG_ID_SECOND_OUTPUT:   second_output   <= prog_word[0];
                PROG_ID_SECOND_DOWNSTREAM_MASK: second_downstream_mask <= prog_word[5:0];
                PROG_ID_ADDON_CONFIG:    addon_config    <= prog_word[19:0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (can_fire) begin
                // the divisor is on the wire NOW (it is being acknowledged this clock): take it, start the loop
                d_reg     <= upstream_val;
                q_reg     <= a_reg;
                r_reg     <= 32'h0;
                remaining <= 6'd32;
                busy      <= 1'b1;
                delivering_second <= 1'b0;
                phase1_offered    <= 1'b0;
                a_arrived <= 1'b0;
            end else if (capture_now) begin
                a_reg     <= upstream_val;
                a_arrived <= 1'b1;
            end

            if (step_now) begin
                r_reg <= nR;
                q_reg <= nQ;
                if (last_clock) begin
                    busy            <= 1'b0;
                    data_valid      <= 1'b1;
                    out_buffer      <= rem_primary ? nR : nQ;
                    captured_second <= rem_primary ? nQ : nR;
                    remaining       <= 6'd0;
                end else begin
                    remaining <= remaining - STEPS;
                end
            end

            if (start_second_phase) begin
                out_buffer        <= captured_second;
                delivering_second <= 1'b1;
            end else if (genuinely_done) begin
                data_valid <= 1'b0;
            end
            if (any_fire) phase1_offered <= 1'b1;
            // a phase transition re-arms pending_ack this very cycle (no window where it reads 0 while data_valid is still high)
            pending_ack <= start_second_phase ? ((|second_downstream_mask[3:0]) ? second_downstream_mask[3:0] : downstream_mask[3:0]) : next_pending_ack;

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
