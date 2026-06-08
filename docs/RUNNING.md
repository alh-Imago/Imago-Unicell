# Running Imago UniCell — Workflow Guide

This document covers every way to run a program in the Imago UniCell ecosystem:
from the Composer visual tool through the Python VM to physical FPGA hardware.
Each stage can be used independently or as part of the full pipeline.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Workflow                                    │
│                                                                     │
│  unicell_composer.html   ──→   .icm file                           │
│       (visual design)          (portable program)                   │
│                                     │                               │
│                            ┌────────┴─────────┐                    │
│                            ▼                  ▼                     │
│                     Python VM (any)     FPGA (hardware)            │
│                     workbench.py        fpga/icm_loader.py         │
│                     run_companion.py    fpga/fpga_bridge.py        │
└─────────────────────────────────────────────────────────────────────┘
```

The `.icm` file is the common currency. Everything produces it; everything runs it.

---

## 1. Composer — Visual Design Tool

The Composer is a standalone HTML file. No server, no install, no build step.

```bash
# Open in any modern browser
open composer/unicell_composer.html         # macOS
xdg-open composer/unicell_composer.html    # Linux
start composer/unicell_composer.html       # Windows
```

### What you can do

- Place cells visually and wire them together
- Drop pre-built model macros from the library panel (INT32_ADD, FP32_MUL, etc.)
- Set gate_state per cell (drop-down or direct hex entry)
- Simulate in-browser before sending to hardware
- Export as `.icm` (File → Export ICM)
- Import community `.icm` files to inspect or extend

### Declaring ports (Composer **ports** tab)

Before exporting, declare named input and output ports in the **ports** tab
(left panel). Each port entry has:

- **Name** — the key that appears in the `.icm` `inputs`/`outputs` header and
  in any PTT (Pond Task Table) entries when the program runs under the OS
- **Address** — the bus address this port maps to (hex or decimal)
- **Direction** — IN or OUT

Port names are how other programs, the OS scheduler, and the CLI `run` command
address this program's I/O. A program with no declared ports still runs, but
its inputs and outputs are anonymous addresses — unusable from outside.

Port names become PTT entries when the program is loaded by a Ward. Name them
to match your design intent (e.g. `pixel_in`, `threshold`, `spike_out`), not
after internal signal names.

### Exporting a program

1. Declare ports in the **ports** tab
2. Design your circuit in the Composer canvas
3. File → Export ICM → choose a filename (e.g. `my_adder.icm`)
4. The `.icm` file is a JSON document containing cell records, metadata, and
   named input/output addresses

### Example `.icm` structure

```json
{
  "name": "not_gate",
  "records": [
    { "gs": 1, "in": 4096, "out": 8192 }
  ],
  "inputs":  { "a": 4096 },
  "outputs": { "result": 8192 }
}
```

`"gs": 1` is GS_NOT (bit 0 set). `"in"` and `"out"` are bus addresses.
Two-input cells add `"inB"` for the B (falling-edge) input address.

---

## 2. Python VM

The Python VM simulates the full UniCell array in software, with unlimited cells.
It is the primary development environment.

### Setup

```bash
git clone https://github.com/alh-Imago/Imago-Unicell.git
cd Imago-Unicell
pip install -r requirements.txt
```

### 2a. Workbench — browser UI

The workbench runs a local HTTP server and provides a live visual debugger:

```bash
python3 workbench.py
# Open http://localhost:7420 in your browser
```

From the workbench you can:
- Load a `.icm` file via the File panel
- Step tick-by-tick or run continuously
- Inspect every cell: gate state, input/output addresses, live data value,
  two-input indicator (A↑ B↓), Input B address and live B value
- Inject bus values manually
- Watch the bus panel update in real time
- Highlight cells by region

To load your `.icm` into the workbench via the UI: use the Load panel in
the top bar, browse to your `.icm` file, click Load.

### 2b. Loading an `.icm` in Python

```python
import json
from controller import ImagoController, CellMapRecord

# Load ICM file
with open("my_adder.icm") as f:
    icm = json.load(f)

