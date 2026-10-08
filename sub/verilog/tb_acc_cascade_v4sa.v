`timescale 1ns/1ps
// Two pulse-mode accumulators in cascade (gear ratio): stage 1 counts input events and fires every T1;
// each stage-1 offer is stage 2's inc_pulse; stage 2 fires every T2 of those. So stage 2 fires once per
// T1*T2 input events -- a count a single accumulator cannot reach (its threshold field is 16 bits).
module tb_acc_cascade_v4sa;
    parameter T1 = 1000, T2 = 1000, W = 32;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg cv = 0; reg [31:0] cd = 0;
    reg inc_in = 0;
    wire a1_ack, a1_v, a2_ack, a2_v; wire [W-1:0] a1_d, a2_d;
    accumulator_cell_v4sa #(.WIDTH(W)) S1 (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cv), .cfg_data(cd),
        .inc_pulse(inc_in), .dec_pulse(1'b0), .ack_out(a1_ack), .data_out(a1_d), .valid_out(a1_v), .ack_in(1'b1));
    reg cv2 = 0; reg [31:0] cd2 = 0;
    accumulator_cell_v4sa #(.WIDTH(W)) S2 (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cv2), .cfg_data(cd2),
        .inc_pulse(a1_v), .dec_pulse(1'b0), .ack_out(a2_ack), .data_out(a2_d), .valid_out(a2_v), .ack_in(1'b1));
    integer events = 0, s1_hits = 0, s2_hits = 0, first2 = 0, second2 = 0, errors = 0;
    always @(posedge clk) if (!rst) begin
        if (inc_in) events <= events + 1;
        if (a1_v) s1_hits <= s1_hits + 1;
        if (a2_v) begin
            s2_hits <= s2_hits + 1;
            if (s2_hits == 0) first2 <= events; else if (s2_hits == 1) second2 <= events;
        end
    end
    initial begin
        @(posedge clk); @(posedge clk); rst = 0;
        cd  = (T1 << 9) | (1 << 8) | 1; cv  = 1;      // step 1, pulse mode, threshold T1
        cd2 = (T2 << 9) | (1 << 8) | 1; cv2 = 1; @(posedge clk); #1; cv = 0; cv2 = 0;
        inc_in = 1;
        repeat (2*T1*T2 + 2) @(posedge clk);
        inc_in = 0; repeat (10) @(posedge clk);
        if (s2_hits !== 2) begin errors = errors + 1; $display("FAIL: stage 2 fired %0d times, want 2", s2_hits); end
        if (s1_hits !== 2*T2) begin errors = errors + 1; $display("FAIL: stage 1 fired %0d, want %0d", s1_hits, 2*T2); end
        // events at the moment of each stage-2 offer: T1*T2 plus the fixed latency (a few cycles), same each time
        if ((second2 - first2) !== T1*T2) begin errors = errors + 1; $display("FAIL: period %0d, want %0d", second2 - first2, T1*T2); end
        if (first2 < T1*T2 || first2 > T1*T2 + 4) begin errors = errors + 1; $display("FAIL: first fire at event %0d, want ~%0d", first2, T1*T2); end
        if (errors == 0) $display("ALL PASS: period %0d input events = %0d x %0d (latency %0d cycles)", second2 - first2, T1, T2, first2 - T1*T2);
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
