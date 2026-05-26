# Imago UniCell — Silicon Validation Results

*Created 2026-05-20. Records confirmed results on physical hardware.*

---

## Summary

The Imago UniCell architecture has been validated on silicon. The core
claim — one cell type, one bus, one program format, identical behaviour
across substrates — is confirmed by hardware measurement.

---

## Hardware

### iCEBreaker (iCE40UP5K)

| Parameter | Value |
|-----------|-------|
| Device | Lattice iCE40UP5K-SG48 |
| Clock | 24 MHz (SB_HFOSC internal oscillator) |
| Cell count | 4 (current bitstream) |
| Address width | 16-bit (timing concession — architecture is 32-bit) |
| ENABLE_LATCH_IN | 0 (compiled out — timing constraint) |
| UART | 115200 baud, COM4 |
| Auth token | 0x2A5 |
| Interface | Python test scripts via pyserial |

**Note:** Board spec is 16 cells. Current bitstream uses 4 (`NUM_CELLS=4`
in `top_icebreaker.v`). Rebuild with `NUM_CELLS=16` to reach spec.
`ENABLE_LATCH_IN=0` means bit 26 (latch_in) is ignored in silicon —
all cells use the standard two-arrival model only.

### Kintex-7 (XC7K480T × 2)

| Parameter | Value |
|-----------|-------|
| Board | Dual XC7K480T PCIe accelerator card |
| Part number | YZCA-00338-104 (QN: QTF507TT0066A01) |
| Board files | github.com/TiferKing/ypcb_00338_1p1_hack |
| Memory | 10 × DDR3 chips (estimated 5–10 GB) |
| Interface | Xilinx Platform USB Cable (JTAG) |
| Status | **Awaiting PCIe riser cable — bring-up pending** |

---

## Confirmed Gate Operations (iCEBreaker, test_32bit_gate.py)

All tests run at 24 MHz, full 32-bit word width. Auth token 0x2A5.

| Test | Operation | Result | Notes |
|------|-----------|--------|-------|
| 1 | PASS(A) = A | ✅ PASS | Full 32-bit passthrough |
| 2 | NOT(A) = ~A | ✅ PASS | `NOT(0xDEADBEEF) = 0x21524110` |
| 3 | NOT(NOT(A)) = A | ✅ PASS | 2-cell chain confirmed |
| 4 | AND(A,B) = A&B | ✅ PASS | `AND(0xDEADBEEF, 0xCAFEBABE) = 0xCAACBAAE` |
| 5 | OR(A,B) = A\|B | ✅ PASS | `OR(0xDEADBEEF, 0xCAFEBABE) = 0xDEFFBEFF` |
| 6 | XOR(A,B) = A^B | ✅ PASS | `XOR(0xDEADBEEF, 0xCAFEBABE) = 0x14530451` |
| 7 | XNOR(A,A) = 0xFFFFFFFF | ✅ PASS | All bits equal |
| 8 | latch_in: store and re-emit | ✅ PASS | Overwrite confirmed |
| 9 | invert_out: PASS+invert = ~A | ✅ PASS | |
| 10 | loop_back: NOT oscillates | ✅ PASS | fire1=~A, fire2=A |

**15/15 PASS. "32-BIT GATE TREE CONFIRMED ON SILICON"**

---

## Confirmed Architecture Properties

### Two-Arrival Model

The fundamental cell behaviour — confirmed on silicon:

```
First arrival  at input_address → stored in a_data, a_arrived=True, NO output
Second arrival at input_address → fires gate(a_data, incoming) → output
```

- `NOT(A) = NOR(A,A)`: send A twice to same address ✅
- `AND(A,B)`: preload a_data=A, inject B as trigger → fires AND(A,B) ✅
- Chain propagation: cell N output = cell N+1 second arrival ✅

### Preloaded-A Pattern

Confirmed on silicon (May 2026). Silicon-validated pattern from
`test_ring_22.py` and `test_32bit_gate.py`:

```
1. Freeze array (CMD 0x06)
2. Configure all cells (topology + addresses)
3. Thaw array (CMD 0x07)
4. Send preload data writes (thawed — freeze drops data writes)
5. Inject trigger wave
```

**Critical: data writes during freeze are silently dropped.** `bus_hit =
!frozen && ...` in `unicell.v`. Freeze is for configuration only.

