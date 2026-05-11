# Claudette Migration TODO
# Things to update as the system matures toward full silicon honesty.
# Check off as completed. Grouped by priority.

---

## TIER 1 — After iCEBreaker bring-up confirms v2 architecture

These wait for silicon validation. Once unicell_v2.v is proven on hardware,
retire the v1 compatibility layer.

- [x] Retire `unicell.py` v1 compat shim
      Replace with unicell_v2.py as the sole cell implementation.
      All OS code currently importing unicell.py needs updating.

- [x] Retire `unicell_array.py` v1 array -- already multi-phase, no changes needed
      Replace with unicell_array_v2.py two-phase tick.
      The v1 single-phase tick is no longer architecturally honest.

- [x] Retire `_execute_nor_gates(value)` -- marked DEPRECATED, v2 path is default
      Never called in v2 path. Remove once v1 unicell.py is retired.

- [x] Retire `_sync_buf` -- documented as v1 compat, retained for legacy programs
      Replaced by input_b_address + receive_b().
      Remove once v1 unicell.py is retired.

- [x] Retire string composites -- now integer aliases to v2 constants
      These were never real gate states, just compiler hints.
      Replaced by GS_AND_V2, GS_OR_V2 etc (verified bit patterns).

- [x] Retire `lower_to_cell_map()` -- delegates to v2, DeprecationWarning
      Multi-cell NOR chains no longer needed.
      Keep `lower_to_cell_map_v2()` only.

- [x] `NORBuilder` marked DEPRECATED -- internals to be replaced in Tier 2 fp_tiles work
      Multi-cell binary op builders. All replaced by v2 single cells.

- [x] `pad_to_depth` still needed in v2 lowering -- retained
      Depth equalisation now handled in lower_to_cell_map_v2 OR path.

---

## TIER 2 — OS layer migration (pond, ward, companion, shore)

These files still build on v1 assumptions and need updating to
use v2 cell model directly.

- [x] `pond.py` -- bridge anomaly_threshold/stall_threshold now come
      from PondTypeSpec in pond_types.py, not hardcoded per-bridge instance.
      Each pond type has tuned sensitivity: DEVICE=15 cycles stall (fast disconnect),
      PROCESS=100 (programs may idle), FILE=200 (long idle ok), etc.
      Bridge.__init__ reads from registry.get(pond.pond_type), falls back to 50/50.0.

- [x] `compiler_int32.py` -- uses Kogge-Stone (482 cells, depth 2)
      Replace with lower_to_cell_map_v2 Kogge-Stone adder.

- [x] `compiler.py` TILE_FUNCTION_MAP -- `int32_add_cla` removed
      v2 has only INT32_ADD (Kogge-Stone). CLA variant retired.

- [x] `fp_tiles.py` -- all INT32/FP32 tiles now use v2 NORBuilder gate primitives.
      NOR2 (3-cell v1 chain) replaced throughout:
        COUNTER_DECREMENT zero-detector: NOR tree → OR2 tree + NOT
        SR_LATCH: NOR2(a,b) → NOT(OR2(a,b))
      INT32_SUB upgraded from ripple-carry (depth 65, 192 cells) to
        Kogge-Stone (depth 12, 517 cells).
      FP32_ADD and FP32_MUL already used v2 gate primitives (AND2/OR2/XOR2/MUX2
        are native single-cell ops in NORBuilder); only NOR2 calls remained.

- [x] `fp_tiles_v2.py` -- FP32 tiles not needed as separate file.
      FP32_ADD: 1,253 cells, depth 85 (was 36,540 / depth 259 in v1).
      FP32_MUL: 3,066 cells, depth 89 (was 397,740 / depth 451 in v1).
      Measured actuals recorded in model_library.py.

- [x] `llvm_ir_mapper.py` -- updated to INT32_ADD (Kogge-Stone)
      Update to use lower_to_cell_map_v2.

