// Testbench for rtl/hexn_jtag_bridge_v1.v: an interactive JTAG frame executor. Reads commands on stdin, writes answers on stdout (tools/hexn_jtag_host_v1.py drives it through pipes):
//   S <40 hex digits>  one 160-bit scan (capture, 160 shifts, update); answer "D <40 hex digits>" (the captured value)
//   T <n>              idle for n clock cycles (50 MHz)     Q   finish
// The clock (20 ns) and TCK (100 ns, shifted 7 ns) are unrelated. +flip=<per mille>: with this chance per scan one random bit of the value sent and one of the value captured are flipped (tests the CRC and the resend).
// Cores behind the bridge: default = a small EMULATED core (every byte received comes back +1; byte 0xFF makes it send 60 bytes, to test backpressure); -DREALCORE = hexn_core_v1 (needs the lattice defines).
`timescale 1ns/1ps
module tb_hexn_jtag_v1;
    reg clk = 0; always #10 clk = ~clk;
    reg rst = 1; initial begin #200 rst = 0; end
    wire [7:0] rx_d; wire rx_v; wire [7:0] tx_d; wire tx_s; wire tx_b;
    hexn_jtag_bridge_v1 #(.FSPACING(`FSP)) dut (.clk(clk), .rst(rst), .rx_d(rx_d), .rx_v(rx_v), .tx_d(tx_d), .tx_s(tx_s), .tx_b(tx_b));
`ifdef REALCORE
    wire [5:0] led;
    hexn_core_v1 core (.clk(clk), .rx_d(rx_d), .rx_v(rx_v), .tx_d(tx_d), .tx_s(tx_s), .tx_b(tx_b), .led(led));
`else
    reg [7:0] eq [0:255]; reg [7:0] eh = 0, et = 0; reg [7:0] dly = 0; reg [7:0] txd_r = 0; reg txs_r = 0; reg [7:0] burst = 0;
    assign tx_d = txd_r; assign tx_s = txs_r;
    always @(posedge clk) begin
        txs_r <= 1'b0;
        if (rx_v) begin if (rx_d == 8'hFF) burst <= 60; else begin eq[et] <= rx_d + 1'b1; et <= et + 1'b1; end end
        if (!tx_b && !txs_r && dly == 0) begin
            if (burst != 0) begin txd_r <= burst; txs_r <= 1'b1; burst <= burst - 1'b1; dly <= 3; end
            else if (eh != et) begin txd_r <= eq[eh]; txs_r <= 1'b1; eh <= eh + 1'b1; dly <= 3; end
        end else if (dly != 0) dly <= dly - 1'b1;
    end
`endif
    integer r, i, n, flip; reg [8*2-1:0] cmd; reg [159:0] val, got; integer seed;
    task tck; begin #50 dut.bscan.r_drck = 1; #50 dut.bscan.r_drck = 0; end endtask
    task scan(input [159:0] din, output [159:0] dout);
        reg [159:0] d; begin
        d = din; if (flip > 0 && ($urandom % 1000) < flip) d[$urandom % 160] = ~d[$urandom % 160];
        dut.bscan.r_sel = 1; dut.bscan.r_capture = 1; dut.bscan.r_shift = 0; tck;
        dut.bscan.r_capture = 0; dut.bscan.r_shift = 1;
        for (i = 0; i < 160; i = i + 1) begin dut.bscan.r_tdi = d[i]; dout[i] = dut.sr[0]; tck; end
        dut.bscan.r_shift = 0; dut.bscan.r_tdi = 0; #100 dut.bscan.r_update = 1; #100 dut.bscan.r_update = 0; #300;
        if (flip > 0 && ($urandom % 1000) < flip) dout[$urandom % 160] = ~dout[$urandom % 160];
        end
    endtask
    initial begin
        if (!$value$plusargs("flip=%d", flip)) flip = 0;
        #7; wait (!rst); #100;
        forever begin
            r = $fscanf(32'h8000_0000, "%s", cmd);
            if (r != 1) $finish;
            if (cmd[7:0] == "S") begin r = $fscanf(32'h8000_0000, "%h", val); scan(val, got); $display("D %h", got); $fflush; end
            else if (cmd[7:0] == "T") begin r = $fscanf(32'h8000_0000, "%d", n); repeat (n) @(posedge clk); $display("T"); $fflush; end
            else $finish;
        end
    end
endmodule
