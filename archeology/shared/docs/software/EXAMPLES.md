# Imago UniCell — Examples

Complete runnable examples demonstrating the architecture.
All examples are in the repository root and run with `python3`.

---

## Bundled `.icm` Programs

Available via `imago examples` and `imago run <name>`:

| Name | Cells | What it shows |
|------|-------|---------------|
| `not_gate` | 1 | Single NOT cell — the primitive |
| `and_gate` | 1 | Two-input AND (GS_AND_V2 \| GS_SYNC_WAIT) |
| `add` | 1 | Single-bit AND (a and b) |
| `mux` | 5 | 2:1 multiplexer — NOT + AND + AND + OR |
| `adder_int32` | 483 | 32-bit Kogge-Stone adder, depth 2 |
| `lif_neuron` | 5 | Leaky Integrate-and-Fire neuron |
| `sum4` | 1,641 | Four int32 values, 3 chained KS adders, depth 6 |
| `equal32` | 95 | 32-bit equality — 32 XNOR cells in parallel |
| `parity8` | 7 | 8-input OR reduction, depth 3 |
| `countdown` | 32 | 8-bit decrement counter with zero-detect |
| `lif_cascade` | 15 | 3-neuron spike cascade, zero routing overhead |

```bash
imago examples                          # list all
imago run not_gate a=1                  # NOT(1) = 0
imago run and_gate a=1 b=1             # AND(1,1) = 1
imago run adder_int32 a=12345 b=67890  # 12345 + 67890 = 80235
imago run mux sel=1 a=1 b=0           # MUX(sel=1,a=1,b=0) = 1
imago run sum4 a=100 b=200 c=300 d=400 # 100+200+300+400 = 1000
imago run equal32 a=42 b=42            # 42==42 → 1
imago run parity8 b0=1 b1=0 b2=0 b3=0 b4=0 b5=0 b6=0 b7=0  # → 1
imago run lif_neuron synapse=1 threshold=1  # spike=1
```

---

## Python API Examples

```python
import imago
imago.set_verbose(False)

# Load and run a bundled program
vm = imago.VM()
vm.load_example("adder_int32")
print(vm.run(a=999, b=1))   # {"result": 1000}

# One-shot
result = imago.run_icm("adder_int32", inputs={"a": 5, "b": 3})
print(result)  # {"result": 8}

# Compile from source
vm2 = imago.compile_function(
    "def add(a, b): return a and b", "add")
print(vm2.run(a=1, b=1))   # {"output": 1}

# Compile with port names
vm3 = imago.compile_function(
    "def sub(a: signed, b: signed) -> signed:\n    return a and b",
    "sub",
    port_names={"output": "result"}
)
print(vm3.status())  # inputs=['a','b'] outputs=['result']
```

---

## Conway's Game of Life — `gol.py`

**43 UniCells per GoL cell.** A 6-stage Wallace tree counts 8 neighbours,
two comparators detect count==2 and count==3, and the GoL rule computes
the next state. All cells evaluate simultaneously — no sequential scan.

```bash
# Quick test: glider on 15×15 (9,675 cells)
python3 gol.py --width 15 --height 15 --pattern glider --ticks 20

# Blinker oscillator (period 2)
python3 gol.py --width 10 --height 10 --pattern blinker --ticks 6

# R-pentomino: chaotic, long-lived, produces gliders and still lifes
python3 gol.py --width 34 --height 34 --pattern r_pentomino --ticks 100

# Random initial state
python3 gol.py --width 34 --height 34 --pattern random --ticks 50

# Large grid — push the VM
python3 gol.py --width 48 --height 48 --pattern r_pentomino --ticks 200
```

**Scale (43 cells/GoL cell):**

| UniCells | GoL cells | Grid |
|----------|-----------|------|
| 10,000 | 232 | 15×15 |
| 50,000 | 1,162 | 34×34 |
| 100,000 | 2,325 | 48×48 |
| 500,000 | 11,627 | 107×107 |

**Verified patterns:**
- Blinker: oscillates H→V→H→V ✓
- Isolated cell: dies (underpopulation) ✓
- 2×2 block: stable still life ✓
- Glider: translates correctly ✓

---

## Parallel Sorting Networks — `sort.py`

**Bitonic sorting network.** All comparators within each stage fire
simultaneously. No sequential scan, no instruction loop.

### 1-bit sort (population sort)

Each compare-and-swap = AND (min) + OR (max) = 2 cells.

```bash
python3 sort.py --mode bits --n 16   # 160 cells, 10 stages
python3 sort.py --mode bits --n 32   # 480 cells, 15 stages
python3 sort.py --mode bits --n 64   # 1,344 cells, 21 stages
python3 sort.py --mode bits --n 128  # 3,584 cells, 28 stages

# Custom input
python3 sort.py --mode bits --n 8 --data 1,0,1,1,0,1,0,0
# → 00001111
```

### 8-bit byte sort

Each compare-and-swap = 8-bit cascaded comparator + 2×8-bit MUX ≈ 41 cells.

