`default_nettype none
// hexn_det_v4.v -- Clone of hexn_det_v3.v (left untouched). v4 = SIGNED TOTAL AND SIGNED MARGIN (30 Oct 2026; Alan: "see what that brings"; model result in HEXN_DESIGN.md, rows 'LAYER 1 WEIGHTS' and the margin-rule row).
// Why: in v3 the accumulator clamps a negative sum to 0 and reports a margin only from 0 to 6 above the threshold, so two detectors that both fall short of their thresholds cannot be ranked.
// v4: the accumulator is SIGNED (AW magnitude bits plus a sign), saturating symmetrically at +-(2^AW - 1); the threshold is signed; at ph_start the SIGNED MARGIN (finished total minus threshold, AW+2 bits, no clamp) is latched
// and held until the next ph_start. There is NO burst output: the controller reads the K margins and takes the largest (ties to the lowest-numbered detector), see hexn_argmax_v1.v. Timing is v3's: window of PL clocks of
// accumulation, the result is taken at the first clock of the next window from the finished accumulator.
// Range note: the accumulator adds the lane sum on EVERY clock of the window, so with the lanes held for PL clocks the total is PL times the lane sum; |total| up to PL*NB must fit in AW bits (PL=10, NB=18 -> 180 -> AW 8).
module hexn_det_v4 #(
    parameter NB = 12, parameter AW = 8
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 ph_start,     // first clock of a window
    input  wire [NB-1:0]        rx,
    input  wire [NB-1:0]        w_pos,        // lane is +1
    input  wire [NB-1:0]        w_neg,        // lane is -1   (both 0 = lane off)
    input  wire signed [AW:0]   cfg_thr,      // signed threshold
    output wire signed [AW+1:0] margin        // signed margin of the last finished window (total - threshold)
);
    localparam CW = $clog2(NB + 1);
    localparam SW = AW + CW + 2;
    reg signed [AW:0]   fwd_acc;
    reg signed [AW+1:0] margin_r;

    reg signed [CW:0] net;
    integer p;
    always @* begin
        net = 0;
        for (p = 0; p < NB; p = p + 1) net = net + $signed({{CW{1'b0}}, rx[p] & w_pos[p]}) - $signed({{CW{1'b0}}, rx[p] & w_neg[p]});
    end
    wire signed [SW-1:0] fbase = ph_start ? {SW{1'b0}} : {{(SW-AW-1){fwd_acc[AW]}}, fwd_acc};
    wire signed [SW-1:0] fs    = fbase + {{(SW-CW-1){net[CW]}}, net};
    localparam signed [SW-1:0] MAXP = (1 <<< AW) - 1;
    localparam signed [SW-1:0] MAXN = -((1 <<< AW) - 1);
    wire signed [AW:0] fwd_nxt = (fs > MAXP) ? MAXP[AW:0] : (fs < MAXN) ? MAXN[AW:0] : fs[AW:0];

    always @(posedge clk) begin
        if (rst) begin fwd_acc <= 0; margin_r <= 0; end
        else begin
            fwd_acc <= fwd_nxt;
            if (ph_start) margin_r <= {fwd_acc[AW], fwd_acc} - {cfg_thr[AW], cfg_thr};
        end
    end
    assign margin = margin_r;
endmodule
`default_nettype wire
