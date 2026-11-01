`default_nettype none
`timescale 1ns / 1ps
// arith_block_v6 mask mode against the REAL mask_cell_v4s: all 256 nibble masks x mask_en 0/1, random data. Block config: mode 7, topology AND (10'h007), heldsrc=1,
// cfg_data[15:8] = mask_en ? ~nibble_mask : 8'hFF. Also: with cfg_data[26]=0 the nano mode still equals the real nano_cell_v4s (v5 behaviour kept).
module tb_arith_block_v6;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg cfgv = 0; reg [31:0] cfgd = 0, mcfg = 0, ncfg = 0, a = 0, b = 0; reg vin = 0; reg lh = 0;
    wire [31:0] ob, om, on; wire vb, vm, vn;
    arith_block_v6 #(.SHARED(1), .NANO_TT(1)) B (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(ob), .valid_out(vb));
    mask_cell_v4s M (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(mcfg), .data_in(a), .valid_in(vin), .data_out(om), .valid_out(vm));
    nano_cell_v4s NC (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(ncfg), .hold_in_data(b), .load_hold(lh), .flow_in_data(a), .valid_in(vin), .data_out(on), .valid_out(vn));
    integer mk, en, i, bad = 0, n = 0; reg [7:0] keep8;
    initial begin
        repeat (3) @(negedge clk); rst = 0;
        for (en = 0; en < 2; en = en + 1) for (mk = 0; mk < 256; mk = mk + 1) begin
            mcfg = {23'b0, mk[7:0], en[0]};
            keep8 = en ? ~mk[7:0] : 8'hFF;
            cfgd = (32'h1 << 26) | (32'h007 << 16) | ({24'b0, keep8} << 8) | 32'h7;
            cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk);
            for (i = 0; i < 4; i = i + 1) begin
                a = (i == 0) ? 32'hFFFFFFFF : $urandom; b = $urandom; vin = 1; @(negedge clk); #1;
                if (!(vb && vm)) begin bad = bad + 1; if (bad < 6) $display("NO ANSWER"); end
                vin = 0; @(negedge clk); n = n + 1;
                if (ob !== om) begin bad = bad + 1; if (bad < 6) $display("MASK DIFF en=%0d mask=%h in=%h block=%h cell=%h", en, mk[7:0], a, ob, om); end
            end
        end
        // v5 behaviour kept: nano XOR with HELD = in_b
        cfgd = (32'h0BC << 16) | 32'h7; ncfg = 32'h0BC; cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk);
        for (i = 0; i < 100; i = i + 1) begin
            b = $urandom; lh = 1; @(negedge clk); lh = 0; a = $urandom; vin = 1; @(negedge clk); vin = 0; @(negedge clk); n = n + 1;
            if (ob !== on) begin bad = bad + 1; if (bad < 6) $display("NANO DIFF"); end
        end
        if (bad == 0) $display("ALL ARITH BLOCK V6 TESTS PASS (%0d checks: 512 mask configs, nano kept)", n); else $display("ARITH BLOCK V6 FAILED: %0d of %0d", bad, n);
        $finish;
    end
endmodule
