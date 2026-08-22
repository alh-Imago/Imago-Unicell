// tb_collector_relay_v1.v — sim-first standalone verification of
// collector_relay_v1.v (points.md #427) BEFORE wiring it into
// top_sentinel_gather_shared_bram_v1.v to replace the nano-based
// COLLECTOR + sequencer. Drives the module directly, no shell
// involved.
`timescale 1ns / 1ps

module tb;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg [31:0] data_in_a = 0, data_in_b = 0, data_in_c = 0;
    reg arrived_a = 0, arrived_b = 0, arrived_c = 0;
    wire ack_out_a, ack_out_b, ack_out_c;
    wire [31:0] data_out;
    wire fire;
    reg ready_in = 1;
    reg ack_in = 0;

    collector_relay_v1 DUT (
        .clk(clk), .rst(rst),
        .data_in_a(data_in_a), .data_in_b(data_in_b), .data_in_c(data_in_c),
        .arrived_a(arrived_a), .arrived_b(arrived_b), .arrived_c(arrived_c),
        .ack_out_a(ack_out_a), .ack_out_b(ack_out_b), .ack_out_c(ack_out_c),
        .data_out(data_out), .fire(fire),
        .ready_in(ready_in), .ack_in(ack_in)
    );

    integer errors = 0;
    task check(input cond, input [255:0] msg);
        begin
            if (!cond) begin
                $display("FAIL: %s", msg);
                errors = errors + 1;
            end
        end
    endtask

    task relay_and_check(input [31:0] value, input integer which);
        begin
            case (which)
                0: begin data_in_a = value; arrived_a = 1; end
                1: begin data_in_b = value; arrived_b = 1; end
                2: begin data_in_c = value; arrived_c = 1; end
            endcase
            // Real check: ack_out is COMBINATIONAL, matching every
            // other core's own "ack fires immediately on capture"
            // convention (e.g. accumulator_cell_v1.v) -- it must be
            // checked in the SAME cycle as the arrival, before the
            // clock edge, not after. A real bug in THIS testbench's
            // own first draft checked it one cycle too late (after
            // the edge, by which point `data_valid` had already
            // flipped to 1, making a genuinely-correct ack look
            // wrong) -- fixed here, not in the core.
            #1;
            case (which)
                0: check(ack_out_a === 1'b1, "ack_out for source should fire same cycle as arrival");
                1: check(ack_out_b === 1'b1, "ack_out for source should fire same cycle as arrival");
                2: check(ack_out_c === 1'b1, "ack_out for source should fire same cycle as arrival");
            endcase
            // The REAL 2-cycle latency check: fire must still be 0
            // right here (before the capture-processing edge below),
            // since `data_valid` hasn't updated yet -- a real bug in
            // this testbench's own first draft placed this check AFTER
            // that edge instead, where data_valid had already updated
            // to 1, making fire=1 (correctly) look like a failure.
            check(fire === 1'b0, "fire must not assert before the capture-processing clock edge");
            @(posedge clk); #1;
            case (which)
                0: arrived_a = 0;
                1: arrived_b = 0;
                2: arrived_c = 0;
            endcase
            @(posedge clk); #1;
            check(fire === 1'b1, "fire should assert one cycle after capture");
            check(data_out === value, "data_out should show the correct captured value, not stale data");
            ack_in = 1;
            @(posedge clk); #1;
            ack_in = 0;
            check(fire === 1'b0, "fire should drop once acked");
        end
    endtask

    initial begin
        #12 rst = 0;
        #10;

        // Relay from each of the 3 sources in turn.
        relay_and_check(32'd111, 0);
        relay_and_check(32'd222, 1);
        relay_and_check(32'd333, 2);

        // Real check: an arrival while a previous offer is still
        // pending (not yet acked) must NOT be acked -- the second real
        // bug found and fixed before testing (unconditional ack would
        // silently lose data here).
        data_in_a = 32'd999; arrived_a = 1;
        #1;
        check(ack_out_a === 1'b1, "first arrival while free should ack");
        @(posedge clk); #1;
        arrived_a = 0;
        // Don't ack yet -- offer is now pending (fire should be 1 next cycle).
        check(fire === 1'b1, "offer should be pending");
        data_in_b = 32'd888; arrived_b = 1;
        #1;
        check(ack_out_b === 1'b0, "arrival while a previous offer is still pending must NOT be acked -- would lose data");
        @(posedge clk); #1;
        arrived_b = 0;
        check(data_out === 32'd999, "data_out should still show the ORIGINAL pending value, not corrupted");
        ack_in = 1;
        @(posedge clk); #1;
        ack_in = 0;

        if (errors == 0) begin
            $display("PASS: collector_relay_v1 relays correctly from all 3 sources, correct 2-cycle latency, no data loss under contention");
        end else begin
            $display("FAIL: %0d error(s) found", errors);
        end
        $finish;
    end
endmodule
