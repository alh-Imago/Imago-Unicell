`default_nettype none
// hexn_merge_core_v1 -- serial MERGE core (2 Nov 2026, Alan 09:39), after the UniCell merge cell: two inputs A and B, one output, mode 0 = A only, 1 = B only, 2 = arbitrate (round robin, one word at a time),
// 3 = join-OR (A | B when both are there). Each input has a one-word FIFO cell (hexn_ramfifo_v8, from hexn_join_core_v2.v), so a word that arrives while the other is being sent waits its turn.
//   In modes 0 and 1 the other input is not stored (its words are dropped). A new word that arrives on an input whose cell still holds one is LOST (the cell takes one word): the same open
//   point as the RAM cell's pulse during a read. rs marks bit 0 of every output word. Function-tested by tests/hexn_merge_core_v1_tb.v.
module hexn_merge_core_v1 (input wire clk, input wire [1:0] mode, input wire a, input wire wsa, input wire b, input wire wsb, output reg r, output reg rs);
    wire qa, qsa, ha, qb, qsb, hb;
    reg busy = 1'b0, selb = 1'b0, lastb = 1'b1, bq = 1'b0; reg pa = 1'b0, pb = 1'b0;
    wire wa_en = (mode != 2'd1), wb_en = (mode != 2'd0);
    wire both = ha & hb;
    wire j3 = (mode == 2'd3);
    wire j3p = both & ~bq & ~busy;                                  // join-OR: release both together
    wire cho_b = (mode == 2'd1) ? 1'b1 : (mode == 2'd0) ? 1'b0 : (ha & hb) ? ~lastb : hb;      // which input goes next
    wire go = !busy && !j3 && (ha | hb) && (mode == 2'd2 ? 1'b1 : (mode == 2'd0 ? ha : hb));
    wire go_a = go & ~cho_b, go_b = go & cho_b;
    hexn_ramfifo_v8 fa (.clk(clk), .din(a), .wstart(wsa & wa_en), .rel(go_a | (j3 & j3p)), .keep(1'b0), .q(qa), .qs(qsa), .have(ha));
    hexn_ramfifo_v8 fb (.clk(clk), .din(b), .wstart(wsb & wb_en), .rel(go_b | (j3 & j3p)), .keep(1'b0), .q(qb), .qs(qsb), .have(hb));
    reg started = 1'b0;
    always @(posedge clk) begin
        bq <= both;
        if (go) begin busy <= 1'b1; selb <= cho_b; lastb <= cho_b; started <= 1'b0; end
        if (j3p) begin busy <= 1'b1; started <= 1'b0; end
        // the word is on its way; the cell(s) empty when the read ends
        if (busy && (qsa | qsb)) started <= 1'b1;
        if (busy && started && (j3 ? (!ha && !hb) : (selb ? !hb : !ha))) busy <= 1'b0;
        r <= qa | qb; rs <= qsa | qsb;
    end
    initial begin r = 1'b0; rs = 1'b0; end
endmodule
