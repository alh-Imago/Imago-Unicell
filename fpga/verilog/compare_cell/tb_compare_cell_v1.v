// tb_compare_cell_v1.v — points.md #294 continuation: confirms
// compare_cell_v1.v's threshold comparison across positive, negative,
// and boundary values.
`timescale 1ns / 1ps

module tb_compare_cell_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_E = 4'b0100;

    reg        cfg = 0;
    reg [63:0] cfg_d = 0;
    // threshold=8, input on N, result out E
    localparam [63:0] CFG = {24'h0, 32'sd8, DIR_N, DIR_E};

    reg  [31:0] val_in = 0;
    reg         pulse = 0;
    wire [31:0] data_out_e;
    wire        fire_e, ready_o;
    reg         cons_ready = 1, cons_ack = 0;

    compare_cell_v1 #(.CELL_ID(16'h0002)) DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(val_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    integer errors = 0;
    reg [31:0] expected;

    task check_result(input signed [31:0] value, input [31:0] exp, input [255:0] label);
        begin
            wait (ready_o == 1'b1);
            val_in = value; pulse = 1'b1;
            expected = exp;
            #10;
            pulse = 1'b0;
            wait (fire_e);
            @(posedge clk); cons_ack = 1'b1; @(posedge clk); cons_ack = 1'b0;
            #20;
            if (data_out_e !== expected) begin
                $display("FAIL: %0s -- input=%0d expected=%0d got=%0d", label, value, expected, data_out_e);
                errors = errors + 1;
            end else begin
                $display("OK: %0s -- input=%0d, result=%0d (correct)", label, value, data_out_e);
            end
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG;
        #10 cfg = 0;
        #10;

        // threshold=8
        check_result(32'sd5,  32'd0, "below threshold (5 < 8)");
        check_result(32'sd8,  32'd1, "exactly at threshold (8 >= 8)");
        check_result(32'sd9,  32'd1, "above threshold (9 >= 8)");
        check_result(-32'sd1, 32'd0, "negative value, correctly below threshold");
        check_result(32'sd0,  32'd0, "zero, below threshold");

        if (errors == 0)
            $display("PASS: compare_cell_v1 -- threshold comparison correct across below/at/above/negative/zero, 5/5");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
