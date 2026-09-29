// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// ram_cell_v4s.v -- stripped version of ram_cell_v4c.v's real function: hold one
// 32-bit value, either fixed at configuration time (ROM-style) or freshly
// captured whenever new data genuinely arrives (flowing). No backward
// ack/draining concept survives here -- in flowing mode, every valid_in simply
// overwrites the held value; there is no "already have unconsumed data" gating,
// because there is no consumer that could ever fail to consume it in time.
//
// Same small-extra-config-port pattern as sequencer_cell_v4s.v: fixed_mode (1
// bit) plus a full 32-bit init_data doesn't fit together in one 32-bit cfg_data,
// so fixed_mode gets its own tiny dedicated config input.
//
// fixed_mode behaviour, unchanged in spirit from v4c: once armed, a fixed-mode
// cell's held value never changes and its valid_out is CONTINUOUSLY high (there
// is no backward "offer draining" to ever clear it, matching the original's own
// `!fixed_mode` guard on that clear). A flowing-mode cell's valid_out pulses only
// on the cycle a genuine new capture happens.
//
// cfg_data field map:
//   [31:0] init_data -- the preset value (fixed mode) or the initial held value
//                        before any real capture (flowing mode)
// cfg_fixed_mode: 1 = ROM-style permanent value, 0 = flowing (captures on valid_in)
`default_nettype none
`timescale 1ns / 1ps

module ram_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,
    input  wire         cfg_fixed_mode,

    input  wire [31:0]  data_in,
    input  wire         valid_in,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    reg        fixed_mode  = 1'b0;
    reg        armed       = 1'b0;
    reg [31:0] data_reg    = 32'h0;
    reg        valid_out_r = 1'b0;

    assign data_out  = data_reg;
    assign valid_out = fixed_mode ? armed : valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            fixed_mode  <= 1'b0;
            armed       <= 1'b0;
            data_reg    <= 32'h0;
            valid_out_r <= 1'b0;
        end else if (cfg_valid) begin
            fixed_mode  <= cfg_fixed_mode;
            data_reg    <= cfg_data;
            armed       <= 1'b1;
            valid_out_r <= 1'b0;
        end else if (!fixed_mode) begin
            if (valid_in) data_reg <= data_in;
            valid_out_r <= armed && valid_in;
        end
        // fixed_mode: data_reg and valid_out (via armed) simply hold forever.
    end

endmodule
