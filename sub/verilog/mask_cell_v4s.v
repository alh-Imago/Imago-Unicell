// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mask_cell_v4s.v -- a NEW v4s cell type: the nibble-mask function, extracted from
// nibble_mask_addon_v1.v (unchanged, reused directly), given its own standalone
// cell shell. See shift_cell_v4s.v / sub/README.md for the family's shared shape
// and rationale; identical structure here, different real function underneath.
//
// cfg_data field map (9 bits used, matching nibble_mask_addon_v1's own real ports
// exactly):
//   [0]    mask_en          -- 0=pass through unchanged, 1=apply the mask
//   [8:1]  nibble_mask[7:0] -- one bit per nibble, 1=BLOCK (zero it), 0=PASS
`default_nettype none
`timescale 1ns / 1ps

module mask_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire [31:0]  data_in,
    input  wire         valid_in,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    reg        mask_en      = 1'b0;
    reg  [7:0] nibble_mask  = 8'h0;
    reg        armed        = 1'b0;
    reg [31:0] out_buffer   = 32'h0;
    reg        valid_out_r  = 1'b0;

    // ── The real mask logic -- unchanged from nibble_mask_addon_v1 ──────
    wire [31:0] mask_result;
    nibble_mask_addon_v1 MASK (
        .mask_en(mask_en), .nibble_mask(nibble_mask),
        .data_in(data_in), .data_out(mask_result)
    );

    assign data_out  = out_buffer;
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            mask_en     <= 1'b0;
            nibble_mask <= 8'h0;
            armed       <= 1'b0;
            out_buffer  <= 32'h0;
            valid_out_r <= 1'b0;
        end else if (cfg_valid) begin
            mask_en     <= cfg_data[0];
            nibble_mask <= cfg_data[8:1];
            armed       <= 1'b1;
            valid_out_r <= 1'b0;
        end else begin
            out_buffer  <= mask_result;
            valid_out_r <= armed && valid_in;
        end
    end

endmodule
