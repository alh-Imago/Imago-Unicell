# FPGA Hardware Reference

Complete reference for the UniCell FPGA implementation.
Covers Verilog architecture, UART protocol, PCIe, build process, and silicon results.

---

## Hardware Overview

UniCell runs on two FPGA targets:

| Board | Device | Interface | Cells | Clock |
|-------|--------|-----------|-------|-------|
| iCEBreaker v1.0e | iCE40UP5K sg48 | UART 115200 | ~8 | 12 MHz |
| YPCB-00338-1P1 | xc7k480tffg1156-2 | PCIe x8 Gen1 | ~1,040 max | 125 MHz |

---

## Verilog Architecture

Four files in `fpga/verilog/`:

```
unicell.v          — single UniCell (the primitive)
unicell_array.v    — parametric array of NUM_CELLS instances
uart_bridge.v      — UART host bridge (iCEBreaker)
top_icebreaker.v   — iCEBreaker top: clock + bridge + array
top_kintex7.v      — Kintex-7 top: clock + bridge + array
```

PCIe files in `pcie/`:
```
axi_unicell_bridge.v   — AXI-Lite → UniCell command/data bus
top_xdma_unicell.v     — Kintex-7 PCIe top: XDMA + bridge + array
unicell_xdma.py        — Python tool: /dev/xdma0_user mmap interface
```

---

## Command Bus Protocol (v2.1)

Three signals form the command bus:

| Signal | Width | Purpose |
|--------|-------|---------|
| `cmd_bus` | 8-bit | Opcode only (256 opcodes, 243 currently free) |
| `cmd_addr` | 16-bit | Physical ID (boot) or logical address (run) |
| `cmd_data` | 32-bit | `auth[31:24]` + payload`[23:0]` |

### Opcodes

| Code | Name | Auth? | Description |
|------|------|-------|-------------|
| 0x00 | `CMD_NOP` | — | No operation |
| 0x01 | `CMD_DATA_WRITE` | — | Inject data packet onto bus |
| 0x02 | `CMD_SET_INPUT_ADDR` | — | Set logical input address |
| 0x03 | `CMD_SET_OUTPUT_ADDR` | — | Set output address, enables firing |
| 0x04 | `CMD_RECONFIGURE` | ✓ | Load topology + flags, sets output_set |
| 0x05 | `CMD_FREEZE` | ✓ | Freeze cell |
| 0x06 | `CMD_RELEASE` | ✓ | Unfreeze cell |
| 0x09 | `CMD_PING` | — | Ping (bridge responds) |
| 0x0A | `CMD_LATCH_IN_ON` | ✓ | Set latch_in — a_arrived held after firing |
| 0x0B | `CMD_LATCH_IN_OFF` | ✓ | Clear latch_in, reset a_arrived |
| 0x0C | `CMD_MEM_CALL` | ✓ | latch_in + one_shot + rearm atomically |
| 0x0D | `CMD_REARM` | ✓ | Rearm one-shot cell without full reconfigure |
| 0x0E | `CMD_SET_LOGICAL` | ✓ | Set logical input addr, suppress physical ID |

Auth token: `cmd_data[31:24]` (8-bit, 256 values).
Cells compare token against stored `auth_mask` in `cmd_latch[18:11]`.
`auth_mask == 0` means first boot — any token accepted, sets the mask.

### cmd_latch Bit Layout

```
[9:0]   topology    NOR gate selection (one-hot, 10 bits)
[10]    edge_mode   0=STANDARD/LATCH, 1=EDGE cell
[18:11] auth_mask   8-bit security token (zeroed before ICM serialisation)
[19]    output_set  1=output address configured, cell may fire
[22]    start_flag  1=cell armed and listening
[24:23] dtype       00=NUMERIC 01=SIGNED 10=ALPHA 11=DATETIME
[25]    invert_out  invert computed output
[26]    latch_in    hold a_arrived set after firing (single arrival fires next)
[27]    priority    high priority scheduling
[28]    trace       log every fire to Ward
[29]    breakpoint  halt array on fire
[30]    one_shot    fire once then disarm (start_flag → 0)
[31]    loop_back   feed computed output back as next a_data
```

### CMD_RECONFIGURE Payload Mapping

`cmd_data[23:0]` carries the config word. Bit positions:

```
cmd_data[9:0]   → topology
cmd_data[10]    → edge_mode
cmd_data[11]    → start_flag
cmd_data[13:12] → dtype
cmd_data[14]    → invert_out
cmd_data[15]    → latch_in
cmd_data[16]    → priority
cmd_data[17]    → trace
cmd_data[18]    → breakpoint
cmd_data[19]    → one_shot
cmd_data[20]    → loop_back
cmd_data[31:24] → auth_mask (stored in cmd_latch[18:11])
```

---

## Cell Boot Sequence

Cells start in **physical mode** — they respond to their `CELL_ID` on the bus.
After boot they switch to **logical mode** — they respond to `input_address`.

**4-packet boot sequence per cell:**

