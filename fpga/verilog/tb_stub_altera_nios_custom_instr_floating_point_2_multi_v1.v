`timescale 1ns / 1ps
// tb_stub_altera_nios_custom_instr_floating_point_2_multi_v1.v --
// SIMULATION-ONLY stand-in for the real Nios II Custom Instruction IP
// `altera_nios_custom_instr_floating_point_2_multi` (points.md #469,
// real port list confirmed directly from Alan's own real generated
// .qsys file). Reproduces the real, documented start/done handshake
// and real per-`n` cycle counts (Intel's own official table: n=253
// ADD/5cyc, n=254 SUB/5cyc, n=252 MUL/4cyc) -- deliberately NOT real
// IEEE-754 arithmetic (a simple, deterministic bitwise placeholder per
// `n`), only real, confirmed TIMING, so dsp_arith_wrapper_v1.v's own
// protocol logic can be verified independent of the real arithmetic
// result. Must NEVER be used in a real synthesis run.
module altera_nios_custom_instr_floating_point_2_multi (
    input  wire        clk,
    input  wire        clk_en,
    input  wire        reset,
    output wire         reset_req,
    input  wire [31:0] dataa,
    input  wire [31:0] datab,
    input  wire [7:0]  n,
    input  wire        start,
    output reg          done,
    output reg  [31:0] result
);
    assign reset_req = 1'b0;   // real direction/behavior unconfirmed (#469) -- inert stub default

    reg [3:0] cyc_left;
    reg       busy;
    reg [31:0] latched_a, latched_b;
    reg [7:0]  latched_n;

    // Real, confirmed per-n cycle counts (Intel's own official table).
    function [3:0] real_cycles(input [7:0] nval);
        case (nval)
            8'd253: real_cycles = 4'd5;   // ADD
            8'd254: real_cycles = 4'd5;   // SUB
            8'd252: real_cycles = 4'd4;   // MUL
            default: real_cycles = 4'd5;
        endcase
    endfunction

    always @(posedge clk) begin
        if (reset) begin
            busy <= 1'b0;
            done <= 1'b0;
            cyc_left <= 4'd0;
        end else begin
            done <= 1'b0;
            if (start && !busy) begin
                busy <= 1'b1;
                latched_a <= dataa;
                latched_b <= datab;
                latched_n <= n;
                cyc_left  <= real_cycles(n) - 4'd1;
            end else if (busy) begin
                if (cyc_left == 4'd0) begin
                    busy   <= 1'b0;
                    done   <= 1'b1;
                    result <= (latched_n == 8'd253) ? (latched_a ^ latched_b) :        // NOT real IEEE-754 add
                              (latched_n == 8'd254) ? (latched_a ^ (~latched_b)) :      // NOT real IEEE-754 sub
                              (latched_a & latched_b);                                  // NOT real IEEE-754 mul
                end else begin
                    cyc_left <= cyc_left - 4'd1;
                end
            end
        end
    end
endmodule
