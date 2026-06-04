# Imago UniCell — Completed Items
**Archive of completed work. Most recent first.**

---

## May 2026 — FPGA Architecture Overhaul (this session)

### Silicon Validation
- [x] iCEBreaker: test_sync_wait.py **16/16 PASS** (May 2026)
- [x] iCEBreaker: test_new_opcodes.py **26/29 PASS** (May 2026, 3 timing edge cases)
- [x] Kintex-7 100-cell: 57,338 LUTs (9%), **26.73 MHz** (PASS at 12 MHz)

### Protocol v2.1 — Bus Narrowing
- [x] cmd_bus: 32→8 bit (opcode only, 256 opcodes)
- [x] bus_addr: 32→16 bit (65,536 cell address space)
- [x] cmd_data: 32-bit (auth[31:24] + payload[23:0])
- [x] UART frame: 8 bytes TX (0x01 + opcode + addr(2) + data(4))
- [x] UART frame: 7 bytes RX fired response (0x10 + addr(2) + data(4))
- [x] UART frame: 7 bytes RX status response (0x11 + armed(2) + cycles(4))
- [x] auth_mask: 11-bit → 8-bit, moved from cmd_bus[14:4] to cmd_data[31:24]
- [x] 0x03 global escape — resets UART parser from any state

### New Opcodes
- [x] CMD_LATCH_IN_ON (0x0A) — hold a_arrived after firing
- [x] CMD_LATCH_IN_OFF (0x0B) — restore two-arrival mode
- [x] CMD_MEM_CALL (0x0C) — latch_in + one_shot + rearm atomically
- [x] CMD_REARM (0x0D) — rearm one-shot cell
- [x] CMD_SET_LOGICAL (0x0E) — switch physical→logical address mode

### Cell Architecture
- [x] `physical_mode` register — boot=1, cleared by CMD_SET_LOGICAL
- [x] `output_set` register — cell cannot fire until SET_OUTPUT_ADDR or RECONFIGURE
- [x] 4-packet boot sequence: RECONFIGURE → SET_LOGICAL → SET_OUTPUT_ADDR → RELEASE
- [x] cmd_latch auth_mask moved to [18:11] (8-bit)
- [x] cmd_valid_w excludes DATA_WRITE (opcode 1) — was causing bus_hit suppression

### Verilog Files Updated
- [x] `unicell.v` — new opcodes, physical_mode, output_set, 8-bit auth
- [x] `unicell_array.v` — 32-bit cmd_data, out_valid timing
- [x] `uart_bridge.v` — 8-byte frame, 7-byte fired response, 0x03 escape
- [x] `top_icebreaker.v` — cmd_valid_w fix, 32-bit cmd_data
- [x] `top_kintex7.v` — cmd_valid_w fix, 32-bit cmd_data

### PCIe Route (XDMA)
- [x] `pcie/axi_unicell_bridge.v` — AXI-Lite slave → UniCell command/data bus
- [x] `pcie/top_xdma_unicell.v` — XDMA + bridge + UniCell array top-level
- [x] `pcie/unicell_xdma.py` — Python tool via /dev/xdma0_user mmap
- [x] `pcie/ypcb003381p1_unicell.xdc` — complete constraints for YPCB-00338-1P1
- [x] Vivado: XDMA 4.2 IP created and configured (x8 Gen1, xc7k480tffg1156-2)
- [x] Vivado: synthesis complete (0 errors)
- [x] AMD 30-day eval license obtained (free, no card)

### Python Tools Updated
- [x] `fpga/fpga_bridge.py` — new frame format, 8-bit auth, new opcodes
- [x] `fpga/test_sync_wait.py` — new frame format, fixed expectations
- [x] `fpga/test_new_opcodes.py` — new test suite for all new opcodes
- [x] `fpga/test_all.py` — combined test runner

### Documentation
- [x] `docs/FPGA_HARDWARE.md` — comprehensive hardware reference (new, ground truth)
- [x] `docs/DOC_AUDIT.md` — full consistency audit cross-reference
- [x] `docs/INDEX.md` — FPGA section updated
- [x] `START.md` — build environment quick-start
- [x] `sessions/latest.md` — session results recorded

---

## May 2026 — Previous Sessions

### iCEBreaker Bring-up (May 14 2026)
- [x] iCEBreaker silicon validated at 26.57 MHz (above 24 MHz target)
- [x] 51% LC utilisation on iCEBreaker
- [x] Command latch + command bus architecture migrated from LOAD_PATTERN
- [x] Verilog declared ground truth

### INT32 Comparators and Sorting
- [x] Five new INT32 comparator tiles registered in model library and Composer
- [x] INT32 bitonic sorting network using INT32_CAS tiles
- [x] `postcode_sort.py` updated to use Haversine metre-precision integer distances

