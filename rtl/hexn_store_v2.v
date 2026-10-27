`timescale 1ns/1ps
// hexn_store_v2.v -- layer 2 STORE AND RETRIEVE with BLOCK-RAM STYLE TABLES. Clone of hexn_store_v1.v (left untouched; same commands, same outputs, same reference model tools/hexn_store_v2.py). Changes: each table is one synchronous-read memory with one read port and one write port (one word per slot), so a synthesiser can map it to block RAM; a slot is read one clock after its address, so every scan runs one clock behind the address counter; a write is a registered request applied on the next clock, with a one-clock gap before the next scan; after reset the tables are cleared by a sweep (busy is high until it ends); the table read-out for the host (dbg ports) is a second synchronous read port (data valid 2 clocks after the address).
// Words: KNOWN {valid, key[13:0], seen[7:0], contra[7:0]} = 31 bits; CAND {valid, key[13:0], count[3:0], start[15:0]} = 35 bits. key = {len[1:0], ctx[8:0], ev[2:0]}.
// Commands: 0 CLR, 1 OBS, 2 LOAD, 3 RD (see hexn_store_v1.v). Outputs valid when done pulses. n_prom 1..15, w_win in events, t_in a 16-bit time from the host.
module hexn_store_v2 #(parameter KCAP = 128, parameter CCAP = 32, parameter KA = 7, parameter CA = 5) (
    input  wire clk, rst, cmd_valid, input wire [2:0] cmd, input wire [2:0] ev_in, input wire [15:0] t_in,
    input  wire [3:0] n_prom, input wire [15:0] w_win,
    output reg  busy, done,
    output reg  [1:0] verdict, vlevel, plevel, output reg [2:0] pbest, output reg [7:0] pbest_seen, output reg [10:0] ptotal,
    output reg  [15:0] n_known, n_cand, n_promoted, n_dropk, n_dropc,
    input  wire [KA-1:0] dbg_ka, output reg [30:0] dbg_kw, input wire [CA-1:0] dbg_ca, output reg [34:0] dbg_cw);
    reg [30:0] kmem [0:KCAP-1]; reg [34:0] cmem [0:CCAP-1];
    reg [30:0] kdata; reg [34:0] cdata; reg [KA-1:0] kra; reg [CA-1:0] cra;
    reg kwe; reg [KA-1:0] kwa; reg [30:0] kwd; reg cwe; reg [CA-1:0] cwa; reg [34:0] cwd;
    always @(posedge clk) begin
        if (kwe) kmem[kwa] <= kwd; kdata <= kmem[kra]; dbg_kw <= kmem[dbg_ka];
        if (cwe) cmem[cwa] <= cwd; cdata <= cmem[cra]; dbg_cw <= cmem[dbg_ca];
    end
    localparam S_INIT = 0, S_IDLE = 1, S_SCAN = 2, S_SEL = 3, S_CON = 4, S_UPD = 5, S_GAP = 6, S_KL = 7, S_KD = 8, S_CL = 9, S_CD = 10, S_FIN = 11;
    reg [3:0] st; reg [2:0] op, ev; reg [15:0] tt; reg [2:0] h0, h1, h2; reg [1:0] hn; reg [1:0] lv;
    reg [KA:0] si; reg [CA:0] ci; reg [KA:0] ii;
    reg an1, an2, an3, ex1, ex2, ex3; reg [10:0] tot1, tot2, tot3; reg [7:0] bs1, bs2, bs3; reg [2:0] be1, be2, be3;
    reg k_hit, k_hasfree, k_hasvic; reg [KA-1:0] k_hidx, k_fidx, k_vidx; reg [7:0] k_vseen; reg [30:0] k_hword;
    reg c_hit, c_hasfree, c_hasvic; reg [CA-1:0] c_hidx, c_fidx, c_vidx; reg [3:0] c_vcnt; reg [15:0] c_vage; reg [34:0] c_hword;
    wire [8:0] ctx1 = {6'b0, h0}, ctx2 = {3'b0, h1, h0}, ctx3 = {h2, h1, h0};
    wire [8:0] ctx_lv = (lv == 2'd1) ? ctx1 : (lv == 2'd2) ? ctx2 : ctx3;
    wire [8:0] ctx_vl = (vlevel == 2'd1) ? ctx1 : (vlevel == 2'd2) ? ctx2 : ctx3;
    wire [13:0] key_lv = {lv, ctx_lv, ev};
    // the word that arrived this clock belongs to the slot addressed one clock ago
    wire kvv = kdata[30]; wire [13:0] ke = kdata[29:16]; wire [7:0] ks = kdata[15:8], kc = kdata[7:0];
    wire pv = (si != 0); wire [KA-1:0] pidx = si[KA-1:0] - 1'b1;
    wire m1 = pv && kvv && ke[13:12] == 2'd1 && ke[11:3] == ctx1 && hn >= 1;
    wire m2 = pv && kvv && ke[13:12] == 2'd2 && ke[11:3] == ctx2 && hn >= 2;
    wire m3 = pv && kvv && ke[13:12] == 2'd3 && ke[11:3] == ctx3 && hn >= 3;
    wire cvv = cdata[34]; wire [13:0] cke = cdata[33:20]; wire [3:0] ccn = cdata[19:16]; wire [15:0] cs = cdata[15:0];
    wire cpv = (ci != 0); wire [CA-1:0] cpidx = ci[CA-1:0] - 1'b1;
    wire [15:0] cage = tt - cs;
    wire [1:0] sel_lv = an3 ? 2'd3 : an2 ? 2'd2 : an1 ? 2'd1 : 2'd0;
    wire [15:0] cdiff = tt - c_hword[15:0];
    wire c_exp = c_hit && (cdiff >= w_win); wire c_keep = c_hit && !c_exp;
    wire [4:0] c_new5 = c_keep ? ({1'b0, c_hword[19:16]} + 5'd1) : 5'd1;
    wire [3:0] c_newcnt = c_new5[3:0]; wire [15:0] c_newst = c_keep ? c_hword[15:0] : tt;
    task add_known(input [7:0] seen_v); begin
        if (k_hasfree) begin kwe <= 1; kwa <= k_fidx; kwd <= {1'b1, key_lv, seen_v, 8'd0}; n_known <= n_known + 1; end
        else begin kwe <= 1; kwa <= k_vidx; kwd <= {1'b1, key_lv, seen_v, 8'd0}; n_dropk <= n_dropk + 1; end
    end endtask
    task next_level; begin if (lv == 2'd3 || hn <= lv) st <= S_FIN; else begin lv <= lv + 1; st <= S_GAP; end end endtask
    always @(posedge clk) begin
        done <= 0; kwe <= 0; cwe <= 0;
        if (rst) begin
            st <= S_INIT; busy <= 1; ii <= 0; h0 <= 0; h1 <= 0; h2 <= 0; hn <= 0; verdict <= 3; vlevel <= 0; plevel <= 0; pbest <= 0; pbest_seen <= 0; ptotal <= 0;
            n_known <= 0; n_cand <= 0; n_promoted <= 0; n_dropk <= 0; n_dropc <= 0; kra <= 0; cra <= 0;
        end else case (st)
        S_INIT: begin     // clear both tables, one slot per clock
            if (ii < KCAP) begin kwe <= 1; kwa <= ii[KA-1:0]; kwd <= 31'd0; end
            if (ii < CCAP) begin cwe <= 1; cwa <= ii[CA-1:0]; cwd <= 35'd0; end
            if (ii >= KCAP && ii >= CCAP) begin st <= S_IDLE; busy <= 0; end else ii <= ii + 1;
        end
        S_IDLE: if (cmd_valid) begin
            op <= cmd; ev <= ev_in; tt <= t_in;
            if (cmd == 3'd0) begin h0 <= 0; h1 <= 0; h2 <= 0; hn <= 0; verdict <= 3; vlevel <= 0; plevel <= 0; pbest <= 0; pbest_seen <= 0; ptotal <= 0; done <= 1; end
            else if ((cmd == 3'd1 || cmd == 3'd2) && hn == 0) begin h0 <= ev_in; hn <= 1; verdict <= 3; vlevel <= 0; plevel <= 0; pbest <= 0; pbest_seen <= 0; ptotal <= 0; done <= 1; end
            else begin busy <= 1; st <= S_SCAN; si <= 0; kra <= 0; an1 <= 0; an2 <= 0; an3 <= 0; ex1 <= 0; ex2 <= 0; ex3 <= 0; tot1 <= 0; tot2 <= 0; tot3 <= 0; bs1 <= 0; bs2 <= 0; bs3 <= 0; be1 <= 0; be2 <= 0; be3 <= 0; end
        end
        S_SCAN: begin
            kra <= si + 1'b1;     // address of the next slot (the word for slot si-1 is in kdata now)
            if (m1) begin an1 <= 1; tot1 <= tot1 + ks; if (!an1 || ks > bs1 || (ks == bs1 && ke[2:0] < be1)) begin bs1 <= ks; be1 <= ke[2:0]; end if (ke[2:0] == ev) ex1 <= 1; end
            if (m2) begin an2 <= 1; tot2 <= tot2 + ks; if (!an2 || ks > bs2 || (ks == bs2 && ke[2:0] < be2)) begin bs2 <= ks; be2 <= ke[2:0]; end if (ke[2:0] == ev) ex2 <= 1; end
            if (m3) begin an3 <= 1; tot3 <= tot3 + ks; if (!an3 || ks > bs3 || (ks == bs3 && ke[2:0] < be3)) begin bs3 <= ks; be3 <= ke[2:0]; end if (ke[2:0] == ev) ex3 <= 1; end
            if (si == KCAP) st <= S_SEL; else si <= si + 1;
        end
        S_SEL: begin
            plevel <= sel_lv; vlevel <= sel_lv;
            case (sel_lv)
                2'd3: begin pbest <= be3; pbest_seen <= bs3; ptotal <= tot3; verdict <= ex3 ? 2'd0 : 2'd1; end
                2'd2: begin pbest <= be2; pbest_seen <= bs2; ptotal <= tot2; verdict <= ex2 ? 2'd0 : 2'd1; end
                2'd1: begin pbest <= be1; pbest_seen <= bs1; ptotal <= tot1; verdict <= ex1 ? 2'd0 : 2'd1; end
                default: begin pbest <= 0; pbest_seen <= 0; ptotal <= 0; verdict <= 2'd2; end
            endcase
            if (op == 3'd3) begin busy <= 0; done <= 1; st <= S_IDLE; end
            else if (op == 3'd1 && sel_lv != 0 && !((sel_lv == 3 && ex3) || (sel_lv == 2 && ex2) || (sel_lv == 1 && ex1))) begin st <= S_CON; si <= 0; kra <= 0; end
            else st <= S_UPD;
        end
        S_CON: begin
            kra <= si + 1'b1;
            if (pv && kvv && ke[13:12] == vlevel && ke[11:3] == ctx_vl && kc != 8'hFF) begin kwe <= 1; kwa <= pidx; kwd <= {kdata[30:8], kc + 8'd1}; end
            if (si == KCAP) st <= S_UPD; else si <= si + 1;
        end
        S_UPD: begin lv <= 2'd1; st <= S_GAP; end
        S_GAP: begin st <= S_KL; si <= 0; kra <= 0; k_hit <= 0; k_hasfree <= 0; k_hasvic <= 0; end     // one idle clock so the last write has landed
        S_KL: begin
            kra <= si + 1'b1;
            if (pv) begin
                if (kvv && ke == key_lv && !k_hit) begin k_hit <= 1; k_hidx <= pidx; k_hword <= kdata; end
                if (!kvv && !k_hasfree) begin k_hasfree <= 1; k_fidx <= pidx; end
                if (kvv && (!k_hasvic || ks < k_vseen)) begin k_hasvic <= 1; k_vidx <= pidx; k_vseen <= ks; end
            end
            if (si == KCAP) st <= S_KD; else si <= si + 1;
        end
        S_KD: begin
            if (k_hit) begin if (k_hword[15:8] != 8'hFF) begin kwe <= 1; kwa <= k_hidx; kwd <= {k_hword[30:16], k_hword[15:8] + 8'd1, k_hword[7:0]}; end next_level; end
            else if (op == 3'd2) begin add_known(8'd1); next_level; end
            else begin st <= S_CL; ci <= 0; cra <= 0; c_hit <= 0; c_hasfree <= 0; c_hasvic <= 0; end
        end
        S_CL: begin
            cra <= ci + 1'b1;
            if (cpv) begin
                if (cvv && cke == key_lv && !c_hit) begin c_hit <= 1; c_hidx <= cpidx; c_hword <= cdata; end
                if (!cvv && !c_hasfree) begin c_hasfree <= 1; c_fidx <= cpidx; end
                if (cvv && (!c_hasvic || ccn < c_vcnt || (ccn == c_vcnt && cage > c_vage))) begin c_hasvic <= 1; c_vidx <= cpidx; c_vcnt <= ccn; c_vage <= cage; end
            end
            if (ci == CCAP) st <= S_CD; else ci <= ci + 1;
        end
        S_CD: begin
            if (c_newcnt >= n_prom) begin
                if (c_hit) begin cwe <= 1; cwa <= c_hidx; cwd <= 35'd0; n_cand <= n_cand - 1; end
                add_known({4'b0, c_newcnt}); n_promoted <= n_promoted + 1;
            end else if (c_hit) begin cwe <= 1; cwa <= c_hidx; cwd <= {1'b1, key_lv, c_newcnt, c_newst}; end
            else if (c_hasfree) begin cwe <= 1; cwa <= c_fidx; cwd <= {1'b1, key_lv, 4'd1, tt}; n_cand <= n_cand + 1; end
            else begin cwe <= 1; cwa <= c_vidx; cwd <= {1'b1, key_lv, 4'd1, tt}; n_dropc <= n_dropc + 1; end
            next_level;
        end
        S_FIN: begin h2 <= h1; h1 <= h0; h0 <= ev; if (hn != 2'd3) hn <= hn + 1; busy <= 0; done <= 1; st <= S_IDLE; end
        default: st <= S_IDLE;
        endcase
    end
endmodule
