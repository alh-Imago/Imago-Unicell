#!/bin/bash
# Overnight size ladder for the Hex-N card design: builds hexn at growing NCELL (cells behind the glue buffer), one after the other, smallest first, and writes one result block per size.
# Run from ~/ypcb-00338-1p1 INSIDE the openXC7 nix shell (nix develop github:openxc7/toolchain-nix), with the chipdb set:
#   export CHIPDB=/home/alan/openFPGALoader/build/demo-projects/chipdb/xc7k480tffg1156.bin
#   bash designs/hexn/sweep_v1.sh 32 64 128 255            (sizes optional; default 32 64 128 255; HEXN_SHAPE=hex19 default)
# Output goes to $HEXN_STORE (default /mnt/hdd/hexn_builds, the big disk: mount it first, `sudo mount /dev/sda1 /mnt/hdd`), one folder per size, with a symlink in designs/hexn so the build tools find it. Results: $HEXN_STORE/sweep_results.txt (also printed).
# After each build the big intermediate files are deleted (the .bit, the logs and the timing report stay). The run stops at the first size that fails, or when less than 15 GB are free on the store.
# HEXN_TAG (optional) is added to every build folder name (for example HEXN_TAG=_c2 keeps an earlier build of the same size). THREADS (default 4) is the number of placer threads; more threads use more memory. DRY=1 only prints what it would do.
set -u
[ -n "${CHIPDB:-}" ] || { echo "set CHIPDB first (see the comment at the top of this script)"; exit 1; }
SHAPE=${HEXN_SHAPE:-hex19}; STORE=${HEXN_STORE:-/mnt/hdd/hexn_builds}; THR=${THREADS:-4}
[ $# -gt 0 ] && NCS="$*" || NCS="32 64 128 255"
D=designs/hexn; [ -d "$D" ] || { echo "run this from ~/ypcb-00338-1p1 (designs/hexn not found)"; exit 1; }
mkdir -p "$STORE" || exit 1
res=$STORE/sweep_results.txt
for nc in $NCS; do
    name=build_${SHAPE}_nc$nc${HEXN_TAG:-}
    free_gb=$(df -BG --output=avail "$STORE" | tail -n1 | tr -dc 0-9)
    if [ "${free_gb:-0}" -lt 15 ]; then echo "only ${free_gb} GB free on $STORE: stopping before $nc cells" | tee -a "$res"; break; fi
    mkdir -p "$STORE/$name"; ln -sfn "$STORE/$name" "$D/$name"
    echo "=== $SHAPE, $nc cells, started $(date '+%F %T'), THREADS=$THR" | tee -a "$res"
    if [ -n "${DRY:-}" ]; then echo "(dry run: HEXN_SHAPE=$SHAPE HEXN_NCELL=$nc BUILD=$name THREADS=$THR ./fpga build $D)"; continue; fi
    t0=$SECONDS
    HEXN_SHAPE=$SHAPE HEXN_NCELL=$nc BUILD=$name THREADS=$THR FPGA_HOST=$(hostname -s) ./fpga build $D > "$STORE/$name.log" 2>&1; rc=$?
    out=$STORE/$name
    { echo "finished $(date '+%F %T') after $((SECONDS - t0)) s, exit code $rc"
      grep -E "^==|Max frequency|using" "$STORE/$name.log" | sed 's/^/  /'
      grep -h -A14 "Device utilisation" "$out"/hexn.nextpnr.log 2>/dev/null | grep -E "LUT|FF|DSP|RAMB|SLICE|CARRY" | sed 's/^Info: */  /' | head -12
      ls -l "$out/hexn.bit" 2>/dev/null | sed 's/^/  /'
      [ "$rc" -ne 0 ] && tail -n 15 "$STORE/$name.log" | sed 's/^/  | /'
    } | tee -a "$res"
    rm -f "$out"/hexn.fasm "$out"/hexn.board.fasm "$out"/hexn.frames "$out"/hexn.json
    [ "$rc" -ne 0 ] && { echo "build failed at $nc cells: stopping" | tee -a "$res"; break; }
done
echo "=== ladder finished $(date '+%F %T'). Results: $res" | tee -a "$res"
