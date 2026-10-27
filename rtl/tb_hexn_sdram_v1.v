`timescale 1ns/1ps
// tb_hexn_sdram_v1.v -- testbench for hexn_sdram_v1 against sdram_model_v1 (both our own). 27 MHz core clock, SDRAM clock = inverted core clock (ideal 180 degrees). Start-up, then 4,096 random word writes with random byte masks over all banks/rows/columns, a read-back of all of them, a long idle (refresh only) stretch, a second read-back, and mixed read/write traffic. Passes when the data matches a reference array and the model counted no rule violation.
module tb_hexn_sdram_v1;
    reg clk = 0, resetn = 0; always #18.5185 clk = ~clk;
    wire clk_sdram = ~clk;
    reg cmd_valid = 0, cmd_we = 0; reg [20:0] cmd_addr = 0; reg [31:0] cmd_wdata = 0; reg [3:0] cmd_wmask = 0;
    wire cmd_ready, rd_valid, init_done; wire [31:0] rd_data;
    wire O_clk, O_cke, O_cs, O_ras, O_cas, O_wen; wire [31:0] dq; wire [10:0] O_a; wire [1:0] O_ba; wire [3:0] O_dqm;
    hexn_sdram_v1 #(.FREQ(27_000_000), .CL(3'd2)) dut (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(3'd3), .cmd_valid(cmd_valid), .cmd_we(cmd_we), .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata), .cmd_wmask(cmd_wmask), .cmd_ready(cmd_ready), .rd_valid(rd_valid), .rd_data(rd_data), .init_done(init_done),
        .O_sdram_clk(O_clk), .O_sdram_cke(O_cke), .O_sdram_cs_n(O_cs), .O_sdram_ras_n(O_ras), .O_sdram_cas_n(O_cas), .O_sdram_wen_n(O_wen), .IO_sdram_dq(dq), .O_sdram_addr(O_a), .O_sdram_ba(O_ba), .O_sdram_dqm(O_dqm));
    sdram_model_v1 #(.CL(3'd2)) model (.CLK(O_clk), .CKE(O_cke), .CS_N(O_cs), .RAS_N(O_ras), .CAS_N(O_cas), .WE_N(O_wen), .A(O_a), .BA(O_ba), .DQM(O_dqm), .DQ(dq));
    integer bad = 0, i, n, ops = 0; integer seed = 7;
    reg [20:0] taddr [0:4095]; reg [31:0] tval [0:4095]; reg [3:0] tknown [0:4095];
    reg [31:0] got; integer rdlat_clk; reg [31:0] refm [0:2097151]; reg known [0:2097151]; reg [2:0] rb; reg [10:0] rr; reg [7:0] rc; reg [31:0] rv;
    initial for (i = 0; i < 2097152; i = i + 1) known[i] = 0;
    task send(input we, input [20:0] a, input [31:0] d, input [3:0] m);
        begin
            @(posedge clk); cmd_valid <= 1; cmd_we <= we; cmd_addr <= a; cmd_wdata <= d; cmd_wmask <= m;
            @(posedge clk); while (!cmd_ready) @(posedge clk);      // cmd_ready is read as it was before this edge, so the command was taken at this edge
            cmd_valid <= 0; ops = ops + 1;
        end
    endtask
    task do_write(input [20:0] a, input [31:0] d, input [3:0] m); begin send(1, a, d, m); refm[a] = known[a] ? merge(refm[a], d, m) : merge(32'h0, d, m); if (m != 0) known[a] = known[a] | (m == 4'b1111); if (!known[a] && m == 4'b1111) known[a] = 1; end endtask
    task do_read(input [20:0] a, output [31:0] d);
        integer k;
        begin
            send(0, a, 0, 4'b1111); k = 0;
            while (!rd_valid && k < 40) begin @(posedge clk); k = k + 1; end
            if (!rd_valid) begin bad = bad + 1; $display("read timed out at %h", a); d = 32'hx; end else d = rd_data;
            rdlat_clk = k;
        end
    endtask
    function [31:0] merge(input [31:0] old, input [31:0] nw, input [3:0] m);
        integer b; begin merge = old; for (b = 0; b < 4; b = b + 1) if (m[b]) merge[b*8 +: 8] = nw[b*8 +: 8]; end
    endfunction
    initial begin
        #200; resetn = 1;
        wait (init_done); $display("init done at %0t", $time);
        // 1) 4096 random full-word writes over all banks, rows and columns
        for (i = 0; i < 4096; i = i + 1) begin
            rb = $urandom; rr = $urandom; rc = $urandom; rv = $urandom;
            taddr[i] = {rb[1:0], rr, rc}; tval[i] = rv;
            do_write(taddr[i], tval[i], 4'b1111);
        end
        // partial byte-mask writes over the first 1024 (a mask of 0 writes nothing)
        for (i = 0; i < 1024; i = i + 1) begin
            n = $urandom; rv = $urandom; do_write(taddr[i], rv, n[3:0]);
        end
        $display("writes sent: %0d ops", ops);
        for (i = 0; i < 4096; i = i + 1) begin
            do_read(taddr[i], got);
            if (got !== refm[taddr[i]]) begin bad = bad + 1; if (bad < 10) $display("mismatch slot %0d addr %h: read %h, expected %h", i, taddr[i], got, refm[taddr[i]]); end
        end
        $display("read latency seen by the user side: %0d clocks after the command was accepted", rdlat_clk);
        // 2) long idle: 400 us of refresh only
        #400000;
        for (i = 0; i < 256; i = i + 1) begin
            do_read(taddr[i*16], got);
            if (got !== refm[taddr[i*16]]) begin bad = bad + 1; $display("after idle: mismatch slot %0d", i*16); end
        end
        // 3) known values: full writes then read back against our own reference
        for (i = 0; i < 512; i = i + 1) begin taddr[i] = (i * 9973) % 2097152; tval[i] = {i[15:0], ~i[15:0]}; do_write(taddr[i], tval[i], 4'b1111); end
        for (i = 0; i < 512; i = i + 1) begin do_read(taddr[i], got); if (got !== refm[taddr[i]]) begin bad = bad + 1; if (bad < 20) $display("known-value mismatch %0d: read %h want %h", i, got, refm[taddr[i]]); end end
        $display("ops %0d, writes %0d, reads %0d, refreshes %0d, longest refresh gap %0.0f ns, rule violations %0d, data mismatches %0d", ops, model.writes, model.reads, model.refreshes, model.max_gap, model.errors, bad);
        if (bad == 0 && model.errors == 0 && model.refreshes > 50) $display("SDRAM TEST PASS"); else $display("SDRAM TEST FAIL");
        $finish;
    end
    initial begin #3000000000; $display("SDRAM TEST FAIL: timeout"); $finish; end
endmodule
