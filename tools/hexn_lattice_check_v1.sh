# Hex-N END TO END on the hex lattice (12 wires, edge bridges): train the generated lattice bank in RTL, classify the test samples, compare every sample (answer and all burst counts) with the Python model. Usage: sh tools/hexn_lattice_check_v1.sh
cd "$(dirname "$0")/.." || exit 1; ok=0; bad=0; D=${TMPDIR:-/tmp}
for c in "rhombus4 4 0" "rhombus4 4 1" "hex7 7 2" "hex7 7 3" "par8 8 4" "par16 16 5" "hex19 19 6"; do set -- $c; SH=$1; K=$2; seed=$3
  exp=$(python3 tools/hexn_bank_stim_v1.py $seed $K 12 $D/lt_stim.txt 6 16 2>$D/lt_note.txt)
  iverilog -g2012 -DLATMOD=hexn_lattice_${SH}_v1 -P tb_hexn_lattice_v1.K=$K -P tb_hexn_lattice_v1.NB=12 -P tb_hexn_lattice_v1.AW=6 -P tb_hexn_lattice_v1.S=16 -o $D/lt_tb.vvp rtl/tb_hexn_lattice_v1.v rtl/gen/hexn_lattice_${SH}_v1.v rtl/hexn_bank_v2.v rtl/hexn_det_v2.v rtl/hexn_trainbank_v2.v rtl/hexn_cfgbank_v2.v rtl/hexn_sdiv_v1.v || exit 1
  out=$(vvp $D/lt_tb.vvp +stim=$D/lt_stim.txt); got=$(echo "$out" | grep -v -E 'CLOCKS|finish'); clk=$(echo "$out" | grep CLOCKS)
  rtl_acc=$(echo "$got" | awk '{n++; if ($3==$1) r++} END{printf "%.3f", r/n}')
  if [ "$exp" = "$got" ]; then ok=$((ok+1)); echo "$SH (K=$K) seed=$seed: all $((K*50)) test samples identical to Python; RTL accuracy $rtl_acc ($clk)"; else bad=$((bad+1)); echo "DIFF $SH K=$K seed=$seed (RTL accuracy $rtl_acc)"; diff <(echo "$exp") <(echo "$got") | head -4; fi
done; echo "Lattice bank RTL matches Python in $ok of $((ok+bad)) cases"
