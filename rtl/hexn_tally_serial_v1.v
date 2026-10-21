// Hex-N counted detector, TRAINING SIDE, SERIAL (v1; new file; sizing sketch checked against the Python model).  Same function as hexn_tally_v1 but ONE lane per clock through ONE shared saturating adder:
//   start_train : latch x/own, then LANES clocks: lane idx counts UP by PUSH_OWN (own class) or DOWN by 1 when x[idx]=1 (saturating at +-(2^(CW-1)-1)).
//   start_final : LANES clocks: wpos[idx] <= cnt[idx] >= +T, wneg[idx] <= cnt[idx] <= -T (one comparator pair, results held in registers for the run-time cell).
//   start_score : latch x/own, then LANES clocks: score = sum over lanes of x*(wpos - wneg); at the end acc_own/acc_oth += score and n_own/n_oth += 1.
// busy is high while a pass runs; start_* pulses are ignored while busy.  Per sample the cost is LANES+1 clocks.  The threshold division is not included.
module hexn_tally_serial_v1 #(parameter LANES = 12, parameter CW = 6, parameter PUSH_OWN = 3, parameter T = 8, parameter SW = 5, parameter AW = 12, parameter NW = 8, parameter IW = 4) (
    input  wire clk, input wire rst,
    input  wire start_train, input wire start_final, input wire start_score, input wire own,
    input  wire [LANES-1:0] x,
    output wire busy,
    output reg  [LANES-1:0] wpos, output reg [LANES-1:0] wneg,
    output reg  signed [AW-1:0] acc_own, output reg signed [AW-1:0] acc_oth,
    output reg  [NW-1:0] n_own, output reg [NW-1:0] n_oth);
  localparam signed [CW-1:0] MAXV = (1 << (CW-1)) - 1;
  localparam [1:0] IDLE = 0, TRAIN = 1, FINAL = 2, SCORE = 3;
  reg [1:0] mode; reg [IW-1:0] idx; reg [LANES-1:0] xr; reg ownr; reg signed [SW-1:0] srun;
  reg signed [CW-1:0] cnt [0:LANES-1];
  assign busy = (mode != IDLE);
  wire signed [CW-1:0] c = cnt[idx];
  wire signed [CW:0] nxt = ownr ? ($signed({c[CW-1], c}) + PUSH_OWN) : ($signed({c[CW-1], c}) - 1);
  wire [LANES-1:0] xm = xr >> idx; wire xi = xm[0];
  wire [LANES-1:0] pm = wpos >> idx; wire [LANES-1:0] nm = wneg >> idx;
  wire signed [SW-1:0] delta = xi ? (pm[0] ? 1 : (nm[0] ? -1 : 0)) : 0;
  wire last = (idx == LANES - 1);
  integer i;
  always @(posedge clk) begin
    if (rst) begin
      mode <= IDLE; idx <= 0; wpos <= 0; wneg <= 0; acc_own <= 0; acc_oth <= 0; n_own <= 0; n_oth <= 0; srun <= 0; xr <= 0; ownr <= 0;
      for (i = 0; i < LANES; i = i + 1) cnt[i] <= 0;
    end else case (mode)
      IDLE: begin
        idx <= 0; srun <= 0;
        if (start_train) begin xr <= x; ownr <= own; mode <= TRAIN; end
        else if (start_score) begin xr <= x; ownr <= own; mode <= SCORE; end
        else if (start_final) mode <= FINAL;
      end
      TRAIN: begin
        if (xi) cnt[idx] <= (nxt > MAXV) ? MAXV : (nxt < -MAXV) ? -MAXV : nxt[CW-1:0];
        if (last) mode <= IDLE; else idx <= idx + 1;
      end
      FINAL: begin
        wpos[idx] <= (c >= T); wneg[idx] <= (c <= -T);
        if (last) mode <= IDLE; else idx <= idx + 1;
      end
      SCORE: begin
        if (last) begin
          if (ownr) begin acc_own <= acc_own + srun + delta; n_own <= n_own + 1; end
          else begin acc_oth <= acc_oth + srun + delta; n_oth <= n_oth + 1; end
          mode <= IDLE;
        end else begin srun <= srun + delta; idx <= idx + 1; end
      end
    endcase
  end
endmodule
