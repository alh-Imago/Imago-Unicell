#!/bin/sh
# stage_v13.sh - stage.sh plus the two files of the sc_sys_v13 build (sc_sys_v13, sc_top_k7_v5).  Usage:  S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_v13.sh
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
sh stage.sh > /dev/null || exit 1
cp "$S_CORE/sc_sys_v13.v" rtl/sc_sys_v13.sv || exit 1
cp "$S_CORE/fpga/sc_top_k7_v5.v" rtl/sc_top_k7_v5.sv || exit 1
ls rtl
