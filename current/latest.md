# Current State (as of 2026-08-16, mid-session update -- see `points.md` #325-337 for the full numbered ledger; the "session close" framing below is stale until this session actually closes and archives)

## MID-SESSION UPDATE (`#336`-`#341`, same day, after the housekeeping described below)

Real progress on `#324`'s own stated next phase, not just more
housekeeping: **ICM v3 format built** (`#336`), **VM dispatch built**
(`#337`), **the tile library's Tier 0 built** (`#338`), **target tagging
added** (`#339`), **Tier 1 started with the sentinel** (`#340`, Alan's
own explicit choice: "start with the sentinel first that's one model we
know" -- verified by replaying the exact proven feed/collect/unfreeze
sequence from real Quartus-fitted hardware), and **Tier 1 generalized**
(`#341`, a second composed tile -- `dual_threshold_monitor`, one
accumulator fanning out to two independent comparator->latch chains in
an L-shaped, non-linear layout -- required a real, backward-compatible
generalization of Tier 0's own port-resolution mechanism to support
fan-out at all). 16/16, 19/19, 22/22, and 11/11 tests passing
respectively, zero regression on the pre-existing nano suite. The
compiler itself is next, now that Tier 1 has two real proof points (a
straight chain and a branching layout) -- see `current/START.md`'s own
NEXT list, kept in sync.

## Read this first (yesterday's/earlier-today's housekeeping, still accurate)

**Yesterday's milestone still stands** (`#324`): the super carrier
shell is real, all 6 cores individually selectable in one cell,
measured cheap (25.9 ALM for the selection mechanism itself). Today
was mostly consolidation and housekeeping ahead of the real VM/ICM/
compiler/PCIe/AI-system work -- no new RTL, but real, valuable ground
-clearing.

## What's real and new today

**A full audit of all 330 prior `points.md` entries done** (`#331`,
full detail in `docs/shared/POINTS_STATUS_AUDIT.md`). Honest finding:
the ledger is in genuinely good shape, nothing found that contradicts
current architecture. Three real connections surfaced that had
drifted disconnected -- most notably, the Tang Nano 20K had already
been adopted back at `#230` (2026-08-08) with a confirmed working
open-source toolchain, before today's own `#326` treated the idea as
fresh. Owned directly.

**A full structural audit of the repo done** (`#332`, full detail in
`docs/shared/STRUCTURE_AUDIT.md`), followed by a real first
reorganization pass** (`#333`): `pcie/` (entirely dead), two different
files both named `fpga_bridge.py` (neither current), a duplicate
`PAPERS.md`, and two abandoned backup files -- 32 files removed from
the live tree, archived via the Onion tool into `archeology/onion/`,
every single one checksum-verified byte-for-byte identical before any
live original was deleted. A real basename-collision bug was found
and fixed DURING this process (two same-named files silently
overwrite on extraction unless staged into distinguishing subpaths)
-- caught specifically because verification-before-deletion was
insisted on, not skipped.

**That same bug then fixed properly at its source**, in the Onion
tool's own code (`#334`-`#335`) -- the metadata auto-split delimiter
changed from comma to semicolon, tested both directions, pushed
genuinely upstream to `github.com/alh-Imago/Onion` with Alan's own
credentials. The Onion submodule init + build steps are now baked
permanently into `current/START.md`'s own session-start ritual.

**Two real, honest gaps confirmed against RTL/Quartus directly, not
assumed:** the on-board DDR4 has never been touched by any real build
in this project's history -- only the internal M20K (`#329`). And
PCIe throughput is confirmed to be a host-motherboard property, not a
card property -- which is precisely why a Dell Precision 5820 was
already the identified target for a dedicated second machine, a
decision that (like `#230` above) had never actually been logged
until today (`#330`, the fourth instance this session of the same
unlogged-conversation gap pattern).

**A new, real testbed track opened:** Sipeed Tang Nano 20K boards
(Gowin GW2AR-18, a genuinely different FPGA vendor), proposed as a
cheap, chained stack -- opening a real, never-tested question: does
"topology is computation" hold across FPGA vendors, not just Intel
devices (`#326`-`#328`). A real correction made and owned twice over:
the onboard BL616's WiFi/BLE capability was wrongly assumed usable on
this specific board; Sipeed's own docs never mention it.

## What's real but NOT yet resolved -- the honest open items

1. **The VM/ICM v3/compiler/PCIe/AI-system work itself** -- still the
   real next phase per `#324`'s own milestone. Nothing started yet;
   today was groundwork (audit, cleanup) ahead of it, per Alan's own
   explicit request to be clean and structured before it begins.
2. **The 77-file root Python sprawl** -- deliberately NOT archived yet,
   held until the real VM/`core/` rebuild actually starts, so archival
   happens as a genuine replacement rather than speculative deletion.
3. **`hardware/Arria10_Programming_Procedure.md`** -- needs Alan's own
   judgment call (archive vs. refresh), not mechanical action.
4. **The `mathtrix` root-vs-`community/` structural question** -- a
   real design decision for when the Trix domain-model rebuild is
   actually in scope, not a cleanup.
5. **The super carrier shell's own remaining gaps** (carried forward
   from `#324`): `latch_in`/`latch_A_dis` completely absent from every
   core; the register-count discrepancy in `#323`'s own entity report
   unresolved; a real host/JTAG-wrapped version of the super cell not
   yet built.
6. **The RAM-side address-arbitration/retry-loop mechanism** (`#301`/
   `#302`) -- real direction, still needs testing before trust.
7. **`sentinel_counter_v1.v`/`v2.v` still not wired into any real
   chain**; **`shared_bram_arbiter_v1.v` still not wired into the full
   tree system** -- both carried forward unchanged.
8. **The two long-queued Quartus diagnostic experiments** (duplication
   flags, aggressive optimization mode) -- still not started.

## Also queued, not yet started (carried forward)

The `#210` programming-delivery decision. The BRAM+DSP hybrid
integration (`#220`). The longer-horizon FPGA dev-tool vision
(`#305`). The two small genuinely-orphaned items from `#331`'s audit
(`#10`, `#45`) -- flagged for a conscious keep/drop decision whenever
convenient, not urgent.

## Next session

Per Alan's own explicit framing at end of day: the ledger and the
repo structure are both now in good, honestly-assessed shape ahead of
"a critical new phase." The real next step is the VM/ICM v3/compiler/
PCIe/AI-system work itself -- `#324`'s own milestone made it well-
scoped, and today's work made the ground it starts on genuinely clean.
