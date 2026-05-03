# unicell-edge — Timing Model

## Overview

The edge model uses both clock edges for computation. The rising edge (posedge)
receives input A. The falling edge (negedge) receives input B and fires the gate
tree. The result is held in an output buffer and released to the bus on the
following half-cycle — either the next negedge (default) or the next posedge
(GS_OUT_POSEDGE, bit 26).

This gives natural two-input cell operation with hard edge separation: A and B
arrive on different edges of the same clock cycle, and the gate tree sees both
simultaneously on the negedge without any wait-for-both logic.

Compare with the latch model, where edge separation is modelled as SYNC_WAIT
with two bus addresses. In the edge model, edge separation is the default — it
is how the cell works, not a special mode.

---

## The Two-Edge Compute Cycle

```
Posedge (rising edge) — A input
  Cell receives bus data at input_address → stores in data_reg.
  If GS_LATCH_IN (bit 25): also stores in input_latch for negedge re-use.
  If GS_OUT_POSEDGE (bit 26) and out_buf_valid: releases output buffer → bus.

Negedge (falling edge) — B input + compute + stage result
  Job 1: receive B input at input_b_address → fires gate tree with (A, B).
  Job 2: if out_buf_valid and NOT GS_OUT_POSEDGE: release output buffer → bus.

  Also: GS_LATCH_IN re-evaluation — if no new A data arrived this posedge,
  re-evaluate the gate tree using the latched A value. Enables single-cell
  counter with LOOP_MODE.
```

---

## Timing Formula

```
chain_latency(n) = 2n   half-cycles  =  n   full cycles
```

Each cell adds one full clock cycle of latency: posedge receives A, negedge
fires the gate tree, result buffered, released on negedge N+1 (or posedge N+1
for GS_OUT_POSEDGE cells).

In practice: inject data at posedge of cycle 0, result available at negedge of
cycle N (or posedge of cycle N for GS_OUT_POSEDGE).

Compare with the latch model: `chain_latency(n) = n+1 ticks`. For small
chains the edge model is slightly faster (no extra load tick). For large arrays
the difference is negligible.

---

## Output Buffer (out_buf)

The output buffer is the edge model's equivalent of the latch model's
`_output_latch`. It holds the gate tree result between compute (negedge) and
drain (negedge N+1 or posedge N+1).

```
Registers:
  out_buf_data    — computed result
  out_buf_addr    — output bus address
  out_buf_valid   — 1 when buffer holds undrained result
  out_buf_posedge — 1: release on next posedge, 0: release on next negedge
```

**GS_OUT_POSEDGE (bit 26):**
When set, the output buffer releases on the rising edge rather than the falling
edge. This separates two cells that both compute on negedge and write to the same
output address — one releases negedge, one releases posedge, avoiding collision
without an extra PASS cell. The compiler assigns this automatically.

---

## Two-Input Operation

Unlike the latch model (which uses two bus addresses and SYNC_WAIT), the edge
model uses the two clock edges directly:

```
A input: received at posedge, stored in data_reg
B input: received at negedge via input_b_address, triggers gate tree
```

The gate tree sees both A (from data_reg) and B (from bus, this negedge)
simultaneously when B arrives. No wait-for-both logic needed — the timing
is built into the clock.

**For single-input cells:** A is used for both operands of the gate tree
(B mirrors A internally). A arrives at posedge, gate tree fires at negedge.

**For two-input cells:** A arrives at posedge, B at negedge of the same
clock cycle. The gate tree fires at the negedge of that cycle, exactly
one half-cycle after A was received.

---

## GS_LATCH_IN (bit 25) — Input Persistence

When set, the cell stores each received A value in `input_latch`. On the
negedge, if no new A data arrived this cycle, the gate tree re-evaluates
using the latched A value and drives the output buffer.

Combined with LOOP_MODE (bit 10), this enables a single-cell counter:
- A arrives at posedge
- Gate tree fires at negedge (e.g., increment)
- Result goes to output_address
- output_address = input_address → result feeds back as next A
- input_latch holds A between cycles so the negedge re-evaluation
  can use the last A if the loopback hasn't arrived yet

This is the edge model's counter pattern. The latch model achieves the same
with GS_LATCH + LOOP_MODE via its three-phase tick.

---

## Configuration Sequence

Same as standard and latch variants:

```
Bus → CONFIG_ADDRESS, 0xA5A5A5A5   — triggers config mode
Bus → any,           gate_state    — NOR topology + mode flags
Bus → any,           input_address — runtime A listen address (posedge)
Bus → any,           output_address
```

For two-input cells (GS_FALL_EDGE path), `input_b_address` is registered
via the `input_b_address` attribute set directly by the controller after
configuration (not via a 4th config word — the edge model's B input routing
is handled differently from the latch model's SYNC_WAIT).

---

## Gate State Bits (edge-model specific)

| Bit | Name | Effect |
|:---|:---|:---|
| 8:0 | NOR topology | Which of 9 gates are active |
| 10 | LOOP_MODE | Stay armed after firing |
| 11 | GS_LATCH | Re-emit stored value each tick |
| 12 | GS_ONE_SHOT | Fire once then lock |
| 13 | GS_INVERT_OUT | Complement output |
| 24 | GS_FALL_EDGE | Legacy: stage result for negedge release (default in edge model) |
| 25 | GS_LATCH_IN | Input persistence + negedge re-evaluation |
| 26 | GS_OUT_POSEDGE | Release output buffer on posedge N+1 (not negedge) |

Note: GS_OUT_POSEDGE (bit 26) is unique to the edge model. The latch and
standard models do not use this bit.

---

## Freeze / Snapshot

The edge model's in-flight register is `out_buf` (equivalent to `_output_latch`
in the latch model). For correct pond migration, snapshots must capture
`out_buf_valid`, `out_buf_data`, `out_buf_addr`, and `out_buf_posedge`.
On restore, pre-loading these registers ensures the result is driven on the
first half-cycle after thaw with no pipeline bubble.

This is the same principle as the latch model's `_output_latch` capture,
documented in MIGRATION_TODO.md under FREEZE/MOVE. The edge model's
Python implementation uses `cell._output_buf` (if present) rather than
`cell._output_latch`.

---

## Comparison: Standard / Latch / Edge

| Property | Standard | Latch | Edge |
|:---|:---|:---|:---|
| Compute trigger | Immediate (posedge only) | Explicit 3-phase tick | Negedge of each cycle |
| Chain latency | `n` ticks | `n+1` ticks | `n` full cycles |
| Two-input model | SYNC_WAIT (wait-for-both) | SYNC_WAIT (two addresses) | Natural (posedge A, negedge B) |
| Output register | None (immediate) | `_output_latch` | `out_buf` |
| Edge separation | GS_FALL_EDGE | N/A | GS_OUT_POSEDGE |
| Counter pattern | GS_LATCH + LOOP | GS_LATCH + LOOP | GS_LATCH_IN + LOOP |
| Synthesis risk | None | None | Negedge FFs (some tools warn) |

**Synthesis note on negedge FFs:**
Some FPGA synthesis tools and lint checkers warn on `always @(negedge clk)`
blocks. This is a style warning, not an error — negedge registers are fully
supported on all common FPGA families (iCE40, ECP5, Xilinx, Intel). On ASIC
the negedge path is standard practice. Flag in tool constraints if needed.

---

*Last updated: 2026-05-12, Claudette v2.1 / unicell-edge*
