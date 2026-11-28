#!/bin/sh
# stage_mb_v15.sh - stage_mb_v14.sh plus sc_sys_v28, sc_block_v9, sc_top_k7_v21 and the fused-load units uc_unitx / uc_unitm (the hr line: byte and halfword loads on fused tasks; ledger #1607).  Cloned from stage_mb_v14.sh (left as proven).
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
sh stage_mb_v14.sh > /dev/null || exit 1
for f in sc_sys_v28 uc_unitx4 uc_unitm4 uc_unitx8 uc_unitm8 uc_unitx16 uc_unitm16 uc_unitx32 uc_unitm32; do cp "$S_CORE/$f.v" "rtl/$f.sv" || exit 1; done
for f in sc_block_v9 sc_top_k7_v21; do cp "$S_CORE/fpga/$f.v" "rtl/$f.sv" || exit 1; done
ls rtl
