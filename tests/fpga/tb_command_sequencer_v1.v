// tb_command_sequencer_v1.v — proves cell_command_sequencer_v1 (points.md
// #395) genuinely drives a real unicell_super_v1 shell through a
// multi-value cardinal_edge sequence, not just a single static value.
`timescale 1ns / 1ps

module tb;
    reg clk = 0;
    reg rst = 1;
    reg dut_rst = 1;
    always #5 clk = ~clk;

    reg cfg_valid = 0;
    reg [79:0] cfg_data = 80'h0;
    reg [31:0] data_in_n = 0, data_in_s = 0, data_in_e = 0, data_in_w = 0;
    reg arrived_n = 0, arrived_s = 0, arrived_e = 0, arrived_w = 0;
    wire [31:0] data_out_n, data_out_s, data_out_e, data_out_w;
    wire fire_n, fire_s, fire_e, fire_w;
    wire ready_out;
    reg ready_in_n = 1, ready_in_s = 1, ready_in_e = 1, ready_in_w = 1;
    wire ack_out_n, ack_out_s, ack_out_e, ack_out_w;
    reg ack_in_n = 0, ack_in_s = 0, ack_in_e = 0, ack_in_w = 0;
    reg freeze_in = 0;
    wire [4:0] status_core_select;

    wire seq_program_out;
    wire [31:0] seq_prog_data_out;
    wire seq_prog_arrived_out;
    wire target_program_done;
    reg advance_trigger = 0;

    // sequence: N-relay(0001), S-relay(0010), E-relay(0100) -- 3 real values
    cell_command_sequencer_v1 #(
        .VALUE_0(4'b0001), .VALUE_1(4'b0010), .VALUE_2(4'b0100), .VALUE_3(4'b0000),
        .SEQUENCE_LEN(2'd3)
    ) SEQ (
        .clk(clk), .rst(rst),
        .advance_trigger(advance_trigger),
        .program_done_in(target_program_done),
        .program_out(seq_program_out),
        .prog_data_out(seq_prog_data_out),
        .prog_arrived_out(seq_prog_arrived_out),
        .seq_index()
    );

    unicell_super_v1 #(.CELL_ID(16'h0002)) DUT (
        .clk(clk), .rst(dut_rst),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(arrived_e), .arrived_w(arrived_w),
        .data_out_n(data_out_n), .data_out_s(data_out_s), .data_out_e(data_out_e), .data_out_w(data_out_w),
        .fire_n(fire_n), .fire_s(fire_s), .fire_e(fire_e), .fire_w(fire_w),
        .ready_out(ready_out),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(ack_out_n), .ack_out_s(ack_out_s), .ack_out_e(ack_out_e), .ack_out_w(ack_out_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_in),
        .program_in(seq_program_out), .program_done(target_program_done),
        .prog_data_in_n(seq_prog_data_out), .prog_data_in_s(seq_prog_data_out),
        .prog_data_in_e(seq_prog_data_out), .prog_data_in_w(seq_prog_data_out),
        .prog_arrived_in_n(seq_prog_arrived_out), .prog_arrived_in_s(1'b0),
        .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .status_core_select(status_core_select)
    );

    integer errors = 0;
    task check(input cond, input [511:0] msg);
        begin
            if (!cond) begin $display("FAIL: %0s", msg); errors = errors + 1; end
            else $display("PASS: %0s", msg);
        end
    endtask

    task pulse_advance;
        begin
            advance_trigger = 1;
            @(posedge clk); #1;
            advance_trigger = 0;
        end
    endtask

    task wait_for_idle;
        integer i;
        begin
            for (i = 0; i < 20; i = i + 1) begin
                @(posedge clk); #1;
                if (SEQ.state == 2'd0) i = 20;
            end
        end
    endtask

    initial begin
        @(posedge clk); @(posedge clk);
        rst = 0;
        dut_rst = 0;
        @(posedge clk);

        // load nano as the selected core, cardinal_edge=0 baseline, routing_mask=E(bit2)
        cfg_valid = 1;
        cfg_data = {13'b0, 20'b0, 6'b0, 6'b000100, 1'b1, 10'b0, 5'd0};
        @(posedge clk); #1;
        cfg_valid = 0;
        @(posedge clk); #1;
        check(status_core_select == 5'd0, "shell loaded with nano selected");

        // STEP 1: advance the sequencer -- should program cardinal_edge to N-relay (VALUE_0)
        pulse_advance();
        wait_for_idle();
        check(SEQ.seq_index == 2'd1, "after step 1, sequencer advanced to index 1");
        check(DUT.CORE_NANO.cardinal_edge == 4'b0001, "step 1: cardinal_edge = N-relay (0001)");

        // verify: a single N arrival now relays immediately (E is routing_mask)
        data_in_n = 32'd111;
        arrived_n = 1;
        @(posedge clk); #1;
        arrived_n = 0;
        @(posedge clk); #1;
        check(fire_e === 1'b1, "step 1: N arrival relays correctly");
        check(data_out_e === 32'd111, "step 1: relayed value correct (111)");

        // real reset between checks so a_arrived state doesn't interfere,
        // matching the same lesson learned in #390 -- ONLY the shell's own
        // reset toggles here, never the sequencer's, so its real seq_index
        // progress survives across these per-step resets.
        dut_rst = 1;
        @(posedge clk); @(posedge clk);
        dut_rst = 0;
        @(posedge clk);
        cfg_valid = 1;
        cfg_data = {13'b0, 20'b0, 6'b0, 6'b000100, 1'b1, 10'b0, 5'd0};
        @(posedge clk); #1;
        cfg_valid = 0;
        @(posedge clk); #1;

        // STEP 2: advance again -- should now program cardinal_edge to S-relay (VALUE_1)
        pulse_advance();
        wait_for_idle();
        check(SEQ.seq_index == 2'd2, "after step 2, sequencer advanced to index 2");
        check(DUT.CORE_NANO.cardinal_edge == 4'b0010, "step 2: cardinal_edge = S-relay (0010)");

        data_in_s = 32'd222;
        arrived_s = 1;
        @(posedge clk); #1;
        arrived_s = 0;
        @(posedge clk); #1;
        check(fire_e === 1'b1, "step 2: S arrival relays correctly");
        check(data_out_e === 32'd222, "step 2: relayed value correct (222)");

        // STEP 3 + wraparound: advance to index 2's value (E-relay), then wrap back to index 0
        dut_rst = 1;
        @(posedge clk); @(posedge clk);
        dut_rst = 0;
        @(posedge clk);
        cfg_valid = 1;
        cfg_data = {13'b0, 20'b0, 6'b0, 6'b001000, 1'b1, 10'b0, 5'd0}; // routing_mask=W this time
        @(posedge clk); #1;
        cfg_valid = 0;
        @(posedge clk); #1;

        pulse_advance();
        wait_for_idle();
        check(SEQ.seq_index == 2'd0, "after step 3, sequencer WRAPPED back to index 0");
        check(DUT.CORE_NANO.cardinal_edge == 4'b0100, "step 3: cardinal_edge = E-relay (0100)");

        data_in_e = 32'd333;
        arrived_e = 1;
        @(posedge clk); #1;
        arrived_e = 0;
        @(posedge clk); #1;
        check(fire_w === 1'b1, "step 3: E arrival relays correctly");
        check(data_out_w === 32'd333, "step 3: relayed value correct (333)");

        @(posedge clk);
        if (errors == 0)
            $display("\nALL CHECKS PASSED -- command sequencer drives a real multi-value cycle correctly");
        else
            $display("\n%0d CHECK(S) FAILED", errors);
        $finish;
    end
endmodule
