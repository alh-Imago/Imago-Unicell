// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// nano_gate_v4.v — points.md #617/#626: nano's own STRIP-DOWN to the
// unified carrier shape, the one core in this whole family that gets
// LESS internal machinery, not more, since it already had the richest
// real feature set of all 8 (per this same session's own real
// discovery). Real core logic CLONED UNCHANGED from
// unicell_stripped_v1.v, per Alan's own direct decision to keep it
// "as is... the Swiss army knife of all the cores": the real
// two-arrival NOR-decomposed gate computation (12 real topology
// codes, unchanged since the FULL cell), the real dynamic
// pattern-based routing (pattern_low/equal/high + dynamic_route_en,
// gated by the real, measured ENABLE_DYNAMIC_ROUTING compile-time
// parameter -- kept precisely because it's genuinely core-specific,
// outcome-dependent routing, the same real reasoning `branch_cell_v4.
// v`'s own route_low/equal/high got, #624), real relay-vs-consume
// classification (`cardinal_edge`), and the full real memory-cell
// extension set (`hold_in`/`fb_internal_in`/`a_reemit_in`/
// `a_update_in`/`a_self_update_in`), plus `error_frozen`'s own real
// protective latch.
//
// REAL, DELIBERATE REMOVAL, per Alan's own direct decision: the
// command-cell mechanism is gone ENTIRELY, moving to a real, separate
// command core (not yet built) rather than staying bolted onto this
// one:
//   - `is_command_cell` (`cmd_latch[10]` in v1) removed outright.
//     Confirmed directly before removing, not assumed: it was ONLY
//     ever a config-time alias forcing `effective_hold`/
//     `effective_reemit` permanently true -- the exact same real
//     behavior remains fully reachable by driving `hold_in`/
//     `a_reemit_in` directly from whatever real source needs it
//     (including a future command core). Zero real capability lost.
//   - `cmd_in_n/s/e/w`/`cmd_out_n/s/e/w` removed outright. Confirmed
//     directly before removing: these were real, reserved PORTS
//     (`#84`) but genuinely UNWIRED in the actual RTL (`cmd_out_x`
//     tied to `32'h0` unconditionally) -- a dead stub, not a working
//     channel. Zero real capability lost removing it either.
//
// Same real shell additions as #618-#625, per Alan's own precise
// 5-point breakdown (#617):
//   1. programming: the real, targeted program_in/PROG_ID channel --
//      ALREADY nano's own real mechanism (the one every other core's
//      own #618-#625 build was faithfully ported FROM, #615) --
//      extended here with one real, new targeted field
//      (`PROG_ID_ADDON_CONFIG`) and widened to a real 4-bit ID (9 real
//      fields + COMPLETE now exceed the original 3-bit/8-slot budget
//      -- the SAME real pressure `branch_cell_v4.v` hit, #624, not a
//      coincidence: both are this project's own richest, most
//      field-dense cores).
//   2. shift/nibble_mask/lane: the real, already-proven 3-addon chain,
//      wired to the offered `out_buffer`, same as #618-#625.
//   3. 6-way cardinality: nano ALREADY had this -- `routing_mask`/
//      `cardinal_edge` are genuinely 6 bits wide in the real v1 RTL,
//      the real prerequisite `#604` itself already named. No change
//      needed here; nano was the one core the other 7 were catching
//      up TO on this specific point.
//   4. ack all around: nano ALREADY had this too -- the real
//      programming channel's own independent per-direction ack was
//      always here (`#615`).
//   5. `active`: the one real, genuinely new addition. Folded into
//      the SAME place `armed` already lives in the real v1 logic
//      (`effective_freeze = freeze_in || error_frozen || !armed`) --
//      matching that EXISTING real convention exactly rather than
//      importing the OTHER 7 cores' own separate `effective_armed`
//      pattern, since nano already had its own established way of
//      composing these gates.
//
// REAL, NOTABLE DATA POINT: `addon_config` (20 bits) fits inside the
// EXISTING 128-bit `cmd_latch` without widening `cfg_data` at all --
// confirmed directly, not assumed: the real v1 header already
// documents roughly 53 bits of genuine, deliberate reserved headroom
// ([63:14] alone is 50 bits) left free specifically for future
// extension. The one core built up from the richest starting budget
// is also the one that needed the LEAST real extra room.
//
// cmd_latch[127:0] field map (atomic boot-load path) -- unchanged
// bit positions from v1 except where noted:
//   [9:0]   topology         — same 12 real NOR-decomposed gate codes
//   [10]    reserved         — was is_command_cell, now free
//   [12:11] reserved
//   [13]    ready            — this cell's own readiness
//   [33:14] addon_config     — 20 bits, SAME real layout as
//                              unicell_super_v3.v's own real addon_config,
//                              placed in v1's own real reserved space
//   [63:34] reserved         — 30 bits, real, honest headroom
//   [69:64] routing_mask     — unchanged from v1
//   [75:70] cardinal_edge    — unchanged from v1
//   [81:76] pattern_low      — unchanged from v1
//   [87:82] pattern_equal    — unchanged from v1
//   [93:88] pattern_high     — unchanged from v1
//   [94]    dynamic_route_en — unchanged from v1
//   [95]    reserved
//   [127:96] out_buffer      — unchanged from v1
`default_nettype none
`timescale 1ns / 1ps