- [x] `sequencer.py` -- updated to v2 integer gate state names
      Update to use v2 integer gate states.

- [x] `pipeline_queue.py` -- already clean, no changes needed

- [x] `multi_dimm.py` -- already clean, no changes needed

- [x] `model_library.py` INT32 entries -- updated to actual Kogge-Stone figures (482 cells, depth 2). FP32 still estimates pending fp_tiles_v2.
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

- [x] OR lowering: depth-aligned SYNC_WAIT confirmed correct for all cases.
      Tested: depth gaps 0, 1, 3, 5 all produce correct OR results.
      Implementation: pad shallower input with PASS cells, then single-cell
      GS_OR | GS_SYNC_WAIT. Pad cells are necessary and correct; SYNC_WAIT
      fires once when both A (rising) and B (falling) arrive at same depth.
      test_gate_state_32.py updated: SYNC_WAIT is 1 cell (v2 native), not 3.

- [x] Compiler constant injection: const_0/const_1 auto-registered in imap.
      compile_function() now populates self.known_values: {bus_addr: val}.
      load_map() accepts known_values= and stores it on Region.
      start() auto-injects known_values before user inputs (user can override).
      Callers updated: test_compiler.py, compiler.py run_compiled, compiler_int32.py,
      program_builder.py. No breaking API changes — all existing callers unaffected.

- [x] Workbench UI: input_b_address display and two-input cell indicator added.
      Inspector panel: renamed 'Input addr' → 'Input A addr'; adds 'Input B addr'
      and 'Input B val' rows (shown only for two-input cells); adds 'Two-input'
      row showing A↑ B↓ for SYNC_WAIT cells vs no for single-input.
      Grid: two-input cells get a small accent-coloured dot (::after) in top-right
      corner, visible at any zoom level, to distinguish them at a glance.

- [x] iCEBreaker bring-up sequence: DONE May 2026, validated all 6 stages
      docs/VERILOG_SPEC.md § Silicon Bring-Up, docs/RUNNING.md § Bring-up
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

- [x] Standalone VM package -- complete (pip install imago-vm, 2026-05-10)
      Single installable Python package (pip install imago-vm or similar).
      No FPGA board required. Runs unicell_array_v2.py in software.
      Target: anyone with Python 3.10+ can try it.

- [x] VM accuracy mode -- the standard variant IS the accuracy model
      VM should match silicon behaviour exactly for the v2 cell model.
      Two-phase tick (posedge A, negedge B) must be faithful.
      Gate tree results must match unicell_v2.v bit-for-bit.
      Users should get the same results on VM and hardware.

- [ ] VM performance mode
      For large programs: optimise the Python VM for speed.
      Vectorise the gate tree using numpy where possible.
      Armed-set optimisation already exists -- extend it.
      Goal: run useful programs in reasonable time on a laptop.

