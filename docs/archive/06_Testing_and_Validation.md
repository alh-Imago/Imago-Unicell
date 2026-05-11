# Imago UniCell — Testing and Validation
## Claudette v1.1

---

## Test Philosophy

Every architectural decision in Claudette has a corresponding test suite. The test suites are not an afterthought — they were written alongside the implementation and in several cases drove the design. When a new feature was added, the tests came first.

**Key principles:**
- No test uses `assertEqual` or a test framework — every test is a standalone Python script with `check()` / `check_eq()` functions that print PASS/FAIL directly
- Tests run in the simulation environment — no hardware required
- Every suite is independent — it can run in any order, with no shared state
- A new feature is not complete until its tests pass and the full regression still passes

---

## Test Results — Claudette v1.1

### Run date: April 2026 | 45 suites | 2586 tests | 0 failures

| Suite | Pass | Total | Fail | Coverage |
|-------|------|-------|------|----------|
| test_addr_latch.py | 49 | 49 | 0 | GS_ADDR_LATCH, 64-bit config register, scope bits, Bus 1/3 |
| test_array.py | 21 | 21 | 0 | UniCellArray tick, bus, segments, armed set |
| test_branch.py | 61 | 61 | 0 | if/else compilation, branch tiles, nested conditions |
| test_bridge_anomaly.py | 60 | 60 | 0 | Bridge anomaly detection, Ward integration |
| test_bridge_integration.py | 55 | 55 | 0 | Full bridge lifecycle, mask enforcement |
| test_cast.py | 54 | 54 | 0 | Cast/Ripple, Stone, process_mask filter, scope-ordered search |
| test_cla.py | 44 | 44 | 0 | Carry-lookahead adder vs ripple carry, depth verification |
| test_command_interface.py | 47 | 47 | 0 | 3-bus protocol, scope bits, auth enforcement, boot sequence |
| test_compiler.py | 35 | 35 | 0 | Python→cells, Int32Value, augmented assignment |
| test_compiler_int32.py | 58 | 58 | 0 | Full arithmetic operation set, comparison chains |
| test_compiler_tile_library.py | 38 | 38 | 0 | Tile-aware compilation, named tile selection |
| test_conditional_pond.py | 41 | 41 | 0 | CONDITIONAL pond, Ward dissolve contract, all 5 conditions, 3 actions |
| test_controller.py | 26 | 26 | 0 | Region loading, run(), capture, address mapping |
| test_counter_tiles.py | 86 | 86 | 0 | SHIFT/RIPPLE/DECREMENT counters, for loop integration |
| test_device_bridge.py | 34 | 34 | 0 | KeyboardBridge, MouseBridge, AudioBridge stub, VideoBridge stub |
| test_display_pond.py | 75 | 75 | 0 | Delta rendering, pygame window, thermal palette, multi-format |
| test_ecc.py | 54 | 54 | 0 | SECDED ECC encode/decode, single-bit correction, double-bit detect |
| test_for_loop.py | 21 | 21 | 0 | for loop compilation, counter tile selection |
| test_fp_tiles.py | 134 | 134 | 0 | Full tile library build + metadata (40 tiles inc. MOUSE_HANDLER) |
| test_freeze.py | 47 | 47 | 0 | FREEZE_BODY, bridge persistence, cell state capture |
| test_fs_search.py | 43 | 43 | 0 | SearchPond, FS Pond, path discovery, hidden FS |
| test_gate_state_32.py | 73 | 73 | 0 | 32-bit gate_state constants, mode flags, config register layout |
| test_gpu_array.py | 35 | 35 | 0 | GPUArrayBackend, NumPy fallback, tick parity with Python sim |
| test_llvm_frontend.py | 77 | 77 | 0 | LLVM IR parsing, CFG construction, phi nodes, instruction validation |
| test_llvm_ir_mapper.py | 86 | 86 | 0 | LLVM→ProgramImage lowering, phi→LATCH, br→SELECT, icmp→tiles |
| test_migration.py | 33 | 33 | 0 | FREEZE_BODY migration, address update, connection restoration |
| test_multi_dimm.py | 36 | 36 | 0 | Multi-segment array, emission limits, segment tracking |
| test_new_tiles.py | 57 | 57 | 0 | Recently added tiles, depth verification |
| test_pond.py | 163 | 163 | 0 | Pond lifecycle, security levels, bridges, whitelist, visit log |
| test_pond_ptt.py | 75 | 75 | 0 | PTT entries, scope fields, entries_by_scope, lookup_by_object_id |
| test_pond_region_scope.py | 42 | 42 | 0 | Pond region allocation, base_address, offset addressing |
| test_pond_restart.py | 44 | 44 | 0 | Pond restart, Ward escalation, COMPANION rule engine |
| test_pond_types.py | 64 | 64 | 0 | Type registry, default_scope per type, CONDITIONAL/SHOREKEEPER |
| test_program_builder.py | 28 | 28 | 0 | ProgramBuilder tile wiring, named range assignment |
| test_program_image.py | 66 | 66 | 0 | ProgramImage format, named ranges, run(), os_version=1.1 |
| test_select.py | 43 | 43 | 0 | GS_SELECT routing, conditional branching |
| test_shore.py | 49 | 49 | 0 | Shore v1 registry, lookup, update |
| test_shore_v2.py | 114 | 114 | 0 | ShoreV2 full feature set, register_extended_v2, scope summary |
| test_shorekeeper.py | 47 | 47 | 0 | ShoreKeeper heartbeat, HyperShore, scope counts, thermal zones |
| test_tile_library.py | 66 | 66 | 0 | TileLibrary registry, user tile precedence, CombinedLibrary |
| test_uniflex.py | 75 | 75 | 0 | UniFlex address space, token allocation, scope assignment |
| test_user_library.py | 54 | 54 | 0 | LIBRARY MODEL scan, import sandbox, user override |
| test_vm_image.py | 54 | 54 | 0 | VM image v3, OS stamp, PTT snapshot, extended entries |
| test_ward.py | 83 | 83 | 0 | Ward state machine, thermal tracking, dissolve contract, escalation |
| test_while.py | 39 | 39 | 0 | while loop compilation, loop variable model |
| **TOTAL** | **2586** | **2586** | **0** | **45 suites — 100% pass rate** |

