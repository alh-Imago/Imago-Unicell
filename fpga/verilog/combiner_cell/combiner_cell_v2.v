// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// combiner_cell_v2.v — TREE-AWARE root combiner. A clone of
// `combiner_cell_v1.v` (never modify a proven file in place), extended
// with per-slot CHILD-INPUT support so a real combiner TREE can be
// assembled, mirroring `mux_cell_v1.v`'s own tree capability on the
// read side (points.md #257/#258/#271). DRAFT — sim-verified only, no
// Quartus data yet.
//
// WHY A NEW FILE, NOT AN EDIT: `combiner_cell_v1.v` (#268) already
// passed real verification (incl. genuine simultaneous-offer
// contention) — that file stays untouched. v2 adds exactly one new
// capability on top: any of its 3 slots can be configured as either a
// RAW CHAIN (v1's existing behavior, unchanged) or a CHILD COMBINER
// (a `combiner_relay_v1.v` instance one level down). With every
// is_child flag OFF, v2's behavior is IDENTICAL to v1 by construction
// — confirmed directly via a regression test reusing v1's own test
// vectors, not just asserted.
//
// THE ENCODE, per points.md #258's own description, built for the
// first time here (the read side's DECODE was built at #266/#271;
// this is its mirror): "each parent node going up increments count by
// 1 and writes its own face into the slot matching the NEW count
// value." Concretely, for whichever slot is currently selected:
//   - RAW CHAIN slot (is_child=0): effective_count is fixed at 1, this
//     slot's own position gets written into the slot1 field — exactly
//     v1's existing {count=1, slot=position, 00, 00}.
//   - CHILD slot (is_child=1): read routing_in for that direction,
//     child_count = routing_in[7:6] (the child's OWN count, e.g. 1 if
//     the child is itself a leaf relay). effective_count =
//     child_count + 1. This root's OWN slot position gets written into
//     whichever field (slot1/slot2/slot3) effective_count now
//     indicates — the OTHER fields are PRESERVED UNCHANGED from the
//     child's own routing_in value (the child's own lower-level stamps
//     ride through untouched, exactly matching the read side's own
//     "no bit shifting, forward the rest unchanged" property).
//
// cfg_data[63:0] field map — extends v1's with 3 new is_child bits:
//   [3:0]   downstream_mask   — unused for direct-to-BRAM root output,
//                               kept for symmetry (same as v1)
//   [7:4]   chain_for_slot0   — one-hot direction checked at position 0
//   [11:8]  chain_for_slot1   — one-hot direction checked at position 1
//   [15:12] chain_for_slot2   — one-hot direction checked at position 2
//   [16]    is_child_slot0    — 1 = this slot's input is a
//   [17]    is_child_slot1      combiner_relay_v1.v child (read its
//   [18]    is_child_slot2      routing_in and re-stamp); 0 = raw chain
//   [63:19] reserved
`default_nettype none
`timescale 1ns / 1ps

