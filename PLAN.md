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

ICM PROFILES -- three states, one save mechanism (refined this session):

  1. PORTABLE / SOFT-ONLY (compiler output, distribution + testing).
     Soft models for everything + a flag: "max N DSP-eligible ops concurrent".
     Runs anywhere (VM, iCEBreaker, any card). Tag: profile=soft, portable=true.
     This is the correctness-proof and sharing artifact. No card dependency.

  2. CARD-TAILORED / HYBRID RUNTIME (loader output, optimised deployment).
     Loader takes portable .icm + card profile -> substitutes DSP/BRAM markers,
     corrects depths to THIS card's hard-block latencies, re-walks the depth
     accounting. NON-PORTABLE BY CONSTRUCTION -- tied to one card type. MUST be
     stamped: profile=hybrid, card=<model> (e.g. arria10-gx660). Refuse-to-load
     guard: a hybrid image for card A must NOT load on card B without going back
     through the loader's re-tailoring. Loading wrong-card depths = silent
     timing corruption (worst-kind bug). Enforce, do not merely document.

  3. SAVE-BACK -- the file must be self-describing. A bare "DSP at depth X" is
     INSUFFICIENT: it does not say what the DSP is computing. So every
     offloadable op in a saved hybrid .icm carries BOTH:
       - soft model  (canonical: what the op logically IS -- mul/add/MAC...)
       - hard binding (this card: maps to DSP block, depth X)
       - marker linking them ("this DSP marker replaces this soft model")
     Soft model = ground truth/substrate; hard binding = card-specific overlay.

ONE SAVE MECHANISM, ONE DECISION (resolves the "two modes?" question):
  Because the hybrid file ALWAYS carries the soft model under the hard binding,
  there is only one save format. Portability = whether you STRIP the overlay:
    Save portable -> soft models only, drop hard bindings, tag soft.
    Save hybrid   -> soft + hard bindings + depth corrections, stamp card.
  The "intelligence" needed is just the rule: soft model is canonical and
  always present; hard binding is an optional card-stamped overlay. Strip it
  for portability, keep it for the optimised runtime.

LOADER'S REAL JOB (not find-and-replace). Substituting a hard block changes
the timing of everything DOWNSTREAM, not just that op. The loader re-walks the
depth accounting through the program table with substituted latencies. Tractable
because the table is compile-time-resolved and step-sequential -- the loader
re-times a KNOWN dependency graph, it does not schedule from scratch. Compiler
did the structure; loader re-times for the card.

CARD PROFILE FILE (the separate device manifest the loader reads):
  Per hard-block type: { type, count, op_class, depth_ticks }. Plus card id
  for the stamp. This is the "correct the depths by availability of the types
  on the specific card" file. Static (emitted with the gateware build) per the
  earlier resource-manifest decision.

THREE-LAYER SAVE MODEL (refined -- master / targeted base / checkpoint):
  - MASTER: portable soft-only .icm, canonical. Never lost. Runs anywhere.
  - TARGETED BASE: produced by RECOMPILING the master with a target card flag
    (cross-compile, not "decompile") -> soft models + hard bindings together,
    card-stamped. The card-specific base.
  - CHECKPOINT: a timed save during a running program. Uses the targeted base
    and writes only the CHANGED STATE (cell states) on top. Stores progress,
    not the whole program.
  Fallback chain: checkpoint -> targeted base -> master. Lose a checkpoint,
  restart from base. Lose the base, recompile from master. Master never lost
  (portable + canonical).

WHAT A CHECKPOINT SAVES, AND WHY THE FREEZE MAKES IT SIMPLE:
  Save-state happens ONLY AFTER A FREEZE. Freeze halts the working logic --
  nothing clocks new data through, pipelines empty, the whole system quiesces.
  Therefore every DSP/hard block has DRAINED: nothing in flight, by
  construction. The freeze IS the clean boundary -- no need to reason about
  in-flight hard-block results or step boundaries; freeze removes that entire
  problem class.
  Save = CELL STATES ONLY. Cells hold persistent data (yours, readable,
  writable). DSP blocks hold NOTHING persistent between ops, and after a freeze
  are empty + idle -- there is nothing to save. So cell states alone capture
  the COMPLETE persistent state of the frozen system. DSP blocks resume their
  fungible work on unfreeze when data flows again.
  Rule: freeze -> system quiesces -> hard blocks settle -> save cell states.
  "Cell states yes, DSP states no" -- not a limitation, a consequence of DSP
  carrying no persistent state and the freeze guaranteeing none in flight.

