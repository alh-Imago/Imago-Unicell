#!/bin/sh
# stage_v15.sh - stage.sh plus the three files of the sc_sys_v15 build (sc_sys_v15, fit_search_tree, sc_top_k7_v7).  Usage:  S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_v15.sh
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
sh stage.sh > /dev/null || exit 1
cp "$S_CORE/sc_sys_v15.v" rtl/sc_sys_v15.sv || exit 1
cp "$S_CORE/fit_search_tree.v" rtl/fit_search_tree.sv || exit 1
cp "$S_CORE/fpga/sc_top_k7_v7.v" rtl/sc_top_k7_v7.sv || exit 1
ls rtl
