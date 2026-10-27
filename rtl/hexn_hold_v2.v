`default_nettype none
// hexn_hold_v2.v -- Clone of hexn_hold_v1.v (left untouched). v2 adds the input skip_none: when high, a sample whose class is NONE (all ones) is IGNORED after the first sample (it does not count as an answer, does not restart the count of a candidate, does not change dout). Found in the exact-match test (docs/hex-n/HEXN_DESIGN.md): with the strict rule a damaged frame ('unknown') restarts the count, so a new key needs N clean frames in a row; model result at 15 percent damaged frames and n = 5: missed key changes 0.141 strict, 0.032 with skip_none. skip_none = 0 behaves exactly as v1.
// (v1 text follows) hexn_hold_v1.v -- Hex-N HOLD-N-SAMPLES counter for one layer-1 bank output, new file (design: docs/hex-n/LAYER_INTERFACES_v1.md; model: tools/hexn_hold_v1.py, function hold()).
// The output dout keeps its last stable class and changes only after a new class has been the input for n samples IN A ROW. A sample is taken on a clock where en is high. The first sample after reset is taken at once (valid goes high). n = 0 or 1 passes every change straight through. A class value of all ones (15 for W = 4) is NONE ('no answer / tie') and counts as an answer like any other.
// chg is high for one clock after a sample that changed dout.
module hexn_hold_v2 #(parameter W = 4, parameter CW = 8) (
    input  wire clk, input wire rst,
    input  wire en, input wire [W-1:0] din, input wire [CW-1:0] n, input wire skip_none,
    output reg  [W-1:0] dout, output reg valid, output reg chg
);
    reg [W-1:0] cand; reg candv; reg [CW-1:0] cnt;
    wire same_cand = candv && (din == cand);
    wire [CW-1:0] nc = same_cand ? cnt + 1'b1 : {{(CW-1){1'b0}}, 1'b1};
    always @(posedge clk) begin
        chg <= 1'b0;
        if (rst) begin dout <= {W{1'b0}}; valid <= 1'b0; cand <= {W{1'b0}}; candv <= 1'b0; cnt <= {CW{1'b0}}; end
        else if (en) begin
            if (!valid) begin dout <= din; valid <= 1'b1; candv <= 1'b0; cnt <= {CW{1'b0}}; end
            else if (skip_none && din == {W{1'b1}}) begin end
            else if (din == dout) begin candv <= 1'b0; cnt <= {CW{1'b0}}; end
            else if (nc >= n) begin dout <= din; candv <= 1'b0; cnt <= {CW{1'b0}}; chg <= 1'b1; end
            else begin cand <= din; candv <= 1'b1; cnt <= nc; end
        end
    end
endmodule
`default_nettype wire
