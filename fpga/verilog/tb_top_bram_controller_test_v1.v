// tb_top_bram_controller_test_v1.v — elaboration + functional sanity
// check for top_bram_controller_test_v1.v before handing off to
// Quartus. Confirms the self-test FSM completes multiple full passes
// with err_sticky never latching.
`timescale 1ns / 1ps

module tb_top_bram_controller_test_v1;

    reg clk100 = 0;
    always #5 clk100 = ~clk100;

    wire led0, led1;

    top_bram_controller_test_v1 DUT (
        .CLK_100M(clk100),
        .LED0_N(led0),
        .LED1_N(led1)
    );

    initial begin
        #500000;   // several full write+read passes at 25MHz derived clock
        if (DUT.err_sticky)
            $display("FAIL: err_sticky latched -- self-test found a mismatch, pass_seed=%h idx=%0d", DUT.pass_seed, DUT.idx);
        else if ((DUT.pass_seed - 32'hA5A5_5A5A) < 2)
            $display("FAIL: only completed %0d pass(es) in 500us -- FSM may be stuck", DUT.pass_seed - 32'hA5A5_5A5A);
        else
            $display("PASS: top_bram_controller_test_v1 -- %0d full write+read passes, no mismatches, err_sticky never latched", DUT.pass_seed - 32'hA5A5_5A5A);
        $finish;
    end

endmodule
