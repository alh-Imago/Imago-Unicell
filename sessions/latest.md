# Session Log — 2026-06-14 (community worked example models)

## Final commit: 169b842
## Suites: 242/242 fp_tiles, 157/157 compiler_int32, 31/31 silicon,
##         27/27 flowtrix, 13/13 flowtrix_collide, 18/18 flowtrix_cylinder,
##         28/28 neurotrix_lif, 14/14 neurotrix_lif_mif, 14/14 mif_mux,
##         16/16 mif_recip, 15/15 mif_rsqrt, 29/29 walker,
##         14/14 community_raw, 19/19 miditrix,
##         175/175 community_models (NEW)
## Previous session archived: sessions/archive-2026-06-13.md

---

## Nature of this session
Started from a fresh PLAN.md review — determined that FlowTrix VM build,
walker follow-ups (1b A+B), and community non-Trix expansion were all
already done in the previous session. Only remaining pre-hardware items were:
(1) CERN-OHL-P verbatim licence text — blocked by network in container,
    flagged for FPGA1 (one curl command).
(2) BioTrix/ChemTrix/PhysTrix worked example models — done this session.

---

## Commits this session
- 169b842  Community: BioTrix/ChemTrix/PhysTrix worked example models + test suite

---

## Community worked example models — DONE

11 models across 3 domains. All tile references validated against
format.valid_tiles. All MANIFEST.json files updated. 175/175 tests.

### BioTrix (5 models)
- **gc_content**: GC% via DNA_GC_COUNT rolling window. GC content correlates
  with melting temperature; human genome ~41%, CpG islands >60%.
- **hamming_distance**: Sequence mismatch count via DNA_HAMMING. Parallel
  XOR+popcount across packed base-pair words.
- **dna_complement**: Reverse complement via DNA_COMPLEMENT + DNA_REVERSE.
  Purely structural on the 2-bit packed encoding — complement is bitwise NOT
  on base bits, reverse is word-order swap. Zero arithmetic.
- **codon_scan**: 3-base window extraction via RNA_WINDOW_3, one reading
  frame at a time. First stage of in-silico translation. Three reading frames
  = three parallel instances.
- **hydrophobicity_profile**: Kyte-Doolittle score per residue via
  AMINO_HYDROPHOBIC. Preloaded K-D constant table; peaks identify
  transmembrane helices. Downstream: MIF sliding average for smoothed profile.

### ChemTrix (3 models)
- **molecular_weight**: Atomic mass accumulation via CHEM_MASS (preloaded
  table indexed by atomic number). Validates: H2O=18.015u, CO2=44.009u,
  glucose=180.156u.
- **valence_check**: Octet-rule validation via CHEM_VALENCE + CHEM_BOND.
  Outputs 1-bit validity flag. Validates CH4 and CO2.
- **electronegativity_delta**: Pauling bond polarity |χA-χB| via
  CHEM_ELECTRONEGATIVITY. Classifies covalent/polar/ionic bonds.
  Reference: H-H=0.00, H-Cl=0.96, Na-Cl=2.23.

### PhysTrix (3 models)
- **hawking_temperature**: T = ℏc³/(8πGMk_B) via SI_HAWKING_TEMP.
  All 4 constants from CODATA 2018. semantic_confidence=1.0 bridge point
  noted (the paper topic — same T feeds Stefan-Boltzmann thermal model).
  Validates: M=M_sun → T≈6.17×10⁻⁸ K.
- **schwarzschild_radius**: r_s = 2GM/c² via SI_SCHWARZSCHILD.
  Companion to hawking_temperature: same inputs, complementary outputs.
  Validates: M=M_sun → r_s≈2954m, M=M_earth → r_s≈0.00887m.
- **arrhenius_rate**: k = A·exp(-Ea/RT) via SI_ARRHENIUS. R computed from
  CODATA NA×kB (not hardcoded). SI_CHECK enforces [k]=s⁻¹. Validates
  Ea=50kJ/mol → k(300K)≈1.0×10⁴ s⁻¹, k(600K)≈2.7×10⁸ s⁻¹.

---

## Doc updates + manual rebuild — DONE (commit 3b87503)

Three docs updated, manual rebuilt.

**INDEX.md:**
- Tile table: MIF_MUX (193c d3), MIF_RECIP (15,288c d349), MIF_RSQRT (22,916c d445) added
- Test suite table: 3 stale entries → 15 current suites at correct counts
- Repo map: domain frontends section, community/, walker, all new files added

**TRIX_ECOSYSTEM.md:** complete rewrite. Was a June 2026 vision doc;
now a current-state reference covering MathTrix/FlowTrix/NeuroTrix/MidiTrix
with tile counts and test counts, FormatDefinition table (12 formats),
bridge system, community contribution space, walker authoring routes.

**LIBRARY.md:** community section rewritten — was pointing to obsolete
`composer/models/INDEX.md`; now documents real `community_tools.py` workflow.

