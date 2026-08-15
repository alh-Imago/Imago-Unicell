// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_shift_lane_addon_v1.v — verifies shift_lane_addon_v1.v faithfully
// reproduces unicell64_v3.v's own proven shift/lane behavior: the exact
// sparse supported-amount set, silent no-op on unsupported amounts,
// lane-cut's coupling to SHIFT_OUT only, and the regression-safety
// invariant (lane_cut=0 must be bit-identical to plain shift, matching
// the FULL cell's own documented guarantee).
`timescale 1ns / 1ps

module tb_shift_lane_addon_v1;

    reg         direction;
    reg         shift_en;
    reg  [4:0]  shift_amt;
    reg  [2:0]  lane_cut;
    reg  [31:0] data_in;
    wire [31:0] data_out;

    integer errors = 0;
    integer i;

    shift_lane_addon_v1 DUT (
        .direction(direction), .shift_en(shift_en), .shift_amt(shift_amt),
        .lane_cut(lane_cut), .data_in(data_in), .data_out(data_out)
    );

    task check(input [255:0] name, input [31:0] expected);
        begin
            #1;
            if (data_out !== expected) begin
                $display("FAIL: %0s -- expected %h, got %h", name, expected, data_out);
                errors = errors + 1;
            end else begin
                $display("OK: %0s -- %h", name, data_out);
            end
        end
    endtask

    initial begin
        lane_cut = 3'b000;

        // ── shift_en=0: passthrough regardless of amount, either direction ──
        direction = 0; shift_en = 0; shift_amt = 5'd8; data_in = 32'hDEADBEEF;
        check("shift_en=0, SHIFT_IN passthrough", 32'hDEADBEEF);
        direction = 1; check("shift_en=0, SHIFT_OUT passthrough", 32'hDEADBEEF);

        // ── SHIFT_IN: every supported amount, exact bit-pattern check ──
        shift_en = 1; direction = 0; data_in = 32'hFFFFFFFF;
        shift_amt = 5'd1;  check("SHIFT_IN amt=1",  32'hFFFFFFFE);
        shift_amt = 5'd2;  check("SHIFT_IN amt=2",  32'hFFFFFFFC);
        shift_amt = 5'd4;  check("SHIFT_IN amt=4",  32'hFFFFFFF0);
        shift_amt = 5'd8;  check("SHIFT_IN amt=8",  32'hFFFFFF00);
        shift_amt = 5'd12; check("SHIFT_IN amt=12", 32'hFFFFF000);
        shift_amt = 5'd16; check("SHIFT_IN amt=16", 32'hFFFF0000);
        shift_amt = 5'd20; check("SHIFT_IN amt=20", 32'hFFF00000);
        shift_amt = 5'd24; check("SHIFT_IN amt=24", 32'hFF000000);
        shift_amt = 5'd28; check("SHIFT_IN amt=28", 32'hF0000000);

        // ── SHIFT_IN: unsupported amounts silently pass through unshifted ──
        shift_amt = 5'd3;  check("SHIFT_IN amt=3 (unsupported)",  32'hFFFFFFFF);
        shift_amt = 5'd5;  check("SHIFT_IN amt=5 (unsupported)",  32'hFFFFFFFF);
        shift_amt = 5'd31; check("SHIFT_IN amt=31 (unsupported)", 32'hFFFFFFFF);

        // ── SHIFT_OUT (lane_cut=0): every supported amount, exact check ──
        direction = 1; lane_cut = 3'b000;
        shift_amt = 5'd1;  check("SHIFT_OUT amt=1, lane=0",  32'h7FFFFFFF);
        shift_amt = 5'd2;  check("SHIFT_OUT amt=2, lane=0",  32'h3FFFFFFF);
        shift_amt = 5'd4;  check("SHIFT_OUT amt=4, lane=0",  32'h0FFFFFFF);
        shift_amt = 5'd8;  check("SHIFT_OUT amt=8, lane=0",  32'h00FFFFFF);
        shift_amt = 5'd12; check("SHIFT_OUT amt=12, lane=0", 32'h000FFFFF);
        shift_amt = 5'd16; check("SHIFT_OUT amt=16, lane=0", 32'h0000FFFF);
        shift_amt = 5'd20; check("SHIFT_OUT amt=20, lane=0", 32'h00000FFF);
        shift_amt = 5'd24; check("SHIFT_OUT amt=24, lane=0", 32'h000000FF);
        shift_amt = 5'd28; check("SHIFT_OUT amt=28, lane=0", 32'h0000000F);

        // ── SHIFT_OUT: unsupported amount, still lane_cut=0 -> passthrough ──
        shift_amt = 5'd7; check("SHIFT_OUT amt=7 (unsupported), lane=0", 32'hFFFFFFFF);

        // ── Lane-cut has ZERO effect on SHIFT_IN, any cut pattern ──
        direction = 0; shift_amt = 5'd8; data_in = 32'hFFFFFFFF;
        for (i = 0; i < 8; i = i + 1) begin
            lane_cut = i[2:0];
            check("SHIFT_IN ignores lane_cut", 32'hFFFFFF00);
        end
        lane_cut = 3'b000;

        // ── Directed lane-cut cases on SHIFT_OUT, hand-verified windows ──
        direction = 1; data_in = 32'hFFFFFFFF; shift_amt = 5'd8;
        lane_cut = 3'b001; // cut at bit8 boundary
        check("SHIFT_OUT amt=8, cut=bit8", 32'h00FFFF00);
        lane_cut = 3'b010; // cut at bit16 boundary
        check("SHIFT_OUT amt=8, cut=bit16", 32'h00FF00FF);
        lane_cut = 3'b100; // cut at bit24 boundary
        check("SHIFT_OUT amt=8, cut=bit24", 32'h0000FFFF);
        lane_cut = 3'b111; // all cuts active
        check("SHIFT_OUT amt=8, cut=all", 32'h00000000);

        if (errors == 0)
            $display("PASS: shift_lane_addon_v1 -- faithful port confirmed, sparse table exact, lane-cut coupling to SHIFT_OUT only confirmed, regression-safe default confirmed");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