```bash
python3 sort.py --mode bytes --n 8   # 2,232 cells, 6 stages
python3 sort.py --mode bytes --n 16  # 7,440 cells, 10 stages
python3 sort.py --mode bytes --n 32  # ≈22,000 cells, 15 stages

# Custom values
python3 sort.py --mode bytes --n 8 --data 57,12,140,125,114,71,52,44
# → [12, 44, 52, 57, 71, 114, 125, 140]

# Random
python3 sort.py --mode bytes --n 16 --random --seed 99
```

**Network sizes:**

| n | Comparators | Stages | 1-bit cells | 8-bit cells |
|---|-------------|--------|-------------|-------------|
| 8 | 24 | 6 | 48 | 2,232 |
| 16 | 80 | 10 | 160 | 7,440 |
| 32 | 240 | 15 | 480 | ~22,000 |
| 64 | 672 | 21 | 1,344 | ~61,000 |
| 128 | 1,792 | 28 | 3,584 | ~163,000 |
| 256 | 4,608 | 36 | 9,216 | ~418,000 |

---

## UK Postcode Sort — `postcode_sort.py`

**Real data.** 997 real UK postcodes from the national dataset
(1.7M postcodes, 1GB uncompressed), geographically spread from
Aberdeen to Shetland. Distance computed by Haversine formula,
then sorted on UniCell using the byte sort network.

```bash
# Sort 32 postcodes by distance from London Paddington (default)
python3 postcode_sort.py

# Different cities
python3 postcode_sort.py --city manchester
python3 postcode_sort.py --city glasgow
python3 postcode_sort.py --city edinburgh
python3 postcode_sort.py --city birmingham
python3 postcode_sort.py --city bristol
python3 postcode_sort.py --city cardiff
python3 postcode_sort.py --city liverpool
python3 postcode_sort.py --city leeds

# Custom coordinates
python3 postcode_sort.py --lat 54.9 --lon -1.38  # Newcastle

# Smaller sort
python3 postcode_sort.py --city manchester --n 16
```

**Sample output (London Paddington):**
```
Rank  Postcode   Distance
  1   W2 4RH         1km   ← Paddington
  2   W1U 6AB        1km
  3   W1B 2HW        2km
  ...
 31   HS2 9PT      839km   ← Outer Hebrides
 32   ZE1 0TF      961km   ← Shetland
```

---

## Workbench UI

```bash
imago-workbench                # opens http://localhost:7420
imago-workbench --port 8080    # custom port
imago-workbench --cells 50000  # larger cell array
```

In the workbench:
- **Ports tab** → declare named inputs/outputs
- **Load .icm** → load any bundled or custom program
- **ws set a 5** → set named input in shell
- **ws run** → fire and read outputs
- **ws prog new adder.py** → open programming space

---

## WORKSPACE Shell

```bash
imago-workbench
# In the shell panel:

ws status                          # current workspace state
ws load adder_int32                # load bundled program
ws set a 12345
ws set b 67890
ws run                             # → result = 80235
ws values                          # show all inputs + outputs

ws prog new my_func.py blank       # create new file
ws prog compile                    # compile it
ws prog run                        # compile + run

ws search adder                    # search workspace
ws fs save adder.py                # save to session fs
ws fs list                         # list saved files
```

---

## Compiling Python Functions

```bash
# Interactive: prompts to confirm/rename ports
imago compile my_function.py my_function

# Non-interactive (piped)
echo "" | imago compile my_function.py my_function

# Save as .icm
imago compile my_function.py my_function --save my_function.icm

# 32-bit integer mode
imago compile adder.py add --int32 --save adder.icm
```

**With type annotations:**

```python
# adder.py
def add(a: signed, b: signed) -> signed:
    return a and b
```

The compiler reads `:signed`, `:datetime`, `:str` annotations and:
- Allocates complement cells for 64-bit types
- Sets GS_TYPE bits 27-28 in each cell's gate_state
- Records `input_types`/`output_types` in the `.icm` header
- PTT entries carry the type through the OS layer

---

## Running on FPGA

```bash
# Flash to iCEBreaker
cd fpga
python3 icm_loader.py --port /dev/ttyUSB0 --icm ../imago/examples/not_gate.icm

# Python bridge
from fpga.fpga_bridge import FPGABridge
from fpga.icm_loader import load_icm, load_onto_fpga

bridge = FPGABridge(port="/dev/ttyUSB0")
bridge.connect()
icm = load_icm("not_gate.icm")
load_onto_fpga(bridge, icm, max_cells=64)

# Inject input and read output
bridge.inject(0x1000, 1)   # a=1
bridge.capture([0x1001])   # read result
```

---

## Further Reading

| | |
|---|---|
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | How it works |
| [docs/ICM_FORMAT.md](ICM_FORMAT.md) | The `.icm` file format |
| [docs/RUNNING.md](RUNNING.md) | Full workflow guide |
| [docs/NEURAL_POND_TUTORIAL.md](NEURAL_POND_TUTORIAL.md) | Neural ponds |
| [docs/VERILOG_SPEC.md](VERILOG_SPEC.md) | Silicon bring-up notes |
| [docs/VISION.md](VISION.md) | What this is trying to become |
| [docs/INDEX.md](INDEX.md) | Full searchable index |
