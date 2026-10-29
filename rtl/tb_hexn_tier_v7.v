`timescale 1ns/1ps
// tb_hexn_tier_v7.v -- testbench for hexn_tier_v7 against the Wishbone DDR stand-in (wb_ddr_model_v1): STEPS pseudo-random PUT/GET operations on NK keys (same arithmetic as tb_hexn_tier_v6.v), flush, counters + every DDR line printed, then a GET of every key, flush, counters + lines again. tests/test_hexn_tier_v7_rtl.py compares all of it with tools/hexn_tier_ref_v3.py (Tier3, SPS = 8).
module tb_hexn_tier_v7;
    parameter KW = 12, VW = 12, FB = 4, BMB = 8, RAMB = 6, SB = 5, NK = 120, STEPS = 400, LAT = 9, JIT = 3, STALLP = 4;
    reg clk = 0, resetn = 0; always #5 clk = ~clk;
    reg cmd_valid = 0, cmd_we = 0, cmd_flush = 0; reg [KW-1:0] key = 0; reg [VW-1:0] wdata = 0;
    wire busy, done, found, ready, ddr_err; wire [VW-1:0] rdata; wire [32*17-1:0] cnts;
    wire wb_stb, wb_we, wb_stall, wb_ack, ddr_ready; wire [24:0] wb_addr; wire [575:0] wb_data, wb_rdata;
    hexn_tier_v7 #(.KW(KW), .VW(VW), .FB(FB), .BMB(BMB), .RAMB(RAMB), .SB(SB), .DDR_BASE(0)) dut (.clk(clk), .resetn(resetn), .cmd_valid(cmd_valid), .cmd_we(cmd_we), .cmd_flush(cmd_flush), .key(key), .wdata(wdata),
        .busy(busy), .done(done), .found(found), .rdata(rdata), .ready(ready), .cnts(cnts), .ddr_err(ddr_err), .ddr_ready(ddr_ready),
        .wb_stb(wb_stb), .wb_we(wb_we), .wb_addr(wb_addr), .wb_data(wb_data), .wb_stall(wb_stall), .wb_ack(wb_ack), .wb_rdata(wb_rdata));
    wb_ddr_model_v1 #(.LINES((1 << SB) + 8), .LAT(LAT), .JIT(JIT), .STALLP(STALLP)) ddr (.clk(clk), .resetn(1'b1), .o_ready(ddr_ready), .i_stb(wb_stb), .i_we(wb_we), .i_addr(wb_addr), .i_data(wb_data), .i_sel({72{1'b1}}), .o_stall(wb_stall), .o_ack(wb_ack), .o_data(wb_rdata));
    function [31:0] hash32(input [31:0] x);
        reg [31:0] m; begin m = x * 32'h9E3779B1; m = m ^ (m >> 15); m = m * 32'h85EBCA6B; hash32 = m ^ (m >> 13); end
    endfunction
    localparam [31:0] MK = (32'd1 << KW) - 1, MV = (64'd1 << VW) - 1;
    reg [VW-1:0] ev [0:NK-1]; reg ek [0:NK-1]; integer bad = 0, n, ki, i, b; reg [31:0] r; reg [KW-1:0] kk;
    task op(input fl, input we, input [KW-1:0] k, input [VW-1:0] d);
        begin
            @(posedge clk); cmd_valid <= 1; cmd_flush <= fl; cmd_we <= we; key <= k; wdata <= d;
            @(posedge clk); cmd_valid <= 0;
            @(posedge clk); while (!done) @(posedge clk);
        end
    endtask
    task show(input [8*10-1:0] tag);
        integer q;
        begin
            $write("%0s", tag);
            for (q = 0; q < 17; q = q + 1) $write(" %0d", cnts[32*q +: 32]);
            $write("\n");
        end
    endtask
    task dump(input [8*6-1:0] tag);
        begin
            for (b = 0; b < (1 << SB); b = b + 1) $write("%0s %0d %0144h\n", tag, b, ddr.mem[b]);
        end
    endtask
    initial begin
        for (i = 0; i < NK; i = i + 1) ek[i] = 0;
        #50; resetn = 1; wait (ready);
        for (n = 0; n < STEPS; n = n + 1) begin
            r = hash32(n + 32'h1111); ki = (r >> 4) % NK; kk = ((ki + 1) * 32'h2545F491) & MK;
            if (((r >> 20) % 10) < 4) begin ev[ki] = hash32(n + 32'h5151) & MV; ek[ki] = 1; op(0, 1, kk, ev[ki]); end
            else begin
                op(0, 0, kk, 0);
                if (found) begin if (!ek[ki] || rdata !== ev[ki]) begin bad = bad + 1; if (bad < 10) $display("step %0d key %0d: got %h want %h known %b", n, ki, rdata, ev[ki], ek[ki]); end end
            end
        end
        op(1, 0, 0, 0); show("COUNTERS1"); dump("LINES1");
        for (i = 0; i < NK; i = i + 1) begin
            kk = ((i + 1) * 32'h2545F491) & MK; op(0, 0, kk, 0);
            $display("R %0d %0d %0d", i, found, found ? rdata : 0);
            if (found && (!ek[i] || rdata !== ev[i])) begin bad = bad + 1; if (bad < 10) $display("final: key %0d got %h want %h known %b", i, rdata, ev[i], ek[i]); end
        end
        op(1, 0, 0, 0); show("COUNTERS2"); dump("LINES2");
        $display("data errors %0d, ddr_err %b", bad, ddr_err);
        if (bad == 0 && !ddr_err) $display("TIER7 TEST PASS"); else $display("TIER7 TEST FAIL");
        $finish;
    end
    initial begin #2000000000; $display("TIER7 TEST FAIL: timeout"); $finish; end
endmodule
