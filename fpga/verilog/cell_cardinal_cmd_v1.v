// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// cell_cardinal_cmd_v1.v — REVISED (points.md #114) per Alan's correction:
// the v1 design's runtime address comparator was NOT what #100 actually
// described, and #109/#111 confirmed it as the expensive part (86.5
// ALM/cell, dominated by the comparator + word-assembly gated behind it).
//
// #100's real framing: commands ride the SAME cardinal path data already
// uses. Data carries NO address — it goes wherever `routing_mask` sends
// it, and landing there IS the addressing. This revision applies the same
// principle: whether a cell CONSUMES an arriving command or RELAYS it
// onward is a STATIC, config-time decision (CONSUME_CMD parameter, set
// once via the wrapper at setup — #99 — alongside routing_mask/
// cardinal_edge), exactly mirroring #94's cardinal_edge mechanism for
// data. NO runtime address field, NO comparator, NO per-cell ID at all.
//
// Initial setup (which cells consume vs relay) uses the wrapper — #99's
// already-known, already-measured cost (14.3 ALM/cell, 165.7 MHz, #109).
// This module is ONLY the in-flight/runtime path: pure cardinal routing,
// nothing more.
`default_nettype none
`timescale 1ns / 1ps

module cell_cardinal_cmd_v1 #(
    // ── Config-time decisions (would be wrapper-loaded in a real system;
    // compile-time parameter here, consistent with how RELAY_DIR/
    // RELAY_NONE and the data grid's own routing_mask/cardinal_edge are
    // all handled as compile-time constants in this measurement campaign
    // — #99's own cost was already measured separately in step 2). ──
    parameter        CONSUME_CMD = 1'b0,   // 1 = this cell applies arriving commands to itself
    parameter [1:0]  RELAY_DIR   = 2'b00,  // which single direction to relay to, if not consuming
    parameter        RELAY_NONE  = 1'b0    // chain end — nowhere to relay to
) (
    input  wire        clk,
    input  wire        rst,

    // ── Incoming, 4 directions — NO address field anymore ──
    input  wire        cmdv_in_n, cmdv_in_s, cmdv_in_e, cmdv_in_w,
    input  wire        cmdo_in_n, cmdo_in_s, cmdo_in_e, cmdo_in_w,   // 0=PROGRAM,1=COLLECT
    input  wire [31:0] cmdd_in_n, cmdd_in_s, cmdd_in_e, cmdd_in_w,

    // ── Outgoing — gated to the single intended direction only,
    // never broadcast (points.md #110's fix, carried forward) ──
    output reg         cmdv_out_n, cmdv_out_s, cmdv_out_e, cmdv_out_w,
    output reg         cmdo_out_n, cmdo_out_s, cmdo_out_e, cmdo_out_w,
    output reg [31:0]  cmdd_out_n, cmdd_out_s, cmdd_out_e, cmdd_out_w,

    // ── This module's own cell ──
    output reg          cell_cfg_valid,
    output reg [127:0]  cell_cfg_data,
    input  wire [31:0]  cell_out_buffer
);

// ── 4-way priority select, incoming (N>S>E>W, same convention as the
// cell's own arrived_val mux) — still genuinely needed, since a real
// cardinal cell can receive from up to 4 directions. This part of the
// v1 design's cost was real and inherent, kept unchanged. ──
wire sel_n = cmdv_in_n;
wire sel_s = cmdv_in_s && !cmdv_in_n;
wire sel_e = cmdv_in_e && !cmdv_in_n && !cmdv_in_s;
wire sel_w = cmdv_in_w && !cmdv_in_n && !cmdv_in_s && !cmdv_in_e;

wire        any_in  = cmdv_in_n | cmdv_in_s | cmdv_in_e | cmdv_in_w;
wire        in_op   = sel_n ? cmdo_in_n : sel_s ? cmdo_in_s : sel_e ? cmdo_in_e : cmdo_in_w;
wire [31:0] in_data = sel_n ? cmdd_in_n : sel_s ? cmdd_in_s : sel_e ? cmdd_in_e : cmdd_in_w;

// ── The fix: "should I apply this" is now a STATIC decision
// (CONSUME_CMD), not a runtime comparison against anything. ──
wire consume = any_in && CONSUME_CMD;

reg [1:0]  word_idx = 2'h0;
reg [95:0] assemble  = 96'h0;

always @(posedge clk) begin
    if (rst) begin
        word_idx       <= 2'h0;
        assemble       <= 96'h0;
        cell_cfg_valid <= 1'b0;
        cell_cfg_data  <= 128'h0;
        cmdv_out_n <= 1'b0; cmdv_out_s <= 1'b0; cmdv_out_e <= 1'b0; cmdv_out_w <= 1'b0;
        cmdo_out_n <= 1'b0; cmdo_out_s <= 1'b0; cmdo_out_e <= 1'b0; cmdo_out_w <= 1'b0;
        cmdd_out_n <= 32'h0; cmdd_out_s <= 32'h0; cmdd_out_e <= 32'h0; cmdd_out_w <= 32'h0;
    end else begin
        cell_cfg_valid <= 1'b0;

        if (consume && !in_op) begin
            case (word_idx)
                2'd0: assemble[31:0]  <= in_data;
                2'd1: assemble[63:32] <= in_data;
                2'd2: begin
                    assemble[95:64] <= in_data;
                    cell_cfg_valid  <= 1'b1;
                    cell_cfg_data   <= {32'h0, in_data, assemble[63:32], assemble[31:0]};
                end
            endcase
            word_idx <= (word_idx == 2'd2) ? 2'd0 : (word_idx + 2'd1);
        end

        // Registered relay — gated to only the single intended direction,
        // CONSUME_CMD cells still relay onward too (a consuming cell can
        // also be mid-chain, same as data's consume-vs-relay independence
        // per #94). Only a chain-end cell (RELAY_NONE) sends nowhere.
        cmdv_out_n <= (!RELAY_NONE && RELAY_DIR==2'b00) ? any_in : 1'b0;
        cmdv_out_s <= (!RELAY_NONE && RELAY_DIR==2'b01) ? any_in : 1'b0;
        cmdv_out_e <= (!RELAY_NONE && RELAY_DIR==2'b10) ? any_in : 1'b0;
        cmdv_out_w <= (!RELAY_NONE && RELAY_DIR==2'b11) ? any_in : 1'b0;
        cmdo_out_n <= in_op; cmdo_out_s <= in_op; cmdo_out_e <= in_op; cmdo_out_w <= in_op;
        begin : relay_data
            reg [31:0] out_val;
            out_val = (consume && in_op) ? cell_out_buffer : in_data;
            cmdd_out_n <= out_val; cmdd_out_s <= out_val; cmdd_out_e <= out_val; cmdd_out_w <= out_val;
        end
    end
end

endmodule
