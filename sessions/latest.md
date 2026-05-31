# Session Log — 2026-05-31

## Status at session end
Last commit: 726389f — gol/postcode/lif fixes.
Suite: **48/48** (vm). All v2.3 changes in.

---

## What happened
Full v2.3 protocol sweep — clean base before silicon testing.

**Verilog:**
- `unicell.v` — 32-bit unified cmd_bus, CMD_BOOT_COMMIT, preload_sel, shift barrel
- `uart_bridge.v` — 9-byte frame, cpu_bus[31:0]
- `top_icebreaker.v` — wired for v2.3

**Python VM:**
- `gate_states.py` — GS_LATCH_IN bit 25→26, LOOP_MODE=0 bug, GS_FALL_EDGE added
- `unicell.py` — latch_in/invert_out read from correct separate bits
- `command_interface.py` — full v2.3 rewrite
- `fpga/fpga_bridge.py` — v2.3 + v2.2 legacy shims (protocol_v22 flag)

**Models:**
- `model_library.py` — 26→54 models, all figures verified from TileLibrary

**Composer:**
- `unicell_composer.html` — GS bits fixed, 20+ new models, tree panel enhanced

**Examples:**
- `gol.py` — retired GS_SYNC_WAIT/GS_OUT_POSEDGE removed
- `postcode_sort.py` — 775→711 cells corrected
- LIF ICM files — gs values corrected for v2.3 bit positions

**Docs:** CELL_INTERNALS, FPGA_HARDWARE, VERILOG_SPEC, COMPOUND_OPCODES,
ARCHITECTURE, PRELOAD_MODEL, DOC_AUDIT, neural_pond_design all updated.

---

## Next session — silicon testing

### Immediate
1. Build iCEBreaker bitstream — v2.3 Verilog
2. SYNC_WAIT test on 4-cell topology
3. CMD_BOOT_COMMIT first silicon test
4. Switch fpga_bridge to protocol_v22=False once verified

### Still open
- `lif_cascade.icm` gs review (same fixes as lif_neuron)
- SUB/comparison tile failures (pre-existing)
- BranchPoint.build() API mismatch
- Sentinel compiler fixes (3 gaps from 2026-05-30)
- Companion-side updates (deferred until base stable)
- OS loader architecture (documented, implementation deferred)

### Test state
- VM: 48/48
- FPGA: v2.2 format — rewrite after bring-up
- Legacy: pre-existing failures, deferred
- composer: iCEBreaker cell budget 64→4 in target dropdown (TARGETS object + select option)

---

## Side note — compiler philosophy (for next compiler session)

**The compiler must be a gatekeeper, not a cheerleader.**

It should never say "sure, let's try it" when the program is structurally
dangerous. It must say: "No. This is invalid. Here's the exact reason. Fix it."

Constructs that must be caught and rejected with clear diagnostics:

- **Self-nesting loops** — spirals into exponential cell state
- **Feedback disguised as dataflow** — cycles that look like pipelines
- **Depth-exploding expressions** — combinatorial depth that blows the pipeline
- **Aliasing tricks that collapse SSA** — address reuse breaking the single-assignment model
- **Infinite MUX forests** — conditional trees that never terminate
- **Type-poisoned expressions** — dtype contamination across incompatible operations
- **Syntactically valid but semantically lethal constructs** — passes the parser, kills the array

These are the ones that break real compilers. UniCell must reject them with
intelligence and precision, not silence or a partial cell map that fires wrong.

The cell budget isn't a soft limit — it's physics. The compiler knows the budget.
It must enforce it at compile time, not discover it at load time.

Context: the sentinel/ward/shore session exposed that the compiler was generating
646 cells for `x > 0`. It didn't warn. It didn't refuse. It just produced something
enormous and wrong. That can't happen on silicon.

---

## Side note — compiler philosophy (for next compiler session)

**The compiler must be a gatekeeper, not a cheerleader.**

It should never say "sure, let's try it" when the program is structurally
dangerous. It must say: "No. This is invalid. Here's the exact reason. Fix it."

Constructs that must be caught and rejected with clear diagnostics:

- **Self-nesting loops** — spirals into exponential cell state
- **Feedback disguised as dataflow** — cycles that look like pipelines
- **Depth-exploding expressions** — combinatorial depth that blows the pipeline
- **Aliasing tricks that collapse SSA** — address reuse breaking the single-assignment model
- **Infinite MUX forests** — conditional trees that never terminate
- **Type-poisoned expressions** — dtype contamination across incompatible operations
- **Syntactically valid but semantically lethal constructs** — passes the parser, kills the array

These are the ones that break real compilers. UniCell must reject them with
intelligence and precision, not silence or a partial cell map that fires wrong.

The cell budget is not a soft limit — it is physics. The compiler knows the budget.
It must enforce it at compile time, not discover it at load time.

Context: the sentinel/ward/shore session exposed the compiler generating 646 cells
for `x > 0`. It did not warn. It did not refuse. It produced something enormous and
wrong. That cannot happen on silicon.

---

## Silicon bring-up notes (2026-05-31 morning)

### iCEBreaker v2.3 first run
- Max frequency: **15.11 MHz** (PASS at 12 MHz) — good headroom
- ICESTORM_LC: **88% → 97%** — cell size increased by >2% per cell with v2.3 additions
  (shift barrel, preload_sel logic, gate_set filtering). Note for composer iCEBreaker target.
- Status responds immediately ✅ — bridge alive
- CMD_BOOT_COMMIT fix needed: not in boot_targeted list in unicell_array.v (fixed)
- cpu_addr mux fix: DATA_WRITE addr now in cmd_data[31:16], data in cmd_data[15:0]
- armed=1 confirmed at Step 10 after fixes ✅ — cell configuring correctly
- Cell firing pending: DATA_WRITE address format fix (rebuilding now)

### FIRST FIRE — v2.3 silicon confirmed 2026-05-31

**TWO-ARRIVAL MODEL CONFIRMED ON SILICON.**

Step 7: `FIRED addr=0x2000 data=0xefffffff`
Step 8: `FIRED addr=0x2000 data=0xefff0000`

NOT gate topology firing correctly:
- NOT(0x0000) → 0xefffffff ✓ (lower 16 bits = 0xffff, upper = bus_addr artefact)
- NOT(0xFFFF) → 0xefff0000 ✓ (lower 16 bits = 0x0000, upper = bus_addr artefact)

The 0xefff upper bits are bus_addr (0x1000) bleeding into cmd_data[31:16]
and being NOT-ed. Not a cell error — packing artefact of 16-bit DATA_WRITE format.
Lower 16 bits invert correctly. Cell gate tree is correct.

armed=4: all 4 cells arm on broadcast RECONFIGURE — expected, auth must
differentiate in multi-cell configs.

preload_sel (Step 9): no fire — all 4 cells reset and preload, interference
from broadcast. Single-cell test needed with auth isolation.

### Immediate next steps
1. Fix DATA_WRITE to send full 32-bit data cleanly (separate bus_addr from data)
2. Test preload_sel with single isolated cell (auth filtering)
3. Test XNOR comparator pattern (two different inputs)
4. Log silicon result in RESULTS.md
