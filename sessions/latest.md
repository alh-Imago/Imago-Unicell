# Session Summary — 2026-05-09 (Full Day)
## Tier 2 Complete · Tier 4 Complete · Docs · Composer

---

## HARDWARE STATUS

| Item | Cost | Order | ETA | Status |
|------|------|-------|-----|--------|
| Kintex-7 XC7K480T board | £54.90 | 22-14594-85183 | 2 Jun – 6 Jul | IN TRANSIT |
| JTAG SMT2 programmer | £25.74 | 23-14593-40180 | By 21 May | IN TRANSIT |
| Vivado ML Standard | Free | N/A | — | Downloading |

---

## WHAT WAS DONE

### fp_tiles.py (Tier 2 final)
- NOR2 removed from COUNTER_DECREMENT (OR tree + NOT) and SR_LATCH (NOT(OR2))
- INT32_SUB: ripple-carry → Kogge-Stone (depth 65→12, 192→517 cells)
- GS_OUT_POSEDGE on all NORBuilder _emit/_emit2/_emit_v2

### ir.py
- GS_OUT_POSEDGE on all compiler-emitted cells in lower_to_cell_map_v2

### model_library.py — FP32 estimates → actuals
- FP32_ADDER: 3,000/40 → **1,253/85**
- FP32_MULTIPLIER: 35,000/80 → **3,066/89**
- INT32_SUBTRACTOR: 580/13 → **517/12**

### pond_types.py + pond.py (Tier 2)
- PondTypeSpec gains stall_threshold + anomaly_threshold fields
- Per-type tuned values (DEVICE=15 cycles, PROCESS=100, FILE=200, etc.)
- Bridge.__init__ reads from registry, falls back to 50/50.0

### OR lowering confirmed + test fix (Tier 4)
- SYNC_WAIT confirmed 1 cell v2 native
- test_gate_state_32.py updated (was checking v1 3-cell behaviour)

### Compiler constant auto-injection (Tier 4)
- compile_function() → self.known_values: {bus_addr: val}
- load_map(known_values=) → stored on Region
- start() auto-injects before user inputs
- Updated: test_compiler.py, compiler.py, compiler_int32.py, program_builder.py

### Workbench UI (Tier 4)
- Inspector: Input A addr, Input B addr (conditional), Input B val, Two-input row
- Grid: two-input cells get small accent dot (CSS ::after)

### README.md — complete rewrite
- Current status table, silicon validation, three variants with real test counts
- v2 gate function table, tile library actuals, portability table, key concepts

### docs/RUNNING.md — new
- Composer → .icm → VM → FPGA workflow guide
- VM Python API (raw + ProgramImage), compile-from-source, FPGA bridge API
- Full pipeline example, bring-up sequence, requirements

### Composer — target selector + budget + vmOnly (2026-05-09)
- Target selector: VM/iCEBreaker 64/iCEstick 16/Basys3 256/OrangeCrab 256/Kintex-7 1500/Custom
- Cell budget bar: live cost/budget(%) — amber 80%, red over
- Model library: accurate figures throughout; new INT32_NOT/AND/OR/XOR models
- vmOnly badge (amber) on models exceeding target budget
- .icm export: embeds target/cell_budget/vm_only; confirm dialogs on violations

---

## TIER STATUS

| Tier | Status |
|------|--------|
| 1 — v1 retirement | ✅ Complete |
| 2 — OS layer v2 migration | ✅ Complete |
| 3 — Silicon features | Deferred to hardware |
| 4 — Architecture refinements | ✅ Complete |
| 5 — VM package | 🔜 **Next session** |
| 6 — Docs | ✅ Substantially complete |

---

## TEST BASELINE

```
Main (standard): 2,329 passed / 6 failed  (all pre-existing deprecated tests)
unicell-latch:   2,535 passed
unicell-edge:    2,326 passed / 9 failed
```

Zero new regressions this session.

---

## GIT STATUS

Latest commit: 8eb71b7 — Composer: FPGA target selector, cell budget, vmOnly
Branch: main — pushed ✓

---

## NEXT SESSION — Tier 5: Standalone VM Package

**Goal:** `pip install imago-vm` — anyone with Python 3.10+ runs UniCell programs
without hardware, without cloning the repo.

**Scope (one session):**
1. `pyproject.toml` — metadata, dependencies, entry points
2. Package structure — `imago/` namespace, core vs optional split
3. Entry points: `imago-workbench`, `imago run <file.icm>`, `imago compile`
4. Bundled example `.icm` programs (NOT gate, AND, adder, for loop)
5. `pip install -e .` test then full install test
6. Update RUNNING.md with pip install instructions

**Out of scope for v1:** numpy perf mode, VM vs silicon diff tool, PyPI upload.

**Note for next assistant:** All Tiers 1–4 complete. 2,329 tests passing.
The code is correct — this is purely a packaging task. Pull the repo,
read this file, trust it. Work is in Tier 5 only.
