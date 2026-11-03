`default_nettype none
`timescale 1ns / 1ps
// hexn_cross_v2 -- hexn_cross_v1 (untouched) with a SMALLER serial->parallel half (3 Nov 2026, slim-frame step 1). hexn_p2s_v2 = hexn_p2s_v1 unchanged in behaviour. hexn_s2p_v2 captures with a SHIFT REGISTER (31 bits, new bit in at the top) instead of v1's variable-index write `sh[cnt] <= ds` (a 32-way write decoder per row) and no longer zeroes the register at the start of a word; the output word, its valid pulse and its timing are the same (checked by tests/vm/test_hexn_cross_v2.py against v1 on random streams).
module hexn_p2s_v2 (input wire clk, input wire clear, input wire [31:0] data, input wire valid, output reg busy, output reg ds, output reg fs, output reg done);
    reg [31:0] sh; reg [4:0] cnt;
    always @(posedge clk) begin
        ds <= 1'b0; fs <= 1'b0; done <= 1'b0;
        if (clear) begin busy <= 1'b0; sh <= 32'd0; cnt <= 5'd0; end
        else if (!busy) begin
            if (valid) begin busy <= 1'b1; ds <= data[0]; fs <= 1'b1; sh <= {1'b0, data[31:1]}; cnt <= 5'd1; end         // bit 0 leaves in the load clock (visible one clock after `valid`)
        end else begin
            ds <= sh[0]; sh <= {1'b0, sh[31:1]}; cnt <= cnt + 5'd1;
            if (cnt == 5'd31) begin busy <= 1'b0; done <= 1'b1; end
        end
    end
    initial begin busy = 1'b0; ds = 1'b0; fs = 1'b0; done = 1'b0; sh = 32'd0; cnt = 5'd0; end
endmodule

module hexn_s2p_v2 (input wire clk, input wire clear, input wire ds, input wire fs, output reg [31:0] data, output reg valid);
    reg [30:0] sh; reg [4:0] cnt; reg act;
    always @(posedge clk) begin
        valid <= 1'b0;
        if (clear) begin act <= 1'b0; cnt <= 5'd0; data <= 32'd0; end
        else if (fs) begin sh <= {ds, sh[30:1]}; cnt <= 5'd1; act <= 1'b1; end             // bit 0
        else if (act) begin
            sh <= {ds, sh[30:1]}; cnt <= cnt + 5'd1;
            if (cnt == 5'd31) begin act <= 1'b0; data <= {ds, sh[30:0]}; valid <= 1'b1; end
        end
    end
    initial begin data = 32'd0; valid = 1'b0; sh = 31'd0; cnt = 5'd0; act = 1'b0; end
endmodule
