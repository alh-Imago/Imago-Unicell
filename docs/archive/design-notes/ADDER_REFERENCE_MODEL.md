# Adder Reference Model — Two-Arrival Analysis

Captured 2026-05-18 from reference implementation.

## Reference model observations

The reference 32-bit ripple-block adder has the same structure as our
unicell model: `a_arrived` flag, two-arrival per cell, explicit `drive()`.

Key pattern from `run_add()`:
```python
for i in range(32):
    self.drive(0x1000 + i, (a_val >> i) & 1)   # A bits
    self.drive(0x2000 + i, (b_val >> i) & 1)   # B bits
self.drive(0x4000, 0)  # carry-in = 0
for _ in range(max_cycles):
    self.tick()  # run for fixed cycles, no early termination
```

And `tick()`:
```python
for cell in self.cells.values():
    for baddr, bdata in list(self.bus.items()):
        out = cell.tick(baddr, bdata)
        if out: break  # one reaction per cell per tick
self.bus.clear()
for addr, data in outputs:
    self.bus[addr] = data
```

## Key architectural points

1. **No fixed termination** — run for max_cycles, don't try to detect
   completion. This avoids the early-exit problem.

2. **Bus cleared each tick** — values don't persist beyond one tick.
   The carry chain propagates because each cell drives output_addr fresh.

3. **Two inputs at different addresses** — XOR/AND cells listen on `a_addr`
   (A's address). B at `b_addr` is separate. The routing question (how B
   reaches the XOR cell) is still open in both the reference and our model.

4. **One reaction per cell per tick** — the `break` after first match
   means each cell only processes one bus value per tick.

## Open problem: two-source routing

For a cell that needs inputs from TWO different upstream cells (different
addresses), the two-arrival model requires both to arrive at the same
`input_address`. Current options:

A. **Relay cells** (GS_PASS_B|latch_in): forward B from src_b → src_a.
   Working for high-level compiler (AND/OR/XOR via ir.py relay).
   Broken for INT32 — relay doubles cell count and disrupts KS timing.

B. **Tile placer merge**: map in_b → in_a in the tile placer.
   Requires injection to send A first, then B at same address.
   Termination breaks before B arrives at second-level cells.

C. **Fixed max_cycles**: don't use smart termination, just run for N cycles.
   The reference model uses this approach. Simple and reliable.

D. **Dedicated INT32 scheduler**: `run_int32_function` drives packets
   explicitly — P_hi → AND1 (first arrival), G_lo → AND1 (second arrival).
   This matches the KS packet schedule exactly.

## Recommended approach for INT32 (next session)

Option C (fixed max_cycles) combined with option D (explicit scheduling):
- `run_int32_function` drives A bits first, B bits second at in_a addresses
- `controller.run()` uses `max_cycles=100` (KS depth ~24 cycles + margin)
  instead of smart termination
- No relay cells in fp_tiles
- Simple, robust, matches reference model

The `arrival_pending` termination check causes infinite loops.
The `buf_pending` check exits too early for multi-stage chains.
Fixed max_cycles avoids both problems.
