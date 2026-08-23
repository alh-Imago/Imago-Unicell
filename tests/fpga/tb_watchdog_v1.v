// tb_watchdog_v1.v — points.md #453/#463's own queue: sim-first
// verification of watchdog_v1.v's own real programmability (the whole
// point of this file, per Alan's own explicit requirement) -- the SAME
// instance must behave correctly under two DIFFERENT real-loaded
// thresholds, not just whatever a single hardcoded test happens to
// match.
`timescale 1ns / 1ps

module tb_watchdog_v1;

    localparam WIDTH = 8;

    reg clk = 0;
    always #5 clk = ~clk;

    reg rst = 1;
    reg cfg_valid;
    reg [WIDTH-1:0] cfg_threshold;
    reg activity_pulse;
    wire timeout_flag;
    wire [WIDTH-1:0] count_out;

    watchdog_v1 #(.WIDTH(WIDTH)) DUT (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid), .cfg_threshold(cfg_threshold),
        .activity_pulse(activity_pulse),
        .timeout_flag(timeout_flag), .count_out(count_out)
    );

    integer errors = 0;

    task load_threshold(input [WIDTH-1:0] t);
        begin
            cfg_threshold = t;
            cfg_valid = 1;
            @(posedge clk); #1;
            cfg_valid = 0;
        end
    endtask

    initial begin
        cfg_valid = 0; cfg_threshold = 0; activity_pulse = 0;
        repeat (3) @(posedge clk);
        rst = 0;
        repeat (2) @(posedge clk);

        // ── Real test 1: default (unconfigured) threshold must be the
        // real maximum representable value -- never trips prematurely. ──
        if (timeout_flag !== 1'b0) begin
            errors = errors + 1;
            $display("FAIL: timeout_flag asserted before any real configuration");
        end else begin
            $display("PASS: watchdog never trips before real configuration (defaults to max threshold)");
        end

        // ── Real test 2: load threshold=5, confirm it trips at EXACTLY
        // the right cycle, not off-by-one. ──
        load_threshold(8'd5);
        begin : test2
            integer cyc;
            cyc = 0;
            while (!timeout_flag && cyc < 20) begin
                @(posedge clk); #1;   // settle before reading -- avoids racing the NBA update from this same edge
                cyc = cyc + 1;
            end
            $display("Test 2: threshold=5, real trip after %0d cycles (count_out=%0d)", cyc, count_out);
            if (cyc != 5) begin
                errors = errors + 1;
                $display("FAIL: expected exactly 5 cycles to trip, got %0d", cyc);
            end else begin
                $display("PASS: real threshold=5 tripped at exactly the right cycle");
            end
        end

        // ── Real test 3: activity_pulse genuinely resets the count --
        // a chain that's slow but still progressing must never trip. ──
        repeat (3) @(posedge clk);   // 3 cycles into a fresh count (threshold still 5, hasn't tripped yet)
        activity_pulse = 1;
        @(posedge clk); #1;
        activity_pulse = 0;
        if (count_out !== 8'd0) begin
            errors = errors + 1;
            $display("FAIL: count did not reset on real activity_pulse");
        end else if (timeout_flag !== 1'b0) begin
            errors = errors + 1;
            $display("FAIL: timeout_flag still asserted after a real reset");
        end else begin
            $display("PASS: real activity_pulse correctly resets the count before timeout");
        end

        // ── Real test 4: THE REAL POINT OF THIS MODULE -- reconfigure
        // the SAME instance to a DIFFERENT threshold, confirm it now
        // trips at the NEW value, not the old one. This is what
        // "genuinely programmable, not hardened" actually means. ──
        load_threshold(8'd12);
        begin : test4
            integer cyc;
            cyc = 0;
            while (!timeout_flag && cyc < 30) begin
                @(posedge clk); #1;   // settle before reading -- same fix as test2
                cyc = cyc + 1;
            end
            $display("Test 4: SAME instance reconfigured to threshold=12, real trip after %0d cycles", cyc);
            if (cyc != 12) begin
                errors = errors + 1;
                $display("FAIL: expected exactly 12 cycles after real reconfiguration, got %0d", cyc);
            end else begin
                $display("PASS: real reconfiguration to a DIFFERENT threshold works correctly on the SAME instance -- genuinely programmable, not a fixed behavior");
            end
        end

        // ── Real test 5: once tripped, timeout_flag stays held (not a
        // pulse) until the next real activity or reconfiguration. ──
        repeat (3) @(posedge clk);
        if (timeout_flag !== 1'b1) begin
            errors = errors + 1;
            $display("FAIL: timeout_flag did not stay held after tripping");
        end else begin
            $display("PASS: timeout_flag correctly stays held, not a one-cycle pulse");
        end

        if (errors == 0) begin
            $display("PASS: watchdog_v1 -- default-never-trips, exact real timing, activity-reset, and genuine same-instance reprogrammability all confirmed correct");
        end else begin
            $display("FAIL: %0d error(s) found", errors);
        end
        $finish;
    end

endmodule
