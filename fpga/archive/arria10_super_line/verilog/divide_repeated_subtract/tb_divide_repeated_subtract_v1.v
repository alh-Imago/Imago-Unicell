// tb_divide_repeated_subtract_v1.v — points.md #506/#518: division via
// repeated subtraction WITH FEEDBACK -- the third and genuinely harder
// of #506's own three composed applications. ZERO new RTL, per #509's
// own decomposition method — a real, closed, self-sustaining loop built
// entirely from two accumulator_cell_v1 instances (#515's step_amount)
// and one branch_cell_v1 instance (#500/#504's held-reference +
// per-outcome suppression), matching #506's own explicit statement of
// what makes division structurally different from multiplication: "the
// accumulator's own current value feeding a comparator or branch cell
// watching for 'gone below B/zero yet', gating whether another
// decrement pulse fires."
//
// THE REAL SHAPE:
//   SUBTRACTED — an accumulator tracking the running total subtracted
//     so far (step_amount=B), starts at 0, continuously offers its own
//     current value.
//   QUOTIENT — a second accumulator (step_amount=1), fed the SAME
//     "continue" pulse as SUBTRACTED, counting real iterations.
//   BR (branch_cell_v1) — the real feedback gate. Its held reference is
//     seeded, ONCE, with the host-precomputed constant (A-B) -- A and B
//     are both known in advance for a division operation, exactly the
//     same "host already knows the operands" pattern #517 already
//     established for multiplication's B. Every later arrival on BR's
//     fixed upstream direction is SUBTRACTED's own current value,
//     compared against that fixed reference: "SUBTRACTED <= (A-B)"
//     (is_low OR is_equal) means there's still room for one more full
//     subtraction of B -- BR fires a real "continue" pulse, fanned out
//     to BOTH SUBTRACTED and QUOTIENT at once (its own real route mask,
//     #497's own multi-direction fan-out, not two separate outcomes).
//     "SUBTRACTED > (A-B)" (is_high) means one more subtraction would
//     go negative -- BR genuinely SUPPRESSES (emit_high=0), and because
//     nothing else in this loop generates a pulse on its own, the whole
//     loop halts by itself, with zero explicit "stop" signal anywhere.
//
// A REAL RACE FOUND AND FIXED -- not assumed away, confirmed directly
// via cycle-level simulation tracing across two successive theories
// before landing on the real, general one. SUBTRACTED's own "re-offer
// whenever free" pacing (offer -> ack -> pending_ack clears, a 1-cycle
// round trip) is FASTER than the full loop round trip needed to
// deliver a genuinely NEW value to offer (offer -> BR's own 2-cycle
// internal decision latency -> BR fires -> SUBTRACTED captures, 3
// cycles total). Left unguarded, SUBTRACTED becomes "free to re-offer"
// a full 2 cycles before its own next real update lands, and spends
// that window re-offering the SAME STALE value a second time -- which
// BR, having no way to know it's stale, genuinely captures as if
// fresh, producing one real extra iteration. Confirmed this ISN'T a
// one-time startup artifact (an earlier theory, tried and disproven
// directly by tracing): freezing SUBTRACTED only until its own first
// real capture just relocated the same duplicate to that first
// capture instead of eliminating it -- the mismatch is general, tied
// to any point SUBTRACTED's own offering starts fresh from a free
// state, not particular to config time.
//
// THE REAL, GENERAL FIX, using an existing mechanism (`freeze_in`),
// not new RTL: SUBTRACTED stays frozen BY DEFAULT, unfrozen ONLY
// during the exact cycle(s) `br_fire_e` genuinely asserts a real
// continue pulse (`sub_freeze_in = !br_fire_e`, permanently, every
// round). Safe because an ALREADY-STARTED offer is never gated by
// freeze -- `fire_e`/ack handling reads `pending_ack` directly, so
// refreezing the cycle after a real capture doesn't abandon or
// corrupt an in-flight offer, it only prevents a NEW, premature one
// from starting before the next genuine continue pulse arrives. This
// also means SUBTRACTED never gets a chance to spontaneously offer
// its own initial value (0) on its own cadence at all -- the real,
// single, controlled first comparison is fed to BR manually instead
// (the kickstart step in `run_case` below), standing in for what that
// spontaneous offer would have been, done once, correctly, host-driven.
//
// FINAL RESULT: QUOTIENT.accumulator is the real quotient. The real
// remainder is A - SUBTRACTED.accumulator -- computed here in the
// testbench (introspection, matching this project's own established
// convention for reading composed results), NOT a real wired-out
// hardware register. A genuine hardware remainder output would need one
// more real cell/subtraction step; explicitly not built here.
`timescale 1ns / 1ps

module tb_divide_repeated_subtract_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

    // ── accumulator_cell_v1 config, per #515: {threshold(16),
    // pulse_mode(1), step_amount(8), downstream_mask(4), dec_dir(4),
    // inc_dir(4)}. Both SUBTRACTED and QUOTIENT: inc on N (the shared
    // "continue" trigger), static/continuous mode. ──
    function [63:0] acc_cfg(input [7:0] step, input [3:0] downstream);
        acc_cfg = {27'h0, 16'h0000, 1'b0, step, downstream, 4'h0, DIR_N};
    endfunction

    // ── branch_cell_v1 config, per #500/#504/#497: {reserved(22),
    // rolling_mode(1), route_high(4), route_equal(4), route_low(4),
    // emit_high(1), emit_equal(1), emit_low(1), fixed_value_high(7),
    // fixed_value_equal(7), fixed_value_low(7), value_source_high(1),
    // value_source_equal(1), value_source_low(1), upstream_dir(2)}.
    // upstream_dir=3 (W) -- SUBTRACTED's own value arrives there.
    // route_low=route_equal=(E|N) -- real fan-out to BOTH SUBTRACTED
    // (E) and QUOTIENT (N) on a genuine "continue." route_high unused
    // -- emit_high=0 means the stop condition is a real, genuine
    // suppression, not a zero-value emit.
    localparam [63:0] BR_CFG = {
        22'h0,              // [63:42] reserved
        1'b0,               // [41]    rolling_mode -- static, reference stays fixed at (A-B)
        4'h0,               // [40:37] route_high    -- unused, emit_high=0
        4'b0101,            // [36:33] route_equal   -- E|N
        4'b0101,            // [32:29] route_low     -- E|N
        1'b0,               // [28]    emit_high     -- genuine suppression on stop
        1'b1,               // [27]    emit_equal
        1'b1,               // [26]    emit_low
        7'h0,               // [25:19] fixed_value_high -- unused
        7'h0,               // [18:12] fixed_value_equal -- data doesn't matter, only arrival
        7'h0,               // [11:5]  fixed_value_low
        1'b0,               // [4]     value_source_high
        1'b1,               // [3]     value_source_equal -- fixed
        1'b1,               // [2]     value_source_low   -- fixed
        2'd3                // [1:0]   upstream_dir -- W
    };

    // ── SUBTRACTED — step_amount=B (set per case), offers on E. See
    // this file's own header for the real race found and the real,
    // general fix applied (`sub_freeze_in`, below). ──
    // REAL FIX, GENERALIZED (not just a startup special-case): keep
    // SUBTRACTED frozen BY DEFAULT, unfrozen ONLY during the exact
    // cycle(s) br_fire_e genuinely asserts a real continue pulse.
    // Confirmed (via direct cycle-level trace, not assumed) that the
    // race above recurs at ANY point SUBTRACTED's own offering starts
    // fresh from a "free" state, not only at config time -- so gating
    // permanently on `br_fire_e` itself, rather than latching
    // permanently open after the first pulse, is the real fix. Safe
    // because an ALREADY-STARTED offer (`pending_ack` already nonzero)
    // is never gated by freeze -- `fire_e`/`ack` handling reads
    // `pending_ack` directly, so refreezing the cycle after a capture
    // doesn't abandon or corrupt an in-flight offer, it only prevents a
    // NEW, premature one from starting before the next real pulse.
    reg  q_cfg = 0;
    reg [63:0] q_cfg_d = 0;
    wire        q_ack_out_n;

    wire sub_freeze_in = !br_fire_e;

    reg        sub_cfg = 0;
    reg [63:0] sub_cfg_d = 0;
    wire [31:0] sub_dout_e;
    wire        sub_fire_e, sub_ack_out_n;

    accumulator_cell_v1 #(.CELL_ID(16'h0030), .WIDTH(32)) SUBTRACTED (
        .clk(clk), .rst(rst), .cfg_valid(sub_cfg), .cfg_data(sub_cfg_d),
        .data_in_n(br_dout_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(br_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(sub_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(sub_fire_e), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(sub_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(br_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(sub_freeze_in), .ready_out(), .status_negative()
    );

    accumulator_cell_v1 #(.CELL_ID(16'h0031), .WIDTH(32)) QUOTIENT (
        .clk(clk), .rst(rst), .cfg_valid(q_cfg), .cfg_data(q_cfg_d),
        .data_in_n(br_dout_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(br_fire_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(q_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .freeze_in(1'b0), .ready_out(), .status_negative()
    );

    // ── BR — the real feedback gate. W input: seeded once with (A-B),
    // then continuously fed SUBTRACTED's own current value. ──
    reg        br_cfg = 0;
    reg        seeding = 0;
    reg [31:0] seed_value = 0;

    wire br_arrived_w = seeding | sub_fire_e;
    wire [31:0] br_din_w = seeding ? seed_value : sub_dout_e;
    wire [31:0] br_dout_e, br_dout_n;
    wire        br_fire_e, br_fire_n, br_ack_out_w;

    branch_cell_v1 #(.CELL_ID(16'h0032)) BR (
        .clk(clk), .rst(rst), .cfg_valid(br_cfg), .cfg_data(BR_CFG),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(br_din_w),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(br_arrived_w),
        .data_out_n(br_dout_n), .data_out_s(), .data_out_e(br_dout_e), .data_out_w(),
        .fire_n(br_fire_n), .fire_s(), .fire_e(br_fire_e), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(br_ack_out_w),
        .ack_in_n(q_ack_out_n), .ack_in_s(1'b0), .ack_in_e(sub_ack_out_n), .ack_in_w(1'b0),
        .freeze_in(1'b0), .ready_out(), .status_data_valid()
    );

    integer errors = 0;

    task check(input [255:0] label, input integer expected, input integer actual);
        begin
            if (actual !== expected) begin
                $display("FAIL: %0s -- expected %0d, got %0d", label, expected, actual);
                errors = errors + 1;
            end else $display("OK: %0s -- correctly %0d", label, actual);
        end
    endtask

    task run_case(input [255:0] label, input integer a, input integer b, input integer settle_ns);
        integer remainder;
        begin
            rst = 1; #12; rst = 0; #10;

            // Real, deliberate order: BR first (with its reference
            // seeded before SUBTRACTED ever exists to race it), THEN
            // QUOTIENT, THEN SUBTRACTED -- which stays permanently
            // frozen except during a genuine br_fire_e pulse (this
            // file's own real fix, see SUBTRACTED's own header above),
            // so it never gets a chance to spontaneously offer on its
            // own cadence at any point in the run.
            br_cfg = 1; #10; br_cfg = 0; #10;

            seeding = 1; seed_value = a - b;
            #10;
            seeding = 0;
            #10;

            q_cfg = 1; q_cfg_d = acc_cfg(8'h01, 4'h0); #10; q_cfg = 0; #10;

            sub_cfg = 1; sub_cfg_d = acc_cfg(b[7:0], DIR_E); #10; sub_cfg = 0; #10;

            // The real, single, controlled first comparison -- standing
            // in for SUBTRACTED's own initial value (0), fed manually
            // and ONCE, host-driven, exactly the mechanism this file's
            // own header describes. SUBTRACTED is permanently frozen
            // except during a real br_fire_e pulse, so there is no
            // possibility of it ever spontaneously contributing a
            // second, duplicate "0" itself.
            seeding = 1; seed_value = 32'h0;
            #10;
            seeding = 0;

            // From here the loop is fully self-driving -- SUBTRACTED
            // unfreezes for exactly one cycle each time a real continue
            // pulse (from the manual kickstart above, or from any later
            // genuine BR decision) actually arrives, and refreezes
            // immediately after. Let it settle (caller supplies a
            // generous margin scaled to the expected iteration count).
            #settle_ns;

            remainder = a - SUBTRACTED.accumulator;
            check({label, ": quotient"},  a / b,       QUOTIENT.accumulator);
            check({label, ": remainder"}, a % b,        remainder);
        end
    endtask

    initial begin
        // ── Case 1: 23 / 7 -- non-exact division, quotient=3, remainder=2 ──
        run_case("23/7", 23, 7, 400);

        // ── Case 2: 21 / 7 -- exact division, exercises the real
        // is_equal outcome landing exactly on the boundary (SUBTRACTED
        // reaches exactly A-B), quotient=3, remainder=0 ──
        run_case("21/7", 21, 7, 400);

        // ── Case 3: 3 / 7 -- A<B, the real degenerate case: the very
        // FIRST comparison (SUBTRACTED's own initial value of 0 against
        // a NEGATIVE reference) must immediately suppress, quotient=0,
        // remainder=3, with QUOTIENT never incrementing at all ──
        run_case("3/7", 3, 7, 200);

        // ── Case 4: 100 / 9 -- a larger, real multi-iteration case,
        // quotient=11, remainder=1 ──
        run_case("100/9", 100, 9, 600);

        if (errors == 0)
            $display("PASS: division via repeated subtraction with feedback (#506/#518) -- two accumulator_cell_v1 instances + one branch_cell_v1, a genuine self-sustaining loop with zero external stop signal, correct across a non-exact case, an exact case, the A<B degenerate case, and a larger multi-iteration case");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
