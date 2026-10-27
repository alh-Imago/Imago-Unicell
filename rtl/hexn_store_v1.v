`timescale 1ns/1ps
// hexn_store_v1.v -- layer 2 STORE AND RETRIEVE (Alan, 27 Oct 2026). New file. Reference model: tools/hexn_store_v2.py (bit-true); checked by tools/hexn_store_rtl_check_v1.py.
// Two tables of fixed size, scanned one slot per clock (a human key press is milliseconds, so serial scans are fast enough):
//   KNOWN (KCAP slots): {valid, key[13:0] = {len[1:0], ctx[8:0], ev[2:0]}, seen[7:0], contra[7:0]}; ctx holds the last len events, newest in the low 3 bits.
//   CAND  (CCAP slots): {valid, key[13:0], count[3:0], start[15:0]}; a sighting at least w_win after the start restarts the count (tumbling window); n_prom sightings promote the pair to KNOWN with seen = count.
// Commands (cmd with cmd_valid, one per busy-free clock): 0 CLR (clear the 3-event history), 1 OBS (predict, self-check, update the store), 2 LOAD (host load: add the pair or seen+1; no verdict, no candidates), 3 RD (retrieve only, no change).
// The first OBS/LOAD after CLR only enters the history (verdict 3). ev_in is a class 0..7; t_in is the host time (16 bit); n_prom 1..15; w_win in events.
// Outputs valid when done pulses: verdict (0 ok, 1 contradiction, 2 novel, 3 start), vlevel, plevel (context length used for the prediction, 0 = none), pbest (best next event), pbest_seen (its count), ptotal (sum of counts at that context). Full tables are read through the dbg ports.
// Full slots are overwritten: KNOWN lowest seen, CAND lowest count then oldest (largest age = t - start, wrap-safe); ties lowest slot. Tables are flop arrays here (simulation model); a block-RAM version is a later step.
module hexn_store_v1 #(parameter KCAP = 128, parameter CCAP = 32, parameter KA = 7, parameter CA = 5) (
    input  wire clk, rst, cmd_valid, input wire [2:0] cmd, input wire [2:0] ev_in, input wire [15:0] t_in,
    input  wire [3:0] n_prom, input wire [15:0] w_win,
    output reg  busy, done,
    output reg  [1:0] verdict, vlevel, plevel, output reg [2:0] pbest, output reg [7:0] pbest_seen, output reg [10:0] ptotal,
    output reg  [15:0] n_known, n_cand, n_promoted, n_dropk, n_dropc,
    input  wire [KA-1:0] dbg_ka, output wire dbg_kv, output wire [13:0] dbg_kkey, output wire [7:0] dbg_kseen, dbg_kcon,
    input  wire [CA-1:0] dbg_ca, output wire dbg_cv, output wire [13:0] dbg_ckey, output wire [3:0] dbg_ccnt, output wire [15:0] dbg_cstart);
    reg kv [0:KCAP-1]; reg [13:0] kkey [0:KCAP-1]; reg [7:0] kseen [0:KCAP-1]; reg [7:0] kcon [0:KCAP-1];
    reg cv [0:CCAP-1]; reg [13:0] ckey [0:CCAP-1]; reg [3:0] ccnt [0:CCAP-1]; reg [15:0] cst [0:CCAP-1];
    assign dbg_kv = kv[dbg_ka]; assign dbg_kkey = kkey[dbg_ka]; assign dbg_kseen = kseen[dbg_ka]; assign dbg_kcon = kcon[dbg_ka];
    assign dbg_cv = cv[dbg_ca]; assign dbg_ckey = ckey[dbg_ca]; assign dbg_ccnt = ccnt[dbg_ca]; assign dbg_cstart = cst[dbg_ca];
    localparam S_IDLE = 0, S_SCAN = 1, S_SEL = 2, S_CON = 3, S_UPD = 4, S_KL = 5, S_KD = 6, S_CL = 7, S_CD = 8, S_FIN = 9;
    reg [3:0] st; reg [2:0] op, ev; reg [15:0] tt; reg [2:0] h0, h1, h2; reg [1:0] hn; reg [1:0] lv;
    reg [KA-1:0] si; reg [CA-1:0] ci;
    // scan 1 accumulators, index 1..3
    reg an1, an2, an3, ex1, ex2, ex3; reg [10:0] tot1, tot2, tot3; reg [7:0] bs1, bs2, bs3; reg [2:0] be1, be2, be3;
    // known lookup / cand lookup
    reg k_hit, k_hasfree, k_hasvic; reg [KA-1:0] k_hidx, k_fidx, k_vidx; reg [7:0] k_vseen;
    reg c_hit, c_hasfree, c_hasvic; reg [CA-1:0] c_hidx, c_fidx, c_vidx; reg [3:0] c_vcnt; reg [15:0] c_vage;
    wire [15:0] cage = tt - cst[ci];   // age of the scanned candidate; wrap-safe (a raw start time would not order correctly after the 16-bit clock wraps)
    // context of each length straight from the history registers (a function reading them would not re-evaluate when they change)
    wire [8:0] ctx1 = {6'b0, h0}, ctx2 = {3'b0, h1, h0}, ctx3 = {h2, h1, h0};
    wire [8:0] ctx_lv = (lv == 2'd1) ? ctx1 : (lv == 2'd2) ? ctx2 : ctx3;
    wire [8:0] ctx_vl = (vlevel == 2'd1) ? ctx1 : (vlevel == 2'd2) ? ctx2 : ctx3;
    wire [13:0] key_lv = {lv, ctx_lv, ev};
    wire [13:0] ke = kkey[si]; wire kvv = kv[si]; wire [7:0] ks = kseen[si];
    wire m1 = kvv && ke[13:12] == 2'd1 && ke[11:3] == ctx1 && hn >= 1;
    wire m2 = kvv && ke[13:12] == 2'd2 && ke[11:3] == ctx2 && hn >= 2;
    wire m3 = kvv && ke[13:12] == 2'd3 && ke[11:3] == ctx3 && hn >= 3;
    wire [1:0] sel_lv = an3 ? 2'd3 : an2 ? 2'd2 : an1 ? 2'd1 : 2'd0;
    wire [15:0] cdiff = tt - cst[c_hidx];
    wire c_exp = c_hit && (cdiff >= w_win);
    wire c_keep = c_hit && !c_exp;
    wire [4:0] c_new5 = c_keep ? ({1'b0, ccnt[c_hidx]} + 5'd1) : 5'd1;
    wire [3:0] c_newcnt = c_new5[3:0]; wire [15:0] c_newst = c_keep ? cst[c_hidx] : tt;
    integer i;
    task add_known(input [7:0] seen_v); begin
        if (k_hasfree) begin kv[k_fidx] <= 1; kkey[k_fidx] <= key_lv; kseen[k_fidx] <= seen_v; kcon[k_fidx] <= 0; n_known <= n_known + 1; end
        else begin kkey[k_vidx] <= key_lv; kseen[k_vidx] <= seen_v; kcon[k_vidx] <= 0; n_dropk <= n_dropk + 1; end
    end endtask
    task next_level; begin if (lv == 2'd3 || hn <= lv) st <= S_FIN; else begin lv <= lv + 1; st <= S_KL; si <= 0; k_hit <= 0; k_hasfree <= 0; k_hasvic <= 0; end end endtask
    always @(posedge clk) begin
        done <= 0;
        if (rst) begin
            st <= S_IDLE; busy <= 0; h0 <= 0; h1 <= 0; h2 <= 0; hn <= 0; verdict <= 3; vlevel <= 0; plevel <= 0; pbest <= 0; pbest_seen <= 0; ptotal <= 0;
            n_known <= 0; n_cand <= 0; n_promoted <= 0; n_dropk <= 0; n_dropc <= 0;
            for (i = 0; i < KCAP; i = i + 1) begin kv[i] <= 0; kkey[i] <= 0; kseen[i] <= 0; kcon[i] <= 0; end
            for (i = 0; i < CCAP; i = i + 1) begin cv[i] <= 0; ckey[i] <= 0; ccnt[i] <= 0; cst[i] <= 0; end
        end else case (st)
        S_IDLE: if (cmd_valid) begin
            op <= cmd; ev <= ev_in; tt <= t_in;
            if (cmd == 3'd0) begin h0 <= 0; h1 <= 0; h2 <= 0; hn <= 0; verdict <= 3; vlevel <= 0; plevel <= 0; pbest <= 0; pbest_seen <= 0; ptotal <= 0; done <= 1; end
            else if ((cmd == 3'd1 || cmd == 3'd2) && hn == 0) begin h0 <= ev_in; hn <= 1; verdict <= 3; vlevel <= 0; plevel <= 0; pbest <= 0; pbest_seen <= 0; ptotal <= 0; done <= 1; end
            else begin busy <= 1; st <= S_SCAN; si <= 0; an1 <= 0; an2 <= 0; an3 <= 0; ex1 <= 0; ex2 <= 0; ex3 <= 0; tot1 <= 0; tot2 <= 0; tot3 <= 0; bs1 <= 0; bs2 <= 0; bs3 <= 0; be1 <= 0; be2 <= 0; be3 <= 0; end
        end
        S_SCAN: begin
            if (m1) begin an1 <= 1; tot1 <= tot1 + ks; if (!an1 || ks > bs1 || (ks == bs1 && ke[2:0] < be1)) begin bs1 <= ks; be1 <= ke[2:0]; end if (ke[2:0] == ev) ex1 <= 1; end
            if (m2) begin an2 <= 1; tot2 <= tot2 + ks; if (!an2 || ks > bs2 || (ks == bs2 && ke[2:0] < be2)) begin bs2 <= ks; be2 <= ke[2:0]; end if (ke[2:0] == ev) ex2 <= 1; end
            if (m3) begin an3 <= 1; tot3 <= tot3 + ks; if (!an3 || ks > bs3 || (ks == bs3 && ke[2:0] < be3)) begin bs3 <= ks; be3 <= ke[2:0]; end if (ke[2:0] == ev) ex3 <= 1; end
            if (si == KCAP - 1) st <= S_SEL; else si <= si + 1;
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
            else if (op == 3'd1 && sel_lv != 0 && !((sel_lv == 3 && ex3) || (sel_lv == 2 && ex2) || (sel_lv == 1 && ex1))) begin st <= S_CON; si <= 0; end
            else begin st <= S_UPD; end
        end
        S_CON: begin
            if (kv[si] && kkey[si][13:12] == vlevel && kkey[si][11:3] == ctx_vl && kcon[si] != 8'hFF) kcon[si] <= kcon[si] + 1;
            if (si == KCAP - 1) st <= S_UPD; else si <= si + 1;
        end
        S_UPD: begin lv <= 2'd1; st <= S_KL; si <= 0; k_hit <= 0; k_hasfree <= 0; k_hasvic <= 0; end
        S_KL: begin
            if (kvv && ke == key_lv && !k_hit) begin k_hit <= 1; k_hidx <= si; end
            if (!kvv && !k_hasfree) begin k_hasfree <= 1; k_fidx <= si; end
            if (kvv && (!k_hasvic || ks < k_vseen)) begin k_hasvic <= 1; k_vidx <= si; k_vseen <= ks; end
            if (si == KCAP - 1) st <= S_KD; else si <= si + 1;
        end
        S_KD: begin
            if (k_hit) begin if (kseen[k_hidx] != 8'hFF) kseen[k_hidx] <= kseen[k_hidx] + 1; next_level; end
            else if (op == 3'd2) begin add_known(8'd1); next_level; end
            else begin st <= S_CL; ci <= 0; c_hit <= 0; c_hasfree <= 0; c_hasvic <= 0; end
        end
        S_CL: begin
            if (cv[ci] && ckey[ci] == key_lv && !c_hit) begin c_hit <= 1; c_hidx <= ci; end
            if (!cv[ci] && !c_hasfree) begin c_hasfree <= 1; c_fidx <= ci; end
            if (cv[ci] && (!c_hasvic || ccnt[ci] < c_vcnt || (ccnt[ci] == c_vcnt && cage > c_vage))) begin c_hasvic <= 1; c_vidx <= ci; c_vcnt <= ccnt[ci]; c_vage <= cage; end
            if (ci == CCAP - 1) st <= S_CD; else ci <= ci + 1;
        end
        S_CD: begin
            if (c_newcnt >= n_prom) begin
                if (c_hit) begin cv[c_hidx] <= 0; n_cand <= n_cand - 1; end
                add_known({4'b0, c_newcnt}); n_promoted <= n_promoted + 1;
            end else if (c_hit) begin ccnt[c_hidx] <= c_newcnt; cst[c_hidx] <= c_newst; end
            else if (c_hasfree) begin cv[c_fidx] <= 1; ckey[c_fidx] <= key_lv; ccnt[c_fidx] <= 4'd1; cst[c_fidx] <= tt; n_cand <= n_cand + 1; end
            else begin ckey[c_vidx] <= key_lv; ccnt[c_vidx] <= 4'd1; cst[c_vidx] <= tt; n_dropc <= n_dropc + 1; end
            next_level;
        end
        S_FIN: begin h2 <= h1; h1 <= h0; h0 <= ev; if (hn != 2'd3) hn <= hn + 1; busy <= 0; done <= 1; st <= S_IDLE; end
        default: st <= S_IDLE;
        endcase
    end
endmodule
