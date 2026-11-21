import re
F='/home/claude/imago-unicell/s-core/fpga/'
# ------------------------------------------------------------------ blk_rd_v1.v, from the bridge's own rbyte text
b=open(F+'host_bridge_v11.v').read()
i0=b.index('    function [7:0] rbyte(input [7:0] c, input [9:0] i);')
i1=b.index('    endfunction',i0)+len('    endfunction')
fn=b[i0:i1]
# keep only the per-block classes Q C T U E N A (the text between the markers is reused unchanged)
def cut(fn, start, end):
    a=fn.index(start); z=fn.index(end,a); return fn[a:z]
q=cut(fn,'            if (c == "Q") begin','            end else if (c == "L") begin')   # Q C T U E
na=cut(fn,'            end else if (c == "N") begin','            end else if (c == "Z") begin')  # N I... careful: I sits between
# split N / A from I
n_blk=cut(fn,'            end else if (c == "N") begin','            end else if (c == "A") begin')
a_blk=cut(fn,'            end else if (c == "A") begin','            end else if (c == "Z") begin')
rd_fn=('    function [7:0] rbyte_f(input [7:0] c, input [9:0] i);\n        reg [63:0] w;\n        begin\n            w = 64\'d0; rbyte_f = 8\'d0;\n'
       + (q+n_blk+a_blk+'            end\n').replace('rbyte =','rbyte_f =')
       + '        end\n    endfunction')
mod='''// blk_rd_v1.v - the status-reading half of host_bridge_v11, moved INTO each block's side of the top so that only ONE BYTE per block (rbyte) crosses to the bridge
//   instead of about 1,600 (8 slices) or 2,200 (16 slices) status wires per block (ledger #1457; the reading of #1456).  The byte function is the text of
//   host_bridge_v11's rbyte for the classes Q C T U E N A, copied unchanged by the generator (gen_v12.py); the snapshots (cyc, qc, qb, busy/leader counts, hold,
//   the 40-bit slice count) are taken here on the same clock edges as the bridge took them (snap / lat are combinational from the bridge, gated by the block select).
//   rbyte is combinational from cmd and idx, so the timing of a reply byte is the same as in v11.   Needs: nothing else.
module blk_rd_v1 #(parameter S = 8) (
    input  wire        clk,
    input  wire [7:0]  cmd,
    input  wire [9:0]  idx,
    input  wire        snap,           // a C, U or T command arrives (this block selected)
    input  wire        lat,            // U, slice record: latch its whole 40-bit count with its first byte
    input  wire        hold,
    input  wire        f_init,
    input  wire [31:0] q_start, q_end, q_a0, q_arr,
    input  wire        q_trap,
    input  wire [1:0]  q_state,
    input  wire [5:0]  q_slot,
    input  wire [24:0] q_pred,
    input  wire [31:0] o_cyc, o_done, o_lerr, o_disp,
    input  wire [63:0] o_busy, o_blocked, o_tail, o_search,
    input  wire [S-1:0] o_busy_l,
    input  wire [32*S-1:0] st_sl,
    input  wire [15:0] st_qc, st_qb,
    input  wire [40*S-1:0] st_bs,
    input  wire [2:0]  q_cause,
    input  wire [15:0] q_taddr,
    input  wire        f_busy, f_done, f_ign,
    input  wire [2:0]  f_err,
    input  wire [31:0] f_moved, f_clocks,
    input  wire        s_busy, s_done,
    input  wire [3:0]  s_err,
    input  wire [15:0] s_steps,
    input  wire [31:0] s_tag, s_clk, s_cclk, s_wclk,
    input  wire [20:0] s_pc,
    input  wire [3:0]  s_op,
    output wire [7:0]  rbyte
);
    reg [31:0] cyc_s = 0;
    reg [39:0] cur_bs = 0;
    reg [15:0] snap_qc = 0, snap_qb = 0;
    reg [7:0]  snap_nb = 0, snap_nl = 0;
    reg        snap_hold = 0;
    integer    ni;
    reg [7:0]  nb_c, nl_c;
    always @(posedge clk) begin
        if (snap) begin
            cyc_s <= o_cyc; snap_qc <= st_qc; snap_qb <= st_qb; snap_hold <= hold;
            nb_c = 0; nl_c = 0;
            for (ni = 0; ni < S; ni = ni + 1) begin nb_c = nb_c + st_sl[ni*32]; nl_c = nl_c + st_sl[ni*32+1]; end
            snap_nb <= nb_c; snap_nl <= nl_c;
        end
        if (lat) cur_bs <= st_bs[40 * ((idx - 8) >> 3) +: 40];
    end
'''+rd_fn+'''
    assign rbyte = rbyte_f(cmd, idx);
endmodule
'''
open(F+'blk_rd_v1.v','w').write(mod)

# ------------------------------------------------------------------ host_bridge_v12.v
s=b
def rep(old,new,cnt=1):
    global s
    assert s.count(old)==cnt,(old,s.count(old)); s=s.replace(old,new)
rep('module host_bridge_v11 #(','module host_bridge_v12 #(')
hdr=('// host_bridge_v12.v - host_bridge_v11 with the status reading moved out (ledger #1457): the per-block replies of Q C T U E N A now come as ONE BYTE (rd_byte) from\n'
     '//   blk_rd_v1 in the selected block (the byte function and the snapshots live there).  Outputs rd_cmd, rd_idx, rd_snap, rd_lat drive it; they are combinational from\n'
     '//   the same registers v11 used, so reply bytes and their timing are as in v11.  Removed: the wide status inputs q_*, o_*, st_*, f_done/f_ign/f_err/f_moved/f_clocks, s_*.\n'
     '//   Kept: dh_q dh_qv dh_busy, f_busy f_init, fh_acc fh_ackv fh_ackd.  Cloned from host_bridge_v11.v (left as proven).\n')
