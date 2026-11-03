`default_nettype none
// hexn_join_core_v3 (and hexn_ramfifo_v9) = hexn_join_core_v2 (untouched) (3 Nov 2026, Alan 09:50 'the general wipe command'): adds a CLEAR input - while clear is 1 every state register goes to its idle value (FIFO 'have' flags, counters, carries, state machine, outputs). The configuration is not touched. 
// hexn_join_core_v3 -- the two-input serial work core with JOIN, now with the compare family (2 Nov 2026, Alan 09:35 'yes, and keep an eye on the ones not yet covered').
//   Two one-word FIFO cells (a, b) + the AND of their 'have' flags release both (as hexn_join_cell_v1). Ops (op input):
//   0 add  1 sub  2 and  3 or  4 xor   : serial, result starts 4 clocks after the later operand's start (as v1).
//   5 lt   : unsigned a < b as a 0/1 word (bit 0 = flag, 31 zeros). One pass: both words are read once while a serial compare runs (LSB first: lt <= (~a & b) | (~(a ^ b) & lt)).
//   6 min  7 max : two passes. Pass 1 reads both words and KEEPS them in the FIFOs (the cells' replay mode) while the compare runs; the second release replays them and the core passes the chosen one.
//   rs marks bit 0 of every result word. Function-tested by tests/hexn_join_core_v3_tb.v.
module hexn_ramfifo_v9 (input wire clk, input wire clear, input wire din, input wire wstart, input wire rel, input wire keep, output reg q, output reg qs, output reg have);
    reg mem [0:31]; reg wq = 1'b0, rq = 1'b0, wr_run = 1'b0, rd_run = 1'b0, keep_q = 1'b0; reg [4:0] wa = 0, ra = 0;
    wire we = wstart & ~wq; wire re = rel & ~rq;
    always @(posedge clk) begin
        wq <= wstart; rq <= rel;
        if (we && !have) begin have <= 1'b1; wr_run <= 1'b1; wa <= 5'd1; mem[5'd0] <= din; end
        else if (wr_run) begin mem[wa] <= din; wa <= wa + 1'b1; if (wa == 5'd31) wr_run <= 1'b0; end
        qs <= 1'b0;
        if (re && have && !rd_run) begin rd_run <= 1'b1; ra <= 5'd0; keep_q <= keep; end
        if (rd_run) begin q <= mem[ra]; qs <= (ra == 5'd0); ra <= ra + 1'b1; if (ra == 5'd31) begin rd_run <= 1'b0; if (!keep_q) have <= 1'b0; end end
        else q <= 1'b0;
        if (clear) begin wq <= 1'b0; rq <= 1'b0; wr_run <= 1'b0; rd_run <= 1'b0; keep_q <= 1'b0; have <= 1'b0; q <= 1'b0; qs <= 1'b0; end
    end
    initial begin have = 1'b0; q = 1'b0; qs = 1'b0; end
endmodule

module hexn_join_core_v3 #(parameter OR_BUG = 0) (input wire clk, input wire clear, input wire [2:0] op, input wire a, input wire wsa, input wire b, input wire wsb, output reg r, output reg rs);
    wire qa, qsa, ha, qb, qsb, hb;
    reg [1:0] st = 0;                 // 0 idle/serial, 1 pass 1 of min/max/lt, 2 pass 2 of min/max
    reg [5:0] cnt = 0; reg lt = 1'b0; reg bq = 1'b0; reg p2 = 1'b0; reg [5:0] ec = 6'd63; reg ltf = 1'b0;
    wire both = OR_BUG ? (ha | hb) : (ha & hb);
    wire cmpop = (op >= 3'd5);
    wire p1 = both & ~bq & (st == 0);
    wire rel = p1 | p2;
    wire keep = (op == 3'd6 || op == 3'd7) && !p2 && (st == 0);
    hexn_ramfifo_v9 fa (.clk(clk), .clear(clear), .din(a), .wstart(wsa), .rel(rel), .keep(keep), .q(qa), .qs(qsa), .have(ha));
    hexn_ramfifo_v9 fb (.clk(clk), .clear(clear), .din(b), .wstart(wsb), .rel(rel), .keep(keep), .q(qb), .qs(qsb), .have(hb));
    reg c = 1'b0; wire ci = qsa ? (op == 3'd1) : c; wire bb = (op == 3'd1) ? ~qb : qb;
    wire ltn = (~qa & qb) | (~(qa ^ qb) & lt);        // running compare, valid after each bit
    wire lt_first = (~qa & qb);
    wire [5:0] cc = qsa ? 6'd0 : cnt;                 // bit index of the bit on qa this clock
    always @(posedge clk) begin
        bq <= both; p2 <= 1'b0; rs <= 1'b0;
        if (!cmpop) begin
            c <= (qa & bb) | (qa & ci) | (bb & ci);
            case (op) 3'd0, 3'd1: r <= qa ^ bb ^ ci; 3'd2: r <= qa & qb; 3'd3: r <= qa | qb; default: r <= qa ^ qb; endcase
            rs <= qsa;
        end else begin
            // compare running over the read of pass 1 (st 0 -> 1 at qsa) and, for min/max, pass 2 passes the chosen word
            if (st == 0 && qsa) begin st <= 2'd1; cnt <= 6'd1; lt <= lt_first; end
            else if (st == 1) begin
                lt <= ltn; cnt <= cnt + 1'b1;
                if (cnt == 6'd31) begin
                    if (op == 3'd5) begin st <= 2'd0; ec <= 6'd0; ltf <= ltn; end        // lt: emit the flag word
                    else begin st <= 2'd3; p2 <= 1'b1; ltf <= ltn; end                // min / max: second release
                end
            end
            // pass 2 of min / max: st 3 waits for the replay to start, then passes the selected word
            if (st == 2'd3 && qsa) begin st <= 2'd2; cnt <= 6'd0; end
            if (st == 2'd3 && qsa || st == 2'd2) begin
                // min: a if a < b else b ; max: b if a < b else a
                r <= ((op == 3'd6) ? ltf : ~ltf) ? qa : qb; rs <= (st == 2'd3); 
                if (st == 2'd2) begin cnt <= cnt + 1'b1; if (cnt == 6'd30) st <= 2'd0; end
            end
            // lt result word
            if (op == 3'd5 && ec < 6'd32) begin r <= (ec == 6'd0) ? ltf : 1'b0; rs <= (ec == 6'd0); ec <= ec + 1'b1; end
        end
        if (clear) begin st <= 2'd0; cnt <= 6'd0; lt <= 1'b0; bq <= 1'b0; p2 <= 1'b0; ec <= 6'd63; ltf <= 1'b0; c <= 1'b0; r <= 1'b0; rs <= 1'b0; end
    end
    initial begin r = 1'b0; rs = 1'b0; end
endmodule
