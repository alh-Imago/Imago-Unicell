`default_nettype none
// hexn_det_v3.v -- Clone of hexn_det_v2.v (left untouched). v3 = NO FEEDBACK PHASE (Alan 22 Oct 2026: "the detector chip can lose the feedback"). The detector only ever accumulates the forward total, so there is no phase input:
// every window is PL clocks of forward accumulation. The result (reach, margin) is taken at the FIRST clock of the next window (ph_start), from the finished accumulator, and the output burst of margin+1 clocks follows in
// clocks 1..margin+1 of that window (margin <= 6, so at most 7 clocks, inside PL = 10). A run therefore needs only 2 windows = 2*PL clocks: window 0 accumulates, window 1 sends (the chip's old timing used 2*2*PL).
// Why the result is taken at ph_start and not at the end of the window: at the last clock of a window the accumulator has taken only PL-1 of its PL additions (the last one lands on that clock edge); one clock later it is complete.
// bc (burst clock counter) is cleared at ph_start and saturates at 7 (> margin+1 at most 7 never reaches 7 clocks of burst except margin 6 = 7 clocks: bc 0..6), so no burst is sent in clock 0 of a window.
module hexn_det_v3 #(
    parameter NB = 12, parameter AW = 6
) (
    input  wire          clk,
    input  wire          rst,
    input  wire          ph_start,     // first clock of a window
    input  wire [NB-1:0] rx,
    input  wire [NB-1:0] w_pos,        // lane is +1
    input  wire [NB-1:0] w_neg,        // lane is -1   (both 0 = lane off)
    input  wire [AW-1:0] cfg_thr,
    output wire          tx
);
    localparam CW = $clog2(NB + 1);
    localparam SW = AW + CW + 1;
    reg [AW-1:0] fwd_acc;
    reg          reach_r;
    reg [2:0]    margin_r;
    reg [2:0]    bc;

    reg signed [CW:0] net;
    integer p;
    always @* begin
        net = 0;
        for (p = 0; p < NB; p = p + 1) net = net + $signed({{CW{1'b0}}, rx[p] & w_pos[p]}) - $signed({{CW{1'b0}}, rx[p] & w_neg[p]});
    end
    wire [SW-1:0] fbase = ph_start ? {SW{1'b0}} : {{(SW-AW){1'b0}}, fwd_acc};
    wire [SW-1:0] fs = fbase + {{(SW-CW-1){net[CW]}}, net};
    wire [AW-1:0] fwd_nxt = fs[SW-1] ? {AW{1'b0}} : (|fs[SW-2:AW] ? {AW{1'b1}} : fs[AW-1:0]);

    wire [AW:0]   df = {1'b0, fwd_acc} - {1'b0, cfg_thr};
    wire          reach_n  = (fwd_acc >= cfg_thr);
    wire [2:0]    margin_n = (|df[AW:3] | (df[2:0] > 3'd6)) ? 3'd6 : df[2:0];

    always @(posedge clk) begin
        if (rst) begin
            fwd_acc <= 0; reach_r <= 0; margin_r <= 0; bc <= 3'd7;
        end else begin
            fwd_acc <= fwd_nxt;
            if (ph_start) begin reach_r <= reach_n; margin_r <= margin_n; bc <= 0; end
            else if (bc != 3'd7) bc <= bc + 1'b1;
        end
    end
    // clock 0 of a window: bc still holds its saturated 7, so nothing is sent; the burst starts when bc = 0 (clock 1)
    assign tx = reach_r & (bc < (margin_r + 3'd1));
endmodule
`default_nettype wire
