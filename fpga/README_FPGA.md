# Imago UniCell — FPGA Implementation
## v2 — Silicon validated May 2026 (iCEBreaker iCE40UP5K)

A physical hardware implementation of the UniCell NOR-universal computing architecture on FPGA. The cell array runs on the FPGA at full clock speed. The OS layer (Shore, COMPANION, workbench) runs on the host CPU via a UART bridge.

---

## What This Is

The Python VM in the main repository simulates the UniCell architecture in software. This FPGA implementation puts the cell array on real silicon — each cell is a physical register file and NOR gate topology running at the FPGA clock frequency, with a real shared bus and real wired-OR combining.

The result is a hybrid system:

```
┌─────────────────────────────┐    UART     ┌──────────────────────────┐
│         Host PC             │◄───────────►│       FPGA               │
│                             │             │                          │
│  Python workbench           │             │  UniCell array (64-1024) │
│  COMPANION OS               │             │  Shared bus              │
│  Shore registry             │             │  Wired-OR combining      │
│  Compiler (Python)          │             │  Deterministic timing    │
│  fpga_bridge.py             │             │  uart_bridge.v           │
└─────────────────────────────┘             └──────────────────────────┘
```

The FPGA handles what only silicon can do: deterministic bus timing at nanosecond resolution, true wired-OR bus combining, and cell execution in hardware.

The host CPU handles everything above the bus: configuration, routing, the OS, and the workbench UI.

---

## Supported Boards

| Board | FPGA | Cells | LUT Usage | Notes |
|-------|------|-------|-----------|-------|
| iCEBreaker | iCE40UP5K | 32-64 | 80-97% | Recommended for first try |
| IceStick | iCE40HX1K | 8-16 | 60-80% | Very small — proof of concept |
| Basys 3 | Artix-7 35T | 256 | ~35% | Good development board |
| Arty A7-35 | Artix-7 35T | 256 | ~35% | Ben Eater territory |
| Arty A7-100 | Artix-7 100T | 1024 | ~14% | Comfortable headroom |
| OrangeCrab | ECP5 25F | 256 | ~20% | Robert Baruch territory |
| ULX3S | ECP5 85F | 1024+ | ~10% | Plenty of room |

---

## Quick Start

### 1. Install the toolchain

**Open source (iCE40 and ECP5):**
```bash
# Ubuntu/Debian
sudo apt install yosys nextpnr-ice40 nextpnr-ecp5 icestorm

# Mac (Homebrew)
brew install yosys nextpnr iceprog
```

**Proprietary (Artix-7 — Basys 3, Arty A7):**
- Vivado (free WebPack edition) from AMD/Xilinx

### 2. Build for your board

**iCEBreaker (iCE40UP5K — recommended first board)**
```bash
cd fpga/verilog
yosys -p "synth_ice40 -top top -json top.json" \
    top_icebreaker.v unicell_array.v unicell.v uart_bridge.v
nextpnr-ice40 --up5k --package sg48 \
    --json top.json --asc top.asc \
    --pcf ../constraints/icebreaker.pcf
icepack top.asc top.bin
iceprog top.bin
```

**IceStick (iCE40HX1K — proof of concept, 8 cells)**
```bash
cd fpga/verilog
yosys -p "synth_ice40 -top top -json top.json" \
    top_icestick.v unicell_array.v unicell.v uart_bridge.v
nextpnr-ice40 --hx1k --package tq144 \
    --json top.json --asc top.asc \
    --pcf ../constraints/icestick.pcf
icepack top.asc top.bin
iceprog top.bin
```

**Basys 3 (Artix-7 35T — 256 cells)**

Open Vivado, create a new RTL project, add all `.v` files and `basys3.xdc`. Set top module to `top`. Run Synthesis → Implementation → Generate Bitstream. Program via Hardware Manager.

**Arty A7-35 (Artix-7 35T — 256 cells)**

Open Vivado, create project, add all `.v` files and `arty_a7_35.xdc`. Top module `top`. Run full flow and program via JTAG.

**Arty A7-100 (Artix-7 100T — 1024 cells)**

Same as A7-35 but use `arty_a7_100.xdc`. In the top-level file set `define ARTY_A7_100` or change `NUM_CELLS` to 1024.

**OrangeCrab (ECP5 25F — 256 cells)**
```bash
cd fpga/verilog
yosys -p "synth_ecp5 -top top -json top.json" \
    top_orangecrab.v unicell_array.v unicell.v uart_bridge.v
nextpnr-ecp5 --25k --package CSFBGA285 \
    --json top.json --textcfg top.config \
    --lpf ../constraints/orangecrab.lpf
ecppack --compress top.config top.bit
dfu-util -d 1209:5af0 -D top.bit
```

**ULX3S (ECP5 85F — 1024 cells)**
```bash
cd fpga/verilog
yosys -p "synth_ecp5 -top top -json top.json" \
    top_ulx3s.v unicell_array.v unicell.v uart_bridge.v
nextpnr-ecp5 --85k --package CABGA381 \
    --json top.json --textcfg top.config \
    --lpf ../constraints/ulx3s.lpf
ecppack --compress top.config top.bit
fujprog top.bit
```

