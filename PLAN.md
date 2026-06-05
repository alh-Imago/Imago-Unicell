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

### 5. MUX selector address space mismatch (correctness bug, silent)
**File:** compiler_int32.py — _place_int32_mux
**Problem:** if/else returning int32 constants always returns the false branch.
Root cause: IR graph node output_addr not in tile placer address space.
The PASS relay connects to the wrong address space.
**Note:** Needs proper investigation — don't work around it.
**Effort:** Unknown — needs a dedicated session.

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

## MathTrix — Python frontend for mathematical problems

Blocked items are resolved. These tiles now exist: SHR_N, SHL_N, INT32_MUL.

- [x] **1D Laplacian demo** — DONE 2026-06-05. mathtrix_laplacian_1d.py.
      Correct physics, 9 steps, heat diffuses from spike to boundaries.
      Cell count: ~3260/call, ~29340/step — large because called per point.
      Real parallel version blocked on multi-param compiler bug (item 6).

- [ ] Pattern matcher for stencil recognition
- [ ] SymPy equation input
- [ ] Validate output against known solution
- [ ] Export to .icm

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

## Future direction — Trix ecosystem / open compiler API

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

