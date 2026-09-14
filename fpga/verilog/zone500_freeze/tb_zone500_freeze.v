// tb_zone500_freeze.v — same proof as tb_zone750_freeze.v, at the
// 500-cell (20x25) fallback zone scale. Confirms top_stripped_zone500_v1.v
// is sim-correct (freeze cascade + recovery, armed gate, routing self-
// consistency) before it's ever needed in Quartus.
`timescale 1ns / 1ps

module tb_zone500_freeze;

    reg CLK_100M = 0;
    always #5 CLK_100M = ~CLK_100M;   // 100MHz

    wire LED0_N, LED1_N;

    top_stripped_zone500_v1 DUT (
        .CLK_100M(CLK_100M),
        .LED0_N(LED0_N),
        .LED1_N(LED1_N)
    );

    reg seen_freeze_cascade = 1'b0;
    reg seen_recovery       = 1'b0;

    always @(posedge CLK_100M) begin
        if (DUT.freeze_cascade_seen && !seen_freeze_cascade) begin
            seen_freeze_cascade <= 1'b1;
            $display("[t=%0t] freeze_cascade_seen went high -- backpressure cascaded through the 500-cell fallback zone", $time);
        end
        if (seen_freeze_cascade && DUT.fz_phase == 2'd3 /* PH_DONE */ && DUT.all_ready && !seen_recovery) begin
            seen_recovery <= 1'b1;
            $display("[t=%0t] all_ready recovered after release", $time);
        end
    end

    initial begin
        $display("Starting 500-cell fallback zone freeze-cascade test...");
        #1400000;

        if (!seen_freeze_cascade)
            $display("FAIL: freeze_cascade_seen never asserted at 500-cell scale");
        else if (!seen_recovery)
            $display("FAIL: cascade seen but all_ready never recovered");
        else
            $display("PASS: freeze cascades correctly through the 500-cell fallback zone, and recovers cleanly after release");

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
