// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mul_cell_v4sa.v -- points.md #916: the Flex-Sub shape (ack+freeze per #906,
// WIDTH per #909/#910) applied to the LUT-built ("actual mul core itself",
// per Alan's own framing) multiply -- the no-DSP-dependency alternative to
// mul_cell_v4sa_dsp.v, kept deliberately separate, not a replacement for it.
//
// A real, deliberate choice made here, not inherited silently:
// `bitwise_multiplier_32bit.v` (mul_cell_v4/v4c/v4s's own real multiplier) is
// hardcoded for exactly 32-bit operands and is SHARED with the mainline
// cardinal-routed cells -- not something to modify for this family's own
// purposes. Rather than touch a shared file (the same caution mask_cell_v4sa.v
// already applied to nibble_mask_addon_v1.v), this uses a plain, genuinely
// WIDTH-generic `in_a * in_b`. #901 already confirmed directly that this
// toolchain's synth_gowin pass never infers DSP blocks from a plain multiply
// -- it synthesises to ordinary LUT logic, functionally equivalent to the
// array multiplier's own real purpose (a no-DSP-dependency fallback), even
// though it is not gate-for-gate identical in structure to the original.
`default_nettype none
`timescale 1ns / 1ps

module mul_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,   // unused; kept for a uniform port shape

    input  wire [WIDTH-1:0]  in_a,
    input  wire [WIDTH-1:0]  in_b,
    input  wire               valid_in,
    output wire                ack_out,     // backward, to whoever feeds in_a/in_b

    output wire [WIDTH-1:0]  data_out,
    output wire               valid_out,   // stays high until ack_in, not a one-shot pulse
    input  wire               ack_in       // backward, from the one fixed downstream receiver
);

    reg             armed       = 1'b0;
    reg             pending     = 1'b0;
    reg [WIDTH-1:0] out_buffer  = {WIDTH{1'b0}};

    // ── The real arithmetic -- a plain, genuinely width-generic multiply,
    // not the shared, fixed-32-bit bitwise_multiplier_32bit.v primitive ────
    wire [2*WIDTH-1:0] full_product = in_a * in_b;

    assign data_out  = out_buffer;
    assign valid_out = pending;
    assign ack_out   = armed && !pending && !freeze_in;

    always @(posedge clk) begin
        if (rst) begin
            armed       <= 1'b0;
            pending     <= 1'b0;
            out_buffer  <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            armed       <= 1'b1;
            pending     <= 1'b0;
        end else if (!freeze_in) begin
            if (pending) begin
                if (ack_in) pending <= 1'b0;
            end else if (valid_in) begin
                out_buffer <= full_product[WIDTH-1:0];
                pending    <= 1'b1;
            end
        end
    end

endmodule
