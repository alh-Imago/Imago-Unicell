#!/bin/sh
# stage_mb_v3.sh - stage.sh plus the files of the multi-block build WITH the fusion unit (sc_sys_v17 (NU units), fit_search_tree, the unit files for 4, 8 and 16 lanes,
# host_bridge_v11, far_arb, sc_block_v2, sc_top_k7_v9).  Usage:  S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_mb_v3.sh
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
sh stage.sh > /dev/null || exit 1
for f in sc_sys_v17 fit_search_tree uc_unitw4 uc_unith4 uc_unitw8 uc_unith8 uc_unitw16 uc_unith16; do cp "$S_CORE/$f.v" "rtl/$f.sv" || exit 1; done
for f in host_bridge_v11 far_arb sc_block_v3 sc_top_k7_v10; do cp "$S_CORE/fpga/$f.v" "rtl/$f.sv" || exit 1; done
ls rtl
