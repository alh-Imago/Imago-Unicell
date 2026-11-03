`default_nettype none
// hexn_seq_core_v2 = hexn_seq_core_v1 (untouched) (3 Nov 2026, Alan 10:07): adds a CLEAR input - position back to value 0, any value in flight is dropped, the edge detector is reset. Hold it >= 130 clocks as for the other cores.
// hexn_seq_core_v1 -- serial SEQUENCER core (2 Nov 2026, Alan 09:46), after the UniCell sequencer: holds up to four 32-bit values (vals, value 0 in bits 31:0) and sends the next one, LSB first with a start flag on bit 0,
// each time the advance input goes high (a rising edge: a one-clock pulse, or the start flag of a word, is enough). After the last value (len) it wraps to value 0. len = 0 sends nothing; cfgload (pulse) sets the position back to value 0.
//   An advance that arrives while a value is still being sent is IGNORED (open point: could be queued one deep). The values are configuration ports (pinned in a generated design).
module hexn_seq_core_v2 (input wire clk, input wire clear, input wire cfgload, input wire [127:0] vals, input wire [2:0] len, input wire adv, output reg r, output reg rs);
    reg [1:0] idx = 2'd0, sel = 2'd0; reg [4:0] cnt = 5'd0; reg busy = 1'b0, advq = 1'b0;
    wire [2:0] nxt = {1'b0, idx} + 3'd1;
    wire [31:0] cur = vals[{sel, 5'd0} +: 32];
    always @(posedge clk) begin
        advq <= adv & ~clear; r <= 1'b0; rs <= 1'b0;
        if (cfgload | clear) begin idx <= 2'd0; busy <= 1'b0; cnt <= 5'd0; end
        else if (busy) begin
            r <= cur[cnt]; rs <= (cnt == 5'd0); cnt <= cnt + 5'd1; if (cnt == 5'd31) busy <= 1'b0;
        end else if (adv && !advq && len != 3'd0) begin
            busy <= 1'b1; cnt <= 5'd0; sel <= idx; idx <= (nxt >= len) ? 2'd0 : nxt[1:0];
        end
    end
    initial begin r = 1'b0; rs = 1'b0; end
endmodule
