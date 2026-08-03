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
    input  wire         freeze_in,

    // ── Hold (points.md #115) — low=normal (current auto-clear behavior,
    // unchanged), high=held. While held, the first-arrival value
    // (data_reg) stays latched across MULTIPLE fires instead of clearing
    // after each one -- the cell keeps auto-firing against every NEW
    // arrival, continuously comparing against the SAME held value. This
    // is the ONLY behavioral change hold_in makes: a_arrived's existing
    // auto-clear-on-fire becomes conditional on !hold_in. Gives a live,
    // continuously-updating comparator (a threshold, an LIF-style
    // accumulator base, etc.) entirely in-fabric, with zero host round-
    // trip per comparison -- release (hold_in returning low) is the only
    // host-mediated event, needed only when the held value itself must
    // change. ──
    input  wire         hold_in,

    // ── Internal feedback (points.md #118) — genuinely SEPARATE path from
    // normal delivery/ack, per Alan: internal (same-cell) feedback needs
    // its own mechanism; feedback arriving from ANOTHER cell keeps using
    // the existing, already-proven cardinal delivery/ack path unchanged.
    // While hold_in && fb_internal_in (and not frozen), the SECOND operand
    // is drawn directly from this cell's own out_buffer (its last result)
    // instead of an external arrival, recomputing every cycle -- no ports
    // beyond this one bit, no ack, no pending_ack involvement at all. This
    // is what closes the self-loop deadlock found in
    // tb_stripped_v1_feedback.v: that deadlock came from forcing a genuine
    // internal recurrence through the ack mechanism built for two
    // INDEPENDENT cells, which cannot correctly distinguish a real prior
    // ack from a same-cell fire spuriously acknowledging itself. ──
    input  wire         fb_internal_in,

    // ── A-passthrough / update (points.md #119) — the last two pieces
    // needed for a genuine persistent, updatable memory cell. Space freed
    // up in cmd_latch's field map now that the command-cell-address-chain
    // idea (#100/#110) was set aside per #114 in favor of the wrapper's
    // existing 3-word update system plus these simple control lines.
    //
    // a_reemit_in: while held, an arriving trigger (value ignored) causes
    // the HELD value (data_reg / A) itself to be pushed to out_buffer,
    // UNPROCESSED — no gate computation at all, distinct from relay_fire
    // (#94, which pushes the ARRIVING value B, ignoring A entirely). This
    // is the genuine "does it just re-emit A" case, separate from #118's
    // internal feedback (which recomputes a gate each cycle).
    //
    // a_update_in: while held, an arriving value REPLACES A (data_reg)
    // directly, instead of triggering a re-emit or a gate computation —
    // the actual write/update path, the one piece that didn't already
    // exist anywhere (checked directly: #37's FULL-cell CMD_MEM_CALL
    // re-arms wholesale, it doesn't do an in-place flush-and-replace
    // either). ──
    input  wire         a_reemit_in,
    input  wire         a_update_in,

    // ── Self-updating threshold (points.md #120) — the "smarter RAM"
    // extension: while internal_fb_active (#118) is running, this bit
    // decides where the computed result goes. Low (default): unchanged
    // #118 behavior, the result oscillates in out_buffer, A stays fixed.
    // High: the SAME computed gate(A, out_buffer) result instead REPLACES
    // A directly — the threshold itself evolves based on its own
    // accumulated history, a genuine self-adjusting accumulator, not just
    // a held constant being compared against. Reading the current A out
    // on demand still uses the existing a_reemit_in path (#119) — meant
    // to be used in sequence (self-update running, then briefly paused
    // via fb_internal_in to read via reemit), not simultaneously, same
    // composition discipline already proven for update+reemit. ──
    input  wire         a_self_update_in,

    // ── program_in / program_done (points.md #123) — the rebuilt, correct
    // command-cell mechanism. Genuinely single-hop, data-source-agnostic:
    // whatever asserts program_in doesn't need to carry or know the config
    // data itself — the 3 words can arrive from ANY direction, ANY sender,
    // via this cell's completely ordinary data_in ports. The target cannot
    // and does not need to distinguish "normal data" from "config data"
    // except via this one control line. While held high, the NEXT 3
    // arrivals (any direction, same sel_n/s/e/w priority already used
    // everywhere else) are redirected into a 3-word assembly buffer
    // instead of the normal two-arrival gate — genuinely suspending
    // ordinary operation, not layering on top of it. Each word consumed
    // generates the EXISTING ack_out_x for free (#91), telling the actual
    // data sender its word landed — no new mechanism needed there.
    // program_done is a SEPARATE signal (broadcast to all 4 directions
    // unconditionally, mirroring ready_out's own convention — #88's
    // reasoning: whoever holds program_in could be on any side, so the
    // completion signal must reach all of them, not just the data's own
    // source direction). Stays high until program_in itself drops. ──
    input  wire         program_in,
    output wire         program_done,

    // ── Dedicated programming data channel (points.md #132, option 1) —
    // genuinely separate from the ordinary cardinal data_in ports, not
    // muxed/shared. Built specifically to test whether sharing the
    // cardinal port (the original #123/#130 design) was itself the real
    // Fmax cost, or whether the cost was already inherent in reusing the
    // same internal priority-select/ack machinery regardless of the
    // external port. If this alone doesn't recover step 1's Fmax, the
    // internal path needs separating too (option 2), same discipline as
    // fb_internal_in's own separate path (#118). ──
    input  wire [31:0]  prog_data_in,
    input  wire         prog_arrived_in,
    output wire         prog_ack_out
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

    // ── points.md #123: 3-word assembly buffer for program_in mode. ──
    reg [1:0]  prog_word_idx = 2'h0;
    reg [95:0] prog_assemble = 96'h0;
    reg        program_done_r = 1'b0;

    wire [9:0] topology     = cmd_latch[9:0];
    wire       ready_bit    = cmd_latch[13];               // this cell's own ready
    wire [5:0] routing_mask = cmd_latch[69:64];             // openness, output side
    wire [5:0] cardinal_edge= cmd_latch[75:70];             // consume(0)/relay(1), per INCOMING dir
    wire [31:0] out_buffer  = cmd_latch[127:96];

    assign ready_out = ready_bit;
    assign program_done = program_done_r;
    // ── points.md #132: dedicated ack for the programming channel — no
    // longer riding the shared cardinal ack_out_x (that path is now purely
    // for ordinary data, since programming has its own port entirely). ──
    assign prog_ack_out = programming_active;

    // ── points.md #123: programming_active — genuinely TOP priority,
    // suspends ordinary operation entirely (not layered on top of it).
    // Any arrival, any direction, while program_in is held — reuses the
    // SAME priority-select and any_arrived already built for everything
    // else, no new arrival-detection logic needed. ──
    wire programming_active = program_in && prog_arrived_in && (prog_word_idx != 2'd3);
    // (prog_word_idx never actually reaches 3 — reset to 0 after word 2 —
    // this guard is defensive only, kept simple rather than clever.)

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
    wire consumed_now = capture_now || can_fire || relay_fire || a_reemit_active || a_update_active;
    assign ack_out_n = consumed_now && sel_n;
    assign ack_out_s = consumed_now && sel_s;
    assign ack_out_e = consumed_now && sel_e;
    assign ack_out_w = consumed_now && sel_w;

    // (reset/cfg_valid/capture/fire/pending_ack are ALL merged into ONE
    // always block further below — points.md #96. Two separate always
    // blocks both driving cmd_latch simulated fine in Icarus but is
    // illegal for synthesis: "multiple constant drivers," caught by
    // Quartus, not by sim. A single register must be driven by exactly
    // one process.)

    // ── Incoming arrival, any direction. cardinal_edge (points.md #94)
    // classifies the SELECTED direction's event as consume (participate in
    // the two-arrival gate below) or relay (pure pass-through, see
    // selected_is_relay/relay_arrived/relay_fire further down). ──
    wire any_arrived = arrived_n | arrived_s | arrived_e | arrived_w;
    wire [31:0] arrived_val = arrived_n ? data_in_n :
                              arrived_s ? data_in_s :
                              arrived_e ? data_in_e :
                                          data_in_w;
    wire capture_now = consume_arrived && !a_arrived && !freeze_in && !program_in;

    // ── points.md #94: relay vs consume classification, per the automaton
    // actually selected this cycle (sel_n/s/e/w above), decides whether this
    // cell CONSUMES the arrival (normal two-arrival participation, cardinal_
    // edge bit=0) or RELAYS it (pure pass-through using THIS cell's own
    // routing_mask, cardinal_edge bit=1) — the same "conduit vs participant"
    // distinction #32/#58 established for zone-boundary transit cells,
    // applied per-hop here instead. cardinal_edge bit order matches
    // routing_mask's own (bit0=N,1=S,2=E,3=W). A relayed value NEVER
    // becomes a_data/computation input — it goes straight to out_buffer
    // unprocessed, exactly like #76 specified. ──
    wire selected_is_relay = (sel_n && cardinal_edge[0]) ||
                             (sel_s && cardinal_edge[1]) ||
                             (sel_e && cardinal_edge[2]) ||
                             (sel_w && cardinal_edge[3]);
    wire relay_arrived   = any_arrived && selected_is_relay;
    wire consume_arrived = any_arrived && !selected_is_relay;

    // ── Internal feedback mode (points.md #118): while active, second_val
    // is drawn from THIS cell's own out_buffer (its last result), not an
    // external arrival — genuinely separate path, per Alan. ──
    wire internal_fb_active = hold_in && fb_internal_in && !freeze_in && !program_in;

    // ── points.md #119: the two remaining memory-cell pieces. ──
    // a_reemit: pure pass-through of A (data_reg), trigger's own value
    // ignored. Writes the shared out_buffer, so respects the SAME
    // ready_bit/targets_all_ready gating as can_fire/relay_fire — a
    // re-emit attempt must stall too if the buffer is still occupied.
    wire a_reemit_active = hold_in && a_reemit_in && consume_arrived &&
                           ready_bit && targets_all_ready && !freeze_in && !program_in;
    // a_update: arriving value REPLACES A directly. Does NOT write
    // out_buffer at all (a separate action from emitting), so does not
    // need ready_bit gating — updating the held constant and offering it
    // downstream are deliberately independent steps.
    wire a_update_active = hold_in && a_update_in && consume_arrived && !freeze_in && !program_in;

    // ── Two-arrival gate computation — UNCHANGED from unicell64_v3.v ──────
    wire [31:0] input_val  = a_arrived ? data_reg : arrived_val;
    wire [31:0] second_val = internal_fb_active ? out_buffer :
                              (a_arrived ? arrived_val : data_reg);

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

    wire new_data = consume_arrived && a_arrived;  // second arrival fires (consume path only)

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
    wire can_fire = new_data && ready_bit && targets_all_ready && !freeze_in && !program_in;

    // ── points.md #94: relay_fire — the RELAY counterpart to can_fire.
    // Single-arrival, immediate forward: no a_arrived/data_reg involvement
    // at all, since a relayed value never becomes this cell's own
    // computation input. Still gated by ready_bit/targets_all_ready/
    // freeze_in exactly like can_fire, because it writes the SAME shared
    // out_buffer — a relay attempt must stall just as a compute fire would
    // if the buffer is still occupied, rather than clobbering an
    // outstanding offer. ──
    wire relay_fire = relay_arrived && ready_bit && targets_all_ready && !freeze_in && !program_in;

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
    wire       any_fire     = can_fire || relay_fire || a_reemit_active;
    wire [5:0] next_pending_ack = any_fire            ? (targeted_vec & ~ack_in_vec) :
                                  (pending_ack != 6'h0) ? (pending_ack  & ~ack_in_vec) :
                                                          pending_ack;
    wire       next_ready = hold_in || (next_pending_ack == 6'h0);
    // points.md #117: while held, ready is treated as PERMANENTLY
    // pre-satisfied, not gated by the normal ack round-trip. Rationale
    // (Alan): once held, the cell's role changes -- the first operand is
    // already resident (no "delivery" to wait on), so the cell doesn't
    // need external ack confirmation to keep re-firing. This is what
    // closes the self-loop deadlock found in tb_stripped_v1_feedback.v:
    // a held cell consuming its OWN output could never generate the ack
    // that would clear its own pending_ack, since capture_now is disabled
    // by hold and can_fire was gated on that same ack. Forcing ready=1
    // while held removes the dependency entirely -- the cell simply
    // fires on every new arrival, continuously, exactly matching the
    // comparator/threshold role hold_in exists for.

    // ── points.md #96: merged into ONE always block, since a register can
    // only be driven by a single process for synthesis. rst/cfg_valid/
    // capture/fire/pending_ack all handled here now, in that priority
    // order, matching the original intent exactly — nothing about the
    // logic changed, only that it's now one process instead of two. ──
    always @(posedge clk) begin
        if (rst) begin
            cmd_latch     <= 128'h0;
            data_reg      <= 32'h0;
            a_arrived     <= 1'b0;
            pending_ack   <= 6'h0;
            prog_word_idx <= 2'h0;
            prog_assemble <= 96'h0;
            program_done_r<= 1'b0;
        end else if (cfg_valid) begin
            // Boot-time load only — see module header note on loader integration.
            cmd_latch     <= cfg_data;
            cmd_latch[13] <= 1'b1;  // a freshly-configured cell starts ready
            pending_ack   <= 6'h0;  // a fresh config clears any stale pending offer
        end else begin
            if (programming_active) begin
                // points.md #123: TOP priority, genuinely suspends ordinary
                // operation (can_fire/relay_fire/etc are already gated off
                // by !program_in in their own definitions, so there's no
                // possibility of this branch and a normal fire both trying
                // to commit the same cycle). Same 3-word packing convention
                // already proven in cell_wrapper_v1.v/cell_cardinal_cmd_v1.v
                // (word0=[31:0], word1=[63:32], word2=[95:64]) — applied to
                // cmd_latch's meaningful 96 bits the SAME safe way cfg_valid
                // already does, on the 3rd word.
                case (prog_word_idx)
                    2'd0: prog_assemble[31:0]  <= prog_data_in;
                    2'd1: prog_assemble[63:32] <= prog_data_in;
                    2'd2: begin
                        prog_assemble[95:64] <= prog_data_in;
                        cmd_latch[95:0]      <= {prog_data_in, prog_assemble[63:32], prog_assemble[31:0]};
                        cmd_latch[13]        <= 1'b1;  // freshly programmed, ready
                        program_done_r       <= 1'b1;
                    end
                endcase
                prog_word_idx <= (prog_word_idx == 2'd2) ? 2'd0 : (prog_word_idx + 2'd1);
            end else if (internal_fb_active) begin
                // points.md #118/#120: genuinely separate path. No
                // a_arrived change (stays held), no pending_ack/ack
                // involvement at all. a_self_update_in decides the
                // destination: out_buffer (unchanged #118 oscillation,
                // A stays fixed) or A itself (#120 — the threshold
                // self-adjusts based on its own accumulated history).
                if (a_self_update_in)
                    data_reg <= computed_output;
                else
                    cmd_latch[127:96] <= computed_output;
            end else if (a_update_active) begin
                // points.md #119: the write path. Arriving value REPLACES
                // A directly — a_arrived is already 1 (held, required to
                // reach this branch at all), left unchanged.
                data_reg <= arrived_val;
            end else if (a_reemit_active) begin
                // points.md #119: pure pass-through of A, unprocessed —
                // the trigger's own VALUE is ignored entirely, only its
                // arrival matters.
                cmd_latch[127:96] <= data_reg;
            end else if (capture_now) begin
                data_reg  <= arrived_val;
                a_arrived <= 1'b1;
                // ack_out (above) tells the sender it's clear THIS cycle —
                // no separate confirm step needed on the receive side.
            end else if (can_fire) begin
                cmd_latch[127:96] <= computed_output;  // out_buffer <= new offer
                a_arrived         <= hold_in;  // points.md #115: normally clears
                                                // (hold_in=0, unchanged behavior);
                                                // held (hold_in=1), STAYS latched,
                                                // so the same first-arrival value
                                                // keeps comparing against every
                                                // new incoming second-arrival.
            end else if (relay_fire) begin
                cmd_latch[127:96] <= arrived_val;  // out_buffer <= RAW pass-through
                                                    // value, never touched a_data/
                                                    // computed_output at all (#94)
            end

            // ── points.md #123: program_done_r resets once program_in
            // itself drops — the source has seen completion and released
            // the line, ready for next use. Mutually exclusive with the
            // programming_active branch setting it (that only happens
            // while program_in IS high), so no same-cycle conflict. ──
            if (!program_in) program_done_r <= 1'b0;

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
