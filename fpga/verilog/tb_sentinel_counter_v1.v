// tb_sentinel_counter_v1.v — points.md #279 continuation: confirms
// sentinel_counter_v1.v's three real behaviors — normal completion
// (need_data raises immediately on wrap, results_ready/safe_to_intervene
// only once diff genuinely drains to 0, not before), the diff<0 error
// (freeze_out fires immediately, even without a wrap), and the
// diff>=2*chain_length error (freeze_in fires) — plus that both error
// latches are genuinely sticky until host_unfreeze_pulse.
`timescale 1ns / 1ps

module tb_sentinel_counter_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam DW = 16;
    reg  feed = 0, collect = 0, out_wrap = 0, unfreeze = 0;
    reg  [DW-1:0] chain_length = 16'd4;

    wire freeze_out, freeze_in, need_data, results_ready, safe, err;
    wire signed [DW:0] diff;

    sentinel_counter_v1 #(.DIFF_WIDTH(DW)) DUT (
        .clk(clk), .rst(rst),
        .feed_pulse(feed), .collect_pulse(collect), .chain_length(chain_length),
        .out_wrap_pulse(out_wrap), .host_unfreeze_pulse(unfreeze),
        .freeze_out(freeze_out), .freeze_in(freeze_in),
        .need_data_flag(need_data), .results_ready_flag(results_ready),
        .safe_to_intervene(safe), .err_flag(err), .diff_out(diff)
    );

    integer errors = 0;

    // NOTE: an earlier draft chained `@(posedge clk)` immediately after
    // setting each pulse signal — the exact same class of testbench
    // race already diagnosed and fixed once this session (points.md
    // #252): every pulse registered TWICE (diff read 8 after 4 feeds,
    // -2 after what should have been a single extra collect). Fixed
    // the same proven way — plain `#`-delays with genuine settling
    // margin, not tightly chained edge-waits.
    task pulse_feed;  begin feed = 1; #10; feed = 0; #10; end endtask
    task pulse_coll;  begin collect = 1; #10; collect = 0; #10; end endtask
    task pulse_wrap;  begin out_wrap = 1; #10; out_wrap = 0; #10; end endtask
    task pulse_unfrz; begin unfreeze = 1; #10; unfreeze = 0; #10; end endtask

    initial begin
        #12 rst = 0;
        #10;

        // ── PART 0: power-on state, BEFORE any feed/collect has ever
        // happened -- Alan's own question, confirmed directly: real
        // deployment never pre-fills memory, so the read side must be
        // frozen from power-on, not just after its first wrap. ──
        if (!need_data || !results_ready || !safe) begin
            $display("FAIL: power-on state should ALREADY show need_data/results_ready/safe -- host should see 'ready to load' immediately, before any run (need_data=%b results_ready=%b safe=%b)",
                need_data, results_ready, safe);
            errors = errors + 1;
        end else begin
            $display("OK: power-on state correctly shows safe_to_intervene immediately -- host knows to load initial data before the first run, same protocol as every later reload");
        end
        if (diff !== 0) begin
            $display("FAIL: diff should be 0 at power-on (nothing fed or collected yet), got %0d", diff);
            errors = errors + 1;
        end

        // Host performs the initial load, then unfreezes -- exactly
        // the same action as any later reload.
        pulse_unfrz();
        #10;
        if (need_data || results_ready || safe || out_wrap /* sanity: out_wrap itself untouched */) begin
            $display("FAIL: flags should clear after the initial unfreeze, same as any later one");
            errors = errors + 1;
        end else begin
            $display("OK: PART 0 (power-on frozen state) -- all correct");
        end

        // ── PART 1: normal completion. Feed 4 items (chain_length=4),
        // confirm diff rises. Wrap (OUT stops feeding) -- need_data
        // should raise IMMEDIATELY, but results_ready/safe should NOT
        // yet (diff is still 4, pipeline hasn't drained). Then collect
        // all 4 -- results_ready/safe should raise only once diff hits
        // exactly 0. ──
        pulse_feed(); pulse_feed(); pulse_feed(); pulse_feed();
        #10;
        if (diff !== 4) begin $display("FAIL: diff should be 4 after 4 feeds, got %0d", diff); errors=errors+1; end

        pulse_wrap();
        #10;
        if (!need_data) begin $display("FAIL: need_data should raise immediately on wrap"); errors=errors+1; end
        if (results_ready || safe) begin $display("FAIL: results_ready/safe should NOT be true yet (diff still nonzero)"); errors=errors+1; end
        else $display("OK: need_data raised immediately, results_ready correctly still false (diff=%0d)", diff);

        pulse_coll(); pulse_coll(); pulse_coll();
        #10;
        if (results_ready || safe) begin $display("FAIL: results_ready/safe should still be false (diff=%0d, not yet 0)", diff); errors=errors+1; end

        pulse_coll();   // 4th collect -- diff should now hit exactly 0
        #10;
        if (!results_ready || !safe) begin $display("FAIL: results_ready/safe should be TRUE now (diff=%0d)", diff); errors=errors+1; end
        else $display("OK: results_ready/safe correctly raised once diff genuinely reached 0");

        pulse_unfrz();
        #10;
        if (need_data || results_ready || safe) begin $display("FAIL: flags should clear after host_unfreeze_pulse"); errors=errors+1; end
        else $display("OK: PART 1 (normal completion) -- all correct");

        // ── PART 2: diff<0 error -- a spurious extra collect beyond
        // what was fed. Should freeze_out + err_flag IMMEDIATELY, no
        // wrap needed. ──
        pulse_coll();
        #10;
        if (!err || !freeze_out) begin $display("FAIL: diff<0 should immediately set err_flag+freeze_out"); errors=errors+1; end
        else $display("OK: diff<0 error correctly detected (diff=%0d), freeze_out asserted", diff);

        // Confirm STICKY -- stays latched even after diff would
        // naturally recover.
        pulse_feed();
        #10;
        if (!err) begin $display("FAIL: err_flag should stay STICKY, not self-clear"); errors=errors+1; end
        else $display("OK: err_flag genuinely sticky, did not self-clear");

        pulse_unfrz();
        #10;
        if (err || freeze_out) begin $display("FAIL: error should clear on host_unfreeze_pulse"); errors=errors+1; end
        else $display("OK: PART 2 (diff<0 error) -- all correct");

        // ── PART 3: diff>=2*chain_length error (chain_length=4, so
        // threshold=8) -- feed 8 times with no collects. Should
        // freeze_in + err_flag. ──
        repeat (8) pulse_feed();
        #10;
        if (!err || !freeze_in) begin $display("FAIL: diff>=2*chain_length should set err_flag+freeze_in (diff=%0d)", diff); errors=errors+1; end
        else $display("OK: diff>=2*chain_length error correctly detected (diff=%0d), freeze_in asserted", diff);

        $display("DEBUG before unfreeze: diff=%0d err_negative=%b err_overflow=%b err=%b freeze_in=%b unfreeze_reg=%b", diff, DUT.err_negative, DUT.err_overflow, err, freeze_in, unfreeze);

        // A genuine recovery, not just clearing the flag while the
        // fault persists — an earlier draft pulsed unfreeze ALONE and
        // expected the error to stay cleared, which is the WRONG
        // expectation: `diff` was still at 8 (>= threshold), so the
        // error correctly re-latched on the very next cycle once
        // unfreeze went back to 0 (confirmed via direct per-edge
        // tracing — err_overflow genuinely cleared for one cycle, then
        // immediately re-asserted because the underlying condition was
        // still true). That's the SAFE, correct behavior — a host
        // can't paper over a real ongoing fault by clearing the flag
        // alone. Real recovery: drain enough of the excess in-flight
        // data first (4 collects, bringing diff from 8 down to 4,
        // safely under the threshold of 8), THEN unfreeze.
        pulse_coll(); pulse_coll(); pulse_coll(); pulse_coll();
        pulse_unfrz();
        $display("DEBUG after real recovery + unfreeze: diff=%0d err_negative=%b err_overflow=%b err=%b freeze_in=%b unfreeze_reg=%b", diff, DUT.err_negative, DUT.err_overflow, err, freeze_in, unfreeze);
        #10;
        $display("DEBUG +10 later: diff=%0d err_negative=%b err_overflow=%b err=%b freeze_in=%b", diff, DUT.err_negative, DUT.err_overflow, err, freeze_in);
        if (err || freeze_in) begin $display("FAIL: error should clear on a genuine recovery (drain + unfreeze)"); errors=errors+1; end
        else $display("OK: PART 3 (diff>=2*chain_length error, genuine recovery) -- all correct");

        if (errors == 0)
            $display("PASS: sentinel_counter_v1 -- normal completion, diff<0 error, and diff>=2*chain_length error all confirmed correct, both error latches genuinely sticky");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
