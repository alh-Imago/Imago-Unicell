// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// cell_cardinal_cmd_v1.v — points.md #100's alternative to #99's wrapper:
// address+program/collect tokens ride the SAME cardinal N/S/E/W adjacency
// the data channel already uses, instead of a separate, independent
// daisy-chain bus topology (#99's wrapper). Sits ALONGSIDE
// unicell_stripped_v1.v — the cell itself remains byte-for-byte unchanged,
// same as #99's wrapper approach; only the BUS TOPOLOGY differs between
// the two mechanisms, not whether the cell itself is touched.
//
// Broadcasts its output identically to all 4 directions (cmd*_out_n/s/e/w
// all carry the SAME value) — deliberately mirroring the cell's own
// data_out_n/s/e/w convention exactly, rather than inventing a per-
// position output mux. Whichever direction is actually wired to a real
// neighbor at the top level is what matters; unused directions are simply
// tied off, same discipline as the data grid.
//
// Genuinely 4-way priority-selects its INCOMING direction (sel_n/s/e/w,
// same N>S>E>W convention as the cell's own arrived_val mux) — unlike
// #99's wrapper, which only ever had ONE incoming bus direction by
// construction (a flat daisy chain). This is real, additional logic #99
// didn't need, and part of what #103 step 3 measures.
//
// EXPLICITLY NOT RESOLVED HERE, per #100's own flagged open question:
// what happens to a cell's in-flight two-arrival state (a_arrived,
// pending_ack) if a reprogram command lands mid-fire. This module simply
// pulses cfg_valid on a completed match+3-word assembly, exactly like
// #99's wrapper — no interrupt-vs-quiesce handshake is built here. That
// question remains open; this is a fit/area/Fmax measurement only.
`default_nettype none
`timescale 1ns / 1ps

module cell_cardinal_cmd_v1 #(
    parameter [4:0] ADDR = 5'd0,
    // ── Fix (points.md #110): gate output to ONLY the single intended
    // direction (matching this cell's own snake position, same
    // simplification the data channel already uses via routing_mask),
    // rather than broadcasting to all 4 -- broadcasting created a real
    // flood/fan-in-collision problem, confirmed by simulation (a distant
    // cell never got programmed correctly). 2'b00=N,01=S,10=E,11=W,
    // any other value = no relay (chain end). ──
    parameter [1:0] RELAY_DIR = 2'b00,
    parameter       RELAY_NONE = 1'b0
) (
    input  wire        clk,
    input  wire        rst,

    // ── Incoming, 4 directions ──
    input  wire        cmdv_in_n, cmdv_in_s, cmdv_in_e, cmdv_in_w,
    input  wire [4:0]  cmda_in_n, cmda_in_s, cmda_in_e, cmda_in_w,
    input  wire        cmdo_in_n, cmdo_in_s, cmdo_in_e, cmdo_in_w,   // 0=PROGRAM,1=COLLECT
    input  wire [31:0] cmdd_in_n, cmdd_in_s, cmdd_in_e, cmdd_in_w,

    // ── Outgoing, broadcast identically to all 4 (registered — one hop
    // per cycle, matching #99's wrapper's registered pass-through) ──
    output reg         cmdv_out_n, cmdv_out_s, cmdv_out_e, cmdv_out_w,
    output reg [4:0]   cmda_out_n, cmda_out_s, cmda_out_e, cmda_out_w,
    output reg         cmdo_out_n, cmdo_out_s, cmdo_out_e, cmdo_out_w,
    output reg [31:0]  cmdd_out_n, cmdd_out_s, cmdd_out_e, cmdd_out_w,

    // ── This module's own cell ──
    output reg          cell_cfg_valid,
    output reg [127:0]  cell_cfg_data,
    input  wire [31:0]  cell_out_buffer
);

// ── 4-way priority select, incoming (N>S>E>W, same convention as the
// cell's own arrived_val mux) — real, additional logic #99's wrapper
// never needed, since its bus only ever had one incoming direction. ──
wire sel_n = cmdv_in_n;
wire sel_s = cmdv_in_s && !cmdv_in_n;
wire sel_e = cmdv_in_e && !cmdv_in_n && !cmdv_in_s;
wire sel_w = cmdv_in_w && !cmdv_in_n && !cmdv_in_s && !cmdv_in_e;

wire        any_in  = cmdv_in_n | cmdv_in_s | cmdv_in_e | cmdv_in_w;
wire [4:0]  in_addr = sel_n ? cmda_in_n : sel_s ? cmda_in_s : sel_e ? cmda_in_e : cmda_in_w;
wire        in_op   = sel_n ? cmdo_in_n : sel_s ? cmdo_in_s : sel_e ? cmdo_in_e : cmdo_in_w;
wire [31:0] in_data = sel_n ? cmdd_in_n : sel_s ? cmdd_in_s : sel_e ? cmdd_in_e : cmdd_in_w;

wire match = any_in && (in_addr == ADDR);

reg [1:0]  word_idx = 2'h0;
reg [95:0] assemble  = 96'h0;

always @(posedge clk) begin
    if (rst) begin
        word_idx       <= 2'h0;
        assemble       <= 96'h0;
        cell_cfg_valid <= 1'b0;
        cell_cfg_data  <= 128'h0;
        cmdv_out_n <= 1'b0; cmdv_out_s <= 1'b0; cmdv_out_e <= 1'b0; cmdv_out_w <= 1'b0;
        cmda_out_n <= 5'h0; cmda_out_s <= 5'h0; cmda_out_e <= 5'h0; cmda_out_w <= 5'h0;
        cmdo_out_n <= 1'b0; cmdo_out_s <= 1'b0; cmdo_out_e <= 1'b0; cmdo_out_w <= 1'b0;
        cmdd_out_n <= 32'h0; cmdd_out_s <= 32'h0; cmdd_out_e <= 32'h0; cmdd_out_w <= 32'h0;
    end else begin
        cell_cfg_valid <= 1'b0;

        if (match && !in_op) begin
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

        // Registered relay — GATED to only the single intended direction
        // (points.md #110 fix), not broadcast to all 4. Avoids the flood/
        // fan-in-collision problem confirmed by simulation.
        cmdv_out_n <= (!RELAY_NONE && RELAY_DIR==2'b00) ? any_in : 1'b0;
        cmdv_out_s <= (!RELAY_NONE && RELAY_DIR==2'b01) ? any_in : 1'b0;
        cmdv_out_e <= (!RELAY_NONE && RELAY_DIR==2'b10) ? any_in : 1'b0;
        cmdv_out_w <= (!RELAY_NONE && RELAY_DIR==2'b11) ? any_in : 1'b0;
        cmda_out_n <= in_addr; cmda_out_s <= in_addr; cmda_out_e <= in_addr; cmda_out_w <= in_addr;
        cmdo_out_n <= in_op;   cmdo_out_s <= in_op;   cmdo_out_e <= in_op;   cmdo_out_w <= in_op;
        begin : relay_data
            reg [31:0] out_val;
            out_val = (match && in_op) ? cell_out_buffer : in_data;
            cmdd_out_n <= out_val; cmdd_out_s <= out_val; cmdd_out_e <= out_val; cmdd_out_w <= out_val;
        end
    end
end

endmodule
