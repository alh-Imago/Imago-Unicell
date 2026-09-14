// tb_cascade_counter_v1.v — points.md #506/#516: the cascade/carry
// counter, the first of #506's own three real composed applications to
// actually be built and proven. ZERO new RTL — per #509's own
// decomposition method ("does an existing cell already accomplish
// this?"), this is nothing but three accumulator_cell_v1 instances
// (real, already-built, #515's pulse_mode) wired stage-to-stage using
// the SAME direct fire->arrived / ack_out->ack_in pattern
// tb_sentinel_discrete_full_v1.v already proved between different
// core types — here proving it works cell-to-cell between three
// instances of the SAME core type instead.
//
// THE REAL SHAPE: accumulator A counts external pulses, pulse_mode=1,
// threshold=10 (its own "digit base"). Each real crossing fires ONE
// pulse downstream to accumulator B and hard-resets A's own internal
// total to 0 (#515's own real reset-after-fire mechanism) — so A's
// internal accumulator IS the live ones-digit (0-9), continuously
// correct regardless of whether its own downstream fire has been
// acked yet (confirmed directly in #515's own RTL: the internal total
// update is unconditional, never gated by pending_ack). B does the
// identical thing one level up (the tens digit), C one level up again
// (the hundreds digit) — a genuine ripple/cascade counter, one stage
// per digit, matching #506's own real description exactly.
//
// WHAT THIS PROVES, honestly scoped: the CARRY PROPAGATION mechanism
// itself — that real crossings genuinely ripple stage to stage, with
// zero pulses lost or double-counted, across enough total pulses to
// exercise ones/tens/hundreds all at once (237 real external pulses).
// What this deliberately does NOT build: a real downstream-readable
// "current digit" output for actual hardware consumption — every
// stage's own live digit is read here via direct internal signal
// access (`STAGE_A.accumulator` etc.), the same introspection
// convention every other testbench in this project already uses, NOT
// a real wired readout path. #506's own real recombiner-pattern
// connection (shift each stage's digit into position, add — #497)
// remains genuinely separate, unbuilt future work for whenever a real
// hardware-readable multi-digit total is actually needed.
`timescale 1ns / 1ps

module tb_cascade_counter_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

    // Real field layout, per #515: {threshold(16), pulse_mode(1),
    // step_amount(8), downstream_mask(4), dec_dir(4), inc_dir(4)}.
    // Every stage: inc on N (from whichever pulse feeds it), pulse
    // mode on, threshold=10 (base-10 digit), offer the carry on E.
    localparam [63:0] CFG_STAGE =
        {27'h0, 16'd10, 1'b1, 8'h01, DIR_E, 4'h0, DIR_N};

    reg feed_pulse = 0;

    // ── Stage A — ones digit ──
    reg        a_cfg = 0;
    reg [63:0] a_cfg_d = 0;
    wire [31:0] a_dout_e;
    wire        a_fire_e, a_ack_out_n;

    accumulator_cell_v1 #(.CELL_ID(16'h0010), .WIDTH(32)) STAGE_A (
        .clk(clk), .rst(rst), .cfg_valid(a_cfg), .cfg_data(a_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(feed_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(a_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(a_fire_e), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(a_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(b_ack_out_n), .ack_in_w(1'b0),
        .freeze_in(1'b0), .ready_out(), .status_negative()
    );

    // ── Stage B — tens digit, fed directly by stage A's own carry ──
    reg        b_cfg = 0;
    reg [63:0] b_cfg_d = 0;
    wire [31:0] b_dout_e;
    wire        b_fire_e, b_ack_out_n;

    accumulator_cell_v1 #(.CELL_ID(16'h0011), .WIDTH(32)) STAGE_B (
        .clk(clk), .rst(rst), .cfg_valid(b_cfg), .cfg_data(b_cfg_d),
        .data_in_n(a_dout_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(a_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(b_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(b_fire_e), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(b_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(c_ack_out_n), .ack_in_w(1'b0),
        .freeze_in(1'b0), .ready_out(), .status_negative()
    );

    // ── Stage C — hundreds digit, fed directly by stage B's own carry ──
    reg        c_cfg = 0;
    reg [63:0] c_cfg_d = 0;
    wire [31:0] c_dout_e;
    wire        c_fire_e, c_ack_out_n;

    accumulator_cell_v1 #(.CELL_ID(16'h0012), .WIDTH(32)) STAGE_C (
        .clk(clk), .rst(rst), .cfg_valid(c_cfg), .cfg_data(c_cfg_d),
        .data_in_n(b_dout_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(b_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(c_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(c_fire_e), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(c_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b1), .ack_in_w(1'b0),
        // C is the end of the chain -- ack_in_e tied high (an always-
        // ready sink). Not load-bearing for correctness either way,
        // since #515's own RTL makes the internal total update
        // unconditional on pending_ack -- tied here only so C's own
        // pending_ack doesn't latch stuck-nonzero across the run.
        .freeze_in(1'b0), .ready_out(), .status_negative()
    );

    integer errors = 0;
    integer i;

    task pulse_feed;
        begin feed_pulse = 1; #10; feed_pulse = 0; #10; end
    endtask

    task check_digit(input [255:0] label, input integer expected, input integer actual);
        begin
            if (actual !== expected) begin
                $display("FAIL: %0s -- expected %0d, got %0d", label, expected, actual);
                errors = errors + 1;
            end else $display("OK: %0s -- correctly %0d", label, actual);
        end
    endtask

    initial begin
        #12 rst = 0;
        #10;
        a_cfg = 1; a_cfg_d = CFG_STAGE;
        b_cfg = 1; b_cfg_d = CFG_STAGE;
        c_cfg = 1; c_cfg_d = CFG_STAGE;
        #10;
        a_cfg = 0; b_cfg = 0; c_cfg = 0;
        #10;

        // ── PART 1: 9 pulses -- below the first carry. Real claim:
        // stage A alone should hold 9, B and C untouched at 0. ──
        for (i = 0; i < 9; i = i + 1) pulse_feed();
        #20;
        check_digit("9 pulses -- stage A (ones)",     9, STAGE_A.accumulator);
        check_digit("9 pulses -- stage B (tens)",      0, STAGE_B.accumulator);
        check_digit("9 pulses -- stage C (hundreds)",  0, STAGE_C.accumulator);

        // ── PART 2: the 10th pulse -- the real carry event. Stage A
        // must reset to 0 (not 10), stage B must show its first real
        // carry (1), proving the ripple actually happened, not just
        // stage A silently capping. ──
        pulse_feed();
        #20;
        check_digit("10th pulse -- stage A resets to 0", 0, STAGE_A.accumulator);
        check_digit("10th pulse -- stage B's first real carry", 1, STAGE_B.accumulator);
        check_digit("10th pulse -- stage C still untouched",    0, STAGE_C.accumulator);

        // ── PART 3: drive to 237 total pulses (227 more from here) --
        // a genuine three-digit real test, exercising all three stages
        // at once. Real expected decomposition: 237 = 2 hundreds, 3
        // tens, 7 ones. ──
        for (i = 0; i < 227; i = i + 1) pulse_feed();
        #20;
        check_digit("237 total pulses -- stage A (ones digit)",      7, STAGE_A.accumulator);
        check_digit("237 total pulses -- stage B (tens digit)",      3, STAGE_B.accumulator);
        check_digit("237 total pulses -- stage C (hundreds digit)",  2, STAGE_C.accumulator);

        if (errors == 0)
            $display("PASS: cascade/carry counter (#506/#516) -- three accumulator_cell_v1 instances in pulse_mode, zero new RTL, genuinely ripple-carry across 237 real external pulses with the correct three-digit decomposition (2,3,7) and zero pulses lost or double-counted");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
