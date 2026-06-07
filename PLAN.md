# Imago UniCell — Active Plan
*Single source of truth for what needs doing and why.*
*Last updated: 2026-06-04*

---

## Naming conventions — Verilog is ground truth

Python names must reflect Verilog names, not invent parallel terminology.

- `preload_sel` — cmd_bus field (Verilog). Python: `PRELOAD_SEL_ZERO`, `PRELOAD_SEL_ONES`
- `shift_sel` — cmd_bus field (Verilog). Python: `SHIFT_SEL_IN_EN`, `SHIFT_SEL_OUT_EN`
- `forward_sim` — Python-only software step, no hardware equivalent. Name makes clear it is simulation, not a hardware feature.

Any new Python constants that reflect hardware fields: name follows the Verilog field name exactly.

**Outstanding:** command_interface.py still uses `PRELOAD_NONE/ZERO/ONES` (old names). Needs aligning to `PRELOAD_SEL_*` in a dedicated session. Don't mix old and new names in the same file — wait until the full rename can be done cleanly with tests passing throughout.

---



| Hardware | Status |
|---|---|
| iCEBreaker iCE40UP5K | Silicon validated, v2.3 protocol confirmed |
| Kintex-7 XC7K480T | Dead — physical layer failure |
| Arria 10 GX1150 (IEI Mustang-F100) | Replacement card, arriving soon |
| Quartus Prime 25.1 Standard | Installed and licensed on F:\Q |

---

## Immediate — Hardware arriving

### Arria 10 bring-up (Quartus)
- [ ] Create Quartus project targeting Arria 10 GX1150
- [ ] Instantiate Intel PCIe Hard IP (replaces Vivado XDMA)
- [ ] Port UniCell Verilog wrapper to Quartus constraints
- [ ] OPAE or raw PCIe driver on host side
- [ ] Verify PCIe enumeration and BAR0 round-trip
- [ ] Scale test — confirm cell count budget on Arria 10

**Note:** UniCell cell logic (unicell.v, unicell_array.v) is toolchain-agnostic.
Only the wrapper, constraints file, and PCIe IP instantiation need rewriting.

---

## Immediate — Verilog (iCEBreaker, no new hardware needed)

### Gate state bits — actual status

After checking unicell.v properly:

- **preload_sel (cmd_bus[18:17])** — ✅ already in silicon. Works.
- **shift_in_en (cmd_bus[19])** — ✅ already in silicon. Works.
- **shift_out_en (cmd_bus[20])** — ✅ already in silicon. Works.
- **a_preload_en / a_preload_val as cmd_latch bits** — NOT needed.
  cmd_latch is full (only bit 19 free). preload_sel already does this
  as a transient modifier. No new Verilog required.

**What actually needs doing instead:**

- [ ] Replace Python forward simulation in `run_int32_function` with
      proper emission of `CMD_RECONFIGURE | preload_sel` per cell.
      The hardware supports this today. The Python is doing extra work
      it doesn't need to do. This is a compiler/runtime fix, not Verilog.
      **Effort:** 1–2 hours. Significant simplification.

- [x] **shift_out_en (cmd_bus[20])** — confirmed on iCEBreaker silicon
- [ ] **shift_in_en (cmd_bus[19])** — cannot test on iCEBreaker (16-bit bus
      packing puts address in cmd_data[31:16] which interferes with input shift).
      Validate on Arria 10 with full 32-bit data bus.
- [x] **one_shot and loop_back** — in Verilog, add to testbench when needed

---

## Compiler — Known bugs (fix in priority order)

### 1. Output padding uses bare GS_PASS ✅ FIXED 2026-06-04
All four instances updated to GS_PASS | GS_LATCH_IN.

### 2. Dead code — duplicate compile_int32_function ✅ FIXED 2026-06-04
Lines 136-225 deleted. 1788 lines remain.

### 3. Dead code block after return ✅ FIXED 2026-06-04
Lines 289-334 deleted.

### 4. MUL preloaded_a normalisation (correctness bug)
**File:** compiler_int32.py — run_int32_function Case 3
**Problem:** Values 0/1 may reach XOR cells as single bits not 0x00000000/0xFFFFFFFF.
**Note:** Moot once a_preload_en lands. Fix now or defer to that point — documented either way.
**Effort:** 30 minutes.

### 5. MUX selector address space mismatch — FIXED (2026-06-07)
Three root causes identified and fixed in compiler_int32.py:
1. GS_PASS (outputs preloaded A=0) → GS_PASS_B (outputs arriving B) in padding chains
2. Zero-comparison fast path replaced with tile-based comparisons (tile-space results)
3. Constants 0/1 now always _compile_int32_literal (not IR single-bit path)
All 22 MUX cases pass: all comparison operators, arithmetic/constant branches,
nested ifs, both TRUE and FALSE branch selection.

