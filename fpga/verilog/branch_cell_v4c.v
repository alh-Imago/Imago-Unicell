// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// branch_cell_v4c.v — points.md #720: the "c" (carrier) variant of
// branch_cell_v4.v. Same real reasoning as the other _v4c files' own
// headers -- the carrier's whole design concept is to hold common
// functionality centrally, and this core's own internal 3-addon chain
// duplicates exactly what the carrier itself now provides once,
// shared. branch_cell_v4.v itself is UNCHANGED, still the real,
// proven, standalone core.
//
// Real, honest scope of this file's own changes from v4:
//   1. The internal addon chain is REMOVED entirely -- data_out_n/s/
//      e/w now come directly from out_buffer.
//   2. addon_config (20 bits) is removed from cfg_data's own field
//      map, the register, and PROG_ID_ADDON_CONFIG. cfg_data KEEPS
//      its original 80-bit width; PROG_ID numbering stays exactly as
//      v4 has it (4'd14, addon_config's own old slot, is simply
//      unused now) rather than renumbering COMPLETE down -- a v4-vs-
//      v4c swap shouldn't also require re-deriving any other real
//      programming word.
//   3. Same real config-off-shell reasoning as every other _v4c file:
//      all real config fields STAY registers (this cell's own live-
//      programming channel needs them independently writable); the
//      real fix lives at the carrier's own shell level.
//
// cfg_data[79:0] field map (atomic boot-load path) -- IDENTICAL to
// v4's own except addon_config's own old home is now reserved:
//   [2:0]   upstream_dir        — single fixed direction, 0=N 1=S 2=E
//                                 3=W, real, reserved headroom at 4-7
//   [3]     value_source_low
//   [4]     value_source_equal
//   [5]     value_source_high
//   [12:6]  fixed_value_low     — 7-bit constant
//   [19:13] fixed_value_equal
//   [26:20] fixed_value_high
//   [27]    emit_low
//   [28]    emit_equal
//   [29]    emit_high
//   [35:30] route_low           — real, absolute one-hot(s), 4 real +
//                                 2 reserved
//   [41:36] route_equal
//   [47:42] route_high
//   [48]    rolling_mode
//   [79:49] reserved            — 31 bits (addon_config's own old
//                                 home, now genuinely free, plus the
//                                 original 11 bits of headroom)

`default_nettype none
`timescale 1ns / 1ps

