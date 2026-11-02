`timescale 1ns/1ps
// testbench for hexn_unary_core_v1: each op on random words (and 0, ffffffff); shift counts 0 1 5 31; several masks; the accumulator over 5 words in a row, with a clear in the middle.
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg [2:0] op = 0; reg [4:0] k = 0; reg [7:0] mask = 0; reg clear = 0; reg a = 0, af = 0; wire r, rs;
    hexn_unary_core_v1 dut (.clk(clk), .op(op), .k(k), .mask(mask), .clear(clear), .a(a), .af(af), .r(r), .rs(rs));
    integer errs = 0, ntest = 0, n, trial, lat, i; reg [31:0] w, got, want, tot, mk;
    task one(input [2:0] o, input [4:0] kk, input [7:0] mm, input [31:0] ww);
        begin
            op = o; k = kk; mask = mm; got = 0; lat = -1;
            for (n = 0; n < 80; n = n + 1) begin
                @(negedge clk);
                a = (n < 32) ? ww[n] : 1'b0; af = (n == 0);
                #4;
                if (rs && lat < 0) lat = n;
                if (lat >= 0 && n >= lat && n < lat + 32) got[n - lat] = r;
            end
            @(negedge clk); a = 0; af = 0; repeat (70) @(negedge clk);       // let the counter go idle again
        end
    endtask
    initial begin
        repeat (3) @(negedge clk);
        for (trial = 0; trial < 12; trial = trial + 1) begin
            w = $random; if (trial == 0) w = 0; if (trial == 1) w = 32'hFFFF_FFFF;
            one(0, 0, 0, w); want = w; ntest = ntest + 1; if (got !== want) begin errs = errs + 1; $display("FAIL cp %h got %h", w, got); end
            for (i = 0; i < 4; i = i + 1) begin
                k = (i == 0) ? 0 : (i == 1) ? 1 : (i == 2) ? 5 : 31;
                one(1, k, 0, w); want = w << k; ntest = ntest + 1; if (got !== want) begin errs = errs + 1; $display("FAIL shl %0d %h got %h want %h", k, w, got, want); end
                one(2, k, 0, w); want = w >> k; ntest = ntest + 1; if (got !== want) begin errs = errs + 1; $display("FAIL shr %0d %h got %h want %h", k, w, got, want); end
            end
            mk = $random; for (i = 0; i < 32; i = i + 1) want[i] = w[i] & mk[i / 4 + 0 * i];
            one(3, 0, mk[7:0], w);
            for (i = 0; i < 32; i = i + 1) want[i] = w[i] & mk[i / 4];
            ntest = ntest + 1; if (got !== want) begin errs = errs + 1; $display("FAIL mask %h lanes %b got %h want %h", w, mk[7:0], got, want); end
            one(4, 0, 0, w); want = ~w; ntest = ntest + 1; if (got !== want) begin errs = errs + 1; $display("FAIL inv %h got %h", w, got); end
        end
        // accumulator: clear, then 5 words, clear in the middle
        clear = 1; @(negedge clk); clear = 0; @(negedge clk); tot = 0;
        for (trial = 0; trial < 5; trial = trial + 1) begin
            w = $random; if (trial == 3) begin clear = 1; @(negedge clk); clear = 0; tot = 0; end
            one(5, 0, 0, w); tot = tot + w; ntest = ntest + 1;
            if (got !== tot) begin errs = errs + 1; $display("FAIL acc word %0d: got %h want %h", trial, got, tot); end
        end
        if (errs == 0) $display("ALL PASS %0d tests", ntest); else $display("SOME FAILED %0d of %0d", errs, ntest);
        $finish;
    end
endmodule
