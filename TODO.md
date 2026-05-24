# Imago UniCell — Active TODO
**Last updated: May 2026**
**Scope: Structural code changes and implementations only. Documentation updates tracked in DOC_AUDIT.md.**

---

## IMMEDIATE — Unblocked, ready to implement

### VM Migration (core architecture update)
- [ ] VM: remove `input_b_address` and `receive_b()` from `unicell.py` (all variants)
- [ ] VM: update `tick()` to two-arrival model (first stores `a_data`, second fires)
- [ ] VM: add `latch_in` mode to `unicell.py` (`a_arrived` stays set after firing)
- [ ] VM: add `edge_mode` to `unicell.py` (`cmd_latch[10]`)
- [ ] VM: update `cmd_latch` field layout to confirmed 32-bit spec (see FPGA_HARDWARE.md)
- [ ] VM: add `cmd_bus` port handling to `unicell.py` (CMD_RECONFIGURE, SET_IN/OUT, FREEZE, RELEASE, PING)

### ICM Format
- [ ] ICM: remove `inB` field (RETIRED — input_b_address removed from silicon)
- [ ] ICM: update `gs`/`cmd_latch` bit layout to new 32-bit spec
- [ ] ICM: add `format_version` field to header
- [ ] ICM: add `address_width` field to header
- [ ] ICM: document two-arrival model (no flag needed)
- [ ] ICM: `auth_mask` field documented as WRITE-ONLY / NOT SAVED (zeroed before serialisation)
- [ ] ICM: add `icm_hash` (SHA-256) field to all ICM files

### icm_loader.py
- [ ] `icm_loader.py`: remove Word 4 (input_b) from RECONFIGURE sequence
- [ ] `icm_loader.py`: separate address commands from RECONFIGURE (emit CMD_SET_INPUT_ADDR + CMD_SET_OUTPUT_ADDR)
- [ ] `icm_loader.py`: zero auth_mask bits in cmd_latch before writing to ICM
- [ ] `icm_loader.py`: SHA-256 hash verification before sending to hardware

### Compiler
- [ ] Compiler: emit new cmd_latch bit layout (per FPGA_HARDWARE.md CMD_RECONFIGURE mapping)
- [ ] Compiler: emit CMD_SET_INPUT_ADDR + CMD_SET_OUTPUT_ADDR as separate ops
- [ ] Compiler: remove GS_SYNC_WAIT (two-arrival is default, no flag needed)
- [ ] Compiler: add memory cell patterns (STORAGE, LOOP, three-cell access)
- [ ] Compiler: emit complement cell for signed outputs
- [ ] Compiler: latch_in flag for memory cells
- [ ] Compiler: edge_mode flag for edge-triggered tiles

### gate_states.py
- [ ] `gate_states.py`: GS_SYNC_WAIT → RETIRED
- [ ] `gate_states.py`: add GS_LATCH_IN, GS_EDGE_MODE, GS_LOOP_BACK constants
- [ ] `gate_states.py`: audit all GS_ constants — topology bits stay, mode flags move to runtime

### model_library.py
- [ ] `model_library.py`: remove `input_b_address` from all tile specs
- [ ] `model_library.py`: add STORAGE_CELL, LOOP_COUNTER, THREE_CELL_MEM tiles

### program_builder.py / program_image.py
- [ ] `program_builder.py`: remove `input_b_address` from `_reassign_addresses`
- [ ] `program_image.py`: `to_dict()` zeroes auth_mask in all cmd_latch fields

### branch.py
- [ ] `branch.py`: remove `_input_latch` clearing (no B-input)

---

## SHORT TERM — After VM migration

### Composer
- [ ] Composer: **DIAGNOSE WHY IT STOPPED WORKING** — fix before any updates
- [ ] Composer: remove `input_b_address` from all tile specs and port panel
- [ ] Composer: update cell inspector (edge_mode, latch_in, loop_back)
- [ ] Composer: add STORAGE/LOOP/COUNTER cells to library
- [ ] Composer: generate `icm_hash` on export

### Workbench
- [ ] Workbench: remove `input_b_address` display row
- [ ] Workbench: add FPGA/silicon workbench mode (PTT-only data source)
- [ ] Workbench: input panel tile grid (max 8)
- [ ] Workbench: WorkspacePond backed by real Pond (not mock)
- [ ] Workbench: mode toggle in UI (VM / Silicon)