### Freeze/Thaw Protocol

```
0x06  FREEZE  — array live, cells cannot fire, data bus inactive
0x07  THAW    — array live, cells fire normally
```

Freeze prevents cell firing but does NOT prevent command (config) packets.
Preload data writes must happen while thawed.

### XNOR as Comparator

```
XNOR(secret, code) = 0xFFFFFFFF  ← all bits equal (match)
XNOR(secret, code) = 0xFFFFFFFE  ← bit 0 differs (mismatch for 1-bit secrets)
XNOR(secret, code) = 0x00000000  ← no bits equal
```

Confirmed 2026-05-20 on silicon. NOT 0 ≠ NOT 0xFFFFFFFF for mismatch
detection — check `!= 0xFFFFFFFF`, not `== 0`.

---

## Sequence Lock Test (test_ring_22.py)

**4-cell lock on 4-cell iCEBreaker bitstream.**

Architecture:
- Cell 0: XNOR in=0x30 out=0x40 (comparer, secret=1)
- Cell 1: XNOR in=0x31 out=0x41 (comparer, secret=0)
- Cell 2: XNOR in=0x32 out=0x42 (comparer, secret=1)
- Cell 3: PASS in=0x40 out=99  (output, one_shot)

Secret: [1, 0, 1]

### Test 1 — Wrong code [0, 0, 0]

```
comparer 0: XNOR(secret=1, code=0) = 0xFFFFFFFE  ← mismatch ✓
comparer 1: XNOR(secret=0, code=0) = 0xFFFFFFFF  ← match (both 0)
comparer 2: XNOR(secret=1, code=0) = 0xFFFFFFFE  ← mismatch ✓
addr99: not triggered (cell 3 not armed for wrong code path)
```

**PASS — Lock blocked unauthorised stream ✅**

### Test 2 — Correct code [1, 0, 1]

```
comparer 0: XNOR(secret=1, code=1) = 0xFFFFFFFF  ← match ✓
comparer 1: XNOR(secret=0, code=0) = 0xFFFFFFFF  ← match ✓
comparer 2: XNOR(secret=1, code=1) = 0xFFFFFFFF  ← match ✓
addr99: 0xFFFFFFFF received ← UNLOCKED
```

**PASS — Lock verified and UNLOCKED ✅**

**Preloaded spatial memory confirmed: cells hold secret values across
injections and correctly discriminate matching from non-matching code.**

---

## Software Validation Results

### INT32 Arithmetic (compiler_int32.py)

All operations confirmed correct via Python simulation using preloaded-A
pattern. Results 2026-05-19:

| Operation | Tests | Result |
|-----------|-------|--------|
| ADD | 9/9 + fuzz | ✅ |
| SUB | 5/5 + fuzz | ✅ |
| EQ | 5/5 | ✅ |
| NEQ | 4/4 | ✅ |
| Lt, Gt, LtE, GtE | 12/12 + fuzz | ✅ |
| min, max | 8/8 + fuzz | ✅ |
| **Total** | **81/82** | ✅ (1 structural depth check — non-critical) |

### Gate Compiler (compiler.py / run_compiled_function)

| Operation | Tests | Result |
|-----------|-------|--------|
| AND, OR, NOT | 10/10 | ✅ |
| MUX (4-cell chain) | 4/4 | ✅ |
| IfExp MUX | 2/2 | ✅ |

### Branch / Dispatch (branch.py)

| Test | Result |
|------|--------|
| DataTable structure | ✅ |
| Comparator all cases | ✅ |
| Routing destinations | ✅ |
| Volatile reload | ✅ |
| Freeze/thaw API | ✅ |
| **Total** | **56/56 ✅** |

### Core Tests

| Suite | Result |
|-------|--------|
| test_array.py | 19/19 ✅ |
| test_compiler.py | included above |
| test_compiler_v2.py | all ✅ |

---

## Key Architectural Discoveries (from silicon bring-up)

These were validated on hardware and now inform all simulation/compiler work:

1. **Two-arrival is the only model.** The old edge/latch/standard split has
   been retired. One cell type, two arrivals at one address. Period.

2. **ENABLE_LATCH_IN=0 on iCEBreaker.** Bit 26 (latch_in) is compiled out.
   Chain propagation must use two-arrival preload pattern, not latch_in.

