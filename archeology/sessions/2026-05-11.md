# Latest Session — 2026-05-11 (full day)

## Tests
All pre-existing passing. Pre-existing failures unchanged (6).
test_workspace_pond.py: 19/19 (new)
test_pond_bootstrap.py: 36/36
test_pond_connect.py: 31/31
test_ptt_sentry.py: 20/20
test_compiler_int32.py: 82/82
test_compiler.py: 39/39

## Latest commit
610033b — two-mode workbench spec

## What was done today (in order)

### Docs
- docs/VM_GETTING_STARTED.md: new standalone guide, all examples verified
- docs/RUNNING.md: port declarations, PondManager API section
- docs/ICM_FORMAT.md: inputs_32/outputs_32 fields, OS bootstrap path, FPGA warnings
- docs/ARCHITECTURE.md: full OS layer rewrite — PondManager, bridge security,
  sentry cluster, PTT entry types, WORKSPACE topology
- docs/INDEX.md: expanded OS layer table, ICM table updated

### compiler_int32.py
- Lt/Gt/LtE/GtE → INT32_LT_U tile (was broken, returned None)
- min/max → INT32_LT_S + INT32_MUX (signed, overflow-safe)
- 82 tests including 20-pair fuzz

### Code audit
- _ptt_ref never wired → fixed in controller.load_map(ptt=...)
- Sentry placeholder address never patched → fixed in load_map
- model_library INT32_EQ figures corrected (63→95 cells)
- gate_states.py stale TODO removed
- Compiler NotImplementedError boundary tests added

### Pond bootstrap
- spawn_pond_from_icm(): full ICM→pond sequence
  input ports as TYPE_TILE_IN, output ports as TYPE_PRIMITIVE with sentries
- spawn_workspace(): PRIVATE WORKSPACE pond
- connect(): bus address wiring + whitelist grants both ways
- Bridge access check in UniCellArray Phase 0 tick loop
- Workspace quota (max 8 concurrent, configurable)

### WorkspacePond refactor
- launch_program / run_program / disconnect_program / status()
- Legacy bare-controller path preserved
- test_workspace_pond.py: 19 tests

### Other
- sort.py n=16 INT32 verified (62k cells, ~10s, correct)
- postcode_sort: INT32 real Haversine distances
- Hardware support matrix documented in fpga/README_FPGA.md
- Composer sim panel: limitations warning box
- Index Pond design decisions documented (all 5 items)

### Deferred
- VM performance mode (numpy): tagged FPGA-dependent — validate on silicon first
- Two-mode workbench spec written in MIGRATION_TODO:
  Mode A: VM microscope (cell inspector, bus monitor, FPGA budget toggle)
  Mode B: Silicon terminal (PTT health, Shore queries, identity/whitelist)
  Startup selector: reflect hardware / standalone / custom N
  Prerequisites: Shore user tables, ws list via Shore, Ward health report,
  session identity, FPGA budget enforcement

## Hardware status
- JTAG programmer: in transit, ~21 May 2026
- Kintex-7 XC7K480T: in transit, ETA Jul 2026
- Target release: August 2026 (post Kintex-7 stress tests)

## Next session priorities (post-JTAG ~21 May)
1. iCEBreaker bring-up: NOT gate → adder → SYNC_WAIT implementation
2. Shore user tables (gate for silicon terminal mode)
3. VM vs silicon diff tool (tick-by-tick comparison)
4. numpy VM performance (post silicon validation)
5. Two-mode workbench foundations
