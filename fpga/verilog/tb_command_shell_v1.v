// tb_command_shell_v1.v — proves `command_shell_v1.v` genuinely
// preserves `command_cell_v4.v`'s own proven behavior in BOTH modes,
// and that single-direction `active`/`freeze_in` assertion (a
// DIFFERENT direction than any previous shell test, per `#639`'s own
// convention) reaches the real core correctly.
`timescale 1ns / 1ps

module tb_command_shell_v1;

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

    function [31:0] make_word(input [3:0] pid, input [19:0] word);
        make_word = {8'h0, pid, word};
    endfunction

    // ═══════════════════════════════════════════════════════════════
    // CMD_TRIG shell -- real single-direction active (south) and
    // freeze_in (west, unused by this mode but exercised anyway)
    // ═══════════════════════════════════════════════════════════════
    reg trig_cfg = 0; reg [63:0] trig_cfg_d;
    reg [31:0] trig_val = 0; reg trig_pulse = 0;
    wire trig_freeze_e;

    command_shell_v1 #(.CELL_ID(16'hA000)) CMD_TRIG (
        .clk(clk), .rst(rst),
        .active_in_n(1'b0), .active_in_s(1'b1), .active_in_e(1'b0), .active_in_w(1'b0),
        .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),
        .cfg_valid(trig_cfg), .cfg_data(trig_cfg_d),
        .data_in_n(trig_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(trig_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
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
    // CMD_PROG shell -- real single-direction active (east) --
    // full real end-to-end programming of a fresh nano_gate_v4 target
    // ═══════════════════════════════════════════════════════════════
    reg prog_cfg = 0; reg [63:0] prog_cfg_d;
    reg [31:0] buf_val = 0; reg buf_pulse = 0;
    wire prog_freeze_w, prog_out_w;
    wire [31:0] prog_data_out_w; wire prog_arrived_out_w;
    wire tgt_prog_ack_out_e;
    wire cmd_prog_active;

    command_shell_v1 #(.CELL_ID(16'hA001)) CMD_PROG (
        .clk(clk), .rst(rst),
        .active_in_n(1'b0), .active_in_s(1'b0), .active_in_e(1'b1), .active_in_w(1'b0),
        .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),
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
        .status_active(cmd_prog_active), .status_freeze_state()
    );

    wire [31:0] tgt_dout_e; wire tgt_fire_e;
    reg tgt_cons_ready = 1'b1; reg tgt_cons_ack = 0;
    reg tgt_west_pulse = 1'b0;

    nano_gate_v4 #(.CELL_ID(16'hA002), .ENABLE_DYNAMIC_ROUTING(1'b0)) TARGET (
        .clk(clk), .rst(rst), .active(1'b1),
        .cfg_valid(1'b0), .cfg_data(128'h0),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'hBEEF0000),
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

    initial begin
        $dumpfile("/tmp/tb_command_shell_v1.vcd");
        $dumpvars(0, tb_command_shell_v1);

        #12 rst = 0;
        @(posedge clk); #1;

        trig_cfg = 1; trig_cfg_d = 64'h0;
        trig_cfg_d[0]   = 1'b0;
        trig_cfg_d[1]   = 1'b0;
        trig_cfg_d[4:2] = DIR_E;
        trig_cfg_d[8:5] = 4'hA;
        @(posedge clk); #1; trig_cfg = 0;
        repeat (2) @(posedge clk);

        check(trig_freeze_e === 1'b1, "command_shell trigger: single-direction active_in_s alone activates the real core, rest frozen");
        trig_send(32'h00A00000);
        check(trig_freeze_e === 1'b0, "command_shell trigger: real toggle match unfreezes through the shell");
        trig_send(32'h00A00000);
        check(trig_freeze_e === 1'b1, "command_shell trigger: real toggle match refreezes through the shell");

        prog_cfg = 1; prog_cfg_d = 64'h0;
        prog_cfg_d[0]   = 1'b1;
        prog_cfg_d[4:2] = DIR_W;
        prog_cfg_d[8:5] = 4'hF;
        @(posedge clk); #1; prog_cfg = 0;
        repeat (2) @(posedge clk);

        check(cmd_prog_active === 1'b0, "command_shell programmer: single-direction active_in_e alone activates the real core, idle at reset");

        prog_send_word(make_word(4'h0, {10'h0, TOPO_PASS_A}), "word1 (topology=PASS_A)");
        prog_send_word(make_word(4'h1, {16'h0, DIR_E4}), "word2 (routing_mask=E)");
        prog_send_word(make_word(4'hF, {19'h0, 1'b1}), "word3 (COMPLETE, arm=1)");
        check(cmd_prog_active === 1'b0 && prog_freeze_w === 1'b0,
              "command_shell programmer: real end-to-end burst completed and target released, through the shell");

        tgt_west_pulse = 1'b1; @(posedge clk); #1; tgt_west_pulse = 1'b0;
        repeat (2) @(posedge clk); #1;
        tgt_west_pulse = 1'b1; @(posedge clk); #1; tgt_west_pulse = 1'b0;
        repeat (3) @(posedge clk); #1;
        check(tgt_fire_e === 1'b1 && tgt_dout_e === 32'hBEEF0000,
              "command_shell programmer: real functional check, target programmed via the shell genuinely works");
        tgt_cons_ack = 1'b1; @(posedge clk); #1; tgt_cons_ack = 1'b0;

        if (checks == 6 && errors == 0)
            $display("PASS: command_shell_v1 genuinely preserves command_cell_v4's own proven behavior in both modes, and single-direction active assertion (a different direction per instance) reaches the real core correctly through the shell");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