s=hdr+s
# ports: remove wide status inputs
for line in ['    input  wire [31:0] q_start, q_end, q_a0, q_arr,\n','    input  wire        q_trap,\n','    input  wire [1:0]  q_state,\n','    input  wire [5:0]  q_slot,\n','    input  wire [24:0] q_pred,\n',
             '    input  wire [31:0] o_cyc, o_done, o_lerr, o_disp,\n','    input  wire [63:0] o_busy, o_blocked, o_tail, o_search,\n','    input  wire [S-1:0] o_busy_l,\n',
             '    input  wire [32*S-1:0] st_sl,\n','    input  wire [15:0] st_qc, st_qb,\n','    input  wire [40*S-1:0] st_bs,\n','    input  wire [2:0]  q_cause,\n','    input  wire [15:0] q_taddr,\n',
             '    input  wire [2:0]  f_err,\n','    input  wire [31:0] f_moved, f_clocks,\n',
             '    input  wire        s_busy, s_done,\n','    input  wire [3:0]  s_err,\n','    input  wire [15:0] s_steps,\n','    input  wire [31:0] s_tag,\n','    input  wire [31:0] s_clk, s_cclk, s_wclk,\n','    input  wire [20:0] s_pc,\n','    input  wire [3:0]  s_op,\n']:
    rep(line,'')
rep('    input  wire        f_busy, f_done, f_ign, f_init,\n','    input  wire        f_busy, f_init,\n')
rep('    output reg         act_rx, act_tx\n','    output reg         act_rx, act_tx,\n    // v12: the per-block status reader (blk_rd_v1)\n    input  wire [7:0]  rd_byte,\n    output wire [7:0]  rd_cmd,\n    output wire [9:0]  rd_idx,\n    output wire        rd_snap,\n    output wire        rd_lat\n')
# state that moved
rep('    reg [39:0] cur_bs = 0;\n','')
rep('    reg [15:0] snap_qc = 0, snap_qb = 0;\n    reg [7:0]  snap_nb = 0, snap_nl = 0;\n    reg        snap_hold = 0;\n','')
rep('    integer    ni;\n    reg [7:0]  nb_c, nl_c;\n    reg [31:0] cyc_s = 0;\n','')
# the function: keep only L r I Z V
a=s.index('    function [7:0] rbyte(input [7:0] c, input [9:0] i);'); z=s.index('    endfunction',a)+len('    endfunction')
fn=s[a:z]
keep=fn[fn.index('            end else if (c == "L") begin'):]
ka=keep.index('            end else if (c == "N") begin'); kz=keep.index('            end else if (c == "Z") begin')
keep=keep[:ka]+keep[kz:]
new_fn=('    function [7:0] rbyte(input [7:0] c, input [9:0] i);\n        reg [63:0] w;\n        begin\n            w = 64\'d0;\n            if (c == "L") begin\n'
        + keep[len('            end else if (c == "L") begin\n'):])
s=s[:a]+new_fn+s[z:]
# commands that took snapshots
rep('"C": begin rlen <= 56; ridx <= 0; cyc_s <= o_cyc; st <= REPLY; end','"C": begin rlen <= 56; ridx <= 0; st <= REPLY; end')
t0=s.index('                    "T": begin\n                        snap_qc'); t1=s.index('                    "U": begin cyc_s <= o_cyc;')
s=s[:t0]+'                    "T": begin rlen <= 8 + 4*S; ridx <= 0; st <= REPLY; end\n'+s[t1:]
rep('"U": begin cyc_s <= o_cyc; rlen <= 8 + 8*S; ridx <= 0; st <= REPLY; end','"U": begin rlen <= 8 + 8*S; ridx <= 0; st <= REPLY; end')
rep('                    tb <= rbyte(cmd, ridx); tsend <= 1\'b1; ridx <= ridx + 1\'b1;\n                    if (cmd == "U" && ridx >= 8 && ridx[2:0] == 0) cur_bs <= st_bs[40 * ((ridx - 8) >> 3) +: 40];   // latch this slice\'s whole count with its first byte\n',
    '                    tb <= rd_cls ? rd_byte : rbyte(cmd, ridx); tsend <= 1\'b1; ridx <= ridx + 1\'b1;\n')
# the new combinational helpers, placed before the main always block
rep('    always @(posedge clk) begin\n        h_push <= 1\'b0;','''    // v12: which commands are answered by the block's reader, and the strobes that drive it (combinational, from the registers v11 used)
    wire rd_cls = (cmd == "Q") || (cmd == "C") || (cmd == "T") || (cmd == "U") || (cmd == "E") || (cmd == "N") || (cmd == "A");
    assign rd_cmd  = cmd;
    assign rd_idx  = ridx;
    assign rd_snap = (st == IDLE) && rv && (rb == "C" || rb == "U" || rb == "T");
    assign rd_lat  = (st == REPLY) && !tbusy && !tsend && (ridx != rlen) && (cmd == "U") && (ridx >= 8) && (ridx[2:0] == 0);

    always @(posedge clk) begin
        h_push <= 1\'b0;''')
open(F+'host_bridge_v12.v','w').write(s)
print('ok bridge v12 lines',s.count('\n'),' blk_rd lines',mod.count('\n'))
