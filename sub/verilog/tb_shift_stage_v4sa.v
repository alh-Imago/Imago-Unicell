`timescale 1ns/1ps
module tb_shift_stage_v4sa;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] data_in = 0;
    reg valid_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    // left shift by 8 -- the default WIDTH=32, a 32-bit regression against
    // shift_stage_v4s's own original behaviour
    shift_stage_v4sa #(.SHIFT_AMT(8), .DIRECTION(1'b0)) dut (
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

    task fire(input [31:0] val);
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

        fire(32'h00000001);
        check_cond(data_out === 32'h00000100, "32-bit: left shift by 8 of 0x1 -> 0x100");

        // real backpressure -- pending was just freed by fire()'s own wait,
        // so this new valid_in genuinely captures a fresh value (2<<8=0x200);
        // THAT offer is the one that then correctly holds while ack_in is low.
        ack_in = 0;
        data_in = 32'h00000002; valid_in = 1;
        @(posedge clk); #1; valid_in = 0;
        check_cond(data_out === 32'h00000200 && valid_out === 1'b1, "backpressure: new offer (2<<8=0x200) captured, now holding since receiver not ready");
        check_cond(ack_out === 1'b0, "ack_out correctly low while unacked");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'h00000200, "backpressure: holds across multiple stalled cycles");
        ack_in = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "once acked, offer clears");

        // freeze: a real, true pause
        fire(32'h00000003);
        check_cond(data_out === 32'h00000300, "pre-freeze: real value captured");
        freeze_in = 1;
        data_in = 32'h000000FF; valid_in = 1; ack_in = 1;
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'h00000300 && valid_out === 1'b0, "frozen: completely unaffected while frozen");
        freeze_in = 0;

        if (errors == 0) $display("ALL PASS (WIDTH=32)");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
