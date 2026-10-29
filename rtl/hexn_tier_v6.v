`timescale 1ns/1ps
// hexn_tier_v6.v -- clone of hexn_tier_v5.v (v5 untouched). New: parameter EXT_RAM; with EXT_RAM = 1 the RAM level is reached through the ram_* port (same command protocol as hexn_sdram_v1: valid/ready, read answers with rv/rd, 21-bit word address, 32-bit words) and no SDRAM controller is built in; EXT_RAM = 0 behaves exactly like v5. For the Kintex card the port is served by hexn_ddr3_port_v1 (UberDDR3, Wishbone).
// hexn_tier_v6.v -- v4 plus the card format of tools/hexn_tier_ref_v5.py: log blocks with a 16-byte header and a CRC16, 62 entries per block, TOMBSTONES on promotion from the card, SAVE (drain the fast and SDRAM levels into the log) and RESTORE BY SCAN (rebuild the index from the card alone). New file; hexn_tier_v4.v is left untouched. Reference model (bit-true, counters and card bytes): tools/hexn_tier_ref_v5.py.
// Alan, 28 Oct 2026: index cached/saved on the card, models and data kept apart (volume id in every block), loaded images later.
// Commands (cmd_valid with one of): cmd_save 1 = SAVE (every fast and SDRAM entry goes down into the log, then the open sector is written); cmd_restore 1 = RESTORE (only valid straight after reset: the SDRAM index is empty then); cmd_flush 1 = write the open sector as it is; otherwise cmd_we 1 = PUT (key, wdata), 0 = GET (key). busy/done as in v4.
// Card block (512 bytes = 128 little-endian words): word 0 = {sequence[23:0], volume id}; word 1 = {version 1, entry count, sequence[39:32] = 0, sequence[31:24]}; word 2 = {CRC16, magic 0x4858}; word 3 = 0; then 62 entries of two words: tag {live, tombstone, zeros, key hash} and value. Sequence = log position + 1 (a 32-bit counter here; the high byte is written as 0 and a block with a non-zero high byte is taken as invalid). Block position = (sequence - 1) mod L. CRC16-CCITT (init FFFF) over the 512 bytes with the CRC field zero, computed here a word at a time.
// SDRAM layout, index, victim level, rules: as v4. Index word = {1, zeros, sector id mod L (LB bits), entry number (6 bits, 0 to 61)}.
// Restore: pass 1 reads all L blocks and notes which are valid (valid bitmap in block RAM) and the lowest and highest sequence; pass 2 reads the valid blocks from the lowest sequence on (cyclic order of position) and replays them (live entry sets an index word, tombstone clears it); then open id = highest sequence, tail = lowest sequence - 1, and the usual compaction runs if the log is short of room. LOW must be at least 3.
// WARNING: the card's raw blocks SD_BASE .. SD_BASE + 2^LB - 1 are overwritten; use a spare card.
module hexn_tier_v6 #(parameter KW = 18, parameter VW = 18, parameter FB = 10, parameter RAMB = 12, parameter LB = 8, parameter LOW = 4, parameter VOL = 1, parameter SD_BASE = 4096, parameter FREQ = 27_000_000, parameter INIT_DIV = 34, parameter FAST_DIV = 1, parameter EXT_RAM = 0) (
    input  wire clk, input wire clk_sdram, input wire resetn, input wire [2:0] rdlat,
    input  wire cmd_valid, input wire cmd_we, input wire cmd_flush, input wire cmd_save, input wire cmd_restore, input wire [KW-1:0] key, input wire [VW-1:0] wdata,
    output reg  busy, output reg done, output reg found, output reg [VW-1:0] rdata, output reg ready,
    output wire [32*27-1:0] cnts,   // v4's 19 (fast_hit sdram_hit skip card_get card_rd card_wr rbuf_hit open_hit promote_sdram promote_card demote_sdram demote_card gc_rd gc_moved log_full found notfound put_update put_new), then tomb_wr tomb_dropped scan_rd replay_live replay_tomb bad_blocks drain_fast drain_sdram (32 bits each, first = lowest bits)
    output wire sd_error,
    output wire O_sdram_clk, output wire O_sdram_cke, output wire O_sdram_cs_n, output wire O_sdram_ras_n, output wire O_sdram_cas_n, output wire O_sdram_wen_n,
    inout  wire [31:0] IO_sdram_dq, output wire [10:0] O_sdram_addr, output wire [1:0] O_sdram_ba, output wire [3:0] O_sdram_dqm,
    output wire sd_clk, output wire sd_mosi, input wire sd_miso, output wire sd_cs_n,
    output wire ram_valid, output wire ram_we, output wire [20:0] ram_addr, output wire [31:0] ram_wdata, input wire ram_ready, input wire ram_rv, input wire [31:0] ram_rd, input wire ram_init);   // EXT_RAM=1: the RAM level is reached through this port (same protocol as hexn_sdram_v1) instead of the Tang's own SDRAM controller
    localparam [31:0] ODD = 32'h9E3779B1 | 32'd1; localparam [31:0] MASK = (32'd1 << KW) - 32'd1; localparam SH = KW / 2;
    function [31:0] hashk(input [31:0] k); reg [31:0] m; begin m = (k * ODD) & MASK; hashk = m ^ (m >> SH); end endfunction
    function [31:0] top(input [31:0] h, input integer nb); begin top = (nb <= KW) ? (h >> (KW - nb)) : h; end endfunction
    function [15:0] crc16w(input [15:0] cin, input [31:0] w);   // CRC16-CCITT over the 4 bytes of a little-endian word, lowest byte first
        integer b, k; reg [15:0] x;
        begin x = cin; for (b = 0; b < 4; b = b + 1) begin x = x ^ {w[8*b +: 8], 8'h00}; for (k = 0; k < 8; k = k + 1) x = x[15] ? ((x << 1) ^ 16'h1021) : (x << 1); end crc16w = x; end
    endfunction
    localparam FN = 1 << FB, SN = 1 << RAMB, TG = KW - FB, EWD = 1 + TG + VW, L = 1 << LB, IDX_BASE = 1 << (RAMB + 1), EPB = 62, CAP = (L - LOW - 2) * EPB; localparam [7:0] VOLB = VOL;
    reg [EWD-1:0] fmem [0:FN-1]; reg [31:0] obuf [0:127]; reg [31:0] rbuf [0:127]; reg vmap [0:L-1];
    reg [EWD-1:0] fdata, fwd; reg [31:0] obq, rbq; reg [FB-1:0] fra, fwa; reg fwe; reg [6:0] ora, owa, rra; reg owe; reg [31:0] owd;
    reg vmq, vmw, vmwd; reg [LB-1:0] vma, vmwa;
    wire        sdw_valid; wire [6:0] sdw_index; wire [31:0] sdw_data; wire [6:0] sd_src_addr; reg wr_stream;
    wire [6:0] obra = wr_stream ? sd_src_addr : ora;
    always @(posedge clk) begin
        if (fwe) fmem[fwa] <= fwd; fdata <= fmem[fra];
        if (owe) obuf[owa] <= owd; obq <= obuf[obra];
        if (sdw_valid) rbuf[sdw_index] <= sdw_data; rbq <= rbuf[rra];
        if (vmw) vmap[vmwa] <= vmwd; vmq <= vmap[vma];
    end
    reg sd_valid, sd_we; reg [20:0] sd_addr; reg [31:0] sd_wdata; wire sd_ready, sd_rv, sd_init; wire [31:0] sd_rd;
    assign ram_valid = sd_valid; assign ram_we = sd_we; assign ram_addr = sd_addr; assign ram_wdata = sd_wdata;
    generate if (EXT_RAM == 0) begin : g_sdr
        hexn_sdram_v1 #(.FREQ(FREQ), .CL(3'd2)) sdr (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(rdlat),
            .cmd_valid(sd_valid), .cmd_we(sd_we), .cmd_addr(sd_addr), .cmd_wdata(sd_wdata), .cmd_wmask(4'b1111), .cmd_ready(sd_ready), .rd_valid(sd_rv), .rd_data(sd_rd), .init_done(sd_init),
            .O_sdram_clk(O_sdram_clk), .O_sdram_cke(O_sdram_cke), .O_sdram_cs_n(O_sdram_cs_n), .O_sdram_ras_n(O_sdram_ras_n), .O_sdram_cas_n(O_sdram_cas_n), .O_sdram_wen_n(O_sdram_wen_n),
            .IO_sdram_dq(IO_sdram_dq), .O_sdram_addr(O_sdram_addr), .O_sdram_ba(O_sdram_ba), .O_sdram_dqm(O_sdram_dqm));
    end else begin : g_ext
        assign sd_ready = ram_ready; assign sd_rv = ram_rv; assign sd_rd = ram_rd; assign sd_init = ram_init;
        assign O_sdram_clk = 1'b0; assign O_sdram_cke = 1'b0; assign O_sdram_cs_n = 1'b1; assign O_sdram_ras_n = 1'b1; assign O_sdram_cas_n = 1'b1; assign O_sdram_wen_n = 1'b1;
        assign IO_sdram_dq = 32'bz; assign O_sdram_addr = 11'd0; assign O_sdram_ba = 2'd0; assign O_sdram_dqm = 4'd0;
    end endgenerate
    reg card_rd, card_wr; reg [31:0] card_blk; wire card_ready, card_busy, card_done; wire [4:0] ec; wire [5:0] ecmd; wire [7:0] erx;
    sd_spi_v1 #(.INIT_DIV(INIT_DIV), .FAST_DIV(FAST_DIV)) card (.clk(clk), .rst(~resetn), .sd_clk(sd_clk), .sd_mosi(sd_mosi), .sd_miso(sd_miso), .sd_cs_n(sd_cs_n),
        .ready(card_ready), .error(sd_error), .err_code(ec), .err_cmd(ecmd), .err_rx(erx), .busy(card_busy), .rd_req(card_rd), .wr_req(card_wr), .block(card_blk),
        .block_done(card_done), .w_valid(sdw_valid), .w_data(sdw_data), .w_index(sdw_index), .src_addr(sd_src_addr), .src_data(obq));
    localparam C_FH = 0, C_SH = 1, C_SK = 2, C_CG = 3, C_CR = 4, C_CW = 5, C_RH = 6, C_OH = 7, C_PS = 8, C_PC = 9, C_DS = 10, C_DC = 11, C_GR = 12, C_GM = 13, C_LF = 14, C_FO = 15, C_NF = 16, C_PU = 17, C_PN = 18,
        C_TW = 19, C_TD = 20, C_SR = 21, C_RL = 22, C_RT = 23, C_BB = 24, C_DF = 25, C_DSD = 26;
    reg [31:0] c [0:26]; genvar gi_; generate for (gi_ = 0; gi_ < 27; gi_ = gi_ + 1) begin : cg assign cnts[32*gi_ +: 32] = c[gi_]; end endgenerate
    integer ii;
    localparam S_CLR = 0, S_WINIT = 1, S_SWEEP = 2, S_WCARD = 3, S_IDLE = 4, S_F1 = 5, S_F2 = 6, S_SDGO = 7, S_ISS = 8, S_RWAIT = 9,
        S_LOC1 = 10, S_LOC2 = 11, S_NOTF = 12, S_GOTV = 13, S_IF1 = 14, S_IF2 = 15, S_IF3 = 16, S_SR1 = 17, S_SR2 = 18, S_SR3 = 19, S_SR4 = 20, S_SR5 = 21, S_ISD1 = 22, S_ISD2 = 23,
        S_FIN = 24, S_FLU = 25, S_FL1 = 26, S_LI0 = 27, S_LI1 = 28, S_LD1 = 29, S_LR1 = 30, S_LR2 = 31, S_LO1 = 32, S_LO2 = 33, S_LX = 34,
        S_AP0 = 35, S_AP1 = 36, S_AP2 = 37, S_AP3 = 38, S_CL0 = 39, S_CL1 = 40, S_CL2 = 41,
        S_GC0 = 42, S_GC1 = 43, S_GC2 = 44, S_GC3 = 45, S_GC4 = 46, S_GC5 = 47, S_GC6 = 48, S_GC7 = 49, S_GC8 = 50, S_GC9 = 51, S_GC1B = 52,
        S_TB0 = 53, S_TB1 = 54, S_TB2 = 55,
        S_SE0 = 56, S_SE1 = 57, S_SE2 = 58, S_SE3 = 59, S_SE4 = 60, S_SE5 = 61, S_SE6 = 62, S_SE6B = 63, S_SE6C = 64, S_SE8 = 65, S_SE9 = 66, S_SE10 = 67,
        S_CK0 = 68, S_CK1 = 69, S_CK2 = 70, S_CK3 = 71, S_CK4 = 72,
        S_RS0 = 73, S_RS1 = 74, S_RS2 = 75, S_RS3 = 76, S_RS4 = 77, S_RS5 = 78, S_RS5B = 79, S_RS5C = 80, S_RS6 = 81, S_RS7 = 82, S_RS7A = 83, S_RS7B = 84, S_RS8 = 85, S_RS8A = 86, S_RS8B = 87, S_RS9 = 88, S_RSE = 89, S_RSN = 90, S_RS10 = 91, S_RS11 = 92,
        S_SV0 = 93, S_SV1 = 94, S_SV2 = 95, S_SV3 = 96, S_SV4 = 97, S_SV5 = 98, S_SV6 = 99, S_SV7 = 100, S_SV8 = 101, S_SV10 = 102;
    reg [6:0] st, nx, app_ret, close_ret, gc_ret, seal_ret, ck_ret, sv_ret; reg [1:0] swph; reg [31:0] ci; reg we_l, fl_l; reg [KW-1:0] hq, eh, oh, ah, gh; reg [VW-1:0] vq, ev, ov, av, val; reg [31:0] rdw; reg ovalid;
    reg [20:0] sa; reg sw; reg [31:0] sdat; reg [31:0] hfull;
    reg [31:0] open_id, tail, n_live; reg [6:0] n_open; reg open_dirty, rbuf_valid, in_gc; reg [LB-1:0] rbuf_id, lsid, gsid; reg [5:0] lslot; reg [6:0] gi; reg [7:0] gcnt;
    reg [7:0] seal_cnt, zi; reg [15:0] crc;
    reg [7:0] ck_i, ck_vol, ck_cnt, ck_ver, ck_seq8; reg [15:0] ck_crc, ck_mag, ck_stored; reg [31:0] ck_seq; reg ck_ok; reg [LB-1:0] ck_pos;
    reg [31:0] n_valid, min_seq, max_seq, rs_k; reg [LB-1:0] rs_p; reg [7:0] rs_cnt; reg [6:0] ei; reg [31:0] rs_tag; reg [KW-1:0] rs_h;
    reg [31:0] sv_i; reg [KW-1:0] sv_h; reg [VW-1:0] sv_v;
    wire [31:0] hqz = {{(32-KW){1'b0}}, hq}, ehz = {{(32-KW){1'b0}}, eh};
    wire [RAMB-1:0] sl_q = top(hqz, RAMB), sl_e = top(ehz, RAMB);
    wire [FB-1:0] f_e = eh[FB-1:0];
    wire [31:0] tag_e = {1'b1, {(31-KW){1'b0}}, eh};
    wire [LB-1:0] sid_open = open_id[LB-1:0];
    wire [31:0] idx_new = {1'b1, {(25-LB){1'b0}}, sid_open, n_open[5:0]};
    wire [31:0] idx_gc = {1'b1, {(25-LB){1'b0}}, gsid, gi[5:0]};
    wire [31:0] log_dist = open_id - tail;
    wire [31:0] seq_now = open_id + 32'd1, seq_m1 = ck_seq - 32'd1, min_m1 = min_seq - 32'd1;
    wire [5:0] n_open_w = n_open[5:0] + 6'd2;   // word pair of the next entry: words 4 + 2n
    always @(posedge clk) begin
        if (!resetn) begin
            st <= S_CLR; swph <= 0; ci <= 0; busy <= 1; done <= 0; ready <= 0; found <= 0; rdata <= 0; fwe <= 0; owe <= 0; sd_valid <= 0; card_rd <= 0; card_wr <= 0; wr_stream <= 0; vmw <= 0;
            open_id <= 0; tail <= 0; n_live <= 0; n_open <= 0; open_dirty <= 0; rbuf_valid <= 0; in_gc <= 0;
            for (ii = 0; ii < 27; ii = ii + 1) c[ii] <= 0;
        end else begin
            done <= 0; fwe <= 0; owe <= 0; card_rd <= 0; card_wr <= 0; vmw <= 0;
            case (st)
            S_CLR: begin
                fwe <= 1; fwa <= ci[FB-1:0]; fwd <= 0; ci <= ci + 1; if (ci == FN - 1) begin st <= S_WINIT; ci <= 0; end
            end
            S_WINIT: if (sd_init) begin st <= S_SWEEP; ci <= 0; swph <= 0; end
            S_SWEEP: begin
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
                st <= cmd_restore ? S_RS0 : cmd_save ? S_SV0 : cmd_flush ? S_FLU : S_F1;
            end
            S_FLU: begin   // flush: seal and write the open sector as it is, if it changed
                if (open_dirty && n_open != 0) begin seal_cnt <= {1'b0, n_open}; seal_ret <= S_FL1; st <= S_SE0; end
                else st <= S_FIN;
            end
            S_FL1: st <= S_FIN;
            S_F1: st <= S_F2;
            S_F2: begin
                if (fdata[EWD-1] && fdata[EWD-2:VW] == hq[KW-1:FB]) begin
                    if (we_l) begin fwe <= 1; fwa <= hq[FB-1:0]; fwd <= {1'b1, hq[KW-1:FB], vq}; c[C_PU] <= c[C_PU] + 1; st <= S_FIN; end
                    else begin found <= 1; rdata <= fdata[VW-1:0]; c[C_FH] <= c[C_FH] + 1; c[C_FO] <= c[C_FO] + 1; st <= S_FIN; end
                end else begin
                    if (we_l) c[C_PN] <= c[C_PN] + 1;
                    sa <= {sl_q, 1'b0}; sw <= 0; nx <= S_LOC1; st <= S_SDGO;
                end
            end
            S_SDGO: begin sd_valid <= 1; sd_we <= sw; sd_addr <= sa; sd_wdata <= sdat; st <= S_ISS; end
            S_ISS: if (sd_valid && sd_ready) begin sd_valid <= 0; st <= sw ? nx : S_RWAIT; end
            S_RWAIT: if (sd_rv) begin rdw <= sd_rd; st <= nx; end
            S_LOC1: begin
                if (rdw[31] && rdw[KW-1:0] == hq) begin
                    c[C_SH] <= c[C_SH] + 1; c[C_PS] <= c[C_PS] + 1; sa <= {sl_q, 1'b1}; sw <= 0; nx <= S_LOC2; st <= S_SDGO;
                end else st <= S_LI0;
            end
            S_LOC2: begin val <= rdw[VW-1:0]; sa <= {sl_q, 1'b0}; sw <= 1; sdat <= 32'd0; nx <= S_GOTV; st <= S_SDGO; end
            S_LI0: begin sa <= IDX_BASE + hq; sw <= 0; nx <= S_LI1; st <= S_SDGO; end
            S_LI1: begin
                if (!rdw[31]) begin c[C_SK] <= c[C_SK] + 1; st <= S_NOTF; end
                else begin
                    c[C_CG] <= c[C_CG] + 1; lsid <= rdw[6 +: LB]; lslot <= rdw[5:0];
                    if (rdw[6 +: LB] == sid_open) begin c[C_OH] <= c[C_OH] + 1; ora <= {rdw[5:0] + 6'd2, 1'b1}; st <= S_LO1; end
                    else if (rbuf_valid && rbuf_id == rdw[6 +: LB]) begin c[C_RH] <= c[C_RH] + 1; rra <= {rdw[5:0] + 6'd2, 1'b1}; st <= S_LR1; end
                    else begin card_blk <= SD_BASE + {{(32-LB){1'b0}}, rdw[6 +: LB]}; card_rd <= 1; c[C_CR] <= c[C_CR] + 1; st <= S_LD1; end
                end
            end
            S_LD1: if (card_done) begin rbuf_valid <= 1; rbuf_id <= lsid; rra <= {lslot + 6'd2, 1'b1}; st <= S_LR1; end
            S_LR1: st <= S_LR2;
            S_LR2: begin val <= rbq[VW-1:0]; st <= S_LX; end
            S_LO1: st <= S_LO2;
            S_LO2: begin val <= obq[VW-1:0]; st <= S_LX; end
            S_LX: begin c[C_PC] <= c[C_PC] + 1; n_live <= n_live - 1; sa <= IDX_BASE + hq; sw <= 1; sdat <= 32'd0; nx <= S_TB0; st <= S_SDGO; end   // promoted: index word cleared, then a tombstone is appended
            S_TB0: begin owe <= 1; owa <= {n_open_w, 1'b0}; owd <= {1'b0, 1'b1, {(30-KW){1'b0}}, hq}; c[C_TW] <= c[C_TW] + 1; st <= S_TB1; end
            S_TB1: begin owe <= 1; owa <= {n_open_w, 1'b1}; owd <= 32'd0; st <= S_TB2; end
            S_TB2: begin
                open_dirty <= 1;
                if (n_open == EPB - 1) begin close_ret <= S_GOTV; st <= S_CL0; end
                else begin n_open <= n_open + 7'd1; st <= S_GOTV; end
            end
            S_NOTF: begin
                if (we_l) begin eh <= hq; ev <= vq; st <= S_IF1; end
                else begin c[C_NF] <= c[C_NF] + 1; st <= S_FIN; end
            end
            S_GOTV: begin
                if (!we_l) begin found <= 1; rdata <= val; c[C_FO] <= c[C_FO] + 1; end
                eh <= hq; ev <= we_l ? vq : val; st <= S_IF1;
            end
            S_IF1: begin fra <= f_e; st <= S_IF2; end
            S_IF2: st <= S_IF3;
            S_IF3: begin
                fwe <= 1; fwa <= f_e; fwd <= {1'b1, eh[KW-1:FB], ev};
                if (fdata[EWD-1]) begin oh <= {fdata[EWD-2:VW], f_e}; ov <= fdata[VW-1:0]; st <= S_SR1; end
                else st <= S_FIN;
            end
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
            S_AP0: begin owe <= 1; owa <= {n_open_w, 1'b0}; owd <= {1'b1, {(31-KW){1'b0}}, ah}; st <= S_AP1; end
            S_AP1: begin owe <= 1; owa <= {n_open_w, 1'b1}; owd <= {{(32-VW){1'b0}}, av}; st <= S_AP2; end
            S_AP2: begin sa <= IDX_BASE + {{(32-KW){1'b0}}, ah}; sw <= 1; sdat <= idx_new; nx <= S_AP3; st <= S_SDGO; end
            S_AP3: begin
                open_dirty <= 1;
                if (n_open == EPB - 1) begin close_ret <= app_ret; st <= S_CL0; end
                else begin n_open <= n_open + 7'd1; st <= app_ret; end
            end
            S_CL0: begin seal_cnt <= EPB; seal_ret <= S_CL1; st <= S_SE0; end
            S_CL1: begin n_open <= 0; open_id <= open_id + 1; st <= S_CL2; end
            S_CL2: begin
                if (!in_gc && log_dist > L - LOW) begin in_gc <= 1; gc_ret <= close_ret; st <= S_GC0; end
                else st <= close_ret;
            end
            // ---- seal the open sector: zero the unused entries, write the header, CRC16 over the block, write it to the card ----
            S_SE0: begin if (seal_cnt >= EPB) st <= S_SE2; else begin zi <= 8'd4 + {seal_cnt[6:0], 1'b0}; st <= S_SE1; end end
            S_SE1: begin owe <= 1; owa <= zi[6:0]; owd <= 32'd0; zi <= zi + 8'd1; if (zi == 8'd127) st <= S_SE2; end
            S_SE2: begin owe <= 1; owa <= 7'd0; owd <= {seq_now[23:0], VOLB}; st <= S_SE3; end
            S_SE3: begin owe <= 1; owa <= 7'd1; owd <= {8'd1, seal_cnt, 8'h00, seq_now[31:24]}; st <= S_SE4; end
            S_SE4: begin owe <= 1; owa <= 7'd2; owd <= {16'h0000, 16'h4858}; st <= S_SE5; end
            S_SE5: begin owe <= 1; owa <= 7'd3; owd <= 32'd0; zi <= 0; crc <= 16'hFFFF; st <= S_SE6; end
            S_SE6: begin ora <= zi[6:0]; st <= S_SE6B; end
            S_SE6B: st <= S_SE6C;
            S_SE6C: begin crc <= crc16w(crc, obq); if (zi == 8'd127) st <= S_SE8; else begin zi <= zi + 8'd1; st <= S_SE6; end end
            S_SE8: begin owe <= 1; owa <= 7'd2; owd <= {crc, 16'h4858}; st <= S_SE9; end
            S_SE9: begin card_blk <= SD_BASE + {{(32-LB){1'b0}}, sid_open}; card_wr <= 1; wr_stream <= 1; c[C_CW] <= c[C_CW] + 1; st <= S_SE10; end
            S_SE10: if (card_done) begin wr_stream <= 0; open_dirty <= 0; if (rbuf_valid && rbuf_id == sid_open) rbuf_valid <= 0; st <= seal_ret; end
            // ---- check the block in rbuf: magic, version, volume, high sequence byte, count, CRC16, position (ck_pos); result in ck_ok, ck_seq, ck_cnt, ck_mag ----
            S_CK0: begin ck_i <= 0; ck_crc <= 16'hFFFF; st <= S_CK1; end
            S_CK1: begin rra <= ck_i[6:0]; st <= S_CK2; end
            S_CK2: st <= S_CK3;
            S_CK3: begin
                case (ck_i)
                0: begin ck_vol <= rbq[7:0]; ck_seq[23:0] <= rbq[31:8]; ck_crc <= crc16w(ck_crc, rbq); end
                1: begin ck_seq[31:24] <= rbq[7:0]; ck_seq8 <= rbq[15:8]; ck_cnt <= rbq[23:16]; ck_ver <= rbq[31:24]; ck_crc <= crc16w(ck_crc, rbq); end
                2: begin ck_mag <= rbq[15:0]; ck_stored <= rbq[31:16]; ck_crc <= crc16w(ck_crc, {16'h0000, rbq[15:0]}); end
                default: ck_crc <= crc16w(ck_crc, rbq);
                endcase
                if (ck_i == 8'd127) st <= S_CK4; else begin ck_i <= ck_i + 8'd1; st <= S_CK1; end
            end
            S_CK4: begin
                ck_ok <= (ck_mag == 16'h4858) && (ck_ver == 8'd1) && (ck_vol == VOL) && (ck_seq8 == 8'd0) && (ck_cnt <= EPB) && (ck_crc == ck_stored) && (ck_seq != 0) && (seq_m1[LB-1:0] == ck_pos);
                st <= ck_ret;
            end
            // ---- compaction: read the oldest block, check it, re-append the live entries whose index word still points at them, drop tombstones ----
            S_GC0: begin gsid <= tail[LB-1:0]; tail <= tail + 1; card_blk <= SD_BASE + {{(32-LB){1'b0}}, tail[LB-1:0]}; card_rd <= 1; c[C_CR] <= c[C_CR] + 1; c[C_GR] <= c[C_GR] + 1; st <= S_GC1; end
            S_GC1: if (card_done) begin rbuf_valid <= 1; rbuf_id <= gsid; ck_pos <= gsid; ck_ret <= S_GC1B; st <= S_CK0; end
            S_GC1B: begin gi <= 0; gcnt <= ck_cnt; if (ck_ok && ck_cnt != 0) st <= S_GC2; else st <= S_GC9; end
            S_GC2: begin rra <= {gi[5:0] + 6'd2, 1'b0}; st <= S_GC3; end
            S_GC3: st <= S_GC4;
            S_GC4: begin
                if (rbq[31]) begin gh <= rbq[KW-1:0]; sa <= IDX_BASE + {{(32-KW){1'b0}}, rbq[KW-1:0]}; sw <= 0; nx <= S_GC5; st <= S_SDGO; end
                else begin if (rbq[30]) c[C_TD] <= c[C_TD] + 1; st <= S_GC8; end
            end
            S_GC5: begin
                if (rdw == idx_gc) begin c[C_GM] <= c[C_GM] + 1; rra <= {gi[5:0] + 6'd2, 1'b1}; st <= S_GC6; end
                else st <= S_GC8;
            end
            S_GC6: st <= S_GC7;
            S_GC7: begin ah <= gh; av <= rbq[VW-1:0]; app_ret <= S_GC8; st <= S_AP0; end
            S_GC8: begin if ({1'b0, gi} + 8'd1 == gcnt) st <= S_GC9; else begin gi <= gi + 7'd1; st <= S_GC2; end end
            S_GC9: begin
                if (log_dist > L - LOW) st <= S_GC0;
                else begin in_gc <= 0; st <= gc_ret; end
            end
            // ---- RESTORE by scan ----
            S_RS0: begin ci <= 0; n_valid <= 0; min_seq <= 32'hFFFFFFFF; max_seq <= 0; st <= S_RS1; end
            S_RS1: begin card_blk <= SD_BASE + ci; card_rd <= 1; c[C_SR] <= c[C_SR] + 1; st <= S_RS2; end
            S_RS2: if (card_done) begin ck_pos <= ci[LB-1:0]; ck_ret <= S_RS3; st <= S_CK0; end
            S_RS3: begin
                vmw <= 1; vmwa <= ci[LB-1:0]; vmwd <= ck_ok;
                if (ck_ok) begin n_valid <= n_valid + 1; if (ck_seq < min_seq) min_seq <= ck_seq; if (ck_seq > max_seq) max_seq <= ck_seq; end
                else if (ck_mag != 16'h0000) c[C_BB] <= c[C_BB] + 1;
                if (ci == L - 1) st <= S_RS4; else begin ci <= ci + 1; st <= S_RS1; end
            end
            S_RS4: begin if (n_valid == 0) st <= S_FIN; else begin rs_k <= 0; rs_p <= min_m1[LB-1:0]; st <= S_RS5; end end
            S_RS5: begin vma <= rs_p; st <= S_RS5B; end
            S_RS5B: st <= S_RS5C;
            S_RS5C: begin if (vmq) st <= S_RS6; else st <= S_RSN; end
            S_RS6: begin card_blk <= SD_BASE + {{(32-LB){1'b0}}, rs_p}; card_rd <= 1; c[C_SR] <= c[C_SR] + 1; st <= S_RS7; end
            S_RS7: if (card_done) begin rra <= 7'd1; st <= S_RS7A; end
            S_RS7A: st <= S_RS7B;
            S_RS7B: begin rs_cnt <= rbq[23:16]; ei <= 0; if (rbq[23:16] == 8'd0) st <= S_RSN; else st <= S_RS8; end
            S_RS8: begin rra <= {ei[5:0] + 6'd2, 1'b0}; st <= S_RS8A; end
            S_RS8A: st <= S_RS8B;
            S_RS8B: begin
                rs_tag <= rbq; rs_h <= rbq[KW-1:0];
                if (rbq[31] || rbq[30]) begin sa <= IDX_BASE + {{(32-KW){1'b0}}, rbq[KW-1:0]}; sw <= 0; nx <= S_RS9; st <= S_SDGO; end
                else st <= S_RSE;
            end
            S_RS9: begin   // rdw = the index word this key has now
                if (rs_tag[31]) begin
                    c[C_RL] <= c[C_RL] + 1; if (!rdw[31]) n_live <= n_live + 1;
                    sa <= IDX_BASE + {{(32-KW){1'b0}}, rs_h}; sw <= 1; sdat <= {1'b1, {(25-LB){1'b0}}, rs_p, ei[5:0]}; nx <= S_RSE; st <= S_SDGO;
                end else begin
                    c[C_RT] <= c[C_RT] + 1;
                    if (rdw[31]) begin n_live <= n_live - 1; sa <= IDX_BASE + {{(32-KW){1'b0}}, rs_h}; sw <= 1; sdat <= 32'd0; nx <= S_RSE; st <= S_SDGO; end
                    else st <= S_RSE;
                end
            end
            S_RSE: begin if ({1'b0, ei} + 8'd1 == rs_cnt) st <= S_RSN; else begin ei <= ei + 7'd1; st <= S_RS8; end end
            S_RSN: begin if (rs_k == L - 1) st <= S_RS10; else begin rs_k <= rs_k + 1; rs_p <= rs_p + 1; st <= S_RS5; end end
            S_RS10: begin open_id <= max_seq; tail <= min_m1; n_open <= 0; open_dirty <= 0; rbuf_valid <= 0; in_gc <= 1; gc_ret <= S_FIN; st <= S_RS11; end
            S_RS11: begin if (log_dist > L - LOW) st <= S_GC0; else begin in_gc <= 0; st <= S_FIN; end end
            // ---- SAVE: drain the fast table, then the SDRAM victim level, into the log; then flush ----
            S_SV0: begin sv_i <= 0; st <= S_SV1; end
            S_SV1: begin fra <= sv_i[FB-1:0]; st <= S_SV2; end
            S_SV2: st <= S_SV3;
            S_SV3: begin
                if (fdata[EWD-1]) begin
                    sv_h <= {fdata[EWD-2:VW], sv_i[FB-1:0]}; sv_v <= fdata[VW-1:0]; fwe <= 1; fwa <= sv_i[FB-1:0]; fwd <= 0; c[C_DF] <= c[C_DF] + 1; sv_ret <= S_SV5; st <= S_SV4;
                end else st <= S_SV5;
            end
            S_SV4: begin   // insert (sv_h, sv_v) into the card level
                c[C_DC] <= c[C_DC] + 1;
                if (n_live >= CAP) begin c[C_LF] <= c[C_LF] + 1; st <= sv_ret; end
                else begin n_live <= n_live + 1; ah <= sv_h; av <= sv_v; app_ret <= sv_ret; st <= S_AP0; end
            end
            S_SV5: begin if (sv_i == FN - 1) begin sv_i <= 0; st <= S_SV6; end else begin sv_i <= sv_i + 1; st <= S_SV1; end end
            S_SV6: begin sa <= {sv_i[RAMB-1:0], 1'b0}; sw <= 0; nx <= S_SV7; st <= S_SDGO; end
            S_SV7: begin
                if (rdw[31]) begin sv_h <= rdw[KW-1:0]; sa <= {sv_i[RAMB-1:0], 1'b1}; sw <= 0; nx <= S_SV8; st <= S_SDGO; end
                else st <= S_SV10;
            end
            S_SV8: begin sv_v <= rdw[VW-1:0]; sa <= {sv_i[RAMB-1:0], 1'b0}; sw <= 1; sdat <= 32'd0; c[C_DSD] <= c[C_DSD] + 1; sv_ret <= S_SV10; nx <= S_SV4; st <= S_SDGO; end
            S_SV10: begin if (sv_i == SN - 1) st <= S_FLU; else begin sv_i <= sv_i + 1; st <= S_SV6; end end
            default: st <= S_IDLE;
            endcase
        end
    end
endmodule
