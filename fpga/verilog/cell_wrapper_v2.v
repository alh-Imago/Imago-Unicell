// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// cell_wrapper_v2.v — points.md #127: the wrapper rebuilt so the external
// (JTAG/host) route has the SAME expressiveness as anything internal to
// the fabric. This is the only route in or out, per Alan, so it needs
// parity with a command cell, not a separate, narrower mechanism.
//
// Two real changes from v1 (#99/#108):
// 1. PROGRAM no longer writes cfg_valid/cfg_data directly. It asserts
//    program_in (#123/#125) and feeds its 3 words through the target's
//    ORDINARY data_in port — the identical path a command cell uses. The
//    target genuinely cannot tell the difference between a command cell
//    and the wrapper triggering it.
// 2. Two new operations: SET_CTRL/CLR_CTRL toggle one of the target's 6
//    persistent control lines (freeze_in, hold_in, fb_internal_in,
//    a_reemit_in, a_update_in, a_self_update_in), held continuously by a
//    small latch inside the wrapper itself (the scan bus only ever
//    delivers a brief instruction; the target's control inputs need to
//    stay held between scan operations). DIAG reads back internal state
//    that isn't otherwise observable (program_done, a_arrived, ready_bit,
//    pending_ack) — not data or programming state, which are already
//    covered by COLLECT/PROGRAM.
//
// OPCODES (3 bits, was 1 in v1):
//   000 PROGRAM   — 3 words via cell_prog_data_out/cell_prog_arrived_out,
//                   cell_program_out held for the whole sequence.
//   001 COLLECT   — substitutes cell_out_buffer onto bus_out_data.
//   010 SET_CTRL  — bus_in_data[2:0] selects which control line to SET.
//   011 CLR_CTRL  — bus_in_data[2:0] selects which control line to CLR.
//   100 DIAG      — substitutes cell_diag_in onto bus_out_data.
// Control line index: 0=freeze 1=hold 2=fb_internal 3=a_reemit
//                      4=a_update 5=a_self_update
`default_nettype none
`timescale 1ns / 1ps

module cell_wrapper_v2 #(
    parameter [4:0] ADDR = 5'd0
) (
    input  wire        clk,
    input  wire        rst,

    // ── Daisy-chain bus, in ──
    input  wire        bus_in_valid,
    input  wire [4:0]  bus_in_addr,
    input  wire [2:0]  bus_in_op,
    input  wire [31:0] bus_in_data,

    // ── Daisy-chain bus, out (registered — one pipeline stage per hop,
    // same discipline as v1 — #108's own reasoning still applies) ──
    output reg         bus_out_valid,
    output reg [4:0]   bus_out_addr,
    output reg [2:0]   bus_out_op,
    output reg [31:0]  bus_out_data,

    // ── Target's ordinary data port (PROGRAM's word injection — NOT
    // cfg_data anymore) ──
    output reg [31:0]  cell_prog_data_out,
    output reg         cell_prog_arrived_out,
    output reg         cell_program_out,
    input  wire        cell_program_done_in,

    // ── The 6 persistent control lines, held continuously ──
    output reg         cell_freeze_out,
    output reg         cell_hold_out,
    output reg         cell_fb_internal_out,
    output reg         cell_a_reemit_out,
    output reg         cell_a_update_out,
    output reg         cell_a_self_update_out,

    // ── Readback sources ──
    input  wire [31:0] cell_out_buffer,
    input  wire [31:0] cell_diag_in
);

localparam [2:0] OP_PROGRAM  = 3'b000;
localparam [2:0] OP_COLLECT  = 3'b001;
localparam [2:0] OP_SET_CTRL = 3'b010;
localparam [2:0] OP_CLR_CTRL = 3'b011;
localparam [2:0] OP_DIAG     = 3'b100;

reg [1:0] word_idx = 2'h0;

wire match = bus_in_valid && (bus_in_addr == ADDR);

always @(posedge clk) begin
    if (rst) begin
        word_idx               <= 2'h0;
        cell_prog_data_out     <= 32'h0;
        cell_prog_arrived_out  <= 1'b0;
        cell_program_out       <= 1'b0;
        cell_freeze_out        <= 1'b0;
        cell_hold_out          <= 1'b0;
        cell_fb_internal_out   <= 1'b0;
        cell_a_reemit_out      <= 1'b0;
        cell_a_update_out      <= 1'b0;
        cell_a_self_update_out <= 1'b0;
        bus_out_valid          <= 1'b0;
        bus_out_addr           <= 5'h0;
        bus_out_op             <= 3'h0;
        bus_out_data           <= 32'h0;
    end else begin
        cell_prog_arrived_out <= 1'b0;   // one-cycle pulse by default

        // ── PROGRAM: assert program_out on the first word, feed each
        // word straight through to the target's ordinary data port, hold
        // program_out until program_done confirms all 3 landed. ──
        if (match && (bus_in_op == OP_PROGRAM)) begin
            cell_program_out      <= 1'b1;
            cell_prog_data_out    <= bus_in_data;
            cell_prog_arrived_out <= 1'b1;
            word_idx <= (word_idx == 2'd2) ? 2'd0 : (word_idx + 2'd1);
        end
        if (cell_program_out && cell_program_done_in) begin
            cell_program_out <= 1'b0;   // confirmed done — release
        end

        // ── SET_CTRL / CLR_CTRL: persistent per-line latches ──
        if (match && (bus_in_op == OP_SET_CTRL)) begin
            case (bus_in_data[2:0])
                3'd0: cell_freeze_out        <= 1'b1;
                3'd1: cell_hold_out          <= 1'b1;
                3'd2: cell_fb_internal_out   <= 1'b1;
                3'd3: cell_a_reemit_out      <= 1'b1;
                3'd4: cell_a_update_out      <= 1'b1;
                3'd5: cell_a_self_update_out <= 1'b1;
                default: ;
            endcase
        end else if (match && (bus_in_op == OP_CLR_CTRL)) begin
            case (bus_in_data[2:0])
                3'd0: cell_freeze_out        <= 1'b0;
                3'd1: cell_hold_out          <= 1'b0;
                3'd2: cell_fb_internal_out   <= 1'b0;
                3'd3: cell_a_reemit_out      <= 1'b0;
                3'd4: cell_a_update_out      <= 1'b0;
                3'd5: cell_a_self_update_out <= 1'b0;
                default: ;
            endcase
        end

        // ── Registered pass-through / COLLECT / DIAG substitution ──
        bus_out_valid <= bus_in_valid;
        bus_out_addr  <= bus_in_addr;
        bus_out_op    <= bus_in_op;
        bus_out_data  <= (match && bus_in_op == OP_COLLECT) ? cell_out_buffer :
                          (match && bus_in_op == OP_DIAG)   ? cell_diag_in   :
                                                               bus_in_data;
    end
end

endmodule
