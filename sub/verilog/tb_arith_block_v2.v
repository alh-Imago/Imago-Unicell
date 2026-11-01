`default_nettype none
`timescale 1ns / 1ps
// arith_block_v2 (shared and naive) vs reference arithmetic; modes 0/1 also vs adder_cell_v4s, mode 4 also vs the real accumulator_cell_v4s (continuous mode).
module tb_arith_block_v2;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg cfgv = 0; reg [31:0] cfgd = 0, a = 0, b = 0; reg vin = 0; reg [31:0] cfgacc = 0; reg inc = 0, dec = 0;
    wire [31:0] o1, o0, oa, oc; wire v1, v0, va, vc;
    arith_block_v2 #(.SHARED(1)) S (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(o1), .valid_out(v1));
    arith_block_v2 #(.SHARED(0)) N (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(o0), .valid_out(v0));
    adder_cell_v4s AC (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(oa), .valid_out(va));
    accumulator_cell_v4s #(.WIDTH(32)) CC (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgacc), .inc_pulse(inc), .dec_pulse(dec), .data_out(oc), .valid_out(vc));
    integer m, i, bad = 0, n = 0; reg [31:0] want; reg signed [31:0] tot; reg [7:0] stp;
    reg [31:0] ex [0:7];
    task fail(input [31:0] x, input [31:0] y, input [31:0] w);
        begin bad = bad + 1; if (bad < 8) $display("MISMATCH m=%0d a=%h b=%h want=%h shared=%h naive=%h", m, x, y, w, o1, o0); end
    endtask
    task try(input [31:0] x, input [31:0] y);
        begin
            a = x; b = y; vin = 1; @(negedge clk); vin = 0; @(negedge clk); n = n + 1;
            case (m)
                0: want = x + y;
                1: want = x - y;
                2: want = ($signed(x) >= $signed(y)) ? 1 : 0;
                default: want = ($signed(x) < $signed(y)) ? 0 : (x == y) ? 1 : 2;
            endcase
            if (o1 !== want || o0 !== want) fail(x, y, want);
            if (m < 2 && oa !== want) begin bad = bad + 1; $display("adder_cell MISMATCH"); end
        end
    endtask
    task pulse_acc(input i_, input d_);
        begin
            a = {30'b0, d_, i_}; inc = i_; dec = d_; vin = 1; @(negedge clk); vin = 0; inc = 0; dec = 0; a = 0; @(negedge clk); n = n + 1;
            if (i_ && !d_) tot = tot + stp; else if (d_ && !i_) tot = tot - stp;
            if (i_ || d_) begin
                if (o1 !== tot || o0 !== tot) begin bad = bad + 1; if (bad < 8) $display("ACC MISMATCH want=%0d shared=%0d naive=%0d", tot, o1, o0); end
                if (oc !== tot) begin bad = bad + 1; if (bad < 8) $display("real accumulator_cell differs: %0d vs %0d", oc, tot); end
            end
        end
    endtask
    initial begin
        ex[0]=0; ex[1]=1; ex[2]=32'hFFFFFFFF; ex[3]=32'h7FFFFFFF; ex[4]=32'h80000000; ex[5]=32'h80000001; ex[6]=32'h12345678; ex[7]=32'hFFFFFFFE;
        repeat (3) @(negedge clk); rst = 0;
        for (m = 0; m < 4; m = m + 1) begin
            cfgd = m; cfgacc = 0; cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk);
            for (i = 0; i < 64; i = i + 1) try(ex[i[5:3]], ex[i[2:0]]);
            for (i = 0; i < 300; i = i + 1) try($urandom, $urandom);
            for (i = 0; i < 100; i = i + 1) begin try($urandom, $urandom); try(32'h7FFFFFFF - ($urandom % 3), 32'h7FFFFFFF - ($urandom % 3)); try($urandom, 32'h0); end
            for (i = 0; i < 40; i = i + 1) begin a = $urandom; try(a, a); end
        end
        m = 4;
        for (stp = 1; stp < 250; stp = stp + 61) begin
            cfgd = {16'h0, stp, 5'b0, 3'd4}; cfgacc = {24'h0, stp}; cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk); tot = 0;
            for (i = 0; i < 200; i = i + 1) pulse_acc($urandom % 2, $urandom % 2);
        end
        if (bad == 0) $display("ALL ARITH BLOCK V2 TESTS PASS (%0d checks, both variants)", n); else $display("ARITH BLOCK V2 FAILED: %0d of %0d", bad, n);
        $finish;
    end
endmodule
