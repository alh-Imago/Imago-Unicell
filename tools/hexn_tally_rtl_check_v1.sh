# Hex-N: check rtl/hexn_tally_v1.v against the Python counted-detector model (tools/hexn_tally_v4.py rule, K=4, 16 samples/class, T=8, push 3) for several seeds and all four detectors. Usage: sh tools/hexn_tally_rtl_check_v1.sh
cd "$(dirname "$0")/.." || exit 1; ok=0; bad=0
iverilog -g2012 -o /tmp/tb_tally.vvp rtl/tb_hexn_tally_v1.v rtl/hexn_tally_v1.v || exit 1
for s in 0 1 2 3; do for d in 0 1 2 3; do
  exp=$(python3 tools/hexn_tally_rtl_stim_v1.py $s $d); got=$(vvp /tmp/tb_tally.vvp | grep -E '^-?[0-9]+ -?[0-9]+ ' | tail -1)
  if [ "$exp" = "$got" ]; then ok=$((ok+1)); else bad=$((bad+1)); echo "DIFF seed $s detector $d: python [$exp] rtl [$got]"; fi
done; done; echo "RTL matches Python in $ok of $((ok+bad)) checks"
