// blk_cmd_v1.v - the command-decoding half of host_bridge_v12, moved INTO each block's side (ledger #1459).  The bridge now broadcasts ONE raw command to all blocks
//   (c_v strobe, c_cmd byte, c_a = up to 8 argument bytes: 73 wires) instead of about 450 decoded wires; the block whose select line (sel) is set decodes it here.
//   Timing is the same as in v12: the strobe c_v is high in the cycle after the bridge's EXEC (when v12's pulse registers were high), and every output below is
//   the value v12's register would have shown in that cycle (a pulse, or the new level in that cycle and held afterwards).  Pulses: *_we, h_push, dh_rd, f_start, d_we,
//   s_start.  Levels (held until the next command that sets them): the rest.  fh_v is held until the far-RAM host port accepts (fh_acc), as v12's FACC state did.
//   The decode lines are the lines of v12's EXEC case, with a[n] -> a<n>.  Needs nothing else.
module blk_cmd_v1 (
    input  wire        clk, sel,
    input  wire        c_v,
    input  wire [7:0]  c_cmd,
    input  wire [63:0] c_a,
    input  wire        fh_acc,
    output wire        h_push,  output wire [15:0] h_tid, h_code, output wire [2:0] h_lw, output wire h_crit, output wire [5:0] h_prog,
    output wire        imem_we, output wire [15:0] imem_wa, output wire [31:0] imem_wd,
    output wire [15:0] q_tid,
    output wire        rg_we,   output wire [5:0] rg_prog, output wire [15:0] rg_cbase, rg_clen, rg_dlen,
    output wire        rs_we,   output wire [5:0] rs_prog, output wire [15:0] rs_base, rs_len,
    output wire        lb_we,   output wire [15:0] lb_base, lb_len,
    output wire        dh_we, dh_rd, output wire [15:0] dh_a, output wire [31:0] dh_wd,
    output wire        f_start, output wire [1:0] f_dir, output wire [15:0] f_near, output wire [20:0] f_far, output wire [15:0] f_cnt,
    output wire        d_we,    output wire [20:0] f_lbase, output wire [21:0] f_llen,
    output wire        s_start, output wire [20:0] s_addr,
    output wire        fh_v, fh_we, output wire [20:0] fh_a, output wire [31:0] fh_wd
);
    wire go = c_v & sel;
    wire [7:0] a0 = c_a[7:0], a1 = c_a[15:8], a2 = c_a[23:16], a3 = c_a[31:24], a4 = c_a[39:32], a5 = c_a[47:40], a6 = c_a[55:48], a7 = c_a[63:56];
    wire cW = go && c_cmd == "W", cP = go && c_cmd == "P", cB = go && c_cmd == "B", cQ = go && (c_cmd == "Q" || c_cmd == "E"), cM = go && c_cmd == "M", cY = go && c_cmd == "Y",
         cX = go && c_cmd == "X", cL = go && c_cmd == "L", cF = go && c_cmd == "F", cJ = go && c_cmd == "J", cD = go && c_cmd == "D", cw = go && c_cmd == "w", cr = go && c_cmd == "r";
    // held copies of the level outputs
    reg [15:0] h_tid_r = 0, h_code_r = 0; reg [2:0] h_lw_r = 0; reg h_crit_r = 0; reg [5:0] h_prog_r = 0; reg [15:0] imem_wa_r = 0; reg [31:0] imem_wd_r = 0; reg [15:0] q_tid_r = 0;
    reg [5:0] rg_prog_r = 0; reg [15:0] rg_cbase_r = 0, rg_clen_r = 0, rg_dlen_r = 0; reg [5:0] rs_prog_r = 0; reg [15:0] rs_base_r = 0, rs_len_r = 0; reg [15:0] lb_base_r = 0, lb_len_r = 0;
    reg [15:0] dh_a_r = 0; reg [31:0] dh_wd_r = 0; reg [1:0] f_dir_r = 0; reg [15:0] f_near_r = 0; reg [20:0] f_far_r = 0; reg [15:0] f_cnt_r = 0; reg [20:0] f_lbase_r = 0; reg [21:0] f_llen_r = 0;
    reg [20:0] s_addr_r = 0; reg fh_v_r = 0, fh_we_r = 0; reg [20:0] fh_a_r = 0; reg [31:0] fh_wd_r = 0;
    // new values (v12's EXEC assignments)
    wire [15:0] n_h_tid = {a1, a0}, n_h_code = {a3, a2}; wire [2:0] n_h_lw = a4[2:0]; wire n_h_crit = a5[0]; wire [5:0] n_h_prog = a6[5:0];
    wire [15:0] n_imem_wa = {a1, a0}; wire [31:0] n_imem_wd = {a5, a4, a3, a2};
    wire [5:0] n_rg_prog = a0[5:0]; wire [15:0] n_rg_cbase = {a2, a1}, n_rg_clen = {a4, a3}, n_rg_dlen = {a6, a5};
    wire [5:0] n_rs_prog = a0[5:0]; wire [15:0] n_rs_base = {a2, a1}, n_rs_len = {a4, a3};
    wire [15:0] n_lb_base = {a1, a0}, n_lb_len = {a3, a2};
    wire [15:0] n_dh_a = {a1, a0}; wire [31:0] n_dh_wd = {a5, a4, a3, a2};
    wire [1:0] n_f_dir = a0[1:0]; wire [15:0] n_f_near = {a2, a1}; wire [20:0] n_f_far = {a5[4:0], a4, a3}; wire [15:0] n_f_cnt = {a7, a6};
    wire [20:0] n_f_lbase = {a2[4:0], a1, a0}; wire [21:0] n_f_llen = {a5[5:0], a4, a3};
    wire [20:0] n_s_addr = {a2[4:0], a1, a0};
    wire [20:0] n_fh_a = {a2[4:0], a1, a0}; wire [31:0] n_fh_wd = {a6, a5, a4, a3};
    // outputs: the new value in the strobe cycle, the held one otherwise
    assign h_push = cP; assign imem_we = cW; assign rg_we = cB; assign rs_we = cX; assign lb_we = cY; assign dh_we = cM; assign dh_rd = cL; assign f_start = cF; assign d_we = cD; assign s_start = cJ;
    assign h_tid = cP ? n_h_tid : h_tid_r;  assign h_code = cP ? n_h_code : h_code_r;  assign h_lw = cP ? n_h_lw : h_lw_r;  assign h_crit = cP ? n_h_crit : h_crit_r;  assign h_prog = cP ? n_h_prog : h_prog_r;
    assign imem_wa = cW ? n_imem_wa : imem_wa_r;  assign imem_wd = cW ? n_imem_wd : imem_wd_r;
    assign q_tid = cQ ? n_h_tid : q_tid_r;
    assign rg_prog = cB ? n_rg_prog : rg_prog_r;  assign rg_cbase = cB ? n_rg_cbase : rg_cbase_r;  assign rg_clen = cB ? n_rg_clen : rg_clen_r;  assign rg_dlen = cB ? n_rg_dlen : rg_dlen_r;
    assign rs_prog = cX ? n_rs_prog : rs_prog_r;  assign rs_base = cX ? n_rs_base : rs_base_r;  assign rs_len = cX ? n_rs_len : rs_len_r;
    assign lb_base = cY ? n_lb_base : lb_base_r;  assign lb_len = cY ? n_lb_len : lb_len_r;
    assign dh_a = (cM || cL) ? n_dh_a : dh_a_r;  assign dh_wd = cM ? n_dh_wd : dh_wd_r;
    assign f_dir = cF ? n_f_dir : f_dir_r;  assign f_near = cF ? n_f_near : f_near_r;  assign f_far = cF ? n_f_far : f_far_r;  assign f_cnt = cF ? n_f_cnt : f_cnt_r;
    assign f_lbase = cD ? n_f_lbase : f_lbase_r;  assign f_llen = cD ? n_f_llen : f_llen_r;
    assign s_addr = cJ ? n_s_addr : s_addr_r;
    assign fh_v = (cw || cr) | fh_v_r;  assign fh_we = (cw || cr) ? cw : fh_we_r;  assign fh_a = (cw || cr) ? n_fh_a : fh_a_r;  assign fh_wd = cw ? n_fh_wd : fh_wd_r;
    always @(posedge clk) begin
        if (cP) begin h_tid_r <= n_h_tid; h_code_r <= n_h_code; h_lw_r <= n_h_lw; h_crit_r <= n_h_crit; h_prog_r <= n_h_prog; end
        if (cW) begin imem_wa_r <= n_imem_wa; imem_wd_r <= n_imem_wd; end
        if (cQ) q_tid_r <= n_h_tid;
        if (cB) begin rg_prog_r <= n_rg_prog; rg_cbase_r <= n_rg_cbase; rg_clen_r <= n_rg_clen; rg_dlen_r <= n_rg_dlen; end
        if (cX) begin rs_prog_r <= n_rs_prog; rs_base_r <= n_rs_base; rs_len_r <= n_rs_len; end
        if (cY) begin lb_base_r <= n_lb_base; lb_len_r <= n_lb_len; end
        if (cM || cL) dh_a_r <= n_dh_a;
        if (cM) dh_wd_r <= n_dh_wd;
        if (cF) begin f_dir_r <= n_f_dir; f_near_r <= n_f_near; f_far_r <= n_f_far; f_cnt_r <= n_f_cnt; end
        if (cD) begin f_lbase_r <= n_f_lbase; f_llen_r <= n_f_llen; end
        if (cJ) s_addr_r <= n_s_addr;
        if (cw || cr) begin fh_we_r <= cw; fh_a_r <= n_fh_a; if (cw) fh_wd_r <= n_fh_wd; end
        fh_v_r <= fh_v & ~fh_acc;
    end
endmodule
