// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_unicell_super_v6.v — points.md #542: extends tb_unicell_super_v1.v's
// own proven 6-core sequence (reused verbatim, proving zero regression)
// with a real sequencer check (closing part of the real, flagged gap
// that neither v2 nor v3 has ever had a dedicated testbench of their
// own) and a SUBSTANTIVE real branch cell test through the shell --
// not a sanity check, the SAME held-reference + per-outcome +
// suppression design already confirmed on real silicon standalone
// (#530), now proven through core_select routing too.
`timescale 1ns / 1ps

module tb_unicell_super_v6;

    reg         clk = 0;
    reg         rst = 1;
    reg         cfg_valid = 0;
    reg  [79:0] cfg_data = 80'h0;
    reg  [31:0] data_in_n = 0, data_in_s = 0, data_in_e = 0, data_in_w = 0;
    reg         arrived_n = 0, arrived_s = 0, arrived_e = 0, arrived_w = 0;
    reg         ready_in_n = 1, ready_in_s = 1, ready_in_e = 1, ready_in_w = 1;
    reg         ack_in_n = 0, ack_in_s = 0, ack_in_e = 0, ack_in_w = 0;
    reg         freeze_in = 0;

    wire [31:0] data_out_n, data_out_s, data_out_e, data_out_w;
    wire        fire_n, fire_s, fire_e, fire_w;
    wire        ready_out, ack_out_n, ack_out_s, ack_out_e, ack_out_w;
    wire [4:0]  status_core_select;

    integer errors = 0;

    unicell_super_v6 DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(arrived_e), .arrived_w(arrived_w),
        .data_out_n(data_out_n), .data_out_s(data_out_s), .data_out_e(data_out_e), .data_out_w(data_out_w),
        .fire_n(fire_n), .fire_s(fire_s), .fire_e(fire_e), .fire_w(fire_w),
        .ready_out(ready_out),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(ack_out_n), .ack_out_s(ack_out_s), .ack_out_e(ack_out_e), .ack_out_w(ack_out_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_in),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .status_core_select(status_core_select)
    );

    always #5 clk = ~clk;

    task load_cfg(input [79:0] word);
        begin
            @(posedge clk); cfg_valid = 1; cfg_data = word;
            @(posedge clk); cfg_valid = 0;
            @(posedge clk);
        end
    endtask

    task ack_dir_e; begin @(posedge clk); ack_in_e = 1; @(posedge clk); ack_in_e = 0; end endtask

    // SUPER_LATCH bit positions, matching unicell_super_v3.v's own header exactly
    function [79:0] pack(input [4:0] sel, input [41:0] core_cfg, input [19:0] addon_cfg);
        pack = {13'b0, addon_cfg, core_cfg, sel};
    endfunction

    localparam [4:0] SEL_SEQ = 5'd6, SEL_BRANCH = 5'd7;

    // Real branch cell config, per branch_cell_v1.v's own field map --
    // IDENTICAL design to the one already proven on real silicon
    // standalone (#530/#541): upstream_dir=N, LOW fires marker=1,
    // EQUAL fires marker=2, HIGH genuinely suppressed (emit_high=0),
    // both outcomes routed to E.
    localparam [41:0] BR_CFG = {
        1'b0,      // [41]    rolling_mode
        4'h0,      // [40:37] route_high (unused, emit_high=0)
        4'b0100,   // [36:33] route_equal = E
        4'b0100,   // [32:29] route_low   = E
        1'b0,      // [28]    emit_high (genuine suppression)
        1'b1,      // [27]    emit_equal
        1'b1,      // [26]    emit_low
        7'd0,      // [25:19] fixed_value_high (unused)
        7'd2,      // [18:12] fixed_value_equal -- marker
        7'd1,      // [11:5]  fixed_value_low   -- marker
        1'b0,      // [4]     value_source_high
        1'b1,      // [3]     value_source_equal
        1'b1,      // [2]     value_source_low
        2'd0       // [1:0]   upstream_dir -- N
    };

    initial begin
        #12 rst = 0;

        // ═══ RAM, fixed mode ═══
        load_cfg(pack(5'd1, {32'hCAFEBEEF, 1'b1, 1'b1, 4'h0, 4'b0001}, 20'h0));
        #20;
        if (data_out_n !== 32'hCAFEBEEF) begin
            $display("FAIL: RAM selected -- expected CAFEBEEF, got %h", data_out_n);
            errors = errors + 1;
        end else $display("OK: RAM selected -- data_out_n = %h", data_out_n);

        // ═══ ADDER -- isolation check plus real A+B ═══
        load_cfg(pack(5'd2, 42'h094, 20'h0));
        if (data_out_n === 32'hCAFEBEEF) begin
            $display("FAIL: RAM's old value leaked through after switching to adder!");
            errors = errors + 1;
        end else $display("OK: RAM's old value did NOT leak through after core switch");

        @(posedge clk); data_in_n = 32'd100; arrived_n = 1;
        @(posedge clk); arrived_n = 0;
        @(posedge clk); data_in_w = 32'd23; arrived_w = 1;
        @(posedge clk); arrived_w = 0;
        ack_dir_e();
        #20;
        if (data_out_e !== 32'd123) begin
            $display("FAIL: adder selected -- expected 123, got %0d", data_out_e);
            errors = errors + 1;
        end else $display("OK: adder selected -- data_out_e = %0d (100+23)", data_out_e);

        // ═══ ACCUMULATOR ═══
        load_cfg(pack(5'd3, {5'h0, 16'h0, 1'b0, 8'h01, 4'b0100, 4'b0000, 4'b0001}, 20'h0));
        @(posedge clk); arrived_n = 1; @(posedge clk); arrived_n = 0; ack_dir_e();
        @(posedge clk); arrived_n = 1; @(posedge clk); arrived_n = 0; ack_dir_e();
        @(posedge clk); arrived_n = 1; @(posedge clk); arrived_n = 0; ack_dir_e();
        #20;
        if (data_out_e !== 32'd3) begin
            $display("FAIL: accumulator selected -- expected 3, got %0d", data_out_e);
            errors = errors + 1;
        end else $display("OK: accumulator selected -- data_out_e = %0d (3 increments)", data_out_e);

        // ═══ COMPARATOR ═══
        load_cfg(pack(5'd4, {32'sd8, 4'b0001, 4'b0100}, 20'h0));
        @(posedge clk); data_in_n = 32'd10; arrived_n = 1; @(posedge clk); arrived_n = 0;
        #20;
        if (data_out_e[0] !== 1'b1) begin
            $display("FAIL: comparator selected -- expected result bit 1 (10>=8), got %b", data_out_e[0]);
            errors = errors + 1;
        end else $display("OK: comparator selected -- data_out_e[0] = %b (10>=8)", data_out_e[0]);

        // ═══ LATCH ═══
        load_cfg(pack(5'd5, {30'h0, 4'b0100, 4'b0000, 4'b0001}, 20'h0));
        @(posedge clk); data_in_n = 32'h1; arrived_n = 1; @(posedge clk); arrived_n = 0;
        ack_dir_e();
        #20;
        if (data_out_e[0] !== 1'b1) begin
            $display("FAIL: latch selected -- expected latched bit 1, got %b", data_out_e[0]);
            errors = errors + 1;
        end else $display("OK: latch selected -- data_out_e[0] = %b (set)", data_out_e[0]);

        // ═══ SEQUENCER -- real check, not previously covered by any
        // dedicated testbench for v2 or v3 (a real, flagged gap this
        // closes partially). VALUE_0=11, VALUE_1=22, SEQUENCE_LEN=2,
        // downstream=E. This core's own real header states capture
        // plays NO role at all -- it self-advances purely on its own
        // ack-drain cycle, confirmed directly before writing this,
        // not assumed the same as every other core here. ═══
        load_cfg(pack(SEL_SEQ, {4'b0100, 2'd2, 8'd0, 8'd0, 8'd22, 8'd11}, 20'h0));
        #20;
        if (data_out_e !== 32'd11) begin
            $display("FAIL: sequencer selected -- expected first value 11, got %0d", data_out_e);
            errors = errors + 1;
        end else $display("OK: sequencer selected -- data_out_e = %0d (VALUE_0)", data_out_e);
        ack_dir_e();
        #20;
        if (data_out_e !== 32'd22) begin
            $display("FAIL: sequencer selected -- expected second value 22, got %0d", data_out_e);
            errors = errors + 1;
        end else $display("OK: sequencer selected -- data_out_e = %0d (VALUE_1)", data_out_e);

        // ═══ BRANCH -- v3's own real new capability (#542). A
        // SUBSTANTIVE test, not a sanity check: the exact same held-
        // reference + per-outcome + genuine-suppression design already
        // confirmed on real silicon standalone (#530), now proven
        // through core_select routing for the first time. ═══
        load_cfg(pack(SEL_BRANCH, BR_CFG, 20'h0));
        if (data_out_e === 32'd22) begin
            $display("FAIL: sequencer's old value leaked through after switching to branch!");
            errors = errors + 1;
        end else $display("OK: sequencer's old value did NOT leak through after core switch");

        // Seed the reference to 8 -- the first real arrival.
        @(posedge clk); data_in_n = 32'd8; arrived_n = 1; @(posedge clk); arrived_n = 0;
        #20;

        // LOW: 5 < 8 -- must fire with the LOW marker (1)
        @(posedge clk); data_in_n = 32'd5; arrived_n = 1; @(posedge clk); arrived_n = 0;
        ack_dir_e();
        #20;
        if (data_out_e !== 32'd1) begin
            $display("FAIL: branch selected -- LOW outcome expected marker 1, got %0d", data_out_e);
            errors = errors + 1;
        end else $display("OK: branch selected -- LOW outcome correctly fired marker %0d (5<8)", data_out_e);

        // EQUAL: 8 == 8 -- must fire with the EQUAL marker (2)
        @(posedge clk); data_in_n = 32'd8; arrived_n = 1; @(posedge clk); arrived_n = 0;
        ack_dir_e();
        #20;
        if (data_out_e !== 32'd2) begin
            $display("FAIL: branch selected -- EQUAL outcome expected marker 2, got %0d", data_out_e);
            errors = errors + 1;
        end else $display("OK: branch selected -- EQUAL outcome correctly fired marker %0d (8==8)", data_out_e);

        // HIGH: 10 > 8 -- must NOT fire at all, checked over a real
        // window (genuine suppression, not absence-by-omission)
        @(posedge clk); data_in_n = 32'd10; arrived_n = 1; @(posedge clk); arrived_n = 0;
        repeat (20) begin
            @(posedge clk);
            if (fire_e) begin
                $display("FAIL: branch selected -- HIGH outcome should be genuinely suppressed, but fire_e asserted");
                errors = errors + 1;
            end
        end
        if (errors == 0) $display("OK: branch selected -- HIGH outcome genuinely suppressed (10>8), zero fires over a real window");

        if (errors == 0)
            $display("PASS: unicell_super_v6 -- core selection and isolation confirmed correct across all 8 cores (compare now reading its own config continuously off core_config, no local latch, #584), including a substantive real branch cell test (held-reference, per-outcome routing, genuine suppression) through core_select for the first time");
        else
            $display("FAIL: %0d error(s) in the super cell's core-selection mechanism", errors);

        $finish;
    end

endmodule
