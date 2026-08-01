// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// unicell_stripped_v1.v — the STRIPPED / next-hop cell, first real RTL draft.
// NOT YET SIMULATED. Written directly against the confirmed baseline in
// points.md #88 (2026-08-01), field-by-field cross-checked against the real,
// silicon-proven unicell64_v3.v rather than invented fresh. Gate computation
// is UNCHANGED from the FULL cell (same NOR-decomposition, same topology
// codes) — only addressing/delivery differs, per unicell_automaton_v1.py's
// own design note (that file is this cell's Python model; nothing here
// contradicts it, this is that model's RTL counterpart).
//
// WHAT'S DELIBERATELY ABSENT, NOT MERELY DISABLED (points.md #76/#84):
// input_address, output_address, auth_mask, config_match, and the whole
// RUN-state address-matched command-bus decode. Those stay in the FULL
// (addressed-shell) cell, whose job is to configure this cell ONCE at boot
// via loader_fsm_v3.v, exactly as it already does today. This module's boot
// interface is therefore intentionally a plain synchronous config load
// (cfg_valid/cfg_data), NOT a reproduction of the FULL cell's addr-matched
// CMD_BOOT_COMMIT path — wiring THIS module's cfg port to that existing
// loader mechanism is separate follow-on work, not yet done.
//
// cmd_latch[31:0] field map (points.md #88):
//   [9:0]   topology      — same NOR-gate selection as unicell64_v3.v
//   [13]    ready         — NEW. This cell's own readiness. Broadcast
//                           UNCONDITIONALLY on all 4 cardinal ports — cannot
//                           be gated by routing_mask/cardinal_edge, since a
//                           cell can't know in advance which neighbor(s)
//                           might be upstream of it in some layout.
//   [69:64] routing_mask  — same field/bits as unicell64_v3.v (output side:
//                           which directions are open on this cell)
//   [75:70] cardinal_edge — same field/bits, REINTERPRETED per-INCOMING
//                           direction (consume vs. relay), per the automaton
//                           model's design note, not per-outgoing as in the
//                           FULL cell
//   [127:96] out_buffer   — NEW. The offered-output value, separate from
//                           data_reg, per points.md #77/#88.
// Everything else in [31:0]/[63:32]/[95:76]/[126:96] is presently free/
// unused by this module — deliberately not claimed here. Reserved
// specifically so a future cardinal COMMAND channel (points.md #84 —
// freeze/reprogram tokens riding the same physical per-cell command wiring,
// reinterpreted as cardinal post-boot) can be added later without a field-
// map reshuffle. Not built in this draft; see cmd_in/cmd_out port note below.
//
// freeze_in (points.md #92): a direct, minimal stand-in for what the
// deferred cardinal command channel will eventually carry as an opcode/
// token. Gates capture_now AND can_fire, mirroring unicell64_v3.v's own
// `frozen` gating of `bus_hit` exactly -- a frozen cell is fully paused,
// not merely fire-blocked. Built now specifically to test the cascade:
// freezing one cell in a chain/ring should back up everything behind it
// (via the same ack-never-arrives mechanism #91 already established),
// and releasing it should let everything drain again.
`default_nettype none
`timescale 1ns / 1ps

