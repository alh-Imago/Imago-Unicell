// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mem_read_splitter_v1_ext.v — a deliberate CLONE of
// `mem_read_splitter_v1.v` (never modify a proven file in place), for
// ONE real gap Alan flagged directly: a genuine SHARED memory between
// the read (OUT) side and write (IN) side. Every prior full-system
// build used TWO SEPARATE `bram_controller_v1.v` instances (matching
// `#257`'s own "two independent regions" design intent) — this variant
// makes a single shared memory actually possible.
//
// THE ONE REAL DIFFERENCE from `mem_read_splitter_v1.v`: this module
// does NOT instantiate its own internal `bram_controller_v1.v` CORE at
// all. Instead it exposes the exact same command shape externally
// (`ext_cmd_valid`/`ext_cmd_addr` outputs, `ext_rdata_valid`/
// `ext_rdata` inputs) — mirroring how `combiner_cell_v1.v`/`v2.v`
// ALREADY expose their own `wr_cmd_*` interface externally rather than
// owning a BRAM themselves (points.md #268). This module simply brings
// the READ side up to the same shape, so ONE external
// `bram_controller_v1.v` instance can now be arbitrated between BOTH
// this module's read requests and a combiner's write requests —
// exactly the missing piece for a genuinely shared memory.
//
// Everything else — the DATA/ROUTING split, the doubly-full guard, the
// cardinal offer/drain mechanism — is unchanged from `mem_read_
// splitter_v1.v`, byte-for-byte identical logic, just wired to an
// external command port instead of an internal CORE instance.
`default_nettype none
`timescale 1ns / 1ps

module mem_read_splitter_v1_ext #(
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

    output wire [7:0]   routing_out,

    output wire         status_data_valid,
    output wire         status_addr_captured,

    // ── External memory command interface — the ONE real change from
    // mem_read_splitter_v1.v. This module never owns a BRAM; whatever
    // wires this up (a top-level, an arbiter) is responsible for
    // actually issuing the read against a real bram_controller_v1.v
    // and returning the result. ──
    output wire                    ext_cmd_valid,
    output wire [ADDR_WIDTH-1:0]   ext_cmd_addr,
    input  wire                    ext_rdata_valid,
    input  wire [39:0]             ext_rdata
);

    // ── State — identical to mem_read_splitter_v1.v ────────────────────
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

    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    wire capture_now = any_upstream_arrived && !addr_captured && !effective_freeze &&
                        !data_valid;

    assign ack_out_n = capture_now && sel_n;
    assign ack_out_s = capture_now && sel_s;
    assign ack_out_e = capture_now && sel_e;
    assign ack_out_w = capture_now && sel_w;

    // ── External command — no internal CORE instance. ──────────────────
    assign ext_cmd_valid = capture_now;
    assign ext_cmd_addr  = upstream_val[ADDR_WIDTH-1:0];

    // ── Downstream DATA offering — identical to mem_read_splitter_v1.v ──
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

            if (read_pending && ext_rdata_valid) begin
                out_buffer    <= ext_rdata[31:0];
                routing_reg   <= ext_rdata[39:32];
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
