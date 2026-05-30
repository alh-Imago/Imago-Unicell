# FPGA Hardware Reference

Complete reference for the UniCell FPGA implementation.
Covers Verilog architecture, UART protocol, PCIe, build process, and silicon results.

*Protocol v2.3. Ground truth: `fpga/verilog/unicell.v`. See also: `docs/CELL_INTERNALS.md`.*

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
uart_bridge.v      — UART host bridge (iCEBreaker) — v2.2 format, update pending
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

## Command Bus Protocol (v2.3)

### Two States — BOOT and RUN

Every cell starts in **BOOT state** at power-on.

```
BOOT state: cell exposes baked-in CELL_ID on input_address register.
            Boot controller finds it, sends CMD_BOOT_COMMIT → RUN state.

RUN state:  cell responds to logical input_address only.
            All commands require auth_token match.
```

### cmd_bus — 32-bit Unified Word

The command bus is a single 32-bit word broadcast to all cells each cycle.

```
bits  7:0   opcode        8-bit command code (256 opcodes)
bit   8     gate_enable   0=broadcast to all cells, 1=filter by gate_set
bits 16:9   gate_set      8-bit group tag (matches cell's stored group_tag)
bits 18:17  preload_sel   TRANSIENT — load constant into a_data + a_arrived:
                          00=none  01=0x00000000  10=0xFFFFFFFF  11=reserved
bits 20:19  shift_sel     TRANSIENT per-transaction shift:
                          bit19=shift_in_en  (left-shift bus_data before gate)
                          bit20=shift_out_en (right-shift output before emit)
                          shift amount in cmd_data[3:0] (nibble count 0-7)
bits 28:21  auth_token    8-bit token matched against cell's stored auth_mask
bits 31:29  spare         reserved, must be zero
```

`cmd_data[31:0]` carries the payload (meaning depends on opcode):

```
CMD_BOOT_COMMIT:      [15:0]=logical_addr  [23:16]=auth_mask  [31:24]=group_tag
CMD_SET_INPUT_ADDR:   [15:0]=address
CMD_SET_OUTPUT_ADDR:  [15:0]=address
CMD_RECONFIGURE:      [31:0]=full cmd_latch word (see below)
shift ops:            [3:0]=nibble shift count (0-7)
```

### Opcodes

| Code | Name | Auth? | Description |
|------|------|-------|-------------|
| 0x00 | `CMD_NOP` | — | No operation |
| 0x01 | `CMD_DATA_WRITE` | — | Inject data packet onto bus |
| 0x02 | `CMD_SET_INPUT_ADDR` | ✓ | Set logical input address |
| 0x03 | `CMD_SET_OUTPUT_ADDR` | ✓ | Set output address, enables firing |
| 0x04 | `CMD_RECONFIGURE` | ✓ | Load cmd_latch word (topology+flags+auth_mask) |
| 0x05 | `CMD_FREEZE` | ✓ | Disarm cell |
| 0x06 | `CMD_RELEASE` | ✓ | Re-arm cell |
| 0x07 | `CMD_BOOT_COMMIT` | — | **BOOT STATE ONLY**: set logical addr + auth_mask + group_tag → RUN |
| 0x09 | `CMD_PING` | — | Ping cell |
| 0x0A | `CMD_LATCH_IN_ON` | ✓ | Set latch_in — a_arrived held after firing |
| 0x0B | `CMD_LATCH_IN_OFF` | ✓ | Clear latch_in, reset a_arrived |
| 0x0C | `CMD_MEM_CALL` | ✓ | latch_in + one_shot + rearm atomically |
| 0x0D | `CMD_REARM` | ✓ | Rearm one-shot cell |
| 0x0E | `CMD_SET_LOGICAL` | ✓ | Legacy: set logical addr (use CMD_BOOT_COMMIT) |
| 0x0F | `CMD_PRELOAD` | ✓ | **DEPRECATED** — use preload_sel bits 18:17 |
| 0x10 | `CMD_CLEAR_ARRIVED` | ✓ | Clear a_arrived + a_data |
| 0x11 | `CMD_RESET_CELL` | ✓ | Clear state + rearm |
| 0x12 | `CMD_SWAP_AB` | ✓ | Load a_data from cmd_data[12:0], set a_arrived |
| 0x13 | `CMD_CAPTURE_REARM` | ✓ | Fire output + rearm one_shot |
| 0x14 | `CMD_SET_TOPO` | ✓ | Write topology bits only |
| 0x15 | `CMD_SET_INVERT` | ✓ | Toggle invert_out |
| 0x16 | `CMD_PRELOAD_HI` | ✓ | **DEPRECATED** — use preload_sel bits 18:17 |
| 0x30–0x45 | `CMD_TOPO_*` | ✓ | Topology presets (cold=even, armed=odd) |

Auth token: `cmd_bus[28:21]` (8-bit). Matched against `cmd_latch[18:11]`.
`auth_mask==0` → BOOT bypass, CMD_BOOT_COMMIT accepted without auth.

