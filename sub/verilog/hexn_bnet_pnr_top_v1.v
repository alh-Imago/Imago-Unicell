`default_nettype none
// hexn_bnet_pnr_top_v1 (8 Nov 2026): place-and-route wrapper for hexn_bnet_net_v1 on the Tang Nano 20K. Every input of the network comes from one shift register (one pin), every output is folded into one registered bit, so the timing measured is the network's own path. Size/speed test, not a board design.
module hexn_bnet_pnr_top_v1 #(parameter G = 2, parameter PER = 8, parameter NIN = 16, parameter FB = 1, parameter SQL = 2) (input wire clk, input wire sin, output reg sout);
    localparam IDW = $clog2(NIN + G*PER); localparam WN = 1 + NIN + 1 + 2 + $clog2(G) + IDW + PER*4 + 1 + 2 + $clog2(G) + $clog2(PER) + 4 + 1 + 2 + $clog2(G) + $clog2(PER) + $clog2(1+6*G);
    reg [WN-1:0] sh; always @(posedge clk) sh <= {sh[WN-2:0], sin};
    wire tick = sh[0]; wire [NIN-1:0] ev = sh[1 +: NIN]; integer dummy;
    wire [WN-1:0] x = sh;
    localparam O1 = 1 + NIN; localparam O2 = O1 + 1 + 2 + $clog2(G) + IDW + PER*4;
    wire wr_en = x[O1]; wire [1:0] wr_layer = x[O1+1 +: 2]; wire [$clog2(G)-1:0] wr_bus = x[O1+3 +: $clog2(G)]; wire [IDW-1:0] wr_addr = x[O1+3+$clog2(G) +: IDW]; wire [PER*4-1:0] wr_data = x[O1+3+$clog2(G)+IDW +: PER*4];
    wire thw_en = x[O2]; wire [1:0] thw_layer = x[O2+1 +: 2]; wire [$clog2(G)-1:0] thw_bus = x[O2+3 +: $clog2(G)]; wire [$clog2(PER)-1:0] thw_idx = x[O2+3+$clog2(G) +: $clog2(PER)]; wire [3:0] thw_val = x[O2+3+$clog2(G)+$clog2(PER) +: 4];
    localparam O3 = O2 + 1 + 2 + $clog2(G) + $clog2(PER) + 4;
    wire rclr = x[O3]; wire [1:0] rate_layer = x[O3+1 +: 2]; wire [$clog2(G)-1:0] rate_bus = x[O3+3 +: $clog2(G)]; wire [$clog2(PER)-1:0] rate_idx = x[O3+3+$clog2(G) +: $clog2(PER)]; wire [$clog2(1+6*G)-1:0] lost_sel = x[O3+3+$clog2(G)+$clog2(PER) +: $clog2(1+6*G)];
    wire [7:0] rate_q; wire [G*PER-1:0] f1, f2, f3; wire [16*(1+6*G)-1:0] lostv; wire [15:0] lost_q;
    hexn_bnet_net_v1 #(.G(G), .PER(PER), .NIN(NIN), .FB(FB), .SQL(SQL)) n (.clk(clk), .tick(tick), .ev(ev), .wr_en(wr_en), .wr_layer(wr_layer), .wr_bus(wr_bus), .wr_addr(wr_addr), .wr_data(wr_data),
        .thw_en(thw_en), .thw_layer(thw_layer), .thw_bus(thw_bus), .thw_idx(thw_idx), .thw_val(thw_val), .rclr(rclr), .rate_layer(rate_layer), .rate_bus(rate_bus), .rate_idx(rate_idx), .rate_q(rate_q),
        .fire1(f1), .fire2(f2), .fire3(f3), .lostv(lostv), .lost_sel(lost_sel), .lost_q(lost_q));
    always @(posedge clk) sout <= ^{rate_q, f1, f2, f3, lost_q};
endmodule
