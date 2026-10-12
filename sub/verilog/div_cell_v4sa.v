// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// div_cell_v4sa.v -- ledger #1070: the division core for the FLEX family (v4sa shape: ack + global freeze,
// WIDTH parameter, a second output as its own port). Unsigned restoring long division, run as a loop:
// STEPS bits of the quotient per clock. The cell takes ceil(WIDTH/STEPS) clocks after it captures its
// operands; STEPS = 1 is the smallest and fastest-clocked form (one subtractor, WIDTH clocks), STEPS = WIDTH
// is the whole division in one clock (a WIDTH-deep chain). Nothing outside the cell needs to know the
// count: valid_out rises when the result is ready and ack_out stays low while the cell is busy, so a
// longer cell only delays what waits on it (the two-operand join upstream waits for its other part).
//
// Operand roles are by PORT, not by arrival: in_a is the DIVIDEND, in_b is the DIVISOR (the join of the
// two, valid_in = vA & vB, is made upstream exactly as for adder_cell_v4sa).
//
// Results (unsigned):  data_out = in_a / in_b   (quotient)
//                      rem_out  = in_a % in_b   (remainder; own valid/ack, only when cfg_data[0] = rem_enable
//                                                and SECOND_PORT = 1, otherwise silent and costs nothing)
// Division by zero is not special-cased in the logic: every step "fits", so the quotient comes out all
// ones and the remainder equals the dividend -- the same rule the LaTeX front end uses (x/0 = all ones,
// x mod 0 = x).
//
// Why the remainder register can be WIDTH bits: before each shift it holds at most the top (j-1) bits of
// the dividend (it is a remainder of a prefix), which is below 2^(WIDTH-1), so 2R+bit always fits.
// The subtract is still done in WIDTH+1 bits so the "does it fit" decision is the borrow bit.
//
// cfg_data[0] = rem_enable.  Reconfiguring discards an operation in flight, as adder_cell_v4sa does.
`default_nettype none
`timescale 1ns / 1ps

module div_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        SECOND_PORT = 0,   // 1 = build the remainder port's logic
    parameter        WIDTH   = 32,      // >= 2
    parameter        STEPS   = 1        // quotient bits produced per clock, 1..WIDTH
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire [WIDTH-1:0]  in_a,      // dividend
    input  wire [WIDTH-1:0]  in_b,      // divisor
    input  wire              valid_in,
    output wire               ack_out,

    output wire [WIDTH-1:0]  data_out,  // quotient
    output wire               valid_out,
    input  wire               ack_in,

    output wire [WIDTH-1:0]  rem_out,   // remainder
    output wire               valid_out_r,
    input  wire               ack_in_r
);

    localparam CW = $clog2(WIDTH + 1);

    reg             rem_enable = 1'b0;
    reg             armed      = 1'b0;
    reg             busy       = 1'b0;
    reg             pending    = 1'b0;
    reg             pending_r  = 1'b0;
    reg [WIDTH-1:0] d_reg      = {WIDTH{1'b0}};
    reg [WIDTH-1:0] r_reg      = {WIDTH{1'b0}};
    reg [WIDTH-1:0] q_reg      = {WIDTH{1'b0}};     // starts as the dividend; its bits shift out at the top as quotient bits shift in
    reg [CW-1:0]    remaining  = {CW{1'b0}};
    reg [WIDTH-1:0] out_buffer = {WIDTH{1'b0}};
    reg [WIDTH-1:0] rem_buffer = {WIDTH{1'b0}};

    // ── STEPS restoring-division steps in one clock; a step is skipped once the bits are used up ──
    reg [WIDTH-1:0] nR, nQ;
    reg [WIDTH:0]   diff;
    integer         i;
    always @* begin
        nR = r_reg;
        nQ = q_reg;
        diff = {(WIDTH+1){1'b0}};
        for (i = 0; i < STEPS; i = i + 1) begin
            if (i < remaining) begin
                nR   = {nR[WIDTH-2:0], nQ[WIDTH-1]};
                nQ   = {nQ[WIDTH-2:0], 1'b0};
                diff = {1'b0, nR} - {1'b0, d_reg};
                if (!diff[WIDTH]) begin
                    nR    = diff[WIDTH-1:0];
                    nQ[0] = 1'b1;
                end
            end
        end
    end
    wire last_clock = (remaining <= STEPS);

    assign data_out    = out_buffer;
    assign valid_out   = pending;
    assign rem_out     = rem_buffer;
    assign valid_out_r = pending_r;
    assign ack_out     = armed && !busy && !pending && !pending_r && !freeze_in;

    always @(posedge clk) begin
        if (rst) begin
            rem_enable <= 1'b0;
            armed      <= 1'b0;
            busy       <= 1'b0;
            pending    <= 1'b0;
            pending_r  <= 1'b0;
            remaining  <= {CW{1'b0}};
            out_buffer <= {WIDTH{1'b0}};
            rem_buffer <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            rem_enable <= (SECOND_PORT != 0) && cfg_data[0];
            armed      <= 1'b1;
            busy       <= 1'b0;
            pending    <= 1'b0;
            pending_r  <= 1'b0;
            out_buffer <= {WIDTH{1'b0}};
            rem_buffer <= {WIDTH{1'b0}};
        end else if (!freeze_in) begin
            if (busy) begin
                r_reg <= nR;
                q_reg <= nQ;
                if (last_clock) begin
                    busy       <= 1'b0;
                    pending    <= 1'b1;
                    pending_r  <= rem_enable;
                    out_buffer <= nQ;
                    rem_buffer <= (SECOND_PORT != 0) ? nR : {WIDTH{1'b0}};
                    remaining  <= {CW{1'b0}};
                end else begin
                    remaining  <= remaining - STEPS;
                end
            end else if (pending || pending_r) begin
                if (pending   && ack_in)   pending   <= 1'b0;
                if (pending_r && ack_in_r) pending_r <= 1'b0;
            end else if (valid_in) begin
                d_reg     <= in_b;
                q_reg     <= in_a;
                r_reg     <= {WIDTH{1'b0}};
                remaining <= WIDTH;
                busy      <= 1'b1;
            end
        end
    end

endmodule
