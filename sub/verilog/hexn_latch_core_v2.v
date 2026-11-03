`default_nettype none
// hexn_latch_core_v2 = hexn_latch_core_v1 (untouched) (3 Nov 2026, Alan 10:07): adds the general CLEAR input (level to 0).
// hexn_latch_core_v1 -- LATCH core (2 Nov 2026, Alan 09:39), after the UniCell latch cell: a held level set by a set pulse, cleared by a clear pulse, flipped by a toggle pulse; CLEAR wins if it arrives with set
// (the UniCell rule, #279 / #284); the level is a 'valid held' signal. In this design it is also the natural source of the 'high' that starts or releases a cell. One register, no counter. Tested by tests/hexn_latch_core_v1_tb.v.
module hexn_latch_core_v2 (input wire clk, input wire clear, input wire set_in, input wire clear_in, input wire toggle_in, output reg q);
    always @(posedge clk) begin
        if (clear | clear_in) q <= 1'b0;
        else if (set_in) q <= 1'b1;
        else if (toggle_in) q <= ~q;
    end
    initial q = 1'b0;
endmodule