module branch_cell_v4c #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    // points.md #617 point 5: real, explicit "active" bit.
    input  wire         active,

    input  wire         cfg_valid,
    input  wire [79:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    // ── points.md #617: real, targeted programming channel — real,
    // necessary 4-bit ID (16 real slots), not the 3-bit budget every
    // prior core used, see the header's own real reasoning. ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,

    output wire         status_data_valid
);

    // ── Real, static config fields, loaded on cfg_valid -- same real
    // shape as v1, widened per the header's own real reasoning. ──
    reg [2:0] upstream_dir = 3'h0;

    reg value_source_low = 1'b0, value_source_equal = 1'b0, value_source_high = 1'b0;
    reg [6:0] fixed_value_low = 7'h0, fixed_value_equal = 7'h0, fixed_value_high = 7'h0;
    reg emit_low = 1'b0, emit_equal = 1'b0, emit_high = 1'b0;
    reg [5:0] route_low = 6'h0, route_equal = 6'h0, route_high = 6'h0;
    reg rolling_mode = 1'b0;

    // ── The held reference, per #497's own real optimization —
    // unchanged from v1. ──
    reg [31:0] ref_value = 32'h0;
    reg        ref_valid = 1'b0;

    reg [31:0] out_buffer  = 32'h0;
    reg        data_valid  = 1'b0;
    reg [5:0]  active_route = 6'h0;
    reg [3:0]  pending_ack  = 4'h0;
    // points.md #617: real, staged-reconfiguration arm state, same
    // real semantics as #618-#623's own.
    reg        armed = 1'b0;

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    // ── Real, single fixed upstream direction -- decoded, not a mask,
    // unchanged from v1. Only values 0-3 are ever real (the widened
    // field's own values 4-7 are real, reserved headroom, matching
    // nano's own convention). ──
    wire sel_n = arrived_n && (upstream_dir == 3'd0);
    wire sel_s = arrived_s && (upstream_dir == 3'd1);
    wire sel_e = arrived_e && (upstream_dir == 3'd2);
    wire sel_w = arrived_w && (upstream_dir == 3'd3);
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    // ── Real, unchanged from v1: the found-not-assumed `consumed`
    // bug guard -- see this file's own real header for why it's
    // necessary. Real, necessary extension: both real capture paths
    // also gated on effective_armed/!program_in (#617's own real
    // "inactive = zero effect" principle, extended here to a
    // genuinely two-path core for the first time). ──
    reg consumed = 1'b0;

    wire capture_reference = any_upstream_arrived && !consumed && !ref_valid &&
                             !effective_freeze && effective_armed && !program_in;
    wire capture_compare   = any_upstream_arrived && !consumed && ref_valid && !data_valid &&
                             !effective_freeze && effective_armed && !program_in;
    wire capture_now       = capture_reference || capture_compare;

    assign ack_out_n = capture_now && sel_n;
    assign ack_out_s = capture_now && sel_s;
    assign ack_out_e = capture_now && sel_e;
    assign ack_out_w = capture_now && sel_w;

    // ── THE CORE — real, unchanged from v1: a genuine two's-complement
    // 3-way outcome. ──
    wire signed [31:0] signed_val = upstream_val;
    wire signed [31:0] signed_ref = ref_value;
    wire is_low   = (signed_val <  signed_ref);
    wire is_equal = (signed_val == signed_ref);
    wire is_high  = (signed_val >  signed_ref);

    wire outcome_value_source = (is_low  ? value_source_low  :
                                  is_equal ? value_source_equal :
                                             value_source_high);
    wire [6:0] outcome_fixed_value = (is_low  ? fixed_value_low  :
                                       is_equal ? fixed_value_equal :
                                                  fixed_value_high);
    wire outcome_emit = (is_low  ? emit_low  :
                          is_equal ? emit_equal :
                                     emit_high);
    wire [5:0] outcome_route = (is_low  ? route_low  :
                                 is_equal ? route_equal :
                                            route_high);

    wire [31:0] outcome_out_value = outcome_value_source ? {25'h0, outcome_fixed_value}
                                                           : upstream_val;

    wire want_to_offer = data_valid && !effective_freeze && effective_armed;
    wire targets_all_ready = (!active_route[0] || ready_in_n) &&
                             (!active_route[1] || ready_in_s) &&
                             (!active_route[2] || ready_in_e) &&
                             (!active_route[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (active_route[3:0] & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack       & ~ack_in_vec) :
                                                           pending_ack;
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    // ── points.md #720: NO addon chain here at all — the carrier
    // already provides one, shared across whichever core is active. ──
    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    assign ready_out = effective_armed && !effective_freeze && !data_valid && ref_valid;
    assign status_data_valid = data_valid;

    // ── points.md #617: real, targeted programming channel — real,
    // necessary 4-bit ID width (16 real slots), the first core where
    // FIELD COUNT (15 real fields) forced this rather than field
    // WIDTH. id at [23:20], word at [19:0] -- same real "ID sits
    // directly above its own data payload" principle every other
    // core's own layout already follows, just wider here. ──
    localparam [3:0] PROG_ID_UPSTREAM_DIR       = 4'd0;
    localparam [3:0] PROG_ID_VALUE_SOURCE_LOW   = 4'd1;
    localparam [3:0] PROG_ID_VALUE_SOURCE_EQUAL = 4'd2;
    localparam [3:0] PROG_ID_VALUE_SOURCE_HIGH  = 4'd3;
    localparam [3:0] PROG_ID_FIXED_VALUE_LOW    = 4'd4;
    localparam [3:0] PROG_ID_FIXED_VALUE_EQUAL  = 4'd5;
    localparam [3:0] PROG_ID_FIXED_VALUE_HIGH   = 4'd6;
    localparam [3:0] PROG_ID_EMIT_LOW           = 4'd7;
    localparam [3:0] PROG_ID_EMIT_EQUAL         = 4'd8;
    localparam [3:0] PROG_ID_EMIT_HIGH          = 4'd9;
    localparam [3:0] PROG_ID_ROUTE_LOW          = 4'd10;
    localparam [3:0] PROG_ID_ROUTE_EQUAL        = 4'd11;
    localparam [3:0] PROG_ID_ROUTE_HIGH         = 4'd12;
    localparam [3:0] PROG_ID_ROLLING_MODE       = 4'd13;
    localparam [3:0] PROG_ID_COMPLETE           = 4'd15;

    wire prog_any_arrived = prog_arrived_in_n | prog_arrived_in_s | prog_arrived_in_e | prog_arrived_in_w;
    wire prog_sel_n = prog_arrived_in_n;
    wire prog_sel_s = prog_arrived_in_s && !prog_arrived_in_n;
    wire prog_sel_e = prog_arrived_in_e && !prog_arrived_in_n && !prog_arrived_in_s;
    wire prog_sel_w = prog_arrived_in_w && !prog_arrived_in_n && !prog_arrived_in_s && !prog_arrived_in_e;
    wire [31:0] prog_data_val = prog_sel_n ? prog_data_in_n :
                                prog_sel_s ? prog_data_in_s :
                                prog_sel_e ? prog_data_in_e :
                                             prog_data_in_w;
    wire [3:0]  prog_id   = prog_data_val[23:20];
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
            upstream_dir        <= 3'h0;
            value_source_low    <= 1'b0; value_source_equal <= 1'b0; value_source_high <= 1'b0;
            fixed_value_low     <= 7'h0; fixed_value_equal  <= 7'h0; fixed_value_high  <= 7'h0;
            emit_low            <= 1'b0; emit_equal         <= 1'b0; emit_high         <= 1'b0;
            route_low           <= 6'h0; route_equal        <= 6'h0; route_high        <= 6'h0;
            rolling_mode        <= 1'b0;
            ref_value            <= 32'h0;
            ref_valid            <= 1'b0;
            out_buffer           <= 32'h0;
            data_valid           <= 1'b0;
            active_route         <= 6'h0;
            pending_ack          <= 4'h0;
            consumed             <= 1'b0;
            armed                <= 1'b0;
            program_done_r       <= 1'b0;
        end else if (cfg_valid) begin
            upstream_dir        <= cfg_data[2:0];
            value_source_low    <= cfg_data[3];
            value_source_equal  <= cfg_data[4];
            value_source_high   <= cfg_data[5];
            fixed_value_low     <= cfg_data[12:6];
            fixed_value_equal   <= cfg_data[19:13];
            fixed_value_high    <= cfg_data[26:20];
            emit_low             <= cfg_data[27];
            emit_equal           <= cfg_data[28];
            emit_high            <= cfg_data[29];
            route_low            <= cfg_data[35:30];
            route_equal          <= cfg_data[41:36];
            route_high           <= cfg_data[47:42];
            rolling_mode         <= cfg_data[48];
            // ── Real release, unchanged from v1: reprogramming
            // discards the held reference and any in-flight offer --
            // see v1's own real, explicitly-flagged judgment call. ──
            ref_value             <= 32'h0;
            ref_valid             <= 1'b0;
            data_valid            <= 1'b0;
            pending_ack           <= 4'h0;
            consumed              <= 1'b0;
            armed                 <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_UPSTREAM_DIR:       upstream_dir       <= prog_word[2:0];
                PROG_ID_VALUE_SOURCE_LOW:   value_source_low   <= prog_word[0];
                PROG_ID_VALUE_SOURCE_EQUAL: value_source_equal <= prog_word[0];
                PROG_ID_VALUE_SOURCE_HIGH:  value_source_high  <= prog_word[0];
                PROG_ID_FIXED_VALUE_LOW:    fixed_value_low    <= prog_word[6:0];
                PROG_ID_FIXED_VALUE_EQUAL:  fixed_value_equal  <= prog_word[6:0];
                PROG_ID_FIXED_VALUE_HIGH:   fixed_value_high   <= prog_word[6:0];
                PROG_ID_EMIT_LOW:           emit_low           <= prog_word[0];
                PROG_ID_EMIT_EQUAL:         emit_equal         <= prog_word[0];
                PROG_ID_EMIT_HIGH:          emit_high          <= prog_word[0];
                PROG_ID_ROUTE_LOW:          route_low          <= prog_word[5:0];
                PROG_ID_ROUTE_EQUAL:        route_equal        <= prog_word[5:0];
                PROG_ID_ROUTE_HIGH:         route_high         <= prog_word[5:0];
                PROG_ID_ROLLING_MODE:       rolling_mode       <= prog_word[0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (capture_reference) begin
                ref_value <= upstream_val;
                ref_valid <= 1'b1;
            end else if (capture_compare) begin
                if (outcome_emit) begin
                    out_buffer   <= outcome_out_value;
                    active_route <= outcome_route;
                    data_valid   <= 1'b1;
                end
                if (rolling_mode) begin
                    ref_value <= upstream_val;
                end
            end

            if (capture_now) begin
                consumed <= 1'b1;
            end else if (!any_upstream_arrived) begin
                consumed <= 1'b0;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end

            pending_ack <= next_pending_ack;

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
