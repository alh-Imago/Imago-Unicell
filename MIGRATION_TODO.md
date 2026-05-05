# Claudette Migration TODO
# Things to update as the system matures toward full silicon honesty.
# Check off as completed. Grouped by priority.

---

## TIER 1 — After iCEBreaker bring-up confirms v2 architecture

These wait for silicon validation. Once unicell_v2.v is proven on hardware,
retire the v1 compatibility layer.

- [ ] Retire `unicell.py` v1 compat shim
      Replace with unicell_v2.py as the sole cell implementation.
      All OS code currently importing unicell.py needs updating.

- [ ] Retire `unicell_array.py` v1 array
      Replace with unicell_array_v2.py two-phase tick.
      The v1 single-phase tick is no longer architecturally honest.

- [ ] Retire `_execute_nor_gates(value)` single-input method
      Never called in v2 path. Remove once v1 unicell.py is retired.

- [ ] Retire `_sync_buf` mechanism in unicell.py
      Replaced by input_b_address + receive_b().
      Remove once v1 unicell.py is retired.

- [ ] Retire `GS_AND`, `GS_OR`, `GS_XOR` as string composites in gate_states.py
      These were never real gate states, just compiler hints.
      Replaced by GS_AND_V2, GS_OR_V2 etc (verified bit patterns).

- [ ] Retire `lower_to_cell_map()` v1 function in ir.py
      Multi-cell NOR chains no longer needed.
      Keep `lower_to_cell_map_v2()` only.

- [ ] Retire `NORBuilder` and `_emit2` in fp_tiles.py
      Multi-cell binary op builders. All replaced by v2 single cells.

- [ ] Retire `pad_to_depth` in ir.py v1 lowering
      Depth equalisation now handled in lower_to_cell_map_v2 OR path.

---

## TIER 2 — OS layer migration (pond, ward, companion, shore)

These files still build on v1 assumptions and need updating to
use v2 cell model directly.

- [ ] `pond.py` -- bridge anomaly_threshold/stall_threshold should come
      from pond type spec not mutable per-bridge instance.

- [ ] `compiler_int32.py` -- uses v1 multi-cell CLA adder.
      Replace with lower_to_cell_map_v2 Kogge-Stone adder.

- [ ] `compiler.py` TILE_FUNCTION_MAP -- remove 'int32_add_cla' entry.
      v2 has only INT32_ADD (Kogge-Stone). CLA variant retired.

- [ ] `fp_tiles.py` -- all INT32/FP32 tiles still use v1 NORBuilder.
      Replace with fp_tiles_v2.py implementations.
      Migration: _build_int32_add -> v2 KS adder, etc.

- [ ] `fp_tiles_v2.py` -- FP32 tiles not yet rebuilt.
      FP32_ADD: estimate 3,000 cells (was 36,540).
      FP32_MUL: estimate 35,000 cells (was 397,740).
      Need proper v2 implementation.

- [ ] `llvm_ir_mapper.py` -- uses v1 gate states and cell model.
      Update to use lower_to_cell_map_v2.

- [ ] `sequencer.py` -- composite gate state strings (v1).
      Update to use v2 integer gate states.

- [ ] `pipeline_queue.py` -- uses v1 cell model.

- [ ] `multi_dimm.py` -- uses v1 cell model.

- [ ] `model_library.py` FP32 entries -- currently estimates.
      Update once FP32 tiles are properly rebuilt in v2.

---

## TIER 3 — Silicon features (deferred to production silicon)

- [ ] ECC -- implement Hamming(39,32) SECDED in silicon.
      Bus packet: 39 bits (32 data + 7 ECC) already locked.
      Encoder: combinational on posedge output driver (~100 LUTs).
      Decoder: combinational on negedge input receiver (~100 LUTs).
      Cost: ~200 LUTs per cell. Flip _ECC_ACTIVE = True in test_ecc.py.

- [ ] Ward as silicon program (~20-30 cells scanning PTT entries).
      Currently Python object. Should be a small cell program loop.

- [ ] PTT cell word comparison in silicon.
      Ward currently compares pipeline_depth in software.
      In silicon: Ward reads PTT cell word, extracts depth field via bus read.

- [ ] Shore table in silicon (resident pond).
      Currently Python dict. Should be a silicon storage pond.

