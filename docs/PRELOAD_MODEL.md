# Preload Architecture — Hosted vs Standalone

**Created: 2026-05-29**

This document defines the three-tier preload model and the plan for
implementing standalone execution without a Python host.

---

## The Three Cases

### Case 1 — Static preload (no runtime computation needed)

Cells whose A-side value is CONSTANT regardless of inputs:
- NOT cells: `a_data = 0xFFFFFFFF` always
- Cells with a constant operand baked at compile time

**Solution:** store `init=` in the ICM at compile time.
The ICM loader issues CMD_PRELOAD from the stored value. Zero runtime cost,
zero extra cells. Works standalone. **Already partially implemented** —
`workspace._install()` auto-detects NOT cells. Full compiler support needed.

### Case 2 — Partial dynamic (A is a raw input bit)

Cells whose A-side is simply a copy of one of the input bits:
- INT32_AND: each cell `a_data = a_bit[i]`
- INT32_OR: same
- INT32_XOR: same

**Solution:** ordered injection. Inject A-side inputs first → they store as
normal first arrivals. Then inject B-side inputs → cells fire. No CMD_PRELOAD,
no PreloadTile, no extra cells. Works standalone with a simple two-phase
injection protocol in the bridge/controller.

### Case 3 — Full dynamic (A is a computed intermediate)

Cells whose A-side is the OUTPUT of a previous cell in the computation tree:
- INT32_ADD: 418/482 cells — KS prefix carries (AND/OR/XOR chain)
- INT32_SUB: 421 cells
- INT32_EQ: 31 cells
- INT32_MUX: 64 cells
- INT32_LT_U, INT32_MIN_U, INT32_MAX_U: 400+ cells
- PARITY_32: 15 cells

**These cannot be pre-computed.** The A values depend on (a, b) at runtime.
They require either a Python host (current) or a PreloadTile (standalone).

---

## Execution Paths

### Hosted path (VM or PCIe card with Python host)

`compute_tile_preloads()` runs in Python — simulates the prefix chain,
returns `{out_addr: a_data_value}` for every cell. Controller issues
CMD_PRELOAD from those values. Zero extra cells.

**This path is kept exactly as-is.** When a host is available, use it.

### Standalone path (no Python host)

A **PreloadTile** — a separate silicon region — computes the prefix chain
and writes results directly onto the bus at the compute tile's input addresses.
The compute tile cells pick those up as natural first arrivals.

#### How it works (no CMD_PRELOAD needed)

```
PreloadTile output_address[i] = ComputeTile input_address[i]

Execution:
  Phase 1 — load(a, b):
    Run PreloadTile with inputs (a, b).
    PreloadTile computes prefix carries, writes them to shared bus addresses.
    ComputeTile cells receive these as first arrivals (a_data stored).

  Phase 2 — run():
    User sends B-side inputs to the same shared bus addresses.
    ComputeTile cells see second arrival → fire → emit sum bits.
```

No CMD_PRELOAD. No special hardware. Pure two-arrival. Works on any silicon.

#### PreloadTile structure (INT32_ADD example)

The prefix carry chain needs AND, OR, XOR cells:
- 227 AND cells  (compute generate: g = a AND b)
- 98  OR cells   (propagate carry: G = G_r OR (P_r AND G_l))
- 93  XOR cells  (propagate: p = a XOR b)
- 64  PASS cells (leaf nodes — pass a_bit directly)

Total: ~480 cells for the preload stage.
Combined with compute tile (~589 cells): ~1069 cells for standalone INT32_ADD.

For hosted: 589 cells + Python sim.
Tradeoff: ~480 extra cells to eliminate the Python host dependency.

---

## ICM Format Change (v3 — multi-region)

To support two-region programs, the ICM format needs a `regions` array:

```json
{
  "name": "int32_add",
  "format_version": 3,
  "regions": [
    {
      "name":    "preload",
      "records": [...],
      "inputs":  {"a": [addr, ...], "b": [addr, ...]},
      "outputs": {}
    },
    {
      "name":    "compute",
      "records": [...],
      "inputs":  {"shared": [addr, ...]},
      "outputs": {"sum": [addr, ...]}
    }
  ]
}
```

Single-region ICMs remain valid — treated as `regions[0]` implicitly.
Multi-region ICMs carry both paths in a single file.

---

## API

```python
# Hosted — unchanged, current path
result = run_compiled_function(src, 'add', {'a': 5, 'b': 3})

# Standalone — new path
model = ctrl.load_model('int32_add.icm')   # loads both regions
model.load({'a': 5, 'b': 3})              # phase 1: run preload region
result = model.run()                       # phase 2: trigger compute region

# Or one-shot:
result = model.execute({'a': 5, 'b': 3})
```

---

## Build Plan

1. **Compiler: emit `init=` for all static A values** (Case 1)
   - NOT cells: always `init=0xFFFFFFFF`
   - Any cell with constant A at compile time
   - Affects: `compiler.py`, `ir.py`, ICM emitter
   - Tests: verify `not_gate.icm` has `init=4294967295`

2. **Controller: ordered injection protocol** (Case 2)
   - `ctrl.run(rid, a_inputs, b_inputs)` — injects A first, waits, injects B
   - OR: two separate `ctrl.run()` calls with the same addresses
   - Affects: `controller.py`
   - Tests: AND/OR/XOR tiles work standalone

3. **PreloadTile builder in `fp_tiles.py`** (Case 3)
   - `make_preload_tile(compute_tile)` — builds carry-prefix tree
   - Output addresses match compute tile's A-source addresses
   - Affects: `fp_tiles.py`

4. **Multi-region ICM format v3**
   - `regions[]` array in ICM
   - Backward-compatible loader
   - Affects: `vm_image.py`, `icm_loader.py`, ICM format spec

5. **PreloadModel in `model_library.py`**
   - Wraps `(preload_tile, compute_tile)` pair
   - `execute()`, `load()`, `run()` API
   - Affects: `model_library.py`

6. **`test_standalone_*.py`** — runs all Case 3 tiles without `compute_tile_preloads()`

---

## What stays the Python host's job (permanently)

Even on a hosted card, the Python sim stays. It is:
- Faster (no extra cells, no bus traffic for the preload phase)
- Simpler (no PreloadTile region to manage)
- Already working

The standalone path is specifically for **truly standalone deployment**:
pure silicon, no attached computer, no Python anywhere.
