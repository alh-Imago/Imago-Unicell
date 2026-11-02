`timescale 1ns/1ps
// testbench for hexn_merge_core_v1: scripted word events on A and B for each mode; the output words (taken at rs) must come out in the expected order with the expected values.
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg [1:0] mode = 0; reg a = 0, wsa = 0, b = 0, wsb = 0; wire r, rs;
    hexn_merge_core_v1 dut (.clk(clk), .mode(mode), .a(a), .wsa(wsa), .b(b), .wsb(wsb), .r(r), .rs(rs));
    integer errs = 0, n, k, na, nb, nout, scen; integer ta [0:5]; integer tb_ [0:5]; reg [31:0] wa [0:5]; reg [31:0] wb [0:5]; reg [31:0] outw [0:11]; reg [31:0] exw [0:11]; integer nex; integer ol [0:11];
    reg [31:0] cur; integer cl;
    task fresh; integer q; begin for (q = 0; q < 6; q = q + 1) begin wa[q] = $random; wb[q] = $random; end end endtask
    task run(input integer nn); begin
        nout = 0; cl = -1; cur = 0;
        for (n = 0; n < nn; n = n + 1) begin
            @(negedge clk); a = 0; wsa = 0; b = 0; wsb = 0;
            for (k = 0; k < na; k = k + 1) if (n >= ta[k] && n < ta[k] + 32) begin a = wa[k][n - ta[k]]; wsa = (n == ta[k]); end
            for (k = 0; k < nb; k = k + 1) if (n >= tb_[k] && n < tb_[k] + 32) begin b = wb[k][n - tb_[k]]; wsb = (n == tb_[k]); end
            #4;
            if (rs) begin cl = 0; cur = 0; end
            if (cl >= 0 && cl < 32) begin cur[cl] = r; cl = cl + 1; if (cl == 32) begin outw[nout] = cur; nout = nout + 1; end end
        end
        repeat (6) @(negedge clk); a = 0; b = 0; wsa = 0; wsb = 0;
    end endtask
    task check(input [255:0] name); integer i; reg ok; begin
        ok = (nout == nex); for (i = 0; i < nex && i < nout; i = i + 1) if (outw[i] !== exw[i]) ok = 0;
        if (ok) $display("PASS %0s", name); else begin errs = errs + 1; $display("FAIL %0s: %0d words out, want %0d; first %h want %h", name, nout, nex, outw[0], exw[0]); end
    end endtask
    initial begin
        repeat (3) @(negedge clk);
        for (k = 0; k < 6; k = k + 1) begin wa[k] = $random; wb[k] = $random; end
        // mode 0: A only. A0 at 0, B0 at 5 (dropped), A1 at 120.
        mode = 0; na = 2; nb = 1; ta[0] = 0; ta[1] = 120; tb_[0] = 5; run(240); nex = 2; exw[0] = wa[0]; exw[1] = wa[1]; check("A only");
        // mode 1: B only.
        fresh; mode = 1; na = 1; nb = 2; ta[0] = 0; tb_[0] = 5; tb_[1] = 120; run(240); nex = 2; exw[0] = wb[0]; exw[1] = wb[1]; check("B only");
        // mode 2: arbitrate. tie (A0,B0 together) -> A0 then B0 (last was B); then A alone (A1) ; then tie (A2,B1) -> last = A, so B first.
        fresh; mode = 2; na = 3; nb = 2; ta[0] = 0; tb_[0] = 0; ta[1] = 100; ta[2] = 200; tb_[1] = 200;
        run(330); nex = 5; exw[0] = wa[0]; exw[1] = wb[0]; exw[2] = wa[1]; exw[3] = wb[1]; exw[4] = wa[2]; check("arbitrate: tie, single, tie (round robin)");
        // mode 2: staggered: B first alone, A arrives while B is being sent and waits.
        fresh; mode = 2; na = 1; nb = 1; ta[0] = 10; tb_[0] = 0; run(160); nex = 2; exw[0] = wb[0]; exw[1] = wa[0]; check("arbitrate: A waits behind B");
        // mode 3: join-OR, both there at different times
        fresh; mode = 3; na = 2; nb = 2; ta[0] = 0; tb_[0] = 17; ta[1] = 100; tb_[1] = 90; run(220); nex = 2; exw[0] = wa[0] | wb[0]; exw[1] = wa[1] | wb[1]; check("join-OR");
        if (errs == 0) $display("ALL PASS"); else $display("SOME FAILED %0d", errs);
        $finish;
    end
endmodule
