#!/usr/bin/env python3
"""make_sys_v17.py - writes sc_sys_v17.v from sc_sys_v16.v (v16 stays as proven)  (ledger #1386, step I3a of FUSION_PLAN.md): NU fusion units per block instead of one.
Parameter NU (default 2).  The dispatcher binds the lowest free unit to the leader of a fused task (lw > 0); with all units busy the task runs at 1 bit, as before.
Every unit has the same width (ULW).  NU = 1 is the v16 behaviour."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(HERE, 'sc_sys_v16.v')).read()
def rr(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:80], s.count(old)); s = s.replace(old, new)
rr('module sc_sys_v16 #(', 'module sc_sys_v17 #(')
rr("    parameter ULW        = 2      // v16: the unit has 2**ULW lanes (2, 3 or 4)",
   "    parameter ULW        = 2,     // v16: each unit has 2**ULW lanes (2, 3 or 4)\n    parameter NU         = 2      // v17: fusion units in the block (each can run one fused task; needs FZ = 1)")
a = s.index("    // ------------------------------------------------------------ v16: the fusion unit and its binding to a leader slice")
b = s.index("    genvar gi;\n")
def inst(mod, lwsel):
    return ("            %s unit (.clk(clk), .rst(rst), .lw(fzb_lw[ku][%s]), .start(u_start), .entry(fzb_ent[ku]), .ce(u_ce), .abort(u_abort), .dblk(u_dblk),\n"
            "                .halted(uv_h[ku]), .trap(uv_t[ku]), .fetching(uv_fetching[ku]), .dmem_act(uv_dact[ku]), .dmem_ld(uv_dldr[ku]), .imem_addr(uv_ia[ku*30 +: 30]), .imem_data(u_imem_data),\n"
            "                .ra_wa(uv_ra_wa[ku*5 +: 5]), .ra_word(u_ra_word), .rb_wa(uv_rb_wa[ku*5 +: 5]), .rb_word(u_rb_word), .rw_we(uv_rw_we[ku]), .rw_wa(uv_rw_wa[ku*5 +: 5]), .rw_word(uv_rw_word[ku*32 +: 32]),\n"
            "                .d_wa(uv_d_wa[ku*30 +: 30]), .d_word(u_d_word), .d_wwe(uv_d_wwe[ku]), .d_wword(uv_d_wword[ku*32 +: 32]));\n") % (mod, lwsel)
units = """    // ------------------------------------------------------------ v17: NU fusion units and their binding to leader slices
    localparam NH = (S >= 2) ? S / 2 : 1;                 // possible leaders: even slices
    localparam HW = (NH > 1) ? $clog2(NH) : 1;
    localparam KW = (NU > 1) ? $clog2(NU) : 1;
    wire [NH-1:0]    z_ce, z_ab, z_dv, z_pend;
    wire [NH*32-1:0] z_id, z_ra, z_rb, z_dq;
    reg  [NU-1:0]    fzb_v;                               // unit k is bound to a leader
    reg  [HW-1:0]    fzb_h  [0:NU-1];                     // ... slice 2*fzb_h[k]
    reg  [3:0]       fzb_lw [0:NU-1];                     // width of the bound task (min(lw, ULW))
    reg  [31:0]      fzb_ent[0:NU-1];
    wire [NU-1:0]    uv_h, uv_t, uv_fetching, uv_dact, uv_dldr, uv_rw_we, uv_d_wwe;
    wire [NU*30-1:0] uv_ia, uv_d_wa;
    wire [NU*5-1:0]  uv_ra_wa, uv_rb_wa, uv_rw_wa;
    wire [NU*32-1:0] uv_rw_word, uv_d_wword;
    genvar ku;
    generate for (ku = 0; ku < NU; ku = ku + 1) begin : fu
        wire [31:0] u_imem_data = z_id[fzb_h[ku]*32 +: 32];
        wire [31:0] u_ra_word   = z_ra[fzb_h[ku]*32 +: 32];
        wire [31:0] u_rb_word   = z_rb[fzb_h[ku]*32 +: 32];
        wire [31:0] u_d_word    = z_dq[fzb_h[ku]*32 +: 32];
        wire        u_ce        = fzb_v[ku] & z_ce[fzb_h[ku]];
        wire        u_start     = fzb_v[ku] & z_pend[fzb_h[ku]];
        wire        u_abort     = fzb_v[ku] & z_ab[fzb_h[ku]];
        wire        u_dblk      = z_dv[fzb_h[ku]];
        if (FZ != 0 && S >= 2) begin : on
            if (ULW == 2) begin : u4
""" + inst('uc_unitw4', '1:0') + """            end else if (ULW == 3) begin : u8
""" + inst('uc_unitw8', '1:0') + """            end else begin : u16
""" + inst('uc_unitw16', '2:0') + """            end
        end else begin : off
            assign uv_h[ku] = 1'b1; assign uv_t[ku] = 1'b0; assign uv_fetching[ku] = 1'b0; assign uv_dact[ku] = 1'b0; assign uv_dldr[ku] = 1'b0;
            assign uv_rw_we[ku] = 1'b0; assign uv_d_wwe[ku] = 1'b0;
            assign uv_ia[ku*30 +: 30] = 30'd0; assign uv_d_wa[ku*30 +: 30] = 30'd0;
            assign uv_ra_wa[ku*5 +: 5] = 5'd0; assign uv_rb_wa[ku*5 +: 5] = 5'd0; assign uv_rw_wa[ku*5 +: 5] = 5'd0;
            assign uv_rw_word[ku*32 +: 32] = 32'd0; assign uv_d_wword[ku*32 +: 32] = 32'd0;
        end
    end endgenerate

