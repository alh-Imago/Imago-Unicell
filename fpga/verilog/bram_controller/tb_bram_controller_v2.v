// tb_bram_controller_v2.v — points.md #284: confirms bram_controller_
// v2.v's write-then-read round trip is bit-exact across the full 40
// bits, and that the read is genuinely TWO-STAGE now (rdata_valid
// pulses one cycle LATER than v1's single-stage timing), not that it
// merely still works by coincidence.
`timescale 1ns / 1ps

module tb_bram_controller_v2;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam OP_READ = 1'b0, OP_WRITE = 1'b1;

    reg         cmd_valid = 0;
    reg         cmd_op    = 0;
    reg  [15:0] cmd_addr  = 0;
    reg  [39:0] cmd_wdata = 0;

    wire        rdata_valid;
    wire [39:0] rdata;
    wire        write_done;

    bram_controller_v2 #(.ADDR_WIDTH(16), .DATA_WIDTH(40)) DUT (
        .clk(clk), .rst(rst),
        .cmd_valid(cmd_valid), .cmd_op(cmd_op), .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata),
        .rdata_valid(rdata_valid), .rdata(rdata), .write_done(write_done)
    );

    integer errors = 0;

    task do_write(input [15:0] addr, input [39:0] data);
        begin
            cmd_valid = 1; cmd_op = OP_WRITE; cmd_addr = addr; cmd_wdata = data;
            #10;   // exactly one clock period -- ONE edge crossed, not two
            cmd_valid = 0;
            if (!write_done) begin
                $display("[%0t] FAIL: write_done not asserted after WRITE to addr=%h", $time, addr);
                errors = errors + 1;
            end
            #10;
        end
    endtask

    // Confirms the read is genuinely TWO-STAGE: rdata_valid must be
    // LOW immediately after the command-sampling edge (unlike v1,
    // where it was already high at that point), and HIGH exactly one
    // edge later.
    //
    // NOTE: an earlier draft held cmd_valid across TWO clock edges
    // (chained `@(posedge clk)` calls, clearing only after the second)
    // -- for v1's single-cycle read this was invisible (a redundant
    // re-read of the same address looks identical), but for v2's
    // genuinely two-stage read it caused a real second, overlapping
    // command, confirmed via direct per-edge tracing after the "too
    // early" failure didn't make sense on paper. Fixed with a genuine
    // single-pulse-per-period, matching the proven style already used
    // reliably elsewhere this session.
    task do_read_check(input [15:0] addr, input [39:0] expected);
        begin
            cmd_valid = 1; cmd_op = OP_READ; cmd_addr = addr;
            #10;   // stage 1 -- address gets registered at this edge
            cmd_valid = 0;
            #1;
            if (rdata_valid) begin
                $display("[%0t] FAIL: rdata_valid asserted too EARLY (should be 2-stage now, not 1) for addr=%h", $time, addr);
                errors = errors + 1;
            end
            #9;   // complete the period -- lands on stage 2's edge
            #1;
            if (!rdata_valid) begin
                $display("[%0t] FAIL: rdata_valid never asserted for addr=%h", $time, addr);
                errors = errors + 1;
            end else if (rdata !== expected) begin
                $display("[%0t] FAIL: addr=%h expected=%h got=%h", $time, addr, expected, rdata);
                errors = errors + 1;
            end else begin
                $display("[%0t] read addr=%h -> %h (correct, genuinely 2-stage: low at stage 1, high at stage 2)", $time, addr, rdata);
            end
            #10;
        end
    endtask

    initial begin
        #12 rst = 0;

        do_write(16'h0000, 40'hA5_DEAD_BEEF);
        do_write(16'h1234, 40'h3C_CAFE_F00D);
        do_write(16'hFFFF, 40'hFF_0000_0001);

        do_read_check(16'hFFFF, 40'hFF_0000_0001);
        do_read_check(16'h0000, 40'hA5_DEAD_BEEF);
        do_read_check(16'h1234, 40'h3C_CAFE_F00D);

        if (errors == 0)
            $display("PASS: bram_controller_v2 -- 3/3 write-then-read round trips bit-exact, genuinely 2-stage read latency confirmed (not 1)");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
