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

- [x] `model_library.py` INT32 entries -- all figures verified against TileLibrary 2026-05-11.
      INT32_ADD: 482 cells depth 2. INT32_SUB: 517 cells depth 12.
      INT32_EQ: 95 cells depth 7 (was stale 63/6 estimate — fixed).
      FP32_ADD: 1253 cells depth 85. FP32_MUL: 3066 cells depth 89 (verified v2).
      INT32_LT_U/S, MIN, MAX, CAS: all registered with correct figures.
      "estimates" comment removed — all figures are now verified.

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

- [ ] VM performance mode — DEFERRED: implement after FPGA/silicon validation
      Tag: FPGA-dependent — validate tick model on silicon first, then optimise.

      Rationale: numpy vectorisation changes the tick loop fundamentally.
      Silicon validation will confirm whether the current cell-by-cell model
      matches hardware exactly. Only then is it safe to vectorise — otherwise
      we risk optimising behaviour that changes when real hardware arrives.

      When ready (post JTAG validation, ~May-Jun 2026):
      - Add use_numpy=False flag to UniCellArray; numpy path runs in parallel
        with cell-by-cell path during transition, verified for identical output.
      - Vectorise gate tree: pack gate_state into numpy array, bit-masked ops
        per gate type (NOT, AND, OR, XOR, PASS etc.) as separate masked passes.
      - Wired-OR bus: scatter-OR across output_address array (numpy ufunc).
      - Armed-set: reconcile with dense array approach or keep as mask.
      - Re-wire: ECC checks, PTT bus intercept, bridge registry must survive.
      - Two-input cell (A/B posedge/negedge, SYNC_WAIT): handle as separate
        masked pass — doesn't vectorise with single-input cells cleanly.
      Expected gain: n=16 sort 10s → <1s; adder_int32 3-5x faster.
      Keep cell-by-cell path as reference/correctness path permanently.

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
      → Superseded by MIGRATION_TODO § WORKBENCH Two-Mode Architecture (2026-05-11).
      Target: post-JTAG validation (May-Jun 2026 for iCEBreaker, Jul 2026 for Kintex-7).
      Full spec including prerequisites, startup flow, and Shore user tables
      is in the WORKBENCH block at the end of this file.
      
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
      → Deferred: implement two-mode workbench first (see WORKBENCH block).
      Display pond layer sits on top of the silicon terminal mode — once Shore
      user tables and PTT health dashboard exist, display ponds are natural next.
      Document how session = pond tree, window = display pond, minimise = view_mask 0.
      No new architecture needed — already supported. Revisit post-JTAG.

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

**Design decisions (2026-05-11):**

- [x] Index Pond metadata fields (2026-05-11)
      Default indexed fields per file entry:
        logical_addr    — 32-bit logical file address (primary key)
        physical_addr   — block address in the storage pond
        name            — UTF-8 filename, packed as alpha cells (4 chars/cell)
        type_tag        — MIME-like type tag (e.g. 0x01=icm, 0x02=source, 0x03=text)
        size_blocks     — file size in storage blocks
        created_at      — Unix timestamp (int32, seconds)
        modified_at     — Unix timestamp (int32, seconds)
        author_id       — owner identity hash (32-bit truncated)
        tags            — bitmask of up to 32 user-defined tag bits
      Each field occupies one or two cells in the Index Pond (two for typed/signed).
      Custom fields: any additional cells at logical_addr+N are user-defined metadata.
      The Shore query interface treats all cells as a flat address space to mask-filter.

- [x] Mask filter syntax (2026-05-11)
      A query is a set of (address_offset, mask, value) triples — expressed as
      three bus writes to the Shore query pond input lanes:
        QUERY_ADDR: offset within the index entry (0=logical_addr, 4=type_tag, ...)
        QUERY_MASK: bitmask to apply to the cell value at that offset
        QUERY_VAL:  value after masking (match condition: (cell & mask) == val)
      Multiple (ADDR, MASK, VAL) triples are AND-combined.
      Example: find all .icm files created after timestamp T:
        (4, 0xFF, 0x01)   ← type_tag == 0x01 (icm)
        (6, 0xFFFFFFFF, T_min)  ← created_at >= T_min (handled by comparator tile)
      Shore fires a ReturnWave for each matching entry's logical_addr.
      This is exactly the Shore.record / ReturnWave pattern already implemented.

- [x] Consistency model (2026-05-11)
      External modification (e.g. USB transfer, FPGA upload to same storage blocks):
        — Index Pond is the authoritative view. External writes are not seen until
          an explicit re-scan or commit is performed.
        — The Index Pond is VOLATILE: a running system may have a stale index if
          the storage is written externally. This is acceptable for the current
          use case (single-user, single-system).
        — Future: a MONITOR bridge on the storage pond detects writes and marks
          affected index entries dirty (status bit in the entry). A background
          Ward-triggered task re-indexes dirty entries.
        — For now: external writes → call fs_search.rebuild_index() to re-scan.

- [x] Index persistence (2026-05-11)
      The Index Pond is a STORAGE-type Pond (GS_LATCH cells).
      On power cycle:
        — The Index Pond cells lose state (DRAM / FPGA BRAM is volatile).
        — On boot, the COMPANION spawns the Index Pond and triggers rebuild_index().
        — rebuild_index() scans block headers in the storage pond to reconstruct
          the index in O(n_blocks) time. This is the same as a filesystem fsck.
        — Future: a non-volatile variant using FLASH-backed storage cells can
          persist the index across power cycles. The pond architecture supports
          this transparently — same interface, different storage type.

- [x] Index rebuild (2026-05-11)
      rebuild_index() in fs_search.py:
        1. Iterate all block headers in the storage pond (each block header is a
           fixed-size record at the start of each storage block).
        2. For each valid header (magic bytes match), emit an index entry to the
           Index Pond: write logical_addr, type_tag, size, created_at, etc.
        3. Mark the Index Pond ACTIVE when complete.
        4. Shore registers the Index Pond's entry addresses for query routing.
      Rebuild is O(n_blocks) — typically < 1 second for a 1GB storage pond at
      24 MHz (one block header per 512 bytes = 2M block headers at 512B each).
      The rebuild path is already partially implemented in fs_search.py via the
      _scan_blocks() helper. Needs wiring to Index Pond cell writes.


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
      518 cells, depth 14 (verified). _place_int32_lt_tile() in compiler_int32.py.
      Gt/LtE/GtE derived by operand swap and/or NOT.

- [x] Compiler: `min(a,b)`, `max(a,b)` → INT32_LT_S + INT32_MUX (2026-05-11)
      INT32_LT_S (523 cells) for overflow-safe signed comparison.
      INT32_MUX (128 cells) selects correct operand. Total: 651 cells.
      _compile_call_typed(), _place_int32_lt_s_tile(), _place_int32_mux_tile().

- [x] sort.py: INT32 mode using INT32_CAS — tested n=4/8/16 (2026-05-11)
      n=4:  6 comparators,  4,650 cells  — ✓ correct, ~180ms
      n=8:  24 comparators, 18,600 cells — ✓ correct, ~1.4s
      n=16: 80 comparators, 62,000 cells — ✓ correct, ~10s
      Fuzz: 10×n=4, 5×n=8, 3×n=16 random inputs — all correct.
      Note: uses custom KS-subtractor CAS (~775 cells), not INT32_CAS tile
      (711 cells). INT32_CAS tile path is a future optimisation.

- [x] postcode_sort.py: INT32 sort with real Haversine distances (2026-05-11)
      Distances stored as integer metres (Haversine, exact — no approximation).
      n=8: ~1.5s, n=16: ~10s, n=32: ~60s — all correct.
      Bar chart and architecture note fixed to use actual n/stages/cells.

- [x] Composer: simulation limitations note (2026-05-11)
      Added amber warning box to sim panel explaining:
      SYNC_WAIT not modelled (B-input evaluates as 0 if not injected),
      tile pipeline depth not tracked (each cell fires once independently),
      LOOP_MODE cells re-arm correctly. Directs tile-based designs to VM.

- [x] Hardware support matrix — fpga/README_FPGA.md (2026-05-11)
      Documents which .icm fields are honoured at each layer (VM / bridge / loader / Verilog).
      inB/SYNC_WAIT: not in Verilog yet — needs hardware to implement and test.
      init: not sent over UART yet — needs hardware to confirm pre-load protocol.
      icm_loader.py now warns when inB or init fields are present in a loaded .icm.
      Full implementation deferred until JTAG programmer arrives (~21 May 2026).

- [ ] Composer: add INT32_LT_U, INT32_LT_S, INT32_MIN, INT32_MAX, INT32_CAS
      to model library with accurate cell counts and vmOnly flags.
      CAS at 711 cells: n=16 sort = 56,880 cells (vm/large-FPGA only).

- [x] model_library.py: all new tiles registered with verified figures (2026-05-11)
      INT32_LT_U: 518 cells depth 14 · INT32_LT_S: 523 depth 16
      INT32_MIN/MAX: 317 cells depth 66 (signed) · INT32_CAS: 711 depth 17

### 32-bit sort network (follows from INT32_CAS wiring)

- [x] sort.py INT32 mode verified (2026-05-11) — see earlier session entry

---

## CODE AUDIT 2026-05-11 — Stubs, placeholders, and silent failures found

Systematic sweep of all TODO/FIXME/stub/placeholder/NotImplemented markers.
Items grouped by severity. Complete, test, check off in order.

---

### CRITICAL — Silent runtime failures (wrong results, no error)

- [x] `_ptt_ref` wired in controller.load_map(ptt=...) (2026-05-11)
      Added optional `ptt=` parameter to load_map(). When set, iterates all loaded
      cells and sets `cell._ptt_ref = ptt`. unicell.py PTT bus interception now
      fires correctly. test_ptt_sentry.py: 20/20 tests passing.

- [x] Sentry PTT address placeholder patched in controller.load_map(ptt=...) (2026-05-11)
      After _ptt_ref wiring, load_map() now walks loaded cells with output_address
      == PTT_BUS_BASE (placeholder) and patches each to the correct per-entry
      ptt_bus_address(entry.index). Patching is FIFO: first placeholder → first
      registered sentry entry. test_ptt_sentry.py verifies two tiles get distinct
      PTT bus addresses. Note: ptt_bus_address(0) == PTT_BUS_BASE is legitimate.

---

### STALE FIGURES — Wrong numbers, misleading docs

- [x] model_library.py: all figures verified and updated (2026-05-11)
      INT32_LT_U/S, MIN, MAX, CAS: all registered with correct verified figures.
      INT32_EQ corrected: 95 cells depth 7 (was stale 63/6).
      FP32_ADD/MUL: verified 1253/3066 cells, "estimates" comment removed.
      INT32_MIN/MAX descriptions corrected to "signed" (signed ripple-borrow tile).

- [x] MIGRATION_TODO.md line 84: corrected to 482 cells (verified figure).

---

### INTENTIONAL STUBS — Document clearly, no code change needed

- [x] AudioBridge / VideoBridge — "deferred until tile exists" comment added (2026-05-11)
      Tracking reference to MIGRATION_TODO added. No code change needed.

- [x] Peripheral tile stubs (KEYBOARD_HANDLER etc.) — intentional, documented (2026-05-11)
      records=[] is correct: Composer uses metadata only, not cell map. No change.

- [x] uniflex_fs.py FsDecoderStub — intentional simulator path, documented (2026-05-11)
      Silicon path is future work. No change needed.

---

### COMPILER BOUNDARIES — NotImplementedError is correct behaviour, needs tests

- [x] compiler.py NotImplementedError boundary tests added (2026-05-11)
      test_compiler.py: chained comparison, non-range iterable, unsupported BinOp (Pow),
      AugAssign on subscript target. 39 tests total, all passing.

- [x] compiler_int32.py NotImplementedError boundary tests added (2026-05-11)
      test_compiler_int32.py: chained int32 comparison, unsupported Pow op.
      82 tests total, all passing.

---

### GATE_STATES TODO — In-code note, verify it is already done

- [x] gate_states.py TODO comment removed (2026-05-11)
      lower_to_cell_map_v2() already sets GS_OUT_POSEDGE on all emitted cells
      (ir.py lines 264, 280). TODO was stale — comment updated to reflect reality.

---

## WORKSPACE POND — Full OS-level implementation (foundation laid 2026-05-11)

The workspace/bridge/security model is the access layer for the full OS.
Foundation is in pond.py: spawn_workspace(), connect(), spawn_pond_from_icm()
with input/output PTT entries, _ptt_ref wiring, and sentry address patching.

