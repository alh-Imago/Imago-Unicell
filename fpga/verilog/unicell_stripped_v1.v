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
    output wire [31:0]  cmd_out_n,   cmd_out_s,   cmd_out_e,   cmd_out_w
);

    // ── State ───────────────────────────────────────────────────────────
    reg [127:0] cmd_latch  = 128'h0;
    reg [31:0]  data_reg   = 32'h0;   // working register — mirrors unicell64_v3.v
    reg         a_arrived  = 1'b0;    // first-arrival latch (two-arrival model)
    reg [3:0]   pending_ack= 4'h0;    // (points.md #89) fire-time snapshot of the
                                      // directions ACTUALLY targeted this fire —
                                      // {W,E,S,N}. ready recovers only when this
                                      // reaches all-zero. A direction never
                                      // targeted is never set here, so it can
                                      // never block recovery — closes the
                                      // "closed direction never confirms"
                                      // deadlock directly.

    wire [9:0] topology     = cmd_latch[9:0];
    wire       ready_bit    = cmd_latch[13];               // this cell's own ready
    wire [5:0] routing_mask = cmd_latch[69:64];             // openness, output side
    wire [5:0] cardinal_edge= cmd_latch[75:70];             // consume(0)/relay(1), per INCOMING dir
    wire [31:0] out_buffer  = cmd_latch[127:96];

    assign ready_out = ready_bit;

    // ── ack_out — asserted the SAME cycle a new arrival is captured into
    // data_reg (the "you're clear on this direction" signal to whichever
    // neighbor actually sent it this cycle, points.md #89). Combinational on
    // the capture condition, not on data_reg itself, so it lands the same
    // cycle the capture happens rather than one cycle late. ──
    wire capture_now = any_arrived && !a_arrived;
    assign ack_out_n = capture_now && arrived_n;
    assign ack_out_s = capture_now && arrived_s;
    assign ack_out_e = capture_now && arrived_e;
    assign ack_out_w = capture_now && arrived_w;

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
    wire can_fire = new_data && ready_bit && targets_all_ready;

    always @(posedge clk) begin
        if (!rst && !cfg_valid) begin
            if (capture_now) begin
                data_reg  <= arrived_val;
                a_arrived <= 1'b1;
                // ack_out (above) tells the sender it's clear THIS cycle —
                // no separate confirm step needed on the receive side.
            end else if (can_fire) begin
                cmd_latch[127:96] <= computed_output;  // out_buffer <= new offer
                cmd_latch[13]     <= 1'b0;             // no longer ready — awaiting ack(s)
                pending_ack       <= {want_w, want_e, want_s, want_n}; // fire-time
                                      // snapshot (points.md #89) — ONLY directions
                                      // actually targeted this fire are set; a
                                      // direction that was never targeted is never
                                      // waited on.
                a_arrived         <= 1'b0;
            end
            // can_fire held false by a not-yet-ready target: new_data stays
            // true, a_arrived stays set, nothing drains — this IS the stall,
            // with no separate mechanism needed (same structural argument
            // as points.md #77 for the FULL cell).

            // ── Ready recovery (points.md #89): clear each pending_ack bit
            // as its ack_in arrives; ready sets again only once ALL bits
            // that were actually set at fire time have cleared. A closed
            // direction was never set here, so it can never block recovery;
            // an open, targeted direction genuinely must be told before
            // recovery happens — never inferred. ──
            if (pending_ack != 4'h0) begin
                pending_ack <= pending_ack & ~{ack_in_w, ack_in_e, ack_in_s, ack_in_n};
                if ((pending_ack & ~{ack_in_w, ack_in_e, ack_in_s, ack_in_n}) == 4'h0)
                    cmd_latch[13] <= 1'b1;  // last outstanding ack just arrived — ready again
            end
        end
    end

    // ── Output distribution — fire only toward targeted, ready directions ──
    assign fire_n = can_fire && want_n;
    assign fire_s = can_fire && want_s;
    assign fire_e = can_fire && want_e;
    assign fire_w = can_fire && want_w;

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