```
1. CMD_RECONFIGURE  (0x04) — what am I? (topology, flags, auth_mask)
2. CMD_SET_LOGICAL  (0x0E) — where do I listen? (logical addr, suppress physical)
3. CMD_SET_OUTPUT_ADDR (0x03) — where do I send? (output addr, enables firing)
4. CMD_RELEASE      (0x06) — arm me (start_flag=1)
```

**Safety gates:**
- Cell will not fire until `output_set=1` (set by RECONFIGURE or SET_OUTPUT_ADDR)
- Cell will not fire until `start_flag=1` (set by RECONFIGURE or RELEASE)
- Cell in physical_mode matches CELL_ID on bus, ignores logical address

---

## Cell Modes

### Standard (two-arrival latch)
Default. Two arrivals required before firing:
- First arrival: stored as `a_data`, `a_arrived=1`, no output
- Second arrival: fires `GATE(a_data, bus_data)`, resets `a_arrived`

### Latch-in (single arrival after first pair)
Set via `CMD_LATCH_IN_ON`. After the first pair fires, `a_arrived` stays set.
Subsequent single arrivals fire immediately using stored `a_data`.
Use: streaming input, continuously updated values.

### One-shot (delay/pipeline cell)
Set via `one_shot` flag in RECONFIGURE. Fires once on second arrival then disarms.
Rearm with `CMD_REARM` for next use.
Use: pipeline delay stages, triggered single-pulse outputs.

### Memory-on-call
`CMD_MEM_CALL` atomically sets `latch_in + one_shot + rearm`.
Cell wakes, fires on next pair, sleeps again.
Use: read-on-demand registers, lookup tables.

### Loop-back (accumulator/counter)
Set via `loop_back` flag. Computed output feeds back as next `a_data`.
Use: counters, accumulators, recurrent state cells.

---

## UART Bridge Protocol (iCEBreaker)

### Host → FPGA Frame (8 bytes)

```
Byte 0: 0x01 (UART_INJECT)
Byte 1: opcode [7:0]
Byte 2: addr_hi [15:8]
Byte 3: addr_lo  [7:0]
Byte 4: data[31:24]
Byte 5: data[23:16]
Byte 6: data[15:8]
Byte 7: data[7:0]
```

### Single-byte commands
```
0x03 — RESET (global escape — works even mid-frame)
0x04 — STATUS request
0x06 — FREEZE array
0x07 — RELEASE array
```

### FPGA → Host: Fired Response (7 bytes)
```
Byte 0: 0x10 (RSP_FIRED)
Byte 1: out_addr[15:8]
Byte 2: out_addr[7:0]
Byte 3: out_data[31:24]
Byte 4: out_data[23:16]
Byte 5: out_data[15:8]
Byte 6: out_data[7:0]
```

### FPGA → Host: Status Response (7 bytes)
```
Byte 0: 0x11 (RSP_STATUS)
Byte 1: armed_count[15:8]
Byte 2: armed_count[7:0]
Byte 3: cycle_count[31:24]
Byte 4: cycle_count[23:16]
Byte 5: cycle_count[15:8]
Byte 6: cycle_count[7:0]
```

---

## PCIe Interface (Kintex-7 / YPCB-00338-1P1)

### Stack
```
Host (Linux/Windows)
  └── xdma.ko (Xilinx/dma_ip_drivers — open source, no custom driver needed)
        └── /dev/xdma0_user (BAR0 MMIO, 4KB)
              └── XDMA IP (x8 Gen1, Vivado-generated, flashed permanently)
                    └── AXI-Lite 32-bit bus (125 MHz)
                          └── axi_unicell_bridge.v (we wrote this)
                                └── unicell_array.v (openXC7-synthesised)
```

### BAR0 Memory Map

Each cell occupies `CELL_STRIDE=32` bytes:

```
cell_base = cell_index × 32

cell_base + 0x00  [W]  CMD_WRITE    opcode[31:24] + payload[23:0]
cell_base + 0x04  [W]  DATA_WRITE   bus_addr[31:16] + data[15:0]
cell_base + 0x08  [R]  OUT_HI       out_addr[31:16] + out_data[15:0]
cell_base + 0x0C  [R]  OUT_LO       out_data[31:0]
cell_base + 0x10  [R]  STATUS       armed_count[31:16] + out_valid[0]
cell_base + 0x14  [R]  CYCLES       cycle_count[31:0]
0x10              [W]  RESET        write any value to reset array
```

### Board: YPCB-00338-1P1 (Inspur XC7K480T)

| Feature | Value |
|---------|-------|
| PCIe lanes | x8 Gen1 |
| GTX banks | X0Y16–X0Y23 |
| Refclk | J8 (100 MHz) |
| PERST | Y26 (LVCMOS18, active low) |
| System clock | AA28 (50 MHz) |
| System reset | R28 (LVCMOS18, active low) |
| LEDs | P30, M30, N30 (LVCMOS18) |
| DDR3 | 4NK77 D9PSH (Micron) |
| Driver | xdma.ko (Xilinx/dma_ip_drivers) |
| Vendor ID | 0x10EE (Xilinx/AMD) |

### Programming

