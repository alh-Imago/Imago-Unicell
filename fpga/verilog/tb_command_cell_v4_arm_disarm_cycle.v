// tb_command_cell_v4_arm_disarm_cycle.v — points.md #863: the real,
// missing piece from #862 -- proves command_cell's own real, already-
// existing `armed` field (set via its own PROG_ID_COMPLETE=3'd7,
// `armed <= prog_word[0]`, confirmed to NEVER auto-clear on its own)
// gives exactly the "start trigger required, reset until re-armed"
// behaviour Alan described, using zero new RTL -- just the two real,
// separate channels command_cell already has: its own incremental
// reprogram channel (managing itself, arm/disarm) and its ordinary
// buffer channel (carrying the real reconfigure sequence toward the
// target, #644/#862's own already-proven mechanism).
//
// Real, complete sequence proven, standing in (by direct testbench
// stimulus, same honest scope #862 already carries) for a real
// section's own drain-latch SET/CLEAR events (#858):
//   1. Command cell starts DISARMED. A real reconfigure sequence sent
//      to its ordinary buffer while disarmed is genuinely IGNORED --
//      the target is never touched.
//   2. A real incremental reprogram word (PROG_ID=7, value=1) ARMS it
//      -- standing in for the drain-latch's own SET event (a new pass
//      beginning).
//   3. The SAME reconfigure sequence, sent again, now correctly runs
//      end to end (matching #862 exactly) -- standing in for the
//      drain-latch's own CLEAR event (drain complete).
//   4. A real incremental reprogram word (PROG_ID=7, value=0) DISARMS
//      it again, as the deliberate FINAL step of the real sequence --
//      the one design choice #862 didn't yet need: going properly deaf
//      again immediately after completing, not staying armed forever.
//   5. A SECOND attempt to send the reconfigure sequence, without
//      re-arming, is genuinely IGNORED -- proving the disarm actually
//      prevents a spurious re-trigger, standing in for a latch that
//      keeps re-offering "drained" repeatedly.
//   6. A SECOND real arm word re-arms it, and the sequence runs
//      correctly a SECOND time -- the real, decisive proof that this
//      is a genuine, repeatable CYCLE, not a one-shot event -- exactly
//      what a real fold/reconfigure loop (#843) needs.
`timescale 1ns / 1ps

module tb_command_cell_v4_arm_disarm_cycle;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [2:0] DIR_N = 3'd0, DIR_S = 3'd1, DIR_E = 3'd2, DIR_W = 3'd3;
    localparam [2:0] CMD_PROG_ID_COMPLETE = 3'd7;

    integer errors = 0;
    integer checks = 0;

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

    // ═══════════════════════════════════════════════════════════════
    // CMD_PROG -- command_cell_v4, programmer mode
    // ═══════════════════════════════════════════════════════════════
    reg prog_cfg = 0; reg [63:0] prog_cfg_d;
    reg [31:0] buf_val = 0; reg buf_pulse = 0;
    wire prog_freeze_w, prog_out_w;
    wire [31:0] prog_data_out_w; wire prog_arrived_out_w;
    wire tgt_prog_ack_out_e;
    wire cmd_prog_active;

    // Real, separate channel: reprogramming CMD_PROG ITSELF (arm/disarm),
    // distinct from the buffer that feeds the target.
    reg self_prog_in = 0;
    reg [31:0] self_prog_data = 0;
    reg self_prog_pulse = 0;

    command_cell_v4 #(.CELL_ID(16'hB000)) CMD_PROG (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(prog_cfg), .cfg_data(prog_cfg_d),
        .data_in_n(buf_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(buf_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ready_out(),
        .freeze_out_n(), .freeze_out_s(), .freeze_out_e(), .freeze_out_w(prog_freeze_w),
        .program_out_n(), .program_out_s(), .program_out_e(), .program_out_w(prog_out_w),
        .prog_data_out_n(), .prog_data_out_s(), .prog_data_out_e(), .prog_data_out_w(prog_data_out_w),
        .prog_arrived_out_n(), .prog_arrived_out_s(), .prog_arrived_out_e(), .prog_arrived_out_w(prog_arrived_out_w),
        .prog_ack_in_n(1'b0), .prog_ack_in_s(1'b0), .prog_ack_in_e(1'b0), .prog_ack_in_w(tgt_prog_ack_out_e),
        // CMD_PROG's OWN incremental reprogram channel -- self-management,
        // fed on its own north side (real, separate from the S/E/W used elsewhere).
        .program_in(self_prog_in), .program_done(),
        .prog_data_in_n(self_prog_data), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(self_prog_pulse), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0),
        .status_active(cmd_prog_active), .status_freeze_state()
    );

    task prog_send_word(input [31:0] w, input [255:0] label);
        begin
            buf_val = w; buf_pulse = 1'b1;
            @(posedge clk); #1;
            buf_pulse = 1'b0;
            while (!prog_arrived_out_w) @(posedge clk);
            while (!tgt_prog_ack_out_e) @(posedge clk);
            #1;
            $display("[t=%0t] %0s relayed and confirmed via real prog_ack", $time, label);
            @(posedge clk); #1;
        end
    endtask

    // Real, necessary distinction from prog_send_word: this attempts a
    // send while CMD_PROG may be DISARMED -- it must NOT assume the
    // word gets relayed, since ready_out itself is gated on
    // effective_armed. Waits a bounded, generous window then reports
    // whether the word was ever actually relayed onward.
    task attempt_send_while_maybe_disarmed(input [31:0] w, input [255:0] label);
        begin
            buf_val = w; buf_pulse = 1'b1;
            @(posedge clk); #1;
            buf_pulse = 1'b0;
            repeat (5) @(posedge clk);
            #1;
            $display("[t=%0t] %0s attempted -- prog_arrived_out_w=%b (0 means correctly ignored while disarmed)",
                      $time, label, prog_arrived_out_w);
        end
    endtask

    task self_reprogram(input value, input [255:0] label);
        begin
            self_prog_in = 1'b1;
            self_prog_data = {9'h0, CMD_PROG_ID_COMPLETE, 19'h0, value};
            self_prog_pulse = 1'b1;
            @(posedge clk); #1;
            self_prog_pulse = 1'b0;
            repeat (2) @(posedge clk); #1;
            self_prog_in = 1'b0;
            repeat (2) @(posedge clk);
            $display("[t=%0t] %0s (armed<=%0d)", $time, label, value);
        end
    endtask

    function [31:0] make_word(input [2:0] pid, input [19:0] word);
        make_word = {9'h0, pid, word};
    endfunction

    // ═══════════════════════════════════════════════════════════════
    // TARGET: a real, fresh mul_cell_v5c, never cfg_valid'd -- same
    // real target #862 already proved, reused here for continuity.
    // ═══════════════════════════════════════════════════════════════
    reg [31:0] opA = 0, opB = 0;
    reg pulse_a = 0, pulse_b = 0;
    wire [31:0] product_out_e;
    wire fire_e;
    reg cons_ready = 1, cons_ack = 0;
    wire tgt_a_arrived;

    mul_cell_v5c #(.CELL_ID(16'hB001)) TARGET (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(1'b0), .cfg_data(64'h0),
        .data_in_n(opA), .data_in_s(opB), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(pulse_a), .arrived_s(pulse_b), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(product_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .program_in(prog_out_w), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(prog_data_out_w), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(prog_arrived_out_w), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(tgt_prog_ack_out_e), .prog_ack_out_w(),
        .freeze_in(prog_freeze_w),
        .status_data_valid(), .status_a_arrived(tgt_a_arrived)
    );

    localparam [5:0] DIR_N6 = 6'b000001, DIR_S6 = 6'b000010, DIR_E6 = 6'b000100;

    task run_reconfigure_sequence;
        begin
            prog_send_word(make_word(3'd0, {14'h0, DIR_E6}), "downstream_mask=E");
            prog_send_word(make_word(3'd1, {14'h0, (DIR_N6 | DIR_S6)}), "upstream_mask=N|S");
            prog_send_word(make_word(3'd2, 20'h1), "wide_mode=1");
            prog_send_word(make_word(3'd7, 20'h1), "COMPLETE (target's own, arm=1)");
        end
    endtask

    initial begin
        #12 rst = 0;
        @(posedge clk); #1;

        prog_cfg = 1; prog_cfg_d = 64'h0;
        prog_cfg_d[0]   = 1'b1;          // mode = programmer
        prog_cfg_d[4:2] = DIR_W;         // drive_dir = W
        prog_cfg_d[8:5] = 4'h7;          // toggle_pattern -- matches mul_cell_v5c's own real COMPLETE
        @(posedge clk); #1; prog_cfg = 0;
        repeat (2) @(posedge clk);

        // ── Real, necessary correction: cfg_valid unconditionally
        // arms CMD_PROG (confirmed directly, line 303) -- explicitly
        // disarm it right after setup, to start in the real, deliberate
        // "reset, awaiting a start trigger" state Alan described. ──
        self_reprogram(1'b0, "explicit disarm after cfg_valid setup");

        // ── Step 1: attempt the real sequence while DISARMED. ──
        attempt_send_while_maybe_disarmed(make_word(3'd0, {14'h0, DIR_E6}), "word1 while disarmed");
        check(prog_freeze_w === 1'b0, "disarmed: target genuinely never frozen -- the sequence was correctly ignored");
        check(cmd_prog_active === 1'b0, "disarmed: command cell never became active");

        // ── Step 2: the real 'start trigger' -- arm it. ──
        self_reprogram(1'b1, "real start trigger");

        // ── Step 3: the SAME sequence now runs correctly, end to end. ──
        run_reconfigure_sequence;
        check(cmd_prog_active === 1'b0, "armed: recognized+confirmed COMPLETE, deactivated");
        check(prog_freeze_w === 1'b0, "armed: released TARGET's freeze after COMPLETE");

        // Real functional check: TARGET genuinely reconfigured.
        opA = 24'hC00000; pulse_a = 1'b1; #10; pulse_a = 1'b0;
        wait (tgt_a_arrived == 1'b1); #10;
        opB = 24'hC00000; pulse_b = 1'b1; #10; pulse_b = 1'b0;
        #40;
        check(fire_e === 1'b1 && product_out_e === 32'h00000000, "pass 1: TARGET's LOW half correct after live reconfigure");
        cons_ack = 1'b1; #2; @(posedge clk); #1; cons_ack = 1'b0; repeat (2) @(posedge clk);
        #10;
        check(fire_e === 1'b1 && product_out_e === 32'h00009000, "pass 1: TARGET's HIGH half correct -- wide_mode genuinely live");
        cons_ack = 1'b1; #2; @(posedge clk); #1; cons_ack = 1'b0; repeat (2) @(posedge clk);

        // ── Step 4: the real, deliberate final step -- disarm again. ──
        self_reprogram(1'b0, "real end-of-cycle disarm");

        // ── Step 5: a SECOND attempt, without re-arming, standing in
        // for a latch that keeps re-offering 'drained' repeatedly --
        // must be genuinely ignored. ──
        attempt_send_while_maybe_disarmed(make_word(3'd0, {14'h0, DIR_E6}), "spurious repeat while disarmed");
        check(cmd_prog_active === 1'b0, "disarmed again: the spurious repeat did NOT restart anything");

        // ── Step 6: the real, decisive proof -- re-arm and run AGAIN.
        // If this works, the mechanism is a genuine, repeatable CYCLE,
        // not a one-shot event. ──
        self_reprogram(1'b1, "real second start trigger");
        run_reconfigure_sequence;
        check(cmd_prog_active === 1'b0, "pass 2: recognized+confirmed COMPLETE a SECOND time");
        check(prog_freeze_w === 1'b0, "pass 2: released TARGET's freeze again");

        opA = 24'hFFFFFF; pulse_a = 1'b1; #10; pulse_a = 1'b0;
        wait (tgt_a_arrived == 1'b1); #10;
        opB = 24'hFFFFFF; pulse_b = 1'b1; #10; pulse_b = 1'b0;
        #40;
        check(fire_e === 1'b1 && product_out_e === 32'hFE000001, "pass 2: TARGET's LOW half correct -- the cycle genuinely repeats");
        cons_ack = 1'b1; #2; @(posedge clk); #1; cons_ack = 1'b0; repeat (2) @(posedge clk);
        #10;
        check(fire_e === 1'b1 && product_out_e === 32'h0000FFFF, "pass 2: TARGET's HIGH half correct -- a real, second, independent reconfigure-and-compute cycle");
        cons_ack = 1'b1; #2; @(posedge clk); #1; cons_ack = 1'b0; repeat (2) @(posedge clk);

        #20;
        $display("=== tb_command_cell_v4_arm_disarm_cycle: %0d checks, %0d errors ===", checks, errors);
        if (errors == 0)
            $display("PASS: command_cell's own real, existing 'armed' field, driven via its own separate incremental reprogram channel, gives exactly the 'explicit start trigger, reset until re-armed' behaviour -- proven as a genuine, REPEATABLE cycle (two full, independent reconfigure-and-compute passes), not a one-shot event. No new RTL needed.");
        else
            $display("FAILURES DETECTED");
        $finish;
    end

endmodule
