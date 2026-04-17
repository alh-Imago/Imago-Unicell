# Imago UniCell — CLI and User Guide
## Claudette v1.1 — Workbench Reference

---

## The Workbench Shell

The workbench (`workbench.py`) is a browser-based terminal for interacting with a running Claudette system. It connects to a live array, Shore registry, COMPANION, and device bridges. All commands are text-based and tab-completable.

### Starting the workbench

```python
from workbench import Workbench
from controller import ImagoController
from shore_v2 import ShoreV2
from companion import Companion

ctrl  = ImagoController(cell_count=500_000)
shore = ShoreV2("shore_0", base_address=0x00500000, array=ctrl.array)
comp  = Companion("companion", ctrl.array, shore)

wb = Workbench(ctrl, shore=shore, companion=comp)
wb.serve(port=8080)   # open http://localhost:8080
```

### Version display

```
> ver
Claudette v1.1
Imago UniCell Workbench
────────────────────────────────
Array:     412/500000 cells
Regions:   3
Cycles:    18472
Shore:     online
Companion: online
Devices:   keyboard,mouse
Search:    4 ponds
```

---

## Command Reference

### System

| Command | Aliases | Args | Description |
|---------|---------|------|-------------|
| `ver` | `version`, `status` | — | Claudette version, array usage, Shore/Companion status |
| `help` | `?`, `h` | — | Full command reference |
| `exit` | `quit`, `q` | — | Close workbench session |
| `clear` | `cls` | — | Clear terminal |

---

### Array Control

| Command | Aliases | Args | Description |
|---------|---------|------|-------------|
| `run <n>` | — | `<n>`: tick count | Run array for N ticks |
| `tick` | `step` | — | Single tick |
| `halt` | `stop` | — | Halt array (sets all start_flags False) |
| `reset` | — | — | Reset array to clean state |
| `cells` | — | — | Summary: total cells, armed cells, regions |
| `bus` | — | `[addr]` optional | Dump bus state at address, or full bus summary |
| `armed` | — | — | List all currently armed cell addresses |
| `trace` | — | `[on|off]` | Enable/disable trace buffer |
| `trace dump` | — | — | Print trace buffer contents |

**Example:**
```
> run 1000
  Ran 1000 ticks. Armed: 0 cells. Cycles total: 19472.
> cells
  Total:   500000
  Armed:       0  (computation complete)
  Regions:     3
```

---

### Pond Management

| Command | Aliases | Args | Description |
|---------|---------|------|-------------|
| `ponds` | `ls ponds` | — | List all Ponds: name, type, security, bridge count, Ward state |
| `pond <n>` | `inspect <n>` | `<n>`: Pond name | Full Pond detail: bridges, PTT summary, whitelist, visit log |
| `create <n>` | — | `<n>`: name + options | Create a new Pond |
| `destroy <n>` | — | `<n>`: Pond name | Destroy Pond (heritage required for anchors) |
| `freeze <n>` | — | `<n>`: Pond name | FREEZE_BODY — halt cells, preserve state |
| `migrate <n>` | — | `<n>`: Pond name | Migrate Pond to new address range |

**Example:**
```
> ponds
  workspace_alice  WORKSPACE  OPEN    2 bridges  Ward: HEALTHY
  fs_docs          FILE       OPEN    2 bridges  Ward: HEALTHY
  companion        COMPANION  HIDDEN  2 bridges  Ward: HEALTHY (anchor)
> pond workspace_alice
  Type:         WORKSPACE
  Security:     OPEN
  Scope:        LOCAL
  Object ID:    0x0000000F
  Base:         0x00200000
  Region size:  65536 cells
  Bridges:      INBOUND (0x00200000), OUTBOUND (0x00200040)
  PTT entries:  412 (312 ACTIVE, 100 IDLE)
  Ward:         HEALTHY (idle 0 cycles)
  Thermal:      load=0.034  limit=100.0  state=NOMINAL  zone=block_0
```

---

### Shore Registry

| Command | Aliases | Args | Description |
|---------|---------|------|-------------|
| `ls` | `dir` | `[TYPE]` filter | List Shore entries (optionally filtered by type) |
| `cat <n>` | `inspect <n>` | `<n>`: entry name | Full ShoreEntry detail |
| `shore` | — | — | Shore registry summary: entry counts per type |
| `connections` | `conns` | — | List live connections |
| `scope` | — | — | Object counts per scope (LOCAL/SHORE/EXTENDED) |

