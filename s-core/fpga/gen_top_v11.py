import re
F='/home/claude/imago-unicell/s-core/fpga/'
s=open(F+'sc_top_k7_v10.v').read()
def rep(old,new,cnt=1):
    global s
    assert s.count(old)==cnt,(old[:60],s.count(old)); s=s.replace(old,new)
rep('module sc_top_k7_v10 #(','module sc_top_k7_v11 #(')
s=('// sc_top_k7_v11.v - sc_top_k7_v10 with the status reading done INSIDE each block\'s side (ledger #1457): a blk_rd_v1 per block returns ONE BYTE of status and the\n'
   '//   bridge (host_bridge_v12) takes the selected block\'s byte; the wide per-block status wires (about 1,600 bits at 8 slices, 2,200 at 16) no longer meet in the hub.\n'
   '//   The LEDs use three bits per block.  Everything else (blocks, far-RAM arbiter, far RAM, command broadcast) is as in v10.  Cloned from sc_top_k7_v10.v (left as proven).\n')+s
kept={'dh_q','dh_qv','dh_busy','f_busy','fh_acc','fh_ackv','fh_ackd'}
# declarations and assigns of the muxed copies
lines=s.split('\n'); out=[]
for L in lines:
    m=re.match(r'^    wire \[[^\]]*\] m_(\w+);$',L)
    if m and m.group(1) not in kept: continue
    m=re.match(r'^    assign m_(\w+) = a_.*;$',L)
    if m and m.group(1) not in kept: continue
    out.append(L)
s='\n'.join(out)
# new declarations
rep('    wire [7:0] rb_data, tb_data; wire rb_valid, tb_send, tb_busy;\n',
    '    wire [7:0] rb_data, tb_data; wire rb_valid, tb_send, tb_busy;\n'
    '    wire [NB*8-1:0] a_rd_byte; wire [7:0] m_rd_byte = a_rd_byte[blk*8 +: 8]; wire [7:0] rd_cmd; wire [9:0] rd_idx; wire rd_snap, rd_lat;\n'
    '    wire [NB-1:0] a_led_done, a_led_err, a_led_trap;\n')
# the bridge instance
a=s.index('    host_bridge_v11 #('); z=s.index('.act_tx(act_tx));',a)+len('.act_tx(act_tx));')
inst=s[a:z]
inst=inst.replace('host_bridge_v11','host_bridge_v12')
moved=['q_start','q_end','q_a0','q_arr','q_trap','q_state','q_slot','q_pred','o_cyc','o_done','o_lerr','o_disp','o_busy','o_blocked','o_tail','o_search','o_busy_l','st_sl','st_qc','st_qb','st_bs','q_cause','q_taddr',
       'f_done','f_ign','f_err','f_moved','f_clocks','s_busy','s_done','s_err','s_steps','s_tag','s_clk','s_cclk','s_wclk']
for p in moved:
    n=len(re.findall(r'\.%s\(m_%s\),?\s*'%(p,p),inst)); assert n==1,(p,n)
    inst=re.sub(r'\.%s\(m_%s\),?\s*'%(p,p),'',inst)
for p,q in (('s_pc','s_pcc'),('s_op','s_opc')):
    n=len(re.findall(r'\.%s\(m_%s\),?\s*'%(p,q),inst)); assert n==1,(p,n)
    inst=re.sub(r'\.%s\(m_%s\),?\s*'%(p,q),'',inst)
inst=inst.replace('.act_tx(act_tx));','.act_tx(act_tx),\n        .rd_byte(m_rd_byte), .rd_cmd(rd_cmd), .rd_idx(rd_idx), .rd_snap(rd_snap), .rd_lat(rd_lat));')
s=s[:a]+inst+s[z:]
# the reader per block, inside the generate, using the block's own connection expressions
g0=s.index('begin : blocks'); g1=s.index('    end endgenerate',g0)
blk=s[g0:g1]
expr={}
for m in re.finditer(r'\.(\w+)\((a_\w+\[gi\*[^\]]+\])\)',blk): expr[m.group(1)]=m.group(2)
ports=['q_start','q_end','q_a0','q_arr','q_trap','q_state','q_slot','q_pred','o_cyc','o_done','o_lerr','o_disp','o_busy','o_blocked','o_tail','o_search','o_busy_l','st_sl','st_qc','st_qb','st_bs','q_cause','q_taddr',
       'f_busy','f_done','f_ign','f_err','f_moved','f_clocks','s_busy','s_done','s_err','s_steps','s_tag','s_clk','s_cclk','s_wclk']
conn=[]
for p in ports: assert p in expr,p; conn.append('.%s(%s)'%(p,expr[p]))
assert 's_pcc' in expr and 's_opc' in expr
conn.append('.s_pc(%s)'%expr['s_pcc']); conn.append('.s_op(%s)'%expr['s_opc'])
rd=('        blk_rd_v1 #(.S(S)) rd (.clk(clk), .cmd(rd_cmd), .idx(rd_idx), .snap(rd_snap & sel[gi]), .lat(rd_lat & sel[gi]), .hold(hold_o[gi]), .f_init(init_done),\n            '
    + ',\n            '.join(conn)+',\n            .rbyte(a_rd_byte[gi*8 +: 8]));\n'
    '        assign a_led_done[gi] = |a_o_done[gi*(32) +: (32)];\n'
    '        assign a_led_err[gi]  = |a_o_lerr[gi*(32) +: (32)];\n'
    '        assign a_led_trap[gi] = a_q_trap[gi*(1) +: (1)];\n')
s=s[:g1]+rd+s[g1:]
rep('    assign led = {|m_o_done | link_act, hb[25], (|m_o_lerr) | m_q_trap};','    assign led = {a_led_done[blk] | link_act, hb[25], a_led_err[blk] | a_led_trap[blk]};')
open(F+'sc_top_k7_v11.v','w').write(s)
print('ok top v11', s.count('\n'),'lines')