---

## Suite Descriptions

### Core cell and array

**test_array.py** — UniCellArray tick loop, armed set management, bus wired-OR combining, segment emission limits, trace buffer, breakpoint halt.

**test_ecc.py** — SECDED (Single Error Correct, Double Error Detect) encode and decode. Single-bit corrections verified. Double-bit detection verified. ECC disabled path verified.

**test_gate_state_32.py** — All 32-bit gate_state constants (GS_PASS, GS_NOT, GS_SELECT, GS_LATCH, GS_ONE_SHOT, GS_INVERT_OUT, GS_BROADCAST, GS_SYNC_WAIT, GS_LOOP_BACK, GS_ADDR_LATCH, GS_BREAKPOINT). Config register layout. Mode flag parsing.

**test_addr_latch.py** — New in v1.1. GS_ADDR_LATCH constant (bit 23). Cell addr_latch flag initialisation. Normal cells return 3-tuple (unchanged). addr_latch cells return 4-tuple with full 64-bit address. Array stores extended addresses in `_extended_addresses`. Bus 1 scope bits (00/01/10). CommandInterface `set_addr_latch()` and `resolve_extended_address()`. Data bus stays 32-bit throughout.

### Tiles and compiler

**test_fp_tiles.py** — All 40 tiles in the library: build, cell count check, depth check, metadata validation. Includes MOUSE_HANDLER tile added in v1.1.

**test_cla.py** — Carry-lookahead adder vs ripple carry: correctness for all input combinations, depth reduction verified (~3× shallower than ripple).

**test_compiler.py** / **test_compiler_int32.py** — Python AST → CellMapRecord compilation. Int32Value arithmetic, augmented assignment, comparison chains, control flow.

**test_llvm_frontend.py** — LLVM IR parsing via llvmlite. CFG construction. Phi nodes with dotted label names. Instruction validation (accepted: add/sub/and/or/xor/icmp/phi/br/ret/alloca/load/store; rejected: getelementptr, vector, i64/float).

**test_llvm_ir_mapper.py** — LLVM IR → ProgramImage lowering. phi → LATCH storage cell. conditional br → SELECT routing. icmp → tile selection. Two-pass block processing in RPO.

### Pond and OS

**test_pond.py** — The most comprehensive suite. Pond creation, type enforcement, security level validation, bridge allocation, mask check, whitelist, visit log, COMPANION integration, scope and object_id fields.

**test_conditional_pond.py** — CONDITIONAL Pond lifecycle contracts. All five condition types (TIME, RETURN, COMPLETE, EXTERNAL, COMPOUND). All three action types (DISSOLVE, FREEZE, CHECKPOINT). COMPOUND ANY/ALL modes.

