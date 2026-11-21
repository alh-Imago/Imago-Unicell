import re
F='/home/claude/imago-unicell/s-core/fpga/'
s=open(F+'host_bridge_v12.v').read()
def rep(old,new,cnt=1):
    global s
    assert s.count(old)==cnt,(old[:70],s.count(old)); s=s.replace(old,new)
rep('module host_bridge_v12 #(','module host_bridge_v13 #(')
s=('// host_bridge_v13.v - host_bridge_v12 with the command decode moved out (ledger #1459): the bridge no longer drives about 450 decoded wires to every block; it pulses c_v (one clock, where v12\n'
   '//   set its pulse registers) with the raw command c_cmd and its argument bytes c_a (a[0] in bits 7:0 ... a[7] in bits 63:56), and each block decodes it in blk_cmd_v1 with the same timing.\n'
   '//   The conditions that decide whether a command is carried out (dh_busy for M and L, f_busy / f_init for w and r) stay here.  O, K, H, G, R, V, Z, I and the reply logic are unchanged.\n'
   '//   Cloned from host_bridge_v12.v (left as proven).\n')+s
# ports
REMOVE=set('h_push h_tid h_code h_lw h_crit h_prog imem_we imem_wa imem_wd q_tid d_we rg_we rg_prog rg_cbase rg_clen rg_dlen rs_we rs_prog rs_base rs_len lb_we lb_base lb_len dh_we dh_rd dh_a dh_wd f_start f_dir f_near f_far f_cnt f_lbase f_llen s_start s_addr fh_v fh_we fh_a fh_wd'.split())
a=s.index('module host_bridge_v13'); z=s.index(');\n',a)
head=s[a:z]; out=[]; removed=0
for L in head.split('\n'):
    m=re.match(r'^\s+output reg\s+(?:\[[^\]]*\]\s*)?(.*?),?\s*$',L)
    if m:
        names=[x.strip() for x in m.group(1).split(',') if x.strip()]
        if names and all(n in REMOVE for n in names): removed+=len(names); continue
    out.append(L)
assert removed==len(REMOVE),(removed,len(REMOVE))
head='\n'.join(out)
head=head.rstrip()
assert head.endswith('rd_lat')
head=head+',\n    // v13: the raw command for the blocks\n    output reg         c_v,\n    output wire [7:0]  c_cmd,\n    output wire [63:0] c_a\n'
s=s[:a]+head+s[z:]
# always default line
rep("        h_push <= 1'b0; rg_we <= 1'b0; rs_we <= 1'b0; lb_we <= 1'b0; dh_we <= 1'b0; dh_rd <= 1'b0; imem_we <= 1'b0; tsend <= 1'b0; f_start <= 1'b0; f_reinit <= 1'b0; s_start <= 1'b0; d_we <= 1'b0;\n",
    "        c_v <= 1'b0; tsend <= 1'b0; f_reinit <= 1'b0;\n")
# EXEC case
e0=s.index('            EXEC: begin\n'); e1=s.index('            FACC:',e0)
newexec='''            EXEC: begin
                case (cmd)
                    "W": begin c_v <= 1'b1; st <= IDLE; end
                    "P": begin c_v <= 1'b1; st <= IDLE; end
                    "B": begin c_v <= 1'b1; st <= IDLE; end
                    "Q": begin c_v <= 1'b1; rlen <= 22; ridx <= 0; st <= REPLY; end
                    "E": begin c_v <= 1'b1; rlen <= 5; ridx <= 0; st <= REPLY; end
                    "M": if (!dh_busy) begin c_v <= 1'b1; st <= IDLE; end
                    "Y": begin c_v <= 1'b1; st <= IDLE; end
                    "X": begin c_v <= 1'b1; st <= IDLE; end
                    "L": if (!dh_busy) begin c_v <= 1'b1; st <= WAITD; end
                    "F": begin c_v <= 1'b1; st <= IDLE; end
                    "J": begin c_v <= 1'b1; st <= IDLE; end
                    "O": begin if (a[0] < NB) blk <= a[0][3:0]; st <= IDLE; end
                    "D": begin c_v <= 1'b1; st <= IDLE; end
                    "K": begin cfg_cl_x <= a[0][1:0] ^ 2'd2; cfg_dly_x <= a[1][1:0] ^ 2'd1; cfg_inv_x <= a[2][0]; f_reinit <= 1'b1; st <= IDLE; end
                    "w": if (f_busy || !f_init) st <= IDLE; else begin c_v <= 1'b1; st <= FACC; end
                    "r": if (f_busy || !f_init) begin fsave <= 32'hDEADBEEF; rlen <= 4; ridx <= 0; st <= REPLY; end
                         else begin c_v <= 1'b1; st <= FACC; end
                    default: st <= IDLE;
                endcase
            end
'''
old_exec=s[e0:e1]
# sanity: the old text must contain exactly the commands we replaced
for k in ['"W": begin imem_we','"P": begin h_push','"B": begin rg_we','"Q": begin q_tid','"E": begin q_tid','"M": if (!dh_busy) begin dh_we','"Y": begin lb_we','"X": begin rs_we','"L": if (!dh_busy) begin dh_rd','"F": begin f_start','"J": begin s_start','"O": begin if (a[0] < NB)','"D": begin d_we','"K": begin cfg_cl_x','"w": if (f_busy','"r": if (f_busy']:
    assert k in old_exec,k
s=s[:e0]+newexec+s[e1:]
rep("            FACC: if (fh_acc) begin fh_v <= 1'b0; st <= FACK; end\n","            FACC: if (fh_acc) begin st <= FACK; end\n")
# initial
i0=s.index('    initial begin s_start = 0;'); i1=s.index('end\n',i0)+4
s=s[:i0]+'    initial begin f_reinit = 0; blk = 0; soft_rst = 0; c_v = 0; end\n'+s[i1:]
# raw command wires, before the always block
rep('    wire rd_cls =','    assign c_cmd = cmd;\n    assign c_a = {a[7], a[6], a[5], a[4], a[3], a[2], a[1], a[0]};\n    wire rd_cls =')
open(F+'host_bridge_v13.v','w').write(s)
print('bridge v13 ok',s.count('\n'))
