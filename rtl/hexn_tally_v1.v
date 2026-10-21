// Hex-N counted detector, TRAINING SIDE (v1; new file; sizing sketch checked against the Python model, not yet integrated with hexn_cell_v2).
// One detector = LANES input lanes. Per lane an up/down saturating counter (CW bits, +-(2^(CW-1)-1)):
//   on a training sample (train_en pulse), every lane whose input bit x[j] is 1 counts UP by PUSH_OWN if the sample is of this detector's own class (own=1), else DOWN by 1.
// After the pass the lane weights are read combinationally: wpos[j] = cnt >= +T, wneg[j] = cnt <= -T (neither = lane off).  Python model: tools/hexn_tally_v4.py (PUSH_OWN = classes-1, T = samples per class / 2).
// Score pass (score_en pulse, weights frozen): score = popcount(x & wpos) - popcount(x & wneg) (signed, SW bits) is added to acc_own (if own) or acc_oth, and the matching sample counter n_own / n_oth counts up;
// a host (or a small divider, NOT included here) turns these into the midpoint threshold = (acc_own/n_own + acc_oth/n_oth)/2 and loads it into the cell.  The run-time cell (hexn_cell_v2) is separate.
module hexn_tally_v1 #(parameter LANES = 12, parameter CW = 6, parameter PUSH_OWN = 3, parameter T = 8, parameter SW = 5, parameter AW = 12, parameter NW = 8) (
    input  wire clk, input wire rst,
    input  wire train_en, input wire score_en, input wire own,
    input  wire [LANES-1:0] x,
    output wire [LANES-1:0] wpos, output wire [LANES-1:0] wneg,
    output wire signed [SW-1:0] score,
    output reg  signed [AW-1:0] acc_own, output reg signed [AW-1:0] acc_oth,
    output reg  [NW-1:0] n_own, output reg [NW-1:0] n_oth);
  localparam signed [CW-1:0] MAXV = (1 << (CW-1)) - 1;
  reg signed [CW-1:0] cnt [0:LANES-1];
  genvar j;
  generate for (j = 0; j < LANES; j = j + 1) begin : lane
    wire signed [CW:0] nxt = own ? ($signed({cnt[j][CW-1], cnt[j]}) + PUSH_OWN) : ($signed({cnt[j][CW-1], cnt[j]}) - 1);
    always @(posedge clk) begin
      if (rst) cnt[j] <= 0;
      else if (train_en && x[j]) cnt[j] <= (nxt > MAXV) ? MAXV : (nxt < -MAXV) ? -MAXV : nxt[CW-1:0];
    end
    assign wpos[j] = (cnt[j] >= T);
    assign wneg[j] = (cnt[j] <= -T);
  end endgenerate
  integer k; reg [SW-1:0] pc_p, pc_n;
  always @* begin pc_p = 0; pc_n = 0; for (k = 0; k < LANES; k = k + 1) begin pc_p = pc_p + (x[k] & wpos[k]); pc_n = pc_n + (x[k] & wneg[k]); end end
  assign score = $signed(pc_p) - $signed(pc_n);
  always @(posedge clk) begin
    if (rst) begin acc_own <= 0; acc_oth <= 0; n_own <= 0; n_oth <= 0; end
    else if (score_en) begin
      if (own) begin acc_own <= acc_own + score; n_own <= n_own + 1; end
      else begin acc_oth <= acc_oth + score; n_oth <= n_oth + 1; end
    end
  end
endmodule
