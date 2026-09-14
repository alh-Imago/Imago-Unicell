// tb_grid5x5_both_v2_freeze.v — confirms points.md #152's host-driven
// freeze/backpressure proof (2-cell scale, tb_wrapper_freeze_cascade.v)
// survives real grid topology and wiring, not just the isolated pair.
// Instantiates the actual synthesis top unmodified and watches its
// internal state via hierarchical reference -- the top's own driver now
// freezes FREEZE_TARGET (r=2,c=2) after programming completes and holds
// it; this testbench just confirms freeze_cascade_seen goes high during
// the hold window and that all_ready recovers after release.
`timescale 1ns / 1ps

module tb_grid5x5_both_v2_freeze;

    reg CLK_100M = 0;
    always #5 CLK_100M = ~CLK_100M;   // 100MHz

    wire LED0_N, LED1_N;

    top_stripped_grid5x5_both_v2 DUT (
        .CLK_100M(CLK_100M),
        .LED0_N(LED0_N),
        .LED1_N(LED1_N)
    );

    reg seen_freeze_cascade = 1'b0;
    reg seen_recovery       = 1'b0;

    always @(posedge CLK_100M) begin
        if (DUT.freeze_cascade_seen && !seen_freeze_cascade) begin
            seen_freeze_cascade <= 1'b1;
            $display("[t=%0t] freeze_cascade_seen went high -- backpressure cascaded through the grid while cell (2,2) was frozen", $time);
        end
        if (seen_freeze_cascade && DUT.fz_phase == 2'd3 /* PH_DONE */ && DUT.all_ready && !seen_recovery) begin
            seen_recovery <= 1'b1;
            $display("[t=%0t] all_ready recovered after release -- backpressure cleared cleanly", $time);
        end
    end

    initial begin
        $display("Starting 25-cell grid freeze-cascade test (this takes a while -- programming + hold + release)...");
        // Programming: 25 cells * 3 words, each word ~4 CLK_100M cycles (clk = CLK_100M/4).
        // Settle (200) + hold (2000) + release, all in 'clk' ticks (x4 CLK_100M each).
        // Generous margin: 20000 CLK_100M cycles covers it with room to spare.
        #200000;

        if (!seen_freeze_cascade) begin
            $display("FAIL: freeze_cascade_seen never asserted -- backpressure did not cascade at grid scale");
        end else if (!seen_recovery) begin
            $display("FAIL: cascade was seen but all_ready never recovered after release");
        end else begin
            $display("PASS: freeze cascades correctly through the full 25-cell grid, and recovers cleanly after release");
        end

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
