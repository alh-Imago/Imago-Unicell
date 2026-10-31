// hexn_neural_v1: THE LAYER 1 JUDGE AND ITS LEARNING RULE IN WHOLE NUMBERS (31 Oct 2026; simulation + synthesis counts only; nothing on a card).
// Bit-true to tools/hexn_layer1_int_v4.py (OnlineInt4: v1 with the bias step corrected from x8 to x64): serial, ONE multiplier, NIN weights + a bias.
//   eval : a = sum(W[i]*x[i]) + B ; idx = (a >>> (WB-6)) + 256 clipped to 0..511 ; y = tanh table[idx] (Q8, signed)
//   learn: eval first, then err = y - t ; gain = 256 - ((y*y) >> 8) ; eg = 5*err*gain*(m2?2:1) ;
//          W[i] -= (eg*x[i] + 2^(sh-1)) >>> sh   (i < NIN) ; B -= (eg*64 + 2^(sh-1)) >>> sh ; sh = 29 - WB
// x: NIN unsigned XB-bit counts (the last input is 8*parity, as in the Python model). t: teacher x256, -256..256.
// Commands (one clock pulse): go_eval, go_learn ; weight write: w_wr with w_addr (0..NIN-1 weights, NIN bias), w_data. done pulses when y (and the update) are final.
module hexn_neural_v1 #(parameter NIN = 7, XB = 6, WB = 14, WW = 16, AW = 28) (
  input clk, input rst,
  input go_eval, input go_learn,
  input [NIN*XB-1:0] x, input signed [9:0] t, input m2,
  input w_wr, input [3:0] w_addr, input signed [WW-1:0] w_data,
  output reg signed [9:0] y, output reg done,
  output [(NIN+1)*WW-1:0] w_flat);
  localparam SH = 29 - WB;
  reg signed [WW-1:0] W [0:NIN];
  reg [NIN*XB-1:0] xr; reg signed [9:0] tr; reg m2r, lr;
  reg signed [AW-1:0] acc; reg [3:0] cnt; reg [3:0] st;
  reg [8:0] idx; wire signed [9:0] q; hexn_tanh512_v1 rom (.clk(clk), .a(idx), .q(q));
  reg signed [31:0] eg;
  localparam IDLE = 0, ACC = 1, IDX = 2, ROM = 3, OUT = 4, EG = 5, UPD = 6;
  wire [XB:0] xsel = (cnt < NIN) ? {1'b0, xr[cnt*XB +: XB]} : 64;   // bias is stepped as if its input were 64 (see tools/hexn_layer1_int_v4.py)
  wire signed [AW-1:0] term = $signed(W[cnt]) * $signed({1'b0, xsel});
  wire signed [AW-1:0] aidx = acc >>> (WB - 6);
  wire signed [AW-1:0] ai2 = aidx + 256;
  wire signed [10:0] err = y - tr;
  wire signed [19:0] yy = y * y;
  wire signed [19:0] yy_hi = yy >>> 8;
  wire signed [10:0] gain = 11'sd256 - yy_hi;
  wire signed [31:0] prod = eg * $signed({1'b0, xsel});
  wire signed [31:0] stp = (prod + (32'sd1 <<< (SH - 1))) >>> SH;
  wire signed [31:0] wn = $signed(W[cnt]) - stp;
  genvar g; generate for (g = 0; g <= NIN; g = g + 1) begin : fl assign w_flat[g*WW +: WW] = W[g]; end endgenerate
  integer k;
  always @(posedge clk) begin
    done <= 1'b0;
    if (rst) begin st <= IDLE; for (k = 0; k <= NIN; k = k + 1) W[k] <= 0; end
    else begin
      if (w_wr) W[w_addr] <= w_data;
      case (st)
        IDLE: if (go_eval || go_learn) begin xr <= x; tr <= t; m2r <= m2; lr <= go_learn; cnt <= 0; acc <= 0; st <= ACC; end
        ACC: begin
          if (cnt == NIN) begin acc <= acc + $signed(W[NIN]); st <= IDX; end   // bias added once (no multiply)
          else begin acc <= acc + term; cnt <= cnt + 1; end
        end
        IDX: begin idx <= (ai2 < 0) ? 9'd0 : (ai2 > 511) ? 9'd511 : ai2[8:0]; st <= ROM; end
        ROM: st <= OUT;
        OUT: begin y <= q; if (lr) st <= EG; else begin done <= 1'b1; st <= IDLE; end end
        EG: begin eg <= 5 * $signed(err) * $signed(gain) * (m2r ? 2 : 1); cnt <= 0; st <= UPD; end
        UPD: begin
          W[cnt] <= wn[WW-1:0];
          if (cnt == NIN) begin done <= 1'b1; st <= IDLE; end else cnt <= cnt + 1;
        end
        default: st <= IDLE;
      endcase
    end
  end
endmodule
