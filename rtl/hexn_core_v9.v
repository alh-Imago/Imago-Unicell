// hexn_core_v9.v -- Clone of hexn_core_v8.v (left untouched). v9 uses the layer 2 store v5 (rtl/hexn_store_v5.v: address index plus dense entry heap, 4-bit events, model tools/hexn_store_v5.py) instead of store v3. Settings in the core: 4 event bits, index 1,024 slots (10 bits), heap 512 rows of 4 slots (9 and 2 bits), probe 4, 32 candidates. Every earlier command and reply is unchanged except where the wider store shows: the event of 0x1A STORECMD is the low 4 bits of its argument; 0x1D STORELAST: b1 = best next event (4 bits), b3/b4 = total count (12 bits); 0x26 STOREGOAL: gbest is 4 bits; 0x1B STORERD [tab addr]: tab 0 = INDEX word (24 bits), tab 1 = candidate word (39 bits), 8-bit address (read of the old known-slot table no longer exists).
//   0x27 STORERD5 [tab alo ahi] -> 5 bytes, little-endian: tab 0 index word {valid, tag[13:0], row[8:0]} (address 0..1023), 1 row header {next_valid, next[8:0]} (0..511), 2 entry word {valid, ev[3:0], seen[7:0], contra[7:0], value[7:0]} (address {row, slot}, 0..2047), 3 candidate word {valid, key[17:0], count[3:0], start[15:0]} (0..31). v8 text follows.
// hexn_core_v8.v -- Clone of hexn_core_v7.v (left untouched). v8 uses the store WITH REWARD VALUES (rtl/hexn_store_v3.v, model tools/hexn_store_v3.py) and adds three commands, no change to any earlier command or reply:
//   0x1E STOREVAL [s g] -> 0xA5: s = value step shift (step 2^-s, 0..7, default 3), g = context length for the goal read (1..3, default 1).
//   0x1F REWARD [r] -> 0xA5: the teacher's reward (signed 8 bit, +64 = 1.0, -32 = -0.5): every store slot used since the last reward moves toward r, then the used list is emptied.
//   0x26 STOREGOAL -> 2 bytes [gbest, gval]: the goal read of the last store command: the possible next event with the highest value (gbest) and its value (signed 8 bit). Read it right after the event, before a REWARD (a REWARD clears it).
// 0x1B STORERD now returns the 39-bit known word (valid, key, seen, contra, VALUE in the low byte) or the 35-bit candidate word, little-endian, 5 bytes. Needs hexn_store_v3.v instead of hexn_store_v2.v. v7 text follows.
// hexn_core_v7.v -- Clone of hexn_core_v6.v (left untouched). v7 CONNECTS THE LAYER 2 STORE (rtl/hexn_store_v2.v) to the hold output, with six new commands and no change to any earlier command or reply:
//   0x18 STORECFG [n wlo whi mode] -> 0xA5: n = promotion sightings (1..15), w = window in events (16 bit), mode 0 = store not fed (default after reset, n=3, w=80), 1 = every NEW held class from RUNHOLD (0x16) is an OBS event (predict, self-check, update), 2 = the same as a host LOAD (pairs are added straight to the known table).
//   0x19 STORECLR -> 0xA5: clears the store's 3-event history (start of a session or sequence). The tables are kept.
//   0x1A STORECMD [c e] -> 5 bytes: runs one store command by hand (c: 0 CLR, 1 OBS, 2 LOAD, 3 RD; e = event 0..7) and replies as 0x1D.
//   0x1B STORERD [tab addr] -> 5 bytes: reads one table slot (tab 0 known, 1 candidate), the raw word, little-endian (known 31 bits, candidate 35 bits).
//   0x1C STORESTAT -> 10 bytes, little-endian 16-bit: known entries, candidates, promoted, known dropped, candidates dropped.
//   0x1D STORELAST -> 5 bytes: the last store result: b0 = {2'b0, plevel[1:0], vlevel[1:0], verdict[1:0]} (verdict 0 ok, 1 contradiction, 2 novel, 3 start), b1 = best next event, b2 = its count, b3/b4 = total count (11 bits).
// A held class is FED to the store when store mode is 1 or 2, the hold's output is valid and is not NONE, and it is either a change (chg) or the first sample since SETHOLD/reset. The event is the class number (K <= 8). The store's time is a 16-bit count of OBS/LOAD commands. Needs hexn_store_v2.v in the build. v6 text follows.
// hexn_core_v6.v -- Clone of hexn_core_v5.v (left untouched). v6 uses hexn_hold_v2 and adds command 0x17 SETHOLDM [m] -> 0xA5: m = 1 makes the hold IGNORE 'unknown' (NONE) answers (skip_none), m = 0 is the strict rule of v5 (default after reset). 0x14 SETHOLD and 0x16 RUNHOLD are as in v5; SETHOLD does not change the mode. Needs hexn_hold_v2.v instead of hexn_hold_v1.v. v5 text follows.
// hexn_core_v5.v -- Clone of hexn_core_v4.v (left untouched). v5 adds the HOLD COUNTER (hexn_hold_v1, design docs/hex-n/LAYER_INTERFACES_v1.md) behind the bank's answer, with two commands and no change to any earlier command: 0x14 SETHOLD [n] -> 0xA5: sets the hold length n (0 or 1 = every change passes at once; default after reset 1) AND clears the hold, so the next sample is taken at once; 0x16 RUNHOLD [b0 b1 b2] -> 3 bytes: runs one sample exactly as 0x06 (plain run, no cells), feeds the bank's answer to the hold (answer NONE = no answer or tie counts as an answer), and replies [held class (all ones in W = KW+1 bits = NONE), flags {6'b0, chg, valid}, raw answer as the STAT byte {ans_valid, 2'b00, pad, ans_class}]. The count bytes of 0x06 are NOT sent. Needs hexn_hold_v1.v in the build and the same defines as core v4.
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
module hexn_core_v9 (input wire clk, input wire [7:0] rx_d, input wire rx_v, output reg [7:0] tx_d, output reg tx_s, input wire tx_b, output wire [5:0] led);
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
    localparam [5:0] IDLE = 0, ARG = 1, GO = 2, WAIT = 3, ACK = 4, RUNW = 5, STAT = 6, CNTS = 7, SEND = 8, DUMP = 9, DUMP2 = 10, DIVW = 11, DIVO = 12, PROBE = 13, PEEK1 = 14, PEEK2 = 15, ECHO = 16, CAP1 = 17, CAP2 = 18, CELLW = 19, CELLB = 20, CELLN = 21, CELLNB = 22, MEMW = 23, MEMD = 24, MEMRB = 25, LDW = 26, HOLDA = 27, HOLDB = 28, HOLDC = 29, HOLDR = 30, STW = 31, STRR = 32, STRT = 33, STRS = 34, STI = 35, STRG = 36;
    // SAVE AND RECALL memory block (commands 0x20..0x25)
    reg m_clr, m_clrall, m_watch, m_save, m_recall; reg [2:0] m_slot, m_rd; reg [103:0] resp; reg [4:0] mcnt; wire m_done, m_rv; wire [3:0] m_id; wire [7:0] m_best, m_second, m_known; wire [NB-1:0] m_cue, m_rec, m_dev, m_rdb;
    wire [23:0] cue24 = {{(24-NB){1'b0}}, m_cue}; wire [23:0] rec24 = {{(24-NB){1'b0}}, m_rec}; wire [23:0] dev24 = {{(24-NB){1'b0}}, m_dev}; wire [23:0] rdb24 = {{(24-NB){1'b0}}, m_rdb}; wire [23:0] mb24 = {a2, a1, a0}; wire [23:0] mm24 = {a5, a4, a3};
    hexn_mem_v1 #(.NB(NB), .M(8)) mem(.clk(clk), .rst(rst), .op_clr(m_clr), .op_clrall(m_clrall), .op_watch(m_watch), .w_bits(mb24[NB-1:0]), .w_mask(mm24[NB-1:0]), .op_save(m_save), .sv_slot(m_slot), .op_recall(m_recall), .done(m_done),
        .rd_slot(m_rd), .rd_valid(m_rv), .rd_bits(m_rdb), .best_id(m_id), .best_m(m_best), .second_m(m_second), .known_cnt(m_known), .cue_bits(m_cue), .rec_bits(m_rec), .dev_mask(m_dev));
    reg [5:0] st, after; reg [7:0] cmd; reg [2:0] nargs, got; reg [7:0] a0, a1, a2, a3, a4, a5; reg cell_mode; reg [NC*40-1:0] lcfg; reg [NC*AWT-1:0] cthr; reg [2:0] leak_sh; reg [7:0] a6; wire [NC*5-1:0] cell_cnt_all; wire [NC*AWT-1:0] cell_fwd_all; wire [4:0] cell_cnt = cell_cnt_all[4:0]; wire [AWT-1:0] cell_fwd = cell_fwd_all[AWT-1:0];
    wire [NC*2*K-1:0] lcfg_w; genvar gq; generate for (gq = 0; gq < NC; gq = gq + 1) begin : LW assign lcfg_w[gq*2*K +: 2*K] = lcfg[gq*40 +: 2*K]; end endgenerate wire [3*K-1:0] cap3; wire [23:0] arg24 = {a3, a2, a1}; wire [23:0] run24 = {a2, a1, a0}; reg [11:0] ci;
    reg [$clog2(K+1):0] dk; wire [23:0] bits24 = {{(24-NB){1'b0}}, bits};
    wire [23:0] dwp_k = {{(24-NB){1'b0}}, dwp[dk*NB +: NB]}; wire [23:0] dwn_k = {{(24-NB){1'b0}}, dwn[dk*NB +: NB]}; reg [2:0] dj; reg [KW-1:0] lastclass; reg lastvalid;
    assign led = ~{lastvalid, {(5-KW){1'b0}}, lastclass};
    // HOLD COUNTER (commands 0x14, 0x16)
    localparam HW = KW + 1; reg h_en, h_clr; reg [7:0] hold_n; reg hold_skip; wire [HW-1:0] h_dout; wire h_valid, h_chg;
    wire [HW-1:0] h_din = ans_valid ? {1'b0, ans_class} : {HW{1'b1}};
    hexn_hold_v2 #(.W(HW), .CW(8)) hold(.clk(clk), .rst(rst | h_clr), .en(h_en), .din(h_din), .n(hold_n), .skip_none(hold_skip), .dout(h_dout), .valid(h_valid), .chg(h_chg));
    initial begin h_en = 0; h_clr = 0; hold_n = 1; hold_skip = 0; end
    // LAYER 2 STORE (commands 0x18..0x1D)
    reg [1:0] store_mode; reg [3:0] st_n; reg [15:0] st_w, store_t, st_t; reg st_cv; reg [2:0] st_cmd, pend_cmd; reg [3:0] st_ev, pend_ev; reg [5:0] pend_next, stw_next; reg h_fresh; reg tab_sel; reg chg_l;      // chg_l: the hold's chg lasts ONE clock, so the reply uses the copy taken in HOLDC
    reg [7:0] st_rew, pend_rew; reg [2:0] st_vs; reg [1:0] st_gl; wire [7:0] st_gval;
    localparam SEVB = 4, SIB = 10, SRB = 9, SRSB = 2, SP = 4, SCC = 32, SCA = 5; localparam SIW = 1 + (2 + 3 * SEVB) + SRB, SEW = 1 + SEVB + 24, SCW = 1 + (2 + 4 * SEVB) + 20;
    reg [SIB-1:0] st_ia; reg [SRB-1:0] st_ha; reg [SRB+SRSB-1:0] st_ea; reg [SCA-1:0] st_ca; reg [1:0] st_tab; wire [SIW-1:0] st_iw; wire [SRB:0] st_hw; wire [SEW-1:0] st_ew; wire [SCW-1:0] st_cw;
    wire st_busy, st_done; wire [1:0] st_verdict, st_vlevel, st_plevel; wire [3:0] st_pbest, st_gbest; wire [7:0] st_pseen; wire [SEVB+7:0] st_ptot; wire [15:0] st_nk, st_nc, st_np, st_ndk, st_ndc;
    hexn_store_v5 #(.EVB(SEVB), .IB(SIB), .RB(SRB), .RSB(SRSB), .P(SP), .CCAP(SCC), .CA(SCA)) store(.clk(clk), .rst(rst), .cmd_valid(st_cv), .cmd(st_cmd), .ev_in(st_ev), .t_in(st_t), .n_prom(st_n), .w_win(st_w), .rew_in(st_rew), .vshift(st_vs), .glvl(st_gl), .busy(st_busy), .done(st_done), .verdict(st_verdict), .vlevel(st_vlevel), .plevel(st_plevel), .pbest(st_pbest), .pbest_seen(st_pseen), .ptotal(st_ptot), .gbest(st_gbest), .gval(st_gval),
        .n_known(st_nk), .n_cand(st_nc), .n_promoted(st_np), .n_dropk(st_ndk), .n_dropc(st_ndc), .dbg_ia(st_ia), .dbg_iw(st_iw), .dbg_ha(st_ha), .dbg_hw(st_hw), .dbg_ea(st_ea), .dbg_ew(st_ew), .dbg_ca(st_ca), .dbg_cw(st_cw));
    wire [39:0] rdw = (st_tab == 2'd0) ? {{(40-SIW){1'b0}}, st_iw} : (st_tab == 2'd1) ? {{(40-SRB-1){1'b0}}, st_hw} : (st_tab == 2'd2) ? {{(40-SEW){1'b0}}, st_ew} : {{(40-SCW){1'b0}}, st_cw};
    initial begin st_rew = 0; pend_rew = 0; st_vs = 3; st_gl = 1; store_mode = 0; st_n = 3; st_w = 80; store_t = 0; st_cv = 0; st_cmd = 0; st_ev = 0; st_t = 0; h_fresh = 1; end
    wire h_isnone = &h_dout; wire feed = (store_mode != 0) && h_valid && !h_isnone && (h_chg || h_fresh);
    always @(posedge clk) begin
        h_en <= 1'b0; h_clr <= 1'b0; st_cv <= 1'b0;
        ld_start <= 1'b0; tdstart <= 1'b0; tr_start <= 1'b0; run_start <= 1'b0; tx_s <= 1'b0; tdstart <= 1'b0; m_clr <= 1'b0; m_clrall <= 1'b0; m_watch <= 1'b0; m_save <= 1'b0; m_recall <= 1'b0;
        if (rst) begin m_slot <= 0; m_rd <= 0; cell_mode <= 0; cthr <= 0; lcfg <= 0; leak_sh <= 0; hold_n <= 8'd1; hold_skip <= 1'b0; store_mode <= 0; st_vs <= 3'd3; st_gl <= 2'd1; st_n <= 4'd3; st_w <= 16'd80; store_t <= 0; h_fresh <= 1'b1; st <= IDLE; lastclass <= 0; lastvalid <= 0; t_in <= 0; bits <= 0; label <= 0; end
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
                    8'h14: begin nargs <= 1; st <= ARG; end
                    8'h16: begin nargs <= 3; st <= ARG; end
                    8'h17: begin nargs <= 1; st <= ARG; end
                    8'h18: begin nargs <= 4; st <= ARG; end
                    8'h19: begin nargs <= 0; st <= GO; end
                    8'h1a: begin nargs <= 2; st <= ARG; end
                    8'h1b: begin nargs <= 2; st <= ARG; end
                    8'h27: begin nargs <= 3; st <= ARG; end
                    8'h1c: begin nargs <= 0; st <= GO; end
                    8'h1d: begin nargs <= 0; st <= GO; end
                    8'h1e: begin nargs <= 2; st <= ARG; end
                    8'h1f: begin nargs <= 1; st <= ARG; end
                    8'h26: begin nargs <= 0; st <= GO; end
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
                    8'h14: begin hold_n <= a0; h_clr <= 1; h_fresh <= 1'b1; st <= ACK; end
                    8'h18: begin st_n <= a0[3:0]; st_w <= {a2, a1}; store_mode <= a3[1:0]; st <= ACK; end
                    8'h19: begin pend_cmd <= 3'd0; pend_ev <= 4'd0; pend_next <= ACK; st <= STI; end
                    8'h1a: begin pend_cmd <= a0[2:0]; pend_ev <= a1[3:0]; pend_next <= STRR; st <= STI; end
                    8'h1b: begin st_tab <= a0[0] ? 2'd3 : 2'd0; st_ia <= {2'b0, a1}; st_ha <= {1'b0, a1}; st_ea <= {3'b0, a1}; st_ca <= a1[4:0]; dj <= 0; st <= STRT; end
                    8'h27: begin st_tab <= a0[1:0]; st_ia <= {a2, a1}; st_ha <= {a2[0], a1}; st_ea <= {a2[2:0], a1}; st_ca <= a1[4:0]; dj <= 0; st <= STRT; end
                    8'h1c: st <= STRS;
                    8'h1d: st <= STRR;
                    8'h1e: begin st_vs <= a0[2:0]; st_gl <= (a1[1:0] == 2'd0) ? 2'd1 : a1[1:0]; st <= ACK; end
                    8'h1f: begin pend_cmd <= 3'd4; pend_ev <= 4'd0; pend_rew <= a0; pend_next <= ACK; st <= STI; end
                    8'h26: st <= STRG;
                    8'h17: begin hold_skip <= a0[0]; st <= ACK; end
                    8'h16: begin bits <= run24[NB-1:0]; cell_mode <= 0; run_start <= 1; st <= RUNW; end
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
            RUNW: if (run_done) st <= (cmd == 8'h0f) ? CELLW : (cmd == 8'h12) ? CELLN : (cmd == 8'h16) ? HOLDA : STAT;
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
            HOLDA: if (!run_busy) begin h_en <= 1'b1; st <= HOLDB; end
            HOLDB: st <= HOLDC;                                                                   // the hold registers update at the end of the clock in which h_en is high
            HOLDC: begin chg_l <= h_chg; h_fresh <= 1'b0; if (feed) begin pend_cmd <= (store_mode == 2'd2) ? 3'd2 : 3'd1; pend_ev <= h_dout[3:0]; pend_next <= HOLDR; st <= STI; end else st <= HOLDR; end
            HOLDR: begin resp <= {80'd0, ans_valid, 2'b00, {(5-KW){1'b0}}, ans_class, 6'b000000, chg_l, h_valid, {(8-HW){1'b0}}, h_dout}; mcnt <= 3; ci <= 0; st <= MEMRB; end
            STI: if (!st_busy && !st_cv) begin st_cv <= 1'b1; st_cmd <= pend_cmd; st_ev <= pend_ev; st_rew <= pend_rew; st_t <= store_t; if (pend_cmd == 3'd1 || pend_cmd == 3'd2) store_t <= store_t + 1'b1; stw_next <= pend_next; st <= STW; end
            STW: if (st_done) st <= stw_next;
            STRR: begin resp <= {64'd0, 4'b0, st_ptot[11:8], st_ptot[7:0], st_pseen, 4'b0, st_pbest, 2'b00, st_plevel, st_vlevel, st_verdict}; mcnt <= 5; ci <= 0; st <= MEMRB; end
            STRT: begin dj <= dj + 1'b1; if (dj == 4) begin resp <= {64'd0, rdw}; mcnt <= 5; ci <= 0; st <= MEMRB; end end
            STRG: begin resp <= {88'd0, st_gval, 4'b0, st_gbest}; mcnt <= 2; ci <= 0; st <= MEMRB; end
            STRS: begin resp <= {24'd0, st_ndc, st_ndk, st_np, st_nc, st_nk}; mcnt <= 10; ci <= 0; st <= MEMRB; end
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
