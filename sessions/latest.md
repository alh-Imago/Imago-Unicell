# Session Summary — 2026-04-28
## The v2 Realisation and Full Implementation

---

### THE MOMENT OF REALISATION

During sentry cell analysis it was discovered that the 9-gate NOR tree
was effectively only one gate deep. The wired-OR bus combined inputs
BEFORE they reached the tree -- gates g1-g8 were unreachable.
The cell was just NOT or PASS.

**Fix: edge separation.**
A arrives on rising edge (posedge), B on falling edge (negedge).
Both reach the tree as distinct signals. Full tree reachable.

**Verified: all 12 logic functions in a single cell, single tick.**

```
GS_PASS_B  0b000000000    GS_NOT_B   0b000000001
GS_NOR     0b000000100    GS_AND     0b000000111
GS_NOT_A   0b000001110    GS_OR      0b000100100
GS_NAND    0b000100111    GS_PASS_A  0b000101100
GS_ZERO    0b000110000    GS_XNOR    0b000111100
GS_ONE     0b010110000    GS_XOR     0b010111100
```

---

### CELL COST REDUCTIONS

| Op | v1 cells | v2 cells |
|----|----------|----------|
| AND | 5 | 1 |
| OR | 3 | 1 |
| XOR | 9 | 1 |
| XNOR | 10 | 1 |
| INT32_ADD | 6,227 | 548 (Kogge-Stone) |
| INT32_EQ | 763 | 63 |
| INT32_MUX | 544 | 128 |

---

### WHAT WAS BUILT

**New v2 foundation (imago_v2/):**
- unicell_v2.py, gate_states_v2.py, unicell_array_v2.py
- ir_v2.py (Kogge-Stone 32-bit adder: 548 cells, depth 12)
- compiler_v2.py, controller_v2.py, fp_tiles_v2.py
- unicell_v2.v (Verilog: posedge A / negedge B)
- test_unicell_v2.py (137 tests)

**v1 migration (Imago-Unicell/):**
- unicell.py -- receive_a/b, _execute_nor_gates_v2, input_b_address
- unicell_array.py -- input_map_b for B delivery
- controller.py -- CellMapRecord.input_b_address
- gate_states.py -- GS_AND_V2, GS_OR_V2, GS_XOR_V2 etc
- ir.py -- lower_to_cell_map_v2()
- branch.py -- XNOR+AND(1) comparator (6 cells, was 12)
- compiler.py -- uses lower_to_cell_map_v2()
- program_builder.py -- input_b_address preserved
- program_image.py -- to_dict/from_dict includes inB
- workbench.py -- v2-aware gate_details and array_snapshot
- model_library.py -- all models updated with v2 figures
- fp_tiles.py -- SentryPrimitive 5 cells, to/from_cell_word
- shore_v2.py -- view_mask, lean index, query_by_ptt_word
- fs_search.py -- KeyNormaliser, CollectionTable, CollectionIndex
- pond_ptt.py -- to/from_cell_word, STATUS_IDLE_WARNING

**ECC:** stubbed, 39-bit bus format locked (32 data + 7 reserved)

**FPGA:** TinyFPGA BX target added (top_tinyfpga_bx.v, pcf, build script)

**Docs:**
- docs/architecture_positioning.md
  - UniCell vs neuromorphic (Loihi 2, TrueNorth, Akida)
  - Silicon scaling table (130nm to 3nm 3D)
  - Throughput: 1 quadrillion ops/second at 3nm 3D
  - 12 use case scenarios
  - Tiny Tapeout 130nm pathway
- docs/lif_neuron_reference.v (Grok LIF Verilog, April 2026)
- MIGRATION_TODO.md (6 tiers, full migration path)
- SESSION_START.md (this system)
- sessions/ (daily summaries)

**Git:** v2.0 and v2.1 tagged, PAT configured, direct push working.

---

### TEST STATUS

2,633+ tests, zero failures.

- test_unicell_v2.py:      137 tests
- test_branch.py:           61 tests
- test_compiler.py:         35 tests
- test_for_loop.py:         21 tests
- test_while.py:            27 tests
- test_program_builder.py:  28 tests
- test_program_image.py:    66 tests

---

### KEY ARCHITECTURAL DECISIONS THIS SESSION

1. Edge separation: A=posedge, B=negedge. The founding fix.
2. OR lowering: depth-align with PASS pads, then GS_OR|GS_SYNC_WAIT.
3. Constant injection: const_0/1 registered in imap, auto-injected.
4. ECC reserved: 7 bits, format locked, passthrough stubs.
5. Branch comparator: XNOR+AND(1) extracts clean bit from 32-bit result.
6. program_builder._reassign_addresses: preserves all v2 fields.
7. Verilog portability: standard RTL only, board files are the only change.

---

### NOTABLE CONVERSATIONS

- LIF neuron: ~6-8 cells per neuron in v2 (was 40-50 in v1)
  iCEBreaker: 6-8 neurons. 3nm card: 60-80M neurons.

- Windowed GUI: session = pond tree, window = display pond,
  minimise = view_mask 0. Citrix/VDI from pond primitives naturally.

- LLVM portability: llvm_ir_mapper.py already started.
  C/C++/Rust/Swift -> LLVM IR -> cell map. No new programming model.

- Throughput framing: 50MHz × 40,000 cells = 2 trillion ops/second.
  Not instructions/second -- simultaneous cell firings per tick.

- Tiny Tapeout: 130nm group tapeout, ~£300/tile, 40,000 cells.
  Bridge between iCEBreaker proof and custom silicon.

- The portability story: same .icm files, VM to iCEBreaker to ASIC.
  Programs written today run on silicon that does not exist yet.

---

### PENDING (priority order)

1. iCEBreaker arrives -- run bring-up sequence
   LED blink -> UART -> NOT gate -> AND -> bridge -> scale

2. Verilog completeness:
   unicell_v2.v missing: GS_LATCH_IN, GS_SELECT, GS_LOOP_BACK, GS_BROADCAST

3. Tier 2 OS migration:
   compiler_int32.py, fp_tiles.py, llvm_ir_mapper.py

4. Tier 5 VM package:
   Standalone install, getting started guide, example programs

5. Tier 6 Documentation:
   README rewrite, vision section, neural sim guide, LLVM portability

---

### ARCHITECTURE QUICK REFERENCE

**The cell:**
```
posedge: A -> input_latch_a
negedge: B -> gate tree: execute_nor_tree(gs, A, B) -> output
```

**Key flags:**
- GS_LATCH_IN (bit 25): hold A between cycles
- GS_SYNC_WAIT (bit 15): wait for both A and B
- LOOP_MODE (bit 10): stay armed after firing
- GS_SELECT (bit 9): conditional router
- GS_FALL_EDGE (bit 24): output on negedge

**Bus packet:** 39 bits (32 data + 7 ECC reserved, always 0)

**Kogge-Stone 32-bit adder:** 548 cells, depth 12
(v1 CLA was 6,227 cells, depth 58)

---
Session end. Next session: pull repo, read MIGRATION_TODO.md, confirm tests.