NOTE on file vs fabric (clears a worry): keeping the soft model in the saved
file costs DISK BYTES, not FABRIC CELLS. When a hard block is bound the loader
does NOT instantiate the soft model's cells -- the fabric gets the DSP bridge,
not the 3066 cells of MIF_MUL. The cell saving is fully realised on silicon.
The soft model in the file is a few KB of description retained for portability
+ self-description, costing zero fabric. "In the file" and "in the fabric" are
different spaces -- the whole hybrid design depends on that separation.


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

PEAK CONCURRENCY -- already solved by the program table. The table-driven
pipeline model is inherently sequential through its steps (streams configs
from DDR, reconfigures fabric step by step). Each table step already declares
how many of each model are active at that step -- that IS what the step is.
So peak concurrent DSP demand is just max-across-steps of the model count
column the table ALREADY carries. No liveness inference needed; read it off
the table. DSP allocation grabs the max-across-steps count once, holds those
blocks for the program lifetime, table reuses them step to step exactly as it
reuses cells.

  Why this works: the programs that use DSP offload at scale ARE the linear,
  table-driven ones (config-streaming pipelines). The pathological
  free-dataflow case where liveness would be hard to infer is NOT a case
  you'd deploy via the hybrid -- the architecture's own structure routes
  around the hard problem. Linearity is the enabler, not a limitation.

  FURTHER SIMPLIFICATION -- no summing, just the max. A DSP slice is a GENERAL
  arithmetic unit (add, sub, mul, MAC -- all of it). So a block allocated to a
  pond serves whatever maths the current step needs; blocks are fungible
  across operation types. The allocator does NOT sum per-type counts. It needs
  exactly one number: max(step.model_count for step in table) -- the tallest
  single step. Grab that many fungible blocks, done. N blocks cover N
  simultaneous maths ops whether adds, muls, or a mix.

  Nested-loop caveat (already handled): if several loop bodies are live at the
  same step, each with its own maths models, that step's count reflects the
  total because the compiler expands loops at table-build time. The concurrent
  step simply shows the higher count and the max-scan catches it for free.
  Only dynamic runtime loop instantiation would break this -- which the table
  model does not do. The table is fully resolved before load; everything
  concurrent is enumerated at compile time. "Compiler picks it up at the
  start" is a structural guarantee, not a hope.

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

WHAT THE HYBRID LAYER ACTUALLY NEEDS (summary):
  1. Target profile flag (pure | hybrid) on the loader -- trivial, one bit.
  2. Max-scan allocator -- max(step.model_count), grab fungible blocks --
     nearly free, prototypable in software against a fake table now.
  3. Shore DSP resource table -- mirrors existing cell-range allocation,
     small extension.
  4. DEVICE-SPECIFIC GATEWARE -- the real new work. Verilog must instantiate
     hardened DSP primitives, which are vendor/device-specific (Arria 10 DSP
     != Kintex-7 DSP48 != iCE40). Current gateware is fabric-generic; hybrid
     needs a per-device layer. GATED on a working Arria 10 -- cannot write or
     test DSP instantiation against a card you cannot program.
  5. RESOURCE MANIFEST mechanism -- get the DSP inventory into Shore's table.
     STATIC (preferred, fits the architecture): synth emits a manifest with
     the build -- "N blocks at these addresses, this latency, these ops" --
     ships alongside the bitstream, Shore loads at bring-up. Declared not
     discovered, same philosophy as dual-encoded .icm and pre-resolved table.
     RUNTIME alternative: gateware register block the host reads at bring-up;
     more flexible for variant cards, more gateware + handshake complexity.

SCALE REALITY CHECK: GX660 has ~1,600+ DSP blocks. A single pond needing 1000
simultaneous maths models is implausible -- cell budget exhausts long before
DSP budget. Realistic peak is dozens to low hundreds per pond. Resource table
is not a single-card contention bottleneck; cross-pond contention covered by
the soft-fallback safety valve.

DEPENDENCY: everything except the allocator logic waits on Arria 10 being up,
because device-specific gateware is the foundation the rest sits on. Allocator
could be prototyped now in software against a fake resource table if a chip-at
task is wanted, but it is low value until real gateware declares real blocks.