**manual.html:** rebuilt (13 sections, no errors).

---

## CERN-OHL-P licence fix (deferred — cannot do in container)

PLAN checklist item: replace reproduced body of LICENSE-HARDWARE with
verbatim official text from CERN. Container network blocks the fetch.
Do on FPGA1:

    curl -sL https://ohwr.org/cern_ohl_p_v2.txt -o /tmp/cern_ohl_p_v2.txt
    # Then: replace lines 1-120 of LICENSE-HARDWARE with content of that file,
    # keeping the SCOPE OF THIS LICENCE section (lines 123-138) unchanged.
    # Commit as: "Licence: replace reproduced CERN-OHL-P body with verbatim official text"

This is the last item before the open source release checklist is fully
software-complete (only remaining gate: Arria 10 working demo).

---

## Pre-hardware checklist status

All pre-hardware non-hardware items now complete except the licence text fix:

- [x] FlowTrix VM build (done 2026-06-13)
- [x] Walker 1b: --module flag + record_hash (done 2026-06-13)
- [x] Community non-Trix exchange (done 2026-06-13)
- [x] BioTrix/ChemTrix/PhysTrix worked example models (done this session)
- [ ] CERN-OHL-P verbatim text — one curl on FPGA1

Hardware-gated items unchanged. Awaiting Waveshare USB Blaster V2 + JST
SH 1.0mm connector kit.

---

## Hardware (unchanged — gated)
Arria 10 GX660. USB Blaster V2 + JST SH 1.0mm paid 26th May.
First test on arrival: jtagconfig → IDCODE on the 660.
FlowTrix collide: 1,714 predicted ticks/update (reciprocal-optimised).
LIF tick: 353 predicted ticks/update.
These become the first predicted-vs-measured checks on silicon.

## Paper references completed (commit c4fe59f) + manual rebuild (6169304)

All 15 references resolved to full, verified citations. Changes:

- **Ref 2** (Heule et al.): full author list, LNCS vol/pp, DOI added
- **Ref 3** (Reynolds): full SIGGRAPH journal title + DOI
- **Ref 4** (Turing): DOI added
- **Ref 5** (Negrut et al.): full author list + DOI
- **Ref 6** (Liu et al.): article number + DOI
- **Ref 7** (Podobas et al.): DOI added
- **Ref 8** (De Sutter et al.): full Springer chapter DOI
- **Ref 9** (was a blank placeholder): resolved to Dennis & Misunas (1975),
  "A preliminary architecture for a basic data-flow processor", ISCA '75,
  SIGARCH 3(4), pp.126–132, DOI 10.1145/641675.642111. This is the correct
  citation: the body text [9] described ordered/tagless firing where tokens
  match on arrival — that is exactly the static-dataflow model Dennis &
  Misunas introduced. The footnote note about them was absorbed here.
- **Ref 10** (Bhattacharya & Bhattacharyya RDF): author names added
- **Ref 11** (Gardner 1970): page range + DOI
- **Ref 12** (von Neumann 1966): full publisher location
- **Ref 13** (Kung & Leiserson): was "verify exact venue/year" — now full:
  Sparse Matrix Proceedings 1978 (SIAM), pp.256–282; Mead-Conway alternate noted
- **Ref 14** (WordPress Playground): "et al." removed (sole creator Zieliński);
  GitHub URL + State of the Word Nov 2022 first presentation added
- **Ref 15** (Codapi / Zhiyanov): year 2023, URLs, first public release added

"To be completed" header and all "verify" annotations removed.
Manual rebuilt cleanly at 6169304, 13 sections.

---

## SensorTrix (commit c3a4759)

### Suites: 53/53 sensortrix (NEW), 252/252 fp_tiles (+10 auto-coverage)

Core insight landed in code: every physical sensor is (location, amount).
A sensor stack is N readings on N consecutive bus addresses — one stream,
one format, one bridge. Robotics 101.

**FormatDefinition** (`cell_format.py`):
- `SensorTrix` — bits 31-16 = amount, bits 15-0 = location
- `pack/unpack/pack_stack/unpack_stack` helpers
- `boundary_in = SENSOR_UNPACK`, `boundary_out = None` (source-only)
- Covers: touch, IMU, mic array, motor encoders, sonar, tactile skin,
  any N-channel ADC. Same format for all.

**Five real tiles, all within 900c budget** (`fp_tiles.py`):

| Tile | Cells | Depth | Job |
|---|---|---|---|
| SENSOR_UNPACK | 144c | d5 | split word → location + amount (parallel paths) |
| SENSOR_THRESHOLD | 518c | d14 | amount ≥ preloaded T → 1-bit fire |
| SENSOR_DELTA | 517c | d12 | current − preloaded prev (velocity, rate) |
| SENSOR_STACK_MAX | 317c | d66 | peak across two readings (binary tree) |
| SENSOR_STACK_SUM | 482c | d10 | sum step for mean filter (binary tree) |

