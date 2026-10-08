`timescale 1ns/1ps
module tb_latch_cell_v4s;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg set_in = 0, clear_in = 0, toggle_in = 0;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    latch_cell_v4s dut (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .set_in(set_in), .clear_in(clear_in), .toggle_in(toggle_in),
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
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;

        set_in = 1; @(posedge clk); #1; check(32'd1, "set -> 1"); set_in = 0;
        @(posedge clk); #1; check(32'd1, "holds after set");

        toggle_in = 1; @(posedge clk); #1; check(32'd0, "toggle 1->0"); toggle_in = 0;
        toggle_in = 1; @(posedge clk); #1; check(32'd1, "toggle 0->1"); toggle_in = 0;

        clear_in = 1; @(posedge clk); #1; check(32'd0, "clear -> 0"); clear_in = 0;

        // priority: clear beats set beats toggle, all asserted together
        set_in = 1; clear_in = 1; toggle_in = 1;
        @(posedge clk); #1; check(32'd0, "clear wins over set+toggle");
        clear_in = 0;
        @(posedge clk); #1; check(32'd1, "set wins over toggle (clear now low)");
        set_in = 0; toggle_in = 0;

        if (errors == 0) $display("ALL PASS"); else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
