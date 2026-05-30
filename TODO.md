# Imago UniCell — TODO

Last updated: 2026-05-30

---

## IMMEDIATE — Verilog / Silicon

### New gate_state bits (iCEBreaker bring-up blocked on these)

- [ ] **a_preload_en (bit A)** — when set at CMD_RECONFIGURE, cell self-loads
      a_data from a_preload_val before arming. Eliminates the entire
      preloaded-A software sequence. One bit in cmd_latch.

- [ ] **a_preload_val (bit B)** — 0 = load 0x00000000, 1 = load 0xFFFFFFFF.
      These are the only two values ever needed for constant comparisons.
      All comparison-against-constant operations reduce to one of these.

- [ ] **shift_in_en (bit C)** — incoming bus data is shifted by nibble_set
      positions before the gate tree sees it. Allows normal gate ops on
      misaligned data without extra cells.

- [ ] **shift_out_en (bit D)** — output is shifted by nibble_set positions
      before emission. Combined with shift_in_en: zero-cell shift operations
      and correct partial product placement for multiply.

- [ ] **Verilog update** — add above four bits to unicell.v cmd_latch decode.
      Confirm bit positions don't conflict with auth_mask (bits 21-11).
      Gate on auth_mask pass before applying preload.

- [ ] **SYNC_WAIT test on iCEBreaker** — 4-cell topology, confirm two-arrival
      model fires correctly before bring-up of anything more complex.

---

## COMPILER — Rewrites needed given new cell capabilities

The compiler was written before the cell's capabilities were fully understood.
It now needs to be updated to exploit what the cell can actually do.

### Comparison against constants — massive overcount

Current: `x > 0` places INT32_LT_U (518 cells) + INT32_MUX (128 cells) = 646 cells.
Correct:  `x > 0` is an OR-reduction of 32 bits = ~5 cells (log2 tree).
          With a_preload_en, each OR cell is self-armed. Single trigger wave.

- [ ] **`x > 0` / `x != 0` intercept** — detect comparison against literal 0
      in `_compile_compare_typed`. Emit OR-reduction tree (5 cells) not LT_U tile.

- [ ] **`x == CONST` intercept** — detect equality against compile-time constant.
      XOR each bit against the constant bit (using a_preload), then NOR-reduce.
      ~37 cells not 864.

- [ ] **`x > CONST` / `x < CONST` general case** — still needs LT_U tile but
      with a_preload_en the A-side is self-loaded at configure time.
      No Python forward sim needed. One pass not two.

### Branch between constants — MUX overkill

Current: `if cond: return A else: return B` where A and B are compile-time
         constants places INT32_MUX (128 cells). The MUX computes 32 bits of
         selection logic when the answer is already known at compile time.

Correct:  condition bit routes between two preloaded address sets.
          With a_preload_en: 32 cells (one per output bit), each self-loaded
          with the correct constant, gated by the condition signal.
          Or simpler: just two PTT addresses, condition selects which fires.

- [ ] **Constant-branch optimisation** — in `_compile_if`, detect when both
      branches return `_broadcast_constant` values. Emit direct preloaded
      selection, not MUX tile.

### Passthrough / identity

- [ ] **`return x` (bare passthrough)** — currently broken for zero-record
      functions (returns 0). Fixed in zero-records early-return path but
      the root issue is output_addrs == input_addrs with no cells. Document
      and test the fix holds.

### Shift operations

- [ ] **`x << N` and `x >> N`** — currently not implemented. With shift_in_en
      and shift_out_en bits these become zero-cell operations for nibble-aligned
      shifts (multiples of 4). Compiler emits shift bits in gate_state, no cells.
      Non-nibble-aligned shifts need up to 3 extra cells (< 4 bits of residual).

### Multiply

- [ ] **INT32_MUL nibble-LUT tile** — partially implemented but broken.
      Root cause identified: preloaded_a values normalised to 0/1 not 0/0xFFFFFFFF,
      causing XOR cells to compute incorrectly. With a_preload_en this entire
      approach changes — each AND cell in the partial product is self-armed,
      no Python forward sim, no preload map. Rewrite after Verilog update.

- [ ] **Partial product placement** — with shift_out_en, each nibble pair
      output lands at the correct bit position on the bus with no extra cells.
      The Wallace tree accumulation just sees numbers at the right addresses.

### Bare `if x:` (int32 as bool)

- [ ] **Int32→bool collapse fix** — currently `if x > 0:` works but `if x:`
      doesn't (PASS relay timing issue in two-arrival model). With a_preload_en
      and OR-reduction, `if x:` becomes natural. Document current workaround
      (use explicit `> 0`) until fixed.

### First-parameter one-shot exclusion

- [ ] **Multi-param MUX passthrough** — first int32 parameter goes into a_vals
      (one-shot, excluded from re-injection). Can't be used as MUX B-side value.
      Workaround: put non-passthrough param first. With a_preload_en this whole
      distinction may disappear. Document until then.

