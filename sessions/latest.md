# Session Log — 2026-06-09 (format system, frontends, licence)

## Final commit: 0c70987
## Suites: 157/157 compiler_int32, 236/236 fp_tiles, 31/31 silicon
## Previous session archived: sessions/archive-2026-06-08.md

---

## The arc of this session

Started from "could we generalise the MIF pattern?" and ended with a complete
format-typed symbolic computation system, three frontends, a community space,
and a dual licence. 20 commits. All non-hardware open items closed.

---

## MIF LUT optimisation (commit 1ce3b15)
LUT initial guess for Newton-Raphson in MIF_DIV / MIF_SQRT.
16-entry table indexed by top 4 mantissa bits → ~8-bit accurate start
→ 2 NR iterations instead of 3. Fits preloaded-A pattern (constants in cells,
4-bit MUX tree selects). Results:
  MIF_DIV  low_latency: depth 633 → 536  (-15%)
  MIF_SQRT low_latency: depth 900 → 584  (-35%, 28% fewer cells)
  cell_budget variants unchanged (4789c/5317c depth 1177)

## Format definition system — cell_format.py (commits b788699, d3eff7e, c04ae30)
MIF was always a "format definition" — named and generalised the pattern.
FormatDefinition base class: name, domain, bits_per_symbol, symbols_per_word,
cell_words, boundary_in/out, valid_tiles, symbol_lut, CONSTANTS, constraints,
produces/consumes. Methods: validate_tile, encode/decode, capacity.

9 formats across 6 domains:
  MathTrix: MIF
  BioTrix:  DNA_4Base, RNA_4Base, Amino20
  ChemTrix: Chemistry_Element (full periodic table, molecular groups 128-255)
  PhysTrix: SI_Physics (17 CODATA 2018 constants)
  FinTrix:  Finance_Currency
  General:  BCD_Decimal, FixedPoint_Q8_24
FormatRegistry singleton: get/list/domains/register_class.
docs/FORMAT_DEFINITION_GUIDE.md — contract-first design (format BEFORE tiles).
Key insight: physical constants are preloaded-A cells; address=identity;
reconfigure=one transaction, no recompile.

## Bridge system + semantic contract (commits c77e58e, bcbded9, 112a9a5,
##   335cf9a, 02dcf80)
BridgeContract class: source/target format+context, formula, constants_used,
output_dimension, semantic_confidence (0.0-1.0), compiler_policy.
semantic_confidence encodes ONTOLOGICAL DEPTH:
  1.0 discovered (law of nature) · 0.8 established · 0.5 model ·
  0.2 speculative · 0.0 no connection.
9 fundamental bridges (physics + biology + chemistry).
Hawking bridge: T=ℏc³/8πGMkB, confidence 1.0 — "a cup of spilt tea and the
edge of a black hole, connected by a bridge tile made of NOR gates" (paper line).
Context stricter than units: thermal_quantum ≠ bulk_fluid.

discover_bridges() — DECLARATION-GROUNDED. Validates against format
produces/consumes dicts and CONSTANTS, not guesses. A bridge is invalid unless
both formats declare the data exists. Finance→DNA correctly returns no connection.
"No guesses, no hope" — the format definition is the proof of what's available.

## Typed neural — TYPED_LIF_MIF (commit 3c18698)
Insight: applying bridge contract to data before it enters a region full of
LIF neurons gives a "typed neural". Membrane/weight/decay/threshold all MIF
pairs, bridge contract at boundary, preloaded-A weights, training = reconfigure
preload cells (no backprop through fabric, no recompile).
Naming care: avoided LIF_MIF (collision), used TYPED_LIF_MIF.
Existing lif_neuron.icm / lif_cascade.icm left unchanged.
docs/TYPED_NEURAL.md — explicit: not AGI, not backprop, not biological.

## Universal symbolic substrate (commit d393f8c)
Paper Section 10d: works for ANY symbolically-describable domain.
PoliticsTrix demonstration (community/politicstrix/): influence→PageRank
conf 0.6, →SI_Physics conf 0.0 (correctly rejected).
"You can connect anything. You must be clear and upfront about what you are
actually claiming."

## Three frontends + hashed ICM (commits 1300d69, 04cb06a, 77daca9, 7c48aae)
Tier 1 Composer — cell/tile level, standalone (existing).
Tier 2 MathTrix frontend (frontend/mathtrix_frontend.html) — rule/model level.
  Blank template: frontend/trix_template.html (replace {{TRIX_NAME}}/
  {{DOMAIN_COLOUR}}, define INITIAL_RULES, implement runRuleDomain). New domain
  frontend in 30 min. Rule = data contract (format/context/reads/update/
  constants/tiles/params/tags).
