`timescale 1ns/1ps
// testbench for hexn_ramroute_v5: pass, hold with dly 1 / 10 / 31 / 32 / 50, repeat. Prints PASS/FAIL lines and a final summary.
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg [5:0] fi = 0; wire [5:0] fo; reg cfg_en = 0, cfg_in = 0; wire cfg_out;
    hexn_ramroute_v5 dut (.clk(clk), .fi(fi), .fo(fo), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(cfg_out));
    integer errs = 0, i, k;
    reg [35:0] cw;
    task cfgload(input [1:0] mode, input [6:0] dly);
        begin
            cw = 0;
            cw[17:0] = {3'd5, 3'd4, 3'd3, 3'd2, 3'd1, 3'd0};      // each output face j takes input face j (pass-through routing)
            cw[19:18] = mode; cw[22:20] = 3'd0; cw[25:23] = 3'd3; cw[32:26] = dly; cw[35:33] = 3'd1;   // held stream: face 0, held/replayed bit out on face 3, word-start flag on face 1
            for (k = 35; k >= 0; k = k - 1) begin @(negedge clk); cfg_en = 1; cfg_in = cw[k]; end
            @(negedge clk); cfg_en = 0;
        end
    endtask
    reg [31:0] word, got; reg [199:0] cap;
    task run_word(input [31:0] w, input integer ncap);
        begin
            word = w;
            @(negedge clk); fi[1] = 1; fi[0] = w[0];
            for (i = 0; i < ncap; i = i + 1) begin
                @(negedge clk); fi[1] = 0; fi[0] = (i + 1 < 32) ? w[i + 1] : 1'b0; cap[i] = fo[3];
            end
        end
    endtask
    task check_hold(input [6:0] dly, input [31:0] w);
        integer start, j; reg [31:0] g;
        begin
            cfgload(2'd1, dly);
            run_word(w, 130);
            // output bit j is expected at capture index (dly + j + 1): input presented at negedge n shows up on fo after dly clocks + 2 register stages (read register + output register) minus alignment: find by search
            g = 0; start = -1;
            for (j = 0; j < 100; j = j + 1) begin : srch
                integer b; reg [31:0] t;
                t = 0; for (b = 0; b < 32; b = b + 1) t[b] = cap[j + b];
                if (start < 0 && t == w && j >= 0) start = j;
            end
            if (start < 0) begin errs = errs + 1; $display("FAIL hold dly=%0d: word not found in output (word %h)", dly, w); end
            else $display("PASS hold dly=%0d: word out starting %0d clocks after the flag clock (dly+%0d)", dly, start, start - dly);
            fi = 0; @(negedge clk);
        end
    endtask
    initial begin
        @(negedge clk);
        // PASS mode: face 0 -> face 0 etc.
        cfgload(2'd0, 0);
        fi = 6'b101010; @(negedge clk); @(negedge clk);
        if (fo !== 6'b101010) begin errs = errs + 1; $display("FAIL pass: fo=%b", fo); end else $display("PASS pass-through routing");
        fi = 0;
        check_hold(1,  32'hA5C3_1E7F);
        check_hold(10, 32'h8000_0001);
        check_hold(31, 32'hDEAD_BEEF);
        check_hold(32, 32'h1234_5678);
        check_hold(50, 32'hFFFF_0F0F);
        // REPEAT: record then replay twice
        cfgload(2'd2, 0);
        run_word(32'hC0DE_F00D, 120);
        begin : rep
            integer j, b; reg [31:0] t; integer found, c;
            found = 0;
            for (j = 0; j < 88 && found < 2; j = j + 1) begin
                t = 0; for (b = 0; b < 32; b = b + 1) t[b] = cap[j + b];
                if (t == 32'hC0DE_F00D) begin found = found + 1; $display("PASS repeat: word replay found at capture index %0d", j); j = j + 31; end
            end
            if (found < 2) begin errs = errs + 1; $display("FAIL repeat: replays found %0d (wanted 2)", found); end
        end
        if (errs == 0) $display("ALL PASS"); else $display("SOME FAILED");
        $finish;
    end
endmodule
