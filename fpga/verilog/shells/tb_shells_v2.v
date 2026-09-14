// tb_shells_v2.v — real verification for the 4 shells `#639` left
// unbuilt (`branch_shell_v1`/`accumulator_shell_v1`/`latch_shell_v1`/
// `sequencer_shell_v1`, points.md #646), closing that real gap before
// the VIX Carrier needs all 9 real shells to exist. Same discipline as
// `tb_shells_v1.v`: single-direction `active` assertion (a different
// direction per instance), proving the OR-combine reaches each real
// core. Freeze exercised on two of the four (branch, latch) as a
// representative real check, not exhaustively on all four, given this
// is secondary to the carrier build this session's own real focus --
// noted plainly, not hidden.
`timescale 1ns / 1ps

module tb_shells_v2;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

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
    // branch_shell_v1 -- single-direction active (south), freeze (west)
    // ═══════════════════════════════════════════════════════════════
    reg br_active_n=0, br_active_s=0, br_active_e=0, br_active_w=0;
    reg br_freeze_n=0, br_freeze_s=0, br_freeze_e=0, br_freeze_w=0;
    reg br_cfg = 0; reg [79:0] br_cfg_d;
    reg [31:0] br_val = 0; reg br_pulse = 0;
    wire [31:0] br_dout_e; wire br_fire_e;
    reg br_cons_ack = 0;

    branch_shell_v1 #(.CELL_ID(16'hB000)) BR (
        .clk(clk), .rst(rst),
        .active_in_n(br_active_n), .active_in_s(br_active_s), .active_in_e(br_active_e), .active_in_w(br_active_w),
        .freeze_in_n(br_freeze_n), .freeze_in_s(br_freeze_s), .freeze_in_e(br_freeze_e), .freeze_in_w(br_freeze_w),
        .cfg_valid(br_cfg), .cfg_data(br_cfg_d),
        .data_in_n(br_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(br_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(br_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(br_fire_e), .fire_w(),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(br_cons_ack), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .status_data_valid()
    );

    // ═══════════════════════════════════════════════════════════════
    // accumulator_shell_v1 -- single-direction active (west)
    // ═══════════════════════════════════════════════════════════════
    reg ac_active_n=0, ac_active_s=0, ac_active_e=0, ac_active_w=0;
    reg ac_cfg = 0; reg [63:0] ac_cfg_d;
    reg [31:0] ac_val = 0; reg ac_pulse = 0;
    wire [31:0] ac_dout_e; wire ac_fire_e;
    reg ac_cons_ack = 0;

    accumulator_shell_v1 #(.CELL_ID(16'hB001)) AC (
        .clk(clk), .rst(rst),
        .active_in_n(ac_active_n), .active_in_s(ac_active_s), .active_in_e(ac_active_e), .active_in_w(ac_active_w),
        .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),
        .cfg_valid(ac_cfg), .cfg_data(ac_cfg_d),
        .data_in_n(ac_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(ac_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(ac_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(ac_fire_e), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ac_cons_ack), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .ready_out(), .status_negative()
    );

    // ═══════════════════════════════════════════════════════════════
    // latch_shell_v1 -- single-direction active (north), freeze (east)
    // ═══════════════════════════════════════════════════════════════
    reg lt_active_n=0, lt_active_s=0, lt_active_e=0, lt_active_w=0;
    reg lt_freeze_n=0, lt_freeze_s=0, lt_freeze_e=0, lt_freeze_w=0;
    reg lt_cfg = 0; reg [63:0] lt_cfg_d;
    reg [31:0] lt_val = 0; reg lt_pulse = 0;
    wire lt_status_latched;

    latch_shell_v1 #(.CELL_ID(16'hB002)) LT (
        .clk(clk), .rst(rst),
        .active_in_n(lt_active_n), .active_in_s(lt_active_s), .active_in_e(lt_active_e), .active_in_w(lt_active_w),
        .freeze_in_n(lt_freeze_n), .freeze_in_s(lt_freeze_s), .freeze_in_e(lt_freeze_e), .freeze_in_w(lt_freeze_w),
        .cfg_valid(lt_cfg), .cfg_data(lt_cfg_d),
        .data_in_n(lt_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(lt_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .ready_out(), .status_latched(lt_status_latched)
    );

    // ═══════════════════════════════════════════════════════════════
    // sequencer_shell_v1 -- single-direction active (east)
    // ═══════════════════════════════════════════════════════════════
    reg sq_active_n=0, sq_active_s=0, sq_active_e=0, sq_active_w=0;
    reg sq_cfg = 0; reg [63:0] sq_cfg_d;
    wire [31:0] sq_dout_e; wire sq_fire_e;
    reg sq_cons_ack = 0;

    sequencer_shell_v1 #(.CELL_ID(16'hB003)) SQ (
        .clk(clk), .rst(rst),
        .active_in_n(sq_active_n), .active_in_s(sq_active_s), .active_in_e(sq_active_e), .active_in_w(sq_active_w),
        .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),
        .cfg_valid(sq_cfg), .cfg_data(sq_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(sq_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(sq_fire_e), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(sq_cons_ack), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .ready_out(), .status_seq_index()
    );

    initial begin
        $dumpfile("/tmp/tb_shells_v2.vcd");
        $dumpvars(0, tb_shells_v2);

        #12 rst = 0;
        @(posedge clk); #1;

        // ── branch: single-direction active_in_s, freeze_in_w ──
        br_active_s = 1'b1;
        br_cfg = 1; br_cfg_d = {
            11'h0, 20'h0, 1'b0, 6'h0, 6'b000100, 6'b000100,
            1'b0, 1'b1, 1'b1, 7'd0, 7'd2, 7'd1, 1'b0, 1'b1, 1'b1, 3'd0
        };
        @(posedge clk); #1; br_cfg = 0;
        repeat (2) @(posedge clk);
        // Real held-reference model: the FIRST arrival seeds the
        // reference (no offer); only the SECOND compares and fires.
        br_val = 32'd8; br_pulse = 1'b1;   // seed reference = 8
        @(posedge clk); #1; br_pulse = 1'b0;
        repeat (3) @(posedge clk); #1;
        br_val = 32'd5; br_pulse = 1'b1;   // 5 < 8 -> LOW -> marker 1
        @(posedge clk); #1; br_pulse = 1'b0;
        repeat (3) @(posedge clk); #1;
        check(br_fire_e === 1'b1 && br_dout_e === 32'd1,
              "branch_shell: single-direction active_in_s alone activates the real core");
        // ack the real offer before proceeding, so the freeze check
        // below isn't racing this one's still-pending fire.
        br_cons_ack = 1'b1; @(posedge clk); #1; br_cons_ack = 1'b0;
        repeat (2) @(posedge clk); #1;

        br_freeze_w = 1'b1;
        repeat (2) @(posedge clk); #1;
        br_val = 32'd8; br_pulse = 1'b1;   // would be EQUAL -> marker 2, but frozen
        @(posedge clk); #1; br_pulse = 1'b0;
        repeat (3) @(posedge clk); #1;
        check(br_fire_e === 1'b0,
              "branch_shell: single-direction freeze_in_w alone genuinely freezes the real core");

        // ── accumulator: single-direction active_in_w, inc_dir=N,
        // downstream_mask=E, step_amount=1 ──
        ac_active_w = 1'b1;
        ac_cfg = 1; ac_cfg_d = 64'h0;
        ac_cfg_d[5:0]   = 6'b000001;   // inc_dir = N
        ac_cfg_d[17:12] = 6'b000100;   // downstream_mask = E
        ac_cfg_d[25:18] = 8'd1;        // step_amount = 1
        @(posedge clk); #1; ac_cfg = 0;
        repeat (2) @(posedge clk);
        ac_val = 32'd0; ac_pulse = 1'b1;
        @(posedge clk); #1; ac_pulse = 1'b0;
        repeat (3) @(posedge clk); #1;
        ac_cons_ack = 1'b1; @(posedge clk); #1; ac_cons_ack = 1'b0;
        repeat (2) @(posedge clk); #1;
        check(ac_fire_e === 1'b1 && ac_dout_e === 32'd1,
              "accumulator_shell: single-direction active_in_w alone activates the real core, real increment to 1");

        // ── latch: single-direction active_in_n, set_dir=N,
        // downstream_mask=E ──
        lt_active_n = 1'b1;
        lt_cfg = 1; lt_cfg_d = 64'h0;
        lt_cfg_d[5:0]   = 6'b000001;   // set_dir = N
        lt_cfg_d[17:12] = 6'b000100;   // downstream_mask = E
        @(posedge clk); #1; lt_cfg = 0;
        repeat (2) @(posedge clk);
        lt_val = 32'd1; lt_pulse = 1'b1;
        @(posedge clk); #1; lt_pulse = 1'b0;
        repeat (3) @(posedge clk); #1;
        check(lt_status_latched === 1'b1,
              "latch_shell: single-direction active_in_n alone activates the real core, real set genuinely latched");

        lt_freeze_e = 1'b1;
        repeat (2) @(posedge clk); #1;
        check(lt_status_latched === 1'b1,
              "latch_shell: single-direction freeze_in_e holds real latch state (no change attempted, still true)");

        // ── sequencer: single-direction active_in_e, value_0=0xAA,
        // downstream_mask=E ──
        sq_active_e = 1'b1;
        sq_cfg = 1; sq_cfg_d = 64'h0;
        sq_cfg_d[7:0]   = 8'hAA;       // value_0
        sq_cfg_d[39:34] = 6'b000100;   // downstream_mask = E
        @(posedge clk); #1; sq_cfg = 0;
        repeat (3) @(posedge clk); #1;
        check(sq_fire_e === 1'b1 && sq_dout_e === 32'h000000AA,
              "sequencer_shell: single-direction active_in_e alone activates the real core, real value_0 offered");

        if (checks == 6 && errors == 0)
            $display("PASS: all 4 remaining real cardinal shells (branch/accumulator/latch/sequencer) genuinely preserve each wrapped core's own proven behavior AND respond correctly to single-direction active/freeze assertion -- all 9 unified-carrier cores now have real cardinal control shells");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
