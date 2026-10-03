`timescale 1ns/1ps
module tb_ram_cell_v4sa;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg cfg_fixed_mode = 0;
    reg [31:0] data_in = 0;
    reg valid_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    ram_cell_v4sa dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data), .cfg_fixed_mode(cfg_fixed_mode),
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

    task cfg(input [31:0] word, input fixed);
        begin
            cfg_data = word; cfg_fixed_mode = fixed; cfg_valid = 1;
            @(posedge clk); #1;   // settle before clearing -- #906/#911/#912
            cfg_valid = 0;
        end
    endtask

    task fire_write(input [31:0] val);
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

        // === flowing mode ===
        cfg(32'h0, 1'b0);
        ack_in = 1;
        fire_write(32'hAAAA0001);
        check_cond(data_out === 32'hAAAA0001, "flowing: capture 1");
        fire_write(32'hBBBB0002);
        check_cond(data_out === 32'hBBBB0002, "flowing: overwrite with new capture");

        // real backpressure
        ack_in = 0;
        data_in = 32'hCCCC0003; valid_in = 1;
        @(posedge clk); #1; valid_in = 0;
        check_cond(data_out === 32'hCCCC0003 && valid_out === 1'b1, "backpressure: offer holds, receiver not ready");
        check_cond(ack_out === 1'b0, "ack_out correctly low while unacked");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'hCCCC0003, "backpressure: holds across multiple stalled cycles");
        ack_in = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "once acked, the offer clears");

        // === fixed mode: always valid, never drains, ack_out never gated by pending ===
        cfg(32'hCAFEBABE, 1'b1);
        check_cond(data_out === 32'hCAFEBABE, "fixed mode: preset value");
        check_cond(valid_out === 1'b1, "fixed mode: valid_out continuously high");
        check_cond(ack_out === 1'b1, "fixed mode: ack_out always ready, nothing to drain");

        // fixed mode genuinely ignores data_in/valid_in/ack_in entirely
        data_in = 32'hDEADDEAD; valid_in = 1; ack_in = 0;
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'hCAFEBABE && valid_out === 1'b1,
            "fixed mode: completely unaffected by data_in/valid_in/ack_in -- a real constant");

        // === freeze, flowing mode: a real, true pause ===
        cfg(32'h0, 1'b0);
        ack_in = 1;
        fire_write(32'd42);
        check_cond(data_out === 32'd42, "pre-freeze: real value captured");
        freeze_in = 1;
        data_in = 32'd999; valid_in = 1; ack_in = 1;  // try to disturb it while frozen
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd42 && valid_out === 1'b0,
            "frozen: completely unaffected by data_in/valid_in/ack_in toggling while frozen");
        freeze_in = 0;

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
