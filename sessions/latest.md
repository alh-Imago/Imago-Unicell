# Latest Session — 2026-05-11

## Tests
2,381 passing / 6 failing (all pre-existing deprecated)

## Latest commit
2b19463 — User library: ~/.imago/library/

## What was done
- INT32 bitonic sort (sort.py --mode int32, n=4✓ n=8✓)
- postcode_sort.py: real Haversine metre precision via INT32_CAS
- Doc tidy: 14 v1.1 docs archived, diagrams/ folder, INDEX links fixed
- model_library.py + Composer: INT32_LT_U/S, MIN, MAX, CAS registered
- fpga/README_FPGA.md: version header updated
- composer/models/INDEX.md: 10 bundled examples listed
- imago/library.py: user library at ~/.imago/library/
- CLI: imago init, imago library add/list/remove/path
- VM.load_library(), library_programs(), library_path()
- docs/LIBRARY.md: full user library documentation

## Hardware status
- JTAG programmer: in transit, ~21 May 2026
- Kintex-7 XC7K480T: in transit, ETA Jul 2026

## Next session priorities
1. compiler_int32.py: wire a<b, min(), max() → INT32_LT_U/S, MIN, MAX
2. sort.py: n=16 INT32 sort testing
3. Composer: simulation limitations note (SYNC_WAIT/LOOP_MODE)
4. Hardware support matrix (inB/stor/init per FPGA target)
