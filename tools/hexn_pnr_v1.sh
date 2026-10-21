# Hex-N bank PLACED AND ROUTED for the Tang Nano 20K (GW2AR-LV18QN88PC8/I7), K detectors of NB wires. Synthesis with native yosys, then YoWASP nextpnr-himbaechel-gowin at 27 MHz. Prints used cells (of the chip), flip-flops, the clock speed it reaches,
# and the largest fan-out among the nets that carry the input wires. Usage: sh tools/hexn_pnr_v1.sh K NB AW [seed]      (S = 16 samples per class; the pins are arbitrary legal pins, this is a size/speed/routing test, not a board file)
K=${1:-4}; NB=${2:-12}; AW=${3:-6}; SEED=${4:-1}
cd "$(dirname "$0")/.." || exit 1; R=$(pwd); D=${OUT:-/tmp/hexn_pnr}/k${K}_n${NB}_a${AW}; mkdir -p $D; cd $D || exit 1
for f in hexn_bank_pnr_top_v1 hexn_bank_v1 hexn_det_v2 hexn_trainbank_v2 hexn_cfgbank_v2 hexn_sdiv_v1; do sed "s/parameter K = 4/parameter K = $K/; s/parameter NB = 12/parameter NB = $NB/; s/parameter AW = 6/parameter AW = $AW/" $R/rtl/$f.v > $f.v; done
KW=$(python3 -c "import math;print(max(1,math.ceil(math.log2($K))))")
python3 - $KW <<'PY' > top.cst
import sys, os, lzma, msgpack, apycula
kw=int(sys.argv[1]); d=os.path.dirname(apycula.__file__)
db=msgpack.unpackb(lzma.open(os.path.join(d,'GW2A-18C.msgpack.xz')).read(), raw=False, strict_map_key=False, use_list=False)
po=db['pinout']['GW2AR-18C']['QFN88P']
free=[p for p,(io,fn) in sorted(po.items(), key=lambda x:int(x[0])) if p!='4' and not any(x in ('TMS','TCK','TDI','TDO') for x in fn) and 'RECONFIG' not in str(fn) and 'DONE' not in str(fn)]
names=['rst','sin','ld','ans_valid','tr_busy','run_busy']+['ans_class[%d]'%i for i in range(kw)]
print('IO_LOC "clk" 4;'); print('IO_PORT "clk" IO_TYPE=LVCMOS33;')
for n,p in zip(names, free): print('IO_LOC "%s" %s;'%(n,p)); print('IO_PORT "%s" IO_TYPE=LVCMOS33;'%n)
PY
/usr/bin/yosys -q -l synth.log -p "read_verilog hexn_bank_pnr_top_v1.v hexn_bank_v1.v hexn_det_v2.v hexn_trainbank_v2.v hexn_cfgbank_v2.v hexn_sdiv_v1.v; synth_gowin -top hexn_bank_pnr_top_v1 -json bank.json" >/dev/null 2>&1 || { echo "synthesis failed"; exit 1; }
yowasp-nextpnr-himbaechel-gowin --device GW2AR-LV18QN88PC8/I7 --vopt family=GW2A-18C --vopt cst=top.cst --json bank.json --freq 27 --seed $SEED --report report.json --write routed.json > pnr.log 2>&1 || { echo "place and route failed:"; tail -5 pnr.log; exit 1; }
python3 - $K $NB $AW <<'PY'
import json, re, sys
log=open('pnr.log').read()
import subprocess
print("== Tang Nano 20K, K=%s detectors, %s wires, accumulator %s bits ==" % (sys.argv[1], sys.argv[2], sys.argv[3]))
for l in log.split('\n'):
    if re.search(r'^Info:\s+(LUT4|ALU|DFF|MUX2_LUT|RAM16|BSRAM|SSRAM|IOB|OBUF|IBUF|LUTRAM)', l) or 'Max frequency' in l or re.search(r'Info:\s+(Total|Pack|ALU).*', l) and 'util' in l.lower(): print(l.strip())
m=re.search(r'Routing (\d+) arcs', log)
if m: print('  routed connections (arcs):', m.group(1))
rp=json.load(open('report.json'))
u=rp.get('utilization',{}); 
for k,v in u.items(): print('  %-18s used %6s of %6s' % (k, v['used'], v['available']))
for c,v in rp.get('fmax',{}).items(): print('  clock %-8s achieved %.1f MHz (target %.1f)' % (c, v['achieved'], v['constraint']))
# input-wire fan-out from the routed netlist
nl=json.load(open('bank.json'))['modules']['hexn_bank_pnr_top_v1']['netnames']
cells=json.load(open('bank.json'))['modules']['hexn_bank_pnr_top_v1']['cells']
load={}
for cn,c in cells.items():
    for pn,bits in c['connections'].items():
        if c['port_directions'].get(pn)=='input':
            for b in bits:
                if isinstance(b,int): load[b]=load.get(b,0)+1
fan=[]
for n,v in nl.items():
    if re.match(r's_bits', n):
        for i,b in enumerate(v['bits']): fan.append((load.get(b,0), n, i))
fan.sort(reverse=True)
if fan: print('  input-wire nets (s_bits): loads per wire min %d, max %d, mean %.1f (%d wires)' % (fan[-1][0], fan[0][0], sum(f[0] for f in fan)/len(fan), len(fan)))
allf=sorted(load.values(), reverse=True)[:5]; print('  five largest fan-outs in the whole design:', allf)
PY
