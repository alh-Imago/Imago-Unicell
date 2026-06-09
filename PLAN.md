# Imago UniCell — Active Plan
*Single source of truth for what needs doing and why.*
*Last updated: 2026-06-09*

---

## Hardware Status

| Hardware | Status |
|---|---|
| iCEBreaker iCE40UP5K | Silicon validated, 31/31 tests, 4-cell limit (UART bus) |
| Arria 10 GX660 (IEI Mustang-F100) | PCIe alive, onboard FTDI USB faulty |
| Waveshare USB Blaster V2 + JST cable | £46 — next month purchase |
| Quartus 25.1 | Installed and licensed on F:\Q |

---

## Naming Conventions — Verilog is Ground Truth

Python names must reflect Verilog names exactly.

- `preload_sel` — cmd_bus field. Python: `PRELOAD_SEL_ZERO`, `PRELOAD_SEL_ONES`
- `shift_sel`   — cmd_bus field. Python: `SHIFT_SEL_IN_EN`, `SHIFT_SEL_OUT_EN`

**Outstanding:** `command_interface.py` still uses `PRELOAD_NONE/ZERO/ONES` (old names).
Needs aligning to `PRELOAD_SEL_*`. Do in one clean pass with tests passing throughout.

---

## Test Suites — Current State

| Suite | Count | Status |
|-------|-------|--------|
| tests/vm/test_compiler_int32.py | 140/140 | ✓ passing |
| tests/vm/test_fp_tiles.py | 236/236 | ✓ passing |
| tests/fpga/test_sanity.py | 31/31 | ✓ silicon validated |

---

## Open Items — Non-Hardware (priority order)

### 1. MUL preloaded_a normalisation (compiler bug #4)
**File:** compiler_int32.py — run_int32_function Case 3
**Problem:** Values 0/1 may reach XOR cells as single bits not 0x00000000/0xFFFFFFFF.
Low priority — MUL not used in current demos. Fix before open-source release.
**Effort:** 30 minutes.

### 2. Multi-param re-injection (#6)
**File:** compiler_int32.py — run_int32_function
**Problem:** First int32 parameter excluded from re-injection. Workaround: put
non-passthrough param first. Real fix: re-injection covers all params equally.
**Effort:** 1 hour.

### 3. Test gaps
- [ ] Multi-param ordering test — covers bug #6
- [ ] Load/run API test — 8 ops (load, run, pause, resume, halt, freeze, reset, status)
      Currently manual-only, no automated coverage

### 4. command_interface.py naming
`PRELOAD_NONE/ZERO/ONES` → `PRELOAD_SEL_*` throughout.
Cosmetic but necessary for Verilog ground-truth consistency.
**Effort:** 30 min rename + verify tests pass.

### 5. Documentation cleanup
- [ ] docs/RUNNING.md — remove `inB` field references
- [ ] docs/ICM_FORMAT.md — deprecate `inB` field, document removal
- [ ] docs/EXAMPLES.md — verify all examples match current API
**Effort:** 1 hour total.

### 6. README animated GIF
Generate Gray-Scott or fast_marching animation from mathtrix_animate.py.
Add to README.md as the opening visual. High impact for outreach.
**Effort:** 15 minutes (mathtrix_animate.py already works).

### 7. Paper figure
Generate fast_marching wavefront PNG at high DPI for paper Section 4.
**Effort:** 10 minutes.

### 8. DisplayPond hosted flag
Add `hosted=True` mode to DisplayPond that routes pixel output to
GPU framebuffer (matplotlib/pygame surface) instead of cells.
mathtrix_animate.py already covers the mathematical output side.
The remaining gap is the cell-array fire visualiser — deferred to Arria 10.
**Effort:** 1-2 hours for the flag stub.

---

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

Not ready yet. Required before release:
- [x] MUX selector bug fixed
- [x] Comparison operators fixed (>=, <=, !=)
- [ ] Multi-param compiler bug fixed (#2 above)
- [ ] MUL preloaded_a bug fixed (#1 above)
- [ ] Arria 10 working and stable
- [ ] 1D Laplacian (or equivalent) on real hardware
- [x] 140/140 compiler tests
- [x] 236/236 tile tests
- [x] 31/31 silicon tests
- [x] Docs consistent and correct
- [x] README with getting-started path
- [x] MIT licence

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
