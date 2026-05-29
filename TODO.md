# Imago UniCell — Active TODO
**Last updated: 2026-05-29 (end of session)**

---

## IMMEDIATE — Unblocked, ready to implement

### Preload model — Case 2 (ordered injection, AND/OR/XOR)
- [ ] `controller.py`: `ctrl.run(rid, a_inputs, b_inputs)` — inject A first,
      wait for propagation, then inject B. OR: two-phase `ctrl.load(a)` / `ctrl.run(b)`
- [ ] Tests: AND/OR/XOR tiles fire correctly standalone (no Python forward sim)
- [ ] Verify `run_int32_function` uses ordered injection path for these tiles

### Preload model — Case 3 (PreloadTile, KS adder prefix tree)
- [ ] `fp_tiles.py`: `make_preload_tile(compute_tile)` builder
      Emits carry-prefix-only KS tree. Output addresses = compute tile input addresses.
      INT32_ADD: ~480 cells. See docs/PRELOAD_MODEL.md.
- [ ] ICM v3 format: `regions[]` array in ICM for multi-region programs
      Backward-compatible — single-region ICMs remain valid.
      Affects: vm_image.py, program_builder.py, workspace.py, ICM spec.
- [ ] `model_library.py`: `PreloadModel` wrapping (preload_tile, compute_tile) pair
      API: `model.load(a,b)`, `model.run()`, `model.execute(a,b)`
- [ ] Standalone tests: run INT32_ADD/SUB/EQ/MUX without compute_tile_preloads()

### iCEBreaker bring-up
- [ ] Full iCEBreaker bring-up — load ICM via icm_loader.py, verify on silicon
      CMD_PRELOAD (0x0F) now wired in firmware ✓
- [ ] SYNC_WAIT test on 4-cell topology

### Code quality
- [ ] `pipeline_queue.py`: rewrite tick loop to use ctrl.run() not ctrl.array.tick()
      3 fixes already applied (placer.place() 5-tuple, storage_mode, bus format)

---

## SHORT TERM — After preload model complete

### Kintex-7
- [ ] PCIe bring-up on Optiplex 9020 (Intel platform — pending)
- [ ] Kintex-7: bus_hit → bus_hit_r in timing-critical paths
- [ ] Kintex-7 top-level skeleton module

### Compiler
- [ ] INT32_MIN/MAX signed overflow boundary — ripple borrow at INT_MAX vs -1
- [ ] load_int32_function: extend for single-operand tiles (NOT, mask, shift)

### Composer / Workbench
- [ ] Add CMD_PRELOAD (0x0F) and CMD_PRELOAD_HI (0x16) to composer preset list
      (topology drop-down should offer these as named options)
- [ ] Model library in Composer: audit cell counts/depths against current tiles
- [ ] Workbench smoke test in test_suite_runner.py

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

### Docs
- [ ] CELL_INTERNALS.md: update NOT cell section (GS_NOT_B, no preload needed)
- [ ] PRELOAD_MODEL.md: add PreloadTile diagram once built
- [ ] RUNNING.md: add Case 2/3 standalone execution examples once implemented
- [ ] docs/diagrams: add preload_model diagram

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

## RECENTLY COMPLETED (2026-05-29 session)
- ✅ Test suite: 22 failing → 27/27 passing (6 Category E, 8 archived)
- ✅ VAR_TRUE = 0xFFFFFFFF, VAR_FALSE = 0x00000000 (was 1/0)
- ✅ Tile builders: make_int32_and/or/xor/parity_32 pass preload_map to Tile
- ✅ ProgramBuilder.build_and_run() routes through run_compiled_function
- ✅ workspace.py: _run_via_compiler() path, _fn_type, _preloaded_a stored
- ✅ Root file audit: shore, model_library, llvm, workspace, fs_search, companion
- ✅ Subfolder audit: imago/, fpga/, docs/ — all validated or updated
- ✅ PRELOAD_MODEL.md: three-tier architecture documented
- ✅ GS_NOT_B fix: NOT cell now uses topology NOT(B) — no preload needed
    Case 1 static preload complete. NOT gate standalone-safe.
- ✅ Composer canvas pan/zoom fix (inferPonds throttled, rAF, tabindex)
- ✅ FILE_AUDIT.md + FOLDER_AUDIT.md: comprehensive tracking for all files
