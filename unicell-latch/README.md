# UniCell — Latch Model

A fork of UniCell Standard adding input and output latches. The clock
controls **flow** only — the internal gate tree runs at its own speed.
This is the long-term stable target for large arrays and FPGA deployment.

## Timing Model

```
Tick N:    Data arrives → stored in INPUT LATCH
           Output latch → driven to bus (if loaded), then cleared

Tick N+1:  Input latch → gate tree fires → result → OUTPUT LATCH

Tick N+2:  Output latch → driven to bus
           New data → input latch
           ...repeats
```

- **Fixed 2-tick latency per cell**, always
- **No edge sensitivity** — no rising/falling edge awareness at all
- **Clock = flow controller only** — gate tree is combinatorial internally
- **Timing skew absorbed** by latches — clock drift in large arrays doesn't matter
- **Depth padding** via PASS cells — insert a PASS anywhere to add exactly 2 ticks

## Key Properties

- Every cell is structurally identical — no special config bits for timing
- Path balancing done in topology, not timing constraints
- Loop cells work naturally — feedback path goes through a PASS cell,
  giving a well-defined loop cycle of 2 × (cells in loop) ticks
- FPGA: gate tree is pure combinatorial logic between two flip-flop banks

## Status

- **Forked from Standard (v2.1)** — 2026-05-02
- Latch model not yet implemented — `unicell.py` is currently Standard
- Next steps: add `_input_latch` and `_output_latch` to UniCell,
  update `unicell_array.py` tick loop, write `fpga/verilog/unicell_latch.v`

## Relationship to Other Variants

- **UniCell Standard** — parent, immediate output, no latches
- **UniCell Edge** — edge-triggered output buffer, v2 FPGA target
