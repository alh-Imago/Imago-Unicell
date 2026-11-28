#!/bin/sh
# stage_mb_v14.sh - stage_mb_v13.sh plus sc_sys_v27, fit_search_tree_v2, uc_core_v2w, sc_block_v8 and sc_top_k7_v20 (the hq / hp lines: high half, byte/half loads, byte-store unit; ledger #1598).  Cloned from stage_mb_v13.sh (left as proven).
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
sh stage_mb_v13.sh > /dev/null || exit 1
for f in sc_sys_v27 fit_search_tree_v2 uc_core_v2w; do cp "$S_CORE/$f.v" "rtl/$f.sv" || exit 1; done
for f in sc_block_v8 sc_top_k7_v20; do cp "$S_CORE/fpga/$f.v" "rtl/$f.sv" || exit 1; done
ls rtl
