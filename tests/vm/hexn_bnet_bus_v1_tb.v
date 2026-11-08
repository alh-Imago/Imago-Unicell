`timescale 1ns / 1ps
// testbench of hexn_bnet_bus_v1 against the Python model (tests/vm/test_hexn_bnet_bus_v1.py writes tab.hex, th.hex, inp.hex into the working directory)
module tb;
    localparam PER = 16, NSRC = 48, IDW = 6, QL = 3, NCLK = 160, LE = 4;
    reg clk = 0; reg tick = 0; reg push_v = 0; reg [IDW-1:0] push_id = 0; reg wr_en = 0; reg [IDW-1:0] wr_addr = 0; reg [PER*4-1:0] wr_data = 0;
    reg thw_en = 0; reg [3:0] thw_idx = 0; reg [3:0] thw_val = 0; wire [7:0] rate_q; wire [PER-1:0] fire; wire [15:0] dropped;
    reg [PER*4-1:0] tabm [0:NSRC-1]; reg [3:0] thm [0:PER-1]; reg [6:0] inpm [0:NCLK-1];
    hexn_bnet_bus_v1 #(.PER(PER), .NSRC(NSRC), .IDW(IDW), .QL(QL), .REFR(3), .SYNC(0)) dut (.clk(clk), .tick(tick), .push_v(push_v), .push_id(push_id), .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data),
        .thw_en(thw_en), .thw_idx(thw_idx), .thw_val(thw_val), .rclr(1'b0), .rate_idx(4'd0), .rate_q(rate_q), .fire(fire), .dropped(dropped));
    integer i, t;
    always #5 clk = ~clk;
    initial begin
        $readmemh("tab.hex", tabm); $readmemh("th.hex", thm); $readmemh("inp.hex", inpm);
        @(negedge clk);
        for (i = 0; i < NSRC; i = i + 1) begin wr_en = 1; wr_addr = i; wr_data = tabm[i]; @(negedge clk); end
        wr_en = 0;
        for (i = 0; i < PER; i = i + 1) begin thw_en = 1; thw_idx = i; thw_val = thm[i]; @(negedge clk); end
        thw_en = 0;
        for (t = 0; t < NCLK; t = t + 1) begin
            tick = ((t % LE) == 0); push_v = inpm[t][6]; push_id = inpm[t][5:0];
            #1 $display("F %0d %h", t, fire);
            @(negedge clk);
        end
        $display("D %0d", dropped); $finish;
    end
endmodule
