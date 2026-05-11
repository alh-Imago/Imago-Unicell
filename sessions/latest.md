# Latest Session — 2026-05-11

## Tests
2,381 passing / 6 failing (all pre-existing deprecated)

## Latest commit
TBD — docs: VM getting started guide, port declarations, README link

## What was done
- docs/VM_GETTING_STARTED.md: new standalone guide (install → run → compile → API → workbench)
  All code examples verified against live VM before writing.
- docs/RUNNING.md: added "Declaring ports (Composer ports tab)" section
  and "CLI compile with port scan and prompt" subsection in §2d
- docs/INDEX.md: Getting Started section leads with VM_GETTING_STARTED.md;
  repo map updated
- README.md: docs table now includes VM_GETTING_STARTED.md
- MIGRATION_TODO.md: getting started item updated to reference new file

## Repo tidy status
- fp_tiles_old.py, shore_v2_old.py, main.py, unicell_composer_v2.html:
  do NOT exist in repo — already cleaned up in prior session
- .gitignore: already complete (egg-info, __pycache__, *.pyc, .DS_Store)

## Hardware status
- JTAG programmer: in transit, ~21 May 2026
- Kintex-7 XC7K480T: in transit, ETA Jul 2026

## Next session priorities
1. compiler_int32.py: wire a<b, min(), max() → INT32_LT_U/S, MIN, MAX
2. sort.py: n=16 INT32 sort testing
3. Composer: simulation limitations note (SYNC_WAIT/LOOP_MODE)
4. Hardware support matrix (inB/stor/init per FPGA target)
