#!/bin/sh
# stage_fzr.sh - copy the RTL of the fusion clock tests into rtl/ with a .sv name (ledger #1369).
# Usage:  S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_fzr.sh
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
mkdir -p rtl
for f in uc_unitr4 uc_unitr8 uc_unitr16 uc_unitp4 uc_unitp8 uc_unitp16; do cp "$S_CORE/$f.v" "rtl/$f.sv" || exit 1; done
ls rtl | grep -E "uc_unit[rp]"
