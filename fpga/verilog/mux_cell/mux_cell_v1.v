// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mux_cell_v1.v — first real RTL draft of the distribution tree's mux
// core (points.md #257/#258's design). DRAFT — sim-verified only, no
// Quartus data yet.
//
// SHELL: same cardinal ports every core here uses, but ONE direction is
// reserved as the fixed upstream input (where DATA+ROUTING arrive from
// a mem_read_splitter_v1.v or a parent mux node), leaving exactly 3
// usable output faces — the real constraint `#258` corrected (every
// node has 4 cardinal faces total, one is always consumed by the
// upstream connection).
//
// ROUTING FIELD, per `#258`'s corrected hierarchical scheme — 8 bits,
// bit layout fixed here (not previously pinned down to exact bit
// positions in the design note):
//   [7:6] count   — 0-3, directly the number of dynamic levels
//                   remaining, no reserved/overloaded values
//   [5:4] slot1   — face selection used when count==1
//   [3:2] slot2   — face selection used when count==2
//   [1:0] slot3   — face selection used when count==3
// A node reads whichever slot the CURRENT count value indexes, decodes
// the 2-bit slot value into ONE of its 3 usable output faces, offers
// DATA there through the ordinary cardinal path, and forwards the
// WHOLE 8-bit field with only `count` decremented by 1 — no bit
// shifting, the other two slots ride along untouched for the next node
// down to use. `#258`'s own reasoning: count==0 on arrival here would
// mean routing was already complete before reaching this node (an
// address error, not a valid case for a mux to receive) — this module
// does not attempt to handle it specially, per the "no reserved
// values" decision.
//
// FACE MAPPING is CONFIG-TIME, not hardcoded — the same physical module
// needs to work at any position in a tree, where "which direction is
// upstream" and "which 3 directions are the outputs, and which slot
// code maps to which of them" differ per instance. `cfg_data` carries
// this exactly like `downstream_mask`/`upstream_mask` do everywhere
// else in this project.
//
// cfg_data[63:0] field map:
//   [3:0]   upstream_mask     — single direction DATA+ROUTING arrive
//                               from (exactly one bit set)
//   [7:4]   face_for_slot0    — one-hot direction for 2-bit slot code 00
//   [11:8]  face_for_slot1    — one-hot direction for 2-bit slot code 01
//   [15:12] face_for_slot2    — one-hot direction for 2-bit slot code 10
//                               (slot code 11 is simply unused/invalid
//                               — 3 real faces, 4 possible codes, no
//                               special handling needed for the 4th)
//   [63:16] reserved
//
// TIMING: DATA and its ROUTING field are captured TOGETHER off the same
// arrival, exactly matching `#260`'s own established property that
// `mem_read_splitter_v1.v`'s `routing_out` is stable through the whole
// window its `data_valid` is asserted — this module reads both at
// capture time, same cycle, no separate synchronization needed.
`default_nettype none
`timescale 1ns / 1ps

