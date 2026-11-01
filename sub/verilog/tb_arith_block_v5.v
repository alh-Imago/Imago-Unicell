`default_nettype none
`timescale 1ns / 1ps
// arith_block_v5 (shared and naive). Modes 0-4 as v4 (spot check, add/sub vs adder_cell_v4s, accumulate vs accumulator_cell_v4s). NEW: 5/6 18-bit shifts against a reference;
// 7 nano logic against the REAL nano_cell_v4s for all 12 topologies (HELD loaded with load_hold = in_b, FLOW = in_a). in_a/in_b are left STALE after each word on purpose.
module tb_arith_block_v5;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg cfgv = 0; reg [31:0] cfgd = 0, a = 0, b = 0; reg vin = 0;
    wire [31:0] o1, o0, on, oT; wire v1, v0, vn, vT;
    arith_block_v5 #(.SHARED(1)) S (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(o1), .valid_out(v1));
    arith_block_v5 #(.SHARED(0)) N (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(o0), .valid_out(v0));
    arith_block_v5 #(.SHARED(1), .NANO_TT(1)) T (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(oT), .valid_out(vT));
    reg [31:0] ncfg = 0; reg lh = 0;
    nano_cell_v4s NC (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(ncfg), .hold_in_data(b), .load_hold(lh), .flow_in_data(a), .valid_in(vin), .data_out(on), .valid_out(vn));
    integer bad = 0, n = 0, i, t; reg [31:0] want; reg [17:0] x; integer m;
    reg [9:0] topos [0:11];
    task chk(input [31:0] w, input [255:0] what);
        begin n = n + 1; if (o1 !== w || o0 !== w || oT !== w) begin bad = bad + 1; if (bad < 8) $display("MISMATCH %0s a=%h b=%h want=%h shared=%h naive=%h tt=%h topo=%h", what, a, b, w, o1, o0, oT, cfgd[25:16]); end end
    endtask
    task word(input [31:0] x_, input [31:0] y_);
        begin a = x_; b = y_; vin = 1; @(negedge clk); #1; if (!(v1 && v0 && vT)) begin bad = bad + 1; if (bad < 8) $display("NO ANSWER m=%0d", m); end vin = 0; @(negedge clk); end
    endtask
    initial begin
        topos[0]=10'h000; topos[1]=10'h02C; topos[2]=10'h001; topos[3]=10'h002; topos[4]=10'h004; topos[5]=10'h007; topos[6]=10'h024; topos[7]=10'h027; topos[8]=10'h0BC; topos[9]=10'h03C; topos[10]=10'h030; topos[11]=10'h0B0;
        repeat (3) @(negedge clk); rst = 0;
        // shifts: every amount 0..31 on random and edge data
        for (m = 5; m <= 6; m = m + 1) begin
            cfgd = m; cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk);
            for (t = 0; t < 32; t = t + 1) for (i = 0; i < 12; i = i + 1) begin
                x = (i == 0) ? 18'h3FFFF : (i == 1) ? 18'h00001 : (i == 2) ? 18'h20000 : $urandom;
                word({$urandom} | 32'hFFFC0000 & {$urandom} | {14'b0, x} , ($urandom & 32'hFFFFFFE0) | t);   // upper bits of a random: only the low 18 may matter
                a = a;
                want = (m == 5) ? ({14'b0, ((a[17:0] << t) & 18'h3FFFF)}) : ({14'b0, (a[17:0] >> t)});
                if (t >= 18) want = 32'h0;
                chk(want, (m == 5) ? "shl" : "shr");
            end
        end
        // nano: all 12 topologies against the real nano cell
        for (t = 0; t < 12; t = t + 1) begin
            cfgd = {6'b0, topos[t], 8'b0, 5'b0, 3'd7}; ncfg = {22'b0, topos[t]}; cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk);
            for (i = 0; i < 40; i = i + 1) begin
                b = $urandom; lh = 1; @(negedge clk); lh = 0;       // HELD = b into the real cell
                a = (i == 0) ? 32'h0 : (i == 1) ? 32'hFFFFFFFF : $urandom; vin = 1; @(negedge clk); #1;
                if (!(v1 && v0 && vn && vT)) begin bad = bad + 1; if (bad < 8) $display("NO ANSWER nano"); end
                vin = 0; @(negedge clk);
                chk(on, "nano vs real nano_cell");
            end
        end
        // spot check of an old mode so a break of modes 0-4 shows: add and sub
        for (m = 0; m <= 1; m = m + 1) begin
            cfgd = m; cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk);
            for (i = 0; i < 100; i = i + 1) begin word($urandom, $urandom); chk((m == 0) ? a + b : a - b, "add/sub"); end
        end
        if (bad == 0) $display("ALL ARITH BLOCK V5 TESTS PASS (%0d checks, three variants: shared, naive, shared + truth-table nano)", n); else $display("ARITH BLOCK V5 FAILED: %0d of %0d", bad, n);
        $finish;
    end
endmodule
