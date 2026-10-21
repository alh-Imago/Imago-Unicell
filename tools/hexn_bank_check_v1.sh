# Hex-N END TO END: train the bank in RTL, classify the test samples with the RTL detectors, compare every test sample (answer and all burst counts) with the Python model. Usage: sh tools/hexn_bank_check_v1.sh   (cases: K NB AW S seed)
cd "$(dirname "$0")/.." || exit 1; ok=0; bad=0; D=${TMPDIR:-/tmp}
for c in "4 12 6 16 0" "4 12 6 16 1" "8 12 6 16 3" "4 18 7 16 4" "4 20 7 16 5" "8 20 7 16 6" "16 12 6 16 7" "16 20 7 16 8"; do set -- $c; K=$1; NB=$2; AW=$3; S=$4; seed=$5
  exp=$(python3 tools/hexn_bank_stim_v1.py $seed $K $NB $D/bk_stim.txt $AW $S 2>$D/bk_note.txt); NT=$((K*50))
  iverilog -g2012 -P tb_hexn_bank_v1.K=$K -P tb_hexn_bank_v1.NB=$NB -P tb_hexn_bank_v1.AW=$AW -P tb_hexn_bank_v1.S=$S -o $D/bk_tb.vvp rtl/tb_hexn_bank_v1.v rtl/hexn_bank_v1.v rtl/hexn_det_v2.v rtl/hexn_trainbank_v2.v rtl/hexn_cfgbank_v2.v rtl/hexn_sdiv_v1.v || exit 1
  out=$(vvp $D/bk_tb.vvp +stim=$D/bk_stim.txt); got=$(echo "$out" | grep -v -E 'CLOCKS|finish'); clk=$(echo "$out" | grep CLOCKS)
  rtl_acc=$(echo "$got" | awk '{n++; if ($3==$1) r++} END{printf "%.3f", r/n}')
  if [ "$exp" = "$got" ]; then ok=$((ok+1)); echo "K=$K NB=$NB AW=$AW seed=$seed: all $NT test samples identical to Python; RTL accuracy $rtl_acc ($clk) | $(cat $D/bk_note.txt)"; else bad=$((bad+1)); echo "DIFF K=$K NB=$NB seed=$seed (RTL accuracy $rtl_acc)"; diff <(echo "$exp") <(echo "$got") | head -6; fi
done; echo "End-to-end RTL bank matches Python in $ok of $((ok+bad)) cases"
