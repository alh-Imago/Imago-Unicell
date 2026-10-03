`timescale 1ns/1ps
module tb_sequencer_cell_v4sa;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [1:0] cfg_seq_len_m1 = 0;
    reg advance_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    sequencer_cell_v4sa dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data), .cfg_seq_len_m1(cfg_seq_len_m1),
        .advance_in(advance_in), .ack_out(ack_out),
        .data_out(data_out), .valid_out(valid_out), .ack_in(ack_in)
    );

    integer errors = 0;
    task check_cond(input cond, input [255:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    // Settle BEFORE clearing, applied from the start per #906/#911/#912.
    task fire_advance;
        begin
            advance_in = 1;
            @(posedge clk);
            #1;
            advance_in = 0;
            while (ack_out !== 1'b1) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        cfg_data = {8'd40, 8'd30, 8'd20, 8'd10}; // value_3=40,value_2=30,value_1=20,value_0=10
        cfg_seq_len_m1 = 2'd3; // length 4
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        ack_in = 1;

        check_cond(data_out === 32'd10, "initial value_0, pre-advance, not yet offered (valid_out low)");
        check_cond(valid_out === 1'b0, "no offer yet until the first real advance");

        fire_advance; check_cond(data_out === 32'd20, "advance -> value_1");
        fire_advance; check_cond(data_out === 32'd30, "advance -> value_2");
        fire_advance; check_cond(data_out === 32'd40, "advance -> value_3");
        fire_advance; check_cond(data_out === 32'd10, "wraps back to value_0");

        // real backpressure
        ack_in = 0;
        advance_in = 1;
        @(posedge clk); #1; advance_in = 0;
        check_cond(data_out === 32'd20 && valid_out === 1'b1, "backpressure: offer holds at value_1, receiver not ready");
        check_cond(ack_out === 1'b0, "ack_out correctly low while unacked");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd20, "backpressure: holds across multiple stalled cycles");

        // a SECOND advance_in while still unacked must be ignored, per this
        // cell's own real, deliberate narrowing from v4s
        advance_in = 1;
        @(posedge clk); #1; advance_in = 0;
        check_cond(data_out === 32'd20, "a second advance_in while unacked is correctly ignored, not silently skipping ahead");

        ack_in = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "once acked, the offer clears");

        // freeze: a real, true pause
        fire_advance; check_cond(data_out === 32'd30, "pre-freeze: real value captured");
        freeze_in = 1;
        advance_in = 1; ack_in = 1;  // try to disturb it while frozen
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd30 && valid_out === 1'b0, "frozen: completely unaffected by advance_in/ack_in toggling while frozen");
        freeze_in = 0;

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
