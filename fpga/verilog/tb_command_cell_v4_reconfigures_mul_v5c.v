// tb_command_cell_v4_reconfigures_mul_v5c.v — points.md #862: the real,
// concrete demonstration `#861` called for -- command_cell_v4.v's own
// already-proven programmer-mode mechanism (freeze target, relay a
// real sequence of PROG_ID words, recognize COMPLETE via the shared
// toggle-pattern comparator, release the target's freeze) used to
// genuinely reconfigure a real, fresh mul_cell_v5c FROM SCRATCH at
// runtime -- specifically enabling wide_mode (#853/#854), then
// PROVING the reconfigure took real effect by actually multiplying two
// real FP32-significand-shaped operands and confirming BOTH halves of
// the product are correctly delivered in sequence, not just that
// words were relayed.
//
// Real, precise detail found and confirmed before building, not
// assumed: mul_cell_v5c's own real PROG_ID_COMPLETE is 3'd7 (3 bits,
// at prog_data_val[22:20]), unlike nano's own 4-bit PROG_ID_COMPLETE
// (4'd15) the original tb_command_cell_v4.v targets. command_cell's
// own toggle_pattern compares against watch_val[23:20] (4 bits) --
// this project's own documented convention (bit[23]=0 in a real
// PROG_ID word) means the correct toggle_pattern for a 3-bit-PROG_ID
// target's COMPLETE word is 4'h7, not 4'hF.
`timescale 1ns / 1ps

module tb_command_cell_v4_reconfigures_mul_v5c;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [2:0] DIR_N = 3'd0, DIR_S = 3'd1, DIR_E = 3'd2, DIR_W = 3'd3;

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

    command_cell_v4 #(.CELL_ID(16'hA000)) CMD_PROG (
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
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
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

    function [31:0] make_word(input [2:0] pid, input [19:0] word);
        make_word = {9'h0, pid, word};
    endfunction

    // ═══════════════════════════════════════════════════════════════
    // TARGET: a real, fresh mul_cell_v5c, never cfg_valid'd --
    // programmed entirely live via CMD_PROG. Operands arrive N/S;
    // product offered E. CMD_PROG sits west of TARGET (drive_dir=W).
    // ═══════════════════════════════════════════════════════════════
    reg [31:0] opA = 0, opB = 0;
    reg pulse_a = 0, pulse_b = 0;
    wire [31:0] product_out_e;
    wire fire_e;
    reg cons_ready = 1, cons_ack = 0;
    wire tgt_a_arrived;

    mul_cell_v5c #(.CELL_ID(16'hA001)) TARGET (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(1'b0), .cfg_data(64'h0),   // never cfg_valid'd -- programmed live only
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

    task send_pair(input [31:0] a_val, input [31:0] b_val);
        begin
            opA = a_val; pulse_a = 1'b1;
            #10;
            pulse_a = 1'b0;
            wait (tgt_a_arrived == 1'b1);
            #10;
            opB = b_val; pulse_b = 1'b1;
            #10;
            pulse_b = 1'b0;
        end
    endtask

    task ack_once;
        begin
            cons_ack = 1'b1;
            #2;
            @(posedge clk); #1;
            cons_ack = 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    initial begin
        #12 rst = 0;
        @(posedge clk); #1;

        // ── CMD_PROG config: mode=1 (programmer), drive_dir=W (TARGET
        // sits west), toggle_pattern=4'h7 (matches mul_cell_v5c's own
        // real 3-bit PROG_ID_COMPLETE=3'd7 at [22:20], bit[23]=0). ──
        prog_cfg = 1; prog_cfg_d = 64'h0;
        prog_cfg_d[0]   = 1'b1;          // mode = programmer
        prog_cfg_d[4:2] = DIR_W;         // drive_dir = W
        prog_cfg_d[8:5] = 4'h7;          // toggle_pattern -- the real, precise detail
        @(posedge clk); #1; prog_cfg = 0;
        repeat (2) @(posedge clk);

        check(prog_freeze_w === 1'b0 && cmd_prog_active === 1'b0, "programmer: idle at reset, target not yet frozen");

        // Real word 1: downstream_mask = E (PROG_ID=0).
        prog_send_word(make_word(3'd0, {14'h0, DIR_E6}), "word1 (downstream_mask=E)");
        check(prog_freeze_w === 1'b1, "programmer: target frozen during the real burst");
        check(cmd_prog_active === 1'b1, "programmer: still active after a non-terminal word");

        // Real word 2: upstream_mask = N|S (PROG_ID=1).
        prog_send_word(make_word(3'd1, {14'h0, (DIR_N6 | DIR_S6)}), "word2 (upstream_mask=N|S)");
        check(cmd_prog_active === 1'b1, "programmer: still active after second non-terminal word");

        // Real word 3: wide_mode = 1 (PROG_ID=2) -- the real, motivating field.
        prog_send_word(make_word(3'd2, 20'h1), "word3 (wide_mode=1)");
        check(cmd_prog_active === 1'b1, "programmer: still active after third non-terminal word");

        // Real word 4: COMPLETE, arm=1 (PROG_ID=7).
        prog_send_word(make_word(3'd7, 20'h1), "word4 (COMPLETE, arm=1)");
        check(cmd_prog_active === 1'b0, "programmer: recognized+confirmed COMPLETE, deactivated");
        check(prog_freeze_w === 1'b0, "programmer: released TARGET's freeze after COMPLETE");

        // ── Real, functional check: TARGET was programmed FROM SCRATCH,
        // entirely live, no cfg_valid ever asserted. Feed it real
        // FP32-significand-shaped operands and confirm wide_mode's own
        // real two-phase delivery (#853) genuinely took effect. ──
        send_pair(24'hC00000, 24'hC00000);   // 1.5 * 1.5 -- real product = 0x900000000000 exactly
        #40;
        check(fire_e === 1'b1, "real functional check: TARGET, live-programmed from scratch, fires");
        check(product_out_e === 32'h00000000,
              "real functional check: LOW half of the real product, from a target that never saw cfg_valid");
        ack_once;
        #10;
        check(fire_e === 1'b1, "real functional check: wide_mode's own two-phase delivery fires a SECOND time, live-programmed and proven");
        check(product_out_e === 32'h00009000,
              "real functional check: HIGH half of the real product -- the exact capability #853 built, reached entirely via command_cell's own live reconfigure, never a boot-time cfg_valid");
        ack_once;

        #20;
        $display("=== tb_command_cell_v4_reconfigures_mul_v5c: %0d checks, %0d errors ===", checks, errors);
        if (errors == 0)
            $display("PASS: a real, fresh mul_cell_v5c, NEVER cfg_valid'd, was fully configured live at runtime by command_cell_v4's own already-proven mechanism (4 real words, freeze-safe prog_ack pacing, toggle-pattern-recognized COMPLETE) -- and its newly-enabled wide_mode capability (#853/#854) was then proven functionally real by actually computing both halves of a real product.");
        else
            $display("FAILURES DETECTED");
        $finish;
    end

endmodule