# Reconstruct cell records
records = [
    CellMapRecord(r["gs"], r["in"], r["out"],
                  input_b_address=r.get("inB"))
    for r in icm["records"]
]

# Create controller and load
ctrl = ImagoController(cell_count=len(records) + 100)
rid  = ctrl.load_map(records, icm.get("name", "program"))

# Inject inputs and run
inputs_raw = {
    icm["inputs"]["a"]: 1,    # set input 'a' to 1
}
result = ctrl.run(rid, inputs=inputs_raw,
                  capture_addresses=[icm["outputs"]["result"]])

print(result)   # {output_address: value}
```

### 2c. Using ProgramImage (named ranges)

`ProgramImage` gives named access to inputs and outputs:

```python
import json
from program_image import ProgramImage

with open("my_adder.icm") as f:
    img = ProgramImage.from_dict(json.load(f))

# Run with named inputs, get named outputs
result = img.run(inputs={"a": 1, "b": 0})
print(result["result"])  # 1
```

### 2d. Compiling from source (no Composer needed)

**CLI compile with port scan and prompt**

```bash
imago compile myfile.py my_function --save my_function.icm
```

Before compiling, the CLI scans the function and identifies its inputs and
return value. In an interactive terminal it prompts you to confirm or rename
each port:

```
Found in 'my_function':
  Inputs:  ['a', 'b']
  Output:  output

Confirm or rename ports (press Enter to keep the discovered name):

  Input 'a' → pixel_in
    → will be named 'pixel_in' in .icm
  Input 'b' → threshold
    → will be named 'threshold' in .icm
  Output 'output' →
```

Press Enter to accept a name as-is, or type a replacement. Port names become
the keys in the `.icm` `inputs`/`outputs` header. They are also registered as
PTT entries when the program is loaded by a Ward, so name them to match your
system's I/O convention.

In non-interactive use (scripts, CI), discovered names are used without
prompting.

**Python API compile**

```python
from compiler import ImagoCompiler
from controller import ImagoController

source = """
def my_and(a, b):
    return a and b
"""

compiler = ImagoCompiler()
records, graph, input_map, output_addrs = compiler.compile_function(
    source, "my_and", ["a", "b"]
)

ctrl = ImagoController(cell_count=len(records) + 50)
rid  = ctrl.load_map(records, "my_and",
                     known_values=compiler.known_values)

result = ctrl.run(rid,
    inputs={input_map["a"]: 1, input_map["b"]: 1},
    capture_addresses=output_addrs
)
print(result)  # {output_addr: 1}
```

### 2e. 32-bit integer functions

```python
from compiler_int32 import run_int32_function

result = run_int32_function(
    "def add(a: int32, b: int32) -> int32: return a + b",
    "add",
    {"a": 100, "b": 200}
)
print(result)  # 300
```

### 2f. Running the OS session

```bash
python3 run_companion.py
```

This launches the COMPANION OS with Shore, Ward, and ShoreKeeper active.
Useful for testing Pond-level programs that use the full OS layer.

### 2f-ii. PondManager — OS-level pond lifecycle

For programs that need Ward health monitoring, PTT tracking, bridge security,
and the workspace/program pond model, use `PondManager` rather than a bare
`ImagoController`:

```python
from pond import PondManager
from unicell_array import UniCellArray
import json

array = UniCellArray(cell_count=8192)
mgr   = PondManager(array)

# Create a user session workspace (PRIVATE, INCREMENTAL PTT)
workspace = mgr.spawn_workspace(owner_id="user_alice")

# Load a program from .icm into its own PRIVATE PROCESS pond
with open("adder_int32.icm") as f:
    icm = json.load(f)
program = mgr.spawn_pond_from_icm(icm, owner_id="user_alice", cell_count=8192)

