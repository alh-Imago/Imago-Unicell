// sc_top_k7_v4.v - sc_top_k7_v2.v (far RAM as ports, for the DDR3 build) with the fixed host link jtag_link_v2 (2026-11-17, see jtag_link_v2.v).  Nothing else changed; v2 is untouched.
// sc_top_k7_v2.v - sc_top_k7_v1 with the far RAM brought out as ports (fr_*) instead of the block RAM inside; everything else is unchanged.  Cloned from
// sc_top_k7_v1.v (which is untouched).  Used by the DDR3 build, where the far RAM is farram_ddr3_v1 (GPL-3.0 folder k7/ddr3_gpl3).  This file has no GPL code.
// sc_top_k7_v1.v - S-Core pool for the Kintex-7 YPCB-00338-1P1 card (XC7K480T).  Cloned from sc_top_pool15.v; pool15 is untouched.
// Differences: 50 MHz SYS_CLK (AA28); no UART: the host talks through the JTAG user register 1 (jtag_link_v1 + BSCANE2); far RAM is block RAM
// (farram_bram_v1, same interface as sdram_ctl) instead of the Tang's SDRAM; three LEDs, active high (P30 red, M30 green, N30 yellow).
// Cores, sc_sys_v12, copy engine (far_copy) and batch sequencer (batch_seq_v2) are unchanged.  Bridge: host_bridge_v10 (version reply 12 as v9).
//   LED0 (red)    launch error or a job trapped          LED1 (green) heartbeat (about 1.5 Hz)          LED2 (yellow) JTAG link active or a task has finished
// sc_top_pool15.v - sc_top_pool14 with batch_seq_v2 (clock counters, live progress) and host_bridge_v9 (A answers 24 bytes, version 12).  Cloned from sc_top_pool14.v.
// sc_top_pool15.v - sc_top_pool13 plus the batch sequencer (batch_seq) and host_bridge_v9 (commands J start / A status).  The sequencer shares the far RAM read port,
// the copy engine start and the scheduler's own host commands (P, B, X, Y) with the bridge: the bridge's outputs and the sequencer's are merged, and while the
// sequencer runs it has priority on every shared signal (the host only polls A).  Cores, sc_sys_v12, copy engine and SDRAM controller are unchanged.
// sc_top_pool13.v - sc_top_pool12 plus the FAR RAM: the onboard 8 MB SDRAM (sdram_ctl), a copy engine (far_copy) and the far RAM commands of
// host_bridge_v7.  The cores and sc_sys_v12 are unchanged: the engine only uses the host port of the shared RAM (which yields to the cores) and the
// host's code-store write port.  The SDRAM controller is reset by the power-on reset only, so far RAM contents and settings survive a core reset (R).
// sc_top_pool12.v - sc_top_pool11 with the status / usage / trap-cause read-out (sc_sys_v12 + host_bridge_v7).
// sc_top_pool11.v - sc_top_pool10 with the shared code library window (sc_sys_v12 + host_bridge_v7).
// sc_top_pool11.v - sc_top_pool9 with the shared data RAM (sc_sys_v12 + host_bridge_v7).
// sc_top_pool11.v - sc_top_pool8 with regions (sc_sys_v12 + host_bridge_v7).
// sc_top_pool11.v - sc_top_pool6 with hold/go (sc_sys_v12 + host_bridge_v7). LED 5 (heartbeat) is unchanged.
// sc_top_tang.v - S-Core single-set build for the Sipeed Tang Nano 20K.
// 27 MHz board clock, UART to the PC through the on-board BL616, six LEDs (active low).
//   led_n[0] heartbeat   led_n[1] some core is running   led_n[2] UART rx activity
//   led_n[3] UART tx activity   led_n[4] launch error (should never light)   led_n[5] at least one task finished
// Power-on reset only (the S1/S2 buttons are the chip's MODE pins: not used).
module sc_top_k7_v4 #(
    parameter S = 1, parameter QD = 16, parameter IMEM_WORDS = 128, parameter DMW = 16, parameter DSH = 256, parameter SHL = 14,
    parameter PROF = 64, parameter LONGEST = 1, parameter FINE = 0, parameter FAR_AW = 16, parameter JK = 32, parameter RXGAP = 512
) (
    input  wire       SYS_CLK,
    output wire [2:0] led,
    // far RAM, brought out (v2): same request / acknowledge interface as sdram_ctl / farram_bram_v1
    output wire        fr_v, fr_we,
    output wire [20:0] fr_a,
    output wire [31:0] fr_wd,
    input  wire        fr_rdy, fr_ackv, fr_init, fr_busy,
    input  wire [31:0] fr_ackd,
    output wire        por_ok         // power-on reset finished (high = the pool is running)
);
    wire clk = SYS_CLK;
    reg [7:0] por = 8'd0;
    wire por_done = (por == 8'hFF);
    always @(posedge clk) if (!por_done) por <= por + 1'b1;
    wire lb_we; wire [15:0] lb_base, lb_len;
    wire soft_rst, hold, rg_we, rs_we, dh_we, dh_rd, dh_qv, dh_busy;
    wire b_dh_we, b_dh_rd, b_imem_we; wire [15:0] b_dh_a, b_imem_wa; wire [31:0] b_dh_wd, b_imem_wd;
    wire [5:0] rs_prog;
    wire [15:0] rs_base, rs_len, dh_a;
    wire [31:0] dh_wd, dh_q;
    wire [5:0] rg_prog;
    wire [15:0] rg_cbase, rg_clen, rg_dlen;
    wire rst = !por_done | soft_rst;

    wire        h_push, h_crit, imem_we, act_rx, act_tx, q_trap;
    wire [15:0] h_tid, h_code, imem_wa, q_tid;
    wire [2:0]  h_lw;
    wire [5:0]  h_prog, q_slot;
    wire [31:0] imem_wd, q_start, q_end, q_a0, q_arr, o_cyc, o_done, o_lerr, o_disp;
    wire [1:0]  q_state;
    wire [24:0] q_pred;
    wire [63:0] o_busy, o_blocked, o_tail, o_search;
    wire [S-1:0] o_busy_l;
    wire [32*S-1:0] st_sl; wire [15:0] st_qc, st_qb; wire [40*S-1:0] st_bs; wire [2:0] q_cause; wire [15:0] q_taddr;


    // ---- merge of bridge and batch sequencer (the sequencer wins while it runs)
    wire        b_h_push, b_h_crit, b_rg_we, b_rs_we, b_lb_we, b_f_start, s_start, s_busy, s_done;
    wire [15:0] b_h_tid, b_h_code, b_rg_cbase, b_rg_clen, b_rg_dlen, b_rs_base, b_rs_len, b_lb_base, b_lb_len, b_f_near, b_f_cnt, s_steps;
    wire [2:0]  b_h_lw; wire [5:0] b_h_prog, b_rg_prog, b_rs_prog; wire [1:0] b_f_dir; wire [20:0] b_f_far, s_addr; wire [3:0] s_err; wire [31:0] s_tag;
    wire [31:0] s_clk, s_cclk, s_wclk; wire [20:0] s_pcc; wire [3:0] s_opc;
    wire        s_push, s_rg, s_rs, s_lb, s_fstart, s_rv; wire [15:0] s_tid, s_code, s_cbase, s_clen, s_dlen, s_base, s_len, s_lbase, s_llen, s_near, s_cnt;
    wire [2:0]  s_lw; wire [5:0] s_hprog, s_rgprog, s_rsprog; wire s_crit; wire [1:0] s_dir; wire [20:0] s_far, s_ra;
    assign h_push = b_h_push | s_push;   assign h_tid = s_busy ? s_tid : b_h_tid;   assign h_code = s_busy ? s_code : b_h_code;   assign h_lw = s_busy ? s_lw : b_h_lw;
    assign h_crit = s_busy ? s_crit : b_h_crit;   assign h_prog = s_busy ? s_hprog : b_h_prog;
    assign rg_we = b_rg_we | s_rg;   assign rg_prog = s_busy ? s_rgprog : b_rg_prog;   assign rg_cbase = s_busy ? s_cbase : b_rg_cbase;   assign rg_clen = s_busy ? s_clen : b_rg_clen;   assign rg_dlen = s_busy ? s_dlen : b_rg_dlen;
    assign rs_we = b_rs_we | s_rs;   assign rs_prog = s_busy ? s_rsprog : b_rs_prog;   assign rs_base = s_busy ? s_base : b_rs_base;   assign rs_len = s_busy ? s_len : b_rs_len;
    assign lb_we = b_lb_we | s_lb;   assign lb_base = s_busy ? s_lbase : b_lb_base;   assign lb_len = s_busy ? s_llen : b_lb_len;
    assign f_start = b_f_start | s_fstart;   assign f_dir = s_busy ? s_dir : b_f_dir;   assign f_near = s_busy ? s_near : b_f_near;   assign f_far = s_busy ? s_far : b_f_far;   assign f_cnt = s_busy ? s_cnt : b_f_cnt;

    host_bridge_v10 #(.S(S), .IMEM_WORDS(IMEM_WORDS), .DMW(DMW), .DSH(DSH), .SHL(SHL)) br (
        .clk(clk), .rb_data(rb_data), .rb_valid(rb_valid), .tb_data(tb_data), .tb_send(tb_send), .tb_busy(tb_busy),
        .h_push(b_h_push), .h_tid(b_h_tid), .h_code(b_h_code), .h_lw(b_h_lw), .h_crit(b_h_crit), .h_prog(b_h_prog),
        .imem_we(b_imem_we), .imem_wa(b_imem_wa), .imem_wd(b_imem_wd), .q_tid(q_tid), .soft_rst(soft_rst), .hold(hold), .rg_we(b_rg_we), .rg_prog(b_rg_prog), .rg_cbase(b_rg_cbase), .rg_clen(b_rg_clen), .rg_dlen(b_rg_dlen),
        .lb_we(b_lb_we), .lb_base(b_lb_base), .lb_len(b_lb_len), .rs_we(b_rs_we), .rs_prog(b_rs_prog), .rs_base(b_rs_base), .rs_len(b_rs_len), .dh_we(b_dh_we), .dh_rd(b_dh_rd), .dh_a(b_dh_a), .dh_wd(b_dh_wd), .dh_q(dh_q), .dh_qv(dh_qv), .dh_busy(dh_busy | f_busy | s_busy),
        .q_start(q_start), .q_end(q_end), .q_a0(q_a0), .q_arr(q_arr), .q_trap(q_trap), .q_state(q_state),
        .q_slot(q_slot), .q_pred(q_pred),
        .o_cyc(o_cyc), .o_done(o_done), .o_lerr(o_lerr), .o_disp(o_disp),
        .o_busy(o_busy), .o_blocked(o_blocked), .o_tail(o_tail), .o_search(o_search), .o_busy_l(o_busy_l), .st_sl(st_sl), .st_qc(st_qc), .st_qb(st_qb), .st_bs(st_bs), .q_cause(q_cause), .q_taddr(q_taddr),
        .f_start(b_f_start), .f_dir(b_f_dir), .f_near(b_f_near), .f_far(b_f_far), .f_cnt(b_f_cnt), .f_lbase(f_lbase), .f_llen(f_llen),
        .f_busy(f_busy), .f_done(f_done), .f_ign(f_ign), .f_init(init_done), .f_err(f_err), .f_moved(f_moved), .f_clocks(f_clocks),
        .f_cl(cfg_cl), .f_dly(cfg_dly), .f_inv(cfg_inv), .f_reinit(reinit),
        .fh_v(fh_v), .fh_we(fh_we), .fh_a(fh_a), .fh_wd(fh_wd), .fh_acc(fh_acc), .fh_ackv(ack_v), .fh_ackd(ack_d),
        .s_start(s_start), .s_addr(s_addr), .s_busy(s_busy), .s_done(s_done), .s_err(s_err), .s_steps(s_steps), .s_tag(s_tag), .s_clk(s_clk), .s_cclk(s_cclk), .s_wclk(s_wclk), .s_pc(s_pcc), .s_op(s_opc),
        .act_rx(act_rx), .act_tx(act_tx));
    // (act_rx / act_tx of the bridge are not used here; the link has its own activity pulse)

    // ---- JTAG byte link (replaces the UART)
    wire j_drck, j_capture, j_shift, j_sel, j_tdi, j_tdo, link_act;
    wire [7:0] rb_data, tb_data; wire rb_valid, tb_send, tb_busy;
    BSCANE2 #(.JTAG_CHAIN(1)) bscan (.CAPTURE(j_capture), .DRCK(j_drck), .RESET(), .RUNTEST(), .SEL(j_sel), .SHIFT(j_shift), .TCK(), .TDI(j_tdi), .TMS(), .UPDATE(), .TDO(j_tdo));
    jtag_link_v2 #(.K(JK), .RXGAP(RXGAP)) jl (.clk(clk), .rst(!por_done), .j_drck(j_drck), .j_capture(j_capture), .j_shift(j_shift), .j_sel(j_sel), .j_tdi(j_tdi), .j_tdo(j_tdo),
        .rb_data(rb_data), .rb_valid(rb_valid), .tb_data(tb_data), .tb_send(tb_send), .tb_busy(tb_busy), .act(link_act));

    // ---- far RAM: block RAM (was the SDRAM controller), copy engine, and who may use what
    wire        f_start, f_busy, f_done, f_ign, init_done, reinit, cfg_inv, ctl_busy;
    wire [1:0]  f_dir, cfg_cl, cfg_dly; wire [2:0] f_err;
    wire [15:0] f_near, f_cnt; wire [20:0] f_far, f_lbase; wire [21:0] f_llen; wire [31:0] f_moved, f_clocks;
    wire        e_dh_we, e_dh_rd, e_imem_we, e_rv, e_rwe; wire [15:0] e_dh_a, e_imem_wa; wire [31:0] e_dh_wd, e_imem_wd, e_rwd; wire [20:0] e_ra;
    wire        fh_v, fh_we; wire [20:0] fh_a; wire [31:0] fh_wd;
    wire        req_rdy, ack_v; wire [31:0] ack_d;
    wire        req_v  = f_busy ? e_rv  : s_rv ? 1'b1 : fh_v;                // while a copy runs it owns the far RAM
    wire        req_we = f_busy ? e_rwe : s_rv ? 1'b0 : fh_we;
    wire [20:0] req_a  = f_busy ? e_ra  : s_rv ? s_ra : fh_a;
    wire [31:0] req_wd = f_busy ? e_rwd : fh_wd;
    wire        fh_acc = fh_v && req_rdy && !f_busy && !s_rv;
    // the engine owns the shared RAM host port and the code-store write port while it runs; the bridge's M / L wait (dh_busy | f_busy)
    assign dh_we  = f_busy ? e_dh_we : b_dh_we;
    assign dh_rd  = f_busy ? e_dh_rd : b_dh_rd;
    assign dh_a   = f_busy ? e_dh_a  : b_dh_a;
    assign dh_wd  = f_busy ? e_dh_wd : b_dh_wd;
    assign imem_we = b_imem_we | e_imem_we;
    assign imem_wa = e_imem_we ? e_imem_wa : b_imem_wa;
    assign imem_wd = e_imem_we ? e_imem_wd : b_imem_wd;

    // v2: the far RAM is outside this module (block RAM in sc_k7_v1, DDR3 in the GPL-3.0 *_ddr3 build)
    assign fr_v = req_v;  assign fr_we = req_we;  assign fr_a = req_a;  assign fr_wd = req_wd;
    assign req_rdy = fr_rdy;  assign ack_v = fr_ackv;  assign ack_d = fr_ackd;  assign init_done = fr_init;  assign ctl_busy = fr_busy;
    assign por_ok = por_done;

    far_copy #(.DSH(DSH), .IMW(IMEM_WORDS)) fc (
        .clk(clk), .rst(rst), .start(f_start), .dir(f_dir), .sh_a(f_near), .far_a(f_far), .count(f_cnt), .lim_base(f_lbase), .lim_len(f_llen), .init_done(init_done),
        .busy(f_busy), .done(f_done), .ignored(f_ign), .err(f_err), .moved(f_moved), .clocks(f_clocks),
        .dh_we(e_dh_we), .dh_rd(e_dh_rd), .dh_a(e_dh_a), .dh_wd(e_dh_wd), .dh_q(dh_q), .dh_qv(dh_qv), .dh_busy(dh_busy),
        .ie_we(e_imem_we), .ie_wa(e_imem_wa), .ie_wd(e_imem_wd),
        .req_v(e_rv), .req_we(e_rwe), .req_a(e_ra), .req_wd(e_rwd), .req_rdy(req_rdy), .ack_v(ack_v), .ack_d(ack_d));


    batch_seq_v2 bs (
        .clk(clk), .rst(rst), .start(s_start), .start_a(s_addr), .init_done(init_done), .busy(s_busy), .done(s_done), .err(s_err), .steps(s_steps), .tag(s_tag),
        .req_v(s_rv), .req_a(s_ra), .req_rdy(req_rdy), .ack_v(ack_v), .ack_d(ack_d),
        .c_start(s_fstart), .c_dir(s_dir), .c_near(s_near), .c_far(s_far), .c_cnt(s_cnt), .c_busy(f_busy), .c_done(f_done), .c_err(f_err),
        .h_push(s_push), .h_tid(s_tid), .h_code(s_code), .h_lw(s_lw), .h_crit(s_crit), .h_prog(s_hprog),
        .rg_we(s_rg), .rg_prog(s_rgprog), .rg_cbase(s_cbase), .rg_clen(s_clen), .rg_dlen(s_dlen),
        .rs_we(s_rs), .rs_prog(s_rsprog), .rs_base(s_base), .rs_len(s_len),
        .lb_we(s_lb), .lb_base(s_lbase), .lb_len(s_llen), .n_done(o_done), .clk_total(s_clk), .clk_copy(s_cclk), .clk_wait(s_wclk), .cur_pc(s_pcc), .cur_op(s_opc));

    sc_sys_v12 #(.S(S), .QD(QD), .IMEM_WORDS(IMEM_WORDS), .DMW(DMW), .DSH(DSH), .SHL(SHL), .PROF(PROF), .EVB(3),
                .PRIO(1), .BESTFIT(1), .LONGEST(LONGEST), .FINE(FINE)) sys (
        .clk(clk), .rst(rst), .hold(hold), .rg_we(rg_we), .rg_prog(rg_prog), .rg_cbase(rg_cbase), .rg_clen(rg_clen), .rg_dlen(rg_dlen),
        .lb_we(lb_we), .lb_base(lb_base), .lb_len(lb_len), .rs_we(rs_we), .rs_prog(rs_prog), .rs_base(rs_base), .rs_len(rs_len), .dh_we(dh_we), .dh_rd(dh_rd), .dh_a(dh_a), .dh_wd(dh_wd), .dh_q(dh_q), .dh_qv(dh_qv), .dh_busy(dh_busy),
        .h_push(h_push), .h_tid(h_tid), .h_code(h_code), .h_lw(h_lw), .h_crit(h_crit), .h_prog(h_prog),
        .imem_we(imem_we), .imem_wa(imem_wa), .imem_wd(imem_wd),
        .q_tid(q_tid), .q_start(q_start), .q_end(q_end), .q_a0(q_a0), .q_arr(q_arr), .q_trap(q_trap),
        .q_state(q_state), .q_slot(q_slot), .q_pred(q_pred),
        .o_cyc(o_cyc), .o_done(o_done), .o_lerr(o_lerr), .o_disp(o_disp),
        .o_busy(o_busy), .o_blocked(o_blocked), .o_tail(o_tail), .o_search(o_search), .o_busy_l(o_busy_l), .st_sl(st_sl), .st_qc(st_qc), .st_qb(st_qb), .st_bs(st_bs), .q_cause(q_cause), .q_taddr(q_taddr),
        .ev_pl_we(1'b0), .ev_pl_id(8'd0), .ev_pl_data(32'd0), .ev_set(1'b0), .ev_set_id(8'd0));

    reg [25:0] hb = 0;
    always @(posedge clk) hb <= hb + 1'b1;
    assign led = {|o_done | link_act, hb[25], (|o_lerr) | q_trap};
endmodule
