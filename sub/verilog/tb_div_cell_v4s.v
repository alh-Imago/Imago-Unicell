// tb_div_cell_v4s.v -- ledger #1072. Bench for div_cell_v4s at any STEPS:
//   iverilog -g2012 -P tb_div_cell_v4s.STEPS=4 -o t div_cell_v4s.v tb_div_cell_v4s.v && vvp t
// Reference: Verilog's own / and % on 32-bit values (divide by zero: all ones, remainder = dividend).
// Checks: the result, the EXACT latency ceil(32/STEPS), a one-cycle valid_out pulse, rem_primary (remainder on the single output),
// not armed before cfg_valid, reconfigure discards an operation, and the throughput rule: STEPS = 32 takes a new pair EVERY clock
// (checked as a stream), STEPS < 32 takes pairs spaced by the latency and silently ignores a pair presented while busy.
`timescale 1ns / 1ps
module tb_div_cell_v4s;
    parameter STEPS = 32;
    localparam LAT = (32 + STEPS - 1) / STEPS;

    reg clk = 0, rst = 1, cfg_valid = 0;
    reg [31:0] cfg_data = 0, in_a = 0, in_b = 0;
    reg valid_in = 0;
    wire [31:0] data_out;
    wire valid_out;

    div_cell_v4s #(.STEPS(STEPS)) dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
                                       .in_a(in_a), .in_b(in_b), .valid_in(valid_in), .data_out(data_out), .valid_out(valid_out));
    always #5 clk = ~clk;

    integer errors = 0, checks = 0, t, c;
    reg rp = 0;
    reg [31:0] ra, rb, expq, expr_;

    task check(input cond, input [255:0] what);
        begin checks = checks + 1; if (!cond) begin errors = errors + 1; $display("FAIL: %0s (STEPS=%0d a=%0h b=%0h)", what, STEPS, in_a, in_b); end end
    endtask
    function [31:0] q_of(input [31:0] a, input [31:0] b); q_of = (b == 0) ? 32'hFFFFFFFF : a / b; endfunction
    function [31:0] r_of(input [31:0] a, input [31:0] b); r_of = (b == 0) ? a : a % b; endfunction

    task configure;
        begin @(negedge clk); cfg_data = {30'd0, rp, 1'b0}; cfg_valid = 1; @(negedge clk); cfg_valid = 0; end
    endtask

    // one operation: present for one clock, count the clocks to valid_out
    task divide(input [31:0] a, input [31:0] b);
        begin
            @(negedge clk); in_a = a; in_b = b; valid_in = 1;
            @(negedge clk); valid_in = 0; in_a = 0; in_b = 0;
            c = 1;
            while (!valid_out && c < 80) begin @(negedge clk); c = c + 1; end
            in_a = a; in_b = b;                                   // for the failure messages
            check(valid_out, "result appears");
            check(c == LAT, "latency is ceil(32/STEPS)");
            check(data_out === (rp ? r_of(a, b) : q_of(a, b)), rp ? "remainder" : "quotient");
            @(negedge clk);
            check(!valid_out, "valid_out is a one-cycle pulse");
            repeat (LAT) @(negedge clk);                          // let a looped cell finish being idle
        end
    endtask

    initial begin
        repeat (3) @(negedge clk); rst = 0;

        // not armed before cfg_valid
        in_a = 100; in_b = 7; valid_in = 1; repeat (3 * LAT + 2) begin @(negedge clk); check(!valid_out, "no output before configuration"); end valid_in = 0;

        configure;
        divide(23, 7); divide(32'hFFFFFFFF, 1); divide(32'hFFFFFFFF, 32'hFFFFFFFF); divide(0, 5); divide(5, 0); divide(0, 0);
        divide(32'hFFFFFFFF, 0); divide(1, 2); divide(32'hFFFFFFFE, 32'hFFFFFFFF); divide(32'h80000000, 3); divide(32'h80000000, 32'h80000000);
        for (t = 0; t < 200; t = t + 1) begin
            ra = $urandom; rb = $urandom;
            if (t % 3 == 1) rb = rb >> ($urandom % 32);
            if (t % 3 == 2) ra = ra >> ($urandom % 32);
            divide(ra, rb);
        end

        // rem_primary: the remainder on the single output
        rp = 1; configure;
        divide(23, 7); divide(32'hFFFFFFFF, 12345); divide(5, 0);
        for (t = 0; t < 60; t = t + 1) begin ra = $urandom; rb = $urandom >> ($urandom % 32); divide(ra, rb); end
        rp = 0; configure;

        // reconfigure in the middle of an operation discards it (only a looped cell has a middle)
        if (LAT > 1) begin
            @(negedge clk); in_a = 50; in_b = 3; valid_in = 1; @(negedge clk); valid_in = 0;
            configure;
            repeat (LAT + 4) begin @(negedge clk); check(!valid_out, "operation discarded by reconfigure"); end
        end

        // reconfigure on the very clock the result is showing: the pulse must end, not be stretched
        @(negedge clk); in_a = 9; in_b = 2; valid_in = 1; @(negedge clk); valid_in = 0;
        c = 1; while (!valid_out && c < 80) begin @(negedge clk); c = c + 1; end
        check(valid_out, "result showing before the reconfigure");
        cfg_data = 0; cfg_valid = 1; @(negedge clk); cfg_valid = 0;
        check(!valid_out, "reconfigure ends a showing valid_out pulse");
        repeat (2) @(negedge clk);

        // throughput
        if (LAT == 1) begin : stream
            // one pair EVERY clock: the result of the pair presented in a clock appears in the next
            reg [31:0] prev_q; reg prev_v;
            prev_v = 0;
            for (t = 0; t < 100; t = t + 1) begin
                @(negedge clk);
                if (prev_v) begin check(valid_out, "stream: result each clock"); check(data_out === prev_q, "stream: result matches"); end
                ra = $urandom; rb = $urandom >> ($urandom % 32);
                in_a = ra; in_b = rb; valid_in = 1; prev_q = q_of(ra, rb); prev_v = 1;
            end
            @(negedge clk); valid_in = 0;
        end else begin
            // a pair presented while busy is NOT taken: the first result is right and no second result appears
            @(negedge clk); in_a = 1000; in_b = 7; valid_in = 1;
            @(negedge clk); in_a = 77; in_b = 3;                  // second pair, one clock later: the cell is busy
            @(negedge clk); valid_in = 0;
            c = 2;
            while (!valid_out && c < 80) begin @(negedge clk); c = c + 1; end
            check(data_out === q_of(1000, 7), "first pair's result is intact");
            repeat (3 * LAT) begin @(negedge clk); check(!valid_out, "no result for the pair presented while busy"); end
            // pairs spaced by exactly the latency are all taken
            for (t = 0; t < 20; t = t + 1) begin
                ra = $urandom; rb = ($urandom >> ($urandom % 32)) | 1;
                @(negedge clk); in_a = ra; in_b = rb; valid_in = 1; @(negedge clk); valid_in = 0;
                c = 1; while (!valid_out && c < 80) begin @(negedge clk); c = c + 1; end
                check(c == LAT && data_out === q_of(ra, rb), "spaced pairs are all taken");
                repeat (0) @(negedge clk);
            end
        end

        if (errors == 0) $display("PASS: div_cell_v4s STEPS=%0d (%0d checks, latency %0d)", STEPS, checks, LAT);
        else $display("FAILED: %0d of %0d checks (STEPS=%0d)", errors, checks, STEPS);
        $finish;
    end

    initial begin #80000000; $display("FAIL: timeout"); $finish; end
endmodule