### cmd_latch Bit Layout (v2.3 — cell internal state)

Loaded by `CMD_RECONFIGURE`. **Not the command bus** — the cell's internal register.

```
[9:0]   topology    NOR gate selection (one-hot, 10 bits)
[10]    edge_mode   0=STANDARD (two-arrival), 1=EDGE (transition detection)
[18:11] auth_mask   8-bit security token — WRITE-ONLY, zeroed in ICM files
[19]    output_set  1=output address configured, cell may fire
[20]    latch_A_dis 1=disable A latch (PASS(B) from any topology)
[21]    latch_B_dis 1=disable B trigger (PASS(A) from any topology)
[22]    start_flag  1=cell armed and listening
[24:23] dtype       00=NUMERIC 01=SIGNED 10=ALPHA 11=DATETIME
[25]    invert_out  invert computed output (in EDGE mode: selects negedge)
[26]    latch_in    hold a_arrived after firing — single arrival fires next
[27]    priority    high priority scheduling
[28]    trace       log every fire to Ward
[29]    breakpoint  halt array on fire
[30]    one_shot    fire once then disarm
[31]    loop_back   feed computed output back as next a_data
```

No reserved bits — all 32 bits assigned.
`preload_sel` and `shift_sel` are command bus transient modifiers, not stored here.

**Latch disable truth table:**

| latch_A_dis | latch_B_dis | Effect |
|-------------|-------------|--------|
| 0 | 0 | Normal two-arrival gate (default) |
| 1 | 0 | PASS(B) — live value straight through |
| 0 | 1 | PASS(A) — stored value rebroadcast on any trigger |
| 1 | 1 | Dead cell — nothing fires |

### CMD_RECONFIGURE Payload Mapping

`cmd_data[31:0]` → `cmd_latch`:

```
cmd_data[9:0]   → topology
cmd_data[10]    → edge_mode
cmd_data[11]    → start_flag
cmd_data[12]    → latch_A_dis
cmd_data[13]    → latch_B_dis
cmd_data[15:14] → dtype
cmd_data[16]    → invert_out
cmd_data[17]    → latch_in
cmd_data[18]    → priority
cmd_data[19]    → trace
cmd_data[20]    → breakpoint
cmd_data[21]    → one_shot
cmd_data[22]    → loop_back
cmd_data[30:23] → auth_mask → stored in cmd_latch[18:11]
```

Note: auth_mask is in `cmd_data[30:23]` (v2.3). In v2.2 it was in `cmd_data[31:24]`.
The auth_token for the transaction itself is always in `cmd_bus[28:21]`.

---

## Cell Boot Sequence (v2.3)

Cells start in **BOOT state** — responding to baked-in `CELL_ID`.
One `CMD_BOOT_COMMIT` transaction flips the cell to **RUN state** permanently.

**2-transaction boot sequence (v2.3):**

```
1. CMD_BOOT_COMMIT (0x07) — no auth needed (cell unconfigured):
   cmd_data[15:0]  = logical input_address
   cmd_data[23:16] = auth_mask to store
   cmd_data[31:24] = group_tag (for gate_set filtering)
   → cell stores all three, clears physical_mode → RUN

2. CMD_RECONFIGURE (0x04) — auth now required:
   cmd_data = full cmd_latch word (topology, flags, auth_mask in [30:23])
   + CMD_SET_OUTPUT_ADDR as needed
   + CMD_RELEASE to arm (or set start_flag in cmd_latch word)
```

**Legacy 4-transaction sequence (v2.2 — current iCEBreaker Verilog):**
```
1. CMD_RECONFIGURE  — topology + flags + auth_mask in cmd_data[31:24]
2. CMD_SET_LOGICAL  — logical input address
3. CMD_SET_OUTPUT_ADDR — output address
4. CMD_RELEASE      — arm cell
```

`FPGABridge(protocol_v22=True)` uses the legacy sequence automatically.
Switch to v2.3 once `uart_bridge.v` is updated.

---

## preload_sel — Transient Preload

`cmd_bus[18:17]` loads a constant into `a_data` and sets `a_arrived=1`.
Applied after opcode logic, if auth passes. Independent of opcode.

```
00 = no preload
01 = load 0x00000000  (AND tree false side, NOR constant)
10 = load 0xFFFFFFFF  (NOT/XOR/XNOR constant)
```

Replaces the old CMD_PRELOAD + CMD_PRELOAD_HI two-step.
One transaction instead of two. Same effect — a_data persists until cell fires.

---

## shift_sel — Transient Shift Modifier

`cmd_bus[20:19]` shifts data in-flight. Amount in `cmd_data[3:0]` (nibble count).

```
bit 19 shift_in_en:  left-shift bus_data before entering gate tree
bit 20 shift_out_en: right-shift computed_output before emitting
shift amount: 0-7 nibbles (0-28 bits), nibble-aligned
```

