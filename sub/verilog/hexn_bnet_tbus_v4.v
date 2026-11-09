`default_nettype none
`timescale 1ns / 1ps
// hexn_bnet_tbus_v4 (10 Nov 2026, v4 = clone of v3 whose selection of the sent id is a per-source candidate wire plus a compare against each source number, written without the nested if per position that sent yosys's resource-sharing pass (SAT) into a very long run at 8x8; v3 text: 9 Nov 2026, v3 = clone of v2 with the arbiter's variable-position slices written as a compare against each constant position, so no multiplier is built (v2 used 52 DSP blocks in the 4x16 shape, all from jj*width on line 30). v2 text follows: clone of v1: the drop counter adds a count that passes through three registers, four clocks late): one TARGET BUS of the merged design: the merger (one small FIFO per feeding source group, a 'listens' bit per table row so packets nobody on this bus wants are not queued, and a round-robin arbiter that passes ONE packet per clock) in front of hexn_bnet_bus_v2 (weight table + cells).
// Sources: NS source groups; sv[i] says group i sends this clock, srow[i] is the table row (source id) it sends. A packet to a sub-queue that is full is dropped and counted; a packet to an empty sub-queue that the arbiter takes in the same clock goes straight through (like the Python model).
module hexn_bnet_tbus_v4 #(parameter PER = 16, parameter ROWS = 64, parameter IDW = 6, parameter NS = 4, parameter SQL = 3, parameter REFR = 3, parameter TH0 = 4) (
    input wire clk, input wire tick,
    input wire [NS-1:0] sv, input wire [NS*IDW-1:0] srow,
    input wire wr_en, input wire [IDW-1:0] wr_addr, input wire [PER*4-1:0] wr_data,
    input wire thw_en, input wire [$clog2(PER)-1:0] thw_idx, input wire [3:0] thw_val,
    input wire rclr, input wire [$clog2(PER)-1:0] rate_idx, output wire [7:0] rate_q,
    output wire [PER-1:0] fire, output reg [15:0] dropped);
    localparam QD = 1 << SQL; localparam NW = (NS > 1) ? $clog2(NS) : 1;
    reg [ROWS-1:0] lis = 0;                                   // row has at least one non-zero weight on this bus
    always @(posedge clk) if (wr_en) lis[wr_addr] <= |wr_data;
    reg [IDW-1:0] qmem [0:NS*QD-1];
    reg [NS*(SQL+1)-1:0] cntv = 0; reg [NS*SQL-1:0] wpv = 0, rpv = 0;       // flat vectors so that plain always @* sees every change
    wire [NS*IDW-1:0] headv;
    genvar gq;
    generate for (gq = 0; gq < NS; gq = gq + 1) begin : hd
        assign headv[gq*IDW +: IDW] = qmem[gq*QD + rpv[gq*SQL +: SQL]];
    end endgenerate
    wire [NS*IDW-1:0] cand;       // per source: the id the arbiter would send if it picked that source (fresh row when the sub-queue is empty, else the queue head)
    generate for (gq = 0; gq < NS; gq = gq + 1) begin : cd
        assign cand[gq*IDW +: IDW] = (cntv[gq*(SQL+1) +: SQL+1] == 0) ? srow[gq*IDW +: IDW] : headv[gq*IDW +: IDW];
    end endgenerate
    reg [15:0] dnr = 0, dnr2 = 0, dnr3 = 0; reg [NW-1:0] rr = 0; initial dropped = 0;
    reg [NS-1:0] wv, avail;
    integer i, k, jj, m; reg got; reg [NW-1:0] sel; reg [IDW-1:0] selid; reg selempty;
    always_comb begin
        for (i = 0; i < NS; i = i + 1) begin wv[i] = sv[i] & lis[srow[i*IDW +: IDW]]; avail[i] = (cntv[i*(SQL+1) +: SQL+1] != 0) | wv[i]; end
        got = 1'b0; sel = 0; selid = 0; selempty = 1'b0;
        for (k = 0; k < NS; k = k + 1) begin
            jj = rr + k; if (jj >= NS) jj = jj - NS;
            if (!got && avail[jj]) begin got = 1'b1; sel = jj[NW-1:0]; end
        end
        selid = 0; selempty = 1'b0;
        for (m = 0; m < NS; m = m + 1) if (got && sel == m) begin selempty = (cntv[m*(SQL+1) +: SQL+1] == 0); selid = selid | cand[m*IDW +: IDW]; end
    end
    hexn_bnet_bus_v2 #(.PER(PER), .ROWS(ROWS), .IDW(IDW), .REFR(REFR), .TH0(TH0)) bus (.clk(clk), .tick(tick), .push_v(got), .push_id(selid), .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data),
        .thw_en(thw_en), .thw_idx(thw_idx), .thw_val(thw_val), .rclr(rclr), .rate_idx(rate_idx), .rate_q(rate_q), .fire(fire));
    always @(posedge clk) begin : upd
        integer q, dn; reg dopop, dopush; reg [SQL:0] c;
        dn = 0;
        for (q = 0; q < NS; q = q + 1) begin
            c = cntv[q*(SQL+1) +: SQL+1];
            dopop = got && (sel == q) && (c != 0);
            dopush = wv[q] && !(got && sel == q && c == 0) && (c < QD);
            if (wv[q] && !(got && sel == q && c == 0) && (c >= QD)) dn = dn + 1;
            if (dopush) begin qmem[q*QD + wpv[q*SQL +: SQL]] <= srow[q*IDW +: IDW]; wpv[q*SQL +: SQL] <= wpv[q*SQL +: SQL] + 1'b1; end
            if (dopop) rpv[q*SQL +: SQL] <= rpv[q*SQL +: SQL] + 1'b1;
            cntv[q*(SQL+1) +: SQL+1] <= c + dopush - dopop;
        end
        dnr <= dn[15:0]; dnr2 <= dnr; dnr3 <= dnr2; dropped <= dropped + dnr3;
        if (got) rr <= (sel == NS - 1) ? 0 : sel + 1'b1;
    end
endmodule
