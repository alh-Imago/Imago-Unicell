// tb_vix_carrier_priority_v1.v — points.md #731: the real, first proof
// that priority (SEL_PRIORITY, the 11th core, #730) genuinely works
// through VIX carrier's own real core_select routing, not just
// standalone. Real, deliberately narrow scope, matching this whole
// project's own established discipline: prove the NEW thing (SEL_
// PRIORITY routes real, competing arrivals through the carrier and
// arbitrates them correctly, in both real scheduling modes) without
// re-proving what the five existing VIX testbenches (re-run and
// confirmed passing unchanged alongside this one) already cover.
`timescale 1ns / 1ps

module tb_vix_carrier_priority_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [4:0] SEL_PRIORITY = 5'd10;
    localparam [5:0] DIR_N6 = 6'b000001, DIR_W6 = 6'b001000, DIR_E6 = 6'b000100;

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

    reg cfg = 0; reg [159:0] cfg_d;
    reg [31:0] val_n = 0, val_w = 0; reg pulse_n = 0, pulse_w = 0;
    wire [31:0] dout_e; wire fire_e;
    reg cons_ready = 1'b1; reg cons_ack = 0;
    reg program_in = 0; reg [31:0] prog_data_n = 0; reg prog_arr_n = 0;
    wire prog_ack_n;
    wire fz_n, fz_s, fz_e, fz_w, po_n, po_s, po_e, po_w;
    wire [31:0] pdo_n, pdo_s, pdo_e, pdo_w;
    wire pao_n, pao_s, pao_e, pao_w;
    reg pai_n = 0, pai_s = 0, pai_e = 0, pai_w = 0;

    unicell_vix_carrier_v1 #(.CELL_ID(16'hC400)) VIX (
        .clk(clk), .rst(rst),
        .active_in_n(1'b1), .active_in_s(1'b0), .active_in_e(1'b0), .active_in_w(1'b0),
        .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(val_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(val_w),
        .arrived_n(pulse_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(pulse_w),
        .data_out_n(), .data_out_s(), .data_out_e(dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .program_in(program_in), .program_done(),
        .prog_data_in_n(prog_data_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(prog_arr_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(prog_ack_n), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
        .freeze_out_n(fz_n), .freeze_out_s(fz_s), .freeze_out_e(fz_e), .freeze_out_w(fz_w),
        .program_out_n(po_n), .program_out_s(po_s), .program_out_e(po_e), .program_out_w(po_w),
        .prog_data_out_n(pdo_n), .prog_data_out_s(pdo_s), .prog_data_out_e(pdo_e), .prog_data_out_w(pdo_w),
        .prog_arrived_out_n(pao_n), .prog_arrived_out_s(pao_s), .prog_arrived_out_e(pao_e), .prog_arrived_out_w(pao_w),
        .prog_ack_in_n(pai_n), .prog_ack_in_s(pai_s), .prog_ack_in_e(pai_e), .prog_ack_in_w(pai_w),
        .status_core_select()
    );

    // cfg_data[159:0]: [4:0]core_select [132:5]core_config
    // priority's own cfg_data[63:0]: [5:0]up [11:6]down [13:12]rank_n
    // [15:14]rank_s [17:16]rank_e [19:18]rank_w [20]sched_mode
    task configure_priority(input [5:0] upstream_mask, input [5:0] downstream_mask,
                             input [1:0] rank_n, input [1:0] rank_w, input sched_mode);
        begin
            cfg = 1'b1;
            cfg_d = 160'h0;
            cfg_d[4:0] = SEL_PRIORITY;
            cfg_d[132:5] = {43'h0, sched_mode, rank_w, 2'h0, 2'h0, rank_n, downstream_mask, upstream_mask};
            @(posedge clk); #1; cfg = 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    initial begin
        $dumpfile("/tmp/tb_vix_carrier_priority_v1.vcd");
        $dumpvars(0, tb_vix_carrier_priority_v1);

        #12 rst = 0;
        @(posedge clk); #1;

        // ── Case 1: real, simultaneous arrival on N (rank 0, higher
        // priority) and W (rank 1), strict mode. Confirm N's own value
        // is offered first through the carrier's own real routing. ──
        configure_priority(DIR_N6 | DIR_W6, DIR_E6, 2'd0, 2'd1, 1'b0);
        val_n = 32'hAAAA0001; val_w = 32'hBBBB0002;
        pulse_n = 1'b1; pulse_w = 1'b1;
        #30;
        pulse_n = 1'b0;
        wait (fire_e === 1'b1);
        check(dout_e === 32'hAAAA0001,
              "VIX/priority: strict mode routes and offers N's own (higher-rank) value first, through the carrier");
        cons_ack = 1'b1; repeat (2) @(posedge clk); cons_ack = 1'b0;
        repeat (4) @(posedge clk);

        // W's own held arrival is served on its own turn next.
        wait (fire_e === 1'b1);
        pulse_w = 1'b0;
        check(dout_e === 32'hBBBB0002,
              "VIX/priority: W's own genuinely-held arrival is correctly served on its own turn, through the carrier");
        cons_ack = 1'b1; repeat (2) @(posedge clk); cons_ack = 1'b0;
        repeat (4) @(posedge clk);

        // ── Case 2: weighted round-robin mode, weight 3:1, through the
        // carrier's own real routing -- confirm a proportional,
        // interleaved service pattern, not starvation. ──
        configure_priority(DIR_N6 | DIR_W6, DIR_E6, 2'd3, 2'd1, 1'b1);
        val_n = 32'hE0000000; val_w = 32'hF0000000;
        pulse_n = 1'b1; pulse_w = 1'b1;

        begin : rr_test
            integer i, n_wins, w_wins;
            n_wins = 0; w_wins = 0;
            for (i = 0; i < 8; i = i + 1) begin
                wait (fire_e === 1'b1);
                if (dout_e == 32'hE0000000) n_wins = n_wins + 1;
                else if (dout_e == 32'hF0000000) w_wins = w_wins + 1;
                cons_ack = 1'b1; repeat (2) @(posedge clk); cons_ack = 1'b0;
                repeat (2) @(posedge clk);
            end
            pulse_n = 1'b0; pulse_w = 1'b0;
            check(n_wins >= 4 && n_wins <= 7 && w_wins >= 1 && w_wins <= 3,
                  "VIX/priority: real weighted round-robin (3:1) gives a proportional service ratio through the carrier");
        end

        if (errors == 0)
            $display("PASS: VIX carrier's own real SEL_PRIORITY routing (#731) genuinely works end to end -- the 11th core arbitrates competing arrivals correctly in both strict-priority and weighted round-robin modes, through the carrier's own external ports");
        else
            $display("FAIL: %0d of %0d checks failed", errors, checks);
        $finish;
    end

endmodule
