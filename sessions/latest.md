# Current State (as of 2026-07-31 — see sessions/archive-2026-07-31.md for the full narrative)

Previous narrative (2026-07-30 through 2026-07-31, plus everything that had
accumulated unarchived before that — PCIe bring-up, the earlier cell-internals
work, etc.) has been moved to `sessions/archive-2026-07-31.md`, most-recent-
first, exactly as it was written. This file starts fresh as the fast
catch-up document, per its own stated purpose.

## Where things stand

**Both cell-internals steps of the definitive task path are CLOSED and
silicon-proven, cleanly, with no outstanding hazard:**
- #42/#58 — per-edge `cardinal_edge`: a cell can be cardinal-only on one
  active direction while staying local on another, same fire.
- #49/#51/#59 — comparator + dynamic routing latch: one static config, three
  different injected values took three genuinely different routes, matching
  the exact silicon-confirmed result.

Along the way: a real top-level address-lane whitelist bug was root-caused
and fixed (#61); an earlier "back-to-back rearm hazard" finding was corrected
— it was a measurement artifact in sticky ISSP readback latches, not a real
cell bug (#64); targeted `CMD_SET_ROUTE_LATCH_AT`/`CMD_FREEZE_AT`/
`CMD_RELEASE_AT` were built and silicon-tested (#62/#65); the in-fabric
loader confirm mechanism was built (`CMD_LOAD_DONE` now fires on the data
bus too, #63); and a real broadcast-emission hazard was closed by making
command-emit genuinely targeted at the array level (#66).

**The VM has been fully rebuilt to match the current RTL exactly (#67),**
replacing the retired pre-v3.1 model for new work: `unicell_v3.py` (cell:
topology/methodology/routing latches, comparator, targeted opcodes,
command-emit) + `unicell_array_v3.py` (array: wired-OR combine, emit
arbiter, targeted-emission delivery). 216 tests, every one traced to a
specific cited RTL line, several direct replays of exact silicon-proven
scenarios (#59, #63, #65/#66). Capped with a working four-role
SENDER/TARGET/WATCHER loader that passed clean on the first run.

**`loader_fsm_v3.v` (the existing, proven boot-time icmP loader) is now
also modeled faithfully in the VM (#68)** — `loader_fsm_v3.py`, a direct
replay of `tb_bram_loader_v3.v`'s exact 3-cell scenario, 24 more tests
(240 VM tests total). This is the foundation for the RAM-read runtime
mechanism, per Alan's explicit direction: extend the real, proven FSM
itself, not a new cell-based mechanism.

**Documentation pass:** the pre-v3.1 VM files (`unicell.py`/
`unicell_array.py`/`command_interface.py`) are still the ACTIVE
implementation behind `controller.py`/`compiler.py`/`workbench.py`/
`pond.py` and 30+ existing tests — NOT yet migrated, NOT archived (would
break all of that). Each now carries a clear legacy note in its own
docstring pointing at the current replacement; `docs/INDEX.md`'s
Repository Map is corrected and split into legacy/current sections.

## Next up

**The open design question, deliberately not rushed into #68's pass:**
the RAM-read runtime extension itself — re-triggering `loader_fsm_v3.v`
(currently runs once to `S_DONE` and stops), sourcing its config table
from a live BRAM read port instead of a fixed array, and critically:
`CMD_LOAD_DONE`'s completion signal is specific to the config-load
protocol — a runtime `SET_TARGET`+`CMD_DATA_WRITE` (plain data injection)
step has no automatic confirm built into the opcode itself. Needs its
own dedicated design conversation (does the receiving cell need to be
command-emit-capable to produce an analogous confirm, is a bounded
settle delay acceptable instead, or something else) before building.

Full detail on everything above: `points.md` #58 through #68, and
`PLAN.md`'s definitive task path section.
