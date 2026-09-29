`timescale 1ns/1ps
module tb_adder_cell_v4s;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 32'h0;
    reg [31:0] in_a = 0, in_b = 0;
    reg valid_in = 0;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    adder_cell_v4s dut (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .in_a(in_a), .in_b(in_b), .valid_in(valid_in),
        .data_out(data_out), .valid_out(valid_out)
    );

    integer errors = 0;
    task check(input [31:0] expected, input [255:0] label);
        begin
            if (data_out !== expected) begin
                $display("FAIL [%0s]: expected %h got %h", label, expected, data_out);
                errors = errors + 1;
            end else begin
                $display("PASS [%0s]: %h", label, data_out);
            end
        end
    endtask

    initial begin
        // reset
        rst = 1; cfg_valid = 0; valid_in = 0;
        @(posedge clk); @(posedge clk);
        rst = 0;
        @(posedge clk);

        // before cfg_valid: not armed, valid_out must stay low regardless of valid_in
        in_a = 32'd5; in_b = 32'd3; valid_in = 1;
        @(posedge clk);
        if (valid_out !== 1'b0) begin
            $display("FAIL: valid_out asserted before cell was ever configured");
            errors = errors + 1;
        end else $display("PASS: valid_out stays low pre-configuration");
        valid_in = 0;

        // configure: add mode
        cfg_data = 32'h0; // subtract_mode = 0
        cfg_valid = 1;
        @(posedge clk); #1;
        cfg_valid = 0;

        // ADD: 5 + 3 = 8, one-cycle latency
        in_a = 32'd5; in_b = 32'd3; valid_in = 1;
        @(posedge clk); // out_buffer/valid_out update on this edge
        #1; // let combinational settle for the check
        if (valid_out !== 1'b1) begin $display("FAIL: valid_out not asserted after valid_in"); errors = errors+1; end
        check(32'd8, "5+3");
        valid_in = 0;
        @(posedge clk); #1;
        if (valid_out !== 1'b0) begin $display("FAIL: valid_out did not deassert (one-shot)"); errors = errors+1; end

        // reconfigure: subtract mode
        cfg_data = 32'h1; // subtract_mode = 1
        cfg_valid = 1;
        @(posedge clk); #1;
        cfg_valid = 0;

        // SUBTRACT: 10 - 4 = 6
        in_a = 32'd10; in_b = 32'd4; valid_in = 1;
        @(posedge clk); #1;
        check(32'd6, "10-4");
        valid_in = 0;

        // back-to-back, every cycle a new result (the fixed-latency pipeline claim)
        cfg_data = 32'h0; cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        in_a = 32'd1; in_b = 32'd1; valid_in = 1;
        @(posedge clk); #1; check(32'd2, "back-to-back 1");
        in_a = 32'd2; in_b = 32'd2;
        @(posedge clk); #1; check(32'd4, "back-to-back 2");
        in_a = 32'd100; in_b = 32'd23;
        @(posedge clk); #1; check(32'd123, "back-to-back 3");
        valid_in = 0;

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