- [ ] Collection tables in silicon (fs_search.py).
      CollectionTable refs currently Python lists.
      In silicon: each collection is a storage pond with Shore entry.

---

## TIER 4 — Architecture refinements

- [ ] OR lowering: confirm depth-aligned SYNC_WAIT is correct for all cases.
      Current implementation: pad shallower input with PASS cells, then
      single-cell GS_OR | GS_SYNC_WAIT. Works but adds pad cells.
      Future: smarter depth tracking to avoid unnecessary pads.

- [ ] Compiler constant injection: const_0/const_1 registered in imap.
      Currently callers must auto-inject from imap. Could be automatic
      in controller.start() for any address with a known initial value.

- [ ] Workbench UI: add input_b_address display, two-input cell indicator.
      Currently in array_snapshot() but may need frontend update.

- [ ] iCEBreaker bring-up sequence:
      1. LED blink (basic FPGA sanity)
      2. UART loopback (bus communication)
      3. 8 cells, NOT gate (single cell v2)
      4. Two-input AND (posedge A, negedge B)
      5. Bridge pair (pond isolation)
      6. Scale to full array

---

## TIER 5 -- VM / Simulator (for users without hardware)

The VM allows anyone to run Imago programs without an iCEBreaker board.
More users = more feedback = better system. This is a first-class deliverable.

- [ ] Standalone VM package
      Single installable Python package (pip install imago-vm or similar).
      No FPGA board required. Runs unicell_array_v2.py in software.
      Target: anyone with Python 3.10+ can try it.

- [ ] VM accuracy mode
      VM should match silicon behaviour exactly for the v2 cell model.
      Two-phase tick (posedge A, negedge B) must be faithful.
      Gate tree results must match unicell_v2.v bit-for-bit.
      Users should get the same results on VM and hardware.

- [ ] VM performance mode
      For large programs: optimise the Python VM for speed.
      Vectorise the gate tree using numpy where possible.
      Armed-set optimisation already exists -- extend it.
      Goal: run useful programs in reasonable time on a laptop.

- [ ] VM web interface (run_companion.py + workbench.py)
      Currently workbench runs as a local HTTP server.
      Package it cleanly so non-developers can launch it with one command.
      Allow loading .icm program images and running them in the VM.

- [ ] VM documentation
      "Getting started" guide: install, write a function, compile, run.
      Examples: AND gate, adder, for loop, conditional.
      Show VM output vs expected silicon output side by side.

- [ ] VM playground / example programs
      A set of working .icm images and source files.
      Users can run them immediately without writing any code.
      Shows off: single-cell AND/OR/XOR, Kogge-Stone adder,
      for loop accumulation, branch comparator.

- [ ] VM feedback channel
      Way for VM users to report bugs, unexpected behaviour, suggestions.
      Could be GitHub issues, a simple form, or a dedicated channel.
      The VM is the feedback loop that improves the silicon design.

- [ ] VM vs silicon diff tool
      When a user has both VM and hardware:
      Run same program on both, compare outputs tick by tick.
      Differences reveal VM inaccuracies or silicon bugs.
      Critical for validating the two-input cell model on real hardware.

---

## TIER 6 -- Documentation rewrites

The architecture has changed significantly from v1. Docs need to reflect
the v2 two-input cell model and the full vision clearly.

- [ ] README.md -- complete rewrite
      Current README reflects v1 architecture.
      Needs to cover:
        - The founding premise: NOR universality, wired-OR bus
        - v2 two-input cell: A=rising edge, B=falling edge
        - Full 9-gate tree: all 12 logic functions in one cell
        - The abstraction stack: workbench -> compiler -> controller -> backend
        - VM vs FPGA: same programs, same results, just faster
        - Getting started: VM (no hardware needed), then FPGA

- [ ] README.md -- Vision section (short, near the top)
      Brief philosophy paragraph -- not a manifesto, just enough.
      The worldview behind "everything is a pond".
      Point at the possibilities without over-claiming.
      Let the reader fill in the rest themselves.
      Examples: robot learning to walk, emergent computation,
      neural ponds alongside OS ponds, the endless possibilities.
      One paragraph. Gets out of the way. Earns its place because
      the architecture actually supports it.
      The original docs had philosophy -- it belonged there.
      It still does.

