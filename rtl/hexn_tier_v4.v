`timescale 1ns/1ps
// hexn_tier_v4.v -- Four-level key/value store for the Tang Nano 20K: FAST table (block RAM) -> SDRAM victim level -> SD CARD AS A LOG with an exact INDEX in the SDRAM. New file; hexn_tier_v3.v (card level with hashed sectors) and hexn_tier_v2.v (board-tested) are left untouched. Reference model: tools/hexn_tier_ref_v4.py (bit-true; its header states the rules; the comparison that chose the log is tools/hexn_batch_model_v1.py).
// Alan, 28 Oct 2026: long-term patterns on the card, the faster table built into the design, the next level in the RAM; batching first.
// Command: cmd_valid with cmd_flush=0: cmd_we 1 = PUT (key, wdata), 0 = GET (key). cmd_flush=1 writes the open sector to the card as it is. busy/done as in v2/v3. Key = KW bits (<= 20), value = VW bits (<= 32). Requires FB <= KW, RAMB <= KW, 2^(RAMB+1) + 2^KW <= 2^21 SDRAM words.
// SDRAM layout (32-bit words): victim level: slot s at words 2s (tag word {1, hash}) and 2s+1 (value); INDEX: word IDX_BASE + hash = {1'b1, zeros, sector id mod L (LB bits), entry number (6 bits)}, 0 = key not on the card. IDX_BASE = 2^(RAMB+1).
// Card: L = 2^LB blocks used as a circular log starting at block SD_BASE. Open sector = obuf (128 words = 64 entries of tag word + value word); read buffer rbuf holds the last block read (the card's read stream writes it).
// Start-up: fast table valid bits cleared, then the SDRAM tag words (2^RAMB writes) and the index (2^KW writes) cleared, then the card must be ready. About 0.18 s for RAMB 18 plus 0.09 s for KW 18 at 27 MHz.
// WARNING: the card's raw blocks SD_BASE .. SD_BASE + 2^LB - 1 are overwritten; use a spare card.
module hexn_tier_v4 #(parameter KW = 18, parameter VW = 18, parameter FB = 10, parameter RAMB = 12, parameter LB = 8, parameter LOW = 4, parameter SD_BASE = 4096, parameter FREQ = 27_000_000, parameter INIT_DIV = 34, parameter FAST_DIV = 1) (
    input  wire clk, input wire clk_sdram, input wire resetn, input wire [2:0] rdlat,
    input  wire cmd_valid, input wire cmd_we, input wire cmd_flush, input wire [KW-1:0] key, input wire [VW-1:0] wdata,
    output reg  busy, output reg done, output reg found, output reg [VW-1:0] rdata, output reg ready,
    output wire [32*19-1:0] cnts,   // fast_hit sdram_hit skip card_get card_rd card_wr rbuf_hit open_hit promote_sdram promote_card demote_sdram demote_card gc_rd gc_moved log_full found notfound put_update put_new (32 bits each, first = lowest bits)
    output wire sd_error,
    output wire O_sdram_clk, output wire O_sdram_cke, output wire O_sdram_cs_n, output wire O_sdram_ras_n, output wire O_sdram_cas_n, output wire O_sdram_wen_n,
    inout  wire [31:0] IO_sdram_dq, output wire [10:0] O_sdram_addr, output wire [1:0] O_sdram_ba, output wire [3:0] O_sdram_dqm,
    output wire sd_clk, output wire sd_mosi, input wire sd_miso, output wire sd_cs_n);
    // ---- reversible hash (same as v2) ----
    localparam [31:0] ODD = 32'h9E3779B1 | 32'd1; localparam [31:0] MASK = (32'd1 << KW) - 32'd1; localparam SH = KW / 2;
    function [31:0] hashk(input [31:0] k); reg [31:0] m; begin m = (k * ODD) & MASK; hashk = m ^ (m >> SH); end endfunction
    function [31:0] top(input [31:0] h, input integer nb); begin top = (nb <= KW) ? (h >> (KW - nb)) : h; end endfunction
    // ---- memories ----
    localparam FN = 1 << FB, SN = 1 << RAMB, TG = KW - FB, EWD = 1 + TG + VW, L = 1 << LB, IDX_BASE = 1 << (RAMB + 1), CAP = (L - LOW - 2) * 64;
    reg [EWD-1:0] fmem [0:FN-1]; reg [31:0] obuf [0:127]; reg [31:0] rbuf [0:127];
    reg [EWD-1:0] fdata, fwd; reg [31:0] obq, rbq; reg [FB-1:0] fra, fwa; reg fwe; reg [6:0] ora, owa, rra; reg owe; reg [31:0] owd;
    wire        sdw_valid; wire [6:0] sdw_index; wire [31:0] sdw_data; wire [6:0] sd_src_addr; reg wr_stream;
    wire [6:0] obra = wr_stream ? sd_src_addr : ora;
    always @(posedge clk) begin
        if (fwe) fmem[fwa] <= fwd; fdata <= fmem[fra];
        if (owe) obuf[owa] <= owd; obq <= obuf[obra];
        if (sdw_valid) rbuf[sdw_index] <= sdw_data; rbq <= rbuf[rra];
    end
    // ---- SDRAM ----
    reg sd_valid, sd_we; reg [20:0] sd_addr; reg [31:0] sd_wdata; wire sd_ready, sd_rv, sd_init; wire [31:0] sd_rd;
    hexn_sdram_v1 #(.FREQ(FREQ), .CL(3'd2)) sdr (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(rdlat),
        .cmd_valid(sd_valid), .cmd_we(sd_we), .cmd_addr(sd_addr), .cmd_wdata(sd_wdata), .cmd_wmask(4'b1111), .cmd_ready(sd_ready), .rd_valid(sd_rv), .rd_data(sd_rd), .init_done(sd_init),
        .O_sdram_clk(O_sdram_clk), .O_sdram_cke(O_sdram_cke), .O_sdram_cs_n(O_sdram_cs_n), .O_sdram_ras_n(O_sdram_ras_n), .O_sdram_cas_n(O_sdram_cas_n), .O_sdram_wen_n(O_sdram_wen_n),
        .IO_sdram_dq(IO_sdram_dq), .O_sdram_addr(O_sdram_addr), .O_sdram_ba(O_sdram_ba), .O_sdram_dqm(O_sdram_dqm));
    // ---- SD card ----
    reg card_rd, card_wr; reg [31:0] card_blk; wire card_ready, card_busy, card_done; wire [4:0] ec; wire [5:0] ecmd; wire [7:0] erx;
    sd_spi_v1 #(.INIT_DIV(INIT_DIV), .FAST_DIV(FAST_DIV)) card (.clk(clk), .rst(~resetn), .sd_clk(sd_clk), .sd_mosi(sd_mosi), .sd_miso(sd_miso), .sd_cs_n(sd_cs_n),
        .ready(card_ready), .error(sd_error), .err_code(ec), .err_cmd(ecmd), .err_rx(erx), .busy(card_busy), .rd_req(card_rd), .wr_req(card_wr), .block(card_blk),
        .block_done(card_done), .w_valid(sdw_valid), .w_data(sdw_data), .w_index(sdw_index), .src_addr(sd_src_addr), .src_data(obq));
    // ---- counters ----
    localparam C_FH = 0, C_SH = 1, C_SK = 2, C_CG = 3, C_CR = 4, C_CW = 5, C_RH = 6, C_OH = 7, C_PS = 8, C_PC = 9, C_DS = 10, C_DC = 11, C_GR = 12, C_GM = 13, C_LF = 14, C_FO = 15, C_NF = 16, C_PU = 17, C_PN = 18;
    reg [31:0] c [0:18]; genvar gi_; generate for (gi_ = 0; gi_ < 19; gi_ = gi_ + 1) begin : cg assign cnts[32*gi_ +: 32] = c[gi_]; end endgenerate
    integer ii;
    // ---- state ----
    localparam S_CLR = 0, S_WINIT = 1, S_SWEEP = 2, S_WCARD = 3, S_IDLE = 4, S_F1 = 5, S_F2 = 6, S_SDGO = 7, S_ISS = 8, S_RWAIT = 9,
        S_LOC1 = 10, S_LOC2 = 11, S_NOTF = 12, S_GOTV = 13, S_IF1 = 14, S_IF2 = 15, S_IF3 = 16, S_SR1 = 17, S_SR2 = 18, S_SR3 = 19, S_SR4 = 20, S_SR5 = 21, S_ISD1 = 22, S_ISD2 = 23,
        S_FIN = 24, S_FLU = 25, S_FL1 = 26, S_LI0 = 27, S_LI1 = 28, S_LD1 = 29, S_LR1 = 30, S_LR2 = 31, S_LO1 = 32, S_LO2 = 33, S_LX = 34,
        S_AP0 = 35, S_AP1 = 36, S_AP2 = 37, S_AP3 = 38, S_CL0 = 39, S_CL1 = 40, S_CL2 = 41,
        S_GC0 = 42, S_GC1 = 43, S_GC2 = 44, S_GC3 = 45, S_GC4 = 46, S_GC5 = 47, S_GC6 = 48, S_GC7 = 49, S_GC8 = 50, S_GC9 = 51;
    reg [5:0] st, nx, app_ret, close_ret, gc_ret; reg [1:0] swph; reg [31:0] ci; reg we_l, fl_l; reg [KW-1:0] hq, eh, oh, ah, gh; reg [VW-1:0] vq, ev, ov, av, val; reg [31:0] rdw; reg ovalid;
    reg [20:0] sa; reg sw; reg [31:0] sdat; reg [31:0] hfull;
    reg [31:0] open_id, tail, n_live; reg [6:0] n_open; reg open_dirty, rbuf_valid, in_gc; reg [LB-1:0] rbuf_id, lsid, gsid; reg [5:0] lslot; reg [6:0] gi;
    wire [31:0] hqz = {{(32-KW){1'b0}}, hq}, ehz = {{(32-KW){1'b0}}, eh};
    wire [RAMB-1:0] sl_q = top(hqz, RAMB), sl_e = top(ehz, RAMB);
    wire [FB-1:0] f_e = eh[FB-1:0];
    wire [31:0] tag_e = {1'b1, {(31-KW){1'b0}}, eh};
    wire [LB-1:0] sid_open = open_id[LB-1:0];
    wire [31:0] idx_new = {1'b1, {(25-LB){1'b0}}, sid_open, n_open[5:0]};
    wire [31:0] idx_gc = {1'b1, {(25-LB){1'b0}}, gsid, gi[5:0]};
    wire [31:0] log_dist = open_id - tail;
    always @(posedge clk) begin
        if (!resetn) begin
            st <= S_CLR; swph <= 0; ci <= 0; busy <= 1; done <= 0; ready <= 0; found <= 0; rdata <= 0; fwe <= 0; owe <= 0; sd_valid <= 0; card_rd <= 0; card_wr <= 0; wr_stream <= 0;
            open_id <= 0; tail <= 0; n_live <= 0; n_open <= 0; open_dirty <= 0; rbuf_valid <= 0; in_gc <= 0;
            for (ii = 0; ii < 19; ii = ii + 1) c[ii] <= 0;
        end else begin
            done <= 0; fwe <= 0; owe <= 0; card_rd <= 0; card_wr <= 0;
            case (st)
            S_CLR: begin   // clear fast valid bits
                fwe <= 1; fwa <= ci[FB-1:0]; fwd <= 0; ci <= ci + 1; if (ci == FN - 1) begin st <= S_WINIT; ci <= 0; end
            end
            S_WINIT: if (sd_init) begin st <= S_SWEEP; ci <= 0; swph <= 0; end
            S_SWEEP: begin   // phase 0: SDRAM tag words (even words); phase 1: the whole index
                if (!sd_valid) begin sd_valid <= 1; sd_we <= 1; sd_addr <= (swph == 0) ? {ci[19:0], 1'b0} : (IDX_BASE + ci[20:0]); sd_wdata <= 0; end
                else if (sd_ready) begin
                    sd_valid <= 0; ci <= ci + 1;
                    if (swph == 0 && ci == SN - 1) begin swph <= 1; ci <= 0; end
                    else if (swph == 1 && ci == (1 << KW) - 1) st <= S_WCARD;
                end
            end
            S_WCARD: if (card_ready) begin st <= S_IDLE; ready <= 1; busy <= 0; end
            S_IDLE: if (cmd_valid) begin
                busy <= 1; we_l <= cmd_we; fl_l <= cmd_flush; vq <= wdata; found <= 0;
                hfull = hashk({{(32-KW){1'b0}}, key}); hq <= hfull[KW-1:0];
                fra <= hfull[FB-1:0];
                st <= cmd_flush ? S_FLU : S_F1;
            end
            S_FLU: begin   // flush: write the open sector as it is, if it changed
                if (open_dirty && n_open != 0) begin card_blk <= SD_BASE + {{(32-LB){1'b0}}, sid_open}; card_wr <= 1; wr_stream <= 1; c[C_CW] <= c[C_CW] + 1; st <= S_FL1; end
                else st <= S_FIN;
            end
            S_FL1: if (card_done) begin wr_stream <= 0; open_dirty <= 0; if (rbuf_valid && rbuf_id == sid_open) rbuf_valid <= 0; st <= S_FIN; end
            S_F1: st <= S_F2;
            S_F2: begin
                if (fdata[EWD-1] && fdata[EWD-2:VW] == hq[KW-1:FB]) begin
                    if (we_l) begin fwe <= 1; fwa <= hq[FB-1:0]; fwd <= {1'b1, hq[KW-1:FB], vq}; c[C_PU] <= c[C_PU] + 1; st <= S_FIN; end
                    else begin found <= 1; rdata <= fdata[VW-1:0]; c[C_FH] <= c[C_FH] + 1; c[C_FO] <= c[C_FO] + 1; st <= S_FIN; end
                end else begin
                    if (we_l) c[C_PN] <= c[C_PN] + 1;
                    sa <= {sl_q, 1'b0}; sw <= 0; nx <= S_LOC1; st <= S_SDGO;   // look in the SDRAM slot
                end
            end
            // ---- SDRAM word access: caller sets sa, sw, sdat, nx and goes to S_SDGO ----
            S_SDGO: begin sd_valid <= 1; sd_we <= sw; sd_addr <= sa; sd_wdata <= sdat; st <= S_ISS; end
            S_ISS: if (sd_valid && sd_ready) begin sd_valid <= 0; st <= sw ? nx : S_RWAIT; end
            S_RWAIT: if (sd_rv) begin rdw <= sd_rd; st <= nx; end
            // ---- locate below the fast level ----
            S_LOC1: begin
                if (rdw[31] && rdw[KW-1:0] == hq) begin   // SDRAM hit
                    c[C_SH] <= c[C_SH] + 1; c[C_PS] <= c[C_PS] + 1; sa <= {sl_q, 1'b1}; sw <= 0; nx <= S_LOC2; st <= S_SDGO;
                end else st <= S_LI0;   // not there: the index decides
            end
            S_LOC2: begin val <= rdw[VW-1:0]; sa <= {sl_q, 1'b0}; sw <= 1; sdat <= 32'd0; nx <= S_GOTV; st <= S_SDGO; end
            S_LI0: begin sa <= IDX_BASE + hq; sw <= 0; nx <= S_LI1; st <= S_SDGO; end
            S_LI1: begin
                if (!rdw[31]) begin c[C_SK] <= c[C_SK] + 1; st <= S_NOTF; end
                else begin
                    c[C_CG] <= c[C_CG] + 1; lsid <= rdw[6 +: LB]; lslot <= rdw[5:0];
                    if (rdw[6 +: LB] == sid_open) begin c[C_OH] <= c[C_OH] + 1; ora <= {rdw[5:0], 1'b1}; st <= S_LO1; end
                    else if (rbuf_valid && rbuf_id == rdw[6 +: LB]) begin c[C_RH] <= c[C_RH] + 1; rra <= {rdw[5:0], 1'b1}; st <= S_LR1; end
                    else begin card_blk <= SD_BASE + {{(32-LB){1'b0}}, rdw[6 +: LB]}; card_rd <= 1; c[C_CR] <= c[C_CR] + 1; st <= S_LD1; end
                end
            end
            S_LD1: if (card_done) begin rbuf_valid <= 1; rbuf_id <= lsid; rra <= {lslot, 1'b1}; st <= S_LR1; end
            S_LR1: st <= S_LR2;
            S_LR2: begin val <= rbq[VW-1:0]; st <= S_LX; end
            S_LO1: st <= S_LO2;
            S_LO2: begin val <= obq[VW-1:0]; st <= S_LX; end
            S_LX: begin c[C_PC] <= c[C_PC] + 1; n_live <= n_live - 1; sa <= IDX_BASE + hq; sw <= 1; sdat <= 32'd0; nx <= S_GOTV; st <= S_SDGO; end   // promoted: index word cleared
            S_NOTF: begin
                if (we_l) begin eh <= hq; ev <= vq; st <= S_IF1; end
                else begin c[C_NF] <= c[C_NF] + 1; st <= S_FIN; end
            end
            S_GOTV: begin
                if (!we_l) begin found <= 1; rdata <= val; c[C_FO] <= c[C_FO] + 1; end
                eh <= hq; ev <= we_l ? vq : val; st <= S_IF1;
            end
            // ---- insert (eh, ev) into the fast table; the resident moves down ----
            S_IF1: begin fra <= f_e; st <= S_IF2; end
            S_IF2: st <= S_IF3;
            S_IF3: begin
                fwe <= 1; fwa <= f_e; fwd <= {1'b1, eh[KW-1:FB], ev};
                if (fdata[EWD-1]) begin oh <= {fdata[EWD-2:VW], f_e}; ov <= fdata[VW-1:0]; st <= S_SR1; end
                else st <= S_FIN;
            end
            // ---- demote (oh, ov) into the SDRAM; its previous occupant goes to the card log ----
            S_SR1: begin c[C_DS] <= c[C_DS] + 1; eh <= oh; ev <= ov; sa <= {top({{(32-KW){1'b0}}, oh}, RAMB), 1'b0}; sw <= 0; nx <= S_SR2; st <= S_SDGO; end
            S_SR2: begin
                ovalid <= rdw[31]; oh <= rdw[KW-1:0];
                if (rdw[31]) begin sa <= {sl_e, 1'b1}; sw <= 0; nx <= S_SR3; st <= S_SDGO; end
                else st <= S_SR4;
            end
            S_SR3: begin ov <= rdw[VW-1:0]; st <= S_SR4; end
            S_SR4: begin sa <= {sl_e, 1'b0}; sw <= 1; sdat <= tag_e; nx <= S_SR5; st <= S_SDGO; end
            S_SR5: begin sa <= {sl_e, 1'b1}; sw <= 1; sdat <= {{(32-VW){1'b0}}, ev}; nx <= S_ISD1; st <= S_SDGO; end
            S_ISD1: begin
                if (ovalid) begin c[C_DC] <= c[C_DC] + 1; st <= S_ISD2; end
                else st <= S_FIN;
            end
            S_ISD2: begin
                if (n_live >= CAP) begin c[C_LF] <= c[C_LF] + 1; st <= S_FIN; end
                else begin n_live <= n_live + 1; ah <= oh; av <= ov; app_ret <= S_FIN; st <= S_AP0; end
            end
            S_FIN: begin busy <= 0; done <= 1; st <= S_IDLE; end
            // ---- append (ah, av) to the open sector; app_ret is where to go next ----
            S_AP0: begin owe <= 1; owa <= {n_open[5:0], 1'b0}; owd <= {1'b1, {(31-KW){1'b0}}, ah}; st <= S_AP1; end
            S_AP1: begin owe <= 1; owa <= {n_open[5:0], 1'b1}; owd <= {{(32-VW){1'b0}}, av}; st <= S_AP2; end
            S_AP2: begin sa <= IDX_BASE + {{(32-KW){1'b0}}, ah}; sw <= 1; sdat <= idx_new; nx <= S_AP3; st <= S_SDGO; end
            S_AP3: begin
                open_dirty <= 1;
                if (n_open == 7'd63) begin close_ret <= app_ret; st <= S_CL0; end   // sector full: write it whole
                else begin n_open <= n_open + 7'd1; st <= app_ret; end
            end
            S_CL0: begin card_blk <= SD_BASE + {{(32-LB){1'b0}}, sid_open}; card_wr <= 1; wr_stream <= 1; c[C_CW] <= c[C_CW] + 1; st <= S_CL1; end
            S_CL1: if (card_done) begin
                wr_stream <= 0; open_dirty <= 0; if (rbuf_valid && rbuf_id == sid_open) rbuf_valid <= 0;
                n_open <= 0; open_id <= open_id + 1; st <= S_CL2;
            end
            S_CL2: begin   // open_id is already the next sector; compaction if the log is short of room (not nested)
                if (!in_gc && log_dist > L - LOW) begin in_gc <= 1; gc_ret <= close_ret; st <= S_GC0; end
                else st <= close_ret;
            end
            // ---- compaction: read the oldest block, re-append the entries whose index word still points at them ----
            S_GC0: begin gsid <= tail[LB-1:0]; tail <= tail + 1; card_blk <= SD_BASE + {{(32-LB){1'b0}}, tail[LB-1:0]}; card_rd <= 1; c[C_CR] <= c[C_CR] + 1; c[C_GR] <= c[C_GR] + 1; st <= S_GC1; end
            S_GC1: if (card_done) begin rbuf_valid <= 1; rbuf_id <= gsid; gi <= 0; st <= S_GC2; end
            S_GC2: begin rra <= {gi[5:0], 1'b0}; st <= S_GC3; end
            S_GC3: st <= S_GC4;
            S_GC4: begin
                if (rbq[31]) begin gh <= rbq[KW-1:0]; sa <= IDX_BASE + {{(32-KW){1'b0}}, rbq[KW-1:0]}; sw <= 0; nx <= S_GC5; st <= S_SDGO; end
                else st <= S_GC8;
            end
            S_GC5: begin
                if (rdw == idx_gc) begin c[C_GM] <= c[C_GM] + 1; rra <= {gi[5:0], 1'b1}; st <= S_GC6; end
                else st <= S_GC8;
            end
            S_GC6: st <= S_GC7;
            S_GC7: begin ah <= gh; av <= rbq[VW-1:0]; app_ret <= S_GC8; st <= S_AP0; end
            S_GC8: begin if (gi == 7'd63) st <= S_GC9; else begin gi <= gi + 7'd1; st <= S_GC2; end end
            S_GC9: begin
                if (log_dist > L - LOW) st <= S_GC0;
                else begin in_gc <= 0; st <= gc_ret; end
            end
            default: st <= S_IDLE;
            endcase
        end
    end
endmodule
