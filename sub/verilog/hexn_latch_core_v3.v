`default_nettype none
// hexn_latch_core_v3 = hexn_latch_core_v2 (untouched) (3 Nov 2026, Alan 14:30 "send a word on each pulse"): the latch now REPORTS ITS LEVEL AS A WORD.
// Every set / clear / toggle pulse updates the level exactly as in v2 (clear wins over set, set over toggle) and, one clock later, sends ONE serial word on r/rs: value 1 if the new level is on, 0 if off
// (start flag rs high on bit 0, bits 1..31 zero, so a one-clock r/rs pulse is the whole word). A pulse that arrives while the previous report is still going out (fewer than 32 clocks after it) still changes the
// level but sends no word of its own: the next pulse after the gap reports the level it finds. q is also still available as a plain output.
module hexn_latch_core_v3 (input wire clk, input wire clear, input wire set_in, input wire clear_in, input wire toggle_in, output reg q, output reg r, output reg rs);
    reg [5:0] gap = 6'd0;
    wire ev = set_in | clear_in | toggle_in;
    wire qn = (clear_in) ? 1'b0 : set_in ? 1'b1 : toggle_in ? ~q : q;
    always @(posedge clk) begin
        r <= 1'b0; rs <= 1'b0;
        if (clear) begin q <= 1'b0; gap <= 6'd0; end
        else begin
            if (ev) q <= qn;
            if (gap != 6'd0) gap <= gap - 6'd1;
            if (ev && gap == 6'd0) begin r <= qn; rs <= 1'b1; gap <= 6'd31; end
        end
    end
    initial begin q = 1'b0; r = 1'b0; rs = 1'b0; end
endmodule
