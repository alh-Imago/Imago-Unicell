# Session 2026-05-04

## Pre-session

Confirmed EDA Playground simulation results for unicell_latch.v:
- Simulator: Icarus Verilog
- Run date: 2026-05-03
- Testbench: tb_unicell_latch.v (22 tests)
- Result: 22 passed, 0 failed — ALL TESTS PASSED
- VCD dump provided (result_1_.zip). pass_count confirmed 0→22, fail_count stayed 0.
- Reference: https://edaplayground.com/x/pVQp

Alan also shared a draft visual cell composer tool (unicell_simulator.html):
a canvas-based drag-and-drop designer for placing cells, wiring by address,
and configuring gate topology via a sidebar inspector. Parked as future work —
"Visual Cell Composer". Currently uses 20-bit / v1 encoding; will need updating
to 32-bit gate_state when developed.

Baseline test status at session open: 424 tests, 0 failures (9 suites).

---

## Part 1 — Yosys multiple-driver fix (standard + edge)

**Problem:** Both unicell-standard and unicell-edge had `out_valid`, `out_data`,
`out_addr` declared as `output reg` and driven from both `posedge clk` and
`negedge clk` always blocks. Yosys flagged 65 "multiple conflicting drivers"
warnings per file (33 bits × 2 signals + valid = 67 — across both variants,
~130 warnings total).

**Fix:** Split output signals into per-domain internal registers:
```verilog
reg pos_valid; reg [31:0] pos_data; reg [31:0] pos_addr;  // posedge domain
reg neg_valid; reg [31:0] neg_data; reg [31:0] neg_addr;  // negedge domain
```
Output ports changed from `output reg` to `output wire`, driven by assign:
```verilog
assign out_valid = pos_valid | neg_valid;
assign out_data  = pos_valid ? pos_data : neg_data;
assign out_addr  = pos_valid ? pos_addr : neg_addr;
```
Only one domain fires per cycle — no real collision. Yosys sees a single
combinational driver per port.

**Result:** All three variants clean.

| Variant | Warnings before | Warnings after |
|:---|:---:|:---:|
| unicell-standard | ~65 | 0 |
| unicell-edge | ~65 | 0 |
| unicell-latch | 0 (already clean) | 0 |

**Files modified:**
- `unicell-standard/fpga/verilog/unicell.v`
- `unicell-edge/fpga/verilog/unicell.v`

**Committed:** `RTL: fix multiple-driver warnings in standard and edge variants`

---

## Part 2 — uart_bridge SET_FLAGS (0x08)

### Verilog

**uart_bridge.v** — new port and command:
```verilog
output reg [63:0] start_flags   // new port
```
Command `0x08` SET_FLAGS: 9 bytes (cmd + 8-byte mask, big-endian).
Writes mask directly to `start_flags` output reg — no LOAD_PATTERN needed.
Response `0x15`: echoes the 64-bit mask back for host verification.

**top_icebreaker.v** — two fixes + wiring:
1. Fixed module name: `unicell_array` → `unicell_array_latch` (was wrong since latch array was written)
2. Wired `start_flags_wire[NUM_CELLS-1:0]` between bridge and array `start_flags_in`
3. Added `start_flags_out_w` for debug observability

Full stack lint (unicell_latch.v + unicell_array_latch.v + uart_bridge.v + top_icebreaker.v):
**0 warnings, 0 errors.**

### Python (fpga_bridge.py)

New file. Two classes:

**FPGABridge** — hardware UART driver for iCEBreaker:
- `configure(cell_id, gate_state, input_addr, output_addr)` — sends LOAD_PATTERN config sequence
- `inject(addr, data)` — injects bus transaction
- `set_flags(mask)` — sends 0x08, verifies 0x15 echo, raises on mismatch
- `reset()`, `freeze()`, `release()`, `status()`, `read_output()`, `read_output_full()`, `drain()`
- Requires `pyserial` — import is lazy, clear error if missing

**SimBridge** — VM-backed drop-in replacement:
- Same API as FPGABridge — swap with one line change
- `configure()` uses `UniCellArray.write_config()` + `assert_start_flag()` correctly
- Cells allocated on demand via `allocate_cell()`, tracked by `_cell_addrs[cell_id]`
- Bus entries written as `(data, ecc=0)` tuples matching latch array format
- `set_flags(mask)` maps bit N → cell N via `_cell_addrs`, calls
  `assert_start_flag()`/`clear_start_flag()` as appropriate

### Tests (test_fpga_bridge.py)

