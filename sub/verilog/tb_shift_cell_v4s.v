`timescale 1ns/1ps
module tb_shift_cell_v4s;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [31:0] data_in = 0;
    reg valid_in = 0;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    shift_cell_v4s dut (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in(data_in), .valid_in(valid_in), .data_out(data_out), .valid_out(valid_out)
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

    task cfg(input [31:0] word);
        begin
            cfg_data = word; cfg_valid = 1;
            @(posedge clk); #1;
            cfg_valid = 0;
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        // shift_en=0: passthrough regardless of shift_amt
        cfg({20'h0, 2'h0, 3'h0, 5'd16, 1'b0, 1'b0}); // reserved,fine=0,lane=0,amt=16,en=0,dir=0
        data_in = 32'hDEADBEEF; valid_in = 1;
        @(posedge clk); #1; check(32'hDEADBEEF, "passthrough shift_en=0");

        // SHIFT_IN (left) by 4: 0x00000001 -> 0x00000010
        cfg({20'h0, 2'h0, 3'h0, 5'd4, 1'b1, 1'b0}); // amt=4, en=1, dir=0(left)
        data_in = 32'h00000001; valid_in = 1;
        @(posedge clk); #1; check(32'h00000010, "left shift by 4");

        // SHIFT_OUT (right) by 8, no lane_cut: 0xFF000000 -> 0x00FF0000
        cfg({20'h0, 2'h0, 3'h0, 5'd8, 1'b1, 1'b1}); // amt=8, en=1, dir=1(right), lane_cut=0
        data_in = 32'hFF000000; valid_in = 1;
        @(posedge clk); #1; check(32'h00FF0000, "right shift by 8");

        if (errors == 0) $display("ALL PASS"); else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
