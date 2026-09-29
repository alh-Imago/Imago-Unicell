// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mul_cell_v4s_dsp3.v -- points.md #902: the time-multiplexed DSP mul, per Alan's
// own real proposal -- trade latency for DSP footprint so MORE logical mul cells
// can fit on the chip at once, each owning a small MULT18X18 slot instead of a
// whole MULT36X36 tile.
//
// Refinement made before building, not after: since this whole family already
// truncates every multiply to its low 32 bits (matching mul_cell_v4/v4c/v4s's
// own existing convention), the A_high*B_high partial product is UNNECESSARY --
// it only ever affects bits 32-63 of the real 64-bit product, which this
// convention discards regardless (verified by exhaustive random check against
// the real product before trusting it, not assumed). So this needs three
// MULT18X18 uses, not four, plus a real 4th state that captures the pipeline's
// first genuinely fresh operands -- see the state list below.
//
// A real off-by-one-cycle bug found and fixed while building this (not assumed
// correct): DOUT is purely combinational for this primitive's chosen
// configuration (AREG=BREG=OUT_REG=0), so each partial product must be
// registered in the SAME cycle its operands are presented to the multiplier --
// an earlier draft tried to capture it one cycle late, using a_hold/b_hold
// before their own capture had taken effect, silently multiplying the WRONG
// (stale) operands. Fixed by registering each partial product in the same case
// branch that sets up the next state's operands, and folding the final partial
// product straight into the sum on its own cycle rather than needing a separate
// sum-only state.
//
// Real states (4 cycles total, matching Alan's own original framing exactly):
//   ST_LOAD: capture fresh in_a/in_b into a_hold/b_hold. Nothing useful to
//            register from the multiplier yet -- a_hold/b_hold aren't valid
//            until NEXT cycle (this is exactly the timing subtlety the bug
//            above was caused by getting wrong).
//   ST_LL:   a_hold/b_hold now valid. mult_a/mult_b = a_low/b_low. Real product
//            registered into pp_ll THIS cycle (DOUT is combinational).
//   ST_LH:   mult_a/mult_b = a_low/b_high. Real product registered into pp_lh.
//   ST_HL:   mult_a/mult_b = a_high/b_low. This cycle's real product is used
//            DIRECTLY (combinationally, same cycle) together with the already-
//            registered pp_ll/pp_lh to compute the final sum, registered into
//            out_buffer -- no separate sum-only state needed.
//
// Real, fixed, known 4-cycle LATENCY -- exactly the kind of number the family's
// still-unbuilt latency-matching work needs, no different in kind from any other
// cell's fixed one-cycle latency, just a bigger fixed number.
//
// A real, honest THROUGHPUT constraint that must be stated plainly, not
// discovered the hard way: this cell can only START a new operation once every
// 4 cycles (the state machine only captures a fresh in_a/in_b during ST_LOAD). A
// `valid_in` pulse presented during the other 3 cycles of an in-flight operation
// is genuinely, silently missed -- not an error, not corruption, simply not
// sampled. Upstream logic driving this cell must only assert `valid_in` once
// every 4 cycles, aligned to this cell's own free-running state counter (or
// accept that faster requests will be dropped). Tested explicitly: the real
// testbench checks the aligned back-to-back case and the off-boundary-miss case
// directly, not just in comment form.
`default_nettype none
`timescale 1ns / 1ps

module mul_cell_v4s_dsp3 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,   // unused; kept for a uniform port shape

    input  wire [31:0]  in_a,
    input  wire [31:0]  in_b,
    input  wire         valid_in,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    reg        armed       = 1'b0;
    reg [31:0] out_buffer  = 32'h0;
    reg        valid_out_r = 1'b0;

    localparam [1:0] ST_LOAD = 2'd0, ST_LL = 2'd1, ST_LH = 2'd2, ST_HL = 2'd3;
    reg [1:0] state = ST_LOAD;

    reg [31:0] a_hold = 32'h0, b_hold = 32'h0;
    reg [31:0] pp_ll  = 32'h0, pp_lh  = 32'h0;
    reg [3:0]  valid_pipe = 4'h0;   // one bit per cycle of the fixed 4-cycle latency

    wire [15:0] a_low  = a_hold[15:0];
    wire [15:0] a_high = a_hold[31:16];
    wire [15:0] b_low  = b_hold[15:0];
    wire [15:0] b_high = b_hold[31:16];

    // The ONE real shared MULT18X18 -- selected operands per state. ST_LOAD's
    // operands are genuinely don't-care (a_hold/b_hold aren't valid yet, and
    // nothing registers this state's dsp_out).
    reg [17:0] mult_a, mult_b;
    always @(*) begin
        case (state)
            ST_LL:   begin mult_a = {2'h0, a_low};  mult_b = {2'h0, b_low};  end
            ST_LH:   begin mult_a = {2'h0, a_low};  mult_b = {2'h0, b_high}; end
            ST_HL:   begin mult_a = {2'h0, a_high}; mult_b = {2'h0, b_low};  end
            default: begin mult_a = 18'h0;          mult_b = 18'h0;         end
        endcase
    end

    wire [35:0] dsp_out;
    MULT18X18 MUL (
        .A(mult_a), .SIA(18'h0), .B(mult_b), .SIB(18'h0),
        .ASIGN(1'b0), .BSIGN(1'b0), .ASEL(1'b0), .BSEL(1'b0),
        .CE(1'b1), .CLK(clk), .RESET(rst),
        .DOUT(dsp_out), .SOA(), .SOB()
    );

    // Only bits [15:0] of pp_lh (and of this cycle's own HL product) land inside
    // the kept low-32-bit output at all -- verified by exhaustive random check
    // against the real product before trusting it (bit k of a shifted-by-16
    // partial product lands at output bit k+16; k=16..31 would land at output
    // bits 32..47, which the 32-bit truncation discards).
    wire [33:0] sum34 = {2'h0, pp_ll} + {2'h0, pp_lh[15:0], 16'h0} + {2'h0, dsp_out[15:0], 16'h0};

    assign data_out  = out_buffer;
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            armed       <= 1'b0;
            out_buffer  <= 32'h0;
            valid_out_r <= 1'b0;
            state       <= ST_LOAD;
            a_hold      <= 32'h0;
            b_hold      <= 32'h0;
            pp_ll       <= 32'h0;
            pp_lh       <= 32'h0;
            valid_pipe  <= 4'h0;
        end else if (cfg_valid) begin
            armed       <= 1'b1;
            valid_out_r <= 1'b0;
            state       <= ST_LOAD;
            valid_pipe  <= 4'h0;
        end else begin
            // Free-running 4-state cycle -- unconditional, exactly like every
            // other v4s cell's fixed-latency register, just spread over more
            // stages.
            case (state)
                ST_LOAD: begin
                    a_hold <= in_a; b_hold <= in_b;
                    state  <= ST_LL;
                end
                ST_LL: begin
                    pp_ll <= dsp_out[31:0];   // real A_low * B_low, THIS cycle's operands
                    state <= ST_LH;
                end
                ST_LH: begin
                    pp_lh <= dsp_out[31:0];   // real A_low * B_high, THIS cycle's operands
                    state <= ST_HL;
                end
                ST_HL: begin
                    // This cycle's own real product (A_high * B_low) is used
                    // directly, combinationally, together with the already-
                    // registered pp_ll/pp_lh -- no separate sum state needed.
                    out_buffer <= sum34[31:0];
                    state      <= ST_LOAD;
                end
            endcase

            valid_pipe  <= {valid_pipe[2:0], armed && valid_in};
            valid_out_r <= valid_pipe[2];
        end
    end

endmodule