module combiner_cell_v2 #(
    parameter [15:0] CELL_ID    = 16'h0000,
    parameter        ADDR_WIDTH = 16
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,
    // Routing companion inputs — only read when the currently-selected
    // slot is flagged is_child; a don't-care otherwise, same pattern
    // as every unused cardinal port elsewhere in this project.
    input  wire [7:0]   routing_in_n, routing_in_s, routing_in_e, routing_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,

    output wire         wr_cmd_valid,
    output wire [ADDR_WIDTH-1:0] wr_cmd_addr,
    output wire [39:0]  wr_cmd_wdata,
    input  wire         wr_write_done,

    input  wire         freeze_in,

    output wire [1:0]   status_slot,
    output wire         status_wrote_this_cycle
);

    reg [3:0] downstream_mask  = 4'h0;
    reg [3:0] chain_for_slot0  = 4'h0;
    reg [3:0] chain_for_slot1  = 4'h0;
    reg [3:0] chain_for_slot2  = 4'h0;
    reg       is_child_slot0   = 1'b0;
    reg       is_child_slot1   = 1'b0;
    reg       is_child_slot2   = 1'b0;

    wire effective_freeze = freeze_in;

    // ── Same fixed round-robin scan as combiner_cell_v1.v — unchanged ──
    reg [1:0] slot = 2'd0;
    wire [3:0] slot_direction = (slot == 2'd0) ? chain_for_slot0 :
                                (slot == 2'd1) ? chain_for_slot1 :
                                                  chain_for_slot2;
    wire slot_is_child = (slot == 2'd0) ? is_child_slot0 :
                         (slot == 2'd1) ? is_child_slot1 :
                                           is_child_slot2;

    wire slot_arrived = (slot_direction[0] && arrived_n) ||
                        (slot_direction[1] && arrived_s) ||
                        (slot_direction[2] && arrived_e) ||
                        (slot_direction[3] && arrived_w);
    wire [31:0] slot_data = (slot_direction[0] ? data_in_n : 32'h0) |
                            (slot_direction[1] ? data_in_s : 32'h0) |
                            (slot_direction[2] ? data_in_e : 32'h0) |
                            (slot_direction[3] ? data_in_w : 32'h0);
    wire [7:0]  slot_routing = (slot_direction[0] ? routing_in_n : 8'h0) |
                               (slot_direction[1] ? routing_in_s : 8'h0) |
                               (slot_direction[2] ? routing_in_e : 8'h0) |
                               (slot_direction[3] ? routing_in_w : 8'h0);

    wire capture_this_cycle = slot_arrived && !effective_freeze;

    assign ack_out_n = capture_this_cycle && slot_direction[0];
    assign ack_out_s = capture_this_cycle && slot_direction[1];
    assign ack_out_e = capture_this_cycle && slot_direction[2];
    assign ack_out_w = capture_this_cycle && slot_direction[3];

    // ── THE ENCODE — the one genuinely new mechanism beyond v1 ────────
    wire [1:0] child_count      = slot_routing[7:6];
    wire [1:0] effective_count  = slot_is_child ? (child_count + 2'd1) : 2'd1;

    // Whichever field effective_count indicates gets THIS node's own
    // slot position; the other two fields are preserved from the
    // child's own routing_in (0 for a raw chain, where they're unused
    // anyway — matches v1's {00,00} exactly in that case).
    wire [1:0] field_slot1 = (effective_count == 2'd1) ? slot :
                             slot_is_child ? slot_routing[5:4] : 2'b00;
    wire [1:0] field_slot2 = (effective_count == 2'd2) ? slot :
                             slot_is_child ? slot_routing[3:2] : 2'b00;
    wire [1:0] field_slot3 = (effective_count == 2'd3) ? slot :
                             slot_is_child ? slot_routing[1:0] : 2'b00;

    reg [ADDR_WIDTH-1:0] write_addr = {ADDR_WIDTH{1'b0}};

    assign wr_cmd_valid = capture_this_cycle;
    assign wr_cmd_addr  = write_addr;
    assign wr_cmd_wdata = {effective_count, field_slot1, field_slot2, field_slot3, slot_data};

    assign status_slot = slot;
    assign status_wrote_this_cycle = capture_this_cycle;

    always @(posedge clk) begin
        if (rst) begin
            slot             <= 2'd0;
            write_addr       <= {ADDR_WIDTH{1'b0}};
            downstream_mask  <= 4'h0;
            chain_for_slot0  <= 4'h0;
            chain_for_slot1  <= 4'h0;
            chain_for_slot2  <= 4'h0;
            is_child_slot0   <= 1'b0;
            is_child_slot1   <= 1'b0;
            is_child_slot2   <= 1'b0;
        end else if (cfg_valid) begin
            downstream_mask  <= cfg_data[3:0];
            chain_for_slot0  <= cfg_data[7:4];
            chain_for_slot1  <= cfg_data[11:8];
            chain_for_slot2  <= cfg_data[15:12];
            is_child_slot0   <= cfg_data[16];
            is_child_slot1   <= cfg_data[17];
            is_child_slot2   <= cfg_data[18];
            slot             <= 2'd0;
            write_addr       <= {ADDR_WIDTH{1'b0}};
        end else begin
            if (capture_this_cycle) begin
                write_addr <= write_addr + {{(ADDR_WIDTH-1){1'b0}}, 1'b1};
            end
            slot <= (slot == 2'd2) ? 2'd0 : (slot + 2'd1);
        end
    end

endmodule
