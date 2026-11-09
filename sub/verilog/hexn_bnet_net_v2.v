`default_nettype none
`timescale 1ns / 1ps
// hexn_bnet_net_v2 (9 Nov 2026, clone of v1 with a PIPELINE REGISTER after every serialiser): the MERGED bus network: three layers of G buses of PER cells, external input lines, a source serialiser per source group, a merger per target bus, optional feedback from layer 3 to layer 1 (FB=1). Direction doc section 44.
// Host ports: table row write (layer, bus, row, PER nibbles), threshold write, fire-counter clear and read. Outputs: the fire vector of every layer each clock (the 'map' the judge can record), merge/drop counters.
// Row addresses: layer 1 bus: rows 0..NIN-1 input lines, rows NIN.. layer 3 cell numbers (FB); layer 2 bus: row = layer 1 cell number; layer 3 bus: row = layer 2 cell number. Cell number = group*PER + index.
// v2: the serialiser output (valid, index) is registered before it enters the merger, so each hop takes one clock more than v1 (Python: tools/hexn_busnet_hw_v2.py HWNetP). v1 text follows. This is the SINGLE-CLOCK-PER-HOP functional netlist (v1): input line -> serialiser -> sub-queue -> arbiter -> table -> cell happens inside one clock (long combinational path; no timing was run and it will need pipelining, which adds clocks of delay per hop).
module hexn_bnet_net_v2 #(parameter G = 4, parameter PER = 16, parameter NIN = 48, parameter FB = 1, parameter SQL = 3, parameter REFR = 3, parameter TH0 = 4) (
    input wire clk, input wire tick, input wire [NIN-1:0] ev,
    input wire wr_en, input wire [1:0] wr_layer, input wire [$clog2(G)-1:0] wr_bus, input wire [$clog2(NIN + G*PER)-1:0] wr_addr, input wire [PER*4-1:0] wr_data,
    input wire thw_en, input wire [1:0] thw_layer, input wire [$clog2(G)-1:0] thw_bus, input wire [$clog2(PER)-1:0] thw_idx, input wire [3:0] thw_val,
    input wire rclr, input wire [1:0] rate_layer, input wire [$clog2(G)-1:0] rate_bus, input wire [$clog2(PER)-1:0] rate_idx, output wire [7:0] rate_q,
    output wire [G*PER-1:0] fire1, output wire [G*PER-1:0] fire2, output wire [G*PER-1:0] fire3,
    output wire [16*(1+6*G)-1:0] lostv, input wire [$clog2(1+6*G)-1:0] lost_sel, output wire [15:0] lost_q);
    localparam IDW = $clog2(NIN + G*PER); localparam IW = $clog2(PER); localparam ROWS1 = NIN + (FB ? G*PER : 0); localparam ROWS2 = G*PER;
    localparam NS1 = 1 + (FB ? G : 0);
    // serialisers: input lines, then one per group of each layer
    wire in_vc; wire [$clog2(NIN)-1:0] in_ic; reg in_v = 1'b0; reg [$clog2(NIN)-1:0] in_i = 0; wire [15:0] in_m;
    hexn_bnet_ser_v2 #(.N(NIN), .IW($clog2(NIN)), .BYP(1)) sin (.clk(clk), .ev(ev), .o_v(in_vc), .o_i(in_ic), .merged(in_m));
    wire [G-1:0] s1vc, s2vc, s3vc; wire [G*IW-1:0] s1ic, s2ic, s3ic; reg [G-1:0] s1v = 0, s2v = 0, s3v = 0; reg [G*IW-1:0] s1i = 0, s2i = 0, s3i = 0;
    always @(posedge clk) begin in_v <= in_vc; in_i <= in_ic; s1v <= s1vc; s2v <= s2vc; s3v <= s3vc; s1i <= s1ic; s2i <= s2ic; s3i <= s3ic; end wire [16*G-1:0] m1, m2, m3;
    genvar g, b;
    generate for (g = 0; g < G; g = g + 1) begin : ser
        hexn_bnet_ser_v2 #(.N(PER), .IW(IW), .BYP(0)) a1 (.clk(clk), .ev(fire1[g*PER +: PER]), .o_v(s1vc[g]), .o_i(s1ic[g*IW +: IW]), .merged(m1[16*g +: 16]));
        hexn_bnet_ser_v2 #(.N(PER), .IW(IW), .BYP(0)) a2 (.clk(clk), .ev(fire2[g*PER +: PER]), .o_v(s2vc[g]), .o_i(s2ic[g*IW +: IW]), .merged(m2[16*g +: 16]));
        hexn_bnet_ser_v2 #(.N(PER), .IW(IW), .BYP(0)) a3 (.clk(clk), .ev(fire3[g*PER +: PER]), .o_v(s3vc[g]), .o_i(s3ic[g*IW +: IW]), .merged(m3[16*g +: 16]));
    end endgenerate
    wire [7:0] rq1 [0:G-1]; wire [7:0] rq2 [0:G-1]; wire [7:0] rq3 [0:G-1]; wire [15:0] d1 [0:G-1]; wire [15:0] d2 [0:G-1]; wire [15:0] d3 [0:G-1];
    generate for (b = 0; b < G; b = b + 1) begin : tb
        wire e1 = wr_en && wr_layer == 2'd0 && wr_bus == b, e2 = wr_en && wr_layer == 2'd1 && wr_bus == b, e3 = wr_en && wr_layer == 2'd2 && wr_bus == b;
        wire t1 = thw_en && thw_layer == 2'd0 && thw_bus == b, t2 = thw_en && thw_layer == 2'd1 && thw_bus == b, t3 = thw_en && thw_layer == 2'd2 && thw_bus == b;
        wire [NS1-1:0] v1; wire [NS1*IDW-1:0] r1;
        assign v1[0] = in_v; assign r1[0 +: IDW] = in_i;
        if (FB) begin : fbw
            for (g = 0; g < G; g = g + 1) begin : f
                assign v1[1+g] = s3v[g]; assign r1[(1+g)*IDW +: IDW] = NIN + g*PER + s3i[g*IW +: IW];
            end
        end
        hexn_bnet_tbus_v2 #(.PER(PER), .ROWS(ROWS1), .IDW(IDW), .NS(NS1), .SQL(SQL), .REFR(REFR), .TH0(TH0)) l1 (.clk(clk), .tick(tick), .sv(v1), .srow(r1), .wr_en(e1), .wr_addr(wr_addr), .wr_data(wr_data),
            .thw_en(t1), .thw_idx(thw_idx), .thw_val(thw_val), .rclr(rclr), .rate_idx(rate_idx), .rate_q(rq1[b]), .fire(fire1[b*PER +: PER]), .dropped(d1[b]));
        wire [G-1:0] v2 = s1v; wire [G*IDW-1:0] r2; wire [G-1:0] v3 = s2v; wire [G*IDW-1:0] r3;
        for (g = 0; g < G; g = g + 1) begin : rr
            assign r2[g*IDW +: IDW] = g*PER + s1i[g*IW +: IW]; assign r3[g*IDW +: IDW] = g*PER + s2i[g*IW +: IW];
        end
        hexn_bnet_tbus_v2 #(.PER(PER), .ROWS(ROWS2), .IDW(IDW), .NS(G), .SQL(SQL), .REFR(REFR), .TH0(TH0)) l2 (.clk(clk), .tick(tick), .sv(v2), .srow(r2), .wr_en(e2), .wr_addr(wr_addr), .wr_data(wr_data),
            .thw_en(t2), .thw_idx(thw_idx), .thw_val(thw_val), .rclr(rclr), .rate_idx(rate_idx), .rate_q(rq2[b]), .fire(fire2[b*PER +: PER]), .dropped(d2[b]));
        hexn_bnet_tbus_v2 #(.PER(PER), .ROWS(ROWS2), .IDW(IDW), .NS(G), .SQL(SQL), .REFR(REFR), .TH0(TH0)) l3 (.clk(clk), .tick(tick), .sv(v3), .srow(r3), .wr_en(e3), .wr_addr(wr_addr), .wr_data(wr_data),
            .thw_en(t3), .thw_idx(thw_idx), .thw_val(thw_val), .rclr(rclr), .rate_idx(rate_idx), .rate_q(rq3[b]), .fire(fire3[b*PER +: PER]), .dropped(d3[b]));
    end endgenerate
    assign rate_q = (rate_layer == 2'd0) ? rq1[rate_bus] : (rate_layer == 2'd1) ? rq2[rate_bus] : rq3[rate_bus];
    // every loss counter (input merges, 3G serialiser merges, 3G sub-queue drops), 16 bits each, side by side; the host reads one at a time through lost_sel (no adder tree: a sum of this many counters was mapped to DSP blocks)
    wire [16*3*G-1:0] dv;
    generate for (b = 0; b < G; b = b + 1) begin : lv
        assign dv[16*(3*b) +: 16] = d1[b]; assign dv[16*(3*b+1) +: 16] = d2[b]; assign dv[16*(3*b+2) +: 16] = d3[b];
    end endgenerate
    assign lostv = {dv, m3, m2, m1, in_m};
    assign lost_q = lostv[16*lost_sel +: 16];
endmodule