**test_ward.py** — Ward state machine transitions. Emission tracking. Thermal load/trend/state. Dissolve contract evaluation. Escalation path to COMPANION.

**test_cast.py** — Cast/Ripple engine. Stone construction. process_mask filtering. Scope-ordered search (LOCAL → SHORE → EXTENDED). preferred_scope field. RippleResult scope field. Skipping Stone.

**test_shore_v2.py** — Full ShoreV2 feature set. register_extended_v2 (new-style). resolve_extended_v2. resolve_full_addr. scope_summary. Object_id auto-assignment. Legacy proxy backward-compat.

### Hardware and extensions

**test_command_interface.py** — Three-bus protocol. Scope bits in Bus 1 (bits 16-17). CMD_RECONFIGURE + scope=LOCAL (lower config). CMD_RECONFIGURE + scope=EXTENDED (upper config). Auth enforcement. Silent rejection on mismatch. set_addr_latch(). resolve_extended_address().

**test_device_bridge.py** — KeyboardBridge stdin polling. MouseBridge pygame event packing. AudioBridge stub (returns STATUS_ERROR). VideoBridge stub (returns STATUS_ERROR).

**test_vm_image.py** — VM image v3 format. OS stamp (os_name=Claudette, os_version=1.1). PTT snapshot. Extended entries (both legacy proxy and new config_upper pairs).

---

## Running the Tests

### Full regression (all 45 suites)

```bash
cd /home/claude/unicell
for f in test_array.py test_controller.py test_compiler.py \
  test_program_builder.py test_multi_dimm.py test_ecc.py \
  test_fp_tiles.py test_tile_library.py test_pond.py \
  test_uniflex.py test_cast.py test_shore.py \
  test_bridge_integration.py test_compiler_tile_library.py \
  test_cla.py test_compiler_int32.py test_pond_region_scope.py \
  test_pond_types.py test_ward.py test_bridge_anomaly.py \
  test_select.py test_while.py test_freeze.py test_branch.py \
  test_shore_v2.py test_pond_ptt.py test_device_bridge.py \
  test_fs_search.py test_vm_image.py test_counter_tiles.py \
  test_gate_state_32.py test_command_interface.py \
  test_pond_restart.py test_for_loop.py test_conditional_pond.py \
  test_shorekeeper.py test_migration.py test_new_tiles.py \
  test_gpu_array.py test_program_image.py test_user_library.py \
  test_llvm_frontend.py test_llvm_ir_mapper.py \
  test_display_pond.py test_addr_latch.py; do
    python3 $f 2>&1 | grep "Results:"
done
```

### Single suite

```bash
python3 test_pond.py
python3 test_addr_latch.py
```

### Expected output (healthy)

```
Results: 163 passed, 0 failed out of 163 tests   # test_pond.py
Results:  49 passed, 0 failed out of  49 tests   # test_addr_latch.py
```

---

## Test Coverage by Architecture Layer

| Layer | Primary suites | Coverage |
|-------|---------------|----------|
| Cell (161-bit register) | test_array, test_gate_state_32, test_ecc, test_addr_latch | Full |
| Bus / wired-OR | test_array, test_multi_dimm | Full |
| Tile library | test_fp_tiles, test_tile_library, test_cla, test_counter_tiles | Full |
| Python compiler | test_compiler, test_compiler_int32, test_branch, test_while, test_for_loop, test_select | Full |
| LLVM path | test_llvm_frontend, test_llvm_ir_mapper | Full |
| Command bus | test_command_interface, test_gate_state_32 | Full |
| Pond / OS | test_pond, test_pond_types, test_pond_ptt, test_pond_region_scope | Full |
| Security / mask | test_pond, test_cast, test_bridge_integration, test_bridge_anomaly | Full |
| Conditional Ponds | test_conditional_pond, test_ward | Full |
| Ward / thermal | test_ward, test_shorekeeper | Full |
| Shore / registry | test_shore, test_shore_v2, test_uniflex | Full |
| Cast / discovery | test_cast, test_fs_search | Full |
| Migration | test_migration, test_freeze, test_pond_restart | Full |
| VM image | test_vm_image | Full |
| GPU backend | test_gpu_array | Full |
| Devices | test_device_bridge, test_display_pond | Full |
| 64-bit addressing | test_addr_latch, test_command_interface, test_shore_v2 | Full |
