// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_top_sentinel_discrete_test_v2.v — regression check for #298's
// remaining bug, root-caused and fixed as #306 (the config-race, one
// feed lost every pass) and #307 (the fixed-collect-count test-
// stimulus bug, latch failing to clear at feed_target=11/12). Public-
// interface-only (LED1_N, the same active-low error signal real
// hardware would show) — no hierarchical debug references, matching
// the discipline that a keepable testbench should check what the
// design actually exposes, not poke internals.
//
// Runs long enough to cycle through all four feed_target values
// (9/10/11/12, #283/#286's varying-stimulus mechanism) many times
// over — far beyond the single intermittent instance #298 originally
// reported, to build real confidence rather than declare victory on
// a short run.
`timescale 1ns / 1ps

module tb_top_sentinel_discrete_test_v2;

    reg CLK_100M = 1'b0;
    wire LED0_N, LED1_N;

    top_sentinel_discrete_test_v2 DUT (
        .CLK_100M(CLK_100M),
        .LED0_N(LED0_N),
        .LED1_N(LED1_N)
    );

    always #5 CLK_100M = ~CLK_100M;   // 100 MHz

    integer errors = 0;

    // LED1_N is active-low: LIT (0) = error. Sample continuously —
    // a single glitch anywhere in the run is a real failure.
    always @(posedge CLK_100M) begin
        if (LED1_N === 1'b0) errors = errors + 1;
    end

    initial begin
        // ~50+ full passes worth of real time at the design's own
        // 25MHz internal clk (CLK_100M/4) — enough to cycle the
        // feed_target=9/10/11/12 sequence more than a dozen times over.
        #5_000_000;   // 5ms of sim time

        if (errors == 0)
            $display("PASS: top_sentinel_discrete_test_v2 -- LED1_N (err_sticky) never lit across the full run, #306/#307's fixes hold");
        else
            $display("FAIL: top_sentinel_discrete_test_v2 -- LED1_N lit %0d time(s) during the run", errors);

        $finish;
    end

endmodule
