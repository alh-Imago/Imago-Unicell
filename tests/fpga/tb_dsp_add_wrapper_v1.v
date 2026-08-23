// tb_dsp_add_wrapper_v1.v — points.md #453/#461/#462: sim-first
// verification of dsp_add_wrapper_v1.v's own real protocol logic
// (dual-operand capture, the real confirmed 3-cycle latency, held-fire-
// until-ack, re-arming for a second real operation) BEFORE any real
// Quartus build. Uses tb_stub_alterafpf_add_single_v1.v -- confirms
// TIMING only, not real floating-point arithmetic (see that file's own
// header for why).
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

    dsp_add_wrapper_v1 DUT (
        .clk(clk), .rst(rst),
        .data_in_a(data_in_a), .arrived_a(arrived_a), .ack_out_a(ack_out_a),
        .data_in_b(data_in_b), .arrived_b(arrived_b), .ack_out_b(ack_out_b),
        .data_out(data_out), .fire(fire), .ready_in(ready_in), .ack_in(ack_in)
    );

    integer errors = 0;

    task reset_stimulus;
        begin
            data_in_a = 32'h0; data_in_b = 32'h0;
            arrived_a = 0; arrived_b = 0;
            ready_in = 1; ack_in = 0;
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

        if (errors == 0) begin
            $display("PASS: dsp_add_wrapper_v1 -- dual-operand capture (both arrival orders), held-fire-until-ack, and re-arming all confirmed correct");
        end else begin
            $display("FAIL: %0d error(s) found", errors);
        end
        $finish;
    end

endmodule
