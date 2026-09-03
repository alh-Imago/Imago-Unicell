// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// adder_cell_v4.v — points.md #617/#618: the FIRST real "unified
// carrier" core. Real, proven core logic CLONED from adder_cell_v1.v
// unchanged (the two-stage A/B capture, the real adder_v1.v carry
// chain, subtract_mode) -- everything ADDED here is real SHELL
// richness, per Alan's own precise 5-point breakdown (#617):
//
//   1. programming/#: a real, working program_in/PROG_ID targeted,
//      staged reconfiguration channel -- FAITHFULLY PORTED from
//      unicell_stripped_v1.v's own real protocol (#123/#140), not
//      reinvented, remapped onto this cell's own real 3 fields
//      (downstream_mask/upstream_mask/subtract_mode) instead of
//      nano's 7.
//   2. shift/nibble_mask/lane: the real, ALREADY-BUILT addon chain
//      (#303-#312), wired here exactly as unicell_super_v3.v already
//      does it -- nibble_mask -> shift/lane -> invert, same
//      addon_config bit layout, reused verbatim, not reimplemented.
//   3. 6-way cardinality: downstream_mask/upstream_mask widened to
//      6 bits (matching nano's own real routing_mask/cardinal_edge
//      width) -- REAL FIELD-WIDTH HEADROOM ONLY. Only 4 real cardinal
//      ports (N/S/E/W) are physically wired in this file; bits [5:4]
//      are real, reserved headroom, exactly mirroring nano's own
//      already-real convention, not a claim that 6-directional
//      routing is implemented here (#604 remains the separate, larger,
//      not-yet-started thread for that).
//   4. "with ack all around": the programming channel gets its own
//      real, independent ack_out/in per direction, matching nano's
//      own real convention -- not a single shared/broadcast ack.
//   5. the `active` bit: a new, real, explicit top-level port. Tied
//      permanently high for standalone (N=1) use -- when a future
//      N-core carrier wraps this same real core, `active` becomes the
//      REAL, ALREADY-PROVEN `incoming_select == SEL_ADDER` decode
//      (unicell_super_v3.v's own real pattern), not a new mechanism.
//      When low, this cell is fully silent: no capture, no offer, no
//      acks on any channel -- confirmed by construction, not asserted.
//
// REAL, HONEST SCOPE, stated plainly, matching #617's own scope doc:
// `is_command_cell` / COMMAND_EMIT mode is NOT included in this first
// build -- a real, separate, later increment (needs real, careful
// semantic design for this core's own two-stage capture model, unlike
// nano's more general hold/reemit shape). The `cmd_in`/`cmd_out`
// cardinal channel remains genuinely unbuilt (#84), same as
// everywhere else in this project today.
//
// cfg_data[63:0] field map (atomic boot-load path, unchanged from v1):
//   [5:0]   downstream_mask  — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  upstream_mask    — one-hot(s), N/S/E/W real + 2 reserved
//   [12]    subtract_mode    — 0=A+B, 1=A-B (unchanged from v1)
//   [32:13] addon_config     — 20 bits, SAME real layout as
//                              unicell_super_v3.v's own real addon_config
//   [63:33] reserved
`default_nettype none
`timescale 1ns / 1ps

