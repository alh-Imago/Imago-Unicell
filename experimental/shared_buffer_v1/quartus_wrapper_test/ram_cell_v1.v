// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// ram_cell_v1.v — first real RTL draft of the RAM cell (points.md #231-#234).
// NOT YET CONFIRMED BY ALAN — he asked to review the read/write mechanism
// himself before this is trusted. NOT YET SIMULATED AGAINST QUARTUS. Only
// iverilog sim run so far (tb_ram_cell_v1_fixed.v, tb_ram_cell_v1_chain.v);
// see points.md #235 for those results and everything still open.
//
// WHAT THIS IS (points.md #233): a genuinely DIFFERENT cell type from
// unicell_stripped_v1.v, not a config variant of it. No NOR-tree, no
// two-arrival gate computation, no topology field — just a single 32-bit
// latch plus the minimum handshake state needed to move it through a
// chain. Deliberately excludes everything unicell_stripped_v1.v has that
// this cell doesn't need: hold/reemit/update/self-update, internal
// feedback, dynamic routing, the programming channel, command-cell mode.
// Adding any of those back is new scope, not an oversight.
//
// THE MECHANISM (points.md #231), stated in RTL terms: chain direction is
// fixed at config time via downstream_mask/upstream_mask (routing_mask-
// style one-hot fields, same convention unicell_stripped_v1.v already uses
// — points.md #231's own framing: "same mechanism as routing_mask/
// cardinal_edge already use"). The "pull" is NOT a new active request
// signal — it falls straight out of the existing ready/ack fabric: this
// cell's ready_out is simply !data_valid (empty = able to receive). The
// moment a downstream delivery is fully acked, data_valid clears (flowing
// mode only) and ready_out goes high on its own the very next cycle —
// which is exactly the event an upstream neighbor's own targets_all_ready
// check is already watching for. No dedicated pull-request wire exists
// anywhere in this module; the passive readiness broadcast IS the request,
// precisely as points.md #231 described it.
//
// FIXED vs FLOWING (points.md #231): fixed_mode=1 loads a permanent value
// at cfg time (data_valid forced high, never clears) and re-offers it
// indefinitely, ROM-style — it never re-enters capture and therefore
// never asserts ready_out again. fixed_mode=0 is the ordinary consumed-
// and-refilled case.
//
// cfg_data[63:0] field map (first proposal, NOT frozen — flag any change
// needed after Alan reviews):
//   [3:0]   downstream_mask  — one-hot(s), N/S/E/W, routing_mask convention
//   [7:4]   upstream_mask    — one-hot(s), N/S/E/W, same convention
//   [8]     fixed_mode       — 1=permanent ROM-style, 0=flowing
//   [9]     load_data_valid  — mark data_reg valid immediately on this load
//   [41:10] init_data[31:0]  — preset value
//   [63:42] reserved         — future: programming-channel wiring, BRAM-
//                              port fields (points.md #232), not designed yet
//
// NOT YET SOLVED (points.md #232): what a chain-terminal cell (downstream_
// mask==4'h0, i.e. the head of a chain feeding a real BRAM port rather than
// another cardinal neighbor) actually wires into. This draft leaves that
// case inert on purpose — data_out_x/status_data_valid are plain
// combinational taps a future BRAM-interface module could read directly,
// but that module doesn't exist yet. Flagged, not solved.
`default_nettype none
`timescale 1ns / 1ps