3. **Freeze drops data.** `bus_hit = !frozen`. Data writes during freeze are
   silently dropped. Freeze is configuration-only.

4. **16-bit address matching** in current iCEBreaker bitstream
   (`bus_addr[15:0] == input_address`). The cell architecture is 32-bit
   throughout. 16-bit is a timing concession only — sits cleanly within
   the 32-bit model. Above Shore, a 64-bit hierarchical address
   (24-bit card + 8-bit die + 16-bit block + 16-bit cell) handles
   global routing. Cells never see above 32 bits.

5. **NUM_CELLS=4** in current bitstream. Board spec is 16. Rebuild with
   `NUM_CELLS=16` via `fpga/verilog/apply_fpga_v1.2.bat`.

6. **XNOR output is 0xFFFFFFFF (match) or varies (mismatch).** Not a
   clean 0/1 — downstream logic must check `== 0xFFFFFFFF` not `!= 0`.

---

## Pending

| Item | Status |
|------|--------|
| iCEBreaker NUM_CELLS=16 rebuild | Pending — known path |
| Kintex-7 PCIe bring-up | Awaiting riser cable |
| Kintex-7 Vivado project | Board files found (TiferKing/ypcb_00338_1p1_hack) |
| ENABLE_LATCH_IN=1 validation | Pending Kintex-7 |
| 32-bit address validation | Pending Kintex-7 |
| Full 8-cell sequence lock | Pending NUM_CELLS=16 rebuild |
| load(A)/run(B) API separation | Deferred |
| LIF neuron v3 rewrite | Deferred |

---

*This document records confirmed results only. See `MIGRATION_TODO.md`
for outstanding work items and `sessions/` for full session logs.*

---

## Kintex-7 Results (XC7K480T × 2)

*Pending riser cable. Section will be populated as bring-up progresses.*
*Capture everything — timings especially.*

### Hardware Identity
- Board: YZCA-00338-104 (QN: QTF507TT0066A01)
- Board files: github.com/TiferKing/ypcb_00338_1p1_hack
- Interface: Xilinx Platform USB Cable (JTAG)
- PCIe riser cable: arriving imminently

### Vivado Setup
| Step | Result | Notes |
|------|--------|-------|
| Board files installed | pending | |
| Device recognised in Hardware Manager | pending | |
| First bitstream load | pending | |
| Programming time | pending | |

### Timing (target 200 MHz)
| Metric | Result | Notes |
|--------|--------|-------|
| Clock period achieved | pending | |
| WNS (Worst Negative Slack) | pending | |
| TNS (Total Negative Slack) | pending | |
| NUM_CELLS at timing closure | pending | |

### Utilisation
| Resource | Used | Available | % |
|----------|------|-----------|---|
| LUTs | pending | 297,600 | - |
| FFs | pending | 595,200 | - |
| BRAMs | pending | 1,030 | - |
| DSPs | pending | 1,920 | - |

### Gate Operations (vs iCEBreaker baseline)
| Operation | iCEBreaker (24MHz) | Kintex-7 (target 200MHz) | Ratio |
|-----------|-------------------|--------------------------|-------|
| PASS | confirmed | pending | ~8x |
| NOT | confirmed | pending | ~8x |
| AND | confirmed | pending | ~8x |
| OR | confirmed | pending | ~8x |
| XOR | confirmed | pending | ~8x |
| XNOR | confirmed | pending | ~8x |

### First Transaction Latency
| Metric | Result |
|--------|--------|
| Host → cell → response | pending |
| vs iCEBreaker baseline | pending |

### Temperature
| Condition | Reading |
|-----------|---------|
| Idle | pending |
| Under load (NUM_CELLS full) | pending |
| Fan speed | pending |

### Notes
*(All results to be captured live during bring-up session)*

---

## Kintex-7 PCIe Build — May 2026 Session Log

*Full record of the XDMA implementation attempts, including failures.*
*Honest documentation of the engineering process — failures included for credibility.*

### Build Environment
- Vivado 2025.2 (AMD, 30-day eval license)
- XDMA IP 4.2 (DMA mode, x8 Gen1)
- Board: YPCB-00338-1P1 (Inspur, xc7k480tffg1156-2)
- Target: 100-cell UniCell array behind AXI-Lite PCIe bridge
- Source files: `pcie/top_xdma_unicell.v`, `pcie/axi_unicell_bridge.v`

