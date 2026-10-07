// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design -- see LICENSE-HARDWARE and NOTICE
//
// tb_priority_cell_v4sa.v -- self-checking bench for priority_cell_v4sa.v (the flex PRIORITY core, ledger #1017). Per-case PASS/FAIL, ends with ALL PASS.
// Run:  iverilog -g2012 -o /tmp/tb_p.vvp tb_priority_cell_v4sa.v priority_cell_v4sa.v && vvp /tmp/tb_p.vvp
// Covers: unarmed silence; STRICT priority (lowest rank wins, N > S > E > W on ties, only the winner is acknowledged, the losers wait and are served in order); the upstream mask; a lone
// candidate; backpressure (a pending result blocks every input); full-width data; WEIGHTED (surplus round robin) proportions 3:1, 2:2:1 and equal weights; reconfiguration clearing credits
// and a pending result; freeze. SEQUENCED channel (#1018): only the due face is taken, early arrivals wait, repeated faces in the order, empty order never captures, a masked-off due
// face blocks, reconfiguration restarts at turn 0, freeze does not advance the turn.
`timescale 1ns/1ps
module tb_priority_cell_v4sa;
    reg clk = 0, rst = 1, freeze_in = 0, cfg_valid = 0, ack_in = 0;
    reg [31:0] cfg_data = 0, dn = 0, ds = 0, de = 0, dw = 0;
    reg vn = 0, vs = 0, ve = 0, vw = 0;
    wire an, as_, ae, aw, vo;
    wire [31:0] d;
    wire xn = vn & an, xs = vs & as_, xe = ve & ae, xw = vw & aw;     // a TRANSFER is valid & ready
    always #5 clk = ~clk;

    priority_cell_v4sa dut (.clk(clk), .rst(rst), .freeze_in(freeze_in), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
                            .in_n(dn), .valid_in_n(vn), .ack_out_n(an), .in_s(ds), .valid_in_s(vs), .ack_out_s(as_),
                            .in_e(de), .valid_in_e(ve), .ack_out_e(ae), .in_w(dw), .valid_in_w(vw), .ack_out_w(aw),
                            .data_out(d), .valid_out(vo), .ack_in(ack_in));

    integer errors = 0, k;
    reg [3:0] xf;
    reg [1023:0] seq;
    task check_cond(input cond, input [1023:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask
    task step;  begin @(posedge clk); #1; end endtask
    // cfg: mask, ranks (n,s,e,w), mode
    task do_cfg(input [3:0] mask, input [1:0] rn, input [1:0] rs, input [1:0] re, input [1:0] rw, input mode);
        begin cfg_data = {19'b0, mode, rw, re, rs, rn, mask}; cfg_valid = 1; step; cfg_valid = 0; end
    endtask
    // sequenced: mask, turn order (len 0..4, t0..t3 face codes)
    task do_cfg_seq(input [3:0] mask, input [2:0] len, input [1:0] t0, input [1:0] t1, input [1:0] t2, input [1:0] t3);
        begin cfg_data = {7'b0, t3, t2, t1, t0, len, 1'b1, 1'b0, 8'b0, mask}; cfg_valid = 1; step; cfg_valid = 0; end
    endtask
    task drain; begin ack_in = 1; step; ack_in = 0; end endtask
    // one round: sample which face is granted just before the edge, then take the edge
    task round(output [3:0] f); begin #1; f = {xw, xe, xs, xn}; step; check_cond(d === (f[0] ? dn : f[1] ? ds : f[2] ? de : dw), "the granted face's word is captured"); end endtask
    // one served item: grant, then the source that was taken stops offering, then the result is drained
    task serve(output [3:0] f);
        begin
            round(f);
            vn = vn & ~f[0]; vs = vs & ~f[1]; ve = ve & ~f[2]; vw = vw & ~f[3];
            drain;
        end
    endtask
    // a source that always has another item: the granted face is only counted
    task serve_always(output [3:0] f); begin round(f); drain; end endtask
    function [7:0] ch(input [3:0] f); begin ch = f[0] ? "n" : f[1] ? "s" : f[2] ? "e" : f[3] ? "w" : "-"; end endfunction

    initial begin
        rst = 1; step; step; rst = 0; step;
        dn = 32'h11111111; ds = 32'h22222222; de = 32'h33333333; dw = 32'h44444444;

        // ---- unarmed ----
        vn = 1; vs = 1; ve = 1; vw = 1; #1;
        check_cond(an === 1'b0 && as_ === 1'b0 && ae === 1'b0 && aw === 1'b0, "unarmed: no input is ready");
        step; check_cond(vo === 1'b0, "unarmed: nothing is captured");
        vn = 0; vs = 0; ve = 0; vw = 0;

        // ---- strict: lowest rank wins; ranks n=2 s=1 e=0 w=3 ----
        do_cfg(4'hF, 2'd2, 2'd1, 2'd0, 2'd3, 1'b0);
        vn = 1; vs = 1; ve = 1; vw = 1; #1;
        check_cond({xn, xs, xe, xw} === 4'b0010, "strict: ONLY the lowest rank (east, 0) is acknowledged");
        round(xf);
        check_cond(vo === 1'b1 && d === 32'h33333333, "strict: east's word is captured");
        ve = 0; #1;
        check_cond(an === 1'b0 && as_ === 1'b0 && aw === 1'b0, "pending: no input is ready while the result waits");
        step; check_cond(vo === 1'b1 && d === 32'h33333333, "backpressure: the result is held until acked");
        drain; check_cond(vo === 1'b0, "ack_in releases the result");
        // the losers waited and are served in rank order: s (1), n (2), w (3)
        serve(xf); check_cond(xf === 4'b0010, "losers: south (rank 1) is served next"); // (xf bit1 = s)
        serve(xf); check_cond(xf === 4'b0001, "losers: north (rank 2) is served next");
        serve(xf); check_cond(xf === 4'b1000, "losers: west (rank 3) is served last");
        step; check_cond(vo === 1'b0, "nothing offered: nothing captured");

        // ---- strict ties: all ranks equal -> N > S > E > W ----
        do_cfg(4'hF, 2'd1, 2'd1, 2'd1, 2'd1, 1'b0);
        vn = 1; vs = 1; ve = 1; vw = 1;
        serve(xf); check_cond(xf === 4'b0001, "tie: north first");
        serve(xf); check_cond(xf === 4'b0010, "tie: then south");
        serve(xf); check_cond(xf === 4'b0100, "tie: then east");
        serve(xf); check_cond(xf === 4'b1000, "tie: then west");

        // ---- the upstream mask: east is masked off though it offers and has the best rank ----
        do_cfg(4'b1011, 2'd2, 2'd1, 2'd0, 2'd3, 1'b0);
        vn = 1; vs = 1; ve = 1; vw = 1; #1;
        check_cond(ae === 1'b0, "mask: a masked-off face is never ready");
        serve(xf); check_cond(xf === 4'b0010, "mask: south wins (east is masked off)");
        ve = 0; vs = 0; vn = 0; vw = 0;

        // ---- a lone candidate passes whatever its rank, full width ----
        do_cfg(4'hF, 2'd3, 2'd3, 2'd3, 2'd3, 1'b0);
        dw = 32'hDEADBEEF; vw = 1; #1;
        check_cond(aw === 1'b1 && an === 1'b0 && as_ === 1'b0 && ae === 1'b0, "lone candidate: only west is ready");
        serve(xf); check_cond(d === 32'hDEADBEEF, "lone candidate: the full 32-bit word passes");
        dw = 32'h44444444;

        // ---- weighted (surplus round robin): north weight 3, south weight 1, both always offering ----
        do_cfg(4'b0011, 2'd3, 2'd1, 2'd0, 2'd0, 1'b1);
        vn = 1; vs = 1; seq = 0;
        for (k = 0; k < 12; k = k + 1) begin serve_always(xf); seq = (seq << 8) | ch(xf); end
        check_cond(seq[95:0] === "nnnsnnnsnnns", "weighted 3:1: n n n s n n n s n n n s");
        vn = 0; vs = 0; drain;

        // ---- weighted 2:2:1 over n, s, e ----
        do_cfg(4'b0111, 2'd2, 2'd2, 2'd1, 2'd0, 1'b1);
        vn = 1; vs = 1; ve = 1; seq = 0;
        for (k = 0; k < 12; k = k + 1) begin serve_always(xf); seq = (seq << 8) | ch(xf); end
        check_cond(seq[95:0] === "nsnsensnsens", "weighted 2:2:1: n s n s e n s n s e n s");
        vn = 0; vs = 0; ve = 0;

        // ---- weighted, equal weights: round robin over all four ----
        do_cfg(4'hF, 2'd1, 2'd1, 2'd1, 2'd1, 1'b1);
        vn = 1; vs = 1; ve = 1; vw = 1; seq = 0;
        for (k = 0; k < 8; k = k + 1) begin serve_always(xf); seq = (seq << 8) | ch(xf); end
        check_cond(seq[63:0] === "nsewnsew", "weighted 1:1:1:1: n s e w n s e w");
        vn = 0; vs = 0; ve = 0; vw = 0;

        // ---- reconfiguration clears the credits and a pending result ----
        do_cfg(4'b0011, 2'd3, 2'd1, 2'd0, 2'd0, 1'b1);
        vn = 1; vs = 1;
        serve_always(xf); serve_always(xf);                          // credits are now non-zero
        round(xf);                                                   // a third item is captured and left pending
        check_cond(vo === 1'b1, "reconfig: a result is pending");
        do_cfg(4'b0011, 2'd3, 2'd1, 2'd0, 2'd0, 1'b1);
        check_cond(vo === 1'b0, "reconfig: the pending result is discarded");
        seq = 0;
        for (k = 0; k < 4; k = k + 1) begin serve_always(xf); seq = (seq << 8) | ch(xf); end
        check_cond(seq[31:0] === "nnns", "reconfig: credits restart from zero (n n n s again)");
        vn = 0; vs = 0;

        // ---- freeze: nothing is captured, nothing is ready ----
        do_cfg(4'hF, 2'd0, 2'd1, 2'd2, 2'd3, 1'b0);
        vn = 1; freeze_in = 1; #1;
        check_cond(an === 1'b0, "freeze: not ready");
        step; step; check_cond(vo === 1'b0, "freeze: nothing captured");
        freeze_in = 0; #1;
        check_cond(an === 1'b1, "freeze released: ready again");
        serve(xf); check_cond(d === 32'h11111111, "after freeze the item is taken");


        // ---- SEQUENCED channel (mode 2): order N, E, N, E ... all four faces offering; only the due face is acknowledged ----
        do_cfg_seq(4'hF, 3'd2, 2'd0, 2'd2, 2'd0, 2'd0);
        vn = 1; vs = 1; ve = 1; vw = 1; #1;
        check_cond({xn, xs, xe, xw} === 4'b1000, "sequenced: only the due face (north) is ready");
        seq = 0;
        for (k = 0; k < 6; k = k + 1) begin serve_always(xf); seq = (seq << 8) | ch(xf); end
        check_cond(seq[47:0] === "nenene", "sequenced 2-turn order N,E: n e n e n e (south and west never taken)");
        vn = 0; vs = 0; ve = 0; vw = 0;

        // ---- an early arrival waits, however long ----
        do_cfg_seq(4'hF, 3'd2, 2'd0, 2'd2, 2'd0, 2'd0);
        ve = 1; #1;
        check_cond(ae === 1'b0, "early arrival: east is not ready while north is due");
        step; step; step; check_cond(vo === 1'b0, "early arrival: nothing captured while it waits");
        vw = 1; #1; check_cond(aw === 1'b0, "early arrival: west is not in the order, never ready"); vw = 0;
        vn = 1; serve(xf); check_cond(xf === 4'b0001, "early arrival: north's turn is taken first");
        ve = 1; #1; check_cond(ae === 1'b1, "early arrival: east, already waiting, is taken on its turn");
        serve(xf); check_cond(xf === 4'b0100 && d === 32'h33333333, "early arrival: east served second, its own word");
        ve = 0; vn = 0;

        // ---- a face may take several turns: N, N, S ----
        do_cfg_seq(4'hF, 3'd3, 2'd0, 2'd0, 2'd1, 2'd0);
        vn = 1; vs = 1; seq = 0;
        for (k = 0; k < 6; k = k + 1) begin serve_always(xf); seq = (seq << 8) | ch(xf); end
        check_cond(seq[47:0] === "nnsnns", "sequenced N,N,S: n n s n n s");
        vn = 0; vs = 0;

        // ---- four turns, all four faces, in the order W, S, E, N ----
        do_cfg_seq(4'hF, 3'd4, 2'd3, 2'd1, 2'd2, 2'd0);
        vn = 1; vs = 1; ve = 1; vw = 1; seq = 0;
        for (k = 0; k < 8; k = k + 1) begin serve_always(xf); seq = (seq << 8) | ch(xf); end
        check_cond(seq[63:0] === "wsenwsen", "sequenced W,S,E,N: w s e n w s e n");
        vn = 0; vs = 0; ve = 0; vw = 0;

        // ---- a lone turn: one face only, the others never taken ----
        do_cfg_seq(4'hF, 3'd1, 2'd1, 2'd0, 2'd0, 2'd0);
        vn = 1; vs = 1; dw = 32'hDEADBEEF; seq = 0;
        for (k = 0; k < 3; k = k + 1) begin serve_always(xf); seq = (seq << 8) | ch(xf); end
        check_cond(seq[23:0] === "sss", "sequenced single turn: s s s");
        vn = 0; vs = 0; dw = 32'h44444444;

        // ---- an empty order never captures ----
        do_cfg_seq(4'hF, 3'd0, 2'd0, 2'd0, 2'd0, 2'd0);
        vn = 1; vs = 1; ve = 1; vw = 1; #1;
        check_cond(an === 1'b0 && as_ === 1'b0 && ae === 1'b0 && aw === 1'b0, "empty order: nothing is ready");
        step; step; check_cond(vo === 1'b0, "empty order: nothing captured");
        vn = 0; vs = 0; ve = 0; vw = 0;

        // ---- the due face is masked off: the cell waits for it for ever (as the VM does) ----
        do_cfg_seq(4'b1110, 3'd2, 2'd0, 2'd2, 2'd0, 2'd0);
        vn = 1; ve = 1; vs = 1; #1;
        check_cond(an === 1'b0 && ae === 1'b0 && as_ === 1'b0, "masked due face: nothing is ready");
        step; step; check_cond(vo === 1'b0, "masked due face: nothing captured");
        vn = 0; ve = 0; vs = 0;

        // ---- reconfiguration restarts at turn 0; a pending result is discarded ----
        do_cfg_seq(4'hF, 3'd2, 2'd0, 2'd2, 2'd0, 2'd0);
        vn = 1; ve = 1;
        serve_always(xf);                                    // north taken, turn is now east
        round(xf);                                           // east taken, left pending
        do_cfg_seq(4'hF, 3'd2, 2'd0, 2'd2, 2'd0, 2'd0);
        check_cond(vo === 1'b0, "sequenced reconfig: the pending result is discarded");
        serve_always(xf); check_cond(xf === 4'b0001, "sequenced reconfig: the order restarts at turn 0 (north)");
        vn = 0; ve = 0;

        // ---- freeze: the turn does not advance, nothing is ready ----
        do_cfg_seq(4'hF, 3'd2, 2'd0, 2'd2, 2'd0, 2'd0);
        vn = 1; ve = 1; freeze_in = 1; #1;
        check_cond(an === 1'b0, "sequenced freeze: not ready");
        step; step; check_cond(vo === 1'b0, "sequenced freeze: nothing captured");
        freeze_in = 0; #1;
        serve(xf); check_cond(xf === 4'b0001, "sequenced freeze released: still turn 0 (north)");
        vn = 0; ve = 0;

        // ---- a sequenced cell carries the full 32-bit word of the due face ----
        do_cfg_seq(4'hF, 3'd1, 2'd3, 2'd0, 2'd0, 2'd0);
        dw = 32'hCAFEF00D; vw = 1; serve(xf); check_cond(d === 32'hCAFEF00D, "sequenced: the full 32-bit word passes");
        dw = 32'h44444444;

        if (errors == 0) $display("ALL PASS"); else $display("FAILED: %0d", errors);
        $finish;
    end
endmodule
