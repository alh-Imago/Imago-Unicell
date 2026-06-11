# Imago UniCell — Active Plan
*Single source of truth for what needs doing and why.*
*Last updated: 2026-06-09 (post-licence, post-Region-Connector)*

---

## Hardware Status

| Hardware | Status |
|---|---|
| iCEBreaker iCE40UP5K | Silicon validated, 31/31 tests, 4-cell limit (UART bus) |
| Arria 10 GX660 (IEI Mustang-F100) | PCIe alive, FTDI USB faulty — likely recoverable |
| Waveshare USB Blaster V2 + JST cable | £46 — ordered, paid 26th |
| Quartus 25.1 | Installed and licensed on F:\Q |

**Arria 10 diagnosis (refined):** Card draws <60W (IEI spec) — 550W bench PSU is
huge headroom, power starvation unlikely. Slot power optional per IEI spec — card
runs on 6-pin alone, no powered riser needed for isolated test. Display showing
ZERO is the card-ID (DIP switch), not a fault code. Two green LEDs + ID display =
board alive, FPGA powered. Likely faults: flaky FTDI or bad flash bitstream —
both JTAG-recoverable. **First test on cable arrival: jtagconfig → read IDCODE on
the 660. Clean read = JTAG chain + FPGA core alive, card recoverable.**

**Staged card plan:** 660 = proving card (bring-up, shift_in_en, scale test).
Then ~£100 early for Arria 10 1150 = clean performance card + rig seed. Working
660 → son's (dials in remotely; his once it enumerates in Linux).

---

## Naming Conventions — Verilog is Ground Truth

Python names must reflect Verilog names exactly.

- `preload_sel` — cmd_bus field. Python: `PRELOAD_SEL_ZERO`, `PRELOAD_SEL_ONES`
- `shift_sel`   — cmd_bus field. Python: `SHIFT_SEL_IN_EN`, `SHIFT_SEL_OUT_EN`

**Done:** `command_interface.py` aligned to `PRELOAD_SEL_*` (commit 5f0ae0f).
Legacy aliases (`PRELOAD_NONE` etc.) retained for backward compatibility.

---

## Test Suites — Current State

| Suite | Count | Status |
|-------|-------|--------|
| tests/vm/test_compiler_int32.py | 157/157 | ✓ passing |
| tests/vm/test_fp_tiles.py | 236/236 | ✓ passing |
| tests/fpga/test_sanity.py | 31/31 | ✓ silicon validated |

---

## Open Items — Non-Hardware

All previously-listed non-hardware items are now DONE (commits 5f0ae0f, 7c48aae,
0c70987). Remaining non-hardware work is architectural, no urgency:

- [ ] Compiler auto-placement of bridge tiles (place bridge between regions
      automatically from a pipeline .icm)
- [ ] Design-time confidence-threshold warning enforcement in the compiler
      (Region Connector already warns at the UI; compiler does not yet)
- [ ] SI_CHECK dimensional analysis integration (verify bridge output_dimension
      matches target consume dimension at compile time)
- [ ] Bridge section in community contribution guide
- [ ] DisplayPond hosted flag (GPU framebuffer passthrough). mathtrix_animate.py
      already covers the mathematical output side; the cell-array fire visualiser
      is deferred to Arria 10 scale.
- [ ] BioTrix / ChemTrix / PhysTrix community models (format defs exist;
      worked example models would help contributors)

### Completed this session (was the old "open items" list)
- [x] MUL preloaded_a normalisation — bits expanded to full 32-bit words
- [x] Multi-param re-injection — all params to both a_vals and b_vals
- [x] Multi-param ordering test (7) + load/run API test (10) → 157/157
- [x] command_interface.py naming → PRELOAD_SEL_* (legacy aliases kept)
- [x] docs/RUNNING.md + ICM_FORMAT.md — inB references removed
- [x] README animated GIF (Gray-Scott) + paper wavefront figure
- [x] Region Connector: pipeline validation, custom bridges, tooltips, shortcuts
- [x] Dual licence: MIT (software) + CERN-OHL-P v2 (hardware)

## Hardware-Gated Items (waiting for Waveshare + JST cable)

- [ ] Arria 10 first bitstream (Quartus, uart_bridge.v)
- [ ] shift_in_en silicon validation (cannot test on iCEBreaker 16-bit bus)
- [ ] Scale test — actual cell count on GX660
- [ ] Paper Section 4 update with Arria 10 results
- [ ] Packed adder tile (make_int32_add_packed) — needs shift bits confirmed
- [ ] MUL rewrite using packed adder — ~650 cells vs current
- [ ] Fabric fire visualiser — cell-by-cell animation (needs scale)
- [ ] SYNC_WAIT hardware test in tests/fpga/

---

## Compiler Optimisations (blocked on Arria 10)

