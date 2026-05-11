# `.icm` File Format Specification

*Imago Cell Map — v1.3*

An `.icm` file is a portable, self-describing program for the Imago UniCell
architecture. The same file runs on the Python VM, any supported FPGA, and
future ASIC without modification.

---

## Structure

An `.icm` file is a JSON object. Fields appear in this order by convention:

```
header fields        — identity, metadata, target
port declarations    — inputs, outputs, input_types, output_types
model references     — models
cell records         — records
integrity            — record_hash
composer data        — composer_meta (optional, for round-trip editing)
```

---

## Minimal valid `.icm`

```json
{
  "name": "not_gate",
  "inputs":  {"a": 4096},
  "outputs": {"result": 4097},
  "models":  [],
  "records": [
    {"gs": 1, "in": 4096, "out": 4097, "inB": null, "alt": null, "stor": false, "init": null}
  ]
}
```

`gs: 1` = `GS_NOT` (bit 0 set). `in`/`out` are bus addresses (decimal integers).

---

## All Fields

### Identity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `program_id` | string | no | Unique identifier, e.g. `"notgate1"` |
| `name` | string | yes | Human-readable program name |
| `os_name` | string | no | Authoring tool (`"Claudette"`) |
| `os_version` | string | no | Tool version (`"1.3"`) |
| `created_at` | float | no | Unix timestamp of creation |
| `description` | string | no | Human-readable description |
| `author` | string | no | Author name |
| `tags` | array of string | no | Classification tags |

### Target

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | string | no | FPGA target the file was compiled for: `"vm"`, `"icebreaker"`, `"kintex7"`, etc. Absent = no specific target. |
| `cell_budget` | int or null | no | Cell count limit for the target. `null` = unlimited (VM). |
| `vm_only` | bool | no | `true` = design exceeds target budget or contains VM-only models. Loading onto constrained FPGA will fail. |

### Port Declarations

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `inputs` | object | recommended | `{name: bus_address}` — named input ports. Integer bus addresses. |
| `outputs` | object | recommended | `{name: bus_address}` — named output ports. |
| `input_types` | object or null | no | `{name: type_name}` — type for each input. Absent or null = all numeric. |
| `output_types` | object or null | no | `{name: type_name}` — type for each output. |
| `inputs_32` | object or null | no | `{name: [addr0..addr31]}` — full 32 bit-addresses for each int32 input port, LSB first. Present only when the program uses `int32` typed inputs. |
| `outputs_32` | array or null | no | `[addr0..addr31]` — the 32 output bit-addresses for an int32 result, LSB first. Present only for programs with a single int32 output. |

**Type names:** `"numeric"` · `"signed"` · `"alpha"` · `"datetime"`

When a port has type `"signed"` or `"datetime"`, it occupies two consecutive
bus addresses: the declared address (primary, bits 0-31) and the next address
(complement, bits 32-63). The `.icm` declares only the primary address; the
loader infers the complement address as `primary + 1`.

**int32 ports** use `inputs_32` / `outputs_32` rather than the single-address
`inputs` / `outputs`. The Kogge-Stone parallel prefix adder, for example,
produces 32 output bits at non-contiguous bus addresses — the tile's pipeline
routes them through PASS delay chains to different final addresses. The
single-address `outputs` field captures only the first output bit (for PTT
registration and Shore indexing); `outputs_32` carries all 32 addresses needed
to reconstruct the 32-bit integer result after a run.

```json
"inputs":    {"a": 4096, "b": 4128},
"outputs":   {"result": 3146210},
"inputs_32": {
  "a": [4096, 4097, ..., 4127],
  "b": [4128, 4129, ..., 4159]
},
"outputs_32": [3146210, 3146179, 3146180, ..., 3146209]
```

`inputs_32` is used by the VM and the pond bootstrap path (`spawn_pond_from_icm`)
to inject all 32 bits of an int32 value. Without it, an int32 program loaded
from `.icm` can only be run by manually injecting all 32 bit-addresses — the
single address in `inputs` is only the LSB.

**Reserved:** `input_shapes` and `output_shapes` fields are reserved for future
array/matrix port declarations:

```json
"input_shapes":  {"A": [4, 4]}    ← occupies 16 consecutive addresses
"output_shapes": {"result": [4, 4]}
```

When present, `inputs[name]` is the base address of the first element.
Elements are in row-major order. Field name `input_shapes` is reserved from
v1.3.

