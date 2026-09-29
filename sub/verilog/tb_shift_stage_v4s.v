`timescale 1ns/1ps
module tb_shift_stage_v4s;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] data_in = 0;
    reg valid_in = 0;
    wire [31:0] stage1_out, stage2_out;
    wire stage1_valid, stage2_valid;

    always #5 clk = ~clk;

    // Chain: shift left by 8, then shift left by 4 -- total left shift by 12,
    // matching one of the original sparse table's own real supported amounts.
    shift_stage_v4s #(.SHIFT_AMT(5'd8), .DIRECTION(1'b0)) STAGE1 (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(32'h0),
        .data_in(data_in), .valid_in(valid_in),
        .data_out(stage1_out), .valid_out(stage1_valid)
    );
    shift_stage_v4s #(.SHIFT_AMT(5'd4), .DIRECTION(1'b0)) STAGE2 (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(32'h0),
        .data_in(stage1_out), .valid_in(stage1_valid),
        .data_out(stage2_out), .valid_out(stage2_valid)
    );

    integer errors = 0;
    task check(input [31:0] expected, input [255:0] label);
        begin
            if (stage2_out !== expected) begin
                $display("FAIL [%0s]: expected %h got %h", label, expected, stage2_out);
                errors = errors + 1;
            end else $display("PASS [%0s]: %h", label, stage2_out);
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;

        // 0x00000001 left-shifted by 12 (8 then 4) = 0x00001000. Two cycles of
        // real latency now (one per stage) -- the chain's own real, fixed,
        // known latency, exactly what the family's latency-matching work needs
        // to know about.
        data_in = 32'h00000001; valid_in = 1;
        @(posedge clk); #1;   // stage1 has captured, not yet visible at stage2
        valid_in = 0;
        @(posedge clk); #1;   // stage2 now holds the real composed result
        check(32'h00001000, "chained shift: 1 << 8 << 4 = 1 << 12");
        if (stage2_valid !== 1'b1) begin
            $display("FAIL: stage2_valid should be high exactly here");
            errors = errors + 1;
        end else $display("PASS: stage2_valid asserted at the right cycle (2-stage latency)");

        if (errors == 0) $display("ALL PASS"); else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
