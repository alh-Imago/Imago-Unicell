# Session 2026-05-05

## Context

iCEBreaker confirmed with local courier — board arriving today.
Priority: ensure everything is ready for first hardware bring-up.
Secondary: Alan's ideas on multiplier architecture + Composer UX improvements.

Baseline at session open: 546 tests, 0 failures (previous session).

---

## Part 1 — EDA Playground confirmation

Alan provided the simulation result zip from yesterday's EDA Playground run.
Extracted and verified:

- Simulator: Icarus Verilog
- Date: 2026-05-03
- Testbench: tb_unicell_latch.v (22 tests)
- Result: **22 passed, 0 failed**
- VCD dump confirmed: pass_count 0→22, fail_count stayed 0
- Reference: https://edaplayground.com/x/pVQp

External silicon-level validation now confirmed on three legs:
Python simulation (684+ tests), Yosys lint (0 warnings/errors),
Icarus Verilog waveform simulation (22/22).

---

## Part 2 — Composer UX: seven improvements (v2.0)

Alan's review list — all seven implemented in a full rewrite:

| Feature | Detail |
|:--------|:-------|
| Zoom & pan | Cursor-centred zoom (1.12× per tick), middle-btn/Space+drag, 0.2×–4× |
| Multi-select | Shift+click toggle, drag marquee box, works with delete/dup/drag |
| Drag-from-port | Drag green output port in select mode — no tool switch needed |
| Undo/Redo | 50-level stack, Ctrl+Z/Y, button opacity reflects availability |
| Simulation | JS tick engine: PASS/NOT/NOR/AND/OR/NAND/XOR/ZERO/ONE, LOOP_MODE, live 120ms, inject, bus state panel, cell overlay |
| Conflict detection | Duplicate addrIn/addrOut in red, ⚠ badge in status bar |
| Keyboard shortcuts | S/L/N/D/F, Del, Esc, Ctrl+Z/Y/S/A/O/D |

**Tagged: `composer-v2.0`**

---

## Part 3 — Model integrity + security_context

- SHA-256 `record_hash` embedded in every `.icm` export
- Canonical form: records array with fixed key order (alt,gs,in,inB,init,out,stor)
- Python and JS produce identical canonical strings — cross-platform verification
- Import verifies hash; mismatch shows warning dialog
- `security_context: null` — explicit blank field, system-assigned at load time
- Non-null security_context on import triggers alert
- `verify_icm()` helper documented in `composer/README.md`
- All community model `.icm` files updated with hash + sc field

---

## Part 4 — Community model library

`composer/` directory established as community model exchange:

```
composer/
├── unicell_composer.html     ← standalone visual designer (no server)
├── README.md                 ← usage, .icm format, contribution guide
├── models/
│   ├── INDEX.md              ← community registry table
│   └── neural/
│       └── LIF_NEURON_6CELL_v1.icm  ← first model, VM-verified, hashed
└── examples/
    ├── not_gate.icm
    └── and_gate.icm
```

The `.icm` format is the universal portable program representation:
Composer → .icm → VM → iCEBreaker → future ASIC.

---

## Part 5 — INT32 multipliers: Dadda tree + Booth radix-4

Alan's two ideas:
- **Absolute speed**: Dadda tree (minimum gate depth)
- **Efficient speed**: Booth radix-4 (fewer cells, same depth)

### INT32_MUL_DADDA — 23,924 cells, depth ~39 (WORKING, default)

Full 32×32 partial product matrix (528 AND2 cells, lower triangle).
Compressed using Dadda schedule: 28→19→13→9→6→4→3→2 rows (~8 stages).
Final CLA adder on two-row residue.

**Key engineering note:** Standard `NORBuilder.NOR2` inserts `pad_to_depth`
PASS cells to balance signal timing — correct for combinational networks but
catastrophic for Dadda trees (produced ~900,000 PASS cells for a 32×32 multiply).
Fixed by `_build_dadda_compress` using raw `_emit` calls (depth-unaware XOR/AND),
letting SYNC_WAIT/final adder absorb the skew.

Now the default compiler target for `int32 *`:
```python
model_library.for_op('Mult', 'int32')  # → INT32_MUL_DADDA
```