### 6. Multi-param re-injection ordering
**File:** compiler_int32.py — run_int32_function
**Problem:** First int32 parameter excluded from re-injection. Workaround: put
non-passthrough param first. Real fix: re-injection should cover all params equally.
**Effort:** 1 hour.

---

## Compiler — Optimisations (blocked on Verilog bits)

These are real improvements but depend on shift_in_en / shift_out_en landing first.
Don't build workarounds for these — wait for the hardware.

- [ ] Packed adder tile (make_int32_add_packed) — 19 cells vs 482, needs shift bits
- [ ] MUL rewrite using packed adder — ~650 cells vs 2915
- [ ] Wallace tree MUL using shift_out_en — ~500 cells, depth ~20
- [ ] x > CONST / x < CONST general case — needs packed adder for cell count improvement

---

## Compiler — tile_config strategy system (DONE 2026-06-07)

tile_config dict is now accepted by all three public compiler entry points:
  Int32Compiler(tile_library=lib, tile_config={...})
  run_int32_function(src, fn, ops, lib, tile_config={...})
  load_int32_function(src, fn, ops, lib, tile_config={...})

Maps tile names to strategy strings. Applied via internal _get_tile() method.
Default (empty dict or None) uses each tile's standard strategy — fully
backward compatible, no existing call sites need updating.

Frontend usage pattern:
  MathTrix Laplacian:  tile_config={}   (no div/sqrt — not needed)
  MathTrix N-body:     tile_config={"MIF_DIV": "low_latency", "MIF_SQRT": "low_latency"}
  MathTrix PageRank:   tile_config={"MIF_DIV": "const_divisor"}
  BioTrix (future):    tile_config={...}  (its own domain choice)

**Future:** MathTrix pattern matcher auto-populates tile_config from expression
context (chain depth, cell budget, operation count). The auto strategy hook
in TileLibrary.get() is the landing point. No compiler changes needed when
this lands — calling code already passes tile_config, just the value changes
from hand-coded to computed.

---

## MIF (MathTrix Internal Float) — tile family (DONE 2026-06-07)

See docs/MIF_FORMAT.md for full specification.

Complete 19-tile family for MathTrix-internal floating-point.
IEEE-754 at region boundaries; MIF (ctrl+mant) pairs throughout.

**Boundary tiles** (paid once per region):
  MIF_UNPACK (74c), MIF_PACK (126c)

**Arithmetic tiles:**
  MIF_ADD (814c, d79), MIF_SUB (810c, d79)
  MIF_MUL (3066c, d89), MIF_MADD (3875c, d107)
  MIF_NEG (1c), MIF_ABS (0c — pure wiring)
  MIF_DIV (4789c, d1177), MIF_SQRT (5317c, d1177)

**Comparison tiles** (operate on ctrl cell — no mantissa decompose):
  MIF_CMP_EQ (98c), MIF_CMP_LT/GT (212c), MIF_CMP_LE/GE (213c)

**Selection tiles** (CMP + 64-bit pair MUX):
  MIF_MIN/MAX (468c)

**Newton-Raphson strategy variants** (via strategy parameter):
  lib.get("MIF_DIV",  strategy="low_latency")   # 23916c, depth 536
  lib.get("MIF_SQRT", strategy="low_latency")   # 42325c, depth 818
  lib.get("MIF_RECIP",strategy="low_latency")   # 20850c, depth 489
  lib.get("MIF_DIV",  strategy="const_divisor") # 3066c,  depth 89 (→ MIF_MUL)

Strategy taxonomy:
  cell_budget   — digit-by-digit (default, fewest cells)
  low_latency   — Newton-Raphson (more cells, ~half depth)
  const_divisor — MIF_DIV only, divisor fixed at compile time
  auto          — resolves to cell_budget; future: context-aware

MIF is documented as MathTrix-primary but usable elsewhere with caution.
Specialist frontends access it via tile_config or direct lib.get() calls.

**Barrel shifter optimisation history (FP32_ADD):**
  Naive MUX2:        1253c, depth 85
  Shared NOT(sel):   1023c, depth 85
  Wired-OR preload:   779c, depth 79  ← current, theoretical minimum

---

## MathTrix — Python frontend for mathematical problems

Blocked items are resolved. These tiles now exist: SHR_N, SHL_N, INT32_MUL.

### MIF tile family — DONE 2026-06-07

