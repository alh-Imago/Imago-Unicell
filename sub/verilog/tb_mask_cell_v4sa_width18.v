// tb_mask_cell_v4sa_width18.v -- points.md #915: real correctness check at the
// native 18-bit width, specifically for the genuinely partial top nibble
// (bits [17:16], only 2 real bits) -- values cross-checked in Python, not
// hand-computed.
`timescale 1ns/1ps
module tb_mask_cell_v4sa_width18;
    localparam W = 18;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [W-1:0] data_in = 0;
    reg valid_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [W-1:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    mask_cell_v4sa #(.WIDTH(W)) dut (
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
        ack_in = 1;

        // #968: at WIDTH=18 each of the 8 mask bits covers ceil(18/8) = 3 data bits, so there are 6 real groups (bits 2:0, 5:3, ..., 17:15)
        cfg({23'h0, 8'h01, 1'b1});
        fire(18'h3FFFF);
        check_cond(data_out === 18'h3FFF8, "18-bit: block group 0 (bits 2:0, a 3-bit group)");

        cfg({23'h0, 8'h20, 1'b1}); // mask bit 5 = the top group, bits 17:15
        fire(18'h3FFFF);
        check_cond(data_out === 18'h07FFF, "18-bit: block the top group (bits 17:15)");

        cfg({23'h0, 8'h3F, 1'b1});
        fire(18'h3FFFF);
        check_cond(data_out === 18'h00000, "18-bit: block all 6 real groups -> 0");

        cfg({23'h0, 8'hC0, 1'b1}); // mask bits 6 and 7 have no group at this width: nothing changes
        fire(18'h3FFFF);
        check_cond(data_out === 18'h3FFFF, "18-bit: mask bits with no group are ignored");

        if (errors == 0) $display("ALL PASS (WIDTH=18)");
        else $display("FAILURES (WIDTH=18): %0d", errors);
        $finish;
    end
endmodule
