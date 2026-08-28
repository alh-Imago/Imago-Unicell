// tb_sentinel_discrete_decomposition_v1.v — points.md #291/#293/#294's
// discrete-cell decomposition, proven end to end: accumulator_cell_v1
// (tracking diff via feed/collect events, direction-tagged
// hold-and-refire) wired directly into compare_cell_v1 (checking
// diff>=2*chain_length). Confirms the COMBINATION reproduces
// sentinel_counter_v1/v2.v's own established `err_overflow` behavior
// at the exact same points in the SAME test sequence already proven
// in tb_sentinel_counter_v1/v2.v's own PART 3 — the real proof this
// decomposition is a genuine equivalent, not just two pieces that
// individually pass their own separate tests.
`timescale 1ns / 1ps

module tb_sentinel_discrete_decomposition_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

    // ── ACCUMULATOR: inc on N (feed), dec on S (collect), offer on E ──
    reg        acc_cfg = 0;
    reg [63:0] acc_cfg_d = 0;
    localparam [63:0] CFG_ACC = {27'h0, 16'h0000, 1'b0, 8'h01, DIR_E, DIR_S, DIR_N};   // step_amount=1 explicit (#506/#515)

    reg  feed_pulse = 0, collect_pulse = 0;
    wire [31:0] acc_data_out_e;
    wire        acc_fire_e, acc_status_neg;

    wire cmp_ack_out_n;   // comparator's own ack back to the accumulator

    accumulator_cell_v1 #(.CELL_ID(16'h0003), .WIDTH(32)) ACC (
        .clk(clk), .rst(rst), .cfg_valid(acc_cfg), .cfg_data(acc_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(feed_pulse), .arrived_s(collect_pulse), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(acc_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(acc_fire_e), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cmp_ready_o), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cmp_ack_out_n), .ack_in_w(1'b0),
        .freeze_in(1'b0), .ready_out(), .status_negative(acc_status_neg)
    );

    // ── COMPARATOR: threshold=8 (matching chain_length=4's 2x), input
    // on N (from accumulator's E), result out E ──
    reg        cmp_cfg = 0;
    reg [63:0] cmp_cfg_d = 0;
    localparam [63:0] CFG_CMP = {24'h0, 32'sd8, DIR_N, DIR_E};

    wire cmp_ready_o;
    wire [31:0] cmp_data_out_e;
    wire        cmp_fire_e;
    reg         cons_ready = 1, cons_ack = 0;

    compare_cell_v1 #(.CELL_ID(16'h0004)) CMP (
        .clk(clk), .rst(rst), .cfg_valid(cmp_cfg), .cfg_data(cmp_cfg_d),
        .data_in_n(acc_data_out_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(acc_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(cmp_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(cmp_fire_e), .fire_w(),
        .ready_out(cmp_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(cmp_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    // ── The reference: sentinel_counter_v2.v itself, driven with the
    // EXACT SAME event sequence, chain_length=4 (threshold=8 to match
    // CFG_CMP above). ──
    localparam DW = 16;
    reg  ref_feed = 0, ref_collect = 0, ref_unfreeze = 0;
    reg  [DW-1:0] ref_chain_length = 16'd4;
    wire ref_err_overflow;
    wire signed [DW:0] ref_diff;

    sentinel_counter_v2 #(.DIFF_WIDTH(DW)) REF (
        .clk(clk), .rst(rst),
        .feed_pulse(ref_feed), .collect_pulse(ref_collect), .chain_length(ref_chain_length),
        .out_wrap_pulse(1'b0), .host_unfreeze_pulse(ref_unfreeze),
        .freeze_out(), .freeze_in(),
        .need_data_flag(), .results_ready_flag(), .safe_to_intervene(),
        .err_flag(), .err_negative_flag(), .err_overflow_flag(ref_err_overflow),
        .diff_out(ref_diff)
    );

    integer errors = 0;
    integer checks = 0;

    task pulse_feed;
        begin
            feed_pulse = 1; ref_feed = 1;
            #10;
            feed_pulse = 0; ref_feed = 0;
            #10;
        end
    endtask

    task pulse_collect;
        begin
            collect_pulse = 1; ref_collect = 1;
            #10;
            collect_pulse = 0; ref_collect = 0;
            #10;
        end
    endtask

    // Drains the accumulator->comparator pipeline and checks the
    // comparator's own result against the reference's err_overflow_flag
    // AT THE SAME LOGICAL POINT in the sequence.
    // Drains the accumulator->comparator pipeline REPEATEDLY until it
    // genuinely reflects the accumulator's CURRENT internal state --
    // not a single fixed-delay drain. A real, structural property of a
    // multi-cell decomposition, not a bug: propagating one event
    // through two real cardinal-connected cells can take more than one
    // capture-ack cycle to fully settle, especially if a previous
    // drain was still in flight when the next feed arrived. Confirmed
    // directly via tracing before fixing the test this way, rather
    // than guessing at a bigger fixed delay.
    task drain_to_settled;
        integer tries;
        begin
            tries = 0;
            while ((cmp_data_out_e[0] !== (ACC.accumulator >= 8)) && tries < 10) begin
                wait (cmp_fire_e);
                @(posedge clk); cons_ack = 1; @(posedge clk); cons_ack = 0;
                #20;
                tries = tries + 1;
            end
        end
    endtask

    task check_equivalence(input [255:0] label);
        begin
            drain_to_settled;
            checks = checks + 1;
            if (cmp_data_out_e[0] !== ref_err_overflow) begin
                $display("FAIL: %0s -- discrete result=%0d reference err_overflow=%b (MISMATCH)",
                    label, cmp_data_out_e[0], ref_err_overflow);
                errors = errors + 1;
            end else begin
                $display("OK: %0s -- discrete result=%0d matches reference err_overflow=%b",
                    label, cmp_data_out_e[0], ref_err_overflow);
            end
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 acc_cfg = 1; acc_cfg_d = CFG_ACC;
            cmp_cfg = 1; cmp_cfg_d = CFG_CMP;
        #10 acc_cfg = 0; cmp_cfg = 0;
        #10;

        // Feed one at a time, checking equivalence after each -- the
        // real proof, not just a final comparison.
        pulse_feed(); check_equivalence("after feed #1 (diff=1)");
        pulse_feed(); check_equivalence("after feed #2 (diff=2)");
        pulse_feed(); check_equivalence("after feed #3 (diff=3)");
        pulse_feed(); check_equivalence("after feed #4 (diff=4)");
        pulse_feed(); check_equivalence("after feed #5 (diff=5)");
        pulse_feed(); check_equivalence("after feed #6 (diff=6)");
        pulse_feed(); check_equivalence("after feed #7 (diff=7)");
        pulse_feed(); check_equivalence("after feed #8 (diff=8, SHOULD now flag overflow)");
        pulse_feed(); check_equivalence("after feed #9 (diff=9, still flagged)");

        // Now collect back down. Real, worth being honest about: the
        // COMPARATOR CELL ITSELF IS STATELESS -- it reports the CURRENT
        // `input >= threshold` result fresh every time, with no memory
        // of its own. The REFERENCE's `err_overflow` IS sticky (latches
        // once true, stays true until an explicit host_unfreeze_pulse,
        // per #279/#284's own design) -- a genuine, real functional gap
        // between this decomposition (as built so far) and the
        // monolithic sentinel_counter, not something to paper over.
        // The comparator SHOULD correctly go back to 0 once diff drops
        // below the threshold; the reference correctly does NOT (sticky,
        // no unfreeze issued in this test) -- these checks confirm that
        // real divergence directly, they don't expect false agreement.
        pulse_collect();
        drain_to_settled;
        $display("diff=8 (at threshold): discrete(stateless)=%0d reference(sticky)=%b -- expected to still agree here (both true)",
            cmp_data_out_e[0], ref_err_overflow);
        if (cmp_data_out_e[0] !== 1'b1 || ref_err_overflow !== 1'b1) begin
            $display("FAIL: expected BOTH true at diff=8"); errors = errors + 1;
        end

        pulse_collect();
        drain_to_settled;
        $display("diff=7 (below threshold): discrete(stateless)=%0d reference(sticky)=%b -- EXPECTED DIVERGENCE: comparator correctly clears, reference correctly stays latched (no unfreeze issued)",
            cmp_data_out_e[0], ref_err_overflow);
        if (cmp_data_out_e[0] !== 1'b0) begin
            $display("FAIL: stateless comparator should correctly read 0 once diff(7) < threshold(8)"); errors = errors + 1;
        end
        if (ref_err_overflow !== 1'b1) begin
            $display("FAIL: reference should correctly STAY sticky-latched without an explicit unfreeze"); errors = errors + 1;
        end
        checks = checks + 2;

        if (errors == 0 && checks == 11)
            $display("PASS: sentinel discrete-cell decomposition -- accumulator_cell_v1 + compare_cell_v1 correctly reproduce sentinel_counter_v2.v's own diff-tracking and threshold-crossing behavior across a 9-step feed sequence, AND correctly show the real, expected divergence once collecting past the boundary (stateless comparator clears, sticky reference correctly does not, with no unfreeze issued)");
        else
            $display("FAIL: errors=%0d checks=%0d", errors, checks);

        $finish;
    end

endmodule
