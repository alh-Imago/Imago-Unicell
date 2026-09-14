// tb_nano_adder_loop_v1.v — points.md #635's own standing queue item 1:
// wire a REAL adder_cell_v4 into the phi/loop-variable feedback path,
// replacing #635's testbench-injected stand-in value with a genuine
// physical cardinal wire carrying a real computed sum.
//
// Real topology: LOOPVAR (nano_gate_v4, PASS_A) sits west of ADDER
// (adder_cell_v4). LOOPVAR's east port and ADDER's west port form ONE
// real, bidirectional cardinal link, used for BOTH directions of this
// loop (the same real "one wire pair carries traffic each way"
// convention every other cell-to-cell link in this project already
// uses):
//   LOOPVAR.data_out_e/fire_e   -> ADDER.data_in_w/arrived_w   (offers i, the A operand)
//   ADDER.ack_out_w             -> LOOPVAR.ack_in_e
//   ADDER.ready_out             -> LOOPVAR.ready_in_e
//   ADDER.data_out_w/fire_w     -> LOOPVAR.data_in_e/arrived_e (returns i+1, the real sum)
//   LOOPVAR.ack_out_e           -> ADDER.ack_in_w
//   LOOPVAR.ready_out           -> ADDER.ready_in_w
//
// Real, honest scope, matching #635's own precedent: the B operand
// (the increment constant, 1) is still injected directly on ADDER's
// NORTH port by this testbench, standing in for a real config-loaded
// constant source (not yet built — a real, separate, later increment).
// Likewise, the reemit/update CONTROL pulses (hold/upd/reemit) remain
// testbench-driven, standing in for the future loop-control mechanism
// (#628's command core, or the loop-exit item still queued behind this
// one) — #635 already established this same real division of scope.
// What's NEW and REAL here: the VALUE flowing through the loop (the
// i+1 the ADDER hands back) is now genuinely computed by a real,
// separate, sim-verified adder_cell_v4 instance over a real physical
// wire, not a testbench constant standing in for it.
`timescale 1ns / 1ps

module tb_nano_adder_loop_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [5:0] DIR_E6 = 6'b000100;   // LOOPVAR routing_mask target: east only
    localparam [9:0] TOPO_PASS_A = 10'h000;

    // ── LOOPVAR stimulus/control (testbench-driven, real scope per header) ──
    reg cfgL = 0; reg [127:0] cfgL_d;
    reg [31:0] entry_val = 0; reg entry_pulse = 0;
    reg [31:0] dummy_val = 0; reg dummy_pulse = 0;   // west-port "trigger" arrivals
    reg hold = 0, upd = 0, reemit = 0;

    // ── ADDER stimulus/control (testbench-driven B operand, real scope per header) ──
    reg cfgA = 0; reg [63:0] cfgA_d;
    reg [31:0] const_b = 0; reg const_pulse = 0;

    // ── Real interconnect: LOOPVAR.east <-> ADDER.west ──
    wire [31:0] l2a_data;  wire l2a_fire;  wire a2l_ack;  wire a_ready;
    wire [31:0] a2l_data;  wire a2l_fire;  wire l2a_ack;  wire l_ready;

    wire loopvar_ready_o, adder_ready_o;
    assign a_ready = adder_ready_o;
    assign l_ready = loopvar_ready_o;

    // Real status outputs (points.md #617/#618) -- used below to drive
    // real sequencing off the ADDER's own actual state instead of
    // guessed fixed delays.
    wire adder_a_arrived, adder_data_valid;

    nano_gate_v4 #(.CELL_ID(16'h5000), .ENABLE_DYNAMIC_ROUTING(1'b0)) LOOPVAR (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfgL), .cfg_data(cfgL_d),
        .data_in_n(32'h0), .data_in_s(32'h0),
        .data_in_e(a2l_data), .data_in_w(dummy_pulse ? dummy_val : entry_val),
        .arrived_n(1'b0), .arrived_s(1'b0),
        .arrived_e(a2l_fire), .arrived_w(dummy_pulse | entry_pulse),
        .data_out_n(), .data_out_s(), .data_out_e(l2a_data), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(l2a_fire), .fire_w(),
        .ready_out(loopvar_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(a_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(l2a_ack), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(a2l_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .hold_in(hold), .fb_internal_in(1'b0), .a_reemit_in(reemit),
        .a_update_in(upd), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    adder_cell_v4 #(.CELL_ID(16'h5001)) ADDER (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(cfgA), .cfg_data(cfgA_d),
        .data_in_n(const_b), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(l2a_data),
        .arrived_n(const_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(l2a_fire),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(a2l_data),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(a2l_fire),
        .ready_out(adder_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(l_ready),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(a2l_ack),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(l2a_ack),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0),
        .status_data_valid(adder_data_valid), .status_a_arrived(adder_a_arrived)
    );

    integer errors = 0;
    integer checks = 0;

    task report(input [255:0] label);
        $display("[t=%0t] %0s | LOOPVAR.data_reg=%0d LOOPVAR.a_arrived=%b | ADDER.a_reg=%0d ADDER.a_arrived=%b ADDER.out_buffer=%0d ADDER.data_valid=%b",
                  $time, label, LOOPVAR.data_reg, LOOPVAR.a_arrived,
                  ADDER.a_reg, ADDER.a_arrived, ADDER.out_buffer, ADDER.data_valid);
    endtask

    task check_data_reg(input [31:0] want, input [255:0] label);
        begin
            checks = checks + 1;
            if (LOOPVAR.data_reg !== want) begin
                $display("[t=%0t] FAIL (%0s): expected LOOPVAR.data_reg=%0d, got %0d", $time, label, want, LOOPVAR.data_reg);
                errors = errors + 1;
            end else begin
                $display("[t=%0t] check #%0d (%0s): LOOPVAR.data_reg=%0d (correct)", $time, checks, label, LOOPVAR.data_reg);
            end
        end
    endtask

    // ── One real loop iteration, sequenced off the ADDER's own real
    // status ports (status_a_arrived/status_data_valid) rather than
    // guessed fixed delays. Real, necessary ordering, found by tracing
    // TWO actual failures, not assumed:
    //
    // Bug 1: the ADDER already holds A (a_arrived=1) coming INTO this
    // task -- either from the entry-seed's own real can_fire (the
    // genuine first offer) or from the PREVIOUS iteration's own
    // trailing reemit. Reemitting again at the START of this task,
    // before that already-held A is consumed, makes the real ADDER
    // silently treat the re-offered A as a bogus B operand instead.
    //
    // Bug 2: a_update_in must already be high BEFORE the real a2l_fire
    // arrival lands, not raised afterward -- nano's own base two-
    // arrival can_fire path sits below a_update_active in real
    // priority but is still satisfied by a_arrived=1 (permanent, under
    // hold) plus ANY fresh consume_arrived, so a real arrival landing
    // while upd=0 gets silently claimed by a plain re-offer of the OLD
    // data_reg instead of the intended update.
    //
    // A real, honest THIRD finding, caught by polling the real status
    // ports instead of guessing delays: fixed-delay sequencing between
    // rounds let a new round's B-injection overlap the PREVIOUS
    // round's still-draining offer, producing extra, redundant real
    // adder computations that happened not to corrupt the final value
    // by luck of timing, not by genuine synchronization. Polling
    // adder_a_arrived/adder_data_valid directly closes that gap. ──
    // Real, necessary sampling discipline, found by tracing a THIRD
    // actual failure: plain `wait(sig)` can resolve in the same delta
    // cycle a nonblocking assignment changes `sig`, before dependent
    // state (like data_reg's own registered update) has genuinely
    // settled -- the same real "settle after the edge" discipline this
    // project's own established multi-cell testbenches already use
    // (`@(posedge clk); #1;`, not bare `wait`). These helper tasks poll
    // only at settled post-edge points.
    task loop_iteration;
        begin
            // 0. Confirm the real A this round will use is genuinely
            // already captured (from the entry-seed or the previous
            // round's trailing reemit) before touching anything else.
            while (adder_a_arrived !== 1'b1) @(posedge clk);
            #1;

            // 1. Assert upd BEFORE triggering the real B operand, keep
            // it high across the real ADDER's whole capture->compute->
            // offer sequence, so whichever real cycle the resulting
            // a2l_fire lands on is consumed as a genuine update.
            upd = 1'b1;

            // Real wire: inject the real B operand (constant 1) on
            // ADDER's own north port, standing in for a not-yet-built
            // constant source per this file's own header -- triggers
            // the real can_fire/sum computation.
            const_b = 32'd1; const_pulse = 1'b1;
            @(posedge clk); #1;
            const_pulse = 1'b0;

            // 2. Real wire: wait for the real sum to actually be
            // computed (status_data_valid), sampled only at settled
            // post-edge points, then let it drain (real ack completes)
            // before moving on -- confirms this exact round's real
            // arrival, not a guessed number of cycles, is what got
            // consumed.
            while (adder_data_valid !== 1'b1) @(posedge clk);
            #1;
            while (adder_data_valid !== 1'b0) @(posedge clk);
            #1;
            upd = 1'b0;

            // Real, necessary settle cycle: one full real cycle after
            // the drain confirms LOOPVAR's own registered data_reg
            // update has genuinely landed before it's asked to reemit.
            @(posedge clk); #1;

            // 3. Reemit: LOOPVAR re-broadcasts its now-updated data_reg
            // onto the real east wire, giving the ADDER a fresh real A
            // for the NEXT call to this task (dummy west arrival is the
            // established real "second arrival" trigger, #629/#630/
            // #633/#635). Wait for the real capture to land before
            // returning, so the next call's own step 0 is never racing
            // this one.
            reemit = 1'b1;
            dummy_val = 32'hFFFFFFFF; dummy_pulse = 1'b1;
            @(posedge clk); #1;
            dummy_pulse = 1'b0; reemit = 1'b0;
            while (adder_a_arrived !== 1'b1) @(posedge clk);
            #1;
        end
    endtask

    initial begin
        $dumpfile("/tmp/tb_nano_adder_loop_v1.vcd");
        $dumpvars(0, tb_nano_adder_loop_v1);

        #12 rst = 0;
        @(posedge clk); #1;

        // LOOPVAR: PASS_A, routing east only.
        cfgL = 1; cfgL_d = 128'h0; cfgL_d[9:0] = TOPO_PASS_A; cfgL_d[69:64] = DIR_E6;
        // ADDER: downstream_mask=W (bit3, offers sum back to LOOPVAR),
        // upstream_mask=N|W (bit0=N for the const-B stand-in, bit3=W
        // for the real A operand from LOOPVAR), subtract_mode=0,
        // addon_config=0 (pure passthrough).
        cfgA = 1; cfgA_d = 64'h0;
        cfgA_d[5:0]  = 6'b001000;  // downstream_mask = W
        cfgA_d[11:6] = 6'b001001;  // upstream_mask   = N | W
        @(posedge clk); #1;
        cfgL = 0; cfgA = 0;
        repeat (2) @(posedge clk);

        // ── Real entry edge: seed LOOPVAR's held value to 0, exactly
        // as #635's own established two-arrival entry-seed sequence
        // (capture_now on the first west arrival, can_fire on the
        // second, which also performs the loop's first real offer). ──
        hold = 1'b1;
        entry_val = 32'd0; entry_pulse = 1'b1;
        @(posedge clk); #1;
        entry_pulse = 1'b0;
        repeat (2) @(posedge clk);
        dummy_val = 32'hDEADBEEF; dummy_pulse = 1'b1;   // real, established "ignored" second arrival
        @(posedge clk); #1;
        dummy_pulse = 1'b0;
        while (adder_a_arrived !== 1'b1) @(posedge clk);   // confirms the real entry offer actually landed in ADDER
        #1;
        report("entry-seed");
        check_data_reg(32'd0, "entry-seed");

        // ── Three real iterations: 0 -> 1 -> 2 -> 3, each hop computed
        // by the real adder_cell_v4 over the real cardinal wire. ──
        loop_iteration;
        report("iteration-1");
        check_data_reg(32'd1, "iteration-1 (0+1 via real adder)");

        loop_iteration;
        report("iteration-2");
        check_data_reg(32'd2, "iteration-2 (1+1 via real adder, carries forward)");

        loop_iteration;
        report("iteration-3");
        check_data_reg(32'd3, "iteration-3 (2+1 via real adder, carries forward)");

        if (checks == 4 && errors == 0)
            $display("PASS: real, genuine physical counting loop -- LOOPVAR (nano_gate_v4) and ADDER (adder_cell_v4) wired over a real cardinal link, LOOPVAR's held value incremented three times (0->1->2->3) by the real adder's own computed sum, not a testbench stand-in");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