### Division

- [ ] **INT32_DIV** — not implemented. Options:
      (a) Reciprocal multiply (compile-time constant divisor only)
      (b) Non-restoring division array (expensive, ~5000 cells)
      (c) Defer — most sentinel/ward/shore logic avoids division by design
          (use shift-based threshold comparisons instead)

---

## SENTINEL / WARD / SHORE — Architecture rethink complete

The original sentinel_core.py / ward_core.py / shore_core.py (24 functions,
~82k cells total) were implementing Tier 3 policy as Tier 1 cell logic.
That was wrong. The correct decomposition:

### Tier 1 — Cells

- [ ] **3-cell Sentinel** (per monitored pipeline):
      Cell 1: in-counter  — latch+loopback on pipeline input address, counts up
      Cell 2: out-counter — latch+loopback on pipeline output address, counts down
      Cell 3: compare     — holds pipeline depth as a_data (via a_preload_en),
                            computes difference, writes raw value to PTT
      Total: 3 cells. No functions. No ICM files.

- [ ] **Ward** — reads PTT table only. No cells of its own.
      Python loop: scan PTT, compare difference to depth and cycle count,
      flag outliers to Shore pond table.

- [ ] **Shore** — tables + address space only:
      Pond table (one row per pond: PTT address, current difference, depth)
      User list
      Extended address list
      Companion space (reserved region within Shore pond)

### Tier 3 — OS Companion

- [ ] **Companion scan loop** — lives in Shore pond's reserved region:
      1. Read pond table
      2. Find need (load, evict, resize)
      3. Reserve address space
      4. Load ICM into reserved space
      5. Arm and step back

- [ ] **Throttle / evict decisions** — Tier 3 only. Not cells.

---

## BOOTLOADER

- [ ] **`.isi` writer for real arrays** — `from_controller_records()` exists,
      needs end-to-end test: compile → write .isi → load onto iCEBreaker.

- [ ] **`.isi` loader in Verilog** — SPI/UART receiver that reads .isi header,
      streams cell table to CMD_RECONFIGURE, sends arm pulse at entry_point.
      This is the static boot sequence for embedded targets.

- [ ] **Pond image (`.ipi`)** — subset of .isi for single-pond migration.
      ADDRESS MAP remap logic when target system base addresses differ.

- [ ] **Bootloader test on iCEBreaker** — write 3-cell sentinel .isi,
      load via iceprog or UART, verify PTT difference updates correctly.

- [ ] **Clean up sentinel_core.py / ward_core.py / shore_core.py** — these
      files and their ICM outputs are now superseded by the architecture rethink.
      Archive or delete. The functions document what Tier 3 *will* do, not
      what cells should implement.

---

## KNOWN BUGS (compiler)

- [ ] **MUL preloaded_a normalisation** — 0/1 values reach XOR cells as
      single bits not 0xFFFFFFFF. `XOR(1, 0xFFFFFFFF) = 0xFFFFFFFE` (wrong).
      Fix: normalise before controller run. Moot after a_preload_en lands.

- [ ] **Output padding uses bare GS_PASS** — `_place_int32_tile` pads output
      bits with `GS_PASS` (gs=0x0) not `GS_PASS | GS_LATCH_IN`. Bare PASS
      waits for two arrivals; in a single-wave propagation it never fires.
      Fix committed but cache may return old tile — clear cache on tile rebuild.

- [ ] **Duplicate `compile_int32_function`** — two definitions in compiler_int32.py
      (lines 136 and 1135). Line 1135 wins (Python last-wins). Line 136 is dead.
      Clean up.

- [ ] **`bus_pressure_band` cell count** — 37k cells due to addition chains
      replacing multiply/divide. Moot once shift bits land (shift = multiply
      by power of 2, covers most threshold comparisons).

---

## TESTS

- [ ] **Bootloader test suite** — `bootloader/tests/test_icms.py` (105 tests)
      tests the old sentinel/ward/shore functions. Update to test the 3-cell
      sentinel .isi round-trip instead.

- [ ] **SYNC_WAIT hardware test** — `tests/fpga/` — needs `pyserial`.

- [ ] **Add .isi round-trip test** — write, read back, verify all cells match.

---

## KINTEX-7

- [ ] **Top-level module** — Kintex-7 wrapper around cell array.
- [ ] **Pre-register `bus_hit`** — fan-out prep for large arrays.
- [ ] **Scale test** — confirm cell count budget for 150k cell target.

---

## NOTES FOR NEXT SESSION

Start with:
1. Verilog update for the 4 new bits (a_preload_en, a_preload_val, shift_in/out)
2. SYNC_WAIT test on iCEBreaker with existing bitstream
3. Then 3-cell sentinel .isi → load → verify PTT on hardware
