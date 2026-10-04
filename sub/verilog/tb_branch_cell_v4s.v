// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design -- see LICENSE-HARDWARE and NOTICE
//
// tb_branch_cell_v4s.v -- self-checking bench for branch_cell_v4s.v (the sub-family branch; Alan #935/#941).
// Same cases as tb_branch_cell_v4sa.v where they still make sense, with the sub family's semantics: NO ack, NO freeze, NO hold -- every
// output is a ONE-CYCLE registered pulse. The v4sa cases that are about backpressure (differential ack, freeze) do not exist here and are
// replaced by cases that ARE this family's contract: one result per cycle (full throughput), the cell is silent until configured, a reconfigure
// needs a reload of a fixed input, and the rolling-style use (the same stream on both inputs, in2 held) that the ICM-branch lowering relies on.
// Run:  iverilog -g2012 -o /tmp/tb_b4s.vvp tb_branch_cell_v4s.v branch_cell_v4s.v && vvp /tmp/tb_b4s.vvp     (prints ALL PASS)
`timescale 1ns/1ps
module tb_branch_cell_v4s;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [31:0] cfg_emit_fixed_value = 0;
    reg [31:0] in1_data = 0, in2_data = 0;
    reg in1_valid = 0, in2_valid = 0;
    wire [31:0] data_out_1, data_out_2;
    wire valid_out_1, valid_out_2;

    always #5 clk = ~clk;

    branch_cell_v4s dut (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data), .cfg_emit_fixed_value(cfg_emit_fixed_value),
        .in1_data(in1_data), .in1_valid(in1_valid),
        .in2_data(in2_data), .in2_valid(in2_valid),
        .data_out_1(data_out_1), .valid_out_1(valid_out_1),
        .data_out_2(data_out_2), .valid_out_2(valid_out_2)
    );

    integer errors = 0;
    task check_cond(input cond, input [1023:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    task cfg(input [31:0] word, input [31:0] fixed_val);
        begin
            cfg_data = word; cfg_emit_fixed_value = fixed_val; cfg_valid = 1;
            @(posedge clk); #1;
            cfg_valid = 0;
        end
    endtask

    // Loads the FIXED in1 (a silent side effect: a load is never an offer).
    task load_in1(input [31:0] val);
        begin
            in1_data = val; in1_valid = 1;
            @(posedge clk); #1;
            in1_valid = 0;
        end
    endtask

    // One in2 round, advancing EXACTLY one edge: the registered pulse for it is visible immediately afterwards (one cycle of latency).
    task present_round(input [31:0] in2_val);
        begin
            in2_data = in2_val; in2_valid = 1;
            @(posedge clk); #1;
            in2_valid = 0;
        end
    endtask

    // An idle edge: with no ack and no hold, every pulse must be gone after exactly one cycle.
    task idle;
        begin
            @(posedge clk); #1;
        end
    endtask

    integer n1, n2;

    initial begin
        // === silent until configured (the cell is not armed by reset) ===
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk); #1;
        in1_data = 32'd5; in1_valid = 1; in2_data = 32'd3; in2_valid = 1;
        @(posedge clk); #1; in1_valid = 0; in2_valid = 0;
        check_cond(valid_out_1 === 1'b0 && valid_out_2 === 1'b0, "unarmed: a round before configuration produces nothing");

        // === one fixed (in1), one flowing (in2). emit=diff; low->out1, equal->out2, high->both. ===
        cfg({22'h0, 2'b11 /*route_high=both*/, 2'b10 /*route_equal=out2*/,
             2'b01 /*route_low=out1*/, 2'b11 /*emit=diff*/, 1'b0 /*in2 flowing*/, 1'b1 /*in1 fixed*/}, 32'h0);
        load_in1(32'd100);
        check_cond(valid_out_1 === 1'b0 && valid_out_2 === 1'b0, "loading the fixed in1 is silent (a load is not an offer)");

        present_round(32'd50);  // 100 > 50 -> HIGH -> both, diff = 50
        check_cond(data_out_1 === 32'd50 && valid_out_1 === 1'b1, "HIGH: out1 gets diff=50");
        check_cond(data_out_2 === 32'd50 && valid_out_2 === 1'b1, "HIGH: out2 ALSO gets diff=50 (route_high=both)");
        idle();
        check_cond(valid_out_1 === 1'b0 && valid_out_2 === 1'b0, "pulses last ONE cycle: gone the next edge with no ack needed (no hold in this family)");

        present_round(32'd100);  // EQUAL -> out2 only, diff = 0
        check_cond(valid_out_1 === 1'b0, "EQUAL: out1 does NOT fire (route_equal=out2 only)");
        check_cond(data_out_2 === 32'd0 && valid_out_2 === 1'b1, "EQUAL: out2 gets diff=0");
        idle();

        present_round(32'd150);  // LOW -> out1 only, diff = -50
        check_cond(data_out_1 === 32'hFFFFFFCE && valid_out_1 === 1'b1, "LOW: out1 gets diff=-50 (two's complement, 0xffffffce)");
        check_cond(valid_out_2 === 1'b0, "LOW: out2 does NOT fire (route_low=out1 only)");
        idle();

        // === the compare is SIGNED ===
        load_in1(32'h80000000);                      // most negative
        present_round(32'd1);                        // -2^31 < 1 -> LOW -> out1
        check_cond(valid_out_1 === 1'b1 && valid_out_2 === 1'b0, "signed compare: 0x80000000 < 1 is LOW (not high)");
        idle();

        // === a FIXED input HOLDS its value: the data bus changing while its valid is low must not disturb it ===
        load_in1(32'd100);
        in1_data = 32'd999;                          // bus garbage; in1_valid stays low
        idle();
        present_round(32'd50);                       // 100 > 50 -> HIGH -> both; diff must be 100 - 50 = 50 (not 999 - 50 = 949)
        check_cond(data_out_1 === 32'd50 && valid_out_1 === 1'b1, "a fixed in1 holds its loaded value while in1_valid is low, whatever the bus does");
        idle();

        // === emit_source = in1, in2, and fixed constant ===
        cfg({22'h0, 2'b01, 2'b01, 2'b01, 2'b01 /*emit=in1*/, 1'b0, 1'b1}, 32'h0);
        load_in1(32'd77);
        present_round(32'd1);
        check_cond(data_out_1 === 32'd77, "emit_source=in1: emits the held in1 value (77)");
        idle();

        cfg({22'h0, 2'b01, 2'b01, 2'b01, 2'b10 /*emit=in2*/, 1'b0, 1'b1}, 32'h0);
        load_in1(32'd77);
        present_round(32'd1);
        check_cond(data_out_1 === 32'd1, "emit_source=in2: emits the flowing in2 value (1)");
        idle();

        cfg({22'h0, 2'b01, 2'b01, 2'b01, 2'b00 /*emit=fixed*/, 1'b0, 1'b1}, 32'hDEADBEEF);
        load_in1(32'd77);
        present_round(32'd1);
        check_cond(data_out_1 === 32'hDEADBEEF, "emit_source=fixed: emits the configured constant");
        idle();

        // === the swallow case: route=00 means consumed, nothing offered ===
        cfg({22'h0, 2'b00 /*route_high=NEITHER*/, 2'b01, 2'b01, 2'b01, 1'b0, 1'b1}, 32'h0);
        load_in1(32'd100);
        present_round(32'd1);  // 100 > 1 -> HIGH -> route_high=00, swallowed
        check_cond(valid_out_1 === 1'b0 && valid_out_2 === 1'b0, "swallow: HIGH with route=00 produces no pulse on either output");

        // === a reconfigure is a fresh start: a fixed input must be RELOADED ===
        cfg({22'h0, 2'b01, 2'b01, 2'b01, 2'b11, 1'b0, 1'b1}, 32'h0);
        present_round(32'd1);                         // no load_in1 since the reconfigure
        check_cond(valid_out_1 === 1'b0 && valid_out_2 === 1'b0, "reconfigure: a fixed in1 that has not been reloaded cannot fire a round");
        load_in1(32'd10);
        present_round(32'd4);
        check_cond(valid_out_1 === 1'b1 && data_out_1 === 32'd6, "after the reload it fires (10 - 4 = 6)");
        idle();

        // === BOTH flowing: a real synchronisation requirement ===
        cfg({22'h0, 2'b01, 2'b01, 2'b01, 2'b11 /*emit=diff*/, 1'b0, 1'b0}, 32'h0);
        in1_data = 32'd9; in1_valid = 1; in2_data = 32'd4; in2_valid = 0;     // only in1 fresh
        @(posedge clk); #1; in1_valid = 0;
        check_cond(valid_out_1 === 1'b0, "both-flowing: no firing when only ONE side presents a fresh value");
        in1_data = 32'd9; in1_valid = 1; in2_data = 32'd4; in2_valid = 1;     // BOTH fresh, same cycle
        @(posedge clk); #1; in1_valid = 0; in2_valid = 0;
        check_cond(data_out_1 === 32'd5 && valid_out_1 === 1'b1, "both-flowing: fires once BOTH present a fresh value the same cycle (9-4=5)");
        idle();

        // === THIS family's contract: one result per cycle (no handshake slows it) ===
        cfg({22'h0, 2'b01, 2'b01, 2'b01, 2'b11, 1'b0, 1'b0}, 32'h0);          // both flowing, diff, everything -> out1
        n1 = 0;
        in1_valid = 1; in2_valid = 1;
        in1_data = 32'd10; in2_data = 32'd1; @(posedge clk); #1; if (valid_out_1 && data_out_1 === 32'd9)  n1 = n1 + 1;
        in1_data = 32'd20; in2_data = 32'd2; @(posedge clk); #1; if (valid_out_1 && data_out_1 === 32'd18) n1 = n1 + 1;
        in1_data = 32'd30; in2_data = 32'd3; @(posedge clk); #1; if (valid_out_1 && data_out_1 === 32'd27) n1 = n1 + 1;
        in1_data = 32'd40; in2_data = 32'd4; @(posedge clk); #1; if (valid_out_1 && data_out_1 === 32'd36) n1 = n1 + 1;
        in1_valid = 0; in2_valid = 0;
        check_cond(n1 === 4, "full throughput: four back-to-back rounds give four consecutive correct pulses (the flex cell manages one per two cycles)");
        idle();

        // === rolling-style use (what the ICM branch lowering relies on): the SAME stream on both inputs, in2 HELD ===
        // in1 flowing, in2 fixed; each value is compared with the PREVIOUS one; the very first finds nothing loaded and only becomes the reference.
        cfg({22'h0, 2'b11 /*high=both*/, 2'b10 /*equal=out2*/, 2'b01 /*low=out1*/, 2'b01 /*emit=in1*/, 1'b1 /*in2 fixed*/, 1'b0 /*in1 flowing*/}, 32'h0);
        n1 = 0; n2 = 0;
        in1_data = 32'd5; in2_data = 32'd5; in1_valid = 1; in2_valid = 1;
        @(posedge clk); #1;
        check_cond(valid_out_1 === 1'b0 && valid_out_2 === 1'b0, "rolling: the FIRST value only becomes the reference -- no output");
        in1_data = 32'd9; in2_data = 32'd9;
        @(posedge clk); #1;
        check_cond(valid_out_1 === 1'b1 && valid_out_2 === 1'b1 && data_out_1 === 32'd9, "rolling: 9 vs previous 5 -> HIGH -> both outputs carry 9");
        in1_data = 32'd3; in2_data = 32'd3;
        @(posedge clk); #1;
        check_cond(valid_out_1 === 1'b1 && valid_out_2 === 1'b0 && data_out_1 === 32'd3, "rolling: 3 vs previous 9 -> LOW -> out1 only");
        in1_data = 32'd3; in2_data = 32'd3;
        @(posedge clk); #1;
        check_cond(valid_out_1 === 1'b0 && valid_out_2 === 1'b1 && data_out_2 === 32'd3, "rolling: 3 vs previous 3 -> EQUAL -> out2 only");
        in1_valid = 0; in2_valid = 0;
        idle();
        // the HELD in2 also ignores its bus while its valid is low (here: garbage 777, then a value 5 against the held reference 3)
        in2_data = 32'd777; idle();
        in1_data = 32'd5; in1_valid = 1; in2_valid = 0;
        @(posedge clk); #1; in1_valid = 0;
        check_cond(valid_out_1 === 1'b1 && valid_out_2 === 1'b1, "rolling: a held in2 keeps its reference (3) while in2_valid is low: 5 vs 3 is HIGH -> both");
        idle();

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
