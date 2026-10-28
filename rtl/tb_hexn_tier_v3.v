`timescale 1ns/1ps
// tb_hexn_tier_v3.v -- testbench for hexn_tier_v3 against the rule-checking SDRAM model and the behavioural SD card model: STEPS pseudo-random PUT/GET operations on a pool of NK distinct keys (everything from the step number by arithmetic, so tests/test_hexn_tier_v3.py can run the same sequence through tools/hexn_tier_ref_v3.py), then a FLUSH. Every GET is checked against a scoreboard; a known key that is not found is only allowed if the card sector overflow counter (sd_full) says entries were dropped. Prints the 17 counters on one line.
module tb_hexn_tier_v3;
    parameter KW = 18, VW = 18, FB = 5, BMB = 10, RAMB = 5, SB = 3, NK = 300, STEPS = 1500;
    reg clk = 0, resetn = 0; always #18.5185 clk = ~clk; wire clk_sdram = ~clk;
    reg cmd_valid = 0, cmd_we = 0, cmd_flush = 0; reg [KW-1:0] key = 0; reg [VW-1:0] wdata = 0;
    wire busy, done, found, ready, sd_error; wire [VW-1:0] rdata; wire [32*17-1:0] cnts;
    wire O_clk, O_cke, O_cs, O_ras, O_cas, O_wen; wire [31:0] dq; wire [10:0] O_a; wire [1:0] O_ba; wire [3:0] O_dqm; wire sclk, mosi, miso, scs;
    hexn_tier_v3 #(.KW(KW), .VW(VW), .FB(FB), .BMB(BMB), .RAMB(RAMB), .SB(SB), .SD_BASE(0), .INIT_DIV(2), .FAST_DIV(1)) dut (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(3'd3),
        .cmd_valid(cmd_valid), .cmd_we(cmd_we), .cmd_flush(cmd_flush), .key(key), .wdata(wdata), .busy(busy), .done(done), .found(found), .rdata(rdata), .ready(ready), .cnts(cnts), .sd_error(sd_error),
        .O_sdram_clk(O_clk), .O_sdram_cke(O_cke), .O_sdram_cs_n(O_cs), .O_sdram_ras_n(O_ras), .O_sdram_cas_n(O_cas), .O_sdram_wen_n(O_wen), .IO_sdram_dq(dq), .O_sdram_addr(O_a), .O_sdram_ba(O_ba), .O_sdram_dqm(O_dqm),
        .sd_clk(sclk), .sd_mosi(mosi), .sd_miso(miso), .sd_cs_n(scs));
    sdram_model_v1 #(.CL(3'd2)) model (.CLK(O_clk), .CKE(O_cke), .CS_N(O_cs), .RAS_N(O_ras), .CAS_N(O_cas), .WE_N(O_wen), .A(O_a), .BA(O_ba), .DQM(O_dqm), .DQ(dq));
    sd_card_model_v1 #(.SDHC(1), .BLOCKS(1 << SB), .READY_AFTER(3)) card (.sclk(sclk), .mosi(mosi), .cs_n(scs), .miso(miso));
    function [31:0] hash32(input [31:0] x);
        reg [31:0] m; begin m = x * 32'h9E3779B1; m = m ^ (m >> 15); m = m * 32'h85EBCA6B; hash32 = m ^ (m >> 13); end
    endfunction
    localparam [31:0] MK = (32'd1 << KW) - 1, MV = (64'd1 << VW) - 1;
    reg [VW-1:0] ev [0:NK-1]; reg ek [0:NK-1]; integer bad = 0, lost = 0, n, ki, i; reg [31:0] r; reg [KW-1:0] kk;
    task op(input fl, input we, input [KW-1:0] k, input [VW-1:0] d);
        begin
            @(posedge clk); cmd_valid <= 1; cmd_flush <= fl; cmd_we <= we; key <= k; wdata <= d;
            @(posedge clk); cmd_valid <= 0;
            @(posedge clk); while (!done) @(posedge clk);
        end
    endtask
    initial begin
        for (i = 0; i < NK; i = i + 1) ek[i] = 0;
        #200; resetn = 1; wait (ready); $display("ready at %0t", $time);
        for (n = 0; n < STEPS; n = n + 1) begin
            r = hash32(n + 32'h1111); ki = (r >> 4) % NK; kk = ((ki + 1) * 32'h2545F491) & MK;
            if (((r >> 20) % 10) < 4) begin ev[ki] = hash32(n + 32'h5151) & MV; ek[ki] = 1; op(0, 1, kk, ev[ki]); end
            else begin
                op(0, 0, kk, 0);
                if (found) begin if (!ek[ki] || rdata !== ev[ki]) begin bad = bad + 1; if (bad < 10) $display("step %0d key %0d: found %b got %h want %h known %b", n, ki, found, rdata, ev[ki], ek[ki]); end end
                else if (ek[ki]) lost = lost + 1;
            end
        end
        op(1, 0, 0, 0);
        $display("COUNTERS fast_hit=%0d sdram_hit=%0d skip=%0d sd_get=%0d fp=%0d sd_blk_rd=%0d sd_blk_wr=%0d buf_hit=%0d promote_sdram=%0d promote_sd=%0d demote_sdram=%0d demote_sd=%0d sd_full=%0d found=%0d notfound=%0d put_update=%0d put_new=%0d",
            cnts[31:0], cnts[63:32], cnts[95:64], cnts[127:96], cnts[159:128], cnts[191:160], cnts[223:192], cnts[255:224], cnts[287:256], cnts[319:288], cnts[351:320], cnts[383:352], cnts[415:384], cnts[447:416], cnts[479:448], cnts[511:480], cnts[543:512]);
        $display("SDRAM rule violations %0d, data errors %0d, known keys not found %0d (sd_full %0d), card error %b", model.errors, bad, lost, cnts[415:384], sd_error);
        if (bad == 0 && model.errors == 0 && !sd_error && lost <= cnts[415:384]) $display("TIER3 TEST PASS"); else $display("TIER3 TEST FAIL");
        $finish;
    end
    initial begin #20000000000; $display("TIER3 TEST FAIL: timeout"); $finish; end
endmodule