Purely combinational — no state held. Sent fresh each transaction.
Nibble-aligned shifts are zero extra cells. Non-nibble-aligned residuals
require up to 3 extra cells.

---

## Cell Modes

### Standard (two-arrival latch)
Default. First arrival stored as `a_data`. Second arrival fires.

### Latch-in (single arrival after preload)
`latch_in=1` (cmd_latch[26]). `a_arrived` stays set after firing.
Every subsequent single arrival fires using stored `a_data`.
Requires `ENABLE_LATCH_IN=1` at synthesis (compiled out on iCEBreaker).

### One-shot
`one_shot=1` (cmd_latch[30]). Fires once then clears `start_flag`.
Rearm with `CMD_REARM`.

### Memory-on-call
`CMD_MEM_CALL` atomically sets `latch_in + one_shot + rearm`.

### Loop-back (accumulator/counter)
`loop_back=1` (cmd_latch[31]). Computed output feeds back as next `a_data`.

### Edge detection
`edge_mode=1` (cmd_latch[10]). Fires on bus_data[0] transition.
`invert_out=0` → posedge (0→1). `invert_out=1` → negedge (1→0).

---

## UART Bridge Protocol (iCEBreaker)

### v2.3 — Host → FPGA Frame (9 bytes) — pending uart_bridge.v update

```
Byte 0:   0x01 (UART_INJECT)
Bytes 1-4: cmd_bus[31:0] (32-bit unified command word)
Bytes 5-8: cmd_data[31:0]
```

### v2.2 Legacy — Host → FPGA Frame (8 bytes) — current iCEBreaker

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

### Single-byte commands (both versions)
```
0x03 — RESET
0x04 — STATUS request
0x06 — FREEZE array
0x07 — RELEASE array
```

### FPGA → Host: Fired Response (7 bytes, unchanged)
```
Byte 0: 0x10 (RSP_FIRED)
Bytes 1-2: out_addr[15:0]
Bytes 3-6: out_data[31:0]
```

### FPGA → Host: Status Response (7 bytes, unchanged)
```
Byte 0: 0x11 (RSP_STATUS)
Bytes 1-2: armed_count[15:0]
Bytes 3-6: cycle_count[31:0]
```

---

## PCIe Interface (Kintex-7 / YPCB-00338-1P1)

### Stack
```
Host (Linux/Windows)
  └── xdma.ko (Xilinx/dma_ip_drivers)
        └── /dev/xdma0_user (BAR0 MMIO, 4KB)
              └── XDMA IP (x8 Gen1, Vivado-generated)
                    └── AXI-Lite 32-bit bus (125 MHz)
                          └── axi_unicell_bridge.v
                                └── unicell_array.v
```

### BAR0 Memory Map (CELL_STRIDE=32 bytes per cell)

```
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
| LEDs | P30, M30, N30 (LVCMOS18) |
| Driver | xdma.ko (Xilinx/dma_ip_drivers) |
| Vendor ID | 0x10EE (Xilinx/AMD) |

---

## Build Process

### iCEBreaker (OSS-CAD Suite)

```cmd
cd fpga
yosys -p "read_verilog verilog/unicell.v verilog/unicell_array.v verilog/uart_bridge.v verilog/top_icebreaker.v; synth_ice40 -top top -json top_icebreaker.json"
nextpnr-ice40 --up5k --package sg48 --pcf constraints/icebreaker.pcf --json top_icebreaker.json --asc top_icebreaker.asc --freq 24
icepack top_icebreaker.asc top_icebreaker.bin
iceprog top_icebreaker.bin
```

### Kintex-7 (WSL + Nix openXC7)

```bash
source ~/.nix-profile/etc/profile.d/nix.sh
nix develop ~/toolchain-nix
cd fpga && bash build_kintex7.sh 100
```

---

## Silicon Validation Results

### iCEBreaker (May 2026 — v2.2 protocol)

| Test | Result |
|------|--------|
| `test_sync_wait.py` | **16/16 PASS** |
| `test_new_opcodes.py` | **26/29 PASS** (3 timing edge cases) |
| ICESTORM_LC | 4,532 / 5,280 (85%) |
| Max frequency | 16.61 MHz (PASS at 12 MHz) |

v2.3 iCEBreaker bring-up pending (uart_bridge.v update + CMD_BOOT_COMMIT test).

### Kintex-7 100-cell (May 2026)

| Metric | Value |
|--------|-------|
| SLICE_LUTX | 57,338 / 597,200 (9%) |
| LUTs per cell | ~573 |
| Max frequency | **26.73 MHz** |
| BRAM / DSP | 0 / 0 |
| Device limit | ~1,040 cells |

### Kintex-7 500-cell (May 2026)

| Metric | Value |
|--------|-------|
| SLICE_LUTX | 271,665 / 597,200 (45%) |
| Max frequency | 3.67 MHz (FAIL — routing congestion) |
| Notes | Bus segmentation needed above ~300 cells |
