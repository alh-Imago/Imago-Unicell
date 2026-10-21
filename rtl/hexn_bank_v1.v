`default_nettype none
// hexn_bank_v1.v -- Hex-N complete counted-detector BANK (Alan, 21 Oct 2026: fan-out and end-to-end). K minimal detectors (hexn_det_v2), their settings (hexn_cfgbank_v2), the shared training unit (hexn_trainbank_v2),
// the run-time controller (window timing as the cell model: W windows of forward phase + feedback phase, PL clocks each), one burst-length counter per detector, and the answer: the class whose detector sent
// strictly the most output clocks in the last window (a tie or silence gives ans_valid = 0, counted wrong). The input wires s_bits are the bank's inputs: the SAME NB wires go to all K detectors (that is the fan-out).
// Training: tr_start + tr_cmd as hexn_trainbank_v2. Running a sample: hold s_bits, pulse run_start, wait for run_done (W*2*PL clocks), read ans_valid / ans_class / cnt_flat.
module hexn_bank_v1 #(
    parameter K = 4, parameter NB = 12, parameter AW = 6, parameter S = 16, parameter CB = 6, parameter W = 2, parameter PL = 10
) (
    input  wire              clk, input wire rst,
    input  wire              tr_start, input wire [2:0] tr_cmd, output wire tr_busy,
    input  wire [NB-1:0]     s_bits, input wire [$clog2(K)-1:0] s_label, input wire [CB-1:0] t_in,
    input  wire              run_start, output reg run_busy, output reg run_done,
    output reg               ans_valid, output reg [$clog2(K)-1:0] ans_class,
    output wire [4*K-1:0]    cnt_flat
);
    localparam KW = $clog2(K);
    wire cw_we, cwp, cwn, ct_we; wire [$clog2(K*NB+1)-1:0] cw_ad; wire [KW-1:0] ct_k; wire [AW-1:0] ct_val;
    wire [K*NB-1:0] w_pos, w_neg; wire [K*AW-1:0] thr_flat;
    hexn_trainbank_v2 #(.K(K), .NB(NB), .AW(AW), .S(S), .CB(CB), .PL(PL)) trn(.clk(clk), .rst(rst), .start(tr_start), .cmd(tr_cmd), .s_bits(s_bits), .s_label(s_label), .t_in(t_in), .busy(tr_busy),
        .cfg_w_we(cw_we), .cfg_w_ad(cw_ad), .cfg_wp(cwp), .cfg_wn(cwn), .cfg_t_we(ct_we), .cfg_t_k(ct_k), .cfg_t_val(ct_val));
    hexn_cfgbank_v2 #(.K(K), .NB(NB), .AW(AW)) cfg(.clk(clk), .rst(rst), .w_we(cw_we), .w_ad(cw_ad), .wp(cwp), .wn(cwn), .t_we(ct_we), .t_k(ct_k), .t_val(ct_val), .w_pos(w_pos), .w_neg(w_neg), .thr_flat(thr_flat));

    // run-time controller: counters t (0..PL-1), ph (0 forward / 1 feedback), w (window)
    reg [$clog2(PL)-1:0] t; reg ph; reg [$clog2(W)-1:0] w;
    wire ph_start = run_busy & (t == 0);
    wire win_end  = run_busy & ph & (t == PL - 1);
    wire lastwin  = run_busy & (w == W - 1);
    wire finish   = lastwin & ph & (t == PL - 1);
    always @(posedge clk) begin
        run_done <= 1'b0;
        if (rst) begin run_busy <= 0; t <= 0; ph <= 0; w <= 0; end
        else if (run_start && !run_busy) begin run_busy <= 1; t <= 0; ph <= 0; w <= 0; end
        else if (run_busy) begin
            if (t == PL - 1) begin
                t <= 0;
                if (ph) begin ph <= 0; w <= w + 1'b1; end else ph <= 1;
            end else t <= t + 1'b1;
            if (finish) begin run_busy <= 0; run_done <= 1; end
        end
    end

    // detectors and their burst counters (count output clocks in the last window)
    wire [K-1:0] txk; reg [3:0] cnt [0:K-1];
    genvar g;
    generate for (g = 0; g < K; g = g + 1) begin : D
        hexn_det_v2 #(.NB(NB), .AW(AW)) det(.clk(clk), .rst(rst), .phase(ph), .ph_start(ph_start), .win_end(win_end), .rx(s_bits),
            .w_pos(w_pos[g*NB +: NB]), .w_neg(w_neg[g*NB +: NB]), .cfg_thr(thr_flat[g*AW +: AW]), .tx(txk[g]));
        always @(posedge clk) begin
            if (rst || (run_start && !run_busy)) cnt[g] <= 0;
            else if (lastwin && txk[g]) cnt[g] <= cnt[g] + 1'b1;
        end
        assign cnt_flat[4*g +: 4] = cnt[g];
    end endgenerate

    // answer: unique strict maximum above zero
    reg [3:0] mx; integer a; reg [KW-1:0] first; reg [KW:0] nmax;
    always @* begin
        mx = 0;
        for (a = 0; a < K; a = a + 1) if (cnt[a] > mx) mx = cnt[a];
        nmax = 0; first = 0;
        for (a = K - 1; a >= 0; a = a - 1) if (cnt[a] == mx) begin nmax = nmax + 1'b1; first = a; end
    end
    always @(posedge clk) begin
        if (rst) begin ans_valid <= 0; ans_class <= 0; end
        else if (run_done) begin ans_valid <= (mx != 0) && (nmax == 1); ans_class <= first; end
    end
endmodule
`default_nettype wire
