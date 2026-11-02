`timescale 1ns/1ps
// testbench for hexn_seq_core_v1: advance pulses at scripted clocks; the words taken at rs must be the stored values in order, wrapping at len.
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg cfgload = 0; reg [127:0] vals = 0; reg [2:0] len = 0; reg adv = 0; wire r, rs;
    hexn_seq_core_v1 dut (.clk(clk), .cfgload(cfgload), .vals(vals), .len(len), .adv(adv), .r(r), .rs(rs));
    integer errs = 0, n, k, np, nout, ncl, nex; integer pt [0:7]; integer plen [0:7]; integer clt = -1;
    reg [31:0] outw [0:15]; reg [31:0] exw [0:15]; reg [31:0] cur; integer cl;
    task run(input integer nn); begin
        nout = 0; cl = -1; cur = 0;
        for (n = 0; n < nn; n = n + 1) begin
            @(negedge clk); adv = 0; cfgload = (n == clt);
            for (k = 0; k < np; k = k + 1) if (n >= pt[k] && n < pt[k] + plen[k]) adv = 1;
            #4;
            if (rs) begin cl = 0; cur = 0; end
            if (cl >= 0 && cl < 32) begin cur[cl] = r; cl = cl + 1; if (cl == 32) begin outw[nout] = cur; nout = nout + 1; end end
        end
        cfgload = 0; adv = 0; clt = -1; repeat (4) @(negedge clk);
    end endtask
    task check(input [255:0] name); integer i; reg ok; begin
        ok = (nout == nex); for (i = 0; i < nex && i < nout; i = i + 1) if (outw[i] !== exw[i]) ok = 0;
        if (ok) $display("PASS %0s", name); else begin errs = errs + 1; $display("FAIL %0s: %0d words out, want %0d; first %h want %h", name, nout, nex, outw[0], exw[0]); end
    end endtask
    task newvals; begin vals = {$random, $random, $random, $random}; cfgload = 1; @(negedge clk); cfgload = 0; @(negedge clk); end endtask
    task pulses(input integer cnt, input integer gap, input integer wd); integer q; begin np = cnt; for (q = 0; q < cnt; q = q + 1) begin pt[q] = 5 + q * gap; plen[q] = wd; end end endtask
    initial begin
        repeat (3) @(negedge clk);
        newvals; len = 3; pulses(5, 60, 1); run(5 * 60 + 60); nex = 5; exw[0] = vals[31:0]; exw[1] = vals[63:32]; exw[2] = vals[95:64]; exw[3] = vals[31:0]; exw[4] = vals[63:32]; check("len 3 wraps");
        newvals; len = 1; pulses(3, 50, 1); run(220); nex = 3; exw[0] = vals[31:0]; exw[1] = vals[31:0]; exw[2] = vals[31:0]; check("len 1 repeats");
        newvals; len = 4; pulses(6, 50, 1); run(380); nex = 6; exw[0] = vals[31:0]; exw[1] = vals[63:32]; exw[2] = vals[95:64]; exw[3] = vals[127:96]; exw[4] = vals[31:0]; exw[5] = vals[63:32]; check("len 4 wraps");
        newvals; len = 4; pulses(3, 50, 1); clt = 95; run(220); nex = 3; exw[0] = vals[31:0]; exw[1] = vals[63:32]; exw[2] = vals[31:0]; check("cfgload returns to value 0");
        newvals; len = 4; np = 3; pt[0] = 5; plen[0] = 1; pt[1] = 15; plen[1] = 1; pt[2] = 100; plen[2] = 1; run(200); nex = 2; exw[0] = vals[31:0]; exw[1] = vals[63:32]; check("advance during a send is ignored");
        newvals; len = 4; np = 1; pt[0] = 5; plen[0] = 120; run(220); nex = 1; exw[0] = vals[31:0]; check("a held advance level sends once");
        newvals; len = 0; pulses(3, 50, 1); run(200); nex = 0; exw[0] = 0; check("len 0 sends nothing");
        if (errs == 0) $display("ALL PASS"); else $display("SOME FAILED %0d", errs);
        $finish;
    end
endmodule