MIF (MathTrix Internal Float) is a complete floating-point subsystem for
MathTrix regions. IEEE-754 is the wire format at region boundaries; MIF
pairs (ctrl+mant) flow through all internal arithmetic without repacking.

Complete MIF tile family (17 tiles):
  Boundary:    MIF_UNPACK (74c), MIF_PACK (126c) — once per region
  Arithmetic:  MIF_ADD (814c), MIF_SUB (810c), MIF_MUL (3066c),
               MIF_MADD (3875c, fused A*B+C), MIF_NEG (1c), MIF_ABS (0c)
  Comparison:  MIF_CMP_EQ (98c), MIF_CMP_LT/GT (212c), MIF_CMP_LE/GE (213c)
  Selection:   MIF_MIN/MAX (468c)

Barrel shifter optimised across three generations:
  Naive MUX2:       480c/barrel  →  Shared NOT(sel): 365c  →  Wired-OR: 240c
  FP32_ADD journey: 1253c → 1023c → 779c  (-474c, 37.8%, depth 85→79)

MIF available for use outside MathTrix with caution — designed primarily
as MathTrix-internal format, documented as such.

### Demo status

- [x] **1D Laplacian — integer** (mathtrix_laplacian_1d.py) DONE 2026-06-05
- [x] **1D Laplacian — MIF float** (mathtrix_laplacian_1d_mif.py) DONE 2026-06-07
- [x] **2D Laplacian** (mathtrix_laplacian_2d_mif.py) DONE 2026-06-07
      5-point stencil, radial diffusion, 10053c shared
- [x] **Ising model** (mathtrix_ising_mif.py) DONE 2026-06-07
      Domain formation, wired-OR bus aggregation = 0 cells in hardware
- [x] **Fast Marching** (mathtrix_fast_marching_mif.py) DONE 2026-06-07
      Geodesic wavefront, MIF_MIN (468c) showcase, slow-region bending
- [x] **Gray-Scott reaction-diffusion** (mathtrix_gray_scott_mif.py) DONE 2026-06-07
      Turing patterns, two coupled MIF regions (u+v)
- [x] **Wave equation** (mathtrix_wave_mif.py) DONE 2026-06-07
      2D wave, u_prev state storage, Gaussian pulse reflection
- [x] **PageRank** (mathtrix_pagerank_mif.py) DONE 2026-06-07
      Graph diffusion, MIF_DIV for PR[j]/deg[j], convergence via CMP_LT
- [x] **N-body gravity** (mathtrix_nbody_mif.py) DONE 2026-06-07
      Softened potential, MIF_SQRT+DIV for 1/r²
- [x] **Boids flocking** (mathtrix_boids_mif.py) DONE 2026-06-07
      Reynolds rules, MIF weighted-sum chains
- [x] **Continuous Conway** (mathtrix_conway_mif.py) DONE 2026-06-07
      Smooth Game of Life, sigmoid via MADD+SUB, wired-OR 8-neighbour sum

**All 9 MathTrix demos complete. Full demo library done.**

### Other MathTrix work
- [ ] Pattern matcher for stencil recognition
- [ ] SymPy equation input
- [ ] Validate output against known solution
- [ ] Export to .icm
- [ ] MIF_DIV — needed for PageRank, N-body (complex, Newton-Raphson mantissa)
- [ ] MIF_SQRT — needed for N-body, distance calculations

**Note:** MathTrix needs compiler MUX bug (item 5 above) fixed before
any demo involving if/else branches will work correctly.

---

## Tests — Gaps

- [ ] MUX selector bug needs a test that catches always-false-branch failure
- [ ] Depth padding correctness test (shallow + deep operand pair)
- [ ] Multi-param ordering test
- [ ] Comparison random fuzz — 300/300 passing but not in suite
- [ ] Load/run API — all 8 ops, currently manual only
- [ ] SYNC_WAIT hardware test in tests/fpga/

---

## Display / Output — Architecture note

### DisplayPond — cell-based rendering is demo/standalone only
Current DisplayPond writes video output directly to cells, which works
but consumes significant cell budget for a small display area.

- [ ] **On hosted systems (PC, server):** output should write to GPU
      framebuffer directly — let the host GPU handle video. No cells
      consumed for display. DisplayPond becomes a thin bridge that
      writes pixel data to a host surface rather than cell arrays.
- [ ] **Current cell-based implementation** is appropriate for:
      standalone embedded systems with no GPU, demo hardware, iCEBreaker
      direct output. Should not be the default on hosted systems.
