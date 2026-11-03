`default_nettype none
// hexn_branch_core_v2 = hexn_branch_core_v1 (untouched) (3 Nov 2026, Alan 09:50 'the general wipe command'): adds a CLEAR input - while clear is 1 every state register goes to its idle value (FIFO 'have' flags, counters, carries, state machine, outputs). The configuration is not touched. Uses hexn_ramfifo_v9 (in hexn_join_core_v3.v).
// hexn_branch_core_v2 -- serial BRANCH core (2 Nov 2026, Alan 09:39), after the UniCell branch cell (branch_cell_v4sa: 3-way signed compare, per-outcome routing to out1 / out2 / both / neither,
// emit source fixed / in1 / in2 / diff). Two one-word FIFO cells (hexn_ramfifo_v9, defined in hexn_join_core_v2.v) hold the words, the AND of their 'have' flags starts it:
//   pass 1 reads both words (kept in the cells) while a serial compare runs: unsigned a < b and a == b (LSB first), plus both sign bits at bit 31, so the signed result is
//   lt = (sa != sb) ? sa : ltu.   Outcome (lt / eq / gt) picks the 2-bit route mask (bit 0 = out1, bit 1 = out2, 00 = neither).
//   pass 2 replays the words and puts the emit word on the chosen output(s): emit 0 = fixed 32-bit value, 1 = a, 2 = b, 3 = a - b. With route 00 the words are read and dropped (the cells empty again).
//   o1s / o2s mark bit 0 of the word on each output. Function-tested by tests/hexn_branch_core_v2_tb.v.
module hexn_branch_core_v2 (input wire clk, input wire clear, input wire [1:0] route_lt, input wire [1:0] route_eq, input wire [1:0] route_gt, input wire [1:0] emit, input wire [31:0] fixed,
                            input wire a, input wire wsa, input wire b, input wire wsb, output reg o1, output reg o1s, output reg o2, output reg o2s);
    wire qa, qsa, ha, qb, qsb, hb;
    reg [1:0] st = 0; reg [5:0] cnt = 0; reg ltu = 1'b0, eq = 1'b1, bq = 1'b0, p2 = 1'b0; reg [1:0] rt = 2'b00; reg c = 1'b0;
    wire both = ha & hb;
    wire p1 = both & ~bq & (st == 0);
    wire rel = p1 | p2;
    wire keep = !p2 && (st == 0);
    hexn_ramfifo_v9 fa (.clk(clk), .clear(clear), .din(a), .wstart(wsa), .rel(rel), .keep(keep), .q(qa), .qs(qsa), .have(ha));
    hexn_ramfifo_v9 fb (.clk(clk), .clear(clear), .din(b), .wstart(wsb), .rel(rel), .keep(keep), .q(qb), .qs(qsb), .have(hb));
    wire ltn = (~qa & qb) | (~(qa ^ qb) & ltu);
    wire eqn = eq & ~(qa ^ qb);
    wire first = (st == 0 && qsa);
    wire ltn0 = (~qa & qb);                           // bit 0
    wire eqn0 = ~(qa ^ qb);
    wire [5:0] idx = (st == 2'd3) ? 6'd0 : (cnt + 6'd1);                // bit index of the bit on qa during pass 2
    wire fbit = fixed[idx[4:0]];
    wire ci = (st == 2'd3) ? 1'b1 : c;
    wire dsum = qa ^ ~qb ^ ci; wire dcar = (qa & ~qb) | (qa & ci) | (~qb & ci);
    wire ebit = (emit == 2'd0) ? fbit : (emit == 2'd1) ? qa : (emit == 2'd2) ? qb : dsum;
    always @(posedge clk) begin
        bq <= both; p2 <= 1'b0; o1s <= 1'b0; o2s <= 1'b0; o1 <= 1'b0; o2 <= 1'b0;
        if (first) begin st <= 2'd1; cnt <= 6'd1; ltu <= ltn0; eq <= eqn0; end
        else if (st == 2'd1) begin
            ltu <= ltn; eq <= eqn; cnt <= cnt + 1'b1;
            if (cnt == 6'd31) begin
                // signed: the bit on qa / qb now is bit 31 (the sign)
                begin : dec
                    reg lts, eqs;
                    lts = (qa != qb) ? qa : ltn; eqs = eqn;
                    rt <= eqs ? route_eq : lts ? route_lt : route_gt;
                end
                st <= 2'd3; p2 <= 1'b1;
            end
        end
        if (st == 2'd3 && qsa) begin st <= 2'd2; cnt <= 6'd0; c <= dcar; end
        if (st == 2'd3 && qsa || st == 2'd2) begin
            o1 <= ebit & rt[0]; o2 <= ebit & rt[1]; o1s <= (st == 2'd3) & rt[0]; o2s <= (st == 2'd3) & rt[1];
            if (st == 2'd2) begin cnt <= cnt + 1'b1; c <= dcar; if (cnt == 6'd30) st <= 2'd0; end
        end
        if (clear) begin st <= 2'd0; cnt <= 6'd0; ltu <= 1'b0; eq <= 1'b1; bq <= 1'b0; p2 <= 1'b0; rt <= 2'b00; c <= 1'b0; o1 <= 1'b0; o2 <= 1'b0; o1s <= 1'b0; o2s <= 1'b0; end
    end
    initial begin o1 = 0; o2 = 0; o1s = 0; o2s = 0; end
endmodule
