import re
F='/home/claude/imago-unicell/s-core/fpga/'
s=open(F+'sc_top_k7_v11.v').read()
def rep(old,new,cnt=1):
    global s
    assert s.count(old)==cnt,(old[:70],s.count(old)); s=s.replace(old,new)
rep('module sc_top_k7_v11 #(','module sc_top_k7_v12 #(')
s=('// sc_top_k7_v12.v - sc_top_k7_v11 with the command side narrowed too (ledger #1459): host_bridge_v13 broadcasts ONE raw command (strobe, command byte, 8 argument bytes: 73 wires)\n'
   '//   and a blk_cmd_v1 in each block decodes it when that block is selected, in place of about 450 decoded wires to every block.  With v11 (status inside the blocks) this leaves the\n'
   '//   blocks sharing the raw command, the far-RAM request lines, the clock and the reset.  Cloned from sc_top_k7_v11.v (left as proven).\n')+s
d0=s.index('    wire        h_push, imem_we,'); d1=s.index('    wire [32-1:0] m_dh_q;')
decl=s[d0:d1]
assert decl.count('\n')==4,decl
s=s[:d0]+'    wire c_v; wire [7:0] c_cmd; wire [63:0] c_a;\n'+s[d1:]
a=s.index('    host_bridge_v12 #('); z=s.index('.rd_lat(rd_lat));',a)+len('.rd_lat(rd_lat));')
inst=s[a:z].replace('host_bridge_v12','host_bridge_v13')
NAMES='h_push h_tid h_code h_lw h_crit h_prog imem_we imem_wa imem_wd q_tid d_we rg_we rg_prog rg_cbase rg_clen rg_dlen rs_we rs_prog rs_base rs_len lb_we lb_base lb_len dh_we dh_rd dh_a dh_wd f_start f_dir f_near f_far f_cnt f_lbase f_llen s_start s_addr fh_v fh_we fh_a fh_wd'.split()
for n in NAMES:
    c=len(re.findall(r'\.%s\(%s\),?\s*'%(n,n),inst)); assert c==1,(n,c)
    inst=re.sub(r'\.%s\(%s\),?\s*'%(n,n),'',inst)
inst=inst.replace('.rd_lat(rd_lat));','.rd_lat(rd_lat),\n        .c_v(c_v), .c_cmd(c_cmd), .c_a(c_a));')
s=s[:a]+inst+s[z:]
W={'h_push':1,'h_tid':16,'h_code':16,'h_lw':3,'h_crit':1,'h_prog':6,'imem_we':1,'imem_wa':16,'imem_wd':32,'q_tid':16,'d_we':1,'rg_we':1,'rg_prog':6,'rg_cbase':16,'rg_clen':16,'rg_dlen':16,'rs_we':1,'rs_prog':6,'rs_base':16,'rs_len':16,
   'lb_we':1,'lb_base':16,'lb_len':16,'dh_we':1,'dh_rd':1,'dh_a':16,'dh_wd':32,'f_start':1,'f_dir':2,'f_near':16,'f_far':21,'f_cnt':16,'f_lbase':21,'f_llen':22,'s_start':1,'s_addr':21,'fh_v':1,'fh_we':1,'fh_a':21,'fh_wd':32}
g0=s.index('begin : blocks'); g1=s.index('    end endgenerate',g0); blk=s[g0:g1]
b0=blk.index('sc_block_v3 #('); b1=blk.index('.ack_d(arb_ack_d));',b0)+len('.ack_d(arb_ack_d));')
bi=blk[b0:b1]; used=set()
def sub(m):
    port,expr=m.group(1),m.group(2).strip()
    base=expr.replace(' & sel[gi]','').strip()
    if base in W:
        used.add(base); return '.%s(l_%s)'%(port,base)
    return m.group(0)
bi2=re.sub(r'\.(\w+)\(([^()]*?)\)',sub,bi)
assert used==set(W),(set(W)-used)
decls=''.join('        wire %sl_%s;\n'%(('[%d:0] '%(W[n]-1)) if W[n]>1 else '',n) for n in NAMES)
cm=('        blk_cmd_v1 cm (.clk(clk), .sel(sel[gi]), .c_v(c_v), .c_cmd(c_cmd), .c_a(c_a), .fh_acc(a_fh_acc[gi*(1) +: (1)]),\n            '
    + ', '.join('.%s(l_%s)'%(n,n) for n in NAMES)+');\n')
blk2=blk[:b0]+decls+cm+bi2+blk[b1:]
s=s[:g0]+blk2+s[g1:]
open(F+'sc_top_k7_v12.v','w').write(s)
print('top v12 ok',s.count('\n'),'lines; locals',len(used))

# after generation sc_top_k7_v12.v was edited by hand: blk_rd_v1 -> blk_rd_v2 (see ledger #1459)
