// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// adder_cell_v4s.v -- the first "v4s" (stripped) cell, per Alan's own real design
// direction from a live conversation (2026-09-29, morning), building directly on
// that session's own measured findings:
//
//   - #886 measured shift_lane_addon_v2 alone at ~2,600 LUT4 -- bigger than this
//     WHOLE adder core (adder_full 2,348 LUT4) -- so the addon chain is gone here
//     entirely, not made optional. There is no addon_config field at all.
//   - #889 found that nearly an entire cell's footprint, for several light types,
//     was the SHARED HANDSHAKE SKELETON (armed/pending_ack/ready_in/ready_out/the
//     4-way mask decode) -- not the function it nominally computed. That skeleton
//     is removed here too: no ack, no ready, no upstream/downstream mask, no
//     per-direction arrived tracking.
//   - #885 already measured the winning shape this design commits to structurally:
//     a static, fixed-latency pipeline stage beat the general ack-driven fold on
//     both size and speed (8 cells/19 ticks vs 56 cells/204 ticks, same job).
//
// What is DELIBERATELY gone, and why (real trade-offs, not oversights):
//   - Cardinal routing (N/S/E/W): replaced by two FIXED, dedicated operand inputs
//     (in_a, in_b) and one fixed output. "No cardinality" removes the runtime
//     DECISION of which direction data comes from/goes to -- it does not reduce
//     a binary function's real arity below two operands. Each operand has its own
//     permanent wire; there is no mask, so there is nothing to decide at runtime.
//   - Backward ack/ready (flow control): gone entirely, by design, not an
//     oversight. This is what makes the cell genuinely timing-agnostic -- no cell
//     can ever be told to wait. The real consequence Alan named directly: every
//     cell's latency must now be a KNOWN, FIXED number of cycles at build time,
//     and any two paths that CONVERGE on a later cell must arrive latency-matched,
//     or a fresh value on one side silently combines with a stale one on the
//     other. This is not a new problem for the project -- #762-#765's timing
//     model and dsp_latency_v1's latency-padding mechanism already exist to solve
//     exactly this; they have simply never been pointed at this cell family yet.
//     That padding work is the real next step this file creates a need for, not
//     something this file itself solves.
//   - freeze_in: also removed, as a direct consequence of the above, not a
//     separate cut. A per-cell pause would silently break every latency guarantee
//     downstream of it. If a global pause is ever needed, it must be a single
//     synchronized clock-enable across the WHOLE chain at once, never per-cell --
//     that is a separate, future design question, not addressed here.
//   - Live per-direction reprogramming (program_in/prog_data_in_*): removed for
//     this first cut. There is no longer a cardinal direction to receive a
//     reprogramming word from. Config is boot-load only here (cfg_valid/cfg_data);
//     a future shared reprogramming bus for the v4s family, if wanted, is a
//     separate design question, deliberately not decided by this file.
//
// The "timing line": a single FORWARD valid_out bit riding alongside data_out,
// asserted for exactly one cycle when data_out holds a genuinely new result.
// This is not ack's replacement -- it carries no backward information and never
// stalls anything upstream. A downstream cell either uses it or free-runs without
// it; either way this cell never waits and never asks anyone else to wait.
//
// Fixed latency: exactly ONE clock cycle from (valid_in asserted, in_a/in_b
// present) to (valid_out asserted, data_out holding the result). This number is
// the whole point -- it is what a real latency-padding scheme downstream needs to
// know, and it must stay exactly this if this file is ever edited.
//
// cfg_data field map (deliberately tiny -- no mask, no addon config left to hold):
//   [0]     subtract_mode -- 0 = A+B, 1 = A-B (same semantics as adder_cell_v4/v4c)
//   [31:1]  reserved
`default_nettype none
`timescale 1ns / 1ps

module adder_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire [31:0]  in_a,
    input  wire [31:0]  in_b,
    input  wire         valid_in,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    reg        subtract_mode = 1'b0;
    reg        armed         = 1'b0;   // gates output until cfg_valid has loaded real config once
    reg [31:0] out_buffer    = 32'h0;
    reg        valid_out_r   = 1'b0;

    // ── The real arithmetic -- unchanged from adder_v1, the same primitive
    // adder_cell_v4/v4c already use ──────────────────────────────────────
    wire [31:0] adder_b_in = subtract_mode ? ~in_b : in_b;
    wire [31:0] adder_sum;
    wire        adder_cout;
    adder_v1 #(.WIDTH(32)) ADD (
        .a(in_a), .b(adder_b_in), .cin(subtract_mode),
        .sum(adder_sum), .cout(adder_cout)
    );

    assign data_out  = out_buffer;
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            subtract_mode <= 1'b0;
            armed         <= 1'b0;
            out_buffer    <= 32'h0;
            valid_out_r   <= 1'b0;
        end else if (cfg_valid) begin
            subtract_mode <= cfg_data[0];
            armed         <= 1'b1;
            valid_out_r   <= 1'b0;
        end else begin
            // Fixed one-cycle latency: this cycle's inputs become next cycle's
            // output, unconditionally once armed. No capture/hold state, no
            // wait -- the whole reason this is timing-agnostic.
            out_buffer  <= adder_sum;
            valid_out_r <= armed && valid_in;
        end
    end

endmodule