### Other allocatable hard resources (same pool-allocation pattern as DSP)

The filter: a resource fits the DSP allocation pattern IF it is a FUNGIBLE
POOL of fixed-location hardened blocks doing a self-contained op with a clean
boundary (in -> out, no ongoing state the fabric manages). Test question:
"could two ponds each want their own private copy of this at once?" Yes =
allocatable pool. No = shared infrastructure (manifest-declared, configured
once, NOT pool-allocated).

ALLOCATABLE POOLS (extend the Shore resource table to these):
- BRAM / M20K blocks -- THE strong next one. Arria 10 has thousands. Move
  large tables OFF fabric cells INTO dedicated memory: MIF reciprocal LUT,
  genetic code table, periodic table, format symbol maps, preloaded weight
  sets. Attacks the cell budget the same way DSP does but for TABLES instead
  of arithmetic -- and this architecture is unusually table-heavy, so the win
  is large. Natural fit: address-as-identity and preloaded-table thinking is
  already the model; BRAM is just a bigger faster table that costs no cells.
  Allocate exactly like DSP: program declares table size, Shore allocates a
  block, bridge cell reads/writes it.
- Hardened crypto blocks (AES/SHA) IF the Arria 10 variant has them. Same
  shape: finite, fixed, self-contained, clean boundary. Allocate like DSP
  (need a hash -> grab a block -> data in, digest out). Dovetails with the
  UniCell Security Module concept (fabric-as-root-of-trust). Check whether
  the target variant carries them.

SHARED INFRASTRUCTURE (manifest-declared, NOT pool-allocated -- allocating
these per-pond would cause contention, category error):
- PLLs / clock regions -- infrastructure, configured once at bring-up.
- PCIe / SerDes transceivers -- the host boundary, shared system link.
- DDR memory controller -- single shared gateway (all ponds share it through
  Shore); it is a bus, not a fungible block.

### I/O reservation -- keep cells fed, keep the bus clear (design sketch)

Distinct from the pool-allocation above: this is about SCHEDULING data
movement, not allocating compute blocks. The aim is to stop the fabric
stalling on data and to stop the shared bus (DDR/PCIe) congesting.

Idea: an I/O reservation layer in Shore that, reading the program table's
per-step data needs, pre-stages raw input into BRAM/near-fabric buffers
AHEAD of the step that consumes it, and drains results OUT of result buffers
behind the step that produced them. The cells always find their next input
already staged (fed), and results leave promptly so buffers do not back up
(bus clearer). Because the program table is compile-time-resolved and
step-sequential, the data schedule is KNOWN IN ADVANCE -- same property that
made DSP peak-concurrency a simple max-scan. So I/O reservation is a
prefetch/drain schedule computed from the table, not a runtime guess.

Open questions (do NOT resolve until single-card Arria 10 stable):
- Buffer sizing: how much BRAM reserved as I/O staging vs as table storage --
  a split of the same BRAM pool, decided per program from the table.
- Double-buffering: stage step N+1 input while step N computes (classic
  ping-pong) -- the table already says what N+1 needs.
- Back-pressure: if the DDR/PCIe bus is busy, the schedule must degrade
  gracefully (compute waits on data) rather than overflow a buffer. Two-
  arrival model helps -- a cell simply holds until its staged input arrives.
- Whether this is one mechanism with DSP/BRAM allocation or a separate Shore
  pass that runs after block allocation. Likely separate: allocate blocks
  first, then schedule the data movement among them.

Principle: the table already knows the whole data itinerary. I/O reservation
just acts on it early -- prefetch ahead, drain behind -- so the fabric is
never waiting and the bus is never choked. Same "declared not discovered,
read it off the table" discipline as everything else.

DEFER ALL OF THIS until single-card Arria 10 stable + pure-fabric validated.


---

## Multi-Cage Scaling (far future -- two-regime design note)

Beyond the 8-card single-cage rig: multiple cages networked together.
The key realisation -- this is NOT just a bigger bus. Crossing a cage boundary
crosses from a BUS to a NETWORK, and that changes the timing physics. Two
distinct regimes, joined at a bridge:

