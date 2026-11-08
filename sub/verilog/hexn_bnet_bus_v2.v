`default_nettype none
`timescale 1ns / 1ps
// hexn_bnet_bus_v2 (8 Nov 2026): clone of hexn_bnet_bus_v1 (kept untouched) with the queue taken OUT, because in the merged design (hexn_bnet_net_v1) the sub-queues of the merger hold the packets and hand this bus at most one per clock. Table, cells, fire counters and the unregistered table read are as in v1 (the cross-check test of v1 applies unchanged to the cells); SYNC and the dropped counter are gone.
module hexn_bnet_bus_v2 #(parameter PER = 16, parameter ROWS = 64, parameter IDW = 6, parameter REFR = 3, parameter TH0 = 4) (
    input wire clk, input wire tick,
    input wire push_v, input wire [IDW-1:0] push_id,
    input wire wr_en, input wire [IDW-1:0] wr_addr, input wire [PER*4-1:0] wr_data,
    input wire thw_en, input wire [$clog2(PER)-1:0] thw_idx, input wire [3:0] thw_val,
    input wire rclr, input wire [$clog2(PER)-1:0] rate_idx, output wire [7:0] rate_q,
    output wire [PER-1:0] fire);
    reg [PER*4-1:0] tab [0:ROWS-1];
    always @(posedge clk) if (wr_en) tab[wr_addr] <= wr_data;
    wire [PER*4-1:0] wrow = tab[push_id];
    wire [PER*8-1:0] rcs;
    genvar i;
    generate for (i = 0; i < PER; i = i + 1) begin : c
        reg signed [5:0] acc = 0; reg [3:0] th = TH0; reg [3:0] rl = 0; reg [7:0] rc = 0;
        wire signed [3:0] w = push_v ? wrow[4*i +: 4] : 4'sd0;
        wire signed [6:0] a0 = acc + w;
        wire signed [6:0] a1 = (tick && a0 > 0) ? a0 - 7'sd1 : a0;
        wire fr = (rl == 0) && (a1 >= $signed({3'b000, th}));
        assign fire[i] = fr;
        assign rcs[8*i +: 8] = rc;
        always @(posedge clk) begin
            if (thw_en && thw_idx == i) th <= thw_val;
            if (rclr) rc <= 8'd0; else if (fr && rc != 8'hFF) rc <= rc + 8'd1;
            if (rl != 0) rl <= rl - 4'd1;
            else if (fr) begin acc <= 6'sd0; rl <= REFR[3:0]; end
            else acc <= (a1 > 31) ? 6'sd31 : (a1 < -32) ? -6'sd32 : a1[5:0];
        end
    end endgenerate
    assign rate_q = rcs[8*rate_idx +: 8];
endmodule
