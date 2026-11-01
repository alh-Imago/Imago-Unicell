`default_nettype none
`timescale 1ns / 1ps
// nano_cell_v4s_tt against the ORIGINAL nano_cell_v4s: same random inputs, every one of the 1,024 topology words, load_hold and flow in random order. Outputs must be identical every clock.
module tb_nano_tt_v1;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg cfgv = 0; reg [31:0] cfgd = 0, hold = 0, flow = 0; reg lh = 0, vin = 0;
    wire [31:0] o1, o2; wire v1, v2;
    nano_cell_v4s    A (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .hold_in_data(hold), .load_hold(lh), .flow_in_data(flow), .valid_in(vin), .data_out(o1), .valid_out(v1));
    nano_cell_v4s_tt B (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .hold_in_data(hold), .load_hold(lh), .flow_in_data(flow), .valid_in(vin), .data_out(o2), .valid_out(v2));
    integer t, i, bad = 0, n = 0;
    always @(negedge clk) begin n = n + 1; if (o1 !== o2 || v1 !== v2) begin bad = bad + 1; if (bad < 6) $display("DIFF at %0t: %h/%b vs %h/%b", $time, o1, v1, o2, v2); end end
    initial begin
        repeat (3) @(negedge clk); rst = 0;
        for (t = 0; t < 1024; t = t + 1) begin
            cfgd = {$urandom} & 32'hFFFFFC00 | t; cfgv = 1; @(negedge clk); cfgv = 0;
            for (i = 0; i < 12; i = i + 1) begin
                hold = (i == 0) ? 32'h0 : (i == 1) ? 32'hFFFFFFFF : $urandom; flow = (i == 2) ? 32'h0 : (i == 3) ? 32'hFFFFFFFF : $urandom;
                lh = ($urandom % 3 != 0); vin = ($urandom % 4 != 0); @(negedge clk);
            end
        end
        if (bad == 0) $display("NANO TT EQUIVALENT (%0d clocks compared, all 1024 topology words)", n); else $display("NANO TT DIFFERS: %0d", bad);
        $finish;
    end
endmodule
