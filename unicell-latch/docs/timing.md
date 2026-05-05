# unicell-latch — Timing Model

## Overview

The latch model separates the clock from the compute path. The NOR gate tree
is purely combinational. Two flip-flop banks are the only registered elements.
The clock controls only when data flows between them.

This gives a clean, predictable timing model with a single formula:

```
chain_latency(n) = n + 1   ticks
```

where `n` is the number of cells in the chain.

---

## The 3-Phase Tick

Each clock tick executes three phases in sequence. In RTL (unicell_latch.v)
all three collapse into a single clocked always block — they happen on the
same posedge, ordered by nonblocking assignment semantics. In the Python
simulator (unicell_array.py) they are explicit method calls.

```
Phase 1 — Drain output_ff → bus
  Each cell that has a pending result in output_ff drives it onto the
  shared wired-OR bus and clears output_ff_valid.

Phase 2 — Bus → input_ff
  Each cell that sees its input_address on the bus loads the data into
  input_ff and sets input_ff_valid. SYNC_WAIT cells also check input_b_address
  and load input_b_ff.

Phase 3 — input_ff → gate tree → output_ff (compute)
  Each cell with input_ff_valid fires the gate tree. The result is stored
  in output_ff for draining next tick.
```

Phases 1 and 2 happen on the same clock edge. This is why each cell adds
only 1 tick of latency to a chain — not 2. One cell's output is drained
to the bus on the same tick that the next cell's input is loaded.

---

## Latency Formula

```
CELL_LATENCY    = 2   (single cell: load tick + compute tick)
chain_latency(n) = n + 1
```

Examples:

| Chain length | Ticks to output |
|:---:|:---:|
| 1 | 2 |
| 2 | 3 |
| 4 | 5 |
| 8 | 9 |
| n | n+1 |

**Single cell (n=1):**
```
Tick 0:  bus → input_ff          (Phase 2)
Tick 1:  input_ff → gate → output_ff  (Phase 3)
Tick 2:  output_ff → bus         (Phase 1)
```
Result visible at tick 2. CELL_LATENCY = 2.

**Two cells (n=2), A→B:**
```
Tick 0:  data → A.input_ff
Tick 1:  A computes → A.output_ff
Tick 2:  A drains → bus = B.input_ff  (Phases 1+2 on same edge)
Tick 3:  B computes → B.output_ff
Tick 4:  B drains → bus
```
Result visible at tick 4 from tick 0. chain_latency(2) = 3 intervening ticks.

Wait — the formula gives n+1 = 3 ticks of *computation time*, meaning
the result is on the bus 3 ticks after input was delivered. This is the
number that test_helpers.py uses for `chain_latency(n)`.

---

## PASS Cells as Delay Elements

A PASS cell (gate_state = 0) passes its input unchanged and adds exactly
1 tick of latency. Use PASS cells to align parallel paths.

```
Path A: 3 cells, latency = 4 ticks
Path B: 1 cell,  latency = 2 ticks

To align B with A: insert 2 PASS cells before B.
  B' = PASS → PASS → B_cell, latency = 4 ticks ✓
```

The compiler inserts PASS cells automatically during depth alignment
in `lower_to_cell_map_v2()`. Each PASS cell costs one cell address
and one tick.

---

## SYNC_WAIT Cells (Two-Input)

A SYNC_WAIT cell (GS_SYNC_WAIT, bit 15) waits until both inputs are valid
before computing. The cell has two listen addresses:

- `input_address` — A input (posedge path, rising edge data)
- `input_b_address` — B input (negedge path, falling edge data)

The cell fires as soon as both `input_ff` and `input_b_ff` are valid.
Whichever arrives last triggers the compute on that tick.

In a balanced design, both A and B should arrive on the same tick. If they
arrive on different ticks, the cell holds the first one in its FF and waits.
This introduces no extra latency beyond the cell's normal n+1 contribution
as long as both paths are depth-aligned.

**Path balancing for SYNC_WAIT:**

If A has depth 3 and B has depth 5 (both feeding a SYNC_WAIT cell):
- A path needs 2 PASS cells to reach depth 5
- Both arrive at tick 6 (chain_latency(5) = 6)
- SYNC_WAIT cell fires at tick 6, result at tick 7

Without alignment: A arrives at tick 4, waits. B arrives at tick 6. Cell
fires at tick 6. Same result — but the A FF holds data for 2 extra ticks.
Both approaches give the same output tick. Alignment is a cleanliness
preference and avoids unexpected interactions if the A FF is repurposed.

---

## Configuration Sequence

The configuration sequence is the same as the standard variant. The cell
recognises a LOAD_PATTERN on its CONFIG_ADDRESS and enters config mode.

**Standard cell (3 config words after LOAD_PATTERN):**
```
Bus → CONFIG_ADDRESS, 0xA5A5A5A5    — triggers config mode
Bus → any,           gate_state     — NOR topology + mode flags
Bus → any,           input_address  — runtime A listen address
Bus → any,           output_address — output write address
                                     — cell arms, exits config mode
```

**SYNC_WAIT cell (4 config words):**
```
... (same first 4 words) ...
Bus → any,           input_b_address — B listen address
                                      — cell arms, exits config mode
```

