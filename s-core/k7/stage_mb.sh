#!/bin/sh
# stage_mb.sh - stage.sh plus the files of the multi-block build (sc_sys_v15, fit_search_tree, host_bridge_v11, far_arb, sc_block, sc_top_k7_v8).
# Usage:  S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_mb.sh
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
sh stage.sh > /dev/null || exit 1
for f in sc_sys_v15 fit_search_tree; do cp "$S_CORE/$f.v" "rtl/$f.sv" || exit 1; done
for f in host_bridge_v11 far_arb sc_block sc_top_k7_v8; do cp "$S_CORE/fpga/$f.v" "rtl/$f.sv" || exit 1; done
ls rtl
