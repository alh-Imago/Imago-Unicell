# Latch Model Timing

*Applies to `unicell-latch/` only.*

---

## Fixed Latency

Every cell in the latch model has exactly **2-tick latency**:

```
Tick N:    Data arrives at input_address → stored in INPUT LATCH
Tick N+1:  Input latch → gate tree → result → OUTPUT LATCH
Tick N+2:  Output latch drives bus → downstream cells receive
```

This is unconditional. It does not depend on routing length, cell placement,
or clock frequency. A 4-stage pipeline always takes exactly 8 ticks.

---

## Path Balancing

When two paths of different depth feed the same cell, the shallower path must
be padded with PASS cells until both arrive at the same tick.

**PASS cell** (`gate_state = 0x00000000`): adds exactly 2 ticks of delay.
No logic, no transformation — just delays the value.

```
Path A (depth 2):  ──────────────────────────── C_merge
Path B (depth 6):  ──PASS──PASS──PASS──PASS──── C_merge
                   (4 PASS cells = 8 ticks extra)
```

Path A needs 2 extra PASS cells to match path B's depth of 6.

**Rule:** `pads_needed = (max_depth - path_depth) / 2`

The compiler handles this automatically via `depth_map` in `NORBuilder`.

---

## Tile Pipeline Depths

All depths are in ticks (multiply by 2 for tick count from above).

| Tile | Cells | Depth (ticks) |
|------|-------|---------------|
| NOT / PASS | 1 | 2 |
| AND / OR / XOR (v2) | 1 | 2 |
| INT32_ADD (KS) | 482 | 4 |
| INT32_SUB | 517 | 24 |
| INT32_EQ | 95 | 14 |
| INT32_MUX | 128 | 6 |
| FP32_ADD | 1,253 | 170 |
| FP32_MUL | 3,066 | 178 |

*Latch model doubles the depth compared to the standard variant because every
cell adds 2 ticks instead of 1.*

---

## Timing at Scale

At 24 MHz (iCEBreaker), one tick = 41.7 ns.

| Operation | Ticks | Time at 24 MHz |
|-----------|-------|---------------|
| NOT gate | 2 | 83 ns |
| AND gate | 2 | 83 ns |
| 32-bit add (KS) | 4 | 167 ns |
| FP32 multiply | 178 | 7.4 µs |
| 8-bit counter decrement | ~16 | 667 ns |

At 200 MHz (Kintex-7 target), one tick = 5 ns:

| Operation | Ticks | Time at 200 MHz |
|-----------|-------|----------------|
| NOT gate | 2 | 10 ns |
| 32-bit add (KS) | 4 | 20 ns |
| FP32 multiply | 178 | 890 ns |

---

## Why the Latch Model

The latch absorbs timing skew between cells across large arrays. On a standard
FPGA, routing delays between cells on opposite sides of the die can differ by
2–5 ns. At 200 MHz that is 40–100% of a clock period — timing closure becomes
hard.

With input and output latches, the cell re-synchronises to the clock boundary
at every stage. Routing skew is absorbed by the setup/hold margin of the latch.
The pipeline depth is a structural property of the cell count, not of the
routing — so timing analysis is trivial.

The tradeoff: 2× latency compared to the standard model. For throughput-bound
pipelines (streaming data) this doesn't matter — throughput equals 1 result
per 2 ticks regardless of pipeline depth once the pipe is full.

---

## Neural Pond Timing

For the 5-cell LIF neuron in the latch model:

- Spike in → spike out: 10 ticks (5 cells × 2 ticks each)
- At 24 MHz: 417 ns per neuron evaluation cycle
- Maximum spike rate: ~2.4 MHz (limited by the 2-tick refractory minimum)
- Biological neurons: 1–100 Hz typical firing rate

The latch model runs neural ponds at millions of times biological speed.
Even at 1 MHz clock the neuron evaluates at 500 kHz — far faster than needed.
The real constraint is how many neurons fit in the cell budget.

---

## Calculating Pipeline Depth

For a custom tile in the latch model:

1. Count the number of cell stages from input to output (the critical path)
2. Multiply by 2 (ticks per cell)
3. Add 2 for the final output latch drain

Example: 4-stage pipeline
- Critical path: 4 cells
- Depth: 4 × 2 = 8 ticks
- Plus output drain: 8 + 2 = 10 ticks total

The `NORBuilder.depth_of(addr)` method returns the depth in cell stages.
Multiply by 2 for ticks in the latch model.
