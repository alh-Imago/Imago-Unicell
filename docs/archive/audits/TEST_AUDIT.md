# Test Audit — 2026-05-28

All tests in `tests/vm/`. Run via `pytest tests/vm/test_suite_runner.py`.
Last major test move: 2026-05-24.

---

## ✅ PASSING (12)

| Test | Notes |
|------|-------|
| test_fp_tiles | 161/161 — core tile tests, fully current |
| test_branch | 28/28 — BranchPoint/DataTable, fully current |
| test_pond | Passes |
| test_pond_ptt | Passes |
| test_pond_region_scope | Passes |
| test_conditional_pond | Passes |
| test_workspace_pond | Passes |
| test_ward | Passes |
| test_shore | Passes |
| test_shorekeeper | Passes |
| test_ptt_sentry | Passes |
| test_program_image | Passes |
| test_fs_search | Passes |
| test_array (pytest-style) | 19/19 |
| test_addr_latch (pytest-style) | 1/1 |

---

## ❌ FAILING — categorised by root cause

### Category A — 32-bit word vs single-bit expectation mismatch
Tests were written expecting single-bit values (0/1) but the VM now
returns 32-bit bus words (0x00000000 / 0xFFFFFFFF). Simple fix: update
expected values in test assertions, or call `& 1` on results.

| Test | Failures | Fix effort |
|------|----------|------------|
| test_compiler_v2 | 9 fail: AND/OR/MUX expect `1`, got `4294967295` | Low — update expected values |
| test_controller | 4 fail: NOT(0)=1 expects `1`, got `0xFFFFFFFF` | Low — update expected values |
| test_program_builder | 4 fail: same pattern | Low |
| test_tile_library | 1 fail: MUX result not normalised | Low |
| test_for_loop | Likely same pattern | Low |

### Category B — Stale API (UniCell attribute changes)
Tests reference old UniCell attributes that were renamed or removed
during the v2.2 migration. The VM API changed but tests weren't updated.

| Test | Error | Fix |
|------|-------|-----|
| test_freeze | `UniCell has no attribute 'tick'` | Remove/rewrite — `tick()` became `array.tick()` |
| test_while_loop | `UniCell has no attribute 'tick'` | Same |
| test_migration | `UniCell has no attribute '_stored_value'` | Remove — internal attribute, not public API |
| test_vm_image | `UniCell has no attribute '_stored_value'` | Same |
| test_select | `UniCell has no attribute 'output_address_alt'` | Remove — alt output retired in v2 |

### Category C — Missing import / renamed symbol
Tests import symbols that were renamed or removed in gate_states.py
or command_interface.py during the v2 migration.

| Test | Error | Fix |
|------|----------|-----|
| test_gpu_array | `cannot import GS_INVERT_OUT from gate_states` | Replace with `GS_SET_INVERT` or remove |
| test_gate_state_32 | Same | Same |
| test_handshake | `cannot import build_bus1 from command_interface` | `build_bus1` removed — rewrite or remove |

### Category D — Wrong working directory / path assumption
Tests assume they run from repo root and reference relative paths
that break when run from `tests/vm/`.

| Test | Error | Fix |
|------|-------|-----|
| test_pond_connect | `FileNotFoundError: composer/examples/not_gate.icm` | Fix path to use `os.path.join` from repo root |
| test_pond_bootstrap | Same | Same |

### Category E — Logic/data failures (deeper issues)
Tests run but compute wrong results — likely stale tile implementations
or changes to how cells fire that weren't reflected in the tests.

| Test | Failures | Notes |
|------|----------|-------|
| test_new_tiles | 14 fail: NOT/AND/OR wrong values (64-bit overflow) | Stale — predates 32-bit word normalisation |
| test_counter_tiles | 3 fail | Stale tile behaviour expectations |
| test_compiler_int32 | 1 fail: KS depth property | Minor — depth check too strict |
| test_cla | 19 fail: CLA not faster than ripple | CLA tile may not exist or changed |
| test_multi_dimm | `KeyError: None` in load_map | Stale multi-pond API usage |
| test_compiler_tile_lib | 5 fail: EQ/NOT correctness | Pre-dates preloaded-A fixes |

### Category F — External dependency missing
| Test | Error | Action |
|------|-------|--------|
| test_display_pond | `ModuleNotFoundError: pygame` | Mark `@pytest.mark.skip` — optional dep |

---

## Recommended action by priority

### Fix now (low effort, high value)
1. **test_compiler_v2, test_controller, test_program_builder, test_tile_library, test_for_loop**
   Update expected values from `1` → `0xFFFFFFFF` (or normalise with `& 1`).
   These are core compiler/controller tests — should be green.

2. **test_pond_connect, test_pond_bootstrap**
   Fix ICM file path: `os.path.join(os.path.dirname(__file__), '../../composer/examples/not_gate.icm')`

3. **test_display_pond**
   Add `pytest.mark.skip(reason="requires pygame")` at top.

### Update (medium effort)
4. **test_new_tiles, test_counter_tiles, test_compiler_tile_lib**
   Update to use 32-bit word inputs (0/0xFFFFFFFF) and `compute_tile_preloads`.
   These test the tile library — should reflect current tile API.

5. **test_cla**
   Verify CLA tile still exists and works, update expectations.

6. **test_compiler_int32, test_multi_dimm**
   Minor fixes — tighten KS depth check, fix None key in multi_dimm.

### Remove or archive (stale, low value)
7. **test_freeze, test_while_loop** — `UniCell.tick()` no longer exists.
   The freeze behaviour is covered by test_fp_tiles and test_branch.
   Candidate for removal unless freeze-specific coverage is needed.

8. **test_migration** — Tests internal attribute `_stored_value`.
   Internal APIs shouldn't be in external tests. Remove.

9. **test_vm_image** — Same internal attribute issue. Remove.

10. **test_select** — `output_address_alt` retired in v2. Remove.

11. **test_handshake** — `build_bus1` removed from command_interface.
    Rewrite against current API or remove.

12. **test_gpu_array, test_gate_state_32** — `GS_INVERT_OUT` renamed.
    Quick symbol fix or remove if coverage is elsewhere.

---

## Summary

| Status | Count |
|--------|-------|
| Passing | 15 |
| Fix now (easy) | 8 |
| Update (medium) | 5 |
| Remove/archive | 7 |
| External dep (skip) | 1 |
| **Total** | **36** |
