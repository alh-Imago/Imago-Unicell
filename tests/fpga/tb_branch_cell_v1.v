// tb_branch_cell_v1.v — points.md #500: sim-first verification of
// branch_cell_v1.v's own real protocol logic BEFORE any real Quartus
// attempt. Exercises: held-reference two-phase capture (first arrival
// becomes the reference, never compared/offered itself), all three
// real outcomes (< relayed, = fixed-value, > genuinely SUPPRESSED),
// real fan-out (multiple directions firing from one outcome), and
// release-on-reprogram (the held reference is discarded, the next
// arrival becomes the new one).
`timescale 1ns / 1ps

module tb_branch_cell_v1;

    reg clk = 0;
    always #5 clk = ~clk;   // 100 MHz

    reg rst = 1;
    reg cfg_valid = 0;
    reg [63:0] cfg_data = 64'h0;

    reg  [31:0] data_in_n, data_in_s, data_in_e, data_in_w;
    reg          arrived_n, arrived_s, arrived_e, arrived_w;
    wire [31:0] data_out_n, data_out_s, data_out_e, data_out_w;
    wire         fire_n, fire_s, fire_e, fire_w;
    wire         ready_out;
    reg          ready_in_n = 1, ready_in_s = 1, ready_in_e = 1, ready_in_w = 1;
    wire         ack_out_n, ack_out_s, ack_out_e, ack_out_w;
    reg          ack_in_n = 0, ack_in_s = 0, ack_in_e = 0, ack_in_w = 0;
    reg          freeze_in = 0;
    wire         status_data_valid;

    branch_cell_v1 DUT (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(arrived_e), .arrived_w(arrived_w),
        .data_out_n(data_out_n), .data_out_s(data_out_s), .data_out_e(data_out_e), .data_out_w(data_out_w),
        .fire_n(fire_n), .fire_s(fire_s), .fire_e(fire_e), .fire_w(fire_w),
        .ready_out(ready_out),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(ack_out_n), .ack_out_s(ack_out_s), .ack_out_e(ack_out_e), .ack_out_w(ack_out_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_in),
        .status_data_valid(status_data_valid)
    );

    integer errors = 0;

    // ── Real direction one-hot convention, matching compare_cell_v1.v
    // exactly: bit0=N bit1=S bit2=E bit3=W. ──
    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

    task program_cell;
        input [1:0] upstream_dir;
        input value_source_low, value_source_equal, value_source_high;
        input [6:0] fixed_value_low, fixed_value_equal, fixed_value_high;
        input emit_low, emit_equal, emit_high;
        input [3:0] route_low, route_equal, route_high;
        input rolling_mode;
        begin
            cfg_data = {22'h0, rolling_mode,
                        route_high, route_equal, route_low,
                        emit_high, emit_equal, emit_low,
                        fixed_value_high, fixed_value_equal, fixed_value_low,
                        value_source_high, value_source_equal, value_source_low,
                        upstream_dir};
            cfg_valid = 1;
            @(posedge clk);
            // ── Real fix for a real race, found not assumed: clearing
            // cfg_valid immediately after @(posedge clk) with a plain
            // blocking assignment races against the DUT's OWN same-edge
            // sampling (both are posedge-triggered processes; same-
            // delta-cycle statement ordering across separate always/
            // initial blocks is simulator-scheduling-dependent, not
            // guaranteed). The #1 here ensures the DUT's own NBA-based
            // register load has genuinely completed before cfg_valid
            // changes -- the standard, safe idiom for this exact class
            // of race. ──
            #1;
            cfg_valid = 0;
            @(posedge clk);
        end
    endtask

    task send_n;
        input [31:0] value;
        begin
            data_in_n = value;
            arrived_n = 1;
            #1;   // let ack_out_n settle combinationally BEFORE the capturing edge
            if (!ack_out_n) begin
                $display("FAIL: expected ack_out_n after sending %0d", value);
                errors = errors + 1;
            end
            @(posedge clk);   // the actual capture happens on this edge
            arrived_n = 0;
            @(posedge clk);
        end
    endtask

    initial begin
        // ── Reset ──
        @(posedge clk); @(posedge clk);
        rst = 0;
        @(posedge clk);

        // ── Program: LOW=relay->E, EQUAL=fixed(42)->S, HIGH=SUPPRESSED ──
        program_cell(2'd0,           // upstream_dir = N
                     1'b0, 1'b1, 1'b0,          // value_source: low=relay, equal=fixed, high=relay(unused, suppressed)
                     7'd0, 7'd42, 7'd0,         // fixed values
                     1'b1, 1'b1, 1'b0,          // emit: low=1, equal=1, high=0 (suppressed)
                     DIR_E, DIR_S, DIR_W,       // routes
                     1'b0);                     // rolling_mode = 0 (static)


        // ── Test 1: first arrival becomes the held reference, no offer ──
        send_n(32'd100);
        if (status_data_valid) begin
            $display("FAIL: reference capture should NOT produce an offer");
            errors = errors + 1;
        end else begin
            $display("PASS: first arrival (100) held as reference, no offer produced");
        end

        // ── Test 2: LOW outcome (50 < 100) -- relay real value, route E ──
        send_n(32'd50);
        @(posedge clk); #1;   // one real extra cycle: capture registers data_valid, THEN the generic offer pass registers pending_ack -- same two-stage latency every core in this project already has
        if (fire_e && data_out_e == 32'd50 && !fire_n && !fire_s && !fire_w) begin
            $display("PASS: LOW outcome (50 < 100) relayed real value 50 on E only");
        end else begin
            $display("FAIL: LOW outcome wrong -- fire_e=%b data_out_e=%0d fire_n=%b fire_s=%b fire_w=%b",
                      fire_e, data_out_e, fire_n, fire_s, fire_w);
            errors = errors + 1;
        end
        ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0; @(posedge clk);
        if (fire_e) begin
            $display("FAIL: fire_e should clear after ack_in_e");
            errors = errors + 1;
        end

        // ── Test 3: EQUAL outcome (100 == 100) -- fixed value 42, route S ──
        send_n(32'd100);
        @(posedge clk); #1;
        if (fire_s && data_out_s == 32'd42 && !fire_n && !fire_e && !fire_w) begin
            $display("PASS: EQUAL outcome (100 == 100) emitted fixed value 42 on S only");
        end else begin
            $display("FAIL: EQUAL outcome wrong -- fire_s=%b data_out_s=%0d", fire_s, data_out_s);
            errors = errors + 1;
        end
        ack_in_s = 1; @(posedge clk); #1; ack_in_s = 0; @(posedge clk);

        // ── Test 4: HIGH outcome (200 > 100) -- genuinely SUPPRESSED ──
        send_n(32'd200);
        @(posedge clk); #1;
        if (!fire_n && !fire_s && !fire_e && !fire_w && !status_data_valid) begin
            $display("PASS: HIGH outcome (200 > 100) genuinely suppressed -- no fire on any direction");
        end else begin
            $display("FAIL: HIGH outcome should be suppressed -- fire_n=%b fire_s=%b fire_e=%b fire_w=%b",
                      fire_n, fire_s, fire_e, fire_w);
            errors = errors + 1;
        end
        // ── Real, important check: ready_out should come back immediately
        // after a suppressed outcome -- nothing was left pending. ──
        if (ready_out) begin
            $display("PASS: ready_out correctly high again immediately after suppression (nothing pending)");
        end else begin
            $display("FAIL: ready_out should be high after a suppressed (non-emitting) outcome");
            errors = errors + 1;
        end

        // ── Test 5: release on reprogram -- next arrival becomes the NEW reference ──
        program_cell(2'd0,
                     1'b0, 1'b0, 1'b0,
                     7'd0, 7'd0, 7'd0,
                     1'b1, 1'b1, 1'b1,
                     DIR_E, DIR_E, DIR_E,
                     1'b0);
        send_n(32'd5);   // this should become the NEW reference, not be compared against 100
        if (status_data_valid) begin
            $display("FAIL: reprogram should have released the old reference -- this arrival should become the new one, not be compared");
            errors = errors + 1;
        end else begin
            $display("PASS: reprogram correctly released the old reference -- next arrival became the new reference");
        end
        send_n(32'd5);   // now compare against the new reference (5 == 5)
        @(posedge clk); #1;
        if (fire_e && data_out_e == 32'd5) begin
            $display("PASS: post-release comparison correct against the NEW reference (5 == 5)");
        end else begin
            $display("FAIL: post-release comparison wrong -- fire_e=%b data_out_e=%0d", fire_e, data_out_e);
            errors = errors + 1;
        end
        ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0; @(posedge clk);

        // ── Test 6: real fan-out -- one outcome firing on MULTIPLE directions at once ──
        program_cell(2'd0,
                     1'b0, 1'b0, 1'b0,
                     7'd0, 7'd0, 7'd0,
                     1'b1, 1'b1, 1'b1,
                     (DIR_E | DIR_S), DIR_N, DIR_W,   // LOW fans out to E AND S
                     1'b0);
        send_n(32'd50);    // reference = 50
        send_n(32'd10);    // 10 < 50 -> LOW -> fan out to E and S both
        @(posedge clk); #1;
        if (fire_e && fire_s && !fire_n && !fire_w &&
            data_out_e == 32'd10 && data_out_s == 32'd10) begin
            $display("PASS: real fan-out confirmed -- LOW outcome fired on BOTH E and S simultaneously");
        end else begin
            $display("FAIL: fan-out wrong -- fire_e=%b fire_s=%b fire_n=%b fire_w=%b",
                      fire_e, fire_s, fire_n, fire_w);
            errors = errors + 1;
        end
        // Only fully clears once BOTH real acks arrive.
        ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0; @(posedge clk);
        if (!fire_s) begin
            $display("FAIL: fire_s should still be held -- only E was acked so far");
            errors = errors + 1;
        end else begin
            $display("PASS: fan-out correctly still held on S after only E acked");
        end
        ack_in_s = 1; @(posedge clk); #1; ack_in_s = 0; @(posedge clk);
        if (fire_e || fire_s) begin
            $display("FAIL: both fires should be clear now that both directions acked");
            errors = errors + 1;
        end else begin
            $display("PASS: fan-out fully drained once both real acks arrived");
        end

        // ── Test 7: ROLLING MODE -- real, continuous change detection
        // against whatever arrived LAST, not a fixed baseline. LOW/
        // HIGH both relay+emit; EQUAL suppressed (won't be hit here). ──
        program_cell(2'd0,
                     1'b0, 1'b0, 1'b0,
                     7'd0, 7'd0, 7'd0,
                     1'b1, 1'b0, 1'b1,
                     DIR_E, DIR_S, DIR_W,
                     1'b1);                     // rolling_mode = 1
        send_n(32'd100);   // seeds the reference (100), no compare -- same as static mode's first arrival
        if (status_data_valid) begin
            $display("FAIL: rolling mode's first arrival should still just seed the reference, not compare");
            errors = errors + 1;
        end

        send_n(32'd90);    // 90 < 100 -> LOW -> fire on E; reference becomes 90 (not still 100)
        @(posedge clk); #1;
        if (fire_e && data_out_e == 32'd90 && DUT.ref_value == 32'd90) begin
            $display("PASS: rolling mode -- 90 < 100 fired LOW correctly, AND reference rolled to 90");
        end else begin
            $display("FAIL: rolling step 1 wrong -- fire_e=%b data_out_e=%0d ref_value=%0d",
                      fire_e, data_out_e, DUT.ref_value);
            errors = errors + 1;
        end
        ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0; @(posedge clk);

        // The real point: 95 is HIGHER than the CURRENT reference (90),
        // even though it's LOWER than the ORIGINAL reference (100) --
        // proving this is genuine rolling comparison, not a fixed
        // baseline silently retained underneath.
        send_n(32'd95);    // 95 > 90 (current ref) -> HIGH -> fire on W; reference rolls to 95
        @(posedge clk); #1;
        if (fire_w && data_out_w == 32'd95 && !fire_e && DUT.ref_value == 32'd95) begin
            $display("PASS: rolling mode -- 95 > 90 (the CURRENT reference) correctly fired HIGH, not LOW against the stale original 100 -- reference rolled to 95");
        end else begin
            $display("FAIL: rolling step 2 wrong (this is the real test of rolling vs static) -- fire_e=%b fire_w=%b data_out_w=%0d ref_value=%0d",
                      fire_e, fire_w, data_out_w, DUT.ref_value);
            errors = errors + 1;
        end
        ack_in_w = 1; @(posedge clk); #1; ack_in_w = 0; @(posedge clk);

        if (errors == 0) begin
            $display("PASS: branch_cell_v1 -- held-reference capture, all three real outcomes (relay/fixed/suppress), release-on-reprogram, and real fan-out all confirmed correct");
        end else begin
            $display("FAIL: %0d error(s)", errors);
        end
        $finish;
    end

endmodule
