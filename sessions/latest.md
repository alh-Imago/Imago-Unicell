# Session Log — 2026-06-16/17 (concept graph + inference engine)

## Hardware news
USB Blaster V2 cable arrived. Arria 10 bring-up begins tomorrow.

---

## Nature of this session

Two-day session covering two distinct threads:

**Thread 1 (2026-06-16):** Pre-hardware software completion — all
non-hardware open items from PLAN.md ticked. Bridge system, compiler
enforcement, SI_CHECK, community docs, auto-placement.

**Thread 2 (2026-06-16/17):** Concept graph / knowledge holes work —
a new research direction emerging from the bridge system. Papers
structure created, concept graph built, visualisations, inference engine.

---

## Thread 1 commits (pre-hardware completion)

- fce404d  Region Connector: Bridge UI → cell_format.py round-trip
- ad955cb  Compiler: design-time bridge confidence enforcement + tests
- 9e2fbc1  SI_CHECK: dimensional analysis integration
- 7609b08  Docs: community bridge guide updated
- 733b95d  Compiler: auto-placement of bridge tiles from pipeline .icm
- 290a5e0  Sessions + PLAN.md cleanup
- 427f962  Docs: TRIX_ECOSYSTEM + FORMAT_DEFINITION_GUIDE + manual rebuilt
- 35050a5  papers/ folder structure created
- e8effa7  PAPERS.md — 7 papers tracked

All non-hardware open items now complete. Every remaining PLAN.md item
is hardware-gated (Arria 10 bring-up, shift_in_en, packed adder).

---

## Thread 2 commits (concept graph)

- 210485c  cell_format: ConceptDeclaration + CONVERSION_MECHANISMS
- bdb3163  papers/paper_bridges: morning thinking session notes
- 53ca9e9  Onion README: wrapper as core invention
- d10550c  NATIVE_FS.md: native filesystem design document
- 59587cd  papers/paper_substrate: making ignorance visible thesis
- 54c6e1d  papers/paper_bridges: E=mc² hub nodes + multidimensional data
- 17fce9e  Concept graph: base table builder (physics seed)
- 4084c75  Concept graph: 3D explorer builder
- e0b2a89  Concept graph: chemistry + cross-domain matching
- 633214a  Concept graph: equation expansion + visualiser improvements
- 5af1986  Bridge visualiser: hub gaps tab + equation placement
- 7ed42af  Genomics isolation as key result
- 3fa457a  papers/paper_bridges: complete state snapshot
- 82f25b1  Bridge inference engine: Dijkstra path finder
- b427d59  Architecture notes: SQL streaming + card-gated items

---

## Concept graph — current state

Database: 203 concepts, 164 equations, 1261 connections
Variables: 153 across 22 domains
Source coverage: ~35-40% of Wikipedia equation pages

Top hub concepts:
  displacement:  14 domains, 103 equations
  mass:          10 domains, 91 equations
  velocity:       8 domains, 76 equations
  temperature:    5 domains, 64 equations (should be 8+)

Key findings:
  250 undeclared cross-domain bridges (amber gaps)
  156 hub concept cross-domain gaps (assumed not declared)
  Genomics almost completely isolated (1 declared bridge)

---

## Inference engine (concept_inference.py)

Modified Dijkstra maximising confidence product:
  edge weight = -log(confidence)
  same as map routing optimising time not distance

Verified results:
  temperature → thermal_energy:   GREEN 1.0 (Q=mcΔT)
  mass → kinetic_energy:          GREEN 1.0 (KE=½mv²)
  frequency → photon_energy:      GREEN 1.0 (E=hf)
  temperature → reaction_rate:    GREEN 1.0 (Arrhenius)
  mass → hawking_temperature:     AMBER 1.0 2-hop
  melting_temperature → KE:       RED (Genomics gap)
  base_count → thermal_energy:    RED (Genomics gap)

RED results return gap_shape with dimensional constraints —
engine points at what a bridge would need to look like.
(melting_temp→KE gap: K→J conversion = Boltzmann kB. Undeclared.)

---

## Philosophical observations (captured)

"The cell structure forces me and you to invent things just to keep up.
It is starting to say: keep up."

The architecture isn't passive. It pulls you forward.
Each constraint propagates outward to the user.
The compiler demands precision. The precision reveals gaps.
The gaps demand new mechanisms. The mechanisms extend the graph.

Honesty and accountability are structural, not imposed.
A NOR gate doesn't negotiate. A bus doesn't approximate.
The system can't be dishonest — and it demands the same
of everything that touches it.

Paper introduction paragraph: state this before the equations.
Before the results. Why it was built this way.

---

## Papers structure

papers/
  PAPERS.md              — 7 papers tracked
  paper_bridges/         — most active (inference engine, gap analysis)
    README.md            — full state summary
    notes.md             — design notes, key insights
    bridge_visualiser.html
    concept_graph_explorer.html
    data/
      concept_graph.db
      build_tables.py
      build_static_explorer.py
      cross_domain.py
      concept_inference.py
      hub_gaps.json
      cross_domain_matches.json
  paper_substrate/
    notes.md             — "making ignorance visible" thesis

---

## Tomorrow (hardware day)

Cable arrived. USB Blaster V2 + JST connector confirmed.

Sequence:
  1. jtagconfig — IDCODE on GX660
  2. First bitstream — single cell loopback
  3. shift_in_en validation
  4. Packed adder → 25× INT32 cost reduction
  5. FlowTrix hardware run → MLUPS/watt
  6. Predicted vs measured tick validation
     LBM: 1,714 ticks/update
     LIF: 353 ticks/update

Open source release gate: Arria 10 working demo.

---

## Test suite totals (end of session)

