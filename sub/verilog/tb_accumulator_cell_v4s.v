`timescale 1ns/1ps
module tb_accumulator_cell_v4s;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg inc_pulse = 0, dec_pulse = 0;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    accumulator_cell_v4s dut (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .inc_pulse(inc_pulse), .dec_pulse(dec_pulse),
        .data_out(data_out), .valid_out(valid_out)
    );

    integer errors = 0;
    task check(input [31:0] expected, input [255:0] label);
        begin
            if (data_out !== expected) begin
                $display("FAIL [%0s]: expected %0d got %0d", label, $signed(expected), $signed(data_out));
                errors = errors + 1;
            end else $display("PASS [%0s]: %0d", label, $signed(data_out));
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

        // continuous mode, step=3, no threshold
        cfg({7'h0, 16'd0, 1'b0, 8'd3}); // reserved,threshold=0,pulse_mode=0,step=3
        inc_pulse = 1; dec_pulse = 0;
        @(posedge clk); #1; check(32'd3, "continuous +3");
        @(posedge clk); #1; check(32'd6, "continuous +3 again -> 6");
        inc_pulse = 0; dec_pulse = 1;
        @(posedge clk); #1; check(32'd3, "continuous -3 -> 3");
        inc_pulse = 0; dec_pulse = 0;
        @(posedge clk); #1;
        if (valid_out !== 1'b0) begin $display("FAIL: valid_out should be low with no pulse"); errors=errors+1; end
        else $display("PASS: valid_out low when neither pulse fires");

        // pulse mode: step=5, threshold=12 -> after 3 increments (5,10,15) fires once at 15
        cfg({7'h0, 16'd12, 1'b1, 8'd5}); // reserved,threshold=12,pulse_mode=1,step=5
        inc_pulse = 1; dec_pulse = 0;
        @(posedge clk); #1;
        if (valid_out !== 1'b0) begin $display("FAIL: pulse mode fired too early (1st step)"); errors=errors+1; end
        @(posedge clk); #1;
        if (valid_out !== 1'b0) begin $display("FAIL: pulse mode fired too early (2nd step)"); errors=errors+1; end
        @(posedge clk); #1;
        if (valid_out !== 1'b1) begin $display("FAIL: pulse mode should have fired on 3rd step (total 15 >= 12)"); errors=errors+1; end
        else check(32'd15, "pulse mode fires at total=15 (>=12)");
        inc_pulse = 0;

        if (errors == 0) $display("ALL PASS"); else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
