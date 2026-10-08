`timescale 1ns/1ps
module tb_sequencer_cell_v4s;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [1:0] cfg_seq_len_m1 = 0;
    reg advance_in = 0;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    sequencer_cell_v4s dut (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .cfg_seq_len_m1(cfg_seq_len_m1), .advance_in(advance_in),
        .data_out(data_out), .valid_out(valid_out)
    );

    integer errors = 0;
    task check(input [31:0] expected, input [255:0] label);
        begin
            if (data_out !== expected) begin
                $display("FAIL [%0s]: expected %0d got %0d", label, expected, data_out);
                errors = errors + 1;
            end else $display("PASS [%0s]: %0d", label, data_out);
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        cfg_data = {8'd40, 8'd30, 8'd20, 8'd10}; // value_3=40,value_2=30,value_1=20,value_0=10
        cfg_seq_len_m1 = 2'd3; // length 4
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;

        check(32'd10, "initial value_0");

        advance_in = 1;
        @(posedge clk); #1; check(32'd20, "advance -> value_1");
        @(posedge clk); #1; check(32'd30, "advance -> value_2");
        @(posedge clk); #1; check(32'd40, "advance -> value_3");
        @(posedge clk); #1; check(32'd10, "wraps back to value_0");
        advance_in = 0;

        @(posedge clk); #1; check(32'd10, "holds without advance_in");
        if (valid_out !== 1'b0) begin $display("FAIL: valid_out should be low without advance_in"); errors=errors+1; end
        else $display("PASS: valid_out low when not advancing");

        if (errors == 0) $display("ALL PASS"); else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
