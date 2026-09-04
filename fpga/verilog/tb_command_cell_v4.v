// tb_command_cell_v4.v — the first real testbench for the 9th unified-
// carrier core. Two real, separate instances under test:
//   CMD_TRIG: mode=0 (trigger), verifies the genuine symmetric toggle
//             (first match unfreezes, second match refreezes).
//   CMD_PROG: mode=1 (programmer), genuinely programs a real, fresh
//             (never cfg_valid'd) nano_gate_v4 TARGET end to end --
//             three real words (topology, routing_mask, COMPLETE)
//             relayed one at a time, each paced by the target's own
//             real, freeze-safe prog_ack_out, the last one recognized
//             via the shared toggle-pattern comparator and confirmed
//             before releasing the target's freeze. Then a real,
//             functional check: does the newly-configured TARGET
//             actually route data correctly, not just "were the words
//             relayed."
`timescale 1ns / 1ps

module tb_command_cell_v4;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [2:0] DIR_N = 3'd0, DIR_S = 3'd1, DIR_E = 3'd2, DIR_W = 3'd3;
    localparam [9:0] TOPO_PASS_A = 10'h000;
    localparam [3:0] DIR_E4 = 4'b0100;

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
    // CMD_TRIG -- trigger mode, genuine symmetric toggle
    // ═══════════════════════════════════════════════════════════════
    reg trig_cfg = 0; reg [63:0] trig_cfg_d;
    reg [31:0] trig_val = 0; reg trig_pulse = 0;
    wire trig_freeze_e, trig_ack_n;

    command_cell_v4 #(.CELL_ID(16'h9000)) CMD_TRIG (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(trig_cfg), .cfg_data(trig_cfg_d),
        .data_in_n(trig_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(trig_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .ack_out_n(trig_ack_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ready_out(),
        .freeze_out_n(), .freeze_out_s(), .freeze_out_e(trig_freeze_e), .freeze_out_w(),
        .program_out_n(), .program_out_s(), .program_out_e(), .program_out_w(),
        .prog_data_out_n(), .prog_data_out_s(), .prog_data_out_e(), .prog_data_out_w(),
        .prog_arrived_out_n(), .prog_arrived_out_s(), .prog_arrived_out_e(), .prog_arrived_out_w(),
        .prog_ack_in_n(1'b0), .prog_ack_in_s(1'b0), .prog_ack_in_e(1'b0), .prog_ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0),
        .status_active(), .status_freeze_state()
    );

    task trig_send(input [31:0] v);
        begin
            trig_val = v; trig_pulse = 1'b1;
            @(posedge clk); #1;
            trig_pulse = 1'b0;
            repeat (2) @(posedge clk); #1;
        end
    endtask

    // ═══════════════════════════════════════════════════════════════
    // CMD_PROG -- programmer mode, real end-to-end target programming
    // ═══════════════════════════════════════════════════════════════
    reg prog_cfg = 0; reg [63:0] prog_cfg_d;
    reg [31:0] buf_val = 0; reg buf_pulse = 0;
    wire prog_freeze_w, prog_out_w, prog_ack_n_buf;
    wire [31:0] prog_data_out_w; wire prog_arrived_out_w;
    wire tgt_prog_ack_out_e;
    wire cmd_prog_active;

    command_cell_v4 #(.CELL_ID(16'h9001)) CMD_PROG (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(prog_cfg), .cfg_data(prog_cfg_d),
        .data_in_n(buf_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(buf_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .ack_out_n(prog_ack_n_buf), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ready_out(),
        .freeze_out_n(), .freeze_out_s(), .freeze_out_e(), .freeze_out_w(prog_freeze_w),
        .program_out_n(), .program_out_s(), .program_out_e(), .program_out_w(prog_out_w),
        .prog_data_out_n(), .prog_data_out_s(), .prog_data_out_e(), .prog_data_out_w(prog_data_out_w),
        .prog_arrived_out_n(), .prog_arrived_out_s(), .prog_arrived_out_e(), .prog_arrived_out_w(prog_arrived_out_w),
        .prog_ack_in_n(1'b0), .prog_ack_in_s(1'b0), .prog_ack_in_e(1'b0), .prog_ack_in_w(tgt_prog_ack_out_e),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_in(1'b0),
        .status_active(cmd_prog_active), .status_freeze_state()
    );

    // ── TARGET: a real, fresh nano_gate_v4, never cfg_valid'd -- the
    // command cell programs it from scratch via the real programming
    // channel. CMD_PROG is west of TARGET (drive_dir=W), so
    // CMD_PROG's west port <-> TARGET's east port. ──
    wire [31:0] tgt_dout_e; wire tgt_fire_e;
    reg tgt_cons_ready = 1'b1; reg tgt_cons_ack = 0;
    reg tgt_west_pulse = 1'b0;   // unused ordinary arrival, kept low throughout

    nano_gate_v4 #(.CELL_ID(16'h9002), .ENABLE_DYNAMIC_ROUTING(1'b0)) TARGET (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(1'b0), .cfg_data(128'h0),   // never cfg_valid'd -- programmed live only
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'hCAFE0000),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(tgt_west_pulse),
        .data_out_n(), .data_out_s(), .data_out_e(tgt_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(tgt_fire_e), .fire_w(),
        .ready_out(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(tgt_cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(tgt_cons_ack), .ack_in_w(1'b0),
        .freeze_in(prog_freeze_w),
        .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(prog_out_w), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(prog_data_out_w), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(prog_arrived_out_w), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(tgt_prog_ack_out_e), .prog_ack_out_w()
    );

    // Send one real 32-bit word into CMD_PROG's watch side, wait for
    // it to be relayed to TARGET and confirmed via the real
    // freeze-safe prog_ack, before returning.
    task prog_send_word(input [31:0] w, input [255:0] label);
        begin
            buf_val = w; buf_pulse = 1'b1;
            @(posedge clk); #1;
            buf_pulse = 1'b0;
            // wait for CMD_PROG to actually offer it on the real
            // programming channel
            while (!prog_arrived_out_w) @(posedge clk);
            // wait for TARGET's own real prog_ack_out to confirm it
            while (!tgt_prog_ack_out_e) @(posedge clk);
            #1;
            $display("[t=%0t] %0s relayed and confirmed via real prog_ack", $time, label);
            @(posedge clk); #1;
        end
    endtask

    // ── Real, explicit, always-32-bit word construction -- avoids the
    // exact zero-extension trap found while building the first version
    // of this test (a concatenation narrower than 32 bits silently
    // misplaces the prog_id nibble on assignment to a 32-bit reg). ──
    function [31:0] make_word(input [3:0] pid, input [19:0] word);
        make_word = {8'h0, pid, word};
    endfunction

    initial begin
        $dumpfile("/tmp/tb_command_cell_v4.vcd");
        $dumpvars(0, tb_command_cell_v4);

        #12 rst = 0;
        @(posedge clk); #1;

        // ── CMD_TRIG config: mode=0 (trigger), polarity=0 (rest
        // frozen), drive_dir=E, toggle_pattern=4'hA. ──
        trig_cfg = 1; trig_cfg_d = 64'h0;
        trig_cfg_d[0]   = 1'b0;          // mode = trigger
        trig_cfg_d[1]   = 1'b0;          // polarity = rest frozen
        trig_cfg_d[4:2] = DIR_E;         // drive_dir = E
        trig_cfg_d[8:5] = 4'hA;          // toggle_pattern
        @(posedge clk); #1; trig_cfg = 0;
        repeat (2) @(posedge clk);

        check(trig_freeze_e === 1'b1, "trigger: rest state frozen (polarity=0) at reset");

        // Non-matching arrival: acked, but no toggle.
        trig_send(32'h00500000);   // [23:20] = 5, no match
        check(trig_freeze_e === 1'b1, "trigger: non-matching value does not toggle");

        // Matching arrival: toggles to unfrozen.
        trig_send(32'h00A00000);   // [23:20] = A, matches toggle_pattern
        check(trig_freeze_e === 1'b0, "trigger: first match unfreezes (real start-of-burst)");

        // Non-matching arrival while unfrozen: still no toggle.
        trig_send(32'h00100000);
        check(trig_freeze_e === 1'b0, "trigger: non-matching value while open still no toggle");

        // Second matching arrival: toggles back to frozen.
        trig_send(32'h00A00000);
        check(trig_freeze_e === 1'b1, "trigger: second match refreezes (real end-of-burst)");

        // ── CMD_PROG config: mode=1 (programmer), drive_dir=W
        // (TARGET sits west), toggle_pattern=4'hF (matches nano's own
        // real PROG_ID_COMPLETE=4'd15 at [23:20]). ──
        prog_cfg = 1; prog_cfg_d = 64'h0;
        prog_cfg_d[0]   = 1'b1;          // mode = programmer
        prog_cfg_d[4:2] = DIR_W;         // drive_dir = W
        prog_cfg_d[8:5] = 4'hF;          // toggle_pattern = nano's real COMPLETE
        @(posedge clk); #1; prog_cfg = 0;
        repeat (2) @(posedge clk);

        check(prog_freeze_w === 1'b0 && cmd_prog_active === 1'b0, "programmer: idle at reset, target not yet frozen");

        // Real word 1: TARGET's topology = PASS_A (PROG_ID=0, value=0).
        prog_send_word(make_word(4'h0, {10'h0, TOPO_PASS_A}), "word1 (topology=PASS_A)");
        check(prog_freeze_w === 1'b1, "programmer: target frozen during the real burst");
        check(cmd_prog_active === 1'b1, "programmer: still active after a non-terminal word");

        // Real word 2: TARGET's routing_mask = E (PROG_ID=1, value=DIR_E4).
        prog_send_word(make_word(4'h1, {16'h0, DIR_E4}), "word2 (routing_mask=E)");
        check(cmd_prog_active === 1'b1, "programmer: still active after second non-terminal word");

        // Real word 3: COMPLETE (PROG_ID=15, value=1 to arm).
        prog_send_word(make_word(4'hF, {19'h0, 1'b1}), "word3 (COMPLETE, arm=1)");
        check(cmd_prog_active === 1'b0, "programmer: recognized+confirmed COMPLETE, deactivated");
        check(prog_freeze_w === 1'b0, "programmer: released the target's freeze after COMPLETE");

        // ── Real, functional check: did TARGET actually get
        // configured correctly, not just "were words relayed"? Feed
        // it a real arrival on its own west port and confirm it
        // captures+fires east per the real routing_mask+topology just
        // programmed live. ──
        tgt_west_pulse = 1'b1;
        @(posedge clk); #1;
        tgt_west_pulse = 1'b0;
        repeat (2) @(posedge clk); #1;
        tgt_west_pulse = 1'b1;   // second real arrival triggers the real two-arrival fire
        @(posedge clk); #1;
        tgt_west_pulse = 1'b0;
        repeat (3) @(posedge clk); #1;
        check(tgt_fire_e === 1'b1 && tgt_dout_e === 32'hCAFE0000,
              "real functional check: TARGET, programmed live from scratch, genuinely routes west-to-east per its newly-set topology+routing_mask");
        tgt_cons_ack = 1'b1; @(posedge clk); #1; tgt_cons_ack = 1'b0;

        if (checks == 12 && errors == 0)
            $display("PASS: command_cell_v4 -- trigger mode's genuine symmetric toggle (4/4 real cases) AND programmer mode genuinely programming a real, fresh nano_gate_v4 target end to end (3 real words, freeze-safe prog_ack pacing, toggle-pattern-recognized COMPLETE, real functional confirmation the target actually works afterward)");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
