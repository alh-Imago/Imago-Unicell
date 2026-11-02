`default_nettype none
// hexn_prio_core_v1 -- serial PRIORITY core (2 Nov 2026, Alan 09:46), after priority_cell_v4sa: up to four inputs (faces 0 n, 1 s, 2 e, 3 w), one output, one word at a time. Each input has a one-word FIFO cell (hexn_ramfifo_v8).
//   A face is a CANDIDATE when its FIFO holds a word and its bit in `mask` is set (an unmasked face does not store). Exactly one candidate is released at a time; the others wait.
//   mode 0 STRICT    lowest rank wins (score 3 - rank), ties N > S > E > W.
//   mode 1 WEIGHTED  surplus round robin: every candidate's credit gains its weight (= its rank field) each round; highest credit wins; only the winner's credit is reduced, by the total weight of the candidates that round (floor 0).
//   mode 2 SEQUENCED a fixed cyclic turn order (len turns, each a face code); only the face whose turn it is is a candidate (the others wait however long); the turn advances when that word is taken, and wraps. len = 0 takes nothing.
//   cfgload (pulse) clears credits and the turn position. The selection logic is the arbitration of priority_cell_v4sa.v ported unchanged (same names, same order of tests); only the handshake is replaced by the FIFO cells.
//   Same limit as the merge: a new word on a face whose cell still holds one is lost. rs marks bit 0 of each output word.
module hexn_prio_core_v1 #(parameter BUG = 0) (input wire clk, input wire cfgload, input wire [3:0] mask, input wire [7:0] ranks, input wire [1:0] mode, input wire [2:0] len, input wire [7:0] order,
    input wire dn, input wire wsn, input wire ds, input wire wss, input wire de, input wire wse, input wire dw, input wire wsw, output reg r, output reg rs);
    wire [3:0] q, qs, h;
    reg busy = 1'b0, started = 1'b0; reg [1:0] selr = 2'd0; reg [2:0] sidx = 3'd0;
    reg [7:0] cr0 = 8'd0, cr1 = 8'd0, cr2 = 8'd0, cr3 = 8'd0;
    wire [1:0] rk0 = ranks[1:0], rk1 = ranks[3:2], rk2 = ranks[5:4], rk3 = ranks[7:6];
    wire sequenced = (mode == 2'd2), weighted = (mode == 2'd1);
    wire [1:0] due = order[{sidx[1:0], 1'b0} +: 2];
    wire due_ok = sequenced && (len != 3'd0);
    wire seq_cap = sequenced && !due_ok;
    wire c0 = h[0] & (mask[0] | BUG == 2) & (!sequenced | (due_ok & due == 2'd0));
    wire c1 = h[1] & (mask[1] | BUG == 2) & (!sequenced | (due_ok & due == 2'd1));
    wire c2 = h[2] & (mask[2] | BUG == 2) & (!sequenced | (due_ok & due == 2'd2));
    wire c3 = h[3] & (mask[3] | BUG == 2) & (!sequenced | (due_ok & due == 2'd3));
    wire [7:0] i0 = c0 ? cr0 + {6'd0, rk0} : cr0, i1 = c1 ? cr1 + {6'd0, rk1} : cr1, i2 = c2 ? cr2 + {6'd0, rk2} : cr2, i3 = c3 ? cr3 + {6'd0, rk3} : cr3;
    wire [7:0] tw = (c0 ? {6'd0, rk0} : 8'd0) + (c1 ? {6'd0, rk1} : 8'd0) + (c2 ? {6'd0, rk2} : 8'd0) + (c3 ? {6'd0, rk3} : 8'd0);
    wire [7:0] s0 = weighted ? i0 : {6'd0, (BUG == 1 ? rk0 : 2'd3 - rk0)}, s1 = weighted ? i1 : {6'd0, (BUG == 1 ? rk1 : 2'd3 - rk1)};
    wire [7:0] s2 = weighted ? i2 : {6'd0, (BUG == 1 ? rk2 : 2'd3 - rk2)}, s3 = weighted ? i3 : {6'd0, (BUG == 1 ? rk3 : 2'd3 - rk3)};
    wire w0 = c0 && (!c1 || (BUG == 5 ? s0 > s1 : s0 >= s1)) && (!c2 || s0 >= s2) && (!c3 || s0 >= s3);
    wire w1 = c1 && !w0 && (!c2 || s1 >= s2) && (!c3 || s1 >= s3);
    wire w2 = c2 && !w0 && !w1 && (!c3 || s2 >= s3);
    wire w3 = c3 && !w0 && !w1 && !w2;
    wire go = !busy && !seq_cap && (w0 | w1 | w2 | w3);
    wire [3:0] rel = {go & w3, go & w2, go & w1, go & w0};
    wire [1:0] wface = w0 ? 2'd0 : w1 ? 2'd1 : w2 ? 2'd2 : 2'd3;
    hexn_ramfifo_v8 f0 (.clk(clk), .din(dn), .wstart(wsn & (mask[0] | BUG == 2)), .rel(rel[0]), .keep(1'b0), .q(q[0]), .qs(qs[0]), .have(h[0]));
    hexn_ramfifo_v8 f1 (.clk(clk), .din(ds), .wstart(wss & (mask[1] | BUG == 2)), .rel(rel[1]), .keep(1'b0), .q(q[1]), .qs(qs[1]), .have(h[1]));
    hexn_ramfifo_v8 f2 (.clk(clk), .din(de), .wstart(wse & (mask[2] | BUG == 2)), .rel(rel[2]), .keep(1'b0), .q(q[2]), .qs(qs[2]), .have(h[2]));
    hexn_ramfifo_v8 f3 (.clk(clk), .din(dw), .wstart(wsw & (mask[3] | BUG == 2)), .rel(rel[3]), .keep(1'b0), .q(q[3]), .qs(qs[3]), .have(h[3]));
    always @(posedge clk) begin
        if (cfgload) begin cr0 <= 8'd0; cr1 <= 8'd0; cr2 <= 8'd0; cr3 <= 8'd0; sidx <= 3'd0; busy <= 1'b0; started <= 1'b0; end
        else begin
            if (go) begin
                busy <= 1'b1; selr <= wface; started <= 1'b0;
                if (sequenced && BUG != 3) sidx <= (sidx + 3'd1 >= len) ? 3'd0 : sidx + 3'd1;
                if (weighted) begin
                    cr0 <= (w0 && BUG != 4) ? ((i0 > tw) ? i0 - tw : 8'd0) : i0; cr1 <= w1 ? ((i1 > tw) ? i1 - tw : 8'd0) : i1;
                    cr2 <= w2 ? ((i2 > tw) ? i2 - tw : 8'd0) : i2; cr3 <= w3 ? ((i3 > tw) ? i3 - tw : 8'd0) : i3;
                end
            end
            if (busy && (|qs)) started <= 1'b1;
            if (busy && started && !h[selr]) busy <= 1'b0;
        end
        r <= |q; rs <= |qs;
    end
    initial begin r = 1'b0; rs = 1'b0; end
endmodule
