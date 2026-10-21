# Hex-N board top, byte-level simulation: the testbench plays the host over the serial link and every reply is compared with the Python model. Usage: sh tools/hexn_tang_sim_v1.sh [shape cells seed]   (default hex7 7 3)
cd "$(dirname "$0")/.." || exit 1; SH=${1:-hex7}; K=${2:-7}; seed=${3:-3}; D=${TMPDIR:-/tmp}
exp=$(python3 tools/hexn_bank_stim_v1.py $seed $K 12 $D/tg_stim.txt 6 16 2>$D/tg_note.txt)
iverilog -g2012 -DLATMOD=hexn_lattice_${SH}_v1 -DNCLS=$K -DCLKDIV=8 -o $D/tg_tb.vvp rtl/tb_hexn_tang_top_v1.v rtl/hexn_tang_top_v1.v rtl/hexn_uart_v1.v rtl/gen/hexn_lattice_${SH}_v1.v rtl/hexn_bank_v2.v rtl/hexn_det_v2.v rtl/hexn_trainbank_v2.v rtl/hexn_cfgbank_v2.v rtl/hexn_sdiv_v1.v || exit 1
out=$(vvp $D/tg_tb.vvp +stim=$D/tg_stim.txt); got=$(echo "$out" | grep -v -E 'CLOCKS|finish'); echo "$out" | grep -E "BAD|CLOCKS"
rtl_acc=$(echo "$got" | awk '{n++; if ($3==$1) r++} END{printf "%.3f", r/n}')
if [ "$exp" = "$got" ]; then echo "board top over the serial link ($SH, K=$K, seed $seed): all $((K*50)) test samples identical to Python; accuracy $rtl_acc"; else echo "DIFF (accuracy $rtl_acc)"; diff <(echo "$exp") <(echo "$got") | head -5; fi
