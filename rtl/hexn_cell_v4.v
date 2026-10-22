// hexn_cell_v4.v -- Clone of hexn_cell_v3.v (left untouched). v4 adds the input leak_sh: at ph_start the forward total is replaced by a - (a >> leak_sh) instead of 0 (leak_sh = 0 gives a - a = 0, i.e. v3 exactly; 7 keeps it). Everything else as v3.
// hexn_cell_v3.v -- Clone of hexn_cell_v2.v (left untouched). v3 adds the output port fwd_o (the forward total register) so a parent can read it; v2 was read by hierarchical name (fcell.fwd_acc), which simulates but has no driver in yosys.
`default_nettype none
// hexn_cell_v2.v -- Hex-N cell v2: the faces feed ONE decision (Alan's choice of 20 Oct 2026; the model is tools/hexn_cell_v2_model.py, assumptions B1..B4 there).
// Clone of hexn_cell_v1.v (left untouched). Changes: ONE forward total and ONE feedback total for the whole cell (every active receiving lane on every face adds 1, NEGATIVE lanes subtract 1),
// ONE threshold (cfg_thr is AW bits, not one per face), one set of window-end results (reach, margin, feedback-agrees, any-input). CHOOSE still picks the lowest-numbered lane WITHIN a face.
`default_nettype none
module hexn_cell_v4 #(
    parameter FACES = 6, parameter PAIRS = 4, parameter AW = 6
) (
    input  wire                       clk,
    input  wire                       rst,
    input  wire                       phase,
    input  wire                       ph_start,
    input  wire                       win_end,
    input  wire [FACES*PAIRS-1:0]     rx,
    output wire [FACES*PAIRS-1:0]     tx,
    output wire [AW-1:0]              fwd_o,
    input  wire [2:0]                 leak_sh,
    input  wire [FACES*PAIRS-1:0]     cfg_active,
    input  wire [2*FACES*PAIRS-1:0]   cfg_dir,
    input  wire [2*FACES*PAIRS-1:0]   cfg_code,
    input  wire [AW-1:0]              cfg_thr,
    input  wire [15:0]                bias
);
    localparam N = FACES * PAIRS;
    localparam CW = $clog2(N + 1);                  // width of the cell-wide lane count
    localparam SW = AW + CW + 1;
    reg [AW-1:0] fwd_acc, fb_acc;
    reg          inany, inany_r, fbok_r, reach_r;
    reg [2:0]    margin_r;
    reg [2:0]    bc;

    wire [N-1:0] rl;
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : RL
        wire [1:0] d = cfg_dir[2*g +: 2];
        assign rl[g] = cfg_active[g] & rx[g] & (phase ? (d == 2'd3) : (d == 2'd0 || d == 2'd2));
    end endgenerate

    reg [CW-1:0] pos, neg;
    integer p;
    always @* begin
        pos = 0; neg = 0;
        for (p = 0; p < N; p = p + 1)
            if (rl[p]) begin
                if (cfg_code[2*p +: 2] == 2'd3) neg = neg + 1'b1; else pos = pos + 1'b1;
            end
    end
    wire any_rx = |rl;
    // LEAK (new in v4): at the start of a forward window the old total becomes a - (a >> leak_sh): 0 = clear (exactly v3), 1 = halve, 2 = three quarters, 3 = seven eighths ..., 7 = keep as it is.
    wire [AW-1:0] leaked = (leak_sh == 3'd7) ? fwd_acc : (fwd_acc - (fwd_acc >> leak_sh));
    wire [SW-1:0] fbase = ph_start ? {{(SW-AW){1'b0}}, leaked} : {{(SW-AW){1'b0}}, fwd_acc};
    wire [SW-1:0] fs = fbase + {{(SW-CW){1'b0}}, pos} - {{(SW-CW){1'b0}}, neg};
    wire [SW-1:0] bs = {{(SW-AW){1'b0}}, fb_acc} + {{(SW-CW){1'b0}}, pos} - {{(SW-CW){1'b0}}, neg};
    wire [AW-1:0] fwd_nxt = fs[SW-1] ? {AW{1'b0}} : (|fs[SW-2:AW] ? {AW{1'b1}} : fs[AW-1:0]);
    wire [AW-1:0] fb_nxt  = bs[SW-1] ? {AW{1'b0}} : (|bs[SW-2:AW] ? {AW{1'b1}} : bs[AW-1:0]);

    wire [AW-1:0]  bcl = (|bias[15:AW]) ? {AW{1'b1}} : bias[AW-1:0];
    wire [AW+1:0]  te  = {2'd0, cfg_thr} + {2'd0, bcl};
    wire [AW+1:0]  w   = {2'd0, fwd_acc};
    wire [AW+1:0]  df  = w - te;
    wire           reach_n  = (w >= te);
    wire [2:0]     margin_n = (|df[AW+1:3] | (df[2:0] > 3'd6)) ? 3'd6 : df[2:0];
    wire           fbok_n   = |fb_nxt;

    always @(posedge clk) begin
        if (rst) begin
            fwd_acc <= 0; fb_acc <= 0; inany <= 0; inany_r <= 0; fbok_r <= 0; reach_r <= 0; margin_r <= 0; bc <= 0;
        end else begin
            if (!phase) begin
                fwd_acc <= fwd_nxt;
                if (ph_start) begin fb_acc <= 0; inany <= any_rx; end else inany <= inany | any_rx;
            end else fb_acc <= fb_nxt;
            if (ph_start) bc <= 0; else if (bc != 3'd7) bc <= bc + 1'b1;
            if (win_end && phase) begin
                reach_r <= reach_n; fbok_r <= fbok_n; inany_r <= inany; margin_r <= margin_n;
            end
        end
    end

    wire [N-1:0] tx_w;
    generate for (g = 0; g < N; g = g + 1) begin : TX
        localparam F = g / PAIRS, P = g % PAIRS;
        wire [1:0] d = cfg_dir[2*g +: 2], cd = cfg_code[2*g +: 2];
        wire sender = cfg_active[g] & (phase ? (d == 2'd2) : (d == 2'd1 || d == 2'd3));
        wire [P:0] earlier;
        assign earlier[0] = 1'b0;
        genvar q;
        for (q = 0; q < P; q = q + 1) begin : EQ
            wire hit = cfg_active[F*PAIRS + q] & (cfg_code[2*(F*PAIRS + q) +: 2] == 2'd1) & (cfg_dir[2*(F*PAIRS + q) +: 2] != 2'd0);
            assign earlier[q+1] = earlier[q] | hit;
        end
        wire pass = (cd == 2'd0) ? (reach_r & fbok_r & inany_r) : (cd == 2'd1) ? (reach_r & ~earlier[P]) : (cd == 2'd2) ? (reach_r & ((P % 2) ? ~inany_r : inany_r)) : 1'b0;
        assign tx_w[g] = sender & pass & (bc < (margin_r + 3'd1));
    end endgenerate
    assign tx = tx_w;
    assign fwd_o = fwd_acc;
endmodule
`default_nettype wire