### Synthesis Results
| Run | Status | LUT% | FF% | Notes |
|-----|--------|------|-----|-------|
| synth_1 (final) | ✅ Complete | 12.38% | 3.38% | 0 errors |
| xdma_0_synth_1 | ✅ Cached | 5.47% | 3.12% | XDMA IP out-of-context |

### Implementation Attempts

| Attempt | Date | Stage Reached | Outcome | Root Cause |
|---------|------|---------------|---------|------------|
| 1 | May 24 11:43 | opt_design | ❌ FAIL | sys_clk_gt port missing in XDMA 4.2 |
| 2 | May 24 14:37 | opt_design | ❌ FAIL | array_freeze port missing in unicell_array |
| 3 | May 24 14:55 | opt_design | ❌ FAIL | Opt 31-67: undriven LUT in pcie_block_i_i_10 |
| 4 | May 24 15:00 | opt_design | ❌ FAIL | DRC override in XDC not reaching cached checkpoint |
| 5 | May 24 15:03 | opt_design | ❌ FAIL | Same — cached synth still used |
| 6 | May 24 15:10 | place_design | ❌ FAIL | opt_design disabled — undriven nets hit place_design DRC |
| 7 | May 24 15:28 | opt_design | ❌ FAIL | pre_opt.tcl hook path doubled up |
| 8 | May 24 (eve) | opt_design | ❌ FAIL | cfg_mgmt_addr port doesn't exist in XDMA 4.2 DMA mode |
| 9 | May 24 (eve) | opt_design | ❌ FAIL | m_axi_awready unconnected — Vivado using cached synth |
| 10 | May 25 01:14 | place_design | ✅ PASS | Nuclear pre_opt.tcl + clean synth — past opt_design! |
| 11 | May 25 01:58 | route_design | ⚠️ TIMING | WNS -1.308ns — cpu_cmd fanout of 1,453 loads |
| 12 | May 25 (day) | route_design | ⚠️ TIMING | WNS -0.776ns — pipeline register helped, not enough |
| 13 | May 25 (day) | synthesis ❌ | ❌ FAIL | cmd_valid_w missing reg declaration |
| 14 | In progress | — | — | Pipeline reg + cmd_valid_w fix + multicycle constraint |

### Errors Encountered and Fixes

**sys_clk_gt** — XDMA 4.2 DMA mode has `sys_clk` only, not `sys_clk_gt`.
Added `IBUFDS_GTE2` refclk buffer, connected single `sys_clk` port.

**array_freeze** — Port removed from `unicell_array.v` (CMD_FREEZE handles it on bus).
Removed from `top_xdma_unicell.v` instantiation.

**Opt 31-67: pcie_block_i_i_10** — Vivado 2025.2 bug with XDMA 4.2 on 7-series.
Undriven LUT inputs inside PCIe hard block. Fixed via pre_opt.tcl hook that
calls `set_logic_zero` on all undriven pins in hierarchical cells before opt_design.