These depend on shift_in_en / shift_out_en being confirmed on Arria 10.
Do not build workarounds — wait for hardware.

- [ ] Packed adder tile — 19 cells vs 482, needs shift bits
- [ ] MUL rewrite using packed adder — ~650 cells vs 2915
- [ ] Wallace tree MUL — ~500 cells, depth ~20
- [ ] x > CONST / x < CONST general case improvement
- [ ] MIF_ADD via packed shift adder — apply packed shift-chain adder to
      stage 4 (24-bit mantissa add) + shift-chain CLZ to stage 5 (normalise).
      Est. 814c -> ~450-550c (30-40% reduction). NOT bigger because the
      dominant cost (stage 3 alignment barrels, ~480c) is already
      shift-optimised. Trade: depth ~79 -> ~90-95 (acceptable for stencils,
      amortised across region). Reason from structure only -- must measure on
      real build. Pairs with shift_in_en validation (same shift ops the
      iCEBreaker cannot fully exercise).

---

## Hybrid Hard-IP Architecture (8-card rig -- future design note)

The Arria 10 GX660/1150 contain hardened DSP/ALU blocks (variable-precision
DSP, native fixed/float multiply-accumulate) alongside the soft fabric.
Current model uses ONLY the soft fabric -- every operation built from NOR
cells. Correct for proving the architecture and grounding truth: all models
and tile functionality validated on pure fabric first.

For LARGE FAST DEPLOYMENT (rack of cards), a hybrid is worth exploring:
offload heavy regular arithmetic (MUL/MADD/DIV -- the cell-expensive tiles)
to hardened DSP blocks, freeing soft-fabric cells for the topology/routing/
control logic that is the architecture's actual contribution. DSP does the
multiply; fabric does what only the fabric can do.

Open questions (do NOT resolve until single-card Arria 10 is stable):
- DSP result re-entry: boundary tile like MIF_PACK/UNPACK -- a HARD_MUL
  boundary hands off to DSP and receives result back into a cell.
- Purity: does this break "topology is computation"? No -- same pattern as
  preloaded-A constants or MIF boundary conversion. Fabric still owns
  structure; DSP is just a very fast arithmetic cell.
- Format typing across the boundary: a DSP MAC consuming MIF pairs needs the
  same contract discipline as any other tile.
- Per-card resource split: how many cells vs DSP blocks, and does the
  compiler choose soft-vs-hard per tile from a target-profile budget flag.

Principle to preserve: pure-fabric path stays the reference (ground truth).
Hybrid is an OPTIMISATION layer for deployment scale, never the foundation.
A tile should be expressible both ways, compiler selecting by target profile
(proving = soft, deployment = hybrid).

CRITICAL SCOPE: hybrid is FPGA-ONLY. FPGAs ship with hardened DSP blocks
already on the die -- declining to use them leaves paid-for silicon idle, so
the hybrid reclaims what is already there. On custom UniCell ASIC the whole
consideration disappears: the silicon IS the fabric, there are no hard blocks
to defer to, and the normal soft models run natively at full density. The
hybrid is a platform accommodation for living on someone else's FPGA silicon,
discarded entirely once on purpose-built silicon. It never touches the
reference architecture. FPGA = hybrid (use the idle DSP). ASIC = pure fabric
(the chip is the architecture).

### Hybrid implementation design (FPGA deployment profile)

DUAL-ENCODED ICM. The .icm carries BOTH representations of each offloadable
operation: the soft maths model (NOR-cell tiles) AND the DSP-offload version.
One artifact runs anywhere. Pure system -> loader uses soft models. Hybrid
FPGA -> loader uses DSP path. Hash still verifies because both are declared
in the file -- nothing invented at load time. The dual encoding is also the
overflow safety valve (see below), not just cross-platform portability.

DSP RESOURCE TABLE (lives in Shore). DSP blocks are finite, hardened, at
fixed die locations -- cannot be discovered or relocated at runtime.
Populated once per card at bring-up from the card device profile. Each entry:
  { dsp_address, operation_class, latency_ticks, in_use_by_pond }
Shore owns it because Shore is already the OS-level pond allocator.

ALLOCATION FLOW (placer):
  1. Loader reads .icm, finds peak concurrent DSP demand (see liveness below).
  2. Placer requests N free blocks from Shore's DSP table.
  3. Shore returns N specific addresses, marks them in-use by this pond.
  4. Placer wires those N DSP addresses into the pond, replacing N soft
     MIF_MUL/MADD/DIV tiles with DSP bridge cells.
  5. Next pond to load cannot grab those blocks -- gets next free. Exclusive
     per-pond allocation, same discipline as cell address ranges. Parallelism
     preserved, no contention.

