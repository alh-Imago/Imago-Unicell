# UniCell — Edge Model (v2)

The edge-triggered variant of UniCell. This is the primary FPGA target for iCEBreaker bring-up.

## Timing Model

- A (primary) input arrives on the **rising edge**
- B (secondary) input arrives on the **falling edge**
- Cell fires on B arrival (negedge), result held in **output buffer**
- Output buffer released on next **rising edge** (GS_OUT_POSEDGE=1) or **falling edge** (default)
- One-cycle latency per cell in feed-forward paths

## Key Files

| File | Purpose |
|------|---------|
| `unicell.py` | Cell model with input/output buffer registers |
| `unicell_array.py` | Array tick loop — `_injected`, `_carry`, Phase 0/1/2 |
| `gate_states.py` | Bit definitions including `GS_OUT_POSEDGE` (bit 26) |
| `controller.py` | Region management, run/halt/freeze/thaw |
| `fpga/verilog/unicell.v` | Synthesisable Verilog — registered outputs |

## Bus Model

Three-layer bus rebuilt fresh each tick:
- `_injected` — external controller writes, one tick only
- `_carry` — output-buffer drains, persist one extra tick for feed-forward
- Phase 2 direct writes — feedback/loop cells, overwrite carry

## Status

- v2.1 tagged, iCEBreaker bring-up in progress
- 2,238 tests passing
- Output buffer added 2026-05-02 (see sessions/)

## Compiler TODO

`lower_to_cell_map_v2()` must set `GS_OUT_POSEDGE` based on whether
output feeds A (posedge) or B (negedge) input of next cell.
