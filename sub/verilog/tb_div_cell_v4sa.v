// tb_div_cell_v4sa.v -- ledger #1070. Bench for div_cell_v4sa at any WIDTH / STEPS:
//   iverilog -g2012 -P tb_div_cell_v4sa.WIDTH=18 -P tb_div_cell_v4sa.STEPS=3 -o t div_cell_v4sa.v tb_div_cell_v4sa.v && vvp t
// Reference is Verilog's own / and % on WIDTH-bit values (divide by zero: all ones, remainder = dividend).
// Checks: quotient and remainder, the exact clock count (the capture clock plus ceil(WIDTH/STEPS) compute clocks), ack_out low while busy
// or holding a result, results held until acknowledged, freeze mid-operation, reconfigure discards an operation,
// and the remainder port silent when rem_enable is clear.
`timescale 1ns / 1ps
module tb_div_cell_v4sa;
    parameter WIDTH = 32;
    parameter STEPS = 1;
    localparam [WIDTH-1:0] ONES = {WIDTH{1'b1}};
    localparam EXPECT_CLOCKS = (WIDTH + STEPS - 1) / STEPS;   // compute clocks; the capture clock comes first, so the result is visible EXPECT_CLOCKS+1 edges after valid_in is taken

    reg clk = 0, rst = 1, freeze_in = 0, cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [WIDTH-1:0] in_a = 0, in_b = 0;
    reg valid_in = 0, ack_in = 0, ack_in_r = 0;
    wire ack_out, valid_out, valid_out_r;
    wire [WIDTH-1:0] data_out, rem_out;

    div_cell_v4sa #(.WIDTH(WIDTH), .STEPS(STEPS), .SECOND_PORT(1)) dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .in_a(in_a), .in_b(in_b), .valid_in(valid_in), .ack_out(ack_out),
        .data_out(data_out), .valid_out(valid_out), .ack_in(ack_in),
        .rem_out(rem_out), .valid_out_r(valid_out_r), .ack_in_r(ack_in_r));

    always #5 clk = ~clk;

    integer errors = 0, checks = 0, k, n;
    reg [WIDTH-1:0] eq, er;

    task fail(input [255:0] what);
        begin errors = errors + 1; $display("FAIL: %0s (W=%0d K=%0d a=%0h b=%0h)", what, WIDTH, STEPS, in_a, in_b); end
    endtask
    task check(input cond, input [255:0] what);
        begin checks = checks + 1; if (!cond) fail(what); end
    endtask

    task configure(input rem_en);
        begin
            @(negedge clk); cfg_data = {31'd0, rem_en}; cfg_valid = 1;
            @(negedge clk); cfg_valid = 0;
        end
    endtask

    // present operands, wait for the result; returns clocks counted from the capture edge to valid_out
    task divide(input [WIDTH-1:0] a, input [WIDTH-1:0] b, input rem_en, input integer hold_cycles, output integer clocks);
        integer c;
        begin
            eq = (b == 0) ? ONES : a / b;
            er = (b == 0) ? a    : a % b;
            @(negedge clk);
            while (!ack_out) @(negedge clk);
            in_a = a; in_b = b; valid_in = 1;
            @(negedge clk);                       // the rising edge in between captured the operands
            valid_in = 0; in_a = 0; in_b = 0;
            c = 0;
            while (!valid_out && c < WIDTH + 10) begin
                check(!ack_out, "ack_out must be low while busy");
                @(negedge clk); c = c + 1;
            end
            clocks = c + 1;                       // the edge that captured counts as the first
            check(valid_out, "result must appear");
            check(data_out === eq, "quotient");
            if (rem_en) begin check(valid_out_r, "remainder valid"); check(rem_out === er, "remainder"); end
            else check(!valid_out_r, "remainder port silent when rem_enable clear");
            check(!ack_out, "ack_out must be low while a result is held");
            // hold: stall the receiver for hold_cycles; the value must stay put
            for (n = 0; n < hold_cycles; n = n + 1) begin
                @(negedge clk);
                check(valid_out && data_out === eq, "result held while receiver stalls");
            end
            ack_in = 1; ack_in_r = rem_en;
            @(negedge clk); ack_in = 0; ack_in_r = 0;
            check(!valid_out && !valid_out_r, "results clear after ack");
        end
    endtask

    integer cl, t;
    reg [WIDTH-1:0] ra, rb;
    initial begin
        repeat (3) @(negedge clk);
        rst = 0;
        configure(1);

        // directed boundary values
        divide(23 & ONES, 7, 1, 0, cl);  check(cl == EXPECT_CLOCKS + 1, "clock count");
        divide(ONES, 1, 1, 0, cl);
        divide(ONES, ONES, 1, 0, cl);
        divide(0, 5, 1, 0, cl);
        divide(5, 0, 1, 0, cl);                              // divide by zero
        divide(0, 0, 1, 0, cl);
        divide(ONES, 0, 1, 0, cl);
        divide(1, 2, 1, 0, cl);
        divide(ONES - 1, ONES, 1, 0, cl);
        divide({1'b1, {(WIDTH-1){1'b0}}}, 3, 1, 0, cl);     // top bit set
        divide({1'b1, {(WIDTH-1){1'b0}}}, {1'b1, {(WIDTH-1){1'b0}}}, 1, 0, cl);
        divide({1'b1, {(WIDTH-1){1'b0}}} - 1, {1'b1, {(WIDTH-1){1'b0}}}, 1, 0, cl);

        // pseudo-random, mixed magnitudes; the clock count is the same every time
        for (t = 0; t < 300; t = t + 1) begin
            ra = {$urandom, $urandom}; rb = {$urandom, $urandom};
            if (t % 3 == 1) rb = rb >> (WIDTH / 2);
            if (t % 3 == 2) ra = ra >> (WIDTH / 3);
            divide(ra, rb, 1, t % 4, cl);
            check(cl == EXPECT_CLOCKS + 1, "clock count constant");
        end

        // remainder port off
        configure(0);
        divide(100 & ONES, 9, 0, 0, cl);
        divide(ONES, 3, 0, 2, cl);

        // freeze in the middle of an operation: held, then finishes correctly
        configure(1);
        @(negedge clk); while (!ack_out) @(negedge clk);
        in_a = 100 & ONES; in_b = 7; valid_in = 1; @(negedge clk); valid_in = 0;
        freeze_in = 1; repeat (WIDTH + 6) @(negedge clk);
        check(!valid_out, "no result while frozen");
        check(!ack_out, "no ack while frozen");
        freeze_in = 0;
        k = 0; while (!valid_out && k < WIDTH + 10) begin @(negedge clk); k = k + 1; end
        check(valid_out && data_out === ((100 & ONES) / 7) && rem_out === ((100 & ONES) % 7), "result after freeze");
        ack_in = 1; ack_in_r = 1; @(negedge clk); ack_in = 0; ack_in_r = 0;

        // reconfigure in the middle of an operation discards it
        @(negedge clk); while (!ack_out) @(negedge clk);
        in_a = 50 & ONES; in_b = 3; valid_in = 1; @(negedge clk); valid_in = 0;
        configure(1);
        repeat (WIDTH + 4) @(negedge clk);
        check(!valid_out, "operation discarded by reconfigure");
        check(ack_out, "ready again after reconfigure");

        if (errors == 0) $display("PASS: div_cell_v4sa W=%0d K=%0d (%0d checks, %0d clocks per divide)", WIDTH, STEPS, checks, EXPECT_CLOCKS);
        else $display("FAILED: %0d of %0d checks (W=%0d K=%0d)", errors, checks, WIDTH, STEPS);
        $finish;
    end

    initial begin #50000000; $display("FAIL: timeout"); $finish; end
endmodule