**SELECT cell (4 config words):**
```
... (same first 4 words) ...
Bus → any,           output_address_alt — condition=0 target
                                        — cell arms, exits config mode
```

Config addresses are fixed synthesis-time parameters (CONFIG_ADDRESS).
Runtime data routing uses the registered `input_address`. These are
intentionally separate — config can never be triggered by data traffic.

---

## Gate State Register

The gate_state register is 32 bits. Bit layout:

| Bits | Name | Effect |
|:---|:---|:---|
| 8:0 | NOR topology | Which of 9 gates are active (one or more bits) |
| 9 | GS_SELECT | Conditional router (not NOR compute) |
| 10 | LOOP_MODE | Stay armed after firing |
| 11 | GS_LATCH | Hold + re-emit stored value each tick |
| 12 | GS_ONE_SHOT | Fire once then lock permanently |
| 13 | GS_INVERT_OUT | Complement output after gate tree |
| 14 | GS_BROADCAST | Fan out to all cells at output_address |
| 15 | GS_SYNC_WAIT | Two-input: wait for both A and B |
| 16 | GS_LOOP_BACK | Internal G8→G0 feedback (future) |
| 22:17 | loopback src/dst | Gate indices for loop_back |
| 23 | GS_ADDR_LATCH | Extended 64-bit address (bridge cells) |
| 24 | GS_FALL_EDGE | Assert on falling edge (standard variant) |
| 31:29 | PRIORITY/TRACE/BREAKPOINT | Debug and scheduling |

In the latch model, GS_FALL_EDGE (bit 24) is not used — the model has no
falling-edge output path. Bit 24 is accepted in config but has no effect.
The two-phase A/B input model is handled by GS_SYNC_WAIT + input_b_address,
not by edge separation.

---

## NOR Gate Topology

9 NOR gates in a fixed topology. A gate is "active" if its bit in
gate_state[8:0] is set; otherwise it is bypassed (passes first operand).

```
One-input mode (standard compute):
  g0 = active(0) ? NOR(A, A) : A      — NOT(A)
  g1 = active(1) ? NOR(A, A) : A      — NOT(A) (redundant in 1-input)
  g2 = active(2) ? NOR(g0, g1) : g0
  g3 = active(3) ? NOR(g2, A)  : g2
  g4 = active(4) ? NOR(g2, A)  : g2
  g5 = active(5) ? NOR(g3, g4) : g3
  g6 = active(6) ? NOR(g5, A)  : g5
  g7 = active(7) ? NOR(g6, g5) : g6
  g8 = active(8) ? NOR(g7, 0)  : g7   — output

Two-input mode (SYNC_WAIT):
  g0 = active(0) ? NOR(A, A) : A      — NOT(A)
  g1 = active(1) ? NOR(B, B) : B      — NOT(B)
  g2 = active(2) ? NOR(g0, g1) : g0   — AND(A,B) when g0=NOT(A), g1=NOT(B)
  g3 = active(3) ? NOR(g2, B)  : g2
  g4 = active(4) ? NOR(g2, A)  : g2
  g5 = active(5) ? NOR(g3, g4) : g3
  g6 = active(6) ? NOR(g5, B)  : g5
  g7 = active(7) ? NOR(g6, g5) : g6
  g8 = active(8) ? NOR(g7, 0)  : g7   — output
```

All 12 logic functions are expressible in a single cell. See gate_states.py
for the verified bit patterns (GS_AND_V2, GS_OR_V2, GS_XOR_V2, etc.).

---

## Verilog Notes (unicell_latch.v)

**Gate tree inputs must be `wire`, not `reg`.**

The gate tree wires (`a_in`, `b_in`, and g0–g8) are combinational off
`input_ff` and `input_b_ff`. They must be declared as `wire`. If declared
as `reg`, the simulator evaluates `computed_bit` using the value from the
*previous* always-block evaluation — giving wrong results for every mode.

This was caught during development: all tests produced the complement of
the correct output. Fix: `wire a_in = input_ff[0];`

**Phase 1 + Phase 2 in the same always block:**

Both drain (Phase 1) and load (Phase 2) are in the same `always @(posedge clk)`
block. Nonblocking assignments mean Phase 2's write to `input_ff` is not
visible to Phase 3 in the same tick — Phase 3 reads the old `input_ff`.
This is intentional: it enforces the one-tick delay between load and compute
that gives chain_latency(n) = n+1.

---

*Last updated: 2026-05-12, Claudette v2.1 / unicell-latch*

---

## Independent Verification — EDA Playground

The latch Verilog (unicell_latch.v + unicell_array_latch.v) was independently
verified using Icarus Verilog on EDA Playground.

**Reference:** https://edaplayground.com/x/pVQp
**Simulator:** Icarus Verilog
**Testbench:** tb_unicell_latch.v (22 tests)
**Result:** 22 passed, 0 failed

Waveform: `unicell test trace.png` (this directory)

Key observations from the waveform:
- pass_count counts 0→22 in binary (10, 100, 101, 110...) — all tests pass
- fail_count stays at 0 throughout the entire trace
- bus_valid pulses clean and regular
- out_valid_a and out_valid_b fire at correct times
- merged_valid shows correct wired-OR arbitration
- freeze_a tested and released cleanly

This constitutes independent third-party verification that the latch cell
timing model is correct before iCEBreaker hardware bring-up.
