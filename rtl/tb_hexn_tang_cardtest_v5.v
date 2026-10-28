`timescale 1ns/1ps
// tb_hexn_tang_cardtest_v5.v -- simulates the board test top hexn_tang_cardtest_v5 with the stand-in PLL, the rule-checking SDRAM model and the behavioural SD card. The card outside the test region is filled with 0xA5 ("owner data") and must be unchanged at the end; POISON >= 0 puts one non-zero byte into that block of the region, and the test must then refuse (no write at all). Decodes the 97-line serial report and prints it as one line "REPORT H00=... ..." for tests/test_hexn_cardtest_v5.py.
module tb_hexn_tang_cardtest_v5;
    parameter KW = 18, VW = 18, FB = 3, RAMB = 3, LB = 5, LOW = 3, SD_BASE = 40, N = 120, M = 40, POISON = -1, ERASE = 0;
    localparam LN = 97, NCH = LN * 14;
    localparam TOTAL = SD_BASE + (1 << LB) + 24;
    reg clk27 = 0; always #18.5185 clk27 = ~clk27;
    wire [5:0] led; wire utx; wire O_clk, O_cke, O_cs, O_cas, O_ras, O_wen; wire [3:0] O_dqm; wire [10:0] O_a; wire [1:0] O_ba; wire [31:0] dq; wire sclk, mosi, miso, scs;
    hexn_tang_cardtest_v5 #(.KW(KW), .VW(VW), .FB(FB), .RAMB(RAMB), .LB(LB), .LOW(LOW), .SD_BASE(SD_BASE), .ERASE(ERASE), .N(N), .M(M), .GAP(2000), .CLKDIV(8), .INIT_DIV(2), .FAST_DIV(1)) dut (.clk27(clk27), .uart_tx(utx), .led(led),
        .O_sdram_clk(O_clk), .O_sdram_cke(O_cke), .O_sdram_cs_n(O_cs), .O_sdram_cas_n(O_cas), .O_sdram_ras_n(O_ras), .O_sdram_wen_n(O_wen), .O_sdram_dqm(O_dqm), .O_sdram_addr(O_a), .O_sdram_ba(O_ba), .IO_sdram_dq(dq),
        .sd_clk(sclk), .sd_mosi(mosi), .sd_miso(miso), .sd_cs_n(scs));
    sdram_model_v1 #(.CL(3'd2)) model (.CLK(O_clk), .CKE(O_cke), .CS_N(O_cs), .RAS_N(O_ras), .CAS_N(O_cas), .WE_N(O_wen), .A(O_a), .BA(O_ba), .DQM(O_dqm), .DQ(dq));
    sd_card_model_v1 #(.SDHC(1), .BLOCKS(TOTAL), .READY_AFTER(3)) card (.sclk(sclk), .mosi(mosi), .cs_n(scs), .miso(miso));
    always @(posedge dut.pl) begin model.inited = 0; model.got_pre = 0; model.mode_set = 0; model.nref_init = 0; model.last_ref = -1; end   // the SDRAM model's start-up rules are only for a chip that has just been powered; the controller starts over after the reset
    reg [7:0] chars [0:NCH-1]; integer n = 0, k, l, bad_out = 0, wr_in_region = 0; reg [7:0] b; real bt = 8 * 37.037;
    initial begin
        for (k = 0; k < TOTAL * 512; k = k + 1) card.mem[k] = (k >= SD_BASE * 512 && k < (SD_BASE + (1 << LB)) * 512) ? 8'h00 : 8'hA5;
        if (POISON >= 0) card.mem[(SD_BASE + POISON) * 512 + 77] = 8'h5A;
        wait (utx === 1'b1);
        forever begin
            @(negedge utx); #(bt * 1.5); for (k = 0; k < 8; k = k + 1) begin b[k] = utx; #bt; end
            if (n < NCH) begin chars[n] = b; n = n + 1; end
        end
    end
    initial begin
        wait (n == NCH); #1000;
        for (k = 0; k < SD_BASE * 512; k = k + 1) if (card.mem[k] !== 8'hA5) bad_out = bad_out + 1;
        for (k = (SD_BASE + (1 << LB)) * 512; k < TOTAL * 512; k = k + 1) if (card.mem[k] !== 8'hA5) bad_out = bad_out + 1;
        if (POISON >= 0 && ERASE == 0) for (k = SD_BASE * 512; k < (SD_BASE + (1 << LB)) * 512; k = k + 1) if (card.mem[k] !== ((k == (SD_BASE + POISON) * 512 + 77) ? 8'h5A : 8'h00)) wr_in_region = wr_in_region + 1;
        $write("REPORT"); for (l = 0; l < NCH; l = l + 1) if (chars[l] != 8'h0D && chars[l] != 8'h0A) $write("%c", chars[l]); else if (chars[l] == 8'h0A) $write(" "); $write("\n");
        $display("leds %b, SDRAM rule violations %0d, bytes changed outside the region %0d, bytes changed in a refused region %0d", led, model.errors, bad_out, wr_in_region);
        if (model.errors == 0 && bad_out == 0 && wr_in_region == 0) $display("CARDTEST SIM DONE"); else $display("CARDTEST SIM FAIL");
        $finish;
    end
    initial begin #20000000000; $display("CARDTEST SIM FAIL: timeout, %0d characters", n); $finish; end
endmodule