### 3. Install Python dependencies

```bash
pip install pyserial
```

### 4. Connect and test

```bash
# Find your serial port
# Windows: check Device Manager for COM port
# Linux: ls /dev/ttyUSB* or ls /dev/ttyACM*
# Mac: ls /dev/tty.usbserial*

# Run the demo
python3 fpga_bridge.py --port /dev/ttyUSB0 --demo
```

You should see:
```
[FPGA] Connected to /dev/ttyUSB0 at 115200 baud
[FPGA] Armed cells: 0
[FPGA] Cycle count: 0

[FPGA] Demo: NOT gate
  Configure one cell as GS_NOT
  Input address:  0x1000
  Output address: 0x2000
  Injecting input=0...
  Output at 0x2000: 1 (expected 1) ✓
  Injecting input=1...
  Output at 0x2000: 0 (expected 0) ✓

[FPGA] Demo: NAND via wired-OR (two NOT cells)
  Cell A: NOT(input_A) → address 0x3000
  Cell B: NOT(input_B) → address 0x3000
  Address 0x3000 receives OR of both outputs = NAND(A,B)
  NAND(0,0) = 1 (expected 1) ✓
  NAND(0,1) = 1 (expected 1) ✓
  NAND(1,0) = 1 (expected 1) ✓
  NAND(1,1) = 0 (expected 0) ✓
```

### 5. Connect the workbench

```bash
# In one terminal — start the FPGA bridge server
python3 fpga_bridge.py --port /dev/ttyUSB0 --server

# In another terminal — start the workbench pointing at the FPGA
python3 workbench.py --fpga --port /dev/ttyUSB0
```

The workbench will show the FPGA cell array. Load a demo or compile a program — it runs on real silicon.

---

## Architecture Notes

### The Wired-OR Bus

The most important architectural property to verify on real hardware is the wired-OR bus. Two NOT cells sharing an output address should produce NAND:

```
NOT(A) → address 0x3000
NOT(B) → address 0x3000

When both fire in the same cycle:
  bus at 0x3000 = NOT(A) OR NOT(B) = NAND(A,B)   [De Morgan]
```

The `demo_wired_or_nand()` function verifies this. If it passes, the fundamental architectural property is confirmed on your hardware.

### Cell Configuration

Each cell is configured via the FUNCTION_LOAD_PATTERN mechanism. When the bus carries `0xA5A5A5A5` at the cell's current input address, the next three bus transactions load:
1. `gate_state` — NOR topology bits and mode flags
2. `input_address` — address to listen to
3. `output_address` — address to write to

After loading, the cell is automatically armed (start flag set).

### Gate State Bits

| Bit | Name | Function |
|-----|------|---------|
| 0 | GS_NOT | NOT gate (NOR(x,x)) |
| 2 | GS_NOR | NOR(g0,g1) |
| 11 | GS_LATCH | Hold value — re-emit on every tick |
| 12 | GS_ONE_SHOT | Fire once then disarm |
| 13 | GS_INVERT | Invert output |
| 16 | GS_LOOP | Feed output back to input |

### CPU Offload Model

On small FPGAs (iCE40UP5K with 32-64 cells), the cell count is limited but the architecture is fully functional. The host CPU compensates by:

- Running the Python compiler to generate cell maps
- Managing address allocation (Shore)
- Handling OS decisions (COMPANION)
- Providing the workbench UI

The FPGA provides what matters most: real hardware timing, real wired-OR, and genuine parallel cell execution. Even 64 cells on real silicon demonstrates the architecture more convincingly than any simulation.

---

## Reporting Results

If you build this and test it, please report:

1. **Board used** and cell count synthesised
2. **LUT/register usage** from the synthesis report
3. **Clock frequency achieved** from timing analysis
4. **Demo results** — did NOT gate and NAND pass?
5. **Any timing issues** — cells firing out of order, bus glitches etc.

Reports can be submitted as GitHub issues at:
`https://github.com/alh-Imago/Imago-Unicell`

---

## File Structure

