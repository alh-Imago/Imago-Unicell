`timescale 1ns / 1ps
module tbm;
    localparam NB = 32, M = 8, MW = 3;
    reg clk = 0, clr = 0, w_en = 0, start = 0; reg [NB-1:0] fire = 0, w_map = 0; reg [MW-1:0] w_idx = 0;
    wire done; wire [MW-1:0] b1, b2; wire [7:0] i1, u1, i2, u2; wire [NB-1:0] live;
    reg [NB-1:0] mp [0:M-1]; reg [NB-1:0] fv [0:3]; integer i, j;
    hexn_bnet_map_v1 #(.NB(NB), .M(M), .MW(MW)) dut (.clk(clk), .clr(clr), .fire(fire), .w_en(w_en), .w_idx(w_idx), .w_map(w_map), .start(start), .done(done), .b1(b1), .b2(b2), .i1(i1), .u1(u1), .i2(i2), .u2(u2), .live_o(live));
    always #5 clk = ~clk;
    initial begin
        $readmemh("maps.hex", mp); $readmemh("fire.hex", fv);
        @(negedge clk); for (i = 0; i < M; i = i + 1) begin w_en = 1; w_idx = i; w_map = mp[i]; @(negedge clk); end
        w_en = 0; clr = 1; @(negedge clk); clr = 0;
        for (j = 0; j < 4; j = j + 1) begin fire = fv[j]; @(negedge clk); end
        fire = 0; start = 1; @(negedge clk); start = 0;
        while (!done) @(negedge clk);
        $display("R %0d %0d %0d %0d %0d %0d %h", b1, b2, i1, u1, i2, u2, live); $finish;
    end
endmodule
