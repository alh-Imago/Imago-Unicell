# Session Log — 2026-06-11 (MIF/FP32 comparison, hybrid hard-IP architecture)

## Final commit: 6bd0d06
## Suites: 157/157 compiler_int32, 236/236 fp_tiles, 31/31 silicon (unchanged)
## Previous session archived: sessions/archive-2026-06-09.md

---

## Nature of this session
Mostly design + records, no production code changes. Caught up the session
log and PLAN (they had drifted behind the licence/Region-Connector commits),
worked out the FP32-vs-MIF comparison, and designed the hybrid hard-IP
architecture for the 8-card rig in full. All design work parked behind the
single-card Arria 10 milestone.

---

## Records caught up
- sessions/latest.md was stale at e7db74c (pre-format-system). Rewritten to
  cover the whole 2026-06-09 run, previous archived. (done start of session)
- PLAN.md was stale at 5f0ae0f -- described that commit's own fixes as still
  open, and 3 commits had landed after. Brought current (commit c86bd74):
  test counts 140->157, command_interface naming done, open-items list moved
  to "completed this session", release checklist updated (both licences done,
  remaining gate = Arria 10 + verbatim CERN-OHL-P text), refined Arria 10
  diagnosis + staged card plan added to hardware status.

## FP32 vs MIF comparison (presented in chat, not yet a doc)
No dedicated side-by-side table exists in repo. Numbers pulled together:
  FP32_ADD: 1,253c / depth 85  vs  MIF_ADD: 814c / depth 79
    -> MIF ~35% fewer cells, ~7% shallower. Core MIF claim made concrete.
  Boundary cost (once per grid point): MIF_UNPACK 74c/25, MIF_PACK 126c/4.
  MIF wins hardest on ctrl-only ops: NEG 1c, ABS 0c, CMP_LT 212c, CMP_EQ 98c.
  MIF-only (no IEEE tile): SUB 810, MUL 3066, MADD 3875, DIV 4789, SQRT 5317.
TODO next session: build a proper FP32-vs-MIF doc; put FP32_ADD and MIF_ADD on
adjacent rows in PAPER_DRAFT table (currently separated by MIF_MUL, buries it).

## MIF_ADD via packed shift adder (PLAN item added)
Apply packed shift-chain adder to stage 4 (24-bit mantissa add) + shift-chain
CLZ to stage 5 (normalise). Est 814c -> ~450-550c (30-40%). NOT bigger because
stage 3 alignment barrels (~480c) are ALREADY shift-optimised. Depth trade
~79 -> ~90-95 (fine for stencils). Structure-level estimate, must measure.
Pairs with shift_in_en validation. packed_shift_adder.py already exists.

---

## HYBRID HARD-IP ARCHITECTURE (major design, 8-card rig, all deferred)

The big design thread of the session. Captured fully in PLAN.

Three-layer silicon story:
  iCEBreaker/proving = pure soft fabric (ground truth)
  Arria 10 rack/deployment = HYBRID (use idle DSP blocks)
  Custom UniCell ASIC = pure fabric again (the chip IS the architecture)

KEY SCOPING: hybrid is FPGA-ONLY. FPGAs ship hardened DSP blocks on the die --
unused = idle paid-for silicon, so hybrid reclaims them. On ASIC there are no
hard blocks; soft models run natively at full density. Hybrid never touches
the reference architecture -- platform accommodation, discarded on ASIC.

Why it doesn't break "topology is computation": a DSP block is just a very
fast arithmetic cell with a boundary. Same pattern as MIF_PACK/UNPACK or
preloaded-A constants. Fabric still owns structure.

### Implementation design (all in PLAN, all deferred)
- DUAL-ENCODED ICM: carries both soft model AND DSP version. One artifact runs
  anywhere. Hash verifies (both declared). Doubles as overflow safety valve.
- DSP RESOURCE TABLE in Shore: finite, hardened, fixed-location blocks.
  Entry = {address, op_class, latency_ticks, in_use_by_pond}. Same allocation
  discipline as cell ranges -- exclusive per pond, parallelism preserved.
- ALLOCATION = MAX-NOT-SUM. DSP slice is general arithmetic (add/mul/MAC), so
  blocks are FUNGIBLE. Allocator needs ONE number: max(step.model_count) over
  the program table. No summing, no per-type tracking.
- PEAK CONCURRENCY ALREADY SOLVED by the program table -- it's compile-time
  resolved and inherently step-sequential, so each step already declares its
  active model count. Read it off, don't infer it. (Corrected an earlier
  overstatement that called this the hard problem -- it isn't, for the table
  model. The linear table-driven programs ARE exactly the hybrid's target.)
- Nested loops handled: compiler expands at table-build time, concurrent step
  shows higher count, max-scan catches it. Only dynamic runtime instantiation
  would break it -- table model doesn't do that. Structural guarantee.
- DSP IS STATEFUL (internal pipeline regs, N-clock latency). Bridge cell not
  transparent -- placer adds latency to depth budget. Two-arrival handles the
  wait naturally. Hence latency_ticks in table.
- FORMAT TYPING across DSP boundary: declared adapter, MIF in / MIF pair out,
  same discipline as every bridge tile.

### What the hybrid layer actually needs (difficulty order)
  1. Target profile flag (pure|hybrid) -- trivial
  2. Max-scan allocator -- nearly free, prototypable in software now
  3. Shore DSP table -- small, mirrors cell-range allocation
  4. DEVICE-SPECIFIC GATEWARE -- the real new work. DSP primitives are
     vendor/device-specific (Arria 10 != Kintex-7 != iCE40). Current gateware
     is fabric-generic. GATED on a working Arria 10.
  5. RESOURCE MANIFEST -- static (synth emits manifest, Shore loads at
     bring-up; declared-not-discovered, fits the architecture) PREFERRED over
     runtime register-block enumeration.

Scale check: GX660 has ~1,600+ DSP blocks. 1000 simultaneous in one pond is
implausible (cell budget exhausts first). Not a single-card bottleneck.

Dependency: everything except allocator logic waits on Arria 10 -- device
gateware is the foundation. Allocator could be prototyped now against a fake
table, low value until real gateware declares real blocks.

---

## Hardware status (unchanged -- gated)
Arria 10 GX660: likely recoverable. <60W draw (550W bench PSU huge headroom),
slot power optional (6-pin alone runs it), zero-display = card-ID not fault,
two green LEDs + ID = board alive. Likely fault: flaky FTDI or bad flash
bitstream, both JTAG-recoverable.
Shopping (paid 26th): Waveshare USB Blaster V2 £32 + JST SH 1.0mm £14.
FIRST TEST ON CABLE ARRIVAL: jtagconfig -> read IDCODE on the 660.
Staged plan: 660 = proving card -> son's once enumerates in Linux.
1150 ~£100 early = clean performance card + rig seed. 8-card rig long-term.

## Everything still routes to one move
Cable -> IDCODE read -> single card stable -> pure-fabric validation (ground
truth) -> THEN hybrid as deployment layer. The whole hybrid design above is
gated on that first IDCODE read coming back clean.

---

## Recurring pattern worth noting
Third+ time this session that an old design decision became the mechanism for
a new problem:
  - program table (built for DDR config-streaming) already carries the DSP
    peak-concurrency count -- no liveness analysis needed
  - MIF_PACK/UNPACK boundary pattern is exactly the DSP handoff pattern
  - preloaded-A / table-driven discipline gives the static resource manifest
    its shape (declared not discovered)
"Emergent properties are a feature" -- independently motivated decisions
converging because they're expressions of the same underlying discipline.