```
fpga/
├── verilog/
│   ├── unicell.v          — Single cell (NOR topology + registers + bus interface)
│   ├── unicell_array.v    — Cell array with wired-OR bus
│   ├── uart_bridge.v      — Host CPU UART interface
│   ├── top_icebreaker.v   — Top level: iCEBreaker (iCE40UP5K, 64 cells)
│   ├── top_icestick.v     — Top level: IceStick (iCE40HX1K, 8-12 cells)
│   ├── top_basys3.v       — Top level: Basys 3 (Artix-7 35T, 256 cells)
│   ├── top_arty_a7.v      — Top level: Arty A7-35 and A7-100 (256 / 1024 cells)
│   ├── top_orangecrab.v   — Top level: OrangeCrab (ECP5 25F, 256 cells)
│   └── top_ulx3s.v        — Top level: ULX3S (ECP5 85F, 1024 cells)
├── constraints/
│   ├── icebreaker.pcf     — iCEBreaker pin assignments
│   ├── icestick.pcf       — IceStick pin assignments
│   ├── basys3.xdc         — Basys 3 pin assignments (Vivado format)
│   ├── arty_a7_35.xdc     — Arty A7-35T pin assignments (Vivado format)
│   ├── arty_a7_100.xdc    — Arty A7-100T pin assignments (Vivado format)
│   ├── orangecrab.lpf     — OrangeCrab pin assignments (nextpnr-ecp5 format)
│   └── ulx3s.lpf          — ULX3S pin assignments (nextpnr-ecp5 format)
└── fpga_bridge.py         — Python host bridge (connects workbench to FPGA)
```

---

## What To Try

Once the basic demos pass, try these progressively more interesting experiments:

**1. SR Latch (GS_LATCH)**
Configure a cell with GS_LATCH. Inject a 1 — it latches and keeps emitting. Inject a 0 — it latches the 0. Demonstrates stateful behaviour in a single cell.

**2. Ring Oscillator (GS_NOT + GS_LOOP)**
Configure a cell with GS_NOT | GS_LOOP. The output feeds back to the input. The cell oscillates — toggling every tick. Watch it on a logic analyser. The frequency is exactly your clock frequency divided by the pipeline depth.

**3. Chain of NOT gates**
Configure 4 cells as NOT gates in a chain: A→B→C→D. Inject 0 at A. Measure latency at D's output. Each cell adds exactly one clock cycle of delay. This demonstrates deterministic pipeline depth.

**4. NAND from NOR**
Build NAND using the standard NOR construction:
`NAND(A,B) = NOR(NOR(A,A), NOR(B,B))`
Three cells. Verify all four input combinations.

**5. Compile and load**
Use the Python compiler to compile a simple function:
```python
from compiler_int32 import run_int32_function
# Then use fpga_bridge.load_map() to put the compiled cells on the FPGA
```

This is the full stack: Python source → compiler → cell map → FPGA silicon → result.

---

*Imago UniCell FPGA Implementation — v2. For timing issues and bring-up findings see [docs/VERILOG_SPEC.md](../docs/VERILOG_SPEC.md)*
*https://github.com/alh-Imago/Imago-Unicell*

---

## Hardware Support Matrix

Which `.icm` record fields are honoured at each layer. Updated as hardware
bring-up confirms behaviour. Last reviewed: 2026-05-11.

| Field | VM | fpga_bridge.py | icm_loader.py | Verilog (iCEBreaker) |
|---|---|---|---|---|
| `gs` — gate state | ✅ | ✅ | ✅ | ✅ validated May 2026 |
| `in` — input address | ✅ | ✅ | ✅ | ✅ validated May 2026 |
| `out` — output address | ✅ | ✅ | ✅ | ✅ validated May 2026 |
| `inB` — B-input address (SYNC_WAIT) | ✅ | ⚠️ sends 5th config word | ⚠️ warns, skips | ❌ not implemented |
| `stor` — storage/latch flag | ✅ | ✅ (encoded in `gs`) | ⚠️ not checked | ✅ GS_LATCH works |
| `init` — pre-load value | ✅ | ❌ not sent | ⚠️ warns, skips | needs hardware test |

### Notes

**`inB` / SYNC_WAIT** is the most significant gap. The Verilog config state
machine handles 4 words (`gs`, `in_addr`, `out_addr`, `data`). A 5th word
for `input_b_address` would need:
- Extended CFG state machine (add CFG_LOAD_BADDR state)
- `a_arrived` register to hold A until B is present
- B-input bus path through the NOR tree
- Timing closure verification at 24 MHz on iCEBreaker

`fpga_bridge.py` already sends the 5th word via `inject()` — the silicon
simply ignores it. `icm_loader.py` will warn if a loaded `.icm` contains
`inB` fields. Any design relying on SYNC_WAIT must use the Python VM until
this is implemented in silicon.

**`stor` / GS_LATCH** is implemented and validated. The `stor` field is
metadata only — what matters is the `gs` word having GS_LATCH (bit 11) set.
The icm_loader does not need to do anything extra for storage cells.

**`init`** (pre-load initial value for storage cells) needs hardware to test
properly. The VM injects the value before the first tick. On FPGA this would
require a pre-arm injection step in the UART protocol — not yet implemented.
`icm_loader.py` will warn if a loaded `.icm` contains non-null `init` fields.

### What to do when JTAG programmer arrives (~21 May 2026)

1. Confirm GS_LATCH holds value correctly across multiple ticks
2. Confirm `init` pre-load via manual injection before arm
3. Implement CFG_LOAD_BADDR in `unicell.v` and test SYNC_WAIT with a
   two-input AND cell (wire A and B, inject both, verify output)
4. Update this matrix when each item is confirmed in silicon
