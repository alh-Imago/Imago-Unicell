`timescale 1ns/1ps
module tb_latch_cell_v4sa;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg set_in = 0, clear_in = 0, toggle_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    latch_cell_v4sa dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(32'h0),
        .set_in(set_in), .clear_in(clear_in), .toggle_in(toggle_in), .ack_out(ack_out),
        .data_out(data_out), .valid_out(valid_out), .ack_in(ack_in)
    );

    integer errors = 0;
    task check_cond(input cond, input [255:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    // Settle BEFORE clearing any pulse the DUT samples on the same edge --
    // applied from the start, per #906/#911/#912.
    task fire(input do_set, input do_clear, input do_toggle);
        begin
            set_in = do_set; clear_in = do_clear; toggle_in = do_toggle;
            @(posedge clk);
            #1;
            set_in = 0; clear_in = 0; toggle_in = 0;
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

        fire(1, 0, 0); check_cond(data_out === 32'd1, "set -> 1");
        fire(0, 0, 1); check_cond(data_out === 32'd0, "toggle 1->0");
        fire(0, 0, 1); check_cond(data_out === 32'd1, "toggle 0->1");
        fire(0, 1, 0); check_cond(data_out === 32'd0, "clear -> 0");

        // priority: all three asserted together -- clear wins, confirmed by
        // asserting them simultaneously via fire()'s own three arguments
        fire(1, 1, 1); check_cond(data_out === 32'd0, "clear wins over set+toggle, all asserted together");

        // real backpressure
        ack_in = 0;
        set_in = 1;
        @(posedge clk); #1; set_in = 0;
        check_cond(data_out === 32'd1 && valid_out === 1'b1, "backpressure: offer holds at 1, receiver not ready");
        check_cond(ack_out === 1'b0, "ack_out correctly low while unacked");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd1, "backpressure: holds across multiple stalled cycles");
        ack_in = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "once acked, the offer clears");

        // freeze: a real, true pause
        fire(0, 1, 0);  // clear -> 0
        check_cond(data_out === 32'd0, "pre-freeze: real value captured");
        freeze_in = 1;
        set_in = 1; ack_in = 1;   // try to disturb it while frozen
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd0 && valid_out === 1'b0, "frozen: completely unaffected by set_in/ack_in toggling while frozen");
        freeze_in = 0;

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
