`default_nettype none
`timescale 1ns / 1ps
// hexn_base_ctl_v6 -- (11 Nov 2026: clone of hexn_base_ctl_v5; ADDED: an EVENT RAM on the chip (2**EA bytes, block RAM; EA = 15: 32,768 bytes) that the host fills once and the controller REPLAYS into the speech chain at the chain's own speed (one event per clock), and a CHAIN RESULT RAM (2,048 words of 32 bits) that takes every window result of a replay; commands w g v; every v5 command is unchanged. Simulated; not run on any card yet.
//   'w' ah al nh nl b..    store nh*256+nl bytes in the event RAM from address ah*256+al (only the low EA bits are used) -> 'K'. Byte 0..253 = an event (ev_idx), 254 = START of a recording, 255 = WINDOW END.
//   'g' ah al nh nl        REPLAY nh*256+nl bytes from address ah*256+al into the chain: an event takes one clock; a window end waits 3 idle clocks, pulses win_end, waits for the chain's result and stores it in the result RAM (from word 0 at every 'g'); a start takes 4 clocks.
//                          -> 7 bytes when done: status 'K' (or 'E' if the chain gave no result within 255 clocks), the clocks the replay took (4 bytes little endian), results produced (2 bytes little endian; only the first 2,048 are stored). During a replay the results do NOT go to the 'u' queue.
//   'v' ah al n            read n (1..255) words of the result RAM from word ah*256+al -> 4n bytes (each word little endian, same bits as the 'u' result word)
// Earlier text of v5:) (11 Nov 2026: clone of hexn_base_ctl_v4; ADDED: the SPEECH CHAIN (rtl/hexn_speech_chain_v1.v, unchanged) as one more target behind the byte port, with three new commands k e u; every v4 command is unchanged. Not run on any card yet.
//   'k' sel ah al d0..d9   write one config word of the chain (cfg_sel = sel: 0 WROM, 1 THR, 2 LP, 3 CFG; address ah*256+al; 80-bit word, d0 = bits 7:0) -> 'K'. sel = 7 is special: pulses the chain's START (clears its state for a new recording; no address/data used, but all 13 bytes are still sent).
//   'e' nh nl b..          stream nh*256+nl event bytes into the chain: a byte 0..254 is an event (ev_idx = step-in-window * 48 + line), 255 is WINDOW END -> 'K' after the last byte. The host sends bytes >= 64 clocks apart (the JTAG bridge gives 128), which satisfies the chain's idle-clock rules (>= 2 idle clocks before a window end, next window's events only after the result).
//   'u'                    next chain result (oldest first) -> 6 bytes: n (results waiting, before this one is taken), 4 result bytes little endian (0 if none: bits 2:0 window, 6:3 class (10 = none), 10:7 prediction, 27:11 gap (signed 17), 28 stop flag), lost (results the 8-deep result queue had to drop, saturating).
// Earlier text of v4:) (5 Nov 2026: clone of hexn_base_ctl_v3; ADDED: a WEIGHT STORE (4 sets of the judge's complete weights, block RAM, separate from the program library) with a cross-index from library slots to weight sets; commands O F E r, and 'Q' / 'Z' load the indexed weights first; every v3 command is unchanged when no index is set. Not run on any card yet. Note for v3:) (5 Nov 2026: clone of hexn_base_ctl_v2; ADDED: a DATA RAM and the commands T (store entries) and H (run entries from the RAM by itself); every v2 command and reply is unchanged. Not run on any card yet. Note for v2:) (5 Nov 2026: clone of hexn_base_ctl_v1 [text of that header follows]; ADDED: a RESULTS RAM with stop-and-flag, commands X, Y, V, and an input stop on 'G'; every v1 command and reply is unchanged. Not run on any card yet.) BASE controller for a Kintex card holding a JUDGE and up to 4 hex pattern ARRAYS in one bitstream (5 Nov 2026, Alan 10:53: "start with 2 ... a base size of the design ... before, during and after could become just a program state"). NEW file. Not run on any card yet.
// It sits between the JTAG byte port (rx_d/rx_v/tx_d/tx_s/tx_b of hexn_jtag_bridge_v1) and NARR copies of hexn_frame_v6 (one per array), and holds: the SELECTOR (which array the host talks to), a PROGRAM LIBRARY (4 slots of 256 bytes: config-chain images, block RAM), and the JUDGE (hexn_scorer_v3) with a small queue that can feed it the selected array's output words by itself (AFTER mode).
// Commands (opcode byte first). Anything that is not one of these is passed to the selected array's frame unchanged (I W B D G L S of hexn_frame_v6, same replies), so every array test of the single-array design works after 'A n':
//   'A' n            select array n (0..NARR-1)                               -> 'K'
//   'N'              base info                                                -> 6 bytes: id 0x42415345 little endian (45 53 41 42), NARR, 4 (library slots)
//   'P' s lh ll d..  write library slot s (0..3): length = lh*256+ll (<= 256), then that many bytes -> 'K'
//   'Q' s            load the selected array's config chain from library slot s: the controller sends 'B' and the array's chain bytes (CHB bytes) to the frame, 16 clocks apart; the frame answers 'K' as for a host 'B'
//   'J' b0 b1 b2 b3  one word (little endian) to the judge (LOAD / BIAS / SCORE words of hexn_scorer_v3) -> 'K' when the judge has taken it
//   'M' m            mode: bit 0 = AFTER mode (the selected array's output words go to the judge by themselves, each nibble limited to 11 = a bin); bit 1 = empty the queues and counters   -> 'K'
//   'R'              next judge result (oldest first) -> 6 bytes: n (results waiting, before this one is taken), 4 result bytes little endian (0 if none), lost (words the judge queue had to drop, saturating)
//   'C' a b          slot choice table: judge result with pred 0 -> slot a, with pred 1 -> slot b (default 0, 1)  -> 'K'
//   'Z'              CHOOSE AND LOAD (judge BEFORE the run, slot side): takes the oldest judge result, picks the slot from the table by its pred bit (bit 31), and loads that slot into the selected array exactly like 'Q' (the frame answers 'K'); with no result waiting it answers 'E' and does nothing
//   'U'              last choice -> 2 bytes: the slot chosen by the last 'Z', the number of choices made (saturating at 255)
// WEIGHT STORE (new in v4): 4 sets x 512 words of 32 bits (block RAM, 8 KB), SEPARATE from the program library. A set holds the judge's complete weights in the judge's own load format: for address k = 0..127 a LOAD word of class 0 then one of class 1, then one BIAS word = 257 words (words 257..511 unused). The judge produces and takes exactly this format (hexn_scorer_v3 dump / LOAD).
//   'O' s            SAVE: the judge dumps all its weights into set s (0..3) -> 'K' (or 'E' if the judge did not answer within 65,536 clocks)
//   'F' s            LOAD: the 257 words of set s are fed to the judge -> 'K'
//   'E' p s          CROSS-INDEX: library slot p (0..3) is tied to weight set s (0..3); s >= 4 removes the tie -> 'K'. While a slot is tied, 'Q' p and the slot chosen by 'Z' first load that weight set into the judge and then load the program, so the final 'K' means both are in. Untied slots (the default) behave exactly as before.
//   'r' s ah al n    READ BACK n words (1..255) of set s from word address ah*256+al -> 4n bytes (each word little endian)
// DATA RAM (new in v3): 2**DA entries of 8 bytes (DA = 9: 512 entries, 4 KB, block RAM). An entry is one step of what the host does today with 'D' and 'G', so a stream of entries is a run: b0 bit 7 = 0: SET INPUT: b0[2:0] = row, b1..b4 = the 32-bit word (little endian), same as 'D'; b0 bit 7 = 1: GO: b0[6:0] = row mask, b1 b2 = clocks to wait after the array has answered 'K' (the output latency of the program; the controller does not know it), same as 'G'. b5..b7 are not used (write 0).
//   'T' ah al nh nl d..   store nh*256+nl entries (8 bytes each) from entry address ah*256+al (only the low DA bits are used: an address beyond the RAM wraps) -> 'K'
//   'H' ah al nh nl       RUN nh*256+nl entries from entry address ah*256+al into the SELECTED array: each entry is sent to its frame as the 'D' or 'G' bytes (16 clocks apart, as 'Q' does), the controller waits for the frame's 'K' (the frame's own 'K' is not passed to the host), and after a GO waits the entry's clocks. A GO is not sent while the results RAM is armed and FULL (the input side stops). -> 3 bytes: status ('K' all entries done, 'F' stopped at a GO because the results RAM is FULL, 'E' the frame did not answer within 65,536 clocks), entries executed (2, little endian). To continue after 'F': read and clear the results ('V', 'X'), then 'H' again from address + executed.
// RESULTS RAM (new in v2): 2**RA records of 8 bytes (RA = 10: 1,024 records, 8 KB, block RAM). A record is written for every output word of the SELECTED array while recording is armed, and for every judge result. Record bytes: b0 = {kind (1 = judge result), array (2 bits), 2'b0, row (3 bits)}, b1 b2 = tick (little endian; 0 for a judge result), b3..b6 = the 32-bit word (little endian), b7 = the record's index mod 256.
//   'X' m            m bit 0 = recording armed (1) or off (0); bit 1 = clear (records, read pointer, lost and refusal counters)  -> 'K'
//   'Y'              status -> 7 bytes: records stored (2, LE), lost (1, saturating: records that did not fit), flags (bit 0 FULL, bit 1 ARMED), read pointer (2, LE), refused starts (1, saturating)
//   'V' n            read the next n records from the read pointer (stops at the last stored one) -> 1 byte k = records returned, then k x 8 bytes; the read pointer advances (the records stay in the RAM until 'X' clears them)
// STOP AND FLAG: FULL is set when the stored count reaches 2**RA - RMARGIN (the margin is for words already in the array's pipeline). While recording is armed and FULL is set, a host 'G' (start of a run: the input side) is refused: the controller swallows 'G' and its mask byte, answers 'F' (0x46) and counts the refusal; nothing is sent to the array. Records stop at 2**RA; any further word is counted as lost.
// Commands are taken only when the selected frame is idle and no base command is running; bytes that follow a command are its arguments.
module hexn_base_ctl_v6 #(parameter EA = 15, parameter NARR = 1, parameter DA = 9, parameter RA = 10, parameter RMARGIN = 16, parameter [16*4-1:0] CHB = {16'd0, 16'd0, 16'd0, 16'd164}) (
    input wire clk,
    input wire [7:0] rx_d, input wire rx_v, output wire [7:0] tx_d, output wire tx_s, input wire tx_b,
    output wire [NARR-1:0] a_rx_v, output wire [7:0] a_rx_d,
    input wire [8*NARR-1:0] a_tx_d, input wire [NARR-1:0] a_tx_s, input wire [NARR-1:0] a_ov, input wire [32*NARR-1:0] a_od, input wire [NARR-1:0] a_idle, input wire [16*NARR-1:0] a_ot, input wire [3*NARR-1:0] a_or);
    // ---------------- selector and state
    reg [1:0] sel = 0;
    localparam IDLE = 0, ARGA = 1, ARGPS = 2, ARGPH = 3, ARGPL = 4, PDATA = 5, ARGQ = 6, QRUN = 7, ARGJ = 8, JWAIT = 9, ARGM = 10, REPLY = 11, ARGC1 = 12, ARGC2 = 13, ARGX = 14, ARGV = 15, VHD = 16, VWT = 17, VSND = 18, ARGG = 19, WLA = 34, WLB = 35, WLC = 36, SV1 = 37, ARGO = 38, ARGF = 39, ARGE1 = 40, ARGE2 = 41, AR1 = 42, AR2 = 43, AR3 = 44, AR4 = 45, RDW = 46, RDS = 47, KARG = 48, EN1 = 49, EN2 = 50, EDAT = 51, EM1 = 52, EM2 = 53, EM3 = 54, EM4 = 55, EMD = 56, GR1 = 57, GR2 = 58, GR3 = 59, GR4 = 60, GRP = 61, GRUN = 62, GRW = 63, GROUT = 64, GRS = 65, GRFIN = 66, CV1 = 67, CV2 = 68, CV3 = 69, CVW = 70, CVS = 71, TA1 = 20, TA2 = 21, TN1 = 22, TN2 = 23, TDATA = 24, HA1 = 25, HA2 = 26, HN1 = 27, HN2 = 28, HFE = 29, HSD = 30, HWK = 31, HGW = 32, HFIN = 33;
    reg [6:0] cs = IDLE;
    wire sel_idle = a_idle[sel];
    reg rec_en = 0; reg [15:0] rcount = 0, rrp = 0; wire rfull = rcount >= (16'd1 << RA) - RMARGIN;      // results RAM state (see below)
    wire is_op = (rx_d == 8'h41) || (rx_d == 8'h4e) || (rx_d == 8'h50) || (rx_d == 8'h51) || (rx_d == 8'h4a) || (rx_d == 8'h4d) || (rx_d == 8'h52) || (rx_d == 8'h43) || (rx_d == 8'h5a) || (rx_d == 8'h55) || (rx_d == 8'h58) || (rx_d == 8'h59) || (rx_d == 8'h56) || (rx_d == 8'h47 && rec_en && rfull) || (rx_d == 8'h54) || (rx_d == 8'h48) || (rx_d == 8'h4f) || (rx_d == 8'h46) || (rx_d == 8'h45) || (rx_d == 8'h72) || (rx_d == 8'h6b) || (rx_d == 8'h65) || (rx_d == 8'h75) || (rx_d == 8'h77) || (rx_d == 8'h67) || (rx_d == 8'h76);
    wire mine = rx_v && cs == IDLE && sel_idle && is_op;
    // ---------------- replay of a library slot into the selected frame
    reg rp_v = 0; reg [7:0] rp_d = 0;
    assign a_rx_d = rp_v ? rp_d : rx_d;
    genvar g; generate for (g = 0; g < NARR; g = g + 1) begin : rxg
        assign a_rx_v[g] = (sel == g) && ((rx_v && cs == IDLE && !mine) || rp_v);
    end endgenerate
    // ---------------- program library: 4 slots x 256 bytes (block RAM: one write port, one registered read port)
    (* ram_style = "block" *) reg [7:0] lib [0:1023];
    reg [9:0] laddr = 0; reg [7:0] libq = 0; reg lw = 0; reg [9:0] lwa = 0; reg [7:0] lwd = 0;
    always @(posedge clk) begin libq <= lib[laddr]; if (lw) lib[lwa] <= lwd; end
    reg [1:0] pslot = 0; reg [15:0] plen = 0; reg [7:0] pi = 0;
    reg [1:0] qslot = 0; reg [8:0] qi = 0; reg [4:0] rc = 0; reg qb = 0; wire [15:0] chb_sel = CHB[16*sel +: 16];
    // ---------------- judge and its queues
    reg [31:0] jw = 0; reg [1:0] jn = 0; reg jhost = 0;
    reg [31:0] af [0:3]; reg [2:0] afn = 0; reg [1:0] afr = 0, afw = 0; reg [7:0] lost = 0;           // words from the array waiting for the judge
    reg [31:0] rq [0:7]; reg [3:0] rqn = 0; reg [2:0] rqr = 0, rqw = 0;                              // judge results waiting for the host
    reg automode = 0; reg [1:0] ch0 = 0, ch1 = 1, lastslot = 0; reg [7:0] nchoice = 0; reg [1:0] cnew;      // slot choice table and the last choice
    wire [31:0] raw = a_od[32*sel +: 32]; wire ovs = a_ov[sel];
    function [31:0] clampbins(input [31:0] x);
        integer i; begin for (i = 0; i < 8; i = i + 1) clampbins[4*i +: 4] = (x[4*i +: 4] > 4'd11) ? 4'd11 : x[4*i +: 4]; end
    endfunction
    wire j_ack, j_ov; wire [31:0] j_od; wire j_clrb, j_dmv, j_dml, j_dmb; wire [31:0] j_dmd; reg j_dump = 0; reg wl_v = 0; reg [31:0] wl_d = 0;
    wire j_in_v = jhost | wl_v | (afn != 0); wire [31:0] j_in_d = jhost ? jw : wl_v ? wl_d : af[afr];
    reg [3:0] por = 4'hf; always @(posedge clk) if (por != 0) por <= por - 1'b1;                       // power-on reset of the judge (its registers have no initial values)
    hexn_scorer_v3 judge (.clk(clk), .rst(por != 0), .in_data(j_in_d), .in_valid(j_in_v), .in_ack(j_ack), .out_data(j_od), .out_valid(j_ov), .out_ack(1'b1),
                          .clr(1'b0), .clr_busy(j_clrb), .dump(j_dump), .dm_valid(j_dmv), .dm_data(j_dmd), .dm_last(j_dml), .dm_busy(j_dmb));
    // ---------------- results RAM (block RAM: one write port, one registered read port)
    (* ram_style = "block" *) reg [63:0] res [0:(1<<RA)-1];
    reg [RA-1:0] rwa = 0; reg [63:0] rwd = 0; reg rw = 0; reg [RA-1:0] raddr = 0; reg [63:0] resq = 0;
    always @(posedge clk) begin resq <= res[raddr]; if (rw) res[rwa] <= rwd; end
    reg [7:0] rlost = 0, gref = 0; reg jh_v = 0; reg [31:0] jh_d = 0;
    wire arec = rec_en && ovs && por == 0; wire [15:0] otk = a_ot[16*sel +: 16]; wire [2:0] orw = a_or[3*sel +: 3];
    wire rdrop_a = (arec || jh_v) && rcount >= (16'd1 << RA); wire rdrop_j = j_ov && rec_en && por == 0 && jh_v && arec;
    reg [7:0] vleft = 0, vi = 0; reg [3:0] vw = 0;
    // ---------------- weight store (block RAM: one write port, one registered read port) and its machines
    (* ram_style = "block" *) reg [31:0] ws [0:2047];
    reg [10:0] wsaddr = 0, wsa = 0; reg [31:0] wsq = 0, wsd = 0; reg wsw = 0;
    always @(posedge clk) begin wsq <= ws[wsaddr]; if (wsw) ws[wsa] <= wsd; end
    reg [11:0] wixv = 0;                         // cross-index: 3 bits per library slot, {tied, set}
    reg [1:0] wl_set = 0, sv_set = 0, rd_set = 0; reg [8:0] wl_k = 0, sv_k = 0; reg wl_then_q = 0; reg [3:0] wlw = 0; reg [15:0] sv_to = 0;
    reg [7:0] ex_slot = 0; reg [15:0] rd_a = 0; reg [7:0] rd_left = 0; reg [1:0] rd_i = 0; reg [3:0] rd_w = 0;
    // ---------------- data RAM (block RAM: one write port, one registered read port) and the run-from-RAM machine
    (* ram_style = "block" *) reg [63:0] dat [0:(1<<DA)-1];
    reg [DA-1:0] daddr = 0, dwa = 0; reg [63:0] datq = 0, dwd = 0; reg dw = 0;
    always @(posedge clk) begin datq <= dat[daddr]; if (dw) dat[dwa] <= dwd; end
    reg [15:0] tadr = 0, tn = 0, hadr = 0, hn = 0, hdone = 0, hwc = 0, hto = 0; reg [55:0] tacc = 0; reg [2:0] tb = 0, hb = 0; reg [4:0] hrc = 0; reg [3:0] hw = 0; reg hrun = 0; reg [7:0] hstat = 0;
    wire fk = a_tx_s[sel];          // the selected frame answers 'K' (not passed to the host while a run from the RAM goes)
    wire hgo = datq[7];             // the entry now read is a GO
    reg [7:0] hbyte;
    always @* case (hb) 3'd0: hbyte = hgo ? 8'h47 : 8'h44; 3'd1: hbyte = hgo ? {1'b0, datq[6:0]} : {5'b0, datq[2:0]}; 3'd2: hbyte = datq[15:8]; 3'd3: hbyte = datq[23:16]; 3'd4: hbyte = datq[31:24]; default: hbyte = datq[39:32]; endcase
    // ---------------- speech chain (unchanged module) and its result queue
    reg ch_we = 0; reg [2:0] ch_sel = 0; reg [15:0] ch_addr = 0; reg [79:0] ch_data = 0; reg ch_start = 0, ch_ev = 0, ch_wend = 0; reg [7:0] ch_idx = 0;
    wire cv_ov; wire [2:0] cv_win; wire [3:0] cv_cls, cv_pred; wire signed [16:0] cv_gap; wire cv_stop;
    hexn_speech_chain_v1 chain (.clk(clk), .rst(por != 0), .cfg_we(ch_we), .cfg_sel(ch_sel), .cfg_addr(ch_addr), .cfg_data(ch_data), .start(ch_start), .ev_valid(ch_ev), .ev_idx(ch_idx), .win_end(ch_wend),
                                .out_valid(cv_ov), .out_win(cv_win), .out_cls(cv_cls), .out_pred(cv_pred), .out_gap(cv_gap), .out_stop(cv_stop));
    (* ram_style = "registers" *) reg [31:0] cq [0:7]; reg [3:0] cqn = 0; reg [2:0] cqr = 0, cqw = 0; reg [7:0] clost = 0; reg [3:0] kb = 0; reg [15:0] en = 0;
    wire [31:0] cv_word = {3'd0, cv_stop, cv_gap, cv_pred, cv_cls, cv_win};
    // ---------------- event RAM and chain result RAM (block RAM: one write port, one registered read port each) and the replay machine
    (* ram_style = "block" *) reg [7:0] evm [0:(1<<EA)-1];
    reg [EA-1:0] eaddr = 0, ewa = 0; reg [7:0] evq = 0, ewd = 0; reg eww = 0;
    always @(posedge clk) begin evq <= evm[eaddr]; if (eww) evm[ewa] <= ewd; end
    (* ram_style = "block" *) reg [31:0] crm [0:2047];
    reg [10:0] craddr = 0, crwa = 0; reg [31:0] crq = 0, crwd = 0; reg crww = 0;
    always @(posedge clk) begin crq <= crm[craddr]; if (crww) crm[crwa] <= crwd; end
    reg [15:0] ea_a = 0, ea_n = 0, gcnt = 0, cva = 0; reg grun = 0; reg [31:0] gclk = 0; reg [1:0] gw = 0, cvi = 0; reg [7:0] gto = 0, gstat = 0, cvn = 0; reg [3:0] cvw = 0;
    // ---------------- reply path of the controller
    reg [63:0] rbuf = 0; reg [2:0] rn = 0, ri = 0; reg c_go = 0; reg [7:0] c_d = 0;
    assign tx_s = c_go | ((|a_tx_s) && !hrun); assign tx_d = c_go ? c_d : a_tx_d[8*sel +: 8];
    task reply_k; begin rbuf[7:0] <= 8'h4b; rn <= 1; ri <= 0; cs <= REPLY; end endtask
    always @(posedge clk) begin
        c_go <= 1'b0; eww <= 1'b0; crww <= 1'b0; if (grun) gclk <= gclk + 1'b1; ch_we <= 1'b0; ch_start <= 1'b0; ch_ev <= 1'b0; ch_wend <= 1'b0; rp_v <= 1'b0; lw <= 1'b0; rw <= 1'b0; dw <= 1'b0; j_dump <= 1'b0; wsw <= 1'b0;
        // results RAM: a word of the selected array (priority) or a held judge result is written; a judge result that cannot be held, or any record beyond the end, is counted as lost
        if ((arec || jh_v) && rcount < (16'd1 << RA)) begin
            rw <= 1'b1; rwa <= rcount[RA-1:0]; rcount <= rcount + 1'b1;
            rwd <= arec ? {rcount[7:0], raw, otk, 1'b0, sel, 2'b00, orw} : {rcount[7:0], jh_d, 16'd0, 1'b1, sel, 2'b00, 3'd0};
        end
        if (!arec && jh_v) jh_v <= 1'b0;
        if (j_ov && rec_en && por == 0 && (!jh_v || !arec)) begin jh_v <= 1'b1; jh_d <= j_od; end
        if (rdrop_a || rdrop_j) rlost <= (rlost >= 8'd254) ? 8'hff : rlost + (rdrop_a ? 8'd1 : 8'd0) + (rdrop_j ? 8'd1 : 8'd0);
        // judge side: results in, words from the array in (AFTER mode)
        if (por == 0) begin       // not before the judge has been reset (its outputs are unknown until then)
        if (j_ov) begin if (rqn < 8) begin rq[rqw] <= j_od; rqw <= rqw + 1'b1; end end
            if (automode && ovs) begin
                if (afn < 4) begin af[afw] <= clampbins(raw); afw <= afw + 1'b1; end else if (lost != 8'hff) lost <= lost + 1'b1;
            end
            if (j_ack && !jhost && !wl_v && afn != 0) begin afr <= afr + 1'b1; end
            afn <= afn + ((automode && ovs && afn < 4) ? 3'd1 : 3'd0) - ((j_ack && !jhost && !wl_v && afn != 0) ? 3'd1 : 3'd0);
            rqn <= rqn + ((j_ov && rqn < 8) ? 4'd1 : 4'd0);
        end
        // chain results into their queue
        if (por == 0 && cv_ov && !grun) begin if (cqn < 8) begin cq[cqw] <= cv_word; cqw <= cqw + 1'b1; end else if (clost != 8'hff) clost <= clost + 1'b1; end
        cqn <= cqn + ((por == 0 && cv_ov && !grun && cqn < 8) ? 4'd1 : 4'd0) - ((cs == IDLE && mine && rx_d == 8'h75 && cqn != 0) ? 4'd1 : 4'd0);
        case (cs)
            IDLE: if (mine) case (rx_d)
                8'h6b: begin kb <= 0; cs <= KARG; end
                8'h77: cs <= EM1;
                8'h67: cs <= GR1;
                8'h76: cs <= CV1;
                8'h65: cs <= EN1;
                8'h75: begin
                    rbuf <= {clost, (cqn != 0) ? cq[cqr] : 32'd0, 4'd0, cqn};
                    if (cqn != 0) cqr <= cqr + 1'b1;
                    rn <= 6; ri <= 0; cs <= REPLY;
                end
                8'h41: cs <= ARGA;
                8'h4e: begin rbuf <= {8'd4, NARR[7:0], 8'h42, 8'h41, 8'h53, 8'h45}; rn <= 6; ri <= 0; cs <= REPLY; end
                8'h50: cs <= ARGPS;
                8'h51: cs <= ARGQ;
                8'h4a: begin jn <= 0; cs <= ARGJ; end
                8'h4d: cs <= ARGM;
                8'h43: cs <= ARGC1;
                8'h55: begin rbuf <= {32'd0, nchoice, 6'd0, lastslot}; rn <= 2; ri <= 0; cs <= REPLY; end
                8'h58: cs <= ARGX;
                8'h54: cs <= TA1;
                8'h4f: cs <= ARGO;
                8'h46: cs <= ARGF;
                8'h45: cs <= ARGE1;
                8'h72: cs <= AR1;
                8'h48: cs <= HA1;
                8'h59: begin rbuf <= {gref, rrp, 6'd0, rec_en, rfull, rlost, rcount}; rn <= 7; ri <= 0; cs <= REPLY; end
                8'h56: cs <= ARGV;
                8'h47: cs <= ARGG;
                8'h5a: begin
                    if (rqn == 0) begin rbuf[7:0] <= 8'h45; rn <= 1; ri <= 0; cs <= REPLY; end
                    else begin
                        cnew = rq[rqr][31] ? ch1 : ch0; lastslot <= cnew; if (nchoice != 8'hff) nchoice <= nchoice + 1'b1;
                        rqr <= rqr + 1'b1; rqn <= rqn - 1'b1 + ((j_ov && rqn < 8) ? 4'd1 : 4'd0);
                        qslot <= cnew; qi <= 0; qb <= 0; rc <= 0; laddr <= {cnew, 8'd0};
                        if (wixv[3*cnew+2]) begin wl_set <= wixv[3*cnew +: 2]; wl_k <= 0; wl_then_q <= 1'b1; cs <= WLA; end else cs <= QRUN;
                    end
                end
                8'h52: begin
                    rbuf <= {lost, (rqn != 0) ? rq[rqr] : 32'd0, 4'd0, rqn};
                    if (rqn != 0) begin rqr <= rqr + 1'b1; rqn <= rqn - 1'b1 + ((j_ov && rqn < 8) ? 4'd1 : 4'd0); end
                    rn <= 6; ri <= 0; cs <= REPLY;
                end
                default: ;
            endcase
            KARG: if (rx_v) begin
                kb <= kb + 1'b1;
                case (kb)
                    4'd0: ch_sel <= rx_d[2:0];
                    4'd1: ch_addr[15:8] <= rx_d;
                    4'd2: ch_addr[7:0] <= rx_d;
                    default: ch_data[8*(kb-3) +: 8] <= rx_d;
                endcase
                if (kb == 4'd12) begin if (ch_sel == 3'd7) ch_start <= 1'b1; else ch_we <= 1'b1; reply_k; end
            end
            EN1: if (rx_v) begin en[15:8] <= rx_d; cs <= EN2; end
            EN2: if (rx_v) begin en[7:0] <= rx_d; if ({en[15:8], rx_d} == 16'd0) reply_k; else cs <= EDAT; end
            EDAT: if (rx_v) begin
                if (rx_d == 8'hff) ch_wend <= 1'b1; else begin ch_ev <= 1'b1; ch_idx <= rx_d; end
                en <= en - 1'b1; if (en == 16'd1) reply_k;
            end
            EM1: if (rx_v) begin ea_a[15:8] <= rx_d; cs <= EM2; end
            EM2: if (rx_v) begin ea_a[7:0] <= rx_d; cs <= EM3; end
            EM3: if (rx_v) begin ea_n[15:8] <= rx_d; cs <= EM4; end
            EM4: if (rx_v) begin ea_n[7:0] <= rx_d; if ({ea_n[15:8], rx_d} == 16'd0) reply_k; else cs <= EMD; end
            EMD: if (rx_v) begin
                eww <= 1'b1; ewa <= ea_a[EA-1:0]; ewd <= rx_d; ea_a <= ea_a + 1'b1; ea_n <= ea_n - 1'b1;
                if (ea_n == 16'd1) reply_k;
            end
            GR1: if (rx_v) begin ea_a[15:8] <= rx_d; cs <= GR2; end
            GR2: if (rx_v) begin ea_a[7:0] <= rx_d; cs <= GR3; end
            GR3: if (rx_v) begin ea_n[15:8] <= rx_d; cs <= GR4; end
            GR4: if (rx_v) begin ea_n[7:0] <= rx_d; eaddr <= ea_a[EA-1:0]; grun <= 1'b1; gclk <= 0; gcnt <= 0; gstat <= 8'h4b; cs <= GRP; end
            GRP: begin eaddr <= eaddr + 1'b1; cs <= GRUN; end            // evq now shows the byte to handle, eaddr points one ahead: an event per clock while GRUN lasts
            GRUN: if (ea_n == 16'd0) cs <= GRFIN;
                  else begin
                      ea_n <= ea_n - 1'b1;
                      if (evq == 8'hff) begin gw <= 2'd2; cs <= GRW; end
                      else if (evq == 8'hfe) begin ch_start <= 1'b1; gw <= 2'd1; cs <= GRS; end
                      else begin ch_ev <= 1'b1; ch_idx <= evq; eaddr <= eaddr + 1'b1; end
                  end
            GRW: if (gw != 0) gw <= gw - 1'b1; else begin ch_wend <= 1'b1; gto <= 0; cs <= GROUT; end
            GROUT: begin
                gto <= gto + 1'b1;
                if (cv_ov) begin
                    if (gcnt < 16'd2048) begin crww <= 1'b1; crwa <= gcnt[10:0]; crwd <= cv_word; end
                    gcnt <= gcnt + 1'b1; gw <= 2'd1; cs <= GRS;
                end else if (gto == 8'hff) begin gstat <= 8'h45; cs <= GRFIN; end
            end
            GRS: if (gw != 0) gw <= gw - 1'b1; else cs <= GRP;
            GRFIN: begin grun <= 1'b0; rbuf <= {8'd0, gcnt, gclk, gstat}; rn <= 7; ri <= 0; cs <= REPLY; end
            CV1: if (rx_v) begin cva[15:8] <= rx_d; cs <= CV2; end
            CV2: if (rx_v) begin cva[7:0] <= rx_d; cs <= CV3; end
            CV3: if (rx_v) begin cvn <= rx_d; craddr <= cva[10:0]; cvw <= 4'd4; cvi <= 0; cs <= (rx_d == 8'd0) ? IDLE : CVW; end
            CVW: if (cvw != 0) cvw <= cvw - 1'b1; else cs <= CVS;
            CVS: if (!tx_b && !c_go) begin
                c_d <= crq[8*cvi +: 8]; c_go <= 1'b1;
                if (cvi == 2'd3) begin cvi <= 0; cvn <= cvn - 1'b1; cva <= cva + 1'b1; craddr <= cva[10:0] + 11'd1; cvw <= 4'd4; cs <= (cvn == 8'd1) ? IDLE : CVW; end
                else cvi <= cvi + 1'b1;
            end
            ARGX: if (rx_v) begin
                rec_en <= rx_d[0];
                if (rx_d[1]) begin rcount <= 0; rrp <= 0; rlost <= 0; gref <= 0; jh_v <= 1'b0; rcount <= 0; end
                reply_k;
            end
            ARGG: if (rx_v) begin if (gref != 8'hff) gref <= gref + 1'b1; rbuf[7:0] <= 8'h46; rn <= 1; ri <= 0; cs <= REPLY; end
            ARGV: if (rx_v) begin
                vleft <= (rx_d > rcount - rrp) ? (rcount - rrp) : rx_d; raddr <= rrp[RA-1:0]; vw <= 4'd4; cs <= VHD;
            end
            VHD: if (vw != 0) vw <= vw - 1'b1;
                 else if (!tx_b && !c_go) begin c_d <= vleft; c_go <= 1'b1; vi <= 0; cs <= (vleft == 0) ? IDLE : VSND; end
            VSND: if (!tx_b && !c_go) begin
                c_d <= resq[8*vi[2:0] +: 8]; c_go <= 1'b1;
                if (vi[2:0] == 3'd7) begin
                    vi <= 0; rrp <= rrp + 1'b1; vleft <= vleft - 1'b1; raddr <= rrp[RA-1:0] + 1'b1; vw <= 4'd4;
                    cs <= (vleft == 8'd1) ? IDLE : VWT;
                end else vi <= vi + 1'b1;
            end
            VWT: if (vw != 0) vw <= vw - 1'b1; else cs <= VSND;
            ARGE1: if (rx_v) begin ex_slot <= rx_d; cs <= ARGE2; end
            ARGE2: if (rx_v) begin
                if (ex_slot < 4) wixv[3*ex_slot[1:0] +: 3] <= (rx_d < 4) ? {1'b1, rx_d[1:0]} : 3'b000;
                reply_k;
            end
            ARGO: if (rx_v) begin sv_set <= rx_d[1:0]; sv_k <= 0; sv_to <= 0; j_dump <= 1'b1; cs <= SV1; end
            SV1: begin
                sv_to <= sv_to + 1'b1;
                if (j_dmv) begin wsw <= 1'b1; wsa <= {sv_set, sv_k}; wsd <= j_dmd; sv_k <= sv_k + 1'b1; if (j_dml) reply_k; end
                else if (sv_to == 16'hffff) begin rbuf[7:0] <= 8'h45; rn <= 1; ri <= 0; cs <= REPLY; end
            end
            ARGF: if (rx_v) begin wl_set <= rx_d[1:0]; wl_k <= 0; wl_then_q <= 1'b0; cs <= WLA; end
            WLA: begin wsaddr <= {wl_set, wl_k}; wlw <= 4'd4; cs <= WLB; end
            WLB: if (wlw != 0) wlw <= wlw - 1'b1; else begin wl_d <= wsq; wl_v <= 1'b1; cs <= WLC; end
            WLC: if (j_ack && wl_v) begin
                wl_v <= 1'b0;
                if (wl_k == 9'd256) begin if (wl_then_q) cs <= QRUN; else reply_k; end
                else begin wl_k <= wl_k + 1'b1; cs <= WLA; end
            end
            AR1: if (rx_v) begin rd_set <= rx_d[1:0]; cs <= AR2; end
            AR2: if (rx_v) begin rd_a[15:8] <= rx_d; cs <= AR3; end
            AR3: if (rx_v) begin rd_a[7:0] <= rx_d; cs <= AR4; end
            AR4: if (rx_v) begin rd_left <= rx_d; wsaddr <= {rd_set, rd_a[8:0]}; rd_w <= 4'd4; rd_i <= 0; cs <= (rx_d == 8'd0) ? IDLE : RDW; end
            RDW: if (rd_w != 0) rd_w <= rd_w - 1'b1; else cs <= RDS;
            RDS: if (!tx_b && !c_go) begin
                c_d <= wsq[8*rd_i +: 8]; c_go <= 1'b1;
                if (rd_i == 2'd3) begin rd_i <= 0; rd_left <= rd_left - 1'b1; rd_a <= rd_a + 1'b1; wsaddr <= {rd_set, rd_a[8:0] + 9'd1}; rd_w <= 4'd4; cs <= (rd_left == 8'd1) ? IDLE : RDW; end
                else rd_i <= rd_i + 1'b1;
            end
            TA1: if (rx_v) begin tadr[15:8] <= rx_d; cs <= TA2; end
            TA2: if (rx_v) begin tadr[7:0] <= rx_d; cs <= TN1; end
            TN1: if (rx_v) begin tn[15:8] <= rx_d; cs <= TN2; end
            TN2: if (rx_v) begin tn[7:0] <= rx_d; tb <= 0; if ({tn[15:8], rx_d} == 16'd0) reply_k; else cs <= TDATA; end
            TDATA: if (rx_v) begin
                if (tb != 3'd7) begin tacc[8*tb +: 8] <= rx_d; tb <= tb + 1'b1; end
                else begin dw <= 1'b1; dwa <= tadr[DA-1:0]; dwd <= {rx_d, tacc}; tadr <= tadr + 1'b1; tn <= tn - 1'b1; tb <= 0; if (tn == 16'd1) reply_k; end
            end
            HA1: if (rx_v) begin hadr[15:8] <= rx_d; cs <= HA2; end
            HA2: if (rx_v) begin hadr[7:0] <= rx_d; cs <= HN1; end
            HN1: if (rx_v) begin hn[15:8] <= rx_d; cs <= HN2; end
            HN2: if (rx_v) begin hn[7:0] <= rx_d; hdone <= 0; hrun <= 1'b1; hw <= 4'd4; daddr <= hadr[DA-1:0]; cs <= HFE; end
            HFE: if (hn == 16'd0) begin hstat <= 8'h4b; cs <= HFIN; end
                 else if (hw != 0) hw <= hw - 1'b1;
                 else if (hgo && rec_en && rfull) begin hstat <= 8'h46; cs <= HFIN; end
                 else begin hb <= 0; hrc <= 0; hto <= 0; cs <= HSD; end
            HSD: if (hrc != 0) hrc <= hrc - 1'b1;
                 else begin rp_v <= 1'b1; rp_d <= hbyte; hrc <= 5'd15; if (hb == (hgo ? 3'd1 : 3'd5)) cs <= HWK; else hb <= hb + 1'b1; end
            HWK: begin
                hto <= hto + 1'b1;
                if (fk) begin hwc <= hgo ? datq[23:8] : 16'd0; cs <= HGW; end
                else if (hto == 16'hffff) begin hstat <= 8'h45; cs <= HFIN; end
            end
            HGW: if (hwc != 0) hwc <= hwc - 1'b1;
                 else begin hdone <= hdone + 1'b1; hadr <= hadr + 1'b1; hn <= hn - 1'b1; daddr <= hadr[DA-1:0] + 1'b1; hw <= 4'd4; cs <= HFE; end
            HFIN: begin hrun <= 1'b0; rbuf <= {40'd0, hdone, hstat}; rn <= 3; ri <= 0; cs <= REPLY; end
            ARGC1: if (rx_v) begin ch0 <= rx_d[1:0]; cs <= ARGC2; end
            ARGC2: if (rx_v) begin ch1 <= rx_d[1:0]; reply_k; end
            ARGA: if (rx_v) begin if (rx_d < NARR) sel <= rx_d[1:0]; reply_k; end
            ARGPS: if (rx_v) begin pslot <= rx_d[1:0]; cs <= ARGPH; end
            ARGPH: if (rx_v) begin plen[15:8] <= rx_d; cs <= ARGPL; end
            ARGPL: if (rx_v) begin plen[7:0] <= rx_d; pi <= 0; if ({plen[15:8], rx_d} == 16'd0) reply_k; else cs <= PDATA; end
            PDATA: if (rx_v) begin
                lw <= 1'b1; lwa <= {pslot, pi}; lwd <= rx_d; pi <= pi + 1'b1; plen <= plen - 1'b1;
                if (plen == 16'd1) reply_k;
            end
            ARGQ: if (rx_v) begin qslot <= rx_d[1:0]; qi <= 0; qb <= 0; rc <= 0; laddr <= {rx_d[1:0], 8'd0};
                if (wixv[3*rx_d[1:0]+2]) begin wl_set <= wixv[3*rx_d[1:0] +: 2]; wl_k <= 0; wl_then_q <= 1'b1; cs <= WLA; end else cs <= QRUN;
            end
            QRUN: begin
                if (rc != 0) rc <= rc - 1'b1;
                else if (!qb) begin rp_v <= 1'b1; rp_d <= 8'h42; qb <= 1'b1; rc <= 5'd15; end
                else if (qi < chb_sel) begin rp_v <= 1'b1; rp_d <= libq; qi <= qi + 1'b1; laddr <= {qslot, qi[7:0] + 8'd1}; rc <= 5'd15; end
                else cs <= IDLE;
            end
            ARGJ: if (rx_v) begin jw[8*jn +: 8] <= rx_d; jn <= jn + 1'b1; if (jn == 2'd3) cs <= JWAIT; end
            JWAIT: begin jhost <= 1'b1; if (j_ack && jhost) begin jhost <= 1'b0; reply_k; end end
            ARGM: if (rx_v) begin
                automode <= rx_d[0];
                if (rx_d[1]) begin afn <= 0; afr <= 0; afw <= 0; rqn <= 0; rqr <= 0; rqw <= 0; lost <= 0; end
                reply_k;
            end
            REPLY: if (!tx_b && !c_go) begin
                c_d <= rbuf[8*ri +: 8]; c_go <= 1'b1;
                if (ri == rn - 1) cs <= IDLE; else ri <= ri + 1'b1;
            end
            default: cs <= IDLE;
        endcase
    end
endmodule
`default_nettype wire