Tier 3 Region Connector (composer/region_connector.html) — pipeline level,
  bridge selection with confidence. Pipeline validation (cycle/orphan/context
  mismatch/low-confidence), custom bridge creation, tooltips, shortcuts.
Hashed ICM export across all three — canonical form
  canonR(records)=JSON.stringify(recs.map(r=>({gs,in,[init,]out}))), SHA-256.
  Python equivalents in unicell_server.py: canon_r/icm_hash/verify_icm/sign_icm.
  /api/export_icm/<job_id>, /api/verify_icm, /api/bridges. Tamper detection
  verified.

## Community space (commits 112109f, 1d83831)
community/ folder: README.md (contributor guide), community_tools.py
  (validate/hash/register/search/new — SHA-256 over .py/.json/.md).
Reference folders: mathtrix/biotrix/chemtrix/phystrix/fintrix/general +
  politicstrix, each with format.py + MANIFEST.json + models/ + README.md.
mathtrix/models/ has all 10 system models as JSON.
community/REGISTRY.md auto-generated. 7 contributions.

## PLAN cleanup + open items (commit 5f0ae0f)
PLAN.md rewritten (was 2026-06-04, now accurate).
compiler_int32.py: Bug#1 MUL preloaded_a normalisation (raw 0/1 → expand to
  0x00000000/0xFFFFFFFF); Bug#2 multi-param re-injection (all params to both
  a_vals AND b_vals). Tests 140 → 157 (7 multi-param + 10 load/run API).
command_interface.py: PRELOAD_NONE/ZERO/ONES → PRELOAD_SEL_* (legacy aliases).
docs/RUNNING.md + ICM_FORMAT.md: inB references removed.
README.md: Gray-Scott GIF added (docs/figures/).

## Dual licence (commit 0c70987)
LICENSE — MIT (all software).
LICENSE-HARDWARE — CERN-OHL-P v2 (Verilog RTL, cell architecture, gateway).
NOTICE — explains the split. SPDX headers on all 16 hardware files.
README licence section. Both permissive, attribution-only.
Copyright (c) 2026 Imago UniCell Project.
TODO before public release: pull verbatim official CERN-OHL-P text from
  ohwr.org/cern_ohl_p_v2.txt to replace the reproduction (official text governs).

---

## Hardware status (unchanged — gated)
Arria 10 GX660 (Mustang-F100): PCIe alive, onboard FTDI USB faulty.
DIAGNOSIS REFINED this session:
  - Card draws <60W (IEI spec). 550W bench PSU is huge headroom — power
    starvation now UNLIKELY.
  - Slot power is OPTIONAL per IEI spec ("preserved for user in case of
    different system configuration"). Card runs on 6-pin alone — no powered
    riser needed for isolated bench test.
  - Display showing ZERO is the card-ID (DIP switch), not a fault code.
    Two green LEDs + ID display = board alive, FPGA powered. Not a dead card.
  - Most likely faults: flaky onboard FTDI, or bad bitstream in flash.
    Both recoverable via JTAG reflash. IEI sells the download cable as a
    standard accessory — reflash is the normal expected path.
Shopping list (paid 26th): Waveshare USB Blaster V2 £32 + JST SH 1.0mm £14.
FIRST TEST WHEN CABLE ARRIVES: jtagconfig → read IDCODE on the 660.
  Clean read = JTAG chain + FPGA core alive, card recoverable.

## Staged card plan
660 = proving card (first bring-up, shift_in_en, scale test).
Then ~£100 early for Arria 10 1150 = clean performance card + rig seed.
Working 660 → goes to son (dials in remotely; becomes his once it
  enumerates in Linux).

---

## Remaining (non-hardware)
- Compiler auto-placement of bridge tiles
- Design-time confidence-threshold warning enforcement
- SI_CHECK dimensional analysis integration
- Bridge section in community guide
- DisplayPond hosted flag (GPU passthrough)
- BioTrix/ChemTrix/PhysTrix community models

## Hardware-gated (waiting on cable)
- Arria 10 first bitstream, shift_in_en validation, scale test
- Packed adder tile, MUL rewrite, Wallace tree MUL
- Fabric fire visualiser, SYNC_WAIT hardware test

## Future papers identified (5-6)
Architecture · Format Definition System · Semantic Contract · Typed Neural ·
Community Architecture · (possibly preloaded-A constant injection)