**Runner** (`sensortrix_runner.py`): three sensor stack demos
- Touch array: 5-finger pressure, peak=31000, 2 contacts, total=44300
- IMU 6-DOF: ax/ay/az/gx/gy/gz, peak=32200 (az, gravity dominant)
- Motor arm: 6-joint encoder, velocity via SENSOR_DELTA, peak=200c/tick

**Community**: `community/sensortrix/` — format.py, README.md, MANIFEST.json,
3 model stubs (touch_array, imu_6dof, motor_arm)

**Sketches**: `sketches/touchtrix_sketch.py` and `visiontrix_sketch.py`
- Touch unpack + pressure detect comfortably fits 900c
- Full Sobel 3×3 is 8334c (9× budget) — temporal blocking is the path
- VisionTrix pixel-level tiles (PIXEL_DELTA 517c, PIXEL_THRESHOLD 518c)
  fit and feed directly into NeuroTrix as spatial LIF drive

### SensorBridge (not yet built)
Thin extension of MouseBridge: background thread packs (location, amount)
from host device → queue → bus word each tick. One loop over N sensors for
a stack. Device-specific details (HID touch, I2C IMU, SPI ADC) stay in the
bridge; fabric sees only the stream.

### What sensor stacks mean for the architecture
The SENSOR_STACK_MAX / SENSOR_STACK_SUM tree reduction is the fabric
doing the aggregation that would normally be a CPU loop — and doing it
in parallel at the binary tree depth, not sequentially. For a 16-element
tactile array: 15 tiles, d264 total (4 levels × d66). That's the
parallelism the architecture was designed for.

---

## CERN-OHL-P licence fix (commit db42d2a)

Verbatim official text now in LICENSE-HARDWARE. Text sourced directly
from CERN (user-provided 2026-06-14). Removed the "in case of discrepancy,
official text governs" disclaimer — no longer needed. Project scope section
retained below the separator.

PLAN.md release checklist: verbatim CERN-OHL-P item ticked.

**Open source release checklist — all software-side items now complete:**
- [x] MUX selector bug fixed
- [x] Comparison operators fixed
- [x] Multi-param compiler bug fixed
- [x] MUL preloaded_a bug fixed
- [x] 157/157 compiler tests
- [x] 252/252 tile tests
- [x] 31/31 silicon tests
- [x] Docs consistent and correct (INDEX, TRIX_ECOSYSTEM, LIBRARY updated)
- [x] README with getting-started path
- [x] MIT licence (software)
- [x] CERN-OHL-P v2 (hardware) — verbatim text
- [ ] Arria 10 working and stable  ← sole remaining gate
- [ ] 1D Laplacian on real Arria 10 hardware

Release goes the moment the card enumerates.

---

## Session summary — 2026-06-14

Full day's work from a clean PLAN.md review. Everything pushed, all
suites green.

**Commits this session:**
- 169b842  Community: BioTrix/ChemTrix/PhysTrix worked example models (175/175)
- 8637b2c  Docs: update INDEX, TRIX_ECOSYSTEM, LIBRARY to current state
- 3b87503  Docs: rebuild manual.html
- c4fe59f  Paper: complete all 15 references with full verified citations
- 6169304  Docs: rebuild manual.html (paper references complete)
- c3a4759  SensorTrix: unified (location, amount) sensor format + tiles + runner
- a440699  Sessions: SensorTrix entry + manual rebuild
- db42d2a  Licence: replace reproduced CERN-OHL-P body with verbatim official text

**Test suite totals at end of session:**
- 252/252 fp_tiles (was 242 — +10 from SensorTrix auto-coverage)
- 157/157 compiler_int32
- 53/53  sensortrix (NEW)
- 175/175 community_models (NEW)
- 29/29  walker
- 27/27  flowtrix
- 19/19  miditrix
- 14/14  community_raw
- 31/31  silicon (iCEBreaker, hardware)

**Key work done:**
1. Confirmed all pre-hardware items from PLAN.md were already complete
2. BioTrix/ChemTrix/PhysTrix: 11 worked example models across 3 domains
3. Doc pass: INDEX, TRIX_ECOSYSTEM (complete rewrite), LIBRARY, manual rebuilt
4. Paper: all 15 references resolved to full verified citations including
   the Dennis & Misunas (1975) dataflow primary (was a blank placeholder)
5. SensorTrix: every physical sensor is (location, amount); a sensor stack
   is N readings on N consecutive bus addresses — one stream, one format,
   one bridge. 5 tiles all within 900c budget. Touch, IMU, motor arm demos.
6. CERN-OHL-P verbatim licence text — last software-side release gate cleared

**Hardware status (unchanged):**
Waveshare USB Blaster V2 + JST SH 1.0mm paid 26th May, in transit.
First test on arrival: jtagconfig → IDCODE on the GX660.
Predicted tick figures to validate on silicon:
  LBM collide:  1,714 ticks/update (MIF_RECIP-optimised)
  LIF tick:       353 ticks/update
