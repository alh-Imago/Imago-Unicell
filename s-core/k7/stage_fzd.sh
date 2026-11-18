#!/bin/sh
# stage_fzd.sh - copy the RTL of the fusion clock tests into rtl/ with a .sv name (ledger #1372).
# Usage:  S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_fzd.sh
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
mkdir -p rtl
for f in uc_unitd4 uc_unitd8 uc_unitd16 uc_unite4 uc_unite8 uc_unite16; do cp "$S_CORE/$f.v" "rtl/$f.sv" || exit 1; done
ls rtl | grep -E "uc_unit[rp]"
