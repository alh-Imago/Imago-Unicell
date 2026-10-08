// hexn_cell_v1.v -- Hex-N cell, draft v0.3 in docs/hex-n/walkthrough-v0.2.md (Alan's description of 9 Oct 2026). A SCOPING PROTOTYPE: each assumption is marked A1..A7.
// FACES faces, PAIRS lanes per face. A lane is logically one wire whose direction is time-shared (never both ways at once); on the die it is rx (arrives) + tx (leaves).
// The mesh controller supplies three global signals: `phase` (0 = forward phase, 1 = feedback phase), `ph_start` (first clock of each phase), `win_end` (last clock of the feedback phase).
//   dir (2 bits per lane): 0 IN_ONLY (receive in forward) | 1 OUT_ONLY (send in forward) | 2 IN_THEN_OUT (receive forward, send in feedback) | 3 OUT_THEN_IN (send forward, receive in feedback)
//   code (2 bits per lane): 0 ALL-THREE ("AND") | 1 CHOOSE ("OR") | 2 STEER ("XOR") | 3 NEGATIVE ("NOT")
// Per clock a face ACCUMULATES: every active receiving lane adds 1 (NEGATIVE lanes subtract 1), floored at 0, saturating at 2^AW-1 (A1). Forward-phase total = fwd weight; feedback-phase total = fb weight.
// At win_end: reach = fwd weight >= thr + bias (A2: the shared 16-bit bias RAISES the threshold = damping); margin = min(weight - (thr+bias), 6) (A3: graded, capped);
//   fbok = fb weight > 0 (A4: "the feedback agrees" = any net positive feedback arrived); inany = some active lane received in the forward phase (A5: the "in-path").
// In the NEXT window a transmitting lane sends a burst of 1+margin clocks high if its code lets it pass (graded flow: more margin, more clocks, more weight at the neighbour):
//   ALL-THREE: reach & fbok & inany | CHOOSE: reach & this is the lowest-numbered active sending-capable CHOOSE lane of the face (A6) | STEER: reach & (even lane: inany, odd lane: ~inany) (A7) | NEGATIVE: never sends.
// Nothing learns at run time; training changes cfg_* offline. The phase length must be >= 7 clocks (longest burst).
`default_nettype none
module hexn_cell_v1 #(
    parameter FACES = 6, parameter PAIRS = 4, parameter AW = 6
) (
    input  wire                       clk,
    input  wire                       rst,
    input  wire                       phase,
    input  wire                       ph_start,
    input  wire                       win_end,
    input  wire [FACES*PAIRS-1:0]     rx,
    output wire [FACES*PAIRS-1:0]     tx,
    input  wire [FACES*PAIRS-1:0]     cfg_active,
    input  wire [2*FACES*PAIRS-1:0]   cfg_dir,
    input  wire [2*FACES*PAIRS-1:0]   cfg_code,
    input  wire [FACES*AW-1:0]        cfg_thr,
    input  wire [15:0]                bias
);
    localparam N = FACES * PAIRS;
    localparam CW = $clog2(PAIRS + 1);              // width of a per-face lane count
    localparam SW = AW + CW + 1;                    // width of accumulator arithmetic
    reg [FACES*AW-1:0] fwd_acc, fb_acc;
    reg [FACES-1:0]    inany, inany_r, fbok_r, reach_r;
    reg [FACES*3-1:0]  margin_r;
    reg [2:0]          bc;                           // clocks since the phase started (shared by every lane), saturating at 7

    // ---- per-lane receive flags
    wire [N-1:0] rl;
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : RL
        wire [1:0] d = cfg_dir[2*g +: 2];
        assign rl[g] = cfg_active[g] & rx[g] & (phase ? (d == 2'd3) : (d == 2'd0 || d == 2'd2));
    end endgenerate

    // ---- per-face: counts, accumulator next values
    wire [FACES*AW-1:0] fwd_nxt, fb_nxt;
    wire [FACES-1:0]    any_rx;
    generate for (g = 0; g < FACES; g = g + 1) begin : FA
        reg [CW-1:0] pos, neg;
        integer p;
        always @* begin
            pos = 0; neg = 0;
            for (p = 0; p < PAIRS; p = p + 1)
                if (rl[g*PAIRS + p]) begin
                    if (cfg_code[2*(g*PAIRS + p) +: 2] == 2'd3) neg = neg + 1'b1; else pos = pos + 1'b1;
                end
        end
        assign any_rx[g] = |rl[g*PAIRS +: PAIRS];
        wire [AW-1:0]   fa = fwd_acc[g*AW +: AW], fbv = fb_acc[g*AW +: AW];
        wire [SW-1:0]   fbase = ph_start ? {SW{1'b0}} : {{(SW-AW){1'b0}}, fa};
        wire [SW-1:0]   fs = fbase + {{(SW-CW){1'b0}}, pos} - {{(SW-CW){1'b0}}, neg};
        wire [SW-1:0]   bs = {{(SW-AW){1'b0}}, fbv} + {{(SW-CW){1'b0}}, pos} - {{(SW-CW){1'b0}}, neg};
        assign fwd_nxt[g*AW +: AW] = fs[SW-1] ? {AW{1'b0}} : (|fs[SW-2:AW] ? {AW{1'b1}} : fs[AW-1:0]);   // floor 0, saturate
        assign fb_nxt[g*AW +: AW]  = bs[SW-1] ? {AW{1'b0}} : (|bs[SW-2:AW] ? {AW{1'b1}} : bs[AW-1:0]);
    end endgenerate

    // ---- window-end evaluation (combinational on the registered totals)
    wire [FACES-1:0] reach_n, fbok_n;
    wire [FACES*3-1:0] margin_n;
    generate for (g = 0; g < FACES; g = g + 1) begin : EV
        wire [AW-1:0]  bcl = (|bias[15:AW]) ? {AW{1'b1}} : bias[AW-1:0];                           // A2: the 16-bit bias, clamped to the weight width
        wire [AW+1:0]  te  = {2'd0, cfg_thr[g*AW +: AW]} + {2'd0, bcl};
        wire [AW+1:0]  w   = {2'd0, fwd_acc[g*AW +: AW]};
        wire [AW+1:0]  df  = w - te;
        assign reach_n[g]  = (w >= te);
        assign margin_n[g*3 +: 3] = (|df[AW+1:3] | (df[2:0] > 3'd6)) ? 3'd6 : df[2:0];                // A3 (only used when reach)
        assign fbok_n[g]   = |fb_nxt[g*AW +: AW];                                                    // A4
    end endgenerate

    always @(posedge clk) begin
        if (rst) begin
            fwd_acc <= 0; fb_acc <= 0; inany <= 0; inany_r <= 0; fbok_r <= 0; reach_r <= 0; margin_r <= 0; bc <= 0;
        end else begin
            if (!phase) begin
                fwd_acc <= fwd_nxt;
                if (ph_start) begin fb_acc <= 0; inany <= any_rx; end else inany <= inany | any_rx;   // A5
            end else fb_acc <= fb_nxt;
            if (ph_start) bc <= 0; else if (bc != 3'd7) bc <= bc + 1'b1;
            if (win_end && phase) begin
                reach_r <= reach_n; fbok_r <= fbok_n; inany_r <= inany;
                margin_r <= margin_n;
            end
        end
    end

    // ---- transmit: a burst of 1+margin clocks when the lane's code lets the path pass
    wire [N-1:0] tx_w;
    generate for (g = 0; g < N; g = g + 1) begin : TX
        localparam F = g / PAIRS, P = g % PAIRS;
        wire [1:0] d = cfg_dir[2*g +: 2], cd = cfg_code[2*g +: 2];
        wire sender = cfg_active[g] & (phase ? (d == 2'd2) : (d == 2'd1 || d == 2'd3));
        // CHOOSE: this is the lowest-numbered active, sending-capable CHOOSE lane of the face (A6)
        wire [P:0] earlier;                                                                        // earlier[q] = some lane below q chosen
        assign earlier[0] = 1'b0;
        genvar q;
        for (q = 0; q < P; q = q + 1) begin : EQ
            wire hit = cfg_active[F*PAIRS + q] & (cfg_code[2*(F*PAIRS + q) +: 2] == 2'd1) & (cfg_dir[2*(F*PAIRS + q) +: 2] != 2'd0);
            assign earlier[q+1] = earlier[q] | hit;
        end
        wire r = reach_r[F], fo = fbok_r[F], ia = inany_r[F];
        wire pass = (cd == 2'd0) ? (r & fo & ia) : (cd == 2'd1) ? (r & ~earlier[P]) : (cd == 2'd2) ? (r & ((P % 2) ? ~ia : ia)) : 1'b0;   // A7 for STEER
        assign tx_w[g] = sender & pass & (bc < (margin_r[F*3 +: 3] + 3'd1));
    end endgenerate
    assign tx = tx_w;
endmodule
`default_nettype wire
