// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mem_read_splitter_v1.v — first real RTL draft of the distribution
// system's read-side split (points.md #257/#258's design, built on
// `#259`'s widened `bram_controller_v1.v`). DRAFT — sim-verified only,
// no Quartus data yet.
//
// A deliberate CLONE of `mem_interface_cell_v1.v`'s READ mode, not an
// in-place edit of that file (never modify a proven file in place) —
// and a genuine fork rather than a version bump, since this module has
// a shape `mem_interface_cell_v1.v` never had: TWO outputs instead of
// one. WRITE mode is dropped entirely here — this module is READ-only,
// single-purpose, matching `#257`'s own read-side/write-side split
// (the write side is the still-unbuilt combiner core, a separate
// module, not a mode flag on this one).
//
// THE SPLIT (points.md #257): every 40-bit BRAM word is
// {8-bit ROUTING, 32-bit DATA}. Both fields diverge at the source, the
// SAME cycle `bram_rdata_valid` arrives — captured together, off the
// same event, naturally synchronized (no separate timing to get wrong
// between them):
//   - DATA (bits [31:0]) follows the entirely ordinary cardinal
//     offer/drain path `mem_interface_cell_v1.v`'s READ mode already
//     proved (`out_buffer`/`data_valid`/`pending_ack`) — unchanged
//     logic, just narrower slice of a wider word.
//   - ROUTING (bits [39:32]) does NOT go through that mechanism at
//     all. It's captured into its own plain register (`routing_reg`)
//     the same cycle, and exposed directly on a new, non-cardinal,
//     8-bit-wide port (`routing_out`) — no ack/valid protocol of its
//     own. `#257`'s own cycle-by-cycle trace already established why
//     this is safe: the mux (once built) is expected to read
//     `routing_out` at the exact moment it captures DATA via the
//     ordinary ack-at-capture convention, and `routing_reg`'s
//     stability for that whole window is already protected by the SAME
//     doubly-full guard (`!(addr_captured && data_valid)`) that
//     protects `out_buffer` — no separate protection logic needed,
//     confirmed by construction, not assumed.
//
// cfg_data[63:0] field map — narrower than `mem_interface_cell_v1.v`'s
// own, since op_mode is gone (always READ here):
//   [3:0]   downstream_mask  — where DATA offers (the staging path)
//   [7:4]   upstream_mask    — address source, same direction-agnostic
//                              convention every core here uses
//   [63:8]  reserved
`default_nettype none
`timescale 1ns / 1ps

module mem_read_splitter_v1 #(
    parameter [15:0] CELL_ID    = 16'h0000,
    parameter        ADDR_WIDTH = 16
) (
    input  wire        clk,
    input  wire        rst,

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

    input  wire         freeze_in,

    // ── The new, non-cardinal port — ROUTING, stable throughout the
    // same window out_buffer/data_valid are offering DATA. ──
    output wire [7:0]   routing_out,

    output wire         status_data_valid,
    output wire         status_addr_captured
);

    // ── State ───────────────────────────────────────────────────────────
    reg [31:0] addr_reg        = 32'h0;
    reg        addr_captured   = 1'b0;
    reg        read_pending    = 1'b0;
    reg [31:0] out_buffer      = 32'h0;
    reg [7:0]  routing_reg     = 8'h0;
    reg        data_valid      = 1'b0;
    reg [3:0]  downstream_mask = 4'h0;
    reg [3:0]  upstream_mask   = 4'h0;
    reg [3:0]  pending_ack     = 4'h0;

    wire effective_freeze = freeze_in;

    // ── Upstream arrival selection — same convention as every core
    // here. ──
    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    // First arrival -> address. Doubly-full gate (`#256`'s established
    // fix) — protects BOTH out_buffer AND routing_reg, since they're
    // captured together off the same event.
    wire capture_now = any_upstream_arrived && !addr_captured && !effective_freeze &&
                        !data_valid;

    assign ack_out_n = capture_now && sel_n;
    assign ack_out_s = capture_now && sel_s;
    assign ack_out_e = capture_now && sel_e;
    assign ack_out_w = capture_now && sel_w;

    // ── The real memory core, now at the real M20K native width
    // (points.md #257/#259). ──
    wire                  bram_cmd_valid = capture_now;
    wire [ADDR_WIDTH-1:0] bram_cmd_addr  = upstream_val[ADDR_WIDTH-1:0];

    wire        bram_rdata_valid;
    wire [39:0] bram_rdata;
    wire        bram_write_done;   // unused — this module never writes

    bram_controller_v1 #(.ADDR_WIDTH(ADDR_WIDTH), .DATA_WIDTH(40)) CORE (
        .clk(clk), .rst(rst),
        .cmd_valid(bram_cmd_valid), .cmd_op(1'b0) /* always READ */,
        .cmd_addr(bram_cmd_addr), .cmd_wdata(40'h0) /* never written through this port */,
        .rdata_valid(bram_rdata_valid), .rdata(bram_rdata), .write_done(bram_write_done)
    );

    // ── Downstream DATA offering — identical shape to
    // mem_interface_cell_v1.v's own READ mode. ──
    wire want_to_offer = data_valid && !effective_freeze;
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

    assign ready_out = !effective_freeze && !addr_captured && !data_valid;
    assign status_data_valid    = data_valid;
    assign status_addr_captured = addr_captured;

    always @(posedge clk) begin
        if (rst) begin
            addr_reg        <= 32'h0;
            addr_captured   <= 1'b0;
            read_pending    <= 1'b0;
            out_buffer      <= 32'h0;
            routing_reg     <= 8'h0;
            data_valid      <= 1'b0;
            downstream_mask <= 4'h0;
            upstream_mask   <= 4'h0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[3:0];
            upstream_mask   <= cfg_data[7:4];
            addr_captured   <= 1'b0;
            read_pending    <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else begin
            if (capture_now) begin
                addr_reg      <= upstream_val;
                addr_captured <= 1'b1;
                read_pending  <= 1'b1;
            end

            // DATA and ROUTING captured TOGETHER, off the same event —
            // the whole point of the split (#257): no separate timing
            // between the two fields.
            if (read_pending && bram_rdata_valid) begin
                out_buffer    <= bram_rdata[31:0];
                routing_reg   <= bram_rdata[39:32];
                data_valid    <= 1'b1;
                addr_captured <= 1'b0;
                read_pending  <= 1'b0;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end

            pending_ack <= next_pending_ack;
        end
    end

endmodule
