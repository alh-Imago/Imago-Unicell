`default_nettype none
// hexn_join_cell_v1 -- the JOIN idea of Alan (2 Nov 2026, 09:11), serial version: two one-word FIFO cells, one per operand of a work core. Each raises 'have' when its word has started to arrive;
// the AND of the two 'have' flags is the release for BOTH, so the early operand waits for the late one by itself: no alignment arithmetic, no counter, no flag pads. When a read ends a cell is empty
// again (have drops, the AND drops), ready for the next round. Same firing rule as the parallel join stage (sub/verilog/join_v1.v: fire when the second operand has arrived), done on bit streams.
// The work core here is a serial adder (carry cleared on the first bit). Function-tested by tests/hexn_join_cell_tb_v1.v. Write-start pulses (wsa, wsb) come from outside (the producers' 'high').
module hexn_ramfifo_v7 (input wire clk, input wire din, input wire wstart, input wire rel, output reg q, output reg qs, output reg have);
    reg mem [0:31]; reg wq = 1'b0, rq = 1'b0; reg wr_run = 1'b0, rd_run = 1'b0; reg [4:0] wa = 0, ra = 0;
    wire we = wstart & ~wq; wire re = rel & ~rq;
    always @(posedge clk) begin
        wq <= wstart; rq <= rel;
        if (we && !have) begin have <= 1'b1; wr_run <= 1'b1; wa <= 5'd1; mem[5'd0] <= din; end
        else if (wr_run) begin mem[wa] <= din; wa <= wa + 1'b1; if (wa == 5'd31) wr_run <= 1'b0; end
        qs <= 1'b0;
        if (re && have && !rd_run) begin rd_run <= 1'b1; ra <= 5'd0; end
        if (rd_run) begin q <= mem[ra]; qs <= (ra == 5'd0); ra <= ra + 1'b1; if (ra == 5'd31) begin rd_run <= 1'b0; have <= 1'b0; end end
        else q <= 1'b0;
    end
    initial begin have = 1'b0; q = 1'b0; qs = 1'b0; end
endmodule

module hexn_join_cell_v1 #(parameter OR_BUG = 0) (input wire clk, input wire a, input wire wsa, input wire b, input wire wsb, output reg r, output reg rs);
    wire qa, qsa, ha, qb, qsb, hb;
    wire both = OR_BUG ? (ha | hb) : (ha & hb);
    hexn_ramfifo_v7 fa (.clk(clk), .din(a), .wstart(wsa), .rel(both), .q(qa), .qs(qsa), .have(ha));
    hexn_ramfifo_v7 fb (.clk(clk), .din(b), .wstart(wsb), .rel(both), .q(qb), .qs(qsb), .have(hb));
    reg c = 1'b0; wire ci = qsa ? 1'b0 : c;
    always @(posedge clk) begin c <= (qa & qb) | (qa & ci) | (qb & ci); r <= qa ^ qb ^ ci; rs <= qsa; end
endmodule
