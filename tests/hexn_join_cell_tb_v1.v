`timescale 1ns/1ps
// testbench for hexn_join_cell_v1: operand A starts at clock 0, operand B at a different clock (before, together, or up to 45 clocks after); the sum must come out right whatever the order.
module tb;
    parameter OR_BUG = 0;
    reg clk = 0; always #5 clk = ~clk;
    reg a = 0, wsa = 0, b = 0, wsb = 0; wire r, rs;
    hexn_join_cell_v1 #(.OR_BUG(OR_BUG)) dut (.clk(clk), .a(a), .wsa(wsa), .b(b), .wsb(wsb), .r(r), .rs(rs));
    integer errs = 0, trial, i, n, off; reg [31:0] wa_, wb_, got; integer seen; integer gap [0:11]; integer lat;
    initial begin
        gap[0] = 0; gap[1] = 1; gap[2] = 7; gap[3] = 31; gap[4] = 33; gap[5] = 45; gap[6] = -1; gap[7] = -7; gap[8] = -31; gap[9] = -33; gap[10] = -45; gap[11] = 20;
        repeat (3) @(negedge clk);
        for (trial = 0; trial < 12; trial = trial + 1) begin
            wa_ = $random; wb_ = $random; off = gap[trial]; got = 0; seen = 0; lat = -1;
            // clock index n counts from the earlier start
            for (n = 0; n < 130; n = n + 1) begin
                @(negedge clk);
                i = n - ((off < 0) ? -off : 0);                   // A's bit index (A starts at n = 0 when off >= 0, else at -off)
                a = (n >= ((off < 0) ? -off : 0) && n < ((off < 0) ? -off : 0) + 32) ? wa_[n - ((off < 0) ? -off : 0)] : 1'b0;
                wsa = (n == ((off < 0) ? -off : 0));
                b = (n >= ((off > 0) ? off : 0) && n < ((off > 0) ? off : 0) + 32) ? wb_[n - ((off > 0) ? off : 0)] : 1'b0;
                wsb = (n == ((off > 0) ? off : 0));
                #4;
                if (rs && lat < 0) lat = n;
                if (lat >= 0 && n >= lat && n < lat + 32) got[n - lat] = r;
            end
            // rs marks result bit 0 (r and rs are registered together)
            if (got === (wa_ + wb_)) $display("PASS join: B starts %0d clocks after A, sum %h, first result bit at clock %0d", off, got, lat);
            else begin errs = errs + 1; $display("FAIL join: B %0d after A: got %h want %h (lat %0d)", off, got, wa_ + wb_, lat); end
            repeat (6) @(negedge clk); a = 0; b = 0; wsa = 0; wsb = 0;
        end
        if (errs == 0) $display("ALL PASS"); else $display("SOME FAILED");
        $finish;
    end
endmodule