module ram_cell_v1 #(
    parameter [15:0] CELL_ID = 16'h0000  // fixed grid position, identification only
) (
    input  wire        clk,
    input  wire         rst,

    // ── Boot-time config load — same stand-in convention as
    // unicell_stripped_v1.v's own cfg_valid/cfg_data (plain synchronous
    // load, no address match). Wiring to the real loader mechanism is
    // separate follow-on work, same as that module's own note. ──
    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    // ── Cardinal data ports — identical shape to unicell_stripped_v1.v so
    // this cell can sit in the same grid wiring / wrapper infrastructure. ──
    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    // ── Ready — broadcast unconditionally like unicell_stripped_v1.v's own
    // ready_out, but a DIFFERENT meaning here: !data_valid (this cell has
    // an empty slot to receive), not "my previous offer finished draining."
    // This is the whole pull mechanism (see header) — no separate signal. ──
    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    // ── Read-confirmation, same convention as unicell_stripped_v1.v:
    // asserted the cycle a genuine consume happens on that direction. ──
    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    // ── Debug/introspection only — not part of the handshake. Cheap, and
    // directly useful for the workbench chain-stall watching points.md
    // #154 already anticipated for this exact purpose. ──
    output wire         status_data_valid
);

    // ── State ───────────────────────────────────────────────────────────
    reg [31:0] data_reg        = 32'h0;
    reg        data_valid      = 1'b0;
    reg [3:0]  downstream_mask = 4'h0;
    reg [3:0]  upstream_mask   = 4'h0;
    reg        fixed_mode      = 1'b0;
    reg [3:0]  pending_ack     = 4'h0;  // downstream offer, level-held until
                                         // acked — same discipline as
                                         // unicell_stripped_v1.v's own
                                         // pending_ack (points.md #91), not
                                         // a one-shot pulse a blocked
                                         // receiver could miss.

    wire effective_freeze = freeze_in;

    // ── Upstream capture (refill). Only accepted while genuinely empty and
    // not fixed — a fixed cell never re-enters this path at all. Reuses the
    // same independent-per-direction OR-combine style unicell_stripped_v1.v
    // uses (points.md #153), though a simple chain is expected to have
    // exactly one upstream_mask bit set. ──
    wire ram_sel_n = arrived_n && upstream_mask[0];
    wire ram_sel_s = arrived_s && upstream_mask[1];
    wire ram_sel_e = arrived_e && upstream_mask[2];
    wire ram_sel_w = arrived_w && upstream_mask[3];
    wire ram_any_upstream_arrived = ram_sel_n | ram_sel_s | ram_sel_e | ram_sel_w;
    wire [31:0] upstream_val = (ram_sel_n ? data_in_n : 32'h0) |
                               (ram_sel_s ? data_in_s : 32'h0) |
                               (ram_sel_e ? data_in_e : 32'h0) |
                               (ram_sel_w ? data_in_w : 32'h0);

    wire capture_now = ram_any_upstream_arrived && !data_valid && !fixed_mode && !effective_freeze;

    assign ack_out_n = capture_now && ram_sel_n;
    assign ack_out_s = capture_now && ram_sel_s;
    assign ack_out_e = capture_now && ram_sel_e;
    assign ack_out_w = capture_now && ram_sel_w;

    // ── Downstream offering. want_to_offer is just "I'm holding something"
    // — a RAM cell has nothing to compute, so there's no separate
    // "computed_output," data_reg itself IS the offer. ──
    wire want_to_offer = data_valid && !effective_freeze;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    // bit order matches downstream_mask/upstream_mask throughout this
    // module: bit0=N,1=S,2=E,3=W — same convention unicell_stripped_v1.v
    // uses for routing_mask/cardinal_edge/targeted_vec.
    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;

    // The cycle the last outstanding targeted ack lands, pending_ack goes
    // nonzero->zero. That transition IS "downstream just took my value" —
    // in flowing mode this is what clears data_valid, which is what makes
    // ready_out go high next cycle, which is the entire "pull" (see
    // header). No separate request signal anywhere.
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = data_reg;
    assign data_out_s = data_reg;
    assign data_out_e = data_reg;
    assign data_out_w = data_reg;

    assign ready_out = !data_valid && !fixed_mode && !effective_freeze;
    assign status_data_valid = data_valid;

    always @(posedge clk) begin
        if (rst) begin
            data_reg        <= 32'h0;
            data_valid      <= 1'b0;
            downstream_mask <= 4'h0;
            upstream_mask   <= 4'h0;
            fixed_mode      <= 1'b0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[3:0];
            upstream_mask   <= cfg_data[7:4];
            fixed_mode      <= cfg_data[8];
            data_valid      <= cfg_data[9];
            data_reg        <= cfg_data[41:10];
            pending_ack     <= 4'h0;  // fresh config clears any stale offer,
                                       // same discipline as unicell_stripped_v1.v
        end else begin
            if (capture_now) begin
                data_reg   <= upstream_val;
                data_valid <= 1'b1;
            end else if (!fixed_mode && offer_draining) begin
                data_valid <= 1'b0;
            end
            pending_ack <= next_pending_ack;
        end
    end

endmodule
