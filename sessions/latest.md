# Session 2026-05-12 — Full Session Log

## Session arc

Long session. Started with repo pull and baseline confirmation, then worked
through a substantial priority list with one very welcome diversion.

---

## Part 1 — unicell_latch.v

**Deliverable:** `unicell-latch/fpga/verilog/unicell_latch.v` + testbench.

The latch-model Verilog cell. Pure combinational gate tree between two FF
banks. Clock controls only the load-enables. No clock path in compute.

Key design insight found during development:
  Gate tree inputs (a_in, b_in) MUST be `wire`, not `reg`.
  If `reg`: gate tree reads previous tick's value on every compute.
  Symptom: all outputs complement of expected. Fix: `wire a_in = input_ff[0]`.

Modes implemented: PASS, NOR topology, LATCH, ONE_SHOT, INVERT_OUT,
SYNC_WAIT (two-input A+B), SELECT (conditional routing), LOOP, Freeze.

Testbench: 22 tests, all passing. chain_latency(2) = 3 confirmed in silicon.

---

## Part 2 — Verilog portability audit

All 9 RTL files across all three variants now clean Verilog-2001.

**Bug 1 (standard + edge):** Local `reg` declarations inside unnamed
`always @(*)` blocks are SystemVerilog syntax, not Verilog-2001.
Fixed by moving g0-g8 and input_val to module scope.

**Bug 2 (unicell-edge/unicell_array.v):** `BASE_ADDRESS` referenced
but never declared as a parameter. Added `parameter BASE_ADDRESS = 0`.

**New file:** `unicell_array_latch.v` — proper latch-model array wrapper.
Instantiates unicell_latch, has start_flags_in/out bus, no clk_n port.

---

## Part 3 — docs/timing.md (unicell-latch)

Full timing model: n+1 formula, 3-phase tick, PASS cells as delay elements,
SYNC_WAIT path balancing, config sequence, gate_state bit table, Verilog
implementation notes including the wire-vs-reg key insight.

---

## Part 4 — The diversion

Alan shared a document on self-growing neural clusters — a coherent design
for biologically-plausible neural ponds that can expand, rewire, and prune
themselves within the UniCell architecture. Nucleus region as local controller,
Hebbian learning via co-firing tracking, reward signal via broadcast address,
quarantine + watchdog stability.

This emerged from looking at near-memory compute chips (Fractile AI and others).
The key insight: not just a neural accelerator, but genuine concurrent isolation —
neural net, Photoshop-equivalent, tax calculation, all running simultaneously
in separate ponds with hard Ward boundaries. Not jack-of-all-trades, not master
of one. A different category.

Noted and filed. Future work, after iCEBreaker bring-up.

---

## Part 5 — Freeze/move output_latch

**The gap:** A cell mid-pipeline (result in _output_latch, not yet drained)
would lose that in-flight result on a naive freeze+migrate. Downstream cell
misses the value entirely.

**Fix:**
- `unicell.py snapshot()`: add `"output_latch"` key
- `controller.py restore_snapshot()`: restore `_input_latch` + `_output_latch`
- First drain tick after thaw drives the restored result — no pipeline bubble

17 new tests. test_freeze.py: 47 → 64 passing, 0 failures.

---

## Part 6 — unicell-edge/docs/timing.md

Two-edge compute model documented. posedge receives A, negedge fires gate
tree and receives B. out_buf as the edge model's _output_latch equivalent.
GS_OUT_POSEDGE (bit 26) for collision avoidance. Comparison table across
all three variants.

---

## Part 7 — top_asic.v (all three variants)

Clean parameterised ASIC-facing top-levels. Standard Verilog-2001, no vendor
primitives. Suitable for Tiny Tapeout 130nm, GF180, or any ASIC process.
Latch variant includes bring-up stub (start_flags all-ones) with TODO for
uart_bridge SET_FLAGS extension.

---

## Part 8 — Yosys lint

unicell_latch.v: CLEAN. Zero warnings, zero errors, zero inferred latches.

Standard/edge: pre-existing multiple-driver warnings — posedge and negedge
always blocks both write out_data/out_addr/out_valid. Logged for next session.
Does not affect simulation correctness.

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
| Verilog sim (unicell_latch.v) | 22 | 0 |
| Yosys lint (unicell_latch.v) | CLEAN | — |

---

## Files committed this session

### New
- `unicell-latch/fpga/verilog/unicell_latch.v`
- `unicell-latch/fpga/verilog/tb_unicell_latch.v`
- `unicell-latch/fpga/verilog/unicell_array_latch.v`
- `unicell-latch/docs/timing.md`
- `unicell-edge/docs/timing.md`
- `unicell-standard/fpga/verilog/top_asic.v`
- `unicell-edge/fpga/verilog/top_asic.v`
- `unicell-latch/fpga/verilog/top_asic.v`

### Modified
- `unicell-latch/unicell.py` — snapshot() includes output_latch
- `unicell-latch/controller.py` — restore_snapshot() restores pipeline latches
- `unicell-latch/test_freeze.py` — 17 new freeze/move tests
- `unicell-standard/fpga/verilog/unicell.v` — Verilog-2001 fix
- `unicell-edge/fpga/verilog/unicell.v` — Verilog-2001 fix
- `unicell-edge/fpga/verilog/unicell_array.v` — BASE_ADDRESS parameter
- `MIGRATION_TODO.md` — items checked off

---

## Next session priorities

1. **Fix standard/edge yosys multiple-driver warnings**
   Split posedge/negedge output registers. Pure RTL cleanup.

2. **uart_bridge SET_FLAGS extension**
   Latch model needs a bridge command to drive start_flags_in directly.

3. **fpga_bringup.py**
   Bring-up sequence script: LED blink → UART → NOT gate → AND → bridge pair.
   Write and test against VM now. Plug-and-run when iCEBreaker arrives.

4. **LIF neuron v2**
   Port lif_neuron_reference.v from v1 to latch model.
   6-8 cells per neuron. Testable in VM. Runs on iCEBreaker at 4-5 neurons.

---

## Note for next session

The iCEBreaker (and possibly a larger FPGA) is on order.
When it arrives, the bring-up sequence is in MIGRATION_TODO.md.
The Verilog is clean and portable. The Python bridge is ready.
The VM is validated. This should be a short sprint to first silicon.

The self-growing neural cluster document is filed under Alan's vision notes.
It belongs there. The architecture already supports it — the hardware just
needs to exist first.

*Session closed 2026-05-12.*
