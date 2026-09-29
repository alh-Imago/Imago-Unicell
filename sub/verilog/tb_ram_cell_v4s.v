`timescale 1ns/1ps
module tb_ram_cell_v4s;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg cfg_fixed_mode = 0;
    reg [31:0] data_in = 0;
    reg valid_in = 0;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    ram_cell_v4s dut (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .cfg_fixed_mode(cfg_fixed_mode), .data_in(data_in), .valid_in(valid_in),
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

        // flowing mode
        cfg_data = 32'h0; cfg_fixed_mode = 0; cfg_valid = 1;
        @(posedge clk); #1; cfg_valid = 0;

        data_in = 32'hAAAA0001; valid_in = 1;
        @(posedge clk); #1; check(32'hAAAA0001, "flowing: capture 1");
        if (valid_out !== 1'b1) begin $display("FAIL: valid_out should pulse on capture"); errors=errors+1; end

        data_in = 32'hBBBB0002; valid_in = 1;
        @(posedge clk); #1; check(32'hBBBB0002, "flowing: overwrite with new capture");

        valid_in = 0;
        @(posedge clk); #1; check(32'hBBBB0002, "flowing: holds without new valid_in");
        if (valid_out !== 1'b0) begin $display("FAIL: valid_out should be low without valid_in"); errors=errors+1; end
        else $display("PASS: valid_out low when holding");

        // fixed mode
        cfg_data = 32'hCAFEBABE; cfg_fixed_mode = 1; cfg_valid = 1;
        @(posedge clk); #1; cfg_valid = 0;
        check(32'hCAFEBABE, "fixed mode: preset value");
        if (valid_out !== 1'b1) begin $display("FAIL: fixed mode valid_out should be continuously high"); errors=errors+1; end
        else $display("PASS: fixed mode valid_out continuously high");

        // fixed mode ignores valid_in/data_in entirely
        data_in = 32'hDEADDEAD; valid_in = 1;
        @(posedge clk); #1; check(32'hCAFEBABE, "fixed mode: unaffected by new data_in");
        if (valid_out !== 1'b1) begin $display("FAIL: fixed mode valid_out should stay high"); errors=errors+1; end
        else $display("PASS: fixed mode valid_out stays high");

        if (errors == 0) $display("ALL PASS"); else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