**First time (JTAG → flash):**
```tcl
# In Vivado TCL console
write_cfgmem -format mcs -interface BPIx16 -size 256 \
    -loadbit "up 0x0 top_xdma_unicell.bit" \
    -file top_xdma_unicell.mcs

program_hw_cfgmem -hw_cfgmem [get_hw_cfgmems] \
    -mem_file top_xdma_unicell.mcs -verify
```

**After flash:** card boots automatically on power-up, PCIe enumerates, no JTAG needed.

### Python Tool
```bash
# Install xdma driver first
git clone https://github.com/Xilinx/dma_ip_drivers
cd dma_ip_drivers/XDMA/linux-kernel
make && sudo insmod xdma/xdma.ko

# Use the tool
sudo python3 pcie/unicell_xdma.py info
sudo python3 pcie/unicell_xdma.py configure --cell 0 --topology 0 --auth 0xa5
sudo python3 pcie/unicell_xdma.py inject --bus-addr 0 --data 42
sudo python3 pcie/unicell_xdma.py read
```

---

## Build Process

### iCEBreaker (OSS-CAD Suite, Windows)

```cmd
# From OSS-CAD Suite shell
cd C:\Users\Alan\Imago-Unicell\fpga
yosys -p "read_verilog verilog/unicell.v verilog/unicell_array.v verilog/uart_bridge.v verilog/top_icebreaker.v; synth_ice40 -top top -json top_icebreaker.json"
nextpnr-ice40 --up5k --package sg48 --pcf constraints/icebreaker.pcf --json top_icebreaker.json --asc top_icebreaker.asc --freq 24
icepack top_icebreaker.asc top_icebreaker.bin
iceprog top_icebreaker.bin
```

### Kintex-7 (WSL + Nix openXC7)

```bash
source ~/.nix-profile/etc/profile.d/nix.sh
nix develop ~/toolchain-nix
cd /mnt/c/Users/Alan/Imago-Unicell/fpga
bash build_kintex7.sh 100   # or 10, 500 etc.
```

### Kintex-7 PCIe (Vivado, one-time)

1. Open Vivado, new project, target `xc7k480tffg1156-2`
2. Add XDMA IP from IP Catalog (DMA/Bridge Subsystem for PCIe)
   - Configuration: x8 Gen1, BAR0=4KB AXI-Lite
3. Add source files:
   - `fpga/verilog/unicell.v`
   - `fpga/verilog/unicell_array.v`
   - `pcie/axi_unicell_bridge.v`
   - `pcie/top_xdma_unicell.v`
4. Add constraints:
   - `fpga/verilog/top_kintex7.xdc`
   - `pcie/gtx_loc.xdc`
5. Run synthesis + implementation
6. Generate bitstream
7. Program to flash (permanent)

---

## Silicon Validation Results

### iCEBreaker (May 2026)

| Test | Result |
|------|--------|
| `test_sync_wait.py` | **16/16 PASS** |
| `test_new_opcodes.py` | **26/29 PASS** (3 timing edge cases) |
| ICESTORM_LC | 4,532 / 5,280 (85%) |
| Max frequency | 16.61 MHz (PASS at 12 MHz) |

### Kintex-7 100-cell (May 2026)

| Metric | Value |
|--------|-------|
| SLICE_LUTX | 57,338 / 597,200 (9%) |
| SLICE_FFX | 19,607 / 597,200 (3%) |
| LUTs per cell | ~573 |
| Max frequency | **26.73 MHz** (PASS at 12 MHz) |
| BRAM | 0 |
| DSP | 0 |
| Device limit | ~1,040 cells |

### Kintex-7 500-cell (May 2026)

| Metric | Value |
|--------|-------|
| SLICE_LUTX | 271,665 / 597,200 (45%) |
| Max frequency | 3.67 MHz (FAIL — routing congestion) |
| Notes | Timing failure due to wired-OR bus routing at scale |
|        | Bus segmentation needed above ~300 cells for timing closure |

---

## Opcode Extension Pattern

`cmd_bus` is 8-bit giving 256 opcodes. Currently 13 used, 243 free.

For future extension beyond 256 opcodes, reserve `0xFF` as an escape prefix:
```
0x00-0xFE  Standard opcodes (255, current)
0xFF + cmd_data[15:0]  Extended opcodes (65,535 additional)
```

The upper byte of cmd_data (`[31:24]`) carries auth on authenticated commands.
The lower 24 bits carry payload — enough for config words, addresses, or counter values.

---

## Counter / ECC Bridge Pattern

The `cmd_data[31:24]` auth field is repurposed as a **sequence counter** on
data packets using opcode `CMD_DATA_COUNTED` (reserved, 0x0F):

```
cmd_bus  = 0x0F (CMD_DATA_COUNTED)
cmd_addr = destination address
cmd_data[31:24] = sequence number (0-255, wraps)
cmd_data[23:0]  = payload data
```

A COUNTER cell stamps `cmd_data[31:24]` on each output.
A COMPARATOR cell at the receiving end checks the sequence number matches
the expected count before gating data through to waiting cells.

This provides simple ECC / delivery confirmation across bridge cell pairs
without any additional hardware — just opcode convention.
