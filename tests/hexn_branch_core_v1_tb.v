`timescale 1ns/1ps
// testbench for hexn_branch_core_v1: signed 3-way compare (including -2^31 against 2^31-1, equal words, negative against positive), five route/emit set-ups, operand B before / together with / after A.
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg [1:0] rlt = 0, req = 0, rgt = 0, emit = 0; reg [31:0] fixed = 0; reg a = 0, wsa = 0, b = 0, wsb = 0; wire o1, o1s, o2, o2s;
    hexn_branch_core_v1 dut (.clk(clk), .route_lt(rlt), .route_eq(req), .route_gt(rgt), .emit(emit), .fixed(fixed), .a(a), .wsa(wsa), .b(b), .wsb(wsb), .o1(o1), .o1s(o1s), .o2(o2), .o2s(o2s));
    integer errs = 0, ntest = 0, n, cfgi, trial, l1, l2, n1, n2, off, offa, offb; reg [31:0] wa_, wb_, g1, g2, w1, w2; reg [1:0] m; integer gaps [0:5];
    reg signed [31:0] sa_, sb_;
    initial begin
        gaps[0] = 0; gaps[1] = 4; gaps[2] = -4; gaps[3] = 25; gaps[4] = -25; gaps[5] = 45;
        repeat (3) @(negedge clk);
        for (cfgi = 0; cfgi < 5; cfgi = cfgi + 1) begin
            case (cfgi)
                0: begin rlt = 2'b01; req = 2'b10; rgt = 2'b11; emit = 2'd1; fixed = 32'h0; end        // lt -> out1, eq -> out2, gt -> both ; emit a
                1: begin rlt = 2'b11; req = 2'b00; rgt = 2'b01; emit = 2'd3; fixed = 32'h0; end        // lt -> both, eq -> neither, gt -> out1 ; emit a - b
                2: begin rlt = 2'b10; req = 2'b01; rgt = 2'b10; emit = 2'd0; fixed = 32'hCAFE_0042; end // emit the fixed word
                3: begin rlt = 2'b01; req = 2'b01; rgt = 2'b01; emit = 2'd2; fixed = 32'h0; end        // everything -> out1, emit b
                default: begin rlt = 2'b00; req = 2'b00; rgt = 2'b00; emit = 2'd1; fixed = 32'h0; end  // neither, always
            endcase
            for (trial = 0; trial < 12; trial = trial + 1) begin
                wa_ = $random; wb_ = $random;
                if (trial == 0) begin wa_ = 32'h8000_0000; wb_ = 32'h7FFF_FFFF; end
                if (trial == 1) begin wa_ = 32'h7FFF_FFFF; wb_ = 32'h8000_0000; end
                if (trial == 2) wb_ = wa_;
                if (trial == 3) begin wa_ = 32'hFFFF_FFFF; wb_ = 32'h0000_0001; end
                if (trial == 4) begin wa_ = 32'h0000_0001; wb_ = 32'hFFFF_FFFF; end
                off = gaps[trial % 6]; offa = (off < 0) ? -off : 0; offb = (off > 0) ? off : 0;
                g1 = 0; g2 = 0; l1 = -1; l2 = -1; n1 = 0; n2 = 0;
                for (n = 0; n < 230; n = n + 1) begin
                    @(negedge clk);
                    a = (n >= offa && n < offa + 32) ? wa_[n - offa] : 1'b0; wsa = (n == offa);
                    b = (n >= offb && n < offb + 32) ? wb_[n - offb] : 1'b0; wsb = (n == offb);
                    #4;
                    if (o1s) begin n1 = n1 + 1; if (l1 < 0) l1 = n; end
                    if (o2s) begin n2 = n2 + 1; if (l2 < 0) l2 = n; end
                    if (l1 >= 0 && n >= l1 && n < l1 + 32) g1[n - l1] = o1;
                    if (l2 >= 0 && n >= l2 && n < l2 + 32) g2[n - l2] = o2;
                end
                sa_ = wa_; sb_ = wb_;
                m = (sa_ == sb_) ? req : (sa_ < sb_) ? rlt : rgt;
                case (emit) 2'd0: w1 = fixed; 2'd1: w1 = wa_; 2'd2: w1 = wb_; default: w1 = wa_ - wb_; endcase
                ntest = ntest + 1;
                if (n1 != (m[0] ? 1 : 0) || n2 != (m[1] ? 1 : 0) || (m[0] && g1 !== w1) || (m[1] && g2 !== w1)) begin
                    errs = errs + 1; $display("FAIL cfg %0d a=%h b=%h: route %b, out1 n=%0d %h out2 n=%0d %h, want %h", cfgi, wa_, wb_, m, n1, g1, n2, g2, w1);
                end
                repeat (6) @(negedge clk); a = 0; b = 0; wsa = 0; wsb = 0;
            end
            if (errs == 0) $display("PASS config %0d", cfgi);
        end
        if (errs == 0) $display("ALL PASS %0d tests", ntest); else $display("SOME FAILED %0d of %0d", errs, ntest);
        $finish;
    end
endmodule