- [ ] Architecture document
      The "everything is a pond" model.
      Shore table as lean index, view_mask as access control.
      PTT, Ward, ShoreKeeper roles.
      Migration (freeze/copy/move/unfreeze).
      Collection search and heuristics.

- [ ] The portability story -- prominent in README and docs
      "Write once, run anywhere in the family":
        VM (laptop)       -- unlimited cells, software speed, no hardware needed
        iCEBreaker        -- ~64 cells, real silicon, proven architecture
        Larger FPGA       -- thousands of cells, same programs
        Custom ASIC       -- millions of cells, full speed
      Same .icm files on all targets. No rewrite, no porting.
      Programs written today run on silicon that does not exist yet.
      Community can develop massive arrays entirely in the VM --
      almost silicon-ready when hardware catches up.

- [ ] VM getting started guide
      Install Python 3.10+, clone repo, launch workbench.
      Write a function, compile it, run it in the VM.
      Inspect cell states in the browser.
      No hardware required -- full development environment.

- [ ] .icm format specification
      The portable program representation.
      Cell records, address space, input/output maps.
      How to load, run, save, share.
      Board-agnostic by design.

- [ ] FPGA bring-up guide
      For iCEBreaker and TinyFPGA BX.
      Step by step: LED blink -> UART -> 8 cells -> NOT gate ->
      two-input AND -> bridge pair -> scale.
      How to connect fpga_bridge.py as the backend.
      Same workbench, same compiler, FPGA as backend.

- [ ] Verilog spec -- unicell_v2.v completeness
      Document missing mode flags vs Python implementation:
        GS_LATCH_IN  -- hold A between cycles (counter pattern)
        GS_SELECT    -- conditional router (branch comparator)
        GS_LOOP_BACK -- feed output back as next A
        GS_BROADCAST -- fan out to all cells at output address
      These need implementing before full silicon parity.

- [ ] Liquid neuron / adaptive cell cluster
      Document the runtime reconfiguration capability.
      gate_state is a 32-bit value -- another cell can write a new one.
      In v2: 12 meaningful configurations vs 2 in v1 -- richer adaptation.
      Reference Verilog: docs/lif_neuron_reference.v (v1-based, Grok April 2026)
      TODO: port to v2 cell pond implementation (~6-8 cells per neuron).

- [ ] Architecture positioning document (DONE: docs/architecture_positioning.md)
      UniCell vs neuromorphic comparison table (Loihi 2, TrueNorth, Akida).
      The portability story. Neural simulation as one workload among many.
      Expand as architecture matures and real silicon benchmarks available.

- [ ] Neuromorphic / neural simulation guide
      How to build a LIF neuron pond in UniCell v2.
      Show cell layout, gate states, wiring.
      Compare with docs/lif_neuron_reference.v standalone approach.
      Demonstrate: 8 neurons on iCEBreaker, 800+ on mid FPGA.

---

## COMPLETED (for reference)

- [x] v2 gate tree: all 12 functions verified by truth table
- [x] unicell_v2.py: receive_a/receive_b, _execute_nor_gates_v2
- [x] unicell_array_v2.py: two-phase tick
- [x] ir_v2.py: single-cell binary ops, Kogge-Stone 32-bit adder
- [x] compiler_v2.py, controller_v2.py: v2-aware
- [x] fp_tiles_v2.py: INT32 tiles rebuilt (NOT/AND/OR/XOR/EQ/NEQ/MUX/ADD/SUB/LT_U)
- [x] unicell_v2.v: Verilog posedge A / negedge B
- [x] lower_to_cell_map_v2() in ir.py: compiler uses v2 lowering
- [x] branch.py: XNOR+AND(1) comparator (6 cells, was 12)
- [x] ECC stubbed: 7 bits reserved, passthrough stubs, format locked
- [x] model_library.py: all INT32 models updated with v2 figures
- [x] program_builder.py: input_b_address preserved in _reassign_addresses
- [x] program_image.py: to_dict/from_dict includes inB field
- [x] workbench.py: gate_details() and array_snapshot() v2-aware
- [x] Shore view_mask, lean index, query_by_ptt_word
- [x] fs_search.py: KeyNormaliser, CollectionTable, CollectionIndex
- [x] pond_ptt.py: to_cell_word/from_cell_word, STATUS_IDLE_WARNING
- [x] SentryPrimitive: 5 cells, Ward does depth comparison in software
- [x] 2,633+ tests, zero failures


