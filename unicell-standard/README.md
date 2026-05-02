# UniCell — Standard Model

The original UniCell model. Immediate output — cell fires on data arrival
and drives the bus in the same tick. No edge awareness, no output buffer.

## Timing Model

- Data arrives on the bus → delivered to cell → gate tree fires → result on bus
- **Same-tick output** — result visible immediately after cell fires
- No latency registers, no hold delay
- Simplest possible model — good for simulation and as a reference baseline

## Key Files

| File | Purpose |
|------|---------|
| `unicell.py` | Cell model, immediate output on fire |
| `unicell_array.py` | Array tick loop — new_bus pattern |
| `gate_states.py` | Bit definitions (no GS_OUT_POSEDGE) |
| `controller.py` | Region management |
| `fpga/verilog/unicell.v` | Synthesisable Verilog |

## Status

- v2.1 codebase (pre-edge-buffer)
- 2,238 tests passing at v2.1 tag
- Stable reference — changes here should be intentional and well-tested

## Relationship to Other Variants

- **UniCell Latch** — fork of Standard, adds input+output latches for
  clock-controlled flow. More stable on FPGA, especially large arrays.
- **UniCell Edge** — adds edge-triggered output buffer. Primary FPGA target.