module mux_cell_v1 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,
    // The routing field rides in ALONGSIDE the cardinal data ports —
    // one dedicated 8-bit input per direction, matching
    // mem_read_splitter_v1.v's own dedicated (non-cardinal) routing_out
    // port. Only the routing_in on whichever direction actually arrives
    // (per upstream_mask) is used in a given cycle.
    input  wire [7:0]   routing_in_n, routing_in_s, routing_in_e, routing_in_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,
    // Forwarded routing field — the same decrement-and-pass-through
    // value, driven on ALL four directions (only the one actually
    // wired to a next-level mux node, if any, matters; a leaf/header
    // cell downstream simply never reads it — same "don't care" pattern
    // every unused cardinal port already has elsewhere in this project).
    output wire [7:0]   routing_out,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    output wire         status_data_valid
);

    // ── State ───────────────────────────────────────────────────────────
    reg [31:0] out_buffer       = 32'h0;
    reg [7:0]  routing_reg      = 8'h0;
    reg        data_valid       = 1'b0;
    reg [3:0]  upstream_mask    = 4'h0;
    reg [3:0]  face_for_slot0   = 4'h0;
    reg [3:0]  face_for_slot1   = 4'h0;
    reg [3:0]  face_for_slot2   = 4'h0;
    reg [3:0]  pending_ack      = 4'h0;

    wire effective_freeze = freeze_in;

    // ── Upstream arrival selection — same convention as every core
    // here, but exactly one direction bit is expected set in
    // upstream_mask (the mux's single reserved input face). ──
    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);
    wire [7:0]  upstream_routing = (sel_n ? routing_in_n : 8'h0) |
                                   (sel_s ? routing_in_s : 8'h0) |
                                   (sel_e ? routing_in_e : 8'h0) |
                                   (sel_w ? routing_in_w : 8'h0);

    // Doubly-full guard (same `#256` fix as every other core here) —
    // don't capture a new transaction while a previous one is still
    // undrained.
    wire capture_now = any_upstream_arrived && !data_valid && !effective_freeze;

    assign ack_out_n = capture_now && sel_n;
    assign ack_out_s = capture_now && sel_s;
    assign ack_out_e = capture_now && sel_e;
    assign ack_out_w = capture_now && sel_w;

    // ── The decode — this IS the mux core, points.md #258 ──────────────
    wire [1:0] cur_count = upstream_routing[7:6];
    wire [1:0] cur_slot  = (cur_count == 2'd1) ? upstream_routing[5:4] :
                           (cur_count == 2'd2) ? upstream_routing[3:2] :
                           (cur_count == 2'd3) ? upstream_routing[1:0] :
                                                  2'b00;   // count==0 — not a valid arrival, see header
    wire [3:0] selected_face = (cur_slot == 2'b00) ? face_for_slot0 :
                               (cur_slot == 2'b01) ? face_for_slot1 :
                               (cur_slot == 2'b10) ? face_for_slot2 :
                                                      4'h0;  // slot code 11 — unused/invalid, no mapping

    wire [1:0] next_count = (cur_count == 2'd0) ? 2'd0 : (cur_count - 2'd1);
    wire [7:0] next_routing = {next_count, upstream_routing[5:0]};   // decrement only, slots untouched

    // ── Downstream offering — the SELECTED face is the dynamic
    // downstream_mask, computed fresh per transaction, exactly the one
    // genuinely new mechanism beyond every static-mask core built
    // before this. ──
    wire want_to_offer = data_valid && !effective_freeze;
    // downstream_mask is LATCHED at capture time into a real register
    // (downstream_mask_reg, declared+driven below) — upstream_routing/
    // selected_face are only valid during the capture cycle itself,
    // same as upstream_val; downstream_mask needs to stay stable for
    // the WHOLE offer/drain window, exactly like every other core's own
    // static downstream_mask does. (An earlier draft declared this as
    // a plain wire tied straight to selected_face AND separately tried
    // to drive it from a register — a genuine double-driver bug, caught
    // before ever compiling.)
    wire [3:0] downstream_mask;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
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
    assign routing_out = routing_reg;

    assign ready_out = !effective_freeze && !data_valid;
    assign status_data_valid = data_valid;

    reg [3:0] downstream_mask_reg = 4'h0;
    assign downstream_mask = downstream_mask_reg;

    always @(posedge clk) begin
        if (rst) begin
            out_buffer         <= 32'h0;
            routing_reg        <= 8'h0;
            data_valid         <= 1'b0;
            upstream_mask      <= 4'h0;
            face_for_slot0     <= 4'h0;
            face_for_slot1     <= 4'h0;
            face_for_slot2     <= 4'h0;
            pending_ack        <= 4'h0;
            downstream_mask_reg <= 4'h0;
        end else if (cfg_valid) begin
            upstream_mask       <= cfg_data[3:0];
            face_for_slot0      <= cfg_data[7:4];
            face_for_slot1      <= cfg_data[11:8];
            face_for_slot2      <= cfg_data[15:12];
            data_valid          <= 1'b0;
            pending_ack         <= 4'h0;
            downstream_mask_reg <= 4'h0;
        end else begin
            if (capture_now) begin
                out_buffer          <= upstream_val;
                routing_reg         <= next_routing;
                downstream_mask_reg <= selected_face;
                data_valid          <= 1'b1;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end

            pending_ack <= next_pending_ack;
        end
    end

endmodule
