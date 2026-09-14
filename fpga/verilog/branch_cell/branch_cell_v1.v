// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// branch_cell_v1.v — first real RTL draft of the branch/comparator
// core, per points.md #491-#497's fully-settled design. DRAFT — shape
// confirmed in a real, extended design conversation with Alan
// (#491-#497), NOT yet silicon-measured or Quartus-attempted. Only
// iverilog sim so far.
//
// WHAT THIS IS: a real, genuine 3-outcome (<, =, >) branch, per
// Alan's own direct request ("conditional branching with teeth") --
// each outcome independently selects (A) which value to emit (the
// real supplied value, relayed, or a fixed constant), (C) whether to
// emit at all (real, genuine suppression -- the qualitatively new
// capability the existing `compare_cell_v1.v` doesn't have; that core
// always emits something, even a real 0), and (D) up to 3 real
// cardinal directions to fan out to. Deliberately a NEW core, not an
// extension of `compare_cell_v1.v` in place -- the field shape and
// internal state machine are both genuinely different (held-reference
// two-phase capture below has no equivalent in the stateless
// comparator).
//
// THE HELD-REFERENCE MECHANISM (Alan's own real optimization, #497,
// closing the real 42-bit `core_config` budget problem): the
// comparison reference is NOT a config field. It is the FIRST value
// captured after programming (or after a release), held indefinitely
// in `ref_value`/`ref_valid` -- never drained, never compared against
// anything itself. Every LATER arrival is compared against the held
// reference and handled per the A/C/D table below. Release happens by
// REPROGRAMMING the cell (`cfg_valid`) -- reusing a mechanism every
// core already has, no new port.
//
// A REAL, EXPLICIT JUDGMENT CALL, flagged plainly rather than buried:
// on reprogram, this cell discards the held reference WITHOUT trying
// to flush/emit it first -- matching EVERY other core's own real,
// established convention (`compare_cell_v1.v`/`adder_cell_v1.v`/etc.
// all simply clear `data_valid`/captured state on `cfg_valid`, they
// never attempt to drain in-flight state through the normal offer
// path first). Alan's own design conversation described release as
// letting the old value "pass normally" -- read here as "the NEXT
// arriving values pass through the normal capture path again (the
// very next one becomes the new held reference)," not as "the OLD
// held value gets actively emitted somewhere." If that reading is
// wrong, this is the first real place to correct once reviewed --
// stated as an assumption, not hidden as a settled fact.
//
// cfg_data field map, within this core's own native 64-bit cfg_data
// bus (same "each core owns bit 0 of its own space" convention every
// other core uses, per `root_definition.json`'s own real, confirmed
// layout) -- 41 of 64 bits used, matching #497's own final table
// EXACTLY:
//   [1:0]   upstream_dir        — single fixed direction, 0=N 1=S 2=E 3=W
//                                 (NOT a one-hot mask like every other
//                                 core's upstream_mask -- #494's own real
//                                 constraint: in+N only has one meaning
//                                 if there's exactly one real "in")
//   [2]     value_source_low    — 0=relay real supplied value, 1=fixed
//   [3]     value_source_equal  — same, for the "=" outcome
//   [4]     value_source_high   — same, for the ">" outcome
//   [11:5]  fixed_value_low     — 7-bit constant, used only if [2]=1
//   [18:12] fixed_value_equal   — 7-bit constant, used only if [3]=1
//   [25:19] fixed_value_high    — 7-bit constant, used only if [4]=1
//   [26]    emit_low            — 0=suppress (real, genuine silence),1=emit
//   [27]    emit_equal          — same, for "="
//   [28]    emit_high           — same, for ">"
//   [32:29] route_low           — real, ABSOLUTE one-hot(s) direction
//                                 mask (real fan-out, up to all 4 bits),
//                                 RESOLVED FROM in+1/in+2/in+3 AT
//                                 ICM-PROGRAMMING TIME by the compiler/
//                                 Designer (#494) -- this field is
//                                 already-absolute by the time it
//                                 reaches this register, this core does
//                                 no direction arithmetic of its own
//   [36:33] route_equal         — same, for "="
//   [40:37] route_high          — same, for ">"
//   [41]    rolling_mode        — real, #497-followup capability (per
//                                 Alan's own direct request): 0=static
//                                 (default, matches every test already
//                                 run) -- the held reference never
//                                 changes except on reprogram/release.
//                                 1=ROLLING -- on every real comparison
//                                 (capture_compare), the just-compared
//                                 value becomes the NEW held reference,
//                                 regardless of whether that outcome's
//                                 own `emit` bit reported it downstream.
//                                 Turns this core from "compare against
//                                 a fixed baseline" into real change/
//                                 drift detection against whatever
//                                 arrived last. The exact 42nd and
//                                 FINAL bit of the real 42-bit
//                                 `core_config` budget (#497) -- zero
//                                 bits of headroom left after this one.
//   [63:42] reserved            — 22 bits, real headroom (within this
//                                 core's own native 64-bit cfg_data bus
//                                 only -- NOT available if this core is
//                                 reconstructed inside the super shell,
//                                 where core_config is capped at 42
//                                 bits total, all of which are now used)
`default_nettype none
`timescale 1ns / 1ps

