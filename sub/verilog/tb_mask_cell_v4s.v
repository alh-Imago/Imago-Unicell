`timescale 1ns/1ps
module tb_mask_cell_v4s;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [31:0] data_in = 0;
    reg valid_in = 0;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    mask_cell_v4s dut (
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

        // mask_en=0: passthrough regardless of nibble_mask
        cfg({23'h0, 8'hFF, 1'b0}); // nibble_mask=0xFF (would block everything), en=0
        data_in = 32'hABCDEF12; valid_in = 1;
        @(posedge clk); #1; check(32'hABCDEF12, "passthrough mask_en=0");

        // mask_en=1, block nibble 0 only (bit0=1): 0xABCDEF12 -> 0xABCDEF10
        cfg({23'h0, 8'h01, 1'b1});
        data_in = 32'hABCDEF12; valid_in = 1;
        @(posedge clk); #1; check(32'hABCDEF10, "block nibble 0");

        // mask_en=1, block nibble 7 only (bit7=1): 0xABCDEF12 -> 0x0BCDEF12
        cfg({23'h0, 8'h80, 1'b1});
        data_in = 32'hABCDEF12; valid_in = 1;
        @(posedge clk); #1; check(32'h0BCDEF12, "block nibble 7");

        // mask_en=1, block all: -> 0x00000000
        cfg({23'h0, 8'hFF, 1'b1});
        data_in = 32'hABCDEF12; valid_in = 1;
        @(posedge clk); #1; check(32'h00000000, "block all");

        if (errors == 0) $display("ALL PASS"); else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
