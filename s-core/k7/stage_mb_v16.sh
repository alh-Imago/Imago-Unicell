#!/bin/sh
# stage_mb_v16.sh - stage_mb_v15.sh plus sc_sys_v29, sc_block_v10, sc_top_k7_v22 and uc_unity<W> (the hs line: misalignment traps; ledger #1608).  Cloned from stage_mb_v15.sh (left as proven).
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
sh stage_mb_v15.sh > /dev/null || exit 1
for f in sc_sys_v29 uc_unity4 uc_unity8 uc_unity16 uc_unity32; do cp "$S_CORE/$f.v" "rtl/$f.sv" || exit 1; done
for f in sc_block_v10 sc_top_k7_v22; do cp "$S_CORE/fpga/$f.v" "rtl/$f.sv" || exit 1; done
ls rtl
