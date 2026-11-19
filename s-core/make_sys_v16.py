#!/usr/bin/env python3
"""make_sys_v16.py - writes sc_sys_v16.v from sc_sys_v15.v (v15 stays as proven)  (ledger #1378, step I1 of FUSION_PLAN.md).
The pool block gets ONE fusion unit (uc_unitw<2**ULW>, ledger #1377).  A task submitted with lw > 0 is launched by the dispatcher exactly as before
(an aligned group of 2**lw slices is reserved, the leader = lowest slice).  If the unit is free the leader's RAMs, fetch register and region checks are
handed to the unit for the length of the task (a leader mux: only even slices can lead a fused task); otherwise, or when lw > ULW, the task runs as before
(lw > ULW: at ULW lanes; no free unit: at 1 bit).  Parameter FZ = 0 makes the block identical to v15 (no unit is built).
The shared data window works for fused tasks too (the word goes through the slice's dacc and its slot, as in the 1-bit core)."""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(HERE, 'sc_sys_v15.v')).read()
def rr(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old, s.count(old)); s = s.replace(old, new)

rr('module sc_sys_v15 #(', 'module sc_sys_v16 #(')
rr("    parameter EVB        = 8      // event payload index bits (lines 64.. use ev_pl[id mod 2^EVB])",
   "    parameter EVB        = 8,     // event payload index bits (lines 64.. use ev_pl[id mod 2^EVB])\n"
   "    parameter FZ         = 1,     // v16: 1 = one fusion unit in the block (needs S >= 2)\n"
   "    parameter ULW        = 2      // v16: the unit has 2**ULW lanes (2, 3 or 4)")
# ---- slice: core-side wires renamed, muxed names kept
rr("        wire        dwd, drd;\n",
   "        wire        dwd, drd;\n"
   "        wire        c_h, c_t, c_fetching, c_dact, c_dldr, c_rwe, c_dwe;\n"
   "        wire [29:0] c_ia;\n        wire [9:0]  c_ra, c_rb, c_rwa;\n        wire [34:0] c_da;\n"
   "        // v16: this slice leads a fused task and the unit stands in for its core\n"
   "        localparam  CAP = (FZ != 0) && (S >= 2) && (gi % 2 == 0);\n"
   "        localparam [5:0] GH = gi / 2;\n"
   "        wire        fz = CAP && fzb_v && (fzb_h == GH);\n"
   "        assign h = fz ? u_h : c_h;            assign t = fz ? u_t : c_t;\n"
   "        assign ia   = fz ? u_ia : c_ia;\n"
   "        assign ra   = fz ? {u_ra_wa, 5'd0} : c_ra;   assign rb = fz ? {u_rb_wa, 5'd0} : c_rb;   assign rwa = fz ? {u_rw_wa, 5'd0} : c_rwa;\n"
   "        assign da   = fz ? {u_d_wa, 5'd0} : c_da;\n"
   "        assign rwe  = fz ? 1'b0 : c_rwe;      assign dwe = fz ? 1'b0 : c_dwe;     // the unit has its own write accumulators\n")
rr("        wire          fetching;\n", "        wire          fetching;      // (muxed, see fz)\n        assign fetching = fz ? u_fetching : c_fetching;\n")
rr("        wire           dact, dldr;\n", "        wire           dact, dldr;    // (muxed, see fz)\n        assign dact = fz ? u_dact : c_dact;   assign dldr = fz ? u_dldr : c_dldr;\n")
# v16: shared window for a fused task: a finished store word goes to dacc and the slice's slot as before; a loaded word is read from dacc (z_dq)
rr("        wire        dflush_s = dflush &  sh_sel;      // shared word: held in dacc until the slice's slot",
   "        wire        dflush_s = fz ? (u_d_wwe & sh_sel) : (dflush & sh_sel);      // shared word: held in dacc until the slice's slot (v16: a word finished by the unit too)")
rr("            rflush_n <= rflush; dflush_n <= dflush_p; rnext_n <= rnext; dnext_n <= dnext;",
   "            rflush_n <= fz ? u_rw_we : rflush; dflush_n <= dflush_p; rnext_n <= fz ? u_rw_word : rnext; dnext_n <= fz ? u_d_wword : dnext;")
rr("                else if (capt) dacc <= sdq;                 // v10: a word read from the shared RAM lands here",
   "                else if (capt) dacc <= sdq;                 // v10: a word read from the shared RAM lands here\n                else if (fz && u_d_wwe && sh_sel) dacc <= u_d_wword;   // v16: a shared word finished by the unit waits here for the slice's slot")
rr("        wire        dflush_p = dflush & ~sh_sel;",
   "        wire        dflush_p = fz ? (u_d_wwe & ~sh_sel) : (dflush & ~sh_sel);")
