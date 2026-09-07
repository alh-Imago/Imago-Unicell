// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_shift_fine_addon_v1.v — verifies shift_fine_addon_v1.v: a genuine
// general 2-bit shifter (no unsupported-amount case, unlike its coarse
// sibling), both directions, and the real forwarding rule for
// `shift_amount_out` (0 whenever shift_en=0, regardless of the
// configured amount -- the value downstream lane_cut math depends on).
`timescale 1ns / 1ps

module tb_shift_fine_addon_v1;

    reg         direction;
    reg         shift_en;
    reg  [1:0]  shift_amount;
    reg  [31:0] data_in;
    wire [31:0] data_out;
    wire [1:0]  shift_amount_out;

    integer errors = 0;

    shift_fine_addon_v1 DUT (
        .direction(direction), .shift_en(shift_en), .shift_amount(shift_amount),
        .data_in(data_in), .data_out(data_out), .shift_amount_out(shift_amount_out)
    );

    task check(input [255:0] name, input [31:0] expected_data, input [1:0] expected_amt_out);
        begin
            #1;
            if (data_out !== expected_data || shift_amount_out !== expected_amt_out) begin
                $display("FAIL: %0s -- expected data=%h amt_out=%0d, got data=%h amt_out=%0d",
                          name, expected_data, expected_amt_out, data_out, shift_amount_out);
                errors = errors + 1;
            end else begin
                $display("OK: %0s -- data=%h amt_out=%0d", name, data_out, shift_amount_out);
            end
        end
    endtask

    initial begin
        // ── shift_en=0: passthrough, AND shift_amount_out forced to 0
        // regardless of the configured amount (the real, physical
        // contribution to any downstream total is genuinely zero) ──
        direction = 0; shift_en = 0; shift_amount = 2'd3; data_in = 32'hDEADBEEF;
        check("shift_en=0, SHIFT_IN passthrough, amt_out forced 0", 32'hDEADBEEF, 2'd0);
        direction = 1;
        check("shift_en=0, SHIFT_OUT passthrough, amt_out forced 0", 32'hDEADBEEF, 2'd0);

        // ── SHIFT_IN (left), every real amount, exact bit pattern ──
        shift_en = 1; direction = 0; data_in = 32'hFFFFFFFF;
        shift_amount = 2'd0; check("SHIFT_IN amt=0", 32'hFFFFFFFF, 2'd0);
        shift_amount = 2'd1; check("SHIFT_IN amt=1", 32'hFFFFFFFE, 2'd1);
        shift_amount = 2'd2; check("SHIFT_IN amt=2", 32'hFFFFFFFC, 2'd2);
        shift_amount = 2'd3; check("SHIFT_IN amt=3", 32'hFFFFFFF8, 2'd3);

        // ── SHIFT_OUT (right), every real amount, exact bit pattern ──
        direction = 1; data_in = 32'hFFFFFFFF;
        shift_amount = 2'd0; check("SHIFT_OUT amt=0", 32'hFFFFFFFF, 2'd0);
        shift_amount = 2'd1; check("SHIFT_OUT amt=1", 32'h7FFFFFFF, 2'd1);
        shift_amount = 2'd2; check("SHIFT_OUT amt=2", 32'h3FFFFFFF, 2'd2);
        shift_amount = 2'd3; check("SHIFT_OUT amt=3", 32'h1FFFFFFF, 2'd3);

        // ── A non-trivial data pattern, both directions, amt=3 ──
        direction = 0; data_in = 32'h00000001;
        shift_amount = 2'd3; check("SHIFT_IN amt=3, single low bit", 32'h00000008, 2'd3);
        direction = 1; data_in = 32'h80000000;
        shift_amount = 2'd3; check("SHIFT_OUT amt=3, single high bit", 32'h10000000, 2'd3);

        if (errors == 0)
            $display("PASS: shift_fine_addon_v1 -- general 2-bit shift confirmed both directions, shift_amount_out forwarding rule confirmed");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
