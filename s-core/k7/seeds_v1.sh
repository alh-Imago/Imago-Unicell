#!/usr/bin/env bash
# seeds_v1.sh - try placement seeds one after another, unattended (overnight), stop at the first one that routes.
#
# Run inside the nix shell, in the build folder (demo-projects/sc_k7_sizes), after stage_v14.sh:
#   sh seeds_v1.sh                      (defaults: Makefile.v14_s16, seeds "1 3 2", freq 50)
#   MAKEFILE=Makefile.v13_s16 SEEDS="1 3" sh seeds_v1.sh
#   FREQ=45 sh seeds_v1.sh              (a lower target gives the router less timing pressure)
# Use bash if sh is not bash:  bash seeds_v1.sh
#
# Watch from a SECOND terminal (any time):   tail -f progress_<project>.txt
# Every minute-ish it writes one line: time, seed, elapsed, stage, newest router line.
#
# A seed is given up (log kept as ..._noroute.log) when
#   - the router has done at least MINITER iterations and the overused count fell by less than
#     MINDROP percent over the last WINDOW iterations (stuck), or
#   - it has run longer than MAXHOURS hours.
# Nothing here is a proof that a seed could never route: it is a time budget. Defaults: MINITER 15,
# WINDOW 8, MINDROP 15, MAXHOURS 6. Logs: build_<project>_seed<N>[_noroute].log
# The synthesis result (.json) is kept between seeds; the placement/route outputs (.fasm .frames .bit)
# are deleted before each seed so make really redoes them. The chip database is never touched.

MAKEFILE=${MAKEFILE:-Makefile.v14_s16}
SEEDS=${SEEDS:-"1 3 2"}
FREQ=${FREQ:-50}
MINITER=${MINITER:-15}
WINDOW=${WINDOW:-8}
MINDROP=${MINDROP:-15}
MAXHOURS=${MAXHOURS:-6}
CHECK=${CHECK:-60}                     # seconds between checks
MAKE_CMD=${MAKE_CMD:-"make -f $MAKEFILE"}   # tests replace this

PROJECT=$(sed -n 's/^PROJECT *= *//p' "$MAKEFILE" 2>/dev/null | head -1)
PROJECT=${PROJECT:-project}
PROG=progress_${PROJECT}.txt

say() { printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$PROG"; }

# newest "iter=N overused=X" line -> "N X" (empty if none)
last_iter() { grep -o 'iter=[0-9]* wires=[0-9]* overused=[0-9]*' "$1" 2>/dev/null | tail -1 | sed 's/iter=\([0-9]*\) .*overused=\([0-9]*\)/\1 \2/'; }
# overused at iteration N
iter_val()  { grep -o "iter=$2 wires=[0-9]* overused=[0-9]*" "$1" 2>/dev/null | tail -1 | sed 's/.*overused=//'; }

stage_of() {
  local f=$1
  if   grep -q 'Max frequency' "$f" 2>/dev/null && grep -q 'Routing' "$f" 2>/dev/null && grep -q 'iter=' "$f"; then echo "routing"
  elif grep -q 'Running router2' "$f" 2>/dev/null; then echo "router start"
  elif grep -q 'SA placement\|analytical placer' "$f" 2>/dev/null; then echo "placing"
  elif [ -s "$f" ]; then echo "synthesis/setup"
  else echo "starting"; fi
}

run_seed() {
  local seed=$1 log=build_${PROJECT}_seed${1}.log start now elapsed li it ov base b
  rm -f "${PROJECT}.fasm" "${PROJECT}.frames" "${PROJECT}.bit"
  say "=== seed $seed: start, freq $FREQ, log $log"
  setsid $MAKE_CMD PNR_ARGS="--freq $FREQ --seed $seed" > "$log" 2>&1 &
  local pid=$!
  start=$(date +%s)
  while kill -0 "$pid" 2>/dev/null; do
    sleep "$CHECK"
    now=$(date +%s); elapsed=$(( (now-start)/60 ))
    li=$(last_iter "$log"); it=${li% *}; ov=${li#* }
    say "seed $seed | ${elapsed} min | $(stage_of "$log") | ${li:+iter $it overused $ov}"
    if [ -n "$it" ] && [ "$it" -ge "$MINITER" ]; then
      b=$(( it - WINDOW )); base=$(iter_val "$log" "$b")
      if [ -n "$base" ] && [ "$base" -gt 0 ]; then
        # percent fallen over the window
        drop=$(( (base - ov) * 100 / base ))
        if [ "$drop" -lt "$MINDROP" ]; then
          say "seed $seed: STUCK (overused $base at iter $b -> $ov at iter $it, fell $drop% < $MINDROP%): stopping it"
          kill -- -"$pid" 2>/dev/null; sleep 5; kill -9 -- -"$pid" 2>/dev/null
          mv "$log" "build_${PROJECT}_seed${seed}_noroute.log"; return 1
        fi
      fi
    fi
    if [ "$elapsed" -ge $(( MAXHOURS*60 )) ]; then
      say "seed $seed: time budget ${MAXHOURS} h used up: stopping it"
      kill -- -"$pid" 2>/dev/null; sleep 5; kill -9 -- -"$pid" 2>/dev/null
      mv "$log" "build_${PROJECT}_seed${seed}_noroute.log"; return 1
    fi
  done
  wait "$pid"; local rc=$?
  if [ "$rc" -eq 0 ] && [ -s "${PROJECT}.bit" ]; then
    say "seed $seed: DONE, bitstream ${PROJECT}.bit written"
    say "  $(grep 'Max frequency' "$log" | tail -1)"
    cp "${PROJECT}.bit" "${PROJECT}_seed${seed}.bit"
    return 0
  fi
  say "seed $seed: make ended with code $rc and no bitstream: see $log (kept as ..._fail.log)"
  mv "$log" "build_${PROJECT}_seed${seed}_fail.log"; return 2
}

say "seeds_v1: $MAKEFILE, seeds: $SEEDS, freq $FREQ, give up after $MAXHOURS h or when stuck"
for s in $SEEDS; do
  run_seed "$s"; rc=$?
  [ "$rc" -eq 0 ] && { say "finished: seed $s routed. Check 'Max frequency' in its log before loading (never load a bitstream whose timing check failed)."; exit 0; }
done
say "finished: no seed routed (logs kept as ..._noroute.log / ..._fail.log)"
exit 1
