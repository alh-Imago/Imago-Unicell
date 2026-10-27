`timescale 1ns/1ps
// tb_hexn_tang_sdramtest_v2.v -- simulates the second board self-test (hexn_tang_sdramtest_v2) with the stand-in PLL against our SDRAM model, decodes the serial report and checks it: the ideal model returns good data only at rdlat 3, so L3 must read err=0000 d0=9E3779B1 and every other line (L1, L2, L4, L5, L6 and the negative control LN) err=0100.
module tb_hexn_tang_sdramtest_v2;
    reg clk27 = 0; always #18.5185 clk27 = ~clk27;
    wire [5:0] led; wire utx; wire O_clk, O_cke, O_cs, O_cas, O_ras, O_wen; wire [3:0] O_dqm; wire [10:0] O_a; wire [1:0] O_ba; wire [31:0] dq;
    hexn_tang_sdramtest_v2 #(.GAP(2000)) dut (.clk27(clk27), .uart_tx(utx), .led(led), .O_sdram_clk(O_clk), .O_sdram_cke(O_cke), .O_sdram_cs_n(O_cs), .O_sdram_cas_n(O_cas), .O_sdram_ras_n(O_ras), .O_sdram_wen_n(O_wen), .O_sdram_dqm(O_dqm), .O_sdram_addr(O_a), .O_sdram_ba(O_ba), .IO_sdram_dq(dq));
    sdram_model_v1 #(.CL(3'd2)) model (.CLK(O_clk), .CKE(O_cke), .CS_N(O_cs), .RAS_N(O_ras), .CAS_N(O_cas), .WE_N(O_wen), .A(O_a), .BA(O_ba), .DQM(O_dqm), .DQ(dq));
    // serial decoder: 115200 baud = 8680.5 ns per bit
    reg [7:0] chars [0:174]; integer n = 0, k, bad = 0; reg [7:0] b;
    initial begin
        wait (utx === 1'b1);
        forever begin
            @(negedge utx); #(8680.5 * 1.5); for (k = 0; k < 8; k = k + 1) begin b[k] = utx; #8680.5; end
            if (n < 175) begin chars[n] = b; n = n + 1; end
        end
    end
    function [31:0] f4(input integer base); f4 = {chars[base], chars[base+1], chars[base+2], chars[base+3]}; endfunction
    integer l; reg [31:0] e4;
    initial begin
        wait (n == 175); #1000;
        for (l = 0; l < 7; l = l + 1) begin
            e4 = f4(l*25 + 7);
            if (l == 2) begin if (e4 !== "0000") begin bad = bad + 1; $display("line %0d: err field %s, wanted 0000", l, e4); end end
            else if (e4 !== "0100") begin bad = bad + 1; $display("line %0d: err field %s, wanted 0100", l, e4); end
        end
        if ({chars[2*25+15], chars[2*25+16], chars[2*25+17], chars[2*25+18], chars[2*25+19], chars[2*25+20], chars[2*25+21], chars[2*25+22]} !== "9E3779B1") begin bad = bad + 1; $display("line 2: d0 wrong"); end
        $write("report:"); for (l = 0; l < 175; l = l + 1) if (chars[l] != 8'h0D) $write("%c", (chars[l] == 8'h0A) ? 8'h7C : chars[l]); $write("\n");
        if (bad == 0 && model.errors == 0) $display("SDRAM SELFTEST2 PASS"); else $display("SDRAM SELFTEST2 FAIL");
        $finish;
    end
    initial begin #400000000; $display("SDRAM SELFTEST2 FAIL: timeout, %0d characters", n); $finish; end
endmodule