# Wire workspace ↔ program: bus addresses + whitelist grants both ways
conn = mgr.connect(workspace, program)
print(conn)
# {
#   "workspace_pond":   "pond_0001",
#   "program_pond":     "pond_0002",
#   "program_name":     "adder_int32",
#   "ws_outbound_addr": 9,      # workspace fires inputs to program INBOUND
#   "pg_inbound_addr":  9,      # program receives here
#   "pg_outbound_addr": 1,      # program fires results to workspace INBOUND
#   "ws_inbound_addr":  1,      # workspace receives results here
# }
```

After `connect()`:
- Program pond is PRIVATE — only `user_alice`'s workspace may write to it
- Workspace PTT has a `PRIMITIVE` entry for the program's output port
- Program PTT has `TILE_IN` entries per input port (IDLE, waiting for values)
- All cells have `_ptt_ref` wired — sentry ticks fire, Ward tracking is live

**Multiple programs on one workspace:**

```python
prog_a = mgr.spawn_pond_from_icm(icm_a, owner_id="user_alice")
prog_b = mgr.spawn_pond_from_icm(icm_b, owner_id="user_alice")

mgr.connect(workspace, prog_a)
mgr.connect(workspace, prog_b)

# Both programs route output back to the same workspace INBOUND address.
# The wired-OR bus handles fan-in — no routing overhead.
# The workspace PTT tracks both: one PRIMITIVE entry per program output.
```

**PTT layout after spawn + connect (adder_int32 example):**

```
Program pond PTT:
  [0] BRIDGE_INBOUND   INBOUND_bridge    ACTIVE  (always-on)
  [1] BRIDGE_OUTBOUND  OUTBOUND_bridge   ACTIVE  (always-on)
  [2] TILE_IN          adder_int32.a     IDLE    ← waiting for input
  [3] TILE_IN          adder_int32.b     IDLE    ← waiting for input
  [4] PRIMITIVE        adder_int32.result IDLE   ← sentry armed, waiting

Workspace PTT:
  [0] BRIDGE_INBOUND   INBOUND_bridge    ACTIVE
  [1] BRIDGE_OUTBOUND  OUTBOUND_bridge   ACTIVE
  [2] WORKSPACE        workspace.session IDLE
  [3] PRIMITIVE        adder_int32.result IDLE  ← connected program output
```

See [ARCHITECTURE.md](ARCHITECTURE.md) § OS Layer for the full design.

### 2g. Test suites

Two primary test suites run against the VM:

```bash
# Compiler and tile library tests
PYTHONPATH=. python tests/vm/test_compiler_int32.py   # 133 tests
PYTHONPATH=. python tests/vm/test_fp_tiles.py         # 236 tests

# iCEBreaker silicon validation (requires hardware connected)
python tests/fpga/test_sanity.py /dev/ttyUSB0         # 31 tests on silicon
```

Current pass counts:
- `test_compiler_int32.py` — **133/133** (MUX selector, passthrough, arithmetic, comparisons, nested ifs)
- `test_fp_tiles.py` — **236/236** (all tile types, MIF family, edge cases)
- `test_sanity.py` — **31/31** on iCEBreaker silicon (two-arrival model, all gate types, CMD_ARRAY_RESET, preload_sel, shift_out_en)

Note: iCEBreaker has a **4-cell hardware limit** due to the 16-bit data bus packing on the UART bridge. Tests are designed for this constraint. `shift_in_en` validation requires Arria 10 (pending hardware bring-up).

---

## 3. FPGA — Physical Hardware

The FPGA runs the UniCell array in real silicon. The Python host handles
everything above the bus (configuration, Shore, COMPANION, workbench UI)
via a UART bridge.

### Supported boards

| Board | FPGA | Cells | Toolchain |
|-------|------|-------|-----------|
| iCEBreaker v1.0e | iCE40UP5K | 32–64 | OSS CAD Suite (yosys + nextpnr-ice40) |
| iCEstick | iCE40HX1K | 8–16 | OSS CAD Suite |
| Basys 3 / Arty A7 | Artix-7 | 256 | Vivado ML Standard (free) |
| OrangeCrab | ECP5 25F | 256 | OSS CAD Suite (nextpnr-ecp5) |
| Kintex-7 XC7K480T | Kintex-7 | 600–1,500 | Vivado ML Standard |

### 3a. Build and flash (iCEBreaker)

```bash
# Install OSS CAD Suite
# https://github.com/YosysHQ/oss-cad-suite-build