- [ ] **Add a `hosted` flag or mode** to DisplayPond that routes output
      to GPU/framebuffer instead of cells when running on a host machine.
- [ ] Document the distinction clearly — cell rendering vs GPU passthrough
      are two different deployment targets.

**Note:** test_display_pond.py is skipped (requires pygame) — when the
GPU passthrough mode is built, it should have its own test that doesn't
require a display.



- [ ] Sentinel/Ward/Shore rethink — 3-cell Sentinel, Python-loop Ward
- [ ] Bootloader (.isi round-trip, Verilog loader)
- [ ] Branch/decision tree (COMPARE/CHOICE/RESULT/TABLE nodes)
- [ ] VoxCell photonic substrate — see docs/VOXCELL_PHOTONIC.md (concept, not buildable yet)

---

## Documentation — Current state

**Ground truth documents (keep current):**
- docs/CELL_INTERNALS.md — cell register model, v2.3 protocol
- docs/ARCHITECTURE.md — overall design
- docs/COMPILER_NOTES.md — compiler capabilities and known issues
- docs/COMPILER_TILE_CONFIG.md — tile_config strategy system (NEW 2026-06-07)
- docs/MIF_FORMAT.md — MIF tile family specification (NEW 2026-06-07)
- docs/FPGA_HARDWARE.md — FPGA reference
- docs/VERILOG_SPEC.md — Verilog spec

**Needs updating:**
- docs/RUNNING.md — inB references to remove
- docs/ICM_FORMAT.md — inB field to remove/deprecate
- docs/EXAMPLES.md — verify examples match current API

**Forward-looking design docs (accurate but not yet built):**
- docs/math_frontend_design.md — MathTrix
- docs/BRANCH_DECISION_TREE.md — branch architecture
- docs/COMPOUND_OPCODES.md — v3 design

---

## What not to do

- Don't add more Python workarounds to run_int32_function
- Don't work around the MUX selector bug — fix it properly
- Don't build the packed adder tile before shift bits are in Verilog
- Don't start another audit document — this is the plan

---

## Open source release

Goal: make UniCell accessible as a real tool for university labs,
researchers, and developers. Low entry point via the mining rig
deployment. MathTrix and Composer as accessible frontends.

**Not ready yet.** Known issues documented in PLAN.md must be
resolved first — specifically:
- MUX selector bug (silent correctness failure)
- Multi-param compiler bug
- Arria 10 bring-up working and stable
- 1D Laplacian (or equivalent) running on real hardware

Open sourcing before these are fixed means first users hit
known bugs immediately. Better to release something that works.

**When ready:**
- GitHub repo public (currently private under alh-Imago)
- README with clear getting-started path
- Working demo (MathTrix 1D Laplacian on VM minimum)
- PLAN.md honest about what's missing
- MIT or Apache 2.0 licence



Concept: 8 × Arria 10 cards in a secondhand mining rig, PCIe pool,
host machine running workbench monitoring ponds via PTT.

- ~£800 for 8 cards at ~£100 each (IEI Mustang-F100 or equivalent)
- ~£100-200 for a secondhand mining rig with 8-12 PCIe slots
- Total ~£1,000 — accessible for university labs

**Cell count is unknown until Arria 10 bring-up is complete.**
Depends on how efficiently UniCell Verilog fits the Arria 10 ALMs.
Kintex-7 gave ~450 LUTs/cell as reference but Arria 10 uses different
primitives. Actual figure comes from the Quartus build.

**Dependencies before this is realistic:**
- Single Arria 10 card working reliably
- PCIe pool architecture (multi-card coordination)
- Pond addressing across PCIe boundaries
- Workbench monitor via PTT on host

This is a post-single-card milestone, not a near-term deliverable.
Worth designing toward once the single card bring-up is stable.



Longer-term vision: a family of domain-specific frontends (Trix) that
all compile to ICM via a documented compiler API. Others build frontends;
they don't need to understand UniCell internals, just the API contract.

- MathTrix — in progress, reference implementation
- BioTrix, ChemTrix, AstroTrix, DataTrix, FinanceTrix — future, by others

**Key dependency:** the compiler is tile-library-aware. A frontend author
either uses existing tiles or supplies domain-specific tile models for
operations that don't exist yet. Domain experts contribute tiles that
match their domain — the compiler API stays stable, the library grows.

**Not realistic until:**
- MathTrix working end-to-end
- Known compiler bugs fixed
- Compiler API surface stable and documented
- ICM format stable

Probably 6-12 months from being genuinely usable by others.
Worth designing toward, not building for yet.

See docs/TRIX_ECOSYSTEM.md for the vision document.

