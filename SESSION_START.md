# Imago UniCell — Session Start Prompt

## Repo

https://github.com/alh-Imago/Imago-Unicell.git
PAT: provided by Alan at session start (single-use per session)

## Working directory

`/home/claude/Imago-Unicell/`

## Session rules

1. Pull repo first. Set remote URL with PAT.
2. Read `sessions/latest.md` — it is the memory.
3. Run full test suite before starting: `for f in test_*.py; do python3 "$f"; done`
4. Run full test suite after any change.
5. Push to GitHub at end of session.
6. Update `sessions/latest.md` and `sessions/YYYY-MM-DD.md` at end.
7. Update `MIGRATION_TODO.md` — check off completed items.

---

## Current state (2026-05-10 end of day)

- **2,329 tests passing** / 6 failing (all pre-existing deprecated)
- **Tiers 1–5**: ✅ Complete
- **Tier 6**: Docs remaining — next session
- **Latest commit**: 526e924

---

## TODAY'S PRIORITY — Docs + repo tidy

### Docs (Alan writing — session assistant supports)

Writing tasks, no code changes unless docs reveal something broken:

- `docs/VM_GETTING_STARTED.md` — for new users: install, run first example,
  compile first function, use workbench. Should take < 5 minutes to follow.

- `docs/ICM_FORMAT.md` — .icm format specification:
  program_id, name, inputs, outputs, input_shapes (reserved), models,
  ranges, records (gs/in/out/inB/alt/stor/init), record_hash, composer_meta.
  One authoritative reference — link from README and RUNNING.md.

- `docs/ARCHITECTURE.md` — the full architecture document:
  Cell model, wired-OR bus, gate_state bits, IR → CellMapRecord,
  Pond/Bridge/Ward/Shore/COMPANION, PTT, WORKSPACE pond,
  portability story (.icm on VM → FPGA → ASIC).

- `docs/NEURAL_POND_TUTORIAL.md` — step-by-step tutorial using
  docs/neural_pond_design.md (already written) as the design reference.
  Include a working LIF .icm example.

- Update `docs/RUNNING.md` for port declarations (scan, prompt, Composer tab).

### Repo tidy

- `.gitignore`: add `imago_vm.egg-info/`, `__pycache__/`, `*.pyc`, `.DS_Store`
- `fp_tiles_old.py`: confirm dead (nothing imports it) → delete
- `shore_v2_old.py`: confirm dead → delete
- `main.py`: review — superseded by `imago/cli.py`? Keep or remove?
- `composer/unicell_composer_v2.html`: keep as backup or remove?
- Orphaned test files: check if any test_ files import deleted modules

---

## Architecture quick reference

- **Cell**: 32-bit gate_state, 12 logic functions, 1 cell = 1 cycle
- **Wired-OR bus**: two cells writing same address → OR, no arbitration
- **WORKSPACE pond**: user's desk — named values, fs, programming space
- **PTT**: OS-level view (pond names, Ward health, I/O ports)
- **.icm**: `{name, inputs, outputs, models, records}` — portable JSON
- **Port names**: user confirms before compile; become PTT entries
- **imago_log**: `imago.set_verbose(False)` or `IMAGO_VERBOSE=0`
- **imago package**: `pip install imago-vm`, `VM()`, `run_icm()`, CLI

The repo IS the memory. Pull it, read it, trust it.