### What exists (2026-05-11)

- [x] PondManager.spawn_workspace(owner_id, name) — creates PRIVATE WORKSPACE pond
      Ward + PTT (INCREMENTAL) created. INBOUND + OUTBOUND bridges.
      Empty whitelist — only connected program ponds get access.

- [x] PondManager.connect(workspace, program) — bus wiring + whitelist grants
      ws OUTBOUND external_address → pg INBOUND external_address (zero overhead)
      pg OUTBOUND external_address → ws INBOUND external_address
      Workspace grants program owner; program grants workspace owner.
      Workspace PTT receives TYPE_PRIMITIVE entry per program output port.

- [x] PondManager.spawn_pond_from_icm() — PRIVATE by default (was OPEN)
      Program ponds are now PRIVATE at spawn; connect() grants workspace access.
      Input ports registered as TYPE_TILE_IN PTT entries.
      Output ports registered as TYPE_PRIMITIVE with sentry clusters.

- [x] test_pond_connect.py: 31 tests covering spawn, connect, wiring, whitelist,
      multi-program workspace, workspace isolation.

### What the full implementation requires

#### WorkspacePond refactor (currently workbench-only, not in-cell)
The existing WorkspacePond class (workspace.py) is a standalone controller
wrapper used by the workbench. It does not use the Pond/PondManager/bridge
architecture. The full OS model requires:

- [x] WorkspacePond backed by real Pond (type=WORKSPACE) (2026-05-11)
      WorkspacePond.__init__(pond_manager=mgr) spawns a real WORKSPACE Pond.
      Ward + PTT + bridge security all active when pond_manager is supplied.

- [x] WorkspacePond.launch_program(icm_dict) → ProgramHandle (2026-05-11)
      Calls spawn_pond_from_icm() then connect(). Returns handle dict.
      Adds to self._active_programs — multiple simultaneous programs supported.

- [x] WorkspacePond.run_program(handle_id, **inputs) (2026-05-11)
      Routes inputs via wired bus addresses. Transitions TILE_IN IDLE→WAITING.
      Captures output. Stores result in named_values under "program.port" key.

- [x] WorkspacePond.status() shows all connected ponds (2026-05-11)
      Returns active_programs dict with program name, pond_id, inputs, outputs,
      and PTT entry status (IDLE/WAITING/ACTIVE) per port.

- [x] WorkspacePond.disconnect_program(handle_id) (2026-05-11)
      Revokes whitelist grants. Removes workspace PTT entries for this program.
      Calls destroy_pond() to free cells.

#### Security enforcement at the bridge (hardware-ready)
- [x] Bridge access check in UniCellArray Phase 0 tick loop (2026-05-11)
      UniCellArray._bridge_registry: {inbound_addr: PondBridge}.
      Phase 0 drain: writes to registered addresses check cell._pond_id vs bridge._pond_id.
      OPEN ponds pass all; PRIVATE/HIDDEN drop unauthorised writes, increment _bridge_rejections.
      PondManager.connect() registers addresses and tags cells with _pond_id.
      Full per-cell identity tokens are future work (MIGRATION_TODO § Access token).

- [ ] Access token in PTT hidden field (bits 0-31 of TYPE_SENTRY entry)
      The process_mask param in check_access() currently defaults to 0xFFFFFFFF.
      Real enforcement requires the caller's identity encoded in the bus packet.
      Design: each pond's owner_id hashed to a 32-bit token at spawn time;
      token flows with every bus write as the high word of a 64-bit address packet.
      Shore resolves token → identity for whitelist check.

#### Multi-user (multiple workspace ponds)
- [ ] Multiple WORKSPACE ponds per PondManager — one per logged-in user
      Already works structurally (test_pond_connect.py verifies isolation).
      Need: Shore registers each workspace's INBOUND external_address under the
      user's identity so program ponds can find their home workspace.
      ShoreKeeper routes: "output for user_alice" → alice's workspace INBOUND addr.

- [x] Workspace quota: max 8 concurrent program ponds per workspace (2026-05-11)
      PondManager.connect() raises ValueError if workspace._active_programs >= max.
      Default max_concurrent = 8; configurable via workspace._max_concurrent_programs.

#### Workbench integration (deferred)
- [ ] Workbench WorkspacePond backed by real Pond
      Currently: workbench creates WorkspacePond(controller) — a bare wrapper.
      Target: workbench calls PondManager.spawn_workspace(owner_id=session_id).
      All ws set / ws run / ws get routes through the real bridge architecture.
      Workbench displays PTT status live — Ward health, bridge packet counts.
      Estimated effort: 1-2 sessions once WorkspacePond refactor is done.

### Architecture summary (for reference)

    User session (Alice):
      WorkspacePond → backed by WORKSPACE Pond (PRIVATE, INCREMENTAL PTT)
        INBOUND bridge  ← receives program outputs
        OUTBOUND bridge → delivers inputs to programs
        PTT tracks: session root, all connected program outputs (IDLE/ACTIVE/FAULTED)

      Program Pond A (not_gate) — PRIVATE, connected via connect()
        INBOUND  ← ws OUTBOUND (addr wired directly, zero overhead)
        OUTBOUND → ws INBOUND  (addr wired directly, zero overhead)
        PTT: TILE_IN entries (inputs), PRIMITIVE entries (outputs with sentries)
        Whitelist: only Alice's workspace identity admitted

      Program Pond B (adder) — same structure, different addresses
        Both route output back to Alice's INBOUND — she sees all results

    Bus packet path (zero-overhead):
      ws set a=5 → ws OUTBOUND fires at pg INBOUND addr → pg sees value next tick
      pg output fires at pg OUTBOUND addr (= ws INBOUND addr) → ws sees result next tick
      No routing hop. No ShoreKeeper in the hot path. One tick end-to-end.

---

## WORKBENCH — Two-Mode Architecture (VM microscope / Silicon terminal)

Fundamental split in how the workbench operates. Both modes share the same
workspace surface (set inputs, run, see outputs) but the routing, visibility,
and constraints underneath are completely different.

---

### Mode A — VM Microscope

Direct access to UniCellArray. Useful for compiler development, tile debugging,
architecture work. Not appropriate for production or multi-user sessions.

**Capabilities:**
- Cell inspector: gate_state, input_address, output_address, armed/fired status
- Bus monitor: live bus values per address per tick
- Tick stepper: advance one tick at a time, observe cell state changes
- Gate tree visualiser: trace signal path from input to output
- Full PTT/Ward visibility (but not enforced — single user, trusted)
- WorkspacePond backed by bare controller OR PondManager (both valid)

**Cell budget modes (startup flag):**
  --mode vm                 Default: unbounded array (up to available RAM)
  --mode vm --cells fpga    Mirror current connected FPGA budget (e.g. 64 cells
                            for iCEBreaker, 1500 for Kintex-7). User sees exactly
                            what fits on real hardware. Programs that exceed the
                            budget are flagged vmOnly=true.
  --mode vm --cells <N>     Explicit cell count (e.g. --cells 60000 for large
                            simulations, --cells 16 for iCEstick accuracy).

The FPGA-mirror sub-mode is the key feature: toggle in the workbench header
switches between "unlimited" and "FPGA budget". A program that compiles fine
unlimited but fails in FPGA-mirror mode tells the user exactly what they need
to know before they hit hardware.

**Startup selector (workbench UI):**
  ┌─────────────────────────────────────────────────────┐
  │  Cell array size                                    │
  │  ○ Reflect current hardware  (iCEBreaker: 64 cells) │
  │  ○ Standalone — large VM     (no budget limit)      │
  │  ○ Custom                    [____] cells           │
  │                                      [ Launch ]     │
  └─────────────────────────────────────────────────────┘
  "Reflect current hardware" locks the VM to the connected FPGA's cell budget.
  "Standalone" removes the budget constraint entirely — useful for exploring
  large programs (n=32 sort, FP32 pipelines) that won't fit on current hardware.
  Once launched, the mode is fixed for the session — no mid-session switch,
  because changing array size would invalidate all loaded regions.

---

### Mode B — Silicon / FPGA Terminal

PTT and Shore only. No direct cell access. This is what a real user session
looks like at scale — the same interface that would work on a billion-cell ASIC.

**Capabilities:**
- PTT health dashboard: entry status (IDLE/WAITING/ACTIVE/FAULTED) per program
- Shore query panel: search registered programs by name, tag, type
- Ward alerts: STALL / SPIKE / ANOMALY / SILENT with escalation history
- Workspace panel: set inputs, run, see outputs (same as VM mode surface)
- Bridge traffic: packet counts on INBOUND/OUTBOUND/MONITOR per pond
- No cell inspector, no bus monitor, no tick stepper — hardware doesn't expose these

**What the OS exposes (silicon mode data sources):**
  PTT entries    → Ward health per pond, per port (TILE_IN and PRIMITIVE status)
  Shore queries  → program discovery filtered by user identity + view_mask
  Bridge counts  → MONITOR bridge emission counts (anomaly detection)
  COMPANION log  → restart/isolate/migrate events

**Identity and whitelist enforcement:**
  Every Shore query is filtered by the current user's identity and view_mask.
  `ws list` in silicon mode:
    user identity
      → Shore query (programs visible to this identity)
        → view_mask filter
          → PTT entries for visible programs
            → display {name, status, inputs, outputs}
  This is OS-level behaviour. The CLI is the surface; Shore is doing the work.

---

### Prerequisites for silicon mode (not yet built)

- [ ] Shore user table — identities registered with Shore, each with view_mask
      Shore currently has no concept of a logged-in user or per-user visibility.
      Need: register_user(identity_id, view_mask) in shore.py / shore_v2.py.
      view_mask controls which PTT entry types / ponds are visible to this user.
      Test: two users with different view_masks see different Shore query results.

- [ ] ws list routed through Shore — not named_values
      WorkspacePond.list_programs() queries Shore for programs registered to
      this workspace's identity. Returns [{name, pond_id, status, inputs, outputs}].
      Filtered by view_mask. Replaces direct _active_programs dict access.
      Test: program not on whitelist does not appear in ws list results.

- [ ] Workbench reads PTT health from Ward — not UniCellArray
      Silicon mode dashboard polls Ward.health_report() for PTT entry statuses.
      Ward.health_report() returns {entry_label: {status, tick_count, last_tick_age}}.
      No direct UniCellArray access. Same interface works on VM and silicon.
      Test: ward reports STALL when a running program stops emitting.

- [ ] Session identity management
      Workbench startup: who is the current user?
      VM mode: default to a single implicit identity (no auth required).
      Silicon mode: identity set at launch (--identity user_alice or from config).
      Identity hash registered with Shore's user table at session start.
      COMPANION issues a session token; all Shore queries carry it.
      Test: launching two workbench instances with different identities produces
      isolated views — each sees only their own programs.

- [ ] Workbench mode toggle in UI
      Header bar: [VM — Microscope ▾] or [Silicon — Terminal ▾]
      VM mode shows: cell inspector tab, bus monitor tab, tick stepper
      Silicon mode shows: PTT dashboard tab, Shore query tab, Ward alerts tab
      Workspace panel (inputs/outputs/run) is identical in both modes.
      Toggle is available when running in VM mode only — silicon mode is fixed
      (you can't pretend to be silicon if you're actually connected to silicon).

- [ ] FPGA budget enforcement in VM
      TileLibrary.get(name) checks cell_count against array.cell_budget.
      If cell_count > budget: compile fails with clear error and vmOnly flag set.
      imago compile ... --cells fpga  respects the budget at CLI level too.
      Composer cell budget bar turns red when design exceeds FPGA budget.
      Test: adder_int32 (483 cells) compiles on vm, fails on --cells 64 (iCEBreaker).

- [ ] GPU/large array path at startup (Standalone mode)
      --mode vm --cells standalone (or no --cells flag) uses full Python array.
      Future: --cells gpu routes to gpu_array.py (numpy/CUDA backend).
      This is the path for 1000s-of-cells programs — postcode sort n=64,
      FP32 neural networks, large bitonic sorts.
      No mode switch once launched (array size is fixed at startup).
      gpu_array.py already exists — needs integration with workbench startup.

---

