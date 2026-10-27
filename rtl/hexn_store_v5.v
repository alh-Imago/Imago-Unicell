`timescale 1ns/1ps
// hexn_store_v5.v -- layer 2 STORE with an ADDRESS INDEX and a DENSE ENTRY HEAP, wider events (EVB bits). New file; hexn_store_v3.v is untouched. Reference model: tools/hexn_store_v5.py (bit-true, same hash, same probe order, same row allocation order).
// Alan, 27 Oct 2026: the quick lookup is a RAM address table (the tokenisation); only known values are stored; a new one is added to the table and the main store.
// INDEX imem[2^IB]: {valid, tag[TW-1:0], row[RB-1:0]}, tag = {len[1:0], e2, e1, e0} (unused events 0). A token hashes (three shift/XOR mixes then an XOR fold to IB bits, see hsh) to a slot; up to P consecutive slots are probed; the first empty slot ends the probe.
// HEAP: row header hmem[2^RB] = {next_valid, next[RB-1:0]}; entry words emem[{row, slot}] (R = 2^RSB slots per row) = {valid, ev[EVB-1:0], seen[7:0], contra[7:0], value[7:0]}. Rows are handed out in order by the pointer hp (never freed). The tables are cleared by a sweep after reset.
// CAND table cmem[CCAP] = {valid, key[KW-1:0], count[3:0], start[15:0]}, key = {len[1:0], e2, e1, e0, ev}: same rules as store v3 (linear scan).
// Commands: 0 CLR, 1 OBS, 2 LOAD, 3 RD, 4 REW. Outputs valid when done pulses. Every read of a memory costs three clocks (address, wait, use): a lookup is about 3 + 3*(1 + R) clocks per heap row of the context.
module hexn_store_v5 #(parameter EVB = 4, parameter IB = 10, parameter RB = 9, parameter RSB = 2, parameter P = 4, parameter CCAP = 32, parameter CA = 5) (
    input  wire clk, rst, cmd_valid, input wire [2:0] cmd, input wire [EVB-1:0] ev_in, input wire [15:0] t_in,
    input  wire [3:0] n_prom, input wire [15:0] w_win, input wire [7:0] rew_in, input wire [2:0] vshift, input wire [1:0] glvl,
    output reg  busy, done,
    output reg  [1:0] verdict, vlevel, plevel, output reg [EVB-1:0] pbest, output reg [7:0] pbest_seen, output reg [EVB+7:0] ptotal, output reg [EVB-1:0] gbest, output reg [7:0] gval,
    output reg  [15:0] n_known, n_cand, n_promoted, n_dropk, n_dropc,
    input  wire [IB-1:0] dbg_ia, output reg [2+3*EVB+RB:0] dbg_iw, input wire [RB-1:0] dbg_ha, output reg [RB:0] dbg_hw,
    input  wire [RB+RSB-1:0] dbg_ea, output reg [EVB+24:0] dbg_ew, input wire [CA-1:0] dbg_ca, output reg [22+4*EVB:0] dbg_cw);
    localparam TW = 2 + 3 * EVB, KW = 2 + 4 * EVB, IW = 1 + TW + RB, EW = 1 + EVB + 24, CW = 1 + KW + 20, R = 1 << RSB, HROWS = 1 << RB, IDXN = 1 << IB, HEN = 1 << (RB + RSB);
    localparam MAXN = (IDXN > HEN) ? ((IDXN > CCAP) ? IDXN : CCAP) : ((HEN > CCAP) ? HEN : CCAP);
    reg [IW-1:0] imem [0:IDXN-1]; reg [RB:0] hmem [0:HROWS-1]; reg [EW-1:0] emem [0:HEN-1]; reg [CW-1:0] cmem [0:CCAP-1];
    reg [IW-1:0] idata; reg [RB:0] hdata; reg [EW-1:0] edata; reg [CW-1:0] cdata;
    reg [IB-1:0] ira; reg [RB-1:0] hra; reg [RB+RSB-1:0] era; reg [CA-1:0] cra;
    reg iwe; reg [IB-1:0] iwa; reg [IW-1:0] iwd; reg hwe; reg [RB-1:0] hwa; reg [RB:0] hwd; reg ewe; reg [RB+RSB-1:0] ewa; reg [EW-1:0] ewd; reg cwe; reg [CA-1:0] cwa; reg [CW-1:0] cwd;
    always @(posedge clk) begin
        if (iwe) imem[iwa] <= iwd; idata <= imem[ira]; dbg_iw <= imem[dbg_ia];
        if (hwe) hmem[hwa] <= hwd; hdata <= hmem[hra]; dbg_hw <= hmem[dbg_ha];
        if (ewe) emem[ewa] <= ewd; edata <= emem[era]; dbg_ew <= emem[dbg_ea];
        if (cwe) cmem[cwa] <= cwd; cdata <= cmem[cra]; dbg_cw <= cmem[dbg_ca];
    end
    localparam S_INIT = 0, S_IDLE = 1, L_START = 2, L_IA = 3, L_IB = 4, L_IC = 5, W_HA = 6, W_HB = 7, W_HC = 8, W_EA = 9, W_EB = 10, W_EC = 11, L_DONE = 12, S_SEL = 13, S_CON = 14, S_UPD = 15, S_FD = 16, S_CL = 17, S_CD = 18, S_RW0 = 19, S_RW1 = 20, S_RW2 = 21, S_FIN = 22;
    reg [4:0] st; reg [2:0] op; reg [EVB-1:0] ev; reg [15:0] tt; reg [EVB-1:0] h0, h1, h2; reg [1:0] hn; reg [31:0] ii;
    reg [1:0] lj, lmode; reg [4:0] pc; reg found, fv; reg [IB-1:0] fs; reg [RB-1:0] rowp, lastrow; reg [RSB-1:0] ws; reg wnv; reg [RB-1:0] wnx;
    reg fhit; reg [RB-1:0] fhit_row; reg [RSB-1:0] fhit_slot; reg [EW-1:0] fhit_word; reg ffree; reg [RB-1:0] ffree_row; reg [RSB-1:0] ffree_slot; reg [RB:0] hp;
    reg an1, an2, an3, ex1, ex2, ex3; reg [EVB+7:0] tot1, tot2, tot3; reg [7:0] bs1, bs2, bs3; reg [EVB-1:0] be1, be2, be3;
    reg [7:0] bv1, bv2, bv3, bq1, bq2, bq3; reg [EVB-1:0] bw1, bw2, bw3;
    reg [RB+RSB-1:0] fq [0:31]; reg [4:0] fq_head; reg [5:0] fq_n; reg [5:0] rw_i; reg [RB+RSB-1:0] rw_idx;
    wire [4:0] fq_tail = fq_head - fq_n[4:0];
    reg [CA:0] ci; reg c_hit, c_hasfree, c_hasvic; reg [CA-1:0] c_hidx, c_fidx, c_vidx; reg [3:0] c_vcnt; reg [15:0] c_vage; reg [CW-1:0] c_hword;
    // token of the level lj: tag, key part, and hash
    wire [3*EVB-1:0] cpk = (lj == 2'd1) ? {{(2*EVB){1'b0}}, h0} : (lj == 2'd2) ? {{EVB{1'b0}}, h1, h0} : {h2, h1, h0};
    wire [TW-1:0] ltag = {lj, cpk};
    wire [KW-1:0] key_lv = {lj, cpk, ev};
    wire [31:0] v0 = (lj == 2'd1) ? ((32'd1 << EVB) | h0) : (lj == 2'd2) ? ((32'd2 << (2*EVB)) | (h1 << EVB) | h0) : ((32'd3 << (3*EVB)) | (h2 << (2*EVB)) | (h1 << EVB) | h0);
    wire [31:0] v1 = v0 ^ (v0 >> 5); wire [31:0] v2 = v1 ^ ((v1 << 7) & 32'h00FFFFFF); wire [31:0] v3 = v2 ^ (v2 >> 11);
    function [IB-1:0] fold(input [31:0] v); integer k; begin fold = 0; for (k = 0; k < 32; k = k + IB) fold = fold ^ (v >> k); end endfunction
    wire [IB-1:0] hsh = fold(v3); wire [IB-1:0] pcx = pc; wire [IB-1:0] pslot = hsh + pcx;
    wire iv = idata[IW-1]; wire [TW-1:0] itag = idata[IW-2:RB]; wire [RB-1:0] irow = idata[RB-1:0];
    wire wvalid = edata[EVB+24]; wire [EVB-1:0] wev = edata[EVB+23:24]; wire [7:0] wseen = edata[23:16], wcon = edata[15:8], wval = edata[7:0];
    wire cvv = cdata[CW-1]; wire [KW-1:0] cke = cdata[CW-2:20]; wire [3:0] ccn = cdata[19:16]; wire [15:0] cs = cdata[15:0];
    wire cpv = (ci != 0); wire [CA-1:0] cpidx = ci[CA-1:0] - 1'b1; wire [15:0] cage = tt - cs;
    wire [1:0] sel_lv = an3 ? 2'd3 : an2 ? 2'd2 : an1 ? 2'd1 : 2'd0;
    wire [1:0] gsel = (an3 && glvl >= 2'd3) ? 2'd3 : (an2 && glvl >= 2'd2) ? 2'd2 : an1 ? 2'd1 : 2'd0;
    function better(input [7:0] v, input [7:0] sn, input [EVB-1:0] e, input [7:0] bv, input [7:0] bs, input [EVB-1:0] be);
        better = ($signed(v) > $signed(bv)) || (v == bv && (sn > bs || (sn == bs && e < be)));
    endfunction
    wire [15:0] cdiff = tt - c_hword[15:0];
    wire c_exp = c_hit && (cdiff >= w_win); wire c_keep = c_hit && !c_exp;
    wire [4:0] c_new5 = c_keep ? ({1'b0, c_hword[19:16]} + 5'd1) : 5'd1;
    wire [3:0] c_newcnt = c_new5[3:0]; wire [15:0] c_newst = c_keep ? c_hword[15:0] : tt;
    task push(input [RB+RSB-1:0] ptr); begin fq[fq_head] <= ptr; fq_head <= fq_head + 5'd1; if (fq_n != 6'd32) fq_n <= fq_n + 6'd1; end endtask
    // add a known entry for the context of level lj using what the lookup found; pq = queue it
    task do_insert(input [7:0] seen_v, input pq); reg [EW-1:0] w; begin
        w = {1'b1, ev, seen_v, 8'd0, 8'd0};
        if (found) begin
            if (ffree) begin ewe <= 1; ewa <= {ffree_row, ffree_slot}; ewd <= w; n_known <= n_known + 1; if (pq) push({ffree_row, ffree_slot}); end
            else if (hp != HROWS) begin ewe <= 1; ewa <= {hp[RB-1:0], {RSB{1'b0}}}; ewd <= w; hwe <= 1; hwa <= lastrow; hwd <= {1'b1, hp[RB-1:0]}; hp <= hp + 1'b1; n_known <= n_known + 1; if (pq) push({hp[RB-1:0], {RSB{1'b0}}}); end
            else n_dropk <= n_dropk + 1;
        end else begin
            if (fv && hp != HROWS) begin iwe <= 1; iwa <= fs; iwd <= {1'b1, ltag, hp[RB-1:0]}; ewe <= 1; ewa <= {hp[RB-1:0], {RSB{1'b0}}}; ewd <= w; hp <= hp + 1'b1; n_known <= n_known + 1; if (pq) push({hp[RB-1:0], {RSB{1'b0}}}); end
            else n_dropk <= n_dropk + 1;
        end
    end endtask
    wire signed [9:0] rw_d = $signed({{2{rew_in[7]}}, rew_in}) - $signed({{2{wval[7]}}, wval});
    wire signed [9:0] rw_up = (rw_d + ((10'sd1 <<< vshift) - 10'sd1)) >>> vshift;
    wire signed [9:0] rw_dn = rw_d >>> vshift;
    wire signed [9:0] rw_step = (rw_d > 0) ? rw_up : rw_dn;
    wire [7:0] rw_new = wval + rw_step[7:0];
    task next_level; begin if (lj == 2'd3 || hn <= lj) st <= S_FIN; else begin lj <= lj + 1; lmode <= 2'd2; st <= L_START; end end endtask
    always @(posedge clk) begin
        done <= 0; iwe <= 0; hwe <= 0; ewe <= 0; cwe <= 0;
        if (rst) begin
            st <= S_INIT; busy <= 1; ii <= 0; h0 <= 0; h1 <= 0; h2 <= 0; hn <= 0; verdict <= 3; vlevel <= 0; plevel <= 0; pbest <= 0; pbest_seen <= 0; ptotal <= 0; gbest <= 0; gval <= 0; fq_head <= 0; fq_n <= 0; hp <= 0;
            n_known <= 0; n_cand <= 0; n_promoted <= 0; n_dropk <= 0; n_dropc <= 0; ira <= 0; hra <= 0; era <= 0; cra <= 0;
        end else case (st)
        S_INIT: begin
            if (ii < IDXN) begin iwe <= 1; iwa <= ii[IB-1:0]; iwd <= 0; end
            if (ii < HROWS) begin hwe <= 1; hwa <= ii[RB-1:0]; hwd <= 0; end
            if (ii < HEN) begin ewe <= 1; ewa <= ii[RB+RSB-1:0]; ewd <= 0; end
            if (ii < CCAP) begin cwe <= 1; cwa <= ii[CA-1:0]; cwd <= 0; end
            if (ii >= MAXN) begin st <= S_IDLE; busy <= 0; end else ii <= ii + 1;
        end
        S_IDLE: if (cmd_valid) begin
            op <= cmd; ev <= ev_in; tt <= t_in;
            if (cmd == 3'd0) begin h0 <= 0; h1 <= 0; h2 <= 0; hn <= 0; verdict <= 3; vlevel <= 0; plevel <= 0; pbest <= 0; pbest_seen <= 0; ptotal <= 0; gbest <= 0; gval <= 0; done <= 1; end
            else if ((cmd == 3'd1 || cmd == 3'd2) && hn == 0) begin h0 <= ev_in; hn <= 1; verdict <= 3; vlevel <= 0; plevel <= 0; pbest <= 0; pbest_seen <= 0; ptotal <= 0; gbest <= 0; gval <= 0; done <= 1; end
            else if (cmd == 3'd3 && hn == 0) begin verdict <= 2; vlevel <= 0; plevel <= 0; pbest <= 0; pbest_seen <= 0; ptotal <= 0; gbest <= 0; gval <= 0; done <= 1; end
            else if (cmd == 3'd4) begin busy <= 1; verdict <= 3; vlevel <= 0; plevel <= 0; pbest <= 0; pbest_seen <= 0; ptotal <= 0; gbest <= 0; gval <= 0; rw_i <= 0; st <= S_RW0; end
            else begin busy <= 1; lj <= 2'd1; lmode <= 2'd0; st <= L_START; an1 <= 0; an2 <= 0; an3 <= 0; ex1 <= 0; ex2 <= 0; ex3 <= 0; tot1 <= 0; tot2 <= 0; tot3 <= 0; bs1 <= 0; bs2 <= 0; bs3 <= 0; be1 <= 0; be2 <= 0; be3 <= 0; bv1 <= 0; bv2 <= 0; bv3 <= 0; bq1 <= 0; bq2 <= 0; bq3 <= 0; bw1 <= 0; bw2 <= 0; bw3 <= 0; end
        end
        L_START: begin pc <= 0; found <= 0; fv <= 0; fhit <= 0; ffree <= 0; st <= L_IA; end
        L_IA: begin ira <= pslot; st <= L_IB; end
        L_IB: st <= L_IC;
        L_IC: begin
            if (!iv) begin fv <= 1; fs <= pslot; st <= L_DONE; end
            else if (itag == ltag) begin found <= 1; rowp <= irow; st <= W_HA; end
            else if (pc == P - 1) st <= L_DONE;
            else begin pc <= pc + 5'd1; st <= L_IA; end
        end
        W_HA: begin hra <= rowp; st <= W_HB; end
        W_HB: st <= W_HC;
        W_HC: begin wnv <= hdata[RB]; wnx <= hdata[RB-1:0]; ws <= 0; st <= W_EA; end
        W_EA: begin era <= {rowp, ws}; st <= W_EB; end
        W_EB: st <= W_EC;
        W_EC: begin
            case (lmode)
            2'd0: if (wvalid) case (lj)
                2'd1: begin an1 <= 1; tot1 <= tot1 + wseen; if (!an1 || wseen > bs1 || (wseen == bs1 && wev < be1)) begin bs1 <= wseen; be1 <= wev; end if (wev == ev) ex1 <= 1;
                    if (!an1 || better(wval, wseen, wev, bv1, bq1, bw1)) begin bv1 <= wval; bq1 <= wseen; bw1 <= wev; end end
                2'd2: begin an2 <= 1; tot2 <= tot2 + wseen; if (!an2 || wseen > bs2 || (wseen == bs2 && wev < be2)) begin bs2 <= wseen; be2 <= wev; end if (wev == ev) ex2 <= 1;
                    if (!an2 || better(wval, wseen, wev, bv2, bq2, bw2)) begin bv2 <= wval; bq2 <= wseen; bw2 <= wev; end end
                default: begin an3 <= 1; tot3 <= tot3 + wseen; if (!an3 || wseen > bs3 || (wseen == bs3 && wev < be3)) begin bs3 <= wseen; be3 <= wev; end if (wev == ev) ex3 <= 1;
                    if (!an3 || better(wval, wseen, wev, bv3, bq3, bw3)) begin bv3 <= wval; bq3 <= wseen; bw3 <= wev; end end
                endcase
            2'd1: if (wvalid && wcon != 8'hFF) begin ewe <= 1; ewa <= {rowp, ws}; ewd <= {edata[EW-1:16], wcon + 8'd1, edata[7:0]}; end
            default: begin
                if (wvalid && wev == ev && !fhit) begin fhit <= 1; fhit_row <= rowp; fhit_slot <= ws; fhit_word <= edata; end
                if (!wvalid && !ffree) begin ffree <= 1; ffree_row <= rowp; ffree_slot <= ws; end
            end
            endcase
            if (ws == R - 1) begin lastrow <= rowp; if (wnv) begin rowp <= wnx; st <= W_HA; end else st <= L_DONE; end
            else begin ws <= ws + 1'b1; st <= W_EA; end
        end
        L_DONE: case (lmode)
            2'd0: if (lj == 2'd3 || hn <= lj) st <= S_SEL; else begin lj <= lj + 1; st <= L_START; end
            2'd1: st <= S_UPD;
            default: st <= S_FD;
        endcase
        S_SEL: begin
            plevel <= sel_lv; vlevel <= sel_lv;
            case (gsel) 2'd3: begin gbest <= bw3; gval <= bv3; end 2'd2: begin gbest <= bw2; gval <= bv2; end 2'd1: begin gbest <= bw1; gval <= bv1; end default: begin gbest <= 0; gval <= 0; end endcase
            case (sel_lv)
                2'd3: begin pbest <= be3; pbest_seen <= bs3; ptotal <= tot3; verdict <= ex3 ? 2'd0 : 2'd1; end
                2'd2: begin pbest <= be2; pbest_seen <= bs2; ptotal <= tot2; verdict <= ex2 ? 2'd0 : 2'd1; end
                2'd1: begin pbest <= be1; pbest_seen <= bs1; ptotal <= tot1; verdict <= ex1 ? 2'd0 : 2'd1; end
                default: begin pbest <= 0; pbest_seen <= 0; ptotal <= 0; verdict <= 2'd2; end
            endcase
            if (op == 3'd3) begin busy <= 0; done <= 1; st <= S_IDLE; end
            else if (op == 3'd1 && sel_lv != 0 && !((sel_lv == 3 && ex3) || (sel_lv == 2 && ex2) || (sel_lv == 1 && ex1))) st <= S_CON;
            else st <= S_UPD;
        end
        S_CON: begin lj <= vlevel; lmode <= 2'd1; st <= L_START; end
        S_UPD: begin lj <= 2'd1; lmode <= 2'd2; st <= L_START; end
        S_FD: begin
            if (fhit) begin
                if (fhit_word[23:16] != 8'hFF) begin ewe <= 1; ewa <= {fhit_row, fhit_slot}; ewd <= {fhit_word[EW-1:24], fhit_word[23:16] + 8'd1, fhit_word[15:0]}; end
                if (op == 3'd1) push({fhit_row, fhit_slot}); next_level;
            end
            else if (op == 3'd2) begin do_insert(8'd1, 1'b0); next_level; end
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
                if (c_hit) begin cwe <= 1; cwa <= c_hidx; cwd <= 0; n_cand <= n_cand - 1; end
                do_insert({4'b0, c_newcnt}, 1'b1); n_promoted <= n_promoted + 1;
            end else if (c_hit) begin cwe <= 1; cwa <= c_hidx; cwd <= {1'b1, key_lv, c_newcnt, c_newst}; end
            else if (c_hasfree) begin cwe <= 1; cwa <= c_fidx; cwd <= {1'b1, key_lv, 4'd1, tt}; n_cand <= n_cand + 1; end
            else begin cwe <= 1; cwa <= c_vidx; cwd <= {1'b1, key_lv, 4'd1, tt}; n_dropc <= n_dropc + 1; end
            next_level;
        end
        S_RW0: begin
            if (rw_i == fq_n) begin fq_n <= 0; busy <= 0; done <= 1; st <= S_IDLE; end
            else begin rw_idx <= fq[fq_tail + rw_i[4:0]]; era <= fq[fq_tail + rw_i[4:0]]; st <= S_RW1; end
        end
        S_RW1: st <= S_RW2;
        S_RW2: begin
            if (wvalid) begin ewe <= 1; ewa <= rw_idx; ewd <= {edata[EW-1:8], rw_new}; end
            rw_i <= rw_i + 6'd1; st <= S_RW0;
        end
        S_FIN: begin h2 <= h1; h1 <= h0; h0 <= ev; if (hn != 2'd3) hn <= hn + 1; busy <= 0; done <= 1; st <= S_IDLE; end
        default: st <= S_IDLE;
        endcase
    end
endmodule