INSIDE A CAGE = a fabric.
  Card-to-card over PCIe: tens-hundreds of ns, predictable, fixed-latency.
  Compile-time-resolved timing holds. Fine-grained tiles, tight pipelines,
  depth accounting valid. This is everything designed so far.

ACROSS CAGES = a network of fabrics.
  Cage-to-cage over network: microseconds, VARIABLE (jitter). The two-arrival
  model tolerates latency (cell holds until input arrives) BUT depth
  accounting assumes KNOWN fixed latencies -- network jitter breaks the
  compile-time timing guarantee. Therefore inter-cage bridges must sit at
  COARSE, latency-tolerant boundaries (between whole sub-computations that
  tolerate variable hand-off), NEVER woven into a fine-timed stencil on a
  critical path.

SMARTNIC AS INTER-CAGE BRIDGE (sound -- the strong idea):
  SmartNICs are FPGAs sitting directly on the network fabric (AMD/Xilinx
  Alveo, Intel/Napatech, BlueField-FPGA). A bridge contract is already just a
  boundary tile (in -> transform -> out). Nothing requires that boundary to be
  in the same card as the regions it joins. A bridge tile synthesised onto a
  SmartNIC's fabric converts a typed result IN THE NETWORK PATH: typed result
  leaves cage A, bridge transform applied in flight, delivered typed+converted
  to cage B. No host-CPU round-trip. Architecturally consistent -- the bridge
  was always a boundary; this places it on the wire.

HIERARCHICAL SHORE (the timing/SPOF fix):
  One SBC managing one cage = fine. One SBC as master allocator for many cages
  = coordination chokepoint + single point of failure. Correct pattern:
  per-cage Shore manages its LOCAL pool; a thin top coordinator manages
  BETWEEN cages (delegates, does not micromanage remote blocks). First cage's
  SBC can host the top coordinator. Each cage self-manages.

Reframe that makes it scale: inside a cage = tight fixed-latency fabric;
across cages = network of fabrics joined by coarse, async, latency-tolerant
SmartNIC bridges, each cage self-managing under a thin coordinator. Treat the
network as a bigger bus and it bites on timing. Treat it as a second regime
and it scales.

DEFER -- far future, post-rack. Captured now so the timing caveat is not
forgotten when the rack exists.

---

## Evaluating an FPGA card -- where does it fit? (reusable framework)

When a candidate FPGA card catches the eye, place it by ROLE, not by specs
alone. Four roles in this architecture, each wanting different things:

1. PROVING / ITERATION card (currently iCEBreaker).
   Wants: cheap, fast synth, open toolchain (yosys/nextpnr ideal), small is
   fine. Used to validate single-cell behaviour and catch bugs at minimum
   scale. A new card fits here if it is cheap and iterates fast. Raw size
   does NOT matter -- 4 cells found three bugs that hid at 482.

2. SCALE / COMPUTE card (currently Arria 10 GX660/1150).
   Wants: large LUT/logic count (cell capacity), abundant DSP + BRAM (the
   hybrid pools), DDR (config streaming), PCIe (host link). This is where raw
   size and hard-block count matter. Judge by: how many cells, how many DSP,
   how much BRAM, DDR bandwidth.

3. NETWORK / BRIDGE card (the SmartNIC idea).
   Wants: FPGA fabric ON a network interface. Judge by: does it sit in the
   data path between hosts/cages, can it run a bridge tile in flight. Size
   secondary -- it carries bridges, not bulk compute.

4. EMBEDDED / DEPLOYMENT target (ECU, security module, edge).
   Wants: small, low power, can boot from flash (.isi), runs a fixed
   pipeline-reconfigured program from DDR. Judge by: power envelope, boot
   options, cost at volume. The pipeline-reconfiguration model (small cells,
   stream configs) is what makes tiny targets viable.

PLACEMENT TEST for any new card:
  - Cheap + fast + open tools         -> proving card
  - Big logic + DSP + BRAM + DDR      -> scale card
  - FPGA on a NIC / in the network    -> bridge card
  - Small + low power + flash boot    -> embedded target
  - None of these cleanly             -> probably not worth adopting yet

Caution before buying ANY card: confirm toolchain (Quartus? Vivado? open?),
confirm programming path (onboard USB-JTAG reliable? external needed?), and
confirm it is not a niche part with no community / docs. The Arria 10 FTDI
saga is the lesson -- a card is only as usable as its programming path.

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
