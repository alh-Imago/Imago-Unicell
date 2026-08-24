`timescale 1ns / 1ps
// tb_stub_alterafpf_add_single_corrected_v1.v -- SIMULATION-ONLY
// stand-in for Alan's own real, actual generated IP, correctly named
// `alterafpf_add_single` (points.md #471 -- the real, top-level
// instantiable name, confirmed directly from a real Quartus error
// message, not the internal Qsys component kind #470 mistakenly used).
// Real, confirmed port list and real start/done handshake (#469, from
// Alan's own real .qsys file). Real, confirmed per-`n` cycle counts
// (Intel's own official table: n=253 ADD/5cyc, n=254 SUB/5cyc, n=252
// MUL/4cyc). Deliberately NOT real IEEE-754 arithmetic -- a simple,
// deterministic bitwise placeholder per `n`, only for verifying
// dsp_arith_wrapper_v1.v's own real protocol logic. Must NEVER be used
// in a real synthesis run.
//
// A SEPARATE FILE from tb_stub_alterafpf_add_single_v1.v (same real
// module name inside, `alterafpf_add_single`, but a DIFFERENT, WRONG
// port list) -- that older stub serves `dsp_add_wrapper_v1.v`, now a
// confirmed-obsolete historical artifact (#471) that was never
// actually built on real Quartus and is now known to use the wrong
// port convention. NEVER compile both stub files in the same run --
// same module name, genuinely different port lists, a real conflict.
module alterafpf_add_single (
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
                    result <= (latched_n == 8'd253) ? (latched_a ^ latched_b) :
                              (latched_n == 8'd254) ? (latched_a ^ (~latched_b)) :
                              (latched_a & latched_b);
                end else begin
                    cyc_left <= cyc_left - 4'd1;
                end
            end
        end
    end
endmodule