### Workbench startup flow (target)

    imago-workbench [--mode vm|silicon] [--cells fpga|standalone|N] [--identity ID]
                    [--fpga /dev/ttyUSB0]

    No flags:          VM mode, standalone (unbounded), implicit identity
    --mode vm          VM mode, prompt for cell budget in UI
    --cells fpga       VM mode, mirror connected FPGA budget (requires --fpga)
    --cells 8192       VM mode, explicit budget
    --mode silicon     Silicon/FPGA terminal mode, requires --fpga
    --fpga PORT        Connect to FPGA over UART bridge
    --identity ID      Set user identity (silicon mode and multi-user VM)

    On launch: startup selector dialog if no --cells flag given.
    Once array is initialised, mode is locked for the session.

---

### Relationship to existing items

This block supersedes and expands:
  - MIGRATION_TODO § Windowed GUI / virtual desktop (Tier 6 doc item)
    The "window = display pond" concept is correct but premature — implement
    the two-mode workbench first, then the display pond layer on top.
  - MIGRATION_TODO § VM performance mode (FPGA-deferred)
    The standalone/GPU path is the large-array path. numpy vectorisation
    unlocks it. Both should land together post-silicon validation.
  - MIGRATION_TODO § FPGA/silicon workbench mode — PTT-only data source
    This block is the full spec for that item. Mark it as superseded below.

---

## Hardware notes — added 2026-05-11 (late)

### Thermal indicator → PTT DEVICE entry
The iCEBreaker / Kintex-7 card has a thermal sensor. Route its output through
the PTT as a TYPE_DEVICE entry so Ward monitoring applies automatically.

- [ ] Wire thermal sensor to dedicated bus address at FPGA bring-up
      Thermal sensor fires periodically → writes temperature reading to bus.
      Register as PTT TYPE_DEVICE entry with:
        staleness_threshold: card datasheet max sample interval + margin
        spike_threshold:     Tjunction_max (85°C for iCE40UP5K, 125°C for Kintex-7)
      Ward raises SILENT if readings stop (sensor fault / card disconnect).
      Ward raises SPIKE if temperature exceeds threshold.
      COMPANION rule: on thermal SPIKE → throttle clock / isolate pond / shutdown.
      No new architecture needed — thermal is just another DEVICE pond input.
      Test: disable sensor feed, confirm Ward raises SILENT within staleness window.

### Memory model — latch vs self-addressing
Clarification on when to use each (for implementation and documentation):

GS_LATCH (dominant pattern):
  - General storage: holds a value and re-emits every cycle until overwritten
  - Use for: storage ponds, accumulators, state machines, PTT entry values,
    any cell that needs to persist a value across ticks
  - This is the default memory cell — use unless there's a specific reason not to

Self-addressing (deliberate, narrower use):
  - Cell whose output_address == its own input_address (feeds back to itself)
  - Use for: counters (increment own value each tick), shift registers,
    in-place mutation where the cell transforms its own previous output
  - Distinction: latch says "hold this value", self-addressing says
    "transform this value each tick"
  - Already used in for-loop counter pattern in compiler.py

Both are correct and needed. Latch is the default. Self-addressing is deliberate.
Documentation should make this distinction explicit — currently implied but not
stated clearly in ARCHITECTURE.md or RUNNING.md. Add a note when updating those.

---

## VM vs FPGA Diff Tool — freeze-and-compare

Simplest and most accurate method to validate silicon matches the VM model.
Freeze both sides after N ticks, diff the JSON files address by address.
Any divergence shows exactly which cell, which address, which value disagrees.

### Method

```
VM path:
  load program.icm
  inject inputs
  run N ticks
  freeze() → vm_state.json

FPGA path:
  load program.icm via icm_loader
  inject same inputs via UART
  run N ticks (clock N pulses)
  freeze() → fpga_state.json

Diff:
  load both JSONs
  compare address by address
  report: {address: {vm: X, fpga: Y}} for any mismatch
  exit 0 if identical, exit 1 with mismatch report if not
```

### Freeze format (agreed schema for both sides)

```json
{
  "program":   "not_gate",
  "icm_hash":  "sha256 of icm file",
  "ticks":     10,
  "inputs":    {"a": 1},
  "cells": {
    "0x1000": {"output_value": 0, "armed": false},
    "0x1001": {"output_value": 1, "armed": false}
  },
  "bus": {
    "0x1001": 1
  },
  "ptt": {
    "not_gate.result": "IDLE"
  }
}
```

### Prerequisites

- [ ] FPGA read-back command in Verilog state machine
      New UART command: READ_CELL(addr) → returns current output_value.
      One new state in the CFG state machine: CFG_READ.
      fpga_bridge.read_cell(addr) → int on Python side.
      Without this the FPGA side can't produce a freeze — cells don't
      report their state unless explicitly read out.

- [ ] freeze() standardised output format
      controller.freeze() currently snapshots region cell values.
      Extend to emit the agreed JSON schema above.
      FPGA freeze: loop read_cell() over all configured addresses,
      build same JSON structure. Both sides produce identical schema.

- [ ] imago_diff.py — the diff tool
      Usage:
        python3 imago_diff.py vm_state.json fpga_state.json
      Output:
        MATCH   — all addresses identical
        MISMATCH — {address: {vm: X, fpga: Y}} for each divergence
        MISSING  — addresses present in one file but not the other
      Exit 0 on match, exit 1 on any mismatch.
      Optional: --ticks N to show first tick of divergence (requires
      per-tick freeze files: vm_tick_001.json ... fpga_tick_001.json).

- [ ] Test programs for diff validation
      Start simple, add complexity:
        not_gate.icm     — 1 cell, 1 tick, simplest possible
        and_gate.icm     — 1 cell, two-input (tests inB/SYNC_WAIT)
        adder_int32.icm  — 483 cells, depth 2, tests pipeline
        lif_neuron.icm   — stateful, tests GS_LATCH persistence
      Run each with N=1, N=5, N=pipeline_depth ticks.
      Any mismatch at N=1 is a configuration error.
      Any mismatch at N>1 is a timing or state error.

### What the diff will reveal

- Configuration errors: cell loaded with wrong gate_state → mismatch at tick 1
- Timing errors: cell fires one tick late/early → mismatch at tick N+1
- inB/SYNC_WAIT: B-input gating works correctly → and_gate diff will show it
- GS_LATCH persistence: lif_neuron holds state → diff across multiple ticks
- Bus OR behaviour: multiple cells driving same address → check wired-OR holds

### This is the green light for numpy

Once imago_diff.py reports MATCH for all test programs across all tick counts,
the cell-by-cell VM model is confirmed correct. At that point numpy vectorisation
can proceed — you are optimising a known-correct reference, not a guess.

Tag: FPGA-dependent — requires JTAG bring-up (~21 May 2026).

---

## Workbench — Bridge-pair-per-tile model (2026-05-12)

Each input panel tile in the workbench is backed by exactly one bridge pair.
The knowledge stays where it belongs:

  Program pond: knows only MY_INBOUND and MY_OUTBOUND addresses. Nothing else.
  Workspace pond: maps tile_N → {bridge_in_addr, bridge_out_addr, handle_id}
  Bus: sees only addresses — no concept of tiles, completely transparent

```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ not_gate    │ │ adder_int32 │ │ lif_neuron  │
│ a: [1]      │ │ a: [5]      │ │ v_mem: [10] │
│             │ │ b: [3]      │ │ thresh: [15]│
│ result: 0   │ │ result: 8   │ │ spike: 0    │
│ [Run] [New] │ │ [Run] [New] │ │ [Run] [New] │
└─────────────┘ └─────────────┘ └─────────────┘
```

Each tile has its own dedicated INBOUND and OUTBOUND bridge pair on the
workspace pond. The workspace INBOUND is NOT shared — each tile gets its
own address so results land in the correct tile's output box unambiguously.

Tile operations:
  Add tile:    allocate new bridge pair → connect(workspace, new_pond, slot=N)
  Replace:     disconnect_program(slot_N) → connect(workspace, new_pond, slot=N)
  Remove:      disconnect_program(slot_N) → free bridge pair, clear tile

Security: program pond whitelist has exactly one entry (workspace identity).
Program has no knowledge of other tiles or other programs. Each bridge pair
is a private channel. Max 8 tiles (workspace quota).

- [ ] Implement bridge-pair-per-tile in spawn_workspace()
      Allocate 8 INBOUND + 8 OUTBOUND bridge slots at workspace creation.
      connect(workspace, program, slot=N) wires slot N's bridge pair.
      Each slot has distinct bus addresses — no shared INBOUND.
      Workbench tile N reads result from slot N's INBOUND address only.

- [ ] Workbench input panel: tile grid (max 8)
      Left panel divided into up to 8 tiles.
      Each tile: program name, input fields, result area, [Run] [New/Replace] buttons.
      [New] → launch_program() into next free slot.
      [Replace] → disconnect then launch into same slot.
      Results populate bottom of their own tile only.

---

## Array Pond — Design Options (think on it)

A user-facing array (list, table, matrix) needs both data and location.
Single bridge pair, two sequential calls — address gives pointer, data is data.
The cell model enforces sequencing via SYNC_WAIT naturally.

### Protocol (two calls, one bridge pair)

```
Call 1: workspace writes target_index → array pond INBOUND
        address latch cell receives index, holds it

Call 2: workspace writes value → array pond INBOUND
        data router cell: A input = value, B input = latched address
        SYNC_WAIT: fires only when both A and B have arrived
        routes value to cell at latched address
        result fires back → array pond OUTBOUND → workspace tile
```

The array pond interface to the workspace is identical to any other program pond
— one INBOUND, one OUTBOUND, one bridge pair. The two-call protocol is internal.
Sequencing is enforced by SYNC_WAIT, not by software. Clean.

### Option A — Fixed-size array (simpler, do first)

Array size declared at compile time. N cells pre-allocated.
Addresses 0..N-1 are compile-time constants baked into routing cells.
The ICM contains the full cell map for the array — no dynamic allocation.

Pros:
  - Simple to implement — spawn_pond_from_icm handles it like any other program
  - Cell count is known at compile time → fits FPGA budget check
  - Routing cells are static → no address resolution overhead
  - Can be compiled to .icm and reused

Cons:
  - Size fixed at compile time — can't grow
  - Large arrays use many cells (1000-element int32 array = ~500k cells)
  - FPGA budget limits practical size on iCEBreaker/Kintex-7

Address latch reset after each pair:
  Option A1: address latch is GS_PASS (holds for one tick only)
             Data arrives on B input same tick → SYNC_WAIT fires → done
             Next address overwrites naturally — no explicit reset needed
  Option A2: address latch is GS_LATCH + explicit CLEAR signal after fire
             More robust for slow data (data arrives later than one tick)
             Requires a third signal (CLEAR) — slightly more complex

A1 is simpler and correct if workspace sends address+data in consecutive ticks.
A2 is safer if there could be a gap between address and data calls.

### Option B — Dynamic array (harder, do later)

Array pond allocates cells on demand as values are written.
Sparse — only written addresses occupy cells. Unwritten addresses return 0.

Pros:
  - Memory-efficient for sparse arrays
  - Can grow beyond fixed compile-time size
  - Natural fit for hash maps, sparse matrices

Cons:
  - Requires pond expansion — cell allocation at runtime
  - Address resolution needs a lookup structure (itself a cell network)
  - Much harder to fit on FPGA — probably VM-only initially
  - Cell count not known at compile time → vmOnly flag by default

### Option C — Segmented array (middle ground)

Array divided into fixed-size segments (pages). Each page is a fixed array pond.
A directory pond maps index → page pond. Two-level lookup.

Pros:
  - Pages fit on FPGA individually
  - Can grow by adding pages (new pond per page)
  - Each page is a normal fixed-size array pond

Cons:
  - Cross-page access needs directory lookup (extra round-trip)
  - Directory pond is itself a small array pond
  - More bridge pairs (one per page + one for directory)

### Option D — Host-backed array (hybrid, pragmatic)

For very large arrays that won't fit in cells: array lives in host memory,
array pond is a thin proxy that translates cell read/write to host memory ops.
On silicon: host memory accessed via PCIe/DMA. On VM: Python dict.

Pros:
  - Unlimited size
  - Fast random access (host memory is fast)
  - Works on both VM and silicon

