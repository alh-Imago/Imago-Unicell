// tb_top_adder_chain50_v1.v — elaboration + functional sanity check for
// top_adder_chain50_v1.v (points.md #248, task 2) before handing off to
// Quartus. Confirms the top-level elaborates cleanly and consume_count
// genuinely increments repeatedly.
`timescale 1ns / 1ps

module tb_top_adder_chain50_v1;

    reg clk100 = 0;
    always #5 clk100 = ~clk100;   // 100MHz

    wire led0, led1;

    top_adder_chain50_v1 DUT (
        .CLK_100M(clk100),
        .LED0_N(led0),
        .LED1_N(led1)
    );

    initial begin
        #200000;  // let reset, autoconfig, and many consume cycles run
        if (DUT.consume_count >= 5)
            $display("PASS: top_adder_chain50_v1 elaborates and cascades pulls -- consume_count=%0d after 200us", DUT.consume_count);
        else
            $display("FAIL: consume_count only reached %0d after 200us -- chain stalled or mis-wired", DUT.consume_count);
        $finish;
    end

endmodule
