`timescale 1ns/1ps
// tb_hexn_tier_v6.v -- testbench for hexn_tier_v5 against the rule-checking SDRAM model and the behavioural SD card model. STEPS pseudo-random PUT/GET operations on NK keys (the same arithmetic as tb_hexn_tier_v4.v, so tests/test_hexn_tier_v5.py runs the same sequence through tools/hexn_tier_ref_v5.py). MODE 0: end with a FLUSH. MODE 1: end with a SAVE, then reset the tier (the card and its contents stay), RESTORE, and GET every key. MODE 2: as MODE 1 but with nothing written at the end (a crash). CORRUPT >= 0 flips one byte of that card block before the reset (a damaged block). Prints COUNTERS1 (after phase 1), the card blocks (BLK1), after a restore COUNTERS2, one line per key (R index found value), COUNTERS3 and the final card (BLK2).
module tb_hexn_tier_v6;
    parameter KW = 12, VW = 12, FB = 4, RAMB = 4, LB = 5, LOW = 3, NK = 120, STEPS = 400, MODE = 1, CORRUPT = -1, LAT = 9, JIT = 3, STALLP = 4;
    reg clk = 0, resetn = 0; always #18.5185 clk = ~clk; wire clk_sdram = ~clk;
    reg cmd_valid = 0, cmd_we = 0, cmd_flush = 0, cmd_save = 0, cmd_restore = 0; reg [KW-1:0] key = 0; reg [VW-1:0] wdata = 0;
    wire busy, done, found, ready, sd_error; wire [VW-1:0] rdata; wire [32*27-1:0] cnts;
    wire O_clk, O_cke, O_cs, O_ras, O_cas, O_wen; wire [31:0] dq; wire [10:0] O_a; wire [1:0] O_ba; wire [3:0] O_dqm; wire sclk, mosi, miso, scs;
    wire r_valid, r_we, r_ready, r_rv, r_init, ddr_ready; wire [20:0] r_addr; wire [31:0] r_wdata, r_rd; wire [31:0] nrd, nwr, ntmo, nnoack;
    wire wb_stb, wb_we, wb_stall, wb_ack; wire [24:0] wb_addr; wire [575:0] wb_data, wb_rdata;
    hexn_tier_v6 #(.KW(KW), .VW(VW), .FB(FB), .RAMB(RAMB), .LB(LB), .LOW(LOW), .VOL(1), .SD_BASE(0), .INIT_DIV(2), .FAST_DIV(1), .EXT_RAM(1)) dut (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(3'd3),
        .cmd_valid(cmd_valid), .cmd_we(cmd_we), .cmd_flush(cmd_flush), .cmd_save(cmd_save), .cmd_restore(cmd_restore), .key(key), .wdata(wdata), .busy(busy), .done(done), .found(found), .rdata(rdata), .ready(ready), .cnts(cnts), .sd_error(sd_error),
        .O_sdram_clk(O_clk), .O_sdram_cke(O_cke), .O_sdram_cs_n(O_cs), .O_sdram_ras_n(O_ras), .O_sdram_cas_n(O_cas), .O_sdram_wen_n(O_wen), .IO_sdram_dq(dq), .O_sdram_addr(O_a), .O_sdram_ba(O_ba), .O_sdram_dqm(O_dqm),
        .sd_clk(sclk), .sd_mosi(mosi), .sd_miso(miso), .sd_cs_n(scs),
        .ram_valid(r_valid), .ram_we(r_we), .ram_addr(r_addr), .ram_wdata(r_wdata), .ram_ready(r_ready), .ram_rv(r_rv), .ram_rd(r_rd), .ram_init(r_init));
    hexn_ddr3_port_v1 port (.clk(clk), .resetn(resetn), .cmd_valid(r_valid), .cmd_we(r_we), .cmd_addr(r_addr), .cmd_wdata(r_wdata), .cmd_wmask(4'b1111), .cmd_ready(r_ready), .rd_valid(r_rv), .rd_data(r_rd), .init_done(r_init), .ddr_ready(ddr_ready),
        .wb_stb(wb_stb), .wb_we(wb_we), .wb_addr(wb_addr), .wb_data(wb_data), .wb_stall(wb_stall), .wb_ack(wb_ack), .wb_rdata(wb_rdata), .n_rd(nrd), .n_wr(nwr), .n_timeout(ntmo), .n_noack(nnoack));
    wb_ddr_model_v1 #(.LINES((((1 << (RAMB + 1)) + (1 << KW)) >> 4) + 8), .LAT(LAT), .JIT(JIT), .STALLP(STALLP)) ddr (.clk(clk), .resetn(1'b1), .o_ready(ddr_ready), .i_stb(wb_stb), .i_we(wb_we), .i_addr(wb_addr), .i_data(wb_data), .i_sel({72{1'b1}}), .o_stall(wb_stall), .o_ack(wb_ack), .o_data(wb_rdata));
    sd_card_model_v1 #(.SDHC(1), .BLOCKS(1 << LB), .READY_AFTER(3)) card (.sclk(sclk), .mosi(mosi), .cs_n(scs), .miso(miso));
    function [31:0] hash32(input [31:0] x);
        reg [31:0] m; begin m = x * 32'h9E3779B1; m = m ^ (m >> 15); m = m * 32'h85EBCA6B; hash32 = m ^ (m >> 13); end
    endfunction
    localparam [31:0] MK = (32'd1 << KW) - 1, MV = (64'd1 << VW) - 1;
    reg [VW-1:0] ev [0:NK-1]; reg ek [0:NK-1]; integer bad = 0, lost = 0, lf1 = 0, n, ki, i, j, b; reg [31:0] r; reg [KW-1:0] kk;
    task op(input fl, input sv, input rs, input we, input [KW-1:0] k, input [VW-1:0] d);
        begin
            @(posedge clk); cmd_valid <= 1; cmd_flush <= fl; cmd_save <= sv; cmd_restore <= rs; cmd_we <= we; key <= k; wdata <= d;
            @(posedge clk); cmd_valid <= 0;
            @(posedge clk); while (!done) @(posedge clk);
        end
    endtask
    task show(input [8*10-1:0] tag);
        integer q;
        begin
            $write("%0s", tag);
            for (q = 0; q < 27; q = q + 1) $write(" %0d", cnts[32*q +: 32]);
            $write("\n");
        end
    endtask
    task dump(input [8*5-1:0] tag);
        begin
            for (b = 0; b < (1 << LB); b = b + 1) begin
                $write("%0s %0d ", tag, b);
                for (j = 0; j < 512; j = j + 1) $write("%02x", card.mem[b * 512 + j]);
                $write("\n");
            end
        end
    endtask
    initial begin
        for (i = 0; i < NK; i = i + 1) ek[i] = 0;
        for (i = 0; i < (1 << LB) * 512; i = i + 1) card.mem[i] = 8'h00;
        #200; resetn = 1; wait (ready);
        for (n = 0; n < STEPS; n = n + 1) begin
            r = hash32(n + 32'h1111); ki = (r >> 4) % NK; kk = ((ki + 1) * 32'h2545F491) & MK;
            if (((r >> 20) % 10) < 4) begin ev[ki] = hash32(n + 32'h5151) & MV; ek[ki] = 1; op(0, 0, 0, 1, kk, ev[ki]); end
            else begin
                op(0, 0, 0, 0, kk, 0);
                if (found) begin if (!ek[ki] || rdata !== ev[ki]) begin bad = bad + 1; if (bad < 10) $display("step %0d key %0d: found %b got %h want %h known %b", n, ki, found, rdata, ev[ki], ek[ki]); end end
            end
        end
        if (MODE == 0) op(1, 0, 0, 0, 0, 0); else if (MODE == 1) op(0, 1, 0, 0, 0, 0);
        if (CORRUPT >= 0) card.mem[CORRUPT * 512 + 100] = card.mem[CORRUPT * 512 + 100] ^ 8'hFF;   // a torn or damaged block
        lf1 = cnts[32*14 +: 32];   // entries dropped because the log was full (the counters are wiped by the reset)
        show("COUNTERS1"); dump("BLK1");
        if (MODE >= 1) begin
            resetn = 0;   // the FPGA side loses everything; the DDR memory and the card keep their contents
            repeat (6) @(posedge clk); resetn = 1; @(posedge clk); wait (ready);
            op(0, 0, 1, 0, 0, 0); show("COUNTERS2");
            for (i = 0; i < NK; i = i + 1) begin
                kk = ((i + 1) * 32'h2545F491) & MK; op(0, 0, 0, 0, kk, 0);
                $display("R %0d %0d %0d", i, found, found ? rdata : 0);
                if (MODE == 1 && found && (!ek[i] || rdata !== ev[i])) begin bad = bad + 1; if (bad < 10) $display("restore: key %0d got %h want %h known %b", i, rdata, ev[i], ek[i]); end
                if (MODE == 1 && !found && ek[i]) lost = lost + 1;
            end
            show("COUNTERS3"); dump("BLK2");
        end
        $display("adapter timeouts %0d no-acks %0d, data errors %0d, known keys not found after restore %0d (log_full before the power loss %0d), card error %b", ntmo, nnoack, bad, lost, lf1, sd_error);
        if (bad == 0 && ntmo == 0 && nnoack == 0 && !sd_error && (MODE != 1 || lost <= lf1)) $display("TIER6 TEST PASS"); else $display("TIER6 TEST FAIL");
        $finish;
    end
    initial begin #20000000000; $display("TIER6 TEST FAIL: timeout"); $finish; end
endmodule
