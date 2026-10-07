// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// ram_cell_v4sa.v -- points.md #915: the Flex-Sub shape (ack+freeze per #906,
// WIDTH per #909/#910) applied to ram. A real design point worth stating:
// fixed_mode and flowing mode genuinely need DIFFERENT treatment here, not
// one shape forced onto both. Fixed mode's whole point is "always valid,
// never drains" (unchanged from ram_cell_v4s.v) -- there is nothing to offer
// and wait for, so it does not use the pending/ack protocol at all; ack_out
// simply reflects "configured", and valid_out is continuously high. Flowing
// mode uses the SAME pending/ack discipline as every other v4sa cell.
//
// cfg_data field map, unchanged: [31:0] init_data. cfg_fixed_mode on its own
// small port, same reason as v4s (1 bit + a full 32-bit word doesn't fit in
// one 32-bit cfg_data together).
`default_nettype none
`timescale 1ns / 1ps

module ram_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,
    // ledger #1011: the constant / init word SCALES with the cell: a WIDTH-bit cell has a WIDTH-bit init port (never narrower than the 32-bit config bus,
    // so every existing 32-bit-or-narrower instance is byte-for-byte the same port as before).
    input  wire [(WIDTH > 32 ? WIDTH : 32)-1:0]  cfg_data,
    input  wire         cfg_fixed_mode,

    input  wire [WIDTH-1:0]  data_in,
    input  wire               valid_in,
    output wire                ack_out,     // backward, to whoever feeds data_in (flowing mode only)

    output wire [WIDTH-1:0]  data_out,
    output wire               valid_out,
    input  wire               ack_in       // backward, from the downstream receiver (flowing mode only)
);

    reg                  fixed_mode  = 1'b0;
    reg                  armed       = 1'b0;
    reg                  pending     = 1'b0;   // flowing mode only
    reg [WIDTH-1:0]      data_reg    = {WIDTH{1'b0}};

    assign data_out  = data_reg;
    assign valid_out = fixed_mode ? armed : pending;
    // Fixed mode is always ready (nothing to offer-and-wait-for, it is a
    // constant); flowing mode follows the standard pending/ack discipline.
    assign ack_out   = fixed_mode ? (armed && !freeze_in) : (armed && !pending && !freeze_in);

    always @(posedge clk) begin
        if (rst) begin
            fixed_mode  <= 1'b0;
            armed       <= 1'b0;
            pending     <= 1'b0;
            data_reg    <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            fixed_mode  <= cfg_fixed_mode;
            data_reg    <= cfg_data[WIDTH-1:0];
            armed       <= 1'b1;
            pending     <= 1'b0;
        end else if (!freeze_in) begin
            if (!fixed_mode) begin
                if (pending) begin
                    if (ack_in) pending <= 1'b0;
                end else if (valid_in) begin
                    data_reg <= data_in;
                    pending  <= 1'b1;
                end
            end
            // fixed_mode: data_reg and valid_out (via armed) simply hold
            // forever, same as v4s.
        end
    end

endmodule
