#!/bin/sh
# stage.sh - copy the S-Core RTL into rtl/ with a .sv name (openXC7.mk reads a .v file as plain Verilog and everything but the top as .sv).
# Usage:  S_CORE=$HOME/Imago-Unicell-score/s-core sh stage.sh
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
cd "$(dirname "$0")" || exit 1
mkdir -p rtl
for f in uc_core_v2v sc_sys_v12; do cp "$S_CORE/$f.v" "rtl/$f.sv" || exit 1; done
for f in jtag_link_v1 jtag_link_v2 host_bridge_v10 farram_bram_v1 far_copy batch_seq_v2 sc_top_k7_v1 sc_top_k7_v3; do cp "$S_CORE/fpga/$f.v" "rtl/$f.sv" || exit 1; done
ls rtl
