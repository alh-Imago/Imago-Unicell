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