Cons:
  - Not pure cell architecture — hybrid
  - Latency: host memory round-trip adds ticks
  - Breaks portability story (.icm can't encode host memory layout)
  - Only appropriate for data that doesn't need cell-speed processing

### Recommendation (for discussion)

Start with Option A (fixed-size, A1 variant — PASS latch, consecutive calls).
It's honest to the architecture, fits the .icm model, works on FPGA.
Add Option C (segmented) when larger arrays are needed post-Kintex-7.
Option B (dynamic) and D (host-backed) are future work / specialist use cases.

The two-call protocol over one bridge pair is the right interface regardless
of which option is chosen internally — the workspace tile experience is identical.

- [ ] Design decision: choose Option A, B, C, or D (or combination)
- [ ] Option A: implement fixed-size array pond compiler
      array_int32(N) → .icm with N storage cells + address latch + data router
      SYNC_WAIT data router: A=value, B=latched_address, fires when both arrive
      Address latch: GS_PASS (A1) or GS_LATCH+CLEAR (A2)
      Test: array[0]=5, array[1]=3, read array[0] → 5, read array[1] → 3
- [ ] Option A: workbench tile for array programs
      Input tile shows: index field + value field + [Write] [Read] buttons
      Write: two calls (index then value) → fires → confirms
      Read: one call (index) → fires → result appears in tile output
- [ ] Option C: segmented array using page ponds (post-Kintex-7)

---

## Signed data over bridges — type-aware bridge pairs (think on it)

Currently bridges handle unsigned data only. Signed values need the complement
cell model (primary + complement at primary+1). This has cascading implications
across the whole stack.

### The problem

A signed int32 value occupies two bus addresses:
  primary_addr:     bits 0-31 (magnitude)
  primary_addr + 1: complement (type bits 27-28 = GS_TYPE_SIGNED)

A bridge currently wires one address. For signed data you need a bridge pair
for the data alone — primary and complement travel together or the type
information is lost in transit.

If that signed data also goes to an array pond, you need:
  - Data bridge pair (primary + complement) — 2 addresses
  - Pointer bridge (array index) — 1 address
  Total: 3 bridge addresses per signed array operation

### Cascading changes required

- [ ] ICM format: encode bridge type alongside port addresses
      Currently inputs/outputs store a single bus address per named port.
      For signed ports: store {primary_addr, complement_addr, type}.
      inputs_32 already stores 32 bit-addresses — extend to inputs_signed
      for the complement cell address alongside the primary.
      Affects: icm_format, program_builder, imago/cli.py compile path.

- [ ] Compiler: emit complement cell for signed outputs
      When a function returns a signed type, the compiler must emit both
      the primary output cell and its complement cell, and declare both
      addresses in the ICM outputs_signed field.
      compiler_int32.py: signed return type → two output addresses in ICM.

- [ ] Composer: ports tab shows type selector per port
      Ports tab currently: name + address + direction.
      Add: type selector (unsigned / signed / alpha / datetime).
      For signed: automatically allocates primary + complement address pair.
      Cell budget increases by 1 per signed port (complement cell).

- [ ] Pond initialisation: bridge allocates address pairs for signed ports
      spawn_pond_from_icm() currently registers one PTT TILE_IN entry per input.
      For signed inputs: register primary address AND complement address.
      connect() wires both addresses in the bridge pair.
      The complement address is implicit (primary + 1) but must be explicit
      in the bridge wiring so the workspace knows to read both.

- [ ] Array pond with signed data: 3-address protocol
      address call:        send index → pointer bridge address
      data primary call:   send value → data bridge primary address
      data complement call: send type bits → data bridge complement address
      All three must arrive before the array cell fires (SYNC_WAIT on all 3).
      OR: pack index + type into a single call using high/low word split.
      Design decision: 3 separate calls vs packed calls — think on it.

### Dependency chain
ICM format → compiler → composer → pond init → bridge wiring → array pond.
All touch the same data path. Do as a single coordinated change, not piecemeal.
Tag: post-JTAG, after bridge-pair-per-tile workbench is stable.

---

## Unlimited word width — beyond 32 bits (thought experiment, capture it)

Why stop at 32 bits? The cell model has no inherent word width limit.
Using multiples of cells in parallel gives effectively unlimited precision.
The bus capacity is the only practical ceiling.

### The idea

A 32-bit value uses 32 cells firing in parallel on the bus.
A 64-bit value uses 64 cells. A 4096-bit value uses 4096 cells.
All fire in the same tick — the wired-OR bus handles it transparently.
The pipeline depth stays the same (determined by the longest carry chain,
not the word width) assuming parallel prefix arithmetic scales correctly.

### What this enables

- 64-bit integers: natural extension of the int32 tiles
  INT64_ADD: ~1000 cells, same depth as INT32_ADD (Kogge-Stone scales)

- Arbitrary precision: 128-bit, 256-bit, 1024-bit arithmetic
  Cryptography: RSA/ECC key operations in a single tick pipeline
  Each key size is a different tile, compiled to .icm, portable

- Full frame video manipulation:
  4K frame = 3840 × 2160 × 3 channels × 8 bits = ~200 million bits
  Per-pixel operations (colour transform, filter kernel) fire in parallel
  One tick per operation if cells are available
  Bus becomes the bottleneck before compute does
  Practical on a large ASIC — not on iCEBreaker or Kintex-7
  But the architecture supports it without modification

- Neural network weights:
  A 1024-neuron layer with 1024 inputs = 1M weights
  All multiply-accumulate operations in parallel = one tick per layer
  Again bus-limited in practice, architecture-unlimited in principle

### The bus ceiling

The wired-OR bus is the real constraint. Every cell firing in the same tick
writes to one address. If N cells all write to different addresses, N bus
lines are active simultaneously. Physical bus width = number of addressable
lines that can be active in one tick without collision.

On iCEBreaker: bus is implemented as FPGA routing fabric — limited by
available routing resources. Wide words consume routing rapidly.
On a custom ASIC: bus width is a design parameter. A 4096-bit bus is
physically large but not architecturally impossible.

The architecture is honest about this: word width scales with bus width,
bus width scales with silicon area. No magic, just geometry.

### Practical near-term steps

- [ ] INT64: extend compiler_int32 to 64-bit (double the tile width)
      INT64_ADD: Kogge-Stone at 64-bit — ~1000 cells, depth ~3
      Natural test: 64-bit timestamps, file sizes, large counters
      Already implied by the complement cell model (primary + complement = 64-bit)

- [ ] Document the scaling principle in ARCHITECTURE.md
      Word width is not fixed at 32. It is a design choice per program.
      The cell model, bus, and tile system all scale cleanly.
      Bus width is the practical ceiling. Silicon area is the cost.
      Add a section: "Word width and bus scaling" after the type system section.

- [ ] Far future: video frame pond
      A display pond that processes one 4K frame per tick.
      Each pixel is a cell cluster. Colour transforms are tile pipelines.
      Bus width = frame width in bits. Tick rate = frame rate.
      At 24 MHz and 4K: ~180 ticks per frame at 24fps — very achievable
      if the bus is wide enough. This is the ASIC target, not FPGA.
      Capture as an architectural horizon — not a near-term deliverable.

Tag: thought experiment / architectural horizon. No blocking dependencies.
INT64 is the practical near-term step. Video frame pond is the far horizon.

---

## Contiguous cell allocation for wide words (follows from unlimited width)

For wide words (int64, int128, video pixels, large datasets) cells must be
spatially contiguous — allocated as a consecutive address block. This minimises
the signal path between adjacent cells and keeps the carry chain short.

### Why contiguity matters

Current allocator assigns addresses from a pool without caring about adjacency.
For int32 this is fine — 32 cells, short carry chains, routing is manageable.
For wider words the inter-cell signal path grows with address distance.
On FPGA: non-contiguous cells route through more fabric → longer timing paths.
On ASIC: contiguous cells are physically adjacent → minimal wire length.

Layout for a wide word (N cells):
```
[cell_0][cell_1][cell_2]...[cell_N]  ← one N-bit value, laid out as a strip
[cell_0][cell_1][cell_2]...[cell_N]  ← next value (next row)
[cell_0][cell_1][cell_2]...[cell_N]  ← next value
         ↑
         bus runs along here
```

Width scales horizontally (more cells = wider word, same pipeline depth).
Throughput scales vertically (more rows = more values per tick).
Pipeline depth stays constant — Kogge-Stone keeps it at ~2-3 ticks
regardless of word width, as long as cells are contiguous.

### The allocator change

- [ ] compiler_int32.py / program_builder.py: allocate_block(N) method
      Allocates N consecutive addresses as a single block.
      Returns base_address — bits occupy base_address + 0..N-1.
      Currently: addresses allocated one at a time from a pool.
      Change: for multi-bit values, reserve a contiguous block upfront.
      Existing int32 path already effectively does this (32 consecutive
      bit-addresses) — make it explicit and generalisable to any N.

- [ ] Int32Placer: enforce contiguous placement for tile inputs/outputs
      When placing a tile, input and output bit-address blocks should be
      contiguous. Currently the placer allocates addresses sequentially
      which tends to produce contiguous blocks in practice — make this
      a guarantee rather than a side effect.

- [ ] Address allocator: add alloc_block(N) to NORBuilder / Int32Placer
      NORBuilder.alloc() currently allocates one address at a time.
      Add NORBuilder.alloc_block(N) → base_address (reserves N consecutive).
      Used by all wide-word tile constructors (int64, int128, etc.)
      Fallback: if N consecutive addresses unavailable, raise AllocationError
      with clear message — don't silently allocate non-contiguous.

- [ ] ICM format: record contiguous block allocations
      For wide-word ports, ICM should record base_address + width rather
      than listing all N addresses individually.
      inputs_32 currently lists all 32 addresses — fine for int32.
      For int64+: inputs_wide: {"a": {"base": 4096, "width": 64}}
      Loader reconstructs bit-addresses as base + 0..width-1.
      More compact, makes contiguity explicit and verifiable.

### Scaling properties (for reference)

  int32:   32 cells/value,  depth ~2   (Kogge-Stone, verified)
  int64:   64 cells/value,  depth ~3   (estimated, same structure)
  int128:  128 cells/value, depth ~4
  1080p pixel (24-bit): 24 cells, depth ~2 per pixel
  1080p frame: 2,073,600 pixels × 24 bits = 49,766,400 cells
  4K frame:    8,294,400 pixels × 24 bits = 199,065,600 cells

Bus width (simultaneous active addresses) = total cells firing per tick.
This is the silicon area / routing constraint — not an architectural limit.
A purpose-built ASIC sizes the bus for its target workload.
Current FPGA targets (iCEBreaker: 64 cells, Kintex-7: ~1500) are dev boards.
A production ASIC for video would size accordingly from the start.

### Near-term priority

alloc_block(N) in NORBuilder is the small change with immediate payoff:
  - Makes int32 allocation explicit rather than coincidental
  - Enables int64 tiles without architectural changes
  - Sets up the path to arbitrary width cleanly

Tag: do alloc_block(N) before int64 tile work. Low risk, high leverage.

---

## Packet-confirmed counter routing for bridge depth (key mechanism)

A neat trick that gives bridge protocols arbitrary depth without extra cells,
extra bridge pairs, or timing dependencies. The counter increments only on
confirmed packet arrival — not on clock ticks.

### The mechanism

```
INBOUND bridge
     ↓
SELECT cell (routes based on counter value)
  count=0 → address latch
  count=1 → data primary
  count=2 → data complement (signed)
  count=N → final slot
     ↓
Each slot fires on arrival → output = confirmation signal
     ↓
Confirmation → counter increment cell
Counter increments ONLY when packet confirmed, not on tick
     ↓
count=N confirmed → CLEAR signal → counter resets to 0
Ready for next packet sequence
```

### Why packet-confirmed not tick-based

Tick-based counting breaks under bus contention or variable latency —
the counter advances regardless of whether valid data arrived.
Packet-confirmed counting means the counter only moves when data
actually landed in the correct slot. Self-synchronising. No timing
dependency. Naturally handles variable inter-packet gaps.

### Bridge depth = counter reset value

The depth of the bridge protocol is just the counter's reset value N.
Declared at compile time, encoded in the ICM as a bridge property.
The mechanism is identical regardless of depth:

  N=1: single value bridge (current unsigned model)
       count=0: data → confirmed → CLEAR

  N=2: index + data (unsigned array)
       count=0: address/index → confirmed → count=1
       count=1: data[0:31]   → confirmed → CLEAR

  N=3: index + signed data (signed array)
       count=0: address/index    → confirmed → count=1
       count=1: data primary     → confirmed → count=2
       count=2: data complement  → confirmed → count=3 → CLEAR

  N=4: index + int64 data
       count=0: address/index    → confirmed → count=1
       count=1: data[0:31]       → confirmed → count=2
       count=2: data[32:63]      → confirmed → count=3
       count=3: complement       → confirmed → count=4 → CLEAR

  N=K: arbitrary struct / wide word — same pattern, different reset value

### Natural backpressure

If packet N has not confirmed, packet N+1 cannot route correctly —
SELECT is still pointing at slot N. The counter simply won't advance.
This is free backpressure from the cell model itself — no extra logic.
The workspace must wait for confirmation before sending the next packet.
Confirmation = the SELECT cell output fired = data landed in slot.

### Bridge property in ICM

The counter reset value becomes a bridge property alongside the port address:

```json
"inputs": {
  "array_write": {
    "address": 4096,
    "bridge_depth": 3,
    "packet_types": ["index", "data_primary", "data_complement"]
  }
}
```

Composer sets bridge_depth when user declares port type.
Compiler emits correct counter reset value automatically from data type:
  unsigned int32:  bridge_depth=1
  unsigned array:  bridge_depth=2
  signed int32:    bridge_depth=2 (primary + complement)
  signed array:    bridge_depth=3
  int64 array:     bridge_depth=4
  signed int64 array: bridge_depth=5

### Implementation

- [ ] Counter cell pattern: SELECT + confirmed-increment + CLEAR feedback
      SELECT cell: gate_state routes A→slot based on counter value
      Counter: GS_LATCH, self-addressing, increments on confirmation signal
      CLEAR: final slot confirmation → writes reset value to counter input
      All standard cells, no new gate types needed.

- [ ] NORBuilder: emit_packet_counter(N, base_address) helper
      Emits the SELECT + counter + CLEAR cell cluster for depth-N protocol.
      Returns {inbound_addr, slot_addrs[0..N-1], confirmation_addr}.
      Used by program_builder when emitting bridge cells for typed ports.

- [ ] ICM format: bridge_depth field on port declarations
      Add bridge_depth (int, default 1) to input/output port entries.
      Loader uses it to configure the SELECT/counter cluster at pond init.
      Backwards compatible: missing bridge_depth = 1 (current behaviour).

- [ ] Compiler: set bridge_depth from port type automatically
      compiler_int32.py: signed return → bridge_depth=2
      Array ports: bridge_depth = 1 + (1 if signed else 0) + extra_packets
      Composer: type selector sets bridge_depth, shown in ports tab.

- [ ] SYNC_WAIT on final processing cell
      The cell that actually uses all N packets (e.g. array store cell)
      has SYNC_WAIT on all N slot addresses.
      Fires only when all N packets have confirmed and landed.
      This is the existing SYNC_WAIT mechanism — no changes needed.

### Key properties

- No extra cells per packet beyond the counter cluster (amortised over all packets)
- No extra bridge pairs regardless of data width or type
- No timing dependency — confirmation-driven throughout
- Arbitrary depth — just a different reset value N
- Self-synchronising — counter cannot get ahead of data
- Natural backpressure — SELECT blocks until current slot confirms
- Composable — bridge_depth is a port property, not a global setting
- Works for OUT bridge too — result packets returned in sequence

This mechanism resolves: signed bridge pairs, array indexing, wide words,
and arbitrary struct passing — all with the same counter/select pattern.

---

## Bridge counter — offset addressing + count tag integrity (extension)

Extension to the packet-confirmed counter mechanism. Two refinements that
simplify the implementation and add inter-pond data integrity checking.

### Counter as address offset (simplification)

Rather than a SELECT cell routing to named slots, the counter value is used
directly as an offset from the base address:

```
base_address + counter = current slot address

count=0 → base+0  (index / address)
count=1 → base+1  (data primary)
count=2 → base+2  (data complement / signed)
count=3 → base+3  (int64 high word)
...
count=N → base+N  (final packet)
```

No SELECT cell needed — the counter IS the routing. Each arriving packet
lands at base+counter automatically. The SYNC_WAIT on the processing cell
holds until all slots base+0..base+N are filled, then fires.

Simpler cell layout:
  Counter cell (GS_LATCH, self-addressing, confirmed-increment)
  SYNC_WAIT cell watching base+0..base+N
  CLEAR feedback from final slot confirmation → counter reset

Reduces cell count vs SELECT-based routing. Offset addressing is
a natural fit for the existing address model — no new gate types.

### Count tag as integrity check (inter-pond data validation)

Each packet carries an external count tag — "I am packet N of this sequence".
The receiving bridge has an internal counter. On arrival, the tag is compared
to the internal counter value before the slot is accepted.

```
Packet arrives at base+counter:
  external_tag == internal_count → in sequence → accept → increment counter
  external_tag != internal_count → misalignment → reject → flag error
```

This catches all inter-pond data integrity problems:
  - Dropped packet:      counter jumps (external tag skips a value)
  - Duplicate packet:    counter repeats (external tag seen twice)
  - Out-of-order packet: counter mismatch (external tag != expected)
  - Corrupted tag:       tag value doesn't match any expected value

### Using ECC cell structure for the tag check

Full Hamming SECDED ECC is not yet implemented. But the count tag check
only needs error DETECTION, not correction — a partial ECC implementation
is sufficient and appropriate here.

The ECC cell structure (when implemented) provides:
  - Syndrome computation: compare received tag against expected value
  - Syndrome == 0 → match → packet accepted
  - Syndrome != 0 → mismatch → packet rejected

For now (pre-ECC implementation): a simple comparison cell suffices —
XOR the external tag with the internal counter value, if result != 0
the packet is misaligned. This is a 1-cell check, no full ECC needed.

```
Tag check cell:
  A input: external_tag (arrives with packet)
  B input: internal_counter (current expected value)
  gate: XOR → 0 = match, non-zero = mismatch
  
  XOR output = 0 → enables SYNC_WAIT slot (packet accepted)
  XOR output ≠ 0 → SYNC_WAIT never releases → pond stalls
```

### Error handling via Ward/COMPANION

A misaligned packet causes SYNC_WAIT to never release.
The processing cell never fires. The pond stops emitting.
Ward detects STALL (no emission beyond stall_threshold).
Ward escalates to COMPANION with reason: BRIDGE_ALIGNMENT_ERROR.
COMPANION can: request retransmit from sending pond, isolate faulty pond,
or flag the bridge pair for diagnostic inspection.

No new error handling needed — the existing Ward/COMPANION machinery
handles it transparently. The count tag check just gives the Ward a
clear signal to work with rather than a mysterious stall.

### Tag encoding

Two options — think on it:

Option A: tag in high bits of the data word
  Packet = [tag(4 bits) | data(28 bits)]
  Reduces effective data width by tag width
  Simple — one bus address carries both tag and data
  Suitable for narrow protocols (depth ≤ 16 packets)

Option B: tag on a dedicated parallel address (base+N+1)
  Tag arrives alongside data on a separate bus address
  Full data width preserved
  One extra address per packet sequence (not per packet)
  Suitable for wide words where bit loss is unacceptable

Option B preferred for int32+ data — tag address is a small overhead
and preserves full data integrity. Option A acceptable for index/pointer
packets where 28 bits is sufficient.

### Relationship to full ECC (future)

When full Hamming SECDED ECC is implemented:
  The count tag check becomes one input to the ECC syndrome.
  Syndrome covers both data bits AND count tag simultaneously.
  Single-bit errors in data OR tag are corrected automatically.
  Multi-bit errors detected and flagged.
  The count tag check cell is replaced by the ECC syndrome cell —
  same interface, stronger guarantees.

The current XOR check is a placeholder that fits cleanly into the
same cell slot when ECC arrives. No architectural rework needed.

### Implementation notes

- [ ] Counter offset addressing: replace SELECT with base+counter scheme
      Simplifies cell layout, reduces cell count vs SELECT routing.
      NORBuilder.emit_packet_counter(N, base_addr) emits counter cluster
      with offset addressing. Slots at base+0..base+N.

- [ ] Count tag check cell: XOR(external_tag, internal_counter)
      Emitted alongside each bridge INBOUND cluster.
      Output gates the SYNC_WAIT for that slot.
      Tag width: 4 bits sufficient for depth ≤ 16 (covers all current cases).

- [ ] Tag encoding: Option B (dedicated parallel address) for int32+ ports
      ICM records tag_address alongside data_address for typed ports.
      Composer shows tag address in ports tab (auto-allocated, read-only).

- [ ] Ward: BRIDGE_ALIGNMENT_ERROR reason code on STALL escalation
      When a stall originates from a tag-check cell, Ward escalation
      carries BRIDGE_ALIGNMENT_ERROR rather than generic STALL.
      COMPANION rule: BRIDGE_ALIGNMENT_ERROR → request retransmit.

- [ ] Full ECC integration (future, post-JTAG)
      Replace XOR tag check with ECC syndrome cell when ECC is implemented.
      Same slot, same interface, stronger guarantees. No structural change.

Note: this mechanism needs rehashing as implementation approaches —
the idea is sound, the cell-level details may need adjustment once
the counter offset scheme is working on real silicon.
Tag: post-JTAG, after basic bridge-pair-per-tile is stable.

---

## ASIC Tape-out Investigation — free/low-cost shuttle runs

The Verilog RTL exists (fpga/verilog/unicell.v). The hard part is done.
Investigate free and low-cost shuttle options for real silicon validation
beyond FPGA — the architecture is logic-only (no analogue, no memory macros)
which makes it a strong candidate for open-source PDK flows.

### Options to investigate

- [ ] Efabless chipIgnite (priority — investigate first)
      Free shuttle for qualifying open-source projects.
      Process: SKY130 (130nm SkyWater open PDK).
      Several runs per year, application required.
      Open-source project + novel architecture = strong candidate.
      Flow: OpenLane RTL-to-GDS (open source, works with SKY130).
      URL: https://efabless.com/chipignite
      Action: check current shuttle schedule, review submission requirements.

- [ ] TinyTapeout
      ~$100-300 for a small tile on a shared die.
      Limited area (~250 standard cells per tile, can buy more tiles).
      Good for: proof-of-concept cell cluster, validate cell model on silicon.
      Simpler submission process than chipIgnite.
      URL: https://tinytapeout.com
      Action: estimate how many UniCell cells fit in one tile.

- [ ] Google/Efabless open shuttle (MPW)
      Periodic multi-project wafer runs, free for open-source designs.
      More area than TinyTapeout, less than a full run.
      Requires OpenLane flow + SKY130 PDK.
      Action: check current MPW schedule at efabless.com.

- [ ] Europractice / IMEC
      Subsidised shuttle runs for academic/research projects.
      Requires university affiliation or research institution connection.
      More process options (28nm, 22nm available).
      Action: check if any affiliation or partnership is possible.

### What UniCell needs for tape-out

RTL: fpga/verilog/unicell.v — exists, hand-written, silicon-validated on FPGA.
Needs:
  - Standard cell mapping to SKY130 library (Liberty files available in PDK)
  - OpenLane configuration for the design
  - Timing closure at target frequency (SKY130 realistic: 50-100 MHz)
  - Area estimate to confirm fit within shuttle tile

UniCell advantages for open PDK tape-out:
  - Logic-only: no SRAM macros, no analogue, no PLLs
  - Regular structure: repeating cell pattern suits automated place-and-route
  - Open source architecture: matches open shuttle ethos exactly
  - Novel: parallel NOR-universal cell array is a genuine research contribution

### Realistic first tape-out target

A 64-256 cell UniCell array with:
  - UART config interface (already in Verilog)
  - Wired-OR bus (already in Verilog)
  - Basic PTT sentry cell support
  - Test harness: scan chain for cell state readback

This is enough to:
  - Validate the cell model at true silicon speed (not FPGA approximation)
  - Run timing tests at process speed (SKY130 ~100MHz realistic)
  - Prove the portability story: same .icm on VM → FPGA → ASIC
  - Establish a publication/research record for the architecture

### OpenLane flow (open-source RTL-to-GDS)

OpenLane automates: synthesis (Yosys) → floorplan → placement → 
CTS → routing → signoff. Works with SKY130 PDK out of the box.
GitHub: https://github.com/The-OpenROAD-Project/OpenLane

Steps once investigating:
  1. Install OpenLane + SKY130 PDK
  2. Run synthesis on unicell.v — check area and timing reports
  3. Estimate cell count per mm² at SKY130 process
  4. Decide target array size for submission
  5. Apply to chipIgnite or TinyTapeout

- [ ] Install OpenLane and run synthesis on unicell.v
      Get area report: how many UniCell cells fit per mm²?
      Get timing report: what frequency is achievable at SKY130?
      This gives concrete numbers for shuttle application.

- [ ] TinyTapeout area estimate
      One TinyTapeout tile = ~160×100 µm at SKY130.
      Run synthesis, check if a minimal UniCell array fits.
      Even 8-16 cells on real ASIC silicon is a proof point.

- [ ] Draft chipIgnite application
      Novel architecture + open source + FPGA-validated =
      strong application. Worth attempting.
      Deadline-driven — check current schedule first.

Tag: investigate now (no hardware dependency), tape-out post-Kintex-7 validation.
Real silicon timeline: if chipIgnite application succeeds, 6-12 months to chips.

---

## SECURITY — Auth Token & Separate Command Bus (ALL THREE VARIANTS)

**Status:** Not yet implemented in any Verilog variant. Critical security gap.
**Priority:** High — this is load-bearing for the full security model.
**Affects:** unicell.v (standard), unicell-edge/unicell.v, unicell-latch/unicell_latch.v

### What the spec says (see docs/CELL_INTERNALS.md — authoritative)

The cell has three completely separate hardware sections:

  1. Command latch   — full cell config, loaded via command bus only
  2. Input latch     — data in, written by normal bus traffic
  3. Output latch    — computed result, written by NOR tree only

And two completely separate buses:

```
Bus 1 — Command & Control (32 bits, lower 16 currently used)
  bits  0-3:   command code (see CMD_ constants below)
  bits  4-14:  auth token (11 bits, card-wide)
  bit   15:    address mode (PTT-relative vs raw)
  bits 16-17:  scope (LOCAL only — SHORE/EXTENDED retired)
  bits 18-21:  handshake / ACK-REQ (bridge cells only)
  bits 22-28:  sequence tag (7 bits — bridge transaction integrity)
  bits 29-31:  reserved
  bits 32-63:  RETIRED — all buses are 32-bit

Bus 2 — Data Payload (32 bits)
  During CMD_RECONFIGURE: carries config words → command latch
  During normal operation: carries runtime data → input latch
  These are the SAME wire but completely different destinations
  depending on whether a CMD_RECONFIGURE is in progress.

Bus 3 — Target Address (32 bits)
  Cell address (PTT-relative or raw, controlled by Bus 1 bit 15)
  0xF0000000-0xFFFFFFFF = Shore index zone (top nibble = 0xF)
```

**The critical separation:** the command latch is only reachable from
Bus 2 during an active CMD_RECONFIGURE with a matching auth token.
At all other times Bus 2 writes go to the input latch only.
There is no path from normal data traffic to the command latch.

### What the Verilog currently does (all three variants)

- One bus: bus_addr (32-bit) + bus_data (32-bit) + bus_valid (1-bit)
- Config distinguished by magic pattern LOAD_PATTERN (0xA5A5A5A5) on bus_data
- No auth token field anywhere in the port list or logic
- No separate command bus port
- FREEZE is a dedicated hardware wire (freeze input) — correct as a fabric
  optimisation, but must still require auth token on command bus to initiate
- RELEASE / RECONFIGURE have no auth protection at all currently

### What needs adding (draft spec for implementation)

#### 1. New port: cmd_bus

All three unicell variants need a command bus port alongside the existing data bus:

```verilog
// Command bus (Bus 1) — separate from data bus
input  wire [15:0] cmd_bus,      // bits 0-3: command, 4-14: auth token, 15: addr_mode
input  wire        cmd_valid,    // command bus has valid data this cycle

// Data bus (Bus 2) — unchanged
input  wire [31:0] bus_addr,
input  wire [31:0] bus_data,
input  wire        bus_valid,
```

Note: start with 16-bit cmd_bus (bits 0-15) — covers command + auth token + addr_mode.
Upper 32 bits (scope, 64-bit addressing) are reserved for future silicon.

#### 2. Command latch registers (the full cell config store)

The command latch is a named register bank — separate from input/output latches.
Only CMD_RECONFIGURE (auth checked) can write to it. Data bus writes never reach it.

```verilog
// Command latch — full cell configuration
// Written ONLY by CMD_RECONFIGURE with matching auth token
// Never readable or writable from the data bus
reg [31:0] cmd_latch_gate_state    = 32'h0;
reg [31:0] cmd_latch_input_addr    = 32'h0;
reg [31:0] cmd_latch_output_addr   = 32'h0;
reg [10:0] cmd_latch_auth_mask     = 11'h0;  // WRITE-ONLY — no read path anywhere
reg        cmd_latch_start_flag    = 1'b0;

// Input and output latches — data path only, no connection to command latch
reg [31:0] input_latch  = 32'h0;
reg [31:0] output_latch = 32'h0;
```

Auth check on every system command (RECONFIGURE, FREEZE, RELEASE):
```verilog
wire auth_ok = (cmd_bus[14:4] == cmd_latch_auth_mask);   // 11-bit token match
```

Silent rejection: no output, no acknowledgement, no error signal.
The cell simply ignores the command if auth_ok is false.

#### 3. Command decoding from cmd_bus (replaces LOAD_PATTERN magic)

```verilog
localparam CMD_NOP         = 4'd0;
localparam CMD_READ        = 4'd1;   // future
localparam CMD_WRITE       = 4'd2;   // future
localparam CMD_RECONFIGURE = 4'd3;   // auth required — loads gate_state + addresses
localparam CMD_FREEZE      = 4'd4;   // auth required — decouples cell from bus
localparam CMD_RELEASE     = 4'd5;   // auth required — re-arms cell

wire [3:0] cmd_code = cmd_bus[3:0];
wire       cmd_is_system = (cmd_code == CMD_RECONFIGURE ||
                            cmd_code == CMD_FREEZE      ||
                            cmd_code == CMD_RELEASE);
```

#### 4. Auth token bootstrap (first CMD_RECONFIGURE special case)

At boot, every cell's auth_mask starts at 0. The BIOS-Plus issues the first
CMD_RECONFIGURE with the card auth token in bits 4-14. The cell must accept
this first command to SET the auth_mask, even though auth_mask is 0.

Bootstrap rule: if (cmd_latch_auth_mask == 0 && cmd_code == CMD_RECONFIGURE) → accept
                and load auth_mask from bus_data[10:0] BEFORE loading gate_state.

After auth_mask is set, all subsequent system commands require a matching token.
This is a one-time write — auth_mask cannot be changed once set (until power cycle).

CMD_RECONFIGURE word sequence (arrives on bus_data, one word per cycle):
  Word 0: auth_mask value   [10:0]  — ONLY on first RECONFIGURE (auth_mask == 0)
  Word 1: gate_state        [31:0]  → cmd_latch_gate_state
  Word 2: input_address     [31:0]  → cmd_latch_input_addr
  Word 3: output_address    [31:0]  → cmd_latch_output_addr
  Word 4: input_b_address   [31:0]  → cmd_latch_input_b_addr (GS_SYNC_WAIT only)

After final word: cmd_latch_start_flag = 1 (cell armed, live next tick).

#### 5. Freeze wire retained (fabric optimisation, not primary control)

The existing freeze input wire stays — it is driven by the array fabric for
power/timing efficiency and is a valid optimisation. However:
- The freeze wire is asserted BY the array controller after it issues CMD_FREEZE
  on the command bus with the auth token
- The freeze wire alone (without prior CMD_FREEZE) should not be the security
  mechanism — it is a convenience signal, not the access gate
- In the Verilog, freeze wire ORs with an internal freeze_latch register that
  is set only after a successful auth-checked CMD_FREEZE

```verilog
reg freeze_latch = 1'b0;   // Set by CMD_FREEZE (auth checked), cleared by CMD_RELEASE (auth checked)
wire cell_frozen = freeze || freeze_latch;   // Either source freezes the cell
```

#### 6. Security properties (must hold after implementation)

- [ ] A cell silently ignores CMD_RECONFIGURE if auth token does not match
- [ ] A cell silently ignores CMD_FREEZE if auth token does not match
- [ ] A cell silently ignores CMD_RELEASE if auth token does not match
- [ ] No error signal, no ACK, no NAK on auth failure — the caller cannot
      even confirm the cell exists at that address
- [ ] The auth_mask register is not readable via any bus operation
- [ ] The auth_mask is set exactly once (on first RECONFIGURE) and cannot
      be changed without a power cycle
- [ ] The freeze wire alone cannot override an auth-failed freeze_latch state
- [ ] These properties hold identically in all three Verilog variants

### Creep note

The edge and latch variants were forked from standard (v2.1) after iCEBreaker
bring-up. The bring-up used the LOAD_PATTERN magic approach (pragmatic for
hardware debugging). Both forks inherited this approach. The auth token and
command bus separation existed in the architecture spec but was never the
priority during bring-up.

This is the expected order of events — validate the cell model on silicon first,
then harden the security model. The architecture was always correct. The Verilog
is the outstanding item.

### Implementation order

1. Add cmd_bus port and auth_mask register to unicell.v (standard) first
2. Write tests: auth match → command executes; auth mismatch → silent ignore
3. Port identical change to unicell-edge/unicell.v
4. Port identical change to unicell-latch/unicell_latch.v
5. Update unicell_array.v (all three variants) to wire cmd_bus through the array
6. Update fpga_bridge.py to construct cmd_bus word for each command
7. Update icm_loader.py to send CMD_RECONFIGURE with auth token on boot
8. Update docs/VERILOG_SPEC.md with command bus port specification
9. Update docs/ARCHITECTURE.md security section to reflect implementation

Tag: pre-Kintex-7 / pre-chipIgnite submission. Must be in before any tape-out.
The security model is the foundation — it cannot be retrofitted onto silicon.

---

## BRIDGE — Security & Split-Data Review (consolidation note, 2026-05-14)

This section consolidates the bridge design across three areas that were
written at different times and need to be read together:

  1. Workbench — Bridge-pair-per-tile model (2026-05-12)
  2. Packet-confirmed counter routing for bridge depth
  3. Bridge counter — offset addressing + count tag integrity
  4. Signed data over bridges — type-aware bridge pairs
  5. Auth token on the command bus (SECURITY section above)

They are the same mechanism viewed from different angles. This note
captures the gaps, the creep, and the correct unified model.

---

### What "bridge" means (clarification — two distinct things)

There are currently two different things called "bridge" in the codebase
and docs. They must not be confused:

**A) UART bridge (uart_bridge.v)**
  The FPGA ↔ host communication module. Translates UART bytes to/from
  bus transactions. One per FPGA top. Not a security boundary.
  Already implemented. Not what this section is about.

