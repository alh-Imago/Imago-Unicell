`timescale 1ns/1ps
module tb_router_cell_v4s;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [31:0] data_in = 0;
    reg valid_in = 0;
    wire [31:0] data_out_a, data_out_b;
    wire valid_out_a, valid_out_b;

    always #5 clk = ~clk;

    router_cell_v4s dut (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in(data_in), .valid_in(valid_in),
        .data_out_a(data_out_a), .valid_out_a(valid_out_a),
        .data_out_b(data_out_b), .valid_out_b(valid_out_b)
    );

    integer errors = 0;

    task cfg(input [31:0] word);
        begin
            cfg_data = word; cfg_valid = 1;
            @(posedge clk); #1;
            cfg_valid = 0;
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        // both outputs enabled: both should carry the same data and both fire
        cfg(32'b11);
        data_in = 32'hCAFEF00D; valid_in = 1;
        @(posedge clk); #1;
        if (data_out_a !== 32'hCAFEF00D || data_out_b !== 32'hCAFEF00D) begin
            $display("FAIL: both-enabled data mismatch a=%h b=%h", data_out_a, data_out_b);
            errors = errors + 1;
        end else $display("PASS: both outputs carry the same data (unconditional copy)");
        if (valid_out_a !== 1'b1 || valid_out_b !== 1'b1) begin
            $display("FAIL: both-enabled valid mismatch a=%b b=%b", valid_out_a, valid_out_b);
            errors = errors + 1;
        end else $display("PASS: both valids fire when both enabled");
        valid_in = 0;

        // only A enabled: B still gets the data value, but B's valid never fires
        cfg(32'b01);
        data_in = 32'h11223344; valid_in = 1;
        @(posedge clk); #1;
        if (data_out_b !== 32'h11223344) begin
            $display("FAIL: disabled output B should still carry the data value");
            errors = errors + 1;
        end else $display("PASS: disabled output B still carries the data (harmless)");
        if (valid_out_a !== 1'b1 || valid_out_b !== 1'b0) begin
            $display("FAIL: expected valid_a=1 valid_b=0, got a=%b b=%b", valid_out_a, valid_out_b);
            errors = errors + 1;
        end else $display("PASS: only the enabled output's valid fires -- no per-item decision, just a static gate");

        if (errors == 0) $display("ALL PASS"); else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