rr("        always @(posedge clk) if (rwe & cph & (rwa[9:5] == 5'd10)) a0s[rwa[4:0]] <= rwd;",
   "        always @(posedge clk) begin\n"
   "            if (rwe & cph & (rwa[9:5] == 5'd10)) a0s[rwa[4:0]] <= rwd;\n"
   "            if (fz && u_rw_we && u_rw_wa == 5'd10) a0s <= u_rw_word;     // v16: a word written by the unit\n"
   "        end")
rr("        uc_core_v2v #(.W(1)) core (\n            .clk(clk), .rst(rst), .start(pend), .entry(ent_q), .ce(ce_g),\n            .halted(h), .trap(t), .fetching(fetching), .abort(abort), .dmem_act(dact), .dmem_ld(dldr),\n            .imem_addr(ia), .imem_data(id),\n            .ra_addr(ra), .ra_data(rad), .rb_addr(rb), .rb_data(rbd),\n            .rw_en(rwe), .rw_addr(rwa), .rw_data(rwd),\n            .d_addr(da), .d_we(dwe), .d_wdata(dwd), .d_rdata(drd));",
   "        uc_core_v2v #(.W(1)) core (\n            .clk(clk), .rst(rst), .start(pend & ~fz), .entry(ent_q), .ce(ce_g),\n            .halted(c_h), .trap(c_t), .fetching(c_fetching), .abort(abort), .dmem_act(c_dact), .dmem_ld(c_dldr),\n            .imem_addr(c_ia), .imem_data(id),\n            .ra_addr(c_ra), .ra_data(rad), .rb_addr(c_rb), .rb_data(rbd),\n            .rw_en(c_rwe), .rw_addr(c_rwa), .rw_data(rwd),\n            .d_addr(c_da), .d_we(c_dwe), .d_wdata(dwd), .d_rdata(drd));\n"
   "        // v16: what the unit reads from this slice (only even slices can lead; entry j = slice 2j)\n"
   "        if (CAP) begin : zl\n"
   "            assign z_ce  [gi/2]            = ce_g;\n"
   "            assign z_id  [(gi/2)*32 +: 32] = fw;\n"
   "            assign z_ra  [(gi/2)*32 +: 32] = rqa_w;\n"
   "            assign z_rb  [(gi/2)*32 +: 32] = rqb_w;\n"
   "            assign z_dq  [(gi/2)*32 +: 32] = sh_sel ? dacc : dq_w;   // a shared word is held in dacc\n"
   "            assign z_ab  [gi/2]            = abort;\n"
   "            assign z_dv  [gi/2]            = dviol;\n"
   "            assign z_pend[gi/2]            = pend;\n"
   "        end")