### Security (auth_mask)
- [ ] `program_image.py`: confirm `to_dict()` zeroes auth_mask in all cmd_latch fields
- [ ] ICM hash: SHA-256 over zeroed-auth version

---

## MEDIUM TERM — Silicon features

### FPGA / Hardware
- [ ] `test_icm_portability.py` — compile NOT chain, load to iCEBreaker, verify silicon
- [ ] `test_icm_portability_memory.py` — STORAGE cell via ICM, write/read verify
- [ ] VM vs silicon diff tool (`imago_diff.py`)
- [ ] Wire thermal sensor to dedicated bus address at FPGA bring-up
- [ ] FPGA read-back command in Verilog state machine
- [ ] `freeze()` standardised output format

### PCIe / Kintex-7
- [ ] Complete Vivado implementation build (currently in progress — XDMA opt_design fix)
- [ ] Flash bitstream to card BPI flash (permanent)
- [ ] Verify PCIe card enumerates (`lspci | grep Xilinx`)
- [ ] Install xdma.ko from Xilinx/dma_ip_drivers
- [ ] Test `unicell_xdma.py info` against live card
- [ ] 32-bit address validation test (2-3 cells, full width)
- [ ] Multi-pond test (latch + edge ponds, bridge conversion)

### Counter / ECC Bridge
- [ ] `CMD_DATA_COUNTED` (0x0F) — opcode for sequence-tagged data packets
- [ ] Counter cell pattern: SELECT + confirmed-increment + CLEAR feedback
- [ ] `NORBuilder`: `emit_packet_counter(N, base_address)` helper
- [ ] ICM format: `bridge_depth` field on port declarations
- [ ] Compiler: set bridge_depth from port type automatically
- [ ] Ward: BRIDGE_ALIGNMENT_ERROR reason code on STALL escalation

### Soft ECC (command bus sequence tags)
- [ ] `command_interface.py`: populate cmd_bus sequence count (cmd_data field)
- [ ] `PondBridge` (Python): XOR check on INBOUND packets
- [ ] Verilog bridge: XOR check on INBOUND gating logic

---

## LONG TERM — Deferred

### VM
- [ ] VM performance mode (after FPGA/silicon validation)
- [ ] GPU/large array path at startup (Standalone mode)
- [ ] FPGA budget enforcement in VM
- [ ] Session identity management

### OS Layer (silicon)
- [ ] Ward as silicon program (~20-30 cells scanning PTT entries)
- [ ] PTT cell word comparison in silicon
- [ ] Shore table in silicon (resident pond)
- [ ] Collection tables in silicon (fs_search.py)
- [ ] Shore user table
- [ ] Multiple WORKSPACE ponds per PondManager
- [ ] Access token in PTT hidden field

### 64-bit Addressing
- [ ] bus_addr/bus_data widen to 64-bit when silicon arrives
- [ ] Bridge cells use upper 32 bits across pond boundaries
- [ ] `command_interface.py`: retire `_SCOPE_EXTENDED`, `_SCOPE_SHORE`, `_config_upper`
- [ ] `docs/ARCHITECTURE.md`: update address space section

### Full ECC
- [ ] Hamming SECDED in silicon (replace soft ECC)

### ASIC Investigation
- [ ] Install OpenLane and run synthesis on `unicell.v`
- [ ] TinyTapeout area estimate
- [ ] Draft chipIgnite application (Efabless priority)
- [ ] Europractice / IMEC investigation

### INT64 / Future
- [ ] INT64: extend `compiler_int32` to 64-bit
- [ ] Windowed GUI / virtual desktop environment
- [ ] Video frame pond (far future)

---

## SECURITY PROPERTIES (design locked, implementation pending)
These are confirmed architectural requirements — implement when corresponding code is touched:
- [ ] Cell silently ignores CMD_RECONFIGURE if auth token does not match
- [ ] Cell silently ignores CMD_FREEZE / CMD_RELEASE if auth token does not match
- [ ] No error signal, no ACK, no NAK on auth failure
- [ ] auth_mask register is not readable via any bus operation
- [ ] auth_mask is set exactly once (first RECONFIGURE) and cannot be changed
- [ ] Freeze wire alone cannot override auth-failed freeze_latch state
- [ ] Auth check is per-transaction, not per bus-write
- [ ] Bridge does not reveal whether it accepted or rejected a transaction
- [ ] OUTBOUND bridge applies same auth model for results leaving a pond
- [ ] Bridge depth declared in ICM, not negotiated at runtime
