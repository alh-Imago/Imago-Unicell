# Imago UniCell — Core Architecture
## Claudette v1.1
> **⚠️ ARCHIVE — Historical reference only.** This document predates the v2.2
> two-arrival model. References to `GS_SYNC_WAIT`, old gate_state bit positions,
> or `write_config()` reflect the earlier architecture. See `docs/CELL_INTERNALS.md`
> and `docs/ARCHITECTURE.md` for current ground truth.



---

## UniCell — The NOR Gate Cell

### Register layout (161 bits per cell)

```
Config register (64 bits, Command 3 / system only):
  Lower 32 bits (CMD_RECONFIGURE + scope=LOCAL):
    bits  0-10:  NOR topology      (11 bits — fanin configuration)
    bits 11-14:  ECC configuration
    bits 15-26:  Auth mask          (12-bit card token — HIDDEN)
    bits 27-31:  Reserved

  Upper 32 bits / _config_upper (CMD_RECONFIGURE + scope=EXTENDED):
    bits 32-63:  Extended forwarding address upper half
                 Active only when GS_ADDR_LATCH (bit 23) set
                 full_addr = (_config_upper << 32) | output_address
                 ZERO connection to data bus or NOR compute path

Mode register (32 bits):
  bit  11:  GS_LATCH        — store output each tick (loop variable model)
  bit  12:  GS_ONE_SHOT     — disarm after first firing
  bit  13:  GS_INVERT_OUT   — invert output signal
  bit  14:  GS_BROADCAST    — write to address range
  bit  15:  GS_SYNC_WAIT    — wait for two sequential arrivals (async merges)
  bit  16:  GS_LOOP_BACK    — feedback output to input address
  bits 17-19: LOOP_BACK_SRC
  bits 20-22: LOOP_BACK_DST
  bit  23:  GS_ADDR_LATCH   — bridge: upper config = upper 32 of 64-bit address
  bits 24-28: reserved
  bit  29:  GS_PRIORITY     — scheduled first each tick
  bit  30:  GS_TRACE        — record to trace buffer on fire
  bit  31:  GS_BREAKPOINT   — halt array on fire

Input address register:    64 bits  (lower 32 for local; full 64 for cross-Pond and cross-card)
Output address register:   64 bits  (lower 32 for local; full 64 for bridge cross-card forwarding)
Data register:            32 bits  (NOR compute only — never used for addressing)
Start flag:                1 bit   (armed=1, disarmed=0)

Register file: 32 (gate_state) + 64 (input_address) + 64 (output_address) + 32 (data) = 192 bits
Start flag: 1 bit (dedicated hardware line, not on any bus)
Total per cell: 193 bits
```

### NOR gate topology (bits 0-10)

The 11-bit topology field configures up to 9 NOR gates within the cell, arranged in a fixed tree:

```
g1 = NOR(value, value)  if bit 0 set, else pass
g2 = NOR(value, value)  if bit 1 set, else pass
g3 = NOR(g1, g2)        if bit 2 set, else g1
g4 = NOR(g3, value)     if bit 3 set, else g3
g5 = NOR(g3, value)     if bit 4 set, else g3
g6 = NOR(g4, g5)        if bit 5 set, else g4
g7 = NOR(g6, value)     if bit 6 set, else g6
g8 = NOR(g7, g6)        if bit 7 set, else g7
result = NOR(g8, 0)     if bit 8 set, else g8
```

Special patterns: topology=0 → GS_PASS (identity), topology=1 → GS_NOT (invert).

### Cell lifecycle

```
1. Config sequence (triggered by FUNCTION_LOAD_PATTERN):
   Field 0: gate_state  (mode flags + NOR topology)
   Field 1: input_address
   Field 2: output_address
   Field 3: output_address_alt  (SELECT cells only)
   Field 4: _config_upper       (addr_latch bridge cells only)

2. Armed (start_flag=True):
   Each tick: if data at input_address → fire
   Fire: compute NOR result, write to output_address
   Clear start_flag (unless loop_mode or latch_mode)

3. Result delivery:
   Normal:     (output_address, value, ecc_check)  3-tuple
   addr_latch: (output_address, value, ecc_check, full_64bit_addr)  4-tuple
```

---

## UniCellArray — The Bus

All cells share a single bus — a dict mapping `address → (value, tick)`. The tick counter prevents stale reads. Every cell writes to and reads from the same medium.

**The wired-OR property:** when two cells write to the same address in the same tick, their values are OR'd together. This is not a conflict — it is the fundamental mechanism for building two-input NOR gates from one-input cells.