module branch_cell_v1 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

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

    input  wire         freeze_in,

    output wire         status_data_valid
);

    // ── Real, static config fields, loaded on cfg_valid ─────────────
    reg [1:0] upstream_dir = 2'h0;

    reg value_source_low = 1'b0, value_source_equal = 1'b0, value_source_high = 1'b0;
    reg [6:0] fixed_value_low = 7'h0, fixed_value_equal = 7'h0, fixed_value_high = 7'h0;
    reg emit_low = 1'b0, emit_equal = 1'b0, emit_high = 1'b0;
    reg [3:0] route_low = 4'h0, route_equal = 4'h0, route_high = 4'h0;
    reg rolling_mode = 1'b0;

    // ── The held reference, per #497's own real optimization ────────
    reg [31:0] ref_value = 32'h0;
    reg        ref_valid = 1'b0;

    // ── Real, per-firing state -- which outcome fired determines what
    // gets offered, latched at capture time since it must persist
    // through the whole offer/fire/ack sequence. ──────────────────────
    reg [31:0] out_buffer  = 32'h0;
    reg        data_valid  = 1'b0;
    reg [3:0]  active_route = 4'h0;
    reg [3:0]  pending_ack  = 4'h0;

    wire effective_freeze = freeze_in;

    // ── Real, single fixed upstream direction -- decoded, not a mask.
    // Exactly one of these can be true at a time (#494's own real
    // constraint), so no OR-combination logic is needed the way every
    // other core's own upstream_mask requires. ──────────────────────
    wire sel_n = arrived_n && (upstream_dir == 2'd0);
    wire sel_s = arrived_s && (upstream_dir == 2'd1);
    wire sel_e = arrived_e && (upstream_dir == 2'd2);
    wire sel_w = arrived_w && (upstream_dir == 2'd3);
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    // ── Real, TWO real capture conditions -- capturing the reference
    // itself (only when no reference is held yet) is entirely separate
    // from capturing a value TO COMPARE (only once a reference exists,
    // and only when the previous comparison's own offer has drained --
    // the same doubly-full guard every other single-shot core uses).
    //
    // A REAL BUG, FOUND AND FIXED (not assumed away): every OTHER core
    // in this project is naturally safe against a held `arrived_x`
    // triggering more than one capture, because their ONE capture path
    // is blocked by the SAME register the capture itself sets
    // (`data_valid`). This core has TWO capture paths with DIFFERENT
    // guards -- completing `capture_reference` sets `ref_valid`, which
    // immediately makes `capture_compare`'s own guard true too, on the
    // SAME still-held arrival (the sender can't drop `arrived_x` before
    // it has SEEN `ack_out_x`, which takes at least one real clock
    // edge -- this is completely normal handshake timing, not a
    // testbench artifact; a real sim run with this exact timing
    // exposed it). Without `consumed` below, a single physical arrival
    // would be captured TWICE -- once as the reference, once
    // immediately compared against itself (always "equal"). `consumed`
    // blocks BOTH capture paths for as long as the CURRENT arrival
    // stays asserted, clearing only once the sender actually drops it.
    reg consumed = 1'b0;

    wire capture_reference = any_upstream_arrived && !consumed && !ref_valid && !effective_freeze;
    wire capture_compare   = any_upstream_arrived && !consumed && ref_valid && !data_valid && !effective_freeze;
    wire capture_now       = capture_reference || capture_compare;

    assign ack_out_n = capture_now && sel_n;
    assign ack_out_s = capture_now && sel_s;
    assign ack_out_e = capture_now && sel_e;
    assign ack_out_w = capture_now && sel_w;

    // ── THE CORE -- a real, genuine two's-complement 3-way outcome,
    // matching compare_cell_v1.v's own real signed convention. Only
    // meaningful when capture_compare fires (a reference already
    // exists); combinational, latched into the per-firing registers
    // below the same cycle. ──────────────────────────────────────────
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
    wire [3:0] outcome_route = (is_low  ? route_low  :
                                 is_equal ? route_equal :
                                            route_high);

    wire [31:0] outcome_out_value = outcome_value_source ? {25'h0, outcome_fixed_value}
                                                           : upstream_val;

    // ── Real, generic single-shot offer pass, same shape every other
    // core in this project already uses. ─────────────────────────────
    wire want_to_offer = data_valid && !effective_freeze;
    wire targets_all_ready = (!active_route[0] || ready_in_n) &&
                             (!active_route[1] || ready_in_s) &&
                             (!active_route[2] || ready_in_e) &&
                             (!active_route[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (active_route & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack  & ~ack_in_vec) :
                                                           pending_ack;
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    assign ready_out = !effective_freeze && !data_valid && ref_valid;
    assign status_data_valid = data_valid;

    always @(posedge clk) begin
        if (rst) begin
            upstream_dir        <= 2'h0;
            value_source_low    <= 1'b0; value_source_equal <= 1'b0; value_source_high <= 1'b0;
            fixed_value_low     <= 7'h0; fixed_value_equal  <= 7'h0; fixed_value_high  <= 7'h0;
            emit_low            <= 1'b0; emit_equal         <= 1'b0; emit_high         <= 1'b0;
            route_low           <= 4'h0; route_equal        <= 4'h0; route_high        <= 4'h0;
            rolling_mode        <= 1'b0;
            ref_value            <= 32'h0;
            ref_valid            <= 1'b0;
            out_buffer           <= 32'h0;
            data_valid           <= 1'b0;
            active_route         <= 4'h0;
            pending_ack          <= 4'h0;
            consumed             <= 1'b0;
        end else if (cfg_valid) begin
            upstream_dir        <= cfg_data[1:0];
            value_source_low    <= cfg_data[2];
            value_source_equal  <= cfg_data[3];
            value_source_high   <= cfg_data[4];
            fixed_value_low     <= cfg_data[11:5];
            fixed_value_equal   <= cfg_data[18:12];
            fixed_value_high    <= cfg_data[25:19];
            emit_low             <= cfg_data[26];
            emit_equal           <= cfg_data[27];
            emit_high            <= cfg_data[28];
            route_low            <= cfg_data[32:29];
            route_equal          <= cfg_data[36:33];
            route_high           <= cfg_data[40:37];
            rolling_mode         <= cfg_data[41];
            // ── Real release: reprogramming discards the held
            // reference and any in-flight offer -- see this file's own
            // header for the real, explicitly-flagged judgment call
            // this encodes. The very next capture after this becomes
            // the new held reference. ──
            ref_value             <= 32'h0;
            ref_valid             <= 1'b0;
            data_valid            <= 1'b0;
            pending_ack           <= 4'h0;
            consumed              <= 1'b0;
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
                // ── Real, genuine suppression: outcome_emit==0 means
                // this arrival is fully consumed (real ack above) but
                // produces no offer at all -- data_valid stays low,
                // ready for the next arrival immediately. Not a zero
                // value; nothing is offered. ──

                // ── ROLLING MODE (real #497-followup, per Alan's own
                // direct request): the just-compared value becomes the
                // NEW held reference -- regardless of whether outcome_
                // emit reported this comparison downstream. Turns
                // "compare against a fixed baseline" into real change/
                // drift detection against whatever arrived last. In
                // static mode (rolling_mode=0, the default -- matches
                // every test already run against this core) ref_value
                // only ever changes on reprogram/release, exactly as
                // originally built and sim-verified. ──
                if (rolling_mode) begin
                    ref_value <= upstream_val;
                end
            end

            // ── consumed: set the same cycle any capture happens,
            // cleared once the sender actually drops the arrival --
            // see this signal's own real, found-not-assumed rationale
            // above. ──
            if (capture_now) begin
                consumed <= 1'b1;
            end else if (!any_upstream_arrived) begin
                consumed <= 1'b0;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end

            pending_ack <= next_pending_ack;
        end
    end

endmodule