**Example:**
```
> shore
  Shore registry: 14 entries
    POND:     6    BRIDGE:   8    FILE:    0
    EXTERNAL: 0    TILE:     0
  Scope summary:
    LOCAL:    12   SHORE:    2    EXTENDED: 0
> scope
  LOCAL:    12 objects  (this stack)
  SHORE:     2 objects  (this card)
  EXTENDED:  0 objects  (cross-card)
```

---

### Ward Monitoring

| Command | Aliases | Args | Description |
|---------|---------|------|-------------|
| `ward <n>` | — | `<n>`: Pond name | Ward state for one Pond |
| `ward --all` | — | `--all` | Ward states for all registered Ponds |
| `escalate <n> <state>` | — | Pond name + state | Manually trigger Ward state |
| `thermal` | — | — | Thermal summary: all zones, hottest Pond |

**Ward states:** IDLE, HEALTHY, DEGRADED, STALLED, SILENT, ISOLATED

**Thermal states:** NOMINAL, THROTTLE (≥100% of limit), FREEZE (≥120%), MIGRATE (sustained FREEZE)

**Example:**
```
> ward --all
  workspace_alice  HEALTHY    thermal=NOMINAL  load=0.034  zone=row_0
  fs_docs          HEALTHY    thermal=NOMINAL  load=0.012  zone=row_0
  companion        HEALTHY    thermal=NOMINAL  load=0.001  zone=row_0
> thermal
  Zone row_0: avg=0.016  peak=0.034 (workspace_alice)  channel=0
  Zone row_1: avg=0.000  peak=0.000  channel=1
  Zone row_2: avg=0.000  peak=0.000  channel=2
  Zone row_3: avg=0.000  peak=0.000  channel=3
```

---

### Cast / Discovery

| Command | Aliases | Args | Description |
|---------|---------|------|-------------|
| `cast` | — | `[key=value ...]` | Cast a Stone into the Pond network |
| `find <type>` | — | `<type>`: Pond type | Find Ponds of a given type |
| `skip <n1> <n2> ...` | — | Pond names | Skipping Stone across named Ponds |

**Example:**
```
> cast pond_type=FILE
  Found 1 result (LOCAL scope):
    fs_docs  FILE  OPEN  addr=0x00300000

> cast collect_all=true
  Found 3 results:
    workspace_alice  WORKSPACE  LOCAL  0x00200000
    fs_docs          FILE       LOCAL  0x00300000
    companion        COMPANION  SHORE  0x00500000  (HIDDEN — whitelisted only)
```

---

### Devices

| Command | Aliases | Args | Description |
|---------|---------|------|-------------|
| `devices` | `dev` | — | List all device bridges with status |
| `device <n>` | — | `<n>`: device name | Inspect one device bridge |

**Example:**
```
> devices
  keyboard    KEYBOARD   inbound   connected   0x00C00000
  mouse       MOUSE      inbound   connected   0x00C10000
  storage     STORAGE    inbound   connected   0x00D00000
  audio       AUDIO      outbound  stub        0x00C20000
  video       VIDEO      inbound   stub        0x00C30000
```

---

### Tile and Model Library

| Command | Aliases | Args | Description |
|---------|---------|------|-------------|
| `tile` | — | — | List all tiles (core + user) with cell count and depth |
| `tile <n>` | — | `<n>`: tile name | Inspect tile detail |
| `model` | — | — | List loaded model instances |
| `model <n>` | — | `<n>`: model name | Inspect a model |

**Example:**
```
> tile INT32_ADD_CLA
  Tile:        INT32_ADD_CLA
  Operation:   32-bit integer addition (carry-lookahead)
  Cells:       3,219
  Depth:       58
  In ports:    2  (A, B)
  Out ports:   1  (RESULT)
  Notes:       3× faster than ripple carry. Default for + operator.
```

---

### VM Image

| Command | Aliases | Args | Description |
|---------|---------|------|-------------|
| `image save <path>` | — | `.img` or `.img.gz` | Save complete system snapshot |
| `image load <path>` | — | — | Restore from snapshot |
| `image info` | — | — | Show current system state without saving |

