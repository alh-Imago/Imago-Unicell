// hexn_bank_v17.v -- Clone of hexn_bank_v16.v (left untouched); v17 uses hexn_cell_v5 (same behaviour, shallower per-clock sum).
// hexn_bank_v16.v -- Clone of hexn_bank_v15.v (left untouched). v16 PIPELINES THE ANSWER: v15 found the maximum burst count, counted the ties and picked the first class in one clock with serial loops (a chain of 19 compares and 19 adds at K = 19), which limited hexn_lattice_hex19 to 27.6 MHz on the Kintex-7 card (nextpnr-xilinx critical path through hexn_bank_v15.v lines 103-109). v16 does it in 4 short stages (group maxima, overall maximum, equality flags, one-hot test and encode) and delays run_done by 4 clocks, so that run_done is high in the same clock in which ans_valid and ans_class are ready (the host top reads them one clock later). Answers, ans_valid, ans_class and burst counts are the same as v15; only run_done comes 4 clocks later.
// hexn_bank_v15.v -- Clone of hexn_bank_v14.v (left untouched). v15 uses hexn_cell_v5 and adds the input leak_sh (3 bits, one setting for all cells): the cells keep a decayed share of their forward total from the previous run instead of clearing it (leak_sh = 0 reproduces v14).
// hexn_bank_v14.v -- Clone of hexn_bank_v13.v (left untouched). v14 = parameter NC full cells behind the one glue buffer (default 1 = v13 behaviour); lane_cfg, cell_thr, cell_cnt, cell_fwd are NC slices, cell g = slice g.
// hexn_bank_v13.v -- Clone of hexn_bank_v12.v (left untouched). v13 reads the cell forward total through the cell port fwd_o (hexn_cell_v3) instead of the hierarchical name fcell.fwd_acc, which yosys cannot synthesize (the v12 board build read 0).
`default_nettype none
// hexn_bank_v12.v -- Clone of hexn_bank_v11.v (left untouched); v12 = CELL MODE: when cell_mode is 1 at run_start the run continues after the detector windows (answer and burst counts are complete at the end of window 1, as before) with the GLUE BUFFER (hexn_glue_v1: captures the detectors' bursts in window 1, replays them in window 2) and ONE full cell (hexn_cell_v2: forward phase in window 2, feedback phase in window 3, output burst counted in window 4; lane settings lane_cfg and threshold cell_thr are inputs); cell_mode 0 gives exactly the v11 run. Outputs: cell_cnt (output burst clocks), cell_fwd (forward total), cap_flat (3 bits per detector: captured burst length). v11 (previous)  = NO FEEDBACK PHASE: uses hexn_det_v3 and a run controller of W windows of PL clocks each (a run is W*PL = 20 clocks, was 40); the full cell keeps its feedback. v10 (previous)  uses trainbank_v9 (any NB, AW) and a 16-bit cap_n. Clone of hexn_bank_v8.v (left untouched); v9 passes the SETW capture port through (trainbank_v8). Clone of hexn_bank_v7.v (left untouched); v8 uses trainbank_v7 (weight comparisons as plain logic). Clone of hexn_bank_v6.v (left untouched); v7 feeds the detectors' settings (w_pos, w_neg) to the trainer (trainbank_v6, one-clock ACCUM). Clone of hexn_bank_v5.v (left untouched); v6 passes the counter peek port through. Clone of hexn_bank_v4.v (left untouched); v5 adds dbg_net / dbg_fwd and parameter ACCMODE for the trainer. Clone of hexn_bank_v3.v (left untouched); v4 adds dbg_sump / dbg_sumn from the trainer. Clone of hexn_bank_v2.v (left untouched); v3 only adds the debug outputs dbg_wpos / dbg_wneg / dbg_thr (the trained settings) so a board can read them back. Clone of hexn_bank_v1.v (left untouched). v2: each detector gets its OWN input wires rx_flat (so the inputs can come through the lattice bridges, hexn_lattice_gen_v1.py), the trainer still sees s_bits, and run_start waits SETTLE clocks before the windows start (the longest bridge line). SETTLE = 0 and rx_flat = K copies of s_bits behaves as v1. Hex-N complete counted-detector BANK (Alan, 21 Oct 2026: fan-out and end-to-end). K minimal detectors (hexn_det_v2), their settings (hexn_cfgbank_v2), the shared training unit (hexn_trainbank_v9),
// the run-time controller (window timing as the cell model: W windows of forward phase + feedback phase, PL clocks each), one burst-length counter per detector, and the answer: the class whose detector sent
// strictly the most output clocks in the last window (a tie or silence gives ans_valid = 0, counted wrong). The input wires s_bits are the bank's inputs: the SAME NB wires go to all K detectors (that is the fan-out).
// Training: tr_start + tr_cmd as hexn_trainbank_v9. Running a sample: hold s_bits, pulse run_start, wait for run_done (W*2*PL clocks), read ans_valid / ans_class / cnt_flat.
module hexn_bank_v17 #(
    parameter K = 4, parameter NB = 12, parameter AW = 6, parameter S = 16, parameter CB = 6, parameter W = 2, parameter PL = 10, parameter SETTLE = 0, parameter ACCMODE = 0, parameter NC = 1
) (
    input  wire              clk, input wire rst,
    input  wire              tr_start, input wire [2:0] tr_cmd, output wire tr_busy,
    input  wire [NB-1:0]     s_bits, input wire [K*NB-1:0] rx_flat, input wire [$clog2(K)-1:0] s_label, input wire [CB-1:0] t_in,
    input  wire              run_start, output reg run_busy, output reg run_done,
    input  wire              cell_mode, input wire [2:0] leak_sh, input wire [NC*2*K-1:0] lane_cfg, input wire [NC*AW-1:0] cell_thr, output wire [NC*5-1:0] cell_cnt, output wire [NC*AW-1:0] cell_fwd, output wire [3*K-1:0] cap_flat,
    output reg               ans_valid, output reg [$clog2(K)-1:0] ans_class,
    output wire [4*K-1:0]    cnt_flat,
    output wire [K*NB-1:0]   dbg_wpos, output wire [K*NB-1:0] dbg_wneg, output wire [K*AW-1:0] dbg_thr,
    output wire [K*16-1:0] dbg_sump, output wire [K*16-1:0] dbg_sumn,
    output wire [K*8-1:0] dbg_net, output wire [K*8-1:0] dbg_fwd,
    input wire [$clog2(K*NB+1)-1:0] cap_ad, output wire [7:0] cap_data, output wire [15:0] cap_n, input wire [$clog2(K*NB+1)-1:0] peek_ad, output wire signed [CB-1:0] peek_data
);
    localparam KW = $clog2(K);
    wire cw_we, cwp, cwn, ct_we; wire [$clog2(K*NB+1)-1:0] cw_ad; wire [KW-1:0] ct_k; wire [AW-1:0] ct_val;
    wire [K*NB-1:0] w_pos, w_neg; wire [K*AW-1:0] thr_flat;
    hexn_trainbank_v9 #(.K(K), .NB(NB), .AW(AW), .S(S), .CB(CB), .PL(PL), .ACCMODE(ACCMODE)) trn(.clk(clk), .rst(rst), .start(tr_start), .cmd(tr_cmd), .s_bits(s_bits), .s_label(s_label), .t_in(t_in), .busy(tr_busy), .dbg_sump(dbg_sump), .dbg_sumn(dbg_sumn), .dbg_net(dbg_net), .dbg_fwd(dbg_fwd), .wp_in(w_pos), .wn_in(w_neg), .cap_ad(cap_ad), .cap_data(cap_data), .cap_n(cap_n), .peek_ad(peek_ad), .peek_data(peek_data),
        .cfg_w_we(cw_we), .cfg_w_ad(cw_ad), .cfg_wp(cwp), .cfg_wn(cwn), .cfg_t_we(ct_we), .cfg_t_k(ct_k), .cfg_t_val(ct_val));
    hexn_cfgbank_v2 #(.K(K), .NB(NB), .AW(AW)) cfg(.clk(clk), .rst(rst), .w_we(cw_we), .w_ad(cw_ad), .wp(cwp), .wn(cwn), .t_we(ct_we), .t_k(ct_k), .t_val(ct_val), .w_pos(w_pos), .w_neg(w_neg), .thr_flat(thr_flat));

    assign dbg_wpos = w_pos; assign dbg_wneg = w_neg; assign dbg_thr = thr_flat;

    // run-time controller (no feedback phase in the detectors): counters t (0..PL-1) and w (window). Detector windows: 0 accumulate, W-1 (= 1) bursts that are counted. Cell mode adds windows W..W+2 (see the header).
    reg [$clog2(PL)-1:0] t; reg [2:0] w; reg [7:0] wc; reg cm;
    wire act      = run_busy & (wc == 0);
    wire t0       = act & (t == 0);
    wire tl       = act & (t == PL - 1);
    wire ph_start = t0 & (w < W);                         // detectors get ph_start in their own windows only
    wire lastwin  = act & (w == W - 1);
    wire finish   = tl & (cm ? (w == W + 2) : (w == W - 1));
    reg done0;
    always @(posedge clk) begin
        done0 <= 1'b0;
        if (rst) begin run_busy <= 0; t <= 0; w <= 0; wc <= 0; cm <= 0; end
        else if (run_start && !run_busy) begin run_busy <= 1; t <= 0; w <= 0; wc <= SETTLE; cm <= cell_mode; end
        else if (run_busy && wc != 0) wc <= wc - 1'b1;
        else if (run_busy) begin
            if (t == PL - 1) begin t <= 0; w <= w + 1'b1; end else t <= t + 1'b1;
            if (finish) begin run_busy <= 0; done0 <= 1; end
        end
    end

    // detectors and their burst counters (count output clocks in the last window)
    wire [K-1:0] txk; reg [3:0] cnt [0:K-1];
    genvar g;
    generate for (g = 0; g < K; g = g + 1) begin : D
        hexn_det_v3 #(.NB(NB), .AW(AW)) det(.clk(clk), .rst(rst), .ph_start(ph_start), .rx(rx_flat[g*NB +: NB]),
            .w_pos(w_pos[g*NB +: NB]), .w_neg(w_neg[g*NB +: NB]), .cfg_thr(thr_flat[g*AW +: AW]), .tx(txk[g]));
        always @(posedge clk) begin
            if (rst || (run_start && !run_busy)) cnt[g] <= 0;
            else if (lastwin && txk[g]) cnt[g] <= cnt[g] + 1'b1;
        end
        assign cnt_flat[4*g +: 4] = cnt[g];
    end endgenerate

    // glue buffer and one full cell (cell mode). Detector windows are W; cell windows: W = forward (replay), W+1 = feedback, W+2 = forward (output burst counted)
    wire clr_g = run_start & !run_busy;
    wire cap_en = act & (w == W - 1);
    wire play = t0 & (w == W);
    wire cph = act & (w == W + 1);
    wire cph_start = t0 & (w == W | w == W + 2);
    wire cwin_end = tl & (w == W + 1);
    wire [K-1:0] gout;
    hexn_glue_v1 #(.K(K)) glue(.clk(clk), .rst(rst), .clr(clr_g), .cap_en(cap_en), .play(play), .tx(txk), .out(gout), .cap_flat(cap_flat));
    // NC full cells share the glue buffer output (every cell hears the same replayed tokens); each has its own lane settings and threshold.
    localparam OUTL = 20;
    // leak applies once per run, at the start of the first cell window (w == W); at the start of window W+2 the total is kept (7), as nothing arrives then.
    wire [2:0] lk_in = (w == W) ? leak_sh : 3'd7;
    genvar gc;
    generate for (gc = 0; gc < NC; gc = gc + 1) begin : CELLS
        reg [23:0] crx, cact; reg [47:0] cdir, ccode; integer ci;
        wire [2*K-1:0] lcfg = lane_cfg[gc*2*K +: 2*K];
        always @* begin
            crx = 0; cact = 0; cdir = 0; ccode = 0;
            for (ci = 0; ci < K; ci = ci + 1) begin crx[ci] = gout[ci]; cact[ci] = (lcfg[2*ci +: 2] != 0); ccode[2*ci +: 2] = (lcfg[2*ci +: 2] == 2) ? 2'd3 : 2'd0; end
            cact[OUTL] = 1'b1; cdir[2*OUTL +: 2] = 2'd1; ccode[2*OUTL +: 2] = 2'd1;
        end
        wire [23:0] ctx; wire [AW-1:0] cfwd;
        hexn_cell_v5 #(.FACES(6), .PAIRS(4), .AW(AW)) fcell(.clk(clk), .rst(rst), .phase(cph), .ph_start(cph_start), .win_end(cwin_end), .rx(crx), .tx(ctx), .fwd_o(cfwd), .leak_sh(lk_in), .cfg_active(cact), .cfg_dir(cdir), .cfg_code(ccode), .cfg_thr(cell_thr[gc*AW +: AW]), .bias(16'd0));
        reg [AW-1:0] fwd_l; always @(posedge clk) if (cwin_end) fwd_l <= cfwd;
        assign cell_fwd[gc*AW +: AW] = fwd_l;
        reg [4:0] ccnt;
        always @(posedge clk) begin
            if (rst || (run_start && !run_busy)) ccnt <= 0;
            else if (act && cm && w == W + 2 && ctx[OUTL]) ccnt <= ccnt + 1'b1;
        end
        assign cell_cnt[gc*5 +: 5] = ccnt;
    end endgenerate

    // answer: unique strict maximum above zero, in four short stages (see the header). cnt is stable from the clock where done0 is high.
    localparam G = 5, NG = (K + G - 1) / G;
    integer a, gi;
    reg [3:0] gm [0:NG-1]; reg [3:0] mx_r; reg [K-1:0] eq_r; reg d1, d2, d3; reg [3:0] t1, t2; reg [K-1:0] low; reg [KW-1:0] enc;
    always @(posedge clk) begin
        for (gi = 0; gi < NG; gi = gi + 1) begin t1 = 0; for (a = gi * G; a < gi * G + G && a < K; a = a + 1) if (cnt[a] > t1) t1 = cnt[a]; gm[gi] <= t1; end      // stage 1: group maxima
        t2 = 0; for (gi = 0; gi < NG; gi = gi + 1) if (gm[gi] > t2) t2 = gm[gi]; mx_r <= t2;                                                                         // stage 2: overall maximum
        for (a = 0; a < K; a = a + 1) eq_r[a] <= (cnt[a] == mx_r);                                                                                           // stage 3: who has it
        d1 <= done0; d2 <= d1; d3 <= d2;
        if (rst) begin d1 <= 0; d2 <= 0; d3 <= 0; end
    end
    always @* begin   // stage 4 (combinational, short): one-hot test and encode of the lowest set flag
        low = eq_r & (~eq_r + 1'b1); enc = 0;
        for (a = 0; a < K; a = a + 1) if (low[a]) enc = enc | a[KW-1:0];
    end
    always @(posedge clk) begin
        run_done <= d3 && !rst;
        if (rst) begin ans_valid <= 0; ans_class <= 0; end
        else if (d3) begin ans_valid <= (mx_r != 0) && (eq_r != 0) && ((eq_r & (eq_r - 1'b1)) == 0); ans_class <= enc; end
    end
endmodule
`default_nettype wire