36 tests, 0 failures:
NOT gate, PASS gate, set_flags (arm all / disarm all / partial / clip to num_cells /
arm-then-disarm), configure auto-arms, reset (clears cells + addrs + pending queue),
drain, read_output_full (3-tuple with hs=0), context manager, protocol constants.

**Committed:** `uart_bridge: add SET_FLAGS (0x08) command — latch bring-up`

---

## Final test status

| Suite | Passing | Failing |
|:---|:---:|:---:|
| test_gate_state_32.py | 73 | 0 |
| test_array.py | 21 | 0 |
| test_controller.py | 26 | 0 |
| test_branch.py | 61 | 0 |
| test_freeze.py | 64 | 0 |
| test_addr_latch.py | 49 | 0 |
| test_select.py | 43 | 0 |
| test_bridge_integration.py | 54 | 0 |
| test_migration.py | 33 | 0 |
| test_fpga_bridge.py | 36 | 0 |
| **Total** | **460** | **0** |

Yosys lint: **0 warnings, 0 errors** across all three variants.

---

## Files committed this session

### New
- `unicell-latch/fpga_bridge.py`
- `unicell-latch/test_fpga_bridge.py`

### Modified
- `unicell-standard/fpga/verilog/unicell.v` — multiple-driver fix
- `unicell-edge/fpga/verilog/unicell.v` — multiple-driver fix
- `unicell-latch/fpga/verilog/uart_bridge.v` — SET_FLAGS command
- `unicell-latch/fpga/verilog/top_icebreaker.v` — module name fix + start_flags wiring

---

## Next session priorities

1. **fpga_bringup.py** — bring-up sequence script
   LED blink → UART loopback → NOT gate → AND → bridge pair.
   Uses SimBridge for VM testing now; plug FPGABridge when iCEBreaker arrives.

2. **LIF neuron v2** — port to latch model
   6-8 cells/neuron. Testable in VM. Runs 4-5 neurons on iCEBreaker.

3. **Visual Cell Composer** — parked, future work
   unicell_simulator.html. Needs 32-bit gate_state update. Develop after bring-up.

---

## Note for next session

iCEBreaker still awaited. When it arrives:
- `fpga_bridge.py` FPGABridge is ready to connect — just pass the port
- `uart_bridge.v` + `top_icebreaker.v` are wired and lint-clean
- SET_FLAGS lets you arm cells without the config sequence — useful for bring-up probing
- All Verilog is Verilog-2001 clean and portable

*Session closed 2026-05-04.*

---

## Part 3 — LIF Neuron v2 (latch model)

### Design

6-cell Leaky Integrate-and-Fire neuron, porting docs/lif_neuron_reference.v
(v1 Verilog, standalone, 40-50 cell equivalent) into a UniCell latch pond.

Binary 1-bit model: V=1 = above threshold (charged), V=0 = discharged.

**Cell layout:**

| Cell | Role | Gate state | A input | B input | Output |
|:---|:---|:---|:---|:---|:---|
| 0 | MEMBRANE | LATCH\|LOOP\|PASS | ADDR_INTEG | — | ADDR_V |
| 1 | LEAK | NOT\|LOOP | ADDR_V | — | ADDR_LEAK |
| 2 | INTEGRATE | SYNC_WAIT\|OR\|LOOP | ADDR_V | ADDR_SYN | ADDR_INTEG |
| 3 | SPIKE | LATCH\|LOOP\|NOR\|INVERT | ADDR_V | — | ADDR_SPIKE |
| 4 | REFRACT | LATCH\|LOOP\|NOT | ADDR_SPIKE | — | ADDR_REF |
| 5 | REARM | PASS\|LOOP | ADDR_REF | — | ADDR_REARM |

**Key design decisions found during development:**

- SYNC_WAIT cells need LOOP_MODE or they disarm after first fire
- Cell 3 (spike): ONE_SHOT fires on V=0 as well as V=1 (disarms on the seed tick).
  Fixed by using LATCH+LOOP+NOR+INVERT — this mirrors V exactly (NOR(V,V)=NOT(V),
  INVERT=V) and stays armed permanently via LOOP_MODE.
- Membrane must be seeded: write ADDR_INTEG=0 during build() so LOOP_MODE starts
  cycling and c2 (SYNC_WAIT) has a V value to match on first stimulate().
- input_b_address=0 is falsy in the tick loop (skipped). All neuron addresses
  use base≥0x1000, so ADDR_SYN=base+0x00=non-zero. Documented constraint.

