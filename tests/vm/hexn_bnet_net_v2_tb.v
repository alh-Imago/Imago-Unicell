`timescale 1ns / 1ps
// testbench of hexn_bnet_net_v2 against the Python merger model (tests/vm/test_hexn_bnet_net_v2.py writes tab.hex, th.hex, inp.hex)
module tbn;
    localparam G = 2, PER = 4, NIN = 8, NCLK = 240, LE = 4, ROWS1 = 16, ROWS2 = 8;
    reg clk = 0, tick = 0; reg [NIN-1:0] ev = 0; reg wr_en = 0; reg [1:0] wr_layer = 0; reg [0:0] wr_bus = 0; reg [3:0] wr_addr = 0; reg [PER*4-1:0] wr_data = 0;
    reg thw_en = 0; reg [1:0] thw_layer = 0; reg [0:0] thw_bus = 0; reg [1:0] thw_idx = 0; reg [3:0] thw_val = 0;
    wire [7:0] rate_q; wire [G*PER-1:0] f1, f2, f3; wire [16*(1+6*G)-1:0] lostv; wire [15:0] lost_q; integer ci, lsum;
    reg [PER*4-1:0] tabm [0:2*(ROWS1+ROWS2+ROWS2)-1]; reg [3:0] thm [0:3*G*PER-1]; reg [NIN-1:0] inpm [0:NCLK-1];
    hexn_bnet_net_v2 #(.G(G), .PER(PER), .NIN(NIN), .FB(1), .SQL(2), .REFR(3), .TH0(4)) dut (.clk(clk), .tick(tick), .ev(ev), .wr_en(wr_en), .wr_layer(wr_layer), .wr_bus(wr_bus), .wr_addr(wr_addr), .wr_data(wr_data),
        .thw_en(thw_en), .thw_layer(thw_layer), .thw_bus(thw_bus), .thw_idx(thw_idx), .thw_val(thw_val), .rclr(1'b0), .rate_layer(2'd0), .rate_bus(1'b0), .rate_idx(2'd0), .rate_q(rate_q),
        .fire1(f1), .fire2(f2), .fire3(f3), .lostv(lostv), .lost_sel(4'd0), .lost_q(lost_q));
    integer l, b, r, i, t, pos;
    always #5 clk = ~clk;
    initial begin
        $readmemh("tab.hex", tabm); $readmemh("th.hex", thm); $readmemh("inp.hex", inpm);
        @(negedge clk); pos = 0;
        for (l = 0; l < 3; l = l + 1) for (b = 0; b < G; b = b + 1) for (r = 0; r < (l == 0 ? ROWS1 : ROWS2); r = r + 1) begin
            wr_en = 1; wr_layer = l; wr_bus = b; wr_addr = r; wr_data = tabm[pos]; pos = pos + 1; @(negedge clk);
        end
        wr_en = 0; pos = 0;
        for (l = 0; l < 3; l = l + 1) for (b = 0; b < G; b = b + 1) for (i = 0; i < PER; i = i + 1) begin
            thw_en = 1; thw_layer = l; thw_bus = b; thw_idx = i; thw_val = thm[pos]; pos = pos + 1; @(negedge clk);
        end
        thw_en = 0;
        for (t = 0; t < NCLK; t = t + 1) begin
            tick = ((t % LE) == 0); ev = inpm[t];
            #1 $display("F %0d %h %h %h", t, f1, f2, f3);
            @(negedge clk);
        end
        for (t = 0; t < 2; t = t + 1) begin tick = 0; ev = 0; @(negedge clk); end   // two quiet clocks: the loss counters add one clock late
        lsum = 0; for (ci = 0; ci < 1 + 6*G; ci = ci + 1) lsum = lsum + lostv[16*ci +: 16];
        $display("L %0d", lsum); $finish;
    end
endmodule
