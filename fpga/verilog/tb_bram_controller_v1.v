// tb_bram_controller_v1.v — points.md #248 task 3 (first half): confirms
// bram_controller_v1.v's WRITE-then-READ round trip is bit-exact across
// several addresses, that READ's result is correctly registered at the
// same edge that samples the command (the real single-stage synchronous
// M20K read timing the eventual chain-head consumer will need to
// absorb), and that WRITE never produces a spurious rdata_valid pulse.
`timescale 1ns / 1ps

module tb_bram_controller_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam OP_READ = 1'b0, OP_WRITE = 1'b1;

    reg         cmd_valid = 0;
    reg         cmd_op    = 0;
    reg  [15:0] cmd_addr  = 0;
    reg  [31:0] cmd_wdata = 0;

    wire        rdata_valid;
    wire [31:0] rdata;
    wire        write_done;

    bram_controller_v1 #(.ADDR_WIDTH(16), .DATA_WIDTH(32)) DUT (
        .clk(clk), .rst(rst),
        .cmd_valid(cmd_valid), .cmd_op(cmd_op), .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata),
        .rdata_valid(rdata_valid), .rdata(rdata), .write_done(write_done)
    );

    integer errors = 0;

    task do_write(input [15:0] addr, input [31:0] data);
        begin
            @(posedge clk);
            cmd_valid = 1; cmd_op = OP_WRITE; cmd_addr = addr; cmd_wdata = data;
            @(posedge clk);
            cmd_valid = 0;
            if (!write_done) begin
                $display("[%0t] FAIL: write_done not asserted after WRITE to addr=%h", $time, addr);
                errors = errors + 1;
            end
        end
    endtask

    // Confirms the read result is available exactly at the edge that
    // samples the command (standard single-cycle registered BRAM read:
    // address+cmd_valid presented before the edge, data registered and
    // visible immediately after that same edge).
    task do_read_check(input [15:0] addr, input [31:0] expected);
        begin
            @(posedge clk);
            cmd_valid = 1; cmd_op = OP_READ; cmd_addr = addr;
            @(posedge clk);   // the sampling edge
            cmd_valid = 0;
            #1;   // let this edge's non-blocking updates settle before checking
            if (!rdata_valid) begin
                $display("[%0t] FAIL: rdata_valid never asserted for addr=%h", $time, addr);
                errors = errors + 1;
            end else if (rdata !== expected) begin
                $display("[%0t] FAIL: addr=%h expected=%h got=%h", $time, addr, expected, rdata);
                errors = errors + 1;
            end else begin
                $display("[%0t] read addr=%h -> %h (correct, registered same edge as command)", $time, addr, rdata);
            end
        end
    endtask

    initial begin
        #12 rst = 0;

        // Write 5 values at scattered addresses (not sequential — real
        // exercise of address decode, not just an incrementing pattern).
        do_write(16'h0000, 32'hDEAD_BEEF);
        do_write(16'h1234, 32'hCAFE_F00D);
        do_write(16'hFFFF, 32'h0000_0001);
        do_write(16'h0001, 32'hFFFF_FFFF);
        do_write(16'h7777, 32'h5A5A_5A5A);

        // Read them back, deliberately out of write order.
        do_read_check(16'hFFFF, 32'h0000_0001);
        do_read_check(16'h0000, 32'hDEAD_BEEF);
        do_read_check(16'h7777, 32'h5A5A_5A5A);
        do_read_check(16'h1234, 32'hCAFE_F00D);
        do_read_check(16'h0001, 32'hFFFF_FFFF);

        // Confirm a WRITE command never produces a spurious rdata_valid.
        do_write(16'h2222, 32'h1111_1111);
        @(posedge clk);
        if (rdata_valid) begin
            $display("[%0t] FAIL: rdata_valid spuriously asserted after a WRITE command", $time);
            errors = errors + 1;
        end

        #20;
        if (errors == 0)
            $display("PASS: bram_controller_v1 -- 5/5 write-then-read round trips bit-exact, single-stage synchronous read timing confirmed, no spurious rdata_valid on WRITE");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
