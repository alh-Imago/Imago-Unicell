`timescale 1ns/1ps
module tb_compare_cell_v4sa;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [31:0] data_in = 0;
    reg valid_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    compare_cell_v4sa dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
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

    task cfg(input [31:0] word);
        begin
            cfg_data = word; cfg_valid = 1;
            @(posedge clk); #1;   // settle BEFORE clearing -- the proven #906/#911 fix,
            cfg_valid = 0;        // applied here from the start, not discovered again.
        end
    endtask

    // Same discipline applied to valid_in: settle before clearing, and wait
    // on the real ack_out signal (polled only after settling) rather than a
    // hand-counted number of cycles.
    task fire_compare(input [31:0] val);
        begin
            data_in = val; valid_in = 1;
            @(posedge clk);
            #1;                   // settle BEFORE clearing valid_in
            valid_in = 0;
            while (ack_out !== 1'b1) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        // === freeze during boot ===
        freeze_in = 1;
        cfg(32'd10); // threshold = 10
        check_cond(ack_out === 1'b0, "ack_out stays low while still frozen post-config");
        @(posedge clk); @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "nothing moves while frozen");
        freeze_in = 0;
        @(posedge clk); #1;
        check_cond(ack_out === 1'b1, "ack_out goes high once freeze releases");

        // === real signed comparisons, always-ready consumer ===
        ack_in = 1;
        fire_compare(32'd15);
        check_cond(data_out === 32'd1, "15 >= 10 -> true");
        fire_compare(32'd5);
        check_cond(data_out === 32'd0, "5 >= 10 -> false");
        fire_compare(32'd10);
        check_cond(data_out === 32'd1, "10 >= 10 -> true (boundary)");
        fire_compare(32'hFFFFFFFF);
        check_cond(data_out === 32'd0, "-1 >= 10 -> false (signed)");

        // === reconfigure to a negative threshold ===
        cfg(-32'sd5);
        fire_compare(32'hFFFFFFFF);
        check_cond(data_out === 32'd1, "-1 >= -5 -> true (signed threshold)");

        // === real backpressure ===
        ack_in = 0;
        data_in = 32'd100; valid_in = 1;
        @(posedge clk); #1; valid_in = 0;
        check_cond(data_out === 32'd1 && valid_out === 1'b1, "backpressure: offer holds (100>=-5 -> true), receiver not ready");
        check_cond(ack_out === 1'b0, "ack_out correctly low while an unacked offer is pending");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd1, "backpressure: offer still holds across multiple stalled cycles");
        ack_in = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "once acked, the offer clears");

        // === freeze mid-operation: a real, true pause ===
        fire_compare(32'd3);  // 3 >= -5 -> true, data_out=1
        check_cond(data_out === 32'd1, "pre-freeze: real value captured");
        freeze_in = 1;
        data_in = 32'hFFFFFFFF; valid_in = 1; ack_in = 1;  // try to disturb it while frozen
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd1 && valid_out === 1'b0,
            "frozen: completely unaffected by data_in/valid_in/ack_in toggling while frozen");
        freeze_in = 0;

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
