// tb_super_program_in_v1.v — proves the new shell-level program_in
// channel (points.md #390) actually reaches nano and reprograms
// cardinal_edge, closing the gap this file's own header comment
// documented honestly since #304/#315.
`timescale 1ns / 1ps

module tb;
    reg clk = 0;
    reg rst = 1;
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

    reg program_in = 0;
    wire program_done;
    reg [31:0] prog_data_in_n = 0, prog_data_in_s = 0, prog_data_in_e = 0, prog_data_in_w = 0;
    reg prog_arrived_in_n = 0, prog_arrived_in_s = 0, prog_arrived_in_e = 0, prog_arrived_in_w = 0;

    wire [4:0] status_core_select;

    unicell_super_v1 #(.CELL_ID(16'h0001)) DUT (
        .clk(clk), .rst(rst),
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
        .program_in(program_in), .program_done(program_done),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s),
        .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(prog_arrived_in_n), .prog_arrived_in_s(prog_arrived_in_s),
        .prog_arrived_in_e(prog_arrived_in_e), .prog_arrived_in_w(prog_arrived_in_w),
        .status_core_select(status_core_select)
    );

    integer errors = 0;
    task check(input cond, input [511:0] msg);
        begin
            if (!cond) begin
                $display("FAIL: %0s", msg);
                errors = errors + 1;
            end else begin
                $display("PASS: %0s", msg);
            end
        end
    endtask

    initial begin
        // reset
        @(posedge clk); @(posedge clk);
        rst = 0;
        @(posedge clk);

        // load nano as the selected core: core_select=0 (SEL_NANO),
        // topology=0, ready=1, routing_mask=E(bit2, per shell's own
        // remap: core_config[16:11]=routing_mask -> nano's own [69:64]),
        // cardinal_edge=0 (ALL CONSUME initially -- baseline)
        // SUPER_LATCH: [4:0]=core_select, [46:5]=core_config, [66:47]=addon_config
        // core_config[9:0]=topology, [10]=ready, [16:11]=routing_mask, [22:17]=cardinal_edge
        cfg_valid = 1;
        cfg_data = {13'b0, 20'b0, 6'b0/*cardinal_edge=0*/, 6'b000100/*routing_mask=E*/, 1'b1/*ready*/, 10'b0/*topology*/, 5'd0/*SEL_NANO*/};
        @(posedge clk);
        cfg_valid = 0;
        @(posedge clk);

        check(status_core_select == 5'd0, "shell loaded with nano selected");

        // BASELINE: single arrival from north, cardinal_edge=0 (consume) --
        // should NOT fire immediately, needs a second (B) arrival first
        data_in_n = 32'd111;
        arrived_n = 1;
        @(posedge clk);
        arrived_n = 0;
        @(posedge clk); #1;
        check(fire_e === 1'b0, "baseline: single consume-mode arrival does NOT fire alone");

        // reset nano's own internal state cleanly with a REAL reset
        // (a cfg_valid reload alone does NOT clear a_arrived -- confirmed
        // directly, not assumed, after the first version of this test
        // left it stuck from the baseline's own unresolved single
        // arrival) before starting the reprogram phase fresh.
        rst = 1;
        @(posedge clk); @(posedge clk);
        rst = 0;
        @(posedge clk);

        cfg_valid = 1;
        cfg_data = {13'b0, 20'b0, 6'b0/*cardinal_edge=0*/, 6'b000100/*routing_mask=E*/, 1'b1/*ready*/, 10'b0/*topology*/, 5'd0/*SEL_NANO*/};
        @(posedge clk);
        cfg_valid = 0;
        @(posedge clk);

        // NOW reprogram cardinal_edge via the NEW shell-level program_in
        // channel -- set N to relay (bit N=1 in cardinal_edge's 4-bit field)
        program_in = 1;
        prog_data_in_n = {13'b0, 3'd2/*PROG_ID_CARDINAL_EDGE*/, 12'b0, 4'b0001/*N=relay*/};
        prog_arrived_in_n = 1;
        @(posedge clk);
        prog_arrived_in_n = 0;
        @(posedge clk);

        // send COMPLETE, armed=1
        prog_data_in_n = {13'b0, 3'd7/*PROG_ID_COMPLETE*/, 15'b0, 1'b1/*armed=1*/};
        prog_arrived_in_n = 1;
        @(posedge clk);
        prog_arrived_in_n = 0;
        program_in = 0;
        @(posedge clk);

        check(program_done === 1'b1, "program_done pulsed after COMPLETE, through the shell");

        @(posedge clk);

        // NOW test: single arrival from north, cardinal_edge N=relay --
        // should fire IMMEDIATELY, single-arrival passthrough, proving
        // the shell-level program_in channel genuinely reprogrammed nano
        data_in_n = 32'd222;
        arrived_n = 1;
        @(posedge clk); #1;
        arrived_n = 0;
        @(posedge clk); #1;
        check(fire_e === 1'b1, "AFTER reprogram: single relay-mode arrival fires immediately");
        check(data_out_e === 32'd222, "AFTER reprogram: relayed value is correct (222, unmodified pass-through)");

        @(posedge clk);
        if (errors == 0)
            $display("\nALL CHECKS PASSED -- shell-level program_in channel confirmed working end to end");
        else
            $display("\n%0d CHECK(S) FAILED", errors);
        $finish;
    end
endmodule
