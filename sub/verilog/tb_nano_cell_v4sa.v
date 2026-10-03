`timescale 1ns/1ps
module tb_nano_cell_v4sa;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [31:0] hold_in_data = 0;
    reg load_hold = 0;
    reg [31:0] flow_in_data = 0;
    reg valid_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    nano_cell_v4sa dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .hold_in_data(hold_in_data), .load_hold(load_hold),
        .flow_in_data(flow_in_data), .valid_in(valid_in), .ack_out(ack_out),
        .data_out(data_out), .valid_out(valid_out), .ack_in(ack_in)
    );

    integer errors = 0;
    task check_cond(input cond, input [255:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    task cfg(input [31:0] word);
        begin
            cfg_data = word; cfg_valid = 1;
            @(posedge clk); #1;
            cfg_valid = 0;
        end
    endtask

    task do_load_hold(input [31:0] val);
        begin
            hold_in_data = val; load_hold = 1;
            @(posedge clk);
            #1;              // settle before clearing -- #906/#911/#912
            load_hold = 0;
        end
    endtask

    task fire(input [31:0] val);
        begin
            flow_in_data = val; valid_in = 1;
            @(posedge clk);
            #1;
            valid_in = 0;
            while (ack_out !== 1'b1) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        // === AND, hold loaded once, persists across multiple flows ===
        cfg(10'h007); // AND
        ack_in = 1;
        do_load_hold(32'hF0F0F0F0);

        fire(32'h0F0F0F0F);
        check_cond(data_out === 32'h00000000, "AND(0xF0F0F0F0 held, 0x0F0F0F0F flow) = 0");
        fire(32'hAAAAAAAA);
        check_cond(data_out === 32'hA0A0A0A0, "same held value, different flow -- hold persisted");
        fire(32'hFFFFFFFF);
        check_cond(data_out === 32'hF0F0F0F0, "hold still correctly persisting on a third flow");

        // === a few more gate codes, same held value ===
        cfg(10'h0BC); // XOR
        fire(32'hAAAAAAAA);
        check_cond(data_out === 32'h5A5A5A5A, "XOR(held, 0xAAAAAAAA)");

        // === real backpressure ===
        cfg(10'h000); // passthrough HELD, simplest to reason about
        ack_in = 0;
        flow_in_data = 32'd1; valid_in = 1;
        @(posedge clk); #1; valid_in = 0;
        check_cond(data_out === 32'hF0F0F0F0 && valid_out === 1'b1, "backpressure: offer holds (passthrough HELD), receiver not ready");
        check_cond(ack_out === 1'b0, "ack_out correctly low while unacked");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'hF0F0F0F0, "backpressure: holds across multiple stalled cycles");
        ack_in = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "once acked, offer clears");

        // === freeze: a real, true pause ===
        cfg(10'h007); // AND
        ack_in = 1;
        do_load_hold(32'hF0F0F0F0);
        fire(32'h0F0F0F0F);
        check_cond(data_out === 32'h00000000, "pre-freeze: real value captured");
        freeze_in = 1;
        flow_in_data = 32'hFFFFFFFF; valid_in = 1; ack_in = 1;
        hold_in_data = 32'd999; load_hold = 1;   // try to disturb everything while frozen
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'h00000000 && valid_out === 1'b0,
            "frozen: completely unaffected by flow/ack/hold-reload toggling while frozen");
        freeze_in = 0; load_hold = 0; valid_in = 0;

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
