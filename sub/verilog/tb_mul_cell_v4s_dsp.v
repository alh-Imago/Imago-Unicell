`timescale 1ns/1ps
module tb_mul_cell_v4s_dsp;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] in_a = 0, in_b = 0;
    reg valid_in = 0;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    mul_cell_v4s_dsp dut (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(32'h0),
        .in_a(in_a), .in_b(in_b), .valid_in(valid_in),
        .data_out(data_out), .valid_out(valid_out)
    );

    integer errors = 0;
    task check(input [31:0] expected, input [255:0] label);
        begin
            if (data_out !== expected) begin
                $display("FAIL [%0s]: expected %h got %h", label, expected, data_out);
                errors = errors + 1;
            end else $display("PASS [%0s]: %h", label, data_out);
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;

        in_a = 32'd6; in_b = 32'd7; valid_in = 1;
        @(posedge clk); #1; check(32'd42, "6*7=42");

        in_a = 32'hFFFFFFFF; in_b = 32'hFFFFFFFF;
        @(posedge clk); #1; check(32'h00000001, "truncated low32, matches mul_cell_v4s exactly");

        in_a = 32'd100; in_b = 32'd0;
        @(posedge clk); #1; check(32'd0, "100*0=0");
        valid_in = 0;

        if (errors == 0) $display("ALL PASS"); else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
