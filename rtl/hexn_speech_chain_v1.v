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
// SH: code 0 = 0, 1 = arithmetic right shift 1, k >= 2 = left shift k-2 (shifts only, no multiplier). Output (out_valid pulse) about 40 clocks after win_end (the argmax and top-2 are scans of one candidate per clock, for timing).
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
    reg [4:0]  st;
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

    // v1 timing fix (10 Nov 2026, after the first card build reached only 32.4 MHz): every 10-way argmax / top-2 is a SCAN of one candidate per clock, the shift and the add of the score are separate clocks,
    // and the store address and read are separate clocks. Results are unchanged (same tie rules); the latency from win_end to out_valid is about 40 clocks.
    reg [3:0]  am, sam, ci;
    reg signed [8:0]  mbest;
    reg signed [15:0] b1, b2;
    reg signed [23:0] sbest;
    reg signed [23:0] shv [0:NC-1];
    reg [6:0]  t7;
    reg [11:0] ad11, lpad;
    reg [3:0]  cd;
    integer c;

    wire [12:0] waddr = wbase + {5'd0, ev_idx};

    always @(posedge clk) begin
        out_valid <= 1'b0;
        wword <= wrom[waddr];
        v1    <= ev_valid;
        if (rst) begin
            st <= 5'd0; v1 <= 1'b0;
        end
        if (start) begin
            win <= 3'd0; wbase <= 13'd0; win11 <= 7'd0; prev <= 4'd10; st <= 5'd0;
            for (c = 0; c < NC; c = c + 1) begin acc[c] <= 8'sd0; msum[c] <= 16'sd0; pathq[c] <= 16'sd0; end
        end else begin
            if (v1) begin
                for (c = 0; c < NC; c = c + 1)
                    acc[c] <= acc[c] + ((wword[2*c +: 2] == 2'b01) ? 8'sd1 : (wword[2*c +: 2] == 2'b11) ? -8'sd1 : 8'sd0);
            end
            case (st)
                5'd0: if (win_end) begin thrw <= thr[win]; st <= 5'd1; end
                5'd1: begin
                    for (c = 0; c < NC; c = c + 1) mg[c] <= $signed({acc[c][7], acc[c]}) - $signed({thrw[8*c+7], thrw[8*c +: 8]});
                    st <= 5'd2;
                end
                5'd2: begin am <= 4'd0; mbest <= mg[0]; ci <= 4'd1; st <= 5'd3; end
                5'd3: begin                                                    // scan the margins, lowest index wins a tie
                    if (mg[ci] > mbest) begin mbest <= mg[ci]; am <= ci; end
                    if (ci == 4'd9) st <= 5'd4; else ci <= ci + 4'd1;
                end
                5'd4: begin cls_r <= (mbest > 9'sd0) ? am : 4'd10; st <= 5'd5; end
                5'd5: begin t7 <= win11 + {3'd0, prev}; st <= 5'd6; end                                    // win*11 + prev
                5'd6: begin ad11 <= ({5'd0, t7} << 3) + ({5'd0, t7} << 1) + {5'd0, t7}; st <= 5'd7; end    // x 11
                5'd7: begin lpad <= ad11 + {8'd0, cls_r}; st <= 5'd8; end
                5'd8: begin lp_rd <= lp[lpad]; st <= 5'd9; end
                5'd9: begin
                    for (c = 0; c < NC; c = c + 1) begin
                        pathq[c] <= pathq[c] + $signed({{8{lp_rd[8*c+7]}}, lp_rd[8*c +: 8]});
                        msum[c]  <= msum[c] + $signed({{7{mg[c][8]}}, mg[c]});
                        acc[c]   <= 8'sd0;
                    end
                    st <= 5'd10;
                end
                5'd10: begin
                    cd = cfgm[win][3:0];
                    for (c = 0; c < NC; c = c + 1) begin
                        if (cd == 4'd0) shv[c] <= 24'sd0;
                        else if (cd == 4'd1) shv[c] <= $signed({{8{msum[c][15]}}, msum[c]}) >>> 1;
                        else shv[c] <= $signed({{8{msum[c][15]}}, msum[c]}) <<< (cd - 4'd2);
                    end
                    st <= 5'd11;
                end
                5'd11: begin
                    for (c = 0; c < NC; c = c + 1) sc[c] <= $signed({{8{pathq[c][15]}}, pathq[c]}) + shv[c];
                    st <= 5'd12;
                end
                5'd12: begin sam <= 4'd0; sbest <= sc[0]; b1 <= msum[0]; b2 <= -16'sd32768; ci <= 4'd1; st <= 5'd13; end
                5'd13: begin                                                   // scan the scores (lowest index wins a tie) and the two best margin sums
                    if (sc[ci] > sbest) begin sbest <= sc[ci]; sam <= ci; end
                    if (msum[ci] > b1) begin b2 <= b1; b1 <= msum[ci]; end
                    else if (msum[ci] > b2) b2 <= msum[ci];
                    if (ci == 4'd9) st <= 5'd14; else ci <= ci + 4'd1;
                end
                5'd14: begin gap_r <= $signed({b1[15], b1}) - $signed({b2[15], b2}); st <= 5'd15; end
                5'd15: begin
                    out_valid <= 1'b1; out_win <= win; out_cls <= cls_r; out_pred <= sam; out_gap <= gap_r;
                    out_stop <= (gap_r >= $signed({cfgm[NWIN][15], cfgm[NWIN]}));
                    prev <= cls_r; win <= win + 3'd1; wbase <= wbase + WSZ; win11 <= win11 + 7'd11;
                    st <= 5'd0;
                end
                default: st <= 5'd0;
            endcase
        end
    end
endmodule
`default_nettype wire