**Timing:**

    Tick 0: stimulate() -> SYN on bus
    Tick 1: Cell 2 (INTEGRATE) fires -> INTEG=1
    Tick 2: Cell 0 (MEMBRANE) fires -> V=1, Cell 3 (SPIKE) fires -> SPIKE=1

**Scaling:**

    iCEBreaker (64 cells):   ~8 neurons (6 cells + 2 wiring overhead)
    10,000 cell array:        ~1,250 neurons
    500M cell ASIC:           ~60M neurons

### Files

**New:**
- `unicell-latch/lif_neuron_v2.py` — LIFNeuron and LIFNeuronPond classes
- `unicell-latch/test_lif_neuron_v2.py` — 39 tests, 0 failures

### Tests

| Feature | Result |
|:---|:---|
| build (6 cells, addresses) | PASS |
| rest state (quiescent) | PASS |
| single spike on stimulate | PASS |
| no spike without input | PASS |
| refractory active while spiking | PASS |
| rearm (no-op in LATCH design) | PASS |
| leak signal observable | PASS |
| stride / address layout | PASS |
| pond build (4 neurons, 24 cells) | PASS |
| pond stimulate (selective) | PASS |
| feed-forward connect (0→1) | PASS |
| repr | PASS |
| **Total** | **39/39** |

**Committed:** `lif_neuron_v2: 6-cell LIF neuron for latch model`

---

## Final test status (end of session)

| Suite | Passing | Failing |
|:---|:---:|:---:|
| test_gate_state_32.py | 73 | 0 |
| test_array.py | 21 | 0 |
| test_controller.py | 26 | 0 |
| test_branch.py | 61 | 0 |
| test_freeze.py | 64 | 0 |
| test_addr_latch.py | 49 | 0 |
| test_select.py | 43 | 0 |
| test_bridge_integration.py | 54 | 0 |
| test_migration.py | 33 | 0 |
| test_fpga_bridge.py | 36 | 0 |
| test_lif_neuron_v2.py | 39 | 0 |
| **Total** | **499** | **0** |

Yosys lint: 0 warnings, 0 errors (all three variants).

---

## Files committed this session (complete)

### New
- `unicell-latch/fpga_bridge.py`
- `unicell-latch/test_fpga_bridge.py`
- `unicell-latch/lif_neuron_v2.py`
- `unicell-latch/test_lif_neuron_v2.py`

### Modified
- `unicell-standard/fpga/verilog/unicell.v` — multiple-driver fix
- `unicell-edge/fpga/verilog/unicell.v` — multiple-driver fix
- `unicell-latch/fpga/verilog/uart_bridge.v` — SET_FLAGS command
- `unicell-latch/fpga/verilog/top_icebreaker.v` — module name + wiring

---

## Next session priorities

1. **fpga_bringup.py** — bring-up sequence script
   LED blink → UART → NOT gate → AND → bridge pair.
   Uses SimBridge in VM now; FPGABridge when iCEBreaker arrives.

2. **Visual Cell Composer** (unicell_simulator.html)
   Update from 20-bit v1 to 32-bit v2 gate_state encoding.
   Add latch model gate presets. Save/load to JSON.
   Low priority — after bring-up.

3. **LIF neuron v2 — extensions**
   Multi-bit membrane (32-bit V using INT32 cells).
   Configurable leak (shift register approximation).
   Synapse weight cell (AND gate before integrate).
   All deferred until bring-up validates the base architecture.

---

## Architecture notes

**Discovered this session:** `input_b_address=0` is treated as "not set" by
the tick loop (`if b_addr:` check). Bus address 0 cannot be used as a SYNC_WAIT
B-input. All ponds must use base address ≥ 1. Documented in lif_neuron_v2.py.

**LIF neuron design insight:** ONE_SHOT is problematic as a spike cell because
it fires on ANY value (including 0) and disarms. The LATCH+LOOP+NOR+INVERT
pattern is the correct spike indicator: mirrors V continuously, stays armed,
no re-arm cycle needed. Spike=1 held as long as V=1.

*Session closed 2026-05-04 (extended).*

---

## Part 7 — fpga_bringup.py

See sessions/2026-05-04-bringup.md for full detail.

**Summary:** Six-step bring-up script, SimBridge VM validation complete.
547 tests total, 0 failures. Ready for iCEBreaker arrival.

Three real bugs found: FUNCTION_LOAD_PATTERN as inject data, missing
LOOP_MODE on truth-table cells, LOOP_MODE stale bus contamination in
scale test. All fixed and documented in commit message.

*Session closed 2026-05-04.*
