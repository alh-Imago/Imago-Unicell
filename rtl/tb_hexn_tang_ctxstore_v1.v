`timescale 1ns/1ps
// tb_hexn_tang_ctxstore_v1.v -- drives the board harness hexn_tang_ctxstore_v1 over its serial port (fast baud, small table) and checks the replies of: status, three OBS, an RD of a known and an unknown key, and two counters.
module tb_hexn_tang_ctxstore_v1;
    localparam CLKDIV = 12;
    reg clk27 = 0; always #18.5185 clk27 = ~clk27; reg rxd = 1; wire txd; wire [5:0] led;
    wire O_clk, O_cke, O_cs, O_cas, O_ras, O_wen; wire [3:0] O_dqm; wire [10:0] O_a; wire [1:0] O_ba; wire [31:0] dq;
    hexn_tang_ctxstore_v1 #(.BB(8), .CB(4), .CLKDIV(CLKDIV)) dut (.clk27(clk27), .uart_rx(rxd), .uart_tx(txd), .led(led), .O_sdram_clk(O_clk), .O_sdram_cke(O_cke), .O_sdram_cs_n(O_cs), .O_sdram_cas_n(O_cas), .O_sdram_ras_n(O_ras), .O_sdram_wen_n(O_wen), .O_sdram_dqm(O_dqm), .O_sdram_addr(O_a), .O_sdram_ba(O_ba), .IO_sdram_dq(dq));
    sdram_model_v1 #(.CL(3'd2)) model (.CLK(O_clk), .CKE(O_cke), .CS_N(O_cs), .RAS_N(O_ras), .CAS_N(O_cas), .WE_N(O_wen), .A(O_a), .BA(O_ba), .DQM(O_dqm), .DQ(dq));
    real BIT = 37.037 * CLKDIV; reg [7:0] rb [0:255]; integer nrb = 0, bad = 0, k;
    task sbyte(input [7:0] b); integer i; begin rxd = 0; #BIT; for (i = 0; i < 8; i = i + 1) begin rxd = b[i]; #BIT; end rxd = 1; #BIT; end endtask
    reg [7:0] c;
    initial begin
        wait (txd === 1'b1);
        forever begin @(negedge txd); #(BIT * 1.5); for (k = 0; k < 8; k = k + 1) begin c[k] = txd; #BIT; end rb[nrb] = c; nrb = nrb + 1; end
    end
    task expect_n(input integer n); integer t; begin t = 0; while (nrb < n && t < 4000000) begin #1000; t = t + 1; end if (nrb < n) begin bad = bad + 1; $display("timeout waiting for %0d reply bytes (have %0d)", n, nrb); end end endtask
    integer base;
    initial begin
        #1000; wait (dut.cs_rdy === 1'b1); #10000;
        base = nrb; sbyte("I"); expect_n(base + 2); if (rb[base] !== "i" || rb[base+1] !== 8'h01) begin bad = bad + 1; $display("status reply %h %h", rb[base], rb[base+1]); end
        base = nrb; sbyte("W"); sbyte(8'h39); sbyte(8'h30); sbyte(8'h00); sbyte(8'h00); sbyte(8'd5); expect_n(base + 1); if (rb[base] !== "k") begin bad = bad + 1; $display("W reply %h", rb[base]); end
        base = nrb; sbyte("W"); sbyte(8'h39); sbyte(8'h30); sbyte(8'h00); sbyte(8'h00); sbyte(8'd5); expect_n(base + 1);
        base = nrb; sbyte("W"); sbyte(8'h39); sbyte(8'h30); sbyte(8'h00); sbyte(8'h00); sbyte(8'd9); expect_n(base + 1);
        base = nrb; sbyte("R"); sbyte(8'h39); sbyte(8'h30); sbyte(8'h00); sbyte(8'h00); expect_n(base + 30);
        if (rb[base] !== "r" || rb[base+1] !== 8'd1 || rb[base+2] !== 8'd2 || rb[base+3] !== 8'd5 || rb[base+4] !== 8'd1 || rb[base+5] !== 8'd9) begin bad = bad + 1; $display("R reply %h %h w=%h f=%h w=%h f=%h", rb[base], rb[base+1], rb[base+2], rb[base+3], rb[base+4], rb[base+5]); end
        base = nrb; sbyte("R"); sbyte(8'h01); sbyte(8'h00); sbyte(8'h00); sbyte(8'h00); expect_n(base + 30);
        if (rb[base] !== "r" || rb[base+1] !== 8'd0) begin bad = bad + 1; $display("unknown-key reply %h %h", rb[base], rb[base+1]); end
        base = nrb; sbyte("S"); sbyte(8'd6); expect_n(base + 5); if (rb[base] !== "s" || rb[base+1] !== 8'd1 || rb[base+2] !== 0) begin bad = bad + 1; $display("created counter reply %h %h", rb[base], rb[base+1]); end
        base = nrb; sbyte("S"); sbyte(8'd0); expect_n(base + 5); if (rb[base] !== "s" || rb[base+1] !== 8'd5) begin bad = bad + 1; $display("ops counter reply %h %h", rb[base], rb[base+1]); end
        $write("nrb=%0d:", nrb); for (k = 0; k < nrb; k = k + 1) $write(" %h", rb[k]); $write("\n");
        if (bad == 0) $display("CTXSTORE BOARD HARNESS PASS"); else $display("CTXSTORE BOARD HARNESS FAIL");
        $finish;
    end
    initial begin #3000000000; $display("CTXSTORE BOARD HARNESS FAIL: total timeout, %0d bytes", nrb); $finish; end
endmodule