cd fpga

# Build bitstream
yosys -p "synth_ice40 -top top -json unicell.json" verilog/unicell.v \
      verilog/unicell_array.v verilog/uart_bridge.v verilog/top_icebreaker.v
nextpnr-ice40 --up5k --package sg48 --json unicell.json \
              --pcf constraints/icebreaker.pcf --asc unicell.asc
icepack unicell.asc unicell.bin

# Flash
iceprog unicell.bin
```

Or use the provided build script:
```bash
cd fpga
./build_icebreaker.bat     # Windows
# (equivalent commands in README_FPGA.md for Linux/Mac)
```

### 3b. Load an `.icm` onto the FPGA

Once the bitstream is on the board and the UART bridge is running:

```bash
# Linux / Mac
python3 fpga/icm_loader.py --port /dev/ttyUSB0 --icm composer/examples/not_gate.icm

# Windows
python3 fpga/icm_loader.py --port COM4 --icm composer\examples\not_gate.icm

# With optional test (injects known input, checks output)
python3 fpga/icm_loader.py --port /dev/ttyUSB0 --icm my_design.icm --test
```

The loader:
1. Reads the `.icm` file
2. Resets the FPGA array
3. Configures each cell via UART (gate_state, input address, output address, inB)
4. Reports armed cell count
5. Runs the optional test if `--test` is set

### 3c. Load an `.icm` in Python (FPGA target)

```python
import json
from fpga.fpga_bridge import FPGABridge
from fpga.icm_loader import load_icm, load_onto_fpga

# Connect to the FPGA
bridge = FPGABridge(port="/dev/ttyUSB0", baud=115200)
bridge.connect()

# Load an ICM file
icm = load_icm("my_design.icm")
success = load_onto_fpga(bridge, icm, max_cells=64)

if success:
    # Inject an input value
    bridge.inject(address=0x1000, value=1)

    # Read a fired event from the FPGA
    event = bridge.wait_fired(timeout=1.0)
    if event:
        print(f"Output address 0x{event.address:04X} = {event.value}")

bridge.disconnect()
```

### 3d. Workbench with FPGA backend

The workbench can route all bus transactions through the physical FPGA instead
of the software VM:

```bash
python3 workbench.py --fpga --port /dev/ttyUSB0
# Open http://localhost:7420

# Windows
python3 workbench.py --fpga --port COM4
```

The UI is identical — cells, bus, regions, inspector — but every tick runs on
silicon. The software VM handles regions and configuration; the FPGA handles
the wired-OR bus and cell execution.

### 3e. FPGA bridge protocol (reference)

The bridge sends 13-byte packets over UART at 115200 baud:

| Command | Byte | Payload |
|---------|------|---------|
| CMD_INJECT | 0x01 | bus1(4) + addr(4) + data(4) |
| CMD_CONFIGURE | 0x02 | gate_state(4) + in_addr(4) + out_addr(4) |
| CMD_RESET | 0x03 | — |
| CMD_STATUS | 0x04 | — |
| CMD_FREEZE | 0x06 | — |
| CMD_RELEASE | 0x07 | — |

Responses:

| Response | Byte | Payload |
|----------|------|---------|
| RSP_FIRED | 0x10 | addr(4) + data(4) + handshake(1) |
| RSP_STATUS | 0x11 | armed_count(4) + cycle_count(4) |
| RSP_ERROR | 0xFF | error_code(1) |

---

## 4. Full Pipeline Example

Design a NOT gate in the Composer, run it in the VM, then load it onto the FPGA.

### Step 1: Design in Composer

Open `composer/unicell_composer.html`. Place one cell, set gate_state = 0x00000001
(GS_NOT), set input address = 0x1000, output address = 0x2000. Export as `not_gate.icm`.

### Step 2: Run in the VM

```python
import json
from controller import ImagoController, CellMapRecord

with open("not_gate.icm") as f:
    icm = json.load(f)