### INT32_MUL_BOOTH — 109,458 cells, depth ~35 (parked)

Built and registered but not the default. Booth radix-4 encodes B into
17 signed partial products (vs 32 for Dadda) — correct in principle.
But MUX2 encoding chains are expensive in NOR-only fabric: the encoding
overhead outweighs the compression benefit.

Correct approach: use `gate_state` SELECT field for digit selection rather
than MUX2 trees. Estimated correct cell count: ~8,000–12,000.
Parked pending NOR-efficient encoding rewrite.

### Compiler option routing (new)

```python
model_library.set_option('int32_mul', 'booth')  # select Booth
model_library.set_option('int32_mul', 'dadda')  # back to default
model_library.for_op('Mult', 'int32')            # respects override
```

`ModelLibrary.set_option()` and `get_option()` added.
`for_op()` checks `_options` override before `_op_index` default.

---

## Part 6 — Composer placeholder cards for large models

Large models (>1000 cells) cannot fit in a 64-cell iCEBreaker pond and
cannot be loaded as flat CellMapRecord lists in a standard .icm.

**Solution:** placeholder cards and blocks.

Library panel:
- Greyed-out card with amber hover, `⊡` marker
- Real cell count + depth shown in red
- Full description on hover
- Clickable — drops a placeholder block for architectural sketching

