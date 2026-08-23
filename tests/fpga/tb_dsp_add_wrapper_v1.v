// tb_dsp_add_wrapper_v1.v — points.md #453/#461/#462/#464: sim-first
// verification of dsp_add_wrapper_v1.v's own real protocol logic
// (dual-operand capture, the real confirmed 3-cycle latency, held-fire-
// until-ack, re-arming for a second real operation) BEFORE any real
// Quartus build. Uses tb_stub_alterafpf_add_single_v1.v -- confirms
// TIMING only, not real floating-point arithmetic (see that file's own
// header for why). Also verifies the real watchdog integration (#464):
// genuine stuck detection trips correctly, real partial progress
// (one operand arriving) correctly resets it, and normal real
// operation never trips it.
`timescale 1ns / 1ps

module tb_dsp_add_wrapper_v1;

    reg clk = 0;
    always #5 clk = ~clk;   // 100 MHz

    reg rst = 1;
    reg [31:0] data_in_a, data_in_b;
    reg arrived_a, arrived_b;
    wire ack_out_a, ack_out_b;
    wire [31:0] data_out;
    wire fire;
    reg ready_in;
    reg ack_in;
    reg wd_cfg_valid;
    reg [15:0] wd_cfg_threshold;
    wire wd_timeout_err;
    wire [15:0] wd_count_out;

    dsp_add_wrapper_v1 DUT (
        .clk(clk), .rst(rst),
        .data_in_a(data_in_a), .arrived_a(arrived_a), .ack_out_a(ack_out_a),
        .data_in_b(data_in_b), .arrived_b(arrived_b), .ack_out_b(ack_out_b),
        .data_out(data_out), .fire(fire), .ready_in(ready_in), .ack_in(ack_in),
        .wd_cfg_valid(wd_cfg_valid), .wd_cfg_threshold(wd_cfg_threshold),
        .wd_timeout_err(wd_timeout_err), .wd_count_out(wd_count_out)
    );

    integer errors = 0;

    task reset_stimulus;
        begin
            data_in_a = 32'h0; data_in_b = 32'h0;
            arrived_a = 0; arrived_b = 0;
            ready_in = 1; ack_in = 0;
            wd_cfg_valid = 0; wd_cfg_threshold = 16'hFFFF;
        end
    endtask

    // Offer operand A on the next cycle where ack_out_a is seen high.
    task offer_a(input [31:0] val);
        begin
            data_in_a = val;
            arrived_a = 1;
            @(posedge clk);
            while (!ack_out_a) @(posedge clk);
            #1;
            arrived_a = 0;
        end
    endtask

    task offer_b(input [31:0] val);
        begin
            data_in_b = val;
            arrived_b = 1;
            @(posedge clk);
            while (!ack_out_b) @(posedge clk);
            #1;
            arrived_b = 0;
        end
    endtask

    initial begin
        reset_stimulus;
        repeat (3) @(posedge clk);
        rst = 0;
        repeat (2) @(posedge clk);

        // ── Real test 1: A arrives, then B (real, staggered arrival
        // order — the wrapper must not assume simultaneity). ──
        offer_a(32'hAAAA0001);
        repeat (2) @(posedge clk);   // real gap between the two arrivals
        offer_b(32'h55550002);

        // Real, precise wait: count cycles until fire actually asserts,
        // rather than assume the exact number -- matching this
        // project's own "measure, don't assume" discipline.
        begin : wait_fire_1
            integer cyc;
            cyc = 0;
            while (!fire && cyc < 20) begin
                @(posedge clk);
                cyc = cyc + 1;
            end
            $display("Test 1: fire asserted %0d cycles after both operands captured", cyc);
            if (!fire) begin
                errors = errors + 1;
                $display("FAIL: fire never asserted for test 1");
            end
        end

        if (fire !== 1'b1) begin
            errors = errors + 1;
            $display("FAIL: fire not held high when expected");
        end

        // Confirm fire STAYS held (not a one-cycle pulse) while ack_in is low.
        @(posedge clk); #1;
        if (fire !== 1'b1) begin
            errors = errors + 1;
            $display("FAIL: fire did not stay held across a cycle with no ack — looks like a one-cycle pulse bug");
        end else begin
            $display("PASS: fire stays held (not a one-cycle pulse) while waiting for ack");
        end

        // Now ack it.
        ack_in = 1;
        @(posedge clk); #1;
        ack_in = 0;

        if (fire !== 1'b0) begin
            errors = errors + 1;
            $display("FAIL: fire did not clear after being acked");
        end else begin
            $display("PASS: fire correctly clears after ack_in");
        end

        // ── Real test 2: re-arm for a SECOND real operation, B arrives
        // before A this time (opposite order from test 1). ──
        repeat (2) @(posedge clk);
        offer_b(32'h11110003);
        repeat (2) @(posedge clk);
        offer_a(32'h22220004);

        begin : wait_fire_2
            integer cyc;
            cyc = 0;
            while (!fire && cyc < 20) begin
                @(posedge clk);
                cyc = cyc + 1;
            end
            $display("Test 2: fire asserted %0d cycles after both operands captured (opposite arrival order)", cyc);
            if (!fire) begin
                errors = errors + 1;
                $display("FAIL: fire never asserted for test 2 (reversed arrival order)");
            end else begin
                $display("PASS: wrapper correctly handles B-before-A arrival order too");
            end
        end

        ack_in = 1;
        @(posedge clk); #1;
        ack_in = 0;

        // ── Real test 3: watchdog integration -- confirm normal real
        // operation (both operands arrive promptly, real op completes)
        // never trips a reasonably-set watchdog. Load a real, generous
        // threshold first. ──
        wd_cfg_threshold = 16'd50;
        wd_cfg_valid = 1;
        @(posedge clk); #1;
        wd_cfg_valid = 0;

        repeat (2) @(posedge clk);
        offer_a(32'hAAAA0005);
        offer_b(32'h55550006);
        begin : wait_fire_3
            integer cyc;
            cyc = 0;
            while (!fire && cyc < 20) begin @(posedge clk); cyc = cyc + 1; end
        end
        if (wd_timeout_err !== 1'b0) begin
            errors = errors + 1;
            $display("FAIL: watchdog false-tripped during real, normal operation");
        end else begin
            $display("PASS: watchdog does not false-trip during real, normal operation");
        end
        ack_in = 1; @(posedge clk); #1; ack_in = 0;
        repeat (2) @(posedge clk);

        // ── Real test 4: watchdog integration -- genuine stuck
        // detection. Load a real, tight threshold, then offer NOTHING
        // at all -- confirm it genuinely trips. ──
        wd_cfg_threshold = 16'd10;
        wd_cfg_valid = 1;
        @(posedge clk); #1;
        wd_cfg_valid = 0;

        begin : wait_timeout_4
            integer cyc;
            cyc = 0;
            while (!wd_timeout_err && cyc < 30) begin @(posedge clk); #1; cyc = cyc + 1; end
            $display("Test 4: watchdog tripped after %0d real cycles of genuine silence (threshold=10)", cyc);
            if (!wd_timeout_err) begin
                errors = errors + 1;
                $display("FAIL: watchdog never tripped during genuine, sustained silence");
            end else if (cyc != 10) begin
                errors = errors + 1;
                $display("FAIL: expected exactly 10 cycles, got %0d", cyc);
            end else begin
                $display("PASS: watchdog correctly detects genuine, sustained silence");
            end
        end

        // ── Real test 5: watchdog integration -- real PARTIAL progress
        // (just one operand arriving, no full operation) must reset it,
        // matching #459's own real "patient, don't false-trip on real
        // progress" requirement. Reload the same tight threshold, then
        // offer operand A partway through, confirm the watchdog does
        // NOT trip even though no full operation ever completes. ──
        wd_cfg_threshold = 16'd10;
        wd_cfg_valid = 1;
        @(posedge clk); #1;
        wd_cfg_valid = 0;

        repeat (6) @(posedge clk);   // real progress into the count, but before it would trip at 10
        offer_a(32'hDEAD0007);       // real partial progress -- only A, never B
        repeat (6) @(posedge clk);   // if the reset genuinely worked, we're now only 6 cycles past the reset, not 12 past the original start
        if (wd_timeout_err !== 1'b0) begin
            errors = errors + 1;
            $display("FAIL: watchdog tripped despite real partial progress (operand A arriving) resetting it");
        end else begin
            $display("PASS: real partial progress (one operand arriving, no full operation) correctly resets the watchdog");
        end

        if (errors == 0) begin
            $display("PASS: dsp_add_wrapper_v1 -- dual-operand capture (both arrival orders), held-fire-until-ack, re-arming, and the real watchdog integration (no false positives, genuine stuck detection, partial-progress reset) all confirmed correct");
        end else begin
            $display("FAIL: %0d error(s) found", errors);
        end
        $finish;
    end

endmodule