module unicell_stripped_v1 #(
    parameter [15:0] CELL_ID = 16'h0000  // fixed grid position, boot-time target only
) (
    input  wire        clk,
    input  wire         rst,

    // ── Boot-time config load (stand-in for loader_fsm_v3.v integration) ──
    // Plain synchronous load, no address match — this module has no bus to
    // match against. Wiring this to the real, existing loader mechanism is
    // separate follow-on work (points.md #88, "not yet worked through").
    input  wire         cfg_valid,
    input  wire [127:0] cfg_data,

    // ── Cardinal data ports — one point-to-point link per direction ───────
    // in_*: this cell as RECEIVER. out_*: this cell as SENDER.
    // arrived_in marks a genuine new value this cycle (edge, not level).
    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    // ── Bidirectional ready — broadcast unconditionally, both directions ──
    // (points.md #88: cannot be routing-gated; any port could be upstream)
    output wire         ready_out,               // this cell's own readiness
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    // ── Read-confirmation — genuinely separate from ready_in/out (points.md
    // #89). A sender cannot infer it's been read; a receiver must SAY so, the
    // cycle it actually captures a new arrival into data_reg. ──
    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    // ── RESERVED, not yet implemented (points.md #84/#88 — command cardinal
    // bus, deferred). Present in the port list now so adding it later is an
    // additive change, not a rewrite. Tie off / leave unconnected for now.
    input  wire [31:0]  cmd_in_n,    cmd_in_s,    cmd_in_e,    cmd_in_w,
    output wire [31:0]  cmd_out_n,   cmd_out_s,   cmd_out_e,   cmd_out_w,

    // ── Freeze — minimal, direct stand-in for what the cardinal command
    // channel will eventually deliver (points.md #92). A plain level input,
    // not yet an opcode/token riding cmd_in/cmd_out — that integration is
    // still deferred. Mirrors the FULL cell's own frozen/bus_hit gating
    // exactly (unicell64_v3.v: `bus_hit = !frozen && ...`): while asserted,
    // this cell neither captures nor fires at all -- fully paused, not just
    // fire-blocked. ──
    input  wire         freeze_in
);

    // ── State ───────────────────────────────────────────────────────────
    reg [127:0] cmd_latch  = 128'h0;
    reg [31:0]  data_reg   = 32'h0;   // working register — mirrors unicell64_v3.v
    reg         a_arrived  = 1'b0;    // first-arrival latch (two-arrival model)
    reg [5:0]   pending_ack= 6'h0;    // (points.md #89, widened #90) fire-time
                                      // snapshot of directions ACTUALLY targeted
                                      // this fire — {2'b00,W,E,S,N}, 6-bit and
                                      // 3D-ready ([5:4] reserved), matching
                                      // routing_mask/cardinal_edge's own
                                      // convention exactly rather than a
                                      // narrower one-off 4-bit encoding. A
                                      // direction never targeted is never set
                                      // here, so it can never block recovery.

    wire [9:0] topology     = cmd_latch[9:0];
    wire       ready_bit    = cmd_latch[13];               // this cell's own ready
    wire [5:0] routing_mask = cmd_latch[69:64];             // openness, output side
    wire [5:0] cardinal_edge= cmd_latch[75:70];             // consume(0)/relay(1), per INCOMING dir
    wire [31:0] out_buffer  = cmd_latch[127:96];

    assign ready_out = ready_bit;

    // ── Priority-select WHICH direction actually supplied the value being
    // consumed this cycle (points.md #91) — needed so ack goes only to the
    // genuine source, not broadcast to every asserting direction. Same
    // priority order as arrived_val's own mux (N>S>E>W). ──
    wire sel_n = arrived_n;
    wire sel_s = arrived_s && !arrived_n;
    wire sel_e = arrived_e && !arrived_n && !arrived_s;
    wire sel_w = arrived_w && !arrived_n && !arrived_s && !arrived_e;

    // ── ack_out (points.md #91 — supersedes #89's capture-only version):
    // asserted ONLY when this cell genuinely CONSUMES the value this cycle —
    // either captures it as a fresh first arrival (capture_now, unconditional
    // — holding an input while a previous output still drains is fine), OR
    // accepts it as the live second-arrival trigger AND ACTUALLY FIRES
    // (can_fire, which already requires ready_bit — i.e. this cell's own
    // output side is clear). If this cell is doubly full (a_arrived=1 AND
    // ready_bit=0), can_fire is false, so NO ack is sent — the delivery
    // stays genuinely unconsumed, and the sender (seeing pending_ack/its own
    // level-held offer never clear) halts too. This is what makes the
    // backward stall a real cascade rather than a lossy one-shot miss. ──
    wire consumed_now = capture_now || can_fire;
    assign ack_out_n = consumed_now && sel_n;
    assign ack_out_s = consumed_now && sel_s;
    assign ack_out_e = consumed_now && sel_e;
    assign ack_out_w = consumed_now && sel_w;

    always @(posedge clk) begin
        if (rst) begin
            cmd_latch <= 128'h0;
            data_reg  <= 32'h0;
            a_arrived <= 1'b0;
        end else if (cfg_valid) begin
            // Boot-time load only — see module header note on loader integration.
            cmd_latch <= cfg_data;
            cmd_latch[13] <= 1'b1;  // a freshly-configured cell starts ready
        end
    end

    // ── Incoming arrival, any direction (cardinal_edge decides consume vs relay
    // per-direction, per the automaton model's reinterpretation — NOT yet wired
    // below; first draft treats every arriving direction as a candidate input
    // to the two-arrival gate, matching unicell_automaton_v1.py's CONSUMING-cell
    // path. The RELAY (pure pass-through) path is follow-on work once this
    // consume-only version is confirmed timing-clean, per #83's own sequencing
    // discipline: smallest scope that answers the timing question first.) ──
    wire any_arrived = arrived_n | arrived_s | arrived_e | arrived_w;
    wire [31:0] arrived_val = arrived_n ? data_in_n :
                              arrived_s ? data_in_s :
                              arrived_e ? data_in_e :
                                          data_in_w;
    wire capture_now = any_arrived && !a_arrived && !freeze_in;

    // ── Two-arrival gate computation — UNCHANGED from unicell64_v3.v ──────
    wire [31:0] input_val  = a_arrived ? data_reg : arrived_val;
    wire [31:0] second_val = a_arrived ? arrived_val : data_reg;

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

    wire new_data = any_arrived && a_arrived;  // second arrival fires

    // ── Multicast fire gating: WAIT-FOR-ALL targeted neighbors ready ──────
    // (points.md #88, Alan's explicit choice: simplest model, one shared
    // out_buffer, one ready bit — cell holds until every targeted direction
    // shows ready, no per-direction partial-fire/partial-hold.)
    wire want_n = routing_mask[0];
    wire want_s = routing_mask[1];
    wire want_e = routing_mask[2];
    wire want_w = routing_mask[3];

    wire targets_all_ready = (!want_n || ready_in_n) &&
                             (!want_s || ready_in_s) &&
                             (!want_e || ready_in_e) &&
                             (!want_w || ready_in_w);

    // A cell with no targeted direction at all (routing_mask==0) is
    // trivially "all ready" — nothing to wait for. Matches the FULL cell's
    // existing convention that an unrouted fire is a legal no-op, not a stall.
    wire can_fire = new_data && ready_bit && targets_all_ready && !freeze_in;

    // ── points.md #90 (option 3 fix): fold any SAME-CYCLE ack into the
    // fire-time snapshot itself, rather than setting pending_ack from
    // targeted_vec alone and checking ack_in only on later cycles. This is
    // the actual bug tb_stripped_v1_2cell.v found: ack_out is a purely
    // combinational pulse tied to the same cycle the fire commits (both
    // driven off the same underlying stimulus window), so a check that only
    // starts looking the cycle AFTER the fire misses an ack that already
    // happened. Computing next_pending_ack combinationally, from whichever
    // path applies THIS cycle, and driving both pending_ack and ready off
    // the SAME computed value closes the exact coincidental-overlap window
    // directly, rather than shifting it by a cycle (rejected option 2). ──
    wire [5:0] targeted_vec = {2'b00, want_w, want_e, want_s, want_n};
    wire [5:0] ack_in_vec   = {2'b00, ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire [5:0] next_pending_ack = can_fire            ? (targeted_vec & ~ack_in_vec) :
                                  (pending_ack != 6'h0) ? (pending_ack  & ~ack_in_vec) :
                                                          pending_ack;
    wire       next_ready = (next_pending_ack == 6'h0);

    always @(posedge clk) begin
        if (!rst && !cfg_valid) begin
            if (capture_now) begin
                data_reg  <= arrived_val;
                a_arrived <= 1'b1;
                // ack_out (above) tells the sender it's clear THIS cycle —
                // no separate confirm step needed on the receive side.
            end else if (can_fire) begin
                cmd_latch[127:96] <= computed_output;  // out_buffer <= new offer
                a_arrived         <= 1'b0;
            end

            // ── points.md #90: pending_ack and ready are now driven off the
            // SAME combinational next-state computation every cycle, whether
            // firing, mid-recovery, or idle — closes the race directly
            // (see next_pending_ack/next_ready above) rather than treating
            // fire and recovery as separate, independently-timed events. ──
            pending_ack   <= next_pending_ack;
            cmd_latch[13] <= next_ready;
        end
    end

    // ── Output distribution (points.md #91): fire_x is now a LEVEL, held by
    // pending_ack[bit_x] — NOT a one-shot pulse off can_fire. This is the
    // second half of the fix: as long as a delivery toward direction x
    // remains genuinely un-acked, the receiver keeps seeing it every cycle
    // and can accept it the moment it's able to, rather than the previous
    // single-cycle window that a blocked receiver could simply miss.
    // pending_ack bit order matches targeted_vec: {2'b00,W,E,S,N}. ──
    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    // ── Command cardinal bus — RESERVED, not implemented this draft ──────
    assign cmd_out_n = 32'h0;
    assign cmd_out_s = 32'h0;
    assign cmd_out_e = 32'h0;
    assign cmd_out_w = 32'h0;

endmodule