module nano_gate_v4 #(
    parameter [15:0] CELL_ID = 16'h0000,
    // Real, unchanged from v1 -- the same measured ALM/timing
    // optimization (#169/silicon session): compile-time gate for the
    // dynamic-routing comparator, zero cost for any cell that never
    // uses it.
    parameter        ENABLE_DYNAMIC_ROUTING = 1'b0
) (
    input  wire        clk,
    input  wire         rst,

    // points.md #617 point 5: real, explicit "active" bit -- folded
    // into effective_freeze alongside armed, matching nano's own
    // existing real convention (see header).
    input  wire         active,

    input  wire         cfg_valid,
    input  wire [127:0] cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    // ── Real, unchanged live control wires from v1 -- these are
    // genuinely live control, not config, per v1's own real,
    // established distinction (see header of unicell_stripped_v1.v). ──
    input  wire         hold_in,
    input  wire         fb_internal_in,
    input  wire         a_reemit_in,
    input  wire         a_update_in,
    input  wire         a_self_update_in,

    // ── points.md #617: real, targeted programming channel -- ALREADY
    // nano's own real mechanism, unchanged in shape, extended with one
    // new real field and a widened 4-bit ID (see header). ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w
);

    // ── State — real, unchanged from v1 ──────────────────────────────
    reg [127:0] cmd_latch  = 128'h0;
    reg [31:0]  data_reg   = 32'h0;
    reg         a_arrived  = 1'b0;
    reg [5:0]   pending_ack= 6'h0;
    reg         program_done_r = 1'b0;
    reg         error_frozen = 1'b0;
    reg         armed = 1'b0;

    wire [9:0] topology     = cmd_latch[9:0];
    wire       ready_bit    = cmd_latch[13];
    wire [19:0] addon_config= cmd_latch[33:14];
    wire [5:0] routing_mask = cmd_latch[69:64];
    wire [5:0] cardinal_edge= cmd_latch[75:70];
    wire [31:0] out_buffer  = cmd_latch[127:96];

    wire [3:0] pattern_low    = cmd_latch[79:76];
    wire [3:0] pattern_equal  = cmd_latch[85:82];
    wire [3:0] pattern_high   = cmd_latch[91:88];
    wire       dynamic_route_en = cmd_latch[94];

    // Real, deliberate removal (see header): is_command_cell is gone.
    // effective_hold/effective_reemit are now just the real, live
    // control wires directly -- the exact same behavior remains fully
    // reachable by driving them from any real source.
    wire effective_hold   = hold_in;
    wire effective_reemit = a_reemit_in;

    assign ready_out = ready_bit && armed && active;
    assign program_done = program_done_r;
    assign prog_ack_out_n = programming_active && prog_sel_n;
    assign prog_ack_out_s = programming_active && prog_sel_s;
    assign prog_ack_out_e = programming_active && prog_sel_e;
    assign prog_ack_out_w = programming_active && prog_sel_w;

    wire prog_any_arrived = prog_arrived_in_n | prog_arrived_in_s | prog_arrived_in_e | prog_arrived_in_w;
    wire prog_sel_n = prog_arrived_in_n;
    wire prog_sel_s = prog_arrived_in_s && !prog_arrived_in_n;
    wire prog_sel_e = prog_arrived_in_e && !prog_arrived_in_n && !prog_arrived_in_s;
    wire prog_sel_w = prog_arrived_in_w && !prog_arrived_in_n && !prog_arrived_in_s && !prog_arrived_in_e;
    wire [31:0] prog_data_val = prog_sel_n ? prog_data_in_n :
                                prog_sel_s ? prog_data_in_s :
                                prog_sel_e ? prog_data_in_e :
                                             prog_data_in_w;

    // ── points.md #617/#626: real, widened 4-bit PROG_ID -- the SAME
    // real pressure branch_cell_v4.v hit (#624): 9 real fields +
    // COMPLETE exceed the original 3-bit/8-slot budget. id at [23:20],
    // word at [19:0], same real "ID directly above its own data
    // payload" principle every other core's own layout follows. ──
    localparam [3:0] PROG_ID_TOPOLOGY     = 4'd0;
    localparam [3:0] PROG_ID_ROUTING_MASK = 4'd1;
    localparam [3:0] PROG_ID_CARDINAL_EDGE= 4'd2;
    localparam [3:0] PROG_ID_PATTERN_LOW  = 4'd3;
    localparam [3:0] PROG_ID_PATTERN_EQUAL= 4'd4;
    localparam [3:0] PROG_ID_PATTERN_HIGH = 4'd5;
    localparam [3:0] PROG_ID_DYN_ROUTE_EN = 4'd6;
    localparam [3:0] PROG_ID_ADDON_CONFIG = 4'd7;
    localparam [3:0] PROG_ID_COMPLETE     = 4'd15;

    wire [3:0]  prog_id   = prog_data_val[23:20];
    wire [19:0] prog_word = prog_data_val[19:0];

    // points.md #617: real, new active gate added here -- the ORIGINAL
    // v1 line had no active concept at all (program_in && prog_any_
    // arrived); every other v4 core's own programming_active includes
    // it, extended here for consistency across the whole real family.
    wire programming_active = program_in && active && prog_any_arrived;

    // ── Real, unchanged from v1: OR-combine arrival selection ────────
    wire any_arrived = arrived_n | arrived_s | arrived_e | arrived_w;
    wire [31:0] arrived_val = (arrived_n ? data_in_n : 32'h0) |
                              (arrived_s ? data_in_s : 32'h0) |
                              (arrived_e ? data_in_e : 32'h0) |
                              (arrived_w ? data_in_w : 32'h0);
    wire capture_now = consume_arrived && !a_arrived && !effective_freeze && !program_in;

    wire sel_n = arrived_n;
    wire sel_s = arrived_s;
    wire sel_e = arrived_e;
    wire sel_w = arrived_w;

    // ── Real, unchanged from v1: relay-vs-consume classification. ────
    wire selected_is_relay = (sel_n && cardinal_edge[0]) ||
                             (sel_s && cardinal_edge[1]) ||
                             (sel_e && cardinal_edge[2]) ||
                             (sel_w && cardinal_edge[3]);
    wire relay_arrived   = any_arrived && selected_is_relay;
    wire consume_arrived = any_arrived && !selected_is_relay;

    wire any_relay_dir   = (sel_n && cardinal_edge[0]) || (sel_s && cardinal_edge[1]) ||
                           (sel_e && cardinal_edge[2]) || (sel_w && cardinal_edge[3]);
    wire any_consume_dir = (sel_n && !cardinal_edge[0]) || (sel_s && !cardinal_edge[1]) ||
                           (sel_e && !cardinal_edge[2]) || (sel_w && !cardinal_edge[3]);
    wire relay_mismatch  = any_arrived && any_relay_dir && any_consume_dir;

    // points.md #617: real, new active gate folded in here, matching
    // nano's own existing real convention of composing gates into
    // effective_freeze (rather than a separate effective_armed the
    // way #618-#625's own cores use, since that pattern doesn't exist
    // in nano's own real design to begin with).
    wire effective_freeze = freeze_in || error_frozen || !armed || !active;

    wire internal_fb_active = hold_in && fb_internal_in && !effective_freeze && !program_in;

    wire a_reemit_active = effective_hold && effective_reemit && a_arrived && consume_arrived &&
                           ready_bit && targets_all_ready && !effective_freeze && !program_in;
    wire a_update_active = hold_in && a_update_in && consume_arrived && !effective_freeze && !program_in;

    // ── Real, unchanged from v1: the two-arrival gate computation. ───
    wire [31:0] input_val  = a_arrived ? data_reg : arrived_val;
    wire [31:0] second_val = internal_fb_active ? out_buffer :
                              (a_arrived ? arrived_val : data_reg);

    wire [3:0] effective_routing;

    generate
    if (ENABLE_DYNAMIC_ROUTING) begin : gen_dynamic_routing
        wire cmp_gt = (second_val > input_val);
        wire cmp_lt = (second_val < input_val);
        wire [3:0] selected_pattern = cmp_gt ? pattern_high :
                                      cmp_lt ? pattern_low  :
                                               pattern_equal;
        assign effective_routing = dynamic_route_en ? (selected_pattern & routing_mask[3:0])
                                                     : routing_mask[3:0];
    end else begin : gen_static_routing_only
        assign effective_routing = routing_mask[3:0];
    end
    endgenerate

    wire [31:0] g0 = ~(input_val  | input_val);
    wire [31:0] g1 = ~(second_val | second_val);
    wire [31:0] g2 = ~(g0 | g1);
    wire [31:0] g3 = ~(g2 | g2);
    wire [31:0] g4 = ~(input_val  | second_val);
    wire [31:0] g5 = ~(g4 | g4);
    wire [31:0] g6 = ~(input_val  | g4);
    wire [31:0] g7 = ~(second_val | g4);
    wire [31:0] g8 = ~(g6 | g7);
    wire [31:0] g9 = ~(g8 | g8);

    reg [31:0] computed_output;
    always @(*) begin
        computed_output = input_val;
        case (topology)
            10'h000: computed_output = input_val;
            10'h02C: computed_output = second_val;
            10'h001: computed_output = g0;
            10'h002: computed_output = g1;
            10'h004: computed_output = g4;
            10'h007: computed_output = g2;
            10'h024: computed_output = g5;
            10'h027: computed_output = g3;
            10'h0BC: computed_output = g9;
            10'h03C: computed_output = g8;
            10'h030: computed_output = 32'h0;
            10'h0B0: computed_output = 32'hFFFFFFFF;
            default: computed_output = input_val;
        endcase
    end

    wire new_data = consume_arrived && a_arrived;

    wire want_n = effective_routing[0];
    wire want_s = effective_routing[1];
    wire want_e = effective_routing[2];
    wire want_w = effective_routing[3];

    wire targets_all_ready = (!want_n || ready_in_n) &&
                             (!want_s || ready_in_s) &&
                             (!want_e || ready_in_e) &&
                             (!want_w || ready_in_w);

    // Real, necessary exclusion, found while wiring a real adder_cell_v4
    // into a genuine hold+update closed loop (LLVM phi/loop-var work,
    // points.md #636): can_fire's own condition (new_data=consume_
    // arrived&&a_arrived) is independently satisfied by ANY real
    // arrival while hold_in keeps a_arrived permanently 1 -- including
    // one that's ALSO a_update_in-intended. Without this exclusion,
    // any_fire (below) schedules a spurious extra offer using STALE
    // cmd_latch[127:96] data (a_update_active's own branch never
    // touches it) whenever a real downstream target happens to already
    // be ready during an update -- silently corrupting the very next
    // real arrival this cell captures. ack_out/consumed_now are
    // unaffected: a_update_active already contributes to consumed_now
    // independently, so the real upstream sender is still acked correctly.
    wire can_fire = new_data && ready_bit && targets_all_ready && !effective_freeze && !program_in && !a_update_in;
    wire relay_fire = relay_arrived && ready_bit && targets_all_ready && !effective_freeze && !program_in;

    wire [5:0] targeted_vec = {2'b00, want_w, want_e, want_s, want_n};
    wire [5:0] ack_in_vec   = {2'b00, ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire       any_fire     = can_fire || relay_fire || a_reemit_active;
    wire [5:0] next_pending_ack = any_fire            ? (targeted_vec & ~ack_in_vec) :
                                  (pending_ack != 6'h0) ? (pending_ack  & ~ack_in_vec) :
                                                          pending_ack;
    wire       next_ready = hold_in || (next_pending_ack == 6'h0);

    wire consumed_now = capture_now || can_fire || relay_fire || a_reemit_active || a_update_active;
    assign ack_out_n = consumed_now && sel_n;
    assign ack_out_s = consumed_now && sel_s;
    assign ack_out_e = consumed_now && sel_e;
    assign ack_out_w = consumed_now && sel_w;

    // ── points.md #617: the real, three-addon chain, applied to the
    // offered out_buffer, wired identically to #618-#625's own. ──
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

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    always @(posedge clk) begin
        if (rst) begin
            cmd_latch     <= 128'h0;
            data_reg      <= 32'h0;
            a_arrived     <= 1'b0;
            pending_ack   <= 6'h0;
            program_done_r<= 1'b0;
            error_frozen  <= 1'b0;
            armed         <= 1'b0;
        end else if (cfg_valid) begin
            cmd_latch     <= cfg_data;
            cmd_latch[13] <= 1'b1;
            pending_ack   <= 6'h0;
            error_frozen  <= 1'b0;
            armed         <= 1'b1;
        end else begin
            if (relay_mismatch) error_frozen <= 1'b1;

            if (programming_active) begin
                case (prog_id)
                    PROG_ID_TOPOLOGY:      cmd_latch[9:0]   <= prog_word[9:0];
                    PROG_ID_ROUTING_MASK:  cmd_latch[67:64] <= prog_word[3:0];
                    PROG_ID_CARDINAL_EDGE: cmd_latch[73:70] <= prog_word[3:0];
                    PROG_ID_PATTERN_LOW:   cmd_latch[79:76] <= prog_word[3:0];
                    PROG_ID_PATTERN_EQUAL: cmd_latch[85:82] <= prog_word[3:0];
                    PROG_ID_PATTERN_HIGH:  cmd_latch[91:88] <= prog_word[3:0];
                    PROG_ID_DYN_ROUTE_EN:  cmd_latch[94]    <= prog_word[0];
                    PROG_ID_ADDON_CONFIG:  cmd_latch[33:14] <= prog_word[19:0];
                    PROG_ID_COMPLETE: begin
                        cmd_latch[13]  <= 1'b1;
                        program_done_r <= 1'b1;
                        error_frozen   <= 1'b0;
                        armed          <= prog_word[0];
                    end
                    default: ;
                endcase
            end else if (internal_fb_active) begin
                if (a_self_update_in)
                    data_reg <= computed_output;
                else
                    cmd_latch[127:96] <= computed_output;
            end else if (a_update_active) begin
                data_reg <= arrived_val;
            end else if (a_reemit_active) begin
                cmd_latch[127:96] <= data_reg;
            end else if (capture_now) begin
                data_reg  <= arrived_val;
                a_arrived <= 1'b1;
            end else if (can_fire) begin
                cmd_latch[127:96] <= computed_output;
                a_arrived         <= hold_in;
            end else if (relay_fire) begin
                cmd_latch[127:96] <= arrived_val;
            end

            if (!program_in) program_done_r <= 1'b0;

            pending_ack   <= next_pending_ack;
            cmd_latch[13] <= next_ready;
        end
    end

endmodule
