// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// dsp_arith_wrapper_v1.v — points.md #466's own real request: a single
// DSP chain build needs real timing values across the real DSP modes,
// so the watchdog threshold for each can be chosen for real reasons,
// not guessed. Generalizes `dsp_add_wrapper_v1.v`'s own exact proven
// protocol (#463/#465, left completely untouched, not modified in
// place) to also cover SUBTRACT and MULTIPLY -- real, confirmed same
// 3-cycle latency as ADD (#462), same real megafunction port
// convention, so one genuinely reusable module covers all three real
// arithmetic modes cleanly rather than three near-duplicate files.
//
// REAL, CONFIRMED megafunction names (#462): `alterafpf_add_single`,
// `alterafpf_sub_single`, `alterafpf_mul_single` -- all real, confirmed
// 3 clock cycles latency, all sharing the same real
// `dataa`/`datab`/`clock`/`result` port shape (assumed, per the same
// standard-Altera-convention caveat `dsp_add_wrapper_v1.v` already
// states -- not independently confirmed against a real generated IP).
//
// Comparison operations (NEQ/LE/GE) are deliberately NOT covered here
// -- real, confirmed shorter latency and a boolean rather than 32-bit
// float result, different enough semantics to warrant their own file
// (`dsp_compare_wrapper_v1.v`) rather than forcing a false unification.
`default_nettype none
`timescale 1ns / 1ps

module dsp_arith_wrapper_v1 #(
    parameter OP             = "ADD",   // "ADD" | "SUB" | "MUL"
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

    // ── Real, confirmed latency (#462): all three arithmetic
    // megafunctions take exactly 3 real clock cycles -- the same
    // value regardless of OP, confirmed against real Intel
    // documentation, not assumed uniform. ──
    localparam ARITH_LATENCY = 3;

    reg [31:0] latched_a, latched_b;
    reg        primed_a, primed_b;
    reg [1:0]  wait_cnt;
    reg        computing;
    reg        result_ready;

    assign ack_out_a = arrived_a && !primed_a && !computing;
    assign ack_out_b = arrived_b && !primed_b && !computing;

    wire both_primed = primed_a && primed_b;

    wire [31:0] arith_result;

    // ── Real, explicit selection of the actual megafunction, per the
    // real `OP` parameter -- a genuine compile-time choice, not a
    // runtime mux across three real hard IP instances (which would
    // needlessly cost 3x the real DSP block usage for a single real
    // operation). ──
    generate
        if (OP == "ADD") begin : gen_add
            alterafpf_add_single DSP_OP (
                .dataa(latched_a), .datab(latched_b), .clock(clk), .result(arith_result)
            );
        end else if (OP == "SUB") begin : gen_sub
            alterafpf_sub_single DSP_OP (
                .dataa(latched_a), .datab(latched_b), .clock(clk), .result(arith_result)
            );
        end else if (OP == "MUL") begin : gen_mul
            alterafpf_mul_single DSP_OP (
                .dataa(latched_a), .datab(latched_b), .clock(clk), .result(arith_result)
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
            wait_cnt     <= 2'd0;
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
                wait_cnt  <= 2'd0;
            end else if (computing && !result_ready) begin
                if (wait_cnt == ARITH_LATENCY - 1) begin
                    data_out     <= arith_result;
                    result_ready <= 1'b1;
                end else begin
                    wait_cnt <= wait_cnt + 2'd1;
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
