`timescale 1ns/1ps
// tb_hexn_tier_v1.v -- testbench for hexn_tier_v1 against sdram_model_v1: puts N keys, updates every 7th, gets all N (checks value) and M never-seen keys (checks not found), then prints the counters on one line for tools/hexn_tier_ref_v1.py to compare. Keys/values: hash32 of an index (same as the Python side).
module tb_hexn_tier_v1;
    parameter KW = 24, FB = 8, BMB = 12, RAMB = 10, P = 8, N = 600, M = 300;
    reg clk = 0, resetn = 0; always #18.5185 clk = ~clk; wire clk_sdram = ~clk;
    reg cmd_valid = 0, cmd_we = 0; reg [KW-1:0] key = 0; reg [31:0] wdata = 0;
    wire busy, done, found, ready; wire [31:0] rdata;
    wire [31:0] n_fast_put, n_sd_put, n_overflow, n_fast_hit, n_skip, n_sd_get, n_fp, n_sd_rd, n_sd_wr, n_found, n_notfound;
    wire O_clk, O_cke, O_cs, O_ras, O_cas, O_wen; wire [31:0] dq; wire [10:0] O_a; wire [1:0] O_ba; wire [3:0] O_dqm;
    hexn_tier_v1 #(.KW(KW), .FB(FB), .BMB(BMB), .RAMB(RAMB), .P(P)) dut (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(3'd3), .cmd_valid(cmd_valid), .cmd_we(cmd_we), .key(key), .wdata(wdata),
        .busy(busy), .done(done), .found(found), .rdata(rdata), .ready(ready), .n_fast_put(n_fast_put), .n_sd_put(n_sd_put), .n_overflow(n_overflow), .n_fast_hit(n_fast_hit), .n_skip(n_skip), .n_sd_get(n_sd_get), .n_fp(n_fp), .n_sd_rd(n_sd_rd), .n_sd_wr(n_sd_wr), .n_found(n_found), .n_notfound(n_notfound),
        .O_sdram_clk(O_clk), .O_sdram_cke(O_cke), .O_sdram_cs_n(O_cs), .O_sdram_ras_n(O_ras), .O_sdram_cas_n(O_cas), .O_sdram_wen_n(O_wen), .IO_sdram_dq(dq), .O_sdram_addr(O_a), .O_sdram_ba(O_ba), .O_sdram_dqm(O_dqm));
    sdram_model_v1 #(.CL(3'd2)) model (.CLK(O_clk), .CKE(O_cke), .CS_N(O_cs), .RAS_N(O_ras), .CAS_N(O_cas), .WE_N(O_wen), .A(O_a), .BA(O_ba), .DQM(O_dqm), .DQ(dq));
    function [31:0] hash32(input [31:0] x);
        reg [31:0] m; begin m = x * 32'h9E3779B1; m = m ^ (m >> 15); m = m * 32'h85EBCA6B; hash32 = m ^ (m >> 13); end
    endfunction
    function [KW-1:0] kof(input integer i); kof = hash32(i + 1) & 24'hFFFFFF; endfunction
    function [31:0] vof(input integer i); vof = hash32(i + 32'h9999); endfunction
    function [31:0] uof(input integer i); uof = hash32(i + 32'h7777); endfunction
    function [KW-1:0] xof(input integer i); xof = hash32(i + 100000) & 24'hFFFFFF; endfunction
    reg [31:0] ev [0:N-1]; reg [KW-1:0] ek [0:N-1]; integer bad = 0, lost = 0, i, j, t0, t1; reg known, ef; reg [31:0] eval;
    task op(input we, input [KW-1:0] k, input [31:0] d);
        begin
            @(posedge clk); cmd_valid <= 1; cmd_we <= we; key <= k; wdata <= d;
            @(posedge clk); cmd_valid <= 0;
            @(posedge clk); while (!done) @(posedge clk);
        end
    endtask
    initial begin
        #200; resetn = 1; wait (ready); $display("ready at %0t", $time); t0 = $time;
        for (i = 0; i < N; i = i + 1) begin ek[i] = kof(i); ev[i] = vof(i); op(1, ek[i], ev[i]); end
        for (i = 0; i < N; i = i + 7) begin ev[i] = uof(i); op(1, ek[i], ev[i]); end
        // a duplicate key made by the hash would have an earlier value overwritten: the scoreboard follows the last write
        for (i = 0; i < N; i = i + 1) begin
            eval = ev[i]; for (j = i + 1; j < N; j = j + 1) if (ek[j] == ek[i]) eval = ev[j];
            op(0, ek[i], 0);
            if (!found) lost = lost + 1;   // allowed only for puts the tier dropped on SDRAM probe overflow (counted)
            else if (rdata !== eval) begin bad = bad + 1; if (bad < 10) $display("known key %0d: got %h want %h", i, rdata, eval); end
        end
        for (i = 0; i < M; i = i + 1) begin
            known = 0; for (j = 0; j < N; j = j + 1) if (ek[j] == xof(i)) known = 1;
            op(0, xof(i), 0);
            if (found && !known) begin bad = bad + 1; if (bad < 10) $display("unknown key %0d: found %b", i, found); end
        end
        t1 = $time;
        $display("COUNTERS fast_put=%0d sd_put=%0d overflow=%0d fast_hit=%0d skip=%0d sd_get=%0d fp=%0d sd_rd=%0d sd_wr=%0d found=%0d notfound=%0d", n_fast_put, n_sd_put, n_overflow, n_fast_hit, n_skip, n_sd_get, n_fp, n_sd_rd, n_sd_wr, n_found, n_notfound);
        $display("ops time %0d us, SDRAM rule violations %0d, data errors %0d, known keys not found %0d (dropped by overflow: %0d)", (t1 - t0) / 1000, model.errors, bad, lost, n_overflow);
        if (bad == 0 && model.errors == 0 && lost <= n_overflow) $display("TIER TEST PASS"); else $display("TIER TEST FAIL");
        $finish;
    end
    initial begin #2000000000; $display("TIER TEST FAIL: timeout"); $finish; end
endmodule