- [ ] Compiler: set GS_OUT_POSEDGE on cells whose output feeds the A (posedge)
      input of the next cell. Cells feeding B (negedge) inputs leave bit 26 clear.
      Currently the bit is defined and parsed but the compiler does not set it.
      Safe default: set GS_OUT_POSEDGE on all cells until per-edge routing is
      implemented — this gives a full half-cycle settling time on every hop,
      at the cost of one extra half-cycle per cell vs. the tight negedge path.
      Location: lower_to_cell_map_v2() in ir.py, fp_tiles_v2.py tile builders.

- [ ] Windowed GUI / virtual desktop environment (Tier 6 doc item)
      Document how session = pond tree, window = display pond,
      minimise = view_mask 0, cascade freeze, live migration.
      Citrix/VDI model emerging from pond primitives naturally.
      No new architecture needed -- already supported.

- [ ] LLVM / open source software portability (Tier 6 doc item)
      Document llvm_ir_mapper.py pathway.
      C/C++/Rust/Swift -> LLVM IR -> cell map.
      Existing software communities, no new programming model needed.

- [ ] Vision: endless possibilities section in docs
      Neural ponds, robots learning to walk, emergent computation,
      windowed sessions, open source portability.
      Brief -- points at possibilities, does not over-claim.
      Lets the reader imagine the rest.
      The philosophy belongs -- the architecture supports it.

- [x] Verilog portability -- ensure transferability across FPGA families and ASIC
      *** COMPLETED 2026-05-12 ***
      unicell-standard/fpga/verilog/unicell.v     -- CLEAN (Verilog-2001)
      unicell-edge/fpga/verilog/unicell.v         -- CLEAN (Verilog-2001)
      unicell-latch/fpga/verilog/unicell_latch.v  -- CLEAN (Verilog-2001)
      All unicell_array.v / uart_bridge.v files   -- CLEAN
      Fix applied: local reg declarations in always @(*) blocks moved to
      module scope for strict Verilog-2001 compliance (was SystemVerilog only).
      BASE_ADDRESS parameter added to unicell-edge/unicell_array.v (was missing).
      unicell_array_latch.v written for latch variant (new, replaces old array
      that incorrectly instantiated unicell instead of unicell_latch).

---
Last updated: Claudette v2.1

---

## LATCH MODEL — unicell-latch/ (new variant, 2026-05-02)

The latch model is forked from Standard (v2.1) and needs the following
to be built out. Work is done inside `unicell-latch/` only.

- [x] `unicell.py`: Added `_input_latch` and `_output_latch` registers.
      tick() fires gate tree on _input_latch → _output_latch.
      drain_output_latch() called by array Phase 1 each tick.
      SYNC_WAIT: v2 (input_b_address) and v1 (_sync_buf) both supported.

- [x] `unicell_array.py`: 3-phase tick loop implemented.
      Phase 1: drain output_latch → fresh bus (no carry, no stale values).
      Phase 2: deliver bus → input latches + B inputs for SYNC_WAIT cells.
      Phase 3: fire cells with input data → output_latch.
      tick_drain() convenience method added.
      run() waits for output latches to drain before completion.

- [x] Tests: All 2,238 tests passing, 0 failures.
      test_helpers.py: CELL_LATENCY=2, chain_latency(n)=n+1 (pipeline formula).
      tick_drain() used throughout, cycle counts updated via chain_latency().
      branch.py load_row() clears _input_latch/_input_b/_output_latch on reload.
      controller.py: pre-run latch cleanup, post-run drain tick.

- [x] `fpga/verilog/unicell_latch.v`: Pure combinatorial gate tree between
      two flip-flop banks (input FF and output FF). Clock controls
      load-enable on each FF bank only. Gate tree has no clock path.
      Written and verified 2026-05-12. 22/22 simulation tests passing.

- [ ] Compiler: `lower_to_cell_map_v2()` needs no special edge bits.
      Depth = chain_latency(n) = n+1 ticks. PASS cells are delay elements.
      Path balancing: insert PASS cells to align parallel paths.

- [ ] Document timing model in `unicell-latch/docs/timing.md`.
---

## FREEZE/MOVE — Output bus capture on migration (2026-05-03)

