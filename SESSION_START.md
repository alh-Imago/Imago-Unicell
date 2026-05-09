# Imago UniCell — Session Start Prompt

Use this file to brief the session assistant at the start of each working session.

---

## Repo

https://github.com/alh-Imago/Imago-Unicell.git
PAT: provided by Alan at session start (single-use per session)

## Working directories

- `/home/claude/Imago-Unicell/` — main repo (standard variant, root of all work)
- `/home/claude/imago_v2/` — clean v2 foundation (reference only)

## Session assistant rules

1. **Pull the repo first.** Set remote URL with PAT, pull to `/home/claude/Imago-Unicell/`.
2. **Read `sessions/latest.md`** — it is the memory of where we left off.
3. **Run the full test suite before starting** — `for f in test_*.py; do python3 "$f"; done`
4. **Run the full test suite after any change** — never leave regressions.
5. **Push to GitHub at end of session** — the repo is the memory.
6. **Update `sessions/latest.md` and `sessions/YYYY-MM-DD.md`** at end of session.
7. **Update `MIGRATION_TODO.md`** — check off completed items, add new ones.

---

## Current state (as of 2026-05-09)

- **2,329 tests passing** (main/standard variant), 6 failing (all pre-existing deprecated)
- **Tier 1** (v1 retirement): ✅ Complete
- **Tier 2** (OS layer v2 migration): ✅ Complete
- **Tier 3** (ECC, Ward-in-silicon, Shore-in-silicon): Deferred to hardware
- **Tier 4** (architecture refinements): ✅ Complete
- **Tier 5** (standalone VM package): 🔜 **TODAY'S WORK**
- **Tier 6** (docs): ✅ Substantially complete (README + docs/RUNNING.md done)

Latest commit: `8eb71b7` — Composer: FPGA target selector, cell budget, vmOnly

---

## TODAY'S PRIORITY — Tier 5: Standalone VM Package

### Goal

```bash
pip install imago-vm
imago-workbench          # opens browser UI at http://localhost:7420
imago run my_design.icm  # runs a .icm program, prints output
imago compile "def f..."  # compiles source, prints cell map summary
```

Anyone with Python 3.10+, no hardware, no repo clone needed.

### Scope

1. **`pyproject.toml`** — package metadata, version, dependencies, entry points
2. **Package structure** — decide what goes in `imago/` namespace (core VM files)
   vs what stays optional (FPGA bridge, llvmlite frontend)
3. **CLI entry points** — `imago-workbench`, `imago run`, `imago compile`
   Small wrapper script, minimal surface area
4. **Bundled examples** — a handful of clean `.icm` files in `imago/examples/`
   (NOT gate, AND gate, 32-bit adder, for loop) that users can run immediately
5. **`pip install -e .` test** — verify it installs and entry points work
6. **Update `docs/RUNNING.md`** — add `pip install imago-vm` at the top

### Out of scope for v1

- numpy performance mode (after user feedback)
- VM vs silicon diff tool (needs hardware)
- PyPI upload (manual step once clean — Alan does this)

### Key files to understand before starting

- `unicell.py`, `unicell_array.py` — the VM itself
- `controller.py` — ImagoController (run/load/halt)
- `compiler.py`, `compiler_int32.py` — compilation
- `workbench.py` — the browser UI (runs its own HTTP server)
- `run_companion.py` — OS session entry point
- `program_image.py` — ProgramImage, from_dict/to_dict

### What NOT to change

- The VM itself — it is correct and tested
- The test suite — do not break 2,329 passing tests
- The compiler — it works
- Any variant directory (unicell-latch/, unicell-edge/) — leave those alone

---

## Hardware tracking

| Item | ETA | Status |
|------|-----|--------|
| Kintex-7 XC7K480T | 2 Jun – 6 Jul 2026 | IN TRANSIT |
| JTAG SMT2 programmer | By 21 May 2026 | IN TRANSIT |
| Vivado ML Standard | — | Downloading |

---

## Architecture reminder (for context)

- **Cell**: 32-bit gate_state config word, 12 logic functions, 1 cell = 1 cycle
- **Wired-OR bus**: two cells writing same address → OR of values, no arbitration
- **Pond**: isolated compute environment (address space + bridges + Ward)
- **Shore**: name→address registry
- **COMPANION**: permanent OS anchor
- **.icm**: JSON portable program format, runs on VM and FPGA unchanged
- **Variants**: root=standard (dev/sim), unicell-latch/ (large FPGA), unicell-edge/ (iCEBreaker)

The repo IS the memory. Pull it, read it, trust it.
