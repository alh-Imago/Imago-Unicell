// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_shift_chain_v1.v — points.md #683. The real, end-to-end proof of
// Alan's own precise claim: chaining `shift_fine_addon_v1` (2-bit
// fine, 0-3) immediately before `shift_lane_addon_v2` (the existing
// 9-tap coarse shifter, `shift_fine_in` wired straight from the fine
// stage's own `shift_amount_out`) gives FULL, GAP-FREE 0-31 shift
// coverage, not just the 9 sparse coarse amounts. Sweeps every real
// (coarse_tap, fine_amount) pair against the corresponding plain
// behavioral shift in both directions, `lane_cut` held at 0 throughout
// (this test is about total-shift correctness, not the lane mechanism
// -- that's `tb_shift_lane_addon_v2.v`'s own job).
`timescale 1ns / 1ps

module tb_shift_chain_v1;

    reg         direction;
    reg         fine_en, coarse_en;
    reg  [1:0]  fine_amt;
    reg  [4:0]  coarse_amt;
    reg  [31:0] data_in;

    wire [31:0] after_fine;
    wire [1:0]  fine_amt_out;
    wire [31:0] data_out;

    integer errors = 0;
    integer coarse_i;
    integer fine_i;
    integer total;
    integer dir_i;
    reg  [4:0] coarse_taps [0:8];
    reg  [31:0] expected_left, expected_right;

    shift_fine_addon_v1 FINE (
        .direction(direction), .shift_en(fine_en), .shift_amount(fine_amt),
        .data_in(data_in), .data_out(after_fine), .shift_amount_out(fine_amt_out)
    );

    shift_lane_addon_v2 COARSE (
        .direction(direction), .shift_en(coarse_en), .shift_amt(coarse_amt),
        .lane_cut(3'b000), .shift_fine_in(fine_amt_out),
        .data_in(after_fine), .data_out(data_out)
    );

    task check_total(input [4:0] total_amt);
        begin
            #1;
            if (direction == 0) begin
                // left-shift by total_amt, real plain behavioral shift
                expected_left = (total_amt == 0) ? data_in : (data_in << total_amt);
                if (data_out !== expected_left) begin
                    $display("FAIL: LEFT total=%0d -- expected %h, got %h",
                              total_amt, expected_left, data_out);
                    errors = errors + 1;
                end
            end else begin
                expected_right = (total_amt == 0) ? data_in : (data_in >> total_amt);
                if (data_out !== expected_right) begin
                    $display("FAIL: RIGHT total=%0d -- expected %h, got %h",
                              total_amt, expected_right, data_out);
                    errors = errors + 1;
                end
            end
        end
    endtask

    initial begin
        coarse_taps[0] = 5'd1;  coarse_taps[1] = 5'd2;  coarse_taps[2] = 5'd4;
        coarse_taps[3] = 5'd8;  coarse_taps[4] = 5'd12; coarse_taps[5] = 5'd16;
        coarse_taps[6] = 5'd20; coarse_taps[7] = 5'd24; coarse_taps[8] = 5'd28;

        data_in = 32'hA5A5A5A5;   // a real, non-trivial, asymmetric pattern

        for (dir_i = 0; dir_i <= 1; dir_i = dir_i + 1) begin
            direction = dir_i[0];
            // total=0: both stages disabled.
            fine_en = 0; coarse_en = 0; fine_amt = 2'd0; coarse_amt = 5'd0;
            check_total(5'd0);

            // Every real coarse tap alone (fine disabled) -- 9 values.
            fine_en = 0; fine_amt = 2'd0;
            for (coarse_i = 0; coarse_i < 9; coarse_i = coarse_i + 1) begin
                coarse_en = 1; coarse_amt = coarse_taps[coarse_i];
                check_total(coarse_taps[coarse_i]);
            end

            // Every real (coarse tap + fine 1-3) combination -- the
            // real claim under test: this must cover every amount
            // from 1 through 31 with NO gaps, 9*3 = 27 more values,
            // plus the 9 coarse-alone values above and total=0 already
            // covered = 1 + 9 + 27 = 37 checks per direction, spanning
            // the full real 0-31 range at least once each (several
            // amounts reachable two ways, e.g. total=4 via coarse=4/
            // fine=0 or coarse=1/fine=3 -- both must agree).
            fine_en = 1; coarse_en = 1;
            for (coarse_i = 0; coarse_i < 9; coarse_i = coarse_i + 1) begin
                for (fine_i = 1; fine_i <= 3; fine_i = fine_i + 1) begin
                    coarse_amt = coarse_taps[coarse_i];
                    fine_amt = fine_i[1:0];
                    total = coarse_taps[coarse_i] + fine_i;
                    if (total <= 31) check_total(total[4:0]);
                end
            end
        end

        // ── Real, explicit, exhaustive sweep: every integer 0-31 is
        // reachable by AT LEAST ONE (coarse, fine) pair, confirmed by
        // construction above rather than asserted -- print a clear,
        // final coverage confirmation.
        if (errors == 0)
            $display("PASS: tb_shift_chain_v1 -- fine+coarse chain confirmed to reproduce a plain behavioral shift exactly, for total amounts 0-31, both directions, lane_cut=0");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
