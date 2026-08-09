// tb_top_ram_chain50_v1.v — elaboration + functional sanity check for
// top_ram_chain50_v1.v (points.md #248, task 1) before handing off to
// Quartus. Confirms the top-level itself elaborates cleanly and that the
// consumer's consume_count genuinely increments repeatedly (i.e. the
// whole 50-cell chain is cascading pulls, not stalled after first fill).
`timescale 1ns / 1ps

module tb_top_ram_chain50_v1;

    reg clk100 = 0;
    always #5 clk100 = ~clk100;   // 100MHz

    wire led0, led1;

    top_ram_chain50_v1 DUT (
        .CLK_100M(clk100),
        .LED0_N(led0),
        .LED1_N(led1)
    );

    // Peek at the consumer's internal consume_count via hierarchical ref
    // (sim-only introspection, same style used elsewhere in this project's
    // top-level sanity testbenches).
    initial begin
        #200000;  // let reset, autoconfig (50 cycles @ div4), and many
                   // consume cycles run
        if (DUT.consume_count >= 10)
            $display("PASS: top_ram_chain50_v1 elaborates and cascades pulls -- consume_count=%0d after 200us", DUT.consume_count);
        else
            $display("FAIL: consume_count only reached %0d after 200us -- chain stalled or mis-wired", DUT.consume_count);
        $finish;
    end

endmodule
