`default_nettype none
// hexn_det_v1.v -- Hex-N MINIMAL DETECTOR (the counted detector's run-time side), Alan 21 Oct 2026: "use that design as the base unit".
// New file; hexn_cell_v2.v is left untouched. It does what ONE hexn_cell_v2 does in the counted detector bank (NB receive-only input lanes, each off / +1 / -1, one threshold, one output lane
// that sends a burst of margin+1 clocks when the forward total reached the threshold) and nothing else: no feedback total, no any-input flag, no CHOOSE chain, no bias, no unused lanes, no direction/code decode.
// Same control timing as the cell (phase, ph_start, win_end) so it can replace the cell in a bank. tools/ and rtl/tb_hexn_det_v1.v check it clock by clock against hexn_cell_v2.
module hexn_det_v1 #(
    parameter NB = 12, parameter AW = 6
) (
    input  wire          clk,
    input  wire          rst,
    input  wire          phase,
    input  wire          ph_start,
    input  wire          win_end,
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

    reg [CW-1:0] pos, neg;
    integer p;
    always @* begin
        pos = 0; neg = 0;
        for (p = 0; p < NB; p = p + 1) begin
            if (rx[p] & w_pos[p]) pos = pos + 1'b1;
            if (rx[p] & w_neg[p]) neg = neg + 1'b1;
        end
    end
    wire [SW-1:0] fbase = ph_start ? {SW{1'b0}} : {{(SW-AW){1'b0}}, fwd_acc};
    wire [SW-1:0] fs = fbase + {{(SW-CW){1'b0}}, pos} - {{(SW-CW){1'b0}}, neg};
    wire [AW-1:0] fwd_nxt = fs[SW-1] ? {AW{1'b0}} : (|fs[SW-2:AW] ? {AW{1'b1}} : fs[AW-1:0]);

    wire [AW:0]   df = {1'b0, fwd_acc} - {1'b0, cfg_thr};
    wire          reach_n  = (fwd_acc >= cfg_thr);
    wire [2:0]    margin_n = (|df[AW:3] | (df[2:0] > 3'd6)) ? 3'd6 : df[2:0];

    always @(posedge clk) begin
        if (rst) begin
            fwd_acc <= 0; reach_r <= 0; margin_r <= 0; bc <= 0;
        end else begin
            if (!phase) fwd_acc <= fwd_nxt;
            if (ph_start) bc <= 0; else if (bc != 3'd7) bc <= bc + 1'b1;
            if (win_end && phase) begin reach_r <= reach_n; margin_r <= margin_n; end
        end
    end
    assign tx = ~phase & reach_r & (bc < (margin_r + 3'd1));
endmodule
`default_nettype wire
