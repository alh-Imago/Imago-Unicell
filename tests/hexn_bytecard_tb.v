`timescale 1ns/1ps
// Test bench for hexn_arr_core (frame v4 around a pattern), driven through its byte port like hexn_jtag_bridge_v1 would: +rx=FILE ($readmemh, one 32-bit word per byte: gap clocks in [31:8], the byte in [7:0]),
// +n=BYTES, +tail=CLOCKS to run after the last byte. tx_b is modelled as the bridge does: busy while a byte is being taken (tx_s or the cycle after). Prints "T cycle byte" for every byte the core sends.
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg [31:0] mem [0:65535]; reg [7:0] rx_d = 0; reg rx_v = 0; wire [7:0] tx_d; wire tx_s; wire [5:0] led; integer n = 0, tail = 0, i, g; integer cyc = 0; reg pend = 0; reg [1023:0] fn;
    wire tx_b = tx_s | pend; always @(posedge clk) begin pend <= tx_s; cyc <= cyc + 1; if (tx_s) $display("T %0d %0d", cyc, tx_d); end
    hexn_arr_core dut (.clk(clk), .rx_d(rx_d), .rx_v(rx_v), .tx_dout(tx_d), .tx_s(tx_s), .tx_b(tx_b), .led(led));
    initial begin
        if (!$value$plusargs("rx=%s", fn) || !$value$plusargs("n=%d", n) || !$value$plusargs("tail=%d", tail)) begin $display("FAIL args"); $finish; end
        $readmemh(fn, mem, 0, n - 1);
        for (i = 0; i < n; i = i + 1) begin
            g = mem[i][31:8]; repeat (g) @(posedge clk);
            #1 rx_d = mem[i][7:0]; rx_v = 1; @(posedge clk); #1 rx_v = 0;
        end
        repeat (tail) @(posedge clk);
        $finish;
    end
endmodule
