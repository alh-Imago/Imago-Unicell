`default_nettype none
// hexn_speech_chain_v1.v -- the speech chain in one block: window detectors (event-driven, widened), count/log-probability store, decision and early-stop flag.
// 10 Nov 2026. Reference model: tools/hexn_chain_hw_v1.py (bit-exact cross-check: tests/vm/test_hexn_speech_chain_v1.py). Direction doc section 63. NOT built on a card yet.
// Clone-in-spirit of the counted detector (rtl/hexn_det_v4.v, left untouched): same ternary lanes (+1 / -1 / 0) and signed margin, but WIDENED: instead of 12 to 20 wires held in parallel, a window of
// STEPS time steps x NLINES lines is delivered as EVENTS. One event = one address (step-in-window * NLINES + line); the block reads ONE word of ternary weights for all 10 detectors and adds it to 10 accumulators.
//   WROM  : NWIN * STEPS * NLINES words of 20 bits, detector c in bits [2c+1:2c]: 00 = 0, 01 = +1, 11 = -1
//   THR   : NWIN words of 80 bits, detector c's threshold = signed byte [8c+7:8c]
//   LP    : NWIN * 11 * 11 words of 80 bits, address (win*11 + prev)*11 + cls, detector/digit d's log-probability (16 x ln p, -127..0) = signed byte [8d+7:8d]
//   CFG   : word w (0..NWIN-1) = shift code of window w in [3:0]; word NWIN = the stop gap (signed 16 bits)
// Per window end (win_end pulse; the host leaves >= 2 idle clocks after the last event of the window): margin = acc - thr; class = largest margin (lowest index on a tie) if > 0 else NONE (10);
// msum += margin; pathq[d] += LP[d][win][prev][cls]; score[d] = pathq[d] + SH(msum[d], code); pred = argmax score (lowest on a tie); gap = best msum - second best msum; stop = gap >= CFG gap.
// SH: code 0 = 0, 1 = arithmetic right shift 1, k >= 2 = left shift k-2 (shifts only, no multiplier). Output (out_valid pulse) 6 clocks after win_end.
// Config can be preloaded from files (parameters, for simulation and for a fit/timing build) or written at run time through the cfg_ port (cfg_sel: 0 WROM, 1 THR, 2 LP, 3 CFG).
module hexn_speech_chain_v1 #(
    parameter NWIN = 5, parameter STEPS = 4, parameter NLINES = 48,
    parameter WFILE = "", parameter TFILE = "", parameter LFILE = "", parameter CFILE = ""
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        cfg_we,
    input  wire [2:0]  cfg_sel,
    input  wire [15:0] cfg_addr,
    input  wire [79:0] cfg_data,
    input  wire        start,        // clear the state for a new recording
    input  wire        ev_valid,
    input  wire [7:0]  ev_idx,       // step-in-window * NLINES + line
    input  wire        win_end,
    output reg         out_valid,
    output reg  [2:0]  out_win,
    output reg  [3:0]  out_cls,
    output reg  [3:0]  out_pred,
    output reg  signed [16:0] out_gap,
    output reg         out_stop
);
    localparam NC = 10, WSZ = STEPS * NLINES, NA = 11;
    reg [19:0] wrom [0:NWIN*WSZ-1];
    reg [79:0] thr  [0:NWIN-1];
    reg [79:0] lp   [0:NWIN*NA*NA-1];
    reg [15:0] cfgm [0:NWIN];
    initial begin
        if (WFILE != "") $readmemh(WFILE, wrom);
        if (TFILE != "") $readmemh(TFILE, thr);
        if (LFILE != "") $readmemh(LFILE, lp);
        if (CFILE != "") $readmemh(CFILE, cfgm);
    end
    always @(posedge clk) if (cfg_we) begin
        case (cfg_sel)
            3'd0: wrom[cfg_addr] <= cfg_data[19:0];
            3'd1: thr[cfg_addr]  <= cfg_data;
            3'd2: lp[cfg_addr]   <= cfg_data;
            3'd3: cfgm[cfg_addr] <= cfg_data[15:0];
            default: ;
        endcase
    end

    reg [2:0]  win;
    reg [12:0] wbase;
    reg [6:0]  win11;
    reg [3:0]  prev;
    reg [3:0]  st;
    reg signed [7:0]  acc   [0:NC-1];
    reg signed [8:0]  mg    [0:NC-1];
    reg signed [15:0] msum  [0:NC-1];
    reg signed [15:0] pathq [0:NC-1];
    reg signed [23:0] sc    [0:NC-1];
    reg [79:0] thrw, lpw;
    reg [19:0] wword;
    reg        v1;
    reg [3:0]  cls_r;
    reg signed [16:0] gap_r;
    reg [79:0] lp_rd;

    // blocking temporaries used inside the clocked block
    integer c;
    reg [3:0]  am;
    reg signed [8:0]  mbest;
    reg signed [15:0] b1, b2;
    reg signed [23:0] sbest, sh;
    reg [3:0]  clsc;
    reg [6:0]  t7;
    reg [11:0] ad11;
    reg [11:0] lpad;
    reg [3:0]  cd;
    reg signed [15:0] gapcfg;

    wire [12:0] waddr = wbase + {5'd0, ev_idx};

    always @(posedge clk) begin
        out_valid <= 1'b0;
        wword <= wrom[waddr];
        v1    <= ev_valid;
        if (rst) begin
            st <= 4'd0; v1 <= 1'b0;
        end
        if (start) begin
            win <= 3'd0; wbase <= 13'd0; win11 <= 7'd0; prev <= 4'd10; st <= 4'd0;
            for (c = 0; c < NC; c = c + 1) begin acc[c] <= 8'sd0; msum[c] <= 16'sd0; pathq[c] <= 16'sd0; end
        end else begin
            if (v1) begin
                for (c = 0; c < NC; c = c + 1)
                    acc[c] <= acc[c] + ((wword[2*c +: 2] == 2'b01) ? 8'sd1 : (wword[2*c +: 2] == 2'b11) ? -8'sd1 : 8'sd0);
            end
            case (st)
                4'd0: if (win_end) begin thrw <= thr[win]; st <= 4'd1; end
                4'd1: begin
                    for (c = 0; c < NC; c = c + 1) mg[c] <= $signed({acc[c][7], acc[c]}) - $signed({thrw[8*c+7], thrw[8*c +: 8]});
                    st <= 4'd2;
                end
                4'd2: begin
                    am = 4'd0; mbest = mg[0];
                    for (c = 1; c < NC; c = c + 1) if (mg[c] > mbest) begin mbest = mg[c]; am = c[3:0]; end
                    clsc = (mbest > 9'sd0) ? am : 4'd10;
                    cls_r <= clsc;
                    t7 = win11 + {3'd0, prev};                       // win*11 + prev
                    ad11 = ({5'd0, t7} << 3) + ({5'd0, t7} << 1) + {5'd0, t7};   // x 11
                    lpad = ad11 + {8'd0, clsc};
                    lp_rd = lp[lpad];
                    st <= 4'd3;
                end
                4'd3: begin
                    for (c = 0; c < NC; c = c + 1) begin
                        pathq[c] <= pathq[c] + $signed({{8{lp_rd[8*c+7]}}, lp_rd[8*c +: 8]});
                        msum[c]  <= msum[c] + $signed({{7{mg[c][8]}}, mg[c]});
                        acc[c]   <= 8'sd0;
                    end
                    st <= 4'd4;
                end
                4'd4: begin
                    cd = cfgm[win][3:0]; gapcfg = cfgm[NWIN];
                    for (c = 0; c < NC; c = c + 1) begin
                        if (cd == 4'd0) sh = 24'sd0;
                        else if (cd == 4'd1) sh = $signed({{8{msum[c][15]}}, msum[c]}) >>> 1;
                        else sh = $signed({{8{msum[c][15]}}, msum[c]}) <<< (cd - 4'd2);
                        sc[c] <= $signed({{8{pathq[c][15]}}, pathq[c]}) + sh;
                    end
                    b1 = msum[0]; b2 = -16'sd32768;                  // best and second best msum
                    for (c = 1; c < NC; c = c + 1) begin
                        if (msum[c] > b1) begin b2 = b1; b1 = msum[c]; end
                        else if (msum[c] > b2) b2 = msum[c];
                    end
                    gap_r <= $signed({b1[15], b1}) - $signed({b2[15], b2});
                    st <= 4'd5;
                end
                4'd5: begin
                    am = 4'd0; sbest = sc[0];
                    for (c = 1; c < NC; c = c + 1) if (sc[c] > sbest) begin sbest = sc[c]; am = c[3:0]; end
                    gapcfg = cfgm[NWIN];
                    out_valid <= 1'b1; out_win <= win; out_cls <= cls_r; out_pred <= am; out_gap <= gap_r;
                    out_stop <= (gap_r >= $signed({gapcfg[15], gapcfg}));
                    prev <= cls_r; win <= win + 3'd1; wbase <= wbase + WSZ; win11 <= win11 + 7'd11;
                    st <= 4'd0;
                end
                default: st <= 4'd0;
            endcase
        end
    end
endmodule
`default_nettype wire
