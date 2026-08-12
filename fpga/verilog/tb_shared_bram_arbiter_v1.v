// tb_shared_bram_arbiter_v1.v — points.md continuation of #279/#281's
// sentinel-system thread, the real shared-memory piece Alan asked for
// next: confirms shared_bram_arbiter_v1.v handles normal read, normal
// write, and — the critical case — a read and write REQUESTED THE SAME
// CYCLE, proving the read gets queued and correctly serviced on the
// next available cycle rather than silently lost.
`timescale 1ns / 1ps

module tb_shared_bram_arbiter_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         rd_cmd_valid = 0;
    reg  [15:0] rd_cmd_addr = 0;
    wire        rd_rdata_valid;
    wire [39:0] rd_rdata;

    reg         wr_cmd_valid = 0;
    reg  [15:0] wr_cmd_addr = 0;
    reg  [39:0] wr_cmd_wdata = 0;
    wire        wr_write_done;

    wire        mem_cmd_valid, mem_cmd_op;
    wire [15:0] mem_cmd_addr;
    wire [39:0] mem_cmd_wdata;
    wire        mem_rdata_valid;
    wire [39:0] mem_rdata;
    wire        mem_write_done;
    wire        status_queued;

    shared_bram_arbiter_v1 #(.ADDR_WIDTH(16)) ARB (
        .clk(clk), .rst(rst),
        .rd_cmd_valid(rd_cmd_valid), .rd_cmd_addr(rd_cmd_addr),
        .rd_rdata_valid(rd_rdata_valid), .rd_rdata(rd_rdata),
        .wr_cmd_valid(wr_cmd_valid), .wr_cmd_addr(wr_cmd_addr), .wr_cmd_wdata(wr_cmd_wdata),
        .wr_write_done(wr_write_done),
        .mem_cmd_valid(mem_cmd_valid), .mem_cmd_op(mem_cmd_op),
        .mem_cmd_addr(mem_cmd_addr), .mem_cmd_wdata(mem_cmd_wdata),
        .mem_rdata_valid(mem_rdata_valid), .mem_rdata(mem_rdata), .mem_write_done(mem_write_done),
        .status_queued(status_queued)
    );

    bram_controller_v1 #(.ADDR_WIDTH(16), .DATA_WIDTH(40)) MEM (
        .clk(clk), .rst(rst),
        .cmd_valid(mem_cmd_valid), .cmd_op(mem_cmd_op), .cmd_addr(mem_cmd_addr), .cmd_wdata(mem_cmd_wdata),
        .rdata_valid(mem_rdata_valid), .rdata(mem_rdata), .write_done(mem_write_done)
    );

    integer errors = 0;

    task do_write(input [15:0] addr, input [39:0] data);
        begin
            wr_cmd_valid = 1; wr_cmd_addr = addr; wr_cmd_wdata = data;
            #10;
            wr_cmd_valid = 0;
            #10;
        end
    endtask

    task check_read(input [15:0] addr, input [39:0] expected, input [255:0] label);
        begin
            rd_cmd_valid = 1; rd_cmd_addr = addr;
            #10;
            rd_cmd_valid = 0;
            // Wait for the result — could arrive same cycle (no
            // contention) or several cycles later (if queued).
            while (!rd_rdata_valid) #10;
            if (rd_rdata !== expected) begin
                $display("FAIL: %0s -- expected=%h got=%h", label, expected, rd_rdata);
                errors = errors + 1;
            end else begin
                $display("%0s: %h (correct)", label, rd_rdata);
            end
            #10;
        end
    endtask

    initial begin
        #12 rst = 0;
        #10;

        // ── PART 1: normal write, normal read, no contention. ──
        do_write(16'h0010, 40'hAA_1111_1111);
        check_read(16'h0010, 40'hAA_1111_1111, "PART1 normal read");

        // ── PART 2: the critical case — a read and write requested the
        // EXACT SAME CYCLE. Write must win immediately; the read must
        // be QUEUED (status_queued should assert) and correctly
        // serviced once the write clears, NOT lost. ──
        do_write(16'h0020, 40'hBB_2222_2222);   // seed a known value to read back

        @(posedge clk);
        rd_cmd_valid = 1; rd_cmd_addr = 16'h0020;
        wr_cmd_valid = 1; wr_cmd_addr = 16'h0030; wr_cmd_wdata = 40'hCC_3333_3333;
        #10;   // both asserted THIS cycle -- genuine simultaneous contention
        if (!status_queued) begin
            $display("FAIL: read should have been QUEUED when it lost arbitration to the simultaneous write");
            errors = errors + 1;
        end else begin
            $display("OK: contention correctly detected, read genuinely queued (status_queued=1)");
        end
        #1;   // settle margin -- clearing exactly at an edge boundary
              // races the arbiter's own sampling (same delta-cycle
              // ordering ambiguity already hit and fixed once this
              // session, #252's own lesson)
        rd_cmd_valid = 0;
        wr_cmd_valid = 0;
        // Now let the queued read actually complete.
        while (!rd_rdata_valid) #10;
        if (rd_rdata !== 40'hBB_2222_2222) begin
            $display("FAIL: queued read should still return the CORRECT value (0x0020's own data), got %h", rd_rdata);
            errors = errors + 1;
        end else begin
            $display("OK: queued read correctly serviced after the write cleared, returned the RIGHT value -- not lost, not corrupted");
        end
        #10;

        // Confirm the write that WON priority also landed correctly.
        check_read(16'h0030, 40'hCC_3333_3333, "PART2 the winning write's own value, read back");

        if (errors == 0)
            $display("PASS: shared_bram_arbiter_v1 -- normal read/write correct, AND the critical simultaneous-contention case correctly queues (not drops) the blocked read");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
