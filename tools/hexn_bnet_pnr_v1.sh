# Merged bus network (hexn_bnet_net_v1) PLACED AND ROUTED for the Tang Nano 20K: native yosys synth_gowin, then YoWASP nextpnr-himbaechel-gowin at a target clock. Prints cells used, and the clock it reaches. Different chip from the Kintex card: a yardstick, not the card's speed.
# NETV=v2 selects the pipelined netlist (default v1). Usage: sh tools/hexn_bnet_pnr_v1.sh G PER NIN FB SQL [target_MHz] [seed]        (pins are arbitrary legal pins)
G=${1:-2}; PER=${2:-8}; NIN=${3:-16}; FB=${4:-1}; SQL=${5:-2}; F=${6:-27}; SEED=${7:-1}
cd "$(dirname "$0")/.." || exit 1; R=$(pwd); NETV=${NETV:-v1}; SV=$NETV; D=${OUT:-/tmp/hexn_bnet_pnr}/${NETV}_g${G}_p${PER}_n${NIN}_f${FB}_s${SQL}; mkdir -p $D; cd $D || exit 1
for f in hexn_bnet_bus_v2 hexn_bnet_ser_$SV hexn_bnet_tbus_$SV hexn_bnet_net_$NETV hexn_bnet_pnr_top_v1; do cp $R/sub/verilog/$f.v .; done; sed -i "s/hexn_bnet_net_v1 #/hexn_bnet_net_$NETV #/" hexn_bnet_pnr_top_v1.v
python3 - <<'PY' > top.cst
import os, lzma, msgpack, apycula
d=os.path.dirname(apycula.__file__)
db=msgpack.unpackb(lzma.open(os.path.join(d,'GW2A-18C.msgpack.xz')).read(), raw=False, strict_map_key=False, use_list=False)
po=db['pinout']['GW2AR-18C']['QFN88P']
free=[p for p,(io,fn) in sorted(po.items(), key=lambda x:int(x[0])) if p!='4' and not any(x in ('TMS','TCK','TDI','TDO') for x in fn) and 'RECONFIG' not in str(fn) and 'DONE' not in str(fn)]
print('IO_LOC "clk" 4;'); print('IO_PORT "clk" IO_TYPE=LVCMOS33;')
for n,p in zip(['sin','sout'], free): print('IO_LOC "%s" %s;'%(n,p)); print('IO_PORT "%s" IO_TYPE=LVCMOS33;'%n)
PY
/usr/bin/yosys -q -l synth.log -p "read_verilog -sv hexn_bnet_bus_v2.v hexn_bnet_ser_$SV.v hexn_bnet_tbus_$SV.v hexn_bnet_net_$NETV.v hexn_bnet_pnr_top_v1.v; chparam -set G $G -set PER $PER -set NIN $NIN -set FB $FB -set SQL $SQL hexn_bnet_pnr_top_v1; hierarchy -top hexn_bnet_pnr_top_v1; synth_gowin -top hexn_bnet_pnr_top_v1 -json net.json" >/dev/null 2>&1 || { echo "synthesis failed"; tail -5 synth.log; exit 1; }
yowasp-nextpnr-himbaechel-gowin --device GW2AR-LV18QN88PC8/I7 --vopt family=GW2A-18C --vopt cst=top.cst --json net.json --freq $F --timing-allow-fail --seed $SEED --report report.json --write routed.json > pnr.log 2>&1 || { echo "place and route failed:"; tail -8 pnr.log; exit 1; }
echo "== Tang Nano 20K, G=$G PER=$PER NIN=$NIN FB=$FB SQL=$SQL target ${F} MHz =="
grep -E "Max frequency|^Info:\s+(LUT4|ALU|DFF|BSRAM|RAM16|SSRAM|MULT|DSP)" pnr.log | tail -12