**B) Pond bridge (Python: PondBridge, architecture: INBOUND/OUTBOUND)**
  The access gate between two ponds. Every inter-pond communication
  passes through a bridge pair. The security model lives here.
  Partly implemented in Python. NOT YET in Verilog at all.
  This section is about (B).

---

### Current state of pond bridges

**Python (pond.py):** PondBridge exists. Access check on bus writes.
  OPEN/PRIVATE/HIDDEN pond types enforced. Whitelist per bridge.
  Foundation laid but split-data protocol not implemented.

**Verilog (all three variants):** No pond bridge exists.
  There is no inbound/outbound address gating in any unicell_array.v.
  The UART bridge (A) is the only bridge in the Verilog.
  Pond isolation on silicon = zero enforcement currently.

---

### The split-data problem at the bridge

The current bridge model assumes one value = one bus write = one packet.
This breaks for:
  - Signed int32:  primary value + complement cell (2 bus writes)
  - Arrays:        index + data (2 bus writes)
  - Signed arrays: index + primary + complement (3 bus writes)
  - Int64:         low word + high word (2 bus writes, or more with complement)
  - Wide structs:  N words in sequence

The bridge must understand that these are a single logical transaction,
not N independent packets. If the bridge applies its access check per-write,
packet 2 of a signed value might be dropped while packet 1 was accepted —
leaving the receiving cell in a permanently stalled SYNC_WAIT state.

