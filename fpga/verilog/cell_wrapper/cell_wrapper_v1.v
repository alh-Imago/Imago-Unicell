// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// cell_wrapper_v1.v — points.md #99's wrapper mechanism, first real RTL.
// Sits ALONGSIDE a unicell_stripped_v1 instance, not inside it — the cell
// stays exactly as-is, zero addressing hardware, #97/#106's confirmed
// area/Fmax unchanged. This is the #103 step 2 measurement: what does
// ADDING this wrapper to every cell actually cost, as a real delta against
// step 1's baseline (146 ALMs, 257.14 MHz, #106).
//
// PROTOCOL (daisy-chain scan bus, precedented by JTAG boundary scan and the
// FPGA's own bitstream config network, per #99):
//   - bus_in_valid/addr/op/data enters each wrapper in sequence.
//   - If addr matches THIS wrapper's ADDR and op=PROGRAM(0): capture 3
//     sequential 32-bit words (word_idx 0,1,2) into a 96-bit assembly
//     register, then pulse this cell's cfg_valid with the assembled word
//     zero-extended to 128 bits (bits [127:96], the out_buffer region, are
//     NOT config-loadable — matches #98's "3 words filling cmd_latch's
//     meaningful 96 bits" exactly).
//   - If addr matches and op=COLLECT(1): substitute this cell's own
//     out_buffer onto bus_out_data instead of passing the incoming value
//     through — "reads" the cell without touching it.
//   - Non-matching wrappers pass the bus straight through — REGISTERED,
//     not combinational, matching real scan-chain/JTAG practice (each
//     TDI->TDO stage is a clocked pipeline stage, not a same-cycle
//     combinational chain through all 25 wrappers at once — that would be
//     an artificial, unrealistic critical path, not a fair measurement of
//     the wrapper's real per-cell cost).
`default_nettype none
`timescale 1ns / 1ps

module cell_wrapper_v1 #(
    parameter [4:0] ADDR = 5'd0
) (
    input  wire        clk,
    input  wire        rst,

    // ── Daisy-chain bus, in ──
    input  wire        bus_in_valid,
    input  wire [4:0]  bus_in_addr,
    input  wire        bus_in_op,     // 0=PROGRAM, 1=COLLECT
    input  wire [31:0] bus_in_data,

    // ── Daisy-chain bus, out (registered — one pipeline stage per hop) ──
    output reg         bus_out_valid,
    output reg [4:0]   bus_out_addr,
    output reg         bus_out_op,
    output reg [31:0]  bus_out_data,

    // ── This wrapper's own cell ──
    output reg          cell_cfg_valid,
    output reg [127:0]  cell_cfg_data,
    input  wire [31:0]  cell_out_buffer,
    input  wire         cell_ready
);

reg [1:0]  word_idx = 2'h0;
reg [95:0] assemble  = 96'h0;

wire match = bus_in_valid && (bus_in_addr == ADDR);

always @(posedge clk) begin
    if (rst) begin
        word_idx       <= 2'h0;
        assemble       <= 96'h0;
        cell_cfg_valid <= 1'b0;
        cell_cfg_data  <= 128'h0;
        bus_out_valid  <= 1'b0;
        bus_out_addr   <= 5'h0;
        bus_out_op     <= 1'b0;
        bus_out_data   <= 32'h0;
    end else begin
        cell_cfg_valid <= 1'b0;   // one-cycle pulse by default

        if (match && !bus_in_op) begin
            // PROGRAM: assemble 3 sequential words, pulse cfg_valid on the 3rd.
            // On word 2, cell_cfg_data is built explicitly from the FRESH
            // incoming word (top 32 bits) plus the ALREADY-COMMITTED lower
            // 64 bits from words 0/1 (assemble[63:0] holds last cycle's
            // values here, since nonblocking reads see pre-edge state) —
            // NOT read back from `assemble` alone, which wouldn't yet
            // reflect this cycle's word.
            case (word_idx)
                2'd0: assemble[31:0]  <= bus_in_data;
                2'd1: assemble[63:32] <= bus_in_data;
                2'd2: begin
                    assemble[95:64] <= bus_in_data;
                    cell_cfg_valid  <= 1'b1;
                    cell_cfg_data   <= {32'h0, bus_in_data, assemble[63:32], assemble[31:0]};
                end
            endcase
            word_idx <= (word_idx == 2'd2) ? 2'd0 : (word_idx + 2'd1);
        end

        // Registered pass-through / COLLECT substitution
        bus_out_valid <= bus_in_valid;
        bus_out_addr  <= bus_in_addr;
        bus_out_op    <= bus_in_op;
        bus_out_data  <= (match && bus_in_op) ? cell_out_buffer : bus_in_data;
    end
end

endmodule
