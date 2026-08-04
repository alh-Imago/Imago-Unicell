# docs/full-cell/

**UPDATE (2026-08-04, even later same session): the FULL cell's entire
active codebase has now moved into `archeology/full-cell/` too — not
just docs.** Per Alan: "everything relating to the old v3 full model
needs to be placed at this time into the archeology folder... rather
than stepping around legacy rubble." `unicell64_v3.v` and its whole
Verilog lineage (82 files: `unicell.v`/`unicell64.v` predecessors, the
zone/array/bridge/loader infrastructure, every `tb_v3_*`/`tb_zone64_*`
testbench, the old iCEBreaker/Arty/Kintex-7 board tops) now live in
`archeology/full-cell/verilog/`. The Python VM side (`unicell_v3.py`,
`unicell_array_v3.py`, `unicell_card_v3.py`, `hybrid_card_v1.py`,
`loader_fsm_v3.py`, `card_ram_loop.py`) is in `archeology/full-cell/
python/`, with its 5 test suites (263 tests total) in `archeology/
full-cell/tests/`. All still run correctly from their new location —
`PYTHONPATH=.:archeology/full-cell/python python3 archeology/full-cell/
tests/test_unicell_v3.py` (needs the repo root on the path too, since
`unicell_v3.py` depends on the shared `unicell_gate_core.py`, which
correctly stayed active rather than being duplicated into the archive).

The active tree (`fpga/verilog/`, repo root `.py` files) is now
genuinely, entirely nano/STRIPPED-cell-and-shared-infrastructure only —
no more FULL-cell material to step around while working on the active
line. Revisiting the FULL cell later means pulling the relevant pieces
back OUT of `archeology/full-cell/` deliberately, applying everything
learned on the STRIPPED line first (per Alan: "not just as an idea, but
make it work"), rather than resuming in place.

---

**UPDATE (2026-08-04, later same session): no longer empty.**
`CELL_INTERNALS.md` now exists — built by reading `unicell64_v3.v`
directly, following the same pattern as `docs/stripped-cell/
CELL_INTERNALS.md`. A real trap caught and flagged in the process: this
RTL file's own HEADER comment block is known stale (still shows
`auth_mask` at the wrong bit position) — the file's own later "verified
current" block is the one that's actually authoritative, and the new
doc was built from that, not the header.

---

Originally created empty (2026-08-04) to mirror `docs/shared/` and
`docs/stripped-cell/`, ready for whenever the FULL-cell-specific
documentation phase started. `archeology/full-cell/docs/` still holds
everything else moved-but-not-yet-re-examined for the FULL cell —
`V3_COMMAND_CONTRACT.md` remains a good next pull if this phase
continues, for the opcode-level detail `CELL_INTERNALS.md` deliberately
didn't try to be exhaustive about.

Per Alan (2026-08-04): the FULL cell is expected to be revisited and
made functional again, carrying back some of what was discovered on the
stripped cell (`docs/stripped-cell/CELL_INTERNALS.md`) — the routing
self-consistency approach from `points.md` #155 and the armed/`COMPLETE`-
LSB convention from #156 (itself modeled on this cell's own
`start_flag`/`CMD_RELEASE`, now documented explicitly in
`CELL_INTERNALS.md`) are the two candidates already flagged. That RTL
work and this documentation phase may need to happen together — worth
deciding when picked up, not assumed.