The packet-confirmed counter mechanism (already in TODO) is the solution.
The bridge wraps the counter cluster. The auth check applies to the
transaction as a whole, not to each individual bus write.

**The key insight (your note on split data):**
  The bridge is the transaction boundary, not the bus-write boundary.
  One transaction = one auth check = one counter sequence.
  Individual bus writes within a transaction are NOT independently auth-checked.
  The counter itself is the sequencing mechanism — it enforces order and
  completeness within a transaction without re-checking auth on each word.

---

### Revised bridge model (unified)

```
INBOUND bridge (one per pond port):

  [Auth check cell]            ← checks cmd_bus token ONCE per transaction
       ↓ ok
  [Transaction counter]        ← offset addressing: base + count = slot
       ↓ count = 0
  [Slot 0: index / address]    ← first word lands here
       ↓ count = 1
  [Slot 1: data primary]       ← second word lands here
       ↓ count = 2  (if signed)
  [Slot 2: data complement]    ← third word lands here (signed only)
       ↓ count = N → CLEAR → counter resets to 0
  [SYNC_WAIT processing cell]  ← fires when ALL slots filled
       ↓
  [OUTBOUND bridge]            ← result leaves under same auth model
```

Auth check: once per transaction (not per word).
Counter: packet-confirmed (advances only on confirmed arrival, not on ticks).
SYNC_WAIT: fires only when all N slots for this transaction are filled.
Backpressure: counter blocks next word if current slot not confirmed.

