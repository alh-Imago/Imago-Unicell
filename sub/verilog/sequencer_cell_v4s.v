// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// sequencer_cell_v4s.v -- stripped version of sequencer_cell_v4c.v's real
// function. A real structural point worth stating: the original never captures
// any incoming data at all -- it advances purely when its CURRENT offer's ack
// completes, i.e. purely on the backward handshake this whole family removes.
// The forward-only replacement: a dedicated `advance_in` pulse, an explicit
// external "move to the next value" event -- a genuine forward control input, not
// a backward ack, so it fits the family's philosophy cleanly (this is exactly the
// external tick pattern #892's real on-board smoke test already used
// successfully for the same underlying core).
//
// One family convention bent slightly, for a real reason: this cell's native
// config (four 8-bit values + a 2-bit sequence length) is 34 bits, one more than
// the shared cfg_data[31:0] can hold once all four values keep their full width.
// Rather than shrink a value or force an awkward re-pack, sequence length gets
// its own small, separate config input, loaded on the same cfg_valid pulse.
//
// cfg_data field map:
//   [7:0]   VALUE_0
//   [15:8]  VALUE_1
//   [23:16] VALUE_2
//   [31:24] VALUE_3
// cfg_seq_len_m1[1:0]: sequence length minus 1 (0 = length 1, ... 3 = length 4)
`default_nettype none
`timescale 1ns / 1ps

module sequencer_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,
    input  wire [1:0]   cfg_seq_len_m1,

    input  wire         advance_in,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    reg [7:0] value_0 = 8'h00, value_1 = 8'h00, value_2 = 8'h00, value_3 = 8'h00;
    reg [1:0] sequence_len_m1 = 2'd0;
    reg       armed = 1'b0;

    reg [1:0] seq_index   = 2'd0;
    reg [7:0] out_buffer  = 8'h00;
    reg       valid_out_r = 1'b0;

    // ── Real, unchanged from v4c ─────────────────────────────────────────
    function [7:0] value_for_index(input [1:0] idx);
        case (idx)
            2'd0: value_for_index = value_0;
            2'd1: value_for_index = value_1;
            2'd2: value_for_index = value_2;
            default: value_for_index = value_3;
        endcase
    endfunction

    wire [1:0] next_seq_index = (seq_index == sequence_len_m1) ? 2'd0 : seq_index + 2'd1;

    assign data_out  = {24'h0, out_buffer};
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            value_0 <= 8'h00; value_1 <= 8'h00; value_2 <= 8'h00; value_3 <= 8'h00;
            sequence_len_m1 <= 2'd0;
            armed           <= 1'b0;
            seq_index       <= 2'd0;
            out_buffer      <= 8'h00;
            valid_out_r     <= 1'b0;
        end else if (cfg_valid) begin
            value_0         <= cfg_data[7:0];
            value_1         <= cfg_data[15:8];
            value_2         <= cfg_data[23:16];
            value_3         <= cfg_data[31:24];
            sequence_len_m1 <= cfg_seq_len_m1;
            armed           <= 1'b1;
            seq_index       <= 2'd0;
            out_buffer      <= cfg_data[7:0];   // value_for_index(0)
            valid_out_r     <= 1'b0;
        end else begin
            if (advance_in) begin
                seq_index  <= next_seq_index;
                out_buffer <= value_for_index(next_seq_index);
            end
            valid_out_r <= armed && advance_in;
        end
    end

endmodule
