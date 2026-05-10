# Imago UniCell — Session Start Prompt

## Repo

https://github.com/alh-Imago/Imago-Unicell.git
PAT: provided by Alan at session start (single-use per session)

## Working directories

- `/home/claude/Imago-Unicell/` — main repo

## Session assistant rules

1. Pull the repo first. Set remote URL with PAT.
2. Read `sessions/latest.md` — it is the memory.
3. Run full test suite before starting: `for f in test_*.py; do python3 "$f"; done`
4. Run full test suite after any change — never leave regressions.
5. Push to GitHub at end of session.
6. Update `sessions/latest.md` and `sessions/YYYY-MM-DD.md` at end of session.
7. Update `MIGRATION_TODO.md` — check off completed items.

---

## Current state (2026-05-10)

- **2,329 tests passing** / 6 failing (all pre-existing deprecated)
- **Tiers 1–5**: ✅ Complete
- **Tier 6** (docs): ✅ Substantially complete
- **Latest commit**: 61dd909

---

## TODAY'S PRIORITY — Composer PORT blocks + compiler output names

### 1. Composer: PORT block type

Current problem: Composer-generated .icm files have no named inputs/outputs.
`addrIn: "0x1000"` is a hex address, not a name. The workspace falls back to
topology inference giving ugly names like `in_0`.

Fix: a PORT block type in the Composer.

**PORT INPUT block:**
- User drops it on canvas, types name `a`, sets address `0x1000`
- Renders as a coloured port marker (not a cell box)
- Doesn't emit a CellMapRecord
- On export → `"inputs": {"a": 4096}` in .icm

**PORT OUTPUT block:**
- Same but direction output
- On export → `"outputs": {"result": 8192}` in .icm

**Implementation plan:**
- Add PORT_INPUT / PORT_OUTPUT to MODELS or as a new block category
- `makeBlock()`: add port_name, port_dir fields
- Inspector: show name input + direction selector (not gate_state fields)
- `exportICM()`: collect PORT blocks → build inputs/outputs before records
- `importICM()`: reconstruct PORT blocks from inputs/outputs on load
- Canvas rendering: draw as a small arrow/triangle marker, not a cell box
- Statusbar: port count in addition to cell count

### 2. Compiler: proper output names

`compile_function()` output addresses are currently named `out_0`, `out_1`.
Should use the function's return variable name:
  `return result` → `{"result": addr}`
  `return a + b` → `{"output": addr}` (anonymous expression)

Check the IR graph — the return node may already carry the variable name.

### 3. MUX compiler bug (low priority, look at if time)

`def mux(sel, a, b): return a if sel else b` always returns 0.
The conditional path in the compiler doesn't correctly lower single-variable
`if` branches to the cell level.

---

## Architecture reminder

- **Cell**: 32-bit gate_state, 12 logic functions, 1 cell = 1 cycle
- **Wired-OR bus**: two cells writing same address → OR, no arbitration
- **WORKSPACE pond**: user's desk — named values, session fs, programming space
- **PTT**: OS-level view of the system (pond names, Ward health, I/O ports)
- **.icm**: portable JSON program format — runs on VM and FPGA unchanged
- **imago_log**: `imago_log.set_level(SILENT)` or `imago.set_verbose(False)`
- **imago package**: `pip install imago-vm`, `VM()`, `run_icm()`, `compile_function()`

The repo IS the memory. Pull it, read it, trust it.