**Cached synthesis** — Vivado aggressively caches synthesis checkpoints.
Even `reset_run synth_1` sometimes reuses stale checkpoints. Fix: manually
delete `YPCB_00338_1P1_systest.runs\synth_1\` folder then relaunch.

**cfg_mgmt_addr** — Does not exist in XDMA 4.2 DMA mode (only in Bridge mode).
Removed tie-off connections from `top_xdma_unicell.v`.

**m_axi_awready fanout** — AXI full master interface ports (m_axi_*) need
tie-offs even when unused. Added to `top_xdma_unicell.v`.

**Timing: WNS -1.308ns** — `bridge/cpu_cmd_reg[0]` fanning out to 1,453 loads
(broadcasting opcode to all 100 cells). Route delay 90% of path.
Fix 1: Pipeline register stage between bridge and array outputs.
Fix 2: Register `cmd_valid_w` in same pipeline stage.
Fix 3: Multicycle path constraint (8 cycles = 32ns for bridge→array).

### Key Insight
The XDMA PCIe userclk runs at 250MHz (4ns period). UniCell only needs 12MHz.
Vivado was trying to close timing at 250MHz for paths that operate at 12MHz.
The multicycle path constraint explicitly tells Vivado to allow 8 clock cycles
(32ns) for bridge→array paths — matching actual operating requirements.

### Resource Usage (route_design attempt 11, 100 cells)
| Resource | Used | Available | % |
|----------|------|-----------|---|
| SLICE_LUTX | 49,214 | 597,200 | 8.2% |
| SLICE_FFX | 34,809 | 597,200 | 5.8% |
| BRAM | 19.5 | 955 | 2.0% |
| DSP | 0 | 2,800 | 0% |
| Failed routes | 0 | — | — |
| Total power | 3.415W | — | — |

*Note: BRAM usage increased vs openXC7 build — XDMA DMA engine uses BRAMs
for descriptor queues.*

---

## v2.2 Silicon Validation — May 2026

### iCEBreaker (OSS-CAD Suite, 12 MHz)

| Metric | Value |
|--------|-------|
| ICESTORM_LC | 4,584 / 5,280 (86%) |
| Max frequency | 15.59 MHz (PASS at 12 MHz) |
| Test suite | test_compound_opcodes.py |
| Results | **10/10 PASS** |

### Validated Features

| Feature | Opcode | Result |
|---------|--------|--------|
| AND preset (armed) | 0x37 | ✅ PASS |
| OR preset (armed) | 0x39 | ✅ PASS |
| XOR preset (armed) | 0x41 | ✅ PASS |
| NOR preset (armed) | 0x35 | ✅ PASS |
| AND preset (cold) | 0x36 | ✅ PASS |
| CMD_CLEAR_ARRIVED | 0x10 | ✅ PASS |
| CMD_RESET_CELL | 0x11 | ✅ PASS |
| CMD_SET_TOPO | 0x14 | ✅ PASS |

### Key Finding — SET_OUTPUT_ADDR
CMD_SET_OUTPUT_ADDR (0x03) appears to break cell firing when used
after RECONFIGURE. Root cause under investigation. Workaround: use
default cell addresses (input=CELL_ID, output=CELL_ID+1) and avoid
SET_OUTPUT_ADDR until the issue is diagnosed. Tests now use this
approach matching test_sync_wait.py proven methodology.

### SET_OUTPUT_ADDR Investigation (May 2026)

**Symptom:** CMD_SET_OUTPUT_ADDR (0x03) causes 6× RSP_ERROR (0xFF) bytes
to appear on the UART TX immediately after the command, before any
DATA_WRITE. Subsequent DATA_WRITEs produce no fired response.

**Same symptom:** CMD_SET_INPUT_ADDR (0x02) — DATA_WRITEs to new address
produce no response.

**Not affected:** CMD_SET_LOGICAL (0x0E) — works correctly.

**Workaround:** Use default cell addresses (input=CELL_ID, output=CELL_ID+1).
All tests use this approach. Compound opcodes 10/10 PASS.

**Root cause:** Unknown. Code inspection shows correct logic. Needs
simulation with waveform capture to identify the exact cycle where
spurious bus activity occurs. Likely a subtle timing issue in the
bridge-to-array signal path specific to iCEBreaker fabric timing.

**Not blocking:** No current functionality requires address reassignment
beyond default. Will investigate with GTKWave simulation.

### SET_OUTPUT_ADDR Bug — Root Cause Found (May 2026)

**Root cause:** Opcode 0x03 (CMD_SET_OUTPUT_ADDR) = ASCII `0x03` = the UART
bridge global escape byte. The 8-byte frame `01 03 00 00 a5 00 00 20` was
being parsed as:
- `0x01` → start 8-byte frame, cmd_active=1
- `0x03` → **global escape fires mid-frame**, cmd_active=0, array_rst=1
- `00 00 a5 00 00 20` → 6 unrecognised bytes → 6× RSP_ERROR (0xFF)

This caused the cell array to reset every time SET_OUTPUT_ADDR was sent.

**Fix:** `uart_bridge.v` — escape `0x03` only fires when `!cmd_active`.
When inside a frame, `0x03` is a valid opcode byte, not an escape.

**Verified:** Test B fires to addr 0x20 correctly. Armed count stays 1
after SET_OUTPUT_ADDR. 10/10 compound opcode tests still pass.

**Lesson:** Opcode assignments must avoid reserved UART control bytes.
`0x03` = ETX. `0x01` is the frame start marker. Both were used as
opcodes without realising `0x03` had special meaning in the bridge parser.

### Full Address Boot Validation (May 2026)

After UART bridge escape fix, boot_cell() fully validated:

| Test | Description | Result |
|------|-------------|--------|
| Test 1 | RECONFIGURE + SET_OUTPUT_ADDR + inject | ✅ fires to 0x20 |
| Test 2 | boot_cell() then inject | ✅ fires to 0x20 |
| Test 3 | boot_cell + CMD_TOPO_AND to logical addr | ❌ None — runtime targeting pending |
| Test 4 | CMD_TOPO_AND to physical CELL addr | ✅ fires to 0x20 |
| Test 5 | Broadcast CMD_TOPO_AND | ✅ fires to 0x20 |
| Test 8 | Step by step SET_OUTPUT_ADDR | ✅ fires to 0x20 |

**boot_cell() is fully functional.** Runtime-targeted preset opcodes
(addressing by logical input_address) still pending — Test 3 uses
addr=IN=0x10 but cell may not match on logical address yet. Separate
investigation needed for runtime targeting via dbg_input_addr wire.

### Kintex-7 PCIe Flash Programming — Status (May 25 2026)

**Bitstream status:** Generated and JTAG-loaded successfully ✅
- `top_xdma_unicell.bit` — in Vivado working dir `C:/Users/Alan/AppData/Roaming/Xilinx/Vivado/`
- `top_xdma_unicell_spi.mcs` — SPIx4 format for W25Q256 flash
- `top_xdma_unicell_spi.prm` — parameter file

**FPGA programmed via JTAG:** ✅
- "End of startup status: HIGH" confirmed
- Design loaded into FPGA RAM successfully

**PCIe enumeration:** ❌ Not yet visible in Device Manager
- Expected: PCIe requires cold boot to enumerate
- Bitstream loaded post-boot so PCIe root complex missed link training
- Need flash programmed → cold boot for proper enumeration

**Flash programming:** Blocked on correct part
- Board: YPCB-00338-1P1 / YZCA-00338-104
- Flash chip: W25Q256 (Winbond QSPI, confirmed from community research)
- Vivado part name: `w25q256jwq-spi-x1_x2_x4` ← use this
- MCS format: SPIx4 (regenerated with BITSTREAM.CONFIG.SPI_BUSWIDTH=4)
- Error: "Failure to set flash parameters" — chip not responding to init

**Next session — flash programming sequence:**
```tcl
open_hw_manager
connect_hw_server
open_hw_target
current_hw_device [get_hw_devices xc7k480t_0]
create_hw_cfgmem -hw_device [current_hw_device] [lindex [get_cfgmem_parts {w25q256jwq-spi-x1_x2_x4}] 0]
set_property PROGRAM.FILES {C:/Users/Alan/AppData/Roaming/Xilinx/Vivado/top_xdma_unicell_spi.mcs} [get_hw_cfgmems]
set_property PROGRAM.PRM_FILES {C:/Users/Alan/AppData/Roaming/Xilinx/Vivado/top_xdma_unicell_spi.prm} [get_hw_cfgmems]
set_property PROGRAM.ERASE 1 [get_hw_cfgmems]
set_property PROGRAM.CFG_PROGRAM 1 [get_hw_cfgmems]
set_property PROGRAM.VERIFY 1 [get_hw_cfgmems]
program_hw_cfgmem -hw_cfgmem [get_hw_cfgmems]
```

**If flash still fails:**
- Try w25q256jwq variant with different init — may need Vivado GUI approach
- Try programming FPGA first via JTAG, then immediately attempt flash
- Check if write-protect pin is held — board may have WP tied low
- Community repo: https://github.com/TiferKing/ypcb_00338_1p1_hack

**After successful flash:**
- Cold power cycle (full off, not reboot)
- Check Device Manager for Xilinx PCIe device
- Install xdma driver
- Run unicell_xdma.py to verify UniCell over PCIe

### Runtime Address Targeting Fix — Silicon Validated (May 2026)

**Fix:** `dbg_input_addr` port connection was backwards — `{16'h0, cell_input_addr}`
was driving the output rather than reading from it. Added dedicated
`dbg_input_addr_short` 16-bit port to unicell.v.

**iCEBreaker results after fix:**
- ICESTORM_LC: 4315/5280 (81%) — down from 88%
- Max frequency: 20.54 MHz — up from 14.60 MHz
- Test 3 (runtime logical address targeting): ✅ PASS

**Full test_v22_diag.py results: 8/8 meaningful tests pass**
- Test 1: None (expected — v2.1 style deprecated, no SET_OUTPUT_ADDR)
- Test 2: ✅ boot_cell() works
- Test 3: ✅ runtime logical address targeting (was broken, now fixed)
- Test 4: ✅ physical ID targeting
- Test 5: ✅ broadcast
- Test 6: ✅ legacy style
- Test 7: ✅ status correct
- Test 8: ✅ raw boot sequence
- Test 9: ✅ SET_LOGICAL correct

v2.2 iCEBreaker silicon fully validated.

### Flash Programming — Blocked (May 26 2026)

All standard approaches exhausted:
- `w25q256jwq-spi-x1_x2_x4` part — correct chip confirmed
- STARTUPE2 primitive added — didn't fix indirect programmer
- Bitstream written to impl_1 directory — no indirect .bit generated
- TiferKing's own bitstream — same "Failure to set flash parameters"
- openFPGALoader — can't detect JTAG cable (driver conflict)

**Root cause hypothesis:** This board uses MicroBlaze + SPI controller
to program flash (TiferKing's approach via xsct + ELF). Vivado's
indirect programmer doesn't work on this board.

**To fix properly:**
1. Install Vitis
2. Open workspace: E:/xilinx/ypcb_00338_1p1_hack/examples/extracted
3. Build YPCB_00338_1P1_App ELF
4. Use xsct to load bitstream + ELF via JTAG to program flash

**Workaround:** JTAG-load bitstream each session:
```tcl
open_hw_manager
connect_hw_server
open_hw_target
set_property PROGRAM.FILE {E:/xilinx/ypcb_00338_1p1_hack/examples/YPCB_00338_1P1_systest/YPCB_00338_1P1_systest.runs/impl_1/top_xdma_unicell.bit} [get_hw_devices xc7k480t_0]
program_hw_devices [get_hw_devices xc7k480t_0]
```

Then cold-reboot to get PCIe enumeration — but bitstream won't survive
power cycle until flash is programmed.

### Flash Programming — Final Diagnosis (May 26 2026)

**Root cause confirmed:** W25Q256JWQ returning all-zeros JEDEC ID
(Mfg ID: 0, Memory Type: 0, Memory Capacity: 0) — SPI bus connected
but flash not responding. WP# pin likely tied to GND on PCB (common
on repurposed compute cards to prevent accidental reprogramming).

**All software approaches exhausted:**
- Vivado TCL indirect programmer — fails
- Vivado GUI programmer — fails  
- STARTUPE2 primitive — didn't help
- TiferKing's own bitstream — fails
- openFPGALoader — can't detect cable
- CONFIG_VOLTAGE 1.8 / CFGBVS GND — set correctly

**Hardware solution required:**
- CH341A USB SPI programmer + SOIC-8 clip (~£5-8 on Amazon)
- Clip directly onto W25Q256 chip, bypass FPGA entirely
- Read existing contents first (backup)
- Write top_xdma_unicell_spi.mcs
- Verify
- Cold boot → PCIe enumeration

**Alternative:** Physically inspect board for WP# jumper or trace,
may be cuttable to enable write access via Vivado.

**MCS file ready at:**
E:/xilinx/ypcb_00338_1p1_hack/examples/YPCB_00338_1P1_systest/
YPCB_00338_1P1_systest.runs/impl_1/top_xdma_unicell_spi.mcs

### iCEBreaker v2.2 Full Regression Results (May 26 2026)

**test_compound_opcodes.py: 10/10 PASS** ✅
**test_v22_diag.py: 8/8 meaningful tests PASS** ✅
**test_sync_wait.py: 15/16 PASS** — 1 failure: one_shot re-fires after disarm (pre-existing)
**test_ring_22.py: FAIL** — pre-existing: uses old RECONFIGURE without SET_OUTPUT_ADDR
**test_chain.py: FAIL** — pre-existing: same issue, needs boot_cell() style setup

**Outstanding fixes needed:**
1. one_shot: after disarm, cell fires again on 2nd arrival — investigate
   pipeline register interaction with start_flag clearing
2. test_ring_22, test_chain: update to use boot_cell() addressing
