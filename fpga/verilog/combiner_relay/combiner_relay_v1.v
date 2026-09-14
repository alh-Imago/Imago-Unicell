// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// combiner_relay_v1.v — the CHILD/leaf node for a combiner TREE
// (points.md #257/#258, extending #268's single-level `combiner_cell_
// v1.v`). DRAFT — sim-verified only, no Quartus data yet.
//
// `combiner_cell_v1.v` writes directly to `bram_controller_v1.v` via
// dedicated `wr_cmd_*` ports — correct for a tree's ROOT, but a CHILD
// node needs to hand its captured, stamped word UP to a parent through
// the ordinary cardinal offer/drain mechanism, exactly mirroring how
// `mux_cell_v1.v`'s `routing_out` works on the read side (points.md
// #266) — a normal 32-bit cardinal data port plus a dedicated 8-bit
// routing companion, no new protocol.
//
// SAME capture mechanism as `combiner_cell_v1.v`, unchanged: a
// chain-select counter scans up to 3 configured input faces in FIXED,
// unconditional round-robin order (Alan's own choice — never wait on a
// slow/empty chain), stamps the counter's own current position as the
// slot ID, `{count=1, slot=position, 00, 00}` exactly matching
// `combiner_cell_v1.v`'s own write-format convention. The DIFFERENCE is
// only in what happens to that captured word next: instead of an
// immediate `wr_cmd_valid` pulse, it's held in `out_buffer`/
// `routing_reg` and OFFERED upward through one configured direction,
// using the standard offer/drain (`pending_ack`/`data_valid`) mechanism
// every other core here already has.
//
// A real consequence, not glossed over: the input-side scan is STILL
// unconditional (advances every cycle regardless of downstream state),
// but capture itself is gated on `!data_valid` (the same "doubly full"
// guard `#256` established) — so if this relay's own upward offer
// hasn't drained yet, a chain arriving during that window is correctly
// NOT captured on that pass and simply gets picked up on the next full
// rotation instead (the chain itself holds its own offer via its own
// ack/fire discipline until genuinely consumed — nothing is silently
// lost, just delayed).
//
// cfg_data[63:0] field map:
//   [3:0]   upstream_mask     — the single direction toward the parent
//                               combiner (exactly one bit set)
//   [7:4]   chain_for_slot0   — one-hot direction checked at position 0
//   [11:8]  chain_for_slot1   — one-hot direction checked at position 1
//   [15:12] chain_for_slot2   — one-hot direction checked at position 2
//   [63:16] reserved
`default_nettype none
`timescale 1ns / 1ps

module combiner_relay_v1 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,

    // ── Upward offer toward the parent combiner — cardinal data on ALL
    // four directions (only the one actually wired to the parent
    // matters, same "unused ports are don't-care" pattern every core
    // here already has), plus the dedicated routing companion. ──
    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,
    output wire [7:0]   routing_out,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    output wire [1:0]   status_slot,
    output wire         status_data_valid
);

    reg [3:0] upstream_mask   = 4'h0;
    reg [3:0] chain_for_slot0 = 4'h0;
    reg [3:0] chain_for_slot1 = 4'h0;
    reg [3:0] chain_for_slot2 = 4'h0;

    wire effective_freeze = freeze_in;

    // ── Same round-robin chain-select scan as combiner_cell_v1.v ──────
    reg [1:0] slot = 2'd0;
    wire [3:0] slot_direction = (slot == 2'd0) ? chain_for_slot0 :
                                (slot == 2'd1) ? chain_for_slot1 :
                                                  chain_for_slot2;

    wire slot_arrived = (slot_direction[0] && arrived_n) ||
                        (slot_direction[1] && arrived_s) ||
                        (slot_direction[2] && arrived_e) ||
                        (slot_direction[3] && arrived_w);
    wire [31:0] slot_data = (slot_direction[0] ? data_in_n : 32'h0) |
                            (slot_direction[1] ? data_in_s : 32'h0) |
                            (slot_direction[2] ? data_in_e : 32'h0) |
                            (slot_direction[3] ? data_in_w : 32'h0);

    // ── State for the upward offer — same shape as mux_cell_v1.v's own
    // out_buffer/routing_reg/data_valid/pending_ack. ──
    reg [31:0] out_buffer  = 32'h0;
    reg [7:0]  routing_reg = 8'h0;
    reg        data_valid  = 1'b0;
    reg [3:0]  pending_ack = 4'h0;

    // Doubly-full guard: don't capture while the previous offer is
    // still undrained.
    wire capture_this_cycle = slot_arrived && !data_valid && !effective_freeze;

    assign ack_out_n = capture_this_cycle && slot_direction[0];
    assign ack_out_s = capture_this_cycle && slot_direction[1];
    assign ack_out_e = capture_this_cycle && slot_direction[2];
    assign ack_out_w = capture_this_cycle && slot_direction[3];

    wire want_to_offer = data_valid && !effective_freeze;
    wire targets_all_ready = (!upstream_mask[0] || ready_in_n) &&
                             (!upstream_mask[1] || ready_in_s) &&
                             (!upstream_mask[2] || ready_in_e) &&
                             (!upstream_mask[3] || ready_in_w);
    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (upstream_mask & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack   & ~ack_in_vec) :
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
    assign status_slot = slot;
    assign status_data_valid = data_valid;

    always @(posedge clk) begin
        if (rst) begin
            slot             <= 2'd0;
            out_buffer       <= 32'h0;
            routing_reg      <= 8'h0;
            data_valid       <= 1'b0;
            pending_ack      <= 4'h0;
            upstream_mask    <= 4'h0;
            chain_for_slot0  <= 4'h0;
            chain_for_slot1  <= 4'h0;
            chain_for_slot2  <= 4'h0;
        end else if (cfg_valid) begin
            upstream_mask    <= cfg_data[3:0];
            chain_for_slot0  <= cfg_data[7:4];
            chain_for_slot1  <= cfg_data[11:8];
            chain_for_slot2  <= cfg_data[15:12];
            slot             <= 2'd0;
            data_valid       <= 1'b0;
            pending_ack      <= 4'h0;
        end else begin
            if (capture_this_cycle) begin
                out_buffer  <= slot_data;
                routing_reg <= {2'd1 /*count=1*/, slot, 4'b0000 /*slot2,slot3 unused at leaf level*/};
                data_valid  <= 1'b1;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end

            // The scan ALWAYS advances — same unconditional round-robin
            // as combiner_cell_v1.v, regardless of this relay's own
            // upward-offer state.
            slot <= (slot == 2'd2) ? 2'd0 : (slot + 2'd1);

            pending_ack <= next_pending_ack;
        end
    end

endmodule