"""
s = s[:a] + units + s[b:]
rr("        wire        fz = CAP && fzb_v && (fzb_h == GH);\n",
"""        wire [NU-1:0] fzs;                              // v17: which unit leads this slice (at most one)
        genvar kz;
        for (kz = 0; kz < NU; kz = kz + 1) begin : fzk
            assign fzs[kz] = CAP && fzb_v[kz] && (fzb_h[kz] == GH);
        end
        wire        fz = |fzs;
        reg         u_h, u_t, u_fetching, u_dact, u_dldr, u_rw_we, u_d_wwe;
        reg  [29:0] u_ia, u_d_wa;
        reg  [4:0]  u_ra_wa, u_rb_wa, u_rw_wa;
        reg  [31:0] u_rw_word, u_d_wword;
        integer     kq;
        always @* begin                                 // the outputs of the unit that leads this slice (all 0 when none does)
            u_h = 1'b0; u_t = 1'b0; u_fetching = 1'b0; u_dact = 1'b0; u_dldr = 1'b0; u_rw_we = 1'b0; u_d_wwe = 1'b0;
            u_ia = 30'd0; u_d_wa = 30'd0; u_ra_wa = 5'd0; u_rb_wa = 5'd0; u_rw_wa = 5'd0; u_rw_word = 32'd0; u_d_wword = 32'd0;
            for (kq = 0; kq < NU; kq = kq + 1) if (fzs[kq]) begin
                u_h = u_h | uv_h[kq]; u_t = u_t | uv_t[kq]; u_fetching = u_fetching | uv_fetching[kq]; u_dact = u_dact | uv_dact[kq]; u_dldr = u_dldr | uv_dldr[kq];
                u_rw_we = u_rw_we | uv_rw_we[kq]; u_d_wwe = u_d_wwe | uv_d_wwe[kq];
                u_ia = u_ia | uv_ia[kq*30 +: 30]; u_d_wa = u_d_wa | uv_d_wa[kq*30 +: 30];
                u_ra_wa = u_ra_wa | uv_ra_wa[kq*5 +: 5]; u_rb_wa = u_rb_wa | uv_rb_wa[kq*5 +: 5]; u_rw_wa = u_rw_wa | uv_rw_wa[kq*5 +: 5];
                u_rw_word = u_rw_word | uv_rw_word[kq*32 +: 32]; u_d_wword = u_d_wword | uv_d_wword[kq*32 +: 32];
            end
        end
""")
a = s.index("    // ------------------------------------------------------------ v16: bind the unit when a fused task starts")
b = s.index("    // ------------------------------------------------------------ idle table + per-core info")
s = s[:a] + """    // ------------------------------------------------------------ v17: bind the lowest free unit when a fused task starts; release it when its leader slice is freed
    // start_v is a one-clock pulse for the leader; launch_lw / launch_entry are valid in that clock.  A task with lw = 0, an odd leader, or no free unit is not bound.
    reg [HW-1:0] bind_h;
    reg          bind_any;
    integer      bi_;
    always @* begin
        bind_any = 1'b0; bind_h = {HW{1'b0}};
        for (bi_ = 0; bi_ < S; bi_ = bi_ + 1)
            if ((bi_ % 2 == 0) && start_v[bi_]) begin bind_any = 1'b1; bind_h = bi_ / 2; end
    end
    reg          bind_ok;
    reg [KW-1:0] bind_k;
    integer      kb_, kc_;
    always @* begin
        bind_ok = 1'b0; bind_k = {KW{1'b0}};
        for (kb_ = NU - 1; kb_ >= 0; kb_ = kb_ - 1) if (!fzb_v[kb_]) begin bind_ok = 1'b1; bind_k = kb_; end   // the lowest free unit wins
    end
    always @(posedge clk) begin
        for (kc_ = 0; kc_ < NU; kc_ = kc_ + 1) begin
            if (rst || FZ == 0) fzb_v[kc_] <= 1'b0;
            else if (bind_any && launch_lw != 3'd0 && bind_ok && bind_k == kc_) begin
                fzb_v[kc_]   <= 1'b1;
                fzb_h[kc_]   <= bind_h;
                fzb_lw[kc_]  <= (launch_lw > ULW) ? ULW[3:0] : {1'b0, launch_lw};
                fzb_ent[kc_] <= launch_entry;
            end else if (fzb_v[kc_] && !slice_busy[{fzb_h[kc_], 1'b0}]) fzb_v[kc_] <= 1'b0;    // leader slice released by the watcher (its results are already stored)
        end
    end
    integer kz_;
    initial for (kz_ = 0; kz_ < NU; kz_ = kz_ + 1) begin fzb_v[kz_] = 0; fzb_h[kz_] = 0; fzb_lw[kz_] = 0; fzb_ent[kz_] = 0; end

""" + s[b:]
s = '// sc_sys_v17.v (GENERATED by make_sys_v17.py from sc_sys_v16.v, do not edit): sc_sys_v16 with NU fusion units per block (ledger #1386).  See make_sys_v17.py.\n' + s
open(os.path.join(HERE, 'sc_sys_v17.v'), 'w').write(s)
print('wrote sc_sys_v17.v')
