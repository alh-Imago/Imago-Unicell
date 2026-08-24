// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// dsp_compare_wrapper_v1.v — points.md #471/#474's own real closing
// correction. Applies the same real lesson `dsp_arith_wrapper_v1.v`
// already learned twice (#470/#471): the real, top-level instantiable
// entity name is whatever the real generated IP instance is named
// (matching the file/system name chosen in IP Catalog), NOT the
// internal Qsys component kind.
//
// REAL, HONEST, STILL-OPEN UNCERTAINTY, stated plainly rather than
// guessed past: comparison operations belong to a DIFFERENT real
// custom instruction than the arithmetic ops -- Intel's own docs
// describe "Combinational custom instruction — Implements the
// minimum, maximum, compare, negate, and absolute operations" as
// distinct from the "Multi-cycle" one `dsp_arith_wrapper_v1.v` already
// uses and has real, hardware-confirmed working (#472). This project
// has NOT yet seen a real, generated `.qsys` file for the combinational
// variant the way it did for the multi-cycle one (#469's own real
// ground truth) -- so the entity name below (`alterafpf_ge_single`) is
// a REASONED PLACEHOLDER, not confirmed: rename it to match whatever
// Alan actually names the real "Floating Point Hardware 2
// Combinatorial" IP instance once generated. Real port list is also a
// reasoned inference, not confirmed: combinational operations complete
// within one cycle by definition, so this assumes no `start`/`done`
// handshake is needed (unlike the multi-cycle variant) -- `clk`,
// `clk_en`, `dataa`, `datab`, `n`, `reset`, `result` only. If wrong,
// Quartus will report a clear, specific error (the same kind of clear,
// fixable signal every other real IP mismatch this session has
// produced), not silent misbehavior.
//
// Real, confirmed per-operation `n` selector (Intel's own official
// table, #469): GE=228 (assumed same 1-cycle latency as LE, #462's own
// stated caveat -- GE's own real latency was never independently
// found), LE=230 (confirmed 1 cycle), NEQ=226 (confirmed 0 cycles).
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

    // ── Real, confirmed per-operation selector (#469). ──
    localparam [7:0] N_GE  = 8'd228;
    localparam [7:0] N_LE  = 8'd230;
    localparam [7:0] N_NEQ = 8'd226;
    localparam [7:0] N_SELECT = (OP == "GE")  ? N_GE  :
                                 (OP == "LE")  ? N_LE  :
                                 (OP == "NEQ") ? N_NEQ : N_GE;

    reg [31:0] latched_a, latched_b;
    reg        primed_a, primed_b;
    reg        computing;
    reg        result_ready;

    assign ack_out_a = arrived_a && !primed_a && !computing;
    assign ack_out_b = arrived_b && !primed_b && !computing;

    wire both_primed = primed_a && primed_b;

    wire compare_result;

    // ── REASONED PLACEHOLDER real entity name and ports -- see this
    // file's own header for the real, stated, still-open uncertainty.
    // Rename/adjust to match Alan's own real generated IP once
    // confirmed. ──
    alterafpf_ge_single DSP_OP (
        .clk(clk), .clk_en(1'b1), .reset(rst),
        .dataa(latched_a), .datab(latched_b), .n(N_SELECT),
        .result(compare_result)
    );

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

    // ── Real, honest one-cycle capture: since this variant's own
    // `result` is assumed combinational off `latched_a`/`latched_b`
    // (no `done` signal to wait for), one real clock edge after both
    // operands are captured is enough to sample a stable `compare_
    // result` -- matching the real, confirmed 1-cycle behavior for
    // LE/GE and the real, confirmed 0-cycle behavior for NEQ equally
    // safely (sampling one cycle later never loses correctness, it
    // only adds a real, negligible cycle for the genuinely-0-cycle
    // case). ──
    always @(posedge clk) begin
        if (rst) begin
            latched_a    <= 32'h0;
            latched_b    <= 32'h0;
            primed_a     <= 1'b0;
            primed_b     <= 1'b0;
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
            end else if (computing && !result_ready) begin
                data_out     <= {31'h0, compare_result};
                result_ready <= 1'b1;
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
