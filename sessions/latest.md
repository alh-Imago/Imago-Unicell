# Session Summary — 2026-05-09
## Tier 2 Complete + Tier 4 Progress

---

## HARDWARE STATUS

| Item | Cost | Order | ETA | Status |
|------|------|-------|-----|--------|
| Kintex-7 XC7K480T board | £54.90 | 22-14594-85183 | 2 Jun – 6 Jul | IN TRANSIT |
| JTAG SMT2 programmer | £25.74 | 23-14593-40180 | By 21 May | IN TRANSIT |
| Vivado ML Standard (7 Series) | Free | N/A | Downloading | Install in progress |

---

## WHAT WAS DONE

### fp_tiles.py — NORBuilder v2 cleanup (Tier 2 final item)

**NOR2 calls eliminated — last v1 remnant removed:**
- `COUNTER_DECREMENT` zero-detector: `NOR2` tree → `OR2` tree + `NOT` (native v2)
- `SR_LATCH`: `NOR2(a,b)` → `NOT(OR2(a,b))` (2 v2 native cells, cleaner semantics)

**INT32_SUB upgraded to Kogge-Stone:**
- Was: ripple-carry, depth 65, 192 cells
- Now: Kogge-Stone, depth 12, 517 cells
- Correctness verified via test_compiler_int32.py (58/58 ✓)

**GS_OUT_POSEDGE added to all NORBuilder emissions:**
- `_emit`, `_emit2`, `_emit_v2` all OR in `GS_OUT_POSEDGE`
- Safe default: output releases on posedge N+1

### ir.py — GS_OUT_POSEDGE on all compiler-emitted cells

All paths in `lower_to_cell_map_v2` now set `GS_OUT_POSEDGE`.

### model_library.py — FP32 estimates → actuals

| Model | Old | New |
|-------|-----|-----|
| FP32_ADDER | 3,000 cells / depth 40 | **1,253 cells / depth 85** |
| FP32_MULTIPLIER | 35,000 cells / depth 80 | **3,066 cells / depth 89** |
| INT32_SUBTRACTOR | 580 cells / depth 13 | **517 cells / depth 12** |

### pond_types.py + pond.py — Tier 2 threshold migration

`PondTypeSpec` now has `stall_threshold` and `anomaly_threshold` fields.
Each type has tuned values (DEVICE=15 cycles, PROCESS=100, FILE=200, etc.).
`Bridge.__init__` reads from type spec, falls back to 50/50.0.

### OR lowering confirmed (Tier 4)

Depth gaps 0,1,3,5 all produce correct OR results. Implementation confirmed correct.

### SYNC_WAIT test updated (Tier 4)

`test_gate_state_32.py`: SYNC_WAIT is 1 cell in v2 (not 3), depth = max+1 (not max+2).

### unicell-edge synced

fp_tiles.py, ir.py, compiler_int32.py, model_library.py, test_fp_tiles.py synced.

---

## TEST BASELINE

```
Main repo:    2,329 passed / 6 failed
  test_cla.py:               41p 3f  (deprecated)
  test_compiler_tile_library: 37p 1f  (pre-existing)
  test_for_loop.py:          19p 2f  (RIPPLE, deprecated)

unicell-edge: 2,326 passed / 9 failed  (all pre-existing or deprecated)
```

---

## MIGRATION_TODO STATUS

- Tier 1: ✅ Complete
- Tier 2: ✅ **Complete**
- Tier 3: Silicon features (deferred to hardware)
- Tier 4: OR lowering ✅, GS_OUT_POSEDGE ✅; remaining: compiler constant injection, workbench UI
- Tier 5: VM package — not started
- Tier 6: Docs — not started

---

## GIT STATUS

Commit: 768fb72 — Tier 2 complete + Tier 4 progress
Branch: main
Pushed: ✓

---

## TODO — NEXT SESSION

### Immediate (Tier 4):
- [ ] Compiler constant injection: const_0/const_1 auto-registered in imap
- [ ] Workbench UI: input_b_address display, two-input cell indicator

### High value:
- [ ] Tier 5: Standalone VM package (pip install imago-vm)
- [ ] Tier 6: README.md rewrite (vision + architecture + portability story)

### Hardware (when JTAG arrives ~21 May):
- [ ] Test JTAG programmer with iCEBreaker first
- [ ] XDC constraints file for Kintex-7
- [ ] Vivado TCL build script


---

## Session 2026-05-09 (continued) — Tier 4 Complete + Docs

### Compiler constant injection (Tier 4)

`compile_function()` now populates `self.known_values: {bus_addr: val}` for every
literal constant in compiled source (e.g. `a and 1` registers `{addr: 1}`).
`load_map()` accepts `known_values=` and stores it on `Region`. `start()` auto-injects
before user inputs. Updated: `test_compiler.py`, `compiler.py`, `compiler_int32.py`,
`program_builder.py`. No API breaks.

### Workbench UI (Tier 4)

Inspector panel: `Input addr` → `Input A addr`; conditional `Input B addr` and
`Input B val` rows for SYNC_WAIT cells; `Two-input` row showing `A↑ B↓`.
Grid: two-input cells get a small accent dot (CSS `::after`) in top-right corner.

### README.md — complete rewrite

Accurate status table, silicon validation results, all three variant summaries with
real test counts, v2 gate function table, tile library with actual cell/depth figures,
portability table, repository structure, key concepts.

### docs/RUNNING.md — new

Full workflow guide: Composer → .icm → VM → FPGA. Covers workbench, Python API for
loading `.icm` into VM, `ProgramImage` named-range API, compile-from-source, 32-bit
compiler, `icm_loader.py` CLI, Python FPGA bridge API, full pipeline example (NOT gate),
variant selection guide, 6-stage bring-up sequence, requirements, file location table.

### Tier 4 — COMPLETE

All items checked off: OR lowering confirmed, GS_OUT_POSEDGE, compiler constant
injection, workbench two-input display.

### Final test count

Main repo: 2,329 passing / 6 failing (all pre-existing deprecated tests).

### Commits this session

- `768fb72` — Tier 2 complete + Tier 4 progress
- `e149596` — Session log 2026-05-09
- `b0d0add` — Tier 4 complete: constant injection + workbench
- `8b9349c` — Docs: README rewrite + RUNNING.md

---

## TODO — NEXT SESSION

- Tier 5: Standalone VM package (pip install imago-vm)
  - Single Python package, no FPGA needed
  - pip-installable, runs unicell_array_v2.py in software
  - Entry point for community feedback

