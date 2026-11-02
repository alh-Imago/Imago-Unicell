`timescale 1ns/1ps
// testbench for hexn_join_core_v2: every op, random operands, operand B starting before / together with / after A; edge words 0 and ffffffff; results compared with the plain operator.
module tb;
    parameter OR_BUG = 0;
    reg clk = 0; always #5 clk = ~clk;
    reg [2:0] op = 0; reg a = 0, wsa = 0, b = 0, wsb = 0; wire r, rs;
    hexn_join_core_v2 #(.OR_BUG(OR_BUG)) dut (.clk(clk), .op(op), .a(a), .wsa(wsa), .b(b), .wsb(wsb), .r(r), .rs(rs));
    integer errs = 0, ntest = 0, n, trial, lat, oi, off, offa, offb; reg [31:0] wa_, wb_, got, want; integer gaps [0:7];
    initial begin
        gaps[0] = 0; gaps[1] = 3; gaps[2] = -3; gaps[3] = 20; gaps[4] = -20; gaps[5] = 40; gaps[6] = -40; gaps[7] = 1;
        repeat (3) @(negedge clk);
        for (oi = 0; oi < 8; oi = oi + 1) begin
            for (trial = 0; trial < 10; trial = trial + 1) begin
                op = oi; wa_ = $random; wb_ = $random;
                if (trial == 0) begin wa_ = 0; wb_ = 32'hFFFF_FFFF; end
                if (trial == 1) begin wa_ = 32'hFFFF_FFFF; wb_ = 0; end
                if (trial == 2) wb_ = wa_;
                if (trial == 3) begin wa_ = 32'h8000_0000; wb_ = 32'h7FFF_FFFF; end
                off = gaps[trial % 8]; offa = (off < 0) ? -off : 0; offb = (off > 0) ? off : 0;
                got = 0; lat = -1;
                for (n = 0; n < 220; n = n + 1) begin
                    @(negedge clk);
                    a = (n >= offa && n < offa + 32) ? wa_[n - offa] : 1'b0; wsa = (n == offa);
                    b = (n >= offb && n < offb + 32) ? wb_[n - offb] : 1'b0; wsb = (n == offb);
                    #4;
                    if (rs && lat < 0) lat = n;
                    if (lat >= 0 && n >= lat && n < lat + 32) got[n - lat] = r;
                end
                case (oi) 0: want = wa_ + wb_; 1: want = wa_ - wb_; 2: want = wa_ & wb_; 3: want = wa_ | wb_; 4: want = wa_ ^ wb_;
                          5: want = (wa_ < wb_) ? 32'd1 : 32'd0; 6: want = (wa_ < wb_) ? wa_ : wb_; default: want = (wa_ < wb_) ? wb_ : wa_; endcase
                ntest = ntest + 1;
                if (lat < 0 || got !== want) begin errs = errs + 1; $display("FAIL op %0d a=%h b=%h got %h want %h (start %0d, B %0d after A)", oi, wa_, wb_, got, want, lat, off); end
                repeat (6) @(negedge clk); a = 0; b = 0; wsa = 0; wsb = 0;
            end
            if (errs == 0) $display("PASS op %0d", oi);
        end
        if (errs == 0) $display("ALL PASS %0d tests", ntest); else $display("SOME FAILED %0d of %0d", errs, ntest);
        $finish;
    end
endmodule
