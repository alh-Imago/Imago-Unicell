`default_nettype none
`timescale 1ns / 1ps
// arith_block_v8 coarse-only shifters. CF2: binary amount, supported 0,1,2,4,8,12,16, others = data unchanged. CF3: tap index in in_b[2:0]. Both directions, edge and random data; add spot check.
module tb_arith_block_v8;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg cfgv = 0; reg [31:0] cfgd = 0, a = 0, b = 0; reg vin = 0;
    wire [31:0] o2, o3; wire v2, v3;
    arith_block_v8 #(.SHIFT_CF(2), .NANO_TT(1)) B2 (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(o2), .valid_out(v2));
    arith_block_v8 #(.SHIFT_CF(3), .NANO_TT(1)) B3 (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(o3), .valid_out(v3));
    integer bad = 0, n = 0, i, t, m; reg [31:0] w2, w3; reg [17:0] x; integer amt3;
    function [17:0] sh1(input [17:0] d, input integer amt, input integer dir);
        begin if (dir == 5) sh1 = (d << amt); else sh1 = (d >> amt); end
    endfunction
    function integer tapamt(input integer idx);
        begin case (idx) 1: tapamt = 1; 2: tapamt = 2; 3: tapamt = 4; 4: tapamt = 8; 5: tapamt = 12; 6: tapamt = 16; default: tapamt = 0; endcase end
    endfunction
    function integer supp(input integer t);
        begin supp = (t == 1 || t == 2 || t == 4 || t == 8 || t == 12 || t == 16); end
    endfunction
    initial begin
        repeat (3) @(negedge clk); rst = 0;
        for (m = 5; m <= 6; m = m + 1) begin
            cfgd = m; cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk);
            for (t = 0; t < 32; t = t + 1) for (i = 0; i < 30; i = i + 1) begin
                x = (i == 0) ? 18'h3FFFF : (i == 1) ? 18'h00001 : (i == 2) ? 18'h20000 : $urandom;
                a = {$urandom} & 32'hFFFC0000 | {14'b0, x}; b = ($urandom & 32'hFFFFFFE0) | t; vin = 1; @(negedge clk); #1;
                if (!(v2 && v3)) begin bad = bad + 1; if (bad < 8) $display("NO ANSWER"); end
                vin = 0; @(negedge clk);
                w2 = {14'b0, supp(t) ? sh1(a[17:0], t, m) : a[17:0]};
                amt3 = (t[2:0] == 0 || t[2:0] == 7) ? 0 : tapamt(t[2:0]);
                w3 = {14'b0, sh1(a[17:0], amt3, m)};
                n = n + 2;
                if (o2 !== w2) begin bad = bad + 1; if (bad < 8) $display("CF2 MISMATCH m=%0d t=%0d a=%h want=%h got=%h", m, t, a, w2, o2); end
                if (o3 !== w3) begin bad = bad + 1; if (bad < 8) $display("CF3 MISMATCH m=%0d t=%0d a=%h want=%h got=%h", m, t, a, w3, o3); end
            end
        end
        cfgd = 0; cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk);
        for (i = 0; i < 100; i = i + 1) begin a = $urandom; b = $urandom; vin = 1; @(negedge clk); vin = 0; @(negedge clk); n = n + 2; if (o2 !== a + b || o3 !== a + b) begin bad = bad + 1; if (bad < 8) $display("ADD MISMATCH"); end end
        if (bad == 0) $display("ALL ARITH BLOCK V8 TESTS PASS (%0d checks)", n); else $display("ARITH BLOCK V8 FAILED: %0d of %0d", bad, n);
        $finish;
    end
endmodule