**Example:**
```
> image save /tmp/session_alice.img.gz
  Snapshot saved: /tmp/session_alice.img.gz
  Cells: 412  Ponds: 3  Shore entries: 14
  OS: Claudette v1.1  Format: v3

> image info
  Claudette v1.1 — VM image summary
  ─────────────────────────────────
  Cells:         412 armed, 0 firing
  Ponds:         3 (2 HEALTHY, 1 HEALTHY anchor)
  Shore:         14 entries (12 LOCAL, 2 SHORE)
  Extended:      0 legacy proxies, 0 new-style entries
  Companion:     online, 0 pending escalations
```

---

## Gate State Flags Reference

| Flag | Bit | Value | Description |
|------|-----|-------|-------------|
| GS_PASS | — | 0x000 | Identity — pass input through unchanged |
| GS_NOT | 0 | 0x001 | Invert input |
| GS_SELECT | 9 | 0x200 | Conditional router (reads bit 0 of input) |
| GS_LATCH | 11 | 0x800 | Store and re-emit result each tick |
| GS_ONE_SHOT | 12 | 0x1000 | Disarm after first firing |
| GS_INVERT_OUT | 13 | 0x2000 | Invert output after gate computation |
| GS_BROADCAST | 14 | 0x4000 | Write to address range |
| GS_SYNC_WAIT | 15 | 0x8000 | Wait for two sequential arrivals |
| GS_LOOP_BACK | 16 | 0x10000 | Internal G8→G0 feedback |
| GS_ADDR_LATCH | 23 | 0x800000 | Bridge: _config_upper = upper 32 of 64-bit address |
| GS_PRIORITY | 29 | 0x20000000 | Scheduled first each tick |
| GS_TRACE | 30 | 0x40000000 | Record to trace buffer on fire |
| GS_BREAKPOINT | 31 | 0x80000000 | Halt array when this cell fires |

---

## User Tile Creation Guide

### File format

Any Python file with `# LIBRARY MODEL` in the first 10 lines is automatically scanned as a user tile library.

```python
# LIBRARY MODEL
# My custom tile library

from fp_tiles import NORBuilder, TileSpec
import gate_states

def make_my_tile(base_address: int) -> TileSpec:
    b = NORBuilder(base_address)
    # ... build cells with b.add_cell(gate_state, in_addr, out_addr)
    return b.build(
        name        = "MY_TILE",
        description = "Does something useful",
        in_ports    = 1,
        out_ports   = 1,
    )

TILES = {
    "MY_TILE": make_my_tile,
}
```

### Permitted imports

The user tile sandbox permits only:
- `fp_tiles` — NORBuilder, TileSpec, existing tile builders
- `gate_states` — GS_PASS, GS_NOT, GS_SELECT, GS_LATCH, etc.
- `controller` — CellMapRecord
- `math` — standard Python math module

All other imports are rejected by AST check before any code executes. This prevents user tiles from accessing the OS layer, Shore registry, or any security-sensitive component.

### Precedence

User tiles take precedence over core tiles with the same name. This allows overriding a built-in tile for a specific deployment without modifying core files.

---

## Device Bridges — Reference

### Peripheral address map

| Base address | Device | Class | Status |
|-------------|--------|-------|--------|
| 0x00C00000 | Keyboard | KeyboardBridge | Implemented |
| 0x00C10000 | Mouse | MouseBridge | Implemented |
| 0x00C20000 | Audio output | AudioBridge | Stub only |
| 0x00C30000 | Video capture | VideoBridge | Stub only |
| 0x00D00000 | Storage | StorageBridge | Implemented |
| 0x00E00000 | Network | NetworkBridge | Implemented |
| 0x00F00000 | Display (start) | DisplayPond | Implemented |

### Address layout (all bridges)

```
base + 0x00:  CMD_ADDR    — write command code here
base + 0x20:  DATA_ADDR   — write command data here
base + 0x40:  OUT_ADDR    — read result / event here
base + 0x60:  STATUS_ADDR — 0=idle, 1=ready, 2=busy, 3=error
```

### KeyboardBridge commands

| Code | Command | Description |
|------|---------|-------------|
| 0x10 | KB_CMD_READ | Block until keypress, return keycode |
| 0x11 | KB_CMD_POLL | Non-blocking: 0 if no key, keycode if ready |
| 0x12 | KB_CMD_FLUSH | Discard all pending keypresses |

