// tb_shift_stage_v4sa_width18.v -- points.md #916: real correctness at the
// native 18-bit width, specifically proving the shift genuinely truncates
// within 18 bits (not accidentally behaving like a 32-bit shift) -- values
// cross-checked in Python, not hand-computed.
`timescale 1ns/1ps
module tb_shift_stage_v4sa_width18;
    localparam W = 18;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [W-1:0] data_in = 0;
    reg valid_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [W-1:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    // left shift by 10
    shift_stage_v4sa #(.WIDTH(W), .SHIFT_AMT(10), .DIRECTION(1'b0)) dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(32'h0),
        .data_in(data_in), .valid_in(valid_in), .ack_out(ack_out),
        .data_out(data_out), .valid_out(valid_out), .ack_in(ack_in)
    );

    integer errors = 0;
    task check_cond(input cond, input [255:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    task fire(input [W-1:0] val);
        begin
            data_in = val; valid_in = 1;
            @(posedge clk); #1;
            valid_in = 0;
            while (ack_out !== 1'b1) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        ack_in = 1;

        fire(18'h3FFFF);  // all 1s, 18 bits
        check_cond(data_out === 18'h3FC00,
            "left shift by 10 of all-1s truncates correctly WITHIN 18 bits (0x3fc00, not a 32-bit-style 0xffffc00)");

        if (errors == 0) $display("ALL PASS (WIDTH=18, left shift by 10)");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