PEAK CONCURRENCY -- the hard compiler problem. "Max 10 multiplies at once" is
a liveness/scheduling question, NOT a count. A pond may CONTAIN 50 multiplies
but only have 10 LIVE simultaneously due to pipeline staging. Need a
depth/liveness analysis across the pipeline to find true concurrent peak.
Overcount -> wastes DSP blocks. Undercount -> deadlock (two ops need a block
same tick, only one exists). This is the real work of the hybrid layer.

OVERFLOW (table exhausted). 8 cards, finite blocks, many ponds -> eventually
a pond asks for N and Shore has fewer free. Design choice, pick explicitly:
  - FALLBACK (preferred): pond uses available DSP + soft tiles for overflow.
    Runs slower but runs. ONLY possible because the .icm carries both
    encodings -- the soft model is the always-present backstop.
  - QUEUE: pond waits in pipeline_queue until blocks free. Use when DSP
    result is required (e.g. latency-critical) and soft fallback too slow.

DSP BLOCK IS STATEFUL. DSP slices have internal pipeline registers: feed,
result emerges N clocks later. Bridge cell is NOT a transparent pass-through
-- it has known latency the placer must add to the pond depth budget. The
two-arrival model handles the wait naturally (cell holds until result
arrives), but depth accounting must know N. Hence latency_ticks in the table.

FORMAT TYPING ACROSS BOUNDARY. A DSP MAC consuming MIF pairs is a typed
boundary like any other. DSP expects a specific operand layout; MIF is a
specific layout. Bridge cell presents MIF to the DSP in the form it wants,
wraps the result back into a MIF pair. Small format adapter -- declared, not
assumed. Same contract discipline as MIF_PACK/UNPACK and every bridge tile.

DEFER ALL OF THIS until single-card Arria 10 stable + pure-fabric validated.

---

## Format Bridge System (architectural — post-community)

BridgeContract base class: DONE (cell_format.py)
FormatRegistry.find_bridge(): DONE
FormatRegistry.discover_bridges(): DONE — declaration-grounded
FUNDAMENTAL_BRIDGES: DONE — 9 bridges, physics + biology + chemistry

Remaining:
- [ ] Compiler auto-placement of bridge tiles
- [ ] Design-time warning system (confidence threshold enforcement)
- [ ] SI_CHECK dimensional analysis integration
- [ ] Bridge section in community guide

---

## Deferred (architectural, no near-term action)

- Sentinel/Ward/Shore rethink — 3-cell Sentinel, Python-loop Ward
- Bootloader (.isi round-trip, Verilog loader)
- Branch/decision tree (COMPARE/CHOICE/RESULT/TABLE nodes)
- VoxCell photonic substrate — concept only, not buildable yet
- LLVM frontend — deferred until current changes settle
- SymPy equation input for MathTrix
- DisplayPond fire visualiser — needs Arria 10 scale

---

## Open Source Release Checklist

Software side essentially ready. Hardware milestone remains.
- [x] MUX selector bug fixed
- [x] Comparison operators fixed (>=, <=, !=)
- [x] Multi-param compiler bug fixed
- [x] MUL preloaded_a bug fixed
- [x] 157/157 compiler tests
- [x] 236/236 tile tests
- [x] 31/31 silicon tests
- [x] Docs consistent and correct
- [x] README with getting-started path
- [x] MIT licence (software)
- [x] CERN-OHL-P v2 (hardware)
- [ ] Verbatim official CERN-OHL-P text from ohwr.org (replace reproduction)
- [ ] Arria 10 working and stable          ← the remaining gate
- [ ] 1D Laplacian (or equivalent) on real Arria 10 hardware

---

## What Not To Do

- Don't add Python workarounds to run_int32_function
- Don't build packed adder before shift bits confirmed on Arria 10
- Don't start another audit document — this is the plan
- Don't mix old PRELOAD_NONE names with new PRELOAD_SEL_* in same file

---

## University Lab Deployment (post-Arria 10)

8 × Arria 10 cards in a secondhand mining rig.
~£1,000 total. Accessible for university labs.
Depends on: single card stable, PCIe pool architecture, pond addressing
across PCIe boundaries. Post-single-card milestone.

---

## Trix Ecosystem (community-driven, ongoing)

Format definitions: DONE — 9 formats, 6 domains + PoliticsTrix
Community space: DONE — scaffold, validate, hash, register, search
Bridge discovery: DONE — declaration-grounded, no guesses
Trix template: DONE — frontend/trix_template.html
MathTrix frontend: DONE — frontend/mathtrix_frontend.html
Region Connector: DONE — composer/region_connector.html

Next community actions:
- BioTrix models (DNA alignment, GC content, codon frequency)
- ChemTrix models (molecular weight, valence check)
- PhysTrix models (unit conversion, dimensional check)
- Compiler auto-placement of bridge tiles