# ---- module-level: unit, binding, buses (declared before the slice generate)
rr("    genvar gi;\n    generate for (gi = 0; gi < S; gi = gi + 1) begin : slot\n",
"""    // ------------------------------------------------------------ v16: the fusion unit and its binding to a leader slice
    localparam NH = (S >= 2) ? S / 2 : 1;                 // possible leaders: even slices
    localparam HW = (NH > 1) ? $clog2(NH) : 1;
    wire [NH-1:0]    z_ce, z_ab, z_dv, z_pend;
    wire [NH*32-1:0] z_id, z_ra, z_rb, z_dq;
    reg              fzb_v;                               // the unit is bound to a leader
    reg  [HW-1:0]    fzb_h;                               // ... slice 2*fzb_h
    reg  [3:0]       fzb_lw;                              // width of the bound task (min(lw, ULW))
    reg  [31:0]      fzb_ent;
    wire             u_h, u_t, u_fetching, u_dact, u_dldr, u_rw_we, u_d_wwe;
    wire [29:0]      u_ia, u_d_wa;
    wire [4:0]       u_ra_wa, u_rb_wa, u_rw_wa;
    wire [31:0]      u_rw_word, u_d_wword;
    wire [31:0]      u_imem_data = z_id[fzb_h*32 +: 32];
    wire [31:0]      u_ra_word   = z_ra[fzb_h*32 +: 32];
    wire [31:0]      u_rb_word   = z_rb[fzb_h*32 +: 32];
    wire [31:0]      u_d_word    = z_dq[fzb_h*32 +: 32];
    wire             u_ce        = fzb_v & z_ce[fzb_h];
    wire             u_start     = fzb_v & z_pend[fzb_h];
    wire             u_abort     = fzb_v & z_ab[fzb_h];
    wire             u_dblk      = z_dv[fzb_h];
    generate if (FZ != 0 && S >= 2) begin : fu
        if (ULW == 2) begin : u4
            uc_unitw4 unit (.clk(clk), .rst(rst), .lw(fzb_lw[1:0]), .start(u_start), .entry(fzb_ent), .ce(u_ce), .abort(u_abort), .dblk(u_dblk),
                .halted(u_h), .trap(u_t), .fetching(u_fetching), .dmem_act(u_dact), .dmem_ld(u_dldr), .imem_addr(u_ia), .imem_data(u_imem_data),
                .ra_wa(u_ra_wa), .ra_word(u_ra_word), .rb_wa(u_rb_wa), .rb_word(u_rb_word), .rw_we(u_rw_we), .rw_wa(u_rw_wa), .rw_word(u_rw_word),
                .d_wa(u_d_wa), .d_word(u_d_word), .d_wwe(u_d_wwe), .d_wword(u_d_wword));
        end else if (ULW == 3) begin : u8
            uc_unitw8 unit (.clk(clk), .rst(rst), .lw(fzb_lw[2:0]), .start(u_start), .entry(fzb_ent), .ce(u_ce), .abort(u_abort), .dblk(u_dblk),
                .halted(u_h), .trap(u_t), .fetching(u_fetching), .dmem_act(u_dact), .dmem_ld(u_dldr), .imem_addr(u_ia), .imem_data(u_imem_data),
                .ra_wa(u_ra_wa), .ra_word(u_ra_word), .rb_wa(u_rb_wa), .rb_word(u_rb_word), .rw_we(u_rw_we), .rw_wa(u_rw_wa), .rw_word(u_rw_word),
                .d_wa(u_d_wa), .d_word(u_d_word), .d_wwe(u_d_wwe), .d_wword(u_d_wword));
        end else begin : u16
            uc_unitw16 unit (.clk(clk), .rst(rst), .lw(fzb_lw[2:0]), .start(u_start), .entry(fzb_ent), .ce(u_ce), .abort(u_abort), .dblk(u_dblk),
                .halted(u_h), .trap(u_t), .fetching(u_fetching), .dmem_act(u_dact), .dmem_ld(u_dldr), .imem_addr(u_ia), .imem_data(u_imem_data),
                .ra_wa(u_ra_wa), .ra_word(u_ra_word), .rb_wa(u_rb_wa), .rb_word(u_rb_word), .rw_we(u_rw_we), .rw_wa(u_rw_wa), .rw_word(u_rw_word),
                .d_wa(u_d_wa), .d_word(u_d_word), .d_wwe(u_d_wwe), .d_wword(u_d_wword));
        end
    end else begin : nu
        assign {u_h, u_t, u_fetching, u_dact, u_dldr, u_rw_we, u_d_wwe} = 7'b1000000;
        assign u_ia = 30'd0; assign u_d_wa = 30'd0; assign u_ra_wa = 5'd0; assign u_rb_wa = 5'd0; assign u_rw_wa = 5'd0;
        assign u_rw_word = 32'd0; assign u_d_wword = 32'd0;
    end endgenerate

    genvar gi;
    generate for (gi = 0; gi < S; gi = gi + 1) begin : slot
""")
# ---- binding register (in its own clocked block, after the slice generate)
rr("    // ------------------------------------------------------------ idle table + per-core info",
"""    // ------------------------------------------------------------ v16: bind the unit when a fused task starts; release it when its leader slice is freed
    // start_v is a one-clock pulse for the leader; launch_lw / launch_entry are valid in that clock.  A task with lw = 0, an odd leader, or no free unit is not bound.
    reg [HW-1:0] bind_h;
    reg          bind_any;
    integer      bi_;
    always @* begin
        bind_any = 1'b0; bind_h = {HW{1'b0}};
        for (bi_ = 0; bi_ < S; bi_ = bi_ + 1)
            if ((bi_ % 2 == 0) && start_v[bi_]) begin bind_any = 1'b1; bind_h = bi_ / 2; end
    end
    always @(posedge clk) begin
        if (rst || FZ == 0) fzb_v <= 1'b0;
        else if (!fzb_v) begin
            if (bind_any && launch_lw != 3'd0) begin
                fzb_v   <= 1'b1;
                fzb_h   <= bind_h;
                fzb_lw  <= (launch_lw > ULW) ? ULW[3:0] : {1'b0, launch_lw};
                fzb_ent <= launch_entry;
            end
        end else if (!slice_busy[{fzb_h, 1'b0}]) fzb_v <= 1'b0;    // leader slice released by the watcher (its results are already stored)
    end
    initial begin fzb_v = 0; fzb_h = 0; fzb_lw = 0; fzb_ent = 0; end

    // ------------------------------------------------------------ idle table + per-core info""")
s = '// sc_sys_v16.v (GENERATED by make_sys_v16.py from sc_sys_v15.v, do not edit): sc_sys_v15 with ONE fusion unit per block (ledger #1378).  See make_sys_v16.py.\n' + s
open(os.path.join(HERE, 'sc_sys_v16.v'), 'w').write(s)
print('wrote sc_sys_v16.v')