### User Library System
- [x] `~/.imago/library/` — user library with CLI and Python API
- [x] 2,300+ passing tests at that point

### Tier 6 Documentation
- [x] `VM_GETTING_STARTED.md`
- [x] `RUNNING.md`
- [x] `ARCHITECTURE.md`
- [x] `ICM_FORMAT.md`

### Bug Fixes
- [x] `_ptt_ref` wire bug fixed
- [x] Sentry address patching bug fixed
- [x] INT32_LT_S using XOR sign bits (overflow-safe)

---

## Earlier Completed Work (from original MIGRATION_TODO)

### VM / Core
- [x] Retire `unicell.py` v1 compat shim
- [x] Retire `unicell_array.py` v1 array
- [x] Retire `_execute_nor_gates(value)` — DEPRECATED, v2 path default
- [x] Retire `_sync_buf` — v1 compat, retained for legacy
- [x] Retire string composites — integer aliases to v2 constants
- [x] Retire `lower_to_cell_map()` — delegates to v2
- [x] `NORBuilder` marked DEPRECATED
- [x] `pond.py` — anomaly_threshold/stall_threshold from bridge
- [x] `compiler_int32.py` — Kogge-Stone (482 cells, depth 2)
- [x] `compiler.py` TILE_FUNCTION_MAP — `int32_add_cla` removed
- [x] `fp_tiles.py` — all INT32/FP32 tiles use v2 NORBuilder primitives
- [x] `llvm_ir_mapper.py` — updated to INT32_ADD (Kogge-Stone)
- [x] `sequencer.py` — v2 integer gate state names
- [x] `model_library.py` INT32 entries — all figures verified
- [x] OR lowering: depth-aligned SYNC_WAIT confirmed correct
- [x] Compiler constant injection: const_0/const_1 auto-registered
- [x] Workbench UI: input_b_address display and two-input indicator

### VM Features
- [x] Standalone VM package (pip install imago-vm, 2026-05-10)
- [x] VM accuracy mode — standard variant IS accuracy model
- [x] VM web interface — workbench.py (http://localhost:7420)
- [x] VM documentation — RUNNING.md, ARCHITECTURE.md, INDEX.md
- [x] VM playground / example programs — bundled in imago/examples/
- [x] VM feedback channel — GitHub Issues

### v2 Gate Tree
- [x] v2 gate tree: all 12 functions verified by truth table
- [x] `unicell_v2.py`: receive_a/receive_b, _execute_nor_gates_v2
- [x] `unicell_array_v2.py`: two-phase tick
- [x] `ir_v2.py`: single-cell binary ops, Kogge-Stone 32-bit adder
- [x] `compiler_v2.py`, `controller_v2.py`: v2-aware
- [x] `fp_tiles_v2.py`: INT32 tiles rebuilt
- [x] `unicell_v2.v`: Verilog posedge A / negedge B
- [x] `lower_to_cell_map_v2()` in ir.py
- [x] `branch.py`: XNOR+AND(1) comparator (6 cells, was 12)
- [x] ECC stubbed: 7 bits reserved, passthrough stubs, format locked
- [x] `model_library.py`: all INT32 models updated
- [x] `program_builder.py`: input_b_address preserved in _reassign_addresses
- [x] `program_image.py`: to_dict/from_dict includes inB field
- [x] `workbench.py`: gate_details() and array_snapshot() v2-aware
- [x] Shore: view_mask, lean index, query_by_ptt_word
- [x] `fs_search.py`: KeyNormaliser, CollectionTable, CollectionIndex
- [x] `pond_ptt.py`: to_cell_word/from_cell_word, STATUS_IDLE_WARNING
- [x] SentryPrimitive: 5 cells
- [x] 2,633+ tests, zero failures

### Latch Model
- [x] `unicell.py`: Added `_input_latch` and `_output_latch` registers
- [x] `unicell_array.py`: 3-phase tick loop
- [x] All 2,238 tests passing
- [x] `fpga/verilog/unicell_latch.v`: pure combinatorial gate tree
- [x] GS_OUT_POSEDGE set on all compiler-emitted cells by default
- [x] Timing model — `unicell-latch/docs/timing.md`

### Documentation (original rewrites)
- [x] README.md — complete rewrite
- [x] docs/RUNNING.md — full workflow guide
- [x] docs/ARCHITECTURE.md
- [x] docs/VISION.md
- [x] docs/VM_GETTING_STARTED.md
- [x] docs/ICM_FORMAT.md
- [x] docs/VERILOG_SPEC.md
- [x] docs/LLVM.md
- [x] docs/NEURAL_POND_TUTORIAL.md
- [x] docs/architecture_positioning.md
- [x] docs/RESULTS.md
- [x] docs/KS_ADDER_UNICELL.md