When a pond freeze-and-move happens, the controller should capture the
output bus state of affected cells (specifically _output_latch for latch
model, _output_buf for edge model) as part of the frozen snapshot.

Why: a cell that has computed a result but not yet driven it to the bus
(result is sitting in the output register) would lose that in-flight
result on a naive freeze. When the pond is restored on a new substrate,
the captured output register content should be pre-loaded so the first
tick after thaw drives that value to the bus — exactly as if the cell
had never moved. The downstream cell sees the correct data on the first
cycle and the pipeline continues without a bubble.

This is a bonus feature for the pond migration system:
  - Freeze: snapshot includes _output_latch (latch) / _output_buf (edge)
  - Move:   output register content travels with the cell state
  - Thaw:   controller pre-loads output register before arming
  - Tick 1: pre-loaded result drives bus, downstream receives immediately

Applies to:
  - unicell-latch:    cell._output_latch  (tuple or None)
  - unicell-edge:     cell._output_buf    (tuple or None)
  - unicell-standard: N/A (immediate output, no output register)

Implementation location:
  - controller.py freeze() / migrate() / restore_snapshot()
  - snapshot() dict should include "output_latch" / "output_buf" key
  - restore_snapshot() should pre-load it before thaw


---

## Composer — Large Model Import (TODO)

**Status:** Parked. Placeholder blocks in composer canvas; excluded from .icm export.

### Problem

Models with >1000 cells (INT32_MUL_DADDA at 23,924; FP32_MULTIPLIER at 35,000;
DISPLAY_OUTPUT at 18,600 etc.) cannot be represented as flat CellMapRecord lists
in a single .icm file and loaded into a standard pond. A 64-cell iCEBreaker array
has no room for a multiply unit at all.

### What needs to happen

1. **Pond-level addressing in the composer**
   The composer needs to know about pond boundaries. A multiply unit needs its
   own dedicated pond with a separate address space. The composer should let the
   designer specify "this model lives in Pond B, connected to Pond A via bridge".

2. **Multi-pond .icm export**
   The .icm format needs a `ponds` section alongside `records`:
   ```json
   {
     "ponds": [
       {"name": "main",     "base": "0x10000", "records": [...]},
       {"name": "multiply", "base": "0x80000", "records": [...], "model": "INT32_MUL_DADDA"}
     ],
     "bridges": [
       {"from": "main.0x1008", "to": "multiply.input_a"}
     ]
   }
   ```

3. **Controller multi-pond load**
   `controller.load_map()` needs to accept a multi-pond image and allocate each
   pond to a separate UniCellArray or array region.

