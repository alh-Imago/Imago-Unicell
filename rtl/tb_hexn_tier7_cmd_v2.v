`timescale 1ns/1ps
// tb_hexn_tier7_cmd_v2.v -- byte-level testbench for hexn_tier7_cmd_v2: sends the bytes of the file given by +script=<hex file> (+n=<number of bytes>) one byte every SP clocks (like the JTAG bridge would), with the transmit side busy at random, and prints every byte the layer sends as "T xx". The DDR3 side is wb_ddr_model_v1. tests/test_hexn_tier7_cmd_v2.py builds the script and compares the answers with the Python model.
module tb_hexn_tier7_cmd_v2;
    parameter KW = 12, VW = 12, FB = 4, BMB = 8, RAMB = 6, SB = 5, SP = 7, LAT = 9, JIT = 3, STALLP = 4;
    reg clk = 0, resetn = 0; always #5 clk = ~clk;
    reg [7:0] rx_d = 0; reg rx_v = 0; wire [7:0] tx_d; wire tx_s; reg tx_b = 0;
    wire wb_stb, wb_we, wb_stall, wb_ack, ddr_ready, t_ready, t_ddr_err; wire [24:0] wb_addr; wire [575:0] wb_data, wb_rdata;
    hexn_tier7_cmd_v2 #(.KW(KW), .VW(VW), .FB(FB), .BMB(BMB), .RAMB(RAMB), .SB(SB), .DDR_BASE(0)) dut (.clk(clk), .resetn(resetn), .rx_d(rx_d), .rx_v(rx_v), .tx_d(tx_d), .tx_s(tx_s), .tx_b(tx_b), .ddr_ready(ddr_ready),
        .wb_stb(wb_stb), .wb_we(wb_we), .wb_addr(wb_addr), .wb_data(wb_data), .wb_stall(wb_stall), .wb_ack(wb_ack), .wb_rdata(wb_rdata), .t_ready(t_ready), .t_ddr_err(t_ddr_err));
    wb_ddr_model_v1 #(.LINES((1 << SB) + 8), .LAT(LAT), .JIT(JIT), .STALLP(STALLP)) ddr (.clk(clk), .resetn(1'b1), .o_ready(ddr_ready), .i_stb(wb_stb), .i_we(wb_we), .i_addr(wb_addr), .i_data(wb_data), .i_sel({72{1'b1}}), .o_stall(wb_stall), .o_ack(wb_ack), .o_data(wb_rdata));
    reg [7:0] script [0:65535]; integer n, i, quiet; reg [31:0] lf = 32'hACE1;
    always @(posedge clk) begin lf <= {lf[30:0], lf[31] ^ lf[21] ^ lf[1] ^ lf[0]}; tx_b <= (lf[2:0] == 3'd0); end
    always @(posedge clk) if (tx_s) $write("T %02x\n", tx_d);
    initial begin
        if (!$value$plusargs("n=%d", n)) n = 0;
        $readmemh("script.hex", script);
        #50; resetn = 1; wait (t_ready);
        for (i = 0; i < n; i = i + 1) begin
            repeat (SP) @(posedge clk); while (!(dut.st == 0 || dut.st == 1)) @(posedge clk);   // like the host: the next command waits for the answer of the last one
            rx_d <= script[i]; rx_v <= 1; @(posedge clk); rx_v <= 0;
        end
        // wait until the layer has been quiet for a while
        quiet = 0; while (quiet < 3000) begin @(posedge clk); if (tx_s || rx_v) quiet = 0; else quiet = quiet + 1; end
        $display("END ddr_err %b", t_ddr_err); $finish;
    end
    initial begin #2000000000; $display("TIMEOUT"); $finish; end
endmodule
