`timescale 1ns/1ps
// hexn_tier_v7.v -- Three-level key/value store for the Kintex card: LUT table (level 0) -> block RAM table (level 1) -> DDR3 bucket lines (level 2), with a 4-bit presence counter per key bucket (block RAM) in front of the DDR3. New file; hexn_tier_v3.v (Tang: fast / SDRAM / SD card) is untouched and this file follows its rules.
// Alan, 29 Oct 2026: "local (lut) storage, then bram, then ddr, and the read out from that is what gets read out by the jtag side". Reference model: tools/hexn_tier_ref_v3.py class Tier3 with SPS = 8 (fast = level 0, 'sdram' = level 1, 'sector' = one DDR3 line). Same counters, same moving rules.
// Command (as v3): cmd_valid with cmd_flush=0: cmd_we 1 = PUT (key, wdata), 0 = GET (key). cmd_flush=1 writes the line buffer back to the DDR3 (nothing else). busy/done as v3. Key = KW bits, value = VW bits (KW <= 31, VW <= 32). Requires FB <= KW, SB <= RAMB <= KW, BMB <= KW, SB <= 24.
// Level 2: one DDR3 line = 576 bits = 8 entries of 64 bits (the 512 data bits of the card's UberDDR3 word); entry = word0 {1'b1 valid, zeros, hash h} (valid 0 = empty), word1 = value. Line number = DDR_BASE + top SB bits of h, any free entry in the line. One line buffer with write-back (a line that was never written reads as empty without touching the DDR3).
// DDR3 side: pipelined Wishbone as UberDDR3 (stb held until stall is low at a clock edge; one ack per request; reads answer with wb_rdata in the clock of wb_ack). Whole-line writes only (no byte strobe needed). ddr_err goes 1 (sticky) if an answer does not come within 4096 clocks.
// Start-up: levels 0 and 1, counters and the 'line written' bits are cleared by a sweep; then it waits for ddr_ready. The DDR3 lines DDR_BASE .. DDR_BASE + 2^SB - 1 are used by the store.
module hexn_tier_v7 #(parameter KW = 18, parameter VW = 18, parameter FB = 10, parameter BMB = 14, parameter RAMB = 12, parameter SB = 8, parameter DDR_BASE = 0) (
    input  wire clk, input wire resetn,
    input  wire cmd_valid, input wire cmd_we, input wire cmd_flush, input wire [KW-1:0] key, input wire [VW-1:0] wdata,
    output reg  busy, output reg done, output reg found, output reg [VW-1:0] rdata, output reg ready,
    output wire [32*17-1:0] cnts,   // fast_hit sdram_hit skip sd_get fp sd_blk_rd sd_blk_wr buf_hit promote_sdram promote_sd demote_sdram demote_sd sd_full found notfound put_update put_new (32 bits each, first = lowest bits); here sdram = level 1, sd = DDR3 line
    output reg  ddr_err,
    input  wire ddr_ready,
    output reg  wb_stb, output reg wb_we, output reg [24:0] wb_addr, output reg [575:0] wb_data, input wire wb_stall, input wire wb_ack, input wire [575:0] wb_rdata);
    localparam [31:0] ODD = 32'h9E3779B1 | 32'd1; localparam [31:0] MASK = (32'd1 << KW) - 32'd1; localparam SH = KW / 2;
    function [31:0] hashk(input [31:0] k); reg [31:0] m; begin m = (k * ODD) & MASK; hashk = m ^ (m >> SH); end endfunction
    function [31:0] top(input [31:0] h, input integer nb); begin top = (nb <= KW) ? (h >> (KW - nb)) : h; end endfunction
    // find in a line: {found, index} of the first valid entry with hash t / of the first free entry
    function [3:0] find_tag(input [575:0] b, input [KW-1:0] t); integer i; reg got; begin find_tag = 4'd0; got = 0;
        for (i = 0; i < 8; i = i + 1) if (!got && b[64*i+31] && b[64*i +: KW] == t) begin got = 1; find_tag = {1'b1, i[2:0]}; end end endfunction
    function [3:0] find_free(input [575:0] b); integer i; reg got; begin find_free = 4'd0; got = 0;
        for (i = 0; i < 8; i = i + 1) if (!got && !b[64*i+31]) begin got = 1; find_free = {1'b1, i[2:0]}; end end endfunction
    localparam FN = 1 << FB, CN = 1 << BMB, WN = 1 << SB, MN = 1 << RAMB, TG = KW - FB, EWD = 1 + TG + VW, MWD = 1 + KW + VW;
    reg [EWD-1:0] fmem [0:FN-1]; reg [MWD-1:0] mmem [0:MN-1]; reg [3:0] cmem [0:CN-1]; reg wmem [0:WN-1];
    reg [EWD-1:0] fdata, fwd; reg [MWD-1:0] mdata, mwd; reg [3:0] cdata, cwd; reg wdat, wwd;
    reg [FB-1:0] fra, fwa; reg fwe; reg [RAMB-1:0] mra, mwa; reg mwe; reg [BMB-1:0] cra, cwa; reg cwe; reg [SB-1:0] wra, wwa; reg wwe;
    always @(posedge clk) begin
        if (fwe) fmem[fwa] <= fwd; fdata <= fmem[fra];
        if (mwe) mmem[mwa] <= mwd; mdata <= mmem[mra];
        if (cwe) cmem[cwa] <= cwd; cdata <= cmem[cra];
        if (wwe) wmem[wwa] <= wwd; wdat <= wmem[wra];
    end
    localparam C_FH = 0, C_SH = 1, C_SK = 2, C_SG = 3, C_FP = 4, C_BR = 5, C_BW = 6, C_BH = 7, C_PS = 8, C_PD = 9, C_DS = 10, C_DD = 11, C_FU = 12, C_FO = 13, C_NF = 14, C_PU = 15, C_PN = 16;
    reg [31:0] c [0:16]; genvar gi; generate for (gi = 0; gi < 17; gi = gi + 1) begin : cg assign cnts[32*gi +: 32] = c[gi]; end endgenerate
    integer ii;
    localparam S_CLR = 0, S_WINIT = 1, S_IDLE = 2, S_F1 = 3, S_F2 = 4, S_M1 = 5, S_M2 = 6, S_LCNT = 7, S_LSC = 8, S_LSE = 9, S_NOTF = 10, S_GOTV = 11,
        S_IF1 = 12, S_IF2 = 13, S_IF3 = 14, S_DM1 = 15, S_DM2 = 16, S_DM3 = 17, S_DD2 = 18, S_FIN = 19, S_FLU = 20,
        S_CU1 = 21, S_CU2 = 22, S_CU3 = 23, S_A0 = 24, S_AWR = 25, S_AWQ = 26, S_AWA = 27, S_ARC1 = 28, S_ARC2 = 29, S_ARC3 = 30, S_ARQ = 31, S_ARA = 32, S_AEND = 33;
    reg [5:0] st, acc_ret, cu_ret; reg [31:0] ci; reg we_l, fl_l; reg [KW-1:0] hq, eh, oh; reg [VW-1:0] vq, ev, ov, val;
    reg [BMB-1:0] cidx; reg cinc; reg cur_valid, dirty; reg [SB-1:0] cur_sec, asec; reg [575:0] lbuf; reg [31:0] hfull; reg [12:0] tmo; reg [3:0] ff;
    wire [31:0] hqz = {{(32-KW){1'b0}}, hq}, ehz = {{(32-KW){1'b0}}, eh}, ohz = {{(32-KW){1'b0}}, oh};
    wire [SB-1:0] sec_q = top(hqz, SB), sec_e = top(ehz, SB);
    wire [RAMB-1:0] sl_q = top(hqz, RAMB), sl_o = top(ohz, RAMB);
    wire [BMB-1:0] hb_q = hqz[BMB-1:0] ^ top(hqz, BMB), hb_e = ehz[BMB-1:0] ^ top(ehz, BMB);
    wire [FB-1:0] f_e = eh[FB-1:0];
    wire [3:0] tg = find_tag(lbuf, hq);
    wire [3:0] fr = find_free(lbuf);
    wire [24:0] cur_addr = DDR_BASE + {{(25-SB){1'b0}}, cur_sec}, acc_addr = DDR_BASE + {{(25-SB){1'b0}}, asec};
    wire [31:0] mx = (FN > CN) ? ((FN > WN) ? ((FN > MN) ? FN : MN) : ((WN > MN) ? WN : MN)) : ((CN > WN) ? ((CN > MN) ? CN : MN) : ((WN > MN) ? WN : MN));
    always @(posedge clk) begin
        if (!resetn) begin
            st <= S_CLR; ci <= 0; busy <= 1; done <= 0; ready <= 0; found <= 0; rdata <= 0; fwe <= 0; mwe <= 0; cwe <= 0; wwe <= 0; wb_stb <= 0; wb_we <= 0; wb_addr <= 0; wb_data <= 0; cur_valid <= 0; dirty <= 0; ddr_err <= 0; lbuf <= 0; tmo <= 0;
            for (ii = 0; ii < 17; ii = ii + 1) c[ii] <= 0;
        end else begin
            done <= 0; fwe <= 0; mwe <= 0; cwe <= 0; wwe <= 0;
            if (wb_stb || st == S_AWA || st == S_ARA) tmo <= tmo + 13'd1; else tmo <= 0;
            case (st)
            S_CLR: begin
                fwe <= (ci < FN); fwa <= ci[FB-1:0]; fwd <= 0; mwe <= (ci < MN); mwa <= ci[RAMB-1:0]; mwd <= 0; cwe <= (ci < CN); cwa <= ci[BMB-1:0]; cwd <= 0; wwe <= (ci < WN); wwa <= ci[SB-1:0]; wwd <= 0;
                ci <= ci + 1; if (ci == mx - 1) begin st <= S_WINIT; ci <= 0; end
            end
            S_WINIT: if (ddr_ready) begin st <= S_IDLE; ready <= 1; busy <= 0; end
            S_IDLE: if (cmd_valid) begin
                busy <= 1; we_l <= cmd_we; fl_l <= cmd_flush; vq <= wdata; found <= 0;
                hfull = hashk({{(32-KW){1'b0}}, key}); hq <= hfull[KW-1:0]; fra <= hfull[FB-1:0];
                st <= cmd_flush ? S_FLU : S_F1;
            end
            S_FLU: begin if (cur_valid && dirty) st <= S_AWR; else st <= S_FIN; end
            S_F1: st <= S_F2;
            S_F2: begin
                if (fdata[EWD-1] && fdata[EWD-2:VW] == hq[KW-1:FB]) begin
                    if (we_l) begin fwe <= 1; fwa <= hq[FB-1:0]; fwd <= {1'b1, hq[KW-1:FB], vq}; c[C_PU] <= c[C_PU] + 1; st <= S_FIN; end
                    else begin found <= 1; rdata <= fdata[VW-1:0]; c[C_FH] <= c[C_FH] + 1; c[C_FO] <= c[C_FO] + 1; st <= S_FIN; end
                end else begin
                    if (we_l) c[C_PN] <= c[C_PN] + 1;
                    mra <= sl_q; st <= S_M1;   // look in the level-1 slot
                end
            end
            S_M1: st <= S_M2;
            S_M2: begin
                if (mdata[MWD-1] && mdata[VW +: KW] == hq) begin   // level-1 hit: take the value, clear the slot
                    c[C_SH] <= c[C_SH] + 1; c[C_PS] <= c[C_PS] + 1; val <= mdata[VW-1:0]; mwe <= 1; mwa <= sl_q; mwd <= 0; st <= S_GOTV;
                end else begin cra <= hb_q; st <= S_LCNT; end
            end
            S_LCNT: st <= S_LSC;
            S_LSC: begin
                if (cdata == 4'd0) begin c[C_SK] <= c[C_SK] + 1; st <= S_NOTF; end
                else begin c[C_SG] <= c[C_SG] + 1; asec <= sec_q; acc_ret <= S_LSE; st <= S_A0; end
            end
            S_LSE: begin
                if (tg[3]) begin
                    c[C_PD] <= c[C_PD] + 1; val <= lbuf[64*tg[2:0] + 32 +: VW]; lbuf[64*tg[2:0] +: 64] <= 64'd0; dirty <= 1;
                    cidx <= hb_q; cinc <= 0; cu_ret <= S_GOTV; st <= S_CU1;
                end else begin c[C_FP] <= c[C_FP] + 1; st <= S_NOTF; end
            end
            S_NOTF: begin
                if (we_l) begin eh <= hq; ev <= vq; st <= S_IF1; end
                else begin c[C_NF] <= c[C_NF] + 1; st <= S_FIN; end
            end
            S_GOTV: begin
                if (!we_l) begin found <= 1; rdata <= val; c[C_FO] <= c[C_FO] + 1; end
                eh <= hq; ev <= we_l ? vq : val; st <= S_IF1;
            end
            // insert (eh, ev) into level 0; the resident moves down
            S_IF1: begin fra <= f_e; st <= S_IF2; end
            S_IF2: st <= S_IF3;
            S_IF3: begin
                fwe <= 1; fwa <= f_e; fwd <= {1'b1, eh[KW-1:FB], ev};
                if (fdata[EWD-1]) begin oh <= {fdata[EWD-2:VW], f_e}; ov <= fdata[VW-1:0]; st <= S_DM1; end
                else st <= S_FIN;
            end
            // demote (oh, ov) into level 1; its previous occupant goes to the DDR3 line
            S_DM1: begin c[C_DS] <= c[C_DS] + 1; mra <= sl_o; st <= S_DM2; end
            S_DM2: st <= S_DM3;
            S_DM3: begin
                mwe <= 1; mwa <= sl_o; mwd <= {1'b1, oh, ov};
                if (mdata[MWD-1]) begin eh <= mdata[VW +: KW]; ev <= mdata[VW-1:0]; c[C_DD] <= c[C_DD] + 1; asec <= top({{(32-KW){1'b0}}, mdata[VW +: KW]}, SB); acc_ret <= S_DD2; st <= S_A0; end
                else st <= S_FIN;
            end
            S_DD2: begin
                if (fr[3]) begin lbuf[64*fr[2:0] +: 64] <= {{(32-VW){1'b0}}, ev, 1'b1, {(31-KW){1'b0}}, eh}; dirty <= 1; cidx <= hb_e; cinc <= 1; cu_ret <= S_FIN; st <= S_CU1; end
                else begin c[C_FU] <= c[C_FU] + 1; st <= S_FIN; end
            end
            S_FIN: begin busy <= 0; done <= 1; st <= S_IDLE; end
            // presence counter update: cidx, cinc (1 = +1, 0 = -1); a counter at 15 stays (sticky)
            S_CU1: begin cra <= cidx; st <= S_CU2; end
            S_CU2: st <= S_CU3;
            S_CU3: begin
                if (cdata != 4'd15) begin
                    if (cinc) begin cwe <= 1; cwa <= cidx; cwd <= cdata + 4'd1; end
                    else if (cdata != 4'd0) begin cwe <= 1; cwa <= cidx; cwd <= cdata - 4'd1; end
                end
                st <= cu_ret;
            end
            // line buffer access: asec wanted, returns to acc_ret
            S_A0: begin
                if (cur_valid && cur_sec == asec) begin c[C_BH] <= c[C_BH] + 1; st <= acc_ret; end
                else if (cur_valid && dirty) st <= S_AWR;
                else st <= S_ARC1;
            end
            S_AWR: begin   // write the line buffer back to its DDR3 line
                wb_stb <= 1; wb_we <= 1; wb_addr <= cur_addr; wb_data <= lbuf; wwe <= 1; wwa <= cur_sec; wwd <= 1; c[C_BW] <= c[C_BW] + 1; st <= S_AWQ;
            end
            S_AWQ: begin
                if (!wb_stall) begin wb_stb <= 0; wb_we <= 0; st <= S_AWA; end
                else if (tmo == 13'd4095) begin ddr_err <= 1; wb_stb <= 0; wb_we <= 0; st <= S_FIN; end
            end
            S_AWA: begin
                if (wb_ack) begin dirty <= 0; st <= fl_l ? S_FIN : S_ARC1; end
                else if (tmo == 13'd4095) begin ddr_err <= 1; dirty <= 0; st <= S_FIN; end
            end
            S_ARC1: begin wra <= asec; st <= S_ARC2; end
            S_ARC2: st <= S_ARC3;
            S_ARC3: begin
                if (wdat) begin wb_stb <= 1; wb_we <= 0; wb_addr <= acc_addr; c[C_BR] <= c[C_BR] + 1; st <= S_ARQ; end
                else begin lbuf <= 576'd0; st <= S_AEND; end
            end
            S_ARQ: begin
                if (!wb_stall) begin wb_stb <= 0; st <= S_ARA; end
                else if (tmo == 13'd4095) begin ddr_err <= 1; wb_stb <= 0; lbuf <= 576'd0; st <= S_AEND; end
            end
            S_ARA: begin
                if (wb_ack) begin lbuf <= wb_rdata; st <= S_AEND; end
                else if (tmo == 13'd4095) begin ddr_err <= 1; lbuf <= 576'd0; st <= S_AEND; end
            end
            S_AEND: begin cur_sec <= asec; cur_valid <= 1; dirty <= 0; st <= acc_ret; end
            default: st <= S_IDLE;
            endcase
        end
    end
endmodule
