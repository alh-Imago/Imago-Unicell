// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// branch_cell_v4.v — points.md #617/#624: the SIXTH real "unified
// carrier" core, and the most structurally complex of the six built
// so far. Real core logic CLONED from branch_cell_v1.v unchanged,
// INCLUDING its own real, documented history, faithfully preserved:
//   - the real held-reference two-phase capture (#497): the first
//     real arrival becomes a held comparison reference (never itself
//     compared or drained); every later arrival is compared against
//     it and routed per a real 3-outcome (<, =, >) table, each with
//     independently configured value source, emit/suppress, and
//     fan-out routing.
//   - the real, found-not-assumed `consumed` bug guard: without it, a
//     single physical arrival would be captured TWICE (once as the
//     reference, once immediately compared against itself) since this
//     core's two capture paths have DIFFERENT guards, unlike every
//     other core's single shared one.
//   - real ROLLING MODE (#497-followup): the just-compared value
//     becomes the new held reference regardless of whether that
//     outcome emitted, turning static baseline comparison into real
//     drift detection.
//
// Same real shell additions as #618-#623, per Alan's own precise
// 5-point breakdown (#617):
//   1. programming: real, targeted program_in/PROG_ID channel -- REAL,
//      NECESSARY ADAPTATION found here, not assumed: this core has 15
//      real distinct fields, more than the 3-bit ID (7 real slots)
//      every prior core's own budget supported. Widened to a real
//      4-bit ID (16 real slots, 15 fields + COMPLETE, a clean, exact
//      fit with zero spare) -- the first real case where FIELD COUNT,
//      not field WIDTH, forced the protocol to adapt.
//   2. shift/nibble_mask/lane: the same real, already-proven 3-addon
//      chain, applied to the offered out_buffer.
//   3. 6-way cardinality: real field-width headroom, applied here to
//      BOTH the real absolute route masks (route_low/equal/high,
//      4->6 bits) AND, a real, deliberate first, `upstream_dir`
//      itself (2->3 bits) -- a single fixed-direction VALUE, not a
//      mask, but widened for the same real reason (future 3D
//      headroom, #604), since a value field needs the same reserved
//      room a mask field does if a 6-way substrate is ever built.
//   4. ack all around: the programming channel's own real ack.
//   5. `active`: the same real, explicit port -- gates BOTH real
//      capture paths (`capture_reference`/`capture_compare`) and the
//      offer side, so an inactive cell neither silently captures a
//      new reference nor silently compares against an old one.
//
// REAL, NECESSARY WIDTH CHANGE: this core's own real field total
// (69 bits with the widened route/upstream_dir fields + addon_config)
// exceeds the original 64-bit cfg_data -- widened to 80 bits, same
// real precedent as `ram_cell_v4.v` (#619), 11 bits of real reserved
// headroom.
//
// REAL, HONEST SCOPE, matching #618-#623's own stated deferrals:
// `is_command_cell` mode NOT included (parked as a possible 9th-core
// question).
//
// cfg_data[79:0] field map (atomic boot-load path):
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
//   [68:49] addon_config        — 20 bits, SAME real layout as
//                                 unicell_super_v3.v's own real addon_config
//   [79:69] reserved            — 11 bits, real, honest headroom
`default_nettype none
`timescale 1ns / 1ps

module branch_cell_v4 #(
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
    reg [19:0] addon_config = 20'h0;

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

    // ── points.md #617: the real, three-addon chain, applied to the
    // offered out_buffer, wired identically to #618-#623's own. ──
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
    localparam [3:0] PROG_ID_ADDON_CONFIG       = 4'd14;
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
            addon_config        <= 20'h0;
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
            addon_config         <= cfg_data[68:49];
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
                PROG_ID_ADDON_CONFIG:       addon_config       <= prog_word[19:0];
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