All prior suites unchanged. New:
  43/43   pipeline_bridge_check + pipeline_compile
  16/16   (bridge check subset)
  22/22   (compile subset)

Concept graph inference engine: 10/10 demo queries correct
  7 GREEN/AMBER (paths found)
  3 RED (Genomics gaps correctly identified)

---

# Session Log — 2026-06-21 (shift primitive: first ISSP config + inject attempt)

## Nature of this session
Designed and ran the first nibble shift_in_en validation on the Arria 10 over
JTAG/ISSP, built on a reusable ICM loader. Deep-read the v2.3 Verilog as ground
truth and caught two pre-hardware landmines before they reached the card.

## Deliverables (placed in repo)
- `imago/examples/shift_pass.icm`  — single PASS cell, in=0x100 out=0x200.
- `fpga/issp_loader.py`            — reusable ICM→v2.3 command-stream expander;
  uses command_interface.build_cmd_bus as the single source of truth.
- `fpga/shift_primitive.tcl`       — quartus_stp harness on the uc_* primitives.

## Two landmines caught (Verilog ground-truth verification)
1. **Stale RECONFIGURE encoding.** v2.3 cmd_data is a COMPACT payload
   (start_flag at cmd_data[11], auth_mask at cmd_data[30:23]) — NOT the cmd_latch
   register layout. The old UART mk_cfg put start_flag at bit 22, so on v2.3
   silicon the cell would configure but never arm. Corrected PASS-armed payload:
   0x52800800. **CONFIRMED on silicon this session (see below).**
2. **Arria 10 inject packs one word.** top_arria10.v line 61: a DATA_WRITE has
   bus_addr=cpu_data[31:16], bus_data=cpu_data(full), shift_nibbles=cpu_data[3:0].
   Address, value and shift count share the single cpu_data word. Test words must
   be shaped 0xADDR_yyyN. Independent 32-bit operands (needed for the adder) will
   require a wider ISSP source or a two-transaction inject — design decision banked.

## Hardware result (Arria 10, USB-Blaster, JTAG IDCODE 0x02E250DD)
- Channel-alive: PASS (cycle advanced ~6.7M ticks — read path + fabric clock live).
- Write-path auth-reset: OK.
- **Config + arm: PASS — `armed 448`.** All 448 cells configured and armed.
  This directly VALIDATES landmine-1's corrected RECONFIGURE encoding on silicon
  (the stale encoding would have shown armed 0).
- **Inject → fire: FAIL — out_count 0, out_seen 0, out_data 0** on all vectors
  incl. control. bus_hit never asserted (a counter, so 0 = genuinely no fire).

## Diagnosis (bus_hit never asserted)
bus_hit = !frozen && start_flag && output_set && bus_valid_r && !cmd_valid && addr_match.
start_flag is proven (armed). So the failure is one of: output_set not set,
addr_match false (bus_addr routing), or the inject not pulsing bus_valid over ISSP.
Data injection causing a fire over ISSP is the unproven frontier — prior validated
ISSP ops were broadcast commands/probes only.

## Next session (ranked)
1. Switch to the PROVEN iCEBreaker firing pattern: preload a_data via preload_sel
   (sets a_arrived) + a SINGLE shifted trigger on a PASS_B cell (output=B). Removes
   the two-self-stored-arrivals assumption entirely. (Harness v2 prepared.)
2. Issue SET_OUTPUT_ADDR AFTER RECONFIGURE and read back to confirm output_set.
3. If a plain no-shift inject still gives out_count 0, the data-bus inject path
   over ISSP (cpu_addr routing / bus_valid pulse) is the gap — inspect the issp
   bridge's data path vs top_arria10 cpu_addr mux.
4. Fix uc_read to return the out_data field only (harness compared full status line).

---

# Session Log — 2026-06-22 (root cause: host inject dropped in the zone)

## Result of shift_primitive_v2.tcl on silicon
Config + arm still good (armed 448). Diagnostic A (plain inject, no shift) gave
out_count 0 — so the gap is the data-bus inject path itself, not the shift and
not the config. This isolated the problem precisely.

## Root cause (traced through the zone hierarchy)
top_arria10 instantiates unicell_zone (16 zones), not the flat unicell_array.
- unicell_array expects the host to drive its data bus via cpu_valid, and raises
  a real arrival on (cpu_valid && cmd_code==1).
- unicell_zone wraps the array but wires the array's cpu_valid to the zone's
  INTERNAL ibus_valid, which is assembled ONLY from za_out (own cell feedback)
  and the N/S/E/W inter-zone bridges. The host's cpu_valid enters the zone as a
  port and is never used.
=> Commands reach cells via a separate registered path (cmd_valid_r) so the
   fabric arms, but a host DATA_WRITE has no path onto the cell bus. An armed
   fabric could never be seeded. Every out_count 0 was this.

## Fix (unicell_zone.v — REQUIRES Quartus recompile + reprogram)
Added the host inject as the top-priority source of ibus:
    if (cpu_valid) begin ibus_addr<=cpu_addr; ibus_data<=cpu_data; ibus_valid<=1; end
    else if (za_out_valid) ... (existing feedback) ...
Timing checked: cmd_bus_r and ibus_valid register on the same edge, so the inner
array sees cpu_valid && cmd_code==1 aligned and raises bus_valid.
STATUS: untested on silicon — pending rebuild. After reflash, shift_primitive_v2
Diagnostic A should move out_count with out_data=0x01002340, then B shows <<4.

## Banked for multi-cell (NOT fixed here)
Feedback/bridge arrivals feed the cell its address via external cpu_addr, not
ibus_addr — so cell-to-cell chaining across the fabric routes to the wrong
address. Needs care because cpu_addr is also the command-targeting input for
SET_INPUT_ADDR/SET_LOGICAL. Fix before the multi-cell / adder steps.
