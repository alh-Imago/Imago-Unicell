`timescale 1ns/1ps
// hexn_tier_v3.v -- Four-level key/value store for the Tang Nano 20K: FAST table (block RAM) -> SDRAM (victim level) -> SD CARD (raw sectors, one write-back sector buffer), with a 4-bit presence counter per key bucket (block RAM) in front of the card. New file; hexn_tier_v2.v (fast + bitmap + SDRAM, board-tested) is left untouched. Reference model: tools/hexn_tier_ref_v3.py (bit-true; read its header for the rules: every key lives in exactly one level, a new or promoted key takes its fast slot and the resident moves DOWN, SDRAM slot occupant moves down to the card sector, a get finds the key below and PROMOTES it).
// Alan, 28 Oct 2026: long-term patterns on the card, the faster table built into the design, the next level in the RAM.
// Command: cmd_valid with cmd_flush=0: cmd_we 1 = PUT (key, wdata), 0 = GET (key). cmd_flush=1 writes the sector buffer back to the card (nothing else). busy/done as in v2. Key = KW bits, value = VW bits (KW <= 31, VW <= 32). Requires FB <= KW, SB <= RAMB <= KW, BMB <= KW.
// Entry (SDRAM and card): two 32-bit words: word0 = {1'b1 valid, zeros, hash h} (valid 0 = empty), word1 = value. Card sector = 64 entries (512 bytes): sector index = top SB bits of h, any free entry in the sector (found by a scan from entry 0). SDRAM word address = {slot, 0/1}. Card block number = SD_BASE + sector.
// Start-up: fast table, counters and the 'sector written' bits are cleared by a sweep, then the SDRAM tag words are cleared (2^RAMB writes), the card must be ready. A sector that was never written reads as empty without touching the card.
// WARNING: the card's raw blocks SD_BASE .. SD_BASE + 2^SB - 1 are overwritten as the store fills; use a spare card.
module hexn_tier_v3 #(parameter KW = 18, parameter VW = 18, parameter FB = 10, parameter BMB = 14, parameter RAMB = 12, parameter SB = 8, parameter SD_BASE = 4096, parameter FREQ = 27_000_000, parameter INIT_DIV = 34, parameter FAST_DIV = 1) (
    input  wire clk, input wire clk_sdram, input wire resetn, input wire [2:0] rdlat,
    input  wire cmd_valid, input wire cmd_we, input wire cmd_flush, input wire [KW-1:0] key, input wire [VW-1:0] wdata,
    output reg  busy, output reg done, output reg found, output reg [VW-1:0] rdata, output reg ready,
    output wire [32*17-1:0] cnts,   // fast_hit sdram_hit skip sd_get fp sd_blk_rd sd_blk_wr buf_hit promote_sdram promote_sd demote_sdram demote_sd sd_full found notfound put_update put_new (32 bits each, in this order, first = lowest bits)
    output wire sd_error,
    output wire O_sdram_clk, output wire O_sdram_cke, output wire O_sdram_cs_n, output wire O_sdram_ras_n, output wire O_sdram_cas_n, output wire O_sdram_wen_n,
    inout  wire [31:0] IO_sdram_dq, output wire [10:0] O_sdram_addr, output wire [1:0] O_sdram_ba, output wire [3:0] O_sdram_dqm,
    output wire sd_clk, output wire sd_mosi, input wire sd_miso, output wire sd_cs_n);
    // ---- reversible hash (same as v2) ----
    localparam [31:0] ODD = 32'h9E3779B1 | 32'd1; localparam [31:0] MASK = (32'd1 << KW) - 32'd1; localparam SH = KW / 2;
    function [31:0] hashk(input [31:0] k); reg [31:0] m; begin m = (k * ODD) & MASK; hashk = m ^ (m >> SH); end endfunction
    function [31:0] top(input [31:0] h, input integer nb); begin top = (nb <= KW) ? (h >> (KW - nb)) : h; end endfunction
    // ---- memories ----
    localparam FN = 1 << FB, CN = 1 << BMB, WN = 1 << SB, SN = 1 << RAMB, TG = KW - FB, EWD = 1 + TG + VW;
    reg [EWD-1:0] fmem [0:FN-1]; reg [3:0] cmem [0:CN-1]; reg wmem [0:WN-1]; reg [31:0] sbuf [0:127];
    reg [EWD-1:0] fdata, fwd; reg [3:0] cdata, cwd; reg wdat, wwd; reg [31:0] sbq;
    reg [FB-1:0] fra, fwa; reg fwe; reg [BMB-1:0] cra, cwa; reg cwe; reg [SB-1:0] wra, wwa; reg wwe; reg [6:0] sra, swa; reg swe; reg [31:0] swd;
    wire        sdw_valid; wire [6:0] sdw_index; wire [31:0] sdw_data; wire [6:0] sd_src_addr; reg wr_stream;
    wire        sbwe = sdw_valid | swe; wire [6:0] sbwa = sdw_valid ? sdw_index : swa; wire [31:0] sbwd = sdw_valid ? sdw_data : swd; wire [6:0] sbra = wr_stream ? sd_src_addr : sra;
    always @(posedge clk) begin
        if (fwe) fmem[fwa] <= fwd; fdata <= fmem[fra];
        if (cwe) cmem[cwa] <= cwd; cdata <= cmem[cra];
        if (wwe) wmem[wwa] <= wwd; wdat <= wmem[wra];
        if (sbwe) sbuf[sbwa] <= sbwd; sbq <= sbuf[sbra];
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
        .block_done(card_done), .w_valid(sdw_valid), .w_data(sdw_data), .w_index(sdw_index), .src_addr(sd_src_addr), .src_data(sbq));
    // ---- counters ----
    localparam C_FH = 0, C_SH = 1, C_SK = 2, C_SG = 3, C_FP = 4, C_BR = 5, C_BW = 6, C_BH = 7, C_PS = 8, C_PD = 9, C_DS = 10, C_DD = 11, C_FU = 12, C_FO = 13, C_NF = 14, C_PU = 15, C_PN = 16;
    reg [31:0] c [0:16]; genvar gi; generate for (gi = 0; gi < 17; gi = gi + 1) begin : cg assign cnts[32*gi +: 32] = c[gi]; end endgenerate
    integer ii;
    // ---- state ----
    localparam S_CLR = 0, S_WINIT = 1, S_SWEEP = 2, S_WCARD = 3, S_IDLE = 4, S_F1 = 5, S_F2 = 6, S_SDGO = 7, S_ISS = 8, S_RWAIT = 9,
        S_LOC1 = 10, S_LOC2 = 11, S_LCNT = 12, S_LSC = 13, S_LSE = 14, S_LV1 = 15, S_LV2 = 16, S_LV3 = 17, S_NOTF = 18, S_GOTV = 19,
        S_IF1 = 20, S_IF2 = 21, S_IF3 = 22, S_SR1 = 23, S_SR2 = 24, S_SR3 = 25, S_SR4 = 26, S_SR5 = 27, S_ISD1 = 28, S_ISD2 = 29, S_ISD3 = 30, S_ISD4 = 31, S_ISD5 = 32,
        S_FIN = 33, S_A0 = 34, S_AWR = 35, S_AWRW = 36, S_ARC1 = 37, S_ARC2 = 38, S_ARC3 = 39, S_ARDW = 40, S_ACLR = 41, S_AEND = 42, S_SC0 = 43, S_SC1 = 44, S_SC2 = 45, S_FLU = 46,
        S_CU1 = 47, S_CU2 = 48, S_CU3 = 49;
    reg [5:0] st, nx, acc_ret, scan_ret, cu_ret; reg [31:0] ci; reg we_l, fl_l; reg [KW-1:0] hq, eh, oh, sk; reg [VW-1:0] vq, ev, ov, val; reg [31:0] rdw; reg ovalid;
    reg [20:0] sa; reg sw; reg [31:0] sdat; reg [BMB-1:0] cidx; reg cinc;
    reg cur_valid, dirty; reg [SB-1:0] cur_sec, asec; reg scan_free, sc_found, ff_found; reg [5:0] sc_idx, ff_idx, ai; reg [31:0] hfull;
    wire [31:0] hqz = {{(32-KW){1'b0}}, hq}, ehz = {{(32-KW){1'b0}}, eh};
    wire [SB-1:0] sec_q = top(hqz, SB), sec_e = top(ehz, SB);
    wire [RAMB-1:0] sl_q = top(hqz, RAMB), sl_e = top(ehz, RAMB);
    wire [BMB-1:0] hb_q = hqz[BMB-1:0] ^ top(hqz, BMB), hb_e = ehz[BMB-1:0] ^ top(ehz, BMB);
    wire [FB-1:0] f_e = eh[FB-1:0];
    wire [31:0] tag_e = {1'b1, {(31-KW){1'b0}}, eh};
    always @(posedge clk) begin
        if (!resetn) begin
            st <= S_CLR; ci <= 0; busy <= 1; done <= 0; ready <= 0; found <= 0; rdata <= 0; fwe <= 0; cwe <= 0; wwe <= 0; swe <= 0; sd_valid <= 0; card_rd <= 0; card_wr <= 0; wr_stream <= 0; cur_valid <= 0; dirty <= 0;
            for (ii = 0; ii < 17; ii = ii + 1) c[ii] <= 0;
        end else begin
            done <= 0; fwe <= 0; cwe <= 0; wwe <= 0; swe <= 0; card_rd <= 0; card_wr <= 0;
            case (st)
            S_CLR: begin   // clear fast valid bits, counters, sector-written bits (one sweep over the longest)
                fwe <= (ci < FN); fwa <= ci[FB-1:0]; fwd <= 0; cwe <= (ci < CN); cwa <= ci[BMB-1:0]; cwd <= 0; wwe <= (ci < WN); wwa <= ci[SB-1:0]; wwd <= 0;
                ci <= ci + 1; if (ci == ((FN > CN) ? ((FN > WN) ? FN : WN) : ((CN > WN) ? CN : WN)) - 1) begin st <= S_WINIT; ci <= 0; end
            end
            S_WINIT: if (sd_init) begin st <= S_SWEEP; ci <= 0; end
            S_SWEEP: begin   // clear the SDRAM tag words (even words)
                if (!sd_valid) begin sd_valid <= 1; sd_we <= 1; sd_addr <= {ci[19:0], 1'b0}; sd_wdata <= 0; end
                else if (sd_ready) begin sd_valid <= 0; ci <= ci + 1; if (ci == SN - 1) st <= S_WCARD; end
            end
            S_WCARD: if (card_ready) begin st <= S_IDLE; ready <= 1; busy <= 0; end
            S_IDLE: if (cmd_valid) begin
                busy <= 1; we_l <= cmd_we; fl_l <= cmd_flush; vq <= wdata; found <= 0;
                hfull = hashk({{(32-KW){1'b0}}, key}); hq <= hfull[KW-1:0];
                fra <= hfull[FB-1:0];
                st <= cmd_flush ? S_FLU : S_F1;
            end
            S_FLU: begin   // flush: write the buffer back if it changed
                if (cur_valid && dirty) st <= S_AWR; else st <= S_FIN;
            end
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
                if (rdw[31] && rdw[KW-1:0] == hq) begin   // SDRAM hit: read its value, then clear the tag
                    c[C_SH] <= c[C_SH] + 1; c[C_PS] <= c[C_PS] + 1; sa <= {sl_q, 1'b1}; sw <= 0; nx <= S_LOC2; st <= S_SDGO;
                end else begin cra <= hb_q; st <= S_LCNT; end   // not there: the presence counter decides
            end
            S_LOC2: begin val <= rdw[VW-1:0]; sa <= {sl_q, 1'b0}; sw <= 1; sdat <= 32'd0; nx <= S_GOTV; st <= S_SDGO; end
            S_LCNT: st <= S_LSC;   // wait for the counter read
            S_LSC: begin
                if (cdata == 4'd0) begin c[C_SK] <= c[C_SK] + 1; st <= S_NOTF; end
                else begin c[C_SG] <= c[C_SG] + 1; asec <= sec_q; acc_ret <= S_LSE; st <= S_A0; end
            end
            S_LSE: begin sk <= hq; scan_free <= 0; scan_ret <= S_LV1; ai <= 0; sc_found <= 0; ff_found <= 0; st <= S_SC0; end
            S_LV1: begin
                if (sc_found) begin c[C_PD] <= c[C_PD] + 1; sra <= {sc_idx, 1'b1}; st <= S_LV2; end
                else begin c[C_FP] <= c[C_FP] + 1; st <= S_NOTF; end
            end
            S_LV2: st <= S_LV3;
            S_LV3: begin   // value read; remove the entry from the buffer; decrement the counter
                val <= sbq[VW-1:0]; swe <= 1; swa <= {sc_idx, 1'b0}; swd <= 32'd0; dirty <= 1;
                cidx <= hb_q; cinc <= 0; cu_ret <= S_GOTV; st <= S_CU1;
            end
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
            // ---- demote (oh, ov) into the SDRAM; its previous occupant goes to the card ----
            S_SR1: begin c[C_DS] <= c[C_DS] + 1; eh <= oh; ev <= ov; sa <= {top({{(32-KW){1'b0}}, oh}, RAMB), 1'b0}; sw <= 0; nx <= S_SR2; st <= S_SDGO; end
            S_SR2: begin   // old tag word read (sl_e is the slot of the entry being demoted)
                ovalid <= rdw[31]; oh <= rdw[KW-1:0];
                if (rdw[31]) begin sa <= {sl_e, 1'b1}; sw <= 0; nx <= S_SR3; st <= S_SDGO; end
                else st <= S_SR4;
            end
            S_SR3: begin ov <= rdw[VW-1:0]; st <= S_SR4; end
            S_SR4: begin sa <= {sl_e, 1'b0}; sw <= 1; sdat <= tag_e; nx <= S_SR5; st <= S_SDGO; end
            S_SR5: begin sa <= {sl_e, 1'b1}; sw <= 1; sdat <= {{(32-VW){1'b0}}, ev}; nx <= S_ISD1; st <= S_SDGO; end
            S_ISD1: begin
                if (ovalid) begin eh <= oh; ev <= ov; c[C_DD] <= c[C_DD] + 1; st <= S_ISD2; end
                else st <= S_FIN;
            end
            S_ISD2: begin asec <= sec_e; acc_ret <= S_ISD3; st <= S_A0; end
            S_ISD3: begin sk <= eh; scan_free <= 1; scan_ret <= S_ISD4; ai <= 0; sc_found <= 0; ff_found <= 0; st <= S_SC0; end
            S_ISD4: begin
                if (ff_found) begin swe <= 1; swa <= {ff_idx, 1'b0}; swd <= tag_e; st <= S_ISD5; end
                else begin c[C_FU] <= c[C_FU] + 1; st <= S_FIN; end
            end
            S_ISD5: begin swe <= 1; swa <= {ff_idx, 1'b1}; swd <= {{(32-VW){1'b0}}, ev}; dirty <= 1; cidx <= hb_e; cinc <= 1; cu_ret <= S_FIN; st <= S_CU1; end
            S_FIN: begin busy <= 0; done <= 1; st <= S_IDLE; end
            // ---- presence counter update: cidx, cinc (1 = +1, 0 = -1); a counter at 15 stays (sticky) ----
            S_CU1: begin cra <= cidx; st <= S_CU2; end
            S_CU2: st <= S_CU3;
            S_CU3: begin
                if (cdata != 4'd15) begin
                    if (cinc) begin cwe <= 1; cwa <= cidx; cwd <= cdata + 4'd1; end
                    else if (cdata != 4'd0) begin cwe <= 1; cwa <= cidx; cwd <= cdata - 4'd1; end
                end
                st <= cu_ret;
            end
            // ---- sector buffer access: asec wanted, returns to acc_ret ----
            S_A0: begin
                if (cur_valid && cur_sec == asec) begin c[C_BH] <= c[C_BH] + 1; st <= acc_ret; end
                else if (cur_valid && dirty) st <= S_AWR;
                else st <= S_ARC1;
            end
            S_AWR: begin   // write the buffer back to its card block
                card_blk <= SD_BASE + {{(32-SB){1'b0}}, cur_sec}; card_wr <= 1; wr_stream <= 1; wwe <= 1; wwa <= cur_sec; wwd <= 1; c[C_BW] <= c[C_BW] + 1; st <= S_AWRW;
            end
            S_AWRW: if (card_done) begin wr_stream <= 0; dirty <= 0; st <= fl_l ? S_FIN : S_ARC1; end
            S_ARC1: begin wra <= asec; st <= S_ARC2; end
            S_ARC2: st <= S_ARC3;
            S_ARC3: begin
                if (wdat) begin card_blk <= SD_BASE + {{(32-SB){1'b0}}, asec}; card_rd <= 1; c[C_BR] <= c[C_BR] + 1; st <= S_ARDW; end
                else begin ai <= 0; st <= S_ACLR; end
            end
            S_ARDW: if (card_done) st <= S_AEND;
            S_ACLR: begin swe <= 1; swa <= {ai, 1'b0}; swd <= 32'd0; ai <= ai + 6'd1; if (ai == 6'd63) st <= S_AEND; end
            S_AEND: begin cur_sec <= asec; cur_valid <= 1; dirty <= 0; st <= acc_ret; end
            // ---- scan of the buffer: scan_free 0 = find sk, 1 = first free entry; results sc_found/sc_idx, ff_found/ff_idx ----
            S_SC0: begin sra <= {ai, 1'b0}; st <= S_SC1; end
            S_SC1: st <= S_SC2;
            S_SC2: begin
                if (!scan_free && sbq[31] && sbq[KW-1:0] == sk) begin sc_found <= 1; sc_idx <= ai; st <= scan_ret; end
                else if (scan_free && !sbq[31]) begin ff_found <= 1; ff_idx <= ai; st <= scan_ret; end
                else if (ai == 6'd63) st <= scan_ret;
                else begin ai <= ai + 6'd1; st <= S_SC0; end
            end
            default: st <= S_IDLE;
            endcase
        end
    end
endmodule