Canvas placeholder blocks:
- Amber dashed border, diagonal hatch fill
- Shows: model name, cells, depth, `TODO: pond addressing`
- No port dots (can't wire)
- Excluded from `.icm` export with status warning

Large models marked placeholder:
| Model | Cells | Depth | Reason |
|:------|------:|------:|:-------|
| INT32_MUL_DADDA | 23,924 | 39 | Needs dedicated pond |
| INT32_MUL_BOOTH | 109,458 | 35 | Parked + needs pond |
| FP32_MULTIPLIER | 35,000 | 80 | v2 tile not yet rebuilt |
| DISPLAY_OUTPUT | 18,600 | — | Peripheral pond needed |

**MIGRATION_TODO.md** updated with full problem description:
pond-level addressing, multi-pond .icm format schema, multi-pond
`controller.load_map()`, Booth radix-4 rewrite path.

---

## Commits this session

| Hash | Description |
|:-----|:------------|
| `0f383c6` | RTL: fix multiple-driver warnings (standard + edge) |
| `642f464` | uart_bridge: SET_FLAGS (0x08) command |
| `9fe546c` | lif_neuron_v2: 6-cell LIF neuron for latch model |
| `7a2f7d4` | unicell_composer.html: full 32-bit visual designer |
| `b58ac41` | composer/: community model library |
| `aedb6ba` | composer: SHA-256 hash + security_context |
| `07f039c` | composer v2: seven UX improvements |
| `01729a1` | docs: composer README v2 |
| `a70d5e2` | fpga_bringup.py: six-step bring-up sequence |
| `c5a1d28` | INT32 multipliers: Dadda + Booth |
| `d3705a8` | composer: placeholder cards for large models |

**Tag:** `composer-v2.0`

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
| test_lif_neuron_v2.py | 39 | 0 |
| test_fpga_bringup.py | 47 | 0 |
| test_fp_tiles.py | 138 | 0 |
| **Total** | **684** | **0** |

Yosys lint: **0 warnings, 0 errors** (all three variants).

---

## Next session priorities

1. **iCEBreaker bring-up** — board arriving today
   `python fpga_bringup.py --port /dev/ttyUSB0`
   Flash `top_icebreaker.v` bitstream first (nextpnr-ice40 + iceprog)

2. **Booth radix-4 rewrite** — use SELECT gate instead of MUX2 chains
   Target: ~8,000–12,000 cells, depth ~35

3. **Large model pond import** — multi-pond .icm format
   See MIGRATION_TODO.md: Composer — Large Model Import

4. **fpga_bringup.py** — step 5 (bridge pair) improvement
   Currently uses relay chain; should test actual Pond isolation via
   pond.py security boundary

*Session closed 2026-05-05.*

---

## Part 7 — NORBuilder audit and native gate upgrade (all variants)

### What was found

Alan correctly identified that the NORBuilder was not using the full
capability of the cells. The cells are not purely NOR gates — the
gate_state register exposes native two-input operations via
GS_SYNC_WAIT | GS_*_V2, and single-cell conditional routing via
GS_SELECT.

The NORBuilder was decomposing every gate into NOR chains:
- AND2 = NOT + NOT + NOR2 = 5 cells
- OR2  = NOR2 + NOT = 5 cells  
- XOR2 = 17 cells
- MUX2 = ~22 cells

After upgrade using native modes:
- AND2 = 1 cell (GS_SYNC_WAIT | GS_AND_V2)
- OR2  = 1 cell (GS_SYNC_WAIT | GS_OR_V2)
- XOR2 = 1 cell (GS_SYNC_WAIT | GS_XOR_V2)
- MUX2 = 4 cells (NOT + AND + AND + OR, all native)
- SYNC_WAIT = 1 cell (GS_SYNC_WAIT | GS_PASS_B_V2)

SELECT() method added to NORBuilder for future Booth encoding rewrite.

### Bugs found during audit

**PASS_A_V2 / PASS_B_V2 naming swapped in gate_states.py.**
GS_PASS_B_V2=0 (all bypass) actually passes A through the gate tree.
GS_PASS_A_V2=0b101100 passes B. The constants are correct as coded —
only the labels were reversed. Fixed with clarifying comment.

**NORBuilder.SYNC_WAIT used wrong gate state.**
Was: GS_SYNC_WAIT | GS_PASS_A_V2 (passes B).
Fixed: GS_SYNC_WAIT | GS_PASS_B_V2 (= GS_SYNC_WAIT | 0, passes A).

**TilePlacer did not remap input_b_address.**
Two-input cells store their B address in input_b_address. TilePlacer
was constructing placed_records without it, breaking functional tests
after the NORBuilder upgrade. Fixed: address scan includes
input_b_address, placed_records carries it through.

### Verilog confirmed consistent

unicell_latch.v: gate tree is 1-bit (a_in = input_ff[0]).
Python VM: gate tree is 32-bit, NOR returns 0xFFFFFFFF for logical 1.
Downstream cells read input_ff[0] so 0xFFFFFFFF[0]=1. Both correct.
All five gates AND/OR/XOR/NAND/XNOR produce matching 1-bit results.

### Scope — all four variants updated

The upgrade was initially applied only to unicell-latch. All four
codebases (unicell-latch, unicell-standard, unicell-edge, root) share
the same gate_state capability and unicell.py implementation. Fix
propagated to all.

| Variant | fp_tiles | gate_states | test_fp_tiles |
|:--------|:--------:|:-----------:|:-------------:|
| unicell-latch | ✅ | ✅ | 138/138 |
| unicell-standard | ✅ | ✅ | 134/134 |
| unicell-edge | ✅ | ✅ | 134/134 |
| root | ✅ | ✅ | — |

### Root codebase note

The root `/` fp_tiles.py and gate_states.py are the original pre-variant
codebase. They will be **retired once the iCEBreaker confirms cell
viability on hardware**. At that point unicell-latch becomes the
canonical implementation and the root + standard + edge variants
are archived. This is tracked in MIGRATION_TODO.md.

### Effect on multiplier cell counts

| Tile | Before | After |
|:-----|-------:|------:|
| INT32_MUL_DADDA | 23,924 | 21,812 |
| INT32_MUL_BOOTH | 109,458 | 19,554 |
| INT32_ADD | ~6,200 | 157 |
| FP32_ADD | ~3,000 est | 1,253 real |
| FP32_MUL | ~35,000 est | 3,066 real |

Booth is now genuinely competitive: 19,554 cells vs 21,812 for Dadda,
4 pipeline levels shallower. Full benefit awaits Booth encoding rewrite
using SELECT instead of MUX2 chains.

---

## Session note: root codebase retirement

The root `/fp_tiles.py`, `/gate_states.py` and related files are the
original codebase predating the standard/edge/latch split. They remain
in the repo for reference and are updated in sync.

**Retirement trigger: iCEBreaker bring-up all 6 steps pass.**

Once the board confirms silicon viability, the MIGRATION_TODO.md
Tier 1 items retire and unicell-latch becomes canonical.
The root and variant codebases will be archived at that point.
This is already tracked in MIGRATION_TODO.md.

*Back soon.*

---

## Session 2026-05-06 — Latch Variant Silicon Validation

### RESULT: LATCH VARIANT VALIDATED ON iCEBreaker

```
NOT(0) = 1 ✓    NOT(1) = 0 ✓
NAND(0,0) = 1 ✓  NAND(0,1) = 1 ✓
NAND(1,0) = 1 ✓  NAND(1,1) = 0 ✓
Fired: 10, Errors: 0
```

### BUGS FOUND AND FIXED

**Bug 1: start_flags_wire hardwired high**
cells accepted input before config completed. input_address initialises
to 0x0000 (same as CONFIG_ADDRESS), so config words were loading into
input_ff simultaneously with being parsed by the config state machine.

Fix: armed_reg register added to unicell_latch.v
- Starts at 0 (unarmed)
- Set to 1 at end of CFG_LOAD_OADDR and CFG_LOAD_BADDR (self-arm)
- All compute/drain/input logic gates on armed = armed_reg
- top_icebreaker.v: start_flags_wire tied LOW (cells self-arm)

**Bug 2: timing closure at 24MHz**
32-bit address comparator is the critical path (~23MHz max without hint).
Fix: dbg_armed = armed_reg | cfg_state bits
The fanout from cfg_state changes placer decisions → 25-26MHz PASS.

**Bug 3: uart_bridge dropped fired events**
Cell fires 2 cycles after inject (~83ns at 24MHz).
Previous status response still transmitting when cell fires.
Fix: fired_pending latch in uart_bridge.v — buffers event until TX free.

### SYNTHESIS RESULTS (unicell-latch, 8 cells, iCEBreaker)

```
ICESTORM_LC: 3780 / 5280  (71%)
Max freq:    25.37 MHz → 26.82 MHz (PASS at 24MHz)
LUTs/cell:   ~420 after P&R
```

### BRING-UP SEQUENCE STATUS

```
Stage 1: LED blink          ✓ COMPLETE
Stage 2: UART loopback      ✓ COMPLETE
Stage 3: NOT gate (standard)✓ COMPLETE (14 May 2026, birthday)
Stage 4: NOT gate (latch)   ✓ COMPLETE (06 May 2026)
Stage 4: NAND wired-OR      ✓ COMPLETE (latch variant)
Stage 5: Bridge pair        PENDING
Stage 6: Scale              PENDING
```

### NOTABLE

- Latch variant responds noticeably faster than standard model
- Two-cycle pipeline tighter than standard combinational path
- Cell self-arms after config (same pattern as standard model)
- fired_pending latch fix benefits all variants going forward


---

## Session 2026-05-07 — Split Variant Attempt

### RESULT: Split variant not viable on iCEBreaker

**Problem 1: iCE40UP5K has only ONE SB_HFOSC primitive.**
Two SB_HFOSC instances (24MHz + 48MHz) cannot both be placed — they
compete for the same physical oscillator. Hardware constraint, not
fixable in Verilog.

Alternative for 2x clock: SB_PLL40_CORE could derive 48MHz from
24MHz input, but adds complexity and LUTs.

**Problem 2: LUT count worse not better.**
Split variant: 5516 LUTs (104%) — exceeds iCEBreaker capacity.
Standard latch: 3780 LUTs (71%).

The 16-bit tree saves ~144 LUTs but the overhead costs more:
- Clock domain crossing logic
- half register + mux
- lower_result register
- Two separate always blocks

The synthesiser sees the full picture — splitting the tree doesn't
save LUTs when the crossing overhead exceeds the tree saving.

### CONCLUSION

Split variant abandoned. Latch variant (unicell_latch.v) is the
production cell for iCEBreaker.

**Real path to LUT reduction:** Narrow address width from 32-bit to
16-bit. The 32-bit address comparators are the actual critical path
bottleneck (~10 LUTs per comparator × 4 comparators per cell × 8 cells).
16-bit addresses would halve comparator cost and improve timing margin.
This is a TODO for a future variant.

### CURRENT STATUS

Validated on iCEBreaker:
- Standard model (unicell.v): NOT gate, NAND via wired-OR ✓
- Latch model (unicell_latch.v): NOT gate, NAND via wired-OR ✓

Next: Edge variant, or 16-bit address optimisation, or Stage 5 (bridge pair).

---

## Session 2026-05-07 (continued) — Stage 5 Bridge Pair Validated

### RESULT: STAGE 5 COMPLETE

```
double_NOT(0) = 0 ✓    double_NOT(1) = 1 ✓
NAND(0,0) = 1 ✓        NAND(0,1) = 1 ✓
NAND(1,0) = 1 ✓        NAND(1,1) = 0 ✓
```

### WHAT WAS PROVEN

Cell 0 (NOT): input=0x1000, output=0x5000 (intermediate bus address)
Cell 1 (NOT): input=0x5000, output=0x2000 (final output)

Inject to 0x1000 → cell 0 fires → result on bus at 0x5000 →
cell 1 sees it automatically → cell 1 fires → result at 0x2000.

No controller involvement. No explicit routing. The wired-OR bus
propagates the first cell's output to the second cell's input
automatically. Computation flows through the fabric by physics.

Visible in raw RX bytes — two fired packets back to back:
  10 00005000 00000001 02   <- cell0 fired NOT(0)=1 to 0x5000
  10 00002000 00000000 02   <- cell1 fired NOT(1)=0 to 0x2000

### BRING-UP SEQUENCE STATUS

```
Stage 1: LED blink          ✓ COMPLETE
Stage 2: UART loopback      ✓ COMPLETE
Stage 3: NOT gate (standard)✓ COMPLETE (14 May 2026)
Stage 4: NOT gate (latch)   ✓ COMPLETE (06 May 2026)
Stage 5: Bridge pair        ✓ COMPLETE (07 May 2026)
Stage 6: Scale (8 cells)    NEXT
```

### NEXT: Stage 6

Scale to full 8 cells. Test patterns:
- 4-cell NOT chain (4 cascaded inversions)
- 3-input NAND (3 NOT cells → wired-OR shared address)
- 8-cell parallel firing (all cells fire simultaneously)
- Mixed: some cells chained, some parallel


---

## Session 2026-05-07 (continued) — Stage 6 Scale Validated

### RESULT: STAGE 6 COMPLETE — BRING-UP SEQUENCE FINISHED

```
Test 1: 4-cell NOT chain    2/2  ✓
Test 2: 3-input NAND        8/8  ✓
Test 3: 8-cell parallel     8/8  ✓
```

### BRING-UP SEQUENCE: ALL STAGES COMPLETE

```
Stage 1: LED blink          ✓  (board alive)
Stage 2: UART loopback      ✓  (comms working)
Stage 3: NOT gate (standard)✓  14 May 2026
Stage 4: NOT gate (latch)   ✓  06 May 2026
Stage 5: Bridge pair        ✓  07 May 2026
Stage 6: Scale (8 cells)    ✓  07 May 2026
```

### WHAT WAS PROVEN TODAY

Test 1 — 4-cell chain:
  Computation propagates automatically through 4 cells.
  Each cell's output feeds the next via the wired-OR bus.
  No controller involvement. Depth-4 chain, correct result.

Test 2 — 3-input NAND (8/8 truth table):
  Three NOT cells writing to the same bus address.
  Physics (wired-OR) combines the outputs correctly.
  All 8 input combinations verified.

Test 3 — 8-cell parallel (8/8 simultaneous):
  All 8 cells configured, armed, fire simultaneously.
  8 fires returned in one burst.
  True parallel computation on real iCE40 silicon.

### ARCHITECTURE VALIDATED END TO END

- Single cell logic ✓
- Self-arming after config ✓
- Bus addressing ✓
- Wired-OR arbitration ✓
- Cell chaining (depth 4) ✓
- 3-input wired-OR NAND ✓
- 8-cell parallel firing ✓

The architecture works. All layers validated on silicon.
Next: Tier 2 migration (compiler, OS layer, LLVM), or edge variant.

