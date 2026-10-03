`timescale 1ns/1ps
module tb_mask_cell_v4sa;
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

    mask_cell_v4sa dut (
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
            @(posedge clk); #1;
            cfg_valid = 0;
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

        // === WIDTH=32 regression: matches mask_cell_v4s's own original behaviour ===
        ack_in = 1;
        cfg({23'h0, 8'h01, 1'b1}); // block nibble 0, en=1
        fire(32'hABCDEF12);
        check_cond(data_out === 32'hABCDEF10, "32-bit: block nibble 0");
        cfg({23'h0, 8'hFF, 1'b1}); // block all
        fire(32'hABCDEF12);
        check_cond(data_out === 32'h00000000, "32-bit: block all");
        cfg({23'h0, 8'hFF, 1'b0}); // mask_en=0: passthrough regardless
        fire(32'hABCDEF12);
        check_cond(data_out === 32'hABCDEF12, "32-bit: passthrough when mask_en=0");

        // === real backpressure ===
        ack_in = 0;
        cfg({23'h0, 8'h00, 1'b1});
        data_in = 32'd42; valid_in = 1;
        @(posedge clk); #1; valid_in = 0;
        check_cond(data_out === 32'd42 && valid_out === 1'b1, "backpressure: offer holds, receiver not ready");
        check_cond(ack_out === 1'b0, "ack_out correctly low while unacked");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd42, "backpressure: holds across multiple stalled cycles");
        ack_in = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "once acked, offer clears");

        // === freeze: a real, true pause ===
        fire(32'd7);
        check_cond(data_out === 32'd7, "pre-freeze: real value captured");
        freeze_in = 1;
        data_in = 32'd999; valid_in = 1; ack_in = 1;
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd7 && valid_out === 1'b0, "frozen: completely unaffected while frozen");
        freeze_in = 0;

        if (errors == 0) $display("ALL PASS (WIDTH=32)");
        else $display("FAILURES (WIDTH=32): %0d", errors);
        $finish;
    end
endmodule
