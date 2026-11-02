`timescale 1ns/1ps
// testbench for hexn_prio_core_v1 (and its BUG-parameter mutants): reads scenario lines from the file named by +cases=; see tests/vm/test_hexn_cores_v4.py for the Python model that writes them.
// line: mode mask ranks len order nrounds { presentmask nexp face0 idx0 face1 idx1 ... }   -- every round all present faces start their word at the same clock; the expected words come out in the listed order.
module tb;
    parameter BUG = 0;
    reg clk = 0; always #5 clk = ~clk;
    reg cfgload = 0; reg [3:0] mask = 0; reg [7:0] ranks = 0; reg [1:0] mode = 0; reg [2:0] len = 0; reg [7:0] order = 0;
    reg [3:0] dd = 0, ws = 0; wire r, rs;
    hexn_prio_core_v1 #(.BUG(BUG)) dut (.clk(clk), .cfgload(cfgload), .mask(mask), .ranks(ranks), .mode(mode), .len(len), .order(order),
        .dn(dd[0]), .wsn(ws[0]), .ds(dd[1]), .wss(ws[1]), .de(dd[2]), .wse(ws[2]), .dw(dd[3]), .wsw(ws[3]), .r(r), .rs(rs));
    integer fd, rc, ncase = 0, errs = 0, c, rd, f, i, t, nrounds, pm, nexp, nout, nex_all, cl;
    integer sent [0:3]; integer ef [0:63]; integer ei [0:63]; reg [31:0] words [0:3][0:15]; reg [31:0] outw [0:63]; reg [31:0] cur; integer m_, mk, rk, ln, od;
    reg [3:0] sentmask; integer fcnt;
    task tick(input integer nn); integer q; begin for (q = 0; q < nn; q = q + 1) begin @(negedge clk); #4; if (rs) begin cl = 0; cur = 0; end
        if (cl >= 0 && cl < 32) begin cur[cl] = r; cl = cl + 1; if (cl == 32) begin outw[nout] = cur; nout = nout + 1; end end end end endtask
    initial begin
        fd = $fopen("cases.txt", "r");
        if (fd == 0) begin $display("FAIL no cases file"); $finish; end
        repeat (3) @(negedge clk);
        while ($fscanf(fd, "%d %d %d %d %d %d", m_, mk, rk, ln, od, nrounds) == 6) begin
            ncase = ncase + 1; mode = m_; mask = mk; ranks = rk; len = ln; order = od;
            @(negedge clk); cfgload = 1; @(negedge clk); cfgload = 0; @(negedge clk);
            for (f = 0; f < 4; f = f + 1) begin sent[f] = 0; for (i = 0; i < 16; i = i + 1) words[f][i] = $random; end
            nout = 0; nex_all = 0; cl = -1; cur = 0;
            for (rd = 0; rd < nrounds; rd = rd + 1) begin
                rc = $fscanf(fd, "%d %d", pm, nexp);
                for (i = 0; i < nexp; i = i + 1) begin rc = $fscanf(fd, "%d %d", ef[nex_all], ei[nex_all]); nex_all = nex_all + 1; end
                // drive the present faces together, 32 bits
                for (t = 0; t <= 32; t = t + 1) begin
                    @(negedge clk);
                    if (t == 32) begin dd = 0; ws = 0; end
                    else for (f = 0; f < 4; f = f + 1) if (pm[f]) begin dd[f] = words[f][sent[f]][t]; ws[f] = (t == 0); end
                    #4; if (rs) begin cl = 0; cur = 0; end
                    if (cl >= 0 && cl < 32) begin cur[cl] = r; cl = cl + 1; if (cl == 32) begin outw[nout] = cur; nout = nout + 1; end end
                end
                for (f = 0; f < 4; f = f + 1) if (pm[f]) sent[f] = sent[f] + 1;
                tick(nexp * 40 + 100);
            end
            begin : chk
                reg ok; ok = (nout == nex_all);
                for (i = 0; i < nex_all && i < nout; i = i + 1) if (outw[i] !== words[ef[i]][ei[i]]) ok = 0;
                if (!ok) begin errs = errs + 1; $display("FAIL case %0d (mode %0d mask %b ranks %h len %0d order %h): %0d words out, want %0d", ncase, m_, mk[3:0], rk, ln, od, nout, nex_all); end
            end
        end
        $display("%0d cases", ncase);
        if (errs == 0) $display("ALL PASS"); else $display("SOME FAILED %0d", errs);
        $finish;
    end
endmodule
