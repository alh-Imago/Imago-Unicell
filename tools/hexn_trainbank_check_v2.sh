# Hex-N: check rtl/hexn_trainbank_v2.v against the Python counted-detector training (tools/hexn_trainbank_stim_v1.py): weights and thresholds of every detector must be identical.
# Usage: sh tools/hexn_trainbank_check_v1.sh      (cases: K NB AW S seed)
cd "$(dirname "$0")/.." || exit 1; ok=0; bad=0; D=${TMPDIR:-/tmp}
for c in "4 12 6 16 0" "4 12 6 16 1" "4 12 6 16 2" "8 12 6 16 3" "4 18 7 16 4" "4 20 7 16 5" "8 20 7 16 6" "16 12 6 16 7" "16 20 7 16 8" "4 12 6 8 9"; do set -- $c; K=$1; NB=$2; AW=$3; S=$4; seed=$5
  exp=$(python3 tools/hexn_trainbank_stim_v1.py $seed $K $NB $D/tb_stim.txt $AW $S 2>$D/tb_note.txt)
  iverilog -g2012 -P tb_hexn_trainbank_v2.K=$K -P tb_hexn_trainbank_v2.NB=$NB -P tb_hexn_trainbank_v2.AW=$AW -P tb_hexn_trainbank_v2.S=$S -o $D/tb_tb.vvp rtl/tb_hexn_trainbank_v2.v rtl/hexn_trainbank_v2.v rtl/hexn_sdiv_v1.v rtl/hexn_cfgbank_v2.v || exit 1
  out=$(vvp $D/tb_tb.vvp +stim=$D/tb_stim.txt); got=$(echo "$out" | grep -E '^[0-9]+ [0-9]+ [0-9]+ [0-9]+$'); clk=$(echo "$out" | grep CLOCKS)
  if [ "$exp" = "$got" ]; then ok=$((ok+1)); echo "K=$K NB=$NB AW=$AW S=$S seed=$seed: identical ($clk) $(cat $D/tb_note.txt)"; else bad=$((bad+1)); echo "DIFF K=$K NB=$NB seed=$seed"; echo "python:"; echo "$exp"; echo "rtl:"; echo "$got"; fi
done; echo "Training bank RTL matches Python in $ok of $((ok+bad)) cases"
