# Legacy Full-Cell Tests

These 33 tests were moved here because the modules they test were
archived to `archeology/onion/` (`points.md #364`) — the old
addressed-bus, `gate_state`-based VM/compiler/tile-library stack,
confirmed genuinely superseded by the Unicell-S rebuild this session
(`nano/icm_v3.py`, `nano/unicell_super_automaton_v1.py`,
`nano/dsl_compiler_v1.py`, `nano/super_tile_library_v1.py`,
`nano/composed_tile_library_v1.py`, `nano/workbench_v1.py`,
`nano/gpu_array_v1.py`).

This is a DIFFERENT reason from `tests/vm/legacy/`'s own README (API
changes within modules that still exist) — here, the modules
themselves no longer exist in the live tree at all. The real source is
not lost: every archived module is byte-for-byte preserved and
independently checksum-verified in `archeology/onion/` (`old_full_
cell_vm_core.onion`, `old_full_cell_tile_library.onion`, `old_full_
cell_ui_and_gpu.onion`, `old_hardware_bringup.onion`).

If any of this functionality needs test coverage again, write it fresh
against the current Unicell-S API — these tests exercise a genuinely
different architecture (bus addresses, `gate_state` words) that the new
substrate doesn't have.

| File | What it tested (old architecture) |
|------|------|
| `test_array.py` | `UniCellArray`'s own addressed-bus array |
| `test_branch.py` | `ImagoController`-driven branching |
| `test_cla.py` | Carry-lookahead adder tiles, old compiler |
| `test_community_raw.py` | Raw `fp_tiles` community model tiles |
| `test_compiler.py`, `test_compiler_gaps.py`, `test_compiler_int32.py`, `test_compiler_tile_library.py`, `test_compiler_v2.py` | The old `ImagoCompiler`/`compiler_int32.py` |
| `test_controller.py` | `ImagoController` |
| `test_counter_tiles.py`, `test_new_tiles.py`, `test_tile_library.py` | The old `model_library.py`/`fp_tiles.py` tile system |
| `test_ecc.py` | Old ECC demo, addressed-bus array |
| `test_for_loop.py` | Old compiler control-flow support |
| `test_fp_tiles.py` | `fp_tiles.py` directly |
| `test_gpu_array.py` | The old `gpu_array.py` (array-of-registers layout, not the new `SuperCell` field shape) |
| `test_level_watchdog.py`, `test_mif_mux.py`, `test_mif_recip.py`, `test_mif_rsqrt.py`, `test_walker.py` | Old MIF-macro tiles |
| `test_nettrix.py`, `test_optitrix.py`, `test_sensortrix.py` | Old Trix-family runners, old compiler pipeline (the domain LOGIC itself may still be worth porting later — see `points.md #360`'s own note on TRIX — the PLUMBING these tests exercise is what's dead) |
| `test_pond.py`, `test_pond_restart.py`, `test_shorekeeper.py`, `test_workspace_pond.py`, `test_ptt_sentry.py` | OS/Pond-layer tests with a direct old-VM dependency (`unicell_array`/`controller`) -- the Pond/Shore/Ward modules themselves were archived in the second batch below (`#365`) |
| `test_program_builder.py`, `test_program_image.py` | Old `program_builder.py`/`program_image.py` |
| `test_standalone_preload.py` | Old standalone preload path, old compiler |

`points.md #364` has the full archival record.

## Second batch (`points.md #365`) — the rest of the old ecosystem

Per Alan's own directive to "really clean house": the OS/Pond layer,
the Trix domain family, `cell_format.py`, the LLVM frontend, old demo
algorithms, and misc utilities that only served the old ecosystem --
all archived to `archeology/onion/`. Every module these 28 tests
reference is gone from the live tree.

| File | What it tested (old architecture) |
|------|------|
| `test_bridge_anomaly.py`, `test_bridge_log.py` | Old Pond bridge/anomaly detection |
| `test_cast.py` | Old `cast.py` type-casting demo |
| `test_community_models.py` | `cell_format.py`'s own `FormatRegistry` |
| `test_conditional_pond.py` | Old Pond conditional logic |
| `test_device_bridge.py` | Old `device_bridge.py`/`shore_v2.py` |
| `test_display_pond.py` | Old `display_pond.py` (pygame-based, already `SKIP`-guarded) |
| `test_flowtrix.py`, `test_flowtrix_collide.py`, `test_flowtrix_cylinder.py` | The FlowTrix domain family, all living inside `cell_format.py` |
| `test_fs_search.py` | Old `fs_search.py` |
| `test_llvm_frontend.py`, `test_llvm_ir_mapper.py` | The old LLVM-IR frontend, targeting the old `ir.py` |
| `test_miditrix.py` | The MidiTrix domain family |
| `test_neurotrix_lif.py`, `test_neurotrix_lif_mif.py` | The NeuroTrix domain family |
| `test_pipeline_bridge_check.py`, `test_pipeline_compile.py` | `cell_format.py`'s own bridge/pipeline compile checks |
| `test_pond_bootstrap.py`, `test_pond_connect.py`, `test_pond_ptt.py`, `test_pond_region_scope.py` | The old Pond OS-layer subsystem |
| `test_shore.py`, `test_shore_v2.py`, `test_ward.py` | The old Shore/Ward OS-layer subsystem |
| `test_uniflex.py` | Old `uniflex_fs.py` |
| `test_suite_runner.py` | The old script-test aggregator -- its own `SCRIPT_TESTS` list references nearly every file already moved here, its purpose is now moot |

`points.md #365` has the full archival record for this batch.
