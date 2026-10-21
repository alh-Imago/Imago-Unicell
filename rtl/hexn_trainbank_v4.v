`default_nettype none
// hexn_trainbank_v4.v -- Clone of hexn_trainbank_v3.v (left untouched). v4: (1) dbg_net / dbg_fwd = the net lane count and forward total this unit computed for each detector in the LAST ACCUM sample (8 bits each), for a board probe; (2) parameter ACCMODE: 0 = signed running sum (as v3), 1 = two unsigned counters (positive and negative lanes) and one unsigned subtraction, no signed arithmetic. Clone of hexn_trainbank_v2.v (left untouched); v3 only adds dbg_sump / dbg_sumn (16 bits per detector, the two running sums of the threshold pass) so a board can read them back. Clone of hexn_trainbank_v1.v (left untouched). v2 keeps NO weight or threshold registers: it reads each weight straight from its counter and WRITES the finished weights/thresholds out through a write port (cfg_*), into the run-time detectors' own settings (see hexn_cfgbank_v1.v). Hex-N TRAINING BANK: ONE shared training unit for a bank of K counted detectors (each NB input lanes), Alan 21 Oct 2026.  Serial and small: the K*NB lane counters live in ONE memory (a single read/write port),
// the weights are formed in place, and one divider forms every threshold.  Python reference: tools/hexn_tally_v5.py (counting up by K-1 / down by 1, saturate +-CAP; weight +1 if counter >= T, -1 if <= -T, else off; threshold = midpoint of the mean forward total of
// own-class and other-class training samples, rounded half to even).  Training is slow on purpose (about 2*K*NB clocks per sample per pass); only the run-time detectors (hexn_det_v2) work at full speed.
// Commands (pulse start with cmd while busy=0; wait for busy=0):
//   1 CLEAR   zero all counters and sums.
//   2 COUNT   one training sample (s_bits, s_label): counters of all K detectors move.        Send every training sample once.
//   3 SETW    form the weights from the counters, using t_in (= T).                           Once, after all samples.
//   4 ACCUM   one training sample again (2*K*NB clocks) (s_bits, s_label): add its forward total to the own-class or other-class sum of every detector.   Send every training sample once more.
//   5 FINISH  form every detector's threshold (midpoint rule, divider).                      Once.
// Outputs w_pos / w_neg / thr_flat are the settings of the K run-time detectors: detector k uses bits [k*NB +: NB] and [k*AW +: AW].
module hexn_trainbank_v4 #(
    parameter K = 4, parameter NB = 12, parameter AW = 6, parameter S = 16, parameter CB = 6, parameter PL = 10, parameter CAP = 31, parameter ACCMODE = 0
) (
    input  wire              clk, input wire rst,
    input  wire              start, input wire [2:0] cmd,
    input  wire [NB-1:0]     s_bits, input wire [$clog2(K)-1:0] s_label, input wire [CB-1:0] t_in,
    output reg               busy,
    output wire              cfg_w_we, output wire [$clog2(K*NB+1)-1:0] cfg_w_ad, output wire cfg_wp, output wire cfg_wn,   // one lane setting written (address = k*NB + j)
    output wire [K*8-1:0]    dbg_net, output wire [K*8-1:0] dbg_fwd,
    output wire [K*16-1:0]   dbg_sump, output wire [K*16-1:0] dbg_sumn,
    output wire              cfg_t_we, output wire [$clog2(K)-1:0] cfg_t_k, output wire [AW-1:0] cfg_t_val                    // one threshold written
);
    localparam NE  = K * NB;
    localparam AD  = $clog2(NE + 1);
    localparam KW  = $clog2(K);
    localparam MAXF = (1 << AW) - 1;
    localparam PW  = $clog2(MAXF * S + 1);                 // sum of S own-class forward totals
    localparam NW_ = $clog2(MAXF * S * (K - 1) + 1);       // sum of S*(K-1) other-class forward totals
    localparam nP  = S, nN = S * (K - 1);
    localparam DEN = 2 * nP * nN;
    localparam DW  = $clog2(DEN + 1);
    localparam NUMW = $clog2(MAXF * nP * nN * 2 + 1) + 1;
    localparam CW  = $clog2(NB + 1);

    // ---- counter memory: one read/write port, registered read
    reg signed [CB-1:0] mem [0:NE-1];
    reg signed [CB-1:0] rd;
    reg [AD-1:0] ad;
    localparam [3:0] IDLE = 0, CLR = 1, CNT_RD = 2, CNT_WR = 3, SW_RD = 4, SW_WR = 5, ACC = 6, FIN_NUM = 7, FIN_DIV = 8, FIN_SET = 9, ACC_RD = 10, ACC_WR = 11;
    reg [3:0] st; reg [KW-1:0] ik; reg [$clog2(NB)-1:0] ij;
    wire last = (ad == NE - 1);
    wire signed [CB-1:0] cnt_nxt;
    wire mem_we = (st == CLR) | (st == CNT_WR);
    wire signed [CB-1:0] mem_wd = (st == CLR) ? {CB{1'b0}} : cnt_nxt;
    always @(posedge clk) begin
        if (mem_we) mem[ad] <= mem_wd;
        rd <= mem[ad];
    end

    reg [PW-1:0]  sumP [0:K-1];
    reg [NW_-1:0] sumN [0:K-1];
    reg signed [CW+1:0] acc;
    genvar gd; generate for (gd = 0; gd < K; gd = gd + 1) begin : DBG
        assign dbg_sump[gd*16 +: 16] = {{(16-PW){1'b0}}, sumP[gd]};
        assign dbg_sumn[gd*16 +: 16] = {{(16-NW_){1'b0}}, sumN[gd]};
    end endgenerate

    // counting step: up by K-1 for the detector's own class, down by 1 otherwise, saturate at +-CAP
    localparam signed [CB+4:0] UP = K - 1, DN = -1;
    wire signed [CB+4:0] sum_c = $signed({{5{rd[CB-1]}}, rd}) + ((ik == s_label) ? UP : DN);
    assign cnt_nxt = (sum_c > CAP) ? CAP : (sum_c < -CAP) ? -CAP : sum_c[CB-1:0];

    // weights from the counters
    wire signed [CB:0] tt = $signed({1'b0, t_in});
    wire signed [CB:0] rdx = $signed({rd[CB-1], rd});

    // serial forward total of detector ik: lanes are visited one per 2 clocks; each lane with its input bit set adds its weight (+1 / -1 / 0); the detector's own result is 10 clocks of the floored running sum with this constant input
    wire signed [1:0] wsel = (rdx >= tt) ? 2'sd1 : (rdx <= -tt) ? -2'sd1 : 2'sd0;
    wire signed [CW+1:0] acc_f0 = acc + (s_bits[ij] ? $signed({{CW{wsel[1]}}, wsel}) : 0);
    wire [CW+AW+4:0] tot0 = (acc_f0 > 0) ? acc_f0 * PL : 0;
    wire [AW-1:0] fwd0 = (tot0 > MAXF) ? MAXF : tot0[AW-1:0];
    // mode 1: unsigned counters
    reg [CW-1:0] accp, accn;
    wire [CW-1:0] accp_f = accp + (s_bits[ij] & (rdx >= tt));
    wire [CW-1:0] accn_f = accn + (s_bits[ij] & (rdx <= -tt));
    wire [CW-1:0] diff1 = (accp_f > accn_f) ? (accp_f - accn_f) : {CW{1'b0}};
    wire [CW+AW+4:0] tot1 = diff1 * PL;
    wire [AW-1:0] fwd1 = (tot1 > MAXF) ? MAXF : tot1[AW-1:0];
    wire signed [CW+1:0] net1 = $signed({2'b0, accp_f}) - $signed({2'b0, accn_f});
    wire signed [CW+1:0] net_f = (ACCMODE == 0) ? acc_f0 : net1;
    wire [AW-1:0] fwdv = (ACCMODE == 0) ? fwd0 : fwd1;
    reg signed [7:0] lastnet [0:K-1]; reg [7:0] lastfwd [0:K-1];
    genvar gp; generate for (gp = 0; gp < K; gp = gp + 1) begin : PRB
        assign dbg_net[gp*8 +: 8] = lastnet[gp]; assign dbg_fwd[gp*8 +: 8] = lastfwd[gp];
    end endgenerate
    assign cfg_w_we = (st == SW_WR); assign cfg_w_ad = ad; assign cfg_wp = (rdx >= tt); assign cfg_wn = (rdx <= -tt);

    // threshold: round_half_even((sumP/nP + sumN/nN)/2) = round_half_even((sumP*nN + sumN*nP) / DEN)
    reg  [NUMW-1:0] num_r; reg dstart;
    wire dbusy, ddone; wire [NUMW-1:0] dq; wire [DW-1:0] dr;
    hexn_sdiv_v1 #(.NW(NUMW), .DW(DW)) dv(.clk(clk), .rst(rst), .start(dstart), .num(num_r), .den(DEN[DW-1:0]), .busy(dbusy), .done(ddone), .q(dq), .r(dr));
    wire [DW:0] r2 = {dr, 1'b0};
    wire [NUMW-1:0] qr = (r2 > DEN) ? dq + 1'b1 : (r2 == DEN) ? dq + dq[0] : dq;

    wire adv = (st == CLR) | ((st == CNT_RD) & ~s_bits[ij]) | (st == CNT_WR) | (st == SW_WR) | (st == ACC_WR);
    assign cfg_t_we = (st == FIN_SET); assign cfg_t_k = ik; assign cfg_t_val = (qr > MAXF) ? MAXF : qr[AW-1:0];
    integer i0;
    always @(posedge clk) begin
        dstart <= 1'b0;
        if (rst) begin
            st <= IDLE; busy <= 0; ad <= 0; ik <= 0; ij <= 0; num_r <= 0; acc <= 0; accp <= 0; accn <= 0;
            for (i0 = 0; i0 < K; i0 = i0 + 1) begin sumP[i0] <= 0; sumN[i0] <= 0; end
        end else begin
            if (adv) begin
                ad <= ad + 1'b1;
                if (ij == NB - 1) begin ij <= 0; ik <= ik + 1'b1; end else ij <= ij + 1'b1;
                if (last) begin st <= IDLE; busy <= 0; end
            end
            case (st)
                IDLE: if (start) begin
                    busy <= 1; ad <= 0; ik <= 0; ij <= 0;
                    case (cmd)
                        3'd1: st <= CLR;
                        3'd2: st <= CNT_RD;
                        3'd3: st <= SW_RD;
                        3'd4: begin st <= ACC_RD; acc <= 0; accp <= 0; accn <= 0; end
                        3'd5: st <= FIN_NUM;
                        default: begin st <= IDLE; busy <= 0; end
                    endcase
                end
                CLR: if (ad < K) begin sumP[ad[KW-1:0]] <= 0; sumN[ad[KW-1:0]] <= 0; end
                CNT_RD: if (s_bits[ij] && !adv) st <= CNT_WR;      // bit set: go and write; bit clear: adv moves on (or finishes)
                CNT_WR: if (!last) st <= CNT_RD;
                SW_RD: st <= SW_WR;
                SW_WR: if (!last) st <= SW_RD;
                ACC_RD: st <= ACC_WR;
                ACC_WR: begin
                    if (ij == NB - 1) begin
                        if (ik == s_label) sumP[ik] <= sumP[ik] + fwdv; else sumN[ik] <= sumN[ik] + fwdv;
                        lastnet[ik] <= net_f; lastfwd[ik] <= {{(8-AW){1'b0}}, fwdv};
                        acc <= 0; accp <= 0; accn <= 0;
                    end else begin acc <= acc_f0; accp <= accp_f; accn <= accn_f; end
                    if (!last) st <= ACC_RD;
                end
                FIN_NUM: begin
                    num_r <= {{(NUMW-PW){1'b0}}, sumP[ik]} * nN + {{(NUMW-NW_){1'b0}}, sumN[ik]} * nP;
                    dstart <= 1'b1; st <= FIN_DIV;
                end
                FIN_DIV: if (ddone) st <= FIN_SET;
                FIN_SET: begin
                    if (ik == K - 1) begin st <= IDLE; busy <= 0; end else begin ik <= ik + 1'b1; st <= FIN_NUM; end
                end
                default: ;
            endcase
        end
    end
endmodule
`default_nettype wire
