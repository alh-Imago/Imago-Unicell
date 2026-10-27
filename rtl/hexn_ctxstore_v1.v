`timescale 1ns/1ps
`default_nettype none
// hexn_ctxstore_v1.v -- SDRAM-backed CONTEXT STORE for Hex-N layer 3. Must match tools/hexn_ctxstore_v1.py (the bit-true model) exactly, including the counters; read that file's header for the record layout, hash, probe order and weight rules.
// Operations (one at a time): RD(key) -> found + 14 slots;  OBS(key, fid) -> learn that follower fid followed context key (creates the context if new).  `done` pulses when finished; for RD `found` and `slots_out` are valid then.
// Memory: every context lives in SDRAM (hash table, 2^BB buckets of 8 words, 4 probes); an on-chip write-through direct-mapped cache of 2^CB records (block RAM) and a presence filter of 65,536 bits (block RAM) sit in front.
// SDRAM side: the command port of rtl/hexn_sdram_v1.v (cmd_valid held until cmd_ready, read data on rd_valid). After reset the store clears word 0 of every bucket (2^BB writes) before `ready` goes high.
// Counters (cnt_sel 0..8): ops, cache_hit, filter_skip, sd_probe, sd_rd, sd_wr, created, slot_evict, overflow. `err` latches if an SDRAM read never answers.
module hexn_ctxstore_v1 #(parameter BB = 17, parameter CB = 8) (
    input  wire         clk, input wire rst,
    input  wire         cmd_valid, input wire cmd_obs, input wire [30:0] cmd_key, input wire [7:0] cmd_fid, output wire cmd_ready,
    output reg          done, output reg found, output wire [223:0] slots_out,
    output reg          ready, output reg err,
    input  wire [3:0]   cnt_sel, output reg [31:0] cnt_val,
    output reg          sd_cmd_valid, output reg sd_cmd_we, output reg [20:0] sd_cmd_addr, output reg [31:0] sd_cmd_wdata, input wire sd_cmd_ready,
    input  wire         sd_rd_valid, input wire [31:0] sd_rd_data, input wire sd_init_done);
    // ---------------- RAMs ----------------
    reg [31:0] cmem [0:(1 << (CB + 3)) - 1]; reg [CB+2:0] caddr = 0; reg cwe = 0; reg [31:0] cwd = 0; reg [31:0] crd = 0;
    always @(posedge clk) begin if (cwe) cmem[caddr] <= cwd; crd <= cmem[caddr]; end
    reg fmem [0:65535]; reg [15:0] faddr = 0; reg fwe = 0; reg fwd = 0; reg frd = 0;
    always @(posedge clk) begin if (fwe) fmem[faddr] <= fwd; frd <= fmem[faddr]; end
    reg [BB-1:0] cbkt [0:(1 << CB) - 1]; reg [(1 << CB) - 1:0] cvalid = 0;
    // ---------------- working record ----------------
    reg [30:0] key = 0; reg [7:0] fid = 0; reg obs = 0; reg [223:0] rs = 224'd0; reg [BB-1:0] curb = 0;
    assign slots_out = rs;
    wire [31:0] P = {1'b0, key} * 32'h9E3779B1;
    wire [BB-1:0] hb = P[31:32 - BB]; wire [CB-1:0] hc = P[31:32 - CB]; wire [15:0] hf = P[23:8];
    // ---------------- update logic (OBS), combinational on rs and fid ----------------
    reg [223:0] ns; reg ev;              // ev: a non-empty slot was replaced
    integer j; reg m_any, e_any, sat; integer m_idx, e_idx, n_idx; reg [7:0] minw; reg [7:0] w, f; reg [223:0] hv;
    always @* begin
        m_any = 0; e_any = 0; m_idx = 0; e_idx = 0; n_idx = 0; minw = 8'hFF; sat = 0; ev = 0; ns = rs; hv = rs;
        for (j = 0; j < 14; j = j + 1) begin
            w = rs[16*j +: 8]; f = rs[16*j + 8 +: 8];
            if (w != 0 && f == fid && !m_any) begin m_any = 1; m_idx = j; if (w == 8'd255) sat = 1; end
            if (w == 0 && !e_any) begin e_any = 1; e_idx = j; end
            if (w < minw) begin minw = w; n_idx = j; end
        end
        if (m_any) begin
            if (sat) for (j = 0; j < 14; j = j + 1) begin w = rs[16*j +: 8]; hv[16*j +: 8] = (w != 0) ? ((w + 9'd1) >> 1) : 8'd0; end
            ns = hv; ns[16*m_idx +: 8] = hv[16*m_idx +: 8] + 8'd1;
        end else if (e_any) ns[16*e_idx +: 16] = {fid, 8'd1};
        else begin ns[16*n_idx +: 16] = {fid, 8'd1}; ev = 1; end
    end
    // ---------------- SDRAM engine ----------------
    localparam E_IDLE = 2'd0, E_REQ = 2'd1, E_WAIT = 2'd2;
    reg [1:0] es = E_IDLE; reg se_start = 0, se_we = 0, se_done = 0; reg [20:0] se_addr = 0; reg [31:0] se_wd = 0; reg [31:0] se_rdata = 0; reg [5:0] ewd = 0;
    // ---------------- counters ----------------
    reg [31:0] cnt [0:8];
    always @* cnt_val = cnt[cnt_sel > 4'd8 ? 4'd8 : cnt_sel];
    // ---------------- main state machine ----------------
    localparam S_RST = 5'd0, S_INIT = 5'd1, S_IDLE = 5'd2, S_C0 = 5'd3, S_C1 = 5'd4, S_C2 = 5'd5, S_CL0 = 5'd6, S_CL1 = 5'd7, S_CL2 = 5'd8, S_F0 = 5'd9, S_F1 = 5'd10, S_F2 = 5'd11,
               S_P0 = 5'd12, S_P1 = 5'd13, S_PL0 = 5'd14, S_PL1 = 5'd15, S_PL2 = 5'd16, S_ABS = 5'd17, S_DO = 5'd18, S_W0 = 5'd19, S_W1 = 5'd20, S_FIN = 5'd21, S_INITW = 5'd22;
    reg [4:0] st = S_RST; reg [3:0] wi = 0; reg [2:0] pi = 0; reg [BB:0] ib = 0; reg [16:0] ic = 0; reg fbit = 0; reg newc = 0;
    assign cmd_ready = (st == S_IDLE) && ready;
    integer k;
    initial for (k = 0; k < 9; k = k + 1) cnt[k] = 32'd0;
    always @(posedge clk) begin
        done <= 1'b0; se_start <= 1'b0; se_done <= 1'b0; cwe <= 1'b0; fwe <= 1'b0;
        // ---- SDRAM engine ----
        case (es)
        E_IDLE: if (se_start) begin sd_cmd_valid <= 1'b1; sd_cmd_we <= se_we; sd_cmd_addr <= se_addr; sd_cmd_wdata <= se_wd; es <= E_REQ; end
        E_REQ: if (sd_cmd_ready) begin sd_cmd_valid <= 1'b0; ewd <= 6'd0; if (se_we) begin se_done <= 1'b1; es <= E_IDLE; end else es <= E_WAIT; end
        E_WAIT: begin ewd <= ewd + 6'd1; if (sd_rd_valid) begin se_rdata <= sd_rd_data; se_done <= 1'b1; es <= E_IDLE; end else if (ewd == 6'd63) begin err <= 1'b1; se_done <= 1'b1; es <= E_IDLE; end end
        endcase
        case (st)
        S_RST: begin ready <= 1'b0; err <= 1'b0; cvalid <= 0; ic <= 17'd0; ib <= 0; for (k = 0; k < 9; k = k + 1) cnt[k] <= 32'd0; sd_cmd_valid <= 1'b0; es <= E_IDLE; st <= S_INIT; end
        // ---- initialisation: clear word 0 of every bucket, and the filter ----
        S_INIT: begin
            if (ic < 17'd65536) begin faddr <= ic[15:0]; fwd <= 1'b0; fwe <= 1'b1; ic <= ic + 17'd1; end
            if (sd_init_done && ib != (1 << BB)) begin se_start <= 1'b1; se_we <= 1'b1; se_addr <= {ib[BB-1:0], 3'b000}; se_wd <= 32'd0; st <= S_INITW; end
            else if (sd_init_done && ib == (1 << BB) && ic >= 17'd65536) begin ready <= 1'b1; st <= S_IDLE; end
        end
        S_INITW: begin
            if (ic < 17'd65536) begin faddr <= ic[15:0]; fwd <= 1'b0; fwe <= 1'b1; ic <= ic + 17'd1; end
            if (se_done) begin ib <= ib + 1'b1; st <= S_INIT; end
        end
        S_IDLE: if (cmd_valid && ready) begin key <= cmd_key; fid <= cmd_fid; obs <= cmd_obs; cnt[0] <= cnt[0] + 1; st <= S_C0; end
        // ---- cache lookup: word 0 of the line ----
        S_C0: begin caddr <= {hc, 3'b000}; st <= S_C1; end
        S_C1: st <= S_C2;
        S_C2: begin
            if (cvalid[hc] && crd == {1'b1, key}) begin cnt[1] <= cnt[1] + 1; curb <= cbkt[hc]; wi <= 4'd1; st <= S_CL0; end
            else begin faddr <= hf; st <= S_F0; end
        end
        S_CL0: begin caddr <= {hc, wi[2:0]}; st <= S_CL1; end
        S_CL1: st <= S_CL2;
        S_CL2: begin rs[32*(wi-1) +: 32] <= crd; if (wi == 4'd7) st <= S_DO; else begin wi <= wi + 4'd1; st <= S_CL0; end end
        // ---- filter ----
        S_F0: st <= S_F1;
        S_F1: st <= S_F2;
        S_F2: begin if (!frd) cnt[2] <= cnt[2] + 1; pi <= 3'd0; st <= S_P0; end
        // ---- SDRAM probe ----
        S_P0: begin se_start <= 1'b1; se_we <= 1'b0; se_addr <= {hb + {{(BB-3){1'b0}}, pi}, 3'b000}; cnt[3] <= cnt[3] + 1; cnt[4] <= cnt[4] + 1; st <= S_P1; end
        S_P1: if (se_done) begin
            if (!se_rdata[31]) begin curb <= hb + {{(BB-3){1'b0}}, pi}; newc <= 1'b1; st <= S_ABS; end
            else if (se_rdata[30:0] == key) begin
                curb <= hb + {{(BB-3){1'b0}}, pi}; cnt[4] <= cnt[4] + 7; caddr <= {hc, 3'b000}; cwd <= {1'b1, key}; cwe <= 1'b1; wi <= 4'd1; st <= S_PL0;
            end else if (pi == 3'd3) begin newc <= 1'b0; st <= S_ABS; end
            else begin pi <= pi + 3'd1; st <= S_P0; end
        end
        S_PL0: begin se_start <= 1'b1; se_we <= 1'b0; se_addr <= {curb, wi[2:0]}; st <= S_PL1; end
        S_PL1: if (se_done) begin rs[32*(wi-1) +: 32] <= se_rdata; caddr <= {hc, wi[2:0]}; cwd <= se_rdata; cwe <= 1'b1; if (wi == 4'd7) st <= S_PL2; else begin wi <= wi + 4'd1; st <= S_PL0; end end
        S_PL2: begin cvalid[hc] <= 1'b1; cbkt[hc] <= curb; st <= S_DO; end      // the last cache word write is in flight; DO does not touch the cache port
        // ---- context absent ----
        S_ABS: begin
            rs <= 224'd0;
            if (!obs) begin found <= 1'b0; done <= 1'b1; st <= S_IDLE; end
            else if (!newc) begin cnt[8] <= cnt[8] + 1; found <= 1'b0; done <= 1'b1; st <= S_IDLE; end
            else begin cnt[6] <= cnt[6] + 1; faddr <= hf; fwd <= 1'b1; fwe <= 1'b1; st <= S_DO; end
        end
        // ---- act on the record ----
        S_DO: begin
            if (!obs) begin found <= 1'b1; done <= 1'b1; st <= S_IDLE; end
            else begin rs <= ns; if (ev) cnt[7] <= cnt[7] + 1; wi <= 4'd0; st <= S_W0; end
        end
        // ---- write-through: cache line and SDRAM record, word by word ----
        S_W0: begin
            caddr <= {hc, wi[2:0]}; cwd <= (wi == 4'd0) ? {1'b1, key} : rs[32*(wi-1) +: 32]; cwe <= 1'b1;
            se_start <= 1'b1; se_we <= 1'b1; se_addr <= {curb, wi[2:0]}; se_wd <= (wi == 4'd0) ? {1'b1, key} : rs[32*(wi-1) +: 32]; cnt[5] <= cnt[5] + 1; st <= S_W1;
        end
        S_W1: if (se_done) begin if (wi == 4'd7) st <= S_FIN; else begin wi <= wi + 4'd1; st <= S_W0; end end
        S_FIN: begin cvalid[hc] <= 1'b1; cbkt[hc] <= curb; found <= 1'b1; done <= 1'b1; st <= S_IDLE; end
        default: st <= S_RST;
        endcase
        if (rst) st <= S_RST;
    end
endmodule
