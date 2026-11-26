#!/bin/sh
# run_builds_v1.sh - build several Vivado designs one after the other and write a summary (ledger #1500).  Usage (from s-core/k7, after stage_mb_v9.sh):
#   sh run_builds_v1.sh hh16s8u1n1 hh16s16u1n1
# Each build: vivado -mode batch -source vivado/run_vivado_v5.tcl -tclargs NAME, log vivado_NAME_v5.log.  A failed build does not stop the next one.
# Summary (also printed at the end): builds_summary_<first name>.txt.  It never loads anything onto the card.
cd "$(dirname "$0")" || exit 1
command -v vivado > /dev/null 2>&1 || . "${VIVADO_SETTINGS:-/media/alan/InternalHDD/Xilinx/2026.2/Vivado/settings64.sh}"
SUM="builds_summary_$1.txt"; : > "$SUM"
for b in "$@"; do
  echo "== building $b  $(date)" | tee -a "$SUM"
  vivado -mode batch -source vivado/run_vivado_v5.tcl -tclargs "$b" > "vivado_${b}_v5.log" 2>&1
  rc=$?
  echo "   finished $(date)  (vivado exit $rc)" >> "$SUM"
done
for b in "$@"; do
  {
  echo "== $b"
  echo "Synth 8-9873 count: $(grep -c 'Synth 8-9873' vivado_${b}_v5.log)"
  echo "ERROR lines in log: $(grep -c '^ERROR' vivado_${b}_v5.log)"; grep -m3 '^ERROR' "vivado_${b}_v5.log"
  echo "timing (WNS TNS fail endpoints  WHS THS fail endpoints):"
  grep -E "WNS|WHS" -A2 "vivado_out_$b/timing_summary.txt" 2>/dev/null | sed -n 3p
  grep -E "Slice LUTs|Slice Registers" "vivado_out_$b/utilization_routed.txt" 2>/dev/null | head -2
  echo "overlaps (first global iteration):"; grep -A12 "Phase 5.1 Global Iteration 0" "vivado_${b}_v5.log" | grep overlaps | tr -s ' ' | tr '\n' ';'; echo
  ls -l "vivado_out_$b/$b.bit" 2>&1
  } >> "$SUM"
done
cat "$SUM"
