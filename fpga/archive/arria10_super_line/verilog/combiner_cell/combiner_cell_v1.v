// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// combiner_cell_v1.v — first real RTL draft of the distribution tree's
// combiner core (points.md #257/#258's design, write-side mirror of
// mux_cell_v1.v/#266). DRAFT — sim-verified only, no Quartus data yet.
//
// SHELL: mirrors mux_cell_v1.v exactly but reversed — one direction is
// the FIXED output (toward bram_controller_v1.v, or a parent combiner
// node in a future tree), leaving up to 3 usable INPUT faces (real
// chains). Same "3 usable faces, one consumed by the fixed connection"
// constraint #258 corrected for the mux applies here identically.
//
// NO ARBITRATION NEEDED — Alan's own insight, not traditional
// arbitration logic: a chain-select counter scans the (up to 3)
// configured chain-input faces in FIXED round-robin order, one slot per
// cycle, REGARDLESS of occupancy (Alan's explicit choice: "if it waits
// then others get backed up" — a slow/empty chain must never stall the
// scan). At each slot: check that direction's `arrived_x` combinationally
// (mirroring every other core's own capture_now check); if data is
// there, capture it, stamp the COUNTER'S OWN CURRENT POSITION as the
// 2-bit slot ID, issue one BRAM WRITE, advance the write-address ONLY
// on that genuine capture; if empty, just advance to the next slot,
// write nothing, advance no address. The counter position doubles as
// both "which chain to check" and "the ID to stamp" — free, matching
// the read side's own free-ID-from-slot-index property (#258), mirrored
// onto the write side.
//
// Every upstream chain simply holds its own offer (its own
// fire_x/pending_ack, standard offer/drain discipline every core here
// already has) until this combiner's counter reaches its slot and acks
// it — no per-direction ready_out gating needed on the combiner's input
// side at all. A chain not yet being checked is entirely unaffected,
// exactly matching how offer/drain always works everywhere else in
// this project.
//
// WRITE FORMAT, matching mux_cell_v1.v's own decode expectations
// exactly (points.md #266's pinned-down bit layout) — this is a
// single-level combiner (count=1, one real hop), same as the paired
// single-level mux test:
//   routing byte = {count=1, slot1=<counter position>, 2'b00, 2'b00}
// packed as the top 8 bits of the 40-bit BRAM word alongside the
// 32-bit data, per #257's own {8-bit ID, 32-bit data} packing.
//
// cfg_data[63:0] field map:
//   [3:0]   downstream_mask   — the single fixed direction toward BRAM
//                               (exactly one bit set)
//   [7:4]   chain_for_slot0   — one-hot direction checked at counter
//                               position 0
//   [11:8]  chain_for_slot1   — one-hot direction checked at position 1
//   [15:12] chain_for_slot2   — one-hot direction checked at position 2
//   [63:16] reserved
`default_nettype none
`timescale 1ns / 1ps

module combiner_cell_v1 #(
    parameter [15:0] CELL_ID    = 16'h0000,
    parameter        ADDR_WIDTH = 16
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,

    // ── The fixed downstream write path — a real bram_controller_v1.v
    // command, driven directly (not through the ordinary cardinal
    // offer/drain mechanism, matching how mem_read_splitter_v1.v's
    // ROUTING side skips it too — a WRITE either lands this cycle or
    // it doesn't, no drain-window semantics apply here). ──
    output wire         wr_cmd_valid,
    output wire [ADDR_WIDTH-1:0] wr_cmd_addr,
    output wire [39:0]  wr_cmd_wdata,
    input  wire         wr_write_done,

    input  wire         freeze_in,

    output wire [1:0]   status_slot,       // current counter position — debug only
    output wire         status_wrote_this_cycle
);

    // ── Config ──────────────────────────────────────────────────────────
    reg [3:0] downstream_mask  = 4'h0;   // unused for routing here (fixed
                                          // single BRAM target) — kept for
                                          // symmetry with mux_cell_v1.v and
                                          // for a future combiner-tree node
                                          // to know which direction its
                                          // OWN output goes, though this
                                          // single-level draft drives
                                          // wr_cmd_* directly rather than
                                          // through cardinal ports.
    reg [3:0] chain_for_slot0  = 4'h0;
    reg [3:0] chain_for_slot1  = 4'h0;
    reg [3:0] chain_for_slot2  = 4'h0;

    wire effective_freeze = freeze_in;

    // ── Chain-select counter — FIXED round-robin, 3 positions
    // (matching the real 3-usable-faces ceiling), advances EVERY cycle
    // unconditionally (Alan's explicit choice — no waiting). ──
    reg [1:0] slot = 2'd0;
    wire [3:0] slot_direction = (slot == 2'd0) ? chain_for_slot0 :
                                (slot == 2'd1) ? chain_for_slot1 :
                                                  chain_for_slot2;   // slot==2'd2 or invalid — same as slot2

    // Combinational check — does the CURRENTLY-SELECTED direction have
    // an arrival right now?
    wire slot_arrived = (slot_direction[0] && arrived_n) ||
                        (slot_direction[1] && arrived_s) ||
                        (slot_direction[2] && arrived_e) ||
                        (slot_direction[3] && arrived_w);
    wire [31:0] slot_data = (slot_direction[0] ? data_in_n : 32'h0) |
                            (slot_direction[1] ? data_in_s : 32'h0) |
                            (slot_direction[2] ? data_in_e : 32'h0) |
                            (slot_direction[3] ? data_in_w : 32'h0);

    wire capture_this_cycle = slot_arrived && !effective_freeze;

    assign ack_out_n = capture_this_cycle && slot_direction[0];
    assign ack_out_s = capture_this_cycle && slot_direction[1];
    assign ack_out_e = capture_this_cycle && slot_direction[2];
    assign ack_out_w = capture_this_cycle && slot_direction[3];

    // ── The write, issued directly the same cycle a capture happens —
    // no wait state needed, matching bram_controller_v1.v's own
    // single-cycle WRITE timing (#255). ──
    reg [ADDR_WIDTH-1:0] write_addr = {ADDR_WIDTH{1'b0}};

    assign wr_cmd_valid = capture_this_cycle;
    assign wr_cmd_addr  = write_addr;
    assign wr_cmd_wdata = {2'd1 /*count=1*/, slot, 4'b0000 /*slot2,slot3 unused at this level*/, slot_data};

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
        end else if (cfg_valid) begin
            downstream_mask  <= cfg_data[3:0];
            chain_for_slot0  <= cfg_data[7:4];
            chain_for_slot1  <= cfg_data[11:8];
            chain_for_slot2  <= cfg_data[15:12];
            slot             <= 2'd0;
            write_addr       <= {ADDR_WIDTH{1'b0}};
        end else begin
            // Advance the write-address ONLY on a genuine capture.
            if (capture_this_cycle) begin
                write_addr <= write_addr + {{(ADDR_WIDTH-1){1'b0}}, 1'b1};
            end

            // The scan ALWAYS advances — fixed, unconditional, per
            // Alan's own explicit choice (no waiting on a slow/empty
            // chain).
            slot <= (slot == 2'd2) ? 2'd0 : (slot + 2'd1);
        end
    end

endmodule