### Model References

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `models` | array of string | yes | Tile library model names this program uses. e.g. `["INT32_ADD", "FP32_MUL"]`. Empty array `[]` if none. |
| `ranges` | array of object | no | Named address ranges from `ProgramImage` (for advanced use — see below). |

### Cell Records

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `records` | array of object | yes | Ordered list of cell configurations. See below. |

Each record object:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `gs` | int | yes | `gate_state` — 32-bit cell configuration word. Decimal. |
| `in` | int | yes | `input_address` — bus address the cell listens on. |
| `out` | int | yes | `output_address` — bus address the cell writes to. |
| `inB` | int or null | no | `input_b_address` — B-input address for two-input cells (AND, OR, XOR etc.). `null` for single-input cells. |
| `alt` | int or null | no | Alternate output address (reserved, `null`). |
| `stor` | bool | no | `true` = cell is a storage cell (latch/loop). Affects region lifecycle. |
| `init` | int or null | no | Initial value pre-loaded into storage cells at load time. `null` if not applicable. |

### Integrity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `record_hash` | string | no | SHA-256 hex digest of the canonical record list. Used for integrity verification. Absent = no verification. |
| `security_context` | object or null | no | Reserved for future auth token binding. Always `null` in current implementations. |

### Composer Round-Trip

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `composer_meta` | object | no | Opaque blob saved by the Composer to enable round-trip editing. Contains `blocks`, `links`, `portDecls`. Ignored by the VM loader and FPGA loader. |

---

## `gate_state` Reference

The `gs` field is a 32-bit integer. Key values:

| Value (hex) | Constant | Function |
|-------------|----------|----------|
| `0x00000000` | GS_PASS | Wire / delay |
| `0x00000001` | GS_NOT | NOT |
| `0x00000007` | GS_AND_V2 | AND (needs GS_SYNC_WAIT) |
| `0x00000024` | GS_OR_V2 | OR (needs GS_SYNC_WAIT) |
| `0x000000BC` | GS_XOR_V2 | XOR (needs GS_SYNC_WAIT) |
| `0x0000003C` | GS_XNOR_V2 | XNOR (needs GS_SYNC_WAIT) |
| `0x00008000` | GS_SYNC_WAIT | Wait for both A and B |
| `0x00000800` | GS_LATCH | Store output each tick |
| `0x00001000` | GS_ONE_SHOT | Fire once then disarm |
| `0x00010000` | GS_LOOP_BACK | Feedback output to input |
| `0x00000400` | LOOP_MODE | Stay armed after firing |
| `0x04000000` | GS_OUT_POSEDGE | Output releases on rising edge |
| `0x08000000` | GS_TYPE_SIGNED | Cell output is signed int |
| `0x10000000` | GS_TYPE_ALPHA | Cell output is character |
| `0x18000000` | GS_TYPE_DATETIME | Cell output is timestamp |

Combine with bitwise OR: `GS_AND_V2 | GS_SYNC_WAIT = 0x00008007`.

Full reference: [gate_states.py](../gate_states.py)

---

## Examples

### NOT gate

```json
{
  "name": "not_gate",
  "inputs":  {"a": 4096},
  "outputs": {"result": 4097},
  "models": [],
  "records": [
    {"gs": 1, "in": 4096, "out": 4097, "inB": null, "alt": null, "stor": false, "init": null}
  ]
}
```

### Two-input AND gate

```json
{
  "name": "and_gate",
  "inputs":  {"a": 4096, "b": 4097},
  "outputs": {"result": 4098},
  "models": [],
  "records": [
    {"gs": 32775, "in": 4096, "out": 4098, "inB": 4097, "alt": null, "stor": false, "init": null}
  ]
}
```

`gs = 0x00008007 = GS_AND_V2 | GS_SYNC_WAIT = 32775`

### Signed subtractor with type declarations

```json
{
  "name": "sub_signed",
  "inputs":  {"a": 4096, "b": 4128},
  "outputs": {"result": 8192},
  "input_types":  {"a": "signed", "b": "signed"},
  "output_types": {"result": "signed"},
  "models": ["INT32_SUB"],
  "records": [ ... 517 records ... ]
}
```

Primary cell for `a` is at 4096; complement cell (`_a_hi`) is at 4097.
Primary for `b` is at 4128; complement at 4129.

### DateTime input

```json
{
  "name": "days_since",
  "inputs":  {"epoch": 4096},
  "outputs": {"days": 8192},
  "input_types":  {"epoch": "datetime"},
  "output_types": {"days": "numeric"},
  "models": [],
  "records": [ ... ]
}
```