module adder_cell_v4 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    // points.md #617 point 5: the real, explicit "active" bit. Tie
    // high for standalone use; drive with a real core_select decode
    // when this core is wrapped by a future N-core carrier.
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

    // ── points.md #617: the real, targeted programming channel,
    // faithfully ported from unicell_stripped_v1.v's own real
    // program_in/PROG_ID protocol (#123/#140/#615) — its own,
    // independent 4-directional real ack, exactly mirroring nano's
    // own real convention. ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,

    output wire         status_data_valid,   // out_buffer holds an unconsumed sum
    output wire         status_a_arrived     // A captured, awaiting B — debug only
);

    // ── State — real core state, unchanged in shape from v1 (6-bit
    // masks instead of 4-bit is the only real width change) ──────────
    reg [31:0] a_reg           = 32'h0;
    reg        a_arrived       = 1'b0;
    reg [31:0] out_buffer      = 32'h0;
    reg        data_valid      = 1'b0;
    reg [5:0]  downstream_mask = 6'h0;
    reg [5:0]  upstream_mask   = 6'h0;
    reg        subtract_mode   = 1'b0;
    reg [19:0] addon_config    = 20'h0;
    reg [3:0]  pending_ack     = 4'h0;
    // points.md #617: real, staged-reconfiguration arm state,
    // faithfully mirroring unicell_stripped_v1.v's own real `armed`
    // register and its own real semantics exactly — a cell mid-
    // reprogram via the targeted channel stays COLD (disarmed) until
    // an explicit COMPLETE with its own data payload's LSB set.
    reg        armed           = 1'b0;

    wire effective_freeze = freeze_in;
    // points.md #617 point 5: `active` gates EVERYTHING below —
    // capture, fire, offer, and both real ack channels — by
    // construction, not by a separate late-stage mux the way the
    // existing super shell currently zeroes out non-selected cores'
    // OWN outputs from the outside. When low, this cell has no real
    // effect on anything it's wired to.
    wire effective_armed  = armed && active;

    // ── Upstream arrival selection — real, only the low 4 bits of
    // the now-6-bit upstream_mask are ever wired to a real physical
    // port in this file (bits [5:4] are real, reserved headroom,
    // matching nano's own real convention exactly — #604's own
    // 3D-cardinal prerequisite, not implemented here). ──
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

    // ── The real arithmetic — unchanged from adder_cell_v1.v ────────
    wire [31:0] adder_b_in = subtract_mode ? ~upstream_val : upstream_val;
    wire [31:0] adder_sum;
    wire        adder_cout;
    adder_v1 #(.WIDTH(32)) ADD (
        .a(a_reg), .b(adder_b_in), .cin(subtract_mode),
        .sum(adder_sum), .cout(adder_cout)
    );

    // ── Downstream offering — real, unchanged shape from v1, gated
    // additionally on `effective_armed` (a disarmed/inactive cell
    // never offers, by construction). ──
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

    // ── points.md #617: the real, three-addon chain, wired exactly
    // as unicell_super_v3.v already does it -- SAME order
    // (nibble_mask -> shift/lane -> invert), SAME 20-bit addon_config
    // layout, reused verbatim (#311/#312's own already-proven wiring,
    // not reinvented). ──
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

    // Real, honest gating: ready_out reflects `armed` the same way
    // nano's own real ready_out does (`ready_bit && armed`, #615) —
    // an inactive or disarmed cell is never ready.
    assign ready_out = effective_armed && !effective_freeze && !(a_arrived && data_valid);
    assign status_data_valid = data_valid;
    assign status_a_arrived  = a_arrived;

    // ── points.md #617: the real, targeted programming channel's own
    // priority-select and field IDs — faithfully mirroring
    // unicell_stripped_v1.v's own real convention (#140), remapped
    // onto this cell's own real 3 fields. Real, deliberate deviation
    // from nano's own exact bit positions: nano's own word is 16 bits
    // (`prog_word[15:0]`, ID at `[18:16]`) since none of ITS OWN 7
    // fields need more; this core's `PROG_ID_ADDON_CONFIG` needs a
    // real, full 20-bit word (the same real `addon_config` width
    // shared with `unicell_super_v3.v`) to land in ONE write rather
    // than being split across two -- so the ID field here sits at
    // `[22:20]`, directly above a genuinely wider `[19:0]` word,
    // non-overlapping, same real principle nano's own layout follows
    // (ID immediately above its own data payload), just sized for
    // this core's own real, wider field. Only 3 real IDs + COMPLETE
    // are used; the 3-bit ID width (same as nano's) leaves real,
    // honest headroom for this core's own future fields, same
    // "nothing wasted, real reserved space" convention nano already
    // has. ──
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd0;
    localparam [2:0] PROG_ID_UPSTREAM_MASK   = 3'd1;
    localparam [2:0] PROG_ID_SUBTRACT_MODE   = 3'd2;
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
            subtract_mode   <= 1'b0;
            addon_config    <= 20'h0;
            pending_ack     <= 4'h0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            // Real, atomic boot-load path — unchanged real semantics
            // from v1, arms immediately (nothing left to stage).
            downstream_mask <= cfg_data[5:0];
            upstream_mask   <= cfg_data[11:6];
            subtract_mode   <= cfg_data[12];
            addon_config    <= cfg_data[32:13];
            a_arrived       <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            // Real, targeted, staged reconfiguration — mirrors
            // unicell_stripped_v1.v's own real case statement exactly,
            // remapped onto this cell's own 3 real fields.
            case (prog_id)
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_UPSTREAM_MASK:   upstream_mask   <= prog_word[5:0];
                PROG_ID_SUBTRACT_MODE:   subtract_mode   <= prog_word[0];
                PROG_ID_ADDON_CONFIG:    addon_config    <= prog_word[19:0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];  // real "commit+arm" vs "commit, stay cold"
                end
                default: ;
            endcase
        end else begin
            if (can_fire) begin
                out_buffer <= adder_sum;
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