Keycodes: ASCII for printable chars. Enter=13, Escape=27, Tab=9.

### MouseBridge commands

| Code | Command | Description |
|------|---------|-------------|
| 0x20 | MS_CMD_POLL | Non-blocking: 0 if no event, packed word if ready |
| 0x21 | MS_CMD_READ | Block until mouse event |
| 0x22 | MS_CMD_GET_X | Current X position (0-65535) |
| 0x23 | MS_CMD_GET_Y | Current Y position (0-65535) |
| 0x24 | MS_CMD_GET_BTN | Button bitmask (bit0=L, bit1=R, bit2=M) |
| 0x25 | MS_CMD_SET_REL | Switch to relative mode (delta X/Y) |
| 0x26 | MS_CMD_SET_ABS | Switch to absolute mode |
| 0x27 | MS_CMD_FLUSH | Discard pending events |

**Event word format** (32-bit, written to OUT_ADDR):
```
bits 31-24:  event type  (0=move, 1=btn_down, 2=btn_up, 3=wheel)
bits 23-16:  button mask / wheel delta
bits 15-8:   X component (delta or position high byte)
bits  7-0:   Y component (delta or position high byte)
```

### AudioBridge / VideoBridge (stubs)

Both return STATUS_ERROR for all commands in simulation. Command codes are defined for future hardware implementation.

Audio (base 0x00C20000): AU_CMD_OPEN (0x30), AU_CMD_WRITE (0x32), AU_CMD_FLUSH (0x33), AU_CMD_SET_GAIN (0x34).

Video (base 0x00C30000): VD_CMD_OPEN (0x40), VD_CMD_READ (0x42), VD_CMD_SEEK (0x43).

On real silicon: USB audio/video devices appear as PERIPHERAL Ponds. The cell array streams to them. The audio clock is hardware-independent — no timing constraints on the cell array side.

### DisplayPond

```python
from display_pond import DisplayPond, DisplayConfig, PixelFormat

cfg = DisplayConfig(
    width        = 320,
    height       = 240,
    pixel_format = PixelFormat.RGB8,
    base_address = 0x00F00000,
    scale        = 2,
)

dp = DisplayPond("main_display", array, "system", cfg)
dp.open()        # opens pygame window
dp.render(bus)   # called each tick — delta rendering
dp.close()
```

**Delta rendering:** only cells whose output has changed since the last frame update the display. A 320×240 display at 8-bit pixel = 76,800 cells. In a typical compute frame fewer than 100 cells change — display update is essentially free.

**Pixel formats:**

| Format | Bits/pixel | Cell count (320×240) |
|--------|-----------|---------------------|
| MONO1 | 1 | 76,800 |
| GRAY4 | 4 | 76,800 |
| GRAY8 | 8 | 76,800 |
| RGB8 | 8 (3-3-2) | 76,800 |
| RGB16 | 16 | 153,600 |
| RGB24 | 24 | 230,400 |

---

## Quick Start — Running a Program

```python
from controller import ImagoController
from compiler import compile_function
from fp_tiles import TileLibrary

# 1. Set up the array
ctrl = ImagoController(cell_count=100_000)
lib  = TileLibrary()

# 2. Compile a function
def add_two(a: int, b: int) -> int:
    return a + b

records, input_map, output_addrs = compile_function(add_two, lib)

# 3. Run it
ctrl.load_map(records, "add_two")
ctrl.set_inputs(input_map, {'a': 5, 'b': 3})
ctrl.run()
result = ctrl.capture_outputs(output_addrs)
print(result['output'])   # 8
```

Or via ProgramImage (recommended for named I/O):

```python
from program_image import ProgramImage

img = ProgramImage.from_compiler(
    name='add_two', records=records,
    input_map=input_map, output_addrs=output_addrs,
    arg_names=['a', 'b'])

result = img.run(inputs={'a': 5, 'b': 3})
print(result['output'])   # 8
```

Or from LLVM IR directly:

```python
from llvm_ir_mapper import compile_ll

images, errors = compile_ll('''
define i32 @add(i32 %a, i32 %b) {
entry:
  %r = add i32 %a, %b
  ret i32 %r
}
''')

result = images[0].run(inputs={'a': 5, 'b': 3})
print(result['output'])   # 8
```