---

### What the bridge must enforce (security properties)

These apply to both the Python implementation and the future Verilog implementation:

- [ ] Auth check is per-transaction, not per bus-write
      The cmd_bus token is presented once at transaction start.
      If it matches, the counter sequence proceeds.
      If it does not match: silent drop of ALL words in the transaction.
      The counter never advances on an auth-failed transaction.

- [ ] A partially-delivered transaction cannot be completed by a second sender
      If sender A delivers word 0 (auth ok) and then sender B tries to deliver
      word 1 (different auth token) — word 1 is dropped silently.
      The counter holds at 1. Sender A's transaction stalls (Ward detects).
      No interleaving of transactions from different senders at one bridge.

- [ ] The bridge does not reveal whether it accepted or rejected a transaction
      Silent drop on auth failure — no NAK, no error, no timing difference.
      Same as the cell-level auth model.

- [ ] OUTBOUND bridge applies same auth model for results leaving a pond
      A result leaving a pond via OUTBOUND must carry the session token
      of the process that owns the destination workspace pond.
      An untrusted process cannot redirect results to a different workspace.

- [ ] Bridge depth (transaction word count) is declared in ICM, not negotiated
      The receiving bridge knows its depth at load time.
      The counter is configured to that depth. It cannot be changed at runtime.
      A sender cannot inject extra words to overflow the counter.

---

### Creep note (same issue as auth token)

The bridge-pair-per-tile workbench model (2026-05-12) and the packet-counter
mechanism were designed without explicitly connecting them to the auth token
requirement. The auth check was in the security model but wasn't written into
the bridge counter spec.

The split-data insight closes this: the auth check belongs at the transaction
boundary (first word of counter sequence), not at the bus-write boundary.
This is the unified model — single auth check per transaction, counter
enforces the rest.

---

### Implementation order (bridge)

These are pre-conditions for each other. Do in order:

1. [ ] Python: add transaction-boundary auth check to PondBridge
       Current check is per bus-write. Change to:
         - First write to INBOUND address starts a transaction (auth checked)
         - Subsequent writes in same counter sequence are unconditionally accepted
         - Counter reset signals end of transaction
       test_pond_bridge_auth.py: multi-word transaction, partial auth-fail cases.

2. [ ] Python: implement packet-confirmed counter in PondBridge
       Counter cell cluster in Python (not yet in cell array — Python-side for now).
       emit_packet_counter(depth, base_addr) → slot addresses.
       Ward detects stall if counter never resets (incomplete transaction).

3. [ ] Verilog: add pond INBOUND/OUTBOUND address gating to unicell_array.v
       Currently no pond bridge in any Verilog variant — add it.
       Bridge = a pair of address ranges (INBOUND_BASE..INBOUND_TOP,
                                          OUTBOUND_BASE..OUTBOUND_TOP)
       Writes to INBOUND range: gated by auth check + counter.
       Writes to OUTBOUND range: gated by session token of owning process.
       One bridge pair per pond connection. Parameters set at load time.

4. [ ] Verilog: add transaction counter to bridge gating logic
       Counter in Verilog is a small register (log2(max_depth) bits).
       Increments on confirmed slot arrival. Resets on CLEAR signal.
       SYNC_WAIT cell at end of counter sequence watches all slot addresses.

5. [ ] ICM format: bridge_depth field on all port declarations (already in TODO)
       Now with explicit note: depth=1 is unsigned scalar (current model).
       depth >= 2 requires counter cluster at the bridge.

6. [ ] Update ARCHITECTURE.md bridge section with unified model

Tag: post-auth-token Verilog implementation, pre-Kintex-7.
The Python bridge auth fix (step 1) can proceed immediately.
The Verilog bridge (steps 3-4) requires the cmd_bus port from the SECURITY section.

---

## ECC bits as bridge transaction token (design note, 2026-05-14)

### The observation

The bus packet is already 39 bits: 32 data + 7 ECC (reserved, all zero).
The 7 ECC bits are on every packet right now — they just carry nothing yet.

The cell auth token (cmd_bus bits 4-14) is card-wide — same token for every
cell on the card. It protects CMD_RECONFIGURE / CMD_FREEZE / CMD_RELEASE on
the command bus. It does not travel on the data bus with normal bus writes.

The bridge needs a lightweight per-transaction sequence tag to:
  - Confirm packets arrive in order (no drop, no duplicate, no interleave)
  - Detect a mis-addressed packet landing at the wrong bridge slot
  - Give Ward a clean signal to work with when something goes wrong

If the packet counts at the bridge are low enough, the 7 reserved ECC bits
can carry this sequence tag for free — no extra bus width, no new fields,
and when full Hamming SECDED arrives the two functions compose naturally.

---

### Packet counts at the bridge

How many packets does a transaction actually need?

```
unsigned int32:      1 packet   (data word only)
signed int32:        2 packets  (primary + complement)
unsigned array:      2 packets  (index + data)
signed array:        3 packets  (index + primary + complement)
int64:               2 packets  (low word + high word)
signed int64:        3 packets  (low word + high word + complement)
int64 array:         3 packets  (index + low + high)
signed int64 array:  4 packets  (index + low + high + complement)
arbitrary struct:    N packets  (declared at compile time, max N=127 with 7 bits)
```

7 bits = 0..127. Maximum declared bridge depth is 127 packets.
In practice the vast majority of bridges are depth 1, 2, or 3.
7 bits is comfortably sufficient for any realistic transaction depth.

---

### How it works (pre-ECC-implementation)

Each packet in a transaction carries its sequence number in bits 32-38
(the currently-reserved ECC field):

```
Packet 0:  data[31:0] | seq=0b0000001  (sequence position 0, 7-bit one-hot or binary)
Packet 1:  data[31:0] | seq=0b0000010  (sequence position 1)
Packet 2:  data[31:0] | seq=0b0000100  (sequence position 2)
...
```

The receiving bridge has an internal counter. On each packet arrival:
  expected_seq = (1 << counter)          -- one-hot, or just counter in binary
  received_seq = bus_packet[38:32]
  match = (received_seq == expected_seq)  -- 1-cell XOR check (7-bit wide)

Match → accept packet, advance counter.
Mismatch → drop packet silently, hold counter, Ward detects stall.

The counter resets to 0 after the final packet of a declared-depth transaction.
The sending side sets bits 32-38 of each packet before transmission.
fpga_bridge.py already constructs the 39-bit packet — it just needs to
populate bits 32-38 with the sequence number instead of zeros.

---

### How it composes with full ECC

When Hamming(39,32) SECDED is implemented, the 7 ECC bits become real parity
bits computed from the 32 data bits. The sequence number carried in those bits
today would be replaced by the syndrome.

But — and this is the elegant part — the ECC syndrome of a correct packet
is a deterministic function of the data. The bridge can pre-compute the
expected syndrome for each sequence position and use it as the match condition:

  expected_syndrome = hamming_encode(data[31:0])   -- computed by sender
  received_syndrome = bus_packet[38:32]
  match = (received_syndrome == expected_syndrome) -- SECDED check

If the data is correct and the sequence is correct: syndrome matches.
If the data is corrupted: syndrome detects it (single-bit corrects, double detects).
If the packet is from the wrong sequence: syndrome mismatches (data landed in
  the wrong slot has a different expected value → syndrome fails).

The bridge check cell is identical in structure — XOR(received, expected) == 0.
Pre-ECC: expected = sequence number. Post-ECC: expected = Hamming syndrome.
Same cell, same logic, stronger guarantee after ECC arrives.

---

### What this means for the auth token

The cell auth token (command bus, card-wide) and the ECC sequence tag (data bus,
per-transaction) are complementary, not competing:

```
Cell auth token (cmd_bus bits 4-14):
  Card-wide, same for all cells.
  Protects: CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE.
  Checked at: command bus, once per command.
  Does NOT travel on the data bus.
  Purpose: stop unauthorised reconfiguration of cell topology.

ECC sequence tag (bus_packet bits 32-38):
  Per-transaction, changes each packet in a sequence.
  Protects: data integrity and ordering within a bridge transaction.
  Checked at: bridge INBOUND, once per packet within a transaction.
  Travels on the data bus with every write.
  Purpose: confirm packets arrive in order, detect interleave/drop/corruption.
```

They operate at different levels and protect different things.
The cell auth token is the hardware config lock.
The ECC sequence tag is the data integrity check at the software/OS boundary.

---

### Sender responsibility

The sending side (fpga_bridge.py / COMPANION / workspace) sets bits 32-38:

Pre-ECC:
  packet[38:32] = sequence_number  -- 0, 1, 2, ... N-1 for this transaction

Post-ECC:
  packet[38:32] = hamming_encode(packet[31:0])  -- real syndrome

The receiving bridge check cell is unchanged — it just XORs received vs expected.
Expected value changes from sequence number to syndrome, but the check is identical.

---

### Implementation notes

- [ ] fpga_bridge.py: populate bits 32-38 with sequence number on each write
      Currently: bus packet = (addr, data, ecc=0) — ecc is always 0.
      Change to:  bus packet = (addr, data, ecc=seq_num) for bridge transactions.
      Non-bridge writes (config, data to non-bridge addresses): ecc=0 unchanged.
      fpga_bridge.send_packet() takes optional seq= parameter, default 0.

- [ ] PondBridge (Python): check bits 32-38 on INBOUND packets
      bridge.receive(addr, data, ecc) → check ecc == expected_seq
      On mismatch: drop, increment _bridge_rejections, do NOT advance counter.
      Ward detects counter stall → BRIDGE_ALIGNMENT_ERROR escalation.

- [ ] Verilog bridge: check bits 32-38 in the INBOUND gating logic
      unicell_array.v receives 39-bit bus packets.
      Bridge input checker: XOR(received[38:32], expected_seq[6:0]) → match wire.
      match wire gates SYNC_WAIT for that bridge slot.
      Currently: bus is 32-bit (bus_addr + bus_data). Needs to widen to 39-bit
      to carry ECC field. Or: ECC field on a parallel wire alongside bus_data.
      Decision: widen to 39-bit now (pre-ECC), or separate ECC wire.
      Recommendation: widen bus_data to 39-bit now — matches the locked packet
      format and avoids a second change when ECC arrives.

- [ ] Document: bits 32-38 are DUAL PURPOSE pre/post ECC
      Pre-ECC:  sequence tag (bridge integrity)
      Post-ECC: Hamming syndrome (data + sequence integrity)
      The ECC section of VERILOG_SPEC.md and ARCHITECTURE.md should note this.

Tag: can start immediately (fpga_bridge.py + Python PondBridge).
Verilog bus widening: do alongside the cmd_bus port addition (same PR).
Full ECC: still deferred to production silicon, unchanged.

---

## COMMAND BUS — Full bit map audit (2026-05-14)

The archive docs (02_Core_Architecture.md) and the current ARCHITECTURE.md
do not reflect the actual Bus 1 layout as implemented in command_interface.py.
This is the authoritative layout as of today:

