# VM Test Suite

Run all: `PYTHONPATH=. pytest tests/vm/`
Run one: `PYTHONPATH=. python tests/vm/test_fp_tiles.py`

Tests that use the standalone runner (not pytest) must be run directly with python.
Tests that use pytest are collected automatically.

---

## Group map

### Core — cell, array, controller
| File | What it tests | Status |
|---|---|---|
| test_array.py | UniCell array tick, bus, firing | ✅ passing |
| test_controller.py | ImagoController load/run API | ✅ passing |
| test_new_tiles.py | Basic gate operations | ✅ passing |
| test_counter_tiles.py | Counter/accumulator tiles | ✅ passing |
| test_ecc.py | ECC reserved — intentional skip | ⏭ skipped |

### Compiler stack
| File | What it tests | Status |
|---|---|---|
| test_compiler.py | Basic compiler (single-bit) | ✅ passing |
| test_compiler_int32.py | INT32 compiler — full op suite | ✅ 101/101 |
| test_compiler_v2.py | Compiler v2 path | ✅ passing |
| test_compiler_tile_library.py | Tile library cache behaviour | ✅ passing |
| test_standalone_preload.py | Preloaded-A forward sim | ✅ passing |
| test_for_loop.py | Compiled for loops | ✅ passing |

### Tiles
| File | What it tests | Status |
|---|---|---|
| test_fp_tiles.py | Full tile library (INT32, FP32) | ✅ 187/187 |
| test_tile_library.py | Save/load round-trip, load_tile | ✅ passing |
| test_cla.py | Carry-lookahead adder tile | ✅ passing |

### Pond / Shore / Ward
| File | What it tests | Status |
|---|---|---|
| test_pond.py | Pond core behaviour | ✅ passing |
| test_pond_bootstrap.py | Pond bootstrap sequence | ✅ passing |
| test_pond_connect.py | Pond connection | ✅ passing |
| test_pond_ptt.py | PTT bus address | ✅ passing |
| test_pond_ptt_sentry.py | Sentry cell + PTT | ✅ passing |
| test_pond_region_scope.py | Region scoping | ✅ passing |
| test_pond_restart.py | Pond restart behaviour | ✅ passing |
| test_conditional_pond.py | Conditional pond | ✅ passing |
| test_workspace_pond.py | Workspace pond | ✅ passing |
| test_shore.py | Shore core | ✅ passing |
| test_shore_v2.py | Shore v2 | ✅ passing |
| test_shorekeeper.py | Shorekeeper | ✅ passing |
| test_ward.py | Ward | ✅ passing |

### Bridge
| File | What it tests | Status |
|---|---|---|
| test_bridge_anomaly.py | Bridge anomaly detection | ✅ passing |
| test_bridge_log.py | Bridge logging | ✅ passing |
| test_device_bridge.py | Device bridge | ✅ passing |

### Programs
| File | What it tests | Status |
|---|---|---|
| test_program_builder.py | Multi-file program compile/run | ✅ passing |
| test_program_image.py | Program image round-trip | ✅ passing |
| test_branch.py | BranchPoint / DataTable | ✅ passing |
| test_cast.py | Cast / query filtering | ✅ passing |

### IO / filesystem
| File | What it tests | Status |
|---|---|---|
| test_fs_search.py | Filesystem search | ✅ passing |
| test_uniflex.py | UniFlex storage manager | ✅ passing |
| test_gpu_array.py | GPU array | ✅ passing |
| test_display_pond.py | Display pond — requires pygame | ⏭ skipped |

### LLVM frontend
| File | What it tests | Status |
|---|---|---|
| test_llvm_frontend.py | LLVM IR parse → UniCell | ⚠ needs llvmlite |
| test_llvm_ir_mapper.py | LLVM IR mapper | ⚠ needs llvmlite |

Install llvmlite: `pip install llvmlite --break-system-packages`

---

## Archive
`tests/vm/archive/` — retired tests, kept for reference only.
- test_addr_latch.py — GS_ADDR_LATCH retired (2026-05-18)
- test_bridge_integration.py — uses write_config() which was retired

## Legacy
`tests/vm/legacy/` — stale API tests from v1/v2 migration. Not run.
Known failures: tick() removed, _stored_value removed, output_address_alt removed.
Not worth fixing — coverage is provided by the current test suite above.
