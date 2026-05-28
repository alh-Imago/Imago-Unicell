# Imago UniCell — Active TODO
**Last updated: May 2026 (post test-suite + workbench session)**

---

## IMMEDIATE — Unblocked, ready to implement

### Tests (6 remaining Category E failures)
- [ ] test_compiler_tile_lib — EQ/NOT correctness, needs compute_tile_preloads in tile load path
- [ ] test_compiler_int32 — KS depth property check too strict, update bounds
- [ ] test_cla — CLA tile expectations stale, verify tile still correct
- [ ] test_new_tiles / test_counter_tiles — 32-bit word model not applied to these tile paths
- [ ] test_program_builder — ProgramBuilder not updated for preloaded-A pattern
      Root fix: update ProgramBuilder.build_and_run() to normalise inputs to 32-bit words

### iCEBreaker bring-up
- [ ] Full iCEBreaker bring-up sequence — load ICM via icm_loader.py, verify live
      CMD_PRELOAD now in firmware (0x0F) — preload_cell() wired in fpga_bridge.py ✓
- [ ] unicell_v3.v testbench: add specific tests for one_shot + loop_back interaction
      (pre-existing testbench timing failures need fixing separately)

### Workbench
- [ ] Workbench smoke test in test_suite_runner.py — import + instantiate to catch drift

---

## SHORT TERM — After iCEBreaker validation

### Kintex-7
- [ ] Kintex-7: swap bus_hit → bus_hit_r in timing-critical paths
      Add 1 cycle to KS_DEPTH in run_int32_function when targeting Kintex-7
- [ ] PCIe bring-up on Optiplex 9020 (Intel platform — weekend test pending)
- [ ] Kintex-7 top-level skeleton module

### Compiler
- [ ] INT32_MIN/MAX signed overflow boundary — ripple borrow fails at INT_MAX vs -1
      Consider KS-based signed comparison instead
- [ ] load_int32_function: extend for single-operand tiles (NOT, mask, shift)

### Composer / Workbench
- [ ] Add CMD_PRELOAD (0x0F) and CMD_PRELOAD_HI (0x16) to composer preset list
- [ ] Composer model library: audit depth/cell counts against current tile implementations
- [ ] Workbench linked-cell highlight: show hop count in logic tree panel too

---

## MEDIUM TERM — Silicon features

### FPGA / Hardware
- [ ] VM vs silicon diff tool (imago_diff.py)
- [ ] FPGA read-back command in Verilog state machine
- [ ] Wire thermal sensor to dedicated bus address at bring-up

### Counter / ECC Bridge
- [ ] CMD_DATA_COUNTED — opcode for sequence-tagged data packets
- [ ] Counter cell pattern: SELECT + confirmed-increment + CLEAR feedback
- [ ] NORBuilder: emit_packet_counter(N, base_address) helper

---

## LONG TERM — Deferred

### OS Layer (silicon)
- [ ] Ward as silicon program (~20-30 cells scanning PTT entries)
- [ ] PTT cell word comparison in silicon
- [ ] Shore table in silicon (resident pond)
- [ ] Multiple WORKSPACE ponds per PondManager

### 64-bit Addressing
- [ ] Widen bus_addr/bus_data to 64-bit when silicon arrives

### ASIC Investigation
- [ ] Install OpenLane, run synthesis on unicell.v
- [ ] TinyTapeout area estimate
- [ ] Draft chipIgnite application (Efabless priority)

### INT64 / Future
- [ ] INT64: extend compiler_int32 to 64-bit

---

## SECURITY PROPERTIES (design locked, implementation pending)
- [ ] Cell silently ignores CMD_RECONFIGURE if auth token does not match
- [ ] auth_mask register not readable via any bus operation
- [ ] auth_mask set exactly once and cannot be changed
- [ ] Bridge does not reveal whether it accepted or rejected a transaction

---

## RECENTLY COMPLETED (this session)
- ✅ CMD_PRELOAD (0x0F) + CMD_PRELOAD_HI (0x16) in unicell.v + fpga_bridge.py
- ✅ Composer: semantic opcode display, pond visualisation, logic tree, link highlighting
- ✅ Workbench: same semantic display + pond colours, consistent with composer
- ✅ Test suite: 22 failing → 6 failing
      VAR_TRUE/FALSE fixed (0xFFFFFFFF/0), backward-compat aliases added,
      8 stale v1 tests archived to tests/vm/legacy/
- ✅ Canvas pan/zoom fix for large designs (inferPonds throttling, tabindex, rAF)
- ✅ Workbench smoke test note added
