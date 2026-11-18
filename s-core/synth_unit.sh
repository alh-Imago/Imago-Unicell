#!/bin/bash
# usage: synth_unit.sh file module  -> Xilinx LUT6 / FF of a module that has sc_lane cells, read PER MODULE from yosys's hierarchical report
# (synth_all.sh adds a hierarchical report twice; this one does not).  Prints the controller (everything except the lanes), one lane, and the total.
f=$1; m=$2
yosys -q -p "read_verilog -sv $f; hierarchy -top $m; synth_xilinx -top $m; tee -o /tmp/su_$$.txt stat" >/dev/null 2>&1
python3 - "$m" /tmp/su_$$.txt <<'PY'
import sys, re
top, f = sys.argv[1], sys.argv[2]; mods = {}; cur = None; inh = False
for ln in open(f):
    m = re.match(r'=== (.+?) ===', ln)
    if m: cur = m.group(1); inh = (cur == 'design' or cur == 'hierarchy'); mods[cur] = dict(lut=0, ff=0, lane=0, other={}); continue
    if cur is None or cur.startswith('design'): continue
    p = ln.split()
    if len(p) == 2 and re.match(r'LUT[1-6]$', p[0]): mods[cur]['lut'] += int(p[1])
    elif len(p) == 2 and p[0].startswith('FD'): mods[cur]['ff'] += int(p[1])
    elif len(p) == 2 and p[0] in ('CARRY4', 'MUXF7', 'MUXF8', 'RAMB18E1', 'RAMB36E1', 'RAM32M', 'RAM64M'): mods[cur]['other'][p[0]] = int(p[1])
    elif len(p) == 2 and p[0] == 'sc_lane': mods[cur]['lane'] = int(p[1])
t = mods[top]; l = mods.get('sc_lane', dict(lut=0, ff=0, lane=0, other={}))
print('%-12s controller LUT6 %5d  FF %4d | lane LUT6 %3d x %2d = %4d | total LUT6 %5d   other cells in controller: %s' % (top, t['lut'], t['ff'], l['lut'], t['lane'], l['lut'] * t['lane'], t['lut'] + l['lut'] * t['lane'], t['other'] or '-'))
PY
