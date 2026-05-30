# Compiler Notes — Capabilities and Gaps

*Added 2026-05-30 after architecture rethink.*

---

## What the Cell Can Actually Do

The UniCell contains nine NOR gates in a tree topology. The cmd_latch
word (32 bits) defines the cell completely. The compiler was written
before the cell's full capability was understood — it under-exploits
the cell significantly.

### Topology (bits 9-0, one-hot)

Ten named topologies from the nine-gate tree. The compiler currently
uses: PASS, NOT, AND_V2, OR_V2, XOR_V2. The others (NOR, NAND, XNOR,
MUX2, SYNC_WAIT) are available but mostly unused in the IR lowering
pass. The correct fix is to lower compound operations to single cells
where the topology supports it directly.

### Preload bits (pending Verilog update)

Two new bits will allow a cell to self-load `a_data` at configure time:

```
bit A  a_preload_en   1 = load a_latch from a_preload_val on arm
bit B  a_preload_val  0 = load 0x00000000, 1 = load 0xFFFFFFFF
```

**Impact on compiler:**

The entire preloaded-A software sequence — `_tile_preloads`, the Python
forward simulation in `run_int32_function`, `known_preloads`, the two
controller passes — can be eliminated. Each cell that currently needs
a_data preloaded gets these two bits set instead. One configure pass,
one trigger wave, done.

The `_ir_preload_map`, `combined_preload`, `sim_vals`, `known_preloads`
dicts in `run_int32_function` all become dead code.

### Shift bits (pending Verilog update)

Two new bits control nibble-level bus routing:

```
bit C  shift_in_en   incoming data shifted by nibble_set before gate tree
bit D  shift_out_en  output shifted by nibble_set before bus emission
```

**Impact on compiler:**

- `x << N` and `x >> N` for nibble-aligned N (multiples of 4) become
  zero-cell operations. Compiler sets shift bits in the downstream cell's
  gate_state, no extra cells emitted.

- Multiply partial products land at the correct bit positions via
  shift_out_en — the 64 nibble pairs in a 32×32 multiply place their
  8-bit results at `(i+j)*4` bit offsets with no extra cells for shifting.
  The Wallace tree accumulation sees correctly-positioned values.

- Non-nibble-aligned shifts (residual 0-3 bits) need up to 3 NOR cells.

---

## Current Compiler Overcounting — Known Cases

### `x > 0` (647 cells, should be ~5)

`_compile_compare_typed` for `Gt` against literal 0 places:
- `INT32_LT_U` tile (518 cells) — full subtractor
- `INT32_MUX` tile (128 cells) — full 32-bit 2:1 MUX

Correct approach: OR-reduction of 32 input bits.
- 5 layers of OR gates = 31 cells for the tree
- With a_preload_en: each cell self-armed, single trigger wave
- Total: ~31 cells, not 646

Fix location: `_compile_compare_typed` in `compiler_int32.py`.
Intercept `Gt`/`Lt`/`NotEq` against literal 0 before tile placement.

### `x == CONST` (864 cells, should be ~37)

Places `INT32_EQ` tile (864 cells).

Correct approach:
- XOR each of 32 bit pairs (a[i] XOR const_bit[i]) using a_preload_en
  (a_preload_val = const_bit[i], so XOR(a[i], const_bit) = NOT(a[i]==const_bit))
- NOR-reduce: any non-zero XOR means not-equal
- Total: 32 XOR cells + 5 NOR reduction = ~37 cells

Fix location: same — intercept `Eq` against `_broadcast_constant`.

### `if cond: return A else: return B` (128 cells for constants, should be ~1-32)

Places `INT32_MUX` tile (128 cells) even when A and B are compile-time constants.

Correct approach: with a_preload_en, 32 cells each preloaded with the
correct output bit. Condition bit routes which set fires. Or simpler:
condition bit directly selects between two PTT write addresses — no
data-path cells at all.

Fix location: `_compile_if` in `compiler_int32.py`.
Detect when both branches are `Int32Value` from `_broadcast_constant`.

---

## Architecture of `run_int32_function`

Currently three cases:

1. **Zero records** — pure constant or passthrough. Read from known_values
   or input_addr_vals directly. Works correctly after 2026-05-30 fix.

2. **Case 2** — all A-sources are direct input bits (simple AND/OR/XOR).
   Build preloaded_a directly from a_vals without forward sim.

3. **Case 3** — A-sources are computed intermediates (KS adder, SUB,
   EQ, MUX). Python forward simulation walks all records in emit order,
   computes correct a_data for each cell, then runs controller.

After a_preload_en lands: Cases 2 and 3 collapse. No forward sim needed.
Each cell's gate_state encodes its own a_data. Single controller pass.

---

## Known Bugs

See TODO.md for full list. Key compiler bugs:

- MUL preloaded_a normalisation: values 0/1 reach XOR cells as single
  bits, should be 0/0xFFFFFFFF. XOR(1, 0xFFFFFFFF) = 0xFFFFFFFE (wrong).
  Moot after a_preload_en.

- Output bit padding in `_place_int32_tile` uses bare `GS_PASS` (gs=0)
  not `GS_PASS | GS_LATCH_IN`. Bare PASS waits for two arrivals and
  never fires in single-wave propagation. Fix: use `GS_PASS | GS_LATCH_IN`
  in all padding chains.

- Duplicate `compile_int32_function` (lines 136 and 1135). Line 1135 wins.
  Line 136 is dead code.

---

## What the Compiler Should Do Next

Priority order:

1. Update gate_state constants for 4 new Verilog bits
2. Remove forward simulation — cells self-preload via a_preload_en
3. Add constant-comparison intercepts (> 0, == CONST)
4. Add constant-branch optimisation (if/else with literal returns)
5. Add shift operator support using shift_in/out bits
6. Rewrite INT32_MUL using shift_out_en for partial product placement
7. Fix INT32_DIV or defer (reciprocal for compile-time constants only)

The compiler's job grew considerably. It now needs to reason about:
- Whether a comparison is against a compile-time constant (simplify)
- Whether branch values are compile-time constants (skip MUX)
- Which cells can self-preload (set bits, skip preload pass)
- What nibble shift gets output to the right bus position (set shift bits)
- Topological order of cell records (for correct restore order in .isi)
- Address space layout (PTT regions, Sentinel regions, Shore regions)

The output is no longer just a list of cell records — it's a `.isi`
system image with a structured address map and typed regions.