`epoch` primary at 4096 = Unix seconds (low 32 bits).
`epoch` complement at 4097 = subsecond + tz_offset (high 32 bits).

---

## Loading `.icm` Files

### Python VM

```python
import imago
vm = imago.VM()
vm.load("my_program.icm")
vm.set("a", 5)
vm.set("b", 3)
print(vm.run())   # {"result": 8}
```

Or one-shot:

```python
result = imago.run_icm("my_program.icm", inputs={"a": 5, "b": 3})
```

**int32 programs** — use `inputs_32` and `outputs_32` for full 32-bit injection:

```python
import json
from compiler_int32 import run_int32_function

# run_int32_function handles inputs_32/outputs_32 internally
result = run_int32_function(source, "add", {"a": 5, "b": 3})
print(result)   # 8

# Or load from .icm manually using inputs_32:
with open("adder_int32.icm") as f:
    icm = json.load(f)

inputs_bus = {}
for name, addrs in (icm.get("inputs_32") or {}).items():
    val = {"a": 5, "b": 3}[name] & 0xFFFFFFFF
    for i, addr in enumerate(addrs):
        inputs_bus[addr] = (val >> i) & 1

output_addrs = icm.get("outputs_32") or []
# then inject and capture via controller
```

### OS bootstrap path (PondManager)

For OS-level use — creates a fully monitored Pond with Ward, PTT, and
bridge security rather than a bare controller region:

```python
import json
from pond import PondManager
from unicell_array import UniCellArray

array = UniCellArray(cell_count=8192)
mgr   = PondManager(array)

# Spawn a workspace for the user session
workspace = mgr.spawn_workspace(owner_id="user_alice")

# Load a program into its own pond
with open("adder_int32.icm") as f:
    icm = json.load(f)
program = mgr.spawn_pond_from_icm(icm, owner_id="user_alice")

# Wire workspace ↔ program (bus addresses + whitelist grants)
conn = mgr.connect(workspace, program)

# program pond is now IDLE, bridges wired, PTT tracking inputs and outputs
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full pond lifecycle.

### FPGA

```bash
python3 fpga/icm_loader.py --port /dev/ttyUSB0 --icm my_program.icm
```

Or in Python:

```python
from fpga.fpga_bridge import FPGABridge
from fpga.icm_loader import load_icm, load_onto_fpga

bridge = FPGABridge(port="/dev/ttyUSB0")
bridge.connect()
icm = load_icm("my_program.icm")
load_onto_fpga(bridge, icm, max_cells=64)
```

Note: `inB` and `init` fields are not yet implemented in the Verilog config
state machine. The FPGA loader will warn if these fields are present.
See [fpga/README_FPGA.md](../fpga/README_FPGA.md) § Hardware Support Matrix.

---

## Producing `.icm` Files

### From the Compiler (recommended)

```bash
imago compile my_function.py my_function --save my_function.icm
```

The CLI prompts to confirm or rename each input/output port before writing.
The confirmed names become PTT entries and appear in `inputs`/`outputs`.

In Python:

```python
import imago
vm = imago.compile_function(
    "def add(a: signed, b: signed) -> signed:\n    return a and b",
    "add",
    port_names={"output": "result"}
)
# vm.workspace._records holds the cell map
```

### From the Composer (visual design)

1. Open `composer/unicell_composer.html` in any browser
2. Design the circuit on the canvas
3. Open the **Ports** tab — declare named inputs and outputs with types
4. File → Export ICM

The Ports tab populates `inputs`, `outputs`, `input_types`, `output_types`
in the exported file.

### By hand (small programs)

For simple programs (NOT gate, AND gate, a handful of cells), write the JSON
directly. The format is intentionally simple. Use `gate_states.py` for the
`gs` values.

---

## Versioning

The `.icm` format is append-only. New optional fields may be added in future
versions. Loaders must ignore unknown fields. Required fields (`name`,
`records`) must always be present.

Current optional fields (v1.3):
- `inputs_32`, `outputs_32` — 32 bit-addresses for int32 ports (present when compiled with `--int32`)
- `input_types`, `output_types` — type annotations per port
- `record_hash` — SHA-256 integrity check
- `target`, `cell_budget`, `vm_only` — FPGA target constraints

Reserved field names (do not use for other purposes):
- `input_shapes`, `output_shapes` — future array/matrix ports
- `timing_model` — future timing constraint annotations
- `security_context` — future auth token binding
- `composer_meta` — Composer round-trip data (not for programmatic use)
