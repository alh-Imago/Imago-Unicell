`timescale 1ns/1ps
module tb_mul_cell_v4sa;
    localparam W = 18;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [W-1:0] in_a = 0, in_b = 0;
    reg valid_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [W-1:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    mul_cell_v4sa #(.WIDTH(W)) dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(32'h0),
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

    task fire(input [W-1:0] a, input [W-1:0] b);
        begin
            in_a = a; in_b = b; valid_in = 1;
            @(posedge clk); #1;
            valid_in = 0;
            while (ack_out !== 1'b1) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        ack_in = 1;

        fire(18'd300, 18'd500);
        check_cond(data_out === 18'd150000, "300*500=150000 at real WIDTH=18, LUT-core multiplier");

        fire(18'h3FFFF, 18'h3FFFF);
        check_cond(data_out === 18'h00001, "max*max truncated correctly to 18 bits (overflow case)");

        // real backpressure
        ack_in = 0;
        in_a = 18'd6; in_b = 18'd7; valid_in = 1;
        @(posedge clk); #1; valid_in = 0;
        check_cond(data_out === 18'd42 && valid_out === 1'b1, "backpressure: offer holds (6*7=42), receiver not ready");
        check_cond(ack_out === 1'b0, "ack_out correctly low while unacked");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 18'd42, "backpressure: holds across multiple stalled cycles");
        ack_in = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "once acked, offer clears");

        // freeze: a real, true pause
        fire(18'd3, 18'd3);
        check_cond(data_out === 18'd9, "pre-freeze: real value captured");
        freeze_in = 1;
        in_a = 18'd999; in_b = 18'd999; valid_in = 1; ack_in = 1;
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 18'd9 && valid_out === 1'b0, "frozen: completely unaffected while frozen");
        freeze_in = 0;

        if (errors == 0) $display("ALL PASS (WIDTH=18, LUT-core)");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
