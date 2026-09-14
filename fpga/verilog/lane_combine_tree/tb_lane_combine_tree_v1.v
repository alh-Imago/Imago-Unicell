// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_lane_combine_tree_v1.v — points.md #696: the real RTL proof of
// #692's own recursive lane-combine tree, taken from the VM
// (test_lane_combine_tree_v1.py) to actual Verilog, per Alan's own
// direct request: "when the new card arrives it is going to have a
// lot of proving to do." Same real 7-cell topology, same real test
// value (0x44332211), same real mechanism (nibble_mask -> shift_fine
// -> shift_lane_v2 -> OR-capture) -- now exercised through 7 real
// unicell_super_v1.v shell instances and the actual addon-chain RTL
// (#683/#684), not the Python model.
//
// Real, deliberate simplification, stated plainly rather than
// silently assumed: every `ready_in_*` is tied permanently high
// (matching `tb_unicell_super_v1.v`'s own established convention) --
// this proves the real DATA TRANSFORMATION correctness of the
// combine tree (masking, shifting, OR-capture), not backpressure/
// handshake behavior under contention, which is a genuinely separate
// concern already proven elsewhere (`tb_grid5x5_both_v2_freeze.v`).
//
// TWO REAL BUGS FOUND WHILE BUILDING THIS -- both in this testbench
// itself, not the RTL under test, confirmed by direct signal tracing
// before assuming otherwise:
// 1. Plain Verilog `output` task arguments only copy OUT to the
//    caller's actual reg when the task RETURNS, not as they're
//    assigned mid-task -- an internal $display inside such a task
//    showed the intended pulse correctly, while the real, port-
//    connected reg outside never saw it at all. `ref` args would fix
//    this but iverilog does not yet support them ("Reference ports
//    not supported yet") -- worked around by inlining each config
//    load directly, matching `tb_unicell_super_v1.v`'s own proven
//    convention (direct assignment, no task indirection).
// 2. The real cardinal-to-bit convention for `downstream_mask`/
//    `upstream_mask` is N=bit0, S=bit1, E=bit2, W=bit3 (confirmed
//    against `ram_cell_v1.v`'s own `ram_sel_w = ...upstream_mask[3]`
//    etc. directly) -- an initial mask of `4'b0110` for "west+east"
//    was actually wired to east+south, silently listening on the
//    wrong pair of directions. Found by tracing that one gatherer's
//    own west-side arrival was permanently asserted but never
//    consumed (never acked), not a vague "wrong answer" alone.
//
// Real topology (identical to the VM's own, `#692`):
//
//   source1(row1) --e--> \
//                          gathererA --n--> \
//   source2(row1) --w--> /                   \
//                                              merge
//   source3(row-1)--e--> \                   /
//                          gathererB --s--> /   [+shift 16]
//   source4(row-1)--w--> /   [+shift 8]
`timescale 1ns / 1ps

module tb_lane_combine_tree_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [4:0] SEL_RAM = 5'd1;

    // ── Real config packer, matching icm_v3.py's own exact field
    // layout, extended for shift_fine at [68:67] (#683/#684). ──
    function [79:0] pack_ram;
        input [3:0] downstream_mask, upstream_mask;
        input fixed_mode, load_data_valid;
        input [31:0] init_data;
        input mask_en;
        input [7:0] nibble_mask;
        input shift_en, direction;
        input [4:0] shift_amt;
        input [2:0] lane_cut;
        input invert_en;
        input [1:0] shift_fine;
        reg [41:0] core_cfg;
        reg [19:0] addon_cfg;
        begin
            core_cfg = {init_data, load_data_valid, fixed_mode, upstream_mask, downstream_mask};
            addon_cfg = {invert_en, lane_cut, direction, shift_en, shift_amt, mask_en, nibble_mask};
            pack_ram = {9'b0, shift_fine, addon_cfg, core_cfg, SEL_RAM};
        end
    endfunction

    // ── Real per-instance signal groups (7 shells) ───────────────────
    reg  [79:0] cfg1=0, cfg2=0, cfgA=0, cfg3=0, cfg4=0, cfgB=0, cfgM=0;
    reg  cfgv1=0, cfgv2=0, cfgvA=0, cfgv3=0, cfgv4=0, cfgvB=0, cfgvM=0;

    wire [31:0] s1_e_data, s2_w_data, gA_n_data;
    wire        s1_e_fire, s2_w_fire, gA_n_fire;
    wire        gA_w_ack,  gA_e_ack,  m_s_ack;
    wire        gA_ready,  m_ready;

    wire [31:0] s3_e_data, s4_w_data, gB_s_data;
    wire        s3_e_fire, s4_w_fire, gB_s_fire;
    wire        gB_w_ack,  gB_e_ack,  m_n_ack;
    wire        gB_ready;

    wire [4:0]  unused_sel [0:6];

    // source1(row1,col-1) -- feeds gathererA from the west, unshifted.
    unicell_super_v1 #(.CELL_ID(16'h0001)) SOURCE1 (
        .clk(clk), .rst(rst), .cfg_valid(cfgv1), .cfg_data(cfg1),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(s1_e_data), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(s1_e_fire), .fire_w(),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(gA_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(gA_w_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .program_in(1'b0), .program_done(), .prog_data_in_n(32'h0), .prog_data_in_s(32'h0),
        .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .status_core_select(unused_sel[0])
    );

    // source2(row1,col+1) -- feeds gathererA from the east, shifted
    // left by 8 (its own local high byte).
    unicell_super_v1 #(.CELL_ID(16'h0002)) SOURCE2 (
        .clk(clk), .rst(rst), .cfg_valid(cfgv2), .cfg_data(cfg2),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(s2_w_data),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(s2_w_fire),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(gA_ready),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(gA_e_ack),
        .freeze_in(1'b0),
        .program_in(1'b0), .program_done(), .prog_data_in_n(32'h0), .prog_data_in_s(32'h0),
        .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .status_core_select(unused_sel[1])
    );

    // gathererA(row1,col0) -- OR-captures source1(w)+source2(e), no
    // addon, relays north to merge.
    unicell_super_v1 #(.CELL_ID(16'h0003)) GATHERER_A (
        .clk(clk), .rst(rst), .cfg_valid(cfgvA), .cfg_data(cfgA),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(s2_w_data), .data_in_w(s1_e_data),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(s2_w_fire), .arrived_w(s1_e_fire),
        .data_out_n(gA_n_data), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(gA_n_fire), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(gA_ready), .ready_in_n(m_ready), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(gA_e_ack), .ack_out_w(gA_w_ack),
        .ack_in_n(m_s_ack), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .program_in(1'b0), .program_done(), .prog_data_in_n(32'h0), .prog_data_in_s(32'h0),
        .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .status_core_select(unused_sel[2])
    );

    // source3(row-1,col-1) -- feeds gathererB from the west, unshifted
    // (locally).
    unicell_super_v1 #(.CELL_ID(16'h0004)) SOURCE3 (
        .clk(clk), .rst(rst), .cfg_valid(cfgv3), .cfg_data(cfg3),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(s3_e_data), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(s3_e_fire), .fire_w(),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(gB_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(gB_w_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .program_in(1'b0), .program_done(), .prog_data_in_n(32'h0), .prog_data_in_s(32'h0),
        .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .status_core_select(unused_sel[3])
    );

    // source4(row-1,col+1) -- feeds gathererB from the east, shifted
    // left by 8 (its own local high byte, matching source2 exactly).
    unicell_super_v1 #(.CELL_ID(16'h0005)) SOURCE4 (
        .clk(clk), .rst(rst), .cfg_valid(cfgv4), .cfg_data(cfg4),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(s4_w_data),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(s4_w_fire),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(gB_ready),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(gB_e_ack),
        .freeze_in(1'b0),
        .program_in(1'b0), .program_done(), .prog_data_in_n(32'h0), .prog_data_in_s(32'h0),
        .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .status_core_select(unused_sel[4])
    );

    // gathererB(row-1,col0) -- OR-captures source3(w)+source4(e),
    // THEN shifts its own already-combined 16-bit local pattern left
    // by 16 -- #692's own real "shift the whole combined pattern"
    // mechanism, now in real RTL.
    unicell_super_v1 #(.CELL_ID(16'h0006)) GATHERER_B (
        .clk(clk), .rst(rst), .cfg_valid(cfgvB), .cfg_data(cfgB),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(s4_w_data), .data_in_w(s3_e_data),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(s4_w_fire), .arrived_w(s3_e_fire),
        .data_out_n(), .data_out_s(gB_s_data), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(gB_s_fire), .fire_e(), .fire_w(),
        .ready_out(gB_ready), .ready_in_n(1'b1), .ready_in_s(m_ready), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(gB_e_ack), .ack_out_w(gB_w_ack),
        .ack_in_n(1'b0), .ack_in_s(m_n_ack), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .program_in(1'b0), .program_done(), .prog_data_in_n(32'h0), .prog_data_in_s(32'h0),
        .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .status_core_select(unused_sel[5])
    );

    // merge(row0,col0) -- final OR-capture, no addon, upstream from
    // gathererA (south, since gathererA is physically south of merge)
    // and gathererB (north).
    wire [31:0] merge_data_reg;
    unicell_super_v1 #(.CELL_ID(16'h0007)) MERGE (
        .clk(clk), .rst(rst), .cfg_valid(cfgvM), .cfg_data(cfgM),
        .data_in_n(gB_s_data), .data_in_s(gA_n_data), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(gB_s_fire), .arrived_s(gA_n_fire), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(m_ready), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(m_n_ack), .ack_out_s(m_s_ack), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .program_in(1'b0), .program_done(), .prog_data_in_n(32'h0), .prog_data_in_s(32'h0),
        .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .status_core_select(unused_sel[6])
    );

    // Real, direct hierarchical read of merge's own captured register
    // -- the same real "read the RAM core's own data_reg" approach
    // every other single-shell testbench in this project already uses.
    assign merge_data_reg = MERGE.CORE_RAM.data_reg;

    // Real, deliberate fix: plain Verilog `output` task arguments only
    // copy OUT to the caller's actual reg when the task RETURNS, not
    // as they're assigned mid-task -- meaning the DUT's own cfg_valid
    // port would never actually see the intermediate `v=1` pulse a
    // task like that would set internally (found directly via
    // simulation, not assumed: an internal $display inside such a
    // task showed v=1 correctly, while the real, port-connected reg
    // outside never did). `ref` args would fix this but iverilog does
    // not yet support them ("Reference ports not supported yet") --
    // so each load below is inlined directly against its own real
    // reg pair, matching `tb_unicell_super_v1.v`'s own proven
    // convention exactly (direct assignment, no task indirection at
    // all) rather than working around a real tool limitation with a
    // fragile macro.

    initial begin
        #12 rst = 0;

        // source1: VALUE1=0x11, natural position, no shift.
        @(posedge clk); cfgv1 = 1; cfg1 = pack_ram(4'b0100 /*e*/, 4'b0000, 1'b0, 1'b1, 32'h00000011,
                       1'b0, 8'h00, 1'b0, 1'b0, 5'd0, 3'b000, 1'b0, 2'd0);
        @(posedge clk); cfgv1 = 0;

        // source2: VALUE2=0x22, shift left 8 -> local bits[15:8].
        @(posedge clk); cfgv2 = 1; cfg2 = pack_ram(4'b1000 /*w*/, 4'b0000, 1'b0, 1'b1, 32'h00000022,
                       1'b0, 8'h00, 1'b1, 1'b0, 5'd8, 3'b000, 1'b0, 2'd0);
        @(posedge clk); cfgv2 = 0;

        // gathererA: plain OR-capture, no addon, relay north.
        @(posedge clk); cfgvA = 1; cfgA = pack_ram(4'b0001 /*n*/, 4'b1100 /*w,e*/, 1'b0, 1'b0, 32'h0,
                       1'b0, 8'h00, 1'b0, 1'b0, 5'd0, 3'b000, 1'b0, 2'd0);
        @(posedge clk); cfgvA = 0;

        // source3: VALUE3=0x33, natural position (locally).
        @(posedge clk); cfgv3 = 1; cfg3 = pack_ram(4'b0100 /*e*/, 4'b0000, 1'b0, 1'b1, 32'h00000033,
                       1'b0, 8'h00, 1'b0, 1'b0, 5'd0, 3'b000, 1'b0, 2'd0);
        @(posedge clk); cfgv3 = 0;

        // source4: VALUE4=0x44, shift left 8 -> local bits[15:8].
        @(posedge clk); cfgv4 = 1; cfg4 = pack_ram(4'b1000 /*w*/, 4'b0000, 1'b0, 1'b1, 32'h00000044,
                       1'b0, 8'h00, 1'b1, 1'b0, 5'd8, 3'b000, 1'b0, 2'd0);
        @(posedge clk); cfgv4 = 0;

        // gathererB: OR-captures locally, THEN shifts the whole
        // combined 16-bit pattern left by 16.
        @(posedge clk); cfgvB = 1; cfgB = pack_ram(4'b0010 /*s*/, 4'b1100 /*w,e*/, 1'b0, 1'b0, 32'h0,
                       1'b0, 8'h00, 1'b1, 1'b0, 5'd16, 3'b000, 1'b0, 2'd0);
        @(posedge clk); cfgvB = 0;

        // merge: plain OR-capture, no addon.
        @(posedge clk); cfgvM = 1; cfgM = pack_ram(4'b0000, 4'b0011 /*n,s*/, 1'b0, 1'b0, 32'h0,
                       1'b0, 8'h00, 1'b0, 1'b0, 5'd0, 3'b000, 1'b0, 2'd0);
        @(posedge clk); cfgvM = 0;

        // Real settle window -- generous, matching the VM's own
        // `run_to_quiescence()` discipline (a bounded wait, not an
        // exact minimal tick count).
        #200;

        if (merge_data_reg !== 32'h44332211) begin
            $display("FAIL: expected 44332211, got %h", merge_data_reg);
        end else begin
            $display("PASS: tb_lane_combine_tree_v1 -- real RTL confirms #692's own 4-lane combine tree, 44332211");
        end
        $finish;
    end

endmodule
