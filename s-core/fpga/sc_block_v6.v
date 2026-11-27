// sc_block_v6.v - sc_block_v5 with the dispatcher sc_sys_v22 (a fused unit waits for its previous shared store; ledger #1531).  Cloned from sc_block_v5.v (left as proven).
// sc_block_v6.v - sc_block_v4 with the dispatcher sc_sys_v22 (bound fusion unit steals free code-store clocks, code store in block RAM; ledger #1519).  Cloned from sc_block_v4.v (left as proven).
// sc_block_v6.v - sc_block_v3 with the dispatcher sc_sys_v22 (no falling-edge registers in front of the block RAMs; ledger #1477).  Cloned from sc_block_v3.v (left as proven).
// sc_block_v6.v - sc_block_v2 with the dispatcher sc_sys_v22 (NU fusion units per block; ledger #1386).  Cloned from sc_block_v2.v (left as proven).  Needs uc_unitw<2**ULW>, uc_unith<2**ULW>.
// sc_block_v2.v - sc_block.v with the dispatcher sc_sys_v16 (one fusion unit per block, parameters FZ, ULW; ledger #1378).  Cloned from sc_block.v (left as proven).  Needs uc_unitw<2**ULW>, uc_unith<2**ULW>.
// sc_block.v - ONE BLOCK of the S-Core: the dispatcher / slices / shared RAM / code store (sc_sys_v15), its own copy engine (far_copy), its own batch
// sequencer (batch_seq_v2) and the merge of host commands with the sequencer's commands.  Everything in here is exactly what sc_top_k7_v7.v wires around
// its single sc_sys_v15; this file only puts it in a box with a port list, so that several blocks can sit side by side (ledger #1347).  The dispatcher
// and the RAM wiring stay inside the box.  What leaves the box: host commands in (already gated to this block by the top), status out, and ONE far-RAM
// request port (req_*) that the top's arbiter serves.  Each block keeps its own copy window (D command) and its own hold.
// Cloned logic from sc_top_k7_v7.v (left as proven).  Needs sc_sys_v15.v, fit_search_tree.v, far_copy.v, batch_seq_v2.v.
module sc_block_v6 #(
    parameter S = 16, parameter QD = 16, parameter IMEM_WORDS = 128, parameter DMW = 16, parameter DSH = 256, parameter SHL = 14,
    parameter PROF = 64, parameter LONGEST = 1, parameter FINE = 0, parameter FZ = 1, parameter ULW = 2, parameter NU = 2
) (
    input  wire        clk, rst, hold,
    // host commands (from the bridge, gated to this block)
    input  wire        b_h_push, b_h_crit,
    input  wire [15:0] b_h_tid, b_h_code,
    input  wire [2:0]  b_h_lw,
    input  wire [5:0]  b_h_prog,
    input  wire        b_imem_we,
    input  wire [15:0] b_imem_wa,
    input  wire [31:0] b_imem_wd,
    input  wire [15:0] q_tid,
    input  wire        b_rg_we,
    input  wire [5:0]  b_rg_prog,
    input  wire [15:0] b_rg_cbase, b_rg_clen, b_rg_dlen,
    input  wire        b_lb_we,
    input  wire [15:0] b_lb_base, b_lb_len,
    input  wire        b_rs_we,
    input  wire [5:0]  b_rs_prog,
    input  wire [15:0] b_rs_base, b_rs_len,
    input  wire        b_dh_we, b_dh_rd,
    input  wire [15:0] b_dh_a,
    input  wire [31:0] b_dh_wd,
    input  wire        b_f_start,
    input  wire [1:0]  b_f_dir,
    input  wire [15:0] b_f_near, b_f_cnt,
    input  wire [20:0] b_f_far,
    input  wire        d_we,
    input  wire [20:0] d_lbase,
    input  wire [21:0] d_llen,
    input  wire        fh_v, fh_we,
    input  wire [20:0] fh_a,
    input  wire [31:0] fh_wd,
    input  wire        hs_start,
    input  wire [20:0] hs_addr,
    input  wire        init_done,
    // status to the bridge
    output wire [31:0] dh_q,
    output wire        dh_qv, dh_busy,
    output wire [31:0] q_start, q_end, q_a0, q_arr,
    output wire        q_trap,
    output wire [1:0]  q_state,
    output wire [5:0]  q_slot,
    output wire [24:0] q_pred,
    output wire [31:0] o_cyc, o_done, o_lerr, o_disp,
    output wire [63:0] o_busy, o_blocked, o_tail, o_search,
    output wire [S-1:0] o_busy_l,
    output wire [32*S-1:0] st_sl,
    output wire [15:0] st_qc, st_qb,
    output wire [40*S-1:0] st_bs,
    output wire [2:0]  q_cause,
    output wire [15:0] q_taddr,
    output wire        f_busy, f_done, f_ign,
    output wire [2:0]  f_err,
    output wire [31:0] f_moved, f_clocks,
    output wire        s_busy, s_done,
    output wire [3:0]  s_err,
    output wire [15:0] s_steps,
    output wire [31:0] s_tag, s_clk, s_cclk, s_wclk,
    output wire [20:0] s_pcc,
    output wire [3:0]  s_opc,
    output wire        fh_acc,
    output wire        fh_ackv,
    output wire [31:0] fh_ackd,
    // the single far-RAM request port (served by the top's arbiter)
    output wire        req_v, req_we,
    output wire [20:0] req_a,
    output wire [31:0] req_wd,
    input  wire        req_rdy, ack_v,
    input  wire [31:0] ack_d
);
    // ---- merge of bridge and batch sequencer (the sequencer wins while it runs)
    wire        s_push, s_rg, s_rs, s_lb, s_fstart, s_rv, s_crit;
    wire [15:0] s_tid, s_code, s_cbase, s_clen, s_dlen, s_base, s_len, s_lbase, s_llen, s_near, s_cnt;
    wire [2:0]  s_lw; wire [5:0] s_hprog, s_rgprog, s_rsprog; wire [1:0] s_dir; wire [20:0] s_far, s_ra;
    wire        h_push, h_crit, rg_we, rs_we, lb_we, f_start, imem_we, dh_we, dh_rd;
    wire [15:0] h_tid, h_code, rg_cbase, rg_clen, rg_dlen, rs_base, rs_len, lb_base, lb_len, f_near, f_cnt, imem_wa, dh_a;
    wire [2:0]  h_lw; wire [5:0] h_prog, rg_prog, rs_prog; wire [1:0] f_dir; wire [20:0] f_far; wire [31:0] imem_wd, dh_wd;
    assign h_push = b_h_push | s_push;   assign h_tid = s_busy ? s_tid : b_h_tid;   assign h_code = s_busy ? s_code : b_h_code;   assign h_lw = s_busy ? s_lw : b_h_lw;
    assign h_crit = s_busy ? s_crit : b_h_crit;   assign h_prog = s_busy ? s_hprog : b_h_prog;
    assign rg_we = b_rg_we | s_rg;   assign rg_prog = s_busy ? s_rgprog : b_rg_prog;   assign rg_cbase = s_busy ? s_cbase : b_rg_cbase;   assign rg_clen = s_busy ? s_clen : b_rg_clen;   assign rg_dlen = s_busy ? s_dlen : b_rg_dlen;
    assign rs_we = b_rs_we | s_rs;   assign rs_prog = s_busy ? s_rsprog : b_rs_prog;   assign rs_base = s_busy ? s_base : b_rs_base;   assign rs_len = s_busy ? s_len : b_rs_len;
    assign lb_we = b_lb_we | s_lb;   assign lb_base = s_busy ? s_lbase : b_lb_base;   assign lb_len = s_busy ? s_llen : b_lb_len;
    assign f_start = b_f_start | s_fstart;   assign f_dir = s_busy ? s_dir : b_f_dir;   assign f_near = s_busy ? s_near : b_f_near;   assign f_far = s_busy ? s_far : b_f_far;   assign f_cnt = s_busy ? s_cnt : b_f_cnt;

    // ---- this block's copy window (written by the D command while this block is selected; not cleared by reset, as in v10)
    reg [20:0] lim_b = 21'd0; reg [21:0] lim_l = 22'd0;
    always @(posedge clk) if (d_we) begin lim_b <= d_lbase; lim_l <= d_llen; end

    // ---- far RAM: who may use the port; the copy engine owns the shared RAM host port and the code-store write port while it runs
    wire        e_dh_we, e_dh_rd, e_imem_we, e_rv, e_rwe; wire [15:0] e_dh_a, e_imem_wa; wire [31:0] e_dh_wd, e_imem_wd, e_rwd; wire [20:0] e_ra;
    assign req_v  = f_busy ? e_rv  : s_rv ? 1'b1 : fh_v;                // while a copy runs it owns the far RAM
    assign req_we = f_busy ? e_rwe : s_rv ? 1'b0 : fh_we;
    assign req_a  = f_busy ? e_ra  : s_rv ? s_ra : fh_a;
    assign req_wd = f_busy ? e_rwd : fh_wd;
    assign fh_acc = fh_v && req_rdy && !f_busy && !s_rv;
    assign fh_ackv = ack_v;  assign fh_ackd = ack_d;
    assign dh_we  = f_busy ? e_dh_we : b_dh_we;
    assign dh_rd  = f_busy ? e_dh_rd : b_dh_rd;
    assign dh_a   = f_busy ? e_dh_a  : b_dh_a;
    assign dh_wd  = f_busy ? e_dh_wd : b_dh_wd;
    assign imem_we = b_imem_we | e_imem_we;
    assign imem_wa = e_imem_we ? e_imem_wa : b_imem_wa;
    assign imem_wd = e_imem_we ? e_imem_wd : b_imem_wd;

    far_copy #(.DSH(DSH), .IMW(IMEM_WORDS)) fc (
        .clk(clk), .rst(rst), .start(f_start), .dir(f_dir), .sh_a(f_near), .far_a(f_far), .count(f_cnt), .lim_base(lim_b), .lim_len(lim_l), .init_done(init_done),
        .busy(f_busy), .done(f_done), .ignored(f_ign), .err(f_err), .moved(f_moved), .clocks(f_clocks),
        .dh_we(e_dh_we), .dh_rd(e_dh_rd), .dh_a(e_dh_a), .dh_wd(e_dh_wd), .dh_q(dh_q), .dh_qv(dh_qv), .dh_busy(dh_busy),
        .ie_we(e_imem_we), .ie_wa(e_imem_wa), .ie_wd(e_imem_wd),
        .req_v(e_rv), .req_we(e_rwe), .req_a(e_ra), .req_wd(e_rwd), .req_rdy(req_rdy), .ack_v(ack_v), .ack_d(ack_d));

    batch_seq_v2 bs (
        .clk(clk), .rst(rst), .start(hs_start), .start_a(hs_addr), .init_done(init_done), .busy(s_busy), .done(s_done), .err(s_err), .steps(s_steps), .tag(s_tag),
        .req_v(s_rv), .req_a(s_ra), .req_rdy(req_rdy), .ack_v(ack_v), .ack_d(ack_d),
        .c_start(s_fstart), .c_dir(s_dir), .c_near(s_near), .c_far(s_far), .c_cnt(s_cnt), .c_busy(f_busy), .c_done(f_done), .c_err(f_err),
        .h_push(s_push), .h_tid(s_tid), .h_code(s_code), .h_lw(s_lw), .h_crit(s_crit), .h_prog(s_hprog),
        .rg_we(s_rg), .rg_prog(s_rgprog), .rg_cbase(s_cbase), .rg_clen(s_clen), .rg_dlen(s_dlen),
        .rs_we(s_rs), .rs_prog(s_rsprog), .rs_base(s_base), .rs_len(s_len),
        .lb_we(s_lb), .lb_base(s_lbase), .lb_len(s_llen), .n_done(o_done), .clk_total(s_clk), .clk_copy(s_cclk), .clk_wait(s_wclk), .cur_pc(s_pcc), .cur_op(s_opc));

    sc_sys_v22 #(.S(S), .QD(QD), .IMEM_WORDS(IMEM_WORDS), .DMW(DMW), .DSH(DSH), .SHL(SHL), .PROF(PROF), .EVB(3),
                .PRIO(1), .BESTFIT(1), .LONGEST(LONGEST), .FINE(FINE), .FZ(FZ), .ULW(ULW), .NU(NU)) sys (
        .clk(clk), .rst(rst), .hold(hold), .rg_we(rg_we), .rg_prog(rg_prog), .rg_cbase(rg_cbase), .rg_clen(rg_clen), .rg_dlen(rg_dlen),
        .lb_we(lb_we), .lb_base(lb_base), .lb_len(lb_len), .rs_we(rs_we), .rs_prog(rs_prog), .rs_base(rs_base), .rs_len(rs_len), .dh_we(dh_we), .dh_rd(dh_rd), .dh_a(dh_a), .dh_wd(dh_wd), .dh_q(dh_q), .dh_qv(dh_qv), .dh_busy(dh_busy),
        .h_push(h_push), .h_tid(h_tid), .h_code(h_code), .h_lw(h_lw), .h_crit(h_crit), .h_prog(h_prog),
        .imem_we(imem_we), .imem_wa(imem_wa), .imem_wd(imem_wd),
        .q_tid(q_tid), .q_start(q_start), .q_end(q_end), .q_a0(q_a0), .q_arr(q_arr), .q_trap(q_trap),
        .q_state(q_state), .q_slot(q_slot), .q_pred(q_pred),
        .o_cyc(o_cyc), .o_done(o_done), .o_lerr(o_lerr), .o_disp(o_disp),
        .o_busy(o_busy), .o_blocked(o_blocked), .o_tail(o_tail), .o_search(o_search), .o_busy_l(o_busy_l), .st_sl(st_sl), .st_qc(st_qc), .st_qb(st_qb), .st_bs(st_bs), .q_cause(q_cause), .q_taddr(q_taddr),
        .ev_pl_we(1'b0), .ev_pl_id(8'd0), .ev_pl_data(32'd0), .ev_set(1'b0), .ev_set_id(8'd0));
endmodule
