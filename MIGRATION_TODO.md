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
      Reference Grok-suggested Verilog when reviewed and ported to v2.

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

---
Last updated: Claudette v2.1
