`timescale 1ns/1ps
// tb_hexn_tang_sdramtest_v1.v -- simulates the board self-test (hexn_tang_sdramtest_v1) against our SDRAM model with the stand-in PLL: start-up, 256 writes, three read-back passes with rdlat 2, 3, 4. The model samples data at the ideal point, so only rdlat 3 should be clean; the LEDs must read: lock, done, init_done and clean for 3 only (lit = 0 on the board, so the LED word is inverted here to show lit = 1).
module tb_hexn_tang_sdramtest_v1;
    reg clk27 = 0; always #18.5185 clk27 = ~clk27;
    wire [5:0] led; wire O_clk, O_cke, O_cs, O_cas, O_ras, O_wen; wire [3:0] O_dqm; wire [10:0] O_a; wire [1:0] O_ba; wire [31:0] dq;
    hexn_tang_sdramtest_v1 dut (.clk27(clk27), .led(led), .O_sdram_clk(O_clk), .O_sdram_cke(O_cke), .O_sdram_cs_n(O_cs), .O_sdram_cas_n(O_cas), .O_sdram_ras_n(O_ras), .O_sdram_wen_n(O_wen), .O_sdram_dqm(O_dqm), .O_sdram_addr(O_a), .O_sdram_ba(O_ba), .IO_sdram_dq(dq));
    sdram_model_v1 #(.CL(3'd2)) model (.CLK(O_clk), .CKE(O_cke), .CS_N(O_cs), .RAS_N(O_ras), .CAS_N(O_cas), .WE_N(O_wen), .A(O_a), .BA(O_ba), .DQM(O_dqm), .DQ(dq));
    wire [5:0] lit = ~led;
    initial begin
        wait (lit[4]); #1000;
        $display("lit LEDs (led5..led0) = %b: clean read-back with rdlat 2 = %b, 3 = %b, 4 = %b; init done = %b; finished = %b; PLL locked = %b; model: writes %0d, reads %0d, refreshes %0d, rule violations %0d", lit, lit[0], lit[1], lit[2], lit[3], lit[4], lit[5], model.writes, model.reads, model.refreshes, model.errors);
        if (lit[5:3] == 3'b111 && lit[2:0] == 3'b010 && model.errors == 0) $display("SDRAM SELFTEST PASS"); else $display("SDRAM SELFTEST FAIL");
        $finish;
    end
    initial begin #50000000; $display("SDRAM SELFTEST FAIL: timeout, LEDs lit %b", lit); $finish; end
endmodule
