`timescale 1ns/1ps
// tb_hexn_tang_tiertest_v1.v -- simulates the board test top (hexn_tang_tiertest_v1) with the stand-in PLL against our SDRAM model, decodes the 16-line serial report and prints it as one line "REPORT R0=... ..." for tests/test_hexn_tiertest_v1.py. Small sizes (the board defaults are larger).
module tb_hexn_tang_tiertest_v1;
    parameter KW = 18, VW = 18, FB = 8, BMB = 12, RAMB = 12, P = 8, N = 300, M = 150;
    reg clk27 = 0; always #18.5185 clk27 = ~clk27;
    wire [5:0] led; wire utx; wire O_clk, O_cke, O_cs, O_cas, O_ras, O_wen; wire [3:0] O_dqm; wire [10:0] O_a; wire [1:0] O_ba; wire [31:0] dq;
    hexn_tang_tiertest_v1 #(.KW(KW), .VW(VW), .FB(FB), .BMB(BMB), .RAMB(RAMB), .P(P), .N(N), .M(M), .GAP(2000), .CLKDIV(8)) dut (.clk27(clk27), .uart_tx(utx), .led(led), .O_sdram_clk(O_clk), .O_sdram_cke(O_cke), .O_sdram_cs_n(O_cs), .O_sdram_cas_n(O_cas), .O_sdram_ras_n(O_ras), .O_sdram_wen_n(O_wen), .O_sdram_dqm(O_dqm), .O_sdram_addr(O_a), .O_sdram_ba(O_ba), .IO_sdram_dq(dq));
    sdram_model_v1 #(.CL(3'd2)) model (.CLK(O_clk), .CKE(O_cke), .CS_N(O_cs), .RAS_N(O_ras), .CAS_N(O_cas), .WE_N(O_wen), .A(O_a), .BA(O_ba), .DQM(O_dqm), .DQ(dq));
    reg [7:0] chars [0:207]; integer n = 0, k, l; reg [7:0] b; real bt = 8 * 37.037;
    initial begin
        wait (utx === 1'b1);
        forever begin
            @(negedge utx); #(bt * 1.5); for (k = 0; k < 8; k = k + 1) begin b[k] = utx; #bt; end
            if (n < 208) begin chars[n] = b; n = n + 1; end
        end
    end
    initial begin
        wait (n == 208); #1000;
        $write("REPORT"); for (l = 0; l < 208; l = l + 1) if (chars[l] != 8'h0D && chars[l] != 8'h0A) $write("%c", chars[l]); else if (chars[l] == 8'h0A) $write(" "); $write("\n");
        $display("leds %b, SDRAM rule violations %0d", led, model.errors);
        if (model.errors == 0) $display("TIERTEST SIM DONE"); else $display("TIERTEST SIM FAIL");
        $finish;
    end
    initial begin #4000000000; $display("TIERTEST SIM FAIL: timeout, %0d characters", n); $finish; end
endmodule
