// hexn_core_v4.v -- Clone of hexn_core_v2.v (left untouched). v4 adds command 0x13 LOADDET [wp0 wp1 wp2 wn0 wn1 wn2 thr] -> 0xA5: writes ONE detector's stored settings into the settings store through the bank's loader (bank v19 / lattice v18). The seven bytes are in the order DUMP (0x07) sends each detector, so a stored DUMP can be replayed byte for byte: send LOADDET for detector 0, then 1, ... K-1, in that order, and nothing else in between. Needs the lattice with the ld_* ports (hexn_lattice_*_v18); core v2 stays with lattice v16/v17.
// hexn_core_v2.v -- Clone of hexn_core_v1.v (left untouched). ONE CHANGE: the byte counter ci of the reply state machines is 12 bits wide, not 8. In v1 the end test of RUNCELLN (ci == 2*NC + K) can never be true when 2*NC + K > 255 (NCELL >= 119 with 19 detectors), so the reply never ended on the 128-cell card build. Found on the card 23 Oct (see docs/hex-n/HEXN_DESIGN.md).
// hexn_core_v1.v -- Clone of hexn_tang_top_v11.v (left untouched) with the serial port taken OUT: the command interpreter and everything behind it is unchanged, but the two UART modules are gone and the byte interface is ports: rx_d/rx_v (one byte in, valid for one clock), tx_d/tx_s (one byte out, send pulse for one clock), tx_b (busy: the sender must not take a new byte while it is high, as the UART transmitter's busy). For a host link that is not a UART (the JTAG bridge, rtl/hexn_jtag_bridge_v1.v). Needs the same defines as the Tang top: LATMOD, NCLS, NBW, AWB, ACCMODE, NCELL (CLKDIV is no longer used).
// hexn_tang_top_v11.v -- Clone of hexn_tang_top_v10.v (left untouched). v11 adds the SAVE AND RECALL memory block hexn_mem_v1 (18 wires, 8 slots): 0x20 MEMCLR (clear the per-wire counters and the known set) ; 0x21 MEMWATCH [b0 b1 b2 m0 m1 m2] (one window: sample bits and mask of KNOWN wires; the counters of masked-in wires move +1/-1) ; 0x22 MEMSAVE [n] (store the integrated pattern in slot n) ; 0x23 MEMRECALL -> 13 bytes: best slot (15 = none), best matches, known wires, second-best matches, integrated cue (3), recalled slot (3), deviation mask (3) ; 0x24 MEMDUMP [n] -> valid, slot bits (3) ; 0x25 MEMCLRALL (all slots empty). Everything else as v10.
// hexn_tang_top_v10.v -- Clone of hexn_tang_top_v9.v (left untouched). v10 = NCELL (define, default 1) leaky cells behind the glue buffer (bank v15, lattice _v14): 0x10 SETLEAK [s] (s 0..7: before each cell window a cell's forward total a becomes a - (a >> s); 0 = clear, 7 = keep; reset value 0); 0x11 LOADCELLN [n, thr, 5 lane bytes] loads cell n (0x0E still loads cell 0); 0x12 RUNCELLN [3 sample bytes] -> for each cell n = 0..NCELL-1: output burst count, forward total; then the K captured burst lengths (2*NCELL + K bytes). 0x0F RUNCELL answers as in v9 (cell 0 only). Cell totals persist from run to run.
`default_nettype none
// hexn_tang_top_v9.v -- Clone of hexn_tang_top_v8.v (left untouched). v9 = CELL MODE commands for the lattice bank v11 (glue buffer and one full cell behind the detectors): 0x0E LOADCELL [thr, 5 bytes of lane settings, 2 bits per detector lane little-endian: 0 off, 1 positive, 2 negative] -> 0xA5; 0x0F RUNCELL [3 sample bytes as RUN] -> cell_cnt (output burst clocks), cell_fwd (the cell's forward total), then K captured burst lengths (one byte each). RUN (0x06) is unchanged (cell mode off). Clone of hexn_tang_top_v7.v (left untouched). v8 = WIDE INPUT: sample bits are always 3 bytes (any NB up to 24; default 18; defines NBW, AWB), so COUNT/ACCUM are [cmd, label, b0, b1, b2] and RUN is [cmd, b0, b1, b2]; DUMP sends wpos (3 bytes), wneg (3 bytes), thr (1 byte) = 7 bytes per detector; ECHO sends bits (3 bytes), label, T; CAP sends the 16-bit write count (2 bytes, low first). Clone of hexn_tang_top_v6.v (left untouched); v7 adds 0x0D CAP (K*12 bytes {wp,wn,counter} seen by the weight-forming pass for write 0..K*12-1, then one byte: number of weight writes). Clone of hexn_tang_top_v5.v (left untouched); v6 adds 0x0C ECHO (4 bytes: sample bits low, sample bits high, label, t_in, exactly as the board holds them for the trainer). Clone of hexn_tang_top_v4.v (left untouched); v5 adds 0x0B PEEK (all K*NB trainer counters, one signed byte each, in the order detector*12 + lane). Clone of hexn_tang_top_v3.v (left untouched); v4 adds 0x0A PROBE (for each detector the net lane count and forward total computed in the last ACCUM sample: net fwd, 2*K bytes) and the define ACCMODE (0 signed sum, 1 unsigned counters). Clone of hexn_tang_top_v2.v (left untouched); v3 adds 0x08 DUMPSUMS (the two running sums of the threshold pass per detector: sumP_lo sumP_hi sumN_lo sumN_hi) and 0x09 DIVTEST (num2 num1 num0 -> divider self-test: q0 q1 q2 r0 r1, divisor = the trainer's). Clone of hexn_tang_top_v1.v (left untouched); v2 adds command 0x07 DUMP (read back the trained settings for diagnosis) and uses the lattice _v2 modules. Hex-N lattice bank on the Tang Nano 20K with a serial command link (USB serial through the BL616, 8N1). Compile with -DLATMOD=hexn_lattice_<shape>_v1 and -DNCLS=<cells>; 12 input wires.
// Commands (host to board); after each one the board answers, so the host never overruns it:
//   0x01 CLEAR                       -> 0xA5
//   0x02 COUNT  label bits_lo bits_hi -> 0xA5     (every training sample once)
//   0x03 SETW   t                    -> 0xA5     (weights from the counters; t = samples per class / 2)
//   0x04 ACCUM  label bits_lo bits_hi -> 0xA5     (every training sample once more)
//   0x05 FINISH                      -> 0xA5     (thresholds)
//   0x07 DUMP                        -> for each detector k = 0..K-1: wpos_lo wpos_hi wneg_lo wneg_hi thr   (5*K bytes; lane j = bit j)
//   0x06 RUN    bits_lo bits_hi      -> status, c0 .. c(K-1)    (status bit 7 = answer valid, bits 4..0 = class; c = output clocks of each detector in the last window)
// bits are the 12 input wires, wire j = bit j (bits_hi uses its low 4 bits). LEDs (active low): bits 4..0 = class of the last answer, bit 5 = answer valid.
`ifndef NBW
`define NBW 18
`endif
`ifndef AWB
`define AWB 7
`endif
`ifndef NCLS
`define NCLS 7
`endif
`ifndef ACCMODE
`define ACCMODE 0
`endif
`ifndef CLKDIV
`define CLKDIV 234
`endif
`ifndef NCELL
`define NCELL 1
`endif
module hexn_core_v4 (input wire clk, input wire [7:0] rx_d, input wire rx_v, output reg [7:0] tx_d, output reg tx_s, input wire tx_b, output wire [5:0] led);
    localparam NC = `NCELL; localparam K = `NCLS; localparam NB = `NBW; localparam AWT = `AWB; localparam KW = $clog2(K);
    reg [7:0] por = 0; wire rst = ~&por; always @(posedge clk) if (~&por) por <= por + 1'b1;
    reg ld_start; reg [23:0] ld_wp, ld_wn; reg [7:0] ld_thr; wire ld_busy; initial begin ld_start = 0; ld_wp = 0; ld_wn = 0; ld_thr = 0; end
    reg tr_start, run_start; reg [2:0] tr_cmd; reg [NB-1:0] bits; reg [KW-1:0] label; reg [5:0] t_in;
    wire tr_busy, run_busy, run_done, ans_valid; wire [KW-1:0] ans_class; wire [4*K-1:0] cnt; wire [K*NB-1:0] dwp, dwn; wire [K*AWT-1:0] dthr; wire [K*16-1:0] dsp, dsn; wire [K*8-1:0] dnet, dfwd; reg [$clog2(K*NB+4)-1:0] ck; wire [7:0] capd; wire [15:0] capn; reg [$clog2(K*NB+4)-1:0] pk; wire signed [5:0] pkd;
    `LATMOD #(.K(K), .NB(NB), .AW(AWT), .ACCMODE(`ACCMODE), .NC(NC)) bank(.clk(clk), .rst(rst), .tr_start(tr_start), .tr_cmd(tr_cmd), .tr_busy(tr_busy), .s_bits(bits), .s_label(label), .t_in(t_in),
        .run_start(run_start), .run_busy(run_busy), .run_done(run_done), .ans_valid(ans_valid), .ans_class(ans_class), .cnt_flat(cnt), .cell_mode(cell_mode), .leak_sh(leak_sh), .lane_cfg(lcfg_w), .cell_thr(cthr), .cell_cnt(cell_cnt_all), .cell_fwd(cell_fwd_all), .cap_flat(cap3), .dbg_wpos(dwp), .dbg_wneg(dwn), .dbg_thr(dthr), .dbg_sump(dsp), .dbg_sumn(dsn), .dbg_net(dnet), .dbg_fwd(dfwd), .cap_ad(ck), .cap_data(capd), .cap_n(capn), .peek_ad(pk), .peek_data(pkd), .ld_start(ld_start), .ld_wp(ld_wp[NB-1:0]), .ld_wn(ld_wn[NB-1:0]), .ld_thr(ld_thr[AWT-1:0]), .ld_busy(ld_busy));
    localparam DEN_T = 2 * 16 * (16 * (K - 1)); localparam DW_T = $clog2(DEN_T + 1);
    reg [23:0] tnum; reg tdstart; wire tdbusy, tddone; wire [23:0] tq; wire [DW_T-1:0] tr_;
    hexn_sdiv_v1 #(.NW(24), .DW(DW_T)) tdiv(.clk(clk), .rst(rst), .start(tdstart), .num(tnum), .den(DEN_T[DW_T-1:0]), .busy(tdbusy), .done(tddone), .q(tq), .r(tr_));
    localparam [4:0] IDLE = 0, ARG = 1, GO = 2, WAIT = 3, ACK = 4, RUNW = 5, STAT = 6, CNTS = 7, SEND = 8, DUMP = 9, DUMP2 = 10, DIVW = 11, DIVO = 12, PROBE = 13, PEEK1 = 14, PEEK2 = 15, ECHO = 16, CAP1 = 17, CAP2 = 18, CELLW = 19, CELLB = 20, CELLN = 21, CELLNB = 22, MEMW = 23, MEMD = 24, MEMRB = 25, LDW = 26;
    // SAVE AND RECALL memory block (commands 0x20..0x25)
    reg m_clr, m_clrall, m_watch, m_save, m_recall; reg [2:0] m_slot, m_rd; reg [103:0] resp; reg [4:0] mcnt; wire m_done, m_rv; wire [3:0] m_id; wire [7:0] m_best, m_second, m_known; wire [NB-1:0] m_cue, m_rec, m_dev, m_rdb;
    wire [23:0] cue24 = {{(24-NB){1'b0}}, m_cue}; wire [23:0] rec24 = {{(24-NB){1'b0}}, m_rec}; wire [23:0] dev24 = {{(24-NB){1'b0}}, m_dev}; wire [23:0] rdb24 = {{(24-NB){1'b0}}, m_rdb}; wire [23:0] mb24 = {a2, a1, a0}; wire [23:0] mm24 = {a5, a4, a3};
    hexn_mem_v1 #(.NB(NB), .M(8)) mem(.clk(clk), .rst(rst), .op_clr(m_clr), .op_clrall(m_clrall), .op_watch(m_watch), .w_bits(mb24[NB-1:0]), .w_mask(mm24[NB-1:0]), .op_save(m_save), .sv_slot(m_slot), .op_recall(m_recall), .done(m_done),
        .rd_slot(m_rd), .rd_valid(m_rv), .rd_bits(m_rdb), .best_id(m_id), .best_m(m_best), .second_m(m_second), .known_cnt(m_known), .cue_bits(m_cue), .rec_bits(m_rec), .dev_mask(m_dev));
    reg [4:0] st, after; reg [7:0] cmd; reg [2:0] nargs, got; reg [7:0] a0, a1, a2, a3, a4, a5; reg cell_mode; reg [NC*40-1:0] lcfg; reg [NC*AWT-1:0] cthr; reg [2:0] leak_sh; reg [7:0] a6; wire [NC*5-1:0] cell_cnt_all; wire [NC*AWT-1:0] cell_fwd_all; wire [4:0] cell_cnt = cell_cnt_all[4:0]; wire [AWT-1:0] cell_fwd = cell_fwd_all[AWT-1:0];
    wire [NC*2*K-1:0] lcfg_w; genvar gq; generate for (gq = 0; gq < NC; gq = gq + 1) begin : LW assign lcfg_w[gq*2*K +: 2*K] = lcfg[gq*40 +: 2*K]; end endgenerate wire [3*K-1:0] cap3; wire [23:0] arg24 = {a3, a2, a1}; wire [23:0] run24 = {a2, a1, a0}; reg [11:0] ci;
    reg [$clog2(K+1):0] dk; wire [23:0] bits24 = {{(24-NB){1'b0}}, bits};
    wire [23:0] dwp_k = {{(24-NB){1'b0}}, dwp[dk*NB +: NB]}; wire [23:0] dwn_k = {{(24-NB){1'b0}}, dwn[dk*NB +: NB]}; reg [2:0] dj; reg [KW-1:0] lastclass; reg lastvalid;
    assign led = ~{lastvalid, {(5-KW){1'b0}}, lastclass};
    always @(posedge clk) begin
        ld_start <= 1'b0; tdstart <= 1'b0; tr_start <= 1'b0; run_start <= 1'b0; tx_s <= 1'b0; tdstart <= 1'b0; m_clr <= 1'b0; m_clrall <= 1'b0; m_watch <= 1'b0; m_save <= 1'b0; m_recall <= 1'b0;
        if (rst) begin m_slot <= 0; m_rd <= 0; cell_mode <= 0; cthr <= 0; lcfg <= 0; leak_sh <= 0; st <= IDLE; lastclass <= 0; lastvalid <= 0; t_in <= 0; bits <= 0; label <= 0; end
        else case (st)
            IDLE: if (rx_v) begin
                cmd <= rx_d; got <= 0;
                case (rx_d)
                    8'h01, 8'h05: begin nargs <= 0; st <= GO; end
                    8'h02, 8'h04: begin nargs <= 4; st <= ARG; end
                    8'h03: begin nargs <= 1; st <= ARG; end
                    8'h06: begin nargs <= 3; st <= ARG; end
                    8'h07: begin nargs <= 0; st <= GO; end
                    8'h08: begin nargs <= 0; st <= GO; end
                    8'h09: begin nargs <= 3; st <= ARG; end
                    8'h0a: begin nargs <= 0; st <= GO; end
                    8'h0b: begin nargs <= 0; st <= GO; end
                    8'h0c: begin nargs <= 0; st <= GO; end
                    8'h0d: begin nargs <= 0; st <= GO; end
                    8'h0e: begin nargs <= 6; st <= ARG; end
                    8'h0f: begin nargs <= 3; st <= ARG; end
                    8'h10: begin nargs <= 1; st <= ARG; end
                    8'h11: begin nargs <= 7; st <= ARG; end
                    8'h12: begin nargs <= 3; st <= ARG; end
                    8'h13: begin nargs <= 7; st <= ARG; end
                    8'h20: begin nargs <= 0; st <= GO; end
                    8'h21: begin nargs <= 6; st <= ARG; end
                    8'h22: begin nargs <= 1; st <= ARG; end
                    8'h23: begin nargs <= 0; st <= GO; end
                    8'h24: begin nargs <= 1; st <= ARG; end
                    8'h25: begin nargs <= 0; st <= GO; end
                    default: st <= IDLE;
                endcase
            end
            ARG: if (rx_v) begin
                if (got == 0) a0 <= rx_d; else if (got == 1) a1 <= rx_d; else if (got == 2) a2 <= rx_d; else if (got == 3) a3 <= rx_d; else if (got == 4) a4 <= rx_d; else if (got == 5) a5 <= rx_d; else a6 <= rx_d;
                got <= got + 1'b1;
                if (got + 1 == nargs) st <= GO;
            end
            GO: begin
                case (cmd)
                    8'h01: begin tr_cmd <= 3'd1; tr_start <= 1; st <= WAIT; end
                    8'h02: begin label <= a0; bits <= arg24[NB-1:0]; tr_cmd <= 3'd2; tr_start <= 1; st <= WAIT; end
                    8'h03: begin t_in <= a0[5:0]; tr_cmd <= 3'd3; tr_start <= 1; st <= WAIT; end
                    8'h04: begin label <= a0; bits <= arg24[NB-1:0]; tr_cmd <= 3'd4; tr_start <= 1; st <= WAIT; end
                    8'h05: begin tr_cmd <= 3'd5; tr_start <= 1; st <= WAIT; end
                    8'h06: begin bits <= run24[NB-1:0]; cell_mode <= 0; run_start <= 1; st <= RUNW; end
                    8'h0e: begin cthr[AWT-1:0] <= a0[AWT-1:0]; lcfg[39:0] <= {a5, a4, a3, a2, a1}; st <= ACK; end
                    8'h10: begin leak_sh <= a0[2:0]; st <= ACK; end
                    8'h11: begin if (a0 < NC) begin cthr[a0*AWT +: AWT] <= a1[AWT-1:0]; lcfg[a0*40 +: 40] <= {a6, a5, a4, a3, a2}; end st <= ACK; end
                    8'h12: begin bits <= run24[NB-1:0]; cell_mode <= 1; run_start <= 1; st <= RUNW; end
                    8'h13: begin ld_wp <= {a2, a1, a0}; ld_wn <= {a5, a4, a3}; ld_thr <= a6; ld_start <= 1; st <= LDW; end
                    8'h20: begin m_clr <= 1; st <= ACK; end
                    8'h21: begin m_watch <= 1; st <= ACK; end
                    8'h22: begin m_slot <= a0[2:0]; m_save <= 1; st <= ACK; end
                    8'h23: begin m_recall <= 1; st <= MEMW; end
                    8'h24: begin m_rd <= a0[2:0]; st <= MEMD; end
                    8'h25: begin m_clrall <= 1; st <= ACK; end
                    8'h0f: begin bits <= run24[NB-1:0]; cell_mode <= 1; run_start <= 1; st <= RUNW; end
                    8'h07: begin dk <= 0; dj <= 0; st <= DUMP; end
                    8'h08: begin dk <= 0; dj <= 0; st <= DUMP2; end
                    8'h09: begin tnum <= {a2, a1, a0}; tdstart <= 1; st <= DIVW; end
                    8'h0a: begin dk <= 0; dj <= 0; st <= PROBE; end
                    8'h0b: begin pk <= 0; dj <= 0; st <= PEEK1; end
                    8'h0c: begin dj <= 0; st <= ECHO; end
                    8'h0d: begin ck <= 0; dj <= 0; st <= CAP1; end
                    default: st <= IDLE;
                endcase
            end
            LDW: if (!ld_start && !ld_busy) st <= ACK;                                              // ld_busy covers the clock of the start pulse (see hexn_loader_v1)
            WAIT: if (!tr_start && !tr_busy) st <= ACK;                                           // tr_busy rises the clock after the start pulse; tr_start is already cleared here
            ACK: begin tx_d <= 8'hA5; tx_s <= 1; st <= SEND; after <= IDLE; end
            RUNW: if (run_done) st <= (cmd == 8'h0f) ? CELLW : (cmd == 8'h12) ? CELLN : STAT;
            CELLW: if (!run_busy) begin ci <= 0; tx_d <= {3'b000, cell_cnt}; tx_s <= 1; st <= SEND; after <= CELLB; end
            CELLB: begin
                if (ci == K + 1) st <= IDLE;
                else begin tx_d <= (ci == 0) ? {{(8-AWT){1'b0}}, cell_fwd} : {5'b00000, cap3[3*(ci-1) +: 3]}; tx_s <= 1; ci <= ci + 1'b1; st <= SEND; after <= CELLB; end
            end
            MEMW: if (m_done && !m_recall) begin resp <= {dev24, rec24, cue24, m_second, m_known, m_best, 4'b0000, m_id}; mcnt <= 13; ci <= 0; st <= MEMRB; end
            MEMD: begin resp <= {72'd0, rdb24, 7'b0000000, m_rv}; mcnt <= 4; ci <= 0; st <= MEMRB; end
            MEMRB: begin
                if (ci == mcnt) st <= IDLE;
                else begin tx_d <= resp[8*ci +: 8]; tx_s <= 1; ci <= ci + 1'b1; st <= SEND; after <= MEMRB; end
            end
            CELLN: if (!run_busy) begin ci <= 0; st <= CELLNB; end
            CELLNB: begin
                if (ci == 2*NC + K) st <= IDLE;
                else begin tx_d <= (ci < 2*NC) ? ((ci[0] == 0) ? {3'b000, cell_cnt_all[5*(ci>>1) +: 5]} : {{(8-AWT){1'b0}}, cell_fwd_all[AWT*(ci>>1) +: AWT]}) : {5'b00000, cap3[3*(ci-2*NC) +: 3]}; tx_s <= 1; ci <= ci + 1'b1; st <= SEND; after <= CELLNB; end
            end
            STAT: if (!run_busy) begin lastvalid <= ans_valid; lastclass <= ans_class; tx_d <= {ans_valid, 2'b00, {(5-KW){1'b0}}, ans_class}; tx_s <= 1; st <= SEND; after <= CNTS; ci <= 0; end
            CNTS: begin
                if (ci == K) st <= IDLE;
                else begin tx_d <= {4'd0, cnt[4*ci +: 4]}; tx_s <= 1; ci <= ci + 1'b1; st <= SEND; after <= CNTS; end
            end
            DUMP: begin
                if (dk == K) st <= IDLE;
                else begin
                    case (dj)
                        3'd0: tx_d <= dwp_k[7:0];
                        3'd1: tx_d <= dwp_k[15:8];
                        3'd2: tx_d <= dwp_k[23:16];
                        3'd3: tx_d <= dwn_k[7:0];
                        3'd4: tx_d <= dwn_k[15:8];
                        3'd5: tx_d <= dwn_k[23:16];
                        default: tx_d <= {{(8-AWT){1'b0}}, dthr[dk*AWT +: AWT]};
                    endcase
                    tx_s <= 1; st <= SEND; after <= DUMP;
                    if (dj == 6) begin dj <= 0; dk <= dk + 1'b1; end else dj <= dj + 1'b1;
                end
            end
            DUMP2: begin
                if (dk == K) st <= IDLE;
                else begin
                    case (dj)
                        3'd0: tx_d <= dsp[dk*16 +: 8];
                        3'd1: tx_d <= dsp[dk*16 + 8 +: 8];
                        3'd2: tx_d <= dsn[dk*16 +: 8];
                        default: tx_d <= dsn[dk*16 + 8 +: 8];
                    endcase
                    tx_s <= 1; st <= SEND; after <= DUMP2;
                    if (dj == 3) begin dj <= 0; dk <= dk + 1'b1; end else dj <= dj + 1'b1;
                end
            end
            PROBE: begin
                if (dk == K) st <= IDLE;
                else begin
                    tx_d <= (dj == 0) ? dnet[dk*8 +: 8] : dfwd[dk*8 +: 8];
                    tx_s <= 1; st <= SEND; after <= PROBE;
                    if (dj == 1) begin dj <= 0; dk <= dk + 1'b1; end else dj <= dj + 1'b1;
                end
            end
            CAP1: begin
                if (ck == K*NB + 2) st <= IDLE;
                else begin dj <= dj + 1'b1; if (dj == 3) begin dj <= 0; st <= CAP2; end end
            end
            CAP2: begin tx_d <= (ck == K*NB) ? capn[7:0] : (ck == K*NB + 1) ? capn[15:8] : capd; tx_s <= 1; ck <= ck + 1'b1; st <= SEND; after <= CAP1; end
            ECHO: if (dj == 5) st <= IDLE; else begin
                tx_d <= (dj == 0) ? bits24[7:0] : (dj == 1) ? bits24[15:8] : (dj == 2) ? bits24[23:16] : (dj == 3) ? {{(8-KW){1'b0}}, label} : {2'b0, t_in};
                tx_s <= 1; st <= SEND; after <= ECHO; dj <= dj + 1'b1;
            end
            PEEK1: if (pk == K*NB) st <= IDLE; else begin dj <= dj + 1'b1; if (dj == 3) begin dj <= 0; st <= PEEK2; end end   // address is stable for 4 clocks before the data is taken
            PEEK2: begin tx_d <= {{2{pkd[5]}}, pkd}; tx_s <= 1; pk <= pk + 1'b1; st <= SEND; after <= PEEK1; end
            DIVW: if (tddone) begin dj <= 0; st <= DIVO; end
            DIVO: begin
                if (dj == 5) st <= IDLE;
                else begin
                    case (dj)
                        3'd0: tx_d <= tq[7:0];
                        3'd1: tx_d <= tq[15:8];
                        3'd2: tx_d <= tq[23:16];
                        3'd3: tx_d <= tr_[7:0];
                        default: tx_d <= {{(16-DW_T){1'b0}}, tr_[DW_T-1:8]};
                    endcase
                    tx_s <= 1; st <= SEND; after <= DIVO; dj <= dj + 1'b1;
                end
            end
            SEND: if (!tx_s && !tx_b) st <= after;    // wait for the transmitter to take the byte and finish it
            default: st <= IDLE;
        endcase
    end
endmodule
`default_nettype wire
