// tb_vixen_priority_seq_v1.v -- ledger #1105: the SEQUENCED CHANNEL of priority_cell_v4e (Alan's #772). Checks: a constant on one face and operands on the other come out strictly alternately
// (the constant is never taken twice in a row, the operand is waited for); an out-of-turn arrival waits however early; a repeated face in the order; an empty order never captures; live
// programming (PROG_ID 3) turns it off (strict arbitration returns) and on; reconfiguring restarts the order.
`timescale 1ns / 1ps
module tb_vixen_priority_seq_v1;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1;
    reg cfg_valid = 0; reg [63:0] cfg_data = 0;
    reg [31:0] din_n = 0, din_s = 0; reg arr_n = 0, arr_s = 0;
    wire [31:0] dout_e; wire fire_e; wire ack_n, ack_s;
    reg program_in = 0; reg [31:0] pdata = 0; reg parr = 0;
    priority_cell_v4e #(.CELL_ID(16'h0004)) DUT (
        .clk(clk), .rst(rst), .active(1'b1), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(din_n), .data_in_s(din_s), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(arr_n), .arrived_s(arr_s), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(ack_n), .ack_out_s(ack_s), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(fire_e), .ack_in_w(1'b0),
        .program_in(program_in), .program_done(),
        .prog_data_in_n(pdata), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(parr), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0), .status_data_valid(), .status_winning_dir()
    );
    integer errors = 0, checks = 0, nout = 0;
    reg [31:0] outs [0:63];
    always @(posedge clk) if (fire_e) begin outs[nout] <= dout_e; nout <= nout + 1; end
    // N: a constant offered again and again (dropped at the edge where it is acknowledged, raised the next clock)
    reg n_on = 0; reg [31:0] n_val = 0;
    always @(posedge clk) if (n_on) begin din_n <= n_val; if (arr_n && ack_n) arr_n <= 0; else if (!arr_n) arr_n <= 1; end
    // S: one operand at a time, held until acknowledged
    task offer_s(input [31:0] v);
        integer k; reg got;
        begin @(posedge clk); din_s <= v; arr_s <= 1; got = 0; k = 0;
            while (!got && k < 300) begin @(posedge clk); got = ack_s; if (got) arr_s <= 0; k = k + 1; end end
    endtask
    task settle(input integer n); begin repeat (n) @(negedge clk); end endtask
    task chk(input cond, input [255:0] what);
        begin checks = checks + 1; if (!cond) begin errors = errors + 1; $display("FAIL: %0s (t=%0t)", what, $time); end end
    endtask
    task cfgw(input [63:0] w); begin @(negedge clk); cfg_data = w; cfg_valid = 1; @(negedge clk); cfg_valid = 0; settle(3); end endtask
    task prog(input [2:0] id, input [19:0] word);
        begin
            @(negedge clk); program_in = 1; pdata = {9'h0, id, word}; parr = 1; @(negedge clk); parr = 0;
            @(negedge clk); pdata = {9'h0, 3'd7, 19'h0, 1'b1}; parr = 1; @(negedge clk); parr = 0; program_in = 0; repeat (3) @(negedge clk);
        end
    endtask
    function [63:0] mk(input seq, input [2:0] len, input [1:0] t0, t1, t2, t3);
        begin mk = 64'h0; mk[5:0] = 6'b000011; mk[11:6] = 6'b000100; mk[21] = seq; mk[24:22] = len; mk[26:25] = t0; mk[28:27] = t1; mk[30:29] = t2; mk[32:31] = t3; end
    endfunction
    integer i, base;
    initial begin
        repeat (3) @(negedge clk); rst = 0; settle(2);
        // T1: order [N, S]: K, 5, K, 6, K, 7, K -- the constant never twice in a row, the operand always waited for
        cfgw(mk(1, 3'd2, 2'd0, 2'd1, 2'd0, 2'd0));
        n_val = 32'd1000; n_on = 1; settle(40);
        chk(nout == 1 && outs[0] === 32'd1000, "sequenced [N,S]: the constant goes first, then the cell waits for S");
        for (i = 0; i < 3; i = i + 1) begin offer_s(32'd5 + i); settle(12); end
        chk(nout == 7, "sequenced [N,S]: seven words after three operands (K,5,K,6,K,7,K)");
        chk(outs[1] === 32'd5 && outs[2] === 32'd1000 && outs[3] === 32'd6 && outs[4] === 32'd1000 && outs[5] === 32'd7 && outs[6] === 32'd1000, "sequenced [N,S]: strictly alternating values");
        settle(80);
        chk(nout == 7, "sequenced [N,S]: nothing more while S is silent (K is never taken twice)");
        // T2: out-of-turn arrival waits: order [N,S] restarted, S offered FIRST, N later
        n_on = 0; arr_n = 0; settle(5); cfgw(mk(1, 3'd2, 2'd0, 2'd1, 2'd0, 2'd0));
        base = nout; din_s = 32'd9; arr_s = 1; settle(30);
        chk(nout == base && !ack_s, "S arrives before its turn: it waits, unacknowledged");
        din_n = 32'd77; arr_n = 1; settle(3);
        begin : w1 integer kk; kk = 0; while (nout < base + 2 && kk < 60) begin @(posedge clk); if (ack_n) arr_n <= 0; if (ack_s) arr_s <= 0; kk = kk + 1; end end
        settle(5); arr_n = 0; arr_s = 0; settle(5);
        chk(nout >= base + 2 && outs[base] === 32'd77 && outs[base+1] === 32'd9, "then N (its turn) first, S second");
        // T3: a repeated face: order [N,N,S]
        cfgw(mk(1, 3'd3, 2'd0, 2'd0, 2'd1, 2'd0));
        base = nout; n_val = 32'd1000; n_on = 1; settle(30);
        chk(nout == base + 2 && outs[base] === 32'd1000 && outs[base+1] === 32'd1000, "order [N,N,S]: two constants, then it waits for S");
        offer_s(32'd5); settle(30);
        chk(nout == base + 5 && outs[base+2] === 32'd5, "order [N,N,S]: the operand, then two constants again");
        // T4: an empty order never captures
        n_on = 0; arr_n = 0; settle(5); cfgw(mk(1, 3'd0, 2'd0, 2'd0, 2'd0, 2'd0));
        base = nout; din_n = 32'd1; arr_n = 1; din_s = 32'd2; arr_s = 1; settle(40);
        chk(nout == base, "sequenced with an empty order never captures"); arr_n = 0; arr_s = 0; settle(5);
        // T5: live programming (PROG_ID 3): sequenced OFF -> strict arbitration (ranks 0: N wins ties); ON again -> the order restarts at turn 0
        prog(3'd3, 20'd0);
        base = nout; din_n = 32'd11; arr_n = 1; din_s = 32'd22; arr_s = 1; settle(1);
        begin : w2 integer kk; kk = 0; while (nout < base + 1 && kk < 40) begin @(posedge clk); if (ack_n) arr_n <= 0; if (ack_s) arr_s <= 0; kk = kk + 1; end end
        settle(6);
        chk(nout >= base + 1 && outs[base] === 32'd11, "PROG_ID 3 off: strict arbitration, N wins the tie");
        arr_n = 0; arr_s = 0; settle(20);
        prog(3'd3, {8'b00_00_00_00, 4'b0, 3'd0, 1'b0} | 20'h0); // still off, harmless
        // on: {turns t3..t0 at [11:4], len [3:1], seq [0]} : order [S,N], len 2 -> t0=1 (S), t1=0 (N)
        prog(3'd3, {8'b00_00_00_01 << 4} | (20'd2 << 1) | 20'd1 | 20'h0);
        base = nout; din_n = 32'd33; arr_n = 1; settle(20);
        chk(nout == base, "PROG_ID 3 on, order [S,N]: N waits for S's turn");
        din_s = 32'd44; arr_s = 1;
        begin : w3 integer kk; kk = 0; while (nout < base + 2 && kk < 60) begin @(posedge clk); if (ack_n) arr_n <= 0; if (ack_s) arr_s <= 0; kk = kk + 1; end end
        settle(6); arr_n = 0; arr_s = 0; settle(5);
        chk(nout == base + 2 && outs[base] === 32'd44 && outs[base+1] === 32'd33, "order [S,N] by PROG_ID 3: S first, then N");
        if (errors == 0) $display("PASS: tb_vixen_priority_seq_v1 -- %0d checks", checks);
        else $display("FAIL: tb_vixen_priority_seq_v1 -- %0d of %0d checks failed", errors, checks);
        $finish;
    end
endmodule