4. **Booth radix-4 rewrite**
   INT32_MUL_BOOTH (109,458 cells) is worse than Dadda because MUX2 encoding
   chains are expensive in NOR-only fabric. The correct implementation uses
   gate_state-level digit selection (the cell's built-in SELECT gate) rather
   than MUX2 trees. Estimated correct cell count: ~8,000–12,000.
   Requires: extending NORBuilder with a SELECT-based digit MUX primitive.

### Current workaround

Large models appear in the composer library as placeholder blocks (amber dashed
border, hatched fill, "⊡" marker). They can be placed on canvas for architectural
sketching but are excluded from .icm export with a warning.

The simulation panel skips placeholder blocks (they have no cell records to tick).



---

## Device & Storage Layer (TODO — Design agreed, implementation pending)

### USB Device Ponds

**Status:** Keyboard and Mouse stubbed in device_bridge.py. Full class driver
layer not yet implemented.

**Design:**
- One Pond per connected device, class driver lives inside the Pond
- Bridge handles Shore registration (device_type stored in parent_pond field)
- Class drivers cover the vast majority of devices:
  - HID (Human Interface)  → every keyboard, mouse, gamepad, tablet
  - MSC (Mass Storage)     → every USB flash drive, SSD, card reader
  - UAC (Audio)            → every USB headset, DAC, microphone
  - CDC (Communications)   → USB serial adapters, some dev boards
  - UVC (Video)            → every webcam, capture card
  - Hub                    → every USB hub
- Vendor-specific devices: unsupported until individual Pond written
- Inward: raw HID/bulk/isochronous data → normalised packet into fabric
- Outward: packet from fabric → control/bulk transfer to hardware
- Enumeration event from AHCI/USB controller feeds device_manager.register()

**Implementation order:** HID first (keyboard/mouse already stubbed), then MSC,
then UAC and CDC as needed. Covers ~80% of devices with 4 drivers.

### SATA Pond Stack

**Status:** Not yet started. Design agreed.

**Stack:**
```
Application Pond
      ↕  file address packets
Filesystem Pond   ← format translation layer
      ↕  sector read/write packets
SATA Pond         ← AHCI block layer (one driver, all drives)
      ↕  AHCI commands
Physical SSD/HDD
```

- SATA Pond: AHCI protocol, one driver covers all spinning rust and SSDs
  Speed negotiation (1.5/3/6 Gbps) handled by AHCI controller hardware
  Presents block device upward: request sector N, receive 512 or 4096 bytes
- Filesystem Pond: format translation sitting above the block layer
  Foreign formats: FAT32, exFAT, NTFS, ext4 (read/write as needed)
  Native format: see below

### Native OS Filesystem (Design agreed)

**Status:** Not yet started. Design agreed.

**Principle:** Separate file identity from file location — conventional filesystems
wrongly bundle these together.

**On-disk layout (flat block pool):**
- No directory tree, no path hierarchy, no inodes in the traditional sense
- Each file: [block address] [metadata header] [data blocks]
- Files can be anywhere on the physical media — location is a physical fact,
  not part of the file's identity

**Heuristic index Pond (in memory / persistent Pond):**
- Holds all file references: logical address → physical block address
- Holds all metadata: tags, type, date, size, author, custom fields
- Query interface: given a mask filter, return matching file addresses
- File identity lives here, not on disk

**Collections:**
- A collection is a saved mask filter only — no physical meaning on disk
- Overlapping collections reference the same physical files, nothing duplicates
- Reorganising = editing mask filters, zero disk movement
- A thousand collections cost nothing on the storage layer

**Benefits over conventional filesystem:**
- Move a file = update one reference in the index, data never moves
- Reorganise = edit mask filters, instant, zero I/O
- Search = query the index Pond, no directory traversal
- The filesystem Pond below doesn't know what a collection is

**Still to design:**
- [ ] Index Pond metadata fields (what fields are indexed by default)
- [ ] Mask filter syntax (how queries are expressed as packets)
- [ ] Consistency model (what happens if media is modified externally)
- [ ] Index persistence (how the index Pond survives a power cycle)
- [ ] Index rebuild (reconstruct index by scanning block headers if lost)


---

## iCEBreaker Silicon Validation — COMPLETE (May 2026)

### First silicon run: iCEBreaker v1.0e (iCE40UP5K sg48)

**Date:** May 2026
**Board:** iCEBreaker v1.0e
**Toolchain:** OSS CAD Suite (yosys 0.64, nextpnr-ice40, icepack, iceprog)
**Clock:** Internal HFOSC ~12.26MHz

### Results

**PASS — Architecture validated on real silicon.**

```
NOT gate:   NOT(0) = 1  ✓
            NOT(1) = 0  ✓

NAND via wired-OR (two NOT cells, shared output address):
            NAND(0,0) = 1  ✓
            NAND(0,1) = 1  ✓
            NAND(1,0) = 1  ✓
            NAND(1,1) = 0  ✓

Armed cells: confirmed via status command
Cycle counter: confirmed incrementing in real time
UART bridge: bidirectional communication confirmed
```

### What was validated
- wired-OR bus: two cells writing same address, data OR'd correctly
- NOR gate topology: g0=NOR(input,input)=NOT(input) correct
- Cell configuration: LOAD_PATTERN sequence arms cells correctly
- Cell firing: output buffer drain path works on real flip-flops
- UART bridge: inject, configure, status, fired-response all working
- 8 UniCells on iCE40UP5K at 83% LC utilisation

### Key fixes found during bring-up
- TX/RX pins swapped in original PCF (from schematic verification)
- HFOSC ±10% requires inter-byte gap in TX state machine
- Single-byte commands (0x04 status) needed immediate execution
- RX parser discarding unknown bytes (UCOK startup message blocked parser)
- input_val used stale data_reg instead of incoming bus_data
- All unicell registers needed explicit initial values

### Next steps
- Confirm external 12MHz oscillator pin for precise timing
- Scale to larger FPGA (Arty A7, 256+ cells)
- Run full fpga_bridge.py session with OS-layer Ponds
- chipIgnite submission planning
