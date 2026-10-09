// tb_zone750_v2_freeze.v — same proof as tb_grid5x5_both_v2_freeze.v, at the
// full 750-cell (25x30) zone scale -- Alan's actual per-zone target.
// Confirms the freeze-cascade exercise threaded into
// top_stripped_zone750_v2.v behaves correctly before this build goes to
// Quartus for re-measurement.
`timescale 1ns / 1ps

module tb_zone750_v2_freeze;

    reg CLK_100M = 0;
    always #5 CLK_100M = ~CLK_100M;   // 100MHz

    wire LED0_N, LED1_N;

    top_stripped_zone750_v2 DUT (
        .CLK_100M(CLK_100M),
        .LED0_N(LED0_N),
        .LED1_N(LED1_N)
    );

    reg seen_freeze_cascade = 1'b0;
    reg seen_recovery       = 1'b0;

    always @(posedge CLK_100M) begin
        if (DUT.freeze_cascade_seen && !seen_freeze_cascade) begin
            seen_freeze_cascade <= 1'b1;
            $display("[t=%0t] freeze_cascade_seen went high -- backpressure cascaded through the full 750-cell zone", $time);
        end
        if (seen_freeze_cascade && DUT.fz_phase == 2'd3 /* PH_DONE */ && DUT.all_ready && !seen_recovery) begin
            seen_recovery <= 1'b1;
            $display("[t=%0t] all_ready recovered after release", $time);
        end
    end

    initial begin
        $display("Starting 750-cell zone freeze-cascade test (750 cells * 3 words to program -- this takes longer)...");
        // 750*3 = 2250 word-cycles + settle(200) + hold(2000) + margin, all
        // in 'clk' ticks (x4 CLK_100M each) -- generous margin below.
        #2000000;

        if (!seen_freeze_cascade)
            $display("FAIL: freeze_cascade_seen never asserted at 750-cell scale");
        else if (!seen_recovery)
            $display("FAIL: cascade seen but all_ready never recovered");
        else
            $display("PASS: freeze cascades correctly through the full 750-cell zone, and recovers cleanly after release");

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
