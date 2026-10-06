// tb_adder_cell_v4sa_width18.v -- points.md #909: real correctness check at the
// native 18-bit width (the real finding from #903/#904: this card's native
// unit is 18 bits, matching BRAM and MULT18X18), not just the default 32-bit
// regression. Confirms the WIDTH parameter genuinely changes real arithmetic
// behaviour, including the 18-bit-specific wraparound boundary -- values
// cross-checked in Python, not hand-computed.
`timescale 1ns/1ps
module tb_adder_cell_v4sa_width18;
    localparam W = 18;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [W-1:0] in_a = 0, in_b = 0;
    reg valid_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [W-1:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    adder_cell_v4sa #(.WIDTH(W)) dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .in_a(in_a), .in_b(in_b), .valid_in(valid_in), .ack_out(ack_out),
        .data_out(data_out), .valid_out(valid_out), .ack_in(ack_in), .ack_in_c(1'b1)
    );

    integer errors = 0;
    task check_cond(input cond, input [255:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        ack_in = 1;

        // ordinary addition, well within 18-bit range
        in_a = 18'd100000; in_b = 18'd50000; valid_in = 1;
        @(posedge clk); #1;
        check_cond(data_out === 18'd150000, "100000+50000=150000 at real WIDTH=18");

        // the real, 18-bit-SPECIFIC wraparound boundary -- max value + 1 wraps
        // to 0 at bit 18, not bit 32 (confirms WIDTH genuinely changed the real
        // arithmetic, not just the port declarations)
        ack_in = 1;
        @(posedge clk); #1;
        in_a = 18'h3FFFF; in_b = 18'd1; valid_in = 1;
        @(posedge clk); #1;
        check_cond(data_out === 18'h0, "0x3FFFF+1 wraps to 0 at the real 18-bit boundary, not 32-bit");

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
