#!/bin/sh
# stage_fzp.sh - copy the RTL of the fusion clock tests into rtl/ with a .sv name (ledger #1364).
# Usage:  S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_fzp.sh
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
mkdir -p rtl
for f in uc_unitp4 uc_unitp8 uc_unitp16; do cp "$S_CORE/$f.v" "rtl/$f.sv" || exit 1; done
ls rtl | grep -E "uc_unitp"
