// tb_nano_bounded_loop_ring_v1.v — resolves #637's own real, standing
// integration question: a genuine 3-cell ring can't close in this
// bipartite cardinal mesh, and a single cell can't both dynamically
// route AND reliably relay. Per Alan's own real design call: since the
// DECISION already lives entirely in LOOP_CTRL, the 4th cell closing
// the ring only ever needs to relay, never decide -- ram_cell_v4 in
// its own real "flowing" mode (fixed_mode=0, single-arrival capture,
// no A/B two-stage, no dynamic routing at all) is exactly that, and
// costs no dummy-second-arrival overhead the way a nano relay would.
//
// Real, legal 4-cell ring (a proper 2x2 square, an even cycle, closes
// cleanly in the N/S/E/W-only mesh):
//
//        LOOPVAR ────south────> LOOP_CTRL ────east────> ADDER
//           ^                        |                     |
//           |                      south                 north
//         west                   (testbench:            (RAM_RELAY)
//      (RAM_RELAY,               EXIT consumer)              |
//       closes the ring)                                     v
//           |                                            RAM_RELAY
//           +───────────────west <── RAM_RELAY <──south───────+
//
// LOOP_CTRL's own real dynamic pattern-routing (#637) decides
// CONTINUE (east, into ADDER) vs EXIT (south, to a real testbench
// consumer) each real round. RAM_RELAY only ever does one thing: catch
// ADDER's real sum on its south port and relay it west, back into
// LOOPVAR, closing the physical loop -- no decision, no dynamic
// routing, so none of #637's own found conflicts apply to it.
//
// Real, honest scope, matching #636's own precedent: the loop bound N
// and the increment constant B are still testbench-injected directly,
// standing in for not-yet-built constant sources. hold/upd/reemit
// stay testbench-driven, standing in for the future loop-control
// mechanism (#628's command core).
`timescale 1ns / 1ps

module tb_nano_bounded_loop_ring_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [9:0] TOPO_PASS_A = 10'h000;
    // Real bit convention, confirmed against the RTL: bit0=N,bit1=S,bit2=E,bit3=W.
    localparam [3:0] DIR_N4 = 4'b0001, DIR_S4 = 4'b0010, DIR_E4 = 4'b0100, DIR_W4 = 4'b1000;

    // ── LOOPVAR stimulus/control ──
    reg cfgLV = 0; reg [127:0] cfgLV_d;
    reg [31:0] entry_val = 0; reg entry_pulse = 0;
    reg [31:0] dummy_val = 0; reg dummy_pulse = 0;
    reg hold = 0, upd = 0, reemit = 0;

    // ── LOOP_CTRL stimulus/control ──
    reg cfgLC = 0; reg [127:0] cfgLC_d;
    reg [31:0] n_val = 0; reg n_pulse = 0;
    reg exit_ready = 1'b1, exit_ack = 0;

    // ── ADDER stimulus/control ──
    reg cfgAD = 0; reg [63:0] cfgAD_d;
    reg [31:0] const_b = 0; reg const_pulse = 0;

    // ── RAM_RELAY config ──
    reg cfgRR = 0; reg [79:0] cfgRR_d;

    // ── Real interconnect wires (the 4-cell ring) ──
    wire [31:0] lv2lc_data; wire lv2lc_fire; wire lc2lv_ack; wire lc_ready;
    wire [31:0] lc2ad_data; wire lc2ad_fire; wire ad2lc_ack; wire ad_ready;
    wire [31:0] ad2rr_data; wire ad2rr_fire; wire rr2ad_ack; wire rr_ready;
    wire [31:0] rr2lv_data; wire rr2lv_fire; wire lv2rr_ack; wire lv_ready;

    wire [31:0] lc2exit_data; wire lc2exit_fire;
    wire adder_a_arrived, adder_data_valid;
    wire rr_data_valid;

    nano_gate_v4 #(.CELL_ID(16'h7000), .ENABLE_DYNAMIC_ROUTING(1'b0)) LOOPVAR (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfgLV), .cfg_data(cfgLV_d),
        .data_in_n(entry_pulse ? entry_val : 32'h0), .data_in_s(32'h0),
        .data_in_e(rr2lv_data), .data_in_w(dummy_pulse ? dummy_val : 32'h0),
        .arrived_n(entry_pulse), .arrived_s(1'b0),
        .arrived_e(rr2lv_fire), .arrived_w(dummy_pulse),
        .data_out_n(), .data_out_s(lv2lc_data), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(lv2lc_fire), .fire_e(), .fire_w(),
        .ready_out(lv_ready),
        .ready_in_n(1'b1), .ready_in_s(lc_ready), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(lv2rr_ack), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(lc2lv_ack), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(hold), .fb_internal_in(1'b0), .a_reemit_in(reemit),
        .a_update_in(upd), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    nano_gate_v4 #(.CELL_ID(16'h7001), .ENABLE_DYNAMIC_ROUTING(1'b1)) LOOP_CTRL (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfgLC), .cfg_data(cfgLC_d),
        .data_in_n(lv2lc_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(n_val),
        .arrived_n(lv2lc_fire), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(n_pulse),
        .data_out_n(), .data_out_s(lc2exit_data), .data_out_e(lc2ad_data), .data_out_w(),
        .fire_n(), .fire_s(lc2exit_fire), .fire_e(lc2ad_fire), .fire_w(),
        .ready_out(lc_ready),
        .ready_in_n(1'b1), .ready_in_s(exit_ready), .ready_in_e(ad_ready), .ready_in_w(1'b1),
        .ack_out_n(lc2lv_ack), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(exit_ack), .ack_in_e(ad2lc_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    adder_cell_v4 #(.CELL_ID(16'h7002)) ADDER (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfgAD), .cfg_data(cfgAD_d),
        .data_in_n(32'h0), .data_in_s(const_b), .data_in_e(32'h0), .data_in_w(lc2ad_data),
        .arrived_n(1'b0), .arrived_s(const_pulse), .arrived_e(1'b0), .arrived_w(lc2ad_fire),
        .data_out_n(ad2rr_data), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(ad2rr_fire), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(ad_ready),
        .ready_in_n(rr_ready), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ad2lc_ack),
        .ack_in_n(rr2ad_ack), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0),
        .status_data_valid(adder_data_valid), .status_a_arrived(adder_a_arrived)
    );

    ram_cell_v4 #(.CELL_ID(16'h7003)) RAM_RELAY (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfgRR), .cfg_data(cfgRR_d),
        .data_in_n(32'h0), .data_in_s(ad2rr_data), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(ad2rr_fire), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(rr2lv_data),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(rr2lv_fire),
        .ready_out(rr_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(lv_ready),
        .ack_out_n(), .ack_out_s(rr2ad_ack), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(lv2rr_ack),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0),
        .status_data_valid(rr_data_valid)
    );

    integer errors = 0;
    integer checks = 0;
    integer round_num = 0;

    task check(input cond, input [255:0] label);
        begin
            checks = checks + 1;
            if (!cond) begin
                $display("[t=%0t] FAIL: %0s", $time, label);
                errors = errors + 1;
            end else begin
                $display("[t=%0t] check #%0d OK: %0s", $time, checks, label);
            end
        end
    endtask

    // ── One real round. Real, necessary ordering, found by tracing an
    // actual failure -- the SAME real bug class as #636's own bug 1:
    // LOOP_CTRL already holds `i` as its real first arrival coming
    // INTO this task (from the entry-seed's own automatic first offer,
    // or from the PREVIOUS round's own trailing reemit below).
    // Reemitting i AGAIN at the start of this task, before that
    // already-held value is consumed, makes LOOP_CTRL treat the
    // REDUNDANT reemit as its real SECOND arrival -- comparing the old
    // i against itself (equal!) and firing a bogus EXIT before N is
    // ever even injected. Real, corrected order: inject N first
    // (completing the already-pending capture), decide, run the real
    // chain if continuing, THEN reemit LOOPVAR's new value so the NEXT
    // call has a fresh i already pending -- exactly #636's own fix,
    // one level up. ──
    task do_round(input [31:0] bound_n, output continued, output [31:0] exit_val);
        begin
            round_num = round_num + 1;

            // Inject the real bound N as LOOP_CTRL's second real
            // arrival, completing its already-pending capture of i and
            // triggering its own real dynamic-routing decision.
            n_val = bound_n; n_pulse = 1'b1;
            @(posedge clk); #1;
            n_pulse = 1'b0;
            repeat (2) @(posedge clk); #1;

            if (lc2exit_fire) begin
                // Real EXIT: capture the final value straight off
                // LOOP_CTRL's own south port. No reemit needed -- the
                // loop is genuinely done.
                exit_val = lc2exit_data;
                continued = 1'b0;
                exit_ack = 1'b1; @(posedge clk); #1; exit_ack = 1'b0;
                repeat (2) @(posedge clk);
            end else begin
                // Real CONTINUE: the value is already offered east
                // into ADDER (lc2ad_fire). Run the real chain through
                // to LOOPVAR's own update, sequenced off ADDER's and
                // RAM_RELAY's real status ports rather than guessed
                // delays (#636's own established discipline).
                continued = 1'b1;
                exit_val = 32'h0;

                while (adder_a_arrived !== 1'b1) @(posedge clk);
                #1;

                upd = 1'b1;
                const_b = 32'd1; const_pulse = 1'b1;
                @(posedge clk); #1;
                const_pulse = 1'b0;

                while (adder_data_valid !== 1'b1) @(posedge clk);
                #1;
                while (rr_data_valid !== 1'b1) @(posedge clk);
                #1;
                // Real, necessary fix, found by tracing an actual
                // failure: waiting for adder_data_valid to drain only
                // confirms the ADDER->RAM_RELAY handoff completed, NOT
                // that RAM_RELAY's own downstream offer reached and
                // was consumed by LOOPVAR. rr_data_valid dropping is
                // the real, correct signal that LOOPVAR genuinely
                // consumed the relayed value.
                while (rr_data_valid !== 1'b0) @(posedge clk);
                #1;
                upd = 1'b0;
                @(posedge clk); #1;   // real settle cycle, #636's own established need

                // Reemit LOOPVAR's now-updated value south into
                // LOOP_CTRL, giving the NEXT call a fresh real i
                // already pending (dummy west arrival is the
                // established real "second arrival" trigger,
                // #629/#630/#633/#635/#636).
                reemit = 1'b1;
                dummy_val = 32'hFFFFFFFF; dummy_pulse = 1'b1;
                @(posedge clk); #1;
                dummy_pulse = 1'b0; reemit = 1'b0;
                while (LOOP_CTRL.a_arrived !== 1'b1) @(posedge clk);
                #1;
            end
        end
    endtask

    initial begin
        reg cont;
        reg [31:0] final_val;

        $dumpfile("/tmp/tb_nano_bounded_loop_ring_v1.vcd");
        $dumpvars(0, tb_nano_bounded_loop_ring_v1);

        #12 rst = 0;
        @(posedge clk); #1;

        // LOOPVAR: PASS_A, routes south only.
        cfgLV = 1; cfgLV_d = 128'h0;
        cfgLV_d[9:0]   = TOPO_PASS_A;
        cfgLV_d[69:64] = {2'b00, DIR_S4};
        // LOOP_CTRL: PASS_A, dynamic routing E(continue)/S(exit).
        cfgLC = 1; cfgLC_d = 128'h0;
        cfgLC_d[9:0]   = TOPO_PASS_A;
        cfgLC_d[69:64] = {2'b00, DIR_E4 | DIR_S4};
        cfgLC_d[79:76] = DIR_S4;   // pattern_low   (N<i, degenerate) -> exit
        cfgLC_d[85:82] = DIR_S4;   // pattern_equal (N==i, real exit) -> exit
        cfgLC_d[91:88] = DIR_E4;   // pattern_high  (N>i, continue)   -> continue
        cfgLC_d[94]    = 1'b1;    // dynamic_route_en
        // ADDER: upstream N|W... here upstream = W(i, from LOOP_CTRL)
        // | S(const B, testbench), downstream = N (to RAM_RELAY).
        cfgAD = 1; cfgAD_d = 64'h0;
        cfgAD_d[5:0]  = 6'b000001;              // downstream_mask = N
        cfgAD_d[11:6] = {2'b00, DIR_W4 | DIR_S4}; // upstream_mask = W | S
        // RAM_RELAY: flowing mode, upstream S (from ADDER), downstream W (to LOOPVAR).
        cfgRR = 1; cfgRR_d = 80'h0;
        cfgRR_d[5:0]  = 6'b001000;   // downstream_mask = W
        cfgRR_d[11:6] = 6'b000010;   // upstream_mask   = S
        cfgRR_d[12]   = 1'b0;        // fixed_mode = 0 (flowing)

        @(posedge clk); #1;
        cfgLV = 0; cfgLC = 0; cfgAD = 0; cfgRR = 0;
        repeat (2) @(posedge clk);

        // ── Real entry edge: seed LOOPVAR's held value to 0. ──
        hold = 1'b1;
        entry_val = 32'd0; entry_pulse = 1'b1;
        @(posedge clk); #1;
        entry_pulse = 1'b0;
        repeat (2) @(posedge clk);
        dummy_val = 32'hDEADBEEF; dummy_pulse = 1'b1;   // established "ignored" second arrival
        @(posedge clk); #1;
        dummy_pulse = 1'b0;
        repeat (3) @(posedge clk);
        check(LOOPVAR.data_reg === 32'd0, "entry-seed: LOOPVAR.data_reg=0");

        // ── Real bounded loop: "for i in 0..3" -- 3 real continue
        // rounds (0->1->2->3, each hop through the real 4-cell ring),
        // then a real exit on round 4 (i==N==3). ──
        do_round(32'd3, cont, final_val);
        check(cont === 1'b1, "round 1: continued (0<3)");
        check(LOOPVAR.data_reg === 32'd1, "round 1: LOOPVAR.data_reg=1 via real 4-cell ring");

        do_round(32'd3, cont, final_val);
        check(cont === 1'b1, "round 2: continued (1<3)");
        check(LOOPVAR.data_reg === 32'd2, "round 2: LOOPVAR.data_reg=2 via real 4-cell ring");

        do_round(32'd3, cont, final_val);
        check(cont === 1'b1, "round 3: continued (2<3)");
        check(LOOPVAR.data_reg === 32'd3, "round 3: LOOPVAR.data_reg=3 via real 4-cell ring");

        do_round(32'd3, cont, final_val);
        check(cont === 1'b0, "round 4: real exit (3==3)");
        check(final_val === 32'd3, "round 4: real exit value=3, captured off LOOP_CTRL's own south port");

        if (checks == 9 && errors == 0)
            $display("PASS: real, genuine bounded loop -- LOOPVAR+LOOP_CTRL+ADDER+RAM_RELAY closed into a proper 4-cell physical ring, 3 real continue rounds (0->1->2->3) each computed by the real adder and relayed by the real RAM cell, then a real exit at i==N==3 captured straight off LOOP_CTRL's own dynamic-routing decision");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
