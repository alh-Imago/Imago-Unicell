`timescale 1ns/1ps
module tb_adder_cell_v4sa;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [31:0] in_a = 0, in_b = 0;
    reg valid_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    adder_cell_v4sa dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .in_a(in_a), .in_b(in_b), .valid_in(valid_in), .ack_out(ack_out),
        .data_out(data_out), .valid_out(valid_out), .ack_in(ack_in)
    );

    integer errors = 0;
    task check_cond(input cond, input [255:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    task cfg(input [31:0] word);
        begin
            cfg_data = word; cfg_valid = 1;
            @(posedge clk); #1;
            cfg_valid = 0;
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        // === Freeze during boot: config loads safely even while frozen ===
        freeze_in = 1;
        cfg(32'h0);  // add mode
        check_cond(ack_out === 1'b0, "while still frozen post-config, ack_out stays low (no data movement while frozen)");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'h0 && valid_out === 1'b0, "nothing moves while frozen, even several cycles later");
        freeze_in = 0;
        @(posedge clk); #1;
        check_cond(ack_out === 1'b1, "ack_out goes high once freeze releases (armed, not pending)");

        // === Normal operation, no stalling (ack_in held high) ===
        ack_in = 1;
        in_a = 32'd6; in_b = 32'd7; valid_in = 1;
        @(posedge clk); #1;
        check_cond(data_out === 32'd13 && valid_out === 1'b1, "6+7=13, valid_out asserted same cycle (1-cycle latency, unstalled)");
        check_cond(ack_out === 1'b0, "ack_out drops while pending (ack_in has not cleared it yet this same instant)");

        // === Real backpressure: downstream NOT ready ===
        ack_in = 0;
        in_a = 32'd100; in_b = 32'd1; valid_in = 1;  // sender tries to offer something new
        @(posedge clk); #1;
        check_cond(data_out === 32'd13 && valid_out === 1'b1, "STILL showing the old result -- correctly held, not overwritten, while receiver not ready");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd13 && valid_out === 1'b1, "held steady across multiple stalled cycles, not just one");

        // === Receiver finally ready: result is consumed, cell may advance ===
        ack_in = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "pending cleared the cycle ack_in arrived (old result considered consumed)");
        check_cond(ack_out === 1'b1, "ack_out back high immediately -- ready for the NEW in_a/in_b now");
        in_a = 32'd100; in_b = 32'd1; valid_in = 1;
        @(posedge clk); #1;
        check_cond(data_out === 32'd101 && valid_out === 1'b1, "100+1=101 -- the value that was held back is now correctly captured");
        ack_in = 1; valid_in = 0;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0 && ack_out === 1'b1, "clean return to idle after being consumed, no leftover state");

        // === Freeze mid-operation: a real, true pause, state unaffected by
        // anything toggling while frozen ===
        in_a = 32'd9; in_b = 32'd9; valid_in = 1; ack_in = 0;
        @(posedge clk); #1;
        check_cond(data_out === 32'd18 && valid_out === 1'b1, "9+9=18, captured and held (ack_in was 0 this cycle)");
        freeze_in = 1;
        ack_in = 1; valid_in = 1; in_a = 32'd999; in_b = 32'd999;  // try to disturb it while frozen
        @(posedge clk); @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd18 && valid_out === 1'b1, "frozen: still showing 18 (9+9), completely unaffected by ack_in/valid_in toggling while frozen");
        freeze_in = 0;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "unfreezing lets the already-asserted ack_in finally clear the held result");

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
