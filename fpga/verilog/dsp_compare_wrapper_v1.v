// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// dsp_compare_wrapper_v1.v — points.md #466's own real request, the
// comparison half. Real, confirmed shorter latency than the arithmetic
// ops (#462): `alterafpf_le_single_LE` = 1 real clock cycle,
// `alterafpf_neq_single_NEQ` = 0 real cycles. `GE`'s own exact real
// latency was NOT independently confirmed in the same search (#462's
// own search result was cut off right after naming
// `alterafpf_ge_single_GE`, before its own cycle count) -- this file
// uses LE's confirmed 1-cycle value as the reasonable default for GE
// too (same real comparison class of operation), flagged explicitly as
// an assumption, not confirmed fact, same discipline as every other
// unconfirmed real IP detail in this project.
//
// A REAL, deliberate design difference from `dsp_arith_wrapper_v1.v`,
// not an oversight: comparison ops produce a single BOOLEAN result,
// not a 32-bit float -- offered on `data_out[0]`, matching this
// project's own already-established "LSB of the 32-bit data bus
// carries a flag" convention (`compare_cell_v1.v`'s own real, already-
// documented convention, reused here for consistency).
`default_nettype none
`timescale 1ns / 1ps

module dsp_compare_wrapper_v1 #(
    parameter OP             = "GE",   // "GE" | "LE" | "NEQ"
    parameter WATCHDOG_WIDTH = 16
) (
    input  wire        clk,
    input  wire        rst,

    input  wire [31:0] data_in_a,
    input  wire        arrived_a,
    output wire         ack_out_a,

    input  wire [31:0] data_in_b,
    input  wire        arrived_b,
    output wire         ack_out_b,

    output reg  [31:0] data_out,
    output wire         fire,
    input  wire         ready_in,
    input  wire         ack_in,

    input  wire                      wd_cfg_valid,
    input  wire [WATCHDOG_WIDTH-1:0] wd_cfg_threshold,
    output wire                      wd_timeout_err,
    output wire [WATCHDOG_WIDTH-1:0] wd_count_out
);

    // ── Real, confirmed for LE/NEQ (#462); GE assumed same as LE,
    // flagged explicitly above, not independently confirmed. ──
    localparam COMPARE_LATENCY = (OP == "NEQ") ? 0 : 1;

    reg [31:0] latched_a, latched_b;
    reg        primed_a, primed_b;
    reg        wait_done;
    reg        computing;
    reg        result_ready;

    assign ack_out_a = arrived_a && !primed_a && !computing;
    assign ack_out_b = arrived_b && !primed_b && !computing;

    wire both_primed = primed_a && primed_b;

    wire compare_result;

    generate
        if (OP == "GE") begin : gen_ge
            alterafpf_ge_single_GE DSP_OP (
                .dataa(latched_a), .datab(latched_b), .clock(clk), .result(compare_result)
            );
        end else if (OP == "LE") begin : gen_le
            alterafpf_le_single_LE DSP_OP (
                .dataa(latched_a), .datab(latched_b), .clock(clk), .result(compare_result)
            );
        end else if (OP == "NEQ") begin : gen_neq
            alterafpf_neq_single_NEQ DSP_OP (
                .dataa(latched_a), .datab(latched_b), .clock(clk), .result(compare_result)
            );
        end
    endgenerate

    wire will_fire = result_ready && ready_in;
    assign fire = will_fire;

    wire wd_activity_pulse = ack_out_a || ack_out_b || (will_fire && ack_in);

    watchdog_v1 #(.WIDTH(WATCHDOG_WIDTH)) WATCHDOG (
        .clk(clk), .rst(rst),
        .cfg_valid(wd_cfg_valid), .cfg_threshold(wd_cfg_threshold),
        .activity_pulse(wd_activity_pulse),
        .timeout_flag(wd_timeout_err),
        .count_out(wd_count_out)
    );

    always @(posedge clk) begin
        if (rst) begin
            latched_a    <= 32'h0;
            latched_b    <= 32'h0;
            primed_a     <= 1'b0;
            primed_b     <= 1'b0;
            wait_done    <= 1'b0;
            computing    <= 1'b0;
            result_ready <= 1'b0;
            data_out     <= 32'h0;
        end else begin
            if (ack_out_a) begin
                latched_a <= data_in_a;
                primed_a  <= 1'b1;
            end
            if (ack_out_b) begin
                latched_b <= data_in_b;
                primed_b  <= 1'b1;
            end

            if (both_primed && !computing) begin
                computing <= 1'b1;
                wait_done <= (COMPARE_LATENCY == 0);   // NEQ's own real 0-cycle case needs no wait at all
            end else if (computing && !result_ready) begin
                if (wait_done) begin
                    data_out     <= {31'h0, compare_result};
                    result_ready <= 1'b1;
                end else begin
                    wait_done <= 1'b1;   // real 1-cycle latency case (LE/GE): one real wait cycle then done
                end
            end

            if (will_fire && ack_in) begin
                computing    <= 1'b0;
                result_ready <= 1'b0;
                primed_a     <= 1'b0;
                primed_b     <= 1'b0;
            end
        end
    end

endmodule