```
Cell A:  input=0x1000, output=0xABCD, gate=NOR(a,a) = NOT(a)
Cell B:  input=0x1001, output=0xABCD, gate=NOR(b,b) = NOT(b)
Result at 0xABCD: NOT(a) OR NOT(b) = NAND(a,b) by De Morgan's law
Note: this is NAND, not NOR. True NOR uses GS_NOR internal topology within a single cell.
Both NAND and NOR are universally complete.
```

The `_armed` set tracks which cells are currently active. When it empties, computation is complete.

### Timing and pad_to_depth

Every program has a known **pipeline depth** — the number of cell stages from input to output. Because all paths to a wired-OR combiner must arrive simultaneously, the compiler uses `pad_to_depth` to insert PASS cells on shorter paths. This is the critical correctness property: a cell that sees a partial input fires with a wrong value.

```
Path A: input → cell → cell → cell → output   (depth 3)
Path B: input → cell → output                 (depth 1)
Without pad_to_depth: output fires at tick 1 with partial result
With pad_to_depth:    PASS cells added to path B → both arrive at tick 3
```

SYNC_WAIT (bit 15) was an alternative that waits for two sequential arrivals. It works for genuine async merges but fails when signals arrive simultaneously (they're combined by wired-OR into one packet). SYNC_WAIT is retained as an explicit primitive for async merges only.

---

## Tile Library

Tiles are pre-designed cell networks implementing named operations. The NORBuilder builds tiles by composing NOR primitives with automatic depth tracking.

### Key tiles

| Tile | Cells | Depth | Notes |
|------|-------|-------|-------|
| INT32_ADD (ripple) | 12,931 | 194 | Baseline carry chain |
| INT32_ADD_CLA | 3,219 | 58 | 3× faster — default for + |
| INT32_SUB | ~3,300 | 60 | Two's complement |
| INT32_AND | 160 | 3 | Parallel bitwise |
| INT32_OR | 128 | 3 | Parallel bitwise |
| INT32_XOR | 576 | 7 | Parallel bitwise |
| INT32_NOT | 32 | 1 | Fastest tile |
| INT32_EQ | ~600 | 10 | XNOR tree |
| INT32_MAX/MIN | 26,077 | 202 | Subtractor + sign MUX |
| COUNTER_SHIFT_N | N | N | One-hot pulse chain |
| COUNTER_RIPPLE_8 | 924 | 4 | For loops, variable range |
| LFSR_16 | 185 | 10 | Pseudo-random, period 65,535 |
| PARITY_32 | 558 | 35 | XOR tree |
| MOUSE_HANDLER | 960 | 12 | HID mouse peripheral |
| KEYBOARD_HANDLER | 840 | 12 | HID keyboard peripheral |
| DISPLAY_HANDLER | 18,600 | 32 | Pixel stream output |

The carry-lookahead adder (CLA) was the first major optimisation — 3× depth reduction over ripple carry by computing all carries in parallel.

### User tiles

Any file with `# LIBRARY MODEL` in the first 10 lines is scanned at startup. Imports are validated by AST before any code executes — only `fp_tiles`, `gate_states`, `controller`, and `math` are permitted. User tiles take precedence over core tiles with the same name.

---

## Compiler

### Python compiler

The Python compiler (`compiler.py` + `compiler_int32.py`) converts a Python function AST to a flat list of CellMapRecords.

**Supported constructs:**
- Integer arithmetic: `+`, `-`, `&`, `|`, `^`
- Augmented assignment: `+=`, `-=`, `&=`, `|=`, `^=`
- Comparisons: `==`, `!=`, `<`, `>`, `<=`, `>=`, chained (`a < b < c`)
- Control flow: `if/else`, `while`, `for` (SHIFT path n≤32, RIPPLE path n>32)
- `ast.Pass`

**Int32Value:** when an operation mixes Int32Value with a Python int literal, the literal is automatically coerced. No explicit casts needed.

**Loop model:** loop variables use GS_LATCH + LOOP_MODE storage cells. The variable lives in a cell that re-emits its value every tick and updates when new data arrives. This is also the phi node model for the LLVM mapper.

### LLVM frontend

`llvm_frontend.py` parses `.ll` text via llvmlite and validates against the supported instruction subset:

**Supported:** `add`, `sub`, `and`, `or`, `xor`, `icmp` (eq/ne/slt/sgt/sle/sge), `phi`, `br`, `ret`, `alloca`, `load`, `store`, permitted intrinsics (ctpop, bswap, ctlz, cttz).

**Rejected with clear errors:** `getelementptr`, exceptions, vector/SIMD, i64/float, extern calls.

The CFG is built with successor/predecessor lists. Phi nodes carry incoming values and block names, including dotted label names (if.true, if.false).

### LLVM IR mapper

`llvm_ir_mapper.py` lowers `LLVMFunction` parse trees to `ProgramImage`:

```
LLVM construct         →  Claudette mechanism
─────────────────────────────────────────────────────────
add/sub/and/or/xor     →  tile placement (INT32_ADD_CLA etc.)
icmp eq/ne             →  INT32_EQ ± NOT
icmp slt/sgt/sle/sge   →  INT32_SUB sign bit extraction
phi                    →  GS_LATCH + LOOP_MODE storage cell
conditional br         →  GS_SELECT routing
ret                    →  designate OUTPUT named range
alloca/load/store      →  bus address allocation + PASS cells
```

Blocks processed in reverse-post-order (RPO). Two-pass: phi nodes pre-allocated in pass 1, instructions lowered in pass 2.

---

## ProgramImage and Execution Model

A `ProgramImage` is a self-describing executable unit with four sections:

```
MANIFEST HEADER   — program_id, name, Claudette version stamp, cell count
MODELS NEEDED     — tile names required to run (checked at load)
NAMED RANGES      — the CPU/GPU reference layer
PROGRAM SCRIPTS   — compiled CellMapRecord list
```

### Named ranges

Named ranges classify every address in the program:

| Kind | Description |
|------|-------------|
| INPUT | Caller injects value before run() |
| OUTPUT | Caller reads result after run() |
| ACCUMULATOR | Loop variable with storage cell |
| LOOP_TICK | Counter tick address |
| LOOP_LIMIT | Counter limit address |
| SCRATCH | Internal working register |

The named range table is the **CPU/GPU contract**: CPU uses `bus_address` by name, GPU uses `vram_offset` as direct index into the cell array. No address guessing. No positional indexing.

### Execution

```python
program = ProgramImage.from_compiler(
    name='add_two', records=records,
    input_map=imap, output_addrs=oa,
    arg_names=['a', 'b'])

result = program.run(inputs={'a': 5, 'b': 3})
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
```

### GPU backend

`GPUArrayBackend` replaces the per-cell Python loop with a vectorised NumPy/CuPy operation. Auto-detects GPU or falls back to NumPy.

```
VRAM:  cell array (gate_state, addresses, flags) — GPU owns between ticks
RAM:   bus buffer {address: value}               — CPU owns, fed to GPU
```

The VRAM figure (~21 bytes/cell) is the **simulation cost only** — not a hardware requirement. On real silicon the cell registers live in the transistors themselves.

---

## Command Bus — Three-Bus Protocol

The CommandInterface translates the three-bus protocol to cell operations.

```
Bus 1 (Command & Control):  64 bits
  bits  0-3:   command code
  bits  4-14:  auth token (11 bits)
  bit  15:     address mode
  bits 16-17:  scope (00=LOCAL, 01=SHORE, 10=EXTENDED)
  bits 18-31:  reserved flags
  bits 32-63:  reserved upper half

Bus 2 (Data Payload):   64 bits (CMD_DATA_WRITE NEVER scope=EXTENDED)
Bus 3 (Target Address): 64 bits (width used depends on scope bits)
```

| Command | Code | Privilege |
|---------|------|-----------|
| DATA_WRITE | 0 | User+System |
| SET_INPUT_ADDR | 1 | User+System |
| SET_OUTPUT_ADDR | 2 | User+System |
| RECONFIGURE | 3 | **System only** (auth required) |
| FREEZE | 4 | **System only** |
| RELEASE | 5 | **System only** |
| COPY_DATA_TO_OUT | 6 | User+System |
| COPY_DATA_TO_IN | 7 | User+System |
| PING | 8 | Anyone |

**CMD_RECONFIGURE + scope=LOCAL** writes lower 32 bits of config register (gate_state, mode flags, auth mask).

**CMD_RECONFIGURE + scope=EXTENDED** writes `_config_upper` — the upper 32 bits of the 64-bit forwarding address for bridge cells. Same command bus wire, same auth protection, scope bits select which register half.

**Data and address are physically separate.** `CMD_DATA_WRITE` is never scope=EXTENDED. The scope bits gate which register is written — data never reaches address registers and addresses never reach data registers.