records = [CellMapRecord(r["gs"], r["in"], r["out"]) for r in icm["records"]]
ctrl = ImagoController(cell_count=50)
rid  = ctrl.load_map(records, "not_gate")

# NOT(0) = 1
result = ctrl.run(rid, inputs={0x1000: 0}, capture_addresses=[0x2000])
print(result)  # {8192: 1}

# NOT(1) = 0
rid2 = ctrl.load_map(records, "not_gate")
result2 = ctrl.run(rid2, inputs={0x1000: 1}, capture_addresses=[0x2000])
print(result2)  # {8192: 0}
```

### Step 3: Load onto FPGA

```bash
python3 fpga/icm_loader.py --port /dev/ttyUSB0 --icm not_gate.icm --test
```

Expected output:
```
[ICM] Program:  not_gate
[ICM] Cells:    1
[FPGA] Cell 0: gs=0x00000001  in=0x1000  out=0x2000
[FPGA] 1 cell(s) armed
[TEST] NOT(0) = 1  ✓
[TEST] NOT(1) = 0  ✓
```

Same `.icm` file, same result, different substrate.

---

## 5. Choosing a Variant for FPGA

| Situation | Use |
|-----------|-----|
| First FPGA bring-up, iCEBreaker | Edge (`unicell-edge/fpga/`) |
| Large array, many PASS delay cells | Latch (`unicell-latch/fpga/`) |
| Development and algorithm testing | Standard (root) |
| Unsure | Build Edge first, compare Latch if timing closure is hard |

The Verilog files are in `fpga/verilog/` (standard), `unicell-latch/fpga/verilog/`,
and `unicell-edge/fpga/verilog/`. All are Verilog-2001 clean and synthesise on any
family (iCE40, ECP5, Artix-7, Kintex-7).

---

## 6. Bring-Up Sequence (new hardware)

When targeting a new FPGA board, follow this sequence — each stage confirms the
previous one before adding complexity:

1. **LED blink** — basic FPGA sanity (clock, reset, I/O)
2. **UART loopback** — verify TX/RX wiring (common gotcha: TX/RX swapped)
3. **NOT gate** — `icm_loader.py not_gate.icm --test`
   Confirms: cell configuration, gate tree, output buffer drain
4. **Two-input AND** — `icm_loader.py and_gate.icm --test`
   Confirms: SYNC_WAIT, posedge A / negedge B, two-cell addressing
5. **Bridge pair** — `fpga/test_stage5.py --port ...`
   Confirms: multi-cell wired-OR, pond isolation via bridge cells
6. **Scale to 8+ cells** — `fpga/test_stage6.py --port ...`
   Confirms: address space, cell density, timing at target frequency

Example ICM files for stages 3–4 are in `composer/examples/`.

---

## 7. Requirements

```
Python 3.10+
pyserial       (FPGA bridge only — pip install pyserial)
llvmlite       (LLVM frontend only — pip install llvmlite)

FPGA (iCE40):
  OSS CAD Suite — https://github.com/YosysHQ/oss-cad-suite-build

FPGA (Artix-7 / Kintex-7):
  Vivado ML Standard (free) — https://www.xilinx.com/support/download.html
  Tick: 7 Series only (saves ~25 GB download)
  Tick: Install Cable Drivers
```

---

## 8. Where Things Live

| What | Where |
|------|-------|
| Composer (visual tool) | `composer/unicell_composer.html` |
| Example `.icm` files | `composer/examples/` |
| Workbench VM | `workbench.py` |
| OS session | `run_companion.py` |
| FPGA UART bridge | `fpga/fpga_bridge.py` |
| ICM loader (FPGA) | `fpga/icm_loader.py` |
| Verilog (standard) | `fpga/verilog/` |
| Verilog (latch) | `unicell-latch/fpga/verilog/` |
| Verilog (edge) | `unicell-edge/fpga/verilog/` |
| FPGA build guide | `fpga/README_FPGA.md` |
| Architecture docs | `docs/` |
| Test suites | `test_*.py` in each variant root |