```
Bus 1 (Command & Control) — 64 bits
  bits  0-3:   command code (4 bits)
               0 = CMD_DATA_WRITE       User+System
               1 = CMD_SET_INPUT_ADDR   User+System
               2 = CMD_SET_OUTPUT_ADDR  User+System
               3 = CMD_RECONFIGURE      System only (auth required)
               4 = CMD_FREEZE           System only (auth required)
               5 = CMD_RELEASE          System only (auth required)
               6 = CMD_COPY_DATA_TO_OUT User+System
               7 = CMD_COPY_DATA_TO_IN  User+System
               8 = CMD_PING             Anyone
               9-15 = reserved

  bits  4-14:  auth token (11 bits)
               Card-wide. Same for all cells on the card.
               Checked on CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE only.
               Silent rejection on mismatch (no ACK, no NAK).
               Set once at boot via first CMD_RECONFIGURE.
               Write-only in hardware — not readable.

  bit   15:    address mode
               0 = PTT-relative (user space default)
               1 = raw system address (system/BIOS only)

  bits 16-17:  scope
               00 = LOCAL    (Bus 3 is 32-bit)
               01 = SHORE    (Bus 3 bits 0-47 used)
               10 = EXTENDED (Bus 3 all 64 bits)
               11 = reserved

  bits 18-21:  handshake / ACK-REQ (4 bits, 16 states)
               0x0 = NONE     normal packet
               0x1 = ACK      received and accepted
               0x2 = NAK      received, rejected (mask mismatch etc.)
               0x3 = BUSY     received, queued, not yet processed
               0x4 = REQUEST  sender requesting resource or response
               0x5 = GRANT    request approved
               0x6 = DENY     request refused
               0x7 = RETRY    transient timing issue, try again
               0x8-0xF = reserved
               Note: only meaningful on bridge cells. Ignored on compute cells.
               Ward monitors bridge handshake state for health concerns.

  bits 22-28:  *** 7 BITS SPARE — candidate for sequence tag ***
               See note below.

  bits 29-31:  *** 3 BITS SPARE — reserved, do not assign yet ***

  bits 32-63:  reserved upper half (future 64-bit extension)
```

### The gate_state mode flags are NOT on Bus 1

GS_ONE_SHOT, GS_LATCH, GS_BROADCAST, GS_LOOP_BACK, GS_SYNC_WAIT etc. are
bits within the gate_state value — they travel on Bus 2 (data payload) as
the argument to CMD_RECONFIGURE. They are NOT fields on the command bus.

This was the thing to check: the archive docs listed mode flags in the
"command" section which created the impression they were command bus fields.
They are not. The command bus carries only the fields listed above.

### Sequence tag — 7 bits fit at bits 22-28

The sequence tag proposed for bridge transaction integrity (see ECC bits
design note) needs 7 bits. Bits 22-28 are available.

Advantage of cmd_bus over bus_data for the sequence tag:
  - bus_data stays 32 bits — no Verilog bus widening needed
  - Sequence tag is control/sequencing, not data — cmd_bus is the right bus
  - ECC field (bus_data bits 32-38) stays clean for Hamming syndrome only
  - The 7 bits ride alongside the handshake bits — same delivery path

Proposed allocation:
  bits 22-28:  sequence tag (7 bits, 0..127)
               Set by sender for each packet in a bridge transaction.
               Checked by receiving bridge INBOUND cluster.
               0 = start of new transaction (or non-bridge packet, ignored)
               1..N = packet N in current transaction
               Compute cells (non-bridge): ignore this field entirely.

  bits 29-31:  still reserved — do not assign

This means the ECC design note needs updating: the sequence tag goes on
cmd_bus bits 22-28, not on bus_data bits 32-38. The bus_data field stays
32 bits and the ECC bits (when implemented) remain dedicated to Hamming.

### Action: update docs to reflect actual Bus 1 layout

- [ ] docs/ARCHITECTURE.md — add Command Bus section with full bit map above
      Currently missing entirely from ARCHITECTURE.md. The cell section and
      pond section exist but the command bus protocol is not documented there.

- [ ] docs/VERILOG_SPEC.md — add cmd_bus port spec with bit map
      Currently no mention of cmd_bus. Add alongside the auth token section.

- [ ] ECC design note (earlier in this TODO) — update sequence tag location
      Change: "bus_data bits 32-38" → "cmd_bus bits 22-28"
      The bus_data widening note is superseded — bus_data stays 32 bits.

- [ ] docs/archive/02_Core_Architecture.md — note: superseded by ARCHITECTURE.md
      The archive doc has an incomplete and partially stale Bus 1 layout.
      Add a header note pointing to ARCHITECTURE.md as the current reference.
      Do not delete the archive — it has useful history.

Tag: do the ARCHITECTURE.md and VERILOG_SPEC.md updates before implementing
the cmd_bus Verilog port, so the implementation has a clean reference doc.

---

## ADDRESS SPACE — 32-bit flat + Shore index zone (decision 2026-05-14)

### Decision: all buses stay 32-bit. 64-bit bus references retired.

Previous design had EXTENDED scope and upper 32 bits on Bus 1 for 64-bit
addressing across cards. This is retired. Reasons:
  - All buses stay 32-bit throughout — simpler Verilog, simpler everything
  - 32-bit address space (4.29B addresses) is sufficient for a single card
  - Cross-card and system-wide routing handled by Shore table, not bus width
  - No bus widening anywhere. Verilog stays clean and portable.

### Address space layout (32-bit, final)

```
0x00000000 to 0xEFFFFFFF   ~3.76B addresses   Local cell space
                                               Physical cell addresses
                                               Direct, no resolution needed

0xF0000000 to 0xFFFFFFFF   ~268M addresses    Shore index namespace
                                               NOT physical addresses
                                               Resolved by Shore table
```

Top nibble = 0xF → Shore index. Hardware check: bits 28-31 == 4'hF.
One 4-bit comparison in the array fabric — zero routing overhead for local traffic.

### Shore index namespace (0xF0000000 to 0xFFFFFFFF)

A write to an address in this zone means:
  "Shore entry (addr & 0x0FFFFFFF), resolve it to wherever that currently lives."

The Shore table holds: index → {card_id, local_address, pond_id, type}

This is NOT a proxy address space. The index is a stable logical identifier.
The physical destination (card, local address) can change without the sender
knowing — update one Shore entry, all senders reach the new location.

Examples:
  0xF0000001  →  Shore entry 1  →  COMPANION INBOUND on this card
  0xF0000042  →  Shore entry 66 →  KeyboardPond INBOUND on card 3, addr 0x00A1F000
  0xF0001000  →  Shore entry 4096 → Named system service, wherever it lives

268M index slots is far more than any realistic system will ever need.
In practice: the low Shore indexes are well-known system services,
higher indexes are dynamically assigned at pond spawn time.

### What a cell sees

A cell writing to 0xF0000042 just writes to that address.
The fabric checks bits 28-31: if 0xF, Shore intercepts and resolves.
The cell has no knowledge of whether the destination is local or remote.
Transparent to the compiler and to the cell program.

### What changes from the previous design

- EXTENDED scope (bits 16-17 = 10) on Bus 1: RETIRED
- Upper 32 bits of Bus 1 (bits 32-63): RETIRED — Bus 1 is 32-bit
- Bus 2 (data payload): already 32-bit, unchanged
- Bus 3 (target address): 32-bit, top nibble = Shore index flag
- _SCOPE_EXTENDED constant in command_interface.py: RETIRE
- _SCOPE_SHORE: RETIRE (Shore routing is implicit in address, not scope bits)
- Scope field now only needs LOCAL (00) — 2 bits remain but SHORE/EXTENDED unused
- GS_ADDR_LATCH (bit 23, bridge 64-bit address extension): RETIRE
- _config_upper register in cell: RETIRE
- All 64-bit address references in docs: UPDATE to 32-bit + Shore index model

### What this enables beyond simple routing

Because Shore indexes are logical identifiers not physical addresses:
  - Pond migration: Shore entry updated, all senders transparently rerouted
  - Named services: well-known indexes for system services (like port numbers)
  - Capability tokens: a Shore index is a capability — hold the index, reach the service
  - Cross-card: Shore entry points to remote card + local address, fully transparent
  - Load balancing: Shore entry can round-robin across multiple physical destinations
  - The Ward and COMPANION already think in Shore entries — cells now do too

### Implementation order

- [ ] command_interface.py: retire _SCOPE_EXTENDED, _SCOPE_SHORE, _config_upper
      Scope field simplifies to LOCAL only for now.
      Add Shore index check: is_shore_index(addr) = (addr >> 28) == 0xF

- [ ] unicell.py / all variants: retire _config_upper register and GS_ADDR_LATCH
      Config sequence stays 4 words (gate_state, input_addr, output_addr, auth)
      No 5th word for upper address.

- [ ] shore.py: add index_resolve(index) → {card_id, local_addr, pond_id}
      Shore table gains explicit index→physical mapping.
      Well-known indexes: COMPANION=1, SHOREKEEPER=2, BIOS=3 (reserve 1-255)
      Dynamic indexes: assigned at pond spawn, freed at pond destroy.

- [ ] unicell_array.py / unicell_array.v: intercept writes to 0xFxxxxxxx
      Before delivering to local bus: check top nibble.
      If 0xF: pass to Shore resolver rather than local bus.
      Shore resolver returns local_addr if on this card, or forwards if remote.

- [ ] docs/ARCHITECTURE.md: update address space section
- [ ] docs/VERILOG_SPEC.md: retire 64-bit bus references
- [ ] MIGRATION_TODO.md: mark all 64-bit / EXTENDED scope items as retired

Tag: foundational decision — update docs before any new Verilog work.
The 32-bit bus constraint ripples through everything cleanly.

---

## CELL SIMPLIFICATION — Command latch redesign (2026-05-14)

### The insight

Port address latches are local to each port, not stored in the central
command latch. The command bus key (auth token) validates whether incoming
data is accepted — the port recognises its own address, the command bus
confirms the write is valid. GS_ mode flags are runtime commands, not
stored config.

### Command latch reduced to 32 bits (fixed, with expansion headroom)

```
bits  0-10:  NOR topology   (11 bits) — the cell's gate wiring
bits 11-21:  auth_mask      (11 bits) — write-once, card-wide token
bit   22:    start_flag     ( 1 bit)  — armed/disarmed
bits 23-31:  reserved       ( 9 bits) — expansion, do not assign yet
```

CMD_RECONFIGURE now loads only 2 words:
  Word 0: auth_mask (first boot only)
  Word 1: NOR topology

Addresses set separately via CMD_SET_INPUT_ADDR / CMD_SET_OUTPUT_ADDR.

### Ripple effect — things that need updating

This is a significant simplification but it flows through a lot of the stack.
Do methodically, validate on iCEBreaker before Kintex-7 port.

**Verilog (all three variants):**
- [ ] Command latch: narrow to 32 bits as above
- [ ] Input port: add own address register, loaded by CMD_SET_INPUT_ADDR
- [ ] Output port: add own address register, loaded by CMD_SET_OUTPUT_ADDR
- [ ] CMD_RECONFIGURE: reduce to 2-word sequence (was 4-5 words)
- [ ] GS_ mode flags: audit which become cmd_bus codes 10-15 runtime commands
- [ ] Re-run full iCEBreaker bring-up sequence after changes

**Python (unicell.py and variants):**
- [ ] Cell config sequence: split into RECONFIGURE (topology) + SET_ADDR commands
- [ ] gate_state field: review — topology bits stay, mode flag bits move to runtime
- [ ] _build_config_sequence() or equivalent: update word count and order

**Compiler / ICM loader:**
- [ ] Compiler: emit CMD_SET_INPUT_ADDR + CMD_SET_OUTPUT_ADDR separately
      Currently emits addresses as part of the RECONFIGURE sequence
- [ ] ICM format: address fields move from cell config block to separate commands
- [ ] icm_loader.py: update load sequence accordingly

**gate_states.py:**
- [ ] Audit all GS_ constants — which are topology (stay), which are runtime
- [ ] Runtime mode flags: define as cmd_bus command codes 10-15
- [ ] Document the split clearly so compiler knows what goes where

**Tests:**
- [ ] test_gate_state_32.py: update for new config sequence
- [ ] test_pond_bridge_auth.py: CMD_SET_*_ADDR is user+system, not auth-gated
- [ ] Bring-up sequence tests: validate 2-word RECONFIGURE + separate addr commands

**Docs:**
- [ ] docs/CELL_INTERNALS.md: updated (this session) — authoritative
- [ ] docs/ARCHITECTURE.md: update cell section to reference CELL_INTERNALS
- [ ] docs/VERILOG_SPEC.md: update port list and config sequence
- [ ] docs/RUNNING.md: update bring-up sequence description

### What this does NOT change

- Auth token model: unchanged — auth_mask still write-once, still 11 bits
- Command bus structure: unchanged — Bus 1 bit map stays as audited
- Security isolation: unchanged — command latch still unreachable from data bus
- Address space: unchanged — 32-bit, Shore index zone at 0xFxxxxxxx
- Bridge/ECC/sequence tag: unchanged

Tag: validate on iCEBreaker first. This touches the full stack.
iCEBreaker re-run is the gate before Kintex-7 port.
