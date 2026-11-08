`default_nettype none
`timescale 1ns / 1ps
// hexn_bnet_bus_v1 (8 Nov 2026): ONE shared bus of the bus network toy (direction doc sections 31 to 43) as synthesisable logic: a queue of source ids (depth 2**QL; a full queue drops the packet and counts it), a weight table (one row per source id, PER nibbles per row = the weight of each cell on this bus for that source, 0 = no connection), and PER leaky accumulating cells.
// Per clock: one packet is taken from the queue (or straight from push_* when the queue is empty, like the Python model); the table row for that id is read; each cell adds its signed 4-bit weight unless it is in its refractory period; if 'tick' (the shared leak clock) and the sum is above 0 it loses 1; at or above its own threshold the cell fires (fire[i] this clock), resets, and rests REFR clocks. Each cell has an 8-bit fire counter for the host (the rate the self-adjusting threshold needs).
// SYNC=0: asynchronous table read (exactly the Python model, used for the cross-check test). SYNC=1: registered table read (lets the table map onto block RAM), one extra clock of delay per bus.
// Differences from the Python model (stated, not hidden): the accumulator saturates at -32..31 (the model is unbounded); ONE push per clock per bus (the model accepts several: the merger in front of a bus is NOT in this module); thresholds 0..15.
module hexn_bnet_bus_v1 #(parameter PER = 16, parameter NSRC = 64, parameter IDW = 6, parameter QL = 3, parameter REFR = 3, parameter SYNC = 0, parameter TH0 = 4) (
    input wire clk, input wire tick,
    input wire push_v, input wire [IDW-1:0] push_id,
    input wire wr_en, input wire [IDW-1:0] wr_addr, input wire [PER*4-1:0] wr_data,
    input wire thw_en, input wire [$clog2(PER)-1:0] thw_idx, input wire [3:0] thw_val,
    input wire rclr, input wire [$clog2(PER)-1:0] rate_idx, output wire [7:0] rate_q,
    output wire [PER-1:0] fire, output reg [15:0] dropped);
    localparam QD = 1 << QL;
    reg [IDW-1:0] qmem [0:QD-1]; reg [QL-1:0] wp = 0, rp = 0; reg [QL:0] cnt = 0; initial dropped = 0;
    wire empty = (cnt == 0);
    wire have = ~empty | push_v;
    wire [IDW-1:0] sid = empty ? push_id : qmem[rp];
    wire do_push = push_v & ~empty & (cnt < QD);
    wire do_pop = ~empty;
    always @(posedge clk) begin
        if (do_push) begin qmem[wp] <= push_id; wp <= wp + 1'b1; end
        if (do_pop) rp <= rp + 1'b1;
        cnt <= cnt + do_push - do_pop;
        if (push_v & ~empty & (cnt >= QD)) dropped <= dropped + 1'b1;
    end
    reg [PER*4-1:0] tab [0:NSRC-1];
    always @(posedge clk) if (wr_en) tab[wr_addr] <= wr_data;
    reg [PER*4-1:0] rd_s = 0; reg v_s = 0;
    always @(posedge clk) begin rd_s <= tab[sid]; v_s <= have; end
    wire [PER*4-1:0] wrow = SYNC ? rd_s : tab[sid];
    wire wv = SYNC ? v_s : have;
    wire [PER*8-1:0] rcs;
    genvar i;
    generate for (i = 0; i < PER; i = i + 1) begin : c
        reg signed [5:0] acc = 0; reg [3:0] th = TH0; reg [3:0] rl = 0; reg [7:0] rc = 0;
        wire signed [3:0] w = wv ? wrow[4*i +: 4] : 4'sd0;
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
