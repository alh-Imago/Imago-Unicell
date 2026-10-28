`timescale 1ns/1ps
// hexn_tier_v2.v -- (v2: clone of hexn_tier_v1.v, left untouched; NATIVE-18 VERSION. Alan, 28 Oct 2026: the Tang is native 18 bit, scale to use it. Changes: key KW (default 18) and value VW (default 18) are parameters; ONE reversible hash (one multiply of KW bits, so one 18x18 DSP when KW <= 18, then an xor-shift) replaces three 32-bit hashes (six 36x36 multipliers in v1); the fast slot is the low FB bits of the hash and only the remaining KW-FB bits are stored as the tag, so a fast entry is 1 + (KW-FB) + VW bits (26 for 18/18/11, v1: 57); the SDRAM start slot is the TOP RAMB bits of the hash, the bitmap bit is low-slice XOR top-slice; the SDRAM tag word holds the hash, not the key.) Three-level key/value store for the Tang Nano 20K: FAST TABLE in block RAM (2^FB slots), PRESENCE BITMAP in block RAM (2^BMB bits), and the embedded SDRAM behind them (2^RAMB slots, 2 words each, linear probe of up to P slots). New file. Reference model: tools/hexn_tier_ref_v2.py (bit-true: same hashes, same probe order, same counters).
// Alan, 28 Oct 2026: long-term patterns on the card, the faster table built directly into the design, the next level in the RAM; sizes are creation-time settings (tools/hexn_config_v1.py: HEXN_FAST_ENTRIES, HEXN_BITMAP_BITS, HEXN_RAM_ENTRIES give FB, BMB, RAMB).
// Key = KW bits (the token), value = 32 bits (the entry word). Rules:
//  PUT: if the key's fast slot is empty or holds the same key, store it there. Otherwise (a different key is resident) the new key goes to the SDRAM: its bitmap bit is set, then the SDRAM slots from the hashed start are probed (tag word read) until an empty slot or the same key is found; tag word and value word are written. After P full slots the put is dropped and counted (n_overflow).
//  GET: fast slot hit -> answer. Else read the bitmap bit: 0 -> not found with NO SDRAM access (n_skip). 1 -> probe the SDRAM the same way as PUT; a false alarm (bit set, key not there) is counted (n_fp).
// The resident key is never evicted by a newcomer (no promotion/demotion yet: a model-only question, see HEXN_DESIGN.md). The SDRAM is cleared by a sweep after reset: 2^(RAMB+1) writes (about 8 clocks each).
// Tag word = {1'b1, zeros, key}; value word = value. SDRAM word address = {slot, 1'b0 (tag) / 1'b1 (value)}; needs RAMB+1 <= 21.
module hexn_tier_v2 #(parameter KW = 18, parameter VW = 18, parameter FB = 10, parameter BMB = 14, parameter RAMB = 12, parameter P = 8, parameter FREQ = 27_000_000) (
    input  wire clk, input wire clk_sdram, input wire resetn, input wire [2:0] rdlat,
    input  wire cmd_valid, input wire cmd_we, input wire [KW-1:0] key, input wire [VW-1:0] wdata,
    output reg  busy, output reg done, output reg found, output reg [VW-1:0] rdata, output reg ready,
    output reg [31:0] n_fast_put, n_sd_put, n_overflow, n_fast_hit, n_skip, n_sd_get, n_fp, n_sd_rd, n_sd_wr, n_found, n_notfound,
    output wire O_sdram_clk, output wire O_sdram_cke, output wire O_sdram_cs_n, output wire O_sdram_ras_n, output wire O_sdram_cas_n, output wire O_sdram_wen_n,
    inout  wire [31:0] IO_sdram_dq, output wire [10:0] O_sdram_addr, output wire [1:0] O_sdram_ba, output wire [3:0] O_sdram_dqm);
    // ---- reversible hash of the KW-bit key (mirrored in tools/hexn_tier_ref_v2.py) ----
    localparam [31:0] ODD = 32'h9E3779B1 | 32'd1; localparam [31:0] MASK = (32'd1 << KW) - 32'd1; localparam SH = KW / 2;
    function [31:0] hashk(input [31:0] k);
        reg [31:0] m;
        begin m = (k * ODD) & MASK; hashk = m ^ (m >> SH); end
    endfunction
    function [31:0] top(input [31:0] h, input integer nb);   // the top nb bits of the KW-bit hash (all of it, zero-extended, if nb > KW)
        begin top = (nb <= KW) ? (h >> (KW - nb)) : h; end
    endfunction
    // ---- memories ----
    localparam FN = 1 << FB, BN = 1 << BMB, SN = 1 << RAMB;
    localparam TG = KW - FB, EWD = 1 + TG + VW;
    reg [EWD-1:0] fmem [0:FN-1];   // {valid, tag (hash bits above the slot), value}
    reg bmem [0:BN-1];
    reg [EWD-1:0] fdata; reg bdata; reg [FB-1:0] fra, fwa; reg fwe; reg [EWD-1:0] fwd; reg [BMB-1:0] bra, bwa; reg bwe, bwd;
    always @(posedge clk) begin
        if (fwe) fmem[fwa] <= fwd; fdata <= fmem[fra];
        if (bwe) bmem[bwa] <= bwd; bdata <= bmem[bra];
    end
    // ---- SDRAM controller ----
    reg sd_valid, sd_we; reg [20:0] sd_addr; reg [31:0] sd_wdata; wire sd_ready, sd_rv, sd_init; wire [31:0] sd_rd;
    hexn_sdram_v1 #(.FREQ(FREQ), .CL(3'd2)) sd (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(rdlat),
        .cmd_valid(sd_valid), .cmd_we(sd_we), .cmd_addr(sd_addr), .cmd_wdata(sd_wdata), .cmd_wmask(4'b1111), .cmd_ready(sd_ready), .rd_valid(sd_rv), .rd_data(sd_rd), .init_done(sd_init),
        .O_sdram_clk(O_sdram_clk), .O_sdram_cke(O_sdram_cke), .O_sdram_cs_n(O_sdram_cs_n), .O_sdram_ras_n(O_sdram_ras_n), .O_sdram_cas_n(O_sdram_cas_n), .O_sdram_wen_n(O_sdram_wen_n),
        .IO_sdram_dq(IO_sdram_dq), .O_sdram_addr(O_sdram_addr), .O_sdram_ba(O_sdram_ba), .O_sdram_dqm(O_sdram_dqm));
    // ---- state ----
    localparam S_CLR = 0, S_WINIT = 1, S_SWEEP = 2, S_IDLE = 3, S_F1 = 4, S_F2 = 5, S_RTAG = 6, S_WTAG = 7, S_USETAG = 8, S_WVAL = 9, S_RVAL = 10, S_FIN = 11, S_ISS = 12, S_RWAIT = 13;
    reg [3:0] st, ret; reg [31:0] ci; reg we_l; reg [KW-1:0] key_l; reg [VW-1:0] wd_l; reg [FB-1:0] hf; reg [RAMB-1:0] hs, slot; reg [BMB-1:0] hb; reg [7:0] p; reg [31:0] tagw; reg [KW-1:0] hk; reg [31:0] hfull;
    reg [31:0] h1, h2, h3;
    wire [31:0] tag_of = {1'b1, {(31-KW){1'b0}}, hk};
    always @(posedge clk) begin
        if (!resetn) begin
            st <= S_CLR; ci <= 0; busy <= 1; done <= 0; ready <= 0; found <= 0; rdata <= 0; fwe <= 0; bwe <= 0; sd_valid <= 0;
            n_fast_put <= 0; n_sd_put <= 0; n_overflow <= 0; n_fast_hit <= 0; n_skip <= 0; n_sd_get <= 0; n_fp <= 0; n_sd_rd <= 0; n_sd_wr <= 0; n_found <= 0; n_notfound <= 0;
        end else begin
            done <= 0; fwe <= 0; bwe <= 0;
            case (st)
            S_CLR: begin   // clear the fast table's valid bits and the bitmap (one sweep, the longer of the two)
                fwe <= (ci < FN); fwa <= ci[FB-1:0]; fwd <= 0; bwe <= (ci < BN); bwa <= ci[BMB-1:0]; bwd <= 0;
                ci <= ci + 1; if (ci == ((FN > BN) ? FN : BN) - 1) begin st <= S_WINIT; ci <= 0; end
            end
            S_WINIT: if (sd_init) begin st <= S_SWEEP; ci <= 0; end
            S_SWEEP: begin   // clear every SDRAM word (2 per slot)
                if (!sd_valid) begin sd_valid <= 1; sd_we <= 1; sd_addr <= ci[20:0]; sd_wdata <= 0; end
                else if (sd_ready) begin
                    sd_valid <= 0; ci <= ci + 1;
                    if (ci == 2 * SN - 1) begin st <= S_IDLE; ready <= 1; busy <= 0; end
                end
            end
            S_IDLE: if (cmd_valid) begin
                busy <= 1; we_l <= cmd_we; key_l <= key; wd_l <= wdata;
                hfull = hashk({{(32-KW){1'b0}}, key}); h1 = hfull; h2 = top(hfull, RAMB); h3 = hfull ^ top(hfull, BMB);
                hk <= hfull[KW-1:0]; hf <= h1[FB-1:0]; hs <= h2[RAMB-1:0]; hb <= h3[BMB-1:0]; fra <= h1[FB-1:0]; bra <= h3[BMB-1:0]; found <= 0; p <= 0; slot <= h2[RAMB-1:0];
                st <= S_F1;
            end
            S_F1: st <= S_F2;   // memory address was presented; data appears next clock
            S_F2: begin
                if (we_l) begin
                    if (!fdata[EWD-1] || fdata[EWD-2:VW] == hk[KW-1:FB]) begin
                        fwe <= 1; fwa <= hf; fwd <= {1'b1, hk[KW-1:FB], wd_l}; n_fast_put <= n_fast_put + 1; st <= S_FIN;
                    end else begin
                        bwe <= 1; bwa <= hb; bwd <= 1; n_sd_put <= n_sd_put + 1; st <= S_RTAG;
                    end
                end else begin
                    if (fdata[EWD-1] && fdata[EWD-2:VW] == hk[KW-1:FB]) begin found <= 1; rdata <= fdata[VW-1:0]; n_fast_hit <= n_fast_hit + 1; n_found <= n_found + 1; st <= S_FIN; end
                    else if (!bdata) begin n_skip <= n_skip + 1; n_notfound <= n_notfound + 1; st <= S_FIN; end
                    else begin n_sd_get <= n_sd_get + 1; st <= S_RTAG; end
                end
            end
            S_RTAG: begin   // issue a read of the tag word of the current slot
                sd_valid <= 1; sd_we <= 0; sd_addr <= {slot, 1'b0}; n_sd_rd <= n_sd_rd + 1; ret <= S_USETAG; st <= S_ISS;
            end
            S_ISS: if (sd_valid && sd_ready) begin sd_valid <= 0; st <= sd_we ? ret : S_RWAIT; end   // taken at this edge (cmd_ready is read as before the edge)
            S_RWAIT: begin
                if (sd_rv) begin tagw <= sd_rd; st <= ret; end   // a read: wait for its data
            end
            S_USETAG: begin
                if (!tagw[31] || tagw[KW-1:0] == hk) begin   // empty slot or same key
                    if (we_l) begin   // PUT: write tag word, then value word
                        sd_valid <= 1; sd_we <= 1; sd_addr <= {slot, 1'b0}; sd_wdata <= tag_of; n_sd_wr <= n_sd_wr + 1; ret <= S_WVAL; st <= S_ISS;
                    end else if (!tagw[31]) begin n_fp <= n_fp + 1; n_notfound <= n_notfound + 1; st <= S_FIN; end
                    else begin sd_valid <= 1; sd_we <= 0; sd_addr <= {slot, 1'b1}; n_sd_rd <= n_sd_rd + 1; ret <= S_RVAL; st <= S_ISS; end
                end else begin   // another key sits here: next slot
                    p <= p + 1; slot <= slot + 1;
                    if (p == P - 1) begin
                        if (we_l) n_overflow <= n_overflow + 1; else begin n_fp <= n_fp + 1; n_notfound <= n_notfound + 1; end
                        st <= S_FIN;
                    end else st <= S_RTAG;
                end
            end
            S_WVAL: begin sd_valid <= 1; sd_we <= 1; sd_addr <= {slot, 1'b1}; sd_wdata <= {{(32-VW){1'b0}}, wd_l}; n_sd_wr <= n_sd_wr + 1; ret <= S_FIN; st <= S_ISS; end
            S_RVAL: begin found <= 1; rdata <= tagw[VW-1:0]; n_found <= n_found + 1; st <= S_FIN; end
            S_FIN: begin busy <= 0; done <= 1; st <= S_IDLE; end
            default: st <= S_IDLE;
            endcase
        end
    end
endmodule