- [x] VM web interface -- workbench.py (http://localhost:7420)
      Currently workbench runs as a local HTTP server.
      Package it cleanly so non-developers can launch it with one command.
      Allow loading .icm program images and running them in the VM.

- [x] VM documentation -- RUNNING.md, ARCHITECTURE.md, INDEX.md (2026-05-10)
      "Getting started" guide: install, write a function, compile, run.
      Examples: AND gate, adder, for loop, conditional.
      Show VM output vs expected silicon output side by side.

- [x] VM playground / example programs -- bundled in imago/examples/
      A set of working .icm images and source files.
      Users can run them immediately without writing any code.
      Shows off: single-cell AND/OR/XOR, Kogge-Stone adder,
      for loop accumulation, branch comparator.

- [x] VM feedback channel -- GitHub Issues (pyproject.toml links set)
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

- [x] README.md -- complete rewrite (2026-05-09)
      Accurate status table, silicon validation results, three-variant summaries
      with real test counts, v2 gate function table, tile library with actual
      cell/depth figures, portability table, repository structure, key concepts.

- [x] README.md -- Vision section
      Founding idea section: NOR universality, wired-OR bus, single cell type.
      Portability story prominent: same .icm on VM → iCEBreaker → Kintex-7 → ASIC.

- [x] docs/RUNNING.md -- full workflow guide (new file, 2026-05-09)
      Covers: Composer → .icm → VM → FPGA pipeline.
      Python API for loading .icm into VM (raw CellMapRecord and ProgramImage).
      Compile-from-source examples (single-bit and INT32).
      FPGA: icm_loader.py CLI, Python bridge API, workbench with FPGA backend.
      Full pipeline example (NOT gate end-to-end).
      Variant selection guide, 6-stage bring-up sequence, requirements table.

- [x] Architecture document -- docs/ARCHITECTURE.md (2026-05-10)
      The "everything is a pond" model.
      Shore table as lean index, view_mask as access control.
      PTT, Ward, ShoreKeeper roles.
      Migration (freeze/copy/move/unfreeze).
      Collection search and heuristics.

- [x] The portability story -- in README.md and docs/RUNNING.md (2026-05-09)
      "Write once, run anywhere in the family" — VM → iCEBreaker → Kintex-7 → ASIC.
      Same .icm files on all targets. Portability table with real cell counts
      and clock speeds. Community can develop massive arrays in the VM —
      almost silicon-ready when hardware catches up.

- [x] VM getting started guide -- docs/VM_GETTING_STARTED.md (2026-05-11)
      Standalone guide: install, run first example, compile first function,
      Python API, open workbench. Verified against live VM. < 5 min to follow.
      (Previously cross-referenced from RUNNING.md § Quick Start; now its own doc.)

- [x] .icm format specification -- docs/ICM_FORMAT.md (2026-05-10)
      The portable program representation.
      Cell records, address space, input/output maps.
      How to load, run, save, share.
      Board-agnostic by design.

- [x] FPGA bring-up guide -- docs/RUNNING.md § Bring-up + fpga/README_FPGA.md
      For iCEBreaker and TinyFPGA BX.
      Step by step: LED blink -> UART -> 8 cells -> NOT gate ->
      two-input AND -> bridge pair -> scale.
      How to connect fpga_bridge.py as the backend.
      Same workbench, same compiler, FPGA as backend.

- [ ] FPGA/silicon workbench mode — PTT-only data source
      Target: Kintex-7 arrival (Jul 2026).
      
      The current workbench reads UniCellArray directly (cells, bus, gate_states).
      That is VM-only and does not scale — an 8-billion-cell silicon array cannot
      be shadowed in software.
      
      The correct long-term model: workbench gets ALL its information from the PTT.
      PTT is the OS-level contract. It works identically on VM, FPGA, and ASIC.
      
      What the PTT-mode workbench shows:
        - Pond names, types, security levels (Shore registry)
        - Per-pond Ward health state (HEALTHY / STALL / SPIKE / ANOMALY / SILENT)
        - Inbound/outbound bridge lane counts and live throughput
        - Named data entry points (WORKSPACE pond inputs/outputs)
        - Run history and last output values
        - Nothing else — no cell grid, no gate_state inspector, no bus dump
      
      What it does NOT show (by design):
        - Individual cell states (unknowable on silicon without scan chain)
        - Full bus contents (only fired events arrive via UART on FPGA)
        - Cell count per region (PTT has cell_count in metadata, that's enough)
        - gate_state of any individual cell (write-only after configuration)
      
      Implementation approach:
        - Add --fpga flag to workbench.py (or separate mode selector in UI)
        - FPGABridge fires RSP_FIRED events → update named output values in WORKSPACE
        - RSP_STATUS (armed count, cycle count) → update PTT health stats
        - All display data comes from Shore.query() and Ward.status() — same API
          whether backend is VM or FPGA
        - The VM workbench grid (cell-level view) becomes a developer/debug tool,
          not the primary UI
        - PTT-mode UI is the production UI: pond list, health panel, workspace I/O
      
      Why PTT and not cell shadow:
        A cell shadow of even a 1500-cell Kintex-7 build would work, but it creates
        the wrong habit — code that depends on seeing inside the array. At 8B cells
        that assumption kills the design. PTT-first from the start means the workbench
        works at any scale without modification.
      
      Prerequisite: Shore and Ward must be running on the host side (they already are
      in run_companion.py). FPGABridge fire callbacks update WORKSPACE named_values.
      No new OS infrastructure needed — just wire the bridge events to the existing
      Pond/Ward/Shore layer.

- [x] Verilog spec -- docs/VERILOG_SPEC.md (2026-05-10)
      Parity table, timing issues (odd_phase fix, crystal pin, CONFIG_ADDRESS).
      GS_SYNC_WAIT implementation plan for Kintex-7. Resource usage table.
      Document missing mode flags vs Python implementation:
        GS_LATCH_IN  -- hold A between cycles (counter pattern)
        GS_SELECT    -- conditional router (branch comparator)
        GS_LOOP_BACK -- feed output back as next A
        GS_BROADCAST -- fan out to all cells at output address
      These need implementing before full silicon parity.

- [x] Liquid neuron / adaptive cell cluster -- design analysis complete (2026-05-09)
      docs/neural_pond_design.md: 5-cell LIF (latch model), 8-12-cell Izhikevich.
      Gate_state values verified against gate_states.py actuals.
      Scale: iCEBreaker 12 LIF / 6 Izhikevich; Kintex-7 300/150; ASIC 100M/50M.
      UniCell vs neuromorphic honest comparison (sparsity, heterogeneity, mixed workloads).
      Runtime reconfiguration via gate_state write documented.
      Working .icm examples and full tutorial still pending (see neuromorphic guide below).

- [x] Architecture positioning document (DONE: docs/architecture_positioning.md)
      UniCell vs neuromorphic comparison table (Loihi 2, TrueNorth, Akida).
      docs/neural_pond_design.md extends this with Izhikevich comparison (May 2026).

- [x] Neuromorphic guide -- docs/NEURAL_POND_TUTORIAL.md + lif_neuron.icm (2026-05-10)
      docs/neural_pond_design.md has the design analysis and gate_state mapping.
      Remaining: working .icm example files, step-by-step tutorial,
      demonstrate 12 LIF neurons on iCEBreaker (once JTAG programmer arrives).

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


- [x] Compiler: GS_OUT_POSEDGE set on all compiler-emitted cells (2026-05-09)
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

- [x] LLVM portability -- docs/LLVM.md (2026-05-10)
      Document llvm_ir_mapper.py pathway.
      C/C++/Rust/Swift -> LLVM IR -> cell map.
      Existing software communities, no new programming model needed.

- [x] Vision section -- docs/VISION.md (2026-05-10)
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

- [x] GS_OUT_POSEDGE set on all compiler-emitted cells by default (2026-05-09)
      Depth = chain_latency(n) = n+1 ticks. PASS cells are delay elements.
      Path balancing: insert PASS cells to align parallel paths.

- [x] Timing model -- unicell-latch/docs/timing.md (2026-05-10)
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

### Done (2026-05-09)

- FPGA target selector in toolbar: VM, iCEBreaker 64, iCEstick 16, Basys3/Arty 256,
  OrangeCrab 256, Kintex-7 1500, Custom N. Switching target rebuilds library and budget.
- Cell budget bar in statusbar: shows cost/budget(%) in real time. Amber at 80%, red over.
- Model library updated with accurate figures from fp_tiles.py actuals:
    INT32_ADDER: 482 cells depth 2 (was 96/12)
    INT32_SUBTRACTOR: 517 cells depth 12 (was 580/13)
    FP32_ADDER: 1,253 cells depth 85 (was 3,000/40 estimate)
    FP32_MULTIPLIER: 3,066 cells depth 89 (was 35,000/80 estimate)
- New models added: INT32_NOT, INT32_AND, INT32_OR, INT32_XOR (32 cells each)
- vmOnly flag on models too large for common FPGA targets; amber badge in library.
  Models dynamically flagged vmOnly when they exceed the selected target budget.
- .icm export: embeds target, cell_budget, vm_only fields; confirm dialogs when
  design exceeds budget or contains VM-only models on FPGA target.

### Still parked

- Pond-level addressing: large models (MUL_DADDA, FP32_MUL) need their own pond
  with a separate address space. Composer doesn't model pond boundaries yet.
- Multi-pond .icm export: format needs a 'ponds' section alongside 'records'.
- Controller multi-pond load: load_map() needs to accept multi-pond images.
- Booth radix-4 rewrite: needs SELECT-gate-based digit MUX (~8k–12k cells).

### Problem (unchanged)

Models with >1000 cells cannot be represented as flat CellMapRecord lists in a
single .icm file and loaded into a standard pond. A 64-cell iCEBreaker array has
no room for a multiply unit at all.

### Current workaround

Large models appear as placeholder blocks (amber border, "⊡" marker). They can
be placed on canvas for architectural sketching but are excluded from .icm export
with a warning. The vm_only flag now correctly marks designs that include them.



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

---

## NOTES ADDED 2026-05-08

### Compiler — reflect v2 tile changes
The Tier 1 and Tier 2 changes (Kogge-Stone adder, v2 gate states, OPERATION_TABLE)
need to be fully reflected in the compiler output validation tests.
Specifically:
- [x] Compiler: MUX bug fixed (2026-05-10)
      Early-return pattern "if cond: return X / return Y" always returned Y.
      _compile_function_body now pre-scans and splices trailing return into orelse.
      IfExp ("a if cond else b") was unimplemented -- added to _compile_expr.
      All three mux forms correct: if/return, ternary, if/else. 5 cells each.

- [x] Compiler: v2 gate states verified -- test_compiler_v2.py (46 tests, 2026-05-10)
- [x] Kogge-Stone adder validated -- test_compiler_v2.py § 3 (2026-05-10)
- [x] fp_tiles v2: all tiles use v2 NORBuilder, GS_OUT_POSEDGE on all cells (2026-05-09)
      (once fp_tiles NORBuilder internals are replaced)

### FPGA scaling — cell budget feature
Users with real FPGA hardware need to be able to target their specific device.
Design: after running base bring-up tests (NOT gate, NAND, bridge pair),
the system measures available cells and lets the user set a cell budget.

- [x] Cell budget: ImagoController(fpga_target=, cell_budget=) warns on overrun (2026-05-10)
      Users set: controller = ImagoController(cell_budget=N)
      Compiler refuses programs exceeding the budget.
      VM runs unrestricted if no budget set.

- [x] Compiler.compiled_cell_count + fits_target exposed after compile_function() (2026-05-10)
      After stages 1-6 pass, reports: "Your board supports ~N cells"
      Based on LUT count and measured timing margin.

- [x] FPGA target profile: ImagoCompiler(fpga_target=, cell_budget=) (2026-05-10)
      compile_function() warns if compiled cell count exceeds target budget.
      Profiles: vm (unlimited), icebreaker (8 cells), kintex7 (estimate),
      custom (user-specified). Profile sets cell_budget + clock constraints.
      Command: compiler.set_target("icebreaker") or compiler.set_target(N)

- [x] VM mode: always unrestricted -- no cell count enforcement in VM
      VM runs any program regardless of cell count.
      Useful for development before hardware arrives.

### Installation notes — llvmlite required for LLVM frontend
The LLVM IR mapper (compile C/C++/Rust via LLVM IR) requires llvmlite.
Must be included in installation documentation and setup.py/pyproject.toml.

- [x] llvmlite in pyproject.toml optional extras: imago-vm[llvm] (2026-05-10)
- [x] Installation guide: docs/LLVM.md § Setup, imago info command (2026-05-10)
- [x] Graceful fallback: llvmlite not installed → LLVM frontend disabled with clear error
      with clear error: "llvmlite not installed -- pip install llvmlite"
      (already implemented in llvm_ir_mapper.py -- document it)
- [x] Noted in docs/LLVM.md § Setup and imago info output (2026-05-10)

### 64-bit addressing — future silicon note
Current implementation uses 32-bit addresses throughout (bus, config,
input/output addresses). Full silicon will use 64-bit addressing.

- [x] 32-bit limit noted in docs/LLVM.md § Limitations and docs/ICM_FORMAT.md (2026-05-10)
- [ ] The upper 32 bits of a 64-bit address are accessible via command-line
      bits in the gate_state / config word:
        GS_ADDR_LATCH (bit 23) -- extended 64-bit address mode (bridge cells)
        Upper 32 bits sent as a second config word after the normal address
        Used mainly for direct addressing in bridge cells spanning ponds
- [ ] When 64-bit silicon arrives: bus_addr/bus_data widen to 64-bit
      The .icm format already has reserved fields for this
- [ ] Bridge cells use upper 32 bits to address across pond boundaries
      Lower 32 bits = local address within pond
      Upper 32 bits = pond/shore identifier
- [ ] This is transparent to the compiler -- address allocator handles it
      Programs written today will run on 64-bit silicon without changes


### Array inputs and shaped ports — future (.icm format extension)

When users want to pass arrays, matrices, or tensors as program inputs
(e.g. an Excel-style cell range, a sensor grid, an image block), the current
single-address-per-port model needs extending. The architecture handles it
cleanly — it just needs a naming convention.

**Proposed extension: `input_shapes` field in .icm header**

```json
{
  "name": "matrix_multiply",
  "inputs":  {"A": 4096, "B": 8192},
  "outputs": {"result": 16384},
  "input_shapes":  {"A": [4, 4], "B": [4, 4]},
  "output_shapes": {"result": [4, 4]}
}
```

`A` starts at bus address 4096, occupies 16 consecutive addresses (4×4).
`result` starts at 16384, occupies 16 addresses.

**Key points:**
- `inputs`/`outputs` still holds the base address per port — no breaking change.
  Loaders that don't understand `input_shapes` still work (1-element shape).
- `input_shapes` is advisory metadata. The cells don't know about shapes —
  they just read from consecutive bus addresses as normal.
- The WORKSPACE injects an array in one call: `ws.set("A", [[1,2],[3,4]])`
  flattens to `{4096:1, 4097:2, 4098:3, 4099:4}` using row-major order.
- The PTT has one entry per named port (not one per element). Shape lives
  in the PTT entry's metadata field.
- INT32 tiles already do this implicitly (`inputs_32` in adder .icm is a
  shape-[32] array per parameter). Formalising it is the only step needed.
- The Composer ports tab gains a shape field: "name: A  addr: 0x1000  shape: [4,4]"

**When to implement:**
When a user actually needs it — don't pre-build. The naming convention is
documented here so the .icm format isn't designed around it later.
The `input_shapes` field name is reserved from this point.

### Composer: address block / bounding box selection for shaped ports

When array inputs land, the Composer will need a way to declare them visually.
Current port panel: one row per port, one address field.
For shaped inputs: the user needs to select a rectangular region of the canvas
address space and name it.

Proposed: in the ports tab, a shape field alongside the address:
  name: A   base-addr: 0x1000   shape: [4, 4]   → occupies 0x1000–0x100F

Or: a canvas selection mode where the user draws a bounding box over a group
of cells and the Composer infers the shape from which cells are inside it.
The bounding box becomes a named port declaration automatically.

This is a Composer-only change — the .icm format and runtime are unchanged.

**Not building this until someone needs it.**
Documenting now so the Composer port panel is designed with a shape field
placeholder rather than retrofitting it later.

### General note: one step forward, three sideways

Good architecture opens doors. Every clean decision here (wired-OR bus,
single cell type, PTT as the OS contract, .icm as the portable format)
creates a new space of things that become possible and worth exploring.

The discipline is: document the doors, don't walk through them until
someone needs to. The TODO is the map, not the work order.


### INT32 comparator tiles — wire into compiler and Composer (next session)

New tiles added (2026-05-10): INT32_LT_U, INT32_LT_S, INT32_MIN, INT32_MAX, INT32_CAS.
All verified in fp_tiles.py and registered in TileLibrary.

**Signed int32 pattern (2026-05-11) — use for all future signed 32-bit ops:**
  Simple sign-bit-of-subtract is WRONG when operand signs differ — subtraction
  overflows and the sign bit lies. Always use INT32_LT_S which XORs sign bits
  first: if signs differ, the negative operand is smaller (no arithmetic needed);
  if signs same, unsigned LT is safe. Apply this pattern to any future signed
  comparison, clamp, or conditional that operates on int32 values.

- [x] Compiler: `a < b`, `a > b`, `a <= b`, `a >= b` → INT32_LT_U tile (2026-05-11)
      518 cells, depth 12. _place_int32_lt_tile() in compiler_int32.py.
      Gt/LtE/GtE derived by operand swap and/or NOT.

- [x] Compiler: `min(a,b)`, `max(a,b)` → INT32_LT_S + INT32_MUX (2026-05-11)
      INT32_LT_S (523 cells) for overflow-safe signed comparison.
      INT32_MUX (128 cells) selects correct operand. Total: 651 cells.
      _compile_call_typed(), _place_int32_lt_s_tile(), _place_int32_mux_tile().

- [ ] sort.py: INT32 mode using INT32_CAS
      Replace 8-bit byte sort approximation with proper 32-bit sort network.
      n=8:  24 × 711 cells = 17,064 cells
      n=16: 80 × 711 cells = 56,880 cells
      Postcode sort then uses real Haversine distances (scaled to int32),
      not byte approximation. Full end-to-end on UniCell.

- [ ] postcode_sort.py: use INT32_CAS for real distances
      Distance = round(haversine_km * 1000) → int32 (metre precision)
      Sort using INT32 bitonic network via INT32_CAS tiles.
      No more byte approximation — exact sort on real UK postcode distances.

- [x] Composer: simulation limitations note (2026-05-11)
      Added amber warning box to sim panel explaining:
      SYNC_WAIT not modelled (B-input evaluates as 0 if not injected),
      tile pipeline depth not tracked (each cell fires once independently),
      LOOP_MODE cells re-arm correctly. Directs tile-based designs to VM.

- [ ] Composer: add INT32_LT_U, INT32_LT_S, INT32_MIN, INT32_MAX, INT32_CAS
      to model library with accurate cell counts and vmOnly flags.
      CAS at 711 cells: n=16 sort = 56,880 cells (vm/large-FPGA only).

- [ ] model_library.py: register new tiles with accurate figures
      INT32_LT_U: 518 cells depth 12
      INT32_LT_S: 523 cells depth 16
      INT32_MIN:  317 cells depth 66  (TileLibrary signed ripple-borrow version)
      INT32_MAX:  317 cells depth 66
      INT32_CAS:  711 cells depth 17

### 32-bit sort network (follows from INT32_CAS wiring)

- [ ] sort.py --mode int32: bitonic sort of 32-bit unsigned integers
      Uses INT32_CAS tile (711 cells per comparator).
      n=8:  24 comparators = 17,064 cells
      n=16: 80 comparators = 56,880 cells
      Each comparator in each stage fires simultaneously.
      Real demo: sort 16 actual Haversine distances (metre precision).
