#!/bin/sh
# stage_fz.sh - copy the RTL of the fusion clock tests into rtl/ with a .sv name (ledger #1360).
# Usage:  S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_fz.sh
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
mkdir -p rtl
for f in uc_core_v2 uc_unitg4 uc_unitg8 uc_unitg16; do cp "$S_CORE/$f.v" "rtl/$f.sv" || exit 1; done
ls rtl | grep -E "uc_core_v2.sv|uc_unitg"
