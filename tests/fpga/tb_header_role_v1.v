// tb_header_role_v1.v — proves the EXISTING accumulator core, already
// real and built, correctly serves the collector mechanism's own
// "header" role (points.md #381/#382) with no new RTL needed: holds
// and increments its own address, continuously re-offers its current
// value (the real, documented "heartbeat" behavior, SUPER_CELL_
// INTERNALS.md), without requiring a new module.
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
    wire [4:0] status_core_select;

    unicell_super_v1 #(.CELL_ID(16'h0003)) DUT (
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
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .status_core_select(status_core_select)
    );

    integer errors = 0;
    task check(input cond, input [511:0] msg);
        begin
            if (!cond) begin $display("FAIL: %0s", msg); errors = errors + 1; end
            else $display("PASS: %0s", msg);
        end
    endtask

    initial begin
        @(posedge clk); @(posedge clk);
        rst = 0;
        @(posedge clk);

        // load accumulator (SEL_ACC=3): inc_dir=N(bit0), dec_dir=none,
        // downstream_mask=E(bit2) -- the header's own real config shape
        cfg_valid = 1;
        cfg_data = {13'b0, 20'b0, 30'b0, {4'b0100/*downstream_mask=E*/, 4'b0000/*dec_dir=none*/, 4'b0001/*inc_dir=N*/}, 5'd3/*SEL_ACC*/};
        @(posedge clk); #1;
        cfg_valid = 0;
        @(posedge clk); #1;
        check(status_core_select == 5'd3, "shell loaded with accumulator selected (header role)");

        // real HEARTBEAT check -- confirm it offers its own current
        // value (0) WITHOUT any external trigger, across several idle
        // ticks, matching the real, documented continuously-live
        // behavior this header role depends on.
        // real, honest sequencing: do NOT hold ack_in_e high in advance
        // (that defeats pending_ack tracking entirely -- confirmed
        // directly: any_fire=1 internally the whole time, but pending_ack
        // never shows it, because the RTL correctly treats an ALREADY-
        // asserted ack as "nothing to track"). A real downstream consumer
        // sees fire_e go high FIRST, then acks -- so this test does too.
        @(posedge clk); #1;
        check(fire_e === 1'b1, "heartbeat: accumulator offers its own value with zero external trigger");
        check(DUT.CORE_ACC.pending_ack == 4'b0100, "heartbeat: pending_ack correctly tracks the real, unacked E offer");
        ack_in_e = 1;
        @(posedge clk); #1;
        ack_in_e = 0;
        check(data_out_e === 32'd0, "heartbeat: initial held value is 0, as configured");

        // real INCREMENT check -- a genuine N arrival should increment
        // the held address by 1
        data_in_n = 32'd1;   // accumulator increments by however inc arrives; check real behavior
        arrived_n = 1;
        @(posedge clk); #1;
        arrived_n = 0;
        @(posedge clk); #1;
        check(data_out_e === 32'd1, "increment: header's own held address advanced to 1 after a real inc arrival");
        // ack the resulting offer before triggering the next increment --
        // the accumulator correctly withholds a NEW value from out_buffer
        // until the current, still-pending offer is acknowledged (a real,
        // sensible protocol, confirmed directly after an earlier version
        // of this test forgot to do this and saw a stale value instead).
        ack_in_e = 1;
        @(posedge clk); #1;
        ack_in_e = 0;

        // a second increment -- confirms it's a real, repeatable counter,
        // not a one-shot
        arrived_n = 1;
        @(posedge clk); #1;
        arrived_n = 0;
        @(posedge clk); #1;
        check(data_out_e === 32'd2, "increment: header's own held address advanced to 2 after a second inc arrival");

        @(posedge clk);
        if (errors == 0)
            $display("\nALL CHECKS PASSED -- the existing accumulator core serves the header role correctly, no new RTL needed");
        else
            $display("\n%0d CHECK(S) FAILED", errors);
        $finish;
    end
endmodule
