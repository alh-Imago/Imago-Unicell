`default_nettype none
// hexn_hist_v1.v -- Hex-N LAYER 2 FRONT: history + dwell counter for one channel, new file (design: docs/hex-n/LAYER_INTERFACES_v1.md). NOT the path learning, only the memory it will read.
// On a change event (ev high for a clock, with the new stable class cls): the class is shifted into a depth-D list (newest in bits [W-1:0] of hist), prev_dwell takes the dwell of the state that just ended, dwell restarts at 0 and count (number of valid entries, up to D) goes up. Otherwise, on every clock where tick is high, dwell goes up by one (saturating at its maximum). An event and a tick in the same clock: the event wins (dwell restarts at 0).
module hexn_hist_v1 #(parameter W = 4, parameter D = 4, parameter DW = 12) (
    input  wire clk, input wire rst,
    input  wire ev, input wire [W-1:0] cls, input wire tick,
    output reg  [D*W-1:0] hist, output reg [DW-1:0] dwell, output reg [DW-1:0] prev_dwell, output reg [$clog2(D+1)-1:0] count
);
    always @(posedge clk) begin
        if (rst) begin hist <= {D*W{1'b0}}; dwell <= {DW{1'b0}}; prev_dwell <= {DW{1'b0}}; count <= 0; end
        else if (ev) begin
            hist <= {hist[(D-1)*W-1:0], cls}; prev_dwell <= dwell; dwell <= {DW{1'b0}}; if (count != D) count <= count + 1'b1;
        end else if (tick && dwell != {DW{1'b1}}) dwell <= dwell + 1'b1;
    end
endmodule
`default_nettype wire
