// tb_hexn_tier7_jtag_v1.v -- frame executor of tb_hexn_jtag_v2.v (same stdin/stdout protocol, tools/hexn_jtag_host_v1.py SimExec) with the Kintex tier behind the bridge: hexn_jtag_bridge_v1 -> hexn_tier7_cmd_v1 (hexn_tier_v8) -> wb_ddr_model_v1. tests/test_hexn_tier7_jtag_v1.py drives it with tools/hexn_tier7_host_v1.py.
`timescale 1ns/1ps
module tb_hexn_jtag_v1;
    parameter KW = 12, VW = 12, FB = 4, BMB = 8, RAMB = 6, SB = 5;
    reg clk = 0; always #10 clk = ~clk;
    reg rst = 1; initial begin #200 rst = 0; end
    wire [7:0] rx_d; wire rx_v; wire [7:0] tx_d; wire tx_s; wire tx_b;
    hexn_jtag_bridge_v1 #(.FSPACING(`FSP)) dut (.clk(clk), .rst(rst), .rx_d(rx_d), .rx_v(rx_v), .tx_d(tx_d), .tx_s(tx_s), .tx_b(tx_b));
    wire wb_stb, wb_we, wb_stall, wb_ack, ddr_ready, t_ready, t_ddr_err; wire [24:0] wb_addr; wire [575:0] wb_data, wb_rdata;
    hexn_tier7_cmd_v1 #(.KW(KW), .VW(VW), .FB(FB), .BMB(BMB), .RAMB(RAMB), .SB(SB), .DDR_BASE(0)) tcmd (.clk(clk), .resetn(~rst), .rx_d(rx_d), .rx_v(rx_v), .tx_d(tx_d), .tx_s(tx_s), .tx_b(tx_b), .ddr_ready(ddr_ready),
        .wb_stb(wb_stb), .wb_we(wb_we), .wb_addr(wb_addr), .wb_data(wb_data), .wb_stall(wb_stall), .wb_ack(wb_ack), .wb_rdata(wb_rdata), .t_ready(t_ready), .t_ddr_err(t_ddr_err));
    wb_ddr_model_v1 #(.LINES((1 << SB) + 8), .LAT(9), .JIT(3), .STALLP(4)) ddr (.clk(clk), .resetn(1'b1), .o_ready(ddr_ready), .i_stb(wb_stb), .i_we(wb_we), .i_addr(wb_addr), .i_data(wb_data), .i_sel({72{1'b1}}), .o_stall(wb_stall), .o_ack(wb_ack), .o_data(wb_rdata));
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
