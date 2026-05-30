# Imago UniCell — Active TODO
**Last updated: 2026-05-29 (end of session)**

---

## IMMEDIATE — Unblocked, ready to implement


### Sentinel compiler fixes (3 gaps)
- [ ] `_compile_binop_typed`: intercept `Constant` nodes before `_compile_expr` converts
      them to IRNode — so `int32 + 1` is caught as `Int32Value + literal`
- [ ] `return literal` in int32 branch: promote to Int32Value using function return annotation
- [ ] `sel_node.output_addr` in `_place_int32_mux`: int32 comparison result must expose
      output_addr. Currently only node_id exists on some IRNode types.
- [ ] `sentinel_core.py` full compilation → ICM output for each function

### Ward/Shore core compilation
- [ ] `ward_core.py` — Ward logic as compilable int32 functions (addr_match, health checks)
- [ ] `shore_core.py` — Shore registration and wave filtering as compilable functions
- [ ] int32 comparison normalisation: returns `1` not `0xFFFFFFFF` (output normalisation gap)
- [ ] `!=` comparison wired wrong in bool path — always returns 0

### Preload model — Case 2 (ordered injection, AND/OR/XOR)
- [x] AND/OR/XOR: direct preload from input bits — complete
- [x] staged_preload: Case 3 zero-extra-cell preload — complete
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


## MEDIUM TERM — Peripheral awareness (post-PCIe)

### Linux peripheral bridge
Staged rollout — each item builds on the last.

- [ ] **Keyboard** (first): evdev listener → bus writes at `KEYBOARD_POND_BASE + keycode`
      Each keypress/release is a bus write. Ward routes to focused workspace.
      ~50-100 cells for a full keyboard handler. Uses `GS_LOOP_BACK` for key-held state.
- [ ] **Mouse** (second): `EV_REL` delta X/Y → accumulator cells (loopback pattern)
      Validates `GS_LOOP_BACK` on silicon. Three button cells.
      Mouse position held in two loopback cells (X, Y) — natural LOOP_BACK test.
- [ ] **USB device detection** (third): udev events → Device Pond registration via Shore
      device_bridge.py stubs already exist. HID/MSC/Audio/CDC class detection.
      Connect/disconnect events wire into the Shore registration path.
- [ ] **Simple media demo** (integration): keyboard pond + state machine + ALSA output
      ~200-300 cells total. Space=play/pause, arrow keys=skip/volume.
      State machine in Ward cells. Output addresses → Linux bridge → mpv/ALSA.
      "A NOR gate computer playing music" — tangible demo.

**Dependency:** PCIe enumeration on Optiplex 9020 required for all of the above.

---

## MEDIUM TERM — Ward/Sentinel address collision detection

Two-layer invariant enforcement: static at pond admission, runtime in Ward/Sentinel.

### Layer 1 — Static check (ICM loader + Ward admission)
- [ ] `icm_loader.py` + `workspace._install()`: validate output_address uniqueness
      One pass: `{output_address: cell}` — if any addr appears twice, reject pond.
      Hard error with: `addr, cell_a, cell_b, pond_id`.
- [ ] Ward pond admission gate: re-run static check when admitting any new pond.
      Catches cross-pond address range collisions that the ICM loader can't see.

### Layer 2 — Runtime detection (unicell_array + Ward response)
- [ ] `unicell_array.py`: collision tracking in `tick()`.
      `written_this_epoch = {}` — if addr written twice in one tick, emit collision event.
      Detection is mechanical (array-level) — Ward owns the response policy.
- [ ] `controller.py`: `PondCollisionError` type, per-region `collision_mode` flag.
      Three modes stored in pond PTT entry:
        `STRICT` — freeze pond, log to Shore, raise to workspace (default)
        `DEBUG`  — log collision, continue (for program development)
        `OFF`    — no tracking (validated trusted programs, max performance)
- [ ] `ward.py`: collision event handler.
      Receives violation as normal bus event (reserved Ward address).
      Reads collision_mode from PTT, applies freeze/log/continue policy.
      Log format: `{addr, tick, pond_id, writer_a, writer_b, timestamp}`.

### Silicon path (post-PCIe validation)
- [ ] `unicell_array.v`: `last_writer` register per bus epoch + collision signal.
      On second write to same addr in same epoch → assert `collision_detected`.
      Feeds into controller as `CMD_COLLISION_EVENT` — same OS contract as VM path.
- [ ] Security hardening: malicious/buggy ICM from PCIe bridge cannot silently
      corrupt other ponds' data. Worst case = clean halt, no lateral contamination.

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
